# Checker brief v3 — model-system atlas context (issue dryingpaint/predictive-validity#76)

You are checking ONE drafted entry written to `DRAFTER_BRIEF_v3.md`. Read that brief first; its rules are
the ones in `RULES_V3_PROPOSAL.md`, all sixteen decided. Then run
`.venv/bin/python analyses/model-system-atlas/drafts/lint.py <draft>`: a draft with lint findings goes back
to the drafter unchecked, with the findings as the verdict.

For EVERY entry in every cell:
1. Re-open the source, from the source bundle if one is given. Confirm the DOI/URL resolves to the
   document the entry names and that `source_tier` is that document's tier. For a paired or tier 4–5
   entry, open `model_src` as well.
2. Confirm the `quote` appears in that source verbatim or near-verbatim (say when you saw only the
   abstract).
3. Confirm the quote supports the `status` under the v3 rules. The failures that flipped most cells in
   the v2 run, and the v3 rules most likely to be misapplied:
   - `same`/`contra` from a pairing whose trial source attributes the result to conditions the model never
     tested (should be `untested`);
   - efficacy scored on a secondary endpoint without `endpoint_role: poc_gate`;
   - a retrodiction scored `same` (should be `retro`), or a prospective model marked `retrodiction`;
   - a `contra` → matched move whose `model_change` is really the same system renamed (same `model_id`
     in substance), or whose `patient_signal_reversed` source does not show attenuation to background;
   - `neg` whose `effect_size` is the sponsor's reading rather than the model's number, or whose
     `class_threshold` is not a bar the class's own successful drugs cleared;
   - a dose ceiling (`margin_stated`) where no model source stated the margin before the trial;
   - a member drug outside the class you were given (another target, a non-selective drug, another
     modality).
4. Confirm `model` is the system the class relied on for that question, not a better one in principle.
5. Search for what the draft missed: in particular a press release, SEC filing or EMA/AdCom document
   reporting a failure the draft does not show.

Do not rewrite the draft. Write a verdict file at the path given below:
{
 "draft": "<path>", "index_base": 1,
 "entries": [
   {"cell": "efficacy", "index": 1, "verdict": "confirmed|corrected|unverified",
    "source_resolves": true, "quote_found": "verbatim|near|not_found|abstract_only",
    "status_supported": true, "proposed_status": "<only if corrected>", "proposed_year": <only if corrected>,
    "rule": "<the decision number the correction rests on>",
    "note": "<≤40 words: what you checked and what you'd change>"}
 ],
 "missing": ["<comparisons the draft should have found, with a source>"],
 "overall": "accept|accept_with_corrections|reject",
 "rule_questions": ["<any case the v3 rules did not decide>"]
}
Number entries from 1. Budget ≤25 tool calls. Then reply with: the verdict path, a one-line verdict per cell,
and the rule questions.

## Adjudication

A corrected entry is not applied by either side. Every `corrected` verdict, with the drafter's status, the
checker's proposal and the `rule` it cites, goes to the adjudication queue (`matrix_entries.csv` rows where
`status_draft` ≠ `status_checked`). A third agent, given both and the cited rule, decides; a case it cannot
decide from the rules becomes a rule question, not a judgement call. Agreement between drafter and checker
on the latest cell status, before adjudication, is the κ the re-draft reports.
