"""The atlas at a glance, as data: for each tile and each question, the cell's headline status at its
latest comparison, the year it earned it, the model, and the reason when it failed (issue #76).

    .venv/bin/python analyses/model-system-atlas/glance.py      # writes glance.csv; glance_nature.py draws it

Reads preclin.atlas_track_entry with its verdicts (the adjudicated status where an adjudicator decided, the
checker's corrected year where the status stands) and applies headline(): a cell's headline is the best
latest status among its tracks, one per model, that predicted before the patient result; untested when none did; a
retrodiction never sets it. The entry drawn is the latest prospective entry on the track that set the headline.
When a cell is split by modality the worst strip is shown. A cell whose only tracks are retrodictions is drawn as
"retrodiction only". A track whose latest status is contradicted while the headline is matched is the cell's
dissent. A never-compared cell carries the untested_reason of the entry drawn. Writes glance.csv beside this file; glance_nature.py imports load() and cells() and draws the figure.
Read-only.
"""
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))

from report import frame

DRAFTS = os.path.join(HERE, "drafts")
QUESTIONS = [("engagement", "Target engagement", "Does the drug hit its target?"), ("dose", "Dose", "How much drug is needed?"),
             ("efficacy", "Efficacy", "Will the disease respond?"), ("safety", "Safety", "Will people be harmed?")]
WORST = ["contra", "neg", "same", "other", "retro", "untested"]
MATCHED = {"same", "neg", "other"}
SHORT = {"metabolic dysfunction-associated steatohepatitis": "MASH", "paroxysmal nocturnal hemoglobinuria": "PNH",
         "gastroesophageal reflux disease": "GERD", "non-small cell lung carcinoma": "NSCLC",
         "hepatitis C virus infection": "hepatitis C", "HIV infectious disease": "HIV", "plasma cell myeloma": "multiple myeloma",
         "acute myeloid leukemia": "acute myeloid leukaemia", "chronic obstructive pulmonary disease": "COPD"}
HEADLINE = ["same", "neg", "other", "contra"]  # statuses a prospective track can set the headline with, best first
# why a never-compared entry was never compared (drafts/DRAFTER_BRIEF.md rule 5), as the figure prints it
UNTESTED_REASON = {"no_prediction": "No checkable prediction", "not_measured": "Not measured in patients",
                   "unpublished": "Model data unpublished", "unsettled": "Patient result unclear"}


def final_status(r) -> str:
    """The adjudicated status when an adjudicator decided, else the drafter's."""
    return r["adjudicated_status"] if r.get("adjudicated_status") else r["status"]


def final_year(r) -> int:
    """The checker's corrected year when the entry's final status is the drafter's, else the drafter's year. It is
    the year shown; a track's order stays the drafted one (seq), which lint.py checked."""
    if r.get("verdict") == "corrected" and r.get("proposed_year") and final_status(r) == r["status"]:
        return int(r["proposed_year"])
    return int(r["year"])


def headline(entries: list[dict]) -> str | None:
    """A cell's headline: the best latest status among its tracks (one per model_id) that predicted before the
    patient result; untested when none did. A track's latest entry is its last in seq order. A retrodiction is shown
    on its track but never sets the headline, nor hides the prospective entries before it on the same track."""
    kept = [e for e in entries if e["final"] != "drop"]
    if not kept:
        return None
    last = {}
    for e in sorted(kept, key=lambda e: e["seq"]):
        if e["final"] != "retro" and not e["retrodiction"]:
            last[e["model_id"]] = e["final"]
    tested = [s for s in last.values() if s in HEADLINE]
    return min(tested, key=HEADLINE.index) if tested else "untested"


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    e = frame.query("""SELECT e.mondo_id, e.mechanism_key, e.question, coalesce(e.modality, '') AS modality, e.seq, e.year, e.status,
                              e.model_id, e.model, e.src_label, e.retrodiction, e.fields, v.verdict, v.proposed_year,
                              v.adjudicated_status
                       FROM preclin.atlas_track_entry e
                       LEFT JOIN preclin.atlas_track_verdict v USING (mondo_id, mechanism_key, question, modality, seq)""")
    e["fields"] = e.fields.map(lambda f: f or {})
    verdicts = [{"status": st, "year": y, "verdict": v if isinstance(v, str) else None,
                 "proposed_year": None if pd.isna(py) else int(py),
                 "adjudicated_status": adj if isinstance(adj, str) else None}
                for st, y, v, py, adj in zip(e.status, e.year, e.verdict, e.proposed_year, e.adjudicated_status)]
    e["final"] = [final_status(r) for r in verdicts]
    e["year"] = [final_year(r) for r in verdicts]
    e["short"] = e.fields.map(lambda f: f.get("short"))
    tiles = pd.DataFrame(json.load(open(os.path.join(DRAFTS, "tiles.json"))))
    stored = set(zip(e.mondo_id, e.mechanism_key))  # a tile is drawn once its track record is stored
    tiles = tiles[[k in stored for k in zip(tiles.mondo_id, tiles.mechanism_key)]].reset_index(drop=True)
    return e, tiles


def strip(g: pd.DataFrame) -> tuple[str, dict, dict] | None:
    """One modality strip: its headline status, the entry that set it, and each track's latest entry, keyed by
    (modality, model_id); None when every entry was dropped. A track's latest entry is its last in seq order; the
    entry drawn is the latest prospective one on a track that set the headline."""
    ents = sorted((x for x in g.to_dict("records") if x["final"] != "drop"), key=lambda x: x["seq"])
    if not ents:
        return None
    st = headline(ents)
    latest = {(x["modality"], x["model_id"]): x for x in ents}
    if st == "untested" and all(x["final"] == "retro" for x in latest.values()):
        return "retro", max(latest.values(), key=lambda x: (x["year"], x["seq"])), latest
    prospective = {(x["modality"], x["model_id"]): x for x in ents if x["final"] != "retro" and not x["retrodiction"]}
    pick = max([x for x in prospective.values() if x["final"] == st] or list(prospective.values()) or ents,
               key=lambda x: (x["year"], x["seq"]))
    return st, pick, latest


def headline_entry(cell: pd.DataFrame) -> tuple[str, dict, dict] | None:
    """The cell's headline across its modality strips: the worst strip, with every track behind the cell."""
    strips = [s for _, g in cell.groupby("modality") if (s := strip(g))]
    if not strips:
        return None
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
                         "outcome_tested": pick.get("fields", {}).get("outcome_tested"),
                         "untested_reason": pick.get("fields", {}).get("untested_reason") if st == "untested" else None,
                         "dissent": None if dissent is None else dissent["short"], "dissent_model": None if dissent is None else dissent["model"]})
    df = pd.DataFrame(rows)
    df["year"] = df.year.astype("Int64")
    return df


def main() -> None:
    e, tiles = load()
    df = cells(e, tiles)
    df.to_csv(os.path.join(HERE, "glance.csv"), index=False)
    print(pd.crosstab(df.question, df.status.fillna("blank")).to_string())
    missing = df[(df.status == "untested") & df.untested_reason.isna()]
    if len(missing):
        print("never-compared cells without untested_reason:", *(missing.slug + " " + missing.question), sep="\n  ")
    print(f"dissent cells {int(df.dissent.notna().sum())}; outcome negative {int((df.outcome_tested == 'negative').sum())}")


if __name__ == "__main__":
    main()
