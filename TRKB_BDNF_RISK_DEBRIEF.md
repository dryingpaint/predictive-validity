# TrkB / BDNF — Comprehensive Risk Debrief (2026-08-19)

**Memo for go/no-go decision on agonist-primary direction.** This is an unflinching assessment of what can go wrong, when we'll know, and what it would take to de-risk. Program direction: **agonist-primary** (obesity + depression indications), antagonist retained as a hedge.

---

## Executive summary: RED with one external test

**Verdict: high-risk target on a high-risk direction.** The agonist thesis rests on four independent pieces:
1. Human genetics (BDNF/NTRK2 haploinsufficiency → obesity) — **real, solid**
2. Mouse agonist rescue (BDNF KO models) — **testable, not yet done**
3. Translational species concordance (rodent efficacy → primate efficacy) — **actively falsified by TAM-163**
4. On-target safety window (seizure/sensory/oncology) — **unresolved, one live test in-flight**

The program should be **gated on the MT200605 Phase 2 safety readout** (expected Q3/Q4 2026). If that trial reports a seizure signal, stop. If it reports clean seizure safety, re-evaluate the full package then. Do not start preclinical work, mouse models, or large cell-line orders before that readout.

**If the MT200605 readout is clean, the remaining risks are high but addressable — and you'd have the first real agonist-trial data on the seizure question, which is the biggest unknown.** The sensory liability is real (TAM-163), the species reversal (rodent weight loss → primate weight gain) is real, and the path to a viable drug is genuinely narrow. But at that point you'd have external de-risking and could make an informed decision.

---

## Risk inventory, tiered by severity and when you'll know

### Tier 1 — External, in-flight, will resolve Q3/Q4 2026

**SEIZURE / EPILEPTOGENESIS RISK (HIGH)**

*What:* TrkB signaling (especially via PLCγ1) is pro-epileptogenic. Germline NTRK2 gain-of-function variants cause severe, refractory human epilepsy (PMID 39540377, 2024/2025 cohort). A chronic TrkB agonist could trigger or exacerbate seizures.

*Verification status:* **Unproven in clinical agonist trials.** TAM-163 (Pfizer, Phase 1 cachexia 2009–2011) was a single-ascending-dose study — too short to see epileptogenesis. **MT200605 (Shaanxi Micot, Phase 2 stroke, NCT07205328) is the live test:** IV 10/20/40 mg BID × 14 consecutive days, 360 patients, 32 China sites. 14 days of BID dosing is long enough that a real epileptogenic signal should surface. Stroke patients get routine seizure monitoring. **No interim results or safety reports have posted** (verified live, Aug 2026).

*When you'll know:* Primary completion expected **May 2026** (per the trial record), so results should land Q2/Q3 2026. If no seizure signal emerges from 360 patients on 14 days of active TrkB agonism, that's the strongest real-world de-risking you can get short of your own long-term preclinical study.

*If it's bad:* Seizure signal = program kill. The human genetics are too strong and the mechanism too well-understood. No amount of partial agonism or CNS restriction will fully escape a pro-epileptogenic pathway.

*If it's clean:* De-risk this single biggest unknown. Re-evaluate the full package with external validation in hand.

---

### Tier 2 — On-target toxicities, verified in humans or by mechanism, but addressable with design

**SENSORY/PAIN LIABILITY (HIGH — verified in human trials)**

*What:* TrkB is expressed in peripheral nociceptive neurons (C-fibers, Aδ fibers). TrkB signaling drives nociceptive sensitization. **TAM-163 (Pfizer agonist antibody, Phase 1 2009–2011) was terminated for "emergent safety concern of sensory symptoms."** This is on the clinical-trial record (NCT01262690), Phase 1 terminated 2011.

*Mechanism validation:* Approved pan-TRK *inhibitors* (larotrectinib, entrectinib) cause **withdrawal hyperalgesia and paresthesias** (PMID 32422171) — mirror-image proof that TrkB tone directly controls pain sensation bidirectionally. So the sensory AE is on-target and inherent to the mechanism.

*Mitigation:* This is **not** a formulation or kinetic problem. It's the biology. Partial agonism (capped ceiling effect) and CNS-restricted delivery (if the indication is central, like depression) could reduce the peripheral sensory load while maintaining efficacy. But you cannot engineer it away completely. **Any full systemic agonist will hit nociceptive sensitization as a side effect.**

*When you'll know:* Immediately upon dosing your own agonist in a PharmPK study or early IND. This is **not** a surprise — it's a known liability you manage with design, not something you avoid.

*De-risking strategy:* If pursuing this, go partial/biased agonism from the start, with explicit sensory-safety endpoints (pain sensitivity, sensory thresholds) in IND-enabling studies. Don't pretend it's not coming.

---

**ONCOLOGY OVERHANG (MODERATE — preclinical, mechanism-based)**

*What:* BDNF/TrkB signaling drives tumor growth and metastasis in multiple cancer types (TNBC brain metastasis, myeloma, cervical/lung/glioma). A chronic systemic TrkB agonist could accelerate tumor growth or metastasis, especially in a population with occult malignancy.

*Verification status:* **Preclinical only.** No clinical TrkB agonist has been dosed long enough (>few weeks) in patients to observe transformation or tumor acceleration. TAM-163 was ~2 weeks single-ascending-dose (too short). MT200605 is 14 days acute stroke (not a cancer risk population, not a long-term durability study).

*When you'll know:* Only after your own Phase 2 or longer-term preclinical. You'd need explicit cancer-risk monitoring and an IRB strategy for handling incidental malignancy.

*De-risking strategy:* Not erasable, only monitorable. Any Phase 1+ program needs explicit safety criteria: baseline and periodic malignancy screening (imaging, labs), documented informed-consent language around TrkB's known role in tumor biology, and a hard stop if any signal emerges.

---

### Tier 3 — Translational species divergence, verified in one agonist

**SPECIES REVERSAL ON BODY-WEIGHT ENDPOINT (HIGH — direct precedent)**

*What:* **TAM-163 (Pfizer TrkB agonist antibody) caused weight LOSS in rodents but weight GAIN in non-human primates** (PMID 23700410). This is the opposite direction on the exact endpoint you'd pursue for obesity. It's not a mild discrepancy — it's a directional flip in the species closest to humans.

*Mechanism:* Likely multi-factorial (CNS vs peripheral routing, satiety vs intake drive, differential receptor expression, metabolic rate). The point is: the rodent obesity indication is *not guaranteed to translate*.

*Verification status:* One real agonist tested; clear species reversal observed. This is not speculative.

*When you'll know:* Only when you dose an NHP with your own agonist and measure body weight. This is a **required gate before any human obesity claim** — you need NHP data showing weight loss, not weight gain.

*De-risking strategy:* **Early NHP PK/efficacy study is mandatory go/no-go, not optional.** If body weight goes up in NHP, the obesity thesis is dead. If it goes down, you have translational support for the mouse rescue efficacy. Budget for this early and gate hard on it.

---

### Tier 4 — Clinical translation gaps, inferred from failure history

**MODALITY FAILURE TRACK RECORD (MODERATE — historical)**

*What:* Agonists for this target have failed across four independent drug modalities over 20 years:
- **Protein (rhBDNF):** failed 1,135-patient Phase 3 in ALS (10227630), diabetic neuropathy (11800042) — proximate killer was PK/BBB, not biology, but the signal stands
- **Small molecule (7,8-DHF, LM22A-4):** **zero clinical trials in 15 years** despite 200+ papers; subsequently shown to not directly activate TrkB (Boltaev 2017 Sci Signal 28831019); 7,8-DHF reassigned as PDXP off-target (Brenner eLife 2024)
- **Prodrug (R13):** one PNAS paper, never progressed, now abandoned
- **Antibody (TAM-163):** Phase 1, terminated for sensory AEs + NHP weight reversal

*Interpretation:* When multiple independent modalities all fail, the parsimonious read is that the problem is the **target/biology**, not any one drug. Categories 1–3 above explain why: it's not an undruggability problem, it's an on-target-liability stacking problem.

*When you'll know:* If your own agonist clears sensory safety and shows NHP weight loss despite TAM-163's precedent, you've re-tested the modality hypothesis with new chemistry. But the base rate is harsh.

---

### Tier 5 — Indication-specific translational gaps

**OBESITY INDICATION — species reversal is the crux**

*Human validation:* Real, solid. BDNF/NTRK2 haploinsufficiency causes hyperphagic obesity (Yeo 2004 PMID 15494731; Gray 2006 PMID 17130481; Han 2008 NEJM PMID 18753648). Dose-response in humans: BDNF-deletion carriers ~100% obese by age 10 vs. 20% of spared-BDNF controls.

*Mouse validation:* Excellent. Bdnf+/− het, conditional KO, and trkB^fBZ hypomorph all show hyperphagia + obesity; effect is on the MC4R pathway (Xu 2003 PMID 12796784), a validated therapeutic axis (setmelanotide approved).

*Translation risk:* **TAM-163 reversal (weight loss in mouse → weight gain in NHP) is a direct, mechanism-uncertain challenge.** You cannot assume your mouse rescue translates to human obesity treatment. **NHP body-weight gate is non-negotiable.**

*The human phenotype gap:* The genetic cases are ultra-rare (dozens worldwide, all syndromic — developmental delay, hyperactivity, altered nociception). Isolated obesity is not the human phenotype. This is a small market and a pleiotropic indication (you're treating obesity but the full biology involves cognition, nociception, development).

---

**DEPRESSION INDICATION — mechanism contested, clinical validation weakest**

*Human validation:* Ketamine-TrkB mechanism (Casarotto Cell 2021 PMID 33606976) says antidepressants bind TrkB TMD and potentiate BDNF. **But the specific claims have been challenged by independent NMR structure** (Kot/Mineev Nat Commun 2024 PMID 39472452) — right-handed vs. left-handed dimer, no cholesterol-binding specificity, HNK (active ketamine metabolite) did not bind in the independent study. The originators have softened the claim themselves (Brunello/Castrén 2024 PMID 39304417, now "may…among other possible effects"). The µM-in-vitro vs nM-in-human concentration critique is still unresolved (Klett & Illes bioRxiv, preprint).

*Mouse validation:* TrkB is required for antidepressant response in FST/TST (Autry 2011 PMID 21677641; Saarelainen 2003 PMID 12514234; downstream mTORC1, Li 2010 PMID 20724638). But FST/TST are weak, handler-dependent, reproducibility-problem-ridden models. And TrkB deletion doesn't cause depression — forebrain TrkB KO is hyperactive/ADHD-like (Zörner 2003 PMID 14625139), not depressive.

*Clinical validation:* **None.** No direct TrkB agonist has ever been dosed in depressed patients. No agonist has reached Phase 1 for depression (TAM-163 was cachexia, not mood). The entire depression story is mechanistic pharmacology + animal behavior, not clinical.

*Translation risk:* Highest of the two indications. You're betting on a contested mechanism, weak animal models (FST/TST), and zero human data. If you pursue depression, you need independent human PK + biomarker validation (CSF BDNF, TrkB occupancy, mechanism engagement) in a Phase 1 before any efficacy claim.

---

### Tier 6 — Data gaps and known unknowns

**F616A chemical-genetic allele (JAX #022363) — tool is inhibition-only, not activation**

*What:* The standard TrkB loss-of-function in-vivo tool (1NM-PP1 inhibitor, analog-sensitive kinase). Useful for testing necessity and off-target kill-switch (does your agonist effect disappear when kinase is inhibited?). But it **cannot show that an agonist works** — no gain-of-function mode.

*When you need it:* As a specificity/on-target control in preclinical, not as an efficacy model. Essential for ruling out off-target effects (the 7,8-DHF problem).

---

**Partial vs. full agonism — untested, speculative**

*What:* The STATE.md thesis is that partial agonism or pathway-biased agonism (ERK/Akt preferentially over PLCγ1) could reduce seizure/sensory risk while maintaining efficacy. **This is a design hypothesis, not validated biology.**

*When you'll know:* Only after you test it. Requires:
- Quantitative TrkB activation assays (dose-response, pathway-specificity) for your candidate agonist
- In-vivo seizure monitoring (EEG) in mouse models under partial-agonist dosing
- Comparison to full agonist (TAM-163, 7,8-DHF benchmark) in the same assays

---

**Asymptomatic seizure vulnerability — untested in any TrkB agonist trial**

*What:* You don't know the baseline seizure risk in the target population. An obese or depressed patient without diagnosed epilepsy might have subclinical seizure susceptibility. TrkB agonism could unmask it.

*When you'll know:* Phase 1 EEG safety, Phase 2 seizure monitoring. MT200605 stroke population is a different risk profile than depression/obesity.

---

## Decision tree and kill criteria

### NOW (before any preclinical commitment)

**GATE 1: MT200605 Phase 2 seizure readout (expected Q3/Q4 2026)**
- **If seizure signal reported:** STOP. Do not proceed. The human genetics are too strong.
- **If clean for seizures:** CONDITIONAL PROCEED to Gate 2.
- **If no data / trial delayed:** WAIT. Do not start major preclinical work. Waiting costs nothing; starting early and then killing the program costs time and money.

---

### IF Gate 1 passes (MT200605 clean)

**GATE 2: NHP body-weight + safety PK study (6–12 months, pre-IND)**
- Dose your best agonist candidate in NHP (macaques, n=3–4 per group)
- Measure: body weight (primary), food intake, tolerability, brain penetration (if CNS indication), safety labs
- **Kill criteria:** Body weight increases, or weight is neutral (not loss). Only proceed if clear, consistent weight loss in NHP.
- **Secondary:** Measure sensory thresholds (pain sensitivity, withdrawal reflex latency) — expect sensitization; quantify the magnitude.
- **Cost:** ~$150–200k for a contract research organization study

**If NHP weight loss is observed:** De-risk the species-reversal concern. Conditional proceed to Gate 3.

---

### IF Gate 2 passes (NHP weight loss confirmed)

**GATE 3: Mechanism-specificity and partial-agonism testing (3–6 months, parallel with IND)**
- **Pathway-bias testing:** Does your agonist preferentially engage ERK/Akt over PLCγ1? (Use TrkB phospho-site-specific assays, live-cell imaging of pathway activation)
- **Partial-agonism testing:** Dose-response in neuronal systems (cortical neurons, hippocampal slices) — is there a ceiling effect? Compare to TAM-163 and 7,8-DHF benchmark.
- **In-vivo seizure modeling:** EEG in Bdnf+/− or Bdnf-conditional-KO mice under escalating agonist doses. Do seizures emerge? At what dose/exposure?
- **Kill criteria:** No evidence of pathway bias OR seizure emergence at exposures lower than the efficacy dose.

**If you find a biased agonist profile (ERK/Akt preferential, reduced PLCγ1 → PLCγ1 signaling <50% of full agonist) AND no seizure emergence in mice:** conditional proceed to IND.

---

### IF all gates pass

**GATE 4: IND-enabling package**
- Full preclinical tox, PK, bioavailability for your candidate
- IND CMC (manufacturability, stability, purity)
- Phase 1 design with explicit seizure monitoring (EEG, seizure questionnaire), sensory safety (quantitative sensory testing), cancer-risk stratification (baseline imaging, labs)
- Deprioritize depression indication for Phase 1; focus obesity or a narrow, mechanistic depression sub-phenotype if you pursue it

---

## If you decide not to proceed (the likely scenario)

**Rationale:** The TAM-163 precedent (agonist failure + NHP species reversal), the sensory liability (verified in humans, on-target), the seizure genetics (human GoF → epilepsy), the 20-year modality-failure base rate, and the weak depression mechanism (contested, no human data) stack into a high-risk, narrow-window bet. **The only external test that could materially improve your odds is MT200605's seizure readout.**

Waiting for that readout (Q3/Q4 2026) is low-cost. You avoid large preclinical commitments, you learn from another team's 14-day BID dosing, and you can re-evaluate with external data in hand.

**Recommendation if deprioritizing:** Redirect SIK3 resources (the #1 assay-quality target with real human genetics for short sleep, a live disease indication with precedent via Sleepy, no multi-modality failure history, and a robust biochemical assay). Or GALR1 as a fast, cheap, low-risk entry (proven assay, real data velocity, with eyes open that the human genetics are animal-only).

---

## Summary table: What needs to be true for this to work

| Risk | Verified? | Needed for go | When known | Mitigation |
|---|---|---|---|---|
| Seizure safety | **In-flight (MT200605)** | MT200605 clean | Q3/Q4 2026 | **HARD GATE — no proceed if signal** |
| NHP obesity translation | **No, unknown** | NHP weight loss | 6–12m pre-IND | **HARD GATE — mandatory before IND** |
| Sensory safety | **Known, real** | Partial/biased agonism | Preclinical | Design-around: partial agonism, CNS restriction |
| Pathway bias (ERK preferential) | **Unknown** | Evidence of ERK/Akt >PLCγ1 | 3–6m pre-IND | Molecule selection; in-vitro testing |
| Depression mechanism | **Contested** | Independent human validation | Phase 1 | Deprioritize or narrow indication; measure mechanism engagement |
| Indication market | **Known, small** | Accept orphan/syndromic obesity | Strategic | Obesity is small but real; depression is large but zero human data |

---

## Honest bottom line

**This is a high-risk target on a high-risk direction, made riskier by the TAM-163 precedent (species reversal) and made urgently dependent on external data (MT200605 seizure outcome).** It is not a bad target — the human genetics are real, the biology is tractable, the assay is sound — but it is a target where the hard part (demonstrating agonist works in higher species + navigating on-target toxicities) remains unproven and the base rate is poor.

**Wait for MT200605.** If seizures emerge, it's a kill. If seizures are clean, you have new external evidence and can make a fresher decision. If you decide to proceed after that gate, you are betting on being able to engineer partial/biased agonism and win a translational species bet that TAM-163 already lost once.

That is a defensible bet *if* you have the resources and risk appetite. But do not make it blind to the base rate or the precedent.
