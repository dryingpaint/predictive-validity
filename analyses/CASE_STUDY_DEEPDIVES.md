# Case-study deep dives — what they got wrong, and what a later drug proved

Reference material for the paper's Case Studies section. For each failed program we answer
two plain questions:

- **(A) What did they get wrong about the biology?**
- **(B) Did a later drug hit the same target a different way — and did it work?**

Question B is the key. A drug can fail for two very different reasons: the *target* was a bad
idea, or the *target was fine but the molecule / dose / timing was wrong*. The way to tell
them apart is to look at what happened next: if a later, better drug aimed at the same target
succeeded, the biology was right and the first attempt just fumbled it. If nobody ever made
that target work, the biology was probably wrong.

> A note on one tool we lean on: **Mendelian randomization (MR)**. People inherit gene
> variants at random, and some of those variants nudge a specific biomarker up or down for
> life. If a variant that lowers (say) LDL also lowers heart-attack risk, that's strong
> evidence LDL actually *causes* heart attacks — a natural randomized experiment, free of the
> confounding that plagues ordinary observational correlations. MR is how the field now tells
> a causal target from a mere marker.

Sourced via literature search (2026-07-29); trial names, effect sizes, and primary citations
verified. Some PMIDs and several still-running trials are flagged in **Verify before
publication** at the end; statuses are as of mid-2026.

**The cases sort into three verdicts:**

| Verdict | Plain meaning | Cases |
|---|---|---|
| **1. Biology was wrong** | the target doesn't actually drive the disease | CETP (HDL), Lp-PLA2 / darapladib, CRP, BACE1 |
| **2. Partly right** | the target matters, but they hit the wrong form of it, too late | anti-amyloid antibodies (APP), gamma-secretase / semagacestat |
| **3. Biology was right** | the target was fine; the molecule, dose, or delivery was the problem | APOC3 / volanesorsen, Factor XI / asundexian, plus the two safety cases (TGN1412, fialuridine — in `CASE_SCORECARD.md`) |

---

## Verdict 1 — the biology was wrong (the target doesn't drive the disease)

### CETP / torcetrapib — chasing HDL, which turned out not to matter
**In one line:** raising "good cholesterol" (HDL) never actually prevented heart attacks; the target only produced a win once the field stopped chasing HDL and used it to lower LDL instead.

- **What they got wrong.** Torcetrapib was meant to raise HDL. In the ILLUMINATE trial it did exactly that (HDL up about 72%) — and *killed people* (mortality up, hazard ratio 1.58; Barter, *NEJM* 2007, PMID 17984165). The proximate cause was a toxicity specific to this one molecule: it triggered adrenal hormones that raised blood pressure. The deeper problem: **raising HDL was never going to help.** Inherited variants that raise HDL do not lower heart-attack risk (Voight, *Lancet* 2012, MR) — HDL is a bystander, not a cause.
- **The later drugs.** The whole CETP class became a natural experiment. **Dalcetrapib** (pure HDL-raiser) — no benefit, stopped for futility (*NEJM* 2012, PMID 23126252). **Evacetrapib** — no benefit despite also lowering LDL about 25% (*NEJM* 2017, PMID 28514624). **Anacetrapib** — the one positive trial (9% fewer coronary events, REVEAL), but the benefit tracked its **LDL lowering, not its HDL raising**. **Obicetrapib** (now in late trials) is deliberately marketed as an **LDL-lowering** drug, not an HDL drug.
- **Bottom line.** The target survived — but only after the field admitted the original rationale (HDL) was wrong and repurposed it to lower LDL.

### Lp-PLA2 / darapladib — the cleanest "wrong target"
**In one line:** they inhibited an enzyme that marks inflamed plaque but doesn't cause disease; two big trials failed and the target was abandoned.

- **What they got wrong.** High Lp-PLA2 is *associated* with heart disease, so darapladib inhibited it to "stabilize" plaque. But it's a passenger, not a driver. Both Phase 3 trials were negative — STABILITY (stable heart disease; *NEJM* 2014, PMID 24678955) and SOLID-TIMI 52 (after a heart attack; *JAMA* 2014, PMID 25173516; event rates literally identical to placebo). Genetics had already warned this would happen: people born with low Lp-PLA2 get no protection from heart disease.
- **The later drugs.** None. The target was dropped and never revived. (Contrast CETP, which was at least rescued by a reframe.)
- **Bottom line.** A marker of the disease, not a cause of it. Lowering it moved the lab value and nothing else.

### CRP / ISIS-CRPRx — the drug worked perfectly on the wrong target
**In one line:** the drug lowered CRP beautifully and did nothing for patients, because CRP is a readout of inflammation, not its cause — the real target sits one step upstream.

- **What they got wrong.** ISIS-CRPRx cut CRP by about 77% and produced **zero clinical benefit** in rheumatoid arthritis (no difference from placebo; PMID 25885521). CRP is a bystander: inherited variants that raise CRP don't raise heart-disease risk (*BMJ* 2011, PMID 21325005; *NEJM* 2008).
- **The real target.** The cause is upstream, in the **IL-6 pathway.** Variants that dampen IL-6 signaling *do* lower heart-disease risk (*Lancet* 2012). And drugs on that pathway show real effects: canakinumab (anti-IL-1-beta) cut cardiovascular events in CANTOS (*NEJM* 2017, PMID 28845751); ziltivekimab (anti-IL-6) is in a large outcomes trial (ZEUS); tocilizumab (anti-IL-6-receptor) is approved in rheumatoid arthritis. This is the tocilizumab-vs-CRP pair in the gate scorecard.
- **Bottom line.** Perfect engagement of the biomarker, no benefit — because they aimed at the readout instead of the cause, which was a different protein entirely.

### BACE1 inhibitors — turning off amyloid production didn't help, and hurt
**In one line:** blocking the enzyme that makes amyloid lowered amyloid but made patients worse, because that enzyme has other important jobs in the brain.

- **What they got wrong.** BACE1 inhibitors cut brain amyloid by 60-80% and produced **no benefit — and cognitive *worsening*** (verubecestat EPOCH, *NEJM* 2018; APECS, *NEJM* 2019). Two lessons: shutting off amyloid *production* once disease is established is too late, and BACE1 also cuts other proteins the brain needs for synapses, so blocking it does harm. Atabecestat added liver toxicity; the rest failed for futility or bad risk/benefit.
- **The later drugs.** None — the entire BACE1 class was abandoned by about 2019. The field switched to *clearing* amyloid with antibodies instead of blocking its synthesis.
- **Bottom line.** Lowering amyloid production is neither enough nor safe. (The *production-blocking* idea was wrong; whether amyloid itself matters is answered by the antibodies below.)

---

## Verdict 2 — partly right (the target matters, but they hit the wrong form of it, too late)

### Anti-amyloid antibodies (APP) — the failures that set up the wins
**In one line:** the first amyloid antibodies aimed at the wrong form of amyloid, too late; the next generation aimed at the right form, early, and finally slowed the disease.

- **What they got wrong.** **Solanezumab** targeted *soluble, single-molecule* amyloid — the wrong form — and failed even when given to people *before* symptoms (the A4 prevention trial, *NEJM* 2023), which rules out "just too late" as the only problem. **Bapineuzumab** did hit plaque but too weakly, and its dose was capped by brain-swelling side effects (ARIA); no benefit (*NEJM* 2014, PMID 24450891).
- **The later drugs — same pathway, done right.** **Lecanemab** targets amyloid *protofibrils* in *early* disease: 27% slowing of decline, confirmed amyloid clearance on PET scans, FDA-approved 2023 (*NEJM* 2023, PMID 36449413). **Donanemab** targets a plaque-specific form of amyloid: about 35% slowing, most patients cleared their plaque (*JAMA* 2023, PMID 37459141). Both carry the same brain-swelling risk as bapineuzumab, now managed with MRI monitoring instead of being a dealbreaker.
- **Bottom line.** The amyloid idea was **partly right.** Clearing the *aggregated* form *early*, with proof the drug reached its target, does slow decline — but only modestly (25-35%), which says amyloid is one upstream contributor, not the whole story.

### Gamma-secretase / semagacestat — right pathway, blunt instrument
**In one line:** they blocked an enzyme in the amyloid pathway, but that enzyme is used all over the body, so the drug made patients worse.

- **What they got wrong.** Semagacestat didn't just fail — it *worsened* cognition and caused skin cancers, so the trial was halted (*NEJM* 2013, PMID 23883379). Gamma-secretase cuts many proteins besides amyloid (notably Notch), so blocking it hits a lot of essential biology at once.
- **The later drugs.** A gentler version (gamma-secretase "modulators," which shift rather than block the enzyme) is still experimental, nothing approved. The wins came from antibodies, not from this enzyme.
- **Bottom line.** This *way* of engaging amyloid was wrong (too blunt); it didn't settle whether amyloid mattered — the antibodies did.

---

## Verdict 3 — the biology was right (the molecule, dose, or delivery was the problem)

### APOC3 / volanesorsen — a delivery problem the next drugs fixed
**In one line:** the drug worked but caused a platelet side effect; later drugs that delivered the same idea straight to the liver kept the benefit and dropped the side effect.

- **What went wrong.** Volanesorsen cut triglycerides by about 77% in a rare fat-metabolism disease (FCS) — **efficacy was never in doubt** (*NEJM* 2019). The problem was a **platelet drop in roughly 75% of patients**, which got it **rejected by the FDA (2018)** even though **Europe approved it (2019)**. That platelet effect is a known quirk of this *type* of molecule (a first-generation antisense drug spread through the whole body), not a problem with the APOC3 target. And the target itself was rock-solid going in: people born with low APOC3 have low triglycerides and about 40% less heart disease (*NEJM* 2014, PMID 24941081).
- **The later drugs — same target, better delivery.** **Olezarsen** attaches a sugar tag that routes the drug straight into liver cells, so it works at far lower doses: similar triglyceride lowering, **no severe platelet problem, FDA-approved December 2024** — the first-ever FDA approval for FCS. **Plozasiran** (a different molecule type, siRNA, same liver targeting) cut triglycerides about 80% with no platelet signal and was **FDA-approved November 2025.**
- **Bottom line.** Same target, and the side effect disappeared once the delivery changed — so the toxicity was about the *molecule*, not the *target*. APOC3 was right all along.

### Factor XI / asundexian — a dose-and-disease miss, not a dead target
**In one line:** the safety promise (less bleeding) held up perfectly; the one trial that failed used too low a dose in a disease where this target matters least — and the same drug worked in a different disease.

- **What went wrong.** The idea behind Factor XI is a "safer blood thinner" — block clots without causing bleeds (people born short on Factor XI rarely bleed but are protected from strokes/clots). In atrial fibrillation (OCEANIC-AF), asundexian was **worse than standard-of-care at preventing strokes** (nearly 4x the events) — **but caused far less bleeding, exactly as promised** (*NEJM* 2024, PMID 39225267). So the safety half of the thesis held; efficacy failed. The likely reasons: the dose was too low (it only blocked about 92% of the enzyme, and atrial fibrillation may need near-total blockade), and atrial-fibrillation clots may simply depend less on Factor XI than other kinds of clots do.
- **The later drugs / other diseases — same target.** **Asundexian's own next trial** in stroke prevention (OCEANIC-STROKE) **succeeded** — same drug, different disease, about 26% fewer strokes with no extra bleeding. **Milvexian** is running an atrial-fibrillation trial at a deliberately higher dose (readout expected 2026). **Abelacimab** (an antibody against Factor XI) cut bleeding about 67% versus a standard blood thinner and is in Phase 3.
- **Bottom line.** The Factor XI idea held (less bleeding everywhere; a win in stroke); asundexian's atrial-fibrillation failure looks like a **dose-and-disease** miss, not a wrong target. The higher-dose milvexian trial will test that directly.

### Safety cases (TGN1412 / CD28, fialuridine / HBV polymerase)
Written up in `CASE_SCORECARD.md` under *"Safety failures — was the target hypothesis actually right?"* Both belong in Verdict 3. **TGN1412**: the *same antibody*, given at roughly 1/1000th the dose (as TAB08 / theralizumab), safely does what it was meant to do; the 2006 disaster was a dose problem plus an animal-model gap (monkeys don't carry the human immune cells the drug hit). **Fialuridine**: its target, HBV polymerase, is the backbone of every modern hepatitis-B drug (tenofovir, entecavir, lamivudine); fialuridine failed on a toxicity specific to that one molecule (it poisoned mitochondria). Right target, wrong molecule.

---

## The through-line for the section

**"Strong evidence, still failed" means three different things — and the later drug tells you
which one:**

- **No later drug at that target ever worked** (Lp-PLA2, BACE1), or the win required
  **throwing out the original rationale** (CETP: HDL out, LDL in) — the **biology was wrong**.
- **A later drug worked once it hit the right *form* at the right *stage*** (anti-amyloid:
  protofibrils, early, with proof of clearance) — the biology was **partly right**.
- **A later drug worked once the *molecule / dose / delivery* changed** (APOC3: liver-targeted
  delivery; Factor XI: higher dose and a different disease; the two safety cases) — the
  **biology was right**, and the first attempt just fumbled the execution.

The sharpest point the case studies add on top of the charts: **genetics and preclinical
evidence get you a candidate target, but they can't tell you whether a failure means the
target was wrong or just the first drug was wrong. Two things settle that — a causal test
(Mendelian randomization) and the natural experiment of whatever drug came next.**

---

## Verify before publication (flags from the research pass)
- **Trials still running (as of mid-2026), confirm before citing as pending/positive:** ZEUS
  (ziltivekimab), PREVAIL (obicetrapib), LIBREXIA-AF (milvexian), and abelacimab's Phase 3s.
  The CRP -> IL-6 "final causal proof still pending ZEUS" line is the one most likely to change.
- **PMIDs to confirm on PubMed (stated from best recall):** verubecestat EPOCH (*NEJM* 2018,
  ~29719179) and APECS (2019, ~30970186); solanezumab A4 (~37458272); the Lp-PLA2 "genetic
  invalidation" paper (*Eur Heart J* 2017); Zacho 2008 (~18971492). DOIs elsewhere are solid.
- **Interpretations, not proofs:** anacetrapib's benefit being "LDL not HDL" is the consensus
  reading, not a formal split; volanesorsen's platelet effect being "molecule not target" is
  inferred from the cleaner later drugs; APOC3 genetics predict heart benefit but no completed
  triglyceride-lowering outcomes trial has proven it yet.
