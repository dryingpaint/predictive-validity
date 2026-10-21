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

Every classification in the pipeline (entity resolution, disease mapping, trial purpose and roles, approvals, stop reasons, trial outcomes, targets) was made by an LLM reading the source record and recorded with its prompt and input. Disease mapping, entity resolution, approved uses, program approvals, stop reasons and trial outcomes were also checked against an independent re-derivation of a seeded sample (Appendix); trial purposes and roles were re-decided under a second prompt version and agree with the first on 98% and 97% of trials, and disease mapping, decided twice, chose the same MONDO term for 92% of conditions; modality, disease area and targets were not audited.


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

For development programs that entered a phase in 2015–2025 and were developed in the US, the likelihood of FDA approval from Phase 1 is 10.5% (95% CI 9.4%–11.8%), against BIO's 7.9% for 2011–2020 (6.8% for novel drugs). Across all industry programs registered on ClinicalTrials.gov, including those run only outside the US, it is 7.2%. Most programs stop without a stated reason: of 6,742 programs that stopped, 45% left no stated reason and no posted or published result, and 20% record an efficacy, safety or pharmacokinetic reason.

### How programs are counted

* **Trial:** a registered interventional study listing Early Phase 1 to Phase 3. A Phase 1/2 trial counts as Phase 2 and a Phase 2/3 trial as Phase 3. Withdrawn trials never enrolled and are left out.
* **Molecular entity:** the active substance, whatever its brand, sponsor code, dose or salt, resolved to its FDA UNII substance where one exists. Biosimilars fold into their reference entity.
* **Disease:** the MONDO term for the condition the trial treats, without line, stage, biomarker or age qualifiers.
* **Program:** one entity developed for one indication. An indication groups the entity's MONDO diseases the way a sponsor runs them as programs (prostate cancer with castration-resistant and metastatic prostate carcinoma; diffuse large B-cell and follicular lymphoma kept apart), decided by an LLM for each entity. An entity belongs to a program only in trials where it is the investigational agent, not a comparator or background therapy. Each industry trial's purpose is classified first: bioequivalence, formulation, food-effect, interaction and other product-support studies (10,770 trials) belong to no program; a first-in-human study or a basket across several diseases counts as Phase 1 only for the program the sponsor pursued next.
* **Phase entry and outcome:** a program enters a phase with its first industry-sponsored trial of that phase. It *advanced* when a later-phase trial in its disease started (any sponsor; a trial registered but not yet recruiting does not count) or the FDA approved the entity for the disease; it is *suspended* when none of its trials, nor the trial that marked its Phase 1 entry, has been active within 24 months of the snapshot (2026-10-20); otherwise it is still running and *censored*. Programs whose entity was already approved for the disease are lifecycle programs and are left out; an approval dated only as before 2015 is placed at the entity's first FDA approval, the earliest it could have happened. As in BIO's report, a phase a program skipped (Phase 1 straight to Phase 3, or approval from Phase 2) counts as a success in that phase, each phase's success rate is advanced ÷ (advanced + suspended), and LOA is their product. *US-developed* programs are those with a US-sited industry trial in the phase; a cohort with fewer than ten entities resolved in a phase gets no LOA.
* **Approval:** FDA approval of the entity for the program's disease, a subtype or population of it, or a broader approved class that includes it, judged from the dated approval letters, original-approval dates and labels of every application of the entity (CDER and CBER).

17,047 programs of 10,253 entities entered at least one phase in 2015–2025.

### Phase transitions

| Transition | All programs (95% CI) | Developed in the US (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- |
| Phase 1 → Phase 2 | 56.8% (55.0–58.6), n=5,714 | 57.0% (54.3–59.7), n=3,104 | 52.0% |
| Phase 2 → Phase 3 | 34.0% (32.3–35.6), n=4,960 | 34.7% (32.7–36.8), n=2,994 | 28.9% |
| Phase 3 → Approval | 37.1% (34.1–40.0), n=1,586 | 53.0% (49.6–56.4), n=1,064 | 52.4% |
| **Phase 1 → Approval (LOA)** | **7.2%** (6.4–8.0) | **10.5%** (9.4–11.8) | **7.9%** (novel drugs 6.8%) |

Programs developed in the US, the closest match to BIO's FDA-focused Biomedtracker programs, advance from Phase 1 at 57.0% (BIO 52.0%), from Phase 2 at 34.7% (BIO 28.9%) and from Phase 3 to approval at 53.0% (BIO 52.4%). Phase 2 remains the steepest single drop. Across all registered industry programs the Phase 3 rate falls to 37.1%, because many programs run only outside the US end in approvals elsewhere, which this report does not count.

The likelihood of approval depends on choices a registry-based count has to make, and the table below shows how far each moves it. It is most sensitive to how long a program must be idle before it counts as suspended: 5.1% with a 12-month window and 10.3% with 36 months (24 in the headline). If every shared trial (a healthy-volunteer study, a basket) counted as the start of every later indication of the drug, LOA would rise to 12.1%, mostly by crediting indication expansions begun at Phase 2 with a Phase 1 success. Restricting to programs that entered a phase in 2015–2019, which have had at least six years to resolve, changes little (10.7% for US-developed programs). Vaccines are left out of the headline figures: annual and variant strain updates are licensed as supplements to the parent product, so registry entities for updated formulations never reach an approval of their own (LOA with vaccines included: 6.4%).


| Cohort or definition | Ph1→2 | Ph2→3 | Ph3→approval | LOA (95% CI) |
| :---- | :---- | :---- | :---- | :---- |
| All programs | 56.8% | 34.0% | 37.1% | 7.2% (6.4–8.0) |
| Programs with a US-sited industry trial in the phase | 57.0% | 34.7% | 53.0% | 10.5% (9.4–11.8) |
| Entity not yet FDA-approved at phase entry | 55.8% | 33.3% | 36.9% | 6.9% (6.1–7.6) |
| Entity already FDA-approved for another disease | 62.8% | 38.6% | 37.8% | 9.2% (6.8–11.7) |
| Suspension lag 12 months | 51.9% | 29.9% | 33.1% | 5.1% (4.6–5.7) |
| Suspension lag 18 months | 53.9% | 31.6% | 34.8% | 5.9% (5.3–6.6) |
| Suspension lag 36 months | 62.1% | 38.8% | 42.7% | 10.3% (9.3–11.4) |
| Uncertain approvals counted as approved | 56.8% | 33.9% | 37.2% | 7.2% (6.4–8.0) |
| Shared trials mark entry for every program of the entity | 68.0% | 46.4% | 38.5% | 12.1% (10.7–13.9) |
| Including vaccines | 55.4% | 33.4% | 34.7% | 6.4% (5.7–7.1) |
| Phase entry 2015-2019 (at least six years of follow-up) | 55.3% | 31.4% | 41.8% | 7.3% (6.3–8.3) |
| Phase entry 2015-2019, developed in the US | 57.1% | 34.0% | 55.1% | 10.7% (9.2–12.3) |

### Why programs stop

Each suspended program takes one reason from the industry trials of the phase it stopped in, in this order: an efficacy reason stated by the sponsor, a primary endpoint missed in posted or published results, a safety signal, a pharmacokinetic or formulation problem, an explicit business or strategic reason, a bare "sponsor decision", an enrollment, operational or regulatory reason, a positive primary readout without advancement, another stated reason, posted results with no stated reason or readable endpoint, and finally neither a reason nor a result.

| Reason | Phase 1 | Phase 2 | Phase 3 |
| :---- | :---- | :---- | :---- |
| PK, dose or formulation | 1% (20) | 0% (8) | 0% (0) |
| business or strategic (explicit) | 12% (308) | 8% (275) | 6% (62) |
| completed, no results posted, no reason stated | 49% (1,219) | 20% (642) | 21% (207) |
| efficacy: primary endpoint not met | 0% (7) | 19% (621) | 17% (170) |
| efficacy: stated | 3% (64) | 6% (195) | 12% (115) |
| enrollment, operational or regulatory | 3% (67) | 6% (182) | 4% (42) |
| other stated reason | 1% (16) | 0% (15) | 1% (5) |
| positive readout, not advanced | 1% (13) | 9% (301) | 18% (181) |
| results posted, no reason stated, endpoint not assessable | 9% (233) | 11% (367) | 3% (27) |
| safety | 2% (54) | 2% (81) | 3% (32) |
| sponsor decision, unspecified | 4% (108) | 4% (138) | 3% (30) |
| stopped, no reason stated | 15% (360) | 14% (451) | 13% (126) |

![Why suspended programs stopped, by phase](report/output/figures/failure_modes_by_phase.png)

The registry rarely says why a program stopped. In Phase 1, 64% of stopped programs left neither a stated reason nor a result, which is expected: Phase 1 trials seldom post results and companies seldom explain pausing early assets. In Phase 2 and Phase 3 the share without a reason falls to 33% and 33%. Efficacy is the recorded reason for 25% of programs that stopped in Phase 2 and 29% of those that stopped in Phase 3: the sponsor said so, or the posted or published primary endpoint was missed. Safety accounts for 2% and 3%: among Phase 2 and Phase 3 stops with an efficacy or safety reason, safety is 9% and 10%, against about 32% in Harrison (2016), whose 2013–2015 failures with a disclosed reason were 24% safety and 52% efficacy. Either registry records under-report safety stops, or company disclosures over-represent them.

At the level of individual trials, the 5,557 industry trials started in 2015–2025 that stopped early or were withdrawn with a reason give: an explicit business, portfolio or competitive reason 36%, a bare "sponsor decision" 19%, efficacy 14%, enrollment or operations 14% and safety 4%. The draft's single 44% "commercial or strategic" category mixed these two kinds of statement; a "sponsor decision" with no reason may or may not hide an efficacy result, and the record cannot tell.

Finally, 18% of Phase 3 programs that stopped short of FDA approval had met their primary endpoint. In a sample we read, most of them were approved outside the US (Japan, China, Korea, Russia) or received a complete response letter from the FDA: a positive Phase 3 readout is necessary but not sufficient for US approval.


### By disease area and modality

| Disease area | All programs, LOA (95% CI) | Entities | Developed in the US, LOA (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- | :---- |
| Hematology | 19.3% (12.5–26.9) | 265 | 19.0% (10.6–29.0) | 23.9% |
| Metabolic | 18.0% (12.1–24.3) | 403 | 26.4% (18.5–34.7) | 15.5% |
| Oncology | 17.2% (14.5–20.3) | 2,581 | 21.0% (17.3–24.9) | 5.3% |
| Endocrine | 11.9% (6.5–18.6) | 317 | 27.9% (18.5–37.2) | 6.6% |
| Psychiatry | 10.6% (5.9–15.9) | 276 | 13.9% (7.6–21.0) | 7.3% |
| Allergy | 10.2% (4.6–17.5) | 132 | 11.6% (4.4–21.9) | 10.3% |
| Autoimmune | 10.2% (7.0–13.7) | 657 | 10.8% (7.2–15.5) | 10.7% |
| Neurology | 8.8% (6.5–11.4) | 898 | 14.3% (10.9–18.1) | 5.9% |
| Other | 7.1% (5.0–9.2) | 905 | 9.8% (7.1–12.9) | 13.0% |
| Respiratory | 7.1% (3.9–10.4) | 474 | 8.8% (4.6–13.4) | 7.5% |
| Cardiovascular | 5.5% (2.9–9.2) | 362 | 13.5% (7.3–20.4) | 4.8% |
| Ophthalmology | 5.1% (2.9–8.0) | 413 | 6.1% (3.1–9.7) | 11.9% |
| Infectious disease | 3.8% (2.7–5.1) | 925 | 6.0% (4.0–8.5) | 13.2% |
| Gastroenterology | 2.8% (1.0–5.5) | 333 | 6.9% (3.0–11.6) | 8.3% |
| Urology | 1.4% (0.0–5.6) | 68 | – | 3.6% |

| Modality | All programs, LOA (95% CI) | Entities | Developed in the US, LOA (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- | :---- |
| Multispecific antibody | 21.3% (12.5–30.4) | 485 | 24.3% (14.0–33.2) | – |
| Antibody–drug conjugate | 20.6% (8.5–33.8) | 411 | 18.2% (6.6–32.1) | 10.8% |
| Monoclonal antibody | 13.9% (10.8–17.2) | 1,287 | 16.0% (12.2–20.2) | 12.1% |
| Antisense oligonucleotide | 13.1% (5.1–23.4) | 113 | 16.4% (6.1–30.7) | 5.2% |
| Peptide | 9.9% (4.9–15.4) | 346 | 13.4% (6.7–20.6) | 8.0% |
| Small molecule | 6.3% (5.5–7.2) | 5,195 | 9.9% (8.5–11.3) | 7.5% |
| Gene therapy | 6.0% (1.8–12.9) | 242 | 6.9% (1.7–14.7) | 10.0% |
| Protein | 4.5% (2.7–6.7) | 537 | 4.9% (2.6–7.6) | 9.4% |
| Other cell therapy | 1.2% (0.3–2.6) | 527 | 2.3% (0.6–5.6) | – |
| Other | 0.2% (0.0–0.7) | 300 | – | – |

![Likelihood of approval by disease area](report/output/figures/loa_by_area.png)

![Likelihood of approval by modality](report/output/figures/loa_by_modality.png)

Disease areas rank differently from BIO's: the rank correlation with BIO's LOA across the 15 areas is 0.26 for all programs and -0.26 for US-developed ones. Across all programs, hematology, metabolic and oncology programs reach approval most often (19.3%, 18.0% and 17.2%), and urology, gastroenterology and infectious-disease programs least. Among US-developed programs, endocrine (27.9%) and oncology programs (21.0%) come out far above BIO's 6.6% and 5.3%; for oncology, the 2015–2025 window holds the wave of immunotherapy, antibody–drug conjugate and bispecific approvals, and an approval in a cancer subtype counts for the program's cancer. Infectious disease (6.0%) sits far below BIO's 13.2%, largely because many registered anti-infective and COVID-19 programs, including US-run ones, were never approved; ophthalmology (6.1%) and gastroenterology (6.9%) also fall below BIO's 11.9% and 8.3%. Among modalities, multispecific antibodies and antibody–drug conjugates reach approval most often across all programs (21.3% and 20.6%), and among the classes BIO also reports, non-antibody proteins (4.5%), gene therapies (6.0%) and small molecules (6.3%) least. RNA interference and CAR-T, near the top of BIO's ordering, have too few entities resolved in Phase 3 here (most of their approvals came straight from Phase 2) to estimate. The modality ordering agrees with BIO's only loosely (rank correlation 0.32 across the 7 classes both estimate).



## Predictive power of preclinical evidence

Human genetic evidence linking a program's target to its disease is the clearest preclinical signal of success. Programs whose target had it before they entered the phase reached FDA approval 2.83 times as often as programs without it (30.6% against 10.8%; 95% CI 2.21–3.64), the likelihood rises with the strength of the evidence, and the association holds at every phase after accounting for disease area, modality, novelty and era. Somatic driver and mouse-model evidence carry weaker signals; targets essential in every cancer cell line are a liability. Yet as a predictor of which individual programs will be approved, the evidence lines raise discrimination only modestly over disease area and modality (held-out AUC 0.611 to 0.665), because most programs have none of them.


### Evidence lines and how they are matched

Each program aimed at a human protein (the entity's primary targets, resolved by an LLM from the entity's mechanism records and trial descriptions) is scored for the evidence its targets had **for the program's disease** in Open Targets Platform 26.09, **as of the year before the program entered the phase**. A target–disease association counts for the program's disease when the evidence disease is the same MONDO term, a subtype of it, or similar to it (Lin similarity ≥ 0.8, the criterion Minikel et al. used). Open Targets publishes a yearly series of each association's score, so evidence is taken as it stood before phase entry, not as it stands today. Evidence lines:

* **Human germline genetics:** GWAS credible sets (with locus-to-gene scores), gene burden tests, ClinVar, Genomics England PanelApp, Orphanet, Gene2Phenotype, ClinGen and UniProt; split into GWAS and rare-variant/Mendelian sources.
* **Somatic drivers:** COSMIC Cancer Gene Census, IntOGen and ClinVar somatic.
* **Mouse models:** IMPC phenotypes. **Expression:** differential expression in the disease (Expression Atlas). **Pathways:** Reactome. **Functional screens:** CRISPR screens.
* **Target-level properties** that are not disease-specific: loss-of-function intolerance (gnomAD v4.1 LOEUF < 0.35) and pan-essentiality across DepMap cell lines, taken from the current releases rather than as of phase entry.

Sources that encode clinical outcomes or literature co-mention (ChEMBL clinical precedence, Europe PMC) are not used. Vaccines, cell and gene therapies and other entities without a single human protein target fall outside this analysis, so its programs reach approval more often than the Section 1 cohort as a whole. Of the 10,190 programs on 1,397 targets scored, 14.9% of Phase 1 entrants had human genetic evidence for their disease at entry.

### Relative success

*Relative success* is the LOA of programs with the evidence divided by the LOA of programs without it (Nelson et al. 2015; Minikel et al. 2024). The 95% intervals resample primary-target sets (an entity's primary targets taken together), since programs on the same targets are not independent.

| Evidence line | Programs with it | LOA with / without | Relative success (95% CI) |
| :---- | :---- | :---- | :---- |
| Rare-variant / Mendelian (ClinVar, Orphanet, G2P, ClinGen, burden) | 1,027 | 33.6% / 11.6% | 2.89 (2.28–3.71) |
| Human genetics (any germline source) | 1,689 | 30.6% / 10.8% | 2.83 (2.21–3.64) |
| Somatic driver (COSMIC CGC, IntOGen, ClinVar somatic) | 1,697 | 26.5% / 11.9% | 2.23 (1.55–2.98) |
| GWAS credible set | 870 | 25.0% / 12.5% | 2.00 (1.33–2.73) |
| Pathway (Reactome) | 207 | 25.8% / 13.1% | 1.97 (1.11–2.99) |
| Mouse model (IMPC) | 1,985 | 17.4% / 12.3% | 1.41 (1.05–1.83) |
| Differential expression in disease (Expression Atlas) | 1,358 | 17.3% / 12.9% | 1.34 (0.93–1.78) |
| LoF-intolerant target (gnomAD LOEUF < 0.35) | 1,853 | 13.4% / 13.4% | 1.00 (0.67–1.42) |
| Pan-essential (DepMap) | 548 | 5.4% / 13.8% | 0.39 (0.13–0.72) |

![Relative success by evidence line](report/output/figures/relative_success_by_evidence.png)

Rare-variant and Mendelian evidence (2.89×) and GWAS evidence (2.00×) both carry the genetic signal, in line with Minikel et al. (2024), who found 2.6× from Phase 1 to launch with Mendelian evidence stronger than GWAS. Somatic driver evidence (2.23×), mouse phenotypes (1.41×) and Reactome pathways (1.97×, from only 207 programs) also associate with success; differential expression in the disease does not clearly (1.34×, interval spanning 1). Loss-of-function-intolerant targets show no penalty (1.00×), while pan-essential targets reach approval less than half as often (0.39×), mostly oncology small molecules aimed at machinery every cell needs (mTOR, tubulin, topoisomerases, histone deacetylases, WEE1 and ATR, BET proteins). CRISPR-screen evidence covered too few programs (72) to estimate.

Two checks bear on whether this reflects foresight rather than hindsight. Evidence is taken as it stood in Open Targets' yearly series before the program entered the phase, so later discoveries do not count. Counting all evidence known by 2026 instead weakens the genetic relative success to 2.43×: what was known in advance is more telling than what was found afterwards. And restricting matches to diseases similar to the program's (Lin ≥ 0.8, Minikel's criterion, without the subtype rule) gives 2.83×.


### Genetic dose–response

| Human genetic support (Open Targets score, as of phase entry) | Programs | Targets | LOA (95% CI) |
| :---- | :---- | :---- | :---- |
| None | 8,580 | 1,274 | 10.8% (8.8–13.3) |
| Lower third (> 0.00 to 0.61) | 659 | 282 | 21.6% (14.9–28.9) |
| Middle third (> 0.61 to 0.88) | 538 | 195 | 35.1% (25.1–44.6) |
| Upper third (> 0.88) | 572 | 213 | 37.6% (29.3–46.3) |

![Likelihood of approval by strength of human genetic support](report/output/figures/genetic_dose_response.png)

### What each line adds once the others are known

Programs with genetic evidence differ from programs without it in disease area, modality and era, and the evidence lines overlap. The table gives, for each phase, the relative risk of advancing for programs with each line, from one Poisson model containing every line together with disease area, modality, entity novelty and entry period (standard errors clustered by primary-target set).

| Evidence | Phase 1 → next | Phase 2 → next | Phase 3 → next |
| :---- | :---- | :---- | :---- |
| GWAS credible set | 1.07 (1.00–1.13) | 1.53 (1.32–1.78) | 1.05 (0.77–1.42) |
| Rare-variant / Mendelian (ClinVar, Orphanet, G2P, ClinGen, burden) | 1.07 (0.98–1.16) | 1.35 (1.16–1.56) | 1.58 (1.31–1.90) |
| Somatic driver (COSMIC CGC, IntOGen, ClinVar somatic) | 1.01 (0.92–1.12) | 1.11 (0.90–1.36) | 1.09 (0.86–1.38) |
| Mouse model (IMPC) | 0.95 (0.89–1.01) | 0.98 (0.86–1.11) | 0.96 (0.81–1.14) |
| Differential expression in disease (Expression Atlas) | 0.98 (0.91–1.05) | 1.04 (0.88–1.22) | 0.88 (0.70–1.09) |
| Pathway (Reactome) | 1.09 (0.96–1.25) | 0.98 (0.74–1.30) | 1.09 (0.78–1.53) |
| LoF-intolerant target (gnomAD LOEUF < 0.35) | 0.98 (0.89–1.08) | 1.16 (0.99–1.37) | 1.01 (0.81–1.27) |
| Pan-essential (DepMap) | 0.78 (0.62–0.99) | 0.65 (0.47–0.90) | 0.75 (0.47–1.20) |

One evidence line at a time, with the same adjustments, human genetic evidence raises the chance of advancing by 1.07× in Phase 1, 1.62× in Phase 2 and 1.45× in Phase 3: the effect sits where efficacy is first tested. In the joint model, GWAS and rare-variant evidence each keep an independent effect at Phase 2, rare-variant evidence also at Phase 3 and GWAS a small one at Phase 1, and pan-essentiality keeps its penalty at Phases 1 and 2; somatic, mouse-model, expression and pathway evidence lose their association once genetics and the covariates are in the model, consistent with their univariate signal riding along with genetic support and with disease area.


### Does the evidence predict which programs reach approval?

We followed programs that entered Phase 1 in 2008–2016 for ten years (3,050 programs, 161 approved), with the Open Targets evidence lines and novelty taken as of entry (loss-of-function constraint and pan-essentiality come from current releases), and fitted logistic models on disease area, modality, novelty and entry year alone, and with the evidence lines added. Performance is measured on held-out primary-target sets (out-of-fold predictions averaged over 20 repetitions of 5-fold cross-validation grouped by primary-target set and stratified by outcome; a single split moves the AUC by several points) and on a temporal split (trained on 2008–2012 entries, tested on 2013–2016).

| Validation | Features | AUC (95% CI) | PR-AUC (base rate) | Programs (approved) |
| :---- | :---- | :---- | :---- | :---- |
| Held-out target sets | Area, modality, novelty, year | 0.611 (0.545–0.673) | 0.116 (0.053) | 3,050 (161) |
| Temporal (2013–2016) | Area, modality, novelty, year | 0.617 (0.536–0.690) | 0.115 (0.057) | 1,533 (87) |
| Held-out target sets | … plus all evidence lines | 0.665 (0.602–0.723) | 0.151 (0.053) | 3,050 (161) |
| Temporal (2013–2016) | … plus all evidence lines | 0.655 (0.581–0.726) | 0.132 (0.057) | 1,533 (87) |
| Held-out target sets | Evidence lines only | 0.611 (0.537–0.688) | 0.094 (0.053) | 3,050 (161) |
| Temporal (2013–2016) | Evidence lines only | 0.638 (0.578–0.705) | 0.112 (0.057) | 1,533 (87) |

Change in held-out AUC when each line is removed from the full model (human genetics: GWAS and rare-variant evidence removed together; lines carried by fewer than 100 programs are not modelled; paired bootstrap over target sets):

| Evidence removed | AUC change (95% CI) |
| :---- | :---- |
| Human genetics (any germline source) | -0.028 (-0.053 to -0.002) |
| Rare-variant / Mendelian (ClinVar, Orphanet, G2P, ClinGen, burden) | -0.028 (-0.049 to -0.002) |
| Pan-essential (DepMap) | -0.015 (-0.027 to -0.003) |
| Differential expression in disease (Expression Atlas) | -0.001 (-0.009 to +0.009) |
| Mouse model (IMPC) | -0.001 (-0.003 to +0.002) |
| Somatic driver (COSMIC CGC, IntOGen, ClinVar somatic) | +0.002 (-0.012 to +0.016) |
| LoF-intolerant target (gnomAD LOEUF < 0.35) | +0.002 (+0.000 to +0.004) |

A model on disease area, modality, novelty and entry year alone ranks programs at an AUC of 0.611 on held-out target sets; adding the evidence lines raises it to 0.665 (95% CI 0.602–0.723), and the temporal split agrees (0.617 without, 0.655 with). Human genetics carries most of the gain: removing it lowers the held-out AUC by 0.028 (95% CI 0.002–0.053), and pan-essentiality is the only other line whose removal measurably lowers it (0.015). GWAS evidence covered too few of the 2008–2016 entrants to be modelled, so genetics here means rare-variant and Mendelian evidence. Discrimination stays modest all the same, and that does not contradict the relative success: genetic support multiplies the chance of approval by about 2.83 for the minority of programs that have it (15% of Phase 1 entrants, fewer among the 2008–2016 entrants this model follows), but says nothing about the majority, so it can sort only a small slice of programs. The draft's AUCs of 0.825 and 0.769 came from a leaked model and phantom programs (AUDIT.md, C33–C34).



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
| Approval date (sampled as approved, dated 2015 or later) | 24 | 96% (80%–99%) | 1 |
| Approval (sampled as approved before 2015) | 15 | 100% (80%–100%) | 0 |
| Approval (sampled as not approved, Phase 2+ programs) | 31 | 100% (89%–100%) | 0 |
| Approval (sampled as uncertain) | 14 | 64% (39%–84%) | 5 |

Each error pattern these audits found was fixed in the pipeline and the affected labels re-derived, not patched by hand: diseases MONDO has no exact term for now map to their nearest broader term; development codes resolve to UNII substances, and the same substance under two names is merged; scanned FDA letters are read by OCR; labelling-only supplements no longer count as approvals; stop reasons stated only in a trial's summary are read; publication-based outcomes use only the abstracts given; and approval dates account for older applications of the same drug. The disease-mapping, entity and approval figures above come from fresh samples drawn after those fixes; before them, disease mapping agreed 94% of the time, entity resolution 95%, and 8 of 25 dated first approvals were wrong. Remaining entity errors are scattered (a development code resolved to the wrong substance, a salt chosen over its parent) rather than systematic. Programs whose approval is judged "uncertain" (104 of 24,329 judgements) count as not approved; counting them as approved instead moves no rate by more than a tenth of a percentage point (sensitivity table). The approval audit's strata are those of the judgements it sampled; it was re-scored after the final rebuild against the auditors' own answers, and programs that are no longer development programs left the sample. The audit of the earlier draft, with every claim's verdict and every data issue, is in `AUDIT.md`.

### Limitations

* **Registry programs are not Biomedtracker programs.** BIO counts transitions that analysts record for programs companies disclose; this report counts programs from registered trials. Trials registered only outside ClinicalTrials.gov (ChiCTR, EU CTR, CTIS) are missing, so programs developed there look suspended. Restricting to programs with a US site removes most of the difference.
* **Suspension is inferred from inactivity.** A program counts as suspended when none of its trials has been active within 24 months. The rates move with that window (sensitivity table); BIO dates suspensions from company disclosures instead.
* **Recent entrants are mostly unresolved.** Programs that entered a phase in 2023–2025 are largely still running; the success rate counts only resolved programs, so it leans on early failures. Entries from 2015–2019 alone, with at least six years of follow-up, are shown as a sensitivity.
* **Outcome is FDA approval only.** Approvals elsewhere count as no approval.
* **Symptom and procedure indications without a MONDO term** (pain, cough, contraception; about 3% of trials) are grouped in each entity's disease-unspecified program, followed through Phase 2 but not to approval.
* **Most stopped programs give no reason.** Reasons come from the registry's why-stopped field, posted results and abstracts of results papers. Published results favour positive findings, and a missing reason is reported as such, not inferred.
* **The model declines some products.** Claude declines to classify some products derived from pathogens, toxins or live bacterial and viral vectors (botulinum and plague vaccines, oncolytic viruses, engineered bacteria) on every attempt: 162 entities have no resolved target and 53 no modality, so they fall out of Section 2 and the modality strata.
* **Constraint and essentiality are current.** gnomAD v4.1 constraint and DepMap pan-essentiality are today's values, not values as of phase entry.
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
