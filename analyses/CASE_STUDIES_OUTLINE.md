# Case Studies — proposed outline for the paper section

A suggested skeleton for the "Case Studies" section of *Modeling Clinical Predictive
Validity* (target venue: medRxiv preprint). Bullets to expand, not final prose. Source
material: `CASE_STUDY_DEEPDIVES.md` (per-case detail + citations) and `CASE_SCORECARD.md`
(the scorecard + safety cases). Figures live in `data/`.

---

## 0. The one-line job of this section
The logical arc: **genetics is the strongest predictor of success — but most programs fail
even with it, so what do the failures reveal about why?**
- Quantify the setup from our own data (Phase 2+ T-I pairs, base approval 23%; the
  `genetics_dose_response` numbers): approval rises 7.5% (no genetics) -> 19.2% (weak) ->
  21.7% (moderate) -> **45.2% (strong)** — about a 6x gradient, the steepest of any evidence
  type, and genetics is the biggest contributor to the model (removing it costs about 17.7
  AUC points). *And yet:* even the strongest genetic tier still fails **more than half the
  time** (45.2% approved). Genetic support moves the odds a lot; it does not make success
  likely.
- So the section's job: given a genetically credible target, **what breaks downstream** — and
  does the *way* it fails tell you whether the biology was wrong or just the execution?

## 1. Setup — the causal gates (short)
- A program has to clear a chain of gates: genetics -> target moves a biomarker -> **the
  biomarker actually causes the outcome** -> the drug engages the target -> it's safe ->
  approval.
- Human genetics only guards the first few gates. The later ones — is the biomarker *causal*,
  can you engage it safely — are where validated targets still die.
- **Figure: `causal_gates_scorecard`** (8 programs; green = gate holds, red = breaks). Point
  out the bottom pair — tocilizumab vs the anti-CRP drug — same genetics score (0.7), both hit
  their biomarker, opposite outcomes, because only one biomarker is causal.

## 2. "Strong evidence, and they still failed" (the scorecard)
- **Figure: `case_scorecard_stephengoldstein`** — seven programs, near-maximal preclinical
  evidence, all failed. Split into efficacy failures (5) and safety failures (2).
- One paragraph making the point that a maxed-out preclinical scorecard is not predictive on
  its own.
- **Figure: `genetics_vs_outcome`** — genetic strength doesn't separate winners from losers
  (three programs sit at the same 0.7 score: one approved, two failed; and APP failed at a
  *higher* score than the approvals). Genetics is necessary-ish, not sufficient.

## 3. The heart of the section — three verdicts, told through cases
Frame: the failure alone doesn't tell you if the target was wrong. **The drug that came next
does.** Organize the cases by what the later drug revealed.

### Tie every case back to the 45%/55% number
These programs *are* the 55%. Each is an instance of failure despite genetic support, and the
point of the section is to name, case by case, *which gate broke*. Note the range of genetic
strength: several failed on only weak support (CETP, CRP, Lp-PLA2), but the anti-amyloid
antibodies failed at **Strong** support — a genetic score (1.9) *higher* than the approved
PCSK9 (1.6). So this is not "they failed because their genetics was weak"; genetically strong
programs fail too, and the reason is always downstream. This table is the spine — consider
including it as a manuscript table, and open each case paragraph by stating its genetic tier
and the gate it failed.

| Case | Genetic support (`genetic_only_v1`) | Gate that broke | Failed because… |
|---|---|---|---|
| CETP / torcetrapib | Weak (0.7) | biomarker not causal | HDL doesn't cause heart disease (MR); plus an off-target toxicity |
| CRP / anti-CRP ASO | Weak (0.7) | biomarker not causal | CRP is a marker, not a cause — the causal node is IL-6, upstream |
| Lp-PLA2 / darapladib | Weak (0.5) | biomarker not causal | Lp-PLA2 is a passenger of plaque inflammation, not a driver |
| BACE1 inhibitors | Moderate (1.0) | wrong node + on-target harm | blocking amyloid *production* is insufficient and the enzyme has essential jobs |
| Anti-amyloid mAbs (APP) | **Strong (1.9)** | right node, wrong form/stage | early antibodies hit the wrong amyloid form too late; fixed by lecanemab/donanemab |
| γ-secretase / semagacestat | Moderate (1.0) | drug engagement (too blunt) | inhibiting the enzyme also blocks Notch and others — net harm |
| APOC3 / volanesorsen | Moderate (1.0) | safety (molecule) | platelet toxicity of the ASO format; fixed by liver-targeted successors |
| Factor XI / asundexian | Moderate (1.3) | drug engagement + indication | under-dosed in AF (a less FXI-dependent clot); won in stroke prevention |
| TGN1412 / CD28 | Moderate (1.0) | safety (dose/species) | superagonist dose + monkey model missed it; works at 1/1000 the dose |
| Fialuridine / HBV pol | n/a (viral) | safety (molecule) | mitochondrial toxicity of this molecule; the target underlies all modern HBV therapy |

### 3a. The biology was wrong
*(the target doesn't drive the disease)*
- **CETP / torcetrapib** — feature case. Raising HDL never worked; the class only produced a
  win (anacetrapib) once repurposed to lower LDL; obicetrapib now sold as an LDL drug. Great
  "the correlation fooled us; genetics (MR) called it" story.
- **CRP / anti-CRP drug** — feature case. Drug lowered CRP about 77%, zero benefit; the real
  target was IL-6, one step upstream. The cleanest "engaged the marker, not the cause" example,
  and it pairs with tocilizumab in the gate figure.
- *Mention briefly:* Lp-PLA2 / darapladib (cleanest "wrong target, abandoned"); BACE1
  (blocking amyloid production was useless and harmful).

### 3b. Partly right — the target matters, wrong form / too late
- **Anti-amyloid antibodies** — feature case, and the emotional arc of the section: the
  early antibodies (solanezumab, bapineuzumab) failed on the wrong amyloid form / too late,
  then lecanemab and donanemab hit the right form early and finally slowed the disease
  (about 25-35%). Shows the same target going from failure to modest success by changing form +
  stage. Also the honest "modest, not a cure" note.

### 3c. The biology was right — molecule / dose / delivery was wrong
- **APOC3 / volanesorsen -> olezarsen / plozasiran** — feature case. Great redemption story:
  volanesorsen worked but had a platelet side effect and was FDA-rejected; liver-targeted
  successors kept the benefit, dropped the side effect, and got approved (2024, 2025). Same
  target — the delivery was the problem.
- **Factor XI / asundexian** — feature case. The safety promise (less bleeding) held; the
  atrial-fibrillation trial failed on dose/indication, but the same drug won in stroke
  prevention (OCEANIC-STROKE). "Right target, wrong dose and disease."
- **Safety failures — TGN1412 and fialuridine** — the purest "right target, wrong molecule/
  dose." TGN1412 works at 1/1000th the dose; fialuridine's target (HBV polymerase) is the
  backbone of modern hepatitis-B therapy. Use these to make the point that a safety
  catastrophe usually indicts the molecule, not the biology.

## 4. The takeaway (close the section)
- Genetics/preclinical evidence gets you a *candidate* target. It cannot tell you, when a
  program fails, whether the target was wrong or just the first drug.
- Two things settle that: a **causal test** (Mendelian randomization) and the **natural
  experiment of the next drug**.
- Tie back to Section 2: this is *why* genetics leads on average but isn't destiny — it clears
  the early gates, and the causal and execution gates do the rest.
- Optional kicker: the failure modes map onto the paper's taxonomy — efficacy failures tend to
  indict the biology; safety failures tend to indict the molecule.

---

## Suggested figure order in the section
1. `causal_gates_scorecard` (the frame)
2. `case_scorecard_stephengoldstein` (strong evidence, still failed)
3. `genetics_vs_outcome` (strength doesn't decide)
`scorecard_legend` is the shared key for the two scorecards.

## Which cases to feature vs mention
- **Feature (write a paragraph each):** CETP, CRP, anti-amyloid, APOC3, Factor XI.
- **Mention in a sentence:** Lp-PLA2, BACE1, gamma-secretase, and the two safety cases (or
  give the safety cases their own short paragraph — they make a clean, separate point).

## Watch-outs (carry from the deep-dives doc)
- All genetics scores are present-day (hindsight) — state it once.
- Several outcome trials are still running (ZEUS, PREVAIL, LIBREXIA-AF) — don't write them as
  settled. A few PMIDs need a PubMed confirm. Full list at the bottom of
  `CASE_STUDY_DEEPDIVES.md`.

---

# Draft text blocks (manuscript register — edit freely)

Draft prose for the Case Studies section in a register suitable for a medRxiv preprint:
declarative, past tense for events, measured claims. Facts are drawn from the verified
`CASE_STUDY_DEEPDIVES.md`; trial names are given as citation cues (full references and
PMIDs/DOIs are in that document) and should be converted to the manuscript's citation style.
Figure numbers are placeholders.

### Opening
> Human genetic support was the strongest single predictor of clinical success in our
> analysis. Across Phase 2+ target-indication pairs, the probability of approval increased
> monotonically with genetic strength, from 7.5% for programs with no genetic support to
> 45.2% for those in the strongest tier (Figure X) — an approximately six-fold gradient — and
> removal of the genetic feature block degraded model discrimination more than that of any
> other evidence class. The same figures, however, bound the value of genetic evidence: even
> in the strongest-support tier, most programs — approximately 55% — still failed. Genetic
> support substantially raises the probability of success without rendering success likely in
> absolute terms. The cases that follow examine this residual failure directly: given a
> genetically credible target, what fails downstream, and does the mode of failure — efficacy
> versus safety, and whether a later agent against the same target succeeds — distinguish
> programs in which the biological hypothesis was wrong from those in which the hypothesis was
> sound but the molecule, dose, or developmental timing was not.

### The gates (frame)
> We represent each program as an ordered sequence of gates that must be cleared: genetic
> implication of the target; evidence that modulating the target moves a biomarker; evidence
> that the biomarker is causal for the clinical endpoint rather than merely correlated with it;
> adequate target engagement by the drug; and acceptable safety. Human genetic evidence informs
> the earliest gates but is largely uninformative about the later ones — biomarker causality and
> safe engagement — which is where genetically validated targets most often fail (Figure X). The
> paired comparison of an anti-IL-6-receptor antibody and an anti-CRP agent is illustrative: the
> two targets receive identical genetic scores and both agents engage their biomarker as
> designed, yet only one has reached approval, because only one biomarker lies on the causal
> pathway.

### Strong evidence, discordant outcomes (into the scorecard)
> Figure X summarizes seven programs with near-maximal preclinical evidence across mechanistic,
> cellular, animal, and human pharmacodynamic domains, all of which failed in clinical
> development. Genetic strength did not discriminate outcomes (Figure Y): three programs share
> an effectively identical genetic score with divergent outcomes (one approval, two failures),
> and the anti-amyloid antibodies failed at a higher genetic score than either lipid-lowering
> success. Strong preclinical evidence thus appears necessary but far from sufficient. The
> programs discussed below are representative of the failures that persist despite genetic
> support; for each, we indicate the strength of genetic support and identify the gate at
> which development failed.

### CETP — a correlational biomarker mistaken for a causal one
> The CETP programs illustrate the misattribution of causality to a correlational biomarker.
> Torcetrapib raised HDL cholesterol by approximately 72%, as intended, but was associated with
> increased mortality (ILLUMINATE); the proximate cause was an off-target, molecule-specific
> effect on adrenal steroidogenesis, but the more fundamental limitation was that HDL elevation
> is not cardioprotective. Mendelian randomization indicates that HDL-raising alleles do not
> reduce myocardial infarction risk, and the subsequent class was consistent with this: a
> selective HDL-raising agent (dalcetrapib, dal-OUTCOMES) conferred no benefit, whereas the only
> CETP inhibitor to reduce events (anacetrapib, REVEAL) did so in proportion to its reduction in
> LDL/apoB rather than its elevation of HDL. The target has been retained only after its
> rationale was reframed around LDL lowering.

### CRP — efficacious engagement of a non-causal biomarker
> The CRP program demonstrates that engaging a biomarker efficaciously is not equivalent to
> engaging a cause. An antisense oligonucleotide reduced C-reactive protein by approximately
> 77% without measurable clinical benefit, consistent with CRP being a marker rather than a
> mediator of inflammatory cardiovascular risk; genetically elevated CRP is not associated with
> increased coronary risk (Mendelian randomization). The causal node lies upstream in IL-6
> signaling, where pharmacological intervention does modify clinical endpoints (e.g., IL-1-beta
> inhibition in CANTOS; ongoing IL-6 outcome trials).

### Anti-amyloid antibodies — the same target, from failure to modest efficacy
> The anti-amyloid antibodies are particularly informative because the same target progressed
> from repeated failure to modest efficacy. The first-generation antibodies failed for
> identifiable reasons: solanezumab targeted soluble monomeric amyloid-beta and failed even in
> an asymptomatic prevention population (A4), while bapineuzumab engaged plaque but with limited
> potency and dose-limiting amyloid-related imaging abnormalities. Second-generation antibodies
> (lecanemab, CLARITY-AD; donanemab, TRAILBLAZER-ALZ 2) targeted aggregated species, were
> administered earlier in disease, and demonstrated target engagement by amyloid PET; both
> slowed cognitive decline by approximately one-quarter to one-third. This constitutes a genuine
> but modest effect, consistent with amyloid as an upstream contributor rather than the sole
> driver of established disease, and it localizes the earlier failures to amyloid species and
> treatment timing rather than to target validity.

### APOC3 — a valid target constrained by molecular format
> The APOC3 program exemplifies a valid target initially constrained by molecular format.
> Volanesorsen reduced triglycerides by approximately 77% in familial chylomicronemia syndrome
> — efficacy was not in question — but produced thrombocytopenia in approximately three-quarters
> of treated patients, resulting in a negative U.S. regulatory decision despite European
> approval. The platelet effect is a recognized liability of systemically distributed
> first-generation antisense oligonucleotides rather than a property of APOC3 inhibition, and
> the target was well supported by loss-of-function genetics (approximately 40% lower coronary
> risk in carriers). Hepatocyte-targeted successors — olezarsen (a GalNAc-conjugated antisense
> oligonucleotide) and plozasiran (a GalNAc-conjugated siRNA) — retained triglyceride lowering
> without clinically significant thrombocytopenia and have since been approved, indicating that
> the limitation resided in the molecule rather than the target.

### Factor XI — failure and success from the same agent
> The Factor XI program demonstrates that failure and success can arise from the same agent.
> The central hypothesis — anticoagulation with reduced bleeding, motivated by the mild
> bleeding phenotype of congenital Factor XI deficiency — was supported: in atrial fibrillation,
> asundexian produced substantially less bleeding than standard-of-care apixaban (OCEANIC-AF).
> It nonetheless prevented fewer strokes and the trial was terminated, plausibly reflecting
> sub-maximal Factor XIa inhibition at the dose studied and an indication in which thrombus
> formation is comparatively less Factor XI-dependent. The same agent subsequently met its
> endpoint in secondary stroke prevention (OCEANIC-STROKE), and other Factor XI inhibitors are
> under evaluation at higher doses (milvexian) and as antibodies (abelacimab). The target
> therefore remains viable, and the atrial-fibrillation failure is more consistent with dose and
> indication than with an incorrect hypothesis.

### Safety failures — implicating the molecule rather than the target
> The two safety failures make a complementary point. A safety failure terminates a drug but
> does not, in itself, invalidate the target, and in both cases the target was subsequently
> vindicated. The anti-CD28 superagonist responsible for a well-documented 2006 cytokine-release
> event produces its intended regulatory-T-cell pharmacology at approximately one-thousandth of
> that dose (redeveloped as TAB08/theralizumab), and the 2006 event is attributable to the dose
> together with a species difference in CD28 expression that rendered the primate model
> non-predictive. The target of fialuridine — the hepatitis B polymerase — underlies all current
> nucleos(t)ide therapy for the disease; fialuridine failed on a molecule-specific mitochondrial
> toxicity. Whereas efficacy failures frequently implicate the biology, safety failures more
> often implicate the molecule.

### Closing
> Taken together, these cases indicate that genetic and preclinical evidence can nominate a
> credible target but cannot, at the point of clinical failure, distinguish an incorrect target
> from an inadequate drug. Two forms of evidence resolve this ambiguity: a formal causal test —
> Mendelian randomization, which separates biomarkers that drive disease from those that merely
> track it — and the subsequent development of alternative agents against the same target. This
> reconciles the population-level primacy of genetic evidence with its limits at the level of an
> individual program: genetic evidence clears the early gates, while the causal and execution
> gates determine the outcome.
