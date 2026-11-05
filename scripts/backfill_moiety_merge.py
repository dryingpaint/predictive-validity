"""Backfill preclin.moiety_merge with the merges made before it existed, from the decisions behind them.

    .venv/bin/python -m scripts.backfill_moiety_merge --since 2026-11-05T04:30:00Z --reversed 4442013 ...

A unii merge: a moiety_unii decision of a run since --since chose a substance for an entity that no longer exists; its
survivor is the entity now holding that substance. A same_entity merge: a moiety_same_entity decision of such a run
pairs an entity that no longer exists with one that does. --reversed names the moiety_unii decisions undone by
pipeline.drugs split; each gets a reversed row after its unii row. Entities deleted without a merge (left unreferenced)
have neither and are not recorded. Prints what it would write; --write writes it.
"""
from __future__ import annotations

import argparse

from psycopg2.extras import execute_values

from pipeline import llm


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--since", required=True)
    p.add_argument("--reversed", type=int, nargs="*", default=[])
    p.add_argument("--write", action="store_true")
    args = p.parse_args()
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT moiety_id FROM preclin.moiety")
        alive = {m for m, in cur.fetchall()}
        cur.execute("SELECT DISTINCT loser_id FROM preclin.moiety_merge WHERE cause <> 'reversed'")
        recorded = {m for m, in cur.fetchall()}
        cur.execute("""SELECT d.llm_decision_id, d.subject_key::int, d.input_payload->>'name', d.parsed_output->>'unii',
                              r.completed_at
                       FROM pv_evidence.llm_decision d JOIN pv_evidence.llm_decision_run r USING (decision_run_id)
                       WHERE d.task = 'moiety_unii' AND r.started_at >= %s AND r.status = 'completed'
                         AND d.prior_decision_id IS NULL AND d.parsed_output->>'unii' IS NOT NULL
                       ORDER BY r.completed_at""", (args.since,))
        unii_rows = [r for r in cur.fetchall() if r[1] not in alive]
        cur.execute("SELECT unii, min(moiety_id) FROM preclin.moiety WHERE unii IS NOT NULL GROUP BY 1")
        holder = dict(cur.fetchall())
        rows, seen = [], set(recorded)
        for did, loser, name, u, at in unii_rows:
            if loser in seen or u not in holder:
                continue
            seen.add(loser)
            rows.append((loser, name, holder[u], "unii", did, "backfilled from the moiety_unii decision", at))
        cur.execute("""SELECT d.subject_key, d.input_payload->'entity'->>'name', d.parsed_output->'same',
                              d.input_payload->'candidates', r.completed_at
                       FROM pv_evidence.llm_decision d JOIN pv_evidence.llm_decision_run r USING (decision_run_id)
                       WHERE d.task = 'moiety_same_entity' AND r.started_at >= %s AND r.status = 'completed'
                         AND jsonb_array_length(d.parsed_output->'same') > 0
                       ORDER BY r.completed_at""", (args.since,))
        for key, name, same, cands, at in cur.fetchall():
            a = int(key.split("|")[0])
            names = {c["moiety_id"]: c["name"] for c in cands}
            for b in same:
                for lo, wi, lo_name in ((a, b, name), (b, a, names.get(b, ""))):
                    if lo not in alive and lo not in seen and wi in alive:
                        seen.add(lo)
                        rows.append((lo, lo_name, wi, "same_entity", None,
                                     "backfilled from the moiety_same_entity decision", at))
        if args.reversed:
            cur.execute("""SELECT llm_decision_id, subject_key::int, input_payload->>'name', parsed_output->>'unii'
                           FROM pv_evidence.llm_decision WHERE llm_decision_id = ANY(%s)""", (args.reversed,))
            for did, loser, name, u in cur.fetchall():
                cur.execute("SELECT moiety_id, name FROM preclin.moiety WHERE lower(name) = lower(%s)", (name,))
                now = cur.fetchall()
                rows.append((loser, name, holder.get(u, 0), "reversed", did,
                             "split by pipeline.drugs split; strings now resolve to "
                             + (f"entity {now[0][0]} ({now[0][1]})" if now else "the entity their own decision names"),
                             None))
        for r in rows:
            print(r[3], r[0], repr(r[1]), "->", r[2], r[4] or "")
        print(f"unii={sum(r[3] == 'unii' for r in rows)} same_entity={sum(r[3] == 'same_entity' for r in rows)} "
              f"reversed={sum(r[3] == 'reversed' for r in rows)}")
        if args.write:
            execute_values(cur, """INSERT INTO preclin.moiety_merge (loser_id, loser_name, survivor_id, cause,
                                     llm_decision_id, note, merged_at) VALUES %s""",
                           [(*r[:6], r[6]) for r in rows],
                           template="(%s, %s, %s, %s, %s, %s, coalesce(%s, now()))")
            conn.commit()


if __name__ == "__main__":
    main()
