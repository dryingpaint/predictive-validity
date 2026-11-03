# Rules v2: walkthrough sheet

Companion to `RULES_V2_PROPOSAL.md`. One block per decision, in the order to take them. Each block ends with a
`Decision:` line to fill in as we go. Numbers are from the finished run (71 contexts, 284 cells, 166 scored).

---

## 1. Who makes the comparison: the source, or us?

**Question.** Rule 1 says a cell can only be coloured when a primary source itself states that the model's
prediction was compared with patients. In practice the drafters mostly found a model paper and a trial
paper and put them side by side.

**Context.** Trial papers almost never look back at the animal data; the comparison lives in the reader's
head. 79 of the 166 coloured cells are such pairings, and so are both of Melissa's own seed contexts
(cf-cftr pairs Van Goor 2009 with Ramsey 2011; ad-amyloid pairs Irizarry 1997 with Doody 2013). Panel C of
the summary shows paired cells land on matched/contradicted at similar rates to stated ones for
engagement and efficacy, so the distinction is provenance, not a different answer.

**Recommend.** Allow pairing. Record `comparison_stated` true/false on every entry and draw paired cells
hatched. A trial paper that merely cites the model paper is a pairing, not a statement.

**Alternative.** Strict reading: 79 cells and the two seeds go grey; the atlas becomes a map of who
bothered to write the comparison down.

**Decision (SG, 2026-11-02):** Agreed. Allow pairing; record `comparison_stated`; draw paired cells hatched.

---

## 2. Which sources are admissible

**Question.** The brief lists peer-reviewed papers, FDA labels/reviews and registry records. Checkers kept
hitting sources outside that list that carried the only comparison.

**Context.** EMA assessment reports turned out to be the best single source of stated comparisons (they
summarise the tox package next to the trial data), FDA advisory-committee transcripts carry comparisons a
year before any paper, and several Phase 3 failures exist only as a press release or an SEC filing
(trabodenoson, LX1033, the two CERC-301 trials). Under the current rule those classes show green.

**Recommend.** Five tiers, recorded as `source_tier`: (1) paper with DOI or PMID; (2) regulator documents,
FDA, EMA, Health Canada, AdCom briefing and transcript; (3) registry results record; (4) meta-analysis,
patient side only; (5) press release or SEC filing, patient side only, never for the model side, and the
cell carries `trial_unreported: true` so its colour is visibly provisional. "Data not shown" on either
side scores at low confidence.

**Alternative.** Stop at tier 3 and accept that unpublished failures stay invisible.

**Decision (SG, 2026-11-02):** Tiers 1–3 in. Tiers 4–5 → Melissa. SG leans no, but notes a press release is sometimes the only source that says *why* a trial failed.

---

## 3. Who counts as "patients"

**Question.** Engagement and dose evidence is often in healthy volunteers (PET occupancy, PK bridging,
natriuresis). The brief says "patient results".

**Context.** 11 of the 44 matched engagement cells rest on volunteers. The clean case is PDE10A: occupancy
was measured by PET, the checker demoted it to "never compared" because the subjects were not
schizophrenic. Biomarker-defined contexts raise the mirror problem: KRAS-mutant pancreatic cancer trials
enrolled everyone, because ~90 % of the disease is KRAS-mutant.

**Recommend.** Volunteers count for engagement and dose (recorded in `subjects`), patients required for
efficacy, either for safety. Unselected trials count for a biomarker context when the biomarker is ≥ 80 %
of the trial population.

**Alternative.** Patients only, everywhere: engagement loses a quarter of its matches.

**Decision (SG, 2026-11-02):** Healthy volunteers count for engagement and for dose. A later patient PK or occupancy source enters as its own dated entry and overrides. (Today 1 of 22 scored dose entries rests on volunteers.)

---

## 4. What each cell asks

**Question.** The four one-line definitions in the brief left the two biggest disagreements between
drafters and checkers undecided: what "engaged" means, and which cell owns a drug that reached its target
exposure and did nothing.

**Context.** ONO-4474 met the rat trough in Phase 1 and fell short of a weak opioid; PF-02545920 occupied
PDE10A and was inert. One drafter scored dose `contra` ("the model's sufficient exposure wasn't
sufficient"), another scored dose `same` and sent the failure to efficacy. Likewise "did the disease
respond" was read as primary endpoint by some and as any predicted activity by others (QAX576 in EoE
missed its responder threshold while eosinophils fell 60 %).

**Recommend.**
- engagement: the PD readout the model used moved in humans (see §15 for grading the readout);
- dose: the exposure or occupancy target was *reached*; engaged-but-inert belongs to efficacy;
- efficacy: the trial's primary endpoint, or the pre-specified proof-of-concept gate when the sponsor named
  one as the decision point;
- safety: the model's stated prediction held, or its silence was contradicted on a harm the species could
  have shown ("askable silence"; a mouse cannot show cytokine release, so its silence on CRS is not a miss).

**Alternative.** Dose = "sufficient": one efficacy failure then counts twice, in two cells.

**Decision (SG, 2026-11-02):** Dose is tied to efficacy: a drug that reached the model's exposure, did not work and was abandoned is a model failure, counted once. Rule: (1) exposure not reached → dose `contra`, efficacy `untested`; (2) reached and worked → both `same`; (3) reached, failed, abandoned → efficacy `contra`, dose `contra` with `derived_from: efficacy`, hatched, excluded from the dose count; (4) reached, failed, a higher dose later worked → dose `contra` (model's target too low, magnitude recorded), efficacy `contra` → `same`. Efficacy = primary endpoint or named PoC gate. Safety = askable silence, agreed. Under this rule 7 of the 66 dose cells become derived and 3 stay independent dose failures.

---

## 5. Animals predicted a harm that never came

**Question.** Is a false alarm a wrong prediction, or a conservative model doing its job?

**Context.** Rodent carcinoids on P-CABs never appeared in five years of human biopsies and the label calls
them rodent-specific; telaprevir's rat testicular toxicity at a fraction of clinical exposure never showed
in men; monkeys predicted vasculitis on ranibizumab in 2007 and were wrong, then missed it on
brolucizumab in 2019. About six safety cells turn on this.

**Recommend.** `contra`, dated to the first patient dataset that could have shown the harm, with
`magnitude: opposite`. The atlas is about prediction, and a wrong prediction is wrong in either direction.

**Alternative.** `same` with `source_calls_it: over_predicted`; the model is credited for caution.

**Decision (SG, 2026-11-02):** Agreed. A predicted harm that never came is a wrong prediction: `contra`, `magnitude: opposite`.

---

## 6. Is `contra` permanent?

**Question.** The brief says `contra` overrides every matched status. It does not say whether a cell can
ever recover.

**Context.** Haemophilia B: the dog model missed the AAV2 capsid immune response (2006), then a macaque
model predicted AAV8 durability and was right (2014). EGFR dose: cell-line potency was wrong for first-gen
inhibitors, the mutant/wild-type selectivity window was right for osimertinib. Seven strips currently show
such a recovery. Under "sticky contra" they stay red from the first miss.

**Recommend.** `contra` is per model and per time point. A later entry may recover the cell when a
different best model took over (marked `model_change: true`) or when a primary source reports that the
contradiction attenuated (dolutegravir neural-tube signal). One drug's `contra` still overrides another
drug's `same` for the same model.

**Alternative.** Sticky: simpler strips, redder atlas, and the model-replacement story is lost.

**Decision (SG, 2026-11-02):** Agreed, tentatively. Flag for Melissa.

---

## 7. Dating an entry

**Question.** Print year, epub year, or registry results-posted date?

**Context.** 25 of the 74 entries with a registry date have a registry year earlier than the paper; 40 of
323 have an epub year before print. The RA/BTK efficacy strip reads matched-then-contradicted by print
year and contradicted-then-matched by registry date. Labels sometimes make the comparison years before a
paper does (vonoprazan).

**Recommend.** The entry's year is the earliest of the admissible dates; all three are recorded so the
strip can be redrawn under any convention. A model introduced mid-cell opens at its first class use, proxy
allowed.

**Alternative.** Print year only, as the seed contexts do; simplest, and wrong in about a third of cases.

**Decision (SG, 2026-11-02):** Agreed, simplified form: the entry's year is the earliest date the comparison was public (registry, epub, label or print); all dates recorded.

---

## 8. What counts as "the model"

**Question.** The brief says "the model the class actually relied on". Several things stretched that.

**Context.** Proxies: the dogs never got valoctocogene, yet the sponsor attributes the durability expectation
to them (14 coloured cells rest on proxies). Human systems: the allergen chamber, UVB evoked pain, patient
ex-vivo cells, a human genetic model (C5 deficiency) were what the class relied on instead of animals.
No model at all: anti-VEGF in DME, anti-PD-1 in HCC, elagolix, acne entered with no disease-specific model
and the regulator accepted it. Drafters wrote some of those as empty cells and others as `untested`.

**Recommend.** Proxies allowed with `product_in_model: false`. Human systems in scope with a `model_kind`
(animal / human_challenge / ex_vivo / in_silico / human_genetic / cross_indication). Empty cell means no
model was relied on and is drawn lighter; `untested` means a model exists and was never compared.

**Alternative.** Animals only; the chamber-vs-field miss for CRTH2 antagonists disappears.

**Decision (SG, 2026-11-02):** Any system the class relied on, labelled. Cousin-drug proxies allowed and flagged (`product_in_model: false`; the dogs did not see the drug). Human challenge and other non-animal systems in scope with `model_kind`. No model relied on = blank cell, drawn lighter, distinct from `untested`.

---

## 9. Surrogate matched, outcome trial failed

**Question.** When the model predicted a surrogate correctly and the outcome trial was null, the cell stays
green because the model never predicted the outcome. Is that acceptable?

**Context.** Cinacalcet (PTH down, EVOLVE null), nesiritide (haemodynamics matched, ASCEND-HF null),
obeticholic acid (ALP down, COBALT null and confounded). All three read "matched" today. This is the
Scannell point and the one thing the five colours cannot express.

**Recommend.** Add `outcome_tested` to the efficacy cell: null / positive / negative / negative_confounded.
Status follows the surrogate; the figure overlays a marker when the outcome was negative.

**Alternative.** Score outcome failure as `contra`; then the model is blamed for a prediction it never made.

**Decision (SG, 2026-11-02):** Agreed. Add `outcome_tested`; status follows the surrogate; marker when the outcome trial was negative.

---

## 10. Models built after the patient result

**Question.** Can a model that reproduces a known clinical finding earn `same`?

**Context.** Knani 2016 reproduced in Magel2 mice the direction of a 2011 rimonabant trend in Prader-Willi;
Kanoski 2012 reproduced liraglutide's nausea in rats after the clinic had seen it; EGFR cell lines
recapitulated the 2004 sensitising-mutation result in the same paper. Drafters scored some of these
`same`.

**Recommend.** Never `same`. A retrodiction can earn `contra` if it fails, otherwise `untested` with
`retrodiction: true`. A non-significant trend in a terminated trial is not a patient result.

**Alternative.** Allow `same` from the first prospective prediction the post-hoc model then makes
(HF/SGLT2 pig model → EMPA-TROPISM).

**Decision (SG, 2026-11-02):** SG's suggestion, flagged for Melissa to decide: a model built after the clinic knew the answer is not used. Kept in the JSON as `retrodiction: true` for traceability, drawn and counted as nothing. A new prospective prediction such a model later makes enters as a fresh entry from its own date.

---

## 11. Magnitude and partial agreement

**Question.** Direction held but the size was off; or one readout matched and another did not.

**Context.** 99 of the coloured cells are "direction only". The macaque gave 420 % FIX at the dose that
gave patients 5 %; brown-fat rodents lose far more weight than people on GLP-1 at matched exposure;
monkeys flagged thrombocytopenia on volanesorsen but not a 47 % incidence. The current bins cannot say
"null" or "opposite", so §9 has nowhere to live.

**Recommend.** Bins: within_2x / off_by_2-5x / off_by_>5x / direction_only / null / opposite,
checker-computed on the quantity the model predicted, with `magnitude_basis` naming it. Partial agreement
is `same` + `source_calls_it: partial`. Right hazard, wrong incidence stays `same` with the incidence in
`magnitude`.

**Alternative.** Source-stated magnitude only; most cells stay direction-only forever.

**Decision (SG, 2026-11-02):** Agreed. Magnitude bins, checker-computed; partial agreement stays `same` with `source_calls_it: partial`.

---

## 12. Class and context boundaries

**Question.** What is "a drug of this class", and when does evidence from another indication or modality
carry over?

**Context.** The DB said "ADORA2A agonists" for glaucoma; every patient datum is the A1 agonist
trabodenoson, and the drafter quietly widened the class. CD19 depleters span CAR-T, naked antibodies and
ADCs, which share an efficacy model but not safety or dose models. The nivolumab monkey-vs-patient
immune-toxicity comparison was made in melanoma patients, then imported into HCC. Liraglutide's safety
match was in diabetics at 1.8 mg; the obesity context runs 3 mg in non-diabetics.

**Recommend.** The DB (target, action) label governs; a class with no patient data stays all-`untested`
with a note rather than being widened. Modality splits safety and dose, shares efficacy. Cross-indication
or sibling-population comparisons transfer for safety only, symmetrically, flagged `imported_from`.
Repurposed classes get a second, flagged context rather than vanishing under the novel-entity filter.

**Alternative.** Let drafters define the class; consistency with the DB join is lost.

**Decision (SG, 2026-11-02):** → Melissa, with the recommendation as written.

---

## 13. `neg` and `other`

**Question.** When does a model get credit for flagging a failure, and what does "other mechanism" mean for
safety?

**Context.** Only two cells are `neg` today. BMS-641988's xenograft data were read as positive by its own
sponsor and called a miss only in retrospect. For safety, a monkey platelet finding on a different-target
antisense drug matched volanesorsen's: same platform toxicity, different pharmacology.

**Recommend.** `neg` needs a prospective flag in this context's population: a source that read the model
as negative before the drug failed. `other` means another pharmacological mechanism for the three
pharmacology cells and another molecule on the same platform for safety.

**Alternative.** Retrospective `neg`; the status then rewards hindsight.

**Decision (SG, 2026-11-02):** Agreed, and → Melissa: `neg` is earned by what the model data showed, not by what the sponsor said about them, judged against a stated effect-size threshold per class with the number recorded; prospective flag not required. Cross-class evidence (`other`) set aside rather than used to colour this class's cell.

---

## 14. Regulatory reliance

**Question.** FDA expanded the Kalydeco label on in-vitro data "in lieu of a clinical trial". Is that a
status?

**Context.** It is the strongest form of reliance a model can earn and the only animal-model qualification
FDA has ever granted is one model (GAO-22-105248). It is not a published model-vs-patient comparison.

**Recommend.** A flag on the context, `regulatory_reliance: true`, drawn as a mark, not a colour.

**Alternative.** Treat it as `same`; it then outranks evidence it did not produce.

**Decision (SG, 2026-11-02):** Agreed. Flag, not colour.

---

## 15. Engagement evidence kind (new, from this afternoon)

**Question.** "Hits the target" covers direct measurement (occupancy, free target, ex-vivo blockade) and
inference from a downstream biomarker. Should the atlas tell them apart?

**Context.** The 44 matched engagement cells split about 15 direct, 10 target-product, 18 downstream. The
local experiment found no predictive difference between kinds (Phase 2 advancement 42 % direct vs 50–52 %
indirect, p = 0.20), so the tier is descriptive. It still matters: the column currently claims 61 %
engagement when directly shown engagement is nearer 20 %.

**Recommend.** Add `readout_tier` (direct / proximal / downstream), set from the existing `model` and
`quote` fields; draw direct solid and inferred hatched. Present it as what the evidence is, not as a
predictor.

**Alternative.** Leave the column as is and say "engagement" means pharmacology showed up.

**Decision (SG, 2026-11-02):** Agreed as a descriptive tag; the kind of engagement evidence did not separate outcomes. Melissa wants that result in the report: see `ENGAGEMENT_KIND_RESULT.md` (engagement_kind_result.py).

---

## Schema v3, if all of the above are accepted

`source_tier`, `trial_unreported`, `model_kind`, `model_change`, `outcome_tested`, `retrodiction`,
`imported_from`, `patient_trials`, `regulatory_reliance`, `readout_tier`; `magnitude` gains null/opposite;
`source_calls_it` gains partial/unresolved/over_predicted; `confidence` becomes an enum with a separate
`confidence_note`. Every one of these can be filled from the existing drafts without new research except
`outcome_tested`, which needs one lookup per efficacy cell.
