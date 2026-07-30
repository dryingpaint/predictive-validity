# Case Studies — proposed outline for the paper section

A suggested skeleton for the "Case Studies" section of *Modeling Clinical Predictive
Validity*. Bullets to expand, not final prose. Source material: `CASE_STUDY_DEEPDIVES.md`
(the per-case detail + citations) and `CASE_SCORECARD.md` (the scorecard + safety cases).
Figures live in `data/`.

---

## 0. The one-line job of this section
Sections 1-2 showed, in aggregate, that most trials fail and that genetics is the evidence
type that most moves the odds. This section makes it concrete and adds the crucial nuance:
**strong evidence — even strong human genetics — does not guarantee success, and the *way* a
program fails tells you whether the biology was wrong or just the execution.**

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

### 3a. The biology was wrong
*(the target doesn't drive the disease)*
- **CETP / torcetrapib** — feature case. Raising HDL never worked; the class only produced a
  win (anacetrapib) once repurposed to lower LDL; obicetrapib now sold as an LDL drug. Great
  "the correlation fooled us; genetics (MR) called it" story.
- **CRP / anti-CRP drug** — feature case. Drug lowered CRP about 77%, zero
  benefit; the real target was IL-6, one step upstream. The cleanest "engaged the marker, not
  the cause" example, and it pairs with tocilizumab in the gate figure.
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
  the early gates, and the causal + execution gates do the rest.
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

# Draft text blocks (starting points — edit freely)

Rough prose to get you off a blank page. Plain-language, every fact drawn from the verified
`CASE_STUDY_DEEPDIVES.md`. Cut, merge, and re-voice as you like; drop figure callouts where
they fit.

### Opening
> The previous section's headline — that genetics moves the odds of success more than any
> other line of evidence — is easy to over-read as "find a genetically supported target and
> you're most of the way there." The cases below are the correction. Every program here
> carried strong preclinical evidence, several carried strong human genetics, and all of them
> failed. What makes them worth studying is not that they failed but *how*: the way a program
> dies tells you whether the underlying biology was wrong, or whether the biology was right
> and the first drug simply got the molecule, dose, or timing wrong. That distinction is the
> difference between abandoning a target and trying again.

### The gates (frame)
> It helps to picture a drug program as a chain of gates it must clear in order: the target
> has to be genetically implicated, modulating it has to move a biomarker, that biomarker has
> to actually *cause* the clinical outcome, the drug has to engage the target well enough, and
> the whole thing has to be safe. Human genetics speaks to the first few gates and says almost
> nothing about the last ones — whether the biomarker is causal rather than merely correlated,
> and whether the target can be hit safely. Those later gates are where genetically validated
> targets keep dying. [*Figure: causal_gates_scorecard.*] The sharpest illustration is the
> pair at the bottom: an anti-IL-6-receptor antibody and an anti-CRP drug score identically on
> genetics and both move their biomarker exactly as designed, yet one is approved and the
> other did nothing — because only one of those biomarkers sits on the causal path.

### "Strong evidence, still failed" (transition into the scorecard)
> [*Figure: case_scorecard.*] Seven programs, near-maximal scores across mechanistic, cell,
> animal, and human-pharmacology evidence — and every one failed in humans. [*Figure:
> genetics_vs_outcome.*] Genetic strength does not sort the winners from the losers either:
> three of these programs sit at exactly the same genetic score, one approved and two failed,
> and the amyloid antibodies failed at a *higher* genetic score than either lipid-lowering
> success. Strong evidence turns out to be necessary-ish and nowhere near sufficient.

### CETP — a correlation mistaken for a cause
> CETP inhibition is the textbook case of chasing a correlation. Torcetrapib raised HDL — "good
> cholesterol" — by about 72%, exactly as intended, and increased deaths. The immediate cause
> was a toxicity specific to that one molecule, but the deeper problem was that raising HDL was
> never going to help: inherited variants that raise HDL do not lower heart-attack risk. The
> cleaner successors proved it. A pure HDL-raiser (dalcetrapib) did nothing, and the single
> CETP inhibitor that eventually reduced events (anacetrapib) did so through the LDL it lowered,
> not the HDL it raised. The target survived only after the field discarded its original
> rationale — the newest CETP drug in development is being positioned as an LDL-lowering agent.

### CRP — the drug worked perfectly on the wrong target
> C-reactive protein is the case where the drug did its job flawlessly and it didn't matter. An
> antisense drug lowered CRP by about 77% and produced no clinical benefit at all, because CRP
> is a readout of inflammation, not a driver of it — people born with CRP-raising variants are
> at no higher cardiovascular risk. The actual causal lever sits one step upstream, in IL-6
> signaling, where drugs do move hard endpoints. Engaging a biomarker is not the same as
> engaging a cause.

### Anti-amyloid antibodies — the same target, from failure to a modest win
> The amyloid antibodies are the most instructive case, because the same target went from a
> decade of failure to a real, if modest, success. The early antibodies missed in two specific
> ways: solanezumab bound the wrong form of amyloid — soluble single molecules — and failed
> even when given before symptoms appeared; bapineuzumab bound plaque but too weakly and with
> dose-limiting brain-swelling side effects. The next generation fixed both the form and the
> timing: lecanemab and donanemab target aggregated amyloid, given early, with brain scans
> confirming the plaque was actually cleared — and they slowed decline by roughly a quarter to
> a third. That is a genuine win and a modest one. It says amyloid is a real upstream
> contributor rather than the whole disease, and that the earlier failures were about hitting
> the wrong form too late, not about the target being a mirage.

### APOC3 — the cleanest "right target, wrong molecule"
> APOC3 is the clearest case of a good target undone by the wrong molecule. Volanesorsen
> lowered triglycerides by about 77% in a severe inherited disorder — efficacy was never in
> doubt — but dropped platelets in roughly three-quarters of patients, enough for the FDA to
> reject it. That platelet effect is a known liability of the drug's *format* (a
> first-generation antisense molecule spread through the whole body), not a problem with APOC3,
> whose genetic credentials were airtight going in. What came next is the proof: two successors
> that deliver the same idea straight to the liver kept the triglyceride benefit, lost the
> platelet problem, and were approved. Same target, fixed molecule.

### Factor XI — failure and success from the same drug
> Factor XI is a target where the failure and the success came from the same drug. The
> premise — a blood thinner that stops clots without causing bleeds — held up cleanly: in
> atrial fibrillation, asundexian caused far less bleeding than standard care, exactly as
> promised. But it prevented fewer strokes, and the trial was stopped. The likely culprits were
> a dose set too low and the disease itself, since atrial-fibrillation clots may depend less on
> Factor XI than other clots do. The tell is that the very same drug then succeeded in stroke
> prevention, and competitors are now testing the target at higher doses. The Factor XI idea is
> alive; asundexian's atrial-fibrillation trial was a dose-and-disease miss, not a dead target.

### Safety failures — the molecule, not the biology (short)
> The two safety catastrophes make the same point from the opposite direction. A safety failure
> kills the drug, but it does not tell you the target was wrong — and in both of ours, later
> work vindicated the target. The CD28 antibody that caused a notorious cytokine storm in 2006
> does exactly what it was designed to do at about one-thousandth the dose. Fialuridine's
> target, the hepatitis-B polymerase, is the backbone of every modern hepatitis-B therapy;
> fialuridine died on a toxicity unique to that one molecule. Where efficacy failures tend to
> indict the biology, safety failures usually indict the molecule.

### Closing takeaway
> The thread through all of these is simple. Genetic and preclinical evidence can hand you a
> promising target, but when a program fails, that evidence cannot by itself tell you whether
> the target was wrong or the drug was. Two things can: a causal test — Mendelian randomization,
> which separates a biomarker that drives disease from one that merely tracks it — and the
> natural experiment of whatever drug comes next. That is why genetics leads on average without
> being destiny: it clears the early gates, and the causal and execution gates decide the rest.
