# Case-study deep dives — what they got wrong, and what a later drug proved

Reference material for the paper's Case Studies section. For each failed program we answer
two questions: **(A) what did they get wrong about the biology?** and **(B) did a later drug
hit the same target with *different* biology — and what happened?** The "later drug" column
is the discriminator: it separates *the target was wrong* from *the molecule/dose/stage was
wrong*.

Sourced via literature search (2026-07-29); trial names, effect sizes, and primary citations
verified. A handful of PMIDs and several still-running outcome trials are flagged in
**Verify before publication** at the end — dates/statuses reflect mid-2026.

The cases sort into three verdicts:

| Verdict | Meaning | Cases |
|---|---|---|
| **1. Biology wrong** | the target/biomarker doesn't drive the disease | CETP (HDL), Lp-PLA2/darapladib, CRP, BACE1 (partly) |
| **2. Partly right — wrong species/stage/molecule** | the node is causal but the approach missed | anti-Aβ mAbs (APP), γ-secretase/semagacestat |
| **3. Biology right — molecule/dose/delivery wrong** | target validated by a later, better drug | APOC3/volanesorsen, Factor XI/asundexian, + the two safety cases (TGN1412, fialuridine — see `CASE_SCORECARD.md`) |

---

## Verdict 1 — the biology was wrong (non-causal target or biomarker)

### CETP / torcetrapib — an HDL story that was really an LDL story
- **What they got wrong.** Two layers. (i) *Proximate:* torcetrapib died on a **molecule-specific off-target** — induction of adrenal aldosterone/cortisol → raised BP → excess deaths (ILLUMINATE: HDL +72%, LDL −25%, yet mortality HR 1.58; Barter, *NEJM* 2007, PMID 17984165). (ii) *Deeper:* the **HDL-raising premise itself was non-causal** — HDL-raising genetic variants do not lower MI risk (Voight, *Lancet* 2012), whereas LDL variants do.
- **Later drugs, same target.** The class became a natural experiment: **dalcetrapib** (HDL-only, dal-OUTCOMES, PMID 23126252) → **futility**; **evacetrapib** (ACCELERATE, PMID 28514624) → futility despite ~25% LDL drop; **anacetrapib** (REVEAL, NEJMoa1706444) → the **only positive** trial (9% fewer coronary events), and the benefit tracks its **LDL/apoB lowering, not HDL**. **Obicetrapib** is now explicitly repositioned as an **LDL/apoB(-and Lp(a))-lowering** drug (BROADWAY ~33% LDL drop; PREVAIL CVOT ongoing).
- **Lesson.** The pathway was pursued for the wrong reason: HDL-raising was a dead end (torcetrapib's adrenal toxicity was the acute killer; MR + dal-OUTCOMES show HDL was never causal), and CETP inhibition only earned a positive trial once **reconceived as LDL/apoB lowering**.

### Lp-PLA2 / darapladib — the cleanest "wrong target"
- **What they got wrong.** Lp-PLA2 (*PLA2G7*) is a **biomarker of plaque inflammation mistaken for a causal node.** Both Phase 3s were negative: **STABILITY** (stable CHD; White, *NEJM* 2014, PMID 24678955) missed its primary endpoint; **SOLID-TIMI 52** (post-ACS; O'Donoghue, *JAMA* 2014, PMID 25173516) was flatly null (15.0% vs 15.0%). Human genetics had already predicted this — *PLA2G7* loss-of-function (V279F null) carriers have lifelong low Lp-PLA2 but **no cardioprotection** ("genetic invalidation of Lp-PLA2," *Eur Heart J* 2017).
- **Later drugs, same target.** **None.** The target was **abandoned** for ASCVD; no successful successor. (Unlike CETP, it wasn't rescued by a reframe.)
- **Lesson.** A marker of the disease milieu, not a driver — inhibiting it moved the readout, not outcomes.

### CRP / ISIS-CRPRx — engaged the biomarker perfectly, wrong target entirely
- **What they got wrong.** The anti-CRP antisense **ISIS-CRPRx cut CRP ~77%** (RA POC, PMID 25885521) — and produced **no clinical benefit** (ACR20 no different from placebo). CRP is a **non-causal bystander**: CRP-raising alleles don't raise CHD risk (CCGC, *BMJ* 2011, PMID 21325005; Zacho, *NEJM* 2008).
- **The different (causal) target.** The lever is **upstream on the IL-6 axis**: IL-6R MR (rs2228145) predicts lower CHD (*Lancet* 2012). Drugs on the *causal* axis: **canakinumab** (anti-IL-1β, CANTOS positive, *NEJM* 2017, PMID 28845751); **ziltivekimab** (anti-IL-6, RESCUE phase 2 PMID 34015342; **ZEUS** CV-outcomes trial pending); **tocilizumab** (anti-IL-6R, approved RA). This is the tocilizumab-vs-ISIS-CRPRx pair in the gate scorecard.
- **Lesson.** Perfect biomarker engagement, zero benefit — because the drug was aimed at the readout, not the cause; the causal target was a *different* protein upstream.

### BACE1 inhibitors — the amyloid-production half of the hypothesis
- **What they got wrong.** Verubecestat cut CSF Aβ 63–81% yet gave **no benefit and cognitive *worsening*** (EPOCH, Egan *NEJM* 2018; APECS prodromal, Egan *NEJM* 2019). Two errors: (i) blocking Aβ *production* once pathology is established is insufficient; (ii) **on-target harm from BACE1 substrate pleiotropy** — BACE1 cleaves neuregulin-1, SEZ6, CHL1 (synaptic substrates), so class-wide dose-dependent cognitive worsening + hippocampal volume loss. Atabecestat also had hepatotoxicity; lanabecestat futility; elenbecestat unfavorable risk/benefit.
- **Later drugs, same target.** **None** — the entire BACE1 class was abandoned by ~2019. The field pivoted to *clearing aggregated Aβ* (antibodies), not blocking synthesis.
- **Lesson.** Lowering Aβ production is neither sufficient nor safe — the enzyme's normal substrate biology is load-bearing for cognition. (Belongs in "biology wrong" for the *production-blocking* thesis specifically.)

---

## Verdict 2 — partly right: the node is causal, the species/stage/molecule were wrong

### Anti-Aβ mAbs (APP) — solanezumab & bapineuzumab → lecanemab & donanemab
- **What they got wrong.** **Solanezumab** targeted **soluble monomeric Aβ** — the *wrong species* — and failed even in *prevention* (A4, Sperling *NEJM* 2023), isolating "wrong species," not just "too late." **Bapineuzumab** engaged plaque (lowered PET/CSF p-tau) but too weakly and with dose-limiting **ARIA**, no benefit (EXPEDITION-era, *NEJM* 2014, PMID 24450891).
- **Later drugs, same pathway, different biology — and they worked.** **Lecanemab** (anti-**protofibril**, early symptomatic AD): CLARITY-AD **27% slowing** on CDR-SB, ~50-centiloid PET reduction, FDA traditional approval 2023 (van Dyck *NEJM* 2023, PMID 36449413). **Donanemab** (anti-**pyroglutamate-N3pG plaque** epitope): TRAILBLAZER-ALZ 2 **~35% slowing**, ~80% reached plaque-clearance threshold (Sims *JAMA* 2023, PMID 37459141). Same ARIA liability as bapineuzumab, now managed with MRI.
- **Lesson.** The amyloid hypothesis is **partly vindicated** — clearing the *aggregated* species *early* with *confirmed PET clearance* modestly slows decline (~25–35%). Solanezumab (wrong species, failed in prevention) is the pivotal control isolating the necessary conditions. Benefit is real but small → amyloid an upstream contributor, not the sole driver of established dementia.

### γ-secretase / semagacestat — right pathway, unselective attack
- **What they got wrong.** IDENTITY (Doody *NEJM* 2013, PMID 23883379) was stopped because semagacestat **worsened** cognition + caused skin cancers/infections — from **Notch and other substrate** inhibition (γ-secretase is a promiscuous protease), plus paradoxical Aβ pharmacology. An unselective attack on essential proteolysis.
- **Later drugs, same target.** γ-secretase **modulators (GSMs)** — designed to *shift* cleavage toward shorter Aβ without blocking Notch — remain **experimental, no approval**. The successful path went to antibodies, not production modulation.
- **Lesson.** *This way* of engaging amyloid was wrong (unselective proteolysis); it didn't by itself resolve whether amyloid was the right target — the antibodies later did.

---

## Verdict 3 — the biology was right: molecule / dose / delivery / indication was wrong

### APOC3 / volanesorsen — a delivery problem later drugs fixed
- **What went wrong.** Volanesorsen (unconjugated 2nd-gen ASO) lowered TG ~77% in FCS (APPROACH, Witztum *NEJM* 2019) — **efficacy was never the problem** — but caused **thrombocytopenia in ~75%** of patients → **FDA rejected (2018)** / **EMA approved (2019, Waylivra)**. The platelet effect is a **modality liability** of high-dose systemic ASO, not an APOC3-target problem. Target was human-genetics-validated first: APOC3 LoF carriers have low TG and **~40% lower CHD** (Crosby & Jørgensen, *NEJM* 2014, PMID 24941081).
- **Later drugs, same target, better delivery.** **Olezarsen** (GalNAc-conjugated, hepatocyte-targeted ASO): BALANCE TG −43.5%, **no severe thrombocytopenia**, **FDA-approved Dec 2024 (Tryngolza)** — first-ever FDA approval in FCS. **Plozasiran** (GalNAc APOC3 **siRNA**): PALISADE TG ~−80%, ~83% fewer pancreatitis events, no platelet signal, **FDA-approved Nov 2025 (Redemplo)**.
- **Lesson.** Same target, safety liability vanishes when delivery changes → the toxicity was **modality-driven, not mechanism-driven**; the APOC3 target was right all along.

### Factor XI / asundexian — a dose/indication miss, not a dead target
- **What went wrong.** OCEANIC-AF (asundexian 50 mg vs apixaban in AF) stopped for **inferior efficacy** — stroke/SE HR **3.79** — *but* major bleeding HR **0.32** (Piccini *NEJM* 2024, PMID 39225267). So the **bleeding half of the FXI thesis held**; efficacy failed. Leading reads: (i) **under-dosing** (only ~92% trough FXIa inhibition; AF may need near-total suppression), (ii) AF's stasis/tissue-factor clot may be **less FXI-dependent** than atherothrombosis. Genetic rationale intact: congenital FXI deficiency → less stroke/VTE with only mild bleeding (Salomon *Blood* 2008, PMID 18268095).
- **Later drugs / other indications, same target.** **Asundexian's own OCEANIC-STROKE** (secondary stroke prevention) **hit its primary endpoint (~26% fewer recurrent strokes, no bleeding increase)** — *same drug, different indication → it worked.* **Milvexian** LIBREXIA-AF (100 mg BID, chosen for deeper suppression) **ongoing, 2026 readout**; LIBREXIA-ACS **failed**. **Abelacimab** (anti-FXI mAb): AZALEA-TIMI 71 stopped early for **~67% bleeding reduction** vs rivaroxaban; Phase 3 LILAC (AF) + cancer-VTE (ASTER/MAGNOLIA) ongoing.
- **Lesson.** The uncouple-thrombosis-from-hemostasis thesis **held** (bleeding reproducibly reduced; OCEANIC-STROKE positive); asundexian's AF failure is a **dose/indication** problem — milvexian's higher-dose LIBREXIA-AF will test it directly.

### Safety cases (TGN1412 / CD28, fialuridine / HBV pol)
Fully written up in `CASE_SCORECARD.md` → *"Safety failures — was the target hypothesis actually right?"* Both belong here: **TGN1412** (same antibody works as TAB08/theralizumab at ~1000× lower dose; failure = superagonist dose + macaque-vs-human CD28 species gap) and **fialuridine** (HBV polymerase is the backbone of modern HBV therapy — tenofovir/entecavir/lamivudine; failure = molecule-specific mtDNA/pol-γ toxicity). Right target, wrong molecule/dose.

---

## The through-line for the section

**"Strong preclinical evidence, still failed" means three different things**, and the *later
drug* tells you which:
- If **no later drug at the same target ever worked** (Lp-PLA2; BACE1 production-blocking) or the win required **abandoning the original rationale** (CETP → LDL not HDL) — the **biology was wrong**.
- If a later drug at the same node succeeded by **changing the species/stage** (anti-Aβ: protofibril + early + PET-confirmed) — the biology was **partly right**.
- If a later drug at the same target succeeded by **changing the molecule/delivery/dose** (APOC3: GalNAc; FXI: higher dose / stroke indication; the safety cases) — the **biology was right**, and the first attempt failed on execution.

This is the sharpest thing the case studies add on top of the scorecards: genetics/evidence
gets you a *candidate* target; only the downstream causal test (MR) and the *later-drug
natural experiment* tell you whether the target — or just the first molecule — was the problem.

---

## Verify before publication (uncertainty flags from the research pass)
- **Ongoing outcome trials (statuses as of mid-2026):** ZEUS (ziltivekimab CV outcomes), PREVAIL (obicetrapib CVOT), LIBREXIA-AF (milvexian), LILAC / ASTER / MAGNOLIA (abelacimab) — confirm whether any have read out before publication; the CRP→IL-6 "causal proof still pending ZEUS" line is the most likely to change.
- **PMIDs flagged as best-recall (confirm on PubMed):** verubecestat EPOCH (Egan *NEJM* 2018, ~29719179) / APECS (2019, ~30970186); solanezumab A4 (~37458272); the *PLA2G7* "genetic invalidation" *Eur Heart J* 2017 paper (PMC5460752); Zacho 2008 (~18971492). DOIs given elsewhere are solid.
- **Interpretive, not proven:** REVEAL's "benefit = LDL/apoB, not HDL" is the consensus reading, not a randomized dissection; volanesorsen's platelet effect as "modality not mechanism" is inferred from the cleaner GalNAc successors; APOC3/TG genetics predict CV benefit but no completed TG-lowering CVOT yet.
