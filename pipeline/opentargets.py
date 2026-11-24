"""Open Targets Platform target-disease evidence -> preclin.ot_association.

    python -m pipeline.opentargets fetch  # DATASETS of the release -> .cache/opentargets/<release>/<dataset>
    python -m pipeline.opentargets load   # release files in .cache/opentargets/<release>
    python -m pipeline.opentargets evidence  # evidence rows behind those associations, dated; mouse phenotypes
    python -m pipeline.opentargets dates     # re-date the rows from preclin.evidence_known_year, rebuild the series
    python -m pipeline.opentargets pqtl      # cis-pQTLs colocalising with disease GWAS signals -> preclin.pqtl_coloc
    python -m pipeline.opentargets adverse   # significant FAERS adverse reactions -> preclin.adverse_reaction

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

`pqtl` and `adverse` query the same release in place, in Google's public BigQuery copy (the colocalisation table
alone is 16 GB), billed to the Google Cloud project $BIGQUERY_PROJECT with application-default credentials.
`pqtl` keeps each cis-pQTL of a target's plasma protein that colocalises with a GWAS signal of a disease, with the
sign of the effect ratio (does the allele raising the protein raise risk); `adverse` keeps each adverse reaction
FAERS reports significantly often for one of our drugs, with the MONDO diseases the reaction is.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
from collections import defaultdict

import pyarrow.dataset as ds
import requests
from psycopg2.extras import Json, execute_values

from pipeline import llm

RELEASE = "26.09"
BIGQUERY = "bigquery-public-data.open_targets_platform"  # the release in BigQuery; ot_release names it
BIGQUERY_URL = "https://bigquery.googleapis.com/bigquery/v2/projects"
H4_MIN = 0.8  # coloc posterior of one shared causal variant at which a pQTL and a GWAS signal colocalise
# Open Targets gives QTL studies no publication date: each pQTL project's paper (PubMed id, year).
PQTL_PUBLISHED = {"Sun_2018": ("29875488", 2018), "UKB_PPP_EUR": ("37794186", 2023)}
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
    "reactome": ("reactionId", "reactionName", "pathways", "targetModulation"),
    "crispr": ("diseaseCellLines",),
    "crispr_screen": ("studyId", "contrast", "log2FoldChangeValue", "cellType"),
}
# The source's own identifiers of every evidence row: the disease and target as the source names them, so a row can
# be traced to the record it came from (an Orphanet or OMIM disease, a ClinVar or Gene2Phenotype entry).
SOURCE_IDS = ("diseaseFromSourceId", "diseaseFromSource", "targetFromSourceId")
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


def entity_targets(cur) -> list[str]:
    """The Ensembl ids of every entity target, the targets the loaders keep."""
    cur.execute("""SELECT DISTINCT t.ensembl_id FROM preclin.moiety_target mt
                   JOIN public.targets t ON t.id = mt.target_id WHERE t.ensembl_id IS NOT NULL""")
    return [r[0] for r in cur.fetchall()]


def release_and_targets(cur, name: str, datasets: list[str], metadata: dict) -> tuple[int, list[str]]:
    """Register the release behind `datasets` (by the sha256 of their cached files), and return it
    with the entity targets."""
    files = sorted(f for d in datasets for f in glob.glob(os.path.join(CACHE, d, "*.parquet")))
    digest = hashlib.sha256("".join(llm.sha256_file(f) for f in files).encode())
    release = llm.register_release(cur, name, RELEASE, SOURCE_URL, digest.hexdigest(),
                                   {"datasets": datasets, **metadata, "sha256_of": "concatenated per-file sha256"})
    return release, entity_targets(cur)


CAST = {"INTEGER": int, "FLOAT": float, "BOOLEAN": lambda v: v == "true"}


def bigquery(sql: str) -> list[dict]:
    """The rows of a standard-SQL query, run in $BIGQUERY_PROJECT with application-default credentials."""
    import google.auth
    from google.auth.transport.requests import AuthorizedSession
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/bigquery"])
    session = AuthorizedSession(credentials)
    base = f"{BIGQUERY_URL}/{os.environ['BIGQUERY_PROJECT']}/queries"
    r = session.post(base, json={"query": sql, "useLegacySql": False, "timeoutMs": 60000, "maxResults": 20000},
                     timeout=120)
    r.raise_for_status()
    page, rows = r.json(), []
    job = page["jobReference"]
    while True:
        if page.get("jobComplete"):
            fields = page["schema"]["fields"]
            rows += [{f["name"]: None if c["v"] is None else CAST.get(f["type"], str)(c["v"])
                      for f, c in zip(fields, row["f"])} for row in page.get("rows", [])]
            if not page.get("pageToken"):
                return rows
        r = session.get(f"{base}/{job['jobId']}", timeout=120,
                        params={"location": job["location"], "timeoutMs": 60000, "maxResults": 20000,
                                **({"pageToken": page["pageToken"]} if page.get("pageToken") else {})})
        r.raise_for_status()
        page = r.json()


def bigquery_release(cur, name: str, rows: list[dict], metadata: dict) -> int:
    """Register the rows a BigQuery load read (by the sha256 of their JSON), after checking the dataset is RELEASE."""
    (found,) = (r["release"] for r in bigquery(f"SELECT release FROM `{BIGQUERY}.ot_release`"))
    if found != RELEASE:
        raise RuntimeError(f"{BIGQUERY} holds Open Targets {found}, not {RELEASE}")
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    return llm.register_release(cur, name, RELEASE, f"bigquery://{BIGQUERY}", digest,
                                {**metadata, "sha256_of": "the rows read, as sorted-key JSON"})


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
    detail = {k: r[k] for k in (*SOURCE_IDS, *DETAIL.get(r["datasourceId"], ())) if r.get(k) not in (None, [], "")}
    if r.get("literature"):
        detail["literature"] = list(r["literature"])  # the supporting papers' PubMed ids
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
                   WHERE k.datasource = e.datasource
                     AND k.key = CASE WHEN e.datasource = 'crispr' THEN e.target_ensembl || ' ' || e.disease_id
                                      ELSE preclin.ot_evidence_key(e.datasource, e.detail) END""")
    cur.execute("UPDATE preclin.ot_association SET series_years = '{}', series_scores = '{}', first_year = NULL")
    cur.execute("""UPDATE preclin.ot_association a
                   SET series_years = s.years, series_scores = s.scores, first_year = s.years[1]
                   FROM (SELECT target_ensembl, disease_id, datasource,
                                (preclin.harmonic_series(array_agg(evidence_year ORDER BY evidence_year, score),
                                                         array_agg(score ORDER BY evidence_year, score))).*
                         FROM preclin.ot_evidence WHERE evidence_year IS NOT NULL AND score > 0
                         GROUP BY 1, 2, 3) s
                   WHERE (a.target_ensembl, a.disease_id, a.datasource) = (s.target_ensembl, s.disease_id, s.datasource)""")
    cur.execute("REFRESH MATERIALIZED VIEW preclin.ot_evidence_tiers")  # the report's summary of the dated evidence


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
        columns = [c for c in {*EVIDENCE_COLUMNS, *SOURCE_IDS, *(k for v in DETAIL.values() for k in v)}
                   if c in data.schema.names]
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


def pqtl(_args) -> None:
    """Each cis-pQTL of an entity target's plasma protein colocalising (H4 >= H4_MIN) with a GWAS signal of a disease,
    once per disease the GWAS study is mapped to; a pair of signals colocalised twice keeps its higher H4."""
    rows = bigquery(f"""
        SELECT c.leftStudyLocusId AS gwas_locus_id, c.rightStudyLocusId AS pqtl_locus_id, d.element AS disease_id,
               q.geneId AS ensembl_id, g.studyId AS gwas_study_id, g.pubmedId AS gwas_pmid,
               g.publicationDate AS gwas_date, q.studyId AS pqtl_study_id, q.projectId AS pqtl_project, c.h4,
               c.betaRatioSignAverage AS beta_ratio_sign
        FROM `{BIGQUERY}.colocalisation_coloc` c
        JOIN `{BIGQUERY}.credible_set` qc ON qc.studyLocusId = c.rightStudyLocusId AND qc.isTransQtl IS FALSE
        JOIN `{BIGQUERY}.study` q ON q.studyId = qc.studyId
        JOIN `{BIGQUERY}.credible_set` gc ON gc.studyLocusId = c.leftStudyLocusId AND gc.studyType = 'gwas'
        JOIN `{BIGQUERY}.study` g ON g.studyId = gc.studyId, UNNEST(g.diseaseIds.list) d
        WHERE c.rightStudyType = 'pqtl' AND c.h4 >= {H4_MIN} AND c.betaRatioSignAverage != 0""")
    unknown = {r["pqtl_project"] for r in rows} - set(PQTL_PUBLISHED)
    if unknown:
        raise RuntimeError(f"pQTL projects without a publication year in PQTL_PUBLISHED: {sorted(unknown)}")
    with llm.connect() as conn, conn.cursor() as cur:
        targets = set(entity_targets(cur))
        release = bigquery_release(cur, "open_targets_pqtl_coloc", rows, {"h4_min": H4_MIN,
                                                                          "pqtl_published": PQTL_PUBLISHED})
        best: dict = {}
        for r in rows:
            if r["ensembl_id"] not in targets:
                continue
            key = (r["gwas_locus_id"], r["pqtl_locus_id"], curie(r["disease_id"]))
            if key not in best or r["h4"] > best[key][10]:
                best[key] = (*key, r["ensembl_id"], r["gwas_study_id"], r["gwas_pmid"],
                             int(r["gwas_date"][:4]) if r["gwas_date"] else None, r["pqtl_study_id"],
                             r["pqtl_project"], PQTL_PUBLISHED[r["pqtl_project"]][1], r["h4"], r["beta_ratio_sign"],
                             release)
        cur.execute("DELETE FROM preclin.pqtl_coloc")
        execute_values(cur, """INSERT INTO preclin.pqtl_coloc
              (gwas_locus_id, pqtl_locus_id, disease_id, ensembl_id, gwas_study_id, gwas_pmid, gwas_year,
               pqtl_study_id, pqtl_project, pqtl_year, h4, beta_ratio_sign, source_release_id) VALUES %s""",
                       list(best.values()), page_size=5000)
        conn.commit()
    print(f"release={RELEASE} colocalisations={len(rows)} kept={len(best)} "
          f"genes={len({v[3] for v in best.values()})}")


def adverse(_args) -> None:
    """Each adverse reaction FAERS reports significantly often for one of our drugs, with the MONDO diseases it is: the
    terms whose label or synonym is its MedDRA preferred term (the drug-level reactions carry no MedDRA code)."""
    rows = bigquery(f"""SELECT chembl_id, event, count AS reports, llr, critval
                        FROM `{BIGQUERY}.openfda_significant_adverse_drug_reactions`""")
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT parent_chembl_id FROM preclin.chembl_moiety")
        ours = {r[0] for r in cur.fetchall()}
        cur.execute("""SELECT lower(n), term_id FROM preclin.ontology_term,
                              unnest(array_append(synonyms, label)) n
                       WHERE ontology = 'MONDO' AND NOT is_obsolete""")
        by_name = defaultdict(set)
        for name, term in cur.fetchall():
            by_name[name].add(term)
        release = bigquery_release(cur, "open_targets_openfda", rows, {})
        kept = [(r["chembl_id"], r["event"], r["reports"], r["llr"], r["critval"],
                 sorted(by_name.get(r["event"].lower(), ())), release) for r in rows if r["chembl_id"] in ours]
        cur.execute("DELETE FROM preclin.adverse_reaction")
        execute_values(cur, """INSERT INTO preclin.adverse_reaction
              (chembl_id, event, reports, llr, critval, mondo_ids, source_release_id) VALUES %s""",
                       kept, page_size=5000)
        conn.commit()
    print(f"release={RELEASE} reactions={len(rows)} ours={len(kept)} drugs={len({k[0] for k in kept})} "
          f"diseases={sum(bool(k[5]) for k in kept)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in [("fetch", fetch), ("load", load), ("evidence", evidence), ("dates", dates), ("pqtl", pqtl),
                     ("adverse", adverse)]:
        sub.add_parser(name).set_defaults(fn=fn)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
