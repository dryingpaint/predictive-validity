# Research prompts behind Draft 4

Run 2026-11-18 as three parallel Claude Code subagents (general-purpose, with web search and fetch). Each prompt is
reproduced exactly.

## 1. Case studies by failure mode

```
You are researching drug-development case studies for a scientific report on why drugs that engage their target in patients still fail. Use web search and fetch primary sources (PubMed, journal pages, FDA, company releases). Every factual claim must come from a source you actually read; give each source as "Author et al. Year" plus a DOI or URL. If you cannot verify a fact, say so rather than guessing. Do not invent numbers.

The report classifies failures of drugs that engaged their target without benefit into modes: A (target does not drive the disease), B (target drives the disease but not in these patients or at this stage), C (target drives it, drug fell short: C1 too little engagement, C2 on-target effects in another tissue cap the dose, C3 off-target effects), D (trial could not answer: underpowered, too short, wrong endpoint).

Write each case in this style: plain, past tense, short declarative sentences, no em dashes, no hype words ("significantly" only in the statistical sense), numbers given exactly with their source. Heading format: "[Disease], [drug mechanism]: [core supporting evidence]. [core failed endpoint]." Then 2-4 paragraphs: the evidence that made the target look right, what the trials showed (endpoint, numbers), and a closing sentence naming the mode and why.

Deliverables:

1. BACE1 inhibitors in Alzheimer's: answer each question precisely with sources, in 1-3 sentences each:
   a. In the 1980s, which findings established that plaques are made of amyloid-beta (Glenner & Wong 1984, Masters et al. 1985), and what data led Hardy & Higgins (1992) to propose the amyloid cascade hypothesis (APP mutations in familial AD, Down syndrome, etc.)?
   b. What did verubecestat (EPOCH, APECS), lanabecestat (AMARANTH, DAYBREAK-ALZ), atabecestat (EARLY) and umibecestat (Generation) trials read out: primary endpoints, whether amyloid PET/plaque fell, and the cognitive results?
   c. Was dose the problem? What CSF Abeta reduction did each achieve, and did lower doses also cause worsening? Did the investigators conclude the dose was too high or the mechanism wrong?
   d. Does BACE1 inhibition reduce existing plaque or only prevent new plaque, in mice and in people (amyloid PET in EPOCH/APECS)? Why (production versus clearance)?
   e. A673T carriers: what lifetime Abeta reduction, and what does that imply for the timing of treatment (primary prevention)?
   f. Was safety what stopped the trials (futility versus cognitive worsening versus liver toxicity for atabecestat)?
   g. A one-paragraph verdict on why the class failed.

2. Mode B cases (write each up fully):
   a. Mepolizumab in asthma: Flood-Page et al. 2007 failure in unselected moderate asthma; DREAM (Pavord 2012) and MENSA (Ortega 2014) in eosinophilic asthma; approval 2015.
   b. Onartuzumab in NSCLC: the Phase 2 MET-IHC subgroup (Spigel 2013), METLung Phase 3 (Spigel 2017) results; contrast with capmatinib and tepotinib in MET exon 14 skipping.
   c. One sepsis case where timing or patient selection was the problem (e.g., anti-TNF or anti-endotoxin trials, or another well-documented one); verify carefully.

3. Mode C1: BTK inhibitors in rheumatoid arthritis: fenebrutinib Phase 2 (Cohen et al. 2020), BMS-986142 (Gillooly? check the RA trial publication), poseltinib (check publication), evobrutinib RA Phase 2, and what investigators said about occupancy. Also angiotensinogen in hypertension: IONIS-AGT-LRx (check the drug's name; the draft says "evazarsen", verify) Phase 2 results versus zilebesiran KARDIA-1 (Bakris 2024). Verify all numbers in this draft text and correct them: "BMS-986142: trough drug levels showed little BTK inhibition across the dosing interval, and levels varied widely; poseltinib occupancy 70% at 5 mg and 90% at 30 mg, no dose beat placebo on ACR20 (placebo 48%, doses 44-55%); evazarsen lowered AGT 54-67%, no BP effect; zilebesiran lowered AGT ~90% and lowered BP."

4. Mode C3: torcetrapib (ILLUMINATE, Barter 2007): deaths, events, aldosterone/BP mechanism; then dalcetrapib, evacetrapib, anacetrapib (REVEAL) outcomes.

5. Mode D: one well-documented case where a trial was underpowered, too short or used the wrong endpoint, and a later trial of the same drug or another drug on the same target succeeded in the same disease. Verify.

Return all of this as finished prose ready to paste, followed by a list of the sources you read for each case, and a list of any claims you could not verify.
```

## 2. Literature for the Discussion

```
You are researching the published evidence for the Discussion of a scientific report on predictive validity in drug development. The report's own data: of Phase 2-3 stops 2008-2019, 20% were drugs that engaged their target without benefit; human rare-variant genetics lowers "target not causal" failures, while mouse genetics, diseased-tissue expression changes, and the drug's potency do not. Use web search and fetch primary sources. Every number must come from a source you actually read; cite as "Author et al. Year" with DOI or URL. Flag anything you could not verify. No invented numbers.

Answer these, each with the key quantitative findings (2-6 sentences per item) and sources:

A. Limits of the single-target paradigm:
 1. Phenotypic versus target-based discovery of first-in-class drugs: Swinney & Anthony 2011 (Nat Rev Drug Discov) counts for 1999-2008; Eder, Sedrani & Wiesmann 2014 update for 1999-2013; any later update (e.g., Moffat et al. 2017, Vincent et al. 2022 on phenotypic drug discovery).
 2. Polypharmacology of approved drugs: average number of targets per approved drug (e.g., Mestres et al., Hopkins 2008 "Network pharmacology"), and the share of approved drugs whose mechanism was unknown or multi-target at approval.
 3. Genetic architecture: what share of common disease heritability lies in large-effect loci versus a diffuse polygenic tail (Boyle, Li & Pritchard 2017 omnigenic model; estimates of number of causal variants for schizophrenia, height, T2D, etc.); share of diseases with known Mendelian forms (OMIM counts); how often GWAS loci point to druggable genes (e.g., Finan et al. 2017 druggable genome).
 4. Any published estimate of what fraction of disease burden or diseases could plausibly be treated by modulating a single target.

B. Why non-genetic target-ID evidence fails:
 5. Mouse models: concordance of mouse knockout phenotypes with human loss-of-function phenotypes; Seok et al. 2013 (PNAS, inflammation transcriptomes); Perrin 2014 (Nature, ALS mouse studies); Hackam & Redelmeier 2006 (animal studies translation); any quantitative estimates of translation rates from animal efficacy studies to human trials.
 6. Diseased-tissue expression changes: evidence they are consequences rather than causes of disease (e.g., Mendelian randomization or eQTL studies showing differential expression is mostly reactive; Porcu et al. 2021 or similar).
 7. Functional genomic screens (CRISPR/RNAi): reproducibility and translation evidence (e.g., RNAi off-target issues; Lin et al. 2019 Sci Transl Med showing cancer drug targets whose CRISPR knockout does not affect fitness; DepMap-based target validation).
 8. Any estimate of how much target selection, versus other causes, explains attrition (e.g., Cook et al. 2014 AZ 5R; Morgan et al. 2018).

C. Minimal model systems and phenotypic screening:
 9. Published frameworks for judging whether a model system has predictive validity (Scannell & Bosley 2016; Scannell et al. 2022 "Predictive validity in drug discovery: what it is, why it matters and how to improve it"; the "chain of translatability" of Vincent et al. 2015).
 10. Examples where organoids, human challenge models or humanized mice predicted clinical efficacy prospectively.

Return a structured summary by item, then a single consolidated source list, then the unverified claims.
```

## 3. History of drug development

```
Write a short history of drug discovery (4-6 paragraphs, about 500-700 words) for the introduction of a scientific report on the predictive validity of preclinical evidence. Research it with web search and primary or authoritative secondary sources; cite as "Author et al. Year" with DOI or URL; every date and fact must come from a source you read, and list anything you could not verify.

The report's figure shows these eras, each narrowing the unit of the biological hypothesis:
1. Observation, natural products, physiology (to ~1935): therapeutic effect or organismal phenotype (morphine, quinine, digitalis, aspirin).
2. Quantitative pharmacology and biochemistry (~1900-1965): receptor activity, enzyme, metabolic pathway (sulfonamides, receptor theory, enzyme inhibitors).
3. Systematic medicinal chemistry (~1950-1985): desired pharmacological mechanism (beta-blockers, H2 antagonists, antimetabolites; Black, Elion & Hitchings).
4. Recombinant DNA and molecular cloning (~1970-1995): named gene and protein (recombinant insulin, cloned GPCRs, channels, kinases).
5. Genomics, high-throughput screening, automation (~1990-2005): target plus compound library (imatinib, genomic target portfolios).
6. Human genetics and functional genomics (~2000-2015): target-disease association (GWAS, RNAi, CRISPR, dependency maps).
7. Multimodal evidence and predictive modelling (2010-): target-indication-mechanism-patient context (Open Targets, gnomAD, single-cell perturbation, AlphaFold).

For each era say what experiment decided whether a molecule was worth taking forward, i.e. what the "model system" was (whole animals and patients early on; isolated tissues and receptor binding; cell-based and biochemical assays; target-based HTS), and note what was lost as the unit narrowed. Include where large-scale in-vivo screening fits (e.g., Paul Janssen's animal pharmacology screening, zebrafish screens). Include Scannell et al. 2012 (Eroom's law) and the observation that productivity fell as screening throughput rose; and Swinney & Anthony 2011 on first-in-class drugs from phenotypic screens.

Style: plain, past tense, short declarative sentences, no em dashes, no metaphors, no hype words. Return the prose, then the source list, then unverified claims.
```
