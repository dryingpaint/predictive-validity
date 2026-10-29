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

This report rebuilds both questions from primary records. We took every interventional drug or biological study on ClinicalTrials.gov (222,915 studies, snapshot of 2026-10-20), resolved each intervention to the molecular entity it contains and each condition to a MONDO disease, and joined them to every FDA approval we could document: Drugs@FDA applications, 6,529 approved uses read from 2008–2026 approval letters, current labels, and 177 CBER biologics applications rebuilt from the agency's yearly pages and letters. The unit throughout is a *development program*: one molecular entity developed for one indication. An entity counts toward a program only in trials where it is the investigational agent, not a comparator or background therapy.

The report has three parts:

1. **Industry failure modes.** Phase transitions, likelihood of approval (LOA) and the reasons programs stop, for programs that entered each phase in 2008–2019: an updated companion to BIO's *Clinical Development Success Rates 2011–2020*.
2. **Predictive power of preclinical evidence.** For programs aimed at a human protein target, whether the target had human genetic, somatic, animal-model, expression, pathway or functional-screen evidence for the program's disease, as known before the program entered the phase, and how much each line changes the chance of approval.
3. **What translates to the clinic.** Which kinds of evidence, at what strength and in which direction, predicted that a Phase 2 program would advance; on which trial endpoints the advantage shows; and which decision rules applied at Phase 2 entry predicted well enough to call a model, with verified case studies.

Every classification in the pipeline was made by an LLM reading the source record and recorded with its prompt and input. The main labels were checked against an independent re-derivation of a seeded sample; modality, disease area and targets were not audited (Appendix).


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

For development programs that entered a phase in 2008–2019 and were developed in the US, the likelihood of FDA approval from Phase 1 is 8.9% (95% CI 8.0%–9.9%), against BIO's 7.9% for 2011–2020 (6.8% for novel drugs). Across all industry programs registered on ClinicalTrials.gov, including those run only outside the US, it is 5.4%. Most programs stop without a stated reason: of 8,867 programs that stopped, 46% left no stated reason and no posted or published result, and 23% record an efficacy, safety or pharmacokinetic reason.

### How programs are counted

* **Trial:** a registered interventional study listing Early Phase 1 to Phase 3. A Phase 1/2 trial counts as Phase 2 and a Phase 2/3 trial as Phase 3. Withdrawn trials never enrolled and are left out.
* **Molecular entity:** the active substance, whatever its brand, sponsor code, dose or salt, resolved to its FDA UNII substance where one exists. Biosimilars fold into their reference entity.
* **Disease:** the MONDO term for the condition the trial treats, without line, stage, biomarker or age qualifiers.
* **Program:** one entity developed for one indication. An indication groups the entity's MONDO diseases the way a sponsor runs them as programs (prostate cancer with castration-resistant and metastatic prostate carcinoma; diffuse large B-cell and follicular lymphoma kept apart), decided by an LLM for each entity. An entity belongs to a program only in trials where it is the investigational agent, not a comparator or background therapy. Each industry trial's purpose is classified first: bioequivalence, formulation, food-effect, interaction and other product-support studies (10,770 trials) belong to no program; a first-in-human study or a basket across several diseases counts as Phase 1 only for the program the sponsor pursued next.
* **Phase entry and outcome:** a program enters a phase when its first industry-sponsored trial of that phase starts. It *advanced* when a later-phase trial in its disease started (any sponsor) or the FDA approved the entity for the disease. A trial that has not started, because it is still not yet recruiting or its record went silent before its estimated start date, marks neither entry nor advancement. A program is *suspended* when none of its trials, nor the trial that marked its Phase 1 entry, has been active within 24 months of the snapshot (2026-10-20); otherwise it is still running and *censored*. Programs whose entity was already approved for the disease are lifecycle programs and are left out; an approval dated only as before 2008 (the first approval letters read) is placed at the entity's first FDA approval, the earliest it could have happened. As in BIO's report, a phase a program skipped (Phase 1 straight to Phase 3, or approval from Phase 2) counts as a success in that phase, each phase's success rate is advanced ÷ (advanced + suspended), and LOA is their product. *US-developed* programs are those with a US-sited industry trial in the phase; a cohort with fewer than ten entities resolved in a phase gets no LOA.
* **Approval:** FDA approval of the entity for the program's disease, a subtype or population of it, or a broader approved class that includes it, judged from the dated approval letters, original-approval dates and labels of every application of the entity (CDER and CBER).

13,490 programs of 7,123 individual drugs entered at least one phase in 2008–2019. Entries end in 2019 so that every program has had at least six years to advance or stop before the snapshot; registration of industry trials became mandatory in the US in late 2007, so the window starts in 2008.

### Phase transitions

| Transition | All programs (95% CI) | Developed in the US (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- |
| Phase 1 → Phase 2 | 54.8% (53.0–56.6), n=6,565 | 57.0% (54.6–59.5), n=4,139 | 52.0% |
| Phase 2 → Phase 3 | 28.4% (26.9–29.6), n=6,277 | 31.3% (29.7–33.1), n=4,032 | 28.9% |
| Phase 3 → Approval | 34.9% (32.5–37.4), n=2,155 | 50.0% (47.0–52.9), n=1,423 | 52.4% |
| **Phase 1 → Approval (LOA)** | **5.4%** (4.9–6.0) | **8.9%** (8.0–9.9) | **7.9%** (novel drugs 6.8%) |

### Change over time

Success rose across the window. Programs that entered a phase in 2008–2011 reached approval from Phase 1 4.1% of the time; those that entered in 2016–2019, 6.9% (7.3% and 10.0% for US-developed programs). The gain came in the later phases: Phase 2 success rose from 25.0% to 30.7% and Phase 3 from 28.4% to 42.4% (44.2% to 55.9% for US-developed programs), while Phase 1 success fell slightly, from 57.6% to 52.7%.

| Phase entry | Entities | Phase 1 → 2 | Phase 2 → 3 | Phase 3 → approval | LOA (95% CI) | US-developed: Phase 3 → approval | US-developed: LOA (95% CI) |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 2008–2011 | 2,756 | 57.6% | 25.0% | 28.4% | 4.1% (3.5–4.9) | 44.2% | 7.3% (6.0–8.7) |
| 2012–2015 | 2,884 | 54.8% | 29.4% | 33.4% | 5.4% (4.4–6.5) | 47.9% | 9.3% (7.7–11.1) |
| 2016–2019 | 3,645 | 52.7% | 30.7% | 42.4% | 6.9% (5.9–7.9) | 55.9% | 10.0% (8.4–11.6) |

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
| 2018 | 49% (13%) | 28% (19%) | 37% (30%) |
| 2019 | 51% (16%) | 33% (18%) | 45% (32%) |


### Why programs stop

Each suspended program takes one reason from the industry trials of the phase it stopped in, in this order: an efficacy reason stated by the sponsor, a primary endpoint missed in posted or published results, a safety signal, a pharmacokinetic or formulation problem, an explicit business or strategic reason, a bare "sponsor decision", an enrollment, operational or regulatory reason, a positive primary readout without advancement, another stated reason, posted results with no stated reason or readable endpoint, and finally neither a reason nor a result.

| Reason | Phase 1 | Phase 2 | Phase 3 |
| :---- | :---- | :---- | :---- |
| PK, dose or formulation | 1% (40) | 0% (17) | 0% (1) |
| business or strategic (explicit) | 8% (238) | 5% (222) | 3% (46) |
| completed, no results posted, no reason stated | 57% (1,690) | 27% (1,228) | 23% (320) |
| efficacy: primary endpoint not met | 0% (10) | 22% (975) | 21% (293) |
| efficacy: stated | 2% (70) | 5% (241) | 10% (137) |
| enrollment, operational or regulatory | 2% (66) | 5% (227) | 3% (49) |
| other stated reason | 0% (14) | 0% (16) | 1% (12) |
| positive readout, not advanced | 0% (11) | 10% (448) | 19% (273) |
| results posted, no reason stated, endpoint not assessable | 13% (390) | 11% (506) | 5% (64) |
| safety | 3% (77) | 3% (114) | 4% (51) |
| sponsor decision, unspecified | 3% (83) | 2% (101) | 1% (21) |
| stopped, no reason stated | 9% (280) | 9% (401) | 10% (135) |

![Why suspended programs stopped, by phase](report/output/figures/failure_modes_by_phase.png)

The registry rarely says why a program stopped. In Phase 1, 66% of stopped programs left neither a stated reason nor a result, which is expected: Phase 1 trials seldom post results and companies seldom explain pausing early assets. In Phase 2 and Phase 3 the share without a reason falls to 36% and 32%. Efficacy is the recorded reason for 27% of programs that stopped in Phase 2 and 31% of those that stopped in Phase 3: the sponsor said so, or the posted or published primary endpoint was missed. Safety accounts for 3% and 4%: among Phase 2 and Phase 3 stops with an efficacy or safety reason, safety is 9% and 11%, against about 32% in Harrison (2016), whose 2013–2015 failures with a disclosed reason were 24% safety and 52% efficacy. Either registry records under-report safety stops, or company disclosures over-represent them.

At the level of individual trials, the 4,390 industry trials started in 2008–2019 that stopped early or were withdrawn with a reason give: an explicit business, portfolio or competitive reason 27%, a bare "sponsor decision" 13%, efficacy 18%, enrollment or operations 19% and safety 7%. The draft's single 44% "commercial or strategic" category mixed these two kinds of statement; a "sponsor decision" with no reason may or may not hide an efficacy result, and the record cannot tell. No study has measured how often a stated business reason hides an efficacy or safety failure. Where a registry gives a reason it mostly agrees with the trial's publication (53 of 57 in [Alturki et al. 2017](https://doi.org/10.1016/j.jclinepi.2016.08.011)); the usual gap is a missing reason. Analysts who also read company filings, press releases and regulator records attribute 57% of drug failures in pivotal trials to efficacy, 17% to safety and 22% to commercial reasons ([Hwang et al. 2016](https://doi.org/10.1001/jamainternmed.2016.6008)), so the efficacy and safety shares here are a floor.

Finally, 19% of Phase 3 programs that stopped short of FDA approval had met their primary endpoint. In a sample we read, most of them were approved outside the US (Japan, China, Korea, Russia) or received a complete response letter from the FDA: a positive Phase 3 readout is necessary but not sufficient for US approval.


### Tracing the stops the registry does not explain

Every program that entered Phase 2 or 3 from 2008 to 2025 and stopped was traced (7,570 programs). The figures here are for the 2008–2019 entries of the Section 1 headline, with later entries compared below. For 2,961 of their 5,898 stops, the registry gives no reason, only "sponsor decision", an unspecified "other" reason, or an efficacy reason that the efficacy reading above found wrong. Each was traced. A model read the program's trials (records, posted results, linked papers) and structured signals: whether the drug went on in other diseases, whether its sponsor started any trial afterwards, whether drugs on the same target stopped at the same time. It then searched the web for company releases, SEC filings, pipeline updates, conference reports and trade news, with ClinicalTrials.gov excluded. It named a cause only where a source supported it, citing only pages its own searches returned, and separately gave a *likely* cause, its best inference from context, where no source says. Each step is recorded in the database (`preclin.analysis_method`, `preclin.stop_signal`, `preclin.stop_cause`), with every decision's inputs, searches and sources in `pv_evidence.llm_decision`.

| Cause of the stop | As registered | After tracing: sourced | After tracing: sourced or likely |
| :---- | :---- | :---- | :---- |
| Efficacy | 28% (1,646) | 37% (2,209) | 41% (2,445) |
| Safety | 3% (165) | 4% (252) | 4% (258) |
| PK or formulation | 0% (18) | 1% (40) | 1% (43) |
| Business or strategic | 5% (268) | 10% (613) | 17% (1,020) |
| Company acquired, merged, unfunded or closed | 0% (0) | 2% (123) | 4% (209) |
| Operational (enrollment, sites, supply, regulatory) | 5% (276) | 5% (316) | 6% (345) |
| Positive readout, not yet advanced | 12% (721) | 21% (1,266) | 22% (1,323) |
| Did not actually stop | 0% (0) | 3% (185) | 3% (190) |
| Unknown | 48% (2,804) | 15% (894) | 1% (65) |

A sourced cause was found for 70% of the traced programs (2,067), and a likely cause for 98%. The biggest changes from the registry's picture:

* **Many quiet stops were not failures.** A positive readout that was not taken further in the disease (approval outside the US, a stalled partnership, a move to another formulation) was the sourced cause for 618 traced programs, and 185 had not stopped at all: development continued under another registry, region, name or combination. Section 1's suspension rule, which reads only ClinicalTrials.gov, counts these as stops, so its failure rates are somewhat high.
* **Efficacy is under-recorded.** Efficacy was the sourced cause of 645 traced programs, usually from published results or a company statement the registry never carried, raising efficacy from 28% of all Phase 2/3 stops as registered to 37% sourced (41% counting likely causes).
* **Business reasons and company events are the rest.** Portfolio decisions account for 17% of all stops counting likely causes, and acquisitions, mergers, lost funding or closures for 4%. Safety stays rare (4%).

**Over time.** Counting sourced and likely causes, and leaving out programs that turned out not to have stopped, efficacy or exposure was the cause of 46% of stops among programs entering in 2008–2011, 43% in 2012–2015 and 42% in 2016–2019; business, strategic and company events were 20%, 22% and 23%, and a positive readout not yet advanced 22%, 25% and 23%. Among entries from 2015 to 2025 (4,112 stops, many later programs still running), the shares are 38% efficacy or exposure, 26% business and 24% positive readouts.

**Phase 1.** Phase 1 stops were traced the same way (4,075 programs entering 2008–2025, 2,969 of them in 2008–2019). As registered, 83% give no usable reason, since Phase 1 trials seldom post results and companies seldom explain pausing early assets. Tracing found a sourced cause for 59% of those and a likely cause for 94%. Counting both, efficacy or exposure was the cause of 20% of Phase 1 stops, safety 9%, business, strategic and company events 45%, operational 6% and a positive readout not yet advanced 15%; 5% stay unknown.

**How far to trust it.** The same procedure was run on 141 stops whose registry does state a reason, drawn at random across causes, with the reason removed and ClinicalTrials.gov blocked. It named a sourced cause for 79% of them, and that cause matched the registry's for 59% (κ = 0.52); the likely cause matched for 54% (κ = 0.46). Accuracy differs by cause. Efficacy stops were recognised almost every time (88%), but only 69% of the stops it called efficacy were efficacy stops in the registry: safety stops were often read as efficacy (companies announce both as an unfavourable benefit–risk), and business and operational stops were confused with each other (58% and 46% recognised). The efficacy share after tracing is therefore an upper estimate, and safety is likely under-counted. The registry's stated reason is itself an imperfect reference, since a stated business reason can hide a failed readout. Stops with a stated reason are probably also easier to trace, so accuracy on the unexplained stops is likely lower. One independent check holds: of programs traced to a company event, 78% had a sponsor that started no trial afterwards, against 26% of those traced to efficacy.


### Why efficacy failed: the target was not engaged, or it was the wrong target

A program that fails on efficacy fails in one of two ways that matter for target selection: the drug never engaged its target well enough in patients, so the target hypothesis was never tested, or it engaged the target and the disease did not respond. The cohort is every Phase 2 and 3 program that entered in 2008–2019 and stopped for efficacy or for PK, dose or formulation: as the registry records it (1,586 efficacy, 16 PK), or as traced with a source from the stops the registry does not explain (588 efficacy, 23 PK). An exposure failure is the same biology as a failure to engage, so PK stops are broken down here rather than counted apart. For each of the 2,213 programs the model would label (36 more, mostly gene and cell therapies and live biotherapeutics, were refused), an LLM read an evidence bundle: the failed trial's record, posted results and papers, the drug's other trials and their outcomes, results posted by its Phase 1 trials, its FDA approvals, other drugs on the same target in the same or a related disease, and PubMed abstracts on the drug's human pharmacology and on the drug in that disease. It judged, for humans and at the doses tested, the three pillars of [Morgan et al. 2012](https://doi.org/10.1016/j.drudis.2011.12.020): exposure at the site of action, binding or engagement of the target, and the expected pathway effect. Engagement could also be inferred when the drug worked in another disease through the same target and tissue compartment at a comparable dose. It then coded the failure, using only the bundle and citing the sources it used. The codes and checks were fixed before any program was labelled; the full method, with examples and prompts, is in `report/methods_stops_and_engagement.md`. Where the bundle held no human evidence of engagement (40% of programs), a second pass, added after the first results, gave the same model the same bundle and the web: it searched full-text papers, conference reports, FDA and EMA reviews and company releases for human pharmacology, and could cite only pages its own searches returned. It decided 181 of the 856 programs it searched; the figures below use those labels.

| What the evidence shows | Phase 2 | Phase 3 | Phase 2 and 3 | Outside oncology |
| :---- | :---- | :---- | :---- | :---- |
| Not engaged: exposure or engagement inadequate, or another drug on the target worked (F1) | 10% (169) | 11% (58) | 10% (227) | 9% (156) |
| Engaged, no benefit: target or mechanism wrong for the disease as tested (F2–F4) | 46% (782) | 49% (247) | 46% (1,029) | 44% (726) |
| Trial design, population or endpoint, mechanism not in question (F7) | 6% (106) | 10% (50) | 7% (156) | 8% (131) |
| Toxicity offset or ended efficacy (F5, F6) | 0% (7) | 0% (2) | 0% (9) | 0% (2) |
| Indeterminate: no human engagement evidence either way (U) | 38% (640) | 30% (152) | 36% (792) | 38% (633) |
| **Not engaged, of failures whose mechanism was tested** | **18%** (15–21) | **19%** (15–24) | **18%** (16–21) | **18%** (15–21) |
| Programs (entities) | 1,704 (1,300) | 509 (432) | 2,213 (1,601) | 1,648 (1,263) |

![Top: Phase 1, 2 and 3 stops by cause, phase entries 2008–2019, excluding programs whose development continued; where no source states the cause, the model's likely cause is counted. Safety is a floor: sponsors rarely state it, a missed endpoint takes precedence over a safety signal, and the tracing recognised fewer than half of known safety stops. Business is the least reliable cause. Positive readouts include programs whose primary endpoints were only partly met. Bottom: the programs of each phase stopped for efficacy or exposure with a sourced cause (likely-only causes are not broken down), by what the evidence shows about target engagement. Phase 1 trials rarely test efficacy, so its efficacy stops are mostly early patient cohorts and dose-finding readouts](report/output/figures/efficacy_attribution.png)

Where the record shows whether the mechanism was tested, the drug had engaged its target in 1,029 of 1,256 programs and the disease did not respond; **18%** (16%–21%) failed without adequate engagement or exposure, or with another drug on the same target succeeding in the disease. The second kind is the larger and is inferred rather than measured: 116 of the 227 not-engaged programs failed where a drug on the same target worked, 94 of them with no human engagement data of their own; the rest had exposure or engagement measured and found inadequate. Failures to engage are about as common in Phase 3 (19%) as in Phase 2 (18%): no regulation requires engagement to be shown, and good practice places it in Phase 1 or 2a, yet engagement was often still unverified when confirmatory trials started. Outside oncology the share is 18%. Trial design, population or endpoint account for 7% of efficacy failures, and toxicity that offset efficacy for 9 programs. Another 52 programs recorded as efficacy stops were not failed efficacy tests (a met endpoint, a missed non-inferiority margin, a business stop, or off-target toxicity); they are counted under their traced cause above and left out here.

* *Engaged, no benefit.* Venglustat cut glucosylceramide in the cerebrospinal fluid of people with *GBA1* Parkinson's disease by about 73% at the top dose ([Peterschmitt 2022](https://doi.org/10.3233/JPD-212714)), and over a year their motor scores worsened by 7.3 points on drug against 4.7 on placebo ([MOVES-PD](https://doi.org/10.1016/S1474-4422(23)00205-3)). CSL112, plasma-derived apolipoprotein A1 that raises cholesterol efflux capacity, did not reduce myocardial infarction, stroke or cardiovascular death at 90 days in 18,219 patients after myocardial infarction (hazard ratio 0.93, 0.81–1.05; [AEGIS-II](https://doi.org/10.1056/NEJMoa2400969)).
* *Not engaged.* PF-06687234, an IL-10 fusion protein added to infliximab for ulcerative colitis, was stopped for futility, and was detected, at low concentration, in only one colon tissue sample: the drug may never have reached the inflamed mucosa at a useful level ([Ther Adv Gastroenterol 2026](https://doi.org/10.1177/17562848251410784)).

**Over time.** Among efficacy failures of programs entering in 2008–2011, 2012–2015 and 2016–2019, the share not engaged where engagement is known was 19%, 19% and 16%, and the share with no engagement evidence 38%, 34% and 35%. For entries from 2015 to 2025 the not-engaged share is 16% (13%–18%, 1,363 programs).

**Phase 1.** Phase 1 trials mostly test safety, dose and exposure, often in healthy volunteers, so an efficacy or exposure stop there is usually an early patient cohort or a dose-finding readout. The same labels were applied to the 387 Phase 1 programs entering 2008–2019 that stopped for efficacy or exposure. Where engagement is known (236 programs), 33% (27%–40%) were not engaged; 38% have no engagement evidence either way.

**The large caveat is what the public record does not say.** For 36% of efficacy failures there is still no human evidence of engagement either way, after the web search, so a drug that never engaged and a target that does not matter cannot be told apart. Engagement was shown in patients with the program's disease for only 30% of the programs where it was shown at all, and was public or registered before the failed trial started for 52%. The gap need not be neutral: a drug that never engaged its target leaves less to publish, and engagement inferred from success in another disease can only add to the engaged side. Among the programs the web search could decide, this shows a little: 31 of the 148 it found tested were not engaged (21%), against 19% among the programs the bundle alone decided. If every program still indeterminate were a failure to engage, the ceiling is 50%. Counting only directly measured engagement gives the same direction:

| Variant | Programs | Mechanism tested | Not engaged, of tested (95% CI) | Indeterminate |
| :---- | :---- | :---- | :---- | :---- |
| All (Phase 2 and 3) | 2,213 | 1,256 | 18% (16–21) | 36% |
| Phase 2 | 1,704 | 951 | 18% (15–21) | 38% |
| Phase 3 | 509 | 305 | 19% (14–24) | 30% |
| Efficacy recorded in the registry | 1,586 | 974 | 17% (14–19) | 31% |
| Traced from unexplained stops | 611 | 272 | 22% (17–28) | 49% |
| Outside oncology | 1,648 | 882 | 18% (15–21) | 38% |
| Oncology | 565 | 374 | 19% (15–24) | 28% |
| Sponsor-stated efficacy reason | 371 | 254 | 20% (15–25) | 29% |
| Primary endpoint missed | 1,215 | 720 | 15% (12–18) | 31% |
| Direct pillar evidence only (inferred engagement counted as unknown) | 2,213 | 912 | 25% (22–28) | 51% |
| Engaged only if shown before the index trial | 2,213 | 768 | 30% (26–33) | 59% |
| One program per entity | 1,601 | 854 | 19% (16–21) | 39% |
| High or medium confidence | 1,384 | 907 | 13% (11–16) | 27% |
| Bundle only (before the web search) | 2,213 | 1,019 | 19% (16–22) | 40% |
| Entries 2015-2025 | 1,363 | 753 | 16% (12–19) | 36% |
| All traced entries 2008-2025 | 2,679 | 1,498 | 17% (15–19) | 36% |

**Checks.** A second model, given the same bundles and asked the pillar questions one at a time before choosing any code, relabelled a seeded random sample of 150 programs (136 with a validated label from both): it agreed on the not-engaged / engaged / other split for 69% (κ = 0.48) and on whether the target was engaged for 79%. Separately, agents with web access researched a seeded random sample of 66 programs from scratch (publications, conference reports, company releases), without the pipeline's labels (65 also have a pipeline label): they agreed on the three-way split for 82% (κ = 0.67) and on the group for 86% of the programs the pipeline decided; they never called engaged a program the pipeline called not engaged, or the reverse (0 contradictions). Of the 16 adjudicated programs the bundle had left indeterminate, the web search and the outside researchers both decided 4 and agreed on 75% of them; the search never decided one the researchers could not, and the researchers decided 2 that the search left open (1 of them not engaged). On their own, they found 5 failures to engage among 36 programs whose mechanism they could judge (14%). The pre-registered construct checks, on data the labels do not use, point one way or nowhere. Programs coded not engaged had germline genetic support for the disease more often than those coded engaged without benefit (13% against 7%, p = 0.04, 111 programs coded F1a), as expected if engaged failures more often test a target the disease does not depend on. The two groups did not differ in whether other drugs on their target failed (52% against 55%) or advanced (48% against 50%) in the disease.

The answer to "was the target wrong, or was it never hit?" is therefore: where anyone can tell, the target was usually hit. Among efficacy failures whose mechanism was tested, 18% failed to engage (13% to 30% across the variants above); in the rest the drug engaged its target and the disease did not move. For 36% of failures the public record, searched, cannot say.


### By disease area and modality

| Disease area | All programs, LOA (95% CI) | Entities | Developed in the US, LOA (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- | :---- |
| Hematology | 18.4% (12.8–25.2) | 212 | 22.9% (14.8–32.8) | 23.9% |
| Metabolic | 10.2% (6.7–14.2) | 285 | 19.0% (13.1–26.5) | 15.5% |
| Oncology | 9.8% (7.8–11.9) | 1,856 | 12.4% (9.7–15.3) | 5.3% |
| Infectious disease | 8.6% (6.3–11.0) | 686 | 17.0% (13.0–21.3) | 13.2% |
| Autoimmune | 7.5% (5.1–10.0) | 523 | 10.1% (6.6–13.9) | 10.7% |
| Allergy | 6.8% (3.0–11.8) | 141 | 12.7% (4.6–22.4) | 10.3% |
| Neurology | 6.5% (5.0–8.2) | 754 | 10.3% (7.9–12.8) | 5.9% |
| Endocrine | 6.3% (3.7–9.4) | 350 | 12.2% (7.3–17.7) | 6.6% |
| Psychiatry | 6.1% (3.5–9.0) | 320 | 8.5% (5.0–12.5) | 7.3% |
| Respiratory | 4.6% (2.5–6.8) | 377 | 9.1% (5.3–13.0) | 7.5% |
| Ophthalmology | 4.3% (2.4–6.5) | 330 | 6.4% (3.6–9.9) | 11.9% |
| Other | 3.8% (2.6–5.3) | 785 | 8.1% (5.7–10.9) | 13.0% |
| Urology | 3.8% (0.9–8.0) | 84 | 6.0% (1.4–12.6) | 3.6% |
| Gastroenterology | 3.0% (1.5–4.8) | 333 | 7.5% (3.9–11.8) | 8.3% |
| Cardiovascular | 2.7% (1.5–4.2) | 341 | 5.5% (3.0–8.9) | 4.8% |

| Modality | All programs, LOA (95% CI) | Entities | Developed in the US, LOA (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- | :---- |
| Monoclonal antibody | 12.8% (9.6–16.1) | 840 | 15.0% (11.1–19.5) | 12.1% |
| Antibody–drug conjugate | 8.9% (3.5–15.2) | 147 | 8.2% (2.9–14.6) | 10.8% |
| Protein | 5.8% (3.9–7.8) | 461 | 8.9% (5.9–12.7) | 9.4% |
| Small molecule | 5.3% (4.6–6.0) | 4,194 | 8.7% (7.5–9.8) | 7.5% |
| Gene therapy | 4.8% (1.6–8.9) | 114 | 6.1% (2.1–10.7) | 10.0% |
| Peptide | 4.6% (2.6–7.2) | 276 | 6.6% (3.7–10.8) | 8.0% |
| Antisense oligonucleotide | 4.5% (1.2–9.9) | 92 | 6.0% (1.6–14.7) | 5.2% |
| Other cell therapy | 0.7% (0.1–1.5) | 274 | 2.0% (0.3–4.7) | – |
| Microbiome or live biotherapeutic | 0.4% (0.0–2.4) | 46 | – | – |
| Other | 0.1% (0.0–0.4) | 301 | 0.4% (0.0–1.7) | – |

![Likelihood of approval by disease area](report/output/figures/loa_by_area.png)

![Likelihood of approval by modality](report/output/figures/loa_by_modality.png)

Disease areas rank differently from BIO's: the rank correlation with BIO's LOA across the 15 areas is 0.50 for all programs and 0.54 for US-developed ones. Across all programs, hematology, metabolic and oncology programs reach approval most often (18.4%, 10.2% and 9.8%), and cardiovascular, gastroenterology and urology programs least (2.7%, 3.0% and 3.8%). Among US-developed programs, endocrine (12.2%) and oncology programs (12.4%) come out far above BIO's 6.6% and 5.3%; for oncology, the window takes in the wave of immunotherapy and antibody–drug conjugate approvals, and an approval in a cancer subtype counts for the program's cancer. Ophthalmology (6.4%) falls well below BIO's 11.9%. Among modalities, monoclonal antibodies and antibody–drug conjugates reach approval most often across all programs (12.8% and 8.9%), and among the classes BIO also reports, antisense oligonucleotides (4.5%), peptides (4.6%) and gene therapies (4.8%) least. RNA interference and CAR-T, near the top of BIO's ordering, have too few entities resolved in Phase 3 here (most of their approvals came straight from Phase 2) to estimate. Across the 7 classes both estimate, the modality ordering agrees with BIO's (rank correlation 0.82).



## Predictive power of preclinical evidence

Human genetic evidence linking a program's target to its disease is the clearest preclinical signal of success. Programs whose target had it before they entered the phase reached FDA approval 2.96 times as often as programs without it (30.1% against 10.2%; 95% CI 2.28–3.83), the likelihood rises with the strength of the evidence, and the association holds at every phase after accounting for disease area, modality, novelty and era. Somatic driver and mouse-model evidence carry weaker signals. Cancer cell-line CRISPR screens single out the same validated oncology targets as somatic drivers and add nothing once those are known, and a target essential in most cell lines, judged by what DepMap had published before entry, is not a clear liability. Yet as a predictor of which individual programs will be approved, the evidence lines raise discrimination only modestly over disease area and modality (held-out AUC 0.605 to 0.641), because most programs have none of them.


### Evidence lines and how they are matched

Each program aimed at a human protein (the entity's primary targets, resolved by an LLM from the entity's mechanism records and trial descriptions) is scored for the evidence its targets had **for the program's disease** in Open Targets Platform 26.09, **as of the year before the program entered the phase**. A target–disease association counts for the program's disease when the evidence disease is the same MONDO term, a subtype of it, or similar to it (Lin similarity ≥ 0.8, the criterion Minikel et al. used). Each association's score is rebuilt year by year from its evidence items, each dated by when it became known (ClinVar records by their creation rather than their latest review, IMPC knockouts by their first data release, Project Score screens by the first Open Targets release that listed them), so evidence is taken as it stood before phase entry, not as it stands today. Evidence lines:

* **Human germline genetics:** GWAS credible sets (with locus-to-gene scores), gene burden tests, ClinVar, Genomics England PanelApp, Orphanet, Gene2Phenotype, ClinGen and UniProt; split into GWAS and rare-variant/Mendelian sources.
* **Somatic drivers:** COSMIC Cancer Gene Census, IntOGen and ClinVar somatic.
* **Mouse models:** IMPC phenotypes. **Expression:** differential expression in the disease (Expression Atlas). **Pathways:** Reactome.
* **Cell screens:** genome-wide CRISPR screens, which switch off (or, in neurons, also switch on) each gene in turn in cultured human cells and record whether the cells grow or change. They are functional genomics, not compound assays: they show the cells depend on the gene, not that any molecule works. *Cancer cell lines* come from Project Score (Wellcome Sanger Institute; 324 lines in [Behan et al. 2019](https://doi.org/10.1038/s41586-019-1103-9), extended in [Pacini et al. 2024](https://pubmed.ncbi.nlm.nih.gov/38215750/)), which names a gene a priority target for a cancer type when knocking it out stops the growth of that type's lines, scoring it higher when the dependency is strong, shared across the type's lines and tied to a genomic marker. *Neurons* come from CRISPRbrain, screens in neurons and microglia made from human stem cells that record survival or a cell phenotype.
* **Target liabilities**, properties of the target rather than evidence for the disease: essential in most cell lines (on the latest yearly DepMap common-essential list from before phase entry; DepMap first published such a list in 2019, so earlier entrants are never flagged) and intolerant of loss of function (gnomAD v4.1 LOEUF < 0.35, from the current release).

Sources that encode clinical outcomes or literature co-mention (ChEMBL clinical precedence, Europe PMC) are not used. Vaccines, cell and gene therapies and other entities without a single human protein target fall outside this analysis, so its programs reach approval more often than the Section 1 cohort as a whole. Of the 10,169 programs on 1,467 targets scored, 15.2% of Phase 1 entrants had human genetic evidence for their disease at entry.

### Relative success

*Relative success* is the LOA of programs with the evidence divided by the LOA of programs without it (Nelson et al. 2015; Minikel et al. 2024). The 95% intervals resample primary-target sets (an entity's primary targets taken together), since programs on the same targets are not independent.

| Evidence line | Programs with it | LOA with / without | Relative success (95% CI) |
| :---- | :---- | :---- | :---- |
| CRISPR knockout screen in cancer cell lines | 182 | 51.1% / 12.6% | 4.05 (2.57–5.89) |
| Any human genetics | 1,740 | 30.1% / 10.2% | 2.96 (2.28–3.83) |
| Rare-variant or Mendelian genetics | 1,130 | 32.1% / 11.0% | 2.93 (2.24–3.77) |
| Somatic cancer driver | 1,646 | 26.8% / 11.3% | 2.37 (1.68–3.25) |
| GWAS | 851 | 26.2% / 11.9% | 2.20 (1.54–2.98) |
| Disease pathway (Reactome) | 206 | 24.7% / 12.6% | 1.95 (1.09–3.05) |
| Mouse model | 2,040 | 16.3% / 11.9% | 1.37 (1.02–1.80) |
| Expressed differently in the disease | 1,560 | 16.6% / 12.4% | 1.34 (0.93–1.83) |
| **Target liabilities** (not specific to the disease) |  |  |  |
| Intolerant of loss of function | 1,976 | 12.2% / 13.1% | 0.93 (0.62–1.37) |
| Essential in most cell lines | 330 | 8.7% / 12.9% | 0.67 (0.09–1.91) |

![Relative success by evidence line](report/output/figures/relative_success_by_evidence.png)

Rare-variant and Mendelian evidence (2.93×) and GWAS evidence (2.20×) both carry the genetic signal, in line with Minikel et al. (2024), who found 2.6× from Phase 1 to launch with Mendelian evidence stronger than GWAS. Somatic driver evidence (2.37×), mouse phenotypes (1.37×) and Reactome pathways (1.95×, from only 206 programs) also associate with success; differential expression in the disease does not clearly (1.34×, interval spanning 1). CRISPR knockout screens in cancer cell lines show the largest ratio (4.05×, 2.57–5.89, 182 programs), but they mostly flag targets oncology had already validated (EGFR, ERBB2, ESR1, KRAS, CDK4 and CDK6), 98% of them also somatic drivers for the cancer; they add nothing once the other lines are in the model (below). Only Project Score pairs listed since its 2019 release count before 2024. The neuron screens matched too few programs (16) to estimate.

Target liabilities, properties of the target rather than evidence for the disease, carry little. Loss-of-function-intolerant targets show no penalty (0.93×). Targets on DepMap's common-essential list before entry reach approval less often (0.67×, 0.09–1.91), but the interval is wide: the list was first published in 2019, so only the 330 programs that entered a phase from 2020 can carry the flag. Judged by today's list instead, as earlier drafts did, the penalty looks firm (0.45×, 0.17–0.83): much of it comes from targets found essential after their programs had started, mostly oncology small molecules aimed at machinery every cell needs (mTOR, tubulin, topoisomerases, histone deacetylases, WEE1 and ATR, BET proteins).

Two checks bear on whether this reflects foresight rather than hindsight. Evidence is taken as it stood the year before the program entered the phase, each item dated by when it became known, so later discoveries do not count. Counting all evidence known by 2026 instead weakens the genetic relative success to 2.47×: what was known in advance is more telling than what was found afterwards. And restricting matches to diseases similar to the program's (Lin ≥ 0.8, Minikel's criterion, without the subtype rule) gives 2.98×.


### Genetic dose–response

| Genetic association score before entry (Open Targets, 0–1) | Programs | Targets | LOA (95% CI) |
| :---- | :---- | :---- | :---- |
| 0 (no genetic support) | 8,491 | 1,310 | 10.2% (8.2–12.7) |
| up to 0.61 (lowest third) | 680 | 346 | 18.1% (12.5–24.3) |
| 0.61–0.88 (middle third) | 539 | 204 | 40.2% (29.8–49.4) |
| above 0.88 (highest third) | 596 | 241 | 37.3% (29.7–45.6) |

![Likelihood of approval by strength of human genetic support](report/output/figures/genetic_dose_response.png)

### What each line adds once the others are known

Programs with genetic evidence differ from programs without it in disease area, modality and era, and the evidence lines overlap. The table gives, for each phase, the relative risk of advancing for programs with each line, from one Poisson model containing every line together with disease area, modality, entity novelty and entry period (standard errors clustered by primary-target set).

| Evidence | Phase 1 → 2 | Phase 2 → 3 | Phase 3 → approval |
| :---- | :---- | :---- | :---- |
| GWAS | 1.08 (1.01–1.15) | 1.54 (1.33–1.80) | 1.05 (0.78–1.40) |
| Rare-variant or Mendelian genetics | 1.12 (1.04–1.22) | 1.35 (1.16–1.57) | 1.51 (1.26–1.81) |
| Somatic cancer driver | 1.03 (0.92–1.15) | 1.11 (0.90–1.38) | 1.07 (0.84–1.35) |
| Mouse model | 0.92 (0.86–0.99) | 0.99 (0.87–1.13) | 0.97 (0.82–1.15) |
| Expressed differently in the disease | 0.94 (0.87–1.02) | 1.02 (0.85–1.22) | 0.90 (0.74–1.10) |
| Disease pathway (Reactome) | 1.10 (0.97–1.25) | 0.97 (0.73–1.28) | 1.10 (0.80–1.52) |
| CRISPR knockout screen in cancer cell lines | 0.92 (0.76–1.13) | 0.99 (0.78–1.26) | – |
| **Target liabilities** (not specific to the disease) |  |  |  |
| Intolerant of loss of function | 0.90 (0.79–1.03) | 1.13 (0.96–1.33) | 1.00 (0.82–1.23) |
| Essential in most cell lines | 1.05 (0.88–1.26) | 1.14 (0.84–1.53) | – |

One evidence line at a time, with the same adjustments, human genetic evidence raises the chance of advancing by 1.10× in Phase 1, 1.62× in Phase 2 and 1.41× in Phase 3: the effect sits where efficacy is first tested. In the joint model, GWAS and rare-variant evidence each keep an independent effect at Phase 2, rare-variant evidence also at Phase 3 and GWAS a small one at Phase 1, and essentiality across cell lines shows no penalty at any phase (1.14 at Phase 2, 0.84–1.53). Cancer cell-line screens, 1.30× at Phase 2 on their own, fall to 0.99× beside the somatic and genetic evidence on the same targets; somatic, mouse-model, expression and pathway evidence also lose their association once genetics and the covariates are in the model, consistent with their univariate signal riding along with genetic support and with disease area.


### Does the evidence predict which programs reach approval?

We followed programs that entered Phase 1 in 2008–2016 for ten years (3,185 programs, 159 approved), with the Open Targets evidence lines and novelty taken as of entry (loss-of-function constraint comes from the current gnomAD release), and fitted logistic models on disease area, modality, novelty and entry year alone, and with the evidence lines added. Performance is measured on held-out primary-target sets (out-of-fold predictions averaged over 20 repetitions of 5-fold cross-validation grouped by primary-target set and stratified by outcome; a single split moves the AUC by several points) and on a temporal split (trained on 2008–2012 entries, tested on 2013–2016).

| Validation | Features | AUC (95% CI) | PR-AUC (base rate) | Programs (approved) |
| :---- | :---- | :---- | :---- | :---- |
| Held-out target sets | Area, modality, novelty, year | 0.605 (0.540–0.668) | 0.098 (0.050) | 3,185 (159) |
| Temporal (2013–2016) | Area, modality, novelty, year | 0.620 (0.545–0.691) | 0.105 (0.056) | 1,603 (89) |
| Held-out target sets | … plus all evidence lines | 0.641 (0.580–0.705) | 0.118 (0.050) | 3,185 (159) |
| Temporal (2013–2016) | … plus all evidence lines | 0.637 (0.565–0.719) | 0.125 (0.056) | 1,603 (89) |
| Held-out target sets | Evidence lines only | 0.622 (0.542–0.703) | 0.092 (0.050) | 3,185 (159) |
| Temporal (2013–2016) | Evidence lines only | 0.623 (0.555–0.693) | 0.105 (0.056) | 1,603 (89) |

Change in held-out AUC when each line is removed from the full model (human genetics: GWAS and rare-variant evidence removed together; lines carried by fewer than 100 programs are not modelled; paired bootstrap over target sets):

| Evidence removed | AUC change (95% CI) |
| :---- | :---- |
| Any human genetics | -0.025 (-0.047 to -0.005) |
| Rare-variant or Mendelian genetics | -0.025 (-0.048 to -0.005) |
| Expressed differently in the disease | -0.007 (-0.022 to +0.010) |
| Mouse model | +0.002 (-0.000 to +0.004) |
| Intolerant of loss of function | +0.002 (-0.002 to +0.006) |
| Somatic cancer driver | +0.002 (-0.015 to +0.019) |

A model on disease area, modality, novelty and entry year alone ranks programs at an AUC of 0.605 on held-out target sets; adding the evidence lines raises it to 0.641 (95% CI 0.580–0.705), and the temporal split agrees (0.620 without, 0.637 with). Human genetics carries most of the gain: removing it lowers the held-out AUC by 0.025 (95% CI 0.005–0.047), and no other line's removal measurably lowers it. GWAS evidence covered too few of the 2008–2016 entrants to be modelled, so genetics here means rare-variant and Mendelian evidence; CRISPR screens and DepMap essentiality were not published before 2019, so none of these entrants carries them. Discrimination stays modest all the same, and that does not contradict the relative success: genetic support multiplies the chance of approval by about 2.96 for the minority of programs that have it (15% of Phase 1 entrants, fewer among the 2008–2016 entrants this model follows), but says nothing about the majority, so it can sort only a small slice of programs. The draft's AUCs of 0.825 and 0.769 came from a leaked model and phantom programs (AUDIT.md, C33–C34).



## What translates to the clinic

Human genetic evidence for the program's own disease is the one kind of preclinical evidence that consistently carried over into Phase 2. Outside oncology, programs whose target had germline genetic evidence for the disease before they entered Phase 2 reached Phase 3 or approval within four years 2.34 times as often as programs whose target had no germline genetic evidence at all (27% against 11%), and the advantage shrinks as the evidence moves to a related disease (20%) or to unrelated diseases only (16%). The same target does better in the diseases its genetics points to than in its other diseases (odds ratio 3.00), and the effect holds after accounting for an approved drug on the target. The advantage shows in efficacy: genetically supported programs stopped for efficacy less often (business and operational stops fell about as much), and their trials missed the primary endpoint less often on regulatory surrogates and clinician-rated scales; on patient-reported, exploratory-biomarker and event endpoints the difference was small or absent. Somatic drivers in oncology and Reactome pathway evidence carried weaker signals, literature mouse models a marginal one and differential expression none, and a mouse model whose direction matched the drug's did not predict Phase 2 success. Whether the direction of the genetic effect matters could not be tested, because almost no program went against an established mechanism. Of the rules a sponsor could have applied at Phase 2 entry, only the benchmark, an approved drug on the same target for a related disease, met the pre-registered bar for a particularly predictive model; Mendelian evidence for a non-hereditary disease came closest. Genetic support covered only 24% of the programs that advanced.


### Design

The analysis plan ([report/translation_plan.md](report/translation_plan.md)) was committed before any of these analyses touched outcomes; departures from it are marked below.

* **Cohort and outcome.** Programs on a human protein target that entered Phase 2 from 2015-01-01 to 2020-10-20 (2,519 programs on 883 primary-target sets). Each has at least four years of follow-up before the 24-month inactivity cutoff, so the outcome needs no inferred suspension: a program *advanced* if a Phase 3 trial of its own started, or the FDA approved it for the disease, within four years of entering Phase 2 (17.5% did). The same is done for Phase 1 entrants (a negative control: genetics should matter little for safety and dosing studies) and Phase 3 entrants (approval within four years).
* **Evidence.** Every Open Targets 26.09 evidence row for the program's primary targets, each dated by the year it became known (ClinVar records by their creation, IMPC knockouts by their first data release, otherwise the row's own publication), frozen at the year before entry and matched to the program's disease on MONDO: the same term, a subtype, or Lin similarity ≥ 0.8 (*G3*, genetics for the disease); a disease at Lin 0.5–0.8 only (*G2*); germline evidence only for unrelated diseases (*G1*); none (*G0*). Evidence is split by family and strength (the best GWAS locus-to-gene score, ≥ 0.8, 0.5–0.8 or below; ClinVar pathogenic with multiple submitters or expert review, ClinGen or Gene2Phenotype definitive or strong, PanelApp green; mouse phenotype match in the top quartile), and mouse models are split into IMPC high-throughput knockouts and literature-curated MGI models.
* **Regimes.** Oncology; *hereditary* (the disease is a MONDO hereditary disease and the target has curated Mendelian evidence for it); and every other disease (*non-oncology*, the regime of the headline hypothesis).
* **Models.** Modified Poisson regression (risk ratios) with standard errors clustered by primary-target set, adjusted for disease area, modality, entity novelty, entry period and target precedent (an FDA-approved entity on the target before entry). The seven confirmatory hypotheses are Holm-corrected together.
* **Trials.** Randomised industry Phase 2/3 trials since 2010 whose governing primary endpoint measures efficacy and whose result is readable (5,674 trials; an LLM classified each trial's governing primary endpoint from its registry entry, without the drug's name). Outcome: primary endpoint not met (a mixed result counts as not met).

### Confirmatory hypotheses

|  | Hypothesis | Measure | Estimate (95% CI) | p | Holm p | Result |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| H1 | Outside oncology: genetics for the disease vs no germline genetics on the target, advancing within 4 years of Phase 2 | risk ratio | 2.34 (1.33–4.14) | 0.003 | 0.020 | supported |
| H2 | Same target in different diseases: genetics for the disease vs not (conditional logit) | odds ratio | 3.00 (1.78–5.03) | < 0.001 | < 0.001 | supported |
| H3 | Direction of genetic effect vs drug action (Open Targets direction fields): discordant < undirected < concordant | risk ratio per step | 0.97 (0.69–1.37) | 0.871 | 1.000 | not supported |
| H4 | Trials outside oncology: how the effect of genetics on missing the primary endpoint changes per step from proximal to distal endpoints (registry-posted results, FDAAA era) | ratio of risk ratios | 1.35 (1.09–1.69) | 0.007 | 0.036 | supported |
| H5 | Genetics for the disease lowers efficacy failure more than business or operational failure (Phases 2 and 3) | ratio of risk ratios | 0.99 (0.58–1.69) | 0.975 | 1.000 | not supported |
| H6 | Outside oncology, target liability raises safety failure, and more than efficacy failure (Phases 1–3; intersection-union test) | risk ratio, safety failure | 0.91 (0.46–1.78) | 0.945 | 1.000 | not supported |
| H7 | Oncology: a somatic driver whose direction matches the drug, advancing within 4 years of Phase 2 | risk ratio | 1.12 (0.72–1.75) | 0.610 | 1.000 | not supported |

![Specificity of the genetic evidence](report/output/figures/s3_specificity.png)

Two of the seven hypotheses hold after correction for multiple testing.

* **H1, H2 (supported).** Outside oncology, Phase 2 programs advanced within four years at 11% with no germline genetic evidence on the target (172 programs), 16% with evidence only for unrelated diseases (1,006), 20% with evidence for a related disease (146) and 27% with evidence for the disease itself (153); only the last differs from none once disease area, modality, novelty, period and target precedent are accounted for. Among the 52 targets developed in several diseases with and without genetic support and with different outcomes (380 programs), the diseases with support advanced more often (odds ratio 3.00, 1.78–5.03): the signal is not only that some targets are better than others.
* **H3 (not supported).** Open Targets' direction-of-effect fields follow each variant's predicted consequence, so a few truncating ClinVar variants make gain-of-function disease genes such as PCSK9, MYH7 and TTR read as loss of function, and inhibitors of them as discordant. The test is reported as registered; the direction analysis below replaces those fields.
* **H4 (supported in the registered analysis; not robust).** In trials with registry-posted results, genetic support lowered the chance of missing the primary endpoint most on proximal endpoints (risk ratio 0.58, 0.44–0.76), and the effect weakened by a factor of 1.35 per step towards distal endpoints (p = 0.007; 0.036 after Holm correction). The registered test survives correction, but the pattern does not hold across all readable trials (1.07, p = 0.513) or with mixed results counted as met (1.27).
* **H5 (not supported).** Genetic support lowered efficacy stops (risk ratio 0.71, 0.53–0.96), but business and operational stops fell by a similar factor (ratio of the two 0.99, 0.58–1.69), so the data cannot say that it acts on efficacy alone. Safety stops were no rarer (1.14, 0.58–2.24), nor were stops for pharmacokinetic, formulation or operational reasons, the plan's negative control (0.70, 0.34–1.44).
* **H6 (not supported).** Targets that are pan-essential, intolerant of loss of function, or lethal when knocked out in mice did not stop for safety more often (0.91, 0.46–1.78). Safety is the recorded reason for fewer than 2% of programs, so registries see little of it.
* **H7 (not supported).** In oncology, a somatic driver whose direction matches the drug's (an activated oncogene and an inhibitor) did not raise the chance of advancing (1.12, 0.72–1.75).

**Checks on H1.** Swapping each program's disease for another program's in the same disease area, 200 times, gives a median G3 risk ratio of 1.78 against the observed 2.34 (95th percentile 2.31; p = 0.040). Part of the contrast with G0 therefore reflects whether a target has been studied genetically at all; matching the disease adds to it. At Phase 1, where efficacy is rarely tested, the same contrast is 1.12 (0.89–1.41). Against all other programs rather than G0, genetic support gives 1.74 outside oncology, and 1.59 (1.13–2.21) after adjusting for an approved drug on the target for a related disease; on targets with no approved drug at all, genetic support gives 1.27 (0.80–2.02, all disease areas). Leaving out the most influential target set (PDE4A+PDE4B+PDE4C+PDE4D) gives 2.21. Leaving out each of the 5 largest target classes in turn gives 1.97 to 2.56; the lowest, without the "gpcr" class, has an interval of 1.01–3.86, so the estimate leans on that class.

**Who is in the cohort.** The cohort is Phase 2 programs with a disease and a single resolved human protein target. Left out are 258 programs with no disease (healthy-volunteer, basket or symptom trials; 6% advanced) and 736 without a single human protein target (8%), so the cohort's base rate is higher than Section 1's.


### Which evidence translates

| Evidence for the disease, known before Phase 2 | Programs (targets) | Advanced: with / without | Share of all that advanced | Risk ratio, all (95% CI) | Risk ratio, non-oncology | Risk ratio, oncology |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Germline genetics for the disease | 368 (194) | 29% / 16% | 24% | 1.83 (1.44–2.32) | 1.74 (1.24–2.43) | 1.98 (1.28–3.07) |
| GWAS, any locus-to-gene score | 149 (84) | 26% / 17% | 9% | 1.52 (1.10–2.10) | 1.71 (1.14–2.57) | 1.70 (0.88–3.27) |
| GWAS, locus-to-gene score ≥ 0.8 | 68 (41) | 25% / 17% | 4% | 1.38 (0.90–2.13) | 1.44 (0.89–2.35) | – |
| GWAS, best score 0.5–0.8 | 37 (24) | 16% / 18% | 1% | 0.95 (0.47–1.91) | – | – |
| GWAS, best score below 0.5 | 44 (27) | 34% / 17% | 3% | 2.11 (1.29–3.46) | 2.37 (1.36–4.13) | – |
| Mendelian or ClinVar pathogenic | 245 (131) | 29% / 16% | 16% | 1.75 (1.30–2.35) | 1.71 (1.11–2.62) | 1.76 (1.02–3.03) |
| Mendelian, top-tier curation | 158 (89) | 32% / 17% | 11% | 2.10 (1.46–3.03) | 1.81 (1.04–3.13) | – |
| Somatic cancer driver | 333 (103) | 23% / 17% | 17% | 1.42 (0.99–2.03) | – | 1.48 (1.02–2.14) |
| Somatic driver, direction matches the drug | 226 (70) | 21% / 17% | 11% | 1.17 (0.77–1.77) | – | 1.12 (0.72–1.75) |
| Mouse model (literature) | 498 (281) | 23% / 16% | 26% | 1.29 (1.00–1.68) | 1.30 (0.97–1.72) | 1.16 (0.60–2.24) |
| Mouse model, top-quartile phenotype match | 308 (184) | 22% / 17% | 15% | 1.15 (0.89–1.49) | 1.08 (0.77–1.51) | 0.95 (0.55–1.64) |
| Expressed differently in the disease | 358 (198) | 18% / 17% | 15% | 1.05 (0.70–1.58) | 0.66 (0.35–1.22) | 1.33 (0.84–2.10) |
| Disease pathway (Reactome) | 66 (32) | 27% / 17% | 4% | 1.50 (1.00–2.25) | – | – |
| **Clinical precedent** |  |  |  |  |  |  |
| Approved drug on the target, related disease | 763 (269) | 29% / 12% | 50% | 2.18 (1.65–2.88) | 2.16 (1.58–2.95) | 2.05 (1.11–3.78) |
| Approved drug on the target, any disease | 1,557 (439) | 21% / 13% | 72% | 1.85 (1.48–2.32) | 1.68 (1.26–2.24) | 2.28 (1.50–3.47) |
| **Target liabilities** (not specific to the disease) |  |  |  |  |  |  |
| Essential in most cell lines | 22 (19) | 14% / 18% | 1% | 0.96 (0.32–2.89) | – | – |
| Intolerant of loss of function | 464 (160) | 17% / 18% | 18% | 1.00 (0.76–1.32) | 1.26 (0.89–1.78) | 0.82 (0.54–1.25) |
| Mouse knockout dies before weaning | 1,178 (411) | 17% / 18% | 47% | 0.98 (0.79–1.21) | 0.96 (0.72–1.26) | 0.97 (0.67–1.41) |

![Evidence map](report/output/figures/s3_evidence_map.png)

* **Human genetics.** Mendelian and ClinVar evidence for the disease (1.75; top-tier curation 2.10) and GWAS (1.52) both carry the signal. Within GWAS, the locus-to-gene score did not grade it: the best score at 0.8 or above gives 1.38, 0.5–0.8 gives 0.95 and below 0.5 gives 2.11, each from a few dozen programs. Most GWAS rows in Open Targets are on measurement traits (LDL cholesterol, blood pressure, body-mass index) with no MONDO disease; they count as germline evidence on the target but cannot match a disease, so G3 undercounts genetics found through a trait. Gene burden results start in 2019, too late for these cohorts.
* **Somatic drivers.** In oncology, a somatic driver for the tumour raised the chance of advancing (1.48, 1.02–2.14); requiring the driver's direction to match the drug's did not sharpen it (1.12). Germline genetics for the tumour type was the stronger signal (1.98), carried by well-validated targets such as EGFR, ERBB2 and ESR1.
* **Mouse models.** Literature-curated (MGI) mouse models of the disease gave 1.29 (1.00–1.68), and a top-quartile phenotype match 1.15. Each MGI model is dated by its first paper, and each knockout from the IMPC consortia by the first IMPC data release with calls for it (2015 at the earliest).
* **Expression and pathways.** Differential expression in the disease carried nothing (1.05; outside oncology 0.66). Reactome pathway evidence gave 1.50 from 66 programs, most of them in hereditary diseases, which Reactome curates. CRISPR-screen evidence matched only 5 programs before entry: Project Score was first released in 2019, when most of this cohort had already entered Phase 2.
* **Clinical precedent.** An FDA-approved drug on the target for a related disease (Lin similarity ≥ 0.5) was the strongest single predictor (2.18) and was present for 50% of the programs that advanced.
* **Target liabilities.** Essentiality across cell lines could be known only for the 22 programs that entered Phase 2 in 2020, after DepMap first published its common-essential list, too few to judge (0.96, 0.32–2.89); loss-of-function intolerance (1.00) and lethality of the mouse knockout (0.98) made no difference.

**What the evidence leaves out.** Of the 442 Phase 2 programs that advanced, 24% had germline genetics for the disease, 48% had any of the disease-specific evidence families, and 30% had neither such evidence nor an approved drug on the target for a related disease.


### By endpoint

| Class of the governing primary endpoint | Trials | Missed primary endpoint | Trials with genetics for the disease | Missed: with / without genetics | Risk ratio of a miss, all readable trials (95% CI) | Risk ratio, registry-posted results (FDAAA era) |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Target engagement | 35 | 26% | 17 | 18% / 33% | – | – |
| Exploratory biomarker | 272 | 68% | 33 | 70% / 67% | 1.06 (0.80–1.42) | – |
| Regulatory surrogate (LDL-C, HbA1c, viral load…) | 1,329 | 24% | 284 | 13% / 27% | 0.68 (0.47–0.98) | 0.45 (0.32–0.63) |
| Objective physiology (6MWD, visual acuity, weight…) | 546 | 45% | 105 | 33% / 48% | 0.86 (0.63–1.17) | 0.84 (0.56–1.28) |
| Clinician-rated scale or responder index | 1,444 | 55% | 245 | 42% / 57% | 0.73 (0.60–0.89) | 0.76 (0.61–0.95) |
| Patient-reported outcome | 642 | 56% | 17 | 59% / 56% | 1.24 (0.88–1.73) | – |
| Disease events (relapses, exacerbations…) | 365 | 44% | 57 | 40% / 45% | 0.90 (0.60–1.33) | 0.94 (0.61–1.45) |
| Hard outcome (death, MI, stroke…) | 184 | 63% | 19 | 53% / 64% | – | – |
| Tumour response | 168 | 67% | 35 | 57% / 70% | 0.86 (0.62–1.19) | 0.72 (0.46–1.11) |
| Progression-free survival | 447 | 61% | 91 | 53% / 63% | 1.09 (0.88–1.36) | 1.05 (0.79–1.39) |
| Overall survival | 219 | 68% | 22 | 50% / 70% | – | – |

![Endpoint classes](report/output/figures/s3_endpoints.png)

Across 5,674 randomised industry efficacy trials, 48% missed their governing primary endpoint. Regulatory surrogates were missed least (24%); outside oncology, exploratory biomarkers (68%) and hard outcomes (63%) were missed most, and oncology's response and survival endpoints as often.

Genetic support for the disease lowered the chance of a miss most on regulatory surrogates (risk ratio 0.68; 0.45 in trials with registry-posted results since FDAAA) and on clinician-rated scales (0.73). Objective physiology (0.86) and disease events (0.90) point the same way with intervals spanning 1; exploratory biomarkers (1.06), patient-reported outcomes (1.24, only 17 genetically supported trials) and oncology's response and progression endpoints show no benefit. Too few genetically supported trials had hard-outcome or overall-survival primaries to estimate. One reading is that genetic support predicts most reliably that a drug will move the measures nearest its biology, often the trait through which the genetics was found (LDL cholesterol, urate, glycaemia), and less reliably that it will change what patients feel or how often events happen.

At the program level, classifying each Phase 2 program by the endpoint of its first randomised Phase 2 efficacy trial (started within a year of entry and before it advanced), genetic support gives 1.32 (0.76–2.28; 296 programs) where that endpoint was proximal and 1.40 (0.83–2.36; 624) where it was intermediate; distal-endpoint and oncology programs had too few genetically supported targets to estimate.

The endpoint classifier read each trial's registered primary outcomes without the drug. In an audit of 40 trials stratified by class, it picked the governing outcome correctly in 40 and the class in 39. Not knowing the drug, it cannot apply the codebook's drug-specific rules: FEV1 is a regulatory surrogate only for bronchodilators, and target engagement means the drug's own target. Trials still in follow-up that have posted results have no outcome label yet and are not counted (168, against 5,674 in the analysis).


### Direction of effect

A drug that lowers its target's function should help when loss of function protects against the disease or gain of function causes it, and harm or do nothing when loss of function causes it. Open Targets' direction fields cannot test this: they label each variant from its predicted consequence, so the few truncating ClinVar variants listed for PCSK9 in hypercholesterolaemia, MYH7 in hypertrophic cardiomyopathy or TTR in amyloidosis make these gain-of-function diseases read as loss of function; their many pathogenic missense variants carry no direction at all.

We therefore had an LLM state, for every target and disease with germline evidence, without being told any drug, whether disease-causing variants lower or raise the gene's function, whether protective variants are known, and the year each was first shown for that disease. Where Gene2Phenotype records an absent gene product, the label was loss of function in 55 of 58 pairs and gain of function in 0. A spot check of an earlier version of the labels found somatic cancer mutations counted as germline and some years taken from another disease; the final prompt rules out both.

Sponsors almost never develop against an established mechanism. Of the Phase 2 programs with genetic support, 189 acted in the direction the genetics favoured, 6 against it, and 111 had genetics without an established direction by entry. Concordant programs advanced at 29% and undirected ones at 26%: once there is genetic support, knowing its direction did not pick winners among the programs sponsors chose to run, and the discordant group is too small to show whether going against the genetics fails. Protective loss of function plus a drug that lowers function, the PCSK9 pattern, covered 36 Phase 2 programs on 16 targets, which advanced as often as others (1.03, 0.56–1.92).

Mouse models were treated the same way: for each model, without the drug, whether it lowers or raises the gene's function and whether its phenotypes resemble the disease or its opposite. A model pointing the drug's way (a knockout protected from the disease, for an inhibitor) gave 1.33 (0.97–1.83) against programs with no oriented model, a model pointing the other way 1.20, and nothing once genetic support is accounted for (1.02). Among Phase 3 programs a concordant model went with approval within four years (2.38, 1.54–3.69), one of many comparisons made after the plan.


### Models that predict: rules applied at Phase 2 entry

A *model* here is a rule a sponsor could have applied at Phase 2 entry without knowing the outcome: an evidence family, strength, direction and drug action. Rules M1–M11 and the precedent benchmark B1 were fixed in the plan; P1–P3 (marked \*) were added after the plan, once the direction labels existed. Target sets were split 60/40 at random; a rule counts as *particularly predictive* when, on the discovery targets, its risk ratio's 90% bootstrap lower bound is above 1.3, and, on the held-out targets, its risk ratio is at least 1.2 with a one-sided 95% lower bound above 1, and it stays at least 1.2 without its most influential target.

| Rule | Applied at Phase 2 entry | Regime | Programs (targets) | Advanced | Share of all that advanced | Adjusted risk ratio (95% CI) | Risk ratio, discovery targets (90% CI) | Risk ratio, held-out targets (90% CI) | Meets the bar |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| M1 | Protective loss-of-function burden + drug that lowers function | All | 0 (0) | – | 0% | – | – | – | not testable |
| M2 | Mendelian evidence + drug that raises function or replaces the gene | Hereditary | 75 (37) | 25% | 66% | 1.08 (0.61–1.90) | 1.59 (0.95–4.00) | 0.50 (0.18–1.15) | no |
| M3 | Mendelian evidence for a non-hereditary disease | Non-oncology | 57 (44) | 32% | 7% | 1.71 (1.11–2.62) | 1.80 (1.01–2.70) | 2.09 (0.92–3.41) | no |
| M4 | GWAS, locus-to-gene ≥ 0.8 | All | 68 (41) | 25% | 4% | 1.38 (0.90–2.13) | 1.10 (0.60–1.60) | 1.86 (0.99–2.75) | no |
| M5 | GWAS and rare-variant evidence for the same disease | All | 26 (17) | 15% | 1% | 0.78 (0.35–1.72) | 1.08 (0.37–1.80) | none advanced | no |
| M6 | Somatic driver matching the drug + drug that lowers function | Oncology | 215 (67) | 22% | 29% | 1.14 (0.73–1.78) | 1.69 (0.87–3.13) | 0.89 (0.50–1.51) | no |
| M7 | IMPC knockout matching the disease, top quartile | All | 9 (5) | 33% | 1% | – | – | – | no |
| M8 | Literature mouse model of the disease | All | 498 (281) | 23% | 26% | 1.29 (1.00–1.68) | 1.59 (1.19–2.09) | 1.18 (0.86–1.56) | no |
| M9 | Expression up in disease + drug that lowers function | All | 177 (104) | 18% | 7% | 1.00 (0.63–1.58) | 1.18 (0.70–1.66) | 0.88 (0.35–1.62) | no |
| M10 | Reactome pathway | All | 66 (32) | 27% | 4% | 1.50 (1.00–2.25) | 1.21 (0.75–1.77) | 2.51 (1.29–4.03) | no |
| M11 | Target liability + drug that lowers function | All | 902 (316) | 18% | 37% | 1.08 (0.86–1.37) | 1.13 (0.85–1.47) | 0.98 (0.70–1.33) | no |
| B1 | Approved drug on the target, related disease (Lin ≥ 0.5) | All | 763 (269) | 29% | 50% | 2.18 (1.65–2.88) | 2.43 (1.95–3.03) | 2.20 (1.72–2.91) | **predictive** |
| P1* | Protective loss of function + drug that lowers function | All | 36 (16) | 19% | 2% | 1.03 (0.56–1.92) | 1.78 (0.73–3.47) | 0.57 (0.00–1.05) | no |
| P2* | Germline mechanism concordant with the drug | All | 189 (97) | 29% | 12% | 1.79 (1.28–2.51) | 1.87 (1.29–2.57) | 1.42 (0.91–1.98) | no |
| P3* | Mouse model direction concordant with the drug | All | 178 (111) | 24% | 10% | 1.29 (0.95–1.75) | 1.72 (1.24–2.32) | 0.92 (0.59–1.30) | no |

![Rule screen](report/output/figures/s3_rules.png)

Only the benchmark met the bar: an approved drug on the target for a related disease (763 programs, 29% advanced; held-out risk ratio 2.20). Among evidence rules:

* **Mendelian evidence for a non-hereditary disease (M3)** came closest: 57 programs on 44 targets, 32% advanced, held-out risk ratio 2.09 (90% lower bound 0.92), but its discovery lower bound (1.01) fell short of 1.3. It covers few programs (7% of the non-oncology programs that advanced).
* **GWAS with locus-to-gene ≥ 0.8 (M4)** and the post-hoc **germline mechanism concordant with the drug (P2)** have adjusted risk ratios of 1.38 and 1.79, but their held-out lower bounds reach 1 or below (0.99 and 0.91).
* **Reactome pathway evidence (M10)** held up on the held-out targets (risk ratio 2.51, 90% lower bound 1.29) but not on the discovery targets (lower bound 0.75); its adjusted risk ratio is 1.50.
* **Literature mouse models (M8)** gave 1.59 on the discovery targets (90% lower bound 1.19) and 1.18 on the held-out targets (90% lower bound 0.86): inconsistent between the two halves.
* **Replacing or activating the gene in a hereditary disease (M2)** advanced at 25%, against 24% for other programs in hereditary diseases.
* Expression up plus an inhibitor (M9), target liability plus an inhibitor (M11), the allelic series (M5), protective loss of function plus an inhibitor (P1) and a concordant mouse model (P3) carry no consistent signal. Protective-variant burden evidence (M1) could not be tested, because Open Targets has no burden results before 2019, and IMPC knockouts matching the disease (M7) covered 9 programs, too few to estimate.


### Verified case studies

The plan's protocol picked cases for the benchmark B1, the only rule that met the bar, and, beyond the plan, for every rule whose adjusted risk ratio's lower bound is above 1 (M3, M4, M10 and P2): four successes and four failures at random, up to two programs of each of the three most influential targets, and up to six programs that stopped after a randomised trial missed its primary endpoint (the plan asked for all such programs; the cap keeps every case checkable against primary sources). In all, 75 cases on 62 programs were checked. For each program one agent established the outcome from registry records, company filings, papers and FDA documents without seeing the evidence, another checked the evidence claim without seeing the outcome, a second coder classified each failure independently, and a third agent adjudicated any disagreement.

The pipeline's outcome was right for 58 of 62 programs. In each of the 4 errors the program advanced and the pipeline missed it: Phase 3 trials registered under another condition (sabizabulin's COVID-19 trial in patients at risk of ARDS; pegadricase's gout trials, against a program mapped to purine metabolism disease), Phase 3 trials run in China and never registered on ClinicalTrials.gov (pruxelutamide), and a Phase 3 the pipeline did not link to the program (eneboparatide's CALYPSO). The evidence claim held for 49 of 75 cases and partly for 19 more (usually because the source matched a broader or neighbouring disease, or the earliest paper predated the row's date), and failed for 7. Of the 30 programs that did not advance, 16 failed for reasons that test the evidence's biology (F2–F5: engagement without benefit, the wrong population, a surrogate gap, on-target toxicity); the rest stopped because exposure or engagement was never shown (F1), on trial design (F7), off-target toxicity (F6) or commercial grounds (F8), which say nothing about whether the evidence was right, and a few are still progressing or unexplained.

| Rule | Cases | Advanced within 4 years (verified) | Evidence claim verified | Evidence published before entry | Why the others stopped (codes) |
| :---- | :---- | :---- | :---- | :---- | :---- |
| M3 Mendelian evidence for a non-hereditary disease | 18 | 9 | 15 (5 partly) | 16 | F2: 4, F3: 2, unknown: 2, F1: 1 |
| M10 Reactome pathway | 17 | 9 | 13 (3 partly) | 13 | F2: 4, F8: 1, F6: 1, unknown: 1, F1: 1 |
| B1 Approved drug on the target, related disease (Lin ≥ 0.5) | 20 | 13 | 20 (5 partly) | 20 | F2: 4, F8: 2, F7: 1 |
| P2* Germline mechanism concordant with the drug | 20 | 10 | 20 (6 partly) | 20 | F2: 5, F8: 2, F6: 2, F1: 1 |

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

Per-source detail (who compiles each source, what the pipeline keeps, raw response shape and a sample record) and the full Section 3 case table are in the Appendix detail tab.

### How LOA moves with each definition

| Cohort or definition | Phase 1 → 2 | Phase 2 → 3 | Phase 3 → approval | LOA (95% CI) |
| :---- | :---- | :---- | :---- | :---- |
| All programs | 54.8% | 28.4% | 34.9% | 5.4% (4.9–6.0) |
| Programs with a US-sited industry trial in the phase | 57.0% | 31.3% | 50.0% | 8.9% (8.0–9.9) |
| Entity not yet FDA-approved at phase entry | 54.5% | 26.9% | 35.8% | 5.3% (4.6–5.9) |
| Entity already FDA-approved for another disease | 55.8% | 37.9% | 32.5% | 6.9% (5.4–8.7) |
| Suspension lag 12 months | 53.9% | 27.7% | 34.2% | 5.1% (4.6–5.7) |
| Suspension lag 18 months | 54.2% | 28.0% | 34.6% | 5.2% (4.7–5.8) |
| Suspension lag 36 months | 56.0% | 29.2% | 36.2% | 5.9% (5.3–6.6) |
| Uncertain approvals counted as approved | 54.8% | 28.4% | 35.0% | 5.4% (4.9–6.1) |
| Shared trials mark entry for every program of the entity | 74.2% | 44.6% | 33.4% | 11.0% (9.4–12.8) |
| Including vaccines | 53.3% | 27.9% | 32.6% | 4.8% (4.3–5.4) |
| Phase entry 2015-2025 (many programs still running) | 54.5% | 33.8% | 38.1% | 7.0% (6.2–7.8) |
| Phase entry 2015-2025, developed in the US | 54.4% | 33.8% | 53.1% | 9.8% (8.7–10.9) |

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

Each error pattern these audits found was fixed in the pipeline and the affected labels re-derived, not patched by hand: diseases MONDO has no exact term for now map to their nearest broader term; development codes resolve to UNII substances, and the same substance under two names is merged; scanned FDA letters are read by OCR; labelling-only supplements no longer count as approvals; stop reasons stated only in a trial's summary are read; publication-based outcomes use only the abstracts given; and approval dates account for older applications of the same drug. The disease-mapping, entity and approval figures above come from fresh samples drawn after those fixes; before them, disease mapping agreed 94% of the time, entity resolution 95%, and 8 of 25 dated first approvals were wrong. Remaining entity errors are scattered (a development code resolved to the wrong substance, a salt chosen over its parent) rather than systematic. Programs whose approval is judged "uncertain" (106 of 24,339 judgements) count as not approved; counting them as approved instead moves no rate by more than a tenth of a percentage point (sensitivity table). The approval audit's strata are those of the judgements it sampled; it was re-scored after the final rebuild against the auditors' own answers, and programs that are no longer development programs left the sample. The audit of the earlier draft, with every claim's verdict and every data issue, is in `AUDIT.md`.

Two labels were also re-decided rather than re-derived. Trial purposes and roles, re-decided under a second prompt version, agree with the first on 98% and 97% of trials. Disease mapping, decided twice, chose the same MONDO term for 92% of conditions. Modality, disease area and targets were not audited. The Section 3 endpoint classes were audited on a seeded sample of trials, and the mechanism and mouse-model labels were spot-checked (Section 3).

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
