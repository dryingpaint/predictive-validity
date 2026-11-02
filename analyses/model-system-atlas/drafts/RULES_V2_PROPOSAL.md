# Rules v2 proposal for the model-system atlas (issue #76, "agree the track-record rules")

Drafted 2026-11-02 from the 70-context run (drafter + checker agents under `DRAFTER_BRIEF.md` v2 and
`CHECKER_BRIEF.md`). The 151 rule questions in `RULE_QUESTIONS.md` collapse into the fourteen
decisions below. Each gives the rule I recommend, the questions it settles, and what it moves in the
current drafts (numbers from `matrix.py` over the finished run: 71 contexts, 284 cells, 166 of them scored
`same`/`contra`/`neg`). Nothing here is applied yet; the
drafts record the facts needed to re-score under either answer.

The one-line version: **keep the five statuses, loosen rule 1 to admit juxtaposition and more source
types, define the four cells sharply, make `contra` per model and per time point, and add six fields
so the figure can show what the colours now hide.**

## 1. A comparison may be stated by the source or made by the drafter

**Rule.** A cell may be scored from (a) a primary source that itself states the model-vs-patient
comparison, or (b) one primary model source and one primary patient source that the drafter pairs.
`comparison_stated` records which. A trial paper whose introduction restates the preclinical premise
and whose results report the readout is (a) only if it draws the comparison in its own words; a bare
citation of the model paper is (b).

**Why.** Read strictly, rule 1 greys 79 of the 166 scored cells and both of Melissa's seed contexts (cf-cftr pairs Van Goor 2009 with Ramsey 2011;
ad-amyloid pairs Irizarry 1997 with Doody 2013). Panel C of `summary.png` shows juxtaposed cells
land on `same`/`contra` at rates similar to stated ones for engagement and efficacy, so the tier is a
provenance mark, not a different answer.

**Settles** #1, #14b, #29, #65, #75, #88, #111, #113. The figure should hatch or outline (b) cells.

## 2. Source tiers, in order

**Rule.** Admissible, from strongest to weakest, with `source_tier` recorded:
1. peer-reviewed paper with a DOI or PMID (a PMID-only supplement counts; #60);
2. regulator documents: FDA review/label/SBRA, FDA AdCom briefing document or transcript, EMA EPAR
   / CHMP assessment, Health Canada SBD/PM (#19, #37, #117, #120). An EPAR carries its CHMP-opinion
   year, not the consolidated-document year;
3. registry results record (ClinicalTrials.gov, EU-CTR) with posted outcome data (#9, #44);
4. meta-analysis of patient RCTs, for the patient side only (#67);
5. sponsor press release or SEC filing, for the patient side only, never for the model side, and
   only when no tier 1–4 record exists (#92, #94, #114). Such a cell carries `trial_unreported: true`
   so its colour is visibly provisional.

A quote whose model side is "data not shown" or whose clinical side is conference-only scores with
`confidence: low` (#36, #38). An OCR-read quote from a scanned FDA review must attach the transcript
line (#102). A registry protocol narrative with no results is a sponsor statement, not a source
(#125); an author-withdrawn retraction is still inadmissible, flagged `retracted` (#126).

**Why.** Without tier 5 the atlas shows green for trabodenoson (Phase 3 missed at every time point,
unpublished), LX1033 (until 2017) and the two CERC-301 trials. Without tier 2's EMA entries, every
EU-first product loses its filed-model and safety-prediction facts.

## 3. Who counts as "patients"

**Rule.** Engagement and dose accept healthy-volunteer PD/PK/occupancy studies (`subjects` records
it). Efficacy requires patients of the context's disease. Safety accepts either. Biomarker-unselected
trials count for a biomarker-labelled context when the biomarker's prevalence in the trial
population is ≥ 80 % (#43). A human physiology study of the endogenous ligand before any drug exists
is not a comparison for the class (#85).

**Impact.** 11 scored cells rest on healthy volunteers (8 engagement); under the stricter reading
they fall to `untested`. Settles #14a, #31 (first published comparison regardless of design, design
recorded), #84, #88.

## 4. The four cells, defined

| cell | question the cell answers | not this cell |
|---|---|---|
| engagement | did the **PD readout** the model used move in humans (occupancy, biomarker, sweat chloride)? | genotype-stratified response (efficacy, #20); target binding without a readout; the drug working by another mechanism is noted, not scored (#28) |
| dose | was the model's exposure / occupancy / regimen target **reached** in humans (#2, #93, #123)? A regimen prediction (half-life → once daily) counts (#91). An FDA NOAEL-margin statement, a post-hoc PK/PD justification, or a regulator's bridge it calls non-translatable is `untested` with `source_calls_it: scaling` (#50, #99, #118). Toxicity-blocked targets are `untested` (#22). Gene therapy: expression per vector dose, not specific activity (#107) | engaged-but-inert belongs to efficacy |
| efficacy | did the **trial's primary endpoint** respond as predicted (#64)? When the sponsor pre-specified a secondary as the proof-of-concept gate that translates the model's readout (TPV for "involution"), that endpoint governs, with `endpoint_role: poc_gate` (#144). Missed primary + significant secondary is `untested` unless the source's own conclusion calls it a match (#32). A trial the authors disclaim as an efficacy test (#57) and an active-comparator ranking failure (#80) are `untested`. "Failed" = the predicted effect was absent or reversed, not that development stopped (#53) | surrogate-vs-outcome: see decision 9 |
| safety | did the model's **stated prediction** hold, or was its **askable silence** contradicted (#13, #54, #89)? Silence is `contra` only if the harm was measurable in the model species at the time. A sponsor-dismissed animal signal that patients confirmed is `same` (#23). A regulator's retrospective reconciliation counts as stated (#79). A pre-signal finding in another frame is `untested` with a note (#87) | mechanism-attribution sentences that name no species or study (#111) |

**Also:** `contra` requires the model's own prediction to have failed; a failure the source attributes
to conditions the model never tested is `untested` (#35, #72). A weak animal signal the source claims
as a negative prediction is `contra` when patients show the effect (#10). A model that cannot detect
a drug later proven effective is `contra` only if the class relied on that model (#73). Null-null
(no effect in model, no effect in patients) is `same` only when the model made the null a prediction
(#58). An unnamed "non-clinical safety concern" is `untested` (#59). A label §8.1 class warning with
no human case is not a comparison (#61). "Tested, could not resolve" is `untested` with
`source_calls_it: unresolved` (#90).

## 5. Animals that predicted harm that did not occur

**Rule.** `contra`, dated to the first patient dataset that could have shown the harm, with
`magnitude: opposite`. A conservative model is still a wrong model for the atlas's question. The
GERD/P-CAB case (rodent ECL carcinoids, "a rodent-specific phenomenon" in the label) and
telaprevir's rat testicular toxicity are the canonical examples (#26). An unattributed signal
("risk cannot be excluded") is `untested` (#41). A 25–50× margin below clinical exposure does not gate
`same`; record it in `magnitude` (#51). A human null can contradict a lifetime rodent carcinogenicity
prediction only when the regulator calls the finding species-specific or the human dataset is
powered for the predicted incidence (#130).

Over-predicted liability (dog heart-rate effect below the clinical dose, ~1 bpm in humans) is the
same family: `same` + `magnitude: off_by_>5x`, `direction: conservative` (#142).

**Alternative if Melissa prefers.** Score these `same` with `source_calls_it: over_predicted`; the
difference is ~6 safety cells.

## 6. `contra` is per model and per time point

**Rule.** `contra` overrides matched statuses **for the model that made the wrong prediction**. A
later entry may move the cell back to `same` when (a) a different best model took over and its
prediction held (entry carries `model_change: true`; #12, #52, #83), or (b) a primary source reports
that the contradiction attenuated (#27, #66, #96). Without such a source the strip stays red. One
drug's `contra` overrides another drug's `same` in the same class and model (#3).

**Impact.** Haemophilia B, NSCLC/EGFR dose, GBM, AML, FL, CRC and the HF renal cell all currently
show a recovery; under "sticky `contra`" they stay red from the first miss.

## 7. Dating

**Rule.** An entry's `year` is the earliest of: registry results-posted year, epub year, print year,
or the year of the earliest admissible source that makes the comparison, label included (#8, #9,
#81, #129, #131). All three are recorded, so the strip can be redrawn under any convention. A model
introduced mid-cell opens at its first class use, proxy allowed (#112). Same-year collisions get the
model entry first (#30). A new entry is written only on a status change or a best-model change;
trial facts that change nothing go in `patient_trials` (#113), except a second miss that removes the
first miss's excuse, which may be entered with `strengthens: true` (#127).

**Impact.** 25 of the 74 entries with a registry date have a registry year earlier than the entry's
print year; 40 of 323 entries have an epub year before print. The RA/BTK efficacy strip reverses
order under registry dating.

## 8. What "the model" is

**Rule.** The model is the system the class actually relied on for that question (pivotal papers,
filed package). Proxies are allowed with `product_in_model: false` (#16, #34; 14 scored cells rest
on them, 8 `same`, 6 `contra`). When sponsors relied on different models, the entry names the one the
scored drug relied on and the other goes in the note (#39, #68, #98). A class that entered with no
indication-specific model opens on the filed cross-indication model, `model_kind: cross_indication`
(#18, #47, #86). A retracted model paper keeps its `model_first_use_year`; add `retracted: true`
(#74). Human systems the class relied on in place of animals (allergen chamber, UVB evoked pain,
patient ex-vivo cells, in-silico QST, human genetic models) are in scope with `model_kind` set
(#82, #100, #122, #56). `model_filed` is per model, not per context (#108).

**Empty vs `untested`.** An empty cell means no model of any kind was relied on; `untested` means a
model exists and was never compared (#6, #7, #42, #121). The figure draws empty cells in a lighter
grey. Six cells are empty today (3 dose, 3 safety).

## 9. Surrogate matched, outcome failed

**Rule.** Add `outcome_tested` to the efficacy cell: `null` (no hard-endpoint trial), `positive`,
`negative`, `negative_confounded`. Status follows the surrogate the model actually predicted; the
figure overlays a marker when `outcome_tested` is negative (#97, #105, #119, #101). This is the
Scannell point and the one thing the five colours cannot show: SHPT/EVOLVE, HF/ASCEND-HF,
PBC/COBALT all read green today.

## 10. Retrodiction and post-hoc models never earn `same`

**Rule.** A model result that post-dates and is motivated by the patient result is not a prediction;
it can earn `contra` if it fails, otherwise `untested` with `retrodiction: true` (#5, #11, #49,
#106, #50). A non-significant trend in a terminated trial is not a patient result.

## 11. Magnitude and partial agreement

**Rule.** `magnitude` bins: `within_2x`, `off_by_2-5x`, `off_by_>5x`, `direction_only`, `null`,
`opposite` (#4, #15, #104), checker-computed on the quantity the model predicted, with
`magnitude_basis` naming it (#133); `source_calls_it` stays source-stated. Direction held with a scaling miss is `same` + the bin. Partial agreement
inside one source (one readout matched, one did not) is `same` on the pre-specified readout with
`source_calls_it: partial` (#110, #115). Right hazard, wrong incidence is `same` + `magnitude` on
incidence (#95, #116). Today 99 scored cells are `direction_only`, 11 `within_2x`, 2 `off_by_>5x`;
the bins are too coarse to carry the surrogate-outcome story, hence decision 9.

## 12. Class and context boundaries

**Rule.** Class = the DB (target, action) label; dual-mechanism drugs are out unless the DB puts them
in (#33, #78). A DB class with no patient comparison stays all-`untested` with a note; the drafter
may not widen it to a sibling target (#124, glaucoma: the DB says ADORA2A, every patient datum is
the A1 agonist trabodenoson). Modality (CAR-T / ADC / naked antibody) splits the safety and dose cells but shares
efficacy (#55, #62). A sibling-class surrogate dosed in the model (anti-PD-L1 for an anti-PD-1 class)
scores `other` (#69). Combination-arm events anchor a `contra` only if the source attributes them to
the class drug (#70). Cross-indication or sibling-population comparisons (T2D trials for an obesity context, HFrEF for
DKD) transfer only for safety, symmetrically, with `imported_from` set and a different dose noted
(#46, #76, #77, #134). Route stays inside the context (#109). Population = what the
class is prescribed by; trial enrolment goes in the note (#45). Duplicate contexts across MONDO
terms are merged to the DB term (#103). Repurposed classes get a second, flagged context per
indication rather than vanishing under the novel-entity filter (#24); thin-plurality classes are
reported with their program count so the reader can see how little of the indication they cover
(#25).

## 13. `neg` and `other`

**Rule.** `neg` needs a prospective flag: a source that read the model as negative before the drug
failed (#49); the model is the system, not the cell line (#48); the failure must be in this context's
population (#21). `other` means another pharmacological mechanism for the three pharmacology cells and
another molecule on the same platform for safety (#115).

## 14. Regulatory reliance is a flag, not a status

**Rule.** FDA/EMA accepting model data in lieu of a trial (Kalydeco in-vitro label expansion) sets
`regulatory_reliance: true` on the context; it does not change a cell's colour (#40). AMQP has
qualified one animal model ever, so this flag will be rare and worth showing.

## Schema v3 additions

| field | where | values |
|---|---|---|
| `source_tier` | entry | 1–5 per decision 2 |
| `trial_unreported` | entry | bool |
| `model_kind` | entry | animal / human_challenge / ex_vivo / in_silico / human_genetic / cross_indication |
| `model_change` | entry | bool (new best model, same or different status) |
| `outcome_tested` | efficacy cell | null / positive / negative / negative_confounded |
| `retrodiction` | entry | bool |
| `imported_from` | entry | MONDO id of the indication the comparison was made in |
| `patient_trials` | entry | list of {nct, registry_date, doi, quote} that change no status |
| `regulatory_reliance` | context | bool |
| `confidence` | entry | enum high / medium / low; free text moves to `confidence_note` (drafters stuffed ~60 notes into it) |

`magnitude` gains `null` and `opposite`; `source_calls_it` gains `partial`, `unresolved`,
`over_predicted`.

## What changes in the drafter brief

1. Rule 1 rewritten as decisions 1–2 (two comparison kinds, five source tiers).
2. Cell definitions from decision 4 pasted in verbatim; the "engaged-but-inert" and "primary
   endpoint" sentences are the two that flipped most cells between drafter and checker.
3. Dating rule from decision 7; registry lookup already mandatory.
4. Empty-vs-`untested` from decision 8.
5. The schema v3 fields above, with `confidence` as an enum.
6. A "do not" list: no `contra` from juxtaposition alone when the source attributes the failure to
   untested conditions; no `same` for retrodiction; no press-release model-side evidence.

## Production note: FDA review PDFs

Six drafters reported FDA multidiscipline/pharmacology reviews as unreadable (WebFetch 10 MB cap,
accessdata bot page on sandboxed curl). The obesity checker then pulled the 22.7 MB Saxenda PharmR
with plain curl + pdftotext and found a safety `contra` (gall-bladder silence in mice and monkeys
vs cholelithiasis at weight-management doses) the drafter had missed (#128, #132). `model_filed`
is null on 193 of 523 entries for the same reason. Before the κ re-run, pre-fetch the review PDFs for
all 70 contexts into a local cache and point the brief at it.

## What to re-run for κ

Re-draft 30 contexts (10 per area group, stratified by the current status mix) under the v2 brief
with fresh agents, check them, and compute κ on the latest cell status against the current checked
drafts. The 19 % drafter-vs-checker flip rate today (mostly `same` → `untested` on juxtaposition
strictness) is the number v2 has to beat.
