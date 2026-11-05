"""The atlas at a glance, as data: for each drafted tile and each question, the cell's headline status at its
latest comparison, the year it earned it, the model, and the reason when it failed (issue #76).

    .venv/bin/python analyses/model-system-atlas/glance.py      # writes glance.csv; glance_nature.py draws it

Reads preclin.atlas_track_entry with its verdicts (the adjudicated status where an adjudicator decided) and
applies report_page.headline, the rule of decision 6: a cell's headline is the best latest status among its
tracks, one per model, that predicted before the patient result; untested when none did; a retrodiction never
sets it. The entry drawn is the latest on the track that set the headline. When a cell is split by modality
the worst strip is shown. A cell whose only tracks are retrodictions is drawn as "retrodiction only". A track
whose latest status is contradicted while the headline is matched is the cell's dissent. Writes glance.csv
beside this file; glance_nature.py imports load() and cells() and draws the figure. Read-only.
"""
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from report_page import final_status, headline

from report import frame

V3 = os.path.join(HERE, "drafts", "v3")
QUESTIONS = [("engagement", "Target engagement", "Does the drug hit its target?"), ("dose", "Dose", "How much drug is needed?"),
             ("efficacy", "Efficacy", "Will the disease respond?"), ("safety", "Safety", "Will people be harmed?")]
WORST = ["contra", "neg", "same", "other", "retro", "untested"]
MATCHED = {"same", "neg", "other"}
SHORT = {"metabolic dysfunction-associated steatohepatitis": "MASH", "paroxysmal nocturnal hemoglobinuria": "PNH",
         "gastroesophageal reflux disease": "GERD", "non-small cell lung carcinoma": "NSCLC",
         "hepatitis C virus infection": "hepatitis C", "HIV infectious disease": "HIV", "plasma cell myeloma": "multiple myeloma",
         "acute myeloid leukemia": "acute myeloid leukaemia"}


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    e = frame.query("""SELECT e.mondo_id, e.mechanism_key, e.question, coalesce(e.modality, '') AS modality, e.seq, e.year, e.status,
                              e.model_id, e.model, e.src_label, e.retrodiction, e.fields, v.adjudicated_status
                       FROM preclin.atlas_track_entry e
                       LEFT JOIN preclin.atlas_track_verdict v USING (mondo_id, mechanism_key, question, modality, seq)""")
    e["fields"] = e.fields.map(lambda f: f or {})
    e["final"] = [final_status({"status": st, "adjudicated_status": adj if isinstance(adj, str) else None})
                  for st, adj in zip(e.status, e.adjudicated_status)]
    e["short"] = e.fields.map(lambda f: f.get("short"))
    tiles = pd.DataFrame(json.load(open(os.path.join(V3, "tiles.json"))))
    stored = set(zip(e.mondo_id, e.mechanism_key))  # tiles.json also lists tiles not yet drafted
    tiles = tiles[[k in stored for k in zip(tiles.mondo_id, tiles.mechanism_key)]].reset_index(drop=True)
    return e, tiles


def strip(g: pd.DataFrame) -> tuple[str, dict, dict]:
    """One modality strip: its headline status, the entry that set it, and each track's latest entry."""
    ents = g.to_dict("records")
    st = headline(ents, lambda x: x["final"])
    last = {}
    for x in sorted(ents, key=lambda x: (x["year"], x["seq"])):
        if x["final"] != "drop":
            last[x["model_id"]] = x
    cand = [x for x in last.values() if x["final"] == st] or list(last.values())
    pick = max(cand, key=lambda x: (x["year"], x["seq"]))
    if st == "untested" and last and all(x["final"] == "retro" for x in last.values()):
        st = "retro"
    return st, pick, last


def headline_entry(cell: pd.DataFrame) -> tuple[str, dict, dict] | None:
    """The cell's headline across its modality strips: the worst strip, with every track behind the cell."""
    if cell.empty:
        return None
    strips = [strip(g) for _, g in cell.groupby("modality")]
    st, pick, _ = min(strips, key=lambda t: WORST.index(t[0]))
    last = {k: v for _, _, lst in strips for k, v in lst.items()}
    return st, pick, last


def cells(e: pd.DataFrame, tiles: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for t in tiles.itertuples():
        for q, _, _ in QUESTIONS:
            c = e[(e.mondo_id == t.mondo_id) & (e.mechanism_key == t.mechanism_key) & (e.question == q)]
            h = headline_entry(c)
            st, pick, last = h if h else (None, {}, {})
            contra = [x for x in last.values() if x["final"] == "contra"] if st in MATCHED else []
            dissent = max(contra, key=lambda x: (x["year"], x["seq"])) if contra else None
            rows.append({"slug": t.slug, "area": t.area, "mondo_id": t.mondo_id, "disease": t.disease, "mechanism": t.mechanism, "programs": t.class_programs,
                         "share": t.class_share, "question": q, "status": st, "year": pick.get("year"), "model": pick.get("model"),
                         "short": pick.get("short"), "tracks": len(last), "other_tracks": max(len(last) - 1, 0),
                         "derived": pick.get("fields", {}).get("derived_from"), "outcome_tested": pick.get("fields", {}).get("outcome_tested"),
                         "dissent": None if dissent is None else dissent["short"], "dissent_model": None if dissent is None else dissent["model"]})
    df = pd.DataFrame(rows)
    df["year"] = df.year.astype("Int64")
    return df


def main() -> None:
    e, tiles = load()
    df = cells(e, tiles)
    df.to_csv(os.path.join(HERE, "glance.csv"), index=False)
    print(pd.crosstab(df.question, df.status.fillna("blank")).to_string())
    print(f"dissent cells {int(df.dissent.notna().sum())}; outcome negative {int((df.outcome_tested == 'negative').sum())}; "
          f"derived dose contras {int(((df.question == 'dose') & (df.status == 'contra') & (df.derived == 'efficacy')).sum())}")


if __name__ == "__main__":
    main()
