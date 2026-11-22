# Appendix detail

<!-- Rendered by `python -m report` into REPORT_APPENDIX.md, the doc's "Appendix detail" tab. -->

## Definitions

What each cause of a stop, and each kind of evidence, means in the main tab.

### Why programs stop: causes and subcauses

Every stop has one cause; where a source gives more detail, one subcause from the cause's list, the first listed winning when more than one applies. A stop no source explains is described by what the drug and its sponsor did next.

| Cause | Subcause | Definition |
| :---- | :---- | :---- |
| **Efficacy or exposure (PK, dose, formulation)** |  | No or too little efficacy: futility, a missed primary endpoint, or efficacy not competitive with the standard of care; or a failure of exposure, pharmacokinetics, dose or formulation |
|  | Not engaged | Exposure or engagement too low, or another drug on the target worked |
|  | Engaged, no benefit | Target or mechanism wrong for the disease as tested |
|  | Trial design, population, endpoint | Trial design, population or endpoint, mechanism not in question |
|  | No engagement data | No human evidence of engagement either way |
| **Safety** |  | Adverse events, poor tolerability, a safety signal, or a clinical hold for safety |
|  | On-target toxicity | The text ties the harm to the drug's mechanism, to hitting its target |
|  | Off-target toxicity | The text ties the harm to the molecule rather than the target (off-target binding, metabolites, the formulation) |
|  | Animal toxicology finding | A toxicity finding in animal or laboratory studies stopped it, with no mechanism stated (a need for more preclinical work that names no toxicity is "not stated") |
|  | Harm in patients, mechanism not stated | Harm or a safety signal seen in people in a trial, named or not (liver injury, deaths, side effects patients would not tolerate, an unfavourable benefit-risk), with no mechanism stated |
|  | Other stated reason | The text gives a specific reason that none of the listed subcauses covers, each read broadly |
|  | Not stated | The text gives no more detail than the cause: 'strategic reasons', 'a change in strategy', 'business' or 'administrative reasons', or a safety concern without saying whether it was seen in people or animals |
| **Sponsor decision (portfolio, commercial, partner, acquisition, funding or closure)** |  | The sponsor chose to stop or could not go on: other programs put first, commercial or competitive reasons, a partner leaving, an acquisition or merger, or running out of money |
|  | Acquisition or merger | The sponsor was acquired or merged and the program was dropped |
|  | Funding or closure | The sponsor or the trial ran out of money (including a grant that ended), or the sponsor wound down, went bankrupt or closed |
|  | Partner exit or none found | A licensing or development partner ended the deal or handed the rights back, or the sponsor was looking for a partner to take it forward and none did |
|  | Replaced by a successor | Development moved to another formulation, dose form, combination or follow-on drug |
|  | Regulator asked for more trials | A regulator required further trials or data and the sponsor did not go on |
|  | Commercial or competitive | The market, pricing, reimbursement, a competing drug, a change in the standard of care or a change in the clinical landscape made it not worth pursuing |
|  | Portfolio prioritisation | The text says the sponsor chose to put its resources into other programs, areas or indications |
|  | Other stated reason | The text gives a specific reason that none of the listed subcauses covers, each read broadly |
|  | Not stated | The text gives no more detail than the cause: 'strategic reasons', 'a change in strategy', 'business' or 'administrative reasons', or a safety concern without saying whether it was seen in people or animals |
| **Operational (enrollment, sites, supply, regulatory)** |  | Running the trial failed: enrollment, sites or drug supply, COVID-19, a regulatory or procedural hold not about safety, or a trial redesigned or replaced |
|  | COVID-19 | The COVID-19 pandemic disrupted the trial |
|  | Regulatory hold on the trial | A regulatory or procedural requirement or hold, not about safety, stopped the trial itself |
|  | Trial redesigned or replaced | The trial was stopped to be redesigned or replaced by another trial of the same drug, or its design could not answer the question |
|  | Enrollment | Patients could not be recruited or retained fast enough |
|  | Sites or supply | Running the trial: sites, investigators or staff, drug supply, manufacturing for the trial, trial procedures or measurements, delays, or other logistics |
|  | Other stated reason | The text gives a specific reason that none of the listed subcauses covers, each read broadly |
|  | Not stated | The text gives no more detail than the cause: 'strategic reasons', 'a change in strategy', 'business' or 'administrative reasons', or a safety concern without saying whether it was seen in people or animals |
| **Positive readout, not yet advanced** |  | The trial met its primary endpoint and the program still did not move on in the disease |
|  | Regulator declined approval | A regulator (the FDA, the EMA, China's NMPA or another) declined to approve it |
|  | Acquisition or merger | The sponsor was acquired or merged and the program was dropped |
|  | Funding or closure | The sponsor or the trial ran out of money (including a grant that ended), or the sponsor wound down, went bankrupt or closed |
|  | Partner exit or none found | A licensing or development partner ended the deal or handed the rights back, or the sponsor was looking for a partner to take it forward and none did |
|  | Replaced by a successor | Development moved to another formulation, dose form, combination or follow-on drug |
|  | Regulator asked for more trials | A regulator required further trials or data and the sponsor did not go on |
|  | Commercial or competitive | The market, pricing, reimbursement, a competing drug, a change in the standard of care or a change in the clinical landscape made it not worth pursuing |
|  | Portfolio prioritisation | The text says the sponsor chose to put its resources into other programs, areas or indications |
|  | Approved outside the US | The drug was approved, or filed, outside the United States, and no other reason is given |
|  | Other stated reason | The text gives a specific reason that none of the listed subcauses covers, each read broadly |
|  | Not stated | The text gives no more detail than the cause: 'strategic reasons', 'a change in strategy', 'business' or 'administrative reasons', or a safety concern without saying whether it was seen in people or animals |
| **Unknown** |  | No source gives the cause or allows a reasoned inference; described instead by what the drug and its sponsor did next |
|  | Sponsor started no later trial | The sponsor started no registered trial more than 12 months after the stop |
|  | Drug approved in another disease | The drug has an FDA approval for another disease |
|  | Drug continued in other diseases | The drug went on in other diseases |
|  | Drug dropped, sponsor active | None of these: the drug went no further while its sponsor stayed active |
| **Did not actually stop** |  | Development went on under another registry, region, name or combination, or the FDA approved the drug for the disease |
| **Not a development program** |  | An academic study using an approved drug as a research tool, or a drug-interaction or dosing study |

### Kinds of evidence

Each program is scored for the evidence its targets had for its disease as of the year before it entered the phase.

| Evidence | What counts | Source and dating |
| :---- | :---- | :---- |
| **Human genetics** |  |  |
| Human genetics | Inherited variants link the target to the disease (GWAS, gene burden, Mendelian): the program's disease, a subtype of it or a disease at least 0.8 similar on MONDO (Lin) | Open Targets 26.09 (GWAS credible sets, gene burden tests, ClinVar, PanelApp, Orphanet, Gene2Phenotype, ClinGen, UniProt); each item dated by when it became known |
| Tumour genetics (oncology) | The gene is recurrently mutated in this cancer (oncology only) | COSMIC Cancer Gene Census, IntOGen and ClinVar somatic, through Open Targets |
| Curated pathway | A curated pathway shows a disease mutation disrupting the target | Reactome, through Open Targets |
| **In vitro and ex vivo** |  |  |
| Cell lines | Changing the target in an established cell line changes a disease feature. Today only knockout screens reach it: in screens published before entry, cancer cell lines of the program's tumour type need the gene (oncology entries from 2015); the literature is to come (#154) | DepMap and earlier RNAi and CRISPR dependency screens, each line dated by its first public release; Project Score through Open Targets, 2019 at the earliest |
| Diseased tissue | The gene's RNA or protein level differs in diseased tissue (protein is to come, #154) | Expression Atlas, through Open Targets (RNA, at least 2.1-fold) |
| **Animals** |  |  |
| Mouse genetics | A genetic change in an animal links the target to the disease: the mutant shows the disease (a knockout or transgene altering an animal model of it is to come, #154) | IMPC knockouts (dated by first data release) and MGI lines (dated by first paper), matched by PhenoDigm |
| Animal model pharmacology | A non-genetic change to the target (drug, antibody, siRNA) alters an animal model of the disease, whatever the agent; today only published studies of the program's own drug are searched, other agents are to come (#154) (exploratory: the searches miss some of these studies) | PubMed abstracts and Firecrawl's research index, screened by an LLM |
| **Human** |  |  |
| Validated at entry | A drug on the target was already approved for the same or a very close disease (Lin at least 0.8) before entry | Drugs@FDA approvals |
| A drug on the target approved for another disease | A drug on the target was approved for another disease, one not close enough to make the pair validated at entry | Drugs@FDA approvals |
| Another drug on the target failed in a related disease in the last 3 years | Another drug on the target had a Phase 2 or 3 trial in a related disease (Lin at least 0.5) miss its primary endpoint or stop for futility in the three years before entry | ClinicalTrials.gov |
| **The drug** |  |  |
| Binding to the target measured before entry (about the drug) | The drug's binding or activity at its primary target was measured in laboratory assays before entry (small molecules) | ChEMBL 37, each measurement dated by the paper, patent or dataset that reported it |
| Pharmacokinetics or target engagement measured in healthy animals (about the drug) | A published study of the drug's pharmacokinetics, or of its effect on its target or pathway, in healthy animals (exploratory: the searches miss some of these studies) | PubMed abstracts and Firecrawl's research index, screened by an LLM |
| Drug shown to act on its target in people (about the drug) | A published study showing the drug acting on its target in people (exploratory) | PubMed abstracts, screened by an LLM |
| Molecule properties (about the drug) | Drug-like size and chemistry (no more than one Lipinski violation); for brain diseases, chemistry suited to entering the brain (TPSA under 90, weight under 450, at most 3 donors) | PubChem and ChEMBL computed properties |
| **Target safety risk** |  |  |
| Any standard safety flag (aggregate) | A property of the target, not evidence for the disease: people rarely carry broken copies of the gene (gnomAD LOEUF below 0.35), mice without it die before weaning, or most human cell types need it | gnomAD v4.1; Mammalian Phenotype ontology, through Open Targets; DepMap |

## Tables behind the figures

The numbers each figure in the main tab draws, with the columns the figures leave out.

### Phase transitions

| Transition | All programs (95% CI) | Developed in the US (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- |
| Phase 1 → Phase 2 | 57.8% (55.9–59.4), n=6,141 | 58.9% (56.4–61.4), n=3,883 | 52.0% |
| Phase 2 → Phase 3 | 31.0% (29.6–32.4), n=5,977 | 33.1% (31.3–34.8), n=3,899 | 28.9% |
| Phase 3 → Approval | 41.7% (39.1–44.4), n=1,912 | 55.6% (52.4–58.7), n=1,353 | 52.4% |
| **Phase 1 → Approval (LOA)** | **7.5%** (6.7–8.3) | **10.8%** (9.7–12.0) | **7.9%** (novel drugs 6.8%) |

### Why programs stop

Cause of each Phase 2 and 3 stop as registered and after tracing.

| Cause of the stop | As registered | After tracing: sourced | After tracing: sourced or likely |
| :---- | :---- | :---- | :---- |
| Efficacy or exposure (PK, dose, formulation) | 29% (1,589) | 41% (2,236) | 46% (2,478) |
| Safety | 1% (68) | 4% (207) | 4% (217) |
| Sponsor decision (portfolio, commercial, partner, acquisition, funding or closure) | 5% (270) | 12% (646) | 20% (1,103) |
| Operational (enrollment, sites, supply, regulatory) | 5% (283) | 6% (316) | 6% (337) |
| Positive readout, not yet advanced | 10% (517) | 17% (923) | 18% (955) |
| Unknown | 50% (2,701) | 15% (815) | 1% (47) |
| Did not actually stop | 0% (0) | 4% (228) | 4% (234) |
| Not a development program | 0% (0) | 1% (57) | 1% (57) |

### Why drugs that engaged their target failed, by disease

A stop where the drug engaged its target without benefit takes one failure mode, decided in order. The target is not causal when no drug on the target has worked in the disease while drugs on it worked elsewhere or were tried again, or when the program's sources judge the only attempt not causal. When a drug on the target worked only in a disease the ontology rates as related, a reading of the two diseases decides whether the success was in a subgroup of this one (wrong patients), a stage of it (wrong time) or a different disease (not causal); of the headline stops it read, nearly all were a different disease. A success in this disease only in biomarker-selected trials, when this program did not select, is wrong patients. Otherwise the verdict read from the program's sources decides: wrong patients, wrong stage or timing, drug inadequate or trial inadequate. Everything else is unresolved, including a "not causal" verdict where another drug on the target worked in this disease, which the record contradicts.

Every disease with at least ten such stops.

| Disease | Area | Stops | Target not causal | Wrong time | Wrong patients | Drug fell short | Trial couldn't answer | Unresolved |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| No disease term (symptom or procedure) | Other | 43 | 95% | 0% | 0% | 0% | 5% | 0% |
| Non-small cell lung carcinoma | Oncology | 37 | 51% | 0% | 8% | 0% | 3% | 38% |
| Asthma | Respiratory | 30 | 43% | 0% | 0% | 3% | 7% | 47% |
| Alzheimer disease | Neurology | 26 | 62% | 0% | 8% | 4% | 0% | 27% |
| Rheumatoid arthritis | Autoimmune | 23 | 65% | 0% | 4% | 9% | 9% | 13% |
| Colorectal cancer | Oncology | 19 | 58% | 0% | 26% | 0% | 5% | 11% |
| Breast cancer | Oncology | 19 | 53% | 0% | 16% | 5% | 0% | 26% |
| Ovarian cancer | Oncology | 18 | 61% | 0% | 11% | 17% | 0% | 11% |
| Ulcerative colitis | Autoimmune | 17 | 65% | 0% | 6% | 6% | 12% | 12% |
| Malignant pancreatic neoplasm | Oncology | 16 | 62% | 0% | 6% | 0% | 0% | 31% |
| Hepatocellular carcinoma | Oncology | 15 | 60% | 0% | 13% | 13% | 13% | 0% |
| Atopic eczema | Other | 15 | 87% | 0% | 0% | 0% | 0% | 13% |
| Small cell lung carcinoma | Oncology | 13 | 69% | 0% | 8% | 0% | 0% | 23% |
| Prostate cancer | Oncology | 13 | 77% | 0% | 0% | 23% | 0% | 0% |
| Schizophrenia | Psychiatry | 13 | 46% | 0% | 0% | 0% | 0% | 54% |
| Type 2 diabetes mellitus | Endocrine | 13 | 23% | 0% | 15% | 15% | 15% | 31% |
| Crohn disease | Autoimmune | 12 | 58% | 0% | 0% | 8% | 25% | 8% |
| Chronic obstructive pulmonary disease | Respiratory | 12 | 58% | 0% | 8% | 0% | 17% | 17% |
| Major depressive disorder | Psychiatry | 12 | 42% | 0% | 8% | 17% | 8% | 25% |
| Acute myeloid leukemia | Oncology | 12 | 58% | 0% | 8% | 8% | 0% | 25% |
| Systemic lupus erythematosus | Autoimmune | 11 | 64% | 0% | 18% | 0% | 18% | 0% |
| Plasma cell myeloma | Oncology | 11 | 64% | 0% | 9% | 9% | 0% | 18% |
| Idiopathic pulmonary fibrosis | Respiratory | 10 | 100% | 0% | 0% | 0% | 0% | 0% |

### Why efficacy failed

Efficacy and exposure stops by what the evidence shows about target engagement, by phase.

| What the evidence shows | Phase 2 | Phase 3 | Phase 2 and 3 | Outside oncology |
| :---- | :---- | :---- | :---- | :---- |
| Not engaged: exposure or engagement too low, or another drug on the target worked | 11% (197) | 11% (51) | 11% (248) | 10% (166) |
| Engaged, no benefit: target or mechanism wrong for the disease as tested | 46% (797) | 50% (240) | 47% (1,037) | 44% (731) |
| Trial design, population or endpoint, mechanism not in question | 6% (104) | 10% (46) | 7% (150) | 8% (129) |
| No engagement data: no human evidence of engagement either way | 36% (624) | 30% (146) | 35% (770) | 38% (620) |
| **Not engaged, of failures whose mechanism was tested** | **20%** (17–23) | **18%** (13–22) | **19%** (17–22) | **19%** (16–21) |
| Programs (entities) | 1,723 (1,336) | 483 (426) | 2,206 (1,643) | 1,647 (1,301) |

### By disease area and modality

| Disease area | All programs, LOA (95% CI) | Entities | Developed in the US, LOA (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- | :---- |
| Hematology | 24.7% (17.6–31.7) | 229 | 30.6% (21.4–40.5) | 23.9% |
| Oncology | 12.8% (10.1–15.5) | 1,807 | 15.0% (11.9–18.5) | 5.3% |
| Metabolic | 12.0% (8.2–16.5) | 268 | 18.3% (12.0–25.1) | 15.5% |
| Allergy | 11.9% (6.1–18.9) | 125 | 20.7% (8.6–34.0) | 10.3% |
| Infectious disease | 10.5% (8.1–13.1) | 640 | 19.2% (15.1–23.9) | 13.2% |
| Autoimmune | 8.9% (6.2–11.6) | 509 | 11.2% (7.6–15.2) | 10.7% |
| Neurology | 8.4% (6.3–10.5) | 751 | 11.7% (8.8–14.7) | 5.9% |
| Endocrine | 8.3% (5.2–11.6) | 319 | 14.9% (9.4–21.3) | 6.6% |
| Psychiatry | 7.9% (4.9–11.3) | 310 | 10.4% (6.4–15.0) | 7.3% |
| Ophthalmology | 7.6% (4.6–11.0) | 318 | 8.0% (4.7–11.5) | 11.9% |
| Respiratory | 6.3% (3.5–9.4) | 347 | 10.8% (6.3–16.0) | 7.5% |
| Other | 5.8% (4.0–7.7) | 725 | 10.5% (7.7–14.0) | 13.0% |
| Cardiovascular | 3.9% (2.0–6.2) | 311 | 6.7% (3.6–10.8) | 4.8% |
| Urology | 3.4% (0.7–7.3) | 78 | – | 3.6% |
| Gastroenterology | 3.4% (1.7–5.5) | 316 | 8.4% (4.5–13.0) | 8.3% |

| Modality | All programs, LOA (95% CI) | Entities | Developed in the US, LOA (95% CI) | BIO 2011–2020 |
| :---- | :---- | :---- | :---- | :---- |
| Monoclonal antibody | 14.8% (11.1–18.8) | 836 | 16.6% (12.2–21.0) | 12.1% |
| Antibody–drug conjugate | 12.0% (5.6–19.1) | 148 | 12.1% (5.3–19.9) | 10.8% |
| Protein | 9.1% (6.5–12.1) | 464 | 11.6% (8.0–15.3) | 9.4% |
| Small molecule | 7.2% (6.4–8.0) | 4,097 | 10.4% (9.2–11.6) | 7.5% |
| Gene therapy | 6.8% (2.7–11.8) | 149 | 8.1% (3.4–14.5) | 10.0% |
| Peptide | 5.0% (2.7–7.9) | 275 | 7.7% (3.9–12.4) | 8.0% |
| Antisense oligonucleotide | 4.0% (1.0–9.0) | 91 | 5.5% (1.5–12.4) | 5.2% |
| Other cell therapy | 2.6% (0.9–5.2) | 270 | 5.4% (2.0–11.5) | – |
| Microbiome or live biotherapeutic | 1.0% (0.0–5.3) | 47 | – | – |
| Other | 0.7% (0.2–1.4) | 272 | 1.9% (0.4–4.6) | – |

### Evidence by kind

Every kind of evidence on US-developed programs, section by section: the kind, the values of its facts, and the lines derived from them, such as evidence agreeing with the drug's direction. The main tab's evidence chart draws each kind and the values of one of its facts.

| Evidence | Entries with it / known | Targets | Relative success to approval (95% CI) | Advancing from Phase 2, adjusted RR | Same, biomarker enrolment held fixed | Stop, adjusted RR |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Human genetics** |  |  |  |  |  |  |
| Human genetics: inherited variants link the target to the disease | 884 / 7,435 | 285 | 2.55 (1.93–3.35) | 1.82 (1.46–2.27) | 1.78 (1.42–2.22) | 0.65 (0.49–0.86) |
| · Rare variants only | 651 / 7,435 | 208 | 2.72 (2.03–3.61) | 2.12 (1.69–2.67) | 2.09 (1.64–2.66) | 0.48 (0.33–0.70) |
| · Common variants only (genome-wide association studies) | 187 / 7,435 | 74 | 1.72 (1.05–2.46) | 1.25 (0.79–1.95) | 1.27 (0.82–1.96) | 0.99 (0.68–1.46) |
| · Both rare and common variants | 46 / 7,435 | 23 | Too rare to estimate | – | – | – |
| · How strong the strongest inherited-variant evidence is (exploratory) | 499 / 7,435 | 176 | 3.06 (2.31–3.93) | 1.96 (1.51–2.55) | 1.90 (1.46–2.47) | 0.55 (0.38–0.80) |
| · Rare inherited variants, including single-gene disease (derived) | 697 / 7,435 | 223 | 2.63 (1.95–3.49) | 1.95 (1.53–2.47) | 1.90 (1.49–2.43) | 0.55 (0.39–0.79) |
| · Common variants (genome-wide association studies) (derived) | 233 / 7,435 | 94 | 1.62 (1.06–2.26) | 1.01 (0.64–1.60) | 1.03 (0.65–1.61) | 1.08 (0.79–1.49) |
| · Genetics agrees with the drug's direction (derived) | 433 / 7,435 | 145 | 2.59 (1.91–3.45) | 1.78 (1.31–2.43) | 1.72 (1.26–2.35) | 0.51 (0.32–0.83) |
| Tumour genetics (oncology): the gene is recurrently mutated in this cancer | 1,061 / 3,582 | 162 | 2.02 (1.14–3.53) | 1.56 (1.08–2.24) | 1.49 (1.03–2.15) | 0.86 (0.65–1.15) |
| · Activating | 743 / 3,582 | 111 | 1.74 (0.97–3.09) | 1.45 (1.01–2.07) | 1.38 (0.96–1.99) | 0.83 (0.60–1.15) |
| · Inactivating | 47 / 3,582 | 13 | Too rare to estimate | – | – | – |
| · Both | 49 / 3,582 | 21 | Too rare to estimate | – | – | – |
| · Mutated, effect unknown | 222 / 3,582 | 47 | 2.09 (0.43–3.80) | 1.86 (1.27–2.75) | 1.83 (1.26–2.66) | 0.76 (0.45–1.26) |
| · The mutation's effect matches the drug's action (derived) | 746 / 3,582 | 110 | 1.76 (0.98–3.16) | 1.46 (1.02–2.09) | 1.37 (0.94–1.98) | 0.88 (0.63–1.22) |
| Curated pathway: a disease mutation disrupts the target's pathway | 195 / 7,435 | 57 | 1.89 (0.93–2.80) | 1.33 (0.92–1.92) | 1.25 (0.87–1.81) | 0.71 (0.35–1.44) |
| **In vitro and ex vivo** |  |  |  |  |  |  |
| Cell lines: changing the target in an established cell line changes a disease feature (oncology, from 2015) | 237 / 1,782 | 62 | 0.55 (0.16–1.38) | 0.56 (0.25–1.25) | 0.57 (0.25–1.28) | 0.55 (0.27–1.13) |
| · A genome-wide knockout screen ranks the target for this cancer, on today's data (hindsight) | 373 / 7,435 | 100 | 1.96 (1.16–2.85) | 1.70 (1.18–2.43) | 1.60 (1.11–2.30) | 0.98 (0.70–1.36) |
| · Cancer cells of this type need the gene to grow (dependency screens) (derived) | 237 / 1,782 | 62 | 0.55 (0.16–1.38) | 0.56 (0.25–1.25) | 0.57 (0.25–1.28) | 0.55 (0.27–1.13) |
| · Gene-knockout screens in human cells (Project Score) (derived) | 0 / 7,435 | 0 | Too rare to estimate | – | – | – |
| Diseased tissue: the gene's level differs in diseased tissue | 907 / 7,435 | 325 | 0.89 (0.58–1.26) | 0.95 (0.65–1.38) | 0.90 (0.63–1.30) | 1.22 (0.99–1.50) |
| · Higher in disease (in at least one comparison) | 548 / 7,435 | 229 | 0.58 (0.29–0.93) | 0.72 (0.44–1.17) | 0.70 (0.43–1.13) | 1.43 (1.14–1.80) |
| · Lower in disease only | 359 / 7,435 | 145 | 1.50 (0.86–2.21) | 1.30 (0.82–2.06) | 1.23 (0.79–1.91) | 0.91 (0.66–1.25) |
| · Target more active in disease, and the drug blocks it (derived) | 418 / 7,435 | 158 | 0.62 (0.28–1.07) | 0.79 (0.46–1.37) | 0.77 (0.45–1.32) | 1.38 (1.06–1.79) |
| **Animals** |  |  |  |  |  |  |
| Mouse genetics: mice with the gene altered show the disease | 1,504 / 7,435 | 462 | 1.44 (1.07–1.87) | 1.36 (1.10–1.68) | 1.34 (1.09–1.65) | 0.83 (0.69–1.00) |
| · Closely | 878 / 7,435 | 317 | 1.44 (1.05–1.91) | 1.44 (1.15–1.80) | 1.42 (1.14–1.77) | 0.76 (0.61–0.96) |
| · Loosely | 626 / 7,435 | 245 | 1.28 (0.87–1.75) | 1.07 (0.77–1.49) | 1.06 (0.77–1.46) | 0.98 (0.77–1.25) |
| · Mutant mice from published studies (MGI) (derived) | 1,496 / 7,435 | 458 | 1.44 (1.07–1.88) | 1.36 (1.10–1.68) | 1.34 (1.08–1.65) | 0.83 (0.69–1.01) |
| · Mouse knockout from a large-scale screen (IMPC) (derived) | 40 / 7,435 | 16 | Too rare to estimate | – | – | – |
| · Mouse genetics agrees with the drug's direction (derived) | 489 / 7,435 | 183 | 1.84 (1.33–2.50) | 1.38 (1.04–1.85) | 1.37 (1.03–1.82) | 0.55 (0.39–0.78) |
| Animal model pharmacology: a non-genetic change to the target alters a disease model (today: the program's own drug) | 4,662 / 8,833 | 1,536 | 0.75 (0.63–0.91) | 0.83 (0.71–0.99) | 0.83 (0.70–0.98) | 0.93 (0.84–1.05) |
| **Human** |  |  |  |  |  |  |
| Validated at entry: a drug on the target approved for this or a very close disease | 1,284 / 7,435 | 336 | 2.17 (1.77–2.75) | 2.01 (1.67–2.41) | 1.99 (1.66–2.38) | 0.66 (0.53–0.82) |
| · A related disease (Lin 0.5 to 0.8) | 892 / 7,435 | 234 | 1.19 (0.80–1.64) | 1.18 (0.93–1.50) | 1.18 (0.93–1.49) | 0.88 (0.72–1.09) |
| · Only unrelated diseases | 2,129 / 7,435 | 433 | 0.74 (0.56–0.96) | 0.71 (0.57–0.89) | 0.72 (0.58–0.89) | 1.50 (1.25–1.80) |
| A drug on the target approved for another disease | 3,021 / 7,435 | 500 | 0.83 (0.63–1.07) | 0.80 (0.65–0.99) | 0.81 (0.66–0.99) | 1.51 (1.22–1.87) |
| · A drug on the target approved for a related disease, Lin at least 0.5 (B1) (derived) | 2,176 / 7,435 | 423 | 1.96 (1.58–2.46) | 1.85 (1.57–2.18) | 1.83 (1.55–2.17) | 0.67 (0.55–0.80) |
| Another drug on the target failed in a related disease in the last 3 years | 1,685 / 5,836 | 393 | 1.57 (1.22–2.01) | 1.49 (1.19–1.86) | 1.47 (1.17–1.84) | 0.75 (0.62–0.90) |
| **The drug** |  |  |  |  |  |  |
| Binding to the target measured before entry | 1,658 / 6,091 | 415 | 1.45 (1.08–1.88) | 1.05 (0.81–1.36) | 1.04 (0.80–1.35) | 1.06 (0.89–1.25) |
| · 10 nM or better | 1,027 / 6,091 | 263 | 1.96 (1.35–2.68) | 1.23 (0.92–1.66) | 1.21 (0.90–1.63) | 0.98 (0.80–1.19) |
| · 10 to 100 nM | 363 / 6,091 | 136 | 0.70 (0.40–1.18) | 0.73 (0.47–1.13) | 0.72 (0.46–1.12) | 1.33 (1.05–1.70) |
| · Weaker than 100 nM | 268 / 6,091 | 92 | 0.80 (0.47–1.31) | 0.91 (0.59–1.39) | 0.93 (0.61–1.43) | 0.87 (0.61–1.24) |
| · Drug's effect measured in living cells | 364 / 6,091 | 105 | 1.19 (0.70–1.95) | 1.05 (0.70–1.57) | 1.05 (0.71–1.57) | 1.12 (0.85–1.47) |
| · Drug binds its target strongly (100 nM or better) (derived) | 1,390 / 6,091 | 358 | 1.57 (1.14–2.08) | 1.08 (0.82–1.43) | 1.06 (0.80–1.41) | 1.10 (0.92–1.31) |
| · Drug binds its target 10× more strongly than other proteins tested (derived) | 579 / 1,121 | 162 | 1.27 (0.71–2.25) | 0.99 (0.64–1.53) | 1.00 (0.65–1.54) | 0.99 (0.70–1.39) |
| · The drug binds another protein within 10-fold of its target (derived) | 542 / 1,121 | 157 | 0.79 (0.45–1.41) | 1.01 (0.65–1.56) | 1.00 (0.65–1.55) | 1.01 (0.72–1.42) |
| Pharmacokinetics or target engagement measured in healthy animals | 5,384 / 9,875 | 1,911 | 0.65 (0.54–0.78) | 0.81 (0.68–0.95) | 0.81 (0.69–0.96) | 0.93 (0.82–1.06) |
| Drug shown to act on its target in people | 2,189 / 5,613 | 858 | 1.05 (0.89–1.27) | 1.16 (0.96–1.40) | 1.16 (0.97–1.40) | 0.97 (0.86–1.11) |
| Molecule properties: drug-like, or suited to the brain | 4,654 / 5,520 | 1,266 | 0.99 (0.75–1.34) | 0.93 (0.71–1.23) | 0.94 (0.71–1.22) | 0.90 (0.75–1.08) |
| · Drug-like size and chemistry | 4,654 / 5,520 | 1,266 | 0.99 (0.75–1.34) | 0.93 (0.71–1.23) | 0.94 (0.71–1.22) | 0.90 (0.75–1.08) |
| · Chemistry suited to entering the brain | 547 / 814 | 194 | 0.86 (0.48–1.65) | 1.43 (0.78–2.64) | 1.40 (0.76–2.58) | 0.91 (0.70–1.17) |
| **Target safety risk** |  |  |  |  |  |  |
| Any standard safety flag (aggregate): people rarely carry broken copies of the gene, mice without it die young, or most cell types need it | 4,045 / 7,435 | 634 | 0.98 (0.71–1.36) | 1.12 (0.90–1.38) | 1.11 (0.90–1.37) | 1.02 (0.54–1.94) (safety) |
| · People rarely carry broken copies of the gene (gnomAD LOEUF below 0.35; today's data) | 1,629 / 7,435 | 242 | 0.83 (0.59–1.16) | 0.97 (0.75–1.26) | 0.98 (0.76–1.27) | 0.62 (0.24–1.61) (safety) |
| · Mice without the gene die before weaning (today's data) | 3,747 / 7,435 | 588 | 0.99 (0.71–1.36) | 1.08 (0.87–1.33) | 1.07 (0.87–1.31) | 1.17 (0.63–2.17) (safety) |
| · Most human cell types need the gene (DepMap common essential) | 0 / 7,435 | 0 | Too rare to estimate | – | – | – |
| · Mutant mice show a phenotype in a vital organ (heart, liver, blood, immune or nervous system; today's data) (exploratory) | 6,576 / 7,435 | 1,099 | 1.46 (0.95–2.31) | 1.05 (0.81–1.37) | 1.05 (0.80–1.36) | 2.10 (0.74–5.98) (safety) |
| · An earlier drug on the same target stopped for safety (exploratory) | 1,220 / 5,836 | 264 | 0.84 (0.60–1.19) | 1.01 (0.81–1.27) | 1.02 (0.81–1.27) | 1.22 (0.44–3.39) (safety) |
| · Most human cell types need the gene, on today's list (hindsight) | 678 / 7,435 | 101 | 0.43 (0.19–0.72) | 0.62 (0.39–0.99) | 0.63 (0.39–1.00) | 0.86 (0.27–2.77) (safety) |
| **Adjustment** |  |  |  |  |  |  |
| Trial enrolled patients selected by a biomarker | 1,855 / 9,957 | 829 | 1.72 (1.30–2.16) | 1.24 (1.02–1.50) | – | 0.92 (0.78–1.09) |

### Relative success, all programs

| Evidence line | Programs with it | LOA with / without | Relative success (95% CI) |
| :---- | :---- | :---- | :---- |
| Rare inherited variants, including single-gene disease | 702 | 25.7% / 8.9% | 2.89 (2.14–3.81) |
| Human genetics: inherited variants link the target to the disease | 910 | 24.1% / 8.7% | 2.76 (2.05–3.62) |
| Curated pathway: a disease mutation disrupts the target's pathway | 197 | 22.0% / 9.9% | 2.21 (1.16–3.32) |
| Tumour genetics (oncology): the gene is recurrently mutated in this cancer | 1,163 | 21.0% / 10.5% | 1.99 (1.15–3.79) |
| Common variants (genome-wide association studies) | 259 | 17.1% / 10.0% | 1.70 (1.04–2.46) |
| Mouse genetics: mice with the gene altered show the disease | 1,679 | 13.6% / 9.3% | 1.46 (1.10–1.91) |
| Diseased tissue: the gene's level differs in diseased tissue | 1,054 | 10.5% / 10.2% | 1.03 (0.68–1.47) |
| **Safety risk of the target** (not specific to the disease) |  |  |  |
| People rarely carry broken copies of the gene (gnomAD LOEUF below 0.35; today's data) | 1,818 | 9.0% / 10.5% | 0.86 (0.56–1.24) |
| **The molecule** (assays of the drug itself, not evidence for the disease) |  |  |  |
| 10 nM or better | 1,143 | 13.5% / 7.4% | 1.82 (1.30–2.41) |
| Drug binds its target strongly (100 nM or better) | 1,587 | 11.3% / 7.4% | 1.53 (1.12–2.00) |
| Binding to the target measured before entry | 1,905 | 10.2% / 7.4% | 1.37 (1.05–1.77) |
| Drug binds its target 10× more strongly than other proteins tested | 665 | 11.6% / 9.6% | 1.20 (0.65–2.13) |
| Drug's effect measured in living cells | 446 | 7.3% / 8.6% | 0.85 (0.52–1.39) |

### Genetic dose–response

| Human genetic support before entry | Programs | Targets | LOA (95% CI) |
| :---- | :---- | :---- | :---- |
| None | 7,713 | 1,275 | 8.7% (7.1–10.6) |
| Supported, none of it strong | 410 | 204 | 17.1% (10.5–24.5) |
| Strong: a gene burden test, GWAS locus-to-gene at least 0.8, or a curated or multi-submitter Mendelian record | 513 | 244 | 29.1% (24.0–34.7) |

### Relative success by disease area

| Evidence line | Oncology | Immunology and inflammation | Other | Neuroscience | Cardiometabolic and endocrine | Hematology | Differs between groups, Phase 2 (p) |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Human genetics: inherited variants link the target to the disease | 2.03 (1.06–3.43), n=317 | 1.51 (0.71–2.51), n=138 | –, n=93 | 2.70 (1.23–4.78), n=123 | 3.40 (2.09–6.19), n=159 | –, n=80 | 0.67 (6 groups) |
| Common variants (genome-wide association studies) | –, n=67 | –, n=81 | –, n=47 | –, n=29 | –, n=35 | –, n=0 | 0.78 (3 groups) |
| Rare inherited variants, including single-gene disease | 2.16 (1.07–3.68), n=259 | –, n=60 | –, n=55 | 2.61 (1.08–4.61), n=108 | 3.32 (2.06–5.85), n=140 | –, n=80 | 0.78 (6 groups) |
| Tumour genetics (oncology): the gene is recurrently mutated in this cancer | 1.99 (1.15–3.79), n=1,163 | –, n=0 | –, n=0 | –, n=0 | –, n=0 | –, n=0 | – |
| Mouse genetics: mice with the gene altered show the disease | 1.00 (0.56–1.75), n=471 | 1.61 (0.91–2.60), n=235 | 1.43 (0.65–2.84), n=185 | 1.77 (1.06–3.11), n=276 | 1.54 (0.98–2.44), n=408 | 1.52 (0.86–3.82), n=104 | 0.50 (6 groups) |
| Diseased tissue: the gene's level differs in diseased tissue | 1.03 (0.61–1.71), n=769 | 0.37 (0.06–0.78), n=169 | –, n=33 | –, n=73 | –, n=10 | –, n=0 | 0.01 (4 groups) |
| Drug binds its target strongly (100 nM or better) | 1.16 (0.69–1.80), n=834 | 2.22 (1.28–3.84), n=185 | 2.18 (1.08–4.06), n=201 | 1.03 (0.52–1.83), n=225 | 1.81 (0.75–3.92), n=126 | –, n=16 | 0.28 (5 groups) |

### What each line adds once the others are known

| Evidence | Phase 1 → 2 | Phase 2 → 3 | Phase 3 → approval |
| :---- | :---- | :---- | :---- |
| Common variants (genome-wide association studies) | 1.06 (0.95–1.19) | 1.12 (0.85–1.46) | 1.13 (0.84–1.54) |
| Rare inherited variants, including single-gene disease | 1.05 (0.96–1.16) | 1.52 (1.29–1.79) | 1.40 (1.16–1.70) |
| Tumour genetics (oncology): the gene is recurrently mutated in this cancer | 1.09 (0.98–1.22) | 1.33 (1.05–1.69) | 1.11 (0.87–1.41) |
| Mouse genetics: mice with the gene altered show the disease | 0.97 (0.91–1.04) | 1.15 (1.01–1.30) | 1.06 (0.90–1.25) |
| Diseased tissue: the gene's level differs in diseased tissue | 0.95 (0.88–1.04) | 0.86 (0.70–1.06) | 0.82 (0.65–1.04) |
| Curated pathway: a disease mutation disrupts the target's pathway | 1.10 (0.99–1.22) | 0.81 (0.59–1.11) | 1.17 (0.94–1.45) |
| **Safety risk of the target** (not specific to the disease) |  |  |  |
| People rarely carry broken copies of the gene (gnomAD LOEUF below 0.35; today's data) | 0.90 (0.82–0.99) | 1.01 (0.85–1.19) | 0.97 (0.78–1.19) |
| **The molecule** (assays of the drug itself, not evidence for the disease) |  |  |  |
| Binding to the target measured before entry | 0.81 (0.64–1.02) | 0.89 (0.67–1.18) | 1.22 (0.87–1.70) |
| Drug binds its target strongly (100 nM or better) | 1.17 (0.93–1.48) | 1.21 (0.88–1.67) | 1.12 (0.80–1.56) |
| Drug's effect measured in living cells | 0.79 (0.60–1.04) | 0.86 (0.67–1.10) | 1.04 (0.78–1.38) |
| Drug binds its target 10× more strongly than other proteins tested | 1.08 (0.90–1.29) | 1.11 (0.88–1.41) | 0.98 (0.75–1.26) |

### Does the evidence predict which programs reach approval?

| Validation | Features | AUC (95% CI) | PR-AUC (base rate) | Programs (approved) |
| :---- | :---- | :---- | :---- | :---- |
| Held-out target sets | Area, modality, novelty, year | 0.593 (0.529–0.659) | 0.121 (0.060) | 3,000 (181) |
| Temporal (later entrants held out) | Area, modality, novelty, year | 0.622 (0.551–0.697) | 0.124 (0.066) | 1,536 (101) |
| Held-out target sets | … plus all evidence lines | 0.623 (0.571–0.677) | 0.133 (0.060) | 3,000 (181) |
| Temporal (later entrants held out) | … plus all evidence lines | 0.630 (0.562–0.713) | 0.129 (0.066) | 1,536 (101) |
| Held-out target sets | Evidence lines only | 0.564 (0.492–0.641) | 0.093 (0.060) | 3,000 (181) |
| Temporal (later entrants held out) | Evidence lines only | 0.613 (0.550–0.681) | 0.111 (0.066) | 1,536 (101) |

Change in held-out AUC when each line is removed from the full model:

| Evidence removed | AUC change (95% CI) |
| :---- | :---- |
| Human genetics: inherited variants link the target to the disease | -0.025 (-0.049 to +0.000) |
| Rare inherited variants, including single-gene disease | -0.025 (-0.048 to -0.001) |
| Tumour genetics (oncology): the gene is recurrently mutated in this cancer | -0.003 (-0.028 to +0.019) |
| People rarely carry broken copies of the gene (gnomAD LOEUF below 0.35; today's data) | -0.001 (-0.009 to +0.008) |
| Mouse genetics: mice with the gene altered show the disease | +0.000 (-0.004 to +0.007) |
| Diseased tissue: the gene's level differs in diseased tissue | +0.002 (-0.018 to +0.031) |

### Confirmatory hypotheses

| Hypothesis | Measure | Estimate (95% CI) | p | Holm p | Result |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Outside oncology: genetics for the disease vs no germline genetics on the target, advancing within 4 years of Phase 2 | risk ratio | 1.59 (1.12–2.28) | 0.010 | 0.061 | not supported |
| Same target in different diseases: genetics for the disease vs not (conditional logit) | odds ratio | 3.07 (2.03–4.65) | < 0.001 | < 0.001 | supported |
| Direction of genetic effect vs drug action (Open Targets direction fields): discordant < undirected < concordant | risk ratio per step | 1.13 (0.83–1.54) | 0.439 | 1.000 | not supported |
| Trials outside oncology: how the effect of genetics on missing the primary endpoint changes per step from proximal to distal endpoints (registry-posted results, FDAAA era) | ratio of risk ratios | 1.12 (0.84–1.50) | 0.441 | 1.000 | not supported |
| Genetics for the disease lowers efficacy failure more than business or operational failure (Phases 2 and 3) | ratio of risk ratios | 1.19 (0.76–1.85) | 0.447 | 1.000 | not supported |
| Outside oncology, the target's safety risk raises safety failure, and more than efficacy failure (Phases 1–3; intersection-union test) | risk ratio, safety failure | 0.90 (0.49–1.67) | 0.960 | 1.000 | not supported |
| Oncology: a gene recurrently mutated in the cancer whose mutation matches the drug, advancing within 4 years of Phase 2 | risk ratio | 1.52 (1.10–2.12) | 0.012 | 0.061 | not supported |

Added by the plan amendment, on US-developed programs:

| Hypothesis | Claim | Exposed entries | Risk ratio (95% CI) | p | Holm p | Result |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| N1 | Small molecules measured on the primary target and an off-target: at least 10-fold selective raises advancing from Phase 2 | 200 (111 targets) | 0.99 (0.64–1.53) | 0.969 | 1.000 | not supported |
| N2 | Small molecules: at most one Rule-of-5 violation raises advancing | 1,899 (796 targets) | 0.93 (0.71–1.23) | 0.623 | 1.000 | not supported |
| N2 | Neurology and psychiatry: brain-penetrant properties raise advancing | 264 (136 targets) | 1.43 (0.78–2.64) | 0.250 | 1.000 | not supported |
| N3 | Outside oncology, small molecules: potency of 100 nM or better raises advancing, human genetics and drug-likeness held fixed | 274 (146 targets) | 1.01 (0.74–1.38) | 0.928 | 1.000 | not supported |

### Which evidence translates: the registered screen

Every rule the plan registered, each against programs without it, before the rules were grouped by kind.

![Phase 2 programs, 2008–2019: each registered rule against programs without it](report/output/figures/s3_evidence_map.png)

| Evidence for the disease, known before Phase 2 | Programs (targets) | Advanced: with / without | Share of all that advanced | Risk ratio, all (95% CI) | Risk ratio, non-oncology | Risk ratio, oncology |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Inherited variants linked to the disease | 534 (243) | 28% / 14% | 21% | 1.94 (1.58–2.39) | 1.49 (1.12–1.99) | 2.31 (1.66–3.22) |
| Common variants, any strength of link to the gene | 140 (77) | 20% / 15% | 4% | 1.23 (0.84–1.80) | 1.29 (0.77–2.14) | 1.59 (0.94–2.69) |
| Common variants, strongly linked to the gene | 60 (38) | 13% / 16% | 1% | 0.81 (0.43–1.53) | 0.81 (0.36–1.83) | – |
| Common variants, moderately linked to the gene | 35 (20) | 17% / 16% | 1% | 1.02 (0.47–2.24) | – | – |
| Common variants, weakly linked to the gene | 45 (29) | 31% / 15% | 2% | 1.93 (1.15–3.24) | 2.09 (1.16–3.75) | – |
| Single-gene disease or a known disease-causing variant | 421 (188) | 29% / 14% | 17% | 2.03 (1.62–2.54) | 1.54 (1.12–2.14) | 2.22 (1.56–3.18) |
| Single-gene disease, best-established | 266 (124) | 32% / 15% | 12% | 2.32 (1.79–3.02) | 1.63 (1.14–2.33) | 3.11 (2.17–4.45) |
| Gene recurrently mutated in this cancer | 542 (133) | 22% / 15% | 17% | 1.66 (1.24–2.23) | – | 1.60 (1.15–2.22) |
| The mutation's effect matches the drug's action | 397 (91) | 22% / 15% | 12% | 1.61 (1.19–2.18) | – | 1.52 (1.10–2.12) |
| Mutant mice from published studies | 939 (427) | 21% / 14% | 28% | 1.49 (1.22–1.82) | 1.49 (1.21–1.85) | 1.32 (0.81–2.14) |
| Mutant mouse phenotype closely matches the disease | 568 (279) | 23% / 14% | 19% | 1.54 (1.27–1.86) | 1.59 (1.25–2.02) | 1.26 (0.85–1.86) |
| The gene's RNA level differs in diseased tissue | 531 (264) | 17% / 15% | 12% | 1.06 (0.74–1.51) | 0.56 (0.32–1.00) | 1.24 (0.83–1.86) |
| A curated pathway shows a disease mutation disrupting the target | 122 (44) | 22% / 15% | 4% | 1.29 (0.90–1.83) | – | – |
| **Earlier drugs on the same target** |  |  |  |  |  |  |
| A drug on the target already approved for a related disease | 1,278 (368) | 25% / 12% | 46% | 2.15 (1.77–2.61) | 1.94 (1.54–2.44) | 2.51 (1.59–3.97) |
| A drug on the target already approved, any disease | 2,620 (569) | 18% / 12% | 68% | 1.60 (1.33–1.93) | 1.52 (1.21–1.92) | 1.72 (1.23–2.39) |
| **Safety risk of the target** (not specific to the disease) |  |  |  |  |  |  |
| Most human cell types need the gene | 0 (0) | – / 16% | 0% | – | – | – |
| People rarely carry broken copies of the gene | 889 (220) | 15% / 16% | 19% | 0.98 (0.77–1.25) | 1.14 (0.88–1.49) | 0.82 (0.54–1.23) |
| Mice without the gene die young | 2,224 (547) | 16% / 15% | 49% | 1.00 (0.83–1.22) | 0.88 (0.72–1.07) | 1.12 (0.76–1.65) |

### By endpoint

| Class of the governing primary endpoint | Trials | Missed primary endpoint | Trials with genetics for the disease | Missed: with / without genetics | Risk ratio of a miss, all readable trials (95% CI) | Risk ratio, registry-posted results (FDAAA era) |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Target engagement | 62 | 29% | 21 | 33% / 27% | 0.99 (0.39–2.54) | – |
| Exploratory biomarker | 262 | 69% | 24 | 79% / 68% | 1.15 (0.88–1.51) | – |
| Regulatory surrogate (LDL-C, HbA1c, viral load…) | 1,372 | 22% | 212 | 17% / 23% | 1.07 (0.71–1.60) | 0.58 (0.28–1.23) |
| Objective physiology (6MWD, visual acuity, weight…) | 452 | 53% | 81 | 46% / 55% | 0.98 (0.69–1.39) | 1.07 (0.76–1.51) |
| Clinician-rated scale or responder index | 1,314 | 55% | 170 | 47% / 56% | 0.83 (0.66–1.04) | 0.88 (0.69–1.12) |
| Patient-reported outcome | 669 | 51% | 7 | 57% / 51% | – | – |
| Disease events (relapses, exacerbations…) | 341 | 42% | 51 | 39% / 42% | 0.90 (0.59–1.38) | – |
| Hard outcome (death, MI, stroke…) | 162 | 53% | 11 | 55% / 53% | – | – |
| Tumour response | 157 | 64% | 34 | 62% / 64% | 1.02 (0.73–1.43) | – |
| Progression-free survival | 536 | 59% | 104 | 52% / 61% | 1.04 (0.86–1.26) | 1.05 (0.77–1.45) |
| Overall survival | 245 | 69% | 26 | 54% / 71% | 0.73 (0.52–1.04) | – |

### Which kinds of evidence predict, and whether being more specific helps

| Evidence before Phase 2 | Applies to | With it (targets) | Advanced: with / without | Adjusted risk ratio (95% CI) | Holm-corrected p |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Inherited variants linked to the disease | All | 534 (243) | 28% / 14% | 1.94 (1.58–2.39) | < 0.001 |
| Mouse genetics: knocked-out or mutant mice show the disease | All | 945 (432) | 21% / 14% | 1.49 (1.22–1.82) | < 0.001 |
| Gene recurrently mutated in this cancer | Oncology | 536 (132) | 22% / 12% | 1.60 (1.15–2.22) | 0.020 |
| Gene-knockout screens in human cells | All | 0 (0) | – / 16% | too few programs (0) to test | – |
| The gene's RNA level differs in diseased tissue | All | 531 (264) | 17% / 15% | 1.06 (0.74–1.51) | 1.000 |
| A curated pathway shows a disease mutation disrupting the target | All | 122 (44) | 22% / 15% | 1.29 (0.90–1.83) | 0.480 |
| Safety risk of the target | All | 2,374 (586) | 16% / 15% | 1.01 (0.83–1.23) | 1.000 |
| **Benchmark** (clinical precedent, not preclinical evidence) |  |  |  |  |  |
| A drug on the target already approved for a related disease | All | 1,278 (368) | 25% / 12% | 2.15 (1.77–2.61) | – |

| More specific version | Within programs with | Programs | Advanced: with / rest of the type | Adjusted risk ratio (95% CI) | Holm-corrected p |
| :---- | :---- | :---- | :---- | :---- | :---- |
| GWAS with locus-to-gene ≥ 0.8 | Inherited variants linked to the disease | 60 of 534 | 13% / 30% | 0.54 (0.27–1.05) | 0.635 |
| Mendelian evidence in a non-hereditary disease | Inherited variants linked to the disease | 119 of 204 | 26% / 20% | 0.92 (0.47–1.82) | 1.000 |
| Both common and rare variants | Inherited variants linked to the disease | 27 of 534 | 7% / 29% | 0.26 (0.07–0.92) | 0.362 |
| Drug raises function or replaces the gene, hereditary disease | Inherited variants linked to the disease | 112 of 170 | 31% / 19% | 1.89 (0.89–4.04) | 0.788 |
| Genetics agrees with the drug's direction (added after the plan) | Inherited variants linked to the disease | 270 of 534 | 28% / 28% | 1.10 (0.76–1.60) | 1.000 |
| Broken copies of the gene protect, and the drug blocks it (added after the plan) | Inherited variants linked to the disease | 30 of 534 | 13% / 29% | too few to test | – |
| Mutant mouse phenotype closely matches the disease | Mouse genetics: knocked-out or mutant mice show the disease | 569 of 945 | 23% / 19% | 1.19 (0.82–1.72) | 1.000 |
| Mouse genetics points the same way as the drug (added after the plan) | Mouse genetics: knocked-out or mutant mice show the disease | 334 of 945 | 23% / 20% | 1.11 (0.83–1.50) | 1.000 |
| Driver matches the drug (activated oncogene + inhibitor) | Gene recurrently mutated in this cancer | 385 of 536 | 22% / 21% | 0.98 (0.62–1.57) | 1.000 |
| Expression up + drug that lowers function | The gene's RNA level differs in diseased tissue | 250 of 531 | 15% / 18% | 0.94 (0.53–1.68) | 1.000 |
| Liability + drug that lowers function | Safety risk of the target | 1,721 of 2,374 | 15% / 17% | 1.04 (0.79–1.38) | 1.000 |

## Sources in detail

Each entry gives who compiles the source and from what, what this analysis takes from it, the shape of the raw response, and a real record from the cached download, trimmed to the fields used.

### ClinicalTrials.gov API v2

*Snapshot 2026-11-02, 227,130 studies · `GET https://clinicaltrials.gov/api/v2/studies?filter.advanced=AREA[StudyType]INTERVENTIONAL AND AREA[InterventionType](DRUG OR BIOLOGICAL OR GENETIC OR COMBINATION_PRODUCT)&pageSize=1000` paged by `pageToken`*

**Compiled by.** The National Library of Medicine runs the registry. Sponsors enter the protocol record and the results themselves, as FDAAA 801 requires for applicable trials. NLM reviews entries for quality but does not check them against source records.
**We use.** From the protocol section we keep status, dates, the why-stopped text, phases, sponsor and its class, design, conditions, interventions, arms, references, countries, brief summary and primary outcomes. From the results section, posted for 53,902 studies, we keep every primary outcome's values per group and every statistical analysis, plus deaths and serious adverse events per arm.
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

### PubMed E-utilities

*Queried at run time; each run is recorded with its date and a hash of what it returned · `esearch.fcgi?db=pubmed&term=NCT…[si]`, then `efetch.fcgi?retmode=xml`*

**Compiled by.** NCBI indexes citations from publishers and MEDLINE. A trial registration number named in an article is recorded in its data-bank list and is searchable as a secondary identifier.
**We use.** We look up only completed industry Phase 2/3 trials, started from 2008, that posted no results. A paper links to a trial when the registry lists it as a RESULT or DERIVED reference, or when PubMed lists the NCT number. This links 2,284 trials. For each paper we keep title, first author, journal, year, DOI and abstract, and the abstracts feed the outcome classifier.
**Shape.** `<PubmedArticle><MedlineCitation><PMID/><Article><Journal/><ArticleTitle/><Abstract/><DataBankList><DataBank><AccessionNumber/></DataBank></DataBankList></Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi"/></ArticleIdList></PubmedData></PubmedArticle>`

```text
NCT03036488 (KEYNOTE-522; no posted results) -> PMID 32101663, linked by both routes
  N Engl J Med 2020, "Pembrolizumab for Early Triple-Negative Breast Cancer", Schmid P et al.
  DataBank ClinicalTrials.gov / AccessionNumber NCT03036488, doi 10.1056/NEJMoa1910549
```

### Drugs@FDA data files

*Data to 2026-10-28 · `GET https://www.fda.gov/media/89850/download`, a zip of tab-separated tables*

**Compiled by.** FDA's drug center (CDER) publishes these files from its own application records. They cover drugs and therapeutic biologics, not the vaccines, blood products and cell or gene therapies that CBER regulates.
**We use.** NDA and BLA applications: sponsor, products and active ingredients, every original and supplement submission with its class, status, date and review priority, and the links to approval letters. That is 6,394 applications.
**Shape.** `Applications.txt` (ApplNo, ApplType, SponsorName), `Products.txt`, `Submissions.txt` (ApplNo, SubmissionClassCodeID, SubmissionType, SubmissionNo, SubmissionStatus, SubmissionStatusDate, ReviewPriority), `ApplicationDocs.txt` (type 1 = letter, URL, date).

```text
Applications     125514  BLA  MERCK SHARP DOHME
Products         125514  001  SOLUTION;INTRAVENOUS  100MG/4ML  KEYTRUDA  PEMBROLIZUMAB
Submissions      125514  class 2 (EFFICACY)  SUPPL 89  AP  2021-07-26  STANDARD
ApplicationDocs  125514  SUPPL 89  letter  …/appletter/2021/125514Orig1s089s114ltr_.pdf
```

### FDA approval letters (CDER)

*Actions 2008 to 2026-10-28 · PDFs at `https://www.accessdata.fda.gov/drugsatfda_docs/appletter/<year>/<ApplNo>…ltr.pdf`, from the Drugs@FDA links*

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

### openFDA drug labels

*Export 2026-10-28, 262,903 labels · `GET https://api.fda.gov/download.json` lists the bulk files, e.g. `https://download.open.fda.gov/drug/label/drug-label-0001-of-0014.json.zip`*

**Compiled by.** Manufacturers submit Structured Product Labeling to FDA. openFDA republishes it in bulk with harmonised identifiers and notes that the data are not validated.
**We use.** We keep the current label of each NDA or BLA product, 5,102 in all, with its application numbers, names, UNII and the full Indications and Usage text. The approval classifier reads that text as evidence of approved uses, including uses approved before 2008.
**Shape.** `{meta, results: [{set_id, id, version, effective_time, indications_and_usage: [str], …, openfda: {application_number[], brand_name[], generic_name[], substance_name[], unii[]}}]}`

```json
{"set_id": "9333c79b-d487-4538-a9f0-71b91a02b287", "effective_time": "20260710",
 "openfda": {"application_number": ["BLA125514"], "brand_name": ["KEYTRUDA"], "unii": ["DPT0O3T46P"]},
 "indications_and_usage": ["1 INDICATIONS AND USAGE KEYTRUDA is a programmed death receptor-1 (PD-1)-blocking
   antibody indicated: Melanoma for the treatment of patients with unresectable or metastatic melanoma. …"]}
```

### CBER biologics approvals

*Actions 2015-01-09 to 2025-12-19, 324 records on 177 applications · yearly pages `https://www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/<year>-biological-license-application-approvals`, live from 2023 and from the Wayback Machine before; product pages; letter PDFs at `https://www.fda.gov/media/<id>/download`*

**Compiled by.** FDA's biologics center posts a yearly table of original licence approvals and noteworthy supplements, and a page per product linking its letters. None of these products are in Drugs@FDA.
**We use.** We keep original licences and supplements that add or change an indication, population, dose or formulation, with each letter's text. 53 letters came from Wayback captures. For the 10 records without a letter, the yearly-table entry stands in.

```json
{"appl_no": "125646", "submission_type": "ORIG", "approval_date": "2017-08-30",
 "product_brand": "KYMRIAH", "proper_name": "tisagenlecleucel", "product_class": "cell_therapy",
 "url": "https://www.fda.gov/media/106989/download", "pdf_source": "fda.gov",
 "yearly_listing_text": "KYMRIAH Tisagenlecleucel | For the treatment of patients up to 25 years of age with B-cell precursor ALL …"}
```

### FDA Global Substance Registration System (UNII)

*2026-08-04, 171,912 substances and 1,047,975 names · `https://precision.fda.gov/uniisearch/archive/2026-08-04/UNII_Data_20260804.zip`, plus the matching names file*

**Compiled by.** FDA assigns each Unique Ingredient Identifier from a substance's structure or defining information. It collects the substance's names from INN, USAN, JAN, brands and sponsor codes, each tagged with its type.
**We use.** Substances, with their INN, RxNorm and PubChem cross-references, and every name in normalised form. These resolve trial intervention names to one molecular entity and merge entities that are the same substance.
**Shape.** Records: 25 tab-separated columns, including UNII, DISPLAY_NAME, RXCUI, PUBCHEM, INN_ID, INCHIKEY and SUBSTANCE_TYPE. Names: NAME, TYPE (brand, code, common, official or systematic), UNII.

```text
53AXN4NNHX  SEMAGLUTIDE  RXCUI 1991302  PUBCHEM 56843331  INN_ID 9113  SUBSTANCE_TYPE protein
  names: NN9535 (code) · NNC-0113-0217 (code) · OZEMPIC (brand) · WEGOVY (brand) · SEMAGLUTIDE [JAN] (common)
```

### MONDO disease ontology

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

### EFO

*Reaches the analysis only as Open Targets disease identifiers*

**Compiled by.** EMBL-EBI maintains EFO for Open Targets, the GWAS Catalog and Expression Atlas. It imports disease classes from MONDO and other ontologies and adds terms of its own.
**We use.** No EFO file. Open Targets keys 9,257 of its diseases by EFO identifiers. Each is mapped to MONDO through the disease's own MONDO cross-reference, then MONDO's declared equivalence to the EFO term. Failing both, it maps through a DOID, Orphanet, NCIT or MeSH cross-reference that points to a single MONDO term.

```text
EFO_0000768 idiopathic pulmonary fibrosis: no MONDO xref, and no MONDO term lists EFO:0000768
  -> DOID:0050156 and Orphanet:2032 are both equivalent to MONDO:0800504
```

### Mammalian Phenotype ontology

*2026-09-23 · `http://purl.obolibrary.org/obo/mp.obo`*

**Compiled by.** Mouse Genome Informatics at the Jackson Laboratory maintains it. MGI and IMPC curators use it to annotate phenotypes of mutant mice.
**We use.** The hierarchy only. A target counts as "knockout lethal before weaning" when any of its Open Targets mouse phenotypes is MP:0010770 *preweaning lethality* or a descendant. That flags 688 genes.

```text
id: MP:0011100
name: preweaning lethality, complete penetrance
is_a: MP:0010770 ! preweaning lethality
```

### Gene symbols and identifiers

*Project catalogue, resolved through HGNC 2026-10-16 · `https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt`*

**Compiled by.** HGNC approves one symbol per human gene and records each gene's previous symbols and aliases. The project's own catalogue of 26,957 human proteins adds Ensembl identifiers, Pharos development level and family, and RefSeq summaries; some of its symbols predate HGNC renames.
**We use.** A target the LLM names is accepted when the symbol is a catalogue protein, or an HGNC approved, previous or alias symbol of one (an alias two genes share is not used). Ensembl identifiers join targets to Open Targets, gnomAD and DepMap.
**Shape.** Tab-separated, one approved gene per row: `hgnc_id, symbol, name, locus_group, alias_symbol, prev_symbol, entrez_id, ensembl_gene_id, uniprot_ids, …`, with lists separated by `|`.

```text
HGNC:11701  CRIPTO  cripto, EGF-CFC family member  protein-coding gene  prev_symbol TDGF1  ensembl ENSG00000241186
TDGF1 (previous) -> CRIPTO · CTGF (previous) -> CCN2 · CD20 (alias) -> MS4A1 · TIM3 (alias) -> HAVCR2
```

### ChEMBL mechanisms of action

*ChEMBL 37 (2026-05-01), 7,561 mechanisms · `GET https://www.ebi.ac.uk/chembl/api/data/mechanism.json?limit=1000&offset=…`, then `target.json` and `molecule.json` for the ids they name*

**Compiled by.** EMBL-EBI curators assign each approved or clinical-stage drug its molecular targets and action type, with references from labels and the literature.
**We use.** Only as hints. When the LLM assigns an entity's targets, it sees every mechanism of the parent molecule of each of its ChEMBL ids, as "SYMBOL: action" for each human gene of the target; its own answer is what we store. A target's genes are its UniProt components mapped to HGNC, so a complex or receptor family keeps all of them (1,257 mechanisms name more than one gene); mechanisms with no human gene, such as antibacterials, are shown as text.
**Shape.** `{mechanisms: [{mec_id, molecule_chembl_id, parent_molecule_chembl_id, target_chembl_id, action_type, mechanism_of_action, …}], page_meta: {next, …}}`; a target's `target_components[{accession}]` give its genes.

```json
{"mec_id": 8862, "molecule_chembl_id": "CHEMBL4297839", "target_chembl_id": "CHEMBL4383", "action_type": "AGONIST",
 "mechanism_of_action": "Gastric inhibitory polypeptide receptor agonist"}
{"mec_id": 8994, "molecule_chembl_id": "CHEMBL4297839", "target_chembl_id": "CHEMBL1784", "action_type": "AGONIST",
 "mechanism_of_action": "Glucagon-like peptide 1 receptor agonist"}
```

Tirzepatide's hints: GIPR: agonist, GLP1R: agonist.

### ChEMBL bioactivities

*ChEMBL 37 (2026-05-01), 137,580 measurements of 3,460 of 7,459 parent molecules · the release's MySQL dump, `https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/chembl_37_mysql.tar.gz`, tables `activities`, `assays`, `docs`, `target_dictionary`, `target_components`, `component_sequences`, `molecule_dictionary` and `molecule_hierarchy`*

**Compiled by.** EMBL-EBI curators extract bioactivity measurements from medicinal chemistry journals and patents, and research groups and companies deposit screening datasets directly. Each measurement is tied to an assay (its type, binding or functional, and its format, such as cell-based or purified protein), a target and the document that reported it. ChEMBL converts half-maximal concentrations and affinity constants to pChEMBL, the negative log of the molar value, flags values it judges doubtful and marks values that repeat an earlier paper's.
**We use.** Every measurement with a pChEMBL value against a human target, for every form of each ChEMBL parent molecule matched to an entity with a development program (the routes are in the evidence methods): 137,580 after dropping 23,613 repeat citations and 0 flagged as doubtful (ChEMBL gives a pChEMBL value only to measurements it has not flagged), on 3,646 targets from 16,138 documents. Each document's year (a paper's publication year, a patent's year, a dataset's deposition year) dates its measurements. A target's genes are its UniProt components mapped to HGNC, as for mechanisms.
**Shape.** A MySQL dump with many rows per `INSERT`: `activities(activity_id, assay_id, doc_id, molregno, standard_type, pchembl_value, data_validity_comment, potential_duplicate, …)`, `assays(assay_id, chembl_id, assay_type, bao_format, tid, …)`, `docs(doc_id, chembl_id, year, journal, src_id, …)`.

```
INSERT INTO `activities` VALUES (…,'IC50',…,NULL,0,7.40,…)   imatinib, Abl kinase, binding assay, protein format
docs: CHEMBL1144977  Bioorg Med Chem Lett  2003
```

### gnomAD constraint

*v4.1 · loaded by earlier project code*

**Compiled by.** The Broad Institute's gnomAD compares each gene's observed loss-of-function variants, in exomes and genomes from about 800,000 people, with the number a mutation model expects. LOEUF is the upper bound of the 90% interval of observed over expected, and a low value means the gene does not tolerate loss of function.
**We use.** A target is LoF-intolerant when its LOEUF is below 0.35. That flags 1,385 of 18,164 genes. The value is today's, not the value at phase entry.

```text
PCSK9   pLI 1.1e-20  LOEUF 1.25    missense z 0.59
POLR2A  pLI 1.0      LOEUF 0.161   missense z 9.21
```

### DepMap gene essentiality

*DepMap Public 19Q4, 20Q4, 21Q4, 22Q4, 23Q4 and 24Q4 · the common-essential file of each release's figshare record (`Achilles_common_essentials.csv` through 20Q4, `CRISPR_common_essentials.csv` in 21Q4, `CRISPRInferredCommonEssentials.csv` from 22Q4), e.g. `https://api.figshare.com/v2/articles/27993248/files`*

**Compiled by.** The Broad Institute's Cancer Dependency Map knocks out every gene by CRISPR in about a thousand cancer cell lines, and Chronos estimates each gene's effect on growth. DepMap's inferred common-essential list holds the genes whose knockout ranks among the most depleting in most lines.
**We use.** The list from the last release of each year, 2019 to 2024 (2,149 genes in 19Q4, 1,523 in 24Q4), keyed by Entrez id and mapped to Ensembl through HGNC. A target is flagged essential in most cell lines when it is on the latest list from before the program entered the phase. DepMap first published the list in 19Q2, so no list covers an earlier year. Through 20Q4 the list comes from the Broad's Achilles screens alone; from 21Q4 it combines them with the Sanger Project Score screens.
**Shape.** One column, `Essentials`, each row `SYMBOL (Entrez id)`.

```text
Essentials
AAMP (14)
AARS1 (16)
POLR2B (5431)
```

### Open Targets Platform: associations

*26.09 · `https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.09/output/association_by_datasource_direct/*.parquet` and `…/disease/`*

**Compiled by.** EMBL-EBI, the Wellcome Sanger Institute and partners run Open Targets. It maps evidence from about 20 resources to Ensembl genes and to disease terms (MONDO, EFO, HP, Orphanet) and scores each item from 0 to 1. Per target, disease and datasource, it combines the items into one association score with a weighted harmonic sum. A "direct" association counts only evidence annotated to that exact disease, not to its subtypes. Each association carries a yearly series of its cumulative score.
**We use.** Direct associations from the 17 datasources below, for targets of drugs in industry programs. We keep each evidence item with the year it became known, so evidence is taken as of the year before phase entry; undated items count only on today's data.
**Shape.** `targetId, diseaseId, aggregationValue (datasource), associationScore, evidenceCount, timeseries[{year, associationScore, yearlyEvidenceCount}]`; diseases: `id, name, dbXRefs[], therapeuticAreas[]`.

```json
{"targetId": "ENSG00000169174", "diseaseId": "MONDO_0005439", "aggregationValue": "eva",
 "associationScore": 0.875, "evidenceCount": 829,
 "timeseries": [{"year": 2018, "associationScore": 0.0}, {"year": 2019, "associationScore": 0.704},
                {"year": 2021, "associationScore": 0.800}, {"year": 2026, "associationScore": 0.875},
                {"year": null, "associationScore": 0.875}]}
```

PCSK9 · familial hypercholesterolemia, ClinVar evidence.

### Open Targets Platform: evidence

*26.09 · `…/output/evidence_<datasource>/*.parquet` and `…/mouse_phenotype/`*

**Compiled by.** One row per supporting item: a variant, study, curated assertion, mouse model, expression contrast or reaction. Each row has a 0–1 score and the upstream statistic. Where the source allows, it also has a date, a confidence grade, and the direction of effect on the target (loss or gain of function) and on the trait (risk or protection).
**We use.** Every row for program targets. The Phase 2 analysis groups them into families and strength tiers, such as locus-to-gene ≥ 0.8, burden p < 2.5e-6, ClinGen definitive or strong, and PanelApp green. Mouse phenotypes give the knockout-lethality flag.
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
| CRISPR | Project Score knockout fitness screens in cancer lines (Behan et al. 2019; re-analysed by Pacini et al. 2024, which Open Targets now dates every row by) | Gene is a fitness dependency in that cancer type | KRAS · plasma cell myeloma · priority 78 |
| CRISPR screens | CRISPRbrain screens in iPSC-derived neurons | Perturbing the gene shifts a screen phenotype | LDLR · neurodegeneration · log2FC −5.8 |
| Mouse phenotypes | IMPC and MGI phenotype annotations (MP terms), not linked to a disease | A mutant allele shows the phenotype | PCSK9 · decreased circulating LDL cholesterol |

We leave out three datasources. Clinical precedence and cancer biomarkers come from drugs' clinical records, so they would leak the outcome. Europe PMC counts literature co-mentions of gene and disease, which is attention, not evidence. For PCSK9 and familial hypercholesterolemia, clinical precedence alone scores 0.97.

