"""Open Targets Platform target-disease evidence -> preclin.ot_association.

    python -m pipeline.opentargets fetch  # DATASETS of the release -> .cache/opentargets/<release>/<dataset>
    python -m pipeline.opentargets load   # release files in .cache/opentargets/<release>
    python -m pipeline.opentargets evidence  # evidence rows behind those associations, dated; mouse phenotypes
    python -m pipeline.opentargets dates     # re-date the rows from preclin.evidence_known_year, rebuild the series

Loads direct associations by data source for the targets of every molecular
entity with an industry-sponsored development program (preclin.moiety_target).
`evidence` and `dates` date each evidence item by the year it became known (the
year preclin.evidence_known_year, filled by pipeline.evidence_dates, holds for its
preclin.ot_evidence_key, else its own publication or evidence date) and rebuild
each association's yearly score series from the dated items in the database
(preclin.harmonic_series), so evidence can be taken as of a date; undated items
count only in the release score.
Sources that encode clinical outcomes or literature co-mention
(clinical_precedence, europepmc, cancer_biomarkers) are not loaded.
Disease identifiers are kept as Open Targets ids in preclin.ot_disease, each
with the MONDO terms it is (mondo_disease); traits and measurements that are
not diseases have none. `evidence` keeps, for the same targets and sources, each
evidence item with its date, direction of effect, confidence and source detail
(preclin.ot_evidence), and the targets' mouse mutant phenotypes
(preclin.ot_mouse_phenotype).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import os
import re
from collections import defaultdict

import pyarrow.dataset as ds
import requests
from psycopg2.extras import Json, execute_values

from pipeline import llm

RELEASE = "26.09"
CACHE = os.path.join(llm.REPO, ".cache", "opentargets", RELEASE)
SOURCE_URL = f"https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/{RELEASE}/output"
DATASETS = ("association_by_datasource_direct", "disease")  # the release datasets load reads
EVIDENCE_DATASETS = ("evidence_gwas_credible_sets", "evidence_gene_burden", "evidence_eva", "evidence_genomics_england",
                     "evidence_orphanet", "evidence_gene2phenotype", "evidence_clingen", "evidence_uniprot_literature",
                     "evidence_uniprot_variants", "evidence_cancer_gene_census", "evidence_intogen",
                     "evidence_eva_somatic", "evidence_impc", "evidence_expression_atlas", "evidence_reactome",
                     "evidence_crispr", "evidence_crispr_screen")  # the evidence rows evidence reads
MOUSE_PHENOTYPE = "mouse_phenotype"  # mouse-model phenotypes per target, which evidence also reads
# Disease-concept vocabularies MONDO declares one-to-one equivalences with; OMIM entries are often
# gene-specific forms and ICD codes classification groups, so neither identifies a disease.
CONCEPT_XREFS = ("DOID", "Orphanet", "NCIT", "MESH")
GERMLINE_DATASOURCES = ("gwas_credible_sets", "gene_burden", "eva", "genomics_england", "orphanet",
                        "uniprot_literature", "uniprot_variants", "gene2phenotype", "clingen")
CLINVAR_PATHOGENIC = ("pathogenic", "likely pathogenic")  # the ClinVar significances that count as evidence
DATASOURCES = {
    # germline genetics
    "gwas_credible_sets": "genetic", "gene_burden": "genetic", "eva": "genetic", "genomics_england": "genetic",
    "orphanet": "genetic", "uniprot_literature": "genetic", "uniprot_variants": "genetic",
    "gene2phenotype": "genetic", "clingen": "genetic",
    # somatic
    "cancer_gene_census": "somatic", "intogen": "somatic", "eva_somatic": "somatic",
    # model organisms, expression, pathways, functional screens
    "impc": "animal_model", "expression_atlas": "rna_expression", "reactome": "affected_pathway",
    "crispr": "functional_screen", "crispr_screen": "functional_screen",
}


# Source-specific fields kept in ot_evidence.detail.
DETAIL = {
    "gwas_credible_sets": ("studyLocusId",),
    "gene_burden": ("beta", "oddsRatio", "pValueMantissa", "pValueExponent", "projectId", "statisticalMethod",
                    "studyCasesWithQualifyingVariants"),
    "eva": ("clinicalSignificances", "alleleOrigins", "studyId", "variantId"),
    "eva_somatic": ("clinicalSignificances", "variantId"),
    "genomics_england": ("studyId", "studyOverview"),
    "orphanet": ("alleleOrigins",),
    "gene2phenotype": ("studyId",),
    "clingen": ("studyId",),
    "uniprot_literature": ("targetModulation",),
    "uniprot_variants": ("targetModulation", "variantId"),
    "cancer_gene_census": ("mutatedSamples",),
    "intogen": ("cohortShortName", "significantDriverMethods"),
    "impc": ("biologicalModelId", "biologicalModelAllelicComposition", "biologicalModelGeneticBackground",
             "targetInModel"),
    "expression_atlas": ("studyId", "contrast", "log2FoldChangeValue", "log2FoldChangePercentileRank"),
    "reactome": ("reactionName", "targetModulation"),
    "crispr": ("diseaseCellLines",),
    "crispr_screen": ("studyId", "contrast", "log2FoldChangeValue", "cellType"),
}
EVIDENCE_COLUMNS = ("id", "targetId", "diseaseId", "datasourceId", "score", "resourceScore", "publicationDate",
                    "evidenceDate", "releaseDate", "directionOnTarget", "directionOnTrait", "confidence",
                    "allelicRequirements", "variantFunctionalConsequenceId", "literature",
                    "diseaseModelAssociatedModelPhenotypes", "diseaseModelAssociatedHumanPhenotypes")


def curie(ot_id: str) -> str:
    prefix, _, local = ot_id.partition("_")
    return f"{prefix}:{local}" if local else ot_id


def mondo_disease(disease_id: str, xrefs: list[str], equivalent: dict[str, set[str]]) -> list[str]:
    """MONDO terms an Open Targets disease is: its own MONDO id or MONDO cross-references; else the
    terms MONDO declares equivalent to its id; else the one term MONDO declares equivalent to its
    CONCEPT_XREFS cross-references (an EFO disease MONDO knows only by its DOID or Orphanet id), none
    when they point at several."""
    direct = {x for x in xrefs if x.startswith("MONDO:")} | ({disease_id} if disease_id.startswith("MONDO:") else set())
    if direct:
        return sorted(direct)
    if equivalent.get(disease_id):
        return sorted(equivalent[disease_id])
    via = set().union(*(equivalent.get(x, set()) for x in xrefs if x.split(":", 1)[0] in CONCEPT_XREFS))
    return sorted(via) if len(via) == 1 else []


def fetch(_args) -> None:
    """Every parquet file of each of DATASETS, EVIDENCE_DATASETS and MOUSE_PHENOTYPE, as listed by the release's
    directory index. A file
    already in the cache is kept; a download lands under a dot-prefixed name (which glob and
    pyarrow skip) and is renamed into place once complete."""
    session = requests.Session()
    for dataset in (*DATASETS, *EVIDENCE_DATASETS, MOUSE_PHENOTYPE):
        url = f"{SOURCE_URL}/{dataset}/"
        index = session.get(url, timeout=60)
        index.raise_for_status()
        names = sorted(set(re.findall(r'href="(?:[^"]*/)?([^"/]+\.parquet)"', index.text)))
        if not names:
            raise RuntimeError(f"no parquet files listed at {url}")
        os.makedirs(os.path.join(CACHE, dataset), exist_ok=True)
        for name in names:
            dest = os.path.join(CACHE, dataset, name)
            if os.path.exists(dest):
                continue
            part = os.path.join(CACHE, dataset, f".{name}.part")
            with session.get(url + name, stream=True, timeout=600) as r, open(part, "wb") as f:
                r.raise_for_status()
                for block in r.iter_content(1 << 20):
                    f.write(block)
            os.replace(part, dest)
        print(f"{dataset}: {len(names)} files -> {os.path.join(CACHE, dataset)}", flush=True)


def release_and_targets(cur, name: str, datasets: list[str], metadata: dict) -> tuple[int, list[str]]:
    """Register the release behind `datasets` (by the sha256 of their cached files), and return it
    with the Ensembl ids of every entity target, the targets the loaders keep."""
    files = sorted(f for d in datasets for f in glob.glob(os.path.join(CACHE, d, "*.parquet")))
    digest = hashlib.sha256("".join(llm.sha256_file(f) for f in files).encode())
    release = llm.register_release(cur, name, RELEASE, SOURCE_URL, digest.hexdigest(),
                                   {"datasets": datasets, **metadata, "sha256_of": "concatenated per-file sha256"})
    cur.execute("""SELECT DISTINCT t.ensembl_id FROM preclin.moiety_target mt
                   JOIN public.targets t ON t.id = mt.target_id WHERE t.ensembl_id IS NOT NULL""")
    return release, [r[0] for r in cur.fetchall()]


def load(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        release, targets = release_and_targets(cur, "open_targets_platform", list(DATASETS),
                                               {"datasources": DATASOURCES})
        cur.execute("""SELECT x.xref_id, x.term_id FROM preclin.ontology_xref x
                       JOIN preclin.ontology_term t ON t.term_id = x.term_id
                       WHERE x.ontology = 'MONDO' AND x.equivalent AND NOT t.is_obsolete""")
        equivalent = defaultdict(set)
        for xref, term in cur.fetchall():
            equivalent[xref].add(term)

    diseases = ds.dataset(os.path.join(CACHE, "disease"), format="parquet").to_table(
        columns=["id", "name", "dbXRefs", "therapeuticAreas"]).to_pylist()
    disease_rows = [(curie(d["id"]), d["name"], mondo_disease(curie(d["id"]), d["dbXRefs"] or [], equivalent),
                     [curie(t) for t in d["therapeuticAreas"] or []], release) for d in diseases]

    assoc = ds.dataset(os.path.join(CACHE, "association_by_datasource_direct"), format="parquet")
    table = assoc.to_table(
        columns=["diseaseId", "targetId", "aggregationValue", "associationScore", "evidenceCount"],
        filter=ds.field("aggregationValue").isin(list(DATASOURCES)) & ds.field("targetId").isin(targets))
    # The yearly series are left empty here: `evidence` builds them from the evidence rows as dated there.
    rows = [(r["targetId"], curie(r["diseaseId"]), r["aggregationValue"], DATASOURCES[r["aggregationValue"]],
             r["associationScore"], r["evidenceCount"], None, [], [], release) for r in table.to_pylist()]
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.ot_association")
        cur.execute("DELETE FROM preclin.ot_disease")
        execute_values(cur, """INSERT INTO preclin.ot_disease (disease_id, name, mondo_ids, therapeutic_areas,
                                 source_release_id) VALUES %s""", disease_rows, page_size=5000)
        execute_values(cur, """INSERT INTO preclin.ot_association
              (target_ensembl, disease_id, datasource, datatype, score, evidence_count, first_year,
               series_years, series_scores, source_release_id) VALUES %s""", rows, page_size=5000)
        conn.commit()  # one transaction: readers never see a half-loaded table
    print(f"release={RELEASE} targets={len(targets)} associations={len(rows)} diseases={len(disease_rows)}")


def evidence_row(r: dict, release: int) -> tuple:
    day = r.get("publicationDate") or r.get("evidenceDate") or r.get("releaseDate")
    detail = {k: r[k] for k in DETAIL.get(r["datasourceId"], ()) if r.get(k) not in (None, [], "")}
    detail["n_literature"] = len(r.get("literature") or [])
    if r.get("diseaseModelAssociatedModelPhenotypes"):  # mouse phenotypes that matched the disease's
        detail["model_phenotypes"] = [p["label"] for p in r["diseaseModelAssociatedModelPhenotypes"]][:10]
        detail["n_human_phenotypes"] = len(r.get("diseaseModelAssociatedHumanPhenotypes") or [])
    return (r["id"], r["targetId"], curie(r["diseaseId"]), r["datasourceId"], r.get("score"), r.get("resourceScore"),
            int(day[:4]) if day else None, r.get("directionOnTarget"), r.get("directionOnTrait"), r.get("confidence"),
            r.get("allelicRequirements"), r.get("variantFunctionalConsequenceId"), Json(detail), release)


def apply_dates(cur) -> None:
    """Date every evidence row by the year preclin.evidence_known_year holds for its key, else its own
    (source) year, and rebuild each association's yearly series from the dated rows."""
    cur.execute("""UPDATE preclin.ot_evidence
                   SET evidence_year = source_year,
                       year_basis = CASE WHEN source_year IS NOT NULL THEN 'open_targets' END
                   WHERE evidence_year IS DISTINCT FROM source_year
                      OR year_basis IS DISTINCT FROM CASE WHEN source_year IS NOT NULL THEN 'open_targets' END""")
    cur.execute("""UPDATE preclin.ot_evidence e SET evidence_year = k.year, year_basis = k.basis
                   FROM preclin.evidence_known_year k
                   WHERE k.datasource = e.datasource AND k.key = preclin.ot_evidence_key(e.datasource, e.detail)""")
    cur.execute("UPDATE preclin.ot_association SET series_years = '{}', series_scores = '{}', first_year = NULL")
    cur.execute("""UPDATE preclin.ot_association a
                   SET series_years = s.years, series_scores = s.scores, first_year = s.years[1]
                   FROM (SELECT target_ensembl, disease_id, datasource,
                                (preclin.harmonic_series(array_agg(evidence_year ORDER BY evidence_year, score),
                                                         array_agg(score ORDER BY evidence_year, score))).*
                         FROM preclin.ot_evidence WHERE evidence_year IS NOT NULL AND score > 0
                         GROUP BY 1, 2, 3) s
                   WHERE (a.target_ensembl, a.disease_id, a.datasource) = (s.target_ensembl, s.disease_id, s.datasource)""")


def dates(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        apply_dates(cur)
        cur.execute("""SELECT coalesce(year_basis, 'undated'), count(*) FROM preclin.ot_evidence GROUP BY 1 ORDER BY 1""")
        counts = cur.fetchall()
        conn.commit()
    print(", ".join(f"{b}={n}" for b, n in counts))


def evidence(_args) -> None:
    """Evidence rows with their own dates, then dated by preclin.evidence_known_year and the association
    series rebuilt from them (apply_dates), so evidence as of a year counts only what was known by then."""
    with llm.connect() as conn, conn.cursor() as cur:
        release, targets = release_and_targets(cur, "open_targets_platform_evidence",
                                               [*EVIDENCE_DATASETS, MOUSE_PHENOTYPE], {})
    rows = []
    for name in EVIDENCE_DATASETS:
        data = ds.dataset(os.path.join(CACHE, name), format="parquet")
        columns = [c for c in {*EVIDENCE_COLUMNS, *(k for v in DETAIL.values() for k in v)} if c in data.schema.names]
        table = data.to_table(columns=columns, filter=ds.field("targetId").isin(targets)
                              & ds.field("datasourceId").isin(list(DATASOURCES)))
        rows += [evidence_row(r, release) for r in table.to_pylist()]
    # A human gene with several mouse orthologs has one row per ortholog for the same phenotype: their
    # models are pooled under the human gene.
    phenotypes: dict = {}
    for m in ds.dataset(os.path.join(CACHE, MOUSE_PHENOTYPE), format="parquet").to_table(
            columns=["targetFromSourceId", "modelPhenotypeId", "modelPhenotypeLabel", "modelPhenotypeClasses",
                     "biologicalModels"], filter=ds.field("targetFromSourceId").isin(targets)).to_pylist():
        label, classes, models = phenotypes.setdefault((m["targetFromSourceId"], m["modelPhenotypeId"]),
                                                       (m["modelPhenotypeLabel"], set(), set()))
        classes.update(c["id"] for c in m["modelPhenotypeClasses"] or [])
        models.update(b["allelicComposition"] for b in m["biologicalModels"] or [] if b.get("allelicComposition"))
    mouse_rows = [(t, ph, label, sorted(classes), sorted(models), release)
                  for (t, ph), (label, classes, models) in phenotypes.items()]
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.ot_evidence")
        cur.execute("DELETE FROM preclin.ot_mouse_phenotype")
        execute_values(cur, """INSERT INTO preclin.ot_evidence
              (evidence_id, target_ensembl, disease_id, datasource, score, resource_score, evidence_year,
               direction_on_target, direction_on_trait, confidence, allelic_requirements, variant_consequence,
               detail, source_release_id) VALUES %s""", rows, page_size=5000)
        cur.execute("UPDATE preclin.ot_evidence SET source_year = evidence_year")
        apply_dates(cur)
        execute_values(cur, """INSERT INTO preclin.ot_mouse_phenotype
              (target_ensembl, phenotype_id, phenotype_label, class_ids, models, source_release_id) VALUES %s""",
                       mouse_rows, page_size=5000)
        conn.commit()  # one transaction: readers never see a half-loaded table
    print(f"release={RELEASE} targets={len(targets)} evidence={len(rows)} mouse phenotypes={len(mouse_rows)} "
          f"undated={sum(r[6] is None for r in rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in [("fetch", fetch), ("load", load), ("evidence", evidence), ("dates", dates)]:
        sub.add_parser(name).set_defaults(fn=fn)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
