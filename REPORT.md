# Predictive Validity in Drug Development

<!-- Rendered by `python -m report` from report/output/*/numbers.json into REPORT.md, the doc's main tab.
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

This report rebuilds both questions from primary records. We took every interventional drug or biological study on ClinicalTrials.gov (227,130 studies, snapshot of 2026-10-20), resolved each intervention to the molecular entity it contains and each condition to a MONDO disease, and joined them to every FDA approval we could document: Drugs@FDA applications, 6,529 approved uses read from 2008–2026 approval letters, current labels, and 177 CBER biologics applications rebuilt from the agency's yearly pages and letters. The unit throughout is a *development program*: one molecular entity developed for one indication. An entity counts toward a program only in trials where it is the investigational agent, not a comparator or background therapy.

The report has three parts:

1. **Industry failure modes.** Phase transitions, likelihood of approval (LOA) and the reasons programs stop, for programs that entered each phase in 2008–2019: an updated companion to BIO's *Clinical Development Success Rates 2011–2020*.
2. **Predictive power of preclinical evidence.** For programs aimed at a human protein target, whether the target had human genetic, somatic, animal-model, expression, pathway or cell-screen evidence for the program's disease, and how potent and selective the drug itself had measured in laboratory assays, all as known before the program entered the phase, and how much each changes the chance of approval.
3. **What translates to the clinic.** Which kinds of evidence predicted that a Phase 2 program would advance, and whether a stronger, more specific or direction-matched version of each did better; on which trial endpoints the advantage shows; with verified case studies.

Every classification in this analysis was made by an LLM reading the source record and recorded with its prompt and input. The main labels were checked against an independent re-derivation of a seeded sample; modality, disease area and targets were not audited (Appendix).


## A history of drug development

Over the past century, drug development moved from natural observation and phenotypic screening to target-based and genetically grounded hypotheses. Each era narrowed the unit of the biological hypothesis, from a whole-organism effect to a target in a specific patient context.

![Eras of drug discovery: the technology of each era and the unit of its biological hypothesis](report/output/figures/history.png)

## Industry failure modes

For development programs that entered a phase in 2008–2019 and were developed in the US, the likelihood of FDA approval from Phase 1 is 8.9% (95% CI 8.0%–9.9%), against BIO's 7.9% for 2011–2020 (6.8% for novel drugs). Across all industry programs registered on ClinicalTrials.gov, including those run only outside the US, it is 5.4%. Once each stop is traced to its cause, efficacy or exposure explains 44% of Phase 2 and 3 stops and sponsor decisions 21%.

### How programs are counted

* **Trial:** a registered interventional study listing Early Phase 1 to Phase 3. A Phase 1/2 trial counts as Phase 2 and a Phase 2/3 trial as Phase 3. Withdrawn trials never enrolled and are left out.
* **Molecular entity:** the active substance, whatever its brand, sponsor code, dose or salt, resolved to its FDA UNII substance where one exists. Biosimilars fold into their reference entity.
* **Disease:** the MONDO term for the condition the trial treats, without line, stage, biomarker or age qualifiers.
* **Program:** one entity developed for one indication. An indication groups the entity's MONDO diseases the way a sponsor runs them as programs (prostate cancer with castration-resistant and metastatic prostate carcinoma; diffuse large B-cell and follicular lymphoma kept apart), decided by an LLM for each entity. An entity belongs to a program only in trials where it is the investigational agent, not a comparator or background therapy. Each industry trial's purpose is classified first: bioequivalence, formulation, food-effect, interaction and other product-support studies (10,770 trials) belong to no program; a first-in-human study or a basket across several diseases counts as Phase 1 only for the program the sponsor pursued next.
* **Phase entry and outcome:** a program enters a phase when its first industry-sponsored trial of that phase starts. It *advanced* when a later-phase trial in its disease started (any sponsor) or the FDA approved the entity for the disease. A trial that has not started, because it is still not yet recruiting or its record went silent before its estimated start date, marks neither entry nor advancement. A program is *suspended* when none of its trials, nor the trial that marked its Phase 1 entry, has been active within 24 months of the snapshot (2026-10-20); otherwise it is still running and *censored*. Programs whose entity was already approved for the disease are lifecycle programs and are left out; an approval dated only as before 2008 (the first approval letters read) is placed at the entity's first FDA approval, the earliest it could have happened. As in BIO's report, a phase a program skipped (Phase 1 straight to Phase 3, or approval from Phase 2) counts as a success in that phase, each phase's success rate is advanced ÷ (advanced + suspended), and LOA is their product. *US-developed* programs are those with a US-sited industry trial in the phase; a cohort with fewer than ten entities resolved in a phase gets no LOA.
* **Approval:** FDA approval of the entity for the program's disease, a subtype or population of it, or a broader approved class that includes it, judged from the dated approval letters, original-approval dates and labels of every application of the entity (CDER and CBER).

13,490 programs of 7,123 individual drugs entered at least one phase in 2008–2019. Entries end in 2019 so that every program has had at least six years to advance or stop before the snapshot; registration of industry trials became mandatory in the US in late 2007, so the window starts in 2008.

### Phase transitions

![Share of Phase 1 entrants still in development at each phase, all programs and those developed in the US, against BIO 2011–2020](report/output/figures/phase_funnel.png)

### Why programs stop

For 3,111 of the 5,898 Phase 2 and 3 stops among 2008–2019 entries, the registry gives no usable reason: none at all, only "sponsor decision", an unspecified "other" reason, or an efficacy reason that the reading of efficacy failures below found wrong. We classified each of these with an LLM that read the program's trials and searched the web for company releases, filings and news. It named a cause only where a source stated or showed it, and otherwise gave its best guess, the *likely* cause. The method and how well it does on stops whose reason is known are in the appendix.

A sourced cause was found for 71% of the traced programs (2,204), and a likely cause for 98%. The biggest changes from the registry's picture:

* **Many quiet stops were not failures.** A positive readout that was not taken further in the disease (approval outside the US, a stalled partnership, a move to another formulation) was the sourced cause for 598 traced programs, and 214 had not stopped at all: development continued under another registry, region, name or combination. Section 1's suspension rule, which reads only ClinicalTrials.gov, counts these as stops, so its failure rates are somewhat high.
* **Efficacy is under-recorded.** Efficacy or exposure was the sourced cause of 737 traced programs, usually from published results or a company statement the registry never carried, raising efficacy or exposure from 28% of all Phase 2/3 stops as registered to 39% sourced (44% counting likely causes).
* **Sponsor decisions are the rest.** Portfolio, commercial and partner decisions, acquisitions, mergers, lost funding and closures account for 21% of all stops counting likely causes. Safety stays rare (3%).

**Within each cause.** Where the sponsor decided, the sources most often name portfolio prioritisation (25%) or the company running out of money or closing (16%); 33% say no more than "business reasons". Operational stops are mostly slow enrollment (71%). 26% of safety stops do not say what the harm was. Most positive readouts that went no further give no reason (79%); otherwise the drug was approved outside the US (10%) or the sponsor chose not to go on, for the same reasons as other sponsor decisions (9%), each as a share of all positive readouts. Of the stops no source explains, 35% had a sponsor that started no later trial, and in 35% the drug was dropped while its sponsor carried on.

![Each cause of Phase 2 and 3 stops, phase entries 2008–2019, broken down by subcause. Subcauses are what the sponsor's stated reason or the traced source says; "not stated" means it says no more than the cause. For stops no source explains (unknown), the breakdown is what the drug and its sponsor did next, not a reason](report/output/figures/stop_subcauses.png)

**Over time.** Counting sourced and likely causes, and leaving out programs that turned out not to have stopped, efficacy or exposure was the cause of 48% of stops among programs entering in 2008–2011, 44% in 2012–2015 and 43% in 2016–2019; sponsor decisions 20%, 23% and 23%, and a positive readout not yet advanced 20%, 23% and 21%. Among entries from 2015 to 2025 (4,112 stops, many later programs still running), the shares are 40% efficacy or exposure, 26% sponsor decision and 22% positive readouts.

**Phase 1.** Phase 1 stops were classified the same way (2,969 programs entering 2008–2019). As registered, 83% give no usable reason, since Phase 1 trials seldom post results and companies seldom explain pausing early assets. Tracing found a sourced cause for 59% of those and a likely cause for 95%. Counting both, efficacy or exposure was the cause of 20% of Phase 1 stops, safety 9%, sponsor decisions 46%, operational 6% and a positive readout not yet advanced 12%; 5% stay unknown.

Tested on stops whose reason is known, the classifier often read safety stops as efficacy, so the efficacy share after tracing is an upper estimate and safety is likely under-counted.


### Why efficacy failed: the target was not engaged, or it was the wrong target

Efficacy fails in one of two ways: the drug never engaged its target in patients, so the hypothesis went untested, or it engaged and the disease did not respond. For every program entering Phase 1, 2 or 3 in 2008–2019 that stopped for efficacy or exposure (PK, dose or formulation), 387 in Phase 1 and 2,215 in Phase 2 or 3, an LLM read the trials, results, papers and, where those were silent, the web, and judged whether the drug reached and engaged its target in humans at the doses tested. The method and its checks are in the appendix.

![Top: Phase 1, 2 and 3 stops by cause, phase entries 2008–2019, excluding programs whose development continued; where no source states the cause, the model's likely cause is counted. Safety is a floor: sponsors rarely state it, a missed endpoint takes precedence over a safety signal, and the tracing recognised fewer than half of known safety stops. Sponsor decision is the least reliable cause. Positive readouts include programs whose primary endpoints were only partly met. Bottom: the programs of each phase stopped for efficacy or exposure with a sourced cause (likely-only causes are not broken down), by what the evidence shows about target engagement. Phase 1 trials rarely test efficacy, so its efficacy stops are mostly early patient cohorts and dose-finding readouts](report/output/figures/efficacy_attribution.png)

Where the record shows whether the mechanism was tested, the drug had engaged its target in 1,031 of 1,258 programs and the disease did not respond; **18%** (16%–21%) failed without adequate engagement or exposure, or with another drug on the same target succeeding in the disease. The second kind is the larger and is inferred rather than measured: 116 of the 227 not-engaged programs failed where a drug on the same target worked, 94 of them with no human engagement data of their own; the rest had exposure or engagement measured and found inadequate. Failures to engage are about as common in Phase 3 (19%) as in Phase 2 (18%): no regulation requires engagement to be shown, and good practice places it in Phase 1 or 2a, yet engagement was often still unverified when confirmatory trials started. Outside oncology the share is 18%. Trial design, population or endpoint account for 7% of efficacy failures, and toxicity that offset efficacy for 9 programs. Another 52 programs recorded as efficacy stops were not failed efficacy tests (a met endpoint, a missed non-inferiority margin, a business stop, or off-target toxicity); they are counted under their traced cause above and left out here.

* *Engaged, no benefit.* Venglustat cut glucosylceramide in the cerebrospinal fluid of people with *GBA1* Parkinson's disease by about 73% at the top dose ([Peterschmitt 2022](https://doi.org/10.3233/JPD-212714)), and over a year their motor scores worsened by 7.3 points on drug against 4.7 on placebo ([MOVES-PD](https://doi.org/10.1016/S1474-4422(23)00205-3)). CSL112, plasma-derived apolipoprotein A1 that raises cholesterol efflux capacity, did not reduce myocardial infarction, stroke or cardiovascular death at 90 days in 18,219 patients after myocardial infarction (hazard ratio 0.93, 0.81–1.05; [AEGIS-II](https://doi.org/10.1056/NEJMoa2400969)).
* *Not engaged.* PF-06687234, an IL-10 fusion protein added to infliximab for ulcerative colitis, was stopped for futility, and was detected, at low concentration, in only one colon tissue sample: the drug may never have reached the inflamed mucosa at a useful level ([Ther Adv Gastroenterol 2026](https://doi.org/10.1177/17562848251410784)).

**Over time.** Among efficacy failures of programs entering in 2008–2011, 2012–2015 and 2016–2019, the share not engaged where engagement is known was 19%, 19% and 16%, and the share with no engagement evidence 38%, 34% and 35%. For entries from 2015 to 2025 the not-engaged share is 15% (13%–19%, 1,365 programs).

**Phase 1.** Phase 1 trials mostly test safety, dose and exposure, often in healthy volunteers, so an efficacy or exposure stop there is usually an early patient cohort or a dose-finding readout. The same labels were applied to the 387 Phase 1 programs entering 2008–2019 that stopped for efficacy or exposure. Where engagement is known (236 programs), 33% (27%–40%) were not engaged; 38% have no engagement evidence either way.

**The large caveat is what the public record does not say.** For 36% of efficacy failures there is still no human evidence of engagement either way, after the web search, so a drug that never engaged and a target that does not matter cannot be told apart. Engagement was shown in patients with the program's disease for only 30% of the programs where it was shown at all, and was public or registered before the failed trial started for 52%. The gap need not be neutral: a drug that never engaged its target leaves less to publish, and engagement inferred from success in another disease can only add to the engaged side. Among the programs the web search could decide, this shows a little: 31 of the 148 it found tested were not engaged (21%), against 19% among the programs the bundle alone decided. If every program still indeterminate were a failure to engage, the ceiling is 50%. Counting only directly measured engagement, and the other variants in the appendix, gives the same direction.

The answer to "was the target wrong, or was it never hit?" is therefore: where anyone can tell, the target was usually hit. Among efficacy failures whose mechanism was tested, 18% failed to engage (13% to 30% across the variants above); in the rest the drug engaged its target and the disease did not move. For 36% of failures the public record, searched, cannot say.


### By disease area and modality

![Likelihood of approval by disease area](report/output/figures/loa_by_area.png)

![Likelihood of approval by modality](report/output/figures/loa_by_modality.png)

Disease areas rank differently from BIO's: the rank correlation with BIO's LOA across the 15 areas is 0.50 for all programs and 0.54 for US-developed ones. Across all programs, hematology, metabolic and oncology programs reach approval most often (18.4%, 10.2% and 9.8%), and cardiovascular, gastroenterology and urology programs least (2.7%, 3.0% and 3.8%). Among US-developed programs, endocrine (12.2%) and oncology programs (12.4%) come out far above BIO's 6.6% and 5.3%; for oncology, the window takes in the wave of immunotherapy and antibody–drug conjugate approvals, and an approval in a cancer subtype counts for the program's cancer. Ophthalmology (6.4%) falls well below BIO's 11.9%. Among modalities, monoclonal antibodies and antibody–drug conjugates reach approval most often across all programs (12.8% and 8.9%), and among the classes BIO also reports, antisense oligonucleotides (4.5%), peptides (4.6%) and gene therapies (4.8%) least. RNA interference and CAR-T, near the top of BIO's ordering, have too few entities resolved in Phase 3 here (most of their approvals came straight from Phase 2) to estimate. Across the 7 classes both estimate, the modality ordering agrees with BIO's (rank correlation 0.82).



## Predictive power of preclinical evidence

Human genetic evidence linking a program's target to its disease is the clearest preclinical signal of success. Programs whose target had it before they entered the phase reached FDA approval 3.08 times as often as programs without it (23.0% against 7.4%; 95% CI 2.32–4.04), the likelihood rises with the strength of the evidence, and the association holds at every phase after accounting for disease area, modality, novelty and era. Somatic driver and mouse-model evidence carry weaker signals. Cancer cell-line CRISPR screens and DepMap's list of essential genes were first published in 2019, too late for any program in the window; judged with hindsight, screens mostly single out oncology targets already validated, and essential targets fail more often. The drug's own laboratory pharmacology, measured before entry for 37% of small-molecule programs and 0% of antibody programs, carries one signal: measured drugs at 100 nM or better at their target reached approval 2.57 times as often as weaker measured drugs, while functional measurement in cells and selectivity did not help. Yet as a predictor of which individual programs will be approved, the evidence lines raise discrimination only modestly over disease area and modality (held-out AUC 0.605 to 0.641), because most programs have none of them.


### Evidence lines

Each program aimed at a human protein is scored for the evidence its targets had **for the program's disease**, **as of the year before it entered the phase**, from Open Targets: human germline genetics (GWAS and rare-variant), somatic cancer drivers, mouse models, expression in the disease, pathways and CRISPR screens in human cells, plus two properties of the target itself (essential in most cells; intolerant of loss of function). A third group describes the drug rather than its target or disease: its potency, functional activity in cells and selectivity, as measured in laboratory assays published before entry and collected in ChEMBL. How each line is dated and matched to the program's disease is in the appendix. Vaccines, cell and gene therapies and other entities without a single human protein target fall outside this analysis, so its programs reach approval more often than the Section 1 cohort as a whole. Of the 9,021 programs on 1,358 targets scored, 9.1% of Phase 1 entrants had human genetic evidence for their disease at entry.

### Relative success

*Relative success* is the LOA of programs with the evidence divided by the LOA of programs without it (Nelson et al. 2015; Minikel et al. 2024).

The figure in Section 3 ("Which evidence translates") sets relative success for each line beside the Phase 2 result for the same evidence.

Rare-variant and Mendelian evidence (3.23×) and GWAS evidence (1.91×) both carry the genetic signal, in line with Minikel et al. (2024), who found 2.6× from Phase 1 to launch with Mendelian evidence stronger than GWAS. Somatic driver evidence (2.52×), mouse phenotypes (1.54×) and Reactome pathways (2.55×, from only 179 programs) also associate with success; differential expression in the disease does not clearly (1.13×, interval spanning 1). CRISPR knockout screens in cancer cell lines (Project Score) were first released in 2019, after every program in the window had entered its phase, so none could count them; scored on today's data instead, as hindsight, they give 2.83× (1.48–4.36, 325 programs), mostly on targets oncology had already validated (EGFR, ERBB2, ESR1, KRAS, CDK4 and CDK6).

Target liabilities, properties of the target rather than evidence for the disease, carry little. Loss-of-function-intolerant targets show no penalty (0.96×). DepMap's common-essential list was also first published in 2019, so no program in the window could have known its target was on it. Judged by today's list, as hindsight, essential targets reach approval far less often (0.35×, 0.12–0.64), but much of that comes from targets found essential after their programs had failed, mostly oncology small molecules aimed at machinery every cell needs (mTOR, tubulin, topoisomerases, histone deacetylases, WEE1 and ATR, BET proteins), so it is not a penalty a sponsor could have applied.

Two checks bear on whether this reflects foresight rather than hindsight. Evidence is taken as it stood the year before the program entered the phase, each item dated by when it became known, so later discoveries do not count. Counting all evidence known by 2026 instead weakens the genetic relative success to 2.16×: what was known in advance is more telling than what was found afterwards. And restricting matches to diseases similar to the program's (Lin ≥ 0.8, Minikel's criterion, without the subtype rule) gives 3.10×.


### Genetic dose–response

![Likelihood of approval by strength of human genetic support](report/output/figures/genetic_dose_response.png)

### What each line adds once the others are known

Programs with genetic evidence differ from programs without it in disease area, modality and era, and the evidence lines overlap. The figure gives, for each phase, the relative risk of advancing for programs with each line, with the other lines, disease area, modality, novelty and entry period held fixed.

![Relative risk of advancing at each phase, with the other lines, disease area, modality, novelty and entry period held fixed](report/output/figures/joint_by_phase.png)

One evidence line at a time, with the same adjustments, human genetic evidence raises the chance of advancing by 1.10× in Phase 1, 1.65× in Phase 2 and 1.55× in Phase 3: the effect sits where efficacy is tested. In the joint model, rare-variant and Mendelian evidence keeps an independent effect at Phase 2 (1.51×) and Phase 3 (1.54×), while GWAS evidence adds little once it is known. Somatic driver evidence keeps an effect at Phase 2 (1.34×, 1.05–1.71); mouse-model evidence keeps a small one that is not clearly above none (1.13×), and expression and pathway evidence lose their association once genetics and the covariates are in the model, consistent with their univariate signal riding along with genetic support and with disease area. A drug measured as potent at its target advances more often from Phase 3 (1.58×, 1.06–2.37).


### By disease area (planned)

*Outline of an analysis not yet run; this section holds no results.*

The estimates above pool every disease area and adjust for area without asking whether an evidence line predicts equally well in each. This section will ask whether genetic support, and the other lines, predict approval more strongly in some disease areas than in others.

* **Areas.** The 15 areas of Section 1 are too small one by one: about 15% of programs carry genetic evidence, so most area-by-line cells would hold a few dozen programs. They will be pooled into six groups: oncology; immunology and inflammation (autoimmune, allergy, respiratory, gastroenterology); neuroscience (neurology, psychiatry); cardiometabolic and endocrine (cardiovascular, metabolic, endocrine); hematology; and all others (infectious disease with a human target, ophthalmology, urology, other).
* **Measures.** For each group and evidence line: the number of programs with the line, LOA with and without it, and relative success with its 95% interval, as in the relative success table. Phase 2 risk ratios of advancing, adjusted for modality, novelty and entry period, as in the joint model. Cells with fewer than 100 programs carrying the line are left blank.
* **Lines.** Human genetics (any, GWAS, rare-variant), mouse models, expression in the disease, an approved drug on the target for a related disease, and drug potency; somatic drivers for oncology only.
* **Does the effect differ?** One model with an interaction between each line and the area group, tested jointly, so that a difference between groups is not read off overlapping intervals. Leaving out each group in turn shows whether the pooled genetics estimate rests on one area.
* **Planned table.** Rows are evidence lines and columns the six groups, each cell holding relative success (95% CI) and the number of programs with the line.
* **Planned figure.** A forest plot of relative success for human genetics by area group, beside the pooled estimate.
* **What it cannot show.** With few genetically supported programs in most groups, the intervals will be wide; a group with no detectable effect is not evidence that genetics fails there. Disease area was assigned by an LLM and has not been audited.

### The drug's own pharmacology

The lines above concern the target and the disease. The drug-pharmacology lines concern the molecule: how strongly it acts on its primary target in laboratory assays (the concentration giving half its maximal effect, or its binding affinity), whether that was measured as a functional response in living cells, and how much more strongly it acts on its target than on any other human protein tested. Each measurement counts from the year of the paper, patent or dataset that reported it, as of the year before phase entry; the definitions are in the appendix.

Coverage is thin and lopsided. 24% of the programs scored had any such measurement at their primary target before a phase entry: 37% of small-molecule programs and 24% of peptide programs, but 0% of antibody and 0% of other protein programs, because ChEMBL's curated measurements come from medicinal chemistry papers and patents about small molecules. Where a drug was measured, it was usually potent: the median best potency was 8.35 on the negative-log scale (4.47 nM), and 83% of measured programs reached 100 nM or better. Off-target measurements existed for 70% of measured programs, and 23% of those were at least 100-fold selective.

A line carried by fewer than 100 programs is not estimated; all five drug lines clear that bar. Having a measurement at all says nothing about success (0.99×, 0.72–1.32). Potency does, a little, once the comparison is kept among drugs that were measured: those at 100 nM or better reached approval 2.57 times as often as the 373 measured programs whose drug was weaker (1.52–5.08); against all programs, measured or not, the ratio is 1.20× and the interval spans 1. In the joint model, with the disease evidence, disease area, modality, novelty and era held fixed, a potent drug advanced more often at each phase, clearly only at Phase 3 (1.17 at Phase 1, 0.92–1.47; 1.32 at Phase 2, 0.96–1.82; 1.58 at Phase 3, 1.06–2.37). Raising the bar to 10 nM separates measured programs less sharply (2.35×, 1.47–3.67). Selectivity of 100-fold or more shows no association (0.99×, 0.47–1.75), and neither does it at any phase in the joint model. Functional potency measured in cells goes the wrong way (0.72×, 0.43–1.11; 0.76 at Phase 1 in the joint model, 0.59–0.97), a pattern these data cannot explain; a cell-based readout is no sign that a program will do better. Counting every measurement published by 2026 instead of before entry gives 1.41× for potency against all programs.

These lines measure the molecule, not whether its target matters in the disease, and they come with a bias of their own: drugs that look promising attract more papers, and potency is published mostly for small molecules from medicinal chemistry programs, so a measurement is partly a marker of a well-studied, novel-chemistry program. Weak measured drugs are a small group of 373 programs, and the clearest reading is that a drug well short of 100 nM at its intended target rarely reaches approval, not that more potency beyond that point helps.


### Does the evidence predict which programs reach approval?

We followed programs that entered Phase 1 in 2008–2016 for ten years (3,185 programs, 159 approved) and asked whether adding the evidence lines to what is known about disease area, modality, novelty and entry year improves the prediction of approval, on targets the model had not seen.

![Held-out AUC with and without the evidence lines, and the change in AUC when each line is removed](report/output/figures/prediction.png)

A model on disease area, modality, novelty and entry year alone ranks programs at an AUC of 0.605 on held-out target sets; adding the evidence lines raises it to 0.641 (95% CI 0.580–0.705), and the temporal split agrees (0.620 without, 0.637 with). Human genetics carries most of the gain: removing it lowers the held-out AUC by 0.025 (95% CI 0.005–0.047), and no other line's removal measurably lowers it. GWAS evidence covered too few of the 2008–2016 entrants to be modelled, so genetics here means rare-variant and Mendelian evidence; CRISPR screens and DepMap essentiality were not published before 2019, so none of these entrants carries them. Discrimination stays modest all the same, and that does not contradict the relative success: genetic support multiplies the chance of approval by about 3.08 for the minority of programs that have it (9% of Phase 1 entrants, fewer among the 2008–2016 entrants this model follows), but says nothing about the majority, so it can sort only a small slice of programs.



## What translates to the clinic

Human genetic evidence for the program's own disease is the preclinical evidence that most clearly carried over into Phase 2. Outside oncology, programs whose target had germline genetic evidence for the disease before they entered Phase 2 reached Phase 3 or approval within four years 1.74 times as often as programs whose target had no germline genetic evidence at all (24% against 11%), and the advantage shrinks as the evidence moves to a related disease (20%) or to unrelated diseases only (14%). The same target does better in the diseases its genetics points to than in its other diseases (odds ratio 3.17), and the effect holds after accounting for an approved drug on the target. The advantage shows in efficacy: genetically supported programs stopped for efficacy less often, though business and operational stops fell about as much. Somatic drivers in oncology and animal models of the disease also predicted advancing, with smaller effects; Reactome pathway evidence pointed the same way without surviving correction, differential expression carried nothing, and a mouse model whose direction matched the drug's did not predict Phase 2 success. Whether the direction of the genetic effect matters could not be tested, because almost no program went against an established mechanism. Grouped by kind, germline genetics, somatic drivers and animal models predict after correcting for the number of kinds tested, and no more specific version of any kind (stronger GWAS, Mendelian evidence, genetics or a mouse model pointing the drug's way) does better than the rest of its kind; an approved drug on the same target for a related disease predicts more strongly still. Genetic support covered only 20% of the programs that advanced.


### Design

The cohort is programs on a human protein target that entered Phase 2 in the report's window, 2008-01-01 to 2019-12-31 (4,596 programs on 1,158 primary-target sets), each followed for four years: a program *advanced* if a Phase 3 trial of its own started, or the FDA approved it for the disease, within four years (15.0% did). Phase 2 is where a drug is first tested for efficacy in patients, so it is the first point at which the evidence's claim about the disease is put to the test; a four-year outcome also resolves for every entry in the window. The analysis plan was committed before any of these analyses touched outcomes; departures from it are marked below. The plan registered Phase 2 entries from 2015 to October 2020 and trials started from 2010; both now use the report's 2008–2019 window, so that every section describes the same programs. How evidence was dated and matched, the regimes, the models and the trial-level analysis are in the appendix.

### Confirmatory hypotheses

![The pre-registered hypotheses](report/output/figures/s3_hypotheses.png)

![Specificity of the genetic evidence](report/output/figures/s3_specificity.png)

Two of the seven hypotheses hold after correction for multiple testing.

* **Genetics for the disease, overall and within a target (supported).** Outside oncology, Phase 2 programs advanced within four years at 11% with no germline genetic evidence on the target (853 programs), 14% with evidence only for unrelated diseases (1,548), 20% with evidence for a related disease (189) and 24% with evidence for the disease itself (201); only the last differs from none once disease area, modality, novelty, period and target precedent are accounted for. Among the 70 targets developed in several diseases with and without genetic support and with different outcomes (736 programs), the diseases with support advanced more often (odds ratio 3.17, 2.10–4.78): the signal is not only that some targets are better than others.
* **Direction of effect, as Open Targets labels it (not supported).** Open Targets' direction-of-effect fields follow each variant's predicted consequence, so a few truncating ClinVar variants make gain-of-function disease genes such as PCSK9, MYH7 and TTR read as loss of function, and inhibitors of them as discordant. The test is reported as registered; the direction analysis below replaces those fields.
* **Proximal against distal endpoints (not supported).** In trials with registry-posted results, genetic support lowered the chance of missing the primary endpoint on proximal endpoints (risk ratio 0.70, 0.49–1.01), but the trend towards distal endpoints (1.23 per step, p = 0.183; 0.733 after Holm correction) is not clear, nor across all readable trials (0.96).
* **Efficacy stops against business stops (not supported).** Genetic support lowered efficacy stops (risk ratio 0.65, 0.50–0.84), but business and operational stops fell by a similar factor (ratio of the two 1.28, 0.83–1.97), so the data cannot say that it acts on efficacy alone. Safety stops were no rarer (0.97, 0.57–1.66), nor were stops for pharmacokinetic, formulation or operational reasons, the plan's negative control (0.84, 0.48–1.47).
* **Target liabilities and safety stops (not supported).** Targets that are pan-essential, intolerant of loss of function, or lethal when knocked out in mice did not stop for safety more often (1.19, 0.73–1.94). Safety is the recorded reason for fewer than 2% of programs, so registries see little of it.
* **Somatic drivers that match the drug (not supported).** In oncology, a somatic driver whose direction matches the drug's (an activated oncogene and an inhibitor) advanced somewhat more often (1.46, 1.05–2.04), but not by more than chance allows across seven tests (Holm-corrected p 0.128).

**Checks on the genetics result.** Swapping each program's disease for another program's in the same disease area, 200 times, gives a median risk ratio for genetics for the disease of 1.44 against the observed 1.74 (95th percentile 1.75; p = 0.060). Much of the contrast with targets that have no germline genetics therefore reflects whether a target has been studied genetically at all; matching the disease adds to it, though the observed value sits at the edge of what shuffled diseases give. At Phase 1, where efficacy is rarely tested, the same contrast is 1.12 (0.95–1.33). Against all other programs rather than those with no germline genetics on the target, genetic support gives 1.56 outside oncology, and 1.45 (1.07–1.96) after adjusting for an approved drug on the target for a related disease; on targets with no approved drug at all, genetic support gives 1.57 (1.10–2.25, all disease areas). Leaving out the most influential target set (IL23A) gives 1.65. Leaving out each of the 5 largest target classes in turn gives 1.63 to 1.78; the lowest, without the "other protein" class, has an interval of 0.98–2.69, so the estimate leans on that class.

**Who is in the cohort.** The cohort is Phase 2 programs with a disease and a single resolved human protein target. Left out are 392 programs with no disease (healthy-volunteer, basket or symptom trials; 6% advanced) and 1,452 without a single human protein target (9%), so the cohort's base rate is higher than Section 1's.


### Which evidence translates

The plan registered fifteen rules a sponsor could apply at Phase 2 entry, but they are not fifteen ideas: several are narrower versions of another (every program with a mouse model pointing the drug's way also has a mouse model of the disease), so a flat screen counts the same programs more than once. The rules are therefore grouped by the kind of evidence behind them. Each kind is tested once against programs without it, with a Holm correction across the 6 preclinical kinds that could be tested; the benchmark, an approved drug on the target for a related disease, is shown beside them but is clinical precedent, not preclinical evidence. Each more specific version is then tested only against the rest of its own kind, with a Holm correction across the 10 that could be tested. This grouping departs from the plan; the registered screen is in the appendix.

The figure sets each kind beside Section 2's measure for the same evidence: relative success in reaching approval from any phase, over the same entry years.

![Each kind of evidence and its narrower versions: relative success in reaching approval from any phase (left), and the adjusted risk ratio of advancing from Phase 2 within four years (right)](report/output/figures/evidence_translates.png)

**Three kinds of preclinical evidence predict.** Phase 2 programs whose target had germline genetic evidence for the disease advanced 1.94 times as often as programs without it (1.55–2.41; Holm-corrected p < 0.001). Somatic drivers in oncology (1.60, 1.16–2.20) and animal models of the disease (1.43, 1.17–1.76) also survive the correction, with smaller effects. Reactome pathways (1.39) point the same way but do not, and expression (1.02) and target liabilities (1.02) carry nothing. The benchmark is stronger than any preclinical kind (2.13, 1.73–2.62).

**Being more specific does not help.** No narrower version beats the rest of its own kind. Among programs with germline genetics, strong GWAS evidence (0.69), Mendelian evidence in a non-hereditary disease (1.13) and genetics pointing the same way as the drug (1.06) advanced about as often as the rest. Among programs with an animal model, a close phenotype match (1.06) or a model pointing the drug's way (1.02) added nothing, nor did a somatic driver matching the drug among oncology programs with a driver (1.06). Protective loss of function plus an inhibitor covered 30 programs, too few targets to test.

**Known only after entry.** Cancer cell-line CRISPR screens and DepMap's list of essential genes were first published in 2019, after every program in the window had entered Phase 2, so no sponsor could have used them. Scored on today's data, as hindsight, a screen hit went with advancing (1.93, 1.38–2.72; 186 programs) and an essential target with not advancing (0.56, 0.37–0.86); both partly reflect what the screens learned from drugs that had already succeeded or failed.


* **Human genetics.** Mendelian and ClinVar evidence for the disease (2.00; top-tier curation 2.21) and GWAS (1.35) both carry the signal. Within GWAS, the locus-to-gene score did not grade it: the best score at 0.8 or above gives 1.04, 0.5–0.8 gives 0.98 and below 0.5 gives 2.02, each from a few dozen programs. Most GWAS rows in Open Targets are on measurement traits (LDL cholesterol, blood pressure, body-mass index) with no MONDO disease; they count as germline evidence on the target but cannot match a disease, so genetics for the disease is undercounted when it was found through a trait. Gene burden results start in 2019, too late for these cohorts.
* **Somatic drivers.** In oncology, a somatic driver for the tumour raised the chance of advancing (1.60, 1.16–2.20); requiring the driver's direction to match the drug's did not sharpen it (1.46). Germline genetics for the tumour type was the stronger signal (2.18), carried by well-validated targets such as EGFR, ERBB2 and ESR1.
* **Mouse models.** Literature-curated (MGI) mouse models of the disease gave 1.43 (1.16–1.76), and a top-quartile phenotype match 1.41. Each MGI model is dated by its first paper, and each knockout from the IMPC consortia by the first IMPC data release with calls for it (2015 at the earliest).
* **Expression and pathways.** Differential expression in the disease carried nothing (1.02; outside oncology 0.53). Reactome pathway evidence gave 1.39 from 106 programs, most of them in hereditary diseases, which Reactome curates.
* **Clinical precedent.** An FDA-approved drug on the target for a related disease (Lin similarity ≥ 0.5) was the strongest single predictor (2.13) and was present for 45% of the programs that advanced.
* **Target liabilities.** Loss-of-function intolerance (1.02) and lethality of the mouse knockout (0.98) made no difference. Essentiality across cell lines could not be known before entry for any program in the window (above).

**What the evidence leaves out.** Of the 689 Phase 2 programs that advanced, 20% had germline genetics for the disease, 46% had any of the disease-specific evidence families, and 35% had neither such evidence nor an approved drug on the target for a related disease.


### By endpoint

![Endpoint classes](report/output/figures/s3_endpoints.png)

Across 5,441 randomised industry efficacy trials, 47% missed their governing primary endpoint. Regulatory surrogates were missed least (23%); outside oncology, exploratory biomarkers (69%) and hard outcomes (52%) were missed most, and oncology's response and survival endpoints as often.

In trials with registry-posted results since FDAAA, genetic support for the disease lowered the chance of missing a regulatory surrogate (risk ratio 0.45), but across all readable trials, including those whose result was read from a paper, it did not (1.00). Clinician-rated scales (0.81, 0.65–1.01), objective physiology (0.93) and disease events (0.90) point towards fewer misses with intervals reaching 1; exploratory biomarkers (1.19) and oncology's response and progression endpoints show no benefit. Too few genetically supported trials had patient-reported, hard-outcome or overall-survival primaries to estimate. The endpoint a trial is judged on does not, on this evidence, decide whether genetic support helps.

At the program level, classifying each Phase 2 program by the endpoint of its first randomised Phase 2 efficacy trial (started within a year of entry and before it advanced), genetic support gives 2.10 (1.39–3.17; 686 programs) where that endpoint was proximal and 1.44 (0.85–2.42; 1,270) where it was intermediate; distal-endpoint and oncology programs had too few genetically supported targets to estimate.

The endpoint classifier read each trial's registered primary outcomes without the drug. In an audit of 40 trials stratified by class, it picked the governing outcome correctly in 40 and the class in 39. Not knowing the drug, it cannot apply the codebook's drug-specific rules: FEV1 is a regulatory surrogate only for bronchodilators, and target engagement means the drug's own target. Trials still in follow-up that have posted results have no outcome label yet and are not counted (78, against 5,441 in the analysis).


### Direction of effect

A drug that lowers its target's function should help when loss of function protects against the disease or gain of function causes it, and harm or do nothing when loss of function causes it. Open Targets' direction fields cannot test this: they label each variant from its predicted consequence, so the few truncating ClinVar variants listed for PCSK9 in hypercholesterolaemia, MYH7 in hypertrophic cardiomyopathy or TTR in amyloidosis make these gain-of-function diseases read as loss of function; their many pathogenic missense variants carry no direction at all.

We therefore had an LLM state, for every target and disease with germline evidence, without being told any drug, whether disease-causing variants lower or raise the gene's function, whether protective variants are known, and the year each was first shown for that disease. Where Gene2Phenotype records an absent gene product, the label was loss of function in 55 of 58 pairs and gain of function in 0. A spot check of an earlier version of the labels found somatic cancer mutations counted as germline and some years taken from another disease; the final prompt rules out both.

Sponsors almost never develop against an established mechanism. Of the Phase 2 programs with genetic support, 251 acted in the direction the genetics favoured, 8 against it, and 167 had genetics without an established direction by entry. Concordant programs advanced at 28% and undirected ones at 27%: once there is genetic support, knowing its direction did not pick winners among the programs sponsors chose to run, and the discordant group is too small to show whether going against the genetics fails. Protective loss of function plus a drug that lowers function, the PCSK9 pattern, covered 47 Phase 2 programs on 19 targets, which advanced as often as others (1.17, 0.68–2.02).

Mouse models were treated the same way: for each model, without the drug, whether it lowers or raises the gene's function and whether its phenotypes resemble the disease or its opposite. A model pointing the drug's way (a knockout protected from the disease, for an inhibitor) gave 1.44 (1.11–1.86) against programs with no oriented model, a model pointing the other way 1.38, and nothing once genetic support is accounted for (1.12). Among Phase 3 programs a concordant model went with approval within four years (1.79, 1.22–2.63), one of many comparisons made after the plan.


### Verified case studies

We checked 13 cases on 11 programs, picked at random for the rules that held up best, against registry records, company filings, papers and FDA documents; the protocol is in the appendix.

The recorded outcome was right for 11 of 11 programs. In each of the 0 errors the program advanced but was recorded as stopped: Phase 3 trials registered under another condition (sabizabulin's COVID-19 trial in patients at risk of ARDS; pegadricase's gout trials, against a program mapped to purine metabolism disease), Phase 3 trials run in China and never registered on ClinicalTrials.gov (pruxelutamide), and a Phase 3 not linked to the program (eneboparatide's CALYPSO). The evidence claim held for 8 of 13 cases and partly for 3 more (usually because the source matched a broader or neighbouring disease, or the earliest paper predated the row's date), and failed for 2. Of the 8 programs that did not advance, 6 failed for reasons that test the evidence's biology: engagement without benefit, the wrong population, a surrogate that did not carry over, or on-target toxicity; the rest stopped because exposure or engagement was never shown, on trial design, off-target toxicity or commercial grounds, which say nothing about whether the evidence was right, and a few are still progressing or unexplained.

![Verified cases by rule: whether the program advanced and, if not, whether its stop tested the evidence's biology](report/output/figures/s3_cases.png)

**When the model worked.** The clearest successes pair germline genetics that points in one direction with a drug that pushes the other way, in a disease defined close to that genetics.

* *Cardiac myosin inhibitors in hypertrophic cardiomyopathy*. Dominant missense mutations in *MYH7* that raise myosin activity were known to cause the disease from 1990. Mavacamten entered Phase 2 in 2016, started its pivotal Phase 3 (EXPLORER-HCM) in May 2018 and was approved in April 2022 for obstructive HCM ([label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2022/214998s000lbl.pdf)); aficamten followed the same path to approval.
* *APOL1 in kidney disease*. The G1 and G2 variants of *APOL1*, toxic gain of function, were linked to FSGS and kidney failure in people of African ancestry in 2010. Inaxaplin, an APOL1 channel inhibitor, cut proteinuria by about half in a Phase 2a restricted to carriers of two risk variants and moved into an adaptive Phase 2/3 (AMPLITUDE) in 2022 ([NEJM 2023](https://pubmed.ncbi.nlm.nih.gov/36920755/)).
* *Amyloid in Alzheimer's disease*. Mendelian *APP* mutations underlie the amyloid hypothesis; donanemab, which clears plaque, advanced to Phase 3 and approval.
* *Clinical precedent*. The benchmark's successes are next-in-class drugs on validated targets: third-generation EGFR inhibitors in lung cancer, HER2 antibodies and conjugates in biliary, gastric and breast cancer, and a PARP inhibitor moving from ovarian into prostate cancer.

**When it did not.** The verified failures show where the same kind of evidence stops predicting:

* *The target was hit and the disease did not move*. Evazarsen, an antisense drug against angiotensinogen, whose common variants were linked to essential hypertension in 1992, lowered plasma angiotensinogen by 55–67% in every trial but did not lower blood pressure in its Phase 2b (NCT04714320). Galegenimab inhibited HtrA1, the gene at one of the two strongest GWAS loci for age-related macular degeneration, but geographic atrophy grew no slower, slightly faster, than on sham (NCT03972709).
* *Protective genetics, the right direction, and still no benefit*. Loss-of-function *TYK2* variants protect against Crohn's disease, and the TYK2 inhibitor deucravacitinib, approved for psoriasis, missed both co-primary endpoints in Crohn's disease (LATTICE-CD, NCT03599622), with no dose response.
* *The molecule, not the target*. NGM621, an anti-C3 antibody for geographic atrophy, a disease in which gain-of-function *C3* variants raise risk, missed its primary endpoint (NCT04465955), while another C3 inhibitor, pegcetacoplan, was approved for the same disease.
* *The evidence was an artefact.* The GWAS evidence linking *CXCR2* to palmoplantar pustulosis came from a pleiotropy meta-analysis that Open Targets mapped to psoriasis at the study level; the locus carries no psoriasis signal in the paper itself. Vimnerixin, the CXCR2 antagonist, was stopped for hepatic safety findings.
* *Commercial stops after positive trials*. Several programs met their Phase 2 endpoints and stopped for portfolio reasons: brepocitinib in psoriasis and Crohn's disease, olamkicept in ulcerative colitis, dalcinonacog alfa in haemophilia B. They count as failures of the outcome, not of the evidence.

Every case, with its verdict and sources, is in the Appendix detail tab.


### What this means

* **Disease-specific human genetics is the evidence that carries over.** It is specific (it fades as the evidence moves away from the disease), it holds within a target, it does not come from hindsight, and it adds to clinical precedent. Its size, about twice the chance of reaching Phase 3 within four years, is in line with published estimates of what genetic support does for clinical success.
* **It is a filter, not a forecast.** Even with it, nearly three in four Phase 2 programs did not advance within four years, and most programs that did advance had no such evidence. Making the evidence more specific (stronger, Mendelian, or pointing the drug's way) did not pick better programs among those that already had it.
* **Its advantage is not tied to one kind of endpoint.** Genetically supported trials missed their primary endpoint somewhat less often on most endpoint classes, but no class stands out once all readable trials are counted.
* **Other preclinical evidence adds less at Phase 2.** Somatic drivers in oncology and animal models of the disease also predict, with smaller effects; Reactome pathways point the same way without surviving correction, and differential expression carries nothing. Neither the mouse model's direction nor the somatic driver's direction sharpens them.
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
| ClinicalTrials.gov API v2 | Every interventional drug or biological study: phases, status, dates, sponsor, arms, interventions, conditions, sites, why stopped, posted results | Snapshot 2026-10-20 (227,130 studies) |
| PubMed | Results papers linked to completed trials without posted results (registry RESULT/DERIVED references and the NCT secondary identifier) | Retrieved 2026-10-20 |
| Drugs@FDA, FDA approval letters, openFDA labels | NDA/BLA applications, submissions and action dates; 6,529 approved uses read from 2008–2026 approval letters; current Indications and Usage text | Retrieved October 2026 |
| CBER yearly approval pages, product pages and letters | 177 biologics applications (vaccines, blood products, cell and gene therapies) and their 2015–2025 approval actions, verified by an independent second enumeration | Retrieved October 2026 |
| FDA Global Substance Registration System | UNII substance identifiers and every registered name (official, common, code, brand) | 2026-08-04 |
| MONDO | Disease ontology and hierarchy | 2026-10-06 |
| Open Targets Platform | Target–disease associations by data source, with yearly score series | 26.09 |
| Open Targets Platform evidence | Every evidence row behind those associations for drug targets, with its date, direction of effect, confidence and source detail; mouse-model phenotypes | 26.09 |
| Mammalian Phenotype ontology | Mouse phenotype hierarchy (knockouts lethal before weaning) | Retrieved October 2026 |
| gnomAD | Loss-of-function constraint (LOEUF) | v4.1 |
| DepMap | Common-essential genes from CRISPR (Chronos) screens | Public 19Q4 to 24Q4, the last release of each year |
| HGNC | Approved human gene symbols with previous symbols and aliases | 2026-10-16 |
| ChEMBL | Drug mechanisms of action, as hints for target assignment | 37 |
| ChEMBL bioactivities | Potency, affinity and selectivity measurements of each entity's molecules, dated by the year of the paper, patent or dataset that reported them | 37 (138,229 measurements) |

Per-source detail (who compiles each source, what this analysis takes from it, raw response shape and a sample record) and the full Section 3 case table are in the Appendix detail tab.

### How LOA moves with each definition

| Cohort or definition | Phase 1 → 2 | Phase 2 → 3 | Phase 3 → approval | LOA (95% CI) |
| :---- | :---- | :---- | :---- | :---- |
| All programs | 54.8% | 28.4% | 34.9% | 5.4% (4.9–6.0) |
| Programs with a US-sited industry trial in the phase | 57.1% | 31.3% | 50.0% | 8.9% (8.0–9.9) |
| Entity not yet FDA-approved at phase entry | 54.6% | 27.0% | 35.8% | 5.3% (4.6–5.9) |
| Entity already FDA-approved for another disease | 55.8% | 37.9% | 32.5% | 6.9% (5.4–8.7) |
| Suspension lag 12 months | 53.9% | 27.7% | 34.2% | 5.1% (4.6–5.7) |
| Suspension lag 18 months | 54.2% | 28.0% | 34.6% | 5.2% (4.7–5.8) |
| Suspension lag 36 months | 56.0% | 29.2% | 36.2% | 5.9% (5.3–6.6) |
| Uncertain approvals counted as approved | 54.8% | 28.4% | 35.0% | 5.5% (4.9–6.1) |
| Shared trials mark entry for every program of the entity | 74.2% | 44.6% | 33.4% | 11.0% (9.4–12.8) |
| Including vaccines | 53.4% | 27.9% | 32.6% | 4.9% (4.3–5.4) |
| Phase entry 2015-2025 (many programs still running) | 54.6% | 33.8% | 38.1% | 7.0% (6.2–7.8) |
| Phase entry 2015-2025, developed in the US | 54.4% | 33.9% | 53.1% | 9.8% (8.6–11.0) |

### Change over time

Success rose across the window. Programs that entered a phase in 2008–2011 reached approval from Phase 1 4.1% of the time; those that entered in 2016–2019, 6.9% (7.3% and 10.0% for US-developed programs). The gain came in the later phases: Phase 2 success rose from 25.0% to 30.7% and Phase 3 from 28.4% to 42.4% (44.2% to 55.9% for US-developed programs), while Phase 1 success fell slightly, from 57.6% to 52.8%.

| Phase entry | Entities | Phase 1 → 2 | Phase 2 → 3 | Phase 3 → approval | LOA (95% CI) | US-developed: Phase 3 → approval | US-developed: LOA (95% CI) |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 2008–2011 | 2,756 | 57.6% | 25.0% | 28.4% | 4.1% (3.5–4.9) | 44.2% | 7.3% (6.0–8.7) |
| 2012–2015 | 2,884 | 54.8% | 29.4% | 33.4% | 5.4% (4.4–6.5) | 47.9% | 9.3% (7.7–11.1) |
| 2016–2019 | 3,645 | 52.8% | 30.7% | 42.4% | 6.9% (5.9–7.9) | 55.9% | 10.0% (8.4–11.6) |

Two features of the registry bear on these trends.

* **Phase 1 registration grew more complete.** US law has required registration of Phase 2 and 3 trials since late 2007 but exempts Phase 1, and journals require it only for trials that are published. Industry Phase 1 registrations grew through the window, partly because more programs were run and partly because more were registered. Programs that fail in an unregistered Phase 1 never enter the count, so the earlier Phase 1 rates may be the more flattering, and the slight fall in Phase 1 success may reflect registration rather than development.
* **Later entrants have had less time.** A program that entered a phase in 2008 has had eighteen years to resolve; one that entered in 2019, under seven. The share of programs still running rises in the latest years, most in Phase 3 (in parentheses below), so those years' rates rest on the programs that resolved first.

| Phase entry year | Phase 1 → 2 (share still running) | Phase 2 → 3 (share still running) | Phase 3 → approval (share still running) |
| :---- | :---- | :---- | :---- |
| 2008 | 56% (4%) | 23% (3%) | 25% (9%) |
| 2009 | 61% (5%) | 26% (2%) | 33% (6%) |
| 2010 | 59% (5%) | 25% (5%) | 25% (11%) |
| 2011 | 54% (6%) | 26% (3%) | 31% (11%) |
| 2012 | 52% (6%) | 26% (6%) | 35% (9%) |
| 2013 | 53% (5%) | 28% (6%) | 25% (11%) |
| 2014 | 59% (2%) | 32% (5%) | 36% (10%) |
| 2015 | 55% (10%) | 31% (9%) | 38% (13%) |
| 2016 | 52% (9%) | 30% (10%) | 45% (16%) |
| 2017 | 58% (9%) | 32% (12%) | 43% (22%) |
| 2018 | 50% (13%) | 28% (19%) | 37% (30%) |
| 2019 | 51% (16%) | 33% (18%) | 45% (32%) |


### How each label was made, and how good it is

Every judgement in this analysis is an LLM call (Claude) that reads the source record and returns a structured answer, stored with its prompt, input, model and code version. Disease mapping, entity resolution, trial purpose and roles, approvals, stop reasons, trial outcomes, modality, disease area and targets were all made this way, not with keyword rules. For each high-stakes label, a seeded random sample was re-derived independently by agents working from the primary sources (registry records, PubMed, Drugs@FDA, DailyMed, CBER pages) before they saw the stored answer. Agreement counts answers judged correct or defensibly different under the same rules.

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

Each error pattern these audits found was fixed at its source and the affected labels re-derived, not patched by hand: diseases MONDO has no exact term for now map to their nearest broader term; development codes resolve to UNII substances, and the same substance under two names is merged; scanned FDA letters are read by OCR; labelling-only supplements no longer count as approvals; stop reasons stated only in a trial's summary are read; publication-based outcomes use only the abstracts given; and approval dates account for older applications of the same drug. The disease-mapping, entity and approval figures above come from fresh samples drawn after those fixes; before them, disease mapping agreed 94% of the time, entity resolution 95%, and 8 of 25 dated first approvals were wrong. Remaining entity errors are scattered (a development code resolved to the wrong substance, a salt chosen over its parent) rather than systematic. Programs whose approval is judged "uncertain" (106 of 24,339 judgements) count as not approved; counting them as approved instead moves no rate by more than a tenth of a percentage point (sensitivity table). The approval audit's strata are those of the judgements it sampled; it was re-scored after the final rebuild against the auditors' own answers, and programs that are no longer development programs left the sample.

Two labels were also re-decided rather than re-derived. Trial purposes and roles, re-decided under a second prompt version, agree with the first on 98% and 97% of trials. Disease mapping, decided twice, chose the same MONDO term for 92% of conditions. ClinicalTrials.gov's own MeSH indexing is no substitute: its terms belong to a study rather than a condition, so only 43% of condition strings can be given one, and where both routes name a disease, MeSH carried to MONDO agrees with the mapping for 60% (24% broader, 11% another disease) and gives a disease to 520 conditions that are not diseases, such as healthy volunteers; a hand review of 20 disagreements favoured the mapping 6 times to MeSH's 1. Modality, disease area and targets were not audited. The Section 3 endpoint classes were audited on a seeded sample of trials, and the mechanism and mouse-model labels were spot-checked (Section 3).

### How stops were traced and efficacy failures classified

**Tracing the stops the registry does not explain.** Every Phase 1, 2 and 3 program that entered from 2008 to 2025 and stopped was traced (7,570 Phase 2 and 3 programs, 4,075 Phase 1); the report's figures use the 2008–2019 entries. Where the registry gives no usable reason, a model read the program's trials (records, posted results, linked papers) and signals of what happened next: whether the drug went on in other diseases, whether its sponsor started any trial afterwards, and whether drugs on the same target stopped at the same time. It then searched the web for company releases, SEC filings, pipeline updates, conference reports and trade news, with ClinicalTrials.gov excluded. It named a cause only where a source supported it, citing only pages its own searches returned, and separately gave a *likely* cause, its best inference from context, where no source says.

**How well the tracing does.** The same procedure was run on 133 stops whose registry does state a reason, drawn at random across causes, with the reason removed and ClinicalTrials.gov blocked. It named a sourced cause for 77% of them, and that cause matched the registry's for 69% (κ = 0.61); the likely cause matched for 62% (κ = 0.52). Accuracy differs by cause. Efficacy or exposure stops were recognised 62% of the time, and only 83% of the stops it called efficacy or exposure were such stops in the registry: safety stops were often read as efficacy (companies announce both as an unfavourable benefit–risk), and sponsor decisions and operational stops were confused with each other (76% and 44% recognised). The efficacy share after tracing is therefore an upper estimate, and safety is likely under-counted. The registry's stated reason is itself an imperfect reference, since a stated business reason can hide a failed readout. Stops with a stated reason are probably also easier to trace, so accuracy on the unexplained stops is likely lower. One independent check holds: of programs traced to an acquisition, merger, lost funding or closure, 65% had a sponsor that started no trial afterwards, against 26% of those traced to efficacy.

**Subcauses.** A second pass, without web search, read each safety, sponsor-decision, operational and positive-readout stop's stated reason or traced source and named the subcause it states or directly implies, or "not stated" where it says no more than the cause. A stop with no traced cause is described by what happened next, from the registry: whether its sponsor started any later trial, and whether the drug was approved or continued in another disease.

**Classifying efficacy failures.** The cohort is every Phase 2 and 3 program that entered in 2008–2019 and stopped for efficacy or for PK, dose or formulation: as the registry records it (1,587 efficacy, 16 PK), or as traced with a source from the stops the registry does not explain (589 efficacy, 23 PK). An exposure failure is the same biology as a failure to engage, so PK stops are broken down here rather than counted apart. For each of the 2,215 programs the model would label (102 more, mostly gene and cell therapies and live biotherapeutics, were refused), an LLM read an evidence bundle: the failed trial's record, posted results and papers, the drug's other trials and their outcomes, results posted by its Phase 1 trials, its FDA approvals, other drugs on the same target in the same or a related disease, and PubMed abstracts on the drug's human pharmacology and on the drug in that disease. It judged, for humans and at the doses tested, the three pillars of [Morgan et al. 2012](https://doi.org/10.1016/j.drudis.2011.12.020): exposure at the site of action, binding or engagement of the target, and the expected pathway effect. Engagement could also be inferred when the drug worked in another disease through the same target and tissue compartment at a comparable dose. It then said why efficacy failed, using only the bundle and citing the sources it used. The categories and checks were fixed before any program was labelled. Where the bundle held no human evidence of engagement (40% of programs), a second pass, added after the first results, gave the same model the same bundle and the web: it searched full-text papers, conference reports, FDA and EMA reviews and company releases for human pharmacology, and could cite only pages its own searches returned. It decided 181 of the 857 programs it searched; the figures below use those labels.

Variants of the not-engaged share:

| Variant | Programs | Mechanism tested | Not engaged, of tested (95% CI) | No engagement data |
| :---- | :---- | :---- | :---- | :---- |
| All (Phase 2 and 3) | 2,215 | 1,258 | 18% (16–20) | 36% |
| Phase 2 | 1,705 | 952 | 18% (15–21) | 38% |
| Phase 3 | 510 | 306 | 19% (14–24) | 30% |
| Efficacy recorded in the registry | 1,587 | 975 | 17% (14–19) | 31% |
| Traced from unexplained stops | 612 | 273 | 22% (17–28) | 49% |
| Outside oncology | 1,650 | 884 | 18% (15–20) | 38% |
| Oncology | 565 | 374 | 19% (15–24) | 28% |
| Sponsor-stated efficacy reason | 372 | 255 | 20% (15–25) | 29% |
| Primary endpoint missed | 1,215 | 720 | 15% (13–18) | 31% |
| Direct pillar evidence only (inferred engagement counted as unknown) | 2,215 | 913 | 25% (22–28) | 51% |
| Engaged only if shown before the index trial | 2,215 | 769 | 30% (26–33) | 59% |
| One program per entity | 1,603 | 856 | 19% (16–21) | 39% |
| High or medium confidence | 1,386 | 909 | 13% (11–16) | 27% |
| Bundle only (before the web search) | 2,215 | 1,020 | 19% (16–22) | 40% |
| Entries 2015-2025 | 1,365 | 755 | 15% (13–19) | 36% |
| All traced entries 2008-2025 | 2,681 | 1,500 | 17% (15–19) | 36% |

**Checks.** A second model, given the same bundles and asked the pillar questions one at a time before choosing a category, relabelled a seeded random sample of 150 programs (136 with a validated label from both): it agreed on the not-engaged / engaged / other split for 69% (κ = 0.48) and on whether the target was engaged for 79%. Separately, agents with web access researched a seeded random sample of 66 programs from scratch (publications, conference reports, company releases), without seeing our labels (65 also have one of ours): they agreed on the three-way split for 82% (κ = 0.67) and on the group for 86% of the programs our labelling decided; they never called engaged a program our labelling called not engaged, or the reverse (0 contradictions). Of the 16 adjudicated programs whose bundle held no engagement data, the web search and the outside researchers both decided 4 and agreed on 75% of them; the search never decided one the researchers could not, and the researchers decided 2 that the search left open (1 of them not engaged). On their own, they found 5 failures to engage among 36 programs whose mechanism they could judge (14%). The pre-registered construct checks, on data the labels do not use, point one way or nowhere. Programs whose exposure or engagement was shown too low had germline genetic support for the disease more often than those engaged without benefit (13% against 7%, p = 0.04, 111 programs shown not engaged), as expected if engaged failures more often test a target the disease does not depend on. The two groups did not differ in whether other drugs on their target failed (52% against 55%) or advanced (48% against 50%) in the disease. A check added after the plan asked whether drugs that failed to engage were simply weaker, using the drug's potency at its primary target from laboratory assays published by the year before phase entry (ChEMBL; Section 2 describes the measurements). The data do not show it: 20% of programs shown not engaged and 23% of those engaged without benefit had such a measurement; among them the median best potency was 7.99 against 8.22 on the negative-log scale (p = 0.16, Mann–Whitney), and 94% against 87% reached 100 nM or better (p = 0.70). Only 18 not-engaged programs had a measurement, so a modest difference could be missed; but most drugs that failed to engage in patients had been potent in the assay, which points to exposure, dose or tissue access rather than a weak molecule.

**What the registry records.** Each suspended program takes one reason from the industry trials of the phase it stopped in, in this order: an efficacy reason stated by the sponsor, a primary endpoint missed in posted or published results, a safety signal, a pharmacokinetic or formulation problem, an explicit business or strategic reason, a bare "sponsor decision", an enrollment, operational or regulatory reason, a positive primary readout without advancement, another stated reason, posted results with no stated reason or readable endpoint, and finally neither a reason nor a result.

| Reason | Phase 1 | Phase 2 | Phase 3 |
| :---- | :---- | :---- | :---- |
| PK, dose or formulation | 1% (40) | 0% (17) | 0% (1) |
| business or strategic (explicit) | 8% (238) | 5% (222) | 3% (46) |
| completed, no results posted, no reason stated | 57% (1,690) | 27% (1,227) | 23% (320) |
| efficacy: primary endpoint not met | 0% (10) | 22% (975) | 21% (293) |
| efficacy: stated | 2% (70) | 5% (241) | 10% (137) |
| enrollment, operational or regulatory | 2% (66) | 5% (227) | 3% (49) |
| other stated reason | 0% (14) | 0% (16) | 1% (12) |
| positive readout, not advanced | 0% (11) | 10% (448) | 19% (273) |
| results posted, no reason stated, endpoint not assessable | 13% (390) | 11% (507) | 5% (64) |
| safety | 3% (77) | 3% (114) | 4% (51) |
| sponsor decision, unspecified | 3% (83) | 2% (101) | 1% (21) |
| stopped, no reason stated | 9% (279) | 9% (401) | 10% (135) |

![Phase 1, 2 and 3 stops among 2008–2019 entries, excluding programs whose development continued: the cause the ClinicalTrials.gov reason gives (efficacy and PK, dose or formulation as efficacy or exposure; business and bare sponsor decisions as sponsor decision; other stated reasons and no reason as unknown), and the cause after tracing, counting likely causes](report/output/figures/stop_causes_registered_vs_traced.png)

The registry rarely says why a program stopped. In Phase 1, 66% of stopped programs left neither a stated reason nor a result, which is expected: Phase 1 trials seldom post results and companies seldom explain pausing early assets. In Phase 2 and Phase 3 the share without a reason falls to 36% and 32%. Efficacy is the recorded reason for 27% of programs that stopped in Phase 2 and 31% of those that stopped in Phase 3: the sponsor said so, or the posted or published primary endpoint was missed. Safety accounts for 3% and 4%: among Phase 2 and Phase 3 stops with an efficacy or safety reason, safety is 9% and 11%, against about 32% in Harrison (2016), whose 2013–2015 failures with a disclosed reason were 24% safety and 52% efficacy. Either registry records under-report safety stops, or company disclosures over-represent them.

At the level of individual trials, the 4,390 industry trials started in 2008–2019 that stopped early or were withdrawn with a reason give: an explicit business, portfolio or competitive reason 27%, a bare "sponsor decision" 13%, efficacy 18%, enrollment or operations 19% and safety 7%. The draft's single 44% "commercial or strategic" category mixed these two kinds of statement; a "sponsor decision" with no reason may or may not hide an efficacy result, and the record cannot tell. No study has measured how often a stated business reason hides an efficacy or safety failure. Where a registry gives a reason it mostly agrees with the trial's publication (53 of 57 in [Alturki et al. 2017](https://doi.org/10.1016/j.jclinepi.2016.08.011)); the usual gap is a missing reason. Analysts who also read company filings, press releases and regulator records attribute 57% of drug failures in pivotal trials to efficacy, 17% to safety and 22% to commercial reasons ([Hwang et al. 2016](https://doi.org/10.1001/jamainternmed.2016.6008)), so the efficacy and safety shares here are a floor.

Finally, 19% of Phase 3 programs that stopped short of FDA approval had met their primary endpoint. In a sample we read, most of them were approved outside the US (Japan, China, Korea, Russia) or received a complete response letter from the FDA: a positive Phase 3 readout is necessary but not sufficient for US approval.



### How the evidence is scored and modelled (Section 2)

**Evidence.** Each program's primary targets are resolved by an LLM from the entity's mechanism records and trial descriptions. Each program is scored for the evidence its targets had **for the program's disease** in Open Targets Platform 26.09, **as of the year before the program entered the phase**. A target–disease association counts for the program's disease when the evidence disease is the same MONDO term, a subtype of it, or similar to it (Lin similarity ≥ 0.8, the criterion Minikel et al. used). Each association's score is rebuilt year by year from its evidence items, each dated by when it became known (ClinVar records by their creation rather than their latest review, IMPC knockouts by their first data release, Project Score screens by the first Open Targets release that listed them), so evidence is taken as it stood before phase entry, not as it stands today.

Evidence lines:

* **Human germline genetics:** GWAS credible sets (with locus-to-gene scores), gene burden tests, ClinVar, Genomics England PanelApp, Orphanet, Gene2Phenotype, ClinGen and UniProt; split into GWAS and rare-variant/Mendelian sources.
* **Somatic drivers:** COSMIC Cancer Gene Census, IntOGen and ClinVar somatic.
* **Mouse models:** IMPC phenotypes. **Expression:** differential expression in the disease (Expression Atlas). **Pathways:** Reactome.
* **Cell screens:** genome-wide CRISPR screens, which switch off (or, in neurons, also switch on) each gene in turn in cultured human cells and record whether the cells grow or change. They are functional genomics, not compound assays: they show the cells depend on the gene, not that any molecule works. *Cancer cell lines* come from Project Score (Wellcome Sanger Institute; 324 lines in [Behan et al. 2019](https://doi.org/10.1038/s41586-019-1103-9), extended in [Pacini et al. 2024](https://pubmed.ncbi.nlm.nih.gov/38215750/)), which names a gene a priority target for a cancer type when knocking it out stops the growth of that type's lines, scoring it higher when the dependency is strong, shared across the type's lines and tied to a genomic marker. *Neurons* come from CRISPRbrain, screens in neurons and microglia made from human stem cells that record survival or a cell phenotype.
* **Target liabilities**, properties of the target rather than evidence for the disease: essential in most cell lines (on the latest yearly DepMap common-essential list from before phase entry; DepMap first published such a list in 2019, so earlier entrants are never flagged) and intolerant of loss of function (gnomAD v4.1 LOEUF < 0.35, from the current release).
* **Drug pharmacology**, assays of the drug itself rather than evidence for the disease, from ChEMBL, EMBL-EBI's database of bioactivity measurements that curators extract from journal papers and patents, plus screening datasets deposited directly. Each measurement is a concentration at which the drug has half its maximal effect (IC50 when it inhibits, EC50 when it activates, AC50 or "potency" in screens) or an affinity constant (Ki, Kd, Kb), converted to pChEMBL, the negative log of the molar value (7 is 100 nM, 8 is 10 nM, higher is more potent). A *binding* assay measures how tightly the drug holds its target; a *functional* assay measures what it does to the target's activity. A *biochemical* assay uses purified protein or membranes; a *cell-based* assay measures the drug acting on its target in living cells, such as a calcium or cAMP readout for a receptor. Every form of the drug (salts and the parent compound) is pooled, values ChEMBL flags as doubtful or as repeat citations are dropped, and each measurement counts from the year of the paper, patent or dataset that reported it, so only measurements published by the year before phase entry are used. A target's potency is the median of its measurements of one kind (Ki, IC50, ...), and the drug's best potency is the highest of these medians at its primary targets (a protein complex or family containing a primary target counts). The lines: any measurement at a primary target; best potency 100 nM or better; 10 nM or better; functional potency measured in cells; and at least 100-fold selectivity, the best potency at a primary target at least 2 log units above the best at any other single human protein measured (programs with no off-target measurement do not count as selective). These describe the molecule, not whether the target matters in the disease, and programs of drugs already approved or long studied carry many more published measurements, so the joint model's adjustment for novelty matters here.

Each entity is matched to its ChEMBL molecules by the first of three routes that succeeds: the ChEMBL id recorded for one of its intervention names; the standard InChIKey of its UNII substance equal to a ChEMBL compound's; or an official, common or code name registered for its UNII equal, ignoring case and punctuation, to the preferred name or a synonym of exactly one ChEMBL molecule (a name two molecules share is not used). 7,307 of the 17,770 entities with a development program matched. A hand check of 12 randomly chosen name matches against ChEMBL's records found 12 correct (for example agatolimod sodium to agatolimod, ergoloid mesylates to ergoloid). Matched antibodies and proteins still carry almost no potency measurements at their targets: ChEMBL curates potency mostly from small-molecule chemistry.

| Modality | Entities | By a ChEMBL id of one of its names | By its UNII structure (InChIKey) | By a registered UNII name | Not matched |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Small molecule | 8,883 | 2,338 | 2,413 | 225 | 3,907 |
| Vaccine | 1,778 | 39 | 1 | 55 | 1,683 |
| Monoclonal antibody | 1,716 | 550 | 0 | 269 | 897 |
| Protein | 884 | 234 | 1 | 185 | 464 |
| Other cell therapy | 704 | 2 | 1 | 50 | 651 |
| Other | 593 | 9 | 4 | 81 | 499 |
| Peptide | 572 | 114 | 54 | 106 | 298 |
| Multispecific antibody | 559 | 41 | 0 | 99 | 419 |
| Antibody–drug conjugate | 548 | 73 | 0 | 72 | 403 |
| CAR-T | 406 | 7 | 0 | 23 | 376 |
| Gene therapy | 316 | 14 | 0 | 49 | 253 |
| siRNA / RNAi | 192 | 16 | 0 | 20 | 156 |
| Antisense oligonucleotide | 178 | 33 | 0 | 45 | 100 |
| Radioligand | 170 | 13 | 9 | 19 | 129 |
| Microbiome or live biotherapeutic | 124 | 0 | 0 | 4 | 120 |
| Other oligonucleotide | 74 | 16 | 0 | 19 | 39 |
| mRNA (non-vaccine) | 40 | 0 | 0 | 3 | 37 |
| Unknown | 33 | 0 | 0 | 1 | 32 |

Sources that encode clinical outcomes or literature co-mention (ChEMBL clinical precedence, Europe PMC) are not used.

**Relative success.** The 95% intervals resample primary-target sets (an entity's primary targets taken together), since programs on the same targets are not independent.

**Adjusted relative risks.** The joint table comes from one modified Poisson model per phase containing every evidence line together with disease area, modality, entity novelty and entry period, with standard errors clustered by primary-target set.

**Prediction.** Programs entering Phase 1 in 2008–2016 were followed for ten years, with the Open Targets evidence lines and novelty taken as of entry (loss-of-function constraint comes from the current gnomAD release). Logistic models were fitted on disease area, modality, novelty and entry year alone, and with the evidence lines added. Performance is measured on held-out primary-target sets (out-of-fold predictions averaged over 20 repetitions of 5-fold cross-validation grouped by primary-target set and stratified by outcome; a single split moves the AUC by several points) and on a temporal split (trained on 2008–2012 entries, tested on 2013–2016). In the line-removal table, human genetics means GWAS and rare-variant evidence removed together; lines carried by fewer than 100 programs are not modelled; intervals are a paired bootstrap over target sets.


### Design of the translation analysis (Section 3)

* **Cohort and outcome.** Programs on a human protein target that entered Phase 2 from 2008-01-01 to 2019-12-31 (4,596 programs on 1,158 primary-target sets). Each has at least four years of follow-up before the 24-month inactivity cutoff, so the outcome needs no inferred suspension: a program *advanced* if a Phase 3 trial of its own started, or the FDA approved it for the disease, within four years of entering Phase 2 (15.0% did). The same is done for Phase 1 entrants (a negative control: genetics should matter little for safety and dosing studies) and Phase 3 entrants (approval within four years).
* **Evidence.** Every Open Targets 26.09 evidence row for the program's primary targets, each dated by the year it became known (ClinVar records by their creation, IMPC knockouts by their first data release, otherwise the row's own publication), frozen at the year before entry and matched to the program's disease on MONDO: the same term, a subtype, or Lin similarity ≥ 0.8 (*genetics for the disease*); a disease at Lin 0.5–0.8 only (*genetics for a related disease*); germline evidence only for unrelated diseases; or none. Evidence is split by family and strength (the best GWAS locus-to-gene score, ≥ 0.8, 0.5–0.8 or below; ClinVar pathogenic with multiple submitters or expert review, ClinGen or Gene2Phenotype definitive or strong, PanelApp green; mouse phenotype match in the top quartile), and mouse models are split into IMPC high-throughput knockouts and literature-curated MGI models.
* **Regimes.** Oncology; *hereditary* (the disease is a MONDO hereditary disease and the target has curated Mendelian evidence for it); and every other disease (*non-oncology*, the regime of the headline hypothesis).
* **Models.** Modified Poisson regression (risk ratios) with standard errors clustered by primary-target set, adjusted for disease area, modality, entity novelty, entry period and target precedent (an FDA-approved entity on the target before entry). The seven confirmatory hypotheses are Holm-corrected together.
* **Trials.** Randomised industry Phase 2/3 trials started in 2008–2019 whose governing primary endpoint measures efficacy and whose result is readable (5,441 trials; an LLM classified each trial's governing primary endpoint from its registry entry, without the drug's name). Outcome: primary endpoint not met (a mixed result counts as not met).

**Registered rule screen.** The plan tested fifteen rules on their own, each against all other programs, with a split of target sets in place of a correction for multiple testing. Because the rules overlap and the split halves the data, the body of the report groups them by kind of evidence instead (a change from the plan). The registered screen, as run: target sets were split 60/40 at random; a rule counts as *particularly predictive* when, on the discovery targets, its risk ratio's 90% bootstrap lower bound is above 1.3, and, on the held-out targets, its risk ratio is at least 1.2 with a one-sided 95% lower bound above 1, and it stays at least 1.2 without its most influential target.

| Rule applied at Phase 2 entry | Regime | Programs (targets) | Advanced | Share of all that advanced | Adjusted risk ratio (95% CI) | Risk ratio, discovery targets (90% CI) | Risk ratio, held-out targets (90% CI) | Meets the bar |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Protective loss-of-function burden + drug that lowers function | All | 0 (0) | – | 0% | – | – | – | not testable |
| Mendelian evidence + drug that raises function or replaces the gene | Hereditary | 95 (49) | 32% | 75% | 1.74 (0.78–3.86) | 1.96 (1.10–4.13) | 1.22 (0.63–3.27) | no |
| Mendelian evidence for a non-hereditary disease | Non-oncology | 114 (65) | 26% | 7% | 1.62 (1.18–2.22) | 1.48 (0.87–2.11) | 3.09 (1.84–4.45) | no |
| GWAS, locus-to-gene ≥ 0.8 | All | 59 (36) | 17% | 1% | 1.04 (0.59–1.83) | 0.54 (0.00–1.11) | 1.71 (0.88–2.55) | no |
| GWAS and rare-variant evidence for the same disease | All | 27 (16) | 11% | 0% | 0.65 (0.28–1.51) | 0.74 (0.00–1.48) | 0.76 (0.00–1.44) | no |
| Somatic driver matching the drug + drug that lowers function | Oncology | 394 (87) | 22% | 35% | 1.49 (1.07–2.09) | 1.63 (1.08–2.44) | 2.88 (1.51–5.22) | no |
| IMPC knockout matching the disease, top quartile | All | 17 (7) | 18% | 0% | – | 0.97 (0.00–1.38) | – | no |
| Literature mouse model of the disease | All | 943 (413) | 20% | 28% | 1.43 (1.16–1.76) | 1.57 (1.24–1.98) | 1.38 (1.06–1.81) | no |
| Expression up in disease + drug that lowers function | All | 247 (130) | 14% | 5% | 0.90 (0.59–1.37) | 0.71 (0.44–1.06) | 1.41 (0.70–2.12) | no |
| Reactome pathway | All | 106 (41) | 23% | 3% | 1.39 (0.91–2.11) | 1.10 (0.58–1.72) | 2.38 (1.56–3.92) | no |
| Target liability + drug that lowers function | All | 1,791 (420) | 15% | 38% | 1.02 (0.83–1.26) | 0.98 (0.77–1.22) | 0.97 (0.74–1.29) | no |
| Approved drug on the target, related disease (Lin ≥ 0.5) | All | 1,234 (342) | 25% | 45% | 2.13 (1.73–2.62) | 2.10 (1.80–2.46) | 2.37 (1.81–3.07) | **predictive** |
| Protective loss of function + drug that lowers function (added after the plan) | All | 47 (19) | 19% | 1% | 1.17 (0.68–2.02) | 1.31 (0.45–2.23) | 1.32 (0.49–2.44) | no |
| Germline mechanism concordant with the drug (added after the plan) | All | 251 (122) | 28% | 10% | 1.93 (1.41–2.64) | 1.98 (1.30–2.65) | 2.06 (1.43–2.84) | **predictive** |
| Mouse model direction concordant with the drug (added after the plan) | All | 334 (152) | 22% | 11% | 1.41 (1.10–1.81) | 1.59 (1.20–2.03) | 1.44 (0.87–2.05) | no |

Of the registered rules only the benchmark met the bar (held-out risk ratio 2.37); a germline mechanism concordant with the drug, added after the plan, also met it (held-out 2.06). Mendelian evidence for a non-hereditary disease came closest among the registered rules (held-out 3.09, discovery lower bound 0.87).

**Case studies.** The plan's protocol picked cases for the rules that met the bar and, beyond the plan, for every rule whose adjusted risk ratio's lower bound is above 1 (Mendelian evidence for a non-hereditary disease, a somatic driver matching the drug, a literature mouse model of the disease and a mouse model pointing the drug's way): four successes and four failures at random, up to two programs of each of the three most influential targets, and up to six programs that stopped after a randomised trial missed its primary endpoint (the plan asked for all such programs; the cap keeps every case checkable against primary sources). For each program one agent established the outcome from registry records, company filings, papers and FDA documents without seeing the evidence, another checked the evidence claim without seeing the outcome, a second coder classified each failure independently, and a third agent adjudicated any disagreement.


### Limitations

* **Registry programs are not Biomedtracker programs.** BIO counts transitions that analysts record for programs companies disclose; this report counts programs from registered trials. Trials registered only outside ClinicalTrials.gov (ChiCTR, EU CTR, CTIS) are missing, so programs developed there look suspended. Restricting to programs with a US site removes most of the difference.
* **Suspension is inferred from inactivity.** A program counts as suspended when none of its trials has been active within 24 months. The rates move with that window (sensitivity table); BIO dates suspensions from company disclosures instead.
* **Section 1 stops at 2019 entries.** Programs that entered a phase in 2020–2025 are largely still running, and the success rate counts only resolved programs, so the headline takes entries from 2008–2019, each with at least six years to resolve. Entries from 2015–2025 are shown as a sensitivity.
* **Older entrants are recorded less completely.** Phase 1 trials need not be registered, and registration grew more complete over the window. CBER approvals (vaccines, blood products, cell and gene therapies) are read from letters only from 2015, and earlier ones are dated from current labels.
* **Outcome is FDA approval only.** Approvals elsewhere count as no approval.
* **Symptom and procedure indications without a MONDO term** (pain, cough, contraception; about 3% of trials) are grouped in each entity's disease-unspecified program, followed through Phase 2 but not to approval.
* **Most stopped programs give no reason.** Reasons come from the registry's why-stopped field, posted results and abstracts of results papers. Published results favour positive findings, and a missing reason is reported as such, not inferred. A vague reason ("sponsor decision", "business reasons") may hide an efficacy or safety result; reasons were not filled in from press releases, company filings or pipeline updates, so efficacy and safety shares are lower bounds.
* **The model declines some products.** Claude declines to classify some products derived from pathogens, toxins or live bacterial and viral vectors (botulinum and plague vaccines, oncolytic viruses, engineered bacteria) on every attempt: 142 entities have no resolved target and 37 no modality, so they fall out of Section 2 and the modality strata.
* **Constraint is current; essentiality starts in 2019.** gnomAD v4.1 constraint comes from that release, not as of phase entry. The common-essential flag uses the last DepMap release of each year from 2019, when DepMap first published the list; programs that entered a phase before 2020 are never flagged, so the flag is a lower bound for them.
* **Evidence as of phase entry undercounts.** The yearly series count only dated evidence. Cancer Gene Census, Orphanet, UniProt, Reactome and PanelApp entries without a publication, and IMPC knockouts first released after 2024, have no date; a sensitivity uses the 2026 scores instead.
* **Section 3 rests on labels made for it.** The trial endpoint class, the germline mechanism of each target in each disease and the orientation of each mouse model were classified by an LLM without the drug's name. The endpoint classifier was audited on 40 trials (39 classes and 40 governing outcomes right); the mechanism and mouse labels were spot-checked, and the errors found there led to a revised prompt rather than hand corrections.
* **Some evidence is dated approximately.** Open Targets dates ClinVar records by their latest review; here each record takes the year it was created, read off its accession number, so a variant first submitted as uncertain and reclassified pathogenic later counts from its first submission. IMPC knockouts take the year of the first IMPC data release with calls for the allele (none before 2015) and MGI models the year of their first paper. Open Targets dates every Project Score row 2024, from the re-analysis that now supplies it; here each target–cancer pair takes the year of the first Open Targets release that listed it (72 pairs from 2019, 175 from 2024). Gene-burden results start in 2019, and GWAS on measurement traits cannot be matched to a disease, so these lines are undercounted in Section 3.
* **Section 3's post-hoc analyses are exploratory.** The direction analyses and the three direction rules were added after the plan was committed, once their labels existed; their intervals are not corrected for the number of comparisons.


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
