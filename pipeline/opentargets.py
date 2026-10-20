"""Open Targets Platform target-disease evidence -> preclin.ot_association.

    python -m pipeline.opentargets load   # release files in .cache/opentargets/<release>

Loads direct associations by data source for the targets of every molecular
entity with a development program (preclin.moiety_target), keeping each
association's yearly score series so evidence can be taken as of a date.
Sources that encode clinical outcomes or literature co-mention
(clinical_precedence, europepmc, cancer_biomarkers) are not loaded.
Disease identifiers are kept as Open Targets ids with their MONDO
cross-references in preclin.ot_disease.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import os

import pyarrow.dataset as ds
from psycopg2.extras import Json, execute_values

from pipeline import llm

RELEASE = "26.09"
CACHE = os.path.join(llm.REPO, ".cache", "opentargets", RELEASE)
SOURCE_URL = f"https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/{RELEASE}/output"
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


def load(_args) -> None:
    files = sorted(glob.glob(os.path.join(CACHE, "*", "*.parquet")))
    digest = hashlib.sha256("".join(hashlib.sha256(open(f, "rb").read()).hexdigest() for f in files).encode())
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO preclin.evidence_source_release
              (source_name, source_version, source_url, content_sha256, metadata)
            VALUES ('open_targets_platform', %s, %s, %s, %s)
            ON CONFLICT (source_name, source_version, content_sha256) DO UPDATE SET metadata = EXCLUDED.metadata
            RETURNING source_release_id""",
                    (RELEASE, SOURCE_URL, digest.hexdigest(),
                     Json({"datasets": sorted({os.path.basename(os.path.dirname(f)) for f in files}),
                           "datasources": DATASOURCES, "sha256_of": "concatenated per-file sha256"})))
        release = cur.fetchone()[0]
        cur.execute("""SELECT DISTINCT t.ensembl_id FROM preclin.moiety_target mt
                       JOIN public.targets t ON t.id = mt.target_id WHERE t.ensembl_id IS NOT NULL""")
        targets = [r[0] for r in cur.fetchall()]

    diseases = ds.dataset(os.path.join(CACHE, "disease"), format="parquet").to_table(
        columns=["id", "name", "dbXRefs", "therapeuticAreas"]).to_pylist()
    disease_rows = [(curie(d["id"]), d["name"],
                     sorted({x for x in (d["dbXRefs"] or []) if x.startswith("MONDO:")}
                            | ({curie(d["id"])} if d["id"].startswith("MONDO_") else set())),
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
        for start in range(0, len(rows), 20000):
            execute_values(cur, """INSERT INTO preclin.ot_association
                  (target_ensembl, disease_id, datasource, datatype, score, evidence_count, first_year,
                   series_years, series_scores, source_release_id) VALUES %s""",
                           rows[start:start + 20000], page_size=5000)
            conn.commit()
        conn.commit()
    print(f"release={RELEASE} targets={len(targets)} associations={len(rows)} diseases={len(disease_rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("load").set_defaults(fn=load)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
