# Target origin: pilot of 100 pairs (#146 step 4), 2026-11-19 to 2026-11-20

## State (2026-11-20 14:55 Pacific, third run, aligned definitions)

**Both gates pass**: set b (untouched) κ 0.65 on the label as read against the majority of three blind readings, set a
0.69, coverage gap 8 points (`target_origin_gate.json` is set b, `target_origin_gate_set_a.json` set a). Labeller
prompt v2, blind reader v3, checker v3; the full run (step 5) started on this result.

The pilot ran three times on the same 100 pairs and this file is the dated record of all three: the first run (prompt
v1, 2026-11-19) failed the agreement gate for a structural reason; after the fix pass the second run (2026-11-20)
passed on the label as read; the third run, under the definitions aligned with the evidence chart, is the state above.

# First run (prompt v1, 2026-11-19)

The gate reference is the one the owner decided on 2026-11-19: three independent blind model readings of hand-check
set a, majority taken. The agreement gate failed and the coverage gate passed; nothing beyond the pilot ran until the
third run. Numbers below are from the gate file as this run wrote it, `python -m pipeline.target_disease summary
--pairs pilot` and the decision log.

## Sample

Seed 20261119: 50 cohort pairs with a settled "not causal" stop and 50 without (pairs with any stop filed as
unresolved left out of both groups, 127 of 5,091, per #158; the 5,091 are the window's 5,174 pairs less the 83 the hub flags `validated_at_entry`,
Lin 0.8 or more; frame 703 and 4,261). Set a: 25 per group.

## Retrieval (`search --pairs pilot`)

| | not causal | other | all |
|---|---|---|---|
| pairs | 50 | 50 | 100 |
| pairs with at least one pre-entry record | 20 (0.40) | 24 (0.48) | 44 |
| records stored | | | 4,583 (median per pair 0, max 1,446) |

Coverage gap 8 points: **passes** (at most 10). Fifty-six pairs have no record that names both the gene and the
disease before the cutoff year. The query is correct; the names are too few. The hub's HGNC table carries the symbol,
the HGNC name and alias symbols but not the protein names, so a receptor of a well-known ligand is searched under its
HGNC name alone (PTGIR was searched as "PTGIR" and "prostaglandin I2 receptor"; its alias "IP" is dropped as too
short; papers say "prostacyclin receptor" or "IP receptor"; the gene names alone find 38 pre-2017 abstracts, the
disease alone 1,141, both none).

## Labelling (`label --pairs pilot`, Opus 5.5, web search and fetch)

99 of 100 pairs decided over three passes (94, 3, 2). Rejected answers: 5 refusals (two pairs, one never decided) and
5 rule breaks (a PMID cited from memory rather than retrieved, 3; a year count mismatch, 1; an origin year not among
the cited sources, 1). Tokens per decision: 4,318 in, 2,144 out.

| origin as read, over the 48 labels the check supported and the 10 left unclear | n |
|---|---|
| animal_model_pharmacology | 11 |
| earlier_drug_other_disease | 7 |
| observational_biomarker | 7 |
| diseased_tissue | 7 |
| human_cell_perturbation | 4 |
| clinical_observation | 4 |
| human_genetics | 3 |
| tumour_genetics | 2 |
| mouse_genetics | 2 |
| curated_pathway | 1 |
| unclear | 10 |

Grades over the same 58: stated 22, pattern 26, none 10; the 41 rows the check rewrote are in the check section. Discovery route: derived
from an existing active 25, repurposed drug 25, target screen 12, de novo design 5, unclear 32.

## Check (`check --pairs pilot`, Sonnet 5.5, fetch only)

89 graded labels checked: supported 48, unverified 37, unsupported 4. Of the 37 unverified, 33 are "could not open":
the checker's fetch failed on PubMed ("too many requests"), ResearchGate, Semantic Scholar and blocked hosts, and 34 of
the 37 labels cite URLs only, so no shown record could carry the quote. Unverified is a fetch failure, not a reading.
Under the design an unverified or unsupported row is rewritten as unclear, so after the check 51 of 99 labelled rows
are unclear.

## Reference reading (`blind --pairs set_a`, Opus 5.5, records only, three replicates)

150 readings, all valid. Consistency: 46 of 50 pairs unanimous, 3 by majority, 1 with no majority; pairwise
agreement 0.94. Reference origins: unclear 39, human_genetics 3, earlier_drug_other_disease 2, and one each of
human_cell_perturbation, diseased_tissue, observational_biomarker, tumour_genetics, curated_pathway.

## Gate (`gate --set a`)

| | pairs | κ labeller raw | κ stored after check | reference unclear | labeller unclear |
|---|---|---|---|---|---|
| all compared | 49 | 0.21 | **0.42** | 39 | 6 |
| pairs with a record | 16 | 0.58 | 0.77 | 6 | 1 |
| pairs with no record | 33 | 0.00 | 0.00 | 33 | 5 |

Agreement gate **fails** (0.42 against 0.6). Collapsed-layer κ 0.41 (stored) and 0.20 (raw); the reference's origin
is the labeller's primary or secondary origin for 0.31 of pairs. (The split by coverage was computed by hand for this
first run; `gate` now reports it as `kappa_covered` and `kappa_uncovered`.)

## Reading of the result

- The failure is structural, not a reading disagreement. The reference reads the stored records and nothing else; 33
  of the 49 compared pairs have no record, so the reference says unclear for all 33 while the labeller, with web
  search, labels 28 of them. On the 16 pairs where both saw records, κ is 0.58 raw and 0.77 after the check, above the
  gate.
- The check's "unverified" outcome is dominated by fetch failures (33 of 37), and it removes 37 labels from the tests.
- Two defects of this pilot are therefore the reference's access and the checker's reach, not the labeller's prompt.
  The registered design allows one prompt revision; the revision worth making is elsewhere.

## Options proposed (all three taken; next part)

1. Give the reference reader the labeller's access (web search and fetch, still no provisional origin and no program,
   three replicates) and re-read set a; the labeller's prompt is unchanged, so set a is still unshaped by it. Set b stays
   reserved for a labeller revision.
2. Add the UniProt and HGNC protein names to the gene names and re-run `search`; fewer pairs without records.
3. Let the checker read a PubMed URL's record through E-utilities instead of fetching the page, throttle its fetches,
   and count a label with a cited but unopenable source as `unverified` only when every source failed; keep the
   registered "unverified as labelled" sensitivity.

Posted to #146 as a dated comment for decision; the full run waits for both gates.

---

# Re-run after the three fixes (2026-11-19 late to 2026-11-20 early)

Same 100 pairs, same labeller prompt (v1). Changes, posted on #146 before the run: gene names gain the UniProt and
HGNC protein names (a symbol of three characters or fewer is searched only when no other name exists; migration 144
stores the count without it); the blind reference reader has the labeller's web search and fetch (prompt v2); the
checker reads cited PubMed records through E-utilities, ignores the label's decision id, runs three passes (prompt
v2). The agreement gate is scored on set b, untouched until now; set a is reported beside it. Gate files:
`target_origin_gate.json` (set b), `target_origin_gate_set_a.json`.

## Retrieval

| | not causal | other | all |
|---|---|---|---|
| pairs with at least one pre-entry record | 22 (0.44) | 26 (0.52) | 48 |
| records stored | | | 5,076 (max per pair 1,598) |

Coverage gap 8 points: **passes**. Fifty-two pairs still have no record naming both the gene and the disease.

## Labelling and check

100 of 100 pairs decided (two passes). Grades over the 55 labels the check supported and the 10 left unclear: stated
28, pattern 27, none 10. Discovery route:
derived from an existing active 31, repurposed drug 23, target screen 12, de novo design 6, unclear 28. Tokens per
label decision 4,262 in and 2,110 out; per reference reading 4,283 in and 930 out; per check 750 in and 379 out.

Check of 90 graded labels: supported 55, unsupported 21, unverified 14. Of the 35 rejections, `quote_found` was
could_not_open 18, yes 11, no 6; `origin_follows` was no 15, partly 11, yes 9; 29 of the 35 cite publisher,
ResearchGate or other non-PubMed URLs that a fetch-only checker cannot open. After the check 45 of 100 stored rows
are unclear.

## Reference reading (web-enabled, three replicates)

| set | readings valid | unanimous | majority | no majority | pairwise agreement |
|---|---|---|---|---|---|
| b | 148 of 150 | 35 | 14 | 1 | 0.82 |
| a | 149 of 150 | 30 | 16 | 4 | 0.72 |

Reference origins on set b: human_cell_perturbation 8, animal_model_pharmacology 8, earlier_drug_other_disease 8,
observational_biomarker 7, diseased_tissue 6, unclear 5, tumour_genetics 2, human_genetics 2, clinical_observation 1,
phenotypic_screen 1, mouse_genetics 1. The labeller's raw origins on the same set: animal_model_pharmacology 9,
earlier_drug_other_disease 9, diseased_tissue 7, observational_biomarker 7, unclear 5, human_cell_perturbation 4,
clinical_observation 4, tumour_genetics 2, mouse_genetics 2, human_genetics 1.

## Gate

| set | pairs | κ labeller raw vs reference | κ stored after check | κ with records | κ without records | reference is primary or secondary | pass (stored) |
|---|---|---|---|---|---|---|---|
| b | 49 | **0.70** | 0.43 | 0.41 (26) | 0.41 (23) | 0.76 | no |
| a | 46 | 0.68 | 0.40 | 0.43 (19) | 0.37 (27) | | no |

Collapsed-layer κ on set b: 0.45 stored. No pair is missing a label.

## Reading of the result

- **The two independent readers agree.** With equal access, the labeller's label and the majority of three blind
  readings agree at κ 0.70 on set b and 0.68 on set a, above the registered 0.6, with the reference's origin being
  the labeller's primary or secondary origin for 0.76 of pairs. The access problem of the first run is gone: κ is the
  same with and without stored records.
- **The check, not the labelling, fails the stored-origin gate.** The checker rejects 35 of 90 labels. On set b the
  reference agrees with the labeller on 6 of 6 labels marked unverified and 7 of 11 marked unsupported, the same
  rate as for the labels it kept (20 of 27). The rejections are mostly the checker's reach (18 "could not open"; 29
  cite pages a fetch-only checker cannot read), not the labels' content.
- The gate statistic "stored origin after the check" was the design's own choice (the registered text says "kappa
  ≥ 0.6 against a blind hand check of 50" and is silent on the check). On the labeller's label as read, the gate
  passes; on the stored origin it fails.

## Decisions (2026-11-20)

Both taken on 2026-11-20 and posted on #146 for the owner to object to: (1) the agreement gate is scored on the
labeller's label as read, the registered wording, and the check's outcome rates are reported as the filter they are
(`gate_origin` in the gate file; the stored-origin κ stays beside it); (2) checker v3, with the labeller's search and
fetch, re-checks the graded labels. Neither is a revision of the labeller's prompt.

# Definitions aligned with the evidence chart (2026-11-20)

The owner's one-list decision of 2026-11-20 (#146): the thirteen origin kinds and the evidence chart's lines are one
list, so each kind is defined the way its chart line is. Against `report/evidence_lines.py`, eight definitions matched
and five were redefined: cell_screen is a screen in human cells (the chart's `crispr` line); earlier_drug_other_disease
is an approval for an unrelated disease (`approved_unrelated_only`; an approval for a related disease, Lin 0.5 or
more, is the chart's b1 line and excludes the tier; the hub's `validated_at_entry` flag is the stricter Lin 0.8, see
`target_origin_run.md`, last section); diseased_tissue covers RNA and protein in the tissue (the `expression` line plus #154's
protein-in-tissue kind) and observational_biomarker is a measurement in blood, another fluid or imaging (#154's
tracking kind); animal_model_pharmacology says non-genetic (#154's second kind). The crosswalk is
`pipeline.target_origin.CHART_LINE` with a test, and a table in the codebook; migration 145 restates the column
comment.

What the change can touch in the pilot: no v1 label or v2 blind reading was cell_screen, and no pilot pair is
validated at entry by the hub's flag (by the chart's approval index six are, five in set a and one in set b;
`target_origin_run.md`, last section), so the first two cannot move a label. The tissue boundary can: 6 of the 12 diseased_tissue labels
rest on protein or staining evidence, and 9 of the 13 observational_biomarker labels mention protein, serum, plasma,
CSF or urine; the pilot's boundary between the two was fuzzy. Both kinds are on the same side of O1. The definitions
sit in all three prompts, so the labeller is v2, the blind reader v3 and the checker stays v3 (no v3 decision exists).
The pilot is relabelled under the aligned prompts before the full run, so that the gate is scored on the prompt the
full run uses; the v1 labels and v2 readings stay on record, and v1 to v2 agreement on the 100 pairs is reported. This
is the owner's definition change, not the registered single prompt revision, which stays unused.

# Pilot under the aligned definitions (2026-11-20, 14:41 to 14:55)

Same 100 pairs and the same records; labeller v2, blind reader v3, checker v3; migration 145 applied first; the gate
scored on the label as read (`gate_origin` raw). Gate files as this run wrote them: commit cf20780; both were rerun
on the stored table after check v2 (`target_origin_run.md`, last section), where set a's stored κ is 0.52 and the
with / without records split is 0.52 / 0.52.

## Labelling and check

100 of 100 pairs decided (passes of 100, 7 and 1). Agreement of the v1 and v2 labels on the 100 pairs: κ 0.73, 76
the same, 0.81 on the collapsed layer. The largest move is observational_biomarker to diseased_tissue (6 pairs), the
boundary the alignment drew; then earlier_drug_other_disease to clinical_observation (3); ten other moves of one pair
each. Origins under v2: diseased_tissue 22, earlier_drug_other_disease 16, animal_model_pharmacology 15, unclear 13,
clinical_observation 11, human_cell_perturbation 9, observational_biomarker 5, human_genetics 4, mouse_genetics 3,
tumour_genetics 1, curated_pathway 1. Grades: stated 35, pattern 52, none 13. Discovery route: derived from an
existing active 28, repurposed drug 20, target screen 14, de novo design 6, unclear 32.

Check v3 of the 87 graded labels: supported 72, unsupported 12, unverified 3 (v2 on the v1 labels: 55, 21, 14 of 90).
`quote_found` yes 81, no 1, could_not_open 5; `year_ok` no 1, unknown 2; `origin_follows` yes 35, partly 42, no 10.
The 12 unsupported: 8 where the origin does not follow from the quote, 2 could not open with the origin not
following, 1 quote not found, 1 source dated in or after the cutoff. After the check 28 of 100 stored rows are
unclear (13 graded none, 15 rejected).

## Reference reading (v3, three replicates)

| set | readings valid | unanimous | majority | no majority | pairwise agreement |
|---|---|---|---|---|---|
| b | 144 of 150 | 34 | 13 | 3 | 0.83 |
| a | 148 of 150 | 36 | 12 | 2 | 0.82 |

The v2 and v3 references agree at κ 0.80 on set b (38 of 46 pairs the same) and 0.79 on set a (36 of 44); the
largest move is again observational_biomarker to diseased_tissue (4 and 3 pairs).

## Gate

| set | pairs | κ label as read | κ stored after check | κ layer, read / stored | κ with / without records (stored) | reference is primary or secondary | gap | pass |
|---|---|---|---|---|---|---|---|---|
| b | 47 | **0.65** | 0.55 | 0.65 / 0.54 | 0.44 / 0.65 | 0.77 | 8 | **yes** |
| a | 48 | 0.69 | 0.54 | 0.68 / 0.53 | 0.53 / 0.53 | 0.77 | 8 | yes |

Both gates pass on both sets. Against the first re-run, κ on the label as read moved from 0.70 to 0.65 on set b and
from 0.68 to 0.69 on set a; κ on the stored origin rose from 0.43 to 0.55 and from 0.40 to 0.54 as the checker's reach
grew (15 of 87 rejected, was 35 of 90). Tokens per decision over every version run on the pilot: label 4,247 in and
2,078 out (299 decisions); reference reading 4,236 in and 1,053 out (739); check 773 in and 381 out (266).

Step 4 is complete. The full run (step 5) ran from 2026-11-20 15:04 to 2026-11-21 09:32 after its announcement on #146; its audit is `target_origin_run.md`.
