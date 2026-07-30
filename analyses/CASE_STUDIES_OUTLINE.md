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
