"""Open Targets Platform target-disease evidence -> preclin.ot_association.

    python -m pipeline.opentargets fetch  # DATASETS of the release -> .cache/opentargets/<release>/<dataset>
    python -m pipeline.opentargets load   # release files in .cache/opentargets/<release>
    python -m pipeline.opentargets evidence  # evidence rows behind those associations, dated; mouse phenotypes
    python -m pipeline.opentargets dates     # re-date the rows from preclin.evidence_known_year, rebuild the series
    python -m pipeline.opentargets pqtl      # cis-pQTLs colocalising with disease GWAS signals -> preclin.pqtl_coloc
    python -m pipeline.opentargets adverse   # significant FAERS adverse reactions -> preclin.adverse_reaction
    python -m pipeline.opentargets adverse-dates  # FAERS yearly counts -> when each reaction became a signal

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
FAERS reports significantly often for one of our drugs, with the MONDO diseases the reaction is. `adverse-dates`
dates the reactions the side-effect fact can reach (a reaction that is the disease of a stored evidence entry, or one
at least 0.8 similar, of a drug on the entry's primary target): it counts their FAERS reports by the year the FDA
received them (openFDA, preclin.faers_year_count) and keeps the first year the reports received by then met
SIGNAL_METHOD's criterion (preclin.faers_signal). Counts already stored are not asked for again.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import time
from collections import defaultdict

import pandas as pd
import pyarrow.dataset as ds
import requests
from psycopg2.extras import Json, execute_values

from pipeline import llm, throttle

RELEASE = "26.09"
BIGQUERY = "bigquery-public-data.open_targets_platform"  # the release in BigQuery; ot_release names it
BIGQUERY_URL = "https://bigquery.googleapis.com/bigquery/v2/projects"
H4_MIN = 0.8  # coloc posterior of one shared causal variant at which a pQTL and a GWAS signal colocalise
OPENFDA_EVENTS = "https://api.fda.gov/drug/event.json"
OPENFDA_PER_SECOND = 3.5  # openFDA without a key allows 240 requests a minute (and 1,000 a day)
# A reaction becomes a signal once the reports received by the end of a year give at least SIGNAL_REPORTS reports
# naming the drug and the reaction, a proportional reporting ratio of at least SIGNAL_PRR and a chi-squared (Yates) of
# at least SIGNAL_CHI2 (Evans, Waller and Davis 2001).
SIGNAL_METHOD, SIGNAL_REPORTS, SIGNAL_PRR, SIGNAL_CHI2 = "faers_signal@v1", 3, 2.0, 4.0
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


def signal(pair: dict, drug: dict, reaction: dict, total: dict, through: int) -> tuple:
    """(signal_year, reports, prr, chi2) of a drug and reaction from yearly report counts ({year: reports}): the first
    year whose cumulative counts meet the criterion, with its statistics; with no such year by `through`, a null year
    and the statistics at `through`."""
    a = b = c = n = 0
    stats = (None, 0, None, None)
    for year in range(min((*pair, *drug, *reaction, *total), default=through), through + 1):
        a, n = a + pair.get(year, 0), n + total.get(year, 0)
        b, c = b + drug.get(year, 0) - pair.get(year, 0), c + reaction.get(year, 0) - pair.get(year, 0)
        d = n - a - b - c
        prr = (a / (a + b)) / (c / (c + d)) if a and c and c + d else None
        chi2 = (n * max(abs(a * d - b * c) - n / 2, 0) ** 2 / ((a + b) * (c + d) * (a + c) * (b + d))
                if a and (a + b) * (c + d) * (a + c) * (b + d) else None)
        stats = (None, a, prr, chi2)
        if a >= SIGNAL_REPORTS and prr is not None and prr >= SIGNAL_PRR and chi2 is not None and chi2 >= SIGNAL_CHI2:
            return year, a, prr, chi2
    return stats


def faers_years(search: str | None) -> dict[int, int]:
    """FAERS reports by the year the FDA received them, for an openFDA drug/event search (None: every report)."""
    params = {"count": "receivedate", **({"search": search} if search else {})}
    for attempt in range(6):
        throttle.wait("openfda", OPENFDA_PER_SECOND)
        r = requests.get(OPENFDA_EVENTS, params=params, timeout=120)
        if r.status_code == 404:  # openFDA's answer to a search with no reports
            return {}
        if r.status_code in (429, 500, 502, 503) and attempt < 5:
            print(f"openFDA {r.status_code}; waiting {30 * (attempt + 1)} s", flush=True)
            time.sleep(30 * (attempt + 1))
            continue
        r.raise_for_status()
        out: dict[int, int] = defaultdict(int)
        for row in r.json()["results"]:
            out[int(row["time"][:4])] += row["count"]
        return dict(out)
    raise RuntimeError("openFDA kept failing")


def adverse_pairs() -> set[tuple[int, str]]:
    """The (drug, reaction) pairs the side-effect fact can reach (report.section3.Evidence.side_effect): a significant
    reaction of an entity on a stored evidence entry's primary target, approved before the entry and developed for no
    disease related to the entry's (Lin RELATED), that is the entry's disease or one at least CLOSE similar."""
    from report import frame
    from report.section3 import CLOSE, RELATED, approval_dates, neighbourhood
    progs = frame.programs()
    p = progs.set_index("program_id")
    first = pd.concat([pd.to_datetime(p.moiety_first_fda_approval), approval_dates(p, p.approved.eq("yes"))],
                      axis=1).min(axis=1)
    approved = first.groupby(p.moiety_id).min().dropna().to_dict()
    developed = progs.dropna(subset=["mondo_id"]).groupby("moiety_id").mondo_id.apply(frozenset).to_dict()
    reach = frame.query("""
        SELECT DISTINCT e.moiety_id, e.mondo_id, e.entry_date, ot.moiety_id AS other
        FROM preclin.evidence_entry e
        JOIN preclin.moiety_target mt ON mt.moiety_id = e.moiety_id AND mt.is_primary
        JOIN preclin.moiety_target ot ON ot.target_id = mt.target_id AND ot.is_primary AND ot.moiety_id <> e.moiety_id
        JOIN preclin.moiety o ON o.moiety_id = ot.moiety_id AND o.target_kind = 'human_protein'
        WHERE e.has_target_disease""")
    reactions = defaultdict(list)
    ae = frame.query("""SELECT DISTINCT cm.moiety_id, a.event, m AS mondo_id FROM preclin.adverse_reaction a
                        JOIN preclin.chembl_moiety cm ON cm.parent_chembl_id = a.chembl_id, unnest(a.mondo_ids) m""")
    for moiety, event, mondo in ae.itertuples(index=False):
        reactions[moiety].append((event, mondo))
    nb = neighbourhood()
    return {(other, event) for _, disease, entry, other in reach.itertuples(index=False)
            if approved.get(other, pd.Timestamp.max) < pd.Timestamp(entry)
            and not developed.get(other, frozenset()) & nb.terms(disease, RELATED)
            for event, mondo in reactions.get(other, ()) if mondo in nb.terms(disease, CLOSE)}


def adverse_dates(_args) -> None:
    """Count the FAERS reports of every pair the side-effect fact can reach, its drug, its reaction and all reports, by
    year received, for counts not stored yet; then date every such pair by SIGNAL_METHOD."""
    through = datetime.date.today().year - 1  # the last whole year received
    pairs = adverse_pairs()
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT m.moiety_id, m.name, array_remove(array_append(array_agg(p.unii), m.unii), NULL)
                       FROM preclin.moiety m LEFT JOIN preclin.unii_parent p ON p.parent_unii = m.unii
                       WHERE m.moiety_id = ANY(%s) GROUP BY m.moiety_id""", ([m for m, _ in pairs],))
        names = {m: (name, sorted(set(uniis))) for m, name, uniis in cur.fetchall()}
        cur.execute("SELECT DISTINCT query_kind, subject_key FROM preclin.faers_year_count")
        have = set(cur.fetchall())
        conn.commit()  # no transaction stays open through the openFDA calls

    def drug_search(m: int) -> str:
        name, uniis = names[m]
        return ("patient.drug.openfda.unii:(" + " ".join(f'"{u}"' for u in uniis) + ")" if uniis
                else f'patient.drug.openfda.generic_name.exact:"{name.upper()}"')

    def reaction_search(event: str) -> str:
        return f'patient.reaction.reactionmeddrapt.exact:"{event.upper()}"'
    queries = [("all", "", None, None, None)]
    queries += [("drug", str(m), m, None, drug_search(m)) for m in sorted({m for m, _ in pairs})]
    queries += [("reaction", e, None, e, reaction_search(e)) for e in sorted({e for _, e in pairs})]
    queries += [("pair", f"{m} {e}", m, e, f"{drug_search(m)} AND {reaction_search(e)}") for m, e in sorted(pairs)]
    todo = [q for q in queries if q[:2] not in have]
    print(f"pairs={len(pairs)} queries={len(queries)} to ask={len(todo)}", flush=True)
    with llm.connect() as conn, conn.cursor() as cur:
        release = llm.register_release(cur, "openfda_drug_event", datetime.date.today().isoformat(), OPENFDA_EVENTS,
                                       hashlib.sha256(json.dumps(sorted(q[:2] for q in todo)).encode()).hexdigest(),
                                       {"count": "receivedate", "queries": len(todo)})
        conn.commit()
    for i, (kind, key, moiety, event, search) in enumerate(todo):
        years = faers_years(search)
        # A query is stored whole, in its own transaction, so an interrupted run resumes after the last one stored;
        # one with no reports keeps a single row of year 0 and 0 reports marking it asked.
        rows = [(kind, key, moiety, event, y, n, release) for y, n in sorted(years.items())] or \
               [(kind, key, moiety, event, 0, 0, release)]
        with llm.connect() as conn, conn.cursor() as cur:
            execute_values(cur, """INSERT INTO preclin.faers_year_count
                  (query_kind, subject_key, moiety_id, event, year, reports, source_release_id) VALUES %s""", rows)
            conn.commit()
        if (i + 1) % 50 == 0:
            print(f"{i + 1}/{len(todo)}", flush=True)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT query_kind, subject_key, year, reports FROM preclin.faers_year_count
                       WHERE year > 0""")
        counts: dict = defaultdict(dict)
        for kind, key, year, n in cur.fetchall():
            counts[(kind, key)][year] = n
        method = llm.record_method(
            cur, SIGNAL_METHOD, "FAERS signal year",
            "First year whose FAERS reports received by its end (openFDA receivedate) give a drug and reaction at "
            "least the minimum reports, proportional reporting ratio and Yates chi-squared (Evans 2001)",
            ["preclin.faers_year_count"], {"min_reports": SIGNAL_REPORTS, "min_prr": SIGNAL_PRR,
                                           "min_chi2": SIGNAL_CHI2, "through": through})
        rows = []
        for m, e in sorted(pairs):
            year, reports, prr, chi2 = signal(counts[("pair", f"{m} {e}")], counts[("drug", str(m))],
                                              counts[("reaction", e)], counts[("all", "")], through)
            rows.append((m, e, year, through, reports, prr, chi2, method))
        cur.execute("DELETE FROM preclin.faers_signal")
        execute_values(cur, """INSERT INTO preclin.faers_signal
              (moiety_id, event, signal_year, dated_through, reports, prr, chi2, method_id) VALUES %s""", rows)
        conn.commit()
    dated = [r for r in rows if r[2] is not None]
    print(f"dated {len(rows)} pairs through {through}: {len(dated)} signals, first years "
          f"{min((r[2] for r in dated), default=None)}-{max((r[2] for r in dated), default=None)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in [("fetch", fetch), ("load", load), ("evidence", evidence), ("dates", dates), ("pqtl", pqtl),
                     ("adverse", adverse), ("adverse-dates", adverse_dates)]:
        sub.add_parser(name).set_defaults(fn=fn)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
