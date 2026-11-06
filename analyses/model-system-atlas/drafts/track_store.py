"""Store tile drafts' track records in preclin.atlas_track_entry and their verdicts in atlas_track_verdict.

    .venv/bin/python analyses/model-system-atlas/drafts/track_store.py DRAFT.json [...] [--drafted-by TEXT]

A draft is stored only if lint.py finds nothing but empty cells in it and its (mondo_id, mechanism_key) is
a tracked row of preclin.atlas_register. Storing a draft replaces its tile: every entry and verdict of
that tile is deleted and rewritten in one transaction. The verdict file is the draft's sibling
<id>.check.json (CHECKER_BRIEF.md); an adjudicator's decision is its adjudicated_status.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..")))
sys.path.insert(0, HERE)

from lint import lint  # noqa: E402
from pipeline import llm  # noqa: E402
from psycopg2.extras import Json, execute_values  # noqa: E402

QUESTIONS = ("engagement", "dose", "efficacy", "safety")
COLUMNS = ("year", "status", "model_id", "model", "src", "srcLabel", "quote", "source_tier", "comparison_stated",
           "retrodiction", "patient_signal_reversed", "confidence")


def rows(d: dict) -> list[tuple]:
    """(question, modality, seq, json_index, entry) per entry; seq counts within the question and modality."""
    out = []
    for q in QUESTIONS:
        seen: dict[str, int] = {}
        for i, e in enumerate(d["cells"][q], 1):
            mod = e.get("modality") or ""
            seen[mod] = seen.get(mod, 0) + 1
            out.append((q, mod, seen[mod], i, e))
    return out


def store(path: str, drafted_by: str, cur) -> int:
    issues = [i for i in lint([path])[1] if "empty cell" not in i[2]]
    if issues:
        raise SystemExit(f"{path}: not stored, lint findings:\n" + "\n".join(" | ".join(i) for i in issues))
    d = json.load(open(path))
    key = (d["mondo_id"], d["mechanism_key"])
    cur.execute("SELECT tracked FROM preclin.atlas_register WHERE mondo_id = %s AND mechanism_key = %s", key)
    hit = cur.fetchone()
    if not hit or not hit[0]:
        raise SystemExit(f"{path}: {key} is not a tracked tile of preclin.atlas_register")
    entries = rows(d)
    cur.execute("DELETE FROM preclin.atlas_track_entry WHERE mondo_id = %s AND mechanism_key = %s", key)
    execute_values(cur, """INSERT INTO preclin.atlas_track_entry (mondo_id, mechanism_key, question, modality, seq,
                               year, status, model_id, model, src, src_label, quote, source_tier, comparison_stated,
                               retrodiction, patient_signal_reversed, confidence, fields, drafted_by)
                            VALUES %s""",
                   [(*key, q, mod, seq, *(e.get(c) if c not in ("retrodiction", "patient_signal_reversed")
                                          else bool(e.get(c)) for c in COLUMNS),
                     Json({k: v for k, v in e.items() if k not in COLUMNS and k != "modality"}), drafted_by)
                    for q, mod, seq, _, e in entries])
    check = path[:-5] + ".check.json"
    n_verdicts = 0
    if os.path.exists(check):
        c = json.load(open(check))
        base = int(c.get("index_base", 1))
        by_index = {(q, i): (mod, seq) for q, mod, seq, i, _ in entries}
        verdicts = [(v, by_index[(v["cell"], int(v["index"]) - base + 1)]) for v in c.get("entries", [])
                    if (v.get("cell"), int(v.get("index", -1)) - base + 1) in by_index]
        execute_values(cur, """INSERT INTO preclin.atlas_track_verdict (mondo_id, mechanism_key, question, modality, seq,
                                   verdict, source_resolves, quote_found, proposed_status, proposed_year, rule, note,
                                   adjudicated_status, adjudication_note, checked_by) VALUES %s""",
                       [(*key, v["cell"], mod, seq, v["verdict"], v.get("source_resolves"), v.get("quote_found"),
                         v.get("proposed_status"), v.get("proposed_year"), v.get("rule"), v.get("note"),
                         v.get("adjudicated_status"), v.get("adjudication_note"),
                         v.get("checked_by") or c.get("checked_by", "CHECKER_BRIEF"))
                        for v, (mod, seq) in verdicts])
        n_verdicts = len(verdicts)
    print(f"{os.path.basename(path)}: {len(entries)} entries, {n_verdicts} verdicts -> {key}")
    return len(entries)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("drafts", nargs="+")
    ap.add_argument("--drafted-by", default="DRAFTER_BRIEF")
    a = ap.parse_args()
    with llm.connect() as conn, conn.cursor() as cur:
        for p in a.drafts:
            store(p, a.drafted_by, cur)
        conn.commit()


if __name__ == "__main__":
    main()
