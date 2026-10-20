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

This report rebuilds both questions from primary records. We took every interventional drug or biological study on ClinicalTrials.gov (222,915 studies, snapshot of 2026-10-20), resolved each intervention to the molecular entity it contains and each condition to a MONDO disease, and joined them to every FDA approval we could document: Drugs@FDA applications, 4,999 approved uses read from 2015–2026 approval letters, current labels, and 177 CBER biologics applications rebuilt from the agency's yearly pages and letters. The unit throughout is a *development program*: one molecular entity developed for one indication. An entity counts toward a program only in trials where it is the investigational agent, not a comparator or background therapy.

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

For development programs that entered a phase in 2015–2025 and were developed in the US, the likelihood of FDA approval from Phase 1 is 9.4% (95% CI 8.4%–10.5%), against BIO's 7.9% for 2011–2020 (6.8% for novel drugs). Across all industry programs registered on ClinicalTrials.gov, including those run only outside the US, it is 5.6%. Most programs stop without a stated reason: of 7,119 programs that stopped, 54% left no stated reason and no posted or published result, and 20% record an efficacy, safety or pharmacokinetic reason.

### How programs are counted

* **Trial:** a registered interventional study listing Early Phase 1 to Phase 3. A Phase 1/2 trial counts as Phase 2 and a Phase 2/3 trial as Phase 3. Withdrawn trials never enrolled and are left out.
* **Molecular entity:** the active substance, whatever its brand, sponsor code, dose or salt, resolved to its FDA UNII substance where one exists. Biosimilars fold into their reference entity.
* **Disease:** the MONDO term for the condition the trial treats, without line, stage, biomarker or age qualifiers.
* **Program:** one entity developed for one indication. An indication groups the entity's MONDO diseases the way a sponsor runs them as programs (prostate cancer with castration-resistant and metastatic prostate carcinoma; diffuse large B-cell and follicular lymphoma kept apart), decided by an LLM for each entity. An entity belongs to a program only in trials where it is the investigational agent, not a comparator or background therapy. Each industry trial's purpose is classified first: bioequivalence, formulation, food-effect, interaction and other product-support studies (10,772 trials) belong to no program; a first-in-human study or a basket across several diseases counts as Phase 1 only for the program the sponsor pursued next.
* **Phase entry and outcome:** a program enters a phase with its first industry-sponsored trial of that phase. It *advanced* when a later-phase trial in its disease started (any sponsor) or the FDA approved the entity for the disease; it is *suspended* when none of its trials has been active within 24 months of the snapshot (2026-10-20); otherwise it is still running and *censored*. Programs whose entity was already approved for the disease are lifecycle programs and are left out. As in BIO's report, each phase's success rate is advanced ÷ (advanced + suspended), and LOA is their product.
* **Approval:** FDA approval of the entity for the program's disease, a subtype or population of it, or a broader approved class that includes it, judged from the dated approval letters, original-approval dates and labels of every application of the entity (CDER and CBER).

17,127 programs of 10,277 entities entered at least one phase in 2015–2025.

### Phase transitions

| Transition | All programs (95% CI) | Developed in the US (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- |
| Phase 1 → Phase 2 | 55.3% (53.4–57.3), n=6,269 | 59.3% (56.8–61.9), n=4,089 | 52.0% |
| Phase 2 → Phase 3 | 29.3% (27.8–30.9), n=4,665 | 32.0% (30.1–33.9), n=2,994 | 28.9% |
| Phase 3 → Approval | 34.3% (31.4–37.2), n=1,548 | 49.4% (46.0–52.9), n=1,050 | 52.4% |
| **Phase 1 → Approval (LOA)** | **5.6%** (4.9–6.3) | **9.4%** (8.4–10.5) | **7.9%** (novel drugs 6.8%) |

Programs developed in the US, the closest match to BIO's FDA-focused Biomedtracker programs, advance from Phase 1 at 59.3% (BIO 52.0%), from Phase 2 at 32.0% (BIO 28.9%) and from Phase 3 to approval at 49.4% (BIO 52.4%). Phase 2 remains the steepest single drop. Across all registered industry programs the Phase 3 rate falls to 34.3%, because many programs run only outside the US end in approvals elsewhere, which this report does not count.

The likelihood of approval depends on choices a registry-based count has to make, and the table below shows how far each moves it. It is most sensitive to how long a program must be idle before it counts as suspended: 4.0% with a 12-month window and 8.0% with 36 months (24 in the headline). If every shared trial (a healthy-volunteer study, a basket) counted as the start of every later indication of the drug, LOA would rise to 10.8%, mostly by crediting indication expansions begun at Phase 2 with a Phase 1 success. Restricting to programs that entered a phase in 2015–2019, which have had at least six years to resolve, changes little (9.5% for US-developed programs). Vaccines are left out of the headline figures: annual and variant strain updates are licensed as supplements to the parent product, so registry entities for updated formulations never reach an approval of their own (LOA with vaccines included: 4.9%).


| Cohort or definition | Ph1→2 | Ph2→3 | Ph3→approval | LOA (95% CI) |
| :---- | :---- | :---- | :---- | :---- |
| All programs | 55.3% | 29.3% | 34.3% | 5.6% (4.9–6.3) |
| Programs with a US site in the phase | 59.3% | 32.0% | 49.4% | 9.4% (8.4–10.5) |
| Entity not yet FDA-approved at phase entry | 56.2% | 29.9% | 34.5% | 5.8% (5.2–6.5) |
| Entity already FDA-approved for another disease | 51.1% | 24.6% | 33.7% | 4.2% (2.9–5.9) |
| Suspension lag 12 months | 51.2% | 25.5% | 30.4% | 4.0% (3.5–4.5) |
| Suspension lag 18 months | 52.9% | 27.1% | 32.1% | 4.6% (4.1–5.2) |
| Suspension lag 36 months | 59.7% | 33.8% | 39.5% | 8.0% (7.2–8.9) |
| Uncertain approvals counted as approved | 55.3% | 29.3% | 34.3% | 5.6% (4.9–6.3) |
| Shared trials mark entry for every program of the entity | 69.2% | 41.8% | 37.1% | 10.8% (9.3–12.3) |
| Including vaccines | 54.1% | 28.7% | 31.8% | 4.9% (4.4–5.5) |
| Phase entry 2015-2019 (at least six years of follow-up) | 53.7% | 26.3% | 37.9% | 5.3% (4.5–6.2) |
| Phase entry 2015-2019, developed in the US | 59.0% | 31.7% | 50.6% | 9.5% (8.2–10.8) |

### Why programs stop

Each suspended program takes one reason from the industry trials of the phase it stopped in, in this order: an efficacy reason stated by the sponsor, a primary endpoint missed in posted or published results, a safety signal, a pharmacokinetic or formulation problem, an explicit business or strategic reason, a bare "sponsor decision", an enrollment, operational or regulatory reason, a positive primary readout without advancement, and finally no reason at all.

| Reason | Phase 1 | Phase 2 | Phase 3 |
| :---- | :---- | :---- | :---- |
| PK, dose or formulation | 1% (21) | 0% (8) | 0% (0) |
| business or strategic (explicit) | 14% (401) | 9% (286) | 6% (63) |
| completed, no results posted, no reason stated | 58% (1,628) | 30% (980) | 23% (234) |
| efficacy: primary endpoint not met | 0% (8) | 19% (633) | 17% (173) |
| efficacy: stated | 3% (81) | 6% (206) | 12% (120) |
| enrollment, operational or regulatory | 3% (78) | 6% (191) | 4% (43) |
| positive readout, not advanced | 0% (13) | 9% (305) | 19% (192) |
| safety | 2% (54) | 2% (82) | 3% (33) |
| sponsor decision, unspecified | 4% (117) | 4% (136) | 3% (30) |
| stopped, no reason stated | 14% (402) | 14% (472) | 13% (129) |

![Why suspended programs stopped, by phase](report/output/figures/failure_modes_by_phase.png)

The registry rarely says why a program stopped. In Phase 1, 72% of stopped programs left neither a stated reason nor a result, which is expected: Phase 1 trials seldom post results and companies seldom explain pausing early assets. In Phase 2 and Phase 3 the share without a reason falls to 44% and 36%. Efficacy is the recorded reason for 25% of programs that stopped in Phase 2 and 29% of those that stopped in Phase 3: the sponsor said so, or the posted or published primary endpoint was missed. Safety accounts for 2% and 3%: among Phase 2 and Phase 3 stops with an efficacy or safety reason, safety is 9% and 10%, below the 24% Harrison (2016) found among 2013–2015 failures with a disclosed reason. Either registry records under-report safety stops, or company disclosures over-represent them.

At the level of individual trials, the 5,557 industry trials started in 2015–2025 that stopped early or were withdrawn with a reason give: an explicit business, portfolio or competitive reason 36%, a bare "sponsor decision" 19%, efficacy 14%, enrollment or operations 14% and safety 4%. The draft's single 44% "commercial or strategic" category mixed these two kinds of statement; a "sponsor decision" with no reason may or may not hide an efficacy result, and the record cannot tell.

Finally, 19% of Phase 3 programs that stopped short of FDA approval had met their primary endpoint. In a sample we read, most of them were approved outside the US (Japan, China, Korea, Russia) or received a complete response letter from the FDA: a positive Phase 3 readout is necessary but not sufficient for US approval.


### By disease area and modality

| Disease area | All programs, LOA (95% CI) | Entities | Developed in the US, LOA (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- | :---- |
| Hematology | 17.3% (11.0–24.6) | 262 | 24.1% (15.8–33.9) | 23.9% |
| Metabolic | 16.7% (11.0–22.5) | 398 | 26.3% (18.7–34.4) | 15.5% |
| Oncology | 12.7% (10.2–15.5) | 2,596 | 16.2% (13.0–19.8) | 5.3% |
| Endocrine | 10.7% (6.0–16.0) | 319 | 26.9% (17.2–36.2) | 6.6% |
| Autoimmune | 9.3% (6.3–12.8) | 671 | 12.0% (8.0–16.7) | 10.7% |
| Allergy | 8.7% (3.3–15.8) | 124 | 15.1% (5.2–27.7) | 10.3% |
| Psychiatry | 8.2% (4.4–12.5) | 276 | 11.1% (5.8–17.3) | 7.3% |
| Respiratory | 6.7% (3.9–10.0) | 484 | 8.4% (4.6–12.9) | 7.5% |
| Neurology | 6.5% (4.8–8.5) | 897 | 12.9% (9.7–16.6) | 5.9% |
| Other | 5.4% (3.8–7.1) | 902 | 8.6% (5.9–11.3) | 13.0% |
| Ophthalmology | 4.4% (2.4–6.9) | 416 | 6.6% (3.7–10.6) | 11.9% |
| Cardiovascular | 3.3% (1.4–5.8) | 368 | 9.8% (4.7–16.0) | 4.8% |
| Infectious disease | 2.6% (1.8–3.6) | 920 | 4.5% (2.9–6.3) | 13.2% |
| Gastroenterology | 2.1% (0.7–4.0) | 342 | 5.7% (2.2–9.8) | 8.3% |
| Urology | 0.9% (0.0–3.1) | 70 | 0.0% (0.0–0.0) | 3.6% |

| Modality | All programs, LOA (95% CI) | Entities | Developed in the US, LOA (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- | :---- |
| siRNA / RNAi | 26.3% (11.8–41.5) | 142 | 32.5% (15.2–53.1) | 13.5% |
| Multispecific antibody | 21.2% (11.3–31.7) | 491 | 24.9% (14.0–35.8) | – |
| Antibody–drug conjugate | 19.3% (9.8–31.2) | 412 | 18.3% (7.8–30.4) | 10.8% |
| Monoclonal antibody | 11.3% (8.4–14.2) | 1,293 | 14.6% (10.9–18.5) | 12.1% |
| Antisense oligonucleotide | 10.0% (4.0–18.7) | 114 | 16.4% (6.6–29.0) | 5.2% |
| CAR-T | 9.4% (4.5–16.6) | 349 | 22.2% (11.2–37.3) | 17.3% |
| Peptide | 8.3% (4.6–12.5) | 346 | 13.0% (7.2–19.5) | 8.0% |
| Gene therapy | 5.6% (1.7–12.5) | 240 | 7.0% (1.9–15.9) | 10.0% |
| Small molecule | 4.6% (4.0–5.4) | 5,209 | 8.0% (7.0–9.3) | 7.5% |
| Protein | 3.3% (1.9–5.0) | 526 | 5.7% (3.2–8.7) | 9.4% |
| Radioligand | 2.6% (0.0–18.8) | 113 | 2.4% (0.0–20.8) | – |
| Other cell therapy | 1.0% (0.3–2.1) | 534 | 2.1% (0.5–4.9) | – |
| Other oligonucleotide | 0.9% (0.0–4.2) | 44 | 1.9% (0.0–8.5) | – |
| Microbiome or live biotherapeutic | 0.3% (0.0–1.3) | 97 | 1.2% (0.0–4.7) | – |
| Other | 0.2% (0.0–0.7) | 300 | 1.0% (0.0–4.4) | – |

![Likelihood of approval by disease area](report/output/figures/loa_by_area.png)

![Likelihood of approval by modality](report/output/figures/loa_by_modality.png)

The ordering of disease areas broadly follows BIO's: hematology (24.1% for US-developed programs) and metabolic programs (26.3%) reach approval most often, and cardiovascular, gastroenterology and urology programs least. Oncology (16.2%) comes out well above BIO's 5.3%: the 2015–2025 window holds the wave of immunotherapy, antibody–drug conjugate and bispecific approvals, and an approval in a cancer subtype counts for the program's cancer. Infectious disease (4.5%) sits far below BIO's 13.2%, largely because many registered anti-infective and COVID-19 programs, including US-run ones, were never approved. Among modalities, RNA interference, multispecific antibodies and antibody–drug conjugates reach approval most often and small molecules and non-antibody proteins least, the same broad pattern BIO reported. Strata with few programs have wide intervals.



## Predictive power of preclinical evidence

Human genetic evidence linking a program's target to its disease is the clearest preclinical signal of success. Programs whose target had it before they entered the phase reached FDA approval 3.50 times as often as programs without it (27.6% against 7.9%; 95% CI 2.65–4.53), the likelihood rises with the strength of the evidence, and the association holds at every phase after accounting for disease area, modality, novelty and era. Somatic driver and mouse-model evidence carry weaker signals; targets essential in every cancer cell line are a liability. Yet as a predictor of which individual programs will be approved, the evidence adds little to what disease area and modality already say, because most programs have none of it.


### Evidence lines and how they are matched

Each program aimed at a human protein (the entity's primary targets, resolved by an LLM from the entity's mechanism records and trial descriptions) is scored for the evidence its targets had **for the program's disease** in Open Targets Platform 26.09, **as of the year before the program entered the phase**. A target–disease association counts for the program's disease when the evidence disease is the same MONDO term, a subtype of it, or similar to it (Lin similarity ≥ 0.8, the criterion Minikel et al. used). Open Targets publishes a yearly series of each association's score, so evidence is taken as it stood before phase entry, not as it stands today. Evidence lines:

* **Human germline genetics:** GWAS credible sets (with locus-to-gene scores), gene burden tests, ClinVar, Genomics England PanelApp, Orphanet, Gene2Phenotype, ClinGen and UniProt; split into GWAS and rare-variant/Mendelian sources.
* **Somatic drivers:** COSMIC Cancer Gene Census, IntOGen and ClinVar somatic.
* **Mouse models:** IMPC phenotypes. **Expression:** differential expression in the disease (Expression Atlas). **Pathways:** Reactome. **Functional screens:** CRISPR screens.
* **Target-level properties** that are not disease-specific: loss-of-function intolerance (gnomAD LOEUF < 0.35) and pan-essentiality across DepMap cell lines.

Sources that encode clinical outcomes or literature co-mention (ChEMBL clinical precedence, Europe PMC) are not used. Vaccines, cell and gene therapies and other entities without a single human protein target fall outside this analysis, so its programs reach approval more often than the Section 1 cohort as a whole. Of the 10,240 programs on 1,662 targets scored, 14.8% of Phase 1 entrants had human genetic evidence for their disease at entry.

### Relative success

*Relative success* is the LOA of programs with the evidence divided by the LOA of programs without it (Nelson et al. 2015; Minikel et al. 2024). The 95% intervals resample targets, since programs on the same target are not independent.

| Evidence (for the program's disease, as of phase entry) | Programs with it | LOA with / without | Relative success (95% CI) |
| :---- | :---- | :---- | :---- |
| Human genetics (any germline source) | 1,681 | 27.6% / 7.9% | 3.50 (2.65–4.53) |
| Rare-variant / Mendelian (ClinVar, Orphanet, G2P, ClinGen, burden) | 1,019 | 30.1% / 8.7% | 3.47 (2.61–4.52) |
| GWAS credible set | 864 | 23.2% / 9.3% | 2.49 (1.69–3.48) |
| Somatic driver (COSMIC CGC, IntOGen, ClinVar somatic) | 1,686 | 21.4% / 9.0% | 2.37 (1.59–3.20) |
| Pathway (Reactome) | 215 | 21.8% / 10.0% | 2.19 (1.30–3.24) |
| Mouse model (IMPC) | 1,951 | 15.2% / 9.0% | 1.69 (1.25–2.21) |
| Differential expression in disease (Expression Atlas) | 1,374 | 14.2% / 9.7% | 1.46 (0.93–2.06) |
| LoF-intolerant target (gnomAD LOEUF < 0.35) | 1,907 | 9.2% / 10.5% | 0.87 (0.56–1.31) |
| Pan-essential (DepMap) | 562 | 2.6% / 10.7% | 0.24 (0.07–0.57) |

![Relative success by evidence line](report/output/figures/relative_success_by_evidence.png)

Rare-variant and Mendelian evidence (3.47×) and GWAS evidence (2.49×) both carry the genetic signal, in line with Minikel et al. (2024), who found 2.6× from Phase 1 to launch with Mendelian evidence stronger than GWAS. Somatic driver evidence (2.37×) and mouse phenotypes (1.69×) also associate with success; differential expression in the disease does not clearly (1.46×, interval spanning 1). Loss-of-function-intolerant targets show no penalty (0.87×), while pan-essential targets reach approval about a quarter as often (0.24×), mostly oncology small molecules aimed at machinery every cell needs (mTOR, tubulin, topoisomerases, histone deacetylases, WEE1 and ATR, BET proteins). CRISPR-screen evidence covered too few programs (78) to estimate.

Two checks bear on whether this reflects foresight rather than hindsight. Evidence is taken as it stood in Open Targets' yearly series before the program entered the phase, so later discoveries do not count. Counting all evidence known by 2026 instead weakens the genetic relative success to 2.99×: what was known in advance is more telling than what was found afterwards. And restricting matches to diseases similar to the program's (Lin ≥ 0.8, Minikel's criterion, without the subtype rule) gives 3.60×.


### Genetic dose–response

| Human genetic support (Open Targets score, as of phase entry) | Programs | Targets | LOA (95% CI) |
| :---- | :---- | :---- | :---- |
| None | 8,638 | 1,478 | 7.9% (6.4–9.7) |
| Lower third (> 0.00 to 0.61) | 660 | 272 | 20.0% (13.4–26.6) |
| Middle third (> 0.61 to 0.88) | 521 | 169 | 31.3% (21.5–40.0) |
| Upper third (> 0.88) | 570 | 204 | 34.5% (27.4–41.7) |

![Likelihood of approval by strength of human genetic support](report/output/figures/genetic_dose_response.png)

### What each line adds once the others are known

Programs with genetic evidence differ from programs without it in disease area, modality and era, and the evidence lines overlap. The table gives, for each phase, the relative risk of advancing for programs with each line, from one Poisson model containing every line together with disease area, modality, entity novelty and entry period (standard errors clustered by target).

| Evidence | Phase 1 → next | Phase 2 → next | Phase 3 → next |
| :---- | :---- | :---- | :---- |
| GWAS credible set | 1.07 (1.01–1.14) | 1.59 (1.35–1.86) | 1.09 (0.80–1.48) |
| Rare-variant / Mendelian (ClinVar, Orphanet, G2P, ClinGen, burden) | 1.09 (1.00–1.19) | 1.40 (1.19–1.66) | 1.57 (1.28–1.93) |
| Somatic driver (COSMIC CGC, IntOGen, ClinVar somatic) | 1.02 (0.92–1.13) | 1.13 (0.89–1.43) | 1.13 (0.85–1.50) |
| Mouse model (IMPC) | 0.97 (0.91–1.04) | 1.00 (0.86–1.16) | 0.98 (0.82–1.17) |
| Differential expression in disease (Expression Atlas) | 0.99 (0.91–1.07) | 1.04 (0.86–1.25) | 0.84 (0.66–1.07) |
| Pathway (Reactome) | 1.05 (0.92–1.19) | 0.90 (0.68–1.21) | 1.14 (0.82–1.58) |
| LoF-intolerant target (gnomAD LOEUF < 0.35) | 0.97 (0.88–1.08) | 1.21 (1.00–1.47) | 0.98 (0.77–1.26) |
| Pan-essential (DepMap) | 0.73 (0.58–0.90) | 0.66 (0.45–0.95) | 0.65 (0.33–1.28) |

One evidence line at a time, with the same adjustments, human genetic evidence raises the chance of advancing by 1.10× in Phase 1, 1.71× in Phase 2 and 1.47× in Phase 3: the effect sits where efficacy is first tested. In the joint model, GWAS and rare-variant evidence each keep an independent effect at Phase 2, rare-variant evidence also at Phase 3, and pan-essentiality keeps its penalty at Phases 1 and 2; somatic, mouse-model, expression and pathway evidence lose their association once genetics and the covariates are in the model, consistent with their univariate signal riding along with genetic support and with disease area.


### Does the evidence predict which programs reach approval?

We followed programs that entered Phase 1 in 2008–2016 for ten years (3,095 programs, 218 approved), with every feature frozen at entry, and fitted logistic models on disease area, modality, novelty and entry year alone, and with the evidence lines added. Performance is measured on held-out targets (5-fold cross-validation grouped by target) and on a temporal split (trained on 2008–2012 entries, tested on 2013–2016).

| Validation | Features | AUC (95% CI) | PR-AUC (base rate) | Programs (approved) |
| :---- | :---- | :---- | :---- | :---- |
| Held-out targets | Area, modality, novelty, year | 0.595 (0.535–0.640) | 0.115 (0.070) | 3,095 (218) |
| Temporal (2013–2016) | Area, modality, novelty, year | 0.640 (0.520–0.727) | 0.149 (0.072) | 1,551 (111) |
| Held-out targets | … plus all evidence lines | 0.604 (0.555–0.652) | 0.110 (0.070) | 3,095 (218) |
| Temporal (2013–2016) | … plus all evidence lines | 0.638 (0.526–0.718) | 0.138 (0.072) | 1,551 (111) |
| Held-out targets | Evidence lines only | 0.485 (0.422–0.556) | 0.078 (0.070) | 3,095 (218) |
| Temporal (2013–2016) | Evidence lines only | 0.549 (0.484–0.611) | 0.090 (0.072) | 1,551 (111) |

Change in held-out AUC when each line is removed from the full model (paired target bootstrap):

| Evidence removed | AUC change (95% CI) |
| :---- | :---- |
| Human genetics (any germline source) | -0.011 (-0.019 to -0.004) |
| Differential expression in disease (Expression Atlas) | -0.003 (-0.013 to +0.008) |
| Rare-variant / Mendelian (ClinVar, Orphanet, G2P, ClinGen, burden) | -0.002 (-0.004 to +0.000) |
| CRISPR screen | +0.000 (-0.000 to +0.000) |
| Mouse model (IMPC) | +0.001 (-0.005 to +0.006) |
| GWAS credible set | +0.001 (-0.001 to +0.004) |
| Pathway (Reactome) | +0.007 (-0.002 to +0.019) |
| Somatic driver (COSMIC CGC, IntOGen, ClinVar somatic) | +0.008 (-0.002 to +0.017) |
| Pan-essential (DepMap) | +0.012 (-0.002 to +0.038) |
| LoF-intolerant target (gnomAD LOEUF < 0.35) | +0.015 (+0.002 to +0.030) |

A model on disease area, modality, novelty and entry year alone ranks programs at an AUC of 0.595 on held-out targets; adding every evidence line gives 0.604. Removing human genetic evidence from the full model costs 0.011 of AUC (95% CI 0.004–0.019), a small but real contribution; no other line's removal measurably hurts. The temporal split tells the same story. The gap between a strong relative success and a small gain in discrimination is not a contradiction: genetic support roughly triples the odds for the minority of programs that have it (15% of Phase 1 entrants, fewer among the 2008–2016 entrants this model follows), but it says nothing about the majority, so it can sort only a small slice of programs. The draft's AUCs of 0.825 and 0.769 came from a leaked model and phantom programs (AUDIT.md, C33–C34).



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
| Drugs@FDA, FDA approval letters, openFDA labels | NDA/BLA applications, submissions and action dates; 4,999 approved uses read from 2015–2026 approval letters; current Indications and Usage text | Retrieved October 2026 |
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
| Approval: judged approved, dated 2015 or later | 25 | 100% (87%–100%) | 0 |
| Approval date: judged approved, dated 2015 or later | 25 | 96% (80%–99%) | 1 |
| Approval: judged approved before 2015 | 15 | 100% (80%–100%) | 0 |
| Approval: judged not approved (Phase 2+ programs) | 35 | 100% (90%–100%) | 0 |
| Approval: judged uncertain | 15 | 60% (36%–80%) | 6 |

Each error pattern these audits found was fixed in the pipeline and the affected labels re-derived, not patched by hand: diseases MONDO has no exact term for now map to their nearest broader term; development codes resolve to UNII substances, and the same substance under two names is merged; scanned FDA letters are read by OCR; labelling-only supplements no longer count as approvals; stop reasons stated only in a trial's summary are read; publication-based outcomes use only the abstracts given; and approval dates account for older applications of the same drug. The disease-mapping, entity and approval figures above come from fresh samples drawn after those fixes; before them, disease mapping agreed 94% of the time, entity resolution 95%, and 8 of 25 dated first approvals were wrong. Remaining entity errors are scattered (a development code resolved to the wrong substance, a salt chosen over its parent) rather than systematic. Programs judged "uncertain" for approval (93 of 24,996 judgements) were defensible only 60% of the time; counting them as approved instead leaves every rate unchanged to the first decimal (sensitivity table). The audit of the earlier draft, with every claim's verdict and every data issue, is in `AUDIT.md`.

### Limitations

* **Registry programs are not Biomedtracker programs.** BIO counts transitions that analysts record for programs companies disclose; this report counts programs from registered trials. Trials registered only outside ClinicalTrials.gov (ChiCTR, EU CTR, CTIS) are missing, so programs developed there look suspended. Restricting to programs with a US site removes most of the difference.
* **Suspension is inferred from inactivity.** A program counts as suspended when none of its trials has been active within 24 months. The rates move with that window (sensitivity table); BIO dates suspensions from company disclosures instead.
* **Recent entrants are mostly unresolved.** Programs that entered a phase in 2023–2025 are largely still running; the success rate counts only resolved programs, so it leans on early failures. Entries from 2015–2019 alone, with at least six years of follow-up, are shown as a sensitivity.
* **Outcome is FDA approval only.** Approvals elsewhere count as no approval.
* **Symptom and procedure indications without a MONDO term** (pain, cough, contraception; about 3% of trials) are grouped in each entity's disease-unspecified program, followed through Phase 2 but not to approval.
* **Most stopped programs give no reason.** Reasons come from the registry's why-stopped field, posted results and abstracts of results papers. Published results favour positive findings, and a missing reason is reported as such, not inferred.
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
