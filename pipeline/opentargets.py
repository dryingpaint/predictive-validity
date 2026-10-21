"""Open Targets Platform target-disease evidence -> preclin.ot_association.

    python -m pipeline.opentargets fetch  # DATASETS of the release -> .cache/opentargets/<release>/<dataset>
    python -m pipeline.opentargets load   # release files in .cache/opentargets/<release>

Loads direct associations by data source for the targets of every molecular
entity with an industry-sponsored development program (preclin.moiety_target), keeping each
association's yearly score series so evidence can be taken as of a date.
Sources that encode clinical outcomes or literature co-mention
(clinical_precedence, europepmc, cancer_biomarkers) are not loaded.
Disease identifiers are kept as Open Targets ids in preclin.ot_disease, each
with the MONDO terms it is (mondo_disease); traits and measurements that are
not diseases have none.
"""
from __future__ import annotations

import argparse
import glob
from collections import defaultdict
import hashlib
import os
import re

import pyarrow.dataset as ds
import requests
from psycopg2.extras import execute_values

from pipeline import llm

RELEASE = "26.09"
CACHE = os.path.join(llm.REPO, ".cache", "opentargets", RELEASE)
SOURCE_URL = f"https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/{RELEASE}/output"
DATASETS = ("association_by_datasource_direct", "disease")  # the release datasets load reads
# Disease-concept vocabularies MONDO declares one-to-one equivalences with; OMIM entries are often
# gene-specific forms and ICD codes classification groups, so neither identifies a disease.
CONCEPT_XREFS = ("DOID", "Orphanet", "NCIT", "MESH")
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
    """Every parquet file of each of DATASETS, as listed by the release's directory index. A file
    already in the cache is kept; a download lands under a dot-prefixed name (which glob and
    pyarrow skip) and is renamed into place once complete."""
    session = requests.Session()
    for dataset in DATASETS:
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


def load(_args) -> None:
    files = sorted(f for name in DATASETS for f in glob.glob(os.path.join(CACHE, name, "*.parquet")))
    digest = hashlib.sha256("".join(llm.sha256_file(f) for f in files).encode())
    with llm.connect() as conn, conn.cursor() as cur:
        release = llm.register_release(
            cur, "open_targets_platform", RELEASE, SOURCE_URL, digest.hexdigest(),
            {"datasets": list(DATASETS),
             "datasources": DATASOURCES, "sha256_of": "concatenated per-file sha256"})
        cur.execute("""SELECT DISTINCT t.ensembl_id FROM preclin.moiety_target mt
                       JOIN public.targets t ON t.id = mt.target_id WHERE t.ensembl_id IS NOT NULL""")
        targets = [r[0] for r in cur.fetchall()]
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
        columns=["diseaseId", "targetId", "aggregationValue", "associationScore", "evidenceCount", "timeseries"],
        filter=ds.field("aggregationValue").isin(list(DATASOURCES)) & ds.field("targetId").isin(targets))
    rows = []
    for r in table.to_pylist():
        series = sorted((p["year"], p["associationScore"]) for p in r["timeseries"] or [] if p["year"])
        positive = [y for y, sc in series if sc and sc > 0]
        rows.append((r["targetId"], curie(r["diseaseId"]), r["aggregationValue"], DATASOURCES[r["aggregationValue"]],
                     r["associationScore"], r["evidenceCount"], min(positive) if positive else None,
                     [y for y, _ in series], [float(sc or 0) for _, sc in series], release))
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in [("fetch", fetch), ("load", load)]:
        sub.add_parser(name).set_defaults(fn=fn)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
