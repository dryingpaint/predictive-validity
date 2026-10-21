"""Trial-stoppage rescore that produces audited JSONL for db/13_ingest_llm_outputs.py.

``rescore_trial_stoppage.py`` (direct calls) and
``rescore_trial_stoppage_openai_batch.py`` (Batch API) are standalone scripts:
they read DB state to determine which trials need scoring, call the OpenAI API
with a versioned prompt, and write resumable results with the exact prompts and
raw model response. The other scripts here retrieve, snapshot and export the
trial sources the rescore reads.

See README.md for schemas, cost estimates, and rerun procedure.
"""
