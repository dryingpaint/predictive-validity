"""Pull the current efficacy-attribution labels with the fields layer 1 reads, one row per labelled stop (moiety × indication × phase).
Read-only. The label merge is the report's own (pipeline.stops.labels: web-search label where the bundle
label was U).

    .venv/bin/python analyses/engagement-readouts/pull.py

Writes labels.csv. content_sha hashes exactly the fields the extractor sees, so a re-pull after the labels
are re-run changes the hash only where the rationale or verdicts changed.
"""
import hashlib
import json
import os
import sys
from datetime import date

import pandas as pd
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
load_dotenv(os.path.join(ROOT, ".env"))
from pipeline import stops  # noqa: E402
from report import frame  # noqa: E402

HASHED = ["rationale", "sources", "exposure", "engagement", "pathway", "primary_code"]


def content_sha(row) -> str:
    payload = {k: row[k] for k in HASHED}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def main():
    lab = stops.labels()
    parts = lab.key.str.split("|", expand=True)
    lab["moiety_id"], lab["mondo_id"], lab["phase"] = parts[0].astype(int), parts[1], parts[2]
    progs = frame.programs()[["program_id", "moiety_id", "mondo_id", "modality"]].drop_duplicates(["moiety_id", "mondo_id"])
    moiety = frame.query("SELECT moiety_id, name AS drug FROM preclin.moiety")
    targets = frame.query("""SELECT mt.moiety_id, string_agg(t.symbol, ';' ORDER BY t.symbol) AS targets,
                                    string_agg(DISTINCT mt.action, ';') AS actions
                             FROM preclin.moiety_target mt JOIN public.targets t ON t.id = mt.target_id
                             WHERE mt.is_primary GROUP BY mt.moiety_id""")
    disease = frame.query("""SELECT DISTINCT ON (mondo_id) mondo_id, mondo_label AS disease FROM preclin.indication
                             WHERE mondo_id IS NOT NULL AND mondo_label IS NOT NULL ORDER BY mondo_id, indication_id""")
    d = (lab.merge(progs, on=["moiety_id", "mondo_id"], how="left").merge(moiety, on="moiety_id", how="left")
            .merge(targets, on="moiety_id", how="left").merge(disease, on="mondo_id", how="left"))
    d["sources"] = d.sources.map(lambda s: ";".join(s) if isinstance(s, list) else "")
    d["content_sha"] = d.apply(content_sha, axis=1)
    d["pulled_at"] = date.today().isoformat()
    cols = ["key", "program_id", "mondo_id", "disease", "phase", "moiety_id", "drug", "modality", "targets", "actions",
            "llm_decision_id", "primary_code", "bundle_code", "searched", "exposure", "engagement", "pathway",
            "engagement_in_disease", "engagement_before_index", "confidence", "rationale", "sources",
            "content_sha", "pulled_at"]
    d = d[cols].sort_values("key")
    d.to_csv(os.path.join(HERE, "labels.csv"), index=False)
    print(f"{len(d)} labelled programs; engagement: {d.engagement.value_counts().to_dict()}")
    print(f"program missing: {int(d.program_id.isna().sum())}, targets missing: {int(d.targets.isna().sum())}, drug missing: {int(d.drug.isna().sum())}, "
          f"disease missing: {int(d.disease.isna().sum())}, searched: {int(d.searched.sum())}")
    print(f"labels.csv {os.path.getsize(os.path.join(HERE, 'labels.csv')) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
