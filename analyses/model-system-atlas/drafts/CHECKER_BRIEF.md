# Checker brief — model-system atlas context (issue dryingpaint/predictive-validity#76, step 3)

You are checking ONE drafted entry. Read `analyses/model-system-atlas/drafts/DRAFTER_BRIEF.md` first for the
definitions and evidence rules; the draft was written to them. Then read the draft file named below.

For EVERY entry in every cell:
1. Re-open the source (PubMed tools `mcp__plugin_bio-research_pubmed__get_article_metadata` /
   `search_articles`, WebFetch for labels and registry pages). Confirm the DOI/URL resolves to the paper
   or document the entry names.
2. Confirm the `quote` appears in that source verbatim or near-verbatim (abstract-level is acceptable;
   say when you could only see the abstract).
3. Confirm the quote actually supports the `status` under the brief's rules. Common failures:
   `same`/`contra` with no published model-vs-patient comparison (should be `untested`); approval status
   or later knowledge used as evidence; a review cited where a primary source exists; year is the
   trial year rather than the publication year of the comparison.
4. Confirm `model` is the model the drug class relied on for that question, not a better one in principle.

Do not rewrite the draft. Write a verdict file at the path given below, shape:
{
 "draft": "<path>",
 "entries": [
   {"cell": "efficacy", "index": 1, "verdict": "confirmed|corrected|unverified",
    "source_resolves": true, "quote_found": "verbatim|near|not_found|abstract_only",
    "status_supported": true, "proposed_status": "<only if corrected>", "proposed_year": <only if corrected>,
    "note": "<≤40 words: what you checked and what you'd change>"}
 ],
 "missing": ["<cells or comparisons the draft should have found, with a source if you have one>"],
 "overall": "accept|accept_with_corrections|reject",
 "rule_questions": ["<any case where the brief's rules did not decide the status>"]
}
Budget ≤25 tool calls. Then reply with: the verdict path, a one-line verdict per cell, and the rule questions.
