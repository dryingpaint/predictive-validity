## Predictive power of preclinical evidence

{{SECTION2_SUMMARY}}

### Evidence lines

Each program aimed at a human protein is scored for the evidence its targets had **for the program's disease**, **as of the year before it entered the phase**, from Open Targets: human germline genetics (GWAS and rare-variant), somatic cancer drivers, mouse models, expression in the disease, pathways and CRISPR screens in human cells, plus two properties of the target itself (essential in most cells; intolerant of loss of function). A third group describes the drug rather than its target or disease: its potency, functional activity in cells and selectivity, as measured in laboratory assays published before entry and collected in ChEMBL. How each line is dated and matched to the program's disease is in the appendix. Vaccines, cell and gene therapies and other entities without a single human protein target fall outside this analysis, so its programs reach approval more often than the Section 1 cohort as a whole. Of the {{section2.n_programs|int}} programs on {{section2.n_targets|int}} targets scored, {{section2.evidence_coverage_ph1.genetic_any|pct}} of Phase 1 entrants had human genetic evidence for their disease at entry.

### Relative success

*Relative success* is the LOA of programs with the evidence divided by the LOA of programs without it (Nelson et al. 2015; Minikel et al. 2024).

{{RS_TABLE}}

![Relative success by evidence line](report/output/figures/relative_success_by_evidence.png)

{{SECTION2_RS}}

### Genetic dose–response

{{DOSE_TABLE}}

![Likelihood of approval by strength of human genetic support](report/output/figures/genetic_dose_response.png)

### What each line adds once the others are known

Programs with genetic evidence differ from programs without it in disease area, modality and era, and the evidence lines overlap. The table gives, for each phase, the relative risk of advancing for programs with each line, with the other lines, disease area, modality, novelty and entry period held fixed.

{{JOINT_TABLE}}

{{SECTION2_JOINT}}

### The drug's own pharmacology

{{SECTION2_DRUG}}

### Does the evidence predict which programs reach approval?

We followed programs that entered Phase 1 in 2008–2016 for ten years ({{section2.n_prediction|int}} programs, {{section2.n_prediction_positive|int}} approved) and asked whether adding the evidence lines to what is known about disease area, modality, novelty and entry year improves the prediction of approval, on targets the model had not seen.

{{PREDICTION_TABLE}}

Change in held-out AUC when each line is removed from the full model:

{{ABLATION_TABLE}}

{{SECTION2_PREDICTION}}
