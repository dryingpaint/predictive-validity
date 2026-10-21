# Predictive Validity in Drug Development

<!-- Rendered by `python -m report.render` from report/output/*/numbers.json.
     Every number in braces comes from the generated outputs; edit prose here, never the numbers. -->

## Introduction

The number of new drugs approved per billion dollars of inflation-adjusted R&D spending halved roughly every nine years from 1950 to 2010, an ~80-fold fall ([Scannell et al. 2012](https://doi.org/10.1038/nrd3681)); the decline has flattened since about 2010 ([Ringel et al. 2020](https://doi.org/10.1038/d41573-020-00059-3)). Only 7.9% of drug development programs (drug–indication pairs) that enter Phase 1 reach FDA approval, and 6.8% for novel drugs ([Thomas et al. 2021, BIO](https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf)). More than nine in ten programs that enter the clinic never reach approval, and we can see little of why.

Existing analyses offer a few data points:

* Nelson et al. (2015) estimated that human genetic support could roughly double the chance of success in clinical development ([Nelson et al. 2015](https://doi.org/10.1038/ng.3314)). With a decade more genetic data, target–indication pairs with genetic support were 2.6 times as likely to progress from Phase 1 to launch ([Minikel et al. 2024](https://doi.org/10.1038/s41586-024-07316-0)).
* Of 174 Phase 2 and Phase 3 failures in 2013–2015 whose sponsors gave a reason, 52% were for efficacy and 24% for safety ([Harrison 2016](https://doi.org/10.1038/nrd.2016.184)).
* A review of AstraZeneca's 2005–2010 pipeline distilled five technical determinants of success, the "5Rs": right target, tissue, safety, patient and commercial potential ([Cook et al. 2014](https://doi.org/10.1038/nrd4309)). After the company adopted the framework, its success rate from candidate nomination to Phase 3 completion rose from 4% to 19% ([Morgan et al. 2018](https://doi.org/10.1038/nrd.2017.244)).

Scannell and colleagues called the decline Eroom's Law (Moore's Law backwards) and attributed it to four causes ([Scannell et al. 2012](https://doi.org/10.1038/nrd3681)):

1. **"Better than the Beatles":** each new drug must beat a growing catalogue of cheap, effective generics.
2. **The cautious regulator:** the bar for safety and evidence keeps rising.
3. **"Throw money at it":** the tendency to add people and money to R&D.
4. **The "basic research–brute force" bias:** overestimating how much molecular biology and high-throughput screening raise the chance that a molecule works in the clinic.

[Scannell and Bosley (2016)](https://doi.org/10.1371/journal.pone.0147215) later used decision theory to show that a model's *predictive validity*, meaning how well its output tracks the clinical outcome, matters far more than its throughput, and proposed that a fall in the predictive validity of the industry's screening and disease models explains much of the decline.

This report rebuilds both questions from primary records. We took every interventional drug or biological study on ClinicalTrials.gov (222,915 studies, snapshot of 2026-10-20), resolved each intervention to the molecular entity it contains and each condition to a MONDO disease, and joined them to every FDA approval we could document: Drugs@FDA applications, 5,034 approved uses read from 2015–2026 approval letters, current labels, and 177 CBER biologics applications rebuilt from the agency's yearly pages and letters. The unit throughout is a *development program*: one molecular entity developed for one indication. An entity counts toward a program only in trials where it is the investigational agent, not a comparator or background therapy.

The report has two parts:

1. **Industry failure modes.** Phase transitions, likelihood of approval (LOA) and the reasons programs stop, for programs that entered each phase in 2015–2025: an updated companion to BIO's *Clinical Development Success Rates 2011–2020*.
2. **Predictive power of preclinical evidence.** For programs aimed at a human protein target, whether the target had human genetic, somatic, animal-model, expression, pathway or functional-screen evidence for the program's disease, as known before the program entered the phase, and how much each line changes the chance of approval.

Every classification in the pipeline (entity resolution, disease mapping, trial purpose and roles, approvals, stop reasons, trial outcomes, targets) was made by an LLM reading the source record, recorded with its prompt and input, and checked against an independent re-derivation of a seeded sample (Appendix).


## A history of drug development

Over the past century, drug development moved from natural observation and phenotypic screening to target-based and genetically grounded hypotheses. Each era narrowed the unit of the biological hypothesis, from a whole-organism effect to a target in a specific patient context.

| Period | Technological developments | Biological hypothesis | Examples |
| :---- | :---- | :---- | :---- |
| Pre-1900 to 1930s | Observation, natural products, physiology | Therapeutic effect or organismal phenotype | Morphine, quinine, digitalis, aspirin |
| 1900s–1960s | Quantitative pharmacology and biochemistry | Receptor activity, enzyme, metabolic pathway | Sulfonamides, receptor theory, enzyme inhibitors |
| 1950s–1980s | Systematic medicinal chemistry | Desired pharmacological mechanism | β-blockers, H2 antagonists, antimetabolites |
| 1970s–1990s | Recombinant DNA and molecular cloning | Named gene and protein | Recombinant insulin, cloned GPCRs, channels, kinases |
| 1990s–2000s | Genomics, HTS, automation | Target plus compound library | Imatinib and kinase programs, genomic target portfolios |
| 2000s–2010s | Human genetics and functional genomics | Target–disease association | GWAS, RNAi, CRISPR, dependency maps |
| 2010s–present | Multimodal evidence integration and predictive modeling | Target–indication–mechanism–patient context | Open Targets, gnomAD, single-cell perturbation, AlphaFold |

## Industry failure modes

For development programs that entered a phase in 2015–2025 and were developed in the US, the likelihood of FDA approval from Phase 1 is 9.5% (95% CI 8.4%–10.5%), against BIO's 7.9% for 2011–2020 (6.8% for novel drugs). Across all industry programs registered on ClinicalTrials.gov, including those run only outside the US, it is 5.6%. Most programs stop without a stated reason: of 7,052 programs that stopped, 54% left no stated reason and no posted or published result, and 20% record an efficacy, safety or pharmacokinetic reason.

### How programs are counted

* **Trial:** a registered interventional study listing Early Phase 1 to Phase 3. A Phase 1/2 trial counts as Phase 2 and a Phase 2/3 trial as Phase 3. Withdrawn trials never enrolled and are left out.
* **Molecular entity:** the active substance, whatever its brand, sponsor code, dose or salt, resolved to its FDA UNII substance where one exists. Biosimilars fold into their reference entity.
* **Disease:** the MONDO term for the condition the trial treats, without line, stage, biomarker or age qualifiers.
* **Program:** one entity developed for one indication. An indication groups the entity's MONDO diseases the way a sponsor runs them as programs (prostate cancer with castration-resistant and metastatic prostate carcinoma; diffuse large B-cell and follicular lymphoma kept apart), decided by an LLM for each entity. An entity belongs to a program only in trials where it is the investigational agent, not a comparator or background therapy. Each industry trial's purpose is classified first: bioequivalence, formulation, food-effect, interaction and other product-support studies (10,770 trials) belong to no program; a first-in-human study or a basket across several diseases counts as Phase 1 only for the program the sponsor pursued next.
* **Phase entry and outcome:** a program enters a phase with its first industry-sponsored trial of that phase. It *advanced* when a later-phase trial in its disease started (any sponsor) or the FDA approved the entity for the disease; it is *suspended* when none of its trials has been active within 24 months of the snapshot (2026-10-20); otherwise it is still running and *censored*. Programs whose entity was already approved for the disease are lifecycle programs and are left out. As in BIO's report, each phase's success rate is advanced ÷ (advanced + suspended), and LOA is their product.
* **Approval:** FDA approval of the entity for the program's disease, a subtype or population of it, or a broader approved class that includes it, judged from the dated approval letters, original-approval dates and labels of every application of the entity (CDER and CBER).

17,005 programs of 10,265 entities entered at least one phase in 2015–2025.

### Phase transitions

| Transition | All programs (95% CI) | Developed in the US (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- |
| Phase 1 → Phase 2 | 55.1% (53.5–56.7), n=6,188 | 59.1% (57.0–61.3), n=4,009 | 52.0% |
| Phase 2 → Phase 3 | 29.5% (28.0–31.1), n=4,639 | 32.3% (30.2–34.2), n=2,984 | 28.9% |
| Phase 3 → Approval | 34.5% (31.8–37.1), n=1,529 | 49.6% (46.2–53.1), n=1,036 | 52.4% |
| **Phase 1 → Approval (LOA)** | **5.6%** (5.0–6.3) | **9.5%** (8.4–10.5) | **7.9%** (novel drugs 6.8%) |

Programs developed in the US, the closest match to BIO's FDA-focused Biomedtracker programs, advance from Phase 1 at 59.1% (BIO 52.0%), from Phase 2 at 32.3% (BIO 28.9%) and from Phase 3 to approval at 49.6% (BIO 52.4%). Phase 2 remains the steepest single drop. Across all registered industry programs the Phase 3 rate falls to 34.5%, because many programs run only outside the US end in approvals elsewhere, which this report does not count.

The likelihood of approval depends on choices a registry-based count has to make, and the table below shows how far each moves it. It is most sensitive to how long a program must be idle before it counts as suspended: 4.0% with a 12-month window and 8.1% with 36 months (24 in the headline). If every shared trial (a healthy-volunteer study, a basket) counted as the start of every later indication of the drug, LOA would rise to 11.1%, mostly by crediting indication expansions begun at Phase 2 with a Phase 1 success. Restricting to programs that entered a phase in 2015–2019, which have had at least six years to resolve, changes little (9.5% for US-developed programs). Vaccines are left out of the headline figures: annual and variant strain updates are licensed as supplements to the parent product, so registry entities for updated formulations never reach an approval of their own (LOA with vaccines included: 5.0%).


| Cohort or definition | Ph1→2 | Ph2→3 | Ph3→approval | LOA (95% CI) |
| :---- | :---- | :---- | :---- | :---- |
| All programs | 55.1% | 29.5% | 34.5% | 5.6% (5.0–6.3) |
| Programs with a US site in the phase | 59.1% | 32.3% | 49.6% | 9.5% (8.4–10.5) |
| Entity not yet FDA-approved at phase entry | 56.1% | 30.1% | 34.7% | 5.9% (5.2–6.6) |
| Entity already FDA-approved for another disease | 49.9% | 24.7% | 33.6% | 4.1% (2.9–5.7) |
| Suspension lag 12 months | 50.9% | 25.7% | 30.6% | 4.0% (3.5–4.5) |
| Suspension lag 18 months | 52.7% | 27.2% | 32.2% | 4.6% (4.1–5.2) |
| Suspension lag 36 months | 59.7% | 34.0% | 39.7% | 8.1% (7.2–9.0) |
| Uncertain approvals counted as approved | 55.1% | 29.5% | 34.5% | 5.6% (5.0–6.2) |
| Shared trials mark entry for every program of the entity | 69.1% | 42.9% | 37.4% | 11.1% (9.7–12.5) |
| Including vaccines | 53.9% | 29.0% | 31.9% | 5.0% (4.5–5.6) |
| Phase entry 2015-2019 (at least six years of follow-up) | 53.4% | 26.3% | 38.2% | 5.4% (4.6–6.2) |
| Phase entry 2015-2019, developed in the US | 58.9% | 31.7% | 50.7% | 9.5% (8.1–10.8) |

### Why programs stop

Each suspended program takes one reason from the industry trials of the phase it stopped in, in this order: an efficacy reason stated by the sponsor, a primary endpoint missed in posted or published results, a safety signal, a pharmacokinetic or formulation problem, an explicit business or strategic reason, a bare "sponsor decision", an enrollment, operational or regulatory reason, a positive primary readout without advancement, and finally no reason at all.

| Reason | Phase 1 | Phase 2 | Phase 3 |
| :---- | :---- | :---- | :---- |
| PK, dose or formulation | 1% (20) | 0% (8) | 0% (0) |
| business or strategic (explicit) | 14% (381) | 9% (287) | 6% (63) |
| completed, no results posted, no reason stated | 58% (1,622) | 30% (977) | 23% (226) |
| efficacy: primary endpoint not met | 0% (8) | 19% (633) | 17% (170) |
| efficacy: stated | 3% (78) | 6% (206) | 12% (119) |
| enrollment, operational or regulatory | 3% (76) | 6% (185) | 4% (42) |
| positive readout, not advanced | 0% (13) | 9% (304) | 19% (188) |
| safety | 2% (54) | 2% (81) | 3% (33) |
| sponsor decision, unspecified | 4% (118) | 4% (135) | 3% (30) |
| stopped, no reason stated | 15% (408) | 14% (456) | 13% (131) |

![Why suspended programs stopped, by phase](report/output/figures/failure_modes_by_phase.png)

The registry rarely says why a program stopped. In Phase 1, 73% of stopped programs left neither a stated reason nor a result, which is expected: Phase 1 trials seldom post results and companies seldom explain pausing early assets. In Phase 2 and Phase 3 the share without a reason falls to 44% and 36%. Efficacy is the recorded reason for 26% of programs that stopped in Phase 2 and 29% of those that stopped in Phase 3: the sponsor said so, or the posted or published primary endpoint was missed. Safety accounts for 2% and 3%: among Phase 2 and Phase 3 stops with an efficacy or safety reason, safety is 9% and 10%, below the 24% Harrison (2016) found among 2013–2015 failures with a disclosed reason. Either registry records under-report safety stops, or company disclosures over-represent them.

At the level of individual trials, the 5,557 industry trials started in 2015–2025 that stopped early or were withdrawn with a reason give: an explicit business, portfolio or competitive reason 36%, a bare "sponsor decision" 19%, efficacy 14%, enrollment or operations 14% and safety 4%. The draft's single 44% "commercial or strategic" category mixed these two kinds of statement; a "sponsor decision" with no reason may or may not hide an efficacy result, and the record cannot tell.

Finally, 19% of Phase 3 programs that stopped short of FDA approval had met their primary endpoint. In a sample we read, most of them were approved outside the US (Japan, China, Korea, Russia) or received a complete response letter from the FDA: a positive Phase 3 readout is necessary but not sufficient for US approval.


### By disease area and modality

| Disease area | All programs, LOA (95% CI) | Entities | Developed in the US, LOA (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- | :---- |
| Hematology | 17.6% (11.5–25.1) | 261 | 25.4% (16.3–36.1) | 23.9% |
| Metabolic | 16.6% (11.3–22.7) | 392 | 26.6% (18.5–34.8) | 15.5% |
| Oncology | 12.7% (10.3–15.3) | 2,579 | 16.2% (12.8–19.4) | 5.3% |
| Endocrine | 9.9% (5.5–15.3) | 316 | 25.8% (16.3–36.4) | 6.6% |
| Autoimmune | 9.4% (6.2–12.6) | 669 | 12.1% (8.0–16.9) | 10.7% |
| Psychiatry | 8.8% (4.9–13.0) | 275 | 12.1% (6.9–18.3) | 7.3% |
| Allergy | 8.6% (3.1–15.5) | 125 | 14.8% (5.2–26.4) | 10.3% |
| Neurology | 6.8% (4.9–8.9) | 897 | 13.2% (10.1–16.8) | 5.9% |
| Respiratory | 6.7% (3.9–10.0) | 481 | 8.6% (5.1–13.0) | 7.5% |
| Other | 5.3% (3.6–7.2) | 900 | 8.6% (6.0–11.3) | 13.0% |
| Ophthalmology | 4.6% (2.5–7.1) | 416 | 6.7% (3.5–10.5) | 11.9% |
| Cardiovascular | 3.5% (1.5–6.1) | 361 | 10.3% (4.8–18.0) | 4.8% |
| Infectious disease | 2.7% (1.8–3.7) | 921 | 4.6% (2.9–6.4) | 13.2% |
| Gastroenterology | 2.2% (0.8–3.9) | 340 | 5.6% (2.0–9.9) | 8.3% |
| Urology | 0.9% (0.0–3.1) | 70 | 0.0% (0.0–0.0) | 3.6% |

| Modality | All programs, LOA (95% CI) | Entities | Developed in the US, LOA (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- | :---- |
| siRNA / RNAi | 26.4% (11.9–41.9) | 142 | 32.8% (15.4–54.0) | 13.5% |
| Multispecific antibody | 21.3% (11.3–31.9) | 491 | 24.8% (13.9–35.8) | – |
| Antibody–drug conjugate | 19.0% (9.5–30.9) | 412 | 18.2% (7.6–30.3) | 10.8% |
| Monoclonal antibody | 11.4% (8.9–14.2) | 1,292 | 14.9% (11.3–18.9) | 12.1% |
| Antisense oligonucleotide | 10.6% (4.1–20.3) | 114 | 17.4% (6.8–30.6) | 5.2% |
| CAR-T | 9.5% (4.5–15.5) | 348 | 21.7% (10.2–35.8) | 17.3% |
| Peptide | 7.9% (4.1–12.0) | 347 | 12.8% (7.2–19.3) | 8.0% |
| Gene therapy | 5.6% (1.6–12.8) | 239 | 7.0% (1.9–16.1) | 10.0% |
| Small molecule | 4.7% (4.0–5.4) | 5,204 | 8.1% (7.0–9.4) | 7.5% |
| Protein | 3.4% (2.0–5.2) | 525 | 6.0% (3.5–8.9) | 9.4% |
| Radioligand | 2.4% (0.0–17.8) | 113 | 2.2% (0.0–19.0) | – |
| Other cell therapy | 1.1% (0.3–2.3) | 533 | 2.2% (0.7–5.1) | – |
| Other oligonucleotide | 0.9% (0.0–4.4) | 44 | 1.9% (0.0–8.5) | – |
| Microbiome or live biotherapeutic | 0.3% (0.0–1.3) | 96 | 1.2% (0.0–4.7) | – |
| Other | 0.2% (0.0–0.6) | 298 | 1.0% (0.0–3.8) | – |

![Likelihood of approval by disease area](report/output/figures/loa_by_area.png)

![Likelihood of approval by modality](report/output/figures/loa_by_modality.png)

Disease areas rank differently from BIO's: the rank correlation with BIO's LOA across the 15 areas is 0.30 for all programs and 0.14 for US-developed ones. Hematology and metabolic programs reach approval most often in both reports (17.6% and 16.6% across all programs), and urology programs least. Among US-developed programs, oncology (16.2%) and endocrine programs (25.8%) come out far above BIO's 5.3% and 6.6%; for oncology, the 2015–2025 window holds the wave of immunotherapy, antibody–drug conjugate and bispecific approvals, and an approval in a cancer subtype counts for the program's cancer. Infectious disease (4.6%) sits far below BIO's 13.2%, largely because many registered anti-infective and COVID-19 programs, including US-run ones, were never approved; ophthalmology (6.7%) and gastroenterology (5.6%) also fall below BIO's 11.9% and 8.3%. Among modalities, RNA interference, multispecific antibodies and antibody–drug conjugates reach approval most often across all programs (26.4%, 21.3% and 19.0%), and among the classes BIO also reports, non-antibody proteins (3.4%) and small molecules (4.7%) least. The modality ordering agrees with BIO's only loosely (rank correlation 0.50), mostly because CAR-T ranks lower here (9.5% against BIO's 17.3%) and antisense oligonucleotides higher. Strata with few programs have wide intervals.



## Predictive power of preclinical evidence

Human genetic evidence linking a program's target to its disease is the clearest preclinical signal of success. Programs whose target had it before they entered the phase reached FDA approval 3.48 times as often as programs without it (27.5% against 7.9%; 95% CI 2.64–4.44), the likelihood rises with the strength of the evidence, and the association holds at every phase after accounting for disease area, modality, novelty and era. Somatic driver and mouse-model evidence carry weaker signals; targets essential in every cancer cell line are a liability. Yet as a predictor of which individual programs will be approved, the evidence adds little to what disease area and modality already say, because most programs have none of it.


### Evidence lines and how they are matched

Each program aimed at a human protein (the entity's primary targets, resolved by an LLM from the entity's mechanism records and trial descriptions) is scored for the evidence its targets had **for the program's disease** in Open Targets Platform 26.09, **as of the year before the program entered the phase**. A target–disease association counts for the program's disease when the evidence disease is the same MONDO term, a subtype of it, or similar to it (Lin similarity ≥ 0.8, the criterion Minikel et al. used). Open Targets publishes a yearly series of each association's score, so evidence is taken as it stood before phase entry, not as it stands today. Evidence lines:

* **Human germline genetics:** GWAS credible sets (with locus-to-gene scores), gene burden tests, ClinVar, Genomics England PanelApp, Orphanet, Gene2Phenotype, ClinGen and UniProt; split into GWAS and rare-variant/Mendelian sources.
* **Somatic drivers:** COSMIC Cancer Gene Census, IntOGen and ClinVar somatic.
* **Mouse models:** IMPC phenotypes. **Expression:** differential expression in the disease (Expression Atlas). **Pathways:** Reactome. **Functional screens:** CRISPR screens.
* **Target-level properties** that are not disease-specific: loss-of-function intolerance (gnomAD LOEUF < 0.35) and pan-essentiality across DepMap cell lines.

Sources that encode clinical outcomes or literature co-mention (ChEMBL clinical precedence, Europe PMC) are not used. Vaccines, cell and gene therapies and other entities without a single human protein target fall outside this analysis, so its programs reach approval more often than the Section 1 cohort as a whole. Of the 10,162 programs on 1,660 targets scored, 15.0% of Phase 1 entrants had human genetic evidence for their disease at entry.

### Relative success

*Relative success* is the LOA of programs with the evidence divided by the LOA of programs without it (Nelson et al. 2015; Minikel et al. 2024). The 95% intervals resample targets, since programs on the same target are not independent.

| Evidence (for the program's disease, as of phase entry) | Programs with it | LOA with / without | Relative success (95% CI) |
| :---- | :---- | :---- | :---- |
| Rare-variant / Mendelian (ClinVar, Orphanet, G2P, ClinGen, burden) | 1,014 | 30.4% / 8.7% | 3.51 (2.59–4.58) |
| Human genetics (any germline source) | 1,682 | 27.5% / 7.9% | 3.48 (2.64–4.44) |
| GWAS credible set | 869 | 22.7% / 9.3% | 2.42 (1.60–3.36) |
| Somatic driver (COSMIC CGC, IntOGen, ClinVar somatic) | 1,704 | 21.1% / 9.0% | 2.33 (1.59–3.19) |
| Pathway (Reactome) | 211 | 22.5% / 10.0% | 2.25 (1.31–3.54) |
| Mouse model (IMPC) | 1,990 | 14.8% / 9.1% | 1.62 (1.19–2.14) |
| Differential expression in disease (Expression Atlas) | 1,383 | 14.4% / 9.7% | 1.48 (0.96–2.05) |
| LoF-intolerant target (gnomAD LOEUF < 0.35) | 1,903 | 9.3% / 10.5% | 0.89 (0.56–1.41) |
| Pan-essential (DepMap) | 570 | 3.1% / 10.7% | 0.29 (0.09–0.60) |

![Relative success by evidence line](report/output/figures/relative_success_by_evidence.png)

Rare-variant and Mendelian evidence (3.51×) and GWAS evidence (2.42×) both carry the genetic signal, in line with Minikel et al. (2024), who found 2.6× from Phase 1 to launch with Mendelian evidence stronger than GWAS. Somatic driver evidence (2.33×), mouse phenotypes (1.62×) and Reactome pathways (2.25×, from only 211 programs) also associate with success; differential expression in the disease does not clearly (1.48×, interval spanning 1). Loss-of-function-intolerant targets show no penalty (0.89×), while pan-essential targets reach approval less than a third as often (0.29×), mostly oncology small molecules aimed at machinery every cell needs (mTOR, tubulin, topoisomerases, histone deacetylases, WEE1 and ATR, BET proteins). CRISPR-screen evidence covered too few programs (77) to estimate.

Two checks bear on whether this reflects foresight rather than hindsight. Evidence is taken as it stood in Open Targets' yearly series before the program entered the phase, so later discoveries do not count. Counting all evidence known by 2026 instead weakens the genetic relative success to 2.98×: what was known in advance is more telling than what was found afterwards. And restricting matches to diseases similar to the program's (Lin ≥ 0.8, Minikel's criterion, without the subtype rule) gives 3.53×.


### Genetic dose–response

| Human genetic support (Open Targets score, as of phase entry) | Programs | Targets | LOA (95% CI) |
| :---- | :---- | :---- | :---- |
| None | 8,558 | 1,477 | 7.9% (6.4–9.8) |
| Lower third (> 0.00 to 0.61) | 670 | 275 | 19.6% (13.5–26.5) |
| Middle third (> 0.61 to 0.87) | 509 | 167 | 31.9% (21.4–41.1) |
| Upper third (> 0.87) | 571 | 204 | 33.9% (27.3–41.9) |

![Likelihood of approval by strength of human genetic support](report/output/figures/genetic_dose_response.png)

### What each line adds once the others are known

Programs with genetic evidence differ from programs without it in disease area, modality and era, and the evidence lines overlap. The table gives, for each phase, the relative risk of advancing for programs with each line, from one Poisson model containing every line together with disease area, modality, entity novelty and entry period (standard errors clustered by target).

| Evidence | Phase 1 → next | Phase 2 → next | Phase 3 → next |
| :---- | :---- | :---- | :---- |
| GWAS credible set | 1.06 (1.00–1.13) | 1.58 (1.34–1.85) | 1.06 (0.78–1.45) |
| Rare-variant / Mendelian (ClinVar, Orphanet, G2P, ClinGen, burden) | 1.08 (0.99–1.19) | 1.40 (1.19–1.66) | 1.61 (1.31–1.98) |
| Somatic driver (COSMIC CGC, IntOGen, ClinVar somatic) | 1.03 (0.93–1.14) | 1.12 (0.88–1.42) | 1.12 (0.84–1.49) |
| Mouse model (IMPC) | 0.97 (0.91–1.04) | 0.97 (0.84–1.13) | 0.96 (0.80–1.15) |
| Differential expression in disease (Expression Atlas) | 1.00 (0.92–1.08) | 1.04 (0.87–1.26) | 0.89 (0.70–1.12) |
| Pathway (Reactome) | 1.09 (0.95–1.24) | 0.90 (0.68–1.21) | 1.12 (0.81–1.54) |
| LoF-intolerant target (gnomAD LOEUF < 0.35) | 0.99 (0.89–1.11) | 1.21 (1.00–1.46) | 0.99 (0.77–1.26) |
| Pan-essential (DepMap) | 0.79 (0.64–0.96) | 0.65 (0.45–0.94) | 0.70 (0.39–1.25) |

One evidence line at a time, with the same adjustments, human genetic evidence raises the chance of advancing by 1.09× in Phase 1, 1.70× in Phase 2 and 1.48× in Phase 3: the effect sits where efficacy is first tested. In the joint model, GWAS and rare-variant evidence each keep an independent effect at Phase 2, rare-variant evidence also at Phase 3, and pan-essentiality keeps its penalty at Phases 1 and 2; somatic, mouse-model, expression and pathway evidence lose their association once genetics and the covariates are in the model, consistent with their univariate signal riding along with genetic support and with disease area.


### Does the evidence predict which programs reach approval?

We followed programs that entered Phase 1 in 2008–2016 for ten years (3,085 programs, 199 approved), with every feature frozen at entry, and fitted logistic models on disease area, modality, novelty and entry year alone, and with the evidence lines added. Performance is measured on held-out targets (out-of-fold predictions averaged over 20 repetitions of 5-fold cross-validation grouped by target and stratified by outcome; a single split moves the AUC by several points) and on a temporal split (trained on 2008–2012 entries, tested on 2013–2016).

| Validation | Features | AUC (95% CI) | PR-AUC (base rate) | Programs (approved) |
| :---- | :---- | :---- | :---- | :---- |
| Held-out targets | Area, modality, novelty, year | 0.551 (0.492–0.601) | 0.106 (0.065) | 3,085 (199) |
| Temporal (2013–2016) | Area, modality, novelty, year | 0.578 (0.480–0.653) | 0.110 (0.063) | 1,559 (98) |
| Held-out targets | … plus all evidence lines | 0.590 (0.528–0.648) | 0.127 (0.065) | 3,085 (199) |
| Temporal (2013–2016) | … plus all evidence lines | 0.575 (0.497–0.651) | 0.103 (0.063) | 1,559 (98) |
| Held-out targets | Evidence lines only | 0.519 (0.448–0.596) | 0.087 (0.065) | 3,085 (199) |
| Temporal (2013–2016) | Evidence lines only | 0.544 (0.470–0.623) | 0.083 (0.063) | 1,559 (98) |

Change in held-out AUC when each line is removed from the full model (paired target bootstrap):

| Evidence removed | AUC change (95% CI) |
| :---- | :---- |
| Human genetics (any germline source) | -0.004 (-0.010 to +0.003) |
| Rare-variant / Mendelian (ClinVar, Orphanet, G2P, ClinGen, burden) | -0.000 (-0.002 to +0.002) |
| CRISPR screen | -0.000 (-0.000 to -0.000) |
| Pathway (Reactome) | +0.000 (-0.001 to +0.001) |
| Differential expression in disease (Expression Atlas) | +0.000 (-0.013 to +0.019) |
| GWAS credible set | +0.000 (-0.001 to +0.002) |
| Mouse model (IMPC) | +0.001 (-0.001 to +0.004) |
| Somatic driver (COSMIC CGC, IntOGen, ClinVar somatic) | +0.005 (-0.003 to +0.014) |
| LoF-intolerant target (gnomAD LOEUF < 0.35) | +0.006 (-0.003 to +0.017) |
| Pan-essential (DepMap) | +0.017 (+0.002 to +0.042) |

A model on disease area, modality, novelty and entry year alone ranks programs at an AUC of 0.551 on held-out targets; adding every evidence line gives 0.590 (95% CI 0.528–0.648). No single line's removal measurably lowers that, human genetics included (0.004, 95% CI -0.003–0.010): the lines overlap, and what they add they add together. On the temporal split the evidence adds nothing (0.578 without, 0.575 with). The gap between a strong relative success and so little gain in discrimination is not a contradiction: genetic support multiplies the chance of approval by about 3.48 for the minority of programs that have it (15% of Phase 1 entrants, fewer among the 2008–2016 entrants this model follows), but it says nothing about the majority, so it can sort only a small slice of programs. The draft's AUCs of 0.825 and 0.769 came from a leaked model and phantom programs (AUDIT.md, C33–C34).



## Case studies

The cases below each looked strong on mechanism, cell and animal evidence, and failed in humans.

| Drug (indication) | Evidence that looked strong | Why it failed |
| :---- | :---- | :---- |
| BACE1 inhibitors: verubecestat, lanabecestat, atabecestat (Alzheimer's disease) | Crystal structures; Aβ lowering in cells and animals; a protective human *APP* variant (A673T) that reduces BACE1 cleavage; CSF Aβ down 50–90% in Phase 1 | No slowing of decline. In the verubecestat (prodromal) and atabecestat (preclinical) trials cognition worsened early, with a dose-related effect that reversed after stopping, consistent with BACE1's other neuronal substrates. Reducing Aβ production did not help people who already had plaques; antibodies that clear plaque (lecanemab, donanemab) later slowed decline modestly. ([Egan 2018](https://doi.org/10.1056/NEJMoa1706441); [Egan 2019](https://doi.org/10.1056/NEJMoa1812840); [Sperling 2021](https://doi.org/10.1001/jamaneurol.2020.4857)) |
| Torcetrapib and later CETP inhibitors (cardiovascular disease) | Raised HDL in people with CETP deficiency; HDL up 60–70% as predicted; less atherosclerosis in rabbits | Torcetrapib increased deaths by 58% (93 vs 59) and major cardiovascular events by 25%, probably through an off-target rise in aldosterone and blood pressure. Dalcetrapib and evacetrapib raised HDL without cutting events. Anacetrapib cut major coronary events by 9%, in line with its modest non-HDL-cholesterol lowering, and was not filed. ([Barter 2007](https://doi.org/10.1056/NEJMoa0706628); [Schwartz 2012](https://doi.org/10.1056/NEJMoa1206797); [Lincoff 2017](https://doi.org/10.1056/NEJMoa1609581); [HPS3/TIMI55–REVEAL 2017](https://doi.org/10.1056/NEJMoa1706444)) |
| Semagacestat (Alzheimer's disease) | Aβ lowering in cells and mice; dose-dependent 47–84% cut in CNS Aβ production in a small human kinetic study | Did not slow decline. At the higher dose, daily function worsened significantly faster than on placebo and cognition trended worse. Patients had more skin cancers, infections and weight loss, consistent with blocking γ-secretase substrates such as Notch. ([Doody 2013](https://doi.org/10.1056/NEJMoa1210951)) |
| Solanezumab, bapineuzumab (Alzheimer's disease) | Aβ binding; plaque prevention in transgenic mice; peripheral Aβ engagement (solanezumab) and partial plaque lowering on PET in APOE4 carriers (bapineuzumab) | No cognitive benefit across several Phase 3 trials. Solanezumab binds soluble Aβ and did not remove plaque; bapineuzumab's dose was capped by brain swelling (ARIA). Antibodies that cleared plaque more deeply later slowed decline modestly, so these failures look more like insufficient target engagement than a misleading mouse model. ([Doody 2014](https://doi.org/10.1056/NEJMoa1312889); [Salloway 2014](https://doi.org/10.1056/NEJMoa1304839)) |
| TGN1412 (B-cell leukemia, rheumatoid arthritis) | Cynomolgus monkeys tolerated 500 times the human starting dose | All six volunteers who received the drug developed a cytokine storm within 90 minutes. Unlike in the monkeys used for toxicology, human CD4+ effector memory T cells carry CD28. The starting dose already occupied most CD28 receptors; human-cell assays and dosing from the minimal anticipated biological effect level would have flagged the risk. ([Suntharalingam 2006](https://doi.org/10.1056/NEJMoa063842); [Eastwood 2010](https://doi.org/10.1111/j.1476-5381.2010.00922.x); [Stebbings 2007](https://doi.org/10.4049/jimmunol.179.5.3325)) |
| Fialuridine (hepatitis B) | Clean toxicology in mice, rats, dogs and monkeys | Seven of 15 patients developed liver failure with lactic acidosis: five died and two needed transplants. Human ENT1, unlike the rodent transporter, is targeted to mitochondria and carries the drug into them. ([McKenzie 1995](https://doi.org/10.1056/NEJM199510263331702); [Lee 2006](https://doi.org/10.1074/jbc.M513825200)) |

## Appendix

### Data

| Source | What it gives | Version |
| :---- | :---- | :---- |
| ClinicalTrials.gov API v2 | Every interventional drug or biological study: phases, status, dates, sponsor, arms, interventions, conditions, sites, why stopped, posted results | Snapshot 2026-10-20 (222,915 studies) |
| PubMed | Results papers linked to completed trials without posted results (registry RESULT/DERIVED references and the NCT secondary identifier) | Retrieved 2026-10-20 |
| Drugs@FDA, FDA approval letters, openFDA labels | NDA/BLA applications, submissions and action dates; 5,034 approved uses read from 2015–2026 approval letters; current Indications and Usage text | Retrieved October 2026 |
| CBER yearly approval pages, product pages and letters | 177 biologics applications (vaccines, blood products, cell and gene therapies) and their 2015–2025 approval actions, verified by an independent second enumeration | Retrieved October 2026 |
| FDA Global Substance Registration System | UNII substance identifiers and every registered name (official, common, code, brand) | 2026-08-04 |
| MONDO, EFO | Disease ontology and hierarchy | MONDO 2026-10-06, EFO 3.95 |
| Open Targets Platform | Target–disease associations by data source, with yearly score series | 26.09 |
| gnomAD | Loss-of-function constraint (LOEUF) | v4.1 |
| DepMap | Pan-essential genes from CRISPR (Chronos) screens | Release not recorded in the project database |

### How each label was made, and how good it is

Every judgement in the pipeline is an LLM call (Claude) that reads the source record and returns a structured answer, stored with its prompt, input, model and code version. Disease mapping, entity resolution, trial purpose and roles, approvals, stop reasons, trial outcomes, modality, disease area and targets were all made this way, not with keyword rules. For each high-stakes label, a seeded random sample was re-derived independently by agents working from the primary sources (registry records, PubMed, Drugs@FDA, DailyMed, CBER pages) before they saw the stored answer. Agreement counts answers judged correct or defensibly different under the same rules.

| Label | Audited | Agreement (95% CI) | Wrong |
| :---- | :---- | :---- | :---- |
| Condition → MONDO disease | 100 | 99% (95%–100%) | 1 |
| Intervention name → molecular entities | 100 | 92% (85%–96%) | 8 |
| FDA application → molecular entities | 100 | 98% (93%–99%) | 2 |
| Approval letter → approved uses | 60 | 100% (94%–100%) | 0 |
| Trial stop reason | 30 | 97% (83%–99%) | 1 |
| Primary endpoint met / not met (posted results) | 60 | 100% (94%–100%) | 0 |
| Primary endpoint met / not met (results papers) | 30 | 97% (83%–99%) | 1 |
| Approval (sampled as approved, dated 2015 or later) | 25 | 100% (87%–100%) | 0 |
| Approval date (sampled as approved, dated 2015 or later) | 25 | 96% (80%–99%) | 1 |
| Approval (sampled as approved before 2015) | 15 | 100% (80%–100%) | 0 |
| Approval (sampled as not approved, Phase 2+ programs) | 31 | 100% (89%–100%) | 0 |
| Approval (sampled as uncertain) | 15 | 80% (55%–93%) | 3 |

Each error pattern these audits found was fixed in the pipeline and the affected labels re-derived, not patched by hand: diseases MONDO has no exact term for now map to their nearest broader term; development codes resolve to UNII substances, and the same substance under two names is merged; scanned FDA letters are read by OCR; labelling-only supplements no longer count as approvals; stop reasons stated only in a trial's summary are read; publication-based outcomes use only the abstracts given; and approval dates account for older applications of the same drug. The disease-mapping, entity and approval figures above come from fresh samples drawn after those fixes; before them, disease mapping agreed 94% of the time, entity resolution 95%, and 8 of 25 dated first approvals were wrong. Remaining entity errors are scattered (a development code resolved to the wrong substance, a salt chosen over its parent) rather than systematic. Programs whose approval is judged "uncertain" (107 of 24,392 judgements) count as not approved; counting them as approved instead leaves every rate unchanged to the first decimal (sensitivity table). The approval audit's strata are those of the judgements it sampled; it was re-scored after the final rebuild against the auditors' own answers, and programs that are no longer development programs left the sample. The audit of the earlier draft, with every claim's verdict and every data issue, is in `AUDIT.md`.

### Limitations

* **Registry programs are not Biomedtracker programs.** BIO counts transitions that analysts record for programs companies disclose; this report counts programs from registered trials. Trials registered only outside ClinicalTrials.gov (ChiCTR, EU CTR, CTIS) are missing, so programs developed there look suspended. Restricting to programs with a US site removes most of the difference.
* **Suspension is inferred from inactivity.** A program counts as suspended when none of its trials has been active within 24 months. The rates move with that window (sensitivity table); BIO dates suspensions from company disclosures instead.
* **Recent entrants are mostly unresolved.** Programs that entered a phase in 2023–2025 are largely still running; the success rate counts only resolved programs, so it leans on early failures. Entries from 2015–2019 alone, with at least six years of follow-up, are shown as a sensitivity.
* **Outcome is FDA approval only.** Approvals elsewhere count as no approval.
* **Symptom and procedure indications without a MONDO term** (pain, cough, contraception; about 3% of trials) are grouped in each entity's disease-unspecified program, followed through Phase 2 but not to approval.
* **Most stopped programs give no reason.** Reasons come from the registry's why-stopped field, posted results and abstracts of results papers. Published results favour positive findings, and a missing reason is reported as such, not inferred.
* **The model declines some products.** Claude declines to classify some products derived from pathogens, toxins or live bacterial and viral vectors (botulinum and plague vaccines, oncolytic viruses, engineered bacteria) on every attempt: 139 entities have no resolved target and 51 no modality, so they fall out of Section 2 and the modality strata.
* **Evidence as of phase entry undercounts.** Open Targets leaves undated evidence out of its yearly series; a sensitivity uses the 2026 scores instead.


## Sources

* Cook D et al. (2014). [Lessons learned from the fate of AstraZeneca's drug pipeline: a five-dimensional framework](https://doi.org/10.1038/nrd4309). *Nature Reviews Drug Discovery* 13, 419–431.
* Harrison RK (2016). [Phase II and phase III failures: 2013–2015](https://doi.org/10.1038/nrd.2016.184). *Nature Reviews Drug Discovery* 15, 817–818.
* Minikel EV et al. (2024). [Refining the impact of genetic evidence on clinical success](https://doi.org/10.1038/s41586-024-07316-0). *Nature* 629, 624–629.
* Morgan P et al. (2018). [Impact of a five-dimensional framework on R&D productivity at AstraZeneca](https://doi.org/10.1038/nrd.2017.244). *Nature Reviews Drug Discovery* 17, 167–181.
* Nelson MR et al. (2015). [The support of human genetic evidence for approved drug indications](https://doi.org/10.1038/ng.3314). *Nature Genetics* 47, 856–860.
* Ringel MS, Scannell JW, Baedeker M, Schulze U (2020). [Breaking Eroom's Law](https://doi.org/10.1038/d41573-020-00059-3). *Nature Reviews Drug Discovery* 19, 833–834.
* Scannell JW et al. (2012). [Diagnosing the decline in pharmaceutical R&D efficiency](https://doi.org/10.1038/nrd3681). *Nature Reviews Drug Discovery* 11, 191–200.
* Scannell JW, Bosley J (2016). [When quality beats quantity: decision theory, drug discovery, and the reproducibility crisis](https://doi.org/10.1371/journal.pone.0147215). *PLoS ONE* 11, e0147215.
* Thomas D et al. (2021). [Clinical Development Success Rates and Contributing Factors 2011–2020](https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf). BIO, Informa Pharma Intelligence and QLS Advisors.
* Case-study primary sources are linked in the table.
