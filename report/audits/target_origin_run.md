# Target origin: full run over the 2008–2019 window (#146 step 5), 2026-11-20 to 2026-11-21

## State (2026-11-22 Pacific, after the reread; the last section)

5,174 pairs, every one with a labelled row: 5,113 labelled, 61 not reached. 4,431 graded labels: supported 3,972,
unsupported 438 (88 validated at entry; the rest on a field answered no, 226 of them the category reread's no),
disputed 15 (`target_origin_disputes.csv`: quote 11, year 4, factual rows the research pass left open), unverified 6.
218 labels moved under the final list's definitions (202 human-cell labels on established cell lines to
cell_line_perturbation, 16 animal labels on a genetic change to mouse_genetics). Stored origin: unclear 1,126,
diseased_tissue 887, animal_model_pharmacology 845, earlier_drug_other_disease 596, clinical_observation 339,
human_cell_perturbation 260, observational_biomarker 256, cell_line_perturbation 206, mouse_genetics 204,
human_genetics 181, tumour_genetics 122, phenotypic_screen 70, not_reached 61, disputed 15, curated_pathway 6. Gates,
scored on the label as read under the prompts that ran: set b κ 0.65, set a 0.69, coverage gap 8 points, both pass.

The sections below are the dated record in the order things happened: the run as it ran (search, label, and the v1
check by Sonnet 5.5 alone), the checker sensitivity study of the next morning, and check method v2, which replaced the
v1 outcomes in the stored table that afternoon. The v1 check and the stored result under it are kept and marked
superseded. Numbers in the run sections are from the run log, `python -m pipeline.target_disease summary --pairs
window` and `pv_evidence.llm_decision`; the state above is from the stored table at the last commit.

**Research pass (2026-11-21, 21:20 to 21:43 Pacific; the last section).** One Opus 5.5 reading with search and fetch
per factual row of the disputes sheet (183: year 87, quote 64, and the 32 earlier-drug category rows the Drugs@FDA
index is silent on), the checkers' answers withheld, the year and the approval tier compared in code: 162 settled (yes
132, no 30), 21 open. The result is a filled copy of the sheet, `target_origin_disputes_research.csv`, not applied:
applying it would move 91 disputed labels to supported and 29 to unsupported, 274 staying disputed. The table above is
unchanged.

## How it ran

The full run started after both pilot gates passed under the aligned definitions (`target_origin_pilot.md`, last
part) and after its announcement on #146 (2026-11-20). It ran from 2026-11-20 15:04 to 2026-11-21 09:32 Pacific
time, unattended, as three invocations of one wrapper outside the repository: search until no pair had failed, then
`label`, `check` and `summary`, each over `--pairs window`, each re-invoked after a pause when it exited non-zero.
Every step is idempotent (search skips searched pairs, label reuses validated decisions, check skips checked rows),
so the second and third invocations only asked again for the pairs still unlabelled. The wrapper's output is
`target_origin_run_log.txt` beside this file (personal paths removed) and, for the afternoon's check v2 passes,
`target_origin_run_v2_log.txt`; the pass tables, refusal counts and token counts below are read from them.

## Scope

The window is every target × disease pair whose first Phase 2 or 3 entry falls in 2008–2019: 5,174 pairs
(`pair_frame("window")`). The 100 pilot pairs are inside it; their label decisions (100) and check decisions (87)
were reused unchanged, so the pilot's gate numbers stand for the same rows.

## Retrieval (`search --pairs window`)

| pass | pairs asked | searched | records stored | failed |
|---|---|---|---|---|
| 1 (15:04 to 03:54) | 5,074 | 5,063 | 235,969 | 11 |
| 2 (03:54 to 03:55) | 11 | 11 | 73 | 0 |

236,042 records stored by this run; with the pilot's 100 pairs, searched on 2026-11-20 (5,076 records), the window
holds 241,118. The 11 failures were Europe PMC 500 and 503 responses in one half hour around 17:00; a failed
pair is rolled back and left unmarked, so the second pass found exactly those 11. Single requests that failed and
were retried by the client (up to five times) appear 99 times in the log and cost nothing. 3,016 pairs (58%) have at
least one record; the median over all pairs is 1 and the largest bundle is 31,193.

## Labelling (`label --pairs window`, Opus 5.5, prompt v2, web search and fetch)

Three invocations of `label`, three passes each (`LABEL_PASSES`); every pass asks again only for the pairs whose last
answer failed validation.

| pass | asked | validated | still undecided |
|---|---|---|---|
| 1 | 5,074 | 4,791 | 283 |
| 2 | 283 | 135 | 148 |
| 3 | 148 | 25 | 123 |
| 4 | 123 | 18 | 105 |
| 5 | 105 | 13 | 92 |
| 6 | 92 | 7 | 85 |
| 7 | 85 | 6 | 79 |
| 8 | 79 | 2 | 77 |
| 9 | 77 | 4 | 73 |

6,066 model calls: 5,001 validated, 950 refused by the API, 115 broke a rule (a cited record the model was not
shown, a year that is not a cited record's, a route quote without a route). Tokens: 34.7 million in (uncached),
331.9 million read from cache, 10.5 million out; 16,087 web searches and 4,789 fetches.

**Refusals.** A refusal is the API's `stop_reason: refusal`, the streaming safety classifier, not a rule break. On
pass 1 it hit 187 of 5,074 calls (3.7%); 176 of the 187 came after the model had begun its answer (one cut off
mid-sentence while reading CD19 expression on AML blasts). The refused inputs are bigger (median 4,251 input tokens
against 959 for validated calls) and carry more pathogen, toxin, vaccine, gene-therapy, radiation and infection
language in their abstracts (each two to four times as often as in validated inputs). They are not one disease or one
target: the 118 pairs still refused after pass 3 spanned more than a hundred targets, the largest groups CSF2 (7
pairs) and FKBP1A (5), and the diseases ran from acute myeloid leukemia (7) to hemophilia, ovarian cancer and malaria.
A refusal is partly random: of the 187 refused on pass 1, 48 passed on pass 2 and 22 of the rest on pass 3; later
passes recovered 18, 13, 7, 6, 2 and 4. The run was stopped at 73 after nine passes; three more passes on 2026-11-21
(the check v2 section) recovered 12 at the same rate, so 61 remain.

**The unlabelled pairs** (73 at this point, 61 after the passes of 2026-11-21; `target_origin_unlabelled.csv` lists
the 61: pair, symbol, disease, records stored, reason) have no row in `preclin.target_disease_origin`. They are
missing data, not `unclear`: an unclear origin is a finding about the record, an unlabelled pair is a pair the method
did not reach. Their record counts run from 0 to 558 (median 11). The in-method remedy is more passes, now at a few
pairs a pass (taken once more on 2026-11-21); the out-of-method remedy is another model for these pairs, recorded as
such (not taken; the owner's call).

## Check v1 (`check --pairs window`, Sonnet 5.5, prompt v3, search and fetch): superseded by check method v2 below

4,419 graded labels (87 reused from the pilot check); 4,335 calls, 4,332 validated, 3 asked again. The first
invocation died on an NCBI efetch outage before any decision (`RuntimeError: eutils efetch failed`) and the wrapper
re-invoked it after two minutes. Tokens: 4.2 million in, 65.5 million read from cache, 1.5 million out; 2,115 fetches.

| outcome | labels |
|---|---|
| supported | 3,519 |
| unsupported | 730 |
| unverified | 170 |

A label that is unsupported or unverified is stored as `unclear` with grade `none`.

## Stored result after check v1 (5,101 rows; superseded, the v2 table is in the last section)

| origin | label as read | stored after the check |
|---|---|---|
| animal_model_pharmacology | 944 | 797 |
| diseased_tissue | 925 | 850 |
| earlier_drug_other_disease | 727 | 361 |
| unclear | 682 | 1,582 |
| human_cell_perturbation | 482 | 425 |
| clinical_observation | 392 | 302 |
| observational_biomarker | 280 | 245 |
| mouse_genetics | 209 | 172 |
| human_genetics | 198 | 170 |
| tumour_genetics | 132 | 122 |
| phenotypic_screen | 113 | 66 |
| curated_pathway | 12 | 6 |
| cell_screen | 5 | 3 |

The 1,582 unclear rows are 682 the labeller left ungraded, 730 the checker rejected and 170 it could not verify.
Grades stored: stated 1,730, pattern 1,789, none 1,582. The check falls hardest on earlier_drug_other_disease (366 of
727 labels as read lost, 50%) and phenotypic_screen (47 of 113, 42%); diseased_tissue loses 75 of 925 (8%).

Discovery route of the first drug: derived_from_active 1,380, repurposed_drug 1,158, target_screen 669,
de_novo_design 228, phenotypic_screen 86, unclear 1,580.

The `summary` command's "tokens per decision" table counts reused decisions again on every run (they are copied as
rows with `prior_decision_id`), so its `n` overstates the calls; the call counts above are rows without a prior.

## Timeline

| step | from | to |
|---|---|---|
| search, pass 1 | 11-20 15:04 | 11-21 03:54 |
| search, pass 2 | 03:54 | 03:55 |
| label, passes 1 to 3 | 03:55 | 05:57 |
| check (first attempt died at 05:57; completed run) | 06:08 | 06:48 |
| summary | 06:48 | |
| label, passes 4 to 6; check; summary | 07:34 | 07:57 |
| label, passes 7 to 9; check; summary | 09:13 | 09:32 |

## Checker sensitivity: Opus 5.5 as a second checker (2026-11-21, 09:50 to 10:51)

Asked on the day the run finished: the checker (Sonnet 5.5) is a smaller model than the labeller (Opus 5.5), so
would an Opus checker verify differently? Measured rather than argued: every one of the 4,419 graded labels was
checked again by Opus 5.5 under the v3 prompt text, recorded as `target_origin_check` prompt version v4 (runs
ddc03aac, ac2d3948, 8e9f70c6, 2a997db7, 878feeb8), in the decision log only; `preclin.target_disease_origin` was not
touched. 4,402 labels were decided by both (Opus refused 17). `target_origin_check_opus.csv` carries both verdicts
per label; `target_origin_check_disagreements.md` shows twenty disagreements with the quote, the definition and both
checkers' notes, for a human read.

| | Opus supported | Opus unsupported | Opus unverified | all |
|---|---|---|---|---|
| Sonnet supported | 3,439 | 47 | 24 | 3,510 |
| Sonnet unsupported | 590 | 125 | 9 | 724 |
| Sonnet unverified | 150 | 12 | 6 | 168 |

κ between the checkers is 0.20 (0.21 on supported against the rest). Opus rejects 184 labels (4.2%), Sonnet 724
(16.4%); they agree on 125 rejections. Under Opus the stored table would hold 223 unclear graded rows instead of 892.

**Where the disagreement sits.** Of the 590 labels Sonnet rejected and Opus supported, Opus scored the category
"partly" on 529 and "yes" on 61; 455 of the 590 are labels Sonnet rejected on the category alone. Read side by side,
the two checkers describe the same facts (the quoted pre-cutoff source shows the drug in use in the same disease and
does not show an earlier approval for an unrelated disease) and set the threshold differently: Sonnet says the
category does not follow, Opus says "partly" and supplies the missing step from its own knowledge ("already approved
for renal cancer", "an existing approved drug repurposed"). The prompt defines "partly" as support only together with
the other sources, or support for a neighbouring category as well; a link the record does not contain is not in that
definition, so on the rule as written Sonnet applied it and Opus was lenient. The leniency is largest where the
labeller over-calls most: earlier_drug_other_disease keeps 663 of 726 labels under Opus against 361 under Sonnet,
phenotypic_screen 105 of 111 against 65. An Opus checker shares the Opus labeller's reading; that is the case for a
second model, in numbers.

**Where Sonnet is weak: the year field.** Opus supported 71 of the 87 labels Sonnet rejected on the year alone, and
38 of Sonnet's 116 year-based rejections carry a note that says the year is fine while the field says no. Those are
checker errors, about 2% of the stored labels. A later prompt version can take the year out of the model's hands:
ask for the year it read for each web source and compute `year_ok` in code.

**The other side.** Opus rejects 47 labels Sonnet supported: 29 on the category, 10 on the year, 7 on the quote, 1 on
both quote and category (13 animal_model_pharmacology, 7 diseased_tissue, 7 earlier_drug_other_disease). Opus marks
"partly" on 61% of the labels it supports, Sonnet on 53%.

Stored origin under each checker, over the 4,402 labels both decided (the 682 the labeller left ungraded are unclear
under both):

| origin | label as read | Sonnet (stored) | Opus |
|---|---|---|---|
| animal_model_pharmacology | 935 | 793 | 884 |
| diseased_tissue | 925 | 850 | 901 |
| earlier_drug_other_disease | 726 | 361 | 663 |
| human_cell_perturbation | 481 | 424 | 464 |
| clinical_observation | 392 | 302 | 370 |
| observational_biomarker | 279 | 244 | 267 |
| mouse_genetics | 206 | 170 | 189 |
| human_genetics | 198 | 170 | 196 |
| tumour_genetics | 132 | 122 | 126 |
| phenotypic_screen | 111 | 65 | 105 |
| curated_pathway | 12 | 6 | 10 |
| cell_screen | 5 | 3 | 4 |
| unclear (graded rows) | 0 | 892 | 223 |

**Status.** Written at 11:00 with the stored table on the Sonnet verdicts. Superseded the same afternoon by check
method v2 (next section): the disagreement was scored against the dated approval index, which showed each checker
wrong in its own direction on the earlier-drug category, and the stored table now follows neither checker alone.

## Check method v2: facts in code, judgment by agreement (2026-11-21, 14:11 to 16:08)

Posted on #146 at 14:08, before any row was rewritten; migration `db/148_target_disease_origin_check_v2.sql` adds
the outcome `disputed` and the column `check_fields`.

**Why.** The earlier-drug category's defining fact, a drug on the target approved before entry, is a dated fact in the
database: `report.section3.Evidence` indexes Drugs@FDA approvals by target gene for the chart's precedent lines.
Scored against it, the 727 earlier-drug labels as read split 408 (approved for an unrelated disease, which is the
definition), 301 (approved for a related disease, Lin at least 0.5, the chart's rule) and 18 (no approval on the
target before entry in the index). The v1 checker kept 219 of the 408 confirmed labels, rejected 168 (154 on the
category alone, for the cited paper not restating the approval) and left 21 unverified; it kept 134 of the 301 related
ones and 8 of the 18 unconfirmed (219 + 134 + 8 is its stored 361). Opus rejected 27 of the 408 and 25 of the 301 and
passed all 18 it cannot confirm, among them roxadustat for myelodysplastic syndrome, approved nowhere before entry,
which its own note says. The v1 check asked a literature record for a database fact, and each model failed it in its
own direction. Separately, Sonnet's year field contradicts its own note on 38 of its 116 year-based rejections.
Neither defect is model strength; both are the design asking a model for what the data or the code already hold.

**The rule** (`check_fields`, `check_outcome_v2`; `CHECK_DESCRIPTION` has it in full). Three fields per graded label.
quote: the two checkers' answers where they agree; could_not_open carries no information. year: no when a cited record
is dated in or after the cutoff year; yes when every source is a record; otherwise the two answers where they agree,
unknown carrying no information. category: for earlier_drug_other_disease the approval fact on the pair's gene (unrelated
yes; close no, an approval within Lin 0.8 of the disease before entry being the hub's validated_at_entry rule; related
no, an approval within Lin 0.5, the chart's b1 line, excluding the approved_unrelated_only tier that the owner's
one-list decision makes the definition, until the owner decides the band; none disputed), for every other origin the two
answers where they agree, partly counting as yes. A field the two disagree on, or that one of them did not answer, is
disputed until a human verdict from `target_origin_disputes.csv` settles it: `check` reads the sheet (`--disputes
PATH`, default that file) and rewrites it with the open rows. A verdict is `yes` (the field holds) or `no`; any other
value stops the run; a verdict applies only where the checkers left the field disputed. Outcome: unsupported if a
field is no, else disputed if one is disputed, else unverified if one is unverified, else supported. A row that is not
supported holds unclear with grade none; `check_fields` records the fields, the fact, both decision ids and the
verdicts applied. The sheet lists only labels whose outcome a verdict can change.

**The run.** `label --pairs window` first, to restore every row to the label as read: 5,101 decisions reused, the 73
refused pairs asked three more times (201 calls, 12 validated, 189 refused), so 5,113 pairs are labelled and 61 are
not (`target_origin_unlabelled.csv` is now the 61). Then `check --pairs window`: Sonnet v3 reused 4,419 decisions
and decided the 12 new labels (12 calls); Opus v4 reused 4,402 and was asked again for the labels it had refused and
the 12 new ones (78 calls over the day's three check passes, 24 validated, 54 refused; 5 labels still have one
checker only and are disputed on that account). No other model calls; the fields are computed from the stored
decisions. Three passes because the second exposed a gap: `check` read only rows still graded, so after the first
pass it saw the 3,649 supported rows and wrote the disputes sheet empty (the table was untouched). It now reads every
label graded as read from its decision and restores a supported row, so it reruns on its own to apply verdicts; the
third pass (15:49 to 16:08) reused all 4,431 stored decisions and wrote the sheet in full. A fourth pass (19:22 to
19:40), after the correction of the approval fact below, reused every decision and re-asked Opus the 5 refused labels
three times (15 calls, all refused).

| outcome | labels (of 4,431 graded) |
|---|---|
| supported | 3,687 |
| unsupported | 344: 88 close and 164 related on the approval fact, and 92 on a field both checkers, or the code, answered no |
| disputed | 394 |
| unverified | 6 |

Disputes sheet: 442 rows over the 394 disputed labels (category 291, year 87, quote 64; 32 of the category rows are
the approval fact none). On the category rows Sonnet says no and Opus partly on 231: the same threshold the previous
section describes, now on a person's desk rather than either model's.

Outcome by origin as read (the 4,431 graded labels; the share is disputed over as read):

| origin as read | labels | supported | unsupported | disputed | unverified | disputed share |
|---|---|---|---|---|---|---|
| animal_model_pharmacology | 949 | 833 | 30 | 85 | 1 | 9% |
| diseased_tissue | 927 | 870 | 9 | 46 | 2 | 5% |
| earlier_drug_other_disease | 727 | 421 | 255 | 49 | 2 | 7% |
| human_cell_perturbation | 486 | 439 | 12 | 35 | 0 | 7% |
| clinical_observation | 393 | 322 | 14 | 56 | 1 | 14% |
| observational_biomarker | 280 | 252 | 6 | 22 | 0 | 8% |
| mouse_genetics | 209 | 176 | 7 | 26 | 0 | 12% |
| human_genetics | 198 | 175 | 1 | 22 | 0 | 11% |
| tumour_genetics | 132 | 120 | 4 | 8 | 0 | 6% |
| phenotypic_screen | 113 | 69 | 3 | 41 | 0 | 36% |
| curated_pathway | 12 | 6 | 2 | 4 | 0 | 33% |
| cell_screen | 5 | 4 | 1 | 0 | 0 | 0% |

The dispute rate is 9% overall and falls unevenly: 36% of phenotypic_screen labels as read and 14% of
clinical_observation, against 5 to 12% in the other categories with more than a dozen labels. Every dispute holds
unclear, so the stored table under-counts those categories until the sheet is read; a verdict can only move a row out
of unclear, and 357 of the 394 disputed labels have one disputed field with the other two yes. The 92 unsupported
labels outside the close and related facts failed on the category (64), the year (25) or the quote (5); two on two
fields. The 6 unverified are 5 whose cited source neither checker could open and 1 whose web source neither could
date.

Stored origin after v2 (5,113 labelled rows), beside v1:

| origin | v1 (Sonnet alone) | v2, after the evening's correction |
|---|---|---|
| unclear | 1,582 | 1,426 (682 ungraded, 344 unsupported, 394 disputed, 6 unverified) |
| diseased_tissue | 850 | 870 |
| animal_model_pharmacology | 797 | 833 |
| human_cell_perturbation | 425 | 439 |
| earlier_drug_other_disease | 361 | 421 |
| clinical_observation | 302 | 322 |
| observational_biomarker | 245 | 252 |
| human_genetics | 170 | 175 |
| mouse_genetics | 172 | 176 |
| tumour_genetics | 122 | 120 |
| phenotypic_screen | 66 | 69 |
| curated_pathway | 6 | 6 |
| cell_screen | 3 | 4 |

**The approval fact, corrected (2026-11-21 evening, announced on #146 before the rerun).** The afternoon's fact was
computed on the first drug's primary targets; the design note said "a drug on the target", and for 457 of the 727
earlier-drug labels the first drug has more than one, so 57 facts came from another target. The fact is now on the
pair's gene, with four values: close (an approval within Lin 0.8 of the disease before entry, the hub's
`validated_at_entry` rule of migration 142), related (within Lin 0.5, the chart's b1 line), unrelated, none. The 727
labels as read split close 88, related 164, unrelated 443, none 32; against the afternoon's entity-level fact, 88 of
the 301 "related" were close, 43 unrelated and 6 none, and 8 of the 408 "unrelated" were none.

"Related" has two thresholds in this repository and the documents of the afternoon used one name for both. The
chart's rule is Lin 0.5 (`report.section3.RELATED`, the b1 line, the threshold inside the approved_unrelated_only tier
the one-list decision defines the category by); the hub's `validated_at_entry` is Lin 0.8 (migration 142). The owner's
one-list comment and the header comment of migration 145 name the hub flag for the related-disease case. The stored
fact keeps both: close is not an origin by the registered definition; whether the related band (164 labels) counts as
earlier_drug_other_disease is put to the owner on #146 with a recommendation (count it, tier recorded, test with and
without), and until then it holds unclear with the fact recorded. Either answer is a rewrite from the stored
decisions.

**The hub's flag misses most validated-at-entry pairs (the owner's code).** `pipeline.target_disease.approvals()`
keeps approvals with an exact date (1,804 programs) and drops the 2,012 whose approval predates the FDA letters
(`date_basis = before_letters`), the oldest drugs and the likeliest validating precedents. The chart dates those at the
entity's first FDA approval (`report.section1.approval_dates`). By the chart's index 294 window pairs have an approval
within Lin 0.8 before entry; the hub flags 83, all of them among the 294. The 211 it misses are in the test frame (108
unclear, 36 clinical_observation, 24 animal_model_pharmacology, 10 observational_biomarker, 9 human_genetics, 8
phenotypic_screen, 6 diseased_tissue, 5 human_cell_perturbation, 3 mouse_genetics, 2 tumour_genetics as stored); six
of the 100 pilot pairs are among the 294 (five in set a, one in set b; the pilot's cohort frame of 5,091 was drawn
with the hub's 83). The one-line fix is to date approvals with `report.section1.approval_dates` in `approvals()` and
rebuild the hub; it is the owner's call because it changes step 6's frame, and it is not made here. The check's
`close` value is computed from the chart's index, so the stored table already carries the right set.

Discovery route is unchanged but for the 12 new labels (unclear 1,583, derived_from_active 1,385, repurposed_drug
1,159, target_screen 670, de_novo_design 230, phenotypic_screen 86).

**Gates, rerun on the v2 table.** Set a: kappa 0.69 on the label as read (stored 0.52), coverage gap 8.0 points,
passed. Set b: 0.65 (stored 0.55), gap 8.0, passed. The gate is scored on the label as read, which v2 does not
touch; the stored kappas are reported beside it as before.

**What this leaves.** The disputes read: the research pass (next section) settles 162 of the 183 factual rows into a
file the owner can apply, and the 259 threshold rows and the 21 open rows are a person's, by default hers (the #146
note offers the sheet back); every verdict moves one row out of unclear, and unread rows stay unclear with the count
reported. Also for step 6: the coverage split by
group over the whole window is not computed (the gate scored it on the pilot's settled-stop frame), and the 61
unlabelled pairs are absent from the table. The residual the check cannot remove: two capable models disagree on at
least one field for 359 of 4,431 graded labels (on the category for 254); the rest of the 394 disputed labels are the
32 the approval index is silent on and the 5 one checker refused. The audit reports that rate rather than present the
check as exact.

## Research pass on the factual disputes (2026-11-21 evening; proposed on #146 at 21:08, run from 21:31)

**Why.** The disputes sheet's 442 rows are two kinds of question. The 259 category rows with a fact other than none
are a threshold question (231 of them Sonnet "no" against Opus "partly" on the same passage) that more reading does
not change. The other 183 are facts one checker could not read: year 87, quote 64, and the 32 category rows of
earlier-drug labels the Drugs@FDA index is silent on. Reading the 183 notes before the pass: of the 87 year rows, in
41 Sonnet's note says every date is before the cutoff and its field says no (25 by a text rule over the notes, 16 more
on reading the other 19; the slip the checker sensitivity section reports for v1), 25 are a source Sonnet did not open
and Opus dated, and 13 are a date Opus read at or after the cutoff; of the 64 quote rows, 43 are a source Sonnet did
not open and Opus found the passage in, often in another copy, and 9 are a passage Opus traced to a paper the label
does not cite; 10 rows are the 5 labels Opus refused. So for 151 rows the task is to fetch a named source and confirm
a date or a passage, and the 32 index-silent rows are the one open question.

**The method** (`research`, `RESEARCH_TASK`, `RESEARCH_DESCRIPTION`; method `target_origin_research@v1`). One model
reading per row: Opus 5.5, prompt v1, web search (10 uses) and fetch (6), effort medium, through `pipeline.llm`, so
every decision is logged with its request and the URLs it retrieved. The model is shown what the checkers were shown
(the label, its quote and sources, the cited records in full) and the question; never the checkers' answers or notes.
Nothing from memory counts: each answer names the page it rests on and copies the words or dates read. Three
questions. Quote: is the passage, or the sentence it closely paraphrases, in a copy of a cited document (the journal,
PubMed Central, Europe PMC, a patent host or the Internet Archive when the cited page will not load); a passage found
only in an uncited paper is no; no copy readable is open. Year: the publication year of every cited source on its
publisher's record, the issue year for a journal article, as PubMed dates the index (ruling: the index's own basis,
so a paper online in the year before its issue is dated by the issue); an earlier online-first year is recorded beside
it and the note says when that basis would flip the verdict, which the code never applies. The verdict is compared in
code: yes when every year is before the cutoff, no when any is in or after it, open when any is unread. Approval: was
any drug the hub lists on the gene approved by any medicines regulator before the entry date, and for what; the
model gives each approval with its regulator, date, indication and the indication's MONDO id, and the code places the
indication by the index's own rule (close within Lin 0.8 of the pair's disease, related within 0.5, else unrelated)
and takes the verdict from `FACT_CATEGORY` of the tier, so the owner's decision on the related band propagates to
these rows on a rerun. Ruling: no approval found, or none before entry, is no (the category's defining claim has no
documented basis; the stored row is unclear either way); an approval in the entry year without a day, or an
indication the ontology does not know, leaves the row open unless a close approval is documented. The output is a
filled copy of the sheet, `target_origin_disputes_research.csv`, reader `target_origin_research@v1`, the evidence in
`note`, the decision id beside it; the committed sheet and the origin table are untouched, and
`check --pairs window --disputes report/audits/target_origin_disputes_research.csv` applies it. A three-row smoke run
(retracted, run cafbe58a: it predated the commit of the code) checked the prompt; the pass ran under commit 5b40d0c.

**Caveats.** Opus 5.5 is one of the two checkers, so agreement with it is not independent evidence; what makes a row
checkable is the evidence URL and the copied words, which a reader can open. The 32 index-silent rows are settled on
approvals by any regulator, a wider index than the Drugs@FDA fact that settled the other 695 earlier-drug labels; the
sheet records the regulator per row. Where a cited page would not load and the model read the passage from a search
result's page content rather than a fetch, the note says so: 55 rows, 45 of them decided.

**The run.** 21:20 to 21:35 Pacific (183 calls, 24 concurrent), then 21:41 to 21:43 for four rows and a recompute at
21:49 with no call: 198 calls in all, 183 validated. 14 answers were rejected by the validator for an approval date
with a month and no day (ibudilast 1989-01, S-1 1999-01), the four rows they belonged to never validating in three
passes; the validator was widened to month precision, test first, in commit 53a41f1 (the entry's own month, like its
own year, cannot say and leaves the row open), and the four were asked again. One refusal, answered on the next pass.
Commit 631cd7d placed an indication given without its MONDO id by its exact label (gastric cancer, subarachnoid
hemorrhage). Tokens: 184k input, 11.5M read from cache, 330k output; 438 searches, 570 fetches; about $10 of tokens at
the list price. `research` reruns from the decision log with no call.

| question | rows | yes | no | open | as Opus read it | as Sonnet read it |
|---|---|---|---|---|---|---|
| quote | 64 | 48 | 7 | 9 | 47 of 55 | 8 of 55 |
| year | 87 | 72 | 12 | 3 | 77 of 84 | 7 of 84 |
| approval | 32 | 12 | 11 | 9 | 9 of 23 | 14 of 23 |
| all | 183 | 132 | 30 | 21 | | |

By the buckets read before the pass: of the 25 year rows where Sonnet's note said the dates pass, 25 read yes; of the
25 where Sonnet had not opened a source, 25 yes; of the 13 where Opus read a date at or after the cutoff, 11 no, 1
yes, 1 open; of the 19 others, 16 yes, 1 no, 2 open; the 5 Opus refused, 5 yes. Of the 43 quote rows Sonnet had not
opened, 36 yes, 2 no, 5 open; of the 9 Opus traced to an uncited paper, 5 no, 1 yes, 3 open; the 5 refused, 5 yes; the
6 others, 5 yes, 1 open. Agreement is with the checker who had read the source: 47 of 55 decided quote rows and 77 of
84 year rows read as Opus did, 8 and 7 as Sonnet did. On the approval rows the checkers' category answers are not the
method (the fact is), and the pass disagrees with both on 7: 3 yes where both read no, amifampridine's EU approval for
Lambert-Eaton myasthenic syndrome (2009-12-23) on KCNA3, KCNA4 and KCNA5 with congenital myasthenic syndrome, at Lin
0.26 unrelated by the index's rule, where the checkers had judged the quoted passage, a 3,4-diaminopyridine trial in
congenital myasthenia itself; 4 no where both read partly, avadomide and golcadomide on IKZF1 and IKZF3 and resiquimod
on TLR8, no approval anywhere before entry.

**The 12 year rows read no.** Each has a source dated in the cutoff year or after by its publisher's record: a 2016
letter the labeller dated 2009 (IGHE), a 2008 reprint cited for a 1985 paper (TNF), an AES abstract of 2018 (CACNA1I),
a patent published 2019-01-03 (TACR1), a vendor page with no date of its own (HDAC2, open), an article in the cutoff
year's issue. Six are online in the year before their issue and would read yes on that basis, which the note flags:
IL4R, TLR8, IL1A, MTNR1B, SEMA4D, and CLCN2, a Canadian patent granted in 2011 whose application was published in
1999. **The 7 quote rows read no** trace the passage to a paper the label does not cite (a different Metabolism paper
for DRD2, Kleiman 2012 for PDE9A, a later citing paper for CHRM3, a different formalin-test study for PDE5A, Hoberman
1997 for SCN5A) or find it absent from the cited document (CHRM4, TLR7).

**The 32 approval rows.** 12 yes, each an approval the Drugs@FDA index does not carry, for a disease unrelated to the
pair's by the index's rule: amifampridine (EMA 2009-12-23, Lambert-Eaton myasthenic syndrome) on the five KCNA3,
KCNA4, KCNA5 and KCNA6 pairs with congenital myasthenic syndrome or myasthenia gravis (Lin 0.26 and 0.19);
levosimendan (Sweden 2000, heart failure) on TNNC1 with amyotrophic lateral sclerosis and with pulmonary hypertension
(0.07, 0.40); ibudilast (Japan 1989-01, asthma) on PDE10A with secondary progressive multiple sclerosis;
thrombomodulin alfa (Japan 2008-01-25, disseminated intravascular coagulation) on THBD with idiopathic pulmonary
fibrosis; oteracil in S-1 (Japan 1999, gastric cancer) on UMPS with cervical cancer (0.41); ozagrel (Japan 1988-01-20,
subarachnoid hemorrhage, placed by its label) on TBXAS1 with dry eye; and Refnot, a TNF-thymosin fusion (Russia
2009-03-27, breast cancer) on TNFRSF1A with glioma (0.37), the row that shows how wide "any regulator" reaches. 11 no:
9 with no approval anywhere before entry (CD22's suciraslimab, epratuzumab and inotuzumab; mitoglitazone; resiquimod;
avadomide and golcadomide on four pairs; nadofaragene firadenovec; roxadustat) and 2 close, validated at entry by the
registered rule and missed by the index: ivabradine on HCN4 with heart failure (EMA 2012, a variation to an EU
authorisation, heart failure itself) and anti-D immunoglobulin on RHD with immune thrombocytopenic purpura (WinRho
SDF, FDA 1995, the disease itself; a CBER biologic, outside Drugs@FDA). 9 open, the approval documented in the note
and its indication not placed: fasudil (Japan 1995, cerebral vasospasm), pipamperone (Switzerland 1964, indication not
stated), sulodexide (Italy 1972, chronic venous ulcers), dibotermin alfa (EMA 2002, acute tibia fractures as an
adjunct, which is not the ontology's "tibia fracture" label), clodronic acid (Ireland 1992, not stated on the
licence), gimeracil (Japan 2004-12, non-small cell lung cancer, which the ontology labels carcinoma), catumaxomab (EMA
2009, malignant ascites), perhexiline (Australia 1995, angina pectoris, a label the hub's ontology table lacks), and
ibudilast on PDE10A with amyotrophic lateral sclerosis, where this row's call found the 2001 revaluation and not the
1989 asthma approval the other PDE10A row found: the calls are per row and do not share findings, and a reader can
carry it over.

**If applied** (`check --pairs window --disputes report/audits/target_origin_disputes_research.csv`, computed from the
stored `check_fields` without a write): of the 394 disputed labels, 91 become supported (as read:
earlier_drug_other_disease 21, animal_model_pharmacology 18, human_cell_perturbation 17, diseased_tissue 10,
clinical_observation 9, mouse_genetics 6, human_genetics 6, observational_biomarker 3, tumour_genetics 1), 29
unsupported (earlier_drug_other_disease 18, animal_model_pharmacology 6, observational_biomarker 2, human_genetics 1,
phenotypic_screen 1, diseased_tissue 1), 274 stay disputed: the 247 whose only open field is a threshold row, and 27
with a verdict on one field and the category still disputed. 147 labels carry at least one verdict. Not applied here:
the sheet is the owner's by default, and the note on #146 puts the file to her.

## Consolidation (2026-11-22)

No model call. Code `pipeline.target_origin` and `pipeline.target_disease` at this branch's commits; migration
`db/151_target_disease_origin_stored_values.sql`.

**The hub's approval fact.** `pipeline.target_disease` reads approvals from `report.section3.Evidence`, the index the
evidence chart and the check already read, through `target_origin.approval_fact` (method `target_disease@v2`,
`target_disease_provisional@v2`). The hub's own reader dropped approvals with no exact date (`before_letters`), so
`validated_at_entry` went from 212 to 834 pairs (83 to 295 in the window; the 294 of the last section plus one); no
pair was added, removed or re-dated, and no flag was lost. The provisional origins were rewritten from the same index:
earlier_drug_other_disease 5,210, unclear 4,142, mouse_genetics 831, diseased_tissue 383, human_genetics 369,
tumour_genetics 350, curated_pathway 24, cell_line_perturbation 2.

**Stored values.** Migration 151 adds `disputed` and `not_reached` to the origin. A label the two checkers dispute is
stored as `disputed`, no longer as `unclear`, which now means only that no source settles the origin or that the
check rejected the label. A pair the labelling never answered has a `not_reached` row (`target_origin_unlabelled.csv`
lists the same 61).

**Restore** (`python -m pipeline.target_disease restore --pairs window --disputes
report/audits/target_origin_disputes_research.csv`, method `target_origin_restore@v1`). Each graded label's outcome is
recomputed by check method v2's rule from the checker decisions its row already cites, with the related-disease band
counting and the research pass's verdicts applied; label decisions that name `cell_screen` are read as
`cell_line_perturbation` (4). Against the stored table before it: supported 3,687 to 3,931 (153 related-band labels
from unsupported, 91 settled by the research pass from disputed), disputed 394 to 278 (29 settled no, 4 newly
disputed once the related band no longer failed the category), unsupported 344 to 216, unverified 6. No supported
label changed.

| origin, stored | before | after |
|---|---|---|
| unclear | 1,426 | 904 |
| diseased_tissue | 870 | 880 |
| animal_model_pharmacology | 833 | 851 |
| earlier_drug_other_disease | 421 | 595 |
| human_cell_perturbation | 439 | 456 |
| clinical_observation | 322 | 331 |
| disputed | | 278 |
| observational_biomarker | 252 | 255 |
| mouse_genetics | 176 | 182 |
| human_genetics | 175 | 181 |
| tumour_genetics | 120 | 121 |
| phenotypic_screen | 69 | 69 |
| not_reached | | 61 |
| curated_pathway | 6 | 6 |
| cell_line_perturbation | 4 | 4 |

Open: the 278 disputed labels (267 on the category, mostly the Sonnet-no against Opus-partly threshold), the relabel of
the pairs the final list's definitions can move (row 8 primary cells, genetic disease models), and the approval fact
as a stored fact on its subject (spec step 2).

## Reread (2026-11-22, later)

`python -m pipeline.target_disease reread --pairs window` (method `target_origin_reread@v1`, task
`target_origin_reread` v1, Sonnet 5.5, effort low, no tools): one reading per question of a stored graded label, from
its quote and its cited stored records only. 1,702 questions, 1,701 answered, 1 unanswered after three passes.

- **Category of the disputed labels** (267, the owner's rule of 2026-11-22: the defining observation must be in a
  cited source or a stored fact; a step a model supplies from its own knowledge does not count): no 226, yes 41. The
  answers are the category verdicts in `target_origin_verdicts.csv`, beside the research pass's.
- **Human-cell labels as read** (486): established cell line 202, primary cells or tissue 151, unclear 132. A cell
  line moves the label to cell_line_perturbation.
- **Animal-pharmacology labels as read** (949): non-genetic 842, unclear 91, genetic 16. A genetic change moves the
  label to mouse_genetics.

A moved label's category is the reread's (the checkers judged the origin as read); its quote and year fields stay the
checkers'. Then `restore --pairs window --disputes report/audits/target_origin_verdicts.csv`. Against the
consolidation: supported 3,931 to 3,972, disputed 278 to 15, unsupported 216 to 438, unclear 904 to 1,126. All 218
moved labels are supported.
