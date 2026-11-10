"""Store tile drafts' track records in preclin.atlas_track, atlas_track_entry and atlas_track_verdict.

    .venv/bin/python analyses/model-system-atlas/drafts/track_store.py DRAFT.json [...] [--drafted-by TEXT]

A draft is stored only if lint.py finds nothing but empty cells in it, every entry key is one the brief lists,
and its (mondo_id, mechanism_key) is a tracked row of preclin.atlas_register. A track is one model system for
one member drug by one route (model_id x drug x route); its drug is linked to the member's moiety through
lists/class_audit/class_members.csv. Storing a draft replaces its tile: every track, entry and verdict of that
tile is deleted and rewritten in one transaction. The verdict file is the draft's sibling <id>.check.json
(CHECKER_BRIEF.md); an adjudicator's decision is its adjudicated_status.
"""
import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..")))
sys.path.insert(0, HERE)

from lint import KEYS, lint  # noqa: E402
from pipeline import llm  # noqa: E402
from psycopg2.extras import Json, execute_values  # noqa: E402

QUESTIONS = ("engagement", "dose", "efficacy", "safety")
MEMBERS = os.path.join(HERE, "..", "lists", "class_audit", "class_members.csv")
TRACK = ("model_id", "model", "model_kind", "prediction_level", "model_first_use_year", "drug", "route")
# draft key -> entry column; the track's own fields live on atlas_track
ENTRY = {"year": "year", "status": "status", "src": "src", "srcLabel": "src_label", "quote": "quote",
         "source_tier": "source_tier", "comparison_stated": "comparison_stated", "retrodiction": "retrodiction",
         "patient_signal_reversed": "patient_signal_reversed", "confidence": "confidence", "population": "population",
         "population_group": "population_group", "combination_with": "combination_with",
         "imported_from": "imported_from", "subjects": "subjects", "untested_reason": "untested_reason",
         "magnitude": "magnitude", "magnitude_basis": "magnitude_basis", "source_calls_it": "source_calls_it",
         "readout_tier": "readout_tier", "endpoint_role": "endpoint_role", "outcome_tested": "outcome_tested",
         "blocked_by": "blocked_by", "margin_stated": "margin_stated", "product_in_model": "product_in_model",
         "model_filed": "model_filed", "trial_unreported": "trial_unreported", "strengthens": "strengthens",
         "effect_size": "effect_size", "class_threshold": "class_threshold", "model_src": "model_src",
         "model_src_tier": "model_src_tier", "registry_date": "registry_date", "epub_year": "epub_year",
         "print_year": "print_year", "short": "short", "note": "note", "judgement": "judgement", "reason": "reason",
         "confidence_note": "confidence_note", "patient_trials": "patient_trials"}
FALSE_IF_MISSING = ("retrodiction", "patient_signal_reversed", "trial_unreported")
assert set(ENTRY) | set(TRACK) | {"modality"} == KEYS, "every key the brief lists has a column"


def rows(d: dict) -> list[tuple]:
    """(question, modality, seq, json_index, entry) per entry; seq counts within the question and modality in year
    order (ties in list order), so a track's entries are ordered by year wherever they sit in the list."""
    out = []
    for q in QUESTIONS:
        seen: dict[str, int] = {}
        for i, e in sorted(enumerate(d["cells"][q], 1), key=lambda ie: (ie[1]["year"], ie[0])):
            mod = e.get("modality") or ""
            seen[mod] = seen.get(mod, 0) + 1
            out.append((q, mod, seen[mod], i, e))
    return out


def track_id(e: dict) -> str:
    return " / ".join(str(e[k]) for k in ("model_id", "drug", "route"))


def moieties(key: tuple[str, str]) -> dict[str, int]:
    """Member drug name -> moiety_id for one tile."""
    with open(MEMBERS) as f:
        return {r["drug"].lower(): int(r["moiety_id"]) for r in csv.DictReader(f)
                if (r["mondo_id"], r["mechanism_key"]) == key and r["drug"]}


def value(col: str, v):
    if col == "patient_trials":
        return Json(v) if v else None
    if col in ("effect_size", "class_threshold") and v is not None:
        return str(v)
    return v


def store(path: str, drafted_by: str, cur) -> int:
    issues = [i for i in lint([path])[1] if "empty cell" not in i[2]]
    if issues:
        raise SystemExit(f"{path}: not stored, lint findings:\n" + "\n".join(" | ".join(i) for i in issues))
    d = json.load(open(path))
    entries = rows(d)
    unknown = sorted({k for *_, e in entries for k in e if k not in KEYS})
    if unknown:
        raise SystemExit(f"{path}: not stored, keys the brief does not list: {unknown}")
    key = (d["mondo_id"], d["mechanism_key"])
    cur.execute("SELECT tracked FROM preclin.atlas_register WHERE mondo_id = %s AND mechanism_key = %s", key)
    hit = cur.fetchone()
    if not hit or not hit[0]:
        raise SystemExit(f"{path}: {key} is not a tracked tile of preclin.atlas_register")
    moiety = moieties(key)
    tracks = {track_id(e): e for *_, e in entries}
    missing = sorted({e["drug"] for e in tracks.values() if e["drug"] != "class" and e["drug"].lower() not in moiety})
    if missing:
        raise SystemExit(f"{path}: not stored, drugs with no moiety among the tile's members: {missing}")
    cur.execute("DELETE FROM preclin.atlas_track_entry WHERE mondo_id = %s AND mechanism_key = %s", key)
    cur.execute("DELETE FROM preclin.atlas_track WHERE mondo_id = %s AND mechanism_key = %s", key)
    execute_values(cur, f"""INSERT INTO preclin.atlas_track (mondo_id, mechanism_key, track_id, {", ".join(TRACK)},
                               moiety_id) VALUES %s""",
                   [(*key, t, *(e.get(k) for k in TRACK), None if e["drug"] == "class" else moiety[e["drug"].lower()])
                    for t, e in tracks.items()])
    cols = list(ENTRY.values())
    execute_values(cur, f"""INSERT INTO preclin.atlas_track_entry (mondo_id, mechanism_key, question, modality, seq,
                               track_id, {", ".join(cols)}, drafted_by) VALUES %s""",
                   [(*key, q, mod, seq, track_id(e),
                     *(bool(e.get(k)) if k in FALSE_IF_MISSING else value(c, e.get(k)) for k, c in ENTRY.items()),
                     drafted_by)
                    for q, mod, seq, _, e in entries])
    check = path[:-5] + ".check.json"
    n_verdicts = 0
    if os.path.exists(check):
        c = json.load(open(check))
        base = int(c.get("index_base", 1))
        by_index = {(q, i): (mod, seq) for q, mod, seq, i, _ in entries}
        unmatched = [f'{v.get("cell")}#{v.get("index")}' for v in c.get("entries", [])
                     if (v.get("cell"), int(v.get("index", -1)) - base + 1) not in by_index]
        if unmatched:
            raise SystemExit(f"{check}: not stored, verdicts name no entry of the draft: {', '.join(unmatched)}")
        verdicts = [(v, by_index[(v["cell"], int(v["index"]) - base + 1)]) for v in c.get("entries", [])]
        execute_values(cur, """INSERT INTO preclin.atlas_track_verdict (mondo_id, mechanism_key, question, modality, seq,
                                   verdict, source_resolves, quote_found, proposed_status, proposed_year, rule, note,
                                   adjudicated_status, adjudication_note, checked_by) VALUES %s""",
                       [(*key, v["cell"], mod, seq, v["verdict"], v.get("source_resolves"), v.get("quote_found"),
                         v.get("proposed_status"), v.get("proposed_year"), v.get("rule"), v.get("note"),
                         v.get("adjudicated_status"), v.get("adjudication_note"),
                         v.get("checked_by") or c.get("checked_by", "CHECKER_BRIEF"))
                        for v, (mod, seq) in verdicts])
        n_verdicts = len(verdicts)
    print(f"{os.path.basename(path)}: {len(tracks)} tracks, {len(entries)} entries, {n_verdicts} verdicts -> {key}")
    return len(entries)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("drafts", nargs="+")
    ap.add_argument("--drafted-by", default="DRAFTER_BRIEF_v3 / atlas-v3-2026-11-05")
    a = ap.parse_args()
    with llm.connect() as conn, conn.cursor() as cur:
        for p in a.drafts:
            store(p, a.drafted_by, cur)
        conn.commit()


if __name__ == "__main__":
    main()
