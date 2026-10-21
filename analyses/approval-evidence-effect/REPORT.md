# Approval-associated research amplification

**Analysis date:** 2026-09-07

**Status:** completed for GWAS Catalog and ClinGen; proposed for literature evidence
**Interpretation:** descriptive association, not a causal effect of approval

## Question

Do targets receive more research after their first drug approval, such that
current-day evidence volume or database coverage can retrospectively encode a
target's success?

This matters because the benchmark is intended to measure evidence available
at a prediction point. A feature assembled from a current snapshot may include
research published only after a target became clinically or commercially
validated.

## Existing event study

The analysis uses a target's first ChEMBL-recorded approval year as the event.
It compares changes in annual evidence records for targets first approved in
2019--2022 with changes for targets not yet approved in the same year. The
reference period is event year -1. The primary post-event summary is the
cumulative difference over years +1 through +3; the approval year is excluded
because only annual approval timing is available.

The analytical universe contains 512 clinical targets with a known ChEMBL
mapping state. The treated sample contains 34 targets whose first clinical
program predates their first approval. Uncertainty uses 5,000 target-cluster
bootstrap resamples with seed 42.

### Universe construction

The current script assembles the universe as follows:

1. Rank every primary drug--target mapping by source priority. The current
   event-study script gives `fda_approval` mappings first priority, followed by
   verified LLM, public therapy-target, ChEMBL bulk, and other LLM mappings.
2. At the best available priority for each drug, retain the drug only if every
   tied row identifies one unique target. This resolves 2,887 of 5,081 mapped
   drugs and excludes 2,194 ambiguous drugs.
3. Link resolved drugs to clinical programs; exclude placebos, pathogen targets,
   and genomic entities; then collapse to target level and retain the earliest
   clinical-program date. This produces 655 dated clinical targets.
4. Retain only targets present in the versioned ChEMBL target-approval mapping,
   so an absent target is treated as unknown mapping status rather than as
   never approved. This leaves 512 targets, including 232 ever-approved targets.
5. Define treatment cohorts by first target approval in 2019--2022 and require
   clinical entry by the year before approval. This leaves 34 treated targets.
6. At each event time, compare a cohort with clinical targets that had entered
   by the same baseline and were not yet approved by that calendar year. A
   never-approved-only control is retained as a sensitivity analysis.

This is a target-level, all-indication clinical universe. It is not restricted
to the same indication or therapeutic area. It also predates the benchmark's
approval-independent consensus mapping: the use of `fda_approval` as the
highest-priority drug--target source can make target inclusion outcome-aware.
Before extending the analysis, the universe query should use
`preclin.v_drug_target_consensus` or its materialized consensus map, quantify
the resulting cohort changes, and regenerate the estimates.

### Results

| Outcome | Observed, years +1 to +3 | Estimated without approval | Excess records | 95% interval | Treated-target coverage |
|---|---:|---:|---:|---:|---:|
| Distinct GWAS studies | 30.85 | 22.80 | **+8.05 (+35%)** | -0.03 to +18.16 | 34/34 |
| ClinGen classifications | 0.235 | 0.037 | **+0.199** | +0.047 to +0.378 | 7/34 |

The GWAS estimate is suggestive but its primary interval narrowly includes
zero. The never-approved-control sensitivity is similar (+8.13, 95% interval
+0.23 to +18.14). ClinGen has a positive absolute estimate but is too sparse
for a stable relative multiplier.

The joint pretrend tests do not reject a zero pretrend (GWAS p=0.826; ClinGen
p=0.178). Non-rejection is not evidence that approval is exogenous or that
parallel trends necessarily hold. Approval is selected by prior evidence and
investment, and research published afterward may have begun before approval.

## Therapeutic-area composition

The primary event study does **not** restrict controls to the same indication
or therapeutic-area space. It operates at target level and pools the mapped
clinical-target universe. Therapeutic area is not an adjustment variable in
the current estimator.

As a diagnostic, each target was assigned its modal therapeutic area by number
of linked programs. The live database composition on 2026-09-07 was:

| Primary therapeutic area | Treated 2019--2022 (n=34) | Other mapped clinical targets (n=478) |
|---|---:|---:|
| Other | 19 (55.9%) | 268 (56.1%) |
| Oncology | 8 (23.5%) | 118 (24.7%) |
| Autoimmune | 3 (8.8%) | 21 (4.4%) |
| Infectious | 2 (5.9%) | 11 (2.3%) |
| Metabolic | 1 (2.9%) | 19 (4.0%) |
| Neuro | 1 (2.9%) | 22 (4.6%) |
| Cardiovascular | 0 | 16 (3.3%) |
| Rare | 0 | 3 (0.6%) |

The two largest categories are similar, so there is no obvious gross imbalance
in this diagnostic. It does not establish comparability: a modal label hides
multi-indication targets, the actual not-yet-approved control set changes by
cohort year, and 34 treated targets are too few for precise area-specific
effects.

Recommended robustness checks are:

1. match or weight controls within therapeutic area and clinical-entry cohort;
2. allow targets to carry multiple area memberships rather than only a modal
   label;
3. report leave-one-area-out estimates;
4. report area-specific estimates only where treated counts support them; and
5. compare results with indication-level panels when evidence can be linked to
   a specific target--indication pair.

## Extension to cell and animal literature

Yes, the same question can be tested for literature Lines B--E. The current
target-level scores are generated from up to 60 canonical PubMed abstracts:

- Line B: mechanistic biology;
- Line C: cell-pathway validation;
- Line D: animal in vivo evidence; and
- Line E: human pharmacodynamic engagement.

However, the stored score is a current cross-sectional summary, not a dated
annual series. Regressing that score directly on approval timing would not be a
valid event study. The evidence must first be reconstructed as it would have
been available in each year.

### What is already backfilled

The publication work is substantial and should not be repeated:

- all 60,589 GWAS studies represented in the association data have normalized,
  versioned evidence-availability dates;
- the canonical source store contains 3,710 distinct PubMed IDs, including
  625 target-linked documents across 315 targets, plus 5,746 distinct
  Paperclip-derived PMC IDs linked across 1,015 targets;
- all 625 target-linked documents contain a PubMed publication date in their
  retained raw XML, even though that date is not yet projected into a
  queryable normalized column; and
- newer Nelson and trial-stoppage model runs retain exact prompts, input
  hashes, source IDs, and excerpts. Nelson has 17,274 PubMed-input links across
  6,701 runs; the trial-stoppage rescore has exact source inputs for 5,525
  runs.

The apparent date gap comes from looking only at `source_updated_at` and
`public.publications`. `source_updated_at` is empty for these PubMed documents,
and only 2 of the 625 target-linked PMIDs overlap a dated row in
`public.publications`, but the raw PubMed XML itself contains the dates. The
next step is local parsing and normalization, not a network refetch.

The PMC corpus needs a separate normalization pass. Its rows retain titles and
abstracts but not a normalized publication date, source version, raw source
payload, attribution, or rights notice. They are linked to targets as
`scored_for` records but are not linked to an exact `llm_run_source` input.
A PMC-to-PMID/DOI crosswalk is needed before combining them with PubMed records
without double counting.

The remaining provenance gap is concentrated in literature scoring. The
target literature **was rerun** as `v2_proper`: the database contains 4,404
Line B--E facts covering 1,101 targets. Those facts were loaded through the
older evidence ingestion path, however, and none is connected to an auditable
`llm_run` containing its prompt, input hash, ordered source documents, or exact
excerpts.

The 579 `legacy_import` target-literature runs are synthetic audit wrappers for
older v1 facts that existed before the run-provenance schema. Of those, 315
have recovered `reported_citation` links, but these are notable citations
rather than the complete ordered abstract set and the original prompts and
hashes are absent. They do not represent the `v2_proper` rerun.

The repository and database do not retain the exact command that produced the
`v2_proper` rows. Their timestamps place them after the audited-run schema was
added, but they do not appear in `ingest_log`, and the repository holds no
scorer that declares prompt version `v2_proper`. The most supportable
explanation is therefore that the v2 content was produced by a separate or
one-off scoring path and loaded through the older evidence-only ingestion
route. This is a provenance failure, not evidence that the content itself was
never rerun. Recovering the original cache or rerunning the missing targets
through an audited scoring path is still required; a paid rerun requires
explicit approval.

Within the 792-target headline cohort, `v2_proper` covers 676 targets; another
87 fall back to v1 evidence and 29 have no literature score. Migration 27 now
selects `v2_proper` explicitly per target and line, with the latest v1 row as a
fallback. Before that fix, the wide view used `MAX(value_numeric)` across every
stored version. The old and new policies happen to produce identical current
values, but the explicit selector prevents a future rerun from silently winning
merely because it produced a larger score.

The 553 legacy drug-evidence runs also have no recovered source links. This is
evidence about a particular molecule or therapeutic program rather than the
target in general: cell efficacy, rodent and non-rodent efficacy, direct target
engagement, structural biology, toxicity signals, and Phase 2/3 endpoint
evidence. Two drugs against the same target may differ in modality, epitope,
selectivity, exposure, and dose, so these facts must remain drug-scoped. Across
all target literature facts, 755--1,077 facts per dimension retain one or more
notable PMIDs. Those facts name 2,704 distinct cited PMIDs, of which only 250
currently have a canonical PubMed source document, so the citation-document
backfill is also incomplete.

### Recommended design

1. **Normalize evidence-availability dates.** Parse the retained PubMed XML
   locally, selecting the earliest electronic publication date and falling
   back to print publication date. Store the date basis and precision rather
   than using retrieval time. Fetch only the residual PMIDs whose stored
   source payload has no usable date.
2. **Reconcile publication identities.** Add the PMC-to-PMID/DOI crosswalk,
   deduplicate PubMed and PMC representations, and complete canonical source
   documents for the remaining cited PMIDs.
3. **Recover complete scorer inputs.** Import original abstract caches where
   available. Mark legacy runs without recoverable inputs as incomplete rather
   than treating their notable PMIDs as the full corpus.
4. **Create atomic, line-specific evidence facts.** Classify each abstract once
   for whether it supports Lines B, C, D, or E, the supported tier component,
   target/indication/drug scope, and direction. This is preferable to repeatedly
   rescoring an entire growing corpus at every annual cutoff.
5. **Construct annual features.** For each target and year, calculate new and
   cumulative supporting abstracts, independent laboratories, source diversity,
   highest supported tier, and whether the line has any coverage.
6. **Run the same event-study estimator.** Use not-yet-approved controls,
   therapeutic-area/entry-cohort matching, event-time estimates, pretrend
   checks, and target-cluster bootstrap intervals.
7. **Separate publication volume from evidence strength.** More abstracts do
   not necessarily mean stronger evidence. Report both record counts and
   changes in the supported biological tier.

A free first pass can measure total target-linked PubMed publication volume
after dates are restored. A credible Line C versus Line D analysis requires
line-specific abstract classification. That may be manual, deterministic with
validation, or LLM-assisted; any paid classification must be separately
approved.

An atomic literature fact should minimally contain:

| Field | Purpose |
|---|---|
| `source_document_id` and `source_locator` | identify the immutable article and supporting passage |
| `target_id`, optional `indication_id`, optional `drug_id` | preserve the biological scope of the claim |
| `evidence_line` and `subdimension` | distinguish, for example, primary-human-cell evidence from rodent efficacy |
| `evidence_polarity` | supported, contradicted, null, mixed, or unclear |
| `species` and `model_system` | retain whether evidence came from cell line, organoid, mouse, primate, or human |
| `replication_group` | distinguish one experiment from independent replication |
| `evidence_available_date`, basis, and precision | permit valid cutoff-time aggregation |
| `extraction_run_id` and `confidence` | connect the fact to an exact, auditable extraction |

`subdimension` is a controlled claim type within a broad evidence line, not a
new headline score. For Line C it could distinguish immortalized cell lines,
primary human cells, iPSC models, organoids, perturbation-rescue, and independent
replication. For Line D it could distinguish rodent efficacy, non-rodent
efficacy, model relevance, multi-species replication, dose-response/PK-PD, and
chronic dosing or toxicity. This prevents any abstract that merely mentions an
animal or cell from receiving the same generic evidence label and makes the
aggregate score reproducible from its supporting claims.

Annual Line C/D features can then be produced deterministically by filtering
facts to `evidence_available_date <= cutoff`, matching their target--indication
or drug scope, and applying a versioned tier rule. The model does not need to
rescore the complete accumulated abstract corpus separately for every year.

## Quantifying model inflation

The event study measures evidence growth, not how much that growth inflates the
benchmark. The decisive model-level analysis is a paired comparison on the
same cohort and held-out-target folds:

1. current-snapshot features;
2. features frozen at the declared prediction date;
3. frozen features plus explicit source-coverage variables; and
4. a negative-control model using only evidence that became available after
   the outcome.

Report paired changes in AUC, top-decile relative success, recall, precision,
and calibration with target-cluster bootstrap intervals. Predictive signal in
the future-only negative control is direct evidence of retrospective leakage.

## Reproduction and artifacts

Run the recorded GWAS/ClinGen analysis with:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  analyses/approval-evidence-effect/approval_research_event_study.py \
  --bootstrap 5000
```

Artifacts:

- `approval_research_event_study.py`: estimator and database queries;
- `data/approval_research_event_study.csv`: dynamic event-time estimates;
- `data/approval_research_event_study_summary.json`: complete audit metadata,
  summary estimates, intervals, and influence checks; and
- `fetch_chembl_target_approval_history.py`: versioned ChEMBL treatment-history
  refresh.
