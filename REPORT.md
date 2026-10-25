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

The report has three parts:

1. **Industry failure modes.** Phase transitions, likelihood of approval (LOA) and the reasons programs stop, for programs that entered each phase in 2015–2025: an updated companion to BIO's *Clinical Development Success Rates 2011–2020*.
2. **Predictive power of preclinical evidence.** For programs aimed at a human protein target, whether the target had human genetic, somatic, animal-model, expression, pathway or functional-screen evidence for the program's disease, as known before the program entered the phase, and how much each line changes the chance of approval.
3. **What translates to the clinic.** Which kinds of evidence, at what strength and in which direction, predicted that a Phase 2 program would advance; on which trial endpoints the advantage shows; and which decision rules applied at Phase 2 entry predicted well enough to call a model, with verified case studies.

Every classification in the pipeline (entity resolution, disease mapping, trial purpose and roles, approvals, stop reasons, trial outcomes, targets, trial endpoints, gene–disease mechanisms and mouse-model relations) was made by an LLM reading the source record and recorded with its prompt and input. Disease mapping, entity resolution, approved uses, program approvals, stop reasons and trial outcomes were also checked against an independent re-derivation of a seeded sample (Appendix); trial purposes and roles were re-decided under a second prompt version and agree with the first on 98% and 97% of trials, and disease mapping, decided twice, chose the same MONDO term for 92% of conditions; modality, disease area and targets were not audited, and the Section 3 labels were spot-checked as described there.


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

For development programs that entered a phase in 2015–2025 and were developed in the US, the likelihood of FDA approval from Phase 1 is 10.4% (95% CI 9.2%–11.8%), against BIO's 7.9% for 2011–2020 (6.8% for novel drugs). Across all industry programs registered on ClinicalTrials.gov, including those run only outside the US, it is 7.3%. Most programs stop without a stated reason: of 6,604 programs that stopped, 43% left no stated reason and no posted or published result, and 21% record an efficacy, safety or pharmacokinetic reason.

### How programs are counted

* **Trial:** a registered interventional study listing Early Phase 1 to Phase 3. A Phase 1/2 trial counts as Phase 2 and a Phase 2/3 trial as Phase 3. Withdrawn trials never enrolled and are left out.
* **Molecular entity:** the active substance, whatever its brand, sponsor code, dose or salt, resolved to its FDA UNII substance where one exists. Biosimilars fold into their reference entity.
* **Disease:** the MONDO term for the condition the trial treats, without line, stage, biomarker or age qualifiers.
* **Program:** one entity developed for one indication. An indication groups the entity's MONDO diseases the way a sponsor runs them as programs (prostate cancer with castration-resistant and metastatic prostate carcinoma; diffuse large B-cell and follicular lymphoma kept apart), decided by an LLM for each entity. An entity belongs to a program only in trials where it is the investigational agent, not a comparator or background therapy. Each industry trial's purpose is classified first: bioequivalence, formulation, food-effect, interaction and other product-support studies (10,770 trials) belong to no program; a first-in-human study or a basket across several diseases counts as Phase 1 only for the program the sponsor pursued next.
* **Phase entry and outcome:** a program enters a phase when its first industry-sponsored trial of that phase starts. It *advanced* when a later-phase trial in its disease started (any sponsor). A trial that has not started, because it is still not yet recruiting or its record went silent before its estimated start date, marks neither entry nor advancement or the FDA approved the entity for the disease; it is *suspended* when none of its trials, nor the trial that marked its Phase 1 entry, has been active within 24 months of the snapshot (2026-10-20); otherwise it is still running and *censored*. Programs whose entity was already approved for the disease are lifecycle programs and are left out; an approval dated only as before 2015 is placed at the entity's first FDA approval, the earliest it could have happened. As in BIO's report, a phase a program skipped (Phase 1 straight to Phase 3, or approval from Phase 2) counts as a success in that phase, each phase's success rate is advanced ÷ (advanced + suspended), and LOA is their product. *US-developed* programs are those with a US-sited industry trial in the phase; a cohort with fewer than ten entities resolved in a phase gets no LOA.
* **Approval:** FDA approval of the entity for the program's disease, a subtype or population of it, or a broader approved class that includes it, judged from the dated approval letters, original-approval dates and labels of every application of the entity (CDER and CBER).

16,562 programs of 9,945 entities entered at least one phase in 2015–2025.

### Phase transitions

| Transition | All programs (95% CI) | Developed in the US (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- |
| Phase 1 → Phase 2 | 56.2% (54.4–58.0), n=5,632 | 56.5% (53.9–59.0), n=3,091 | 52.0% |
| Phase 2 → Phase 3 | 34.4% (32.7–36.0), n=4,836 | 34.7% (32.4–36.8), n=2,981 | 28.9% |
| Phase 3 → Approval | 37.9% (34.9–41.1), n=1,550 | 53.2% (49.6–56.8), n=1,061 | 52.4% |
| **Phase 1 → Approval (LOA)** | **7.3%** (6.5–8.2) | **10.4%** (9.2–11.8) | **7.9%** (novel drugs 6.8%) |

Programs developed in the US, the closest match to BIO's FDA-focused Biomedtracker programs, advance from Phase 1 at 56.5% (BIO 52.0%), from Phase 2 at 34.7% (BIO 28.9%) and from Phase 3 to approval at 53.2% (BIO 52.4%). Phase 2 remains the steepest single drop. Across all registered industry programs the Phase 3 rate falls to 37.9%, because many programs run only outside the US end in approvals elsewhere, which this report does not count.

The likelihood of approval depends on choices a registry-based count has to make, and the table below shows how far each moves it. It is most sensitive to how long a program must be idle before it counts as suspended: 5.3% with a 12-month window and 10.5% with 36 months (24 in the headline). If every shared trial (a healthy-volunteer study, a basket) counted as the start of every later indication of the drug, LOA would rise to 12.4%, mostly by crediting indication expansions begun at Phase 2 with a Phase 1 success. Restricting to programs that entered a phase in 2015–2019, which have had at least six years to resolve, changes little (10.6% for US-developed programs). Vaccines are left out of the headline figures: annual and variant strain updates are licensed as supplements to the parent product, so registry entities for updated formulations never reach an approval of their own (LOA with vaccines included: 6.5%).


| Cohort or definition | Ph1→2 | Ph2→3 | Ph3→approval | LOA (95% CI) |
| :---- | :---- | :---- | :---- | :---- |
| All programs | 56.2% | 34.4% | 37.9% | 7.3% (6.5–8.2) |
| Programs with a US-sited industry trial in the phase | 56.5% | 34.7% | 53.2% | 10.4% (9.2–11.8) |
| Entity not yet FDA-approved at phase entry | 55.4% | 33.7% | 37.7% | 7.0% (6.2–7.8) |
| Entity already FDA-approved for another disease | 61.3% | 39.4% | 38.7% | 9.3% (6.9–12.0) |
| Suspension lag 12 months | 51.2% | 30.2% | 33.9% | 5.3% (4.7–5.9) |
| Suspension lag 18 months | 53.3% | 32.0% | 35.7% | 6.1% (5.4–6.8) |
| Suspension lag 36 months | 61.7% | 39.2% | 43.4% | 10.5% (9.4–11.6) |
| Uncertain approvals counted as approved | 56.2% | 34.4% | 38.0% | 7.3% (6.6–8.2) |
| Shared trials mark entry for every program of the entity | 67.5% | 46.7% | 39.3% | 12.4% (10.9–14.0) |
| Including vaccines | 54.8% | 33.7% | 35.4% | 6.5% (5.9–7.3) |
| Phase entry 2015-2019 (at least six years of follow-up) | 54.8% | 31.2% | 42.0% | 7.2% (6.2–8.2) |
| Phase entry 2015-2019, developed in the US | 56.8% | 34.0% | 55.1% | 10.6% (9.1–12.2) |

### Why programs stop

Each suspended program takes one reason from the industry trials of the phase it stopped in, in this order: an efficacy reason stated by the sponsor, a primary endpoint missed in posted or published results, a safety signal, a pharmacokinetic or formulation problem, an explicit business or strategic reason, a bare "sponsor decision", an enrollment, operational or regulatory reason, a positive primary readout without advancement, another stated reason, posted results with no stated reason or readable endpoint, and finally neither a reason nor a result.

| Reason | Phase 1 | Phase 2 | Phase 3 |
| :---- | :---- | :---- | :---- |
| PK, dose or formulation | 1% (20) | 0% (8) | 0% (0) |
| business or strategic (explicit) | 13% (311) | 9% (275) | 6% (62) |
| completed, no results posted, no reason stated | 51% (1,247) | 20% (646) | 22% (207) |
| efficacy: primary endpoint not met | 0% (7) | 20% (621) | 18% (170) |
| efficacy: stated | 3% (65) | 6% (195) | 12% (115) |
| enrollment, operational or regulatory | 3% (67) | 6% (182) | 4% (42) |
| other stated reason | 1% (16) | 0% (15) | 1% (5) |
| positive readout, not advanced | 1% (13) | 9% (301) | 19% (181) |
| results posted, no reason stated, endpoint not assessable | 10% (239) | 12% (367) | 3% (27) |
| safety | 2% (54) | 3% (82) | 3% (32) |
| sponsor decision, unspecified | 4% (108) | 4% (138) | 3% (30) |
| stopped, no reason stated | 13% (321) | 11% (344) | 9% (91) |

![Why suspended programs stopped, by phase](report/output/figures/failure_modes_by_phase.png)

The registry rarely says why a program stopped. In Phase 1, 64% of stopped programs left neither a stated reason nor a result, which is expected: Phase 1 trials seldom post results and companies seldom explain pausing early assets. In Phase 2 and Phase 3 the share without a reason falls to 31% and 31%. Efficacy is the recorded reason for 26% of programs that stopped in Phase 2 and 30% of those that stopped in Phase 3: the sponsor said so, or the posted or published primary endpoint was missed. Safety accounts for 3% and 3%: among Phase 2 and Phase 3 stops with an efficacy or safety reason, safety is 9% and 10%, against about 32% in Harrison (2016), whose 2013–2015 failures with a disclosed reason were 24% safety and 52% efficacy. Either registry records under-report safety stops, or company disclosures over-represent them.

At the level of individual trials, the 5,557 industry trials started in 2015–2025 that stopped early or were withdrawn with a reason give: an explicit business, portfolio or competitive reason 36%, a bare "sponsor decision" 19%, efficacy 14%, enrollment or operations 14% and safety 4%. The draft's single 44% "commercial or strategic" category mixed these two kinds of statement; a "sponsor decision" with no reason may or may not hide an efficacy result, and the record cannot tell. No study has measured how often a stated business reason hides an efficacy or safety failure. Where a registry gives a reason it mostly agrees with the trial's publication (53 of 57 in [Alturki et al. 2017](https://doi.org/10.1016/j.jclinepi.2016.08.011)); the usual gap is a missing reason. Analysts who also read company filings, press releases and regulator records attribute 57% of drug failures in pivotal trials to efficacy, 17% to safety and 22% to commercial reasons ([Hwang et al. 2016](https://doi.org/10.1001/jamainternmed.2016.6008)), so the efficacy and safety shares here are a floor.

Finally, 19% of Phase 3 programs that stopped short of FDA approval had met their primary endpoint. In a sample we read, most of them were approved outside the US (Japan, China, Korea, Russia) or received a complete response letter from the FDA: a positive Phase 3 readout is necessary but not sufficient for US approval.


### By disease area and modality

| Disease area | All programs, LOA (95% CI) | Entities | Developed in the US, LOA (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- | :---- |
| Hematology | 19.6% (12.4–27.2) | 260 | 18.5% (9.9–28.3) | 23.9% |
| Metabolic | 17.8% (12.1–24.0) | 398 | 25.8% (17.7–34.9) | 15.5% |
| Oncology | 17.8% (14.6–20.8) | 2,502 | 21.2% (17.4–25.3) | 5.3% |
| Endocrine | 12.7% (6.9–19.2) | 308 | 27.4% (18.1–37.1) | 6.6% |
| Psychiatry | 11.0% (5.7–16.5) | 273 | 13.7% (8.0–19.8) | 7.3% |
| Allergy | 10.4% (4.7–17.9) | 129 | 11.6% (4.4–21.9) | 10.3% |
| Autoimmune | 10.2% (6.9–13.8) | 626 | 10.5% (6.9–15.0) | 10.7% |
| Neurology | 9.2% (6.9–11.7) | 868 | 14.1% (10.4–17.9) | 5.9% |
| Other | 7.2% (5.2–9.3) | 876 | 9.8% (6.8–13.0) | 13.0% |
| Respiratory | 7.0% (4.2–10.4) | 463 | 8.6% (4.8–13.1) | 7.5% |
| Cardiovascular | 5.6% (2.8–9.2) | 351 | 12.4% (6.7–19.7) | 4.8% |
| Ophthalmology | 5.1% (2.9–7.9) | 408 | 6.1% (3.1–9.7) | 11.9% |
| Infectious disease | 3.8% (2.7–5.2) | 891 | 5.9% (3.8–8.4) | 13.2% |
| Gastroenterology | 2.8% (1.0–5.1) | 324 | 6.6% (2.8–11.0) | 8.3% |
| Urology | 1.3% (0.0–5.1) | 64 | – | 3.6% |

| Modality | All programs, LOA (95% CI) | Entities | Developed in the US, LOA (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- | :---- |
| Multispecific antibody | 22.7% (13.0–32.0) | 470 | 24.5% (14.1–33.4) | – |
| Antibody–drug conjugate | 21.0% (8.1–34.2) | 403 | 18.3% (6.7–32.2) | 10.8% |
| Monoclonal antibody | 14.1% (10.9–17.3) | 1,266 | 16.0% (12.1–20.1) | 12.1% |
| Antisense oligonucleotide | 13.5% (5.6–24.2) | 112 | 16.8% (6.6–31.2) | 5.2% |
| Peptide | 9.8% (4.8–14.9) | 342 | 12.9% (6.4–20.2) | 8.0% |
| Small molecule | 6.4% (5.5–7.4) | 5,059 | 9.7% (8.3–11.3) | 7.5% |
| Gene therapy | 5.9% (1.8–13.5) | 232 | 6.7% (1.6–15.0) | 10.0% |
| Protein | 4.5% (2.6–6.6) | 529 | 4.9% (2.6–7.6) | 9.4% |
| Other cell therapy | 1.3% (0.4–2.8) | 482 | 2.3% (0.5–5.8) | – |
| Other | 0.1% (0.0–0.5) | 277 | – | – |

![Likelihood of approval by disease area](report/output/figures/loa_by_area.png)

![Likelihood of approval by modality](report/output/figures/loa_by_modality.png)

Disease areas rank differently from BIO's: the rank correlation with BIO's LOA across the 15 areas is 0.26 for all programs and -0.26 for US-developed ones. Across all programs, hematology, metabolic and oncology programs reach approval most often (19.6%, 17.8% and 17.8%), and urology, gastroenterology and infectious-disease programs least. Among US-developed programs, endocrine (27.4%) and oncology programs (21.2%) come out far above BIO's 6.6% and 5.3%; for oncology, the 2015–2025 window holds the wave of immunotherapy, antibody–drug conjugate and bispecific approvals, and an approval in a cancer subtype counts for the program's cancer. Infectious disease (5.9%) sits far below BIO's 13.2%, largely because many registered anti-infective and COVID-19 programs, including US-run ones, were never approved; ophthalmology (6.1%) and gastroenterology (6.6%) also fall below BIO's 11.9% and 8.3%. Among modalities, multispecific antibodies and antibody–drug conjugates reach approval most often across all programs (22.7% and 21.0%), and among the classes BIO also reports, non-antibody proteins (4.5%), gene therapies (5.9%) and small molecules (6.4%) least. RNA interference and CAR-T, near the top of BIO's ordering, have too few entities resolved in Phase 3 here (most of their approvals came straight from Phase 2) to estimate. The modality ordering agrees with BIO's only loosely (rank correlation 0.32 across the 7 classes both estimate).



## Predictive power of preclinical evidence

Human genetic evidence linking a program's target to its disease is the clearest preclinical signal of success. Programs whose target had it before they entered the phase reached FDA approval 2.80 times as often as programs without it (30.8% against 11.0%; 95% CI 2.16–3.61), the likelihood rises with the strength of the evidence, and the association holds at every phase after accounting for disease area, modality, novelty and era. Somatic driver and mouse-model evidence carry weaker signals; targets essential in every cancer cell line are a liability. Yet as a predictor of which individual programs will be approved, the evidence lines raise discrimination only modestly over disease area and modality (held-out AUC 0.611 to 0.665), because most programs have none of them.


### Evidence lines and how they are matched

Each program aimed at a human protein (the entity's primary targets, resolved by an LLM from the entity's mechanism records and trial descriptions) is scored for the evidence its targets had **for the program's disease** in Open Targets Platform 26.09, **as of the year before the program entered the phase**. A target–disease association counts for the program's disease when the evidence disease is the same MONDO term, a subtype of it, or similar to it (Lin similarity ≥ 0.8, the criterion Minikel et al. used). Open Targets publishes a yearly series of each association's score, so evidence is taken as it stood before phase entry, not as it stands today. Evidence lines:

* **Human germline genetics:** GWAS credible sets (with locus-to-gene scores), gene burden tests, ClinVar, Genomics England PanelApp, Orphanet, Gene2Phenotype, ClinGen and UniProt; split into GWAS and rare-variant/Mendelian sources.
* **Somatic drivers:** COSMIC Cancer Gene Census, IntOGen and ClinVar somatic.
* **Mouse models:** IMPC phenotypes. **Expression:** differential expression in the disease (Expression Atlas). **Pathways:** Reactome. **Functional screens:** CRISPR screens.
* **Target-level properties** that are not disease-specific: loss-of-function intolerance (gnomAD v4.1 LOEUF < 0.35) and pan-essentiality across DepMap cell lines, taken from the current releases rather than as of phase entry.

Sources that encode clinical outcomes or literature co-mention (ChEMBL clinical precedence, Europe PMC) are not used. Vaccines, cell and gene therapies and other entities without a single human protein target fall outside this analysis, so its programs reach approval more often than the Section 1 cohort as a whole. Of the 9,993 programs on 1,388 targets scored, 14.8% of Phase 1 entrants had human genetic evidence for their disease at entry.

### Relative success

*Relative success* is the LOA of programs with the evidence divided by the LOA of programs without it (Nelson et al. 2015; Minikel et al. 2024). The 95% intervals resample primary-target sets (an entity's primary targets taken together), since programs on the same targets are not independent.

| Evidence line | Programs with it | LOA with / without | Relative success (95% CI) |
| :---- | :---- | :---- | :---- |
| Rare-variant / Mendelian (ClinVar, Orphanet, G2P, ClinGen, burden) | 1,003 | 33.9% / 11.8% | 2.87 (2.24–3.68) |
| Human genetics (any germline source) | 1,651 | 30.8% / 11.0% | 2.80 (2.16–3.61) |
| Somatic driver (COSMIC CGC, IntOGen, ClinVar somatic) | 1,658 | 27.1% / 12.0% | 2.26 (1.58–2.99) |
| GWAS credible set | 846 | 25.2% / 12.7% | 1.99 (1.33–2.79) |
| Pathway (Reactome) | 202 | 25.6% / 13.3% | 1.92 (1.08–3.05) |
| Mouse model (IMPC) | 1,945 | 17.5% / 12.6% | 1.39 (1.04–1.79) |
| Differential expression in disease (Expression Atlas) | 1,333 | 17.6% / 13.1% | 1.34 (0.92–1.82) |
| LoF-intolerant target (gnomAD LOEUF < 0.35) | 1,820 | 13.7% / 13.6% | 1.01 (0.71–1.48) |
| Pan-essential (DepMap) | 537 | 5.6% / 14.0% | 0.40 (0.17–0.73) |

![Relative success by evidence line](report/output/figures/relative_success_by_evidence.png)

Rare-variant and Mendelian evidence (2.87×) and GWAS evidence (1.99×) both carry the genetic signal, in line with Minikel et al. (2024), who found 2.6× from Phase 1 to launch with Mendelian evidence stronger than GWAS. Somatic driver evidence (2.26×), mouse phenotypes (1.39×) and Reactome pathways (1.92×, from only 202 programs) also associate with success; differential expression in the disease does not clearly (1.34×, interval spanning 1). Loss-of-function-intolerant targets show no penalty (1.01×), while pan-essential targets reach approval less than half as often (0.40×), mostly oncology small molecules aimed at machinery every cell needs (mTOR, tubulin, topoisomerases, histone deacetylases, WEE1 and ATR, BET proteins). CRISPR-screen evidence covered too few programs (61) to estimate.

Two checks bear on whether this reflects foresight rather than hindsight. Evidence is taken as it stood in Open Targets' yearly series before the program entered the phase, so later discoveries do not count. Counting all evidence known by 2026 instead weakens the genetic relative success to 2.39×: what was known in advance is more telling than what was found afterwards. And restricting matches to diseases similar to the program's (Lin ≥ 0.8, Minikel's criterion, without the subtype rule) gives 2.80×.


### Genetic dose–response

| Human genetic support (Open Targets score, as of phase entry) | Programs | Targets | LOA (95% CI) |
| :---- | :---- | :---- | :---- |
| None | 8,417 | 1,264 | 11.0% (8.9–13.5) |
| Lower third (> 0.00 to 0.61) | 644 | 278 | 21.4% (14.8–29.3) |
| Middle third (> 0.61 to 0.88) | 521 | 194 | 36.0% (25.9–45.1) |
| Upper third (> 0.88) | 563 | 212 | 37.8% (29.9–46.8) |

![Likelihood of approval by strength of human genetic support](report/output/figures/genetic_dose_response.png)

### What each line adds once the others are known

Programs with genetic evidence differ from programs without it in disease area, modality and era, and the evidence lines overlap. The table gives, for each phase, the relative risk of advancing for programs with each line, from one Poisson model containing every line together with disease area, modality, entity novelty and entry period (standard errors clustered by primary-target set).

| Evidence | Phase 1 → next | Phase 2 → next | Phase 3 → next |
| :---- | :---- | :---- | :---- |
| GWAS credible set | 1.08 (1.02–1.15) | 1.54 (1.32–1.79) | 1.02 (0.75–1.38) |
| Rare-variant / Mendelian (ClinVar, Orphanet, G2P, ClinGen, burden) | 1.08 (0.99–1.17) | 1.35 (1.17–1.55) | 1.57 (1.30–1.89) |
| Somatic driver (COSMIC CGC, IntOGen, ClinVar somatic) | 0.99 (0.89–1.10) | 1.12 (0.91–1.38) | 1.09 (0.86–1.38) |
| Mouse model (IMPC) | 0.95 (0.89–1.01) | 0.98 (0.86–1.10) | 0.95 (0.80–1.13) |
| Differential expression in disease (Expression Atlas) | 0.98 (0.91–1.06) | 1.02 (0.87–1.20) | 0.89 (0.72–1.10) |
| Pathway (Reactome) | 1.09 (0.96–1.24) | 0.98 (0.75–1.28) | 1.08 (0.77–1.52) |
| LoF-intolerant target (gnomAD LOEUF < 0.35) | 0.98 (0.88–1.09) | 1.17 (0.99–1.37) | 1.03 (0.83–1.28) |
| Pan-essential (DepMap) | 0.79 (0.62–1.01) | 0.68 (0.50–0.94) | 0.73 (0.45–1.17) |

One evidence line at a time, with the same adjustments, human genetic evidence raises the chance of advancing by 1.08× in Phase 1, 1.61× in Phase 2 and 1.43× in Phase 3: the effect sits where efficacy is first tested. In the joint model, GWAS and rare-variant evidence each keep an independent effect at Phase 2, rare-variant evidence also at Phase 3 and GWAS a small one at Phase 1, and pan-essentiality keeps its penalty at Phase 2 (at Phase 1 its interval just reaches 1); somatic, mouse-model, expression and pathway evidence lose their association once genetics and the covariates are in the model, consistent with their univariate signal riding along with genetic support and with disease area.


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

A model on disease area, modality, novelty and entry year alone ranks programs at an AUC of 0.611 on held-out target sets; adding the evidence lines raises it to 0.665 (95% CI 0.602–0.723), and the temporal split agrees (0.617 without, 0.655 with). Human genetics carries most of the gain: removing it lowers the held-out AUC by 0.028 (95% CI 0.002–0.053), and pan-essentiality is the only other line whose removal measurably lowers it (0.015). GWAS evidence covered too few of the 2008–2016 entrants to be modelled, so genetics here means rare-variant and Mendelian evidence. Discrimination stays modest all the same, and that does not contradict the relative success: genetic support multiplies the chance of approval by about 2.80 for the minority of programs that have it (15% of Phase 1 entrants, fewer among the 2008–2016 entrants this model follows), but says nothing about the majority, so it can sort only a small slice of programs. The draft's AUCs of 0.825 and 0.769 came from a leaked model and phantom programs (AUDIT.md, C33–C34).



## What translates to the clinic

Human genetic evidence for the program's own disease is the one kind of preclinical evidence that consistently carried over into Phase 2. Outside oncology, programs whose target had germline genetic evidence for the disease before they entered Phase 2 reached Phase 3 or approval within four years 2.29 times as often as programs whose target had no germline genetic evidence at all (31% against 13%), and the advantage shrinks as the evidence moves to a related disease (23%) or to unrelated diseases only (17%). The same target does better in the diseases its genetics points to than in its other diseases (odds ratio 3.43), and the effect holds after accounting for an approved drug on the target. The advantage shows in efficacy: genetically supported programs stopped for efficacy less often (business and operational stops fell about as much), and their trials missed the primary endpoint less often on regulatory surrogates and clinician-rated scales; on patient-reported, exploratory-biomarker and event endpoints the difference was small or absent. Somatic drivers in oncology and Reactome pathway evidence carried weaker signals, literature mouse models a marginal one and differential expression none, and a mouse model whose direction matched the drug's did not predict Phase 2 success. Whether the direction of the genetic effect matters could not be tested, because almost no program went against an established mechanism. Of the rules a sponsor could have applied at Phase 2 entry, only the benchmark, an approved drug on the same target for a related disease, met the pre-registered bar for a particularly predictive model; Mendelian evidence for a non-hereditary disease came closest. Genetic support covered only 24% of the programs that advanced.


### Design

The analysis plan ([report/translation_plan.md](report/translation_plan.md)) was committed before any of these analyses touched outcomes; departures from it are marked below.

* **Cohort and outcome.** Programs on a human protein target that entered Phase 2 from 2015-01-01 to 2020-10-20 (2,538 programs on 874 primary-target sets). Each has at least four years of follow-up before the 24-month inactivity cutoff, so the outcome needs no inferred suspension: a program *advanced* if a Phase 3 trial of its own started, or the FDA approved it for the disease, within four years of entering Phase 2 (18.2% did). The same is done for Phase 1 entrants (a negative control: genetics should matter little for safety and dosing studies) and Phase 3 entrants (approval within four years).
* **Evidence.** Every Open Targets 26.09 evidence row for the program's primary targets, each carrying its own date, frozen at the year before entry and matched to the program's disease on MONDO: the same term, a subtype, or Lin similarity ≥ 0.8 (*G3*, genetics for the disease); a disease at Lin 0.5–0.8 only (*G2*); germline evidence only for unrelated diseases (*G1*); none (*G0*). Evidence is split by family and strength (the best GWAS locus-to-gene score, ≥ 0.8, 0.5–0.8 or below; ClinVar pathogenic with multiple submitters or expert review, ClinGen or Gene2Phenotype definitive or strong, PanelApp green; mouse phenotype match in the top quartile), and mouse models are split into IMPC high-throughput knockouts and literature-curated MGI models.
* **Regimes.** Oncology; *hereditary* (the disease is a MONDO hereditary disease and the target has curated Mendelian evidence for it); and every other disease (*non-oncology*, the regime of the headline hypothesis).
* **Models.** Modified Poisson regression (risk ratios) with standard errors clustered by primary-target set, adjusted for disease area, modality, entity novelty, entry period and target precedent (an FDA-approved entity on the target before entry). The seven confirmatory hypotheses are Holm-corrected together.
* **Trials.** Randomised industry Phase 2/3 trials since 2010 whose governing primary endpoint measures efficacy and whose result is readable (5,651 trials; an LLM classified each trial's governing primary endpoint from its registry entry, without the drug's name). Outcome: primary endpoint not met (a mixed result counts as not met).

### Confirmatory hypotheses

|  | Hypothesis | Measure | Estimate (95% CI) | p | Holm p | Result |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| H1 | Outside oncology: genetics for the disease (G3) vs no germline genetics (G0), advancing within 4 years of Phase 2 | risk ratio | 2.29 (1.31–3.99) | 0.003 | 0.021 | supported |
| H2 | Same target, different diseases: G3 vs not (conditional logit) | odds ratio | 3.43 (2.09–5.64) | < 0.001 | < 0.001 | supported |
| H3 | Direction of genetic effect vs drug action (Open Targets direction fields): discordant < undirected < concordant | risk ratio per step | 0.80 (0.56–1.13) | 0.205 | 0.821 | not supported |
| H4 | Trials outside oncology: change in G3's effect on NOT MET per step from proximal to distal endpoints (registry-posted results, FDAAA era) | ratio of risk ratios | 1.27 (1.01–1.59) | 0.042 | 0.211 | not supported |
| H5 | G3 lowers efficacy failure more than business or operational failure (Phase 2 and 3) | ratio of risk ratios | 1.06 (0.63–1.78) | 0.839 | 1.000 | not supported |
| H6 | Outside oncology, target liability raises safety failure, and more than efficacy failure (Phases 1–3; intersection-union test) | risk ratio, safety failure | 0.87 (0.43–1.76) | 0.953 | 1.000 | not supported |
| H7 | Oncology: a somatic driver whose direction matches the drug, advancing within 4 years of Phase 2 | risk ratio | 1.19 (0.76–1.85) | 0.452 | 1.000 | not supported |

Two of the seven hypotheses hold after correction for multiple testing.

* **H1, H2 (supported).** Outside oncology, Phase 2 programs advanced within four years at 13% with no germline genetic evidence on the target (181 programs), 17% with evidence only for unrelated diseases (1,023), 23% with evidence for a related disease (144) and 31% with evidence for the disease itself (150); only the last differs from none once disease area, modality, novelty, period and target precedent are accounted for. Among the 59 targets developed in several diseases with and without genetic support and with different outcomes (452 programs), the diseases with support advanced more often (odds ratio 3.43, 2.09–5.64): the signal is not only that some targets are better than others.
* **H3 (not supported).** Open Targets' direction-of-effect fields follow each variant's predicted consequence, so a few truncating ClinVar variants make gain-of-function disease genes such as PCSK9, MYH7 and TTR read as loss of function, and inhibitors of them as discordant. The test is reported as registered; the direction analysis below replaces those fields.
* **H4 (not supported).** In trials with registry-posted results, genetic support lowered the chance of missing the primary endpoint most on proximal endpoints, and the effect weakened by a factor of 1.27 per step towards distal endpoints (p = 0.042). That does not survive correction, nor hold across all readable trials (1.09, p = 0.407) or with mixed results counted as met (1.21).
* **H5 (not supported).** Genetic support lowered efficacy stops (risk ratio 0.71, 0.53–0.95), but business and operational stops fell by a similar factor (ratio of the two 1.06, 0.63–1.78), so the data cannot say that it acts on efficacy alone. Safety stops were no rarer (1.46, 0.75–2.85).
* **H6 (not supported).** Targets that are pan-essential, intolerant of loss of function, or lethal when knocked out in mice did not stop for safety more often (0.87, 0.43–1.76). Safety is the recorded reason for fewer than 2% of programs, so registries see little of it.
* **H7 (not supported).** In oncology, a somatic driver whose direction matches the drug's (an activated oncogene and an inhibitor) did not raise the chance of advancing (1.19, 0.76–1.85).

**Checks on H1.** Swapping each program's disease for another program's in the same disease area, 200 times, gives a median G3 risk ratio of 1.66 against the observed 2.29 (95th percentile 2.15; p = 0.015). Part of the contrast with G0 therefore reflects whether a target has been studied genetically at all; matching the disease adds to it. At Phase 1, where efficacy is rarely tested, the same contrast is 1.23 (0.99–1.53). Against all other programs rather than G0, genetic support gives 1.89 outside oncology, and 1.74 (1.28–2.36) after adjusting for an approved drug on the target for a related disease; on targets with no approved drug at all, genetic support gives 1.51 (0.97–2.35, all disease areas). Leaving out the most influential target set (PDE4A+PDE4B+PDE4C+PDE4D) gives 2.19; leaving out all targets classed as "other protein", the largest class, gives 1.75 (0.85–3.61), so the estimate leans on that class.

**Who is in the cohort.** The cohort is Phase 2 programs with a disease and a single resolved human protein target. Left out are 260 programs with no disease (healthy-volunteer, basket or symptom trials; 6% advanced) and 752 without a single human protein target (9%), so the cohort's base rate is higher than Section 1's.


### Which evidence translates

| Evidence for the program's disease, before entry | Programs (targets) | Advanced: with / without | Share of all that advanced | Risk ratio vs programs without it, all (95% CI) | Non-oncology | Oncology | Evidence known today |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Human germline genetics for the disease (G3) | 351 (186) | 31% / 16% | 24% | 1.95 (1.56–2.45) | 1.89 (1.40–2.56) | 2.23 (1.46–3.41) | 1.65 (n=582) |
| GWAS, any locus-to-gene | 149 (83) | 28% / 18% | 9% | 1.60 (1.17–2.19) | 1.77 (1.22–2.59) | 1.79 (0.94–3.38) | 1.59 (n=418) |
| GWAS, locus-to-gene >= 0.8 | 68 (41) | 29% / 18% | 4% | 1.61 (1.08–2.42) | 1.74 (1.11–2.73) | – | 1.58 (n=216) |
| GWAS, best locus-to-gene 0.5-0.8 | 36 (23) | 17% / 18% | 1% | 0.94 (0.46–1.91) | – | – | 1.61 (n=81) |
| GWAS, best locus-to-gene < 0.5 | 45 (27) | 33% / 18% | 3% | 1.99 (1.22–3.25) | 2.14 (1.24–3.69) | – | 1.22 (n=121) |
| Mendelian / ClinVar pathogenic | 225 (122) | 32% / 17% | 16% | 1.91 (1.45–2.51) | 1.96 (1.35–2.84) | 2.13 (1.31–3.45) | 1.70 (n=270) |
| Mendelian, top-tier curation | 157 (84) | 33% / 17% | 11% | 2.11 (1.52–2.93) | 1.93 (1.19–3.12) | – | 1.92 (n=175) |
| Somatic driver, any | 332 (102) | 23% / 18% | 16% | 1.37 (0.97–1.94) | – | 1.51 (1.04–2.19) | 1.26 (n=373) |
| Somatic driver, concordant with drug action | 223 (69) | 21% / 18% | 10% | 1.16 (0.77–1.76) | – | 1.19 (0.76–1.85) | 1.23 (n=245) |
| Mouse model (literature, MGI) | 494 (271) | 23% / 17% | 25% | 1.26 (0.98–1.62) | 1.22 (0.92–1.60) | 1.19 (0.63–2.24) | 1.27 (n=499) |
| Literature mouse model, top-quartile match | 311 (177) | 23% / 18% | 15% | 1.18 (0.92–1.50) | 1.12 (0.82–1.54) | 0.96 (0.58–1.59) | 1.18 (n=316) |
| Differential expression in disease | 317 (177) | 19% / 18% | 13% | 1.11 (0.75–1.63) | 0.62 (0.34–1.14) | 1.42 (0.91–2.21) | 1.09 (n=386) |
| Pathway (Reactome) | 66 (33) | 30% / 18% | 4% | 1.66 (1.14–2.43) | – | – | 1.60 (n=72) |
| Approved drug on the target for a related disease | 762 (258) | 30% / 13% | 50% | 2.12 (1.60–2.81) | 2.16 (1.57–2.98) | 2.07 (1.11–3.84) | – |
| Approved drug on the target (any disease) | 1,577 (427) | 21% / 13% | 72% | 1.83 (1.47–2.27) | 1.66 (1.27–2.18) | 2.16 (1.42–3.28) | – |
| Pan-essential (DepMap) | 115 (48) | 10% / 19% | 2% | 0.59 (0.32–1.10) | – | 0.48 (0.22–1.05) | – |
| LoF-intolerant (LOEUF < 0.35) | 446 (148) | 18% / 18% | 17% | 1.00 (0.76–1.31) | 1.21 (0.85–1.72) | 0.85 (0.57–1.28) | – |
| Mouse knockout lethal before weaning | 1,173 (393) | 18% / 19% | 45% | 0.92 (0.75–1.14) | 0.89 (0.68–1.18) | 0.92 (0.62–1.35) | – |

![Evidence map](report/output/figures/s3_evidence_map.png)

* **Human genetics.** Mendelian and ClinVar evidence for the disease (1.91; top-tier curation 2.11) and GWAS (1.60) both carry the signal. Within GWAS, the locus-to-gene score did not grade it: the best score at 0.8 or above gives 1.61, 0.5–0.8 gives 0.94 and below 0.5 gives 1.99, each from a few dozen programs. Most GWAS rows in Open Targets are on measurement traits (LDL cholesterol, blood pressure, body-mass index) with no MONDO disease; they count as germline evidence on the target but cannot match a disease, so G3 undercounts genetics found through a trait. Gene burden results start in 2019, too late for these cohorts.
* **Somatic drivers.** In oncology, a somatic driver for the tumour raised the chance of advancing (1.51, 1.04–2.19); requiring the driver's direction to match the drug's did not sharpen it (1.19). Germline genetics for the tumour type was the stronger signal (2.23), carried by well-validated targets such as EGFR, ERBB2 and ESR1.
* **Mouse models.** Literature-curated (MGI) mouse models of the disease gave 1.26 (0.98–1.62), and a top-quartile phenotype match 1.18. Open Targets dates MGI models by the gene's earliest literature rather than the model's, so they look older than they are. Knockouts from the IMPC consortia carry no date of their own, so they cannot be frozen at entry and the IMPC rule is untestable.
* **Expression and pathways.** Differential expression in the disease carried nothing (1.11; outside oncology 0.62). Reactome pathway evidence gave 1.66 from 66 programs, most of them in hereditary diseases, which Reactome curates. No CRISPR-screen evidence matched a program before its entry.
* **Clinical precedent.** An FDA-approved drug on the target for a related disease (Lin similarity ≥ 0.5) was the strongest single predictor (2.12) and was present for 50% of the programs that advanced.
* **Target liabilities.** Pan-essential targets advanced less often (0.59, 0.32–1.10, mostly oncology); loss-of-function intolerance (1.00) and lethality of the mouse knockout (0.92) made no difference.

**Foresight, not hindsight.** Counting all the evidence known today instead of what was known before entry weakens the genetic signal (1.65 against 1.95): evidence that arrived after entry also arrived for targets that failed.

**What the evidence leaves out.** Of the 463 Phase 2 programs that advanced, 24% had germline genetics for the disease, 46% had any of the disease-specific evidence families, and 31% had neither such evidence nor an approved drug on the target for a related disease.


### By endpoint

| Class of the governing primary endpoint | Trials | Not met | Trials with G3 | Not met: with G3 / without | Risk ratio of NOT MET, all readable (95% CI) | Registry-posted, FDAAA era |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Target engagement | 35 | 29% | 18 | 22% / 35% | – | – |
| Exploratory biomarker | 273 | 66% | 30 | 70% / 65% | 1.09 (0.81–1.48) | – |
| Regulatory surrogate (LDL-C, HbA1c, viral load…) | 1,326 | 24% | 261 | 13% / 27% | 0.61 (0.43–0.86) | 0.48 (0.34–0.66) |
| Objective physiology (FEV1, 6MWD, weight…) | 546 | 45% | 104 | 32% / 48% | 0.81 (0.59–1.12) | 0.77 (0.49–1.20) |
| Clinician-rated scale or responder index | 1,447 | 55% | 235 | 43% / 57% | 0.77 (0.62–0.94) | 0.80 (0.64–1.01) |
| Patient-reported outcome | 637 | 55% | 17 | 59% / 55% | 1.25 (0.89–1.75) | – |
| Disease events (relapses, exacerbations…) | 362 | 44% | 56 | 39% / 44% | 0.87 (0.58–1.32) | 0.92 (0.59–1.43) |
| Hard outcome (death, MI, stroke…) | 183 | 62% | 19 | 53% / 63% | – | – |
| Tumour response | 168 | 68% | 33 | 61% / 70% | 0.93 (0.65–1.33) | 0.84 (0.56–1.26) |
| Progression-free survival | 441 | 60% | 86 | 52% / 62% | 1.11 (0.88–1.39) | 1.03 (0.77–1.38) |
| Overall survival | 213 | 67% | 20 | 50% / 69% | – | – |

![Endpoint classes](report/output/figures/s3_endpoints.png)

Across 5,651 randomised industry efficacy trials, 48% missed their governing primary endpoint. Regulatory surrogates were missed least (24%), exploratory biomarkers (66%) and hard outcomes (62%) most.

Genetic support for the disease lowered the chance of a miss most on regulatory surrogates (risk ratio 0.61; 0.48 in trials with registry-posted results since FDAAA) and on clinician-rated scales (0.77). Objective physiology (0.81) and disease events (0.87) point the same way with intervals spanning 1; exploratory biomarkers (1.09), patient-reported outcomes (1.25, only 17 genetically supported trials) and oncology's response and progression endpoints show no benefit. Too few genetically supported trials had hard-outcome or overall-survival primaries to estimate. One reading is that genetic support predicts most reliably that a drug will move the measures nearest its biology, often the trait through which the genetics was found (LDL cholesterol, urate, glycaemia), and less reliably that it will change what patients feel or how often events happen.

At the program level, classifying each Phase 2 program by the endpoint of its first randomised Phase 2 efficacy trial (started within a year of entry and before it advanced), genetic support gives 1.41 (0.81–2.46; 294 programs) where that endpoint was proximal and 1.52 (0.94–2.45; 626) where it was intermediate; distal-endpoint and oncology programs were too few.

The endpoint classifier read each trial's registered primary outcomes without the drug. In an audit of 40 trials stratified by class, it picked the governing outcome correctly in all 40 and the class in 39. Not knowing the drug, it puts FEV1 in the regulatory-surrogate class for every respiratory drug, where the codebook reserves that for bronchodilators; moving the 74 affected trials to the intermediate class barely moves the H4 estimate. Trials still in follow-up with results posted have no outcome label yet and are not counted (about 2% of the H4 trials).


### Direction of effect

A drug that lowers its target's function should help when loss of function protects against the disease or gain of function causes it, and harm or do nothing when loss of function causes it. Open Targets' direction fields cannot test this: they label each variant from its predicted consequence, so the few truncating ClinVar variants listed for PCSK9 in hypercholesterolaemia, MYH7 in hypertrophic cardiomyopathy or TTR in amyloidosis make these gain-of-function diseases read as loss of function; their many pathogenic missense variants carry no direction at all.

We therefore had an LLM state, for every target and disease with germline evidence, without being told any drug, whether disease-causing variants lower or raise the gene's function, whether protective variants are known, and the year each was first shown for that disease. Where Gene2Phenotype records an absent gene product, the label was loss of function in 54 of 57 pairs and never gain of function. A spot check of an earlier version of the labels found somatic cancer mutations counted as germline and some years taken from another disease; the final prompt rules out both.

Sponsors almost never develop against an established mechanism. Of the Phase 2 programs with genetic support, 178 acted in the direction the genetics favoured, 6 against it, and 104 had genetics without an established direction by entry. Concordant programs advanced at 30% and undirected ones at 29%: once there is genetic support, knowing its direction did not pick winners among the programs sponsors chose to run, and the discordant group is too small to show whether going against the genetics fails. Protective loss of function plus a drug that lowers function, the PCSK9 pattern, covered 36 Phase 2 programs on 16 targets, which advanced as often as others (1.02, 0.55–1.91).

Mouse models were treated the same way: for each model, without the drug, whether it lowers or raises the gene's function and whether its phenotypes resemble the disease or its opposite. A model pointing the drug's way (a knockout protected from the disease, for an inhibitor) gave 1.24 (0.91–1.69) against programs with no oriented model, a model pointing the other way 0.99, and nothing once genetic support is accounted for (0.91). Among Phase 3 programs a concordant model went with approval within four years (2.21, 1.42–3.46), one of many comparisons made after the plan.


### Models that predict: rules applied at Phase 2 entry

A *model* here is a rule a sponsor could have applied at Phase 2 entry without knowing the outcome: an evidence family, strength, direction and drug action. Rules M1–M11 and the precedent benchmark B1 were fixed in the plan; P1–P3 (marked \*) were added after the plan, once the direction labels existed. Target sets were split 60/40 at random; a rule counts as *particularly predictive* when, on the discovery targets, its risk ratio's 90% bootstrap lower bound is above 1.3, and, on the held-out targets, its risk ratio is at least 1.2 with a one-sided 95% lower bound above 1, and it stays at least 1.2 without its most influential target.

| Rule | Applied at Phase 2 entry | Regime | Programs (targets) | Advanced | Share of all that advanced | Adjusted RR (95% CI) | Discovery RR (90%) | Held-out RR (90%) | Meets the bar |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| M1 | Protective loss-of-function burden + drug that decreases function | All | 0 (0) | – | 0% | – | – | – | not testable |
| M2 | Mendelian evidence + drug that increases function or replaces the gene | Hereditary | 67 (33) | 21% | 50% | 0.68 (0.38–1.22) | 0.63 (0.31–1.30) | 0.68 (0.11–1.63) | no |
| M3 | Mendelian evidence extrapolated to a common disease | Non-oncology | 53 (42) | 38% | 7% | 1.96 (1.35–2.84) | 2.12 (1.14–3.02) | 2.18 (1.29–3.16) | no |
| M4 | GWAS, locus-to-gene >= 0.8 for the indication | All | 68 (41) | 29% | 4% | 1.61 (1.08–2.42) | 1.62 (1.06–2.20) | 1.68 (0.65–2.58) | no |
| M5 | GWAS and rare-variant evidence for the same disease | All | 23 (16) | 17% | 1% | 0.87 (0.41–1.87) | none advanced | 1.46 (0.63–2.33) | no |
| M6 | Concordant somatic driver + drug that decreases function | Oncology | 212 (66) | 22% | 29% | 1.21 (0.77–1.89) | 1.10 (0.61–1.93) | 2.14 (0.99–3.91) | no |
| M7 | IMPC knockout phenotype matching the disease, top quartile | All | 0 (0) | – | 0% | – | – | – | not testable |
| M8 | Literature-curated mouse model of the disease | All | 494 (271) | 23% | 25% | 1.26 (0.98–1.62) | 1.16 (0.92–1.49) | 1.80 (1.30–2.42) | no |
| M9 | Expression up in disease + drug that decreases function | All | 156 (95) | 19% | 6% | 1.04 (0.67–1.60) | 0.96 (0.56–1.40) | 1.29 (0.47–2.08) | no |
| M10 | Reactome pathway evidence | All | 66 (33) | 30% | 4% | 1.66 (1.14–2.43) | 1.56 (1.10–2.31) | 1.93 (0.74–3.21) | no |
| M11 | Target liability + drug that decreases function | All | 909 (311) | 18% | 36% | 0.99 (0.78–1.25) | 0.94 (0.72–1.22) | 1.07 (0.75–1.46) | no |
| B1 | Approved drug on the target for a disease within Lin 0.5 | All | 762 (258) | 30% | 50% | 2.12 (1.60–2.81) | 2.17 (1.75–2.64) | 2.55 (2.00–3.37) | **predictive** |
| P1* | Protective loss of function established + drug that decreases function | All | 36 (16) | 19% | 2% | 1.02 (0.55–1.91) | 0.78 (0.26–1.53) | 2.05 (0.68–3.33) | no |
| P2* | Germline mechanism concordant with drug action | All | 178 (91) | 30% | 12% | 1.82 (1.33–2.49) | 1.67 (1.26–2.17) | 1.89 (0.99–2.81) | no |
| P3* | Mouse model direction concordant with drug action | All | 175 (109) | 23% | 9% | 1.19 (0.89–1.60) | 1.18 (0.82–1.60) | 1.51 (0.93–2.23) | no |

![Rule screen](report/output/figures/s3_rules.png)

Only the benchmark met the bar: an approved drug on the target for a related disease (762 programs, 30% advanced; held-out risk ratio 2.55). Among evidence rules:

* **Mendelian evidence for a non-hereditary disease (M3)** came closest: 53 programs on 42 targets, 38% advanced, held-out risk ratio 2.18 (90% lower bound 1.29), but its discovery lower bound (1.14) fell short of 1.3. It covers few programs (7% of the non-oncology programs that advanced).
* **GWAS with locus-to-gene ≥ 0.8 (M4)**, **Reactome pathway evidence (M10)** and the post-hoc **germline mechanism concordant with the drug (P2)** have adjusted risk ratios of 1.61, 1.66 and 1.82, but their held-out lower bounds reach 1 or below.
* **Literature mouse models (M8)** gave 1.80 on the held-out targets but 1.16 (90% lower bound 0.92) on the discovery targets: inconsistent between the two halves.
* **Replacing or activating the gene in a hereditary disease (M2)** advanced less often than other programs in hereditary diseases (21% against 32%).
* Expression up plus an inhibitor (M9), target liability plus an inhibitor (M11), the allelic series (M5), protective loss of function plus an inhibitor (P1) and a concordant mouse model (P3) carry no signal. Protective-variant burden evidence (M1) and IMPC knockouts (M7) could not be tested: Open Targets has no burden results before 2019 and no dates for IMPC models.


### Verified case studies

The plan's protocol picked cases for the benchmark B1, the only rule that met the bar, and, beyond the plan, for every rule whose adjusted risk ratio excludes 1 (M3, M4, M10 and P2): four successes and four failures at random, the programs of the three most influential targets, and up to six programs that stopped after a randomised trial missed its primary endpoint (the plan asked for all such programs; the cap keeps every case checkable against primary sources). In all, 89 cases on 76 programs were checked. For each program one agent established the outcome from registry records, company filings, papers and FDA documents without seeing the evidence, another checked the evidence claim without seeing the outcome, a second coder classified each failure independently, and a third agent adjudicated any disagreement.

The pipeline's outcome was right for 74 of 76 programs. The two errors were an open-label safety extension registered as Phase 2/3 that counted as a Phase 3 start (amlitelimab) and another drug's Phase 3 trial linked to the program (zigakibart, credited with atrasentan's ALIGN trial). The evidence claim held for 60 of 89 cases and partly for 25 more (usually because the source matched a broader or neighbouring disease, or the earliest paper predated the row's date), and failed for 4. Of the 43 programs that did not advance, 20 failed for reasons that test the evidence's biology (F2–F5: engagement without benefit, the wrong population, a surrogate gap, on-target toxicity); the rest stopped because exposure or engagement was never shown (F1), on trial design (F7), off-target toxicity (F6) or commercial grounds (F8), which say nothing about whether the evidence was right, and a few are still progressing or unexplained.

| Rule | Cases | Advanced within 4 years (verified) | Evidence claim verified | Evidence published before entry | Why the others stopped (codes) |
| :---- | :---- | :---- | :---- | :---- | :---- |
| B1 Approved drug on the target, related disease | 20 | 10 | 19 (5 partly) | 20 | F2: 4, F3: 3, F1: 2, F4: 1 |
| M10 Reactome pathway | 15 | 8 | 14 (6 partly) | 13 | F8: 4, F3: 2, F2: 1 |
| M3 Mendelian evidence, non-hereditary disease | 15 | 7 | 14 (5 partly) | 15 | F8: 2, F2: 2, F7: 1, unknown: 1, F3: 1, F1: 1 |
| M4 GWAS, locus-to-gene ≥ 0.8 | 19 | 7 | 18 (2 partly) | 19 | F2: 5, F8: 3, still progressing: 2, F6: 1, F7: 1 |
| P2* Germline mechanism concordant with the drug | 20 | 9 | 20 (7 partly) | 20 | F2: 3, F1: 3, F8: 3, F7: 1, still progressing: 1 |

**When the model worked.** The clearest successes pair germline genetics that points in one direction with a drug that pushes the other way, in a disease defined close to that genetics.

* *Cardiac myosin inhibitors in hypertrophic cardiomyopathy* (M3, P2). Dominant missense mutations in *MYH7* that raise myosin activity were known to cause the disease from 1990. Mavacamten entered Phase 2 in 2016, started its pivotal Phase 3 (EXPLORER-HCM) in May 2018 and was approved in April 2022 for obstructive HCM ([label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2022/214998s000lbl.pdf)); aficamten followed the same path to approval.
* *APOL1 in kidney disease* (M3). The G1 and G2 variants of *APOL1*, toxic gain of function, were linked to FSGS and kidney failure in people of African ancestry in 2010. Inaxaplin, an APOL1 channel inhibitor, cut proteinuria by about half in a Phase 2a restricted to carriers of two risk variants and moved into an adaptive Phase 2/3 (AMPLITUDE) in 2022 ([NEJM 2023](https://pubmed.ncbi.nlm.nih.gov/36920755/)).
* *Amyloid in Alzheimer's disease* (M3, M10). Mendelian *APP* mutations underlie the amyloid hypothesis; donanemab, which clears plaque, advanced to Phase 3 and approval.
* *Clinical precedent* (B1). The benchmark's successes are next-in-class drugs on validated targets: third-generation EGFR inhibitors in lung cancer, HER2 antibodies and conjugates in biliary, gastric and breast cancer, and a PARP inhibitor moving from ovarian into prostate cancer.

**When it did not.** The verified failures show where the same kind of evidence stops predicting:

* *The target was hit and the disease did not move* (F2). Evazarsen, an antisense drug against angiotensinogen, whose common variants were linked to essential hypertension in 1992, lowered plasma angiotensinogen by 55–67% in every trial but did not lower blood pressure in its Phase 2b (NCT04714320). Galegenimab inhibited HtrA1, the gene at one of the two strongest GWAS loci for age-related macular degeneration, but geographic atrophy grew no slower, slightly faster, than on sham (NCT03972709).
* *Protective genetics, the right direction, and still no benefit* (F2). Loss-of-function *TYK2* variants protect against Crohn's disease, and the TYK2 inhibitor deucravacitinib, approved for psoriasis, missed both co-primary endpoints in Crohn's disease (LATTICE-CD, NCT03599622), with no dose response.
* *The molecule, not the target* (F1). NGM621, an anti-C3 antibody for geographic atrophy, a disease in which gain-of-function *C3* variants raise risk, missed its primary endpoint (NCT04465955), while another C3 inhibitor, pegcetacoplan, was approved for the same disease.
* *The evidence was an artefact.* The GWAS evidence linking *CXCR2* to palmoplantar pustulosis came from a pleiotropy meta-analysis that Open Targets mapped to psoriasis at the study level; the locus carries no psoriasis signal in the paper itself. Vimnerixin, the CXCR2 antagonist, was stopped for hepatic safety findings.
* *Commercial stops after positive trials* (F8). Several programs met their Phase 2 endpoints and stopped for portfolio reasons: brepocitinib in psoriasis and Crohn's disease, olamkicept in ulcerative colitis, dalcinonacog alfa in haemophilia B. They count as failures of the outcome, not of the evidence.

Every case, with its verdict and sources, is in the Appendix and in `report/audits/section3_cases.json`.


### What this means

* **Disease-specific human genetics is the evidence that carries over.** It is specific (it fades as the evidence moves away from the disease), it holds within a target, it does not come from hindsight, and it adds to clinical precedent. Its size, about twice the chance of reaching Phase 3 within four years, is in line with published estimates of what genetic support does for clinical success.
* **It is a filter, not a forecast.** Even with it, about two in three Phase 2 programs did not advance within four years, and most programs that did advance had no such evidence. No single rule built from preclinical evidence ranks programs reliably on targets it was not tuned on.
* **It predicts efficacy where efficacy is measured close to the biology.** The advantage is clearest on regulatory surrogates and clinician scales and is not demonstrable on patient-reported outcomes or exploratory biomarkers; trials with hard-outcome primaries were too few to judge.
* **Other preclinical evidence adds less at Phase 2.** Somatic drivers in oncology and Reactome pathways carry weaker signals than germline genetics, literature mouse models a marginal one and differential expression none; neither the mouse model's direction nor the somatic driver's direction sharpens them.
* **Direction cannot be learned from what sponsors ran.** Programs against an established genetic mechanism barely exist, so the data cannot show the cost of getting direction wrong, only that knowing the direction does not separate winners among the programs that were run.
* **Registries do not see target safety.** Genetic and mouse liabilities did not predict safety stops, which are rarely recorded as such.



## Historical case studies

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
| Open Targets Platform evidence | Every evidence row behind those associations for drug targets, with its date, direction of effect, confidence and source detail; mouse-model phenotypes | 26.09 |
| Mammalian Phenotype ontology | Mouse phenotype hierarchy (knockouts lethal before weaning) | Retrieved October 2026 |
| gnomAD | Loss-of-function constraint (LOEUF) | v4.1 |
| DepMap | Pan-essential genes from CRISPR (Chronos) screens | Release not recorded in the project database |

### Sources in detail

Each entry gives who compiles the source and from what, what the pipeline keeps, the shape of the raw response, and a real record from the cached download, trimmed to the fields used.

#### ClinicalTrials.gov API v2

*Snapshot 2026-10-20, 222,915 studies · `GET https://clinicaltrials.gov/api/v2/studies?filter.advanced=AREA[StudyType]INTERVENTIONAL AND AREA[InterventionType](DRUG OR BIOLOGICAL)&pageSize=1000` paged by `pageToken`*

**Compiled by.** The National Library of Medicine runs the registry. Sponsors enter the protocol record and the results themselves, as FDAAA 801 requires for applicable trials. NLM reviews entries for quality but does not check them against source records.
**We use.** From the protocol section we keep status, dates, the why-stopped text, phases, sponsor and its class, design, conditions, interventions, arms, references, countries, brief summary and primary outcomes. From the results section, posted for 53,446 studies, we keep every primary outcome's values per group and every statistical analysis, plus deaths and serious adverse events per arm.
**Shape.** `{totalCount, nextPageToken, studies: [{protocolSection: {statusModule, sponsorCollaboratorsModule, designModule, armsInterventionsModule, conditionsModule, outcomesModule, referencesModule, …}, resultsSection: {participantFlowModule, baselineCharacteristicsModule, outcomeMeasuresModule, adverseEventsModule}, hasResults}]}`

```json
{"nctId": "NCT03548935", "overallStatus": "COMPLETED", "phases": ["PHASE3"],
 "leadSponsor": {"name": "Novo Nordisk A/S", "class": "INDUSTRY"},
 "startDateStruct": {"date": "2018-06-04"}, "enrollmentInfo": {"count": 1961},
 "primaryOutcomes": [{"measure": "Change in Body Weight (%)", "timeFrame": "…week 68"}],
 "outcomeMeasures[0].analyses[0]": {"pValue": "<.0001", "statisticalMethod": "ANCOVA",
   "paramType": "Treatment difference", "paramValue": "-12.44", "ciLowerLimit": "-13.37", "ciUpperLimit": "-11.51"},
 "eventGroups[0]": {"title": "Sema 2.4 mg", "deathsNumAffected": 1, "deathsNumAtRisk": 1306, "seriousNumAffected": 128}}
```

#### PubMed E-utilities

*Queried at run time, with no snapshot recorded · `esearch.fcgi?db=pubmed&term=NCT…[si]`, then `efetch.fcgi?retmode=xml`*

**Compiled by.** NCBI indexes citations from publishers and MEDLINE. A trial registration number named in an article is recorded in its data-bank list and is searchable as a secondary identifier.
**We use.** We look up only completed industry Phase 2/3 trials, started from 2010, that posted no results. A paper links to a trial when the registry lists it as a RESULT or DERIVED reference, or when PubMed lists the NCT number. This links 2,284 trials. For each paper we keep title, first author, journal, year, DOI and abstract, and the abstracts feed the outcome classifier.
**Shape.** `<PubmedArticle><MedlineCitation><PMID/><Article><Journal/><ArticleTitle/><Abstract/><DataBankList><DataBank><AccessionNumber/></DataBank></DataBankList></Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi"/></ArticleIdList></PubmedData></PubmedArticle>`

```text
NCT03036488 (KEYNOTE-522; no posted results) -> PMID 32101663, linked by both routes
  N Engl J Med 2020, "Pembrolizumab for Early Triple-Negative Breast Cancer", Schmid P et al.
  DataBank ClinicalTrials.gov / AccessionNumber NCT03036488, doi 10.1056/NEJMoa1910549
```

#### Drugs@FDA data files

*Data to 2026-10-16 · `GET https://www.fda.gov/media/89850/download`, a zip of tab-separated tables*

**Compiled by.** FDA's drug center (CDER) publishes these files from its own application records. They cover drugs and therapeutic biologics, not the vaccines, blood products and cell or gene therapies that CBER regulates.
**We use.** NDA and BLA applications: sponsor, products and active ingredients, every original and supplement submission with its class, status, date and review priority, and the links to approval letters. That is 6,389 applications.
**Shape.** `Applications.txt` (ApplNo, ApplType, SponsorName), `Products.txt`, `Submissions.txt` (ApplNo, SubmissionClassCodeID, SubmissionType, SubmissionNo, SubmissionStatus, SubmissionStatusDate, ReviewPriority), `ApplicationDocs.txt` (type 1 = letter, URL, date).

```text
Applications     125514  BLA  MERCK SHARP DOHME
Products         125514  001  SOLUTION;INTRAVENOUS  100MG/4ML  KEYTRUDA  PEMBROLIZUMAB
Submissions      125514  class 2 (EFFICACY)  SUPPL 89  AP  2021-07-26  STANDARD
ApplicationDocs  125514  SUPPL 89  letter  …/appletter/2021/125514Orig1s089s114ltr_.pdf
```

#### FDA approval letters (CDER)

*Actions 2015 to 2026-10-16 · PDFs at `https://www.accessdata.fda.gov/drugsatfda_docs/appletter/<year>/<ApplNo>…ltr.pdf`, from the Drugs@FDA links*

**Compiled by.** The review division sends the letter to the sponsor when it acts, and FDA posts it. It names the approved submission and, for efficacy supplements, usually the new use it provides for.
**We use.** We fetch letters for every approved original application and every efficacy supplement. Text comes from the PDF's text layer, or from OCR when that layer is empty or garbled. An LLM records each approved use from the letter: disease, verbatim indication, qualifiers, type of change and accelerated approval.

```text
BLA 125514/S-089 + S-114 (Keytruda, 2021-07-26):
"(S-089) provides for a new indication for the treatment of patients with high-risk, early-stage
 triple negative breast cancer, in combination with chemotherapy as neoadjuvant treatment, then as
 a single agent as adjuvant treatment after surgery…"
-> use: triple-negative breast cancer · new population · not accelerated
-> use (S-114): metastatic TNBC, PD-L1 CPS ≥10 · conversion of the 2020 accelerated approval to full
```

#### openFDA drug labels

*Export 2026-10-16, 262,897 labels · `GET https://api.fda.gov/download.json` lists the bulk files, e.g. `https://download.open.fda.gov/drug/label/drug-label-0001-of-0014.json.zip`*

**Compiled by.** Manufacturers submit Structured Product Labeling to FDA. openFDA republishes it in bulk with harmonised identifiers and notes that the data are not validated.
**We use.** We keep the current label of each NDA or BLA product, 5,273 in all, with its application numbers, names, UNII and the full Indications and Usage text. The approval classifier reads that text as evidence of approved uses, including uses approved before 2015.
**Shape.** `{meta, results: [{set_id, id, version, effective_time, indications_and_usage: [str], …, openfda: {application_number[], brand_name[], generic_name[], substance_name[], unii[]}}]}`

```json
{"set_id": "9333c79b-d487-4538-a9f0-71b91a02b287", "effective_time": "20260710",
 "openfda": {"application_number": ["BLA125514"], "brand_name": ["KEYTRUDA"], "unii": ["DPT0O3T46P"]},
 "indications_and_usage": ["1 INDICATIONS AND USAGE KEYTRUDA is a programmed death receptor-1 (PD-1)-blocking
   antibody indicated: Melanoma for the treatment of patients with unresectable or metastatic melanoma. …"]}
```

#### CBER biologics approvals

*Actions 2015-01-09 to 2025-12-19, 324 records on 177 applications · yearly pages `https://www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/<year>-biological-license-application-approvals`, live from 2023 and from the Wayback Machine before; product pages; letter PDFs at `https://www.fda.gov/media/<id>/download`*

**Compiled by.** FDA's biologics center posts a yearly table of original licence approvals and noteworthy supplements, and a page per product linking its letters. None of these products are in Drugs@FDA.
**We use.** We keep original licences and supplements that add or change an indication, population, dose or formulation, with each letter's text. 53 letters came from Wayback captures. For the 10 records without a letter, the yearly-table entry stands in.

```json
{"appl_no": "125646", "submission_type": "ORIG", "approval_date": "2017-08-30",
 "product_brand": "KYMRIAH", "proper_name": "tisagenlecleucel", "product_class": "cell_therapy",
 "url": "https://www.fda.gov/media/106989/download", "pdf_source": "fda.gov",
 "yearly_listing_text": "KYMRIAH Tisagenlecleucel | For the treatment of patients up to 25 years of age with B-cell precursor ALL …"}
```

#### FDA Global Substance Registration System (UNII)

*2026-08-04, 171,912 substances and 1,047,975 names · `https://precision.fda.gov/uniisearch/archive/2026-08-04/UNII_Data_20260804.zip`, plus the matching names file*

**Compiled by.** FDA assigns each Unique Ingredient Identifier from a substance's structure or defining information. It collects the substance's names from INN, USAN, JAN, brands and sponsor codes, each tagged with its type.
**We use.** Substances, with their INN, RxNorm and PubChem cross-references, and every name in normalised form. These resolve trial intervention names to one molecular entity and merge entities that are the same substance.
**Shape.** Records: 25 tab-separated columns, including UNII, DISPLAY_NAME, RXCUI, PUBCHEM, INN_ID, INCHIKEY and SUBSTANCE_TYPE. Names: NAME, TYPE (brand, code, common, official or systematic), UNII.

```text
53AXN4NNHX  SEMAGLUTIDE  RXCUI 1991302  PUBCHEM 56843331  INN_ID 9113  SUBSTANCE_TYPE protein
  names: NN9535 (code) · NNC-0113-0217 (code) · OZEMPIC (brand) · WEGOVY (brand) · SEMAGLUTIDE [JAN] (common)
```

#### MONDO disease ontology

*2026-10-06 · `https://github.com/monarch-initiative/mondo/releases/latest/download/mondo.obo`*

**Compiled by.** The Monarch Initiative merges disease terms from OMIM, Orphanet, DOID, NCIT, EFO and others into one hierarchy. Each cross-reference is tagged as an exact equivalence or a looser relation.
**We use.** We keep terms, exact synonyms, obsolete flags, the is-a hierarchy with its full ancestor closure, and the cross-references with their equivalence flag. MONDO is the target vocabulary for trial conditions and for Open Targets diseases. Its hierarchy defines disease similarity: subtypes, and Lin ≥ 0.8.

```text
id: MONDO:0005439
name: familial hypercholesterolemia
synonym: "hyperlipoproteinemia type II" EXACT []
xref: EFO:0004911 {source="MONDO:equivalentTo"}      -> equivalent
xref: ICD9:V19.8 {source="MONDO:relatedTo"}          -> not equivalent
is_a: MONDO:0001336 ! familial hyperlipidemia
```

#### EFO

*Reaches the analysis only as Open Targets disease identifiers*

**Compiled by.** EMBL-EBI maintains EFO for Open Targets, the GWAS Catalog and Expression Atlas. It imports disease classes from MONDO and other ontologies and adds terms of its own.
**We use.** No EFO file. Open Targets keys 9,257 of its diseases by EFO identifiers. Each is mapped to MONDO through the disease's own MONDO cross-reference, then MONDO's declared equivalence to the EFO term. Failing both, it maps through a DOID, Orphanet, NCIT or MeSH cross-reference that points to a single MONDO term.

```text
EFO_0000768 idiopathic pulmonary fibrosis: no MONDO xref, and no MONDO term lists EFO:0000768
  -> DOID:0050156 and Orphanet:2032 are both equivalent to MONDO:0800504
```

#### Mammalian Phenotype ontology

*2026-09-23 · `http://purl.obolibrary.org/obo/mp.obo`*

**Compiled by.** Mouse Genome Informatics at the Jackson Laboratory maintains it. MGI and IMPC curators use it to annotate phenotypes of mutant mice.
**We use.** The hierarchy only. A target counts as "knockout lethal before weaning" when any of its Open Targets mouse phenotypes is MP:0010770 *preweaning lethality* or a descendant. That flags 688 genes.

```text
id: MP:0011100
name: preweaning lethality, complete penetrance
is_a: MP:0010770 ! preweaning lethality
```

#### Gene symbols and identifiers

*Loaded by earlier project code; release not recorded*

**Compiled by.** The symbols follow HGNC, which approves one symbol per human gene, but the table is the project's own catalogue. It adds Ensembl identifiers, Pharos development level and family, and RefSeq summaries. Some symbols predate HGNC renames.
**We use.** The 26,957 human protein symbols are the closed list that every LLM-assigned drug target must match. Ensembl identifiers join targets to Open Targets, gnomAD and DepMap.

```text
PCSK9  proprotein convertase subtilisin/kexin type 9  Protein  ENSG00000169174  Tclin  Enzyme  secreted
```

#### ChEMBL mechanisms of action

*Loaded by the project's first ingest; ChEMBL release not recorded*

**Compiled by.** EMBL-EBI curators assign each approved or clinical-stage drug its molecular targets and action type, with references from labels and the literature.
**We use.** Only as hints. When the LLM assigns an entity's targets, it sees up to 12 "SYMBOL: action" pairs from ChEMBL; its own answer is what we store. The bulk file kept one symbol per drug name, so multi-target drugs are incomplete there; tirzepatide shows only GIPR.

```text
pembrolizumab (CHEMBL3137343)  PDCD1  inhibitor
semaglutide   (CHEMBL2108724)  GLP1R  agonist   PMID 22918257
```

#### gnomAD constraint

*v4.1 · loaded by earlier project code*

**Compiled by.** The Broad Institute's gnomAD compares each gene's observed loss-of-function variants, in exomes and genomes from about 800,000 people, with the number a mutation model expects. LOEUF is the upper bound of the 90% interval of observed over expected, and a low value means the gene does not tolerate loss of function.
**We use.** A target is LoF-intolerant when its LOEUF is below 0.35. That flags 1,385 of 18,164 genes. The value is today's, not the value at phase entry.

```text
PCSK9   pLI 1.1e-20  LOEUF 1.25    missense z 0.59
POLR2A  pLI 1.0      LOEUF 0.161   missense z 9.21
```

#### DepMap gene essentiality

*Loaded by earlier project code; DepMap release and the pan-essential rule not recorded*

**Compiled by.** The Broad Institute's Cancer Dependency Map knocks out every gene by CRISPR in about a thousand cancer cell lines. Chronos estimates each gene's effect on growth: 0 is none, and −1 is the median effect of common-essential genes.
**We use.** The pan-essential flag alone, set for 1,284 of 17,916 genes across 1,178 screened lines, as of today. The flag's cutoff is not documented. Some core genes, such as POLR2A, are missing from the table and read as not essential.

```text
POLR2B  mean effect -2.42  1,178 lines  pan-essential  dependent in 30 lineages
PCSK9   mean effect -0.19  1,178 lines  not essential  dependent in 0 lineages
```

#### Open Targets Platform: associations

*26.09 · `https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.09/output/association_by_datasource_direct/*.parquet` and `…/disease/`*

**Compiled by.** EMBL-EBI, the Wellcome Sanger Institute and partners run Open Targets. It maps evidence from about 20 resources to Ensembl genes and to disease terms (MONDO, EFO, HP, Orphanet) and scores each item from 0 to 1. Per target, disease and datasource, it combines the items into one association score with a weighted harmonic sum. A "direct" association counts only evidence annotated to that exact disease, not to its subtypes. Each association carries a yearly series of its cumulative score.
**We use.** Direct associations from the 17 datasources below, for targets of drugs in industry programs. We keep the score, the evidence count and the yearly series, so evidence is taken as of the year before phase entry. The yearly series leaves out undated evidence.
**Shape.** `targetId, diseaseId, aggregationValue (datasource), associationScore, evidenceCount, timeseries[{year, associationScore, yearlyEvidenceCount}]`; diseases: `id, name, dbXRefs[], therapeuticAreas[]`.

```json
{"targetId": "ENSG00000169174", "diseaseId": "MONDO_0005439", "aggregationValue": "eva",
 "associationScore": 0.875, "evidenceCount": 829,
 "timeseries": [{"year": 2018, "associationScore": 0.0}, {"year": 2019, "associationScore": 0.704},
                {"year": 2021, "associationScore": 0.800}, {"year": 2026, "associationScore": 0.875},
                {"year": null, "associationScore": 0.875}]}
```

PCSK9 · familial hypercholesterolemia, ClinVar evidence.

#### Open Targets Platform: evidence

*26.09 · `…/output/evidence_<datasource>/*.parquet` and `…/mouse_phenotype/`*

**Compiled by.** One row per supporting item: a variant, study, curated assertion, mouse model, expression contrast or reaction. Each row has a 0–1 score and the upstream statistic. Where the source allows, it also has a date, a confidence grade, and the direction of effect on the target (loss or gain of function) and on the trait (risk or protection).
**We use.** Every row for program targets. Section 3 groups them into families and strength tiers, such as locus-to-gene ≥ 0.8, burden p < 2.5e-6, ClinGen definitive or strong, and PanelApp green. Mouse phenotypes give the knockout-lethality flag.
**Shape.** `id, targetId, diseaseId, datasourceId, score, resourceScore, confidence, publicationDate, directionOnTarget, directionOnTrait, variantFunctionalConsequenceId, literature[]`, plus source-specific fields such as `studyLocusId`, `beta`, `pValueMantissa`/`pValueExponent`, `clinicalSignificances`, `biologicalModelAllelicComposition`, `log2FoldChangeValue`.

```json
{"datasourceId": "gene_burden", "targetId": "ENSG00000169174", "diseaseId": "EFO_0022275",
 "projectId": "AstraZeneca PheWAS Portal", "cohortId": "UK Biobank 470k", "statisticalMethod": "flexdmg",
 "studyCasesWithQualifyingVariants": 584, "beta": -0.527, "pValueMantissa": 2.107, "pValueExponent": -40,
 "score": 1.0, "directionOnTarget": "LoF", "directionOnTrait": "protect", "publicationDate": "2021-08-10"}
```

PCSK9 loss of function lowers free cholesterol in very small VLDL.

| Datasource | Upstream and how Open Targets builds it | A row asserts | Example (target · disease · value) |
| :---- | :---- | :---- | :---- |
| GWAS credible sets | GWAS Catalog and summary statistics, fine-mapped; genes assigned by the locus-to-gene model | A fine-mapped locus implicates the gene; score = locus-to-gene | PCSK9 · LDL cholesterol · 0.987 |
| Gene burden | Rare-variant burden tests in exome cohorts (AstraZeneca PheWAS, Genebass, Regeneron, FinnGen and others) | Qualifying variants associate with the trait; effect, p, direction | PCSK9 · VLDL free cholesterol · β −0.53, p 2e-40, LoF protective |
| ClinVar (EVA) | ClinVar germline submissions via EMBL-EBI | A variant is classified for the disease; review status as confidence | PCSK9 · hypercholesterolemia AD3 · pathogenic, multiple submitters |
| Genomics England PanelApp | Diagnostic gene panels | Gene is on the disease's panel; green (diagnostic grade) or amber | PCSK9 · familial hypercholesterolaemia panel · green |
| Orphanet | Expert-curated gene–rare disease links | Gene causes or is associated with the disease | PCSK9 · homozygous FH · assessed |
| Gene2Phenotype | EMBL-EBI curated panels | Gene–disease link with allelic requirement; definitive to limited | LDLR · hypercholesterolemia · definitive, monoallelic |
| ClinGen | Gene–disease validity expert panels | Validity classification, definitive to refuted | PCSK9 · hypercholesterolemia AD3 · definitive (2018) |
| UniProt literature | UniProtKB disease annotations, from OMIM and the literature | Gene is involved in the disease | PCSK9 · hypercholesterolemia AD3 · high, 5 papers |
| UniProt variants | UniProtKB curated disease variants | A specific variant causes the disease | LDLR · FH type 1 · rs879254753 |
| Cancer Gene Census | COSMIC census drivers with per-tumour mutation counts | Gene drives the tumour type; oncogene (GoF) or suppressor (LoF) | EGFR · ovarian adenocarcinoma · GoF, 24/54 samples |
| IntOGen | Driver discovery over tumour cohorts (TCGA, PCAWG) | Gene is a significant driver in the cohort | EGFR · lung adenocarcinoma · p 2e-48, 7 methods |
| ClinVar somatic | ClinVar somatic submissions | A somatic variant is classified for the disease | LDLR · FH type 1 · pathogenic, expert panel |
| IMPC | IMPC and MGI mouse models, matched to diseases by PhenoDigm phenotype similarity | The mutant's phenotypes resemble the disease's | PCSK9 · hyperlipoproteinemia V · knockout, PhenoDigm 95 |
| Expression Atlas | Disease-versus-normal differential expression experiments | Gene is differentially expressed in the disease | PCSK9 · psoriasis · log2FC +2.5 |
| Reactome | Curated disease reactions | A variant perturbs a reaction in a disease pathway | CFTR · cystic fibrosis · F508del binds ERAD machinery |
| CRISPR | Project Score knockout fitness screens in cancer lines | Gene is a fitness dependency in that cancer type | KRAS · plasma cell myeloma · priority 78 |
| CRISPR screens | CRISPRbrain screens in iPSC-derived neurons | Perturbing the gene shifts a screen phenotype | LDLR · neurodegeneration · log2FC −5.8 |
| Mouse phenotypes | IMPC and MGI phenotype annotations (MP terms), not linked to a disease | A mutant allele shows the phenotype | PCSK9 · decreased circulating LDL cholesterol |

We leave out three datasources. Clinical precedence and cancer biomarkers come from drugs' clinical records, so they would leak the outcome. Europe PMC counts literature co-mentions of gene and disease, which is attention, not evidence. For PCSK9 and familial hypercholesterolemia, clinical precedence alone scores 0.97.


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

### Section 3 case studies

Every case picked by the rule protocol, checked by agents against primary sources: one agent established each program's outcome without seeing its evidence, another checked the evidence claim without seeing the outcome, a second agent coded each failure independently, and a third adjudicated any disagreement with the pipeline or between agents.

| Rule | Drug (target, action) | Disease | Phase 2 entry | Evidence claim: verdict; earliest source | Outcome (verified) | Failure |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| B1 | zanidatamab (ERBB2 (inhibitor)) | biliary tract cancer | 2020-10-01 | partial; FDA supplemental BLA approval letter, Herceptin (trastuzumab) BLA 103792/5250, October 20, 2010, approving trastuzumab for HER2-overexpressi (2010) | advanced | – |
| B1 | aumolertinib (EGFR (inhibitor)) | non-small cell lung carcinoma | 2017-05-08 | yes; FDA accelerated approval of IRESSA (gefitinib), NDA 21-399, AstraZeneca, 5 May 2003, for locally advanced or metastatic NSCLC after failure  (2003) | advanced | – |
| B1 | niraparib (PARP1 (inhibitor), PARP2 (inhibitor)) | ovarian cancer | 2015-03-23 | yes; FDA accelerated approval of Lynparza (olaparib, AstraZeneca), NDA 206162, approval letter dated 12/19/2014: monotherapy for deleterious or s (2014) | advanced | – |
| B1 | niraparib (PARP1 (inhibitor), PARP2 (inhibitor)) | prostate cancer | 2016-08-31 | partial; FDA accelerated approval of Lynparza (olaparib) capsules, NDA 206162, AstraZeneca, signed 12/19/2014. Indication: monotherapy for deleteriou (2014) | advanced | – |
| B1 | trastuzumab deruxtecan (ERBB2 (binder_neutralizer)) | gastric cancer | 2019-11-26 | yes; FDA supplemental BLA approval letter STN 103792/5250, Herceptin (trastuzumab, Genentech), dated October 20, 2010. It approved Herceptin for  (2010) | advanced | – |
| B1 | ramucirumab (KDR (binder_neutralizer)) | synovial sarcoma | 2020-03-04 | yes; FDA approval letter NDA 022465/S-010 (Votrient/pazopanib, GlaxoSmithKline), dated 04/26/2012, approving pazopanib "for the treatment of pati (2012) | did not advance | F2 biology did not translate |
| B1 | disitamab vedotin (ERBB2 (binder_neutralizer)) | breast cancer | 2016-12-23 | yes; The FDA approved Genentech's Trastuzumab (Herceptin, BLA 103792) on September 25, 1998 (approval letter ref. 98-0369), for metastatic breast (1998) | advanced | – |
| B1 | rezivertinib (EGFR (inhibitor)) | non-small cell lung carcinoma | 2017-08-16 | yes; FDA accelerated approval letter, NDA 21-399, IRESSA (gefitinib, an EGFR tyrosine kinase inhibitor), to AstraZeneca, signed 5/5/03. It covers (2003) | advanced | – |
| B1 | fazirsiran (SERPINA1 (gene_expression_reduction)) | alpha 1-antitrypsin deficiency | 2019-08-07 | partial; FDA Purple Book: BLA 103174, Prolastin (Alpha-1-Proteinase Inhibitor (Human)), current holder Grifols Therapeutics, original approval Decemb (1987) | advanced | – |
| B1 | kdt-501, (+)- (PPARG (partial_agonist)) | type 2 diabetes mellitus | 2015-04-01 | yes; FDA approval of troglitazone (Rezulin, NDA 020720, Parke-Davis/Warner-Lambert, now listed under Pfizer; companion NDA 020719 Prelay, Sankyo) (1997) | did not advance | F1 exposure |
| B1 | rezvilutamide (AR (antagonist)) | prostate cancer | 2016-04-12 | yes; FDA approval of Eulexin (flutamide), NDA 018554 (Schering), approved 1989-01-27. Its label indication is use with LHRH agonists for metastat (1989) | advanced | – |
| B1 | rozibafusp alfa (ICOSLG (binder_neutralizer), TNFSF13B (binder_neutralizer)) | systemic lupus erythematosus | 2020-02-19 | yes; FDA approval letter, BLA 125370 (Benlysta/belimumab), March 9, 2011. It approves belimumab for adult patients with active, autoantibody-posi (2011) | did not advance | F2 biology did not translate |
| B1 | sacubitril (MME (inhibitor)) | hypertrophic cardiomyopathy | 2020-01-08 | partial; FDA approval letter for NDA 207620 (ENTRESTO, sacubitril/valsartan, Novartis), dated 2015-07-07. It approves the drug to reduce the risk of  (2015) | did not advance | F4 surrogate gap |
| B1 | V565 (TNF (binder_neutralizer)) | Crohn disease | 2016-12-01 | yes; FDA (CBER) approval letter for Remicade (infliximab, Centocor), BLA 103772, dated August 24, 1998, approving it for moderately to severely a (1998) | did not advance | F2 biology did not translate |
| B1 | trc-253 (AR (antagonist)) | prostate adenocarcinoma | 2017-05-23 | yes; FDA approval of Eulexin (flutamide) capsules, NDA 018554 (Schering), original approval 1989-01-27; flutamide is a nonsteroidal antiandrogen  (1989) | did not advance | F3 wrong population |
| B1 | onfasprodil (GRIN2B (negative_modulator)) | major depressive disorder | 2019-02-08 | no; FDA approval of NDA 21-487 (Namenda, memantine HCl, Forest Laboratories), approved 2003-10-16 for moderate to severe dementia of the Alzheim (2003) | did not advance | F3 wrong population |
| B1 | plocabulin (TUBB4B (inhibitor)) | colorectal cancer | 2018-01-16 | partial; FDA approval letter NDA 20-449/S-035 for Taxotere (docetaxel), Sanofi-Aventis, signed 3/22/2006. It approves docetaxel with cisplatin and fl (2006) | did not advance | F2 biology did not translate |
| B1 | metopimazine (DRD2 (antagonist)) | gastroparesis | 2020-08-01 | yes; FDA approval of metoclopramide (Reglan), a dopamine D2 receptor antagonist, with an indication for relief of symptoms of acute and recurrent (1979) | did not advance | F3 wrong population |
| B1 | OPC-64005 (SLC6A4 (inhibitor), SLC6A2 (inhibitor), SLC6A3 (inhibitor)) | major depressive disorder | 2020-03-03 | yes; Tofranil (imipramine, NDA 011838), FDA original approval on 1959-10-02 per Drugs@FDA. Imipramine labeling: "for the relief of symptoms of de (1959) | did not advance | F1 exposure |
| B1 | NCX 470 (PTGFR (agonist)) | open-angle glaucoma | 2018-08-01 | yes; FDA approval of XALATAN (latanoprost ophthalmic solution 0.005%), NDA 020597 (Upjohn), original approval 06/05/1996, indicated to reduce ele (1996) | advanced | – |
| M10 | dorzagliatin (GCK (activator)) | type 2 diabetes mellitus | 2015-09-01 | partial; Froguel P et al. 'Close linkage of glucokinase locus on chromosome 7p to early-onset non-insulin-dependent diabetes mellitus', Nature 356:16 (1992) | advanced | – |
| M10 | DFV890 (NLRP3 (inhibitor)) | COVID-19 | 2020-05-27 | partial; Siu KL, Yuen KS, Castano-Rodriguez C, ... Jin DY. "Severe acute respiratory syndrome coronavirus ORF3a protein activates the NLRP3 inflammas (2019) | did not advance | F3 wrong population |
| M10 | denecimig (F9 (other), F10 (other)) | hemophilia A | 2020-01-10 | partial; Usharani P, Warn-Cramer BJ, Kasper CK, Bajaj SP. Characterization of three abnormal factor IX variants (Bm Lake Elsinore, Long Beach, and Lo (1985) | advanced | – |
| M10 | sar-125844 (MET (inhibitor)) | cancer | 2015-11-01 | partial; Reactome reaction R-HSA-2400009 'PI3K inhibitors block PI3K catalytic activity' (disease: cancer, DOID:162; created 2012-07-13, released 201 (2016) | did not advance | F8 commercial |
| M10 | sepiapterin (PAH (positive_modulator)) | phenylketonuria | 2019-01-03 | yes; Guldberg P, Mallmann R, Henriksen KF, Guttler F. "Phenylalanine hydroxylase deficiency in a population in Germany: mutational profile and ni (1996) | advanced | – |
| M10 | pabinafusp alfa (IDS (replacement)) | mucopolysaccharidosis type 2 | 2017-03-30 | yes; Crotty PL, Braun SE, Anderson RA, Whitley CB. "Mutation R468W of the iduronate-2-sulfatase gene in mild Hunter syndrome (mucopolysaccharidos (1992) | advanced | – |
| M10 | derazantinib (FGFR2 (inhibitor), FGFR1 (inhibitor), FGFR3 (inhibitor)) | gastric adenocarcinoma | 2020-10-06 | yes; Itoh H, Hattori Y, ... Terada M. "Preferential alternative splicing in cancer generates a K-sam messenger RNA with higher transforming activ (1994) | did not advance | F8 commercial |
| M10 | tividenofusp alfa (IDS (replacement)) | mucopolysaccharidosis type 2 | 2020-07-16 | yes; Crotty PL, Braun SE, Anderson RA, Whitley CB. "Mutation R468W of the iduronate-2-sulfatase gene in mild Hunter syndrome (mucopolysaccharidos (1992) | advanced | – |
| M10 | donanemab (APP (depleter)) | Alzheimer disease | 2017-12-18 | yes; Lee MS, Kwon YT, Li M, Peng J, Friedlander RM, Tsai LH. "Neurotoxicity induces cleavage of p35 to p25 by calpain." Nature 2000;405:360-4 (PM (2000) | advanced | – |
| M10 | efzofitimod (NRP1 (agonist)) | COVID-19 | 2020-06-04 | no; Daly JL et al., 'Neuropilin-1 is a host factor for SARS-CoV-2 infection', bioRxiv 10.1101/2020.06.05.134114, posted 2020-06-05 (published in (2020) | did not advance | F8 commercial |
| M10 | acoramidis (TTR (other)) | cardiomyopathy | 2018-08-08 | partial; Costa PP, Figueira AS, Bravo FR. "Amyloid fibril protein related to prealbumin in familial amyloidotic polyneuropathy." Proc Natl Acad Sci U (1978) | advanced | – |
| M10 | afuresertib (AKT1 (inhibitor), AKT2 (inhibitor), AKT3 (inhibitor)) | ovarian cancer | 2020-07-07 | yes; Carpten JD et al., "A transforming mutation in the pleckstrin homology domain of AKT1 in cancer", Nature 2007;448:439-44 (PMID 17611497; epu (2007) | did not advance | F3 wrong population |
| M10 | valiltramiprosate (APP (other)) | Alzheimer disease | 2020-09-30 | yes; Lee MS, Kwon YT, Li M, Peng J, Friedlander RM, Tsai LH. "Neurotoxicity induces cleavage of p35 to p25 by calpain." Nature 2000;405:360-4 (PM (2000) | advanced | – |
| M10 | dalcinonacog alfa (F9 (replacement)) | hemophilia B | 2019-06-18 | yes; Usharani P, Warn-Cramer BJ, Kasper CK, Bajaj SP. Characterization of three abnormal factor IX variants (Bm Lake Elsinore, Long Beach, and Lo (1985) | did not advance | F8 commercial |
| M10 | dilpacimab (DLL4 (binder_neutralizer), VEGFA (binder_neutralizer)) | cancer | 2018-03-20 | partial; Weng AP et al., 'Activating mutations of NOTCH1 in human T cell acute lymphoblastic leukemia', Science 2004;306:269-71 (PMID 15472075). It i (2004) | did not advance | F2 biology did not translate |
| M3 | molgramostim (CSF2RA (agonist), CSF2RB (agonist)) | pulmonary alveolar proteinosis | 2016-03-21 | yes; Suzuki T et al., 'Familial pulmonary alveolar proteinosis caused by mutations in CSF2RA', J Exp Med 2008;205:2703-10 (PMID 18955570, epub 27 (2008) | advanced | – |
| M3 | mavacamten (MYH7 (inhibitor)) | hypertrophic cardiomyopathy | 2016-08-01 | yes; Geisterfer-Lowrance AA, Kass S, Tanigawa G, Vosberg HP, McKenna W, Seidman CE, Seidman JG. "A molecular basis for familial hypertrophic card (1990) | advanced | – |
| M3 | radiprodil (GRIN2B (negative_modulator)) | infantile spasms | 2017-12-04 | yes; Lemke JR et al., "GRIN2B mutations in West syndrome and intellectual disability with focal epilepsy", Ann Neurol 2014;75(1):147-54 (PMID 242 (2014) | did not advance | F7 trial design |
| M3 | apadamtase alfa (ADAMTS13 (replacement)) | acquired thrombotic thrombocytopenic purpura | 2019-10-09 | yes; Levy GG et al. 'Mutations in a member of the ADAMTS gene family cause thrombotic thrombocytopenic purpura.' Nature 2001 Oct 4;413:488-94 (PM (2001) | did not advance | F8 commercial |
| M3 | somapacitan (GHR (agonist)) | pituitary dwarfism | 2016-03-31 | partial; Amselem S et al., 'Spectrum of growth hormone receptor mutations and associated haplotypes in Laron syndrome', Hum Mol Genet 1993;2(4):355-9 (1993) | advanced | – |
| M3 | aficamten (MYH7 (inhibitor)) | hypertrophic cardiomyopathy | 2020-01-10 | yes; Geisterfer-Lowrance AA, Kass S, Tanigawa G, Vosberg HP, McKenna W, Seidman CE, Seidman JG. "A molecular basis for familial hypertrophic card (1990) | advanced | – |
| M3 | evazarsen (AGT (gene_expression_reduction)) | hypertensive disorder | 2019-01-03 | partial; Jeunemaitre X, Soubrier F, ... Lifton RP, ... Lalouel JM. "Molecular basis of human hypertension: role of angiotensinogen." Cell 1992 Oct 2; (1992) | did not advance | F2 biology did not translate |
| M3 | donanemab (APP (depleter)) | Alzheimer disease | 2017-12-18 | yes; Goate A et al., 'Segregation of a missense mutation in the amyloid precursor protein gene with familial Alzheimer's disease', Nature 1991 Fe (1991) | advanced | – |
| M3 | PE0139 (INSR (agonist)) | type 2 diabetes mellitus | 2015-10-01 | partial; O'Rahilly S et al., "Detection of mutations in insulin-receptor gene in NIDDM patients by analysis of single-stranded conformation polymorph (1991) | did not advance | unknown |
| M3 | insulin 338 (INSR (agonist)) | type 2 diabetes mellitus | 2015-06-01 | partial; Cocozza S et al., "NIDDM associated with mutation in tyrosine kinase domain of insulin receptor gene", Diabetes 1992 Apr;41(4):521-6 (PMID 1 (1992) | did not advance | F8 commercial |
| M3 | valiltramiprosate (APP (other)) | Alzheimer disease | 2020-09-30 | yes; Goate A et al., 'Segregation of a missense mutation in the amyloid precursor protein gene with familial Alzheimer's disease', Nature 1991 Fe (1991) | advanced | – |
| M3 | inaxaplin (APOL1 (inhibitor)) | kidney disorder | 2020-06-08 | yes; Genovese G, Friedman DJ, ... Pollak MR. "Association of trypanolytic ApoL1 variants with kidney disease in African Americans." Science 2010; (2010) | advanced | – |
| M3 | TOL-3021 (INS (other)) | type 1 diabetes mellitus | 2019-06-17 | partial; Stoy J et al., "Insulin gene mutations as a cause of permanent neonatal diabetes", PNAS 2007;104(38):15040-4 (PMID 17855560). It is the earl (2007) | did not advance | F2 biology did not translate |
| M3 | asp-8302 (CHRM3 (positive_modulator)) | urinary bladder disorder | 2018-11-20 | yes; Weber S et al., "Muscarinic Acetylcholine Receptor M3 Mutation Causes Urinary Bladder Disease and a Prune-Belly-like Syndrome", Am J Hum Gen (2011) | did not advance | F3 wrong population |
| M3 | RO7123520 (CDH11 (binder_neutralizer), TNF (binder_neutralizer)) | rheumatoid arthritis | 2016-12-22 | no; Balding J et al., "Cytokine gene polymorphisms: association with psoriatic arthritis susceptibility and severity", Arthritis Rheum 2003;48(5 (2003) | did not advance | F1 exposure |
| M4 | vimnerixin (CXCR2 (antagonist)) | palmoplantar pustulosis | 2019-02-13 | no; Ellinghaus D et al., "Analysis of five chronic inflammatory diseases identifies 27 new associations and highlights disease-specific patterns (2016) | did not advance | F6 off-target toxicity |
| M4 | deucravacitinib (TYK2 (negative_modulator)) | psoriatic arthritis | 2019-04-01 | yes; Strange A et al. (Genetic Analysis of Psoriasis Consortium and WTCCC2), "A genome-wide association study identifies new psoriasis susceptibi (2010) | advanced | – |
| M4 | palazestrant (ESR1 (antagonist)) | breast cancer | 2020-08-13 | yes; Zhou W, ..., Willer CJ, Lee S. "Efficiently controlling for case-control imbalance and sample relatedness in large-scale genetic association (2018) | advanced | – |
| M4 | stapokibart (IL4R (binder_neutralizer)) | atopic eczema | 2020-07-21 | yes; Kichaev G, Bhatia G, Loh PR, ... Pasaniuc B, Price AL. "Leveraging Polygenic Functional Enrichment to Improve GWAS Power." Am J Hum Genet 20 (2018) | advanced | – |
| M4 | amlitelimab (TNFSF4 (binder_neutralizer)) | atopic eczema | 2018-12-13 | partial; Ferreira MA et al., 'Shared genetic origin of asthma, hay fever and eczema elucidates allergic disease biology', Nat Genet 2017;49:1752-1757 (2017) | did not advance (pipeline wrong) | – |
| M4 | brepocitinib (TYK2 (inhibitor), JAK1 (inhibitor)) | Crohn disease | 2018-02-02 | yes; Franke A et al., 'Genome-wide meta-analysis increases to 71 the number of confirmed Crohn's disease susceptibility loci', Nat Genet 2010;42( (2010) | did not advance | F8 commercial |
| M4 | brepocitinib (TYK2 (inhibitor), JAK1 (inhibitor)) | psoriasis | 2016-12-01 | yes; Strange A et al. (Genetic Analysis of Psoriasis Consortium & WTCCC2), "A genome-wide association study identifies new psoriasis susceptibili (2010) | did not advance | F8 commercial |
| M4 | brepocitinib (TYK2 (inhibitor), JAK1 (inhibitor)) | systemic lupus erythematosus | 2019-04-18 | yes; Bentham J et al., "Genetic association analyses implicate aberrant regulation of innate and adaptive immunity genes in the pathogenesis of s (2015) | did not advance | F7 trial design |
| M4 | sibeprenlimab (TNFSF13 (binder_neutralizer)) | IgA glomerulonephritis | 2020-07-20 | yes; Yu XQ et al., "A genome-wide association study in Han Chinese identifies multiple susceptibility loci for IgA nephropathy", Nat Genet 2011 D (2011) | advanced | – |
| M4 | camizestrant (ESR1 (degrader)) | breast cancer | 2020-04-22 | yes; Zhou W et al., "Efficiently controlling for case-control imbalance and sample relatedness in large-scale genetic association studies" (SAIGE (2018) | advanced | – |
| M4 | galegenimab (HTRA1 (inhibitor)) | age-related macular degeneration | 2019-06-03 | yes; Ruamviboonsuk P et al., "Genome-wide association study of neovascular age-related macular degeneration in the Thai population", J Hum Genet  (2017) | did not advance | F2 biology did not translate |
| M4 | astegolimab (IL1RL1 (binder_neutralizer)) | atopic eczema | 2019-02-06 | yes; Kichaev G et al., 'Leveraging Polygenic Functional Enrichment to Improve GWAS Power', Am J Hum Genet 2019;104(1):65-75, epub 2018-12-27 (PMI (2018) | did not advance | F2 biology did not translate |
| M4 | zigakibart (TNFSF13 (binder_neutralizer)) | IgA glomerulonephritis | 2019-04-08 | yes; Yu XQ, Li M, Zhang H, ... Liu JJ. "A genome-wide association study in Han Chinese identifies multiple susceptibility loci for IgA nephropath (2011) | did not advance (pipeline wrong) | – |
| M4 | futibatinib (FGFR1 (inhibitor), FGFR2 (inhibitor), FGFR3 (inhibitor), FGFR4 (inhibitor)) | breast cancer | 2020-01-28 | yes; Easton DF et al., "Genome-wide association study identifies novel breast cancer susceptibility loci", Nature 2007;447:1087-93 (PMID 17529967 (2007) | did not advance | F2 biology did not translate |
| M4 | olamkicept (IL6R (binder_neutralizer), IL6 (binder_neutralizer)) | ulcerative colitis | 2018-02-06 | partial; Ellinghaus D et al., "Analysis of five chronic inflammatory diseases identifies 27 new associations and highlights disease-specific patterns (2016) | did not advance | F8 commercial |
| M4 | vepdegestrant (ESR1 (degrader)) | breast cancer | 2019-09-22 | yes; Zhou W et al., 'Efficiently controlling for case-control imbalance and sample relatedness in large-scale genetic association studies' (SAIGE (2018) | advanced | – |
| M4 | recaticimab (PCSK9 (binder_neutralizer)) | hyperlipidemia | 2019-06-20 | yes; Zhou W et al., "Efficiently controlling for case-control imbalance and sample relatedness in large-scale genetic association studies" (SAIGE (2018) | advanced | – |
| M4 | ichorcumab (F2 (inhibitor)) | venous thromboembolism | 2017-11-13 | yes; Germain M et al., "Meta-analysis of 65,734 individuals identifies TSPAN15 and SLC44A2 as two susceptibility loci for venous thromboembolism" (2015) | did not advance | F2 biology did not translate |
| M4 | cinpanemab (SNCA (binder_neutralizer)) | Parkinson disease | 2018-01-10 | yes; Hamza TH et al., "Common genetic variation in the HLA region is associated with late-onset sporadic Parkinson's disease", Nat Genet 2010 (ep (2010) | did not advance | F2 biology did not translate |
| P2* | aumolertinib (EGFR (inhibitor)) | non-small cell lung carcinoma | 2017-05-08 | yes; Bell DW et al., "Inherited susceptibility to lung cancer may be associated with the T790M drug resistance mutation in EGFR", Nat Genet 2005; (2005) | advanced | – |
| P2* | pyrotinib (ERBB2 (inhibitor), EGFR (inhibitor)) | non-small cell lung carcinoma | 2016-10-20 | yes; Bell DW et al., "Inherited susceptibility to lung cancer may be associated with the T790M drug resistance mutation in EGFR", Nature Genetics (2005) | advanced | – |
| P2* | deucravacitinib (TYK2 (negative_modulator)) | Crohn disease | 2018-07-16 | yes; Dendrou CA et al., "Resolving TYK2 locus genotype-to-phenotype differences in autoimmunity", Sci Transl Med 2016 Nov 2;8(363):363ra149 (PMID (2016) | did not advance | F2 biology did not translate |
| P2* | molgramostim (CSF2RA (agonist), CSF2RB (agonist)) | pulmonary alveolar proteinosis | 2016-03-21 | yes; Suzuki T, ..., Trapnell BC. "Familial pulmonary alveolar proteinosis caused by mutations in CSF2RA." J Exp Med 2008;205(12):2703-10 (epub 27 (2008) | advanced | – |
| P2* | mavacamten (MYH7 (inhibitor)) | hypertrophic cardiomyopathy | 2016-08-01 | partial; Geisterfer-Lowrance AA, Kass S, Tanigawa G, Vosberg HP, McKenna W, Seidman CE, Seidman JG. 'A molecular basis for familial hypertrophic card (1990) | advanced | – |
| P2* | pyrilutamide (AR (antagonist)) | androgenetic alopecia | 2020-09-28 | partial; Sawaya ME, Shalita AR. Androgen receptor polymorphisms (CAG repeat lengths) in androgenetic alopecia, hirsutism, and acne. J Cutan Med Surg  (1998) | advanced | – |
| P2* | brepocitinib (TYK2 (inhibitor), JAK1 (inhibitor)) | systemic lupus erythematosus | 2019-04-18 | yes; Diogo D et al., "TYK2 protein-coding variants protect against rheumatoid arthritis and autoimmunity, with no evidence of major pleiotropic e (2015) | did not advance | F7 trial design |
| P2* | rezivertinib (EGFR (inhibitor)) | non-small cell lung carcinoma | 2017-08-16 | yes; Bell DW, ..., Haber DA. "Inherited susceptibility to lung cancer may be associated with the T790M drug resistance mutation in EGFR." Nat Gen (2005) | advanced | – |
| P2* | ngm-621 (C3 (inhibitor)) | dry age related macular degeneration | 2020-07-22 | yes; Yates JR et al., "Complement C3 variant and the risk of age-related macular degeneration", N Engl J Med 2007;357:553-61 (PMID 17634448, epub (2007) | did not advance | F1 exposure |
| P2* | sibeprenlimab (TNFSF13 (binder_neutralizer)) | IgA glomerulonephritis | 2020-07-20 | partial; Yu XQ et al., "A genome-wide association study in Han Chinese identifies multiple susceptibility loci for IgA nephropathy", Nat Genet 44:178 (2011) | advanced | – |
| P2* | rAAV2tYF-CB-hRS1 (RS1 (replacement)) | X-linked retinoschisis | 2015-05-01 | yes; Sauer CG et al., "Positional cloning of the gene associated with X-linked juvenile retinoschisis," Nat Genet 1997 Oct;17(2):164-70, PMID 932 (1997) | did not advance | F1 exposure |
| P2* | pegzilarginase (ARG1 (replacement)) | arginase deficiency | 2016-06-01 | yes; Haraguchi Y et al., "Molecular basis of argininemia. Identification of two discrete frame-shift deletions in the liver-type arginase gene",  (1990) | advanced | – |
| P2* | aficamten (MYH7 (inhibitor)) | hypertrophic cardiomyopathy | 2020-01-10 | yes; Geisterfer-Lowrance AA, ..., Seidman CE, Seidman JG. 'A molecular basis for familial hypertrophic cardiomyopathy: a beta cardiac myosin heav (1990) | advanced | – |
| P2* | evazarsen (AGT (gene_expression_reduction)) | hypertensive disorder | 2019-01-03 | yes; Jeunemaitre X, Soubrier F, Kotelevtsev YV, Lifton RP, ... Lalouel JM. "Molecular basis of human hypertension: role of angiotensinogen." Cell (1992) | did not advance | F2 biology did not translate |
| P2* | zigakibart (TNFSF13 (binder_neutralizer)) | IgA glomerulonephritis | 2019-04-08 | partial; Yu XQ et al., "A genome-wide association study in Han Chinese identifies multiple susceptibility loci for IgA nephropathy", Nat Genet 44:178 (2011) | did not advance (pipeline wrong) | – |
| P2* | insulin 338 (INSR (agonist)) | type 2 diabetes mellitus | 2015-06-01 | partial; Taira M et al., "Human diabetes associated with a deletion of the tyrosine kinase domain of the insulin receptor", Science 1989;245:63-66 (P (1989) | did not advance | F8 commercial |
| P2* | suvecaltamide (CACNA1G (blocker), CACNA1H (blocker), CACNA1I (blocker)) | epilepsy | 2018-02-25 | partial; Chen Y et al., Ann Neurol 2003;54:239-43 (PMID 12891677) reported the germline CACNA1H missense variants in childhood absence epilepsy (CAE) (2004) | did not advance | F8 commercial |
| P2* | branaplam (SMN2 (gene_expression_increase)) | spinal muscular atrophy | 2015-04-02 | yes; Campbell L, Potter A, Ignatius J, Dubowitz V, Davies K. "Genomic variation and gene conversion in spinal muscular atrophy: implications for  (1997) | did not advance | F8 commercial |
| P2* | PF-06687234 (IL10RA (agonist)) | ulcerative colitis | 2017-12-20 | partial; Glocker EO et al. "Inflammatory bowel disease and mutations affecting the interleukin-10 receptor." N Engl J Med 2009;361(21):2033-45, PMID  (2009) | did not advance | F1 exposure |
| P2* | ichorcumab (F2 (inhibitor)) | venous thromboembolism | 2017-11-13 | yes; Poort SR, Rosendaal FR, Reitsma PH, Bertina RM. A common genetic variation in the 3'-untranslated region of the prothrombin gene is associat (1996) | did not advance | F2 biology did not translate |

### Limitations

* **Registry programs are not Biomedtracker programs.** BIO counts transitions that analysts record for programs companies disclose; this report counts programs from registered trials. Trials registered only outside ClinicalTrials.gov (ChiCTR, EU CTR, CTIS) are missing, so programs developed there look suspended. Restricting to programs with a US site removes most of the difference.
* **Suspension is inferred from inactivity.** A program counts as suspended when none of its trials has been active within 24 months. The rates move with that window (sensitivity table); BIO dates suspensions from company disclosures instead.
* **Recent entrants are mostly unresolved.** Programs that entered a phase in 2023–2025 are largely still running; the success rate counts only resolved programs, so it leans on early failures. Entries from 2015–2019 alone, with at least six years of follow-up, are shown as a sensitivity.
* **Outcome is FDA approval only.** Approvals elsewhere count as no approval.
* **Symptom and procedure indications without a MONDO term** (pain, cough, contraception; about 3% of trials) are grouped in each entity's disease-unspecified program, followed through Phase 2 but not to approval.
* **Most stopped programs give no reason.** Reasons come from the registry's why-stopped field, posted results and abstracts of results papers. Published results favour positive findings, and a missing reason is reported as such, not inferred. A vague reason ("sponsor decision", "business reasons") may hide an efficacy or safety result; reasons were not filled in from press releases, company filings or pipeline updates, so efficacy and safety shares are lower bounds.
* **The model declines some products.** Claude declines to classify some products derived from pathogens, toxins or live bacterial and viral vectors (botulinum and plague vaccines, oncolytic viruses, engineered bacteria) on every attempt: 162 entities have no resolved target and 53 no modality, so they fall out of Section 2 and the modality strata.
* **Constraint and essentiality are current.** gnomAD v4.1 constraint and DepMap pan-essentiality are today's values, not values as of phase entry.
* **Evidence as of phase entry undercounts.** Open Targets leaves undated evidence out of its yearly series; a sensitivity uses the 2026 scores instead.
* **Section 3 rests on labels made for it.** The trial endpoint class, the germline mechanism of each target in each disease and the orientation of each mouse model were classified by an LLM without the drug's name. The endpoint classifier was audited on 40 trials (39 classes and 40 governing outcomes right); the mechanism and mouse labels were spot-checked, and the errors found there led to a revised prompt rather than hand corrections.
* **Some evidence cannot be dated.** IMPC knockouts carry no date in Open Targets, MGI mouse models carry their gene's earliest literature year, gene-burden results start in 2019, and GWAS on measurement traits cannot be matched to a disease, so these lines are untestable or undercounted in Section 3.
* **Section 3's post-hoc analyses are exploratory.** The direction analyses and rules P1–P3 were added after the plan was committed, once their labels existed; their intervals are not corrected for the number of comparisons.


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
