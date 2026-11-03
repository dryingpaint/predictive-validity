# Engagement readouts: what "engaged" rests on

Working plan for a possible PR (#82). Companion to the model-system atlas (#76, PR #81) but independent
of it: the input is the efficacy-attribution labels in `pv_evidence`, not the atlas drafts.

## Question

When an efficacy-failed program is labelled "target engaged", what was actually measured, and was that
readout ever tied to the target in humans independently of the preclinical model? A downstream biomarker
counts as engagement only if something established that it moves when, and only when, the target is
modulated. That link can come from a direct assay calibrated against the marker (PET occupancy vs
prolactin), from human genetics (SLC5A2 loss of function and glucosuria), from a prior drug of the same
mechanism, or from pathway logic alone, which for a first-in-class drug usually means the animal model
itself. The last case makes "engagement matched" partly circular.

## What the DB holds today

- Programs that stopped for efficacy or exposure (Phase 2 and 3, 2008–2019) carry an efficacy-attribution
  label: three pillar verdicts (`exposure`, `engagement`, `pathway`, each adequate / inadequate /
  inferred_adequate / no_human_data), two flags (`engagement_in_disease`, `engagement_before_index`), a
  failure code, a free-text `rationale` and `sources`. Task `efficacy_failure_attribution`; a second pass,
  `efficacy_attribution_search`, re-labels with web search where the bundle was indeterminate.
  `pipeline.stops.labels()` is the merge the report uses.
- In the run completed 2026-11-02 (3,160 programs): engaged 910, inferred 469, not engaged 136, no human
  data 1,645. Of the 910, 358 were shown in the disease itself and 533 before the failed trial started.
- The readout behind each verdict is named only inside the rationale (HSP70 induction in plasma, plasma
  LPA, tumour AXL protein, brain NAD+/NADH by MRS). No field records it.

## Design: two layers, re-runnable

| layer | file | keyed by | changes when the labels are re-run? |
|---|---|---|---|
| 1 program → readout | `readouts.csv` | `content_sha` = sha256 of the label fields read (rationale, sources, three verdicts, code) | only rows whose rationale changed are re-extracted |
| 2 target × readout → anchor | `anchors.csv` | `target` + `readout_canonical` | no |

Layer 1 is a mechanical LLM extraction from the rationale text alone, no research, under
`EXTRACTION_BRIEF.md`. Layer 2 is researched once per (target, readout) pair with a date and a source.
A re-run of the labels is: `pull.py` → `extract.py todo` (writes only the rows whose hash is new) → run
the extraction on those batches → `extract.py merge`. The join to layer 2 is by canonical readout name,
so the vocabulary is controlled: the extractor picks from the existing names first and proposes a new
one only when nothing fits.

## Steps

| step | what | status |
|---|---|---|
| 1 | `pull.py`: current labels with drug, primary targets, hash. `extract.py`: delta, batches, merge, vocabulary. Run the extraction on every row with a human-data verdict | done 2026-11-02: 2,067 rows extracted, `readouts.csv`; result in `RESULTS_STEP1.md` |
| 2 | Cross-check the extraction against the 44 atlas engagement cells (PR #81, `readout_tier`) where the drug class overlaps | not started |
| 3 | `anchors.csv`: for each (target, readout) pair, how the readout was tied to the target in humans (direct_assay / genetics / prior_drug / pathway_only), with the earliest year and source; agent brief like the atlas drafter brief | not started; first job is collapsing the 1,326 names to one per target × readout family (about 700 targets) |
| 4 | Join and ask: how many "engaged" verdicts rest on a pathway-only readout; whether those programs sit in "engaged, disease did not respond" (F2) more often than anchored ones; the not-engaged share of the report under "anchored engagement only" as a new appendix variant | not started |

## Schemas

`labels.csv` (from `pull.py`, one row per labelled program): `key`, `program_id`, `mondo_id`, `phase`,
`moiety_id`, `drug`, `modality`, `targets` (primary target symbols, `;`-joined), `actions`,
`primary_code`, `bundle_code`, `searched`, `exposure`, `engagement`, `pathway`, `engagement_in_disease`,
`engagement_before_index`, `confidence`, `rationale`, `sources`, `content_sha`, `pulled_at`.

`readouts.csv` (layer 1, one row per `content_sha`): `content_sha`, `key`, `readout`, `readout_kind`
(occupancy / target_product / downstream_marker / clinical_response / exposure_only / none), `matrix`,
`subjects`, `inference_basis` (measured / other_disease / class / none), `specific_to_target`,
`readout_canonical`, `quote`, `note`, `extracted_by`, `extracted_at`.

`anchors.csv` (layer 2): `target`, `readout_canonical`, `anchor` (direct_assay / genetics / prior_drug /
pathway_only / unknown), `anchor_year`, `anchor_source`, `anchor_quote`, `specific_to_target`, `note`.

## Known gaps after the pull

- 720 of the 3,845 stops have no primary target in `preclin.moiety_target` (gene and cell therapies,
  unmapped biologics), so their canonical readout name is keyed by drug rather than target until a
  target is assigned; layer 2 needs one.
- 438 stops have no MONDO label in `preclin.indication`; the extractor sees the MONDO id only.
- `batches/` is not tracked: `readouts.csv` is the record and names the batch each row came from.

## Out of scope, and questions for Melissa

- Nothing writes to the DB (#70). The production form of layer 1 is a `pipeline/llm.py` Task whose
  subject is her attribution row, so her re-runs produce our delta automatically; that port waits on the
  DB-write question already in PR #81.
- The labels moved today (a run completed 2026-11-02 21:52 UTC). `labels.csv` records the decision ids it
  was pulled from; any number quoted from this directory should name that pull.
- Whether "inferred_adequate" (engaged because the drug worked elsewhere) should be split out of
  "engaged" in the report's headline once the readouts are known.
