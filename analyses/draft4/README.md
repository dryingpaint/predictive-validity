# Draft 4: research prompts and one-off numbers

Draft 4 of the report ("Modeling Clinical Predictive Validity: Draft 4, revised (with figures)", Google Doc, 2026-11-18)
added literature research and a few numbers computed outside `python -m report`. This folder holds what produced them.

- `research_prompts.md`: the exact prompts given to the three research agents (Claude Code subagents with web search)
  for the case studies, the Discussion literature and the history of drug development. Their findings, with every
  source, are in Draft 4's text and its "Sources for the case studies and discussion" appendix. Facts the agents could
  not verify were left out or flagged there.
- `draft4_numbers.py`: reproduces each number Draft 4 or the issues quote that the report build does not produce.

The related-success reading used by `report/engaged_modes.py` is documented in `report/audits/related_success_modes.md`.
