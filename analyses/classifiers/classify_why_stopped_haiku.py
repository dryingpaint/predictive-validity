"""Haiku classifier for trial termination reasons.

Reads terminated / withdrawn trials from `public.trials`, sends the
`why_stopped` free-text (plus metadata) to claude-haiku, gets back a
category + confidence + rationale. Writes JSONL matching the schema that
`db/02_ingest.py` reads at
`data/clinical_trials/why_stopped_haiku.jsonl`.

Output row schema (per `db/02_ingest.py:ingest_classifications`):
    {
      "nct_id": str,
      "cat": one of {"efficacy","safety","commercial_strategic",
                     "enrollment_fail","other","unclear"},
      "confidence": "high"|"medium"|"low",
      "rationale": str,
      "_input_tokens": int,
      "_output_tokens": int,
      "_cost_usd": float,
      "_model": str,
      "_prompt_version": str,
    }

Usage:
    python3 analyses/classifiers/classify_why_stopped_haiku.py \\
        --out data/clinical_trials/why_stopped_haiku.jsonl

    # Resume from where it stopped (default: skips NCTs already in --out)
    python3 analyses/classifiers/classify_why_stopped_haiku.py \\
        --out data/clinical_trials/why_stopped_haiku.jsonl --limit 500

Cost: ~$0.005-0.01 per trial. 5,000 trials ≈ $25-50.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import (
    append_jsonl,
    call_with_retry,
    db_conn,
    extract_json_block,
    get_client,
    load_processed_keys,
)

PROMPT_VERSION = "v1"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You classify why an industry-sponsored clinical trial was terminated. Categories are exhaustive and mutually exclusive. Sponsors euphemize — a "strategic reconsideration of the portfolio" often masks efficacy failure. Be conservative: prefer "unclear" over over-confident guessing."""

USER_TEMPLATE = """Trial: {nct_id}
Phase: {phase}
Condition(s): {conditions}
Intervention: {intervention}
Overall status: {status}
Start / completion: {start_date} / {completion_date}
Enrollment (actual / target): {enrollment}
Sponsor: {sponsor}

why_stopped free-text (verbatim from CT.gov):
"{why_stopped}"

Classify the termination reason into ONE category:

- **efficacy** — trial stopped because primary/secondary endpoint was missed OR interim analysis showed futility. Includes "insufficient effect size", "not clinically meaningful", "did not meet endpoint".
- **safety** — trial stopped because of adverse events, tolerability, or a mechanism-based tox signal. Includes DSMB-recommended stops for safety.
- **commercial_strategic** — trial stopped because of portfolio decision, company acquisition, licensing change, IP dispute, funding withdrawal, or strategic pipeline reprioritization. This bucket contains ~60% disguised efficacy failures per Cook 2014; assign confidence accordingly.
- **enrollment_fail** — trial stopped because it could not recruit enough patients (slow accrual, competing trials, protocol issues that limited eligibility).
- **other** — administrative reasons (change of investigator, protocol amendment cascaded to closure), or reasons that don't fit above.
- **unclear** — the free-text is empty, generic ("study terminated"), or does not permit confident categorization.

Return a JSON object with:
  cat: one of the labels above
  confidence: "high" | "medium" | "low"
  rationale: one short sentence explaining the classification, quoting from the why_stopped text where possible
"""


TRIALS_SQL = """
    SELECT t.nct_id,
           t.phase,
           COALESCE(t.status, '') AS status,
           COALESCE(t.why_stopped, '') AS why_stopped,
           COALESCE(t.brief_title, '') AS title,
           COALESCE(t.conditions, '') AS conditions,
           COALESCE(t.interventions, '') AS intervention,
           COALESCE(t.sponsor_name, '') AS sponsor,
           t.start_date::text AS start_date,
           t.completion_date::text AS completion_date,
           COALESCE(t.enrollment_actual::text, '') || ' / ' ||
             COALESCE(t.enrollment_target::text, '')  AS enrollment
    FROM public.trials t
    WHERE t.why_stopped IS NOT NULL
      AND t.why_stopped != ''
      AND t.status IN ('TERMINATED','WITHDRAWN','SUSPENDED')
      AND t.phase IN ('Phase 1','Phase 1/Phase 2','Phase 2','Phase 2/Phase 3','Phase 3','Phase 4')
    ORDER BY t.nct_id
    LIMIT %s
"""


def classify_one(client, trial: dict, model: str) -> dict:
    user = USER_TEMPLATE.format(**trial)
    result = call_with_retry(client, model, SYSTEM_PROMPT, user, max_tokens=512)
    parsed = extract_json_block(result.text)
    parsed["nct_id"] = trial["nct_id"]
    parsed["_model"] = model
    parsed["_prompt_version"] = PROMPT_VERSION
    parsed["_input_tokens"] = result.input_tokens
    parsed["_output_tokens"] = result.output_tokens
    parsed["_cost_usd"] = round(result.cost_usd, 6)
    return parsed


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=10000)
    ap.add_argument("--model", type=str, default=DEFAULT_MODEL)
    return ap.parse_args()


def main():
    args = parse_args()
    conn = db_conn()
    cur = conn.cursor()
    cur.execute(TRIALS_SQL, (args.limit,))
    trials = [dict(zip((
        "nct_id","phase","status","why_stopped","title","conditions",
        "intervention","sponsor","start_date","completion_date","enrollment"
    ), r)) for r in cur.fetchall()]
    conn.close()
    print(f"Candidate trials: {len(trials)}")

    already = load_processed_keys(args.out, "nct_id")
    todo = [t for t in trials if t["nct_id"] not in already]
    print(f"Already classified: {len(already)}; to do: {len(todo)}")

    client = get_client()
    total_cost = 0.0
    for i, t in enumerate(todo, start=1):
        try:
            row = classify_one(client, t, args.model)
        except Exception as e:
            print(f"  [{i}] {t['nct_id']} FAILED: {e}", file=sys.stderr, flush=True)
            continue
        append_jsonl(args.out, row)
        total_cost += row.get("_cost_usd", 0.0)
        print(
            f"  [{i}/{len(todo)}] {row['nct_id']:<12s} "
            f"cat={row.get('cat','?'):<20s} conf={row.get('confidence','?'):<7s} "
            f"cost=${row.get('_cost_usd',0):.4f} cum=${total_cost:.2f}",
            flush=True,
        )

    print(f"\nDone. Total cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
