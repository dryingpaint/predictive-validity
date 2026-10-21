# Classifier scripts

The LLM classifiers that produce resumable JSONL / CSV outputs. New audited
JSONL runs are loaded incrementally with `db/13_ingest_llm_outputs.py`;
`db/02_ingest.py` remains the legacy big-bang bootstrap loader.

**Every paid workflow here:**
- reads Neon DB state to pick which subjects need scoring
- calls Anthropic or OpenAI with a versioned prompt
- writes a resumable JSONL / CSV output
- records the exact system/user prompts, raw response, model parameters,
  provider request id, prompt version, token counts, and USD cost per row

## Setup

```bash
pip install anthropic openai psycopg2-binary
export ANTHROPIC_API_KEY=sk-ant-...
# The trial-stoppage rescore calls OpenAI:
export OPENAI_API_KEY=sk-...
export DATABASE_URL=postgres://...
```

## Classifier workflows

| Script | Purpose | Target file | Default model | Cost per 1k items |
|---|---|---|---|---|
| `rescore_trial_stoppage.py` | Multi-axis trial stoppage adjudication from registry results, publications, and curated external evidence | `data/clinical_trials/stoppage_rescore_*.jsonl` | GPT-5.6 Terra | depends on dossier size |

## Trial-stoppage rescore

The stoppage rescore does not replace `why_stopped`. It writes a separate
`trial_stoppage_rescore` task so old and new labels can be compared before any
analytical cutover. Its result has independent fields for study execution,
primary-endpoint assessment, scientific outcome, termination driver, and
program outcome. This prevents a phrase such as "business decision" from
silently becoming an efficacy failure—or hiding a successful efficacy readout.

Refresh canonical registry records and their linked PubMed abstracts first.
Exact-NCT PubMed discovery is optional and requires `NCBI_EMAIL`:

```bash
.venv/bin/dotenv run -- .venv/bin/python db/11_ingest_trial_sources.py \
  --scope classified --limit 100 --search-pubmed-by-nct
```

For a frozen subset, pass one NCT per line with `--nct-id-file`. An exact-NCT
search hit is only a discovery candidate: it can still be a protocol, review
table, sibling trial, or unrelated result. Preserve raw results and inspect the
source text before linking it to a trial.

Curated sponsor, SEC, regulatory, non-US registry, and scholarly excerpts are
loaded with the dry-run-by-default external-source importer:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  db/ingest_trial_external_sources.py curated_sources.jsonl

.venv/bin/dotenv run -- .venv/bin/python \
  db/ingest_trial_external_sources.py --commit curated_sources.jsonl
```

Every row declares its relationship to the target (`exact_nct`,
`unique_protocol`, `probable_composite`, `parent_trial`, `extension_trial`,
`sibling_indication`, or `program_only`), whether it can support each
classification axis, a controlled list of supported claim types, and whether
the retained text is an exact excerpt, source text, or a verified paraphrase.
Program-supporting rows also declare `target_indication`, `protocol_family`, or
`asset_global` scope. Parent, sibling, and program-only evidence cannot be
marked as the target trial's own scientific outcome.

Prepare and validate a free single-trial dossier:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  analyses/classifiers/rescore_trial_stoppage.py prepare \
  --nct-id NCT02470585 \
  --out data/clinical_trials/stoppage_rescore_pilot.dossiers.jsonl

.venv/bin/python analyses/classifiers/rescore_trial_stoppage.py validate \
  --dossiers data/clinical_trials/stoppage_rescore_pilot.dossiers.jsonl
```

Before a cohort run, create a reproducible validation set balanced across the
11 legacy Sonnet categories and across registry/results/publication coverage:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  analyses/classifiers/rescore_trial_stoppage.py prepare \
  --validation-per-category 5 --seed 20260902 \
  --out tmp/stoppage-validation-v1/dossiers.jsonl \
  --selection-out tmp/stoppage-validation-v1/selection.jsonl

.venv/bin/dotenv run -- .venv/bin/python \
  analyses/classifiers/rescore_trial_stoppage.py score \
  --dossiers tmp/stoppage-validation-v1/dossiers.jsonl \
  --out tmp/stoppage-validation-v1/luna.jsonl \
  --model gpt-5.6-luna --workers 4 --confirm-paid
```

Run the identical frozen dossiers with `gpt-5.6-terra` into a separate output
file for a paired comparison. Validation sampling metadata is excluded from the
model prompt, so the legacy category cannot leak into the new verdict.

For a cohort run, omit `--nct-id`. The default scope is every trial that has a
legacy `why_stopped` classification. The dossier includes structured primary
outcome values/analyses, adverse-event summary counts, and up to 20 linked
publication abstracts. Every excerpt is tied to its immutable
`source_document_id`. Dossier v4 also includes curated external-source excerpts,
their target relationship, support flags/types, locator, source-text kind, and
program scope. Result v3 requires separate source-ID arrays for scientific
outcome, termination driver, and program outcome; deterministic validation
rejects sources whose flags do not permit the claimed axis. Multiple explicit
stopping causes retain one benchmark-compatible primary driver plus secondary
drivers.

Use the resumable Batch API for the full cohort. Submission is the only command
below that starts paid work:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  analyses/classifiers/rescore_trial_stoppage_openai_batch.py submit \
  --dossiers data/clinical_trials/stoppage_rescore_all.dossiers.jsonl \
  --manifest data/clinical_trials/stoppage_rescore_all.batches.jsonl \
  --model gpt-5.6-terra --confirm-paid-batch

.venv/bin/dotenv run -- .venv/bin/python \
  analyses/classifiers/rescore_trial_stoppage_openai_batch.py collect \
  --dossiers data/clinical_trials/stoppage_rescore_all.dossiers.jsonl \
  --manifest data/clinical_trials/stoppage_rescore_all.batches.jsonl \
  --out data/clinical_trials/stoppage_rescore_all.raw.jsonl

.venv/bin/python analyses/classifiers/rescore_trial_stoppage.py assemble \
  --dossiers data/clinical_trials/stoppage_rescore_all.dossiers.jsonl \
  --results data/clinical_trials/stoppage_rescore_all.raw.jsonl \
  --out data/clinical_trials/stoppage_rescore_all.jsonl \
  --expected-count 5510

.venv/bin/dotenv run -- .venv/bin/python db/13_ingest_llm_outputs.py \
  --task trial-stoppage-rescore --dry-run \
  data/clinical_trials/stoppage_rescore_all.jsonl
```

The direct `score` subcommand exists for a small pilot, rejected-row repair, or
Batch API long tail and also requires `--confirm-paid`. Pass each reviewed
repair file with `--replacement-result`; base-result duplicates, invalid rows,
or a missing trial prevent final output. Replacements are applied explicitly
and counted. Both scoring paths use strict structured output, reject cited
document IDs absent from the dossier, and retain exact prompts, responses,
hashes, token usage, and costs. Rejected direct calls retain the raw response
and usage envelope. Narrow deterministic repairs may fill an unknown axis's
registry citation, conservatively downgrade an unsupported primary-endpoint
claim to `unclear`, or apply the declared precedence to causes the model itself
describes as coequal; every such edit is recorded in
`_deterministic_repairs`. The Batch manifest also pins the prompt version and,
for new submissions, the system prompt hash so a changed collector cannot
misattribute the submitted prompt.

**Canonical cost field is `_cost_usd`.** Older classifier outputs used
`_cost_share` (Sonnet why_stopped verify) or `_cost` (silent_kill,
target_resolution). `db/02_ingest.py:_read_cost` accepts all three for
back-compat, but new runs write only `_cost_usd`.

The cost value is never produced by the LLM — the LLM output schema is
strictly the evidence fields (cat / confidence / rationale / scores /
tier / etc.). `common.py:call_with_retry` reads `resp.usage.input_tokens`
and `resp.usage.output_tokens` from the API response, applies a per-model
price table, and the wrapper appends `_cost_usd` to the row.

## Resumability

Each script skips subjects already present in its output file. Interrupted runs
resume cleanly — just re-invoke with the same `--out`.

## Prompt versioning

Every script has a `PROMPT_VERSION` constant. When the prompt changes:

1. Bump `PROMPT_VERSION` (e.g. `"v1"` → `"v2"`).
2. Rerun with a new output filename.
3. Ingest both files — `preclin.evidence_score` and `preclin.classification` are
   keyed on `(subject_id, dimension, source, source_version)` or
   `(subject_key, classifier_task, classifier_model, classifier_version)`,
   so old and new records coexist. Views resolve to the latest by default.

Never edit prompts in place without a version bump. That kills reproducibility.

New classifier JSONL rows receive a unique `_run_id`. After
`db/10_clinical_trial_source_audit.sql` has been applied,
`db/13_ingest_llm_outputs.py` stores them in `preclin.llm_run`. Verdicts point
to their latest run, while literature extraction runs connect to every
`preclin.evidence_score` fact they produced and retain an immutable
`fact_snapshot` of the run-produced value. Legacy rows remain auditable as
outputs but are explicitly marked as missing their unrecoverable exact inputs.

## Cost accounting

Every classifier records per-row token counts and USD cost. Aggregate at any
time with e.g.:

```bash
jq -s 'map(._cost_usd) | add' data/clinical_trials/stoppage_rescore_all.jsonl
```

Cumulative spend is also printed after each row while a script runs.

## Not in scope

- **Genome-browser ETL** (gnomAD / GWAS Catalog / DepMap / ClinGen / OMIM /
  STRING / Reactome / SIDER / HPO / DGIdb / HPA / GTEx / Open Targets / IMPC).
  Those tables live in `public.*`, populated by a separate project. This repo
  reads from them but does not rebuild them.

## Adding a new classifier

Follow the existing pattern:

1. Add a script to `analyses/classifiers/`.
2. Use `common.py` for the Anthropic client, retry, JSON extraction, JSONL
   append, and resumability helpers.
3. Define `PROMPT_VERSION` and `DEFAULT_MODEL` at module top.
4. Write audited JSONL that `db/13_ingest_llm_outputs.py` knows how to read,
   or add a new explicit task handler there. CSV-only workflows need their own
   importer because CSV currently drops the exact prompts and raw response.
5. Add a row to the table above.
