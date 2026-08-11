"""Sonnet re-classification of the trials Haiku labeled 'commercial_strategic'
or 'unclear' with medium/low confidence.

This is the disagreement / verification pass. Cook 2014 estimates ~60% of
"commercial/strategic" bucket contains disguised efficacy failures. Sending
these back through a stronger model with additional web / PubMed context
(when we have it) resolves a large fraction.

Writes JSONL matching the schema `db/02_ingest.py` reads at
`data/clinical_trials/why_stopped_sonnet.jsonl`.

Usage:
    python3 analyses/classifiers/classify_why_stopped_sonnet.py \\
        --haiku data/clinical_trials/why_stopped_haiku.jsonl \\
        --out   data/clinical_trials/why_stopped_sonnet.jsonl

    # Only re-verify low-confidence commercial_strategic + unclear
    python3 analyses/classifiers/classify_why_stopped_sonnet.py \\
        --haiku data/clinical_trials/why_stopped_haiku.jsonl \\
        --out   data/clinical_trials/why_stopped_sonnet.jsonl \\
        --targets commercial_strategic,unclear \\
        --confidence-below high

Cost: ~$0.02-0.04 per trial. 1,000 trials ≈ $30.
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
    read_jsonl,
)

PROMPT_VERSION = "v1"
DEFAULT_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are re-verifying a first-pass classification of a clinical trial's termination reason. Prior classifier used a weaker model. Your job: independently classify from the primary evidence (why_stopped text + metadata) and flag any disagreement with the prior labels. Sponsors euphemize — assume "portfolio decision" often masks efficacy failure unless the evidence positively excludes efficacy."""

USER_TEMPLATE = """Trial: {nct_id}
Phase: {phase}
Condition(s): {conditions}
Intervention: {intervention}
Sponsor: {sponsor}

why_stopped text (verbatim):
"{why_stopped}"

Prior Haiku classification: cat={prior_cat}, confidence={prior_confidence}
Prior rationale: {prior_rationale}

Classify independently into ONE of:
- efficacy
- safety
- commercial_strategic
- enrollment_fail
- other
- unclear

For "commercial_strategic": specifically consider whether the language ("strategic reconsideration", "portfolio decision", "sponsor decision") is the sponsor's euphemism for a hidden efficacy fail. If the evidence supports a disguised efficacy fail, use "efficacy" and note the reasoning.

Return JSON:
  cat: label
  confidence: "high" | "medium" | "low"
  rationale: 1-2 sentences
  agrees_with_haiku: bool
  reclassification_reason: string (empty if you agree)
"""


def build_context(row: dict, haiku_row: dict) -> dict:
    return {
        "nct_id": row["nct_id"],
        "phase": row.get("phase") or "",
        "conditions": row.get("conditions") or "",
        "intervention": row.get("intervention") or "",
        "sponsor": row.get("sponsor") or "",
        "why_stopped": row.get("why_stopped") or "",
        "prior_cat": haiku_row.get("cat", "unknown"),
        "prior_confidence": haiku_row.get("confidence", "unknown"),
        "prior_rationale": haiku_row.get("rationale", ""),
    }


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--haiku", type=Path, required=True,
                    help="Path to Haiku output JSONL")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--targets", type=str, default="commercial_strategic,unclear",
        help="Comma-separated cats to re-verify (default: commercial_strategic,unclear)",
    )
    ap.add_argument("--confidence-below", type=str, default="high",
                    choices=["high", "medium", "low"],
                    help="Only re-verify when Haiku confidence is below this")
    ap.add_argument("--limit", type=int, default=10000)
    ap.add_argument("--model", type=str, default=DEFAULT_MODEL)
    return ap.parse_args()


def confidence_rank(c: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(c, 0)


def fetch_trial_meta(cur, nct_ids: list[str]) -> dict:
    """Return {nct_id: trial_row_dict}."""
    if not nct_ids:
        return {}
    cur.execute(
        """
        SELECT nct_id, phase, COALESCE(why_stopped,'') AS why_stopped,
               COALESCE(conditions,'') AS conditions,
               COALESCE(interventions,'') AS intervention,
               COALESCE(sponsor_name,'') AS sponsor
        FROM public.trials
        WHERE nct_id = ANY(%s)
        """,
        (list(nct_ids),),
    )
    out = {}
    for r in cur.fetchall():
        out[r[0]] = dict(zip(("nct_id","phase","why_stopped","conditions","intervention","sponsor"), r))
    return out


def main():
    args = parse_args()

    targets_set = {t.strip() for t in args.targets.split(",") if t.strip()}
    max_conf = confidence_rank(args.confidence_below)

    to_verify = []
    for row in read_jsonl(args.haiku):
        if row.get("cat") not in targets_set:
            continue
        if confidence_rank(row.get("confidence", "low")) >= max_conf:
            continue
        to_verify.append(row)
    to_verify = to_verify[: args.limit]
    print(f"Trials to re-verify with Sonnet: {len(to_verify)}")

    conn = db_conn()
    cur = conn.cursor()
    trial_meta = fetch_trial_meta(cur, [r["nct_id"] for r in to_verify])
    conn.close()

    already = load_processed_keys(args.out, "nct_id")
    todo = [r for r in to_verify if r["nct_id"] not in already and r["nct_id"] in trial_meta]
    print(f"Already Sonnet-classified: {len(already)}; to do: {len(todo)}")

    client = get_client()
    total_cost = 0.0
    for i, haiku_row in enumerate(todo, start=1):
        nct = haiku_row["nct_id"]
        ctx = build_context(trial_meta[nct], haiku_row)
        user = USER_TEMPLATE.format(**ctx)
        try:
            result = call_with_retry(client, args.model, SYSTEM_PROMPT, user, max_tokens=512)
            parsed = extract_json_block(result.text)
        except Exception as e:
            print(f"  [{i}] {nct} FAILED: {e}", file=sys.stderr, flush=True)
            continue
        parsed["nct_id"] = nct
        parsed["_model"] = args.model
        parsed["_prompt_version"] = PROMPT_VERSION
        parsed["_input_tokens"] = result.input_tokens
        parsed["_output_tokens"] = result.output_tokens
        parsed["_cost_share"] = round(result.cost_usd, 6)
        append_jsonl(args.out, parsed)
        total_cost += result.cost_usd
        agrees = "agree" if parsed.get("agrees_with_haiku") else "DISAGREE"
        print(
            f"  [{i}/{len(todo)}] {nct:<12s} haiku={haiku_row['cat']:<20s} "
            f"→ sonnet={parsed.get('cat','?'):<20s} conf={parsed.get('confidence','?'):<6s} "
            f"{agrees}  cost=${result.cost_usd:.4f}  cum=${total_cost:.2f}",
            flush=True,
        )

    print(f"\nDone. Total cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
