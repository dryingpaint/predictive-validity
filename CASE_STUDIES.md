# Case studies: drugs with strong preclinical evidence that FAILED clinically

Curated examples where mechanistic biology + cell-pathway validation + animal in vivo were all robust, and the drug still failed in humans. These are the falsification instances that support the "preclinical validation is weakly predictive" thesis.

Every score below is against the rubric:
- **Mechanistic biology**: 0-3 (crystal structure, biochemistry, drugability)
- **Cell-pathway validation**: 0-3 (iPSC / organoid / primary human cell rescue)
- **Animal in vivo**: 0-3 (rodent + non-rodent efficacy with disease-relevant models)
- **Human PD engagement**: 0-3 (biomarker movement in Phase 1+)
- **Clinical outcome**: efficacy result in humans

---

## 1. BACE1 inhibitors (Alzheimer disease) — the most expensive class-failure in modern pharma

**Target:** BACE1 (β-secretase), the amyloid-precursor-protein cleavage enzyme.

**Drugs failed:** Merck's verubecestat, AstraZeneca's lanabecestat, Lilly's LY2886721, Novartis + Amgen's atabecestat/umibecestat.

**Preclinical scores:**
- Mechanistic biology: **3** — multiple crystal structures, active-site defined at atomic resolution, Km known
- Cell-pathway validation: **3** — human iPSC-derived neurons show dose-dependent Aβ reduction on BACE1 inhibition
- Animal in vivo: **3** — mouse BACE1 knockouts have reduced Aβ; drugs lower plaque burden in AD mouse models
- Human PD engagement: **3** — CSF Aβ42 reduced 50-80% in Phase 1

**Why they failed:** BACE1 has essential neurophysiological roles beyond APP cleavage (myelination via neuregulin-1 processing, synaptic function). Lowering Aβ in humans did NOT improve cognition. In several trials cognitive decline WORSENED. Merck, AZ, Lilly, and Novartis all discontinued.

**Cumulative cost:** ~$4 billion in R&D across the class.

**What preclinical could NOT predict:** the Aβ-cognition link (amyloid hypothesis) was itself the wrong causal model. Preclinical validated the mechanism of Aβ reduction, but the assumption that reducing Aβ improves cognition was wrong.

---

## 2. Torcetrapib (CETP inhibitor for cardiovascular disease) — target worked, patients died

**Target:** CETP (cholesteryl ester transfer protein).

**Drug:** Pfizer's torcetrapib. Followed by anacetrapib, dalcetrapib, evacetrapib (all failed).

**Preclinical scores:**
- Mechanistic biology: **3** — CETP crystal structure, inhibitor SAR extensively characterized
- Cell-pathway validation: **3** — human HDL particle reverse cholesterol transport measurable
- Animal in vivo: **3** — rabbit and mouse models show HDL elevation, reduced atherosclerosis
- Human PD engagement: **3** — HDL-C rose 60% as predicted
- Human genetic support: **YES** — CETP loss-of-function humans have elevated HDL and reduced CVD

**Why it failed:** ILLUMINATE trial (2006) showed 25% INCREASED mortality. Off-target aldosterone stimulation caused hypertension and adverse cardiovascular events. Follow-on CETP inhibitors (anacetrapib) removed the off-target effect, still failed on outcomes — because the causal HDL→CVD link is more complex than the epidemiology suggested (recent Mendelian randomization showed HDL levels themselves not causal for CVD reduction).

**What preclinical could NOT predict:**
- Off-target aldosterone-mediated hypertension (torcetrapib-specific)
- The fundamental Mendelian randomization result — CETP LoF humans have high HDL but their reduced CVD risk comes from LDL-lowering, not HDL. Standard preclinical models can't test causal genetic architecture directly.

---

## 3. Semagacestat (γ-secretase inhibitor, Alzheimer disease) — biomarker moved, patients got worse

**Target:** γ-secretase complex (presenilin PS1/PS2 catalytic subunit).

**Drug:** Lilly's semagacestat.

**Preclinical scores:**
- Mechanistic biology: **3** — γ-secretase structure resolved, mechanism (regulated intramembrane proteolysis) well-characterized
- Cell-pathway validation: **3** — direct reduction of Aβ in neuronal cultures + iPSCs
- Animal in vivo: **3** — mouse models show plaque reduction with γ-secretase inhibition
- Human PD engagement: **3** — CSF Aβ42 reduced dose-dependently in Phase 1

**Why it failed:** IDENTITY trial (2010) stopped early. Semagacestat patients showed WORSE cognitive decline than placebo, plus skin cancer, weight loss, GI toxicity. γ-secretase also cleaves Notch — Notch signaling disruption causes systemic toxicity.

**What preclinical could NOT predict:** on-target toxicity in humans. Notch pathway involvement was known in preclinical work but the therapeutic window in humans was too narrow. Similar mechanism issues with tarenflurbil (γ-secretase modulator, failed Phase 3).

---

## 4. Solanezumab + bapineuzumab (anti-Aβ monoclonal antibodies) — biomarker moved, no cognitive benefit

**Target:** Amyloid-β peptide, extracellular clearance.

**Drugs:** Lilly's solanezumab (soluble Aβ), Pfizer/Elan's bapineuzumab (plaque-binding). Preceded aducanumab (approved 2021 but withdrawn), lecanemab (approved 2023, marginal benefit), donanemab (approved 2024).

**Preclinical scores:**
- Mechanistic biology: **3** — Aβ epitope binding, Fc-mediated microglial clearance mechanism
- Cell-pathway validation: **3** — iPSC neuron cultures show Aβ oligomer neurotoxicity
- Animal in vivo: **3** — Aβ transgenic mouse models show plaque reduction, some cognitive improvement
- Human PD engagement: **2-3** — amyloid PET imaging showed target engagement, but effect sizes modest for solanezumab

**Why they failed:** Multiple Phase 3 trials (EXPEDITION 1, 2, 3 for solanezumab; multiple for bapineuzumab) showed no cognitive benefit despite biomarker movement. Late-stage AD patients had already accumulated neurodegeneration. Even successful successor drugs (lecanemab, donanemab) show ~30% slowing of decline, not reversal.

**What preclinical could NOT predict:** the amyloid cascade hypothesis was partially right (recent successful trials suggest earlier treatment helps), but the effect size expected from preclinical models overpredicted human clinical benefit. Mouse AD models are transgenic overexpression models — different biology than sporadic human AD.

---

## 5. TGN1412 (CD28 superagonist antibody) — animal safe, human catastrophe

**Target:** CD28 (T-cell co-stimulation receptor), superagonist mechanism.

**Drug:** TeGenero's TGN1412 (later theralizumab). Halted after Phase 1.

**Preclinical scores:**
- Mechanistic biology: **3** — CD28 structure and superagonist binding mechanism characterized
- Cell-pathway validation: **3** — human T-cell activation profile characterized in vitro
- Animal in vivo: **3** — cynomolgus monkeys received 500× human starting dose without adverse effects; rat and mouse studies clean

**Why it failed:** Phase 1 first-in-human trial (2006). All 6 volunteers developed catastrophic cytokine release syndrome within 90 minutes of a 0.1 mg/kg dose (500× LOWER than the safe monkey dose). All 6 ICU'd; several suffered permanent tissue damage.

**Root cause:** CD28 on human effector memory T-cells (CD4+ CD28+) signals differently than on monkey T-cells. Cynomolgus CD28+ T-cells are more rare and less prone to superagonist activation. In vitro assays that used isolated T-cells missed the effect because tissue-context is required for cytokine cascade.

**What preclinical could NOT predict:** species-specific immunological pharmacology. Not detectable in ANY standard preclinical model at the time. Led to the FDA's Minimum Anticipated Biological Effect Level (MABEL) approach for biologics dosing.

---

## 6. Fialuridine (nucleoside analog for chronic hepatitis B) — 5 deaths

**Target:** Hepatitis B viral polymerase (via nucleoside incorporation).

**Drug:** Fialuridine (FIAU). NIH-sponsored trial, 1993.

**Preclinical scores:**
- Mechanistic biology: **3** — nucleoside analog mechanism established
- Cell-pathway validation: **2** — HBV replication inhibition in hepatocyte cell lines
- Animal in vivo: **3** — mouse, rat, dog, monkey tox studies all clean — some for extended dosing

**Why it failed:** Phase 2 trial of 15 patients (1993). 7 patients developed severe hepatotoxicity + lactic acidosis. 5 died. 2 required emergency liver transplants.

**Root cause:** Fialuridine is transported into mitochondria via a human-specific transporter (equilibrative nucleoside transporter 1, hENT1). Rodents and dogs lack the same transport, so fialuridine doesn't accumulate in their mitochondria. Human hepatocyte mitochondrial DNA polymerase is inhibited → mitochondrial dysfunction → lactic acidosis + hepatic necrosis.

**What preclinical could NOT predict:** species-specific pharmacokinetics for a nucleoside. NIH investigation concluded the toxicity was undetectable in any available preclinical model.

---

## What these 6 cases share

1. **All had strong scores on mechanistic biology, cell-pathway validation, and animal in vivo evidence.** Composite would score 8-12 out of 12.
2. **All had at least some human PD engagement evidence** — biomarker movement in the direction expected.
3. **All failed catastrophically or on efficacy despite the strong preclinical signature.**
4. **The root cause in each case was unmeasurable in preclinical models:**
   - BACE1 / γ-secretase / anti-Aβ — wrong causal model (amyloid → cognition)
   - CETP — human genetic architecture more complex than epidemiology
   - TGN1412 — species-specific immunology
   - Fialuridine — species-specific pharmacokinetics
5. **Cost of these class-failures:** rough total ~$10-15 billion in R&D across these 6 examples, based on published estimates.

**The pattern:** strong preclinical scores can be individually correct but collectively fail when the underlying causal hypothesis is wrong. Preclinical models test the mechanism WORKS as predicted, not whether the mechanism DRIVES the disease outcome in humans. That second question is what human genetics + human clinical readouts answer.

**Reference in report:** these cases falsify the naive "high preclinical evidence = high approval odds" model. Consistent with the null cell-pathway / animal-in-vivo odds ratios in the current data (§2 of REPORT.md).
