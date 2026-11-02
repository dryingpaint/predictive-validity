## Predictive power of preclinical evidence

{{SECTION2_SUMMARY}}

### Evidence lines

Each program on a human protein target is scored for the evidence its targets had **for the program's disease, as of the year before it entered the phase**: human germline genetics (GWAS and rare-variant), somatic cancer drivers, mouse models, expression in the disease, pathways and CRISPR screens (from Open Targets); two properties of the target itself (essential in most cells, intolerant of loss of function); and the drug's own potency and selectivity in laboratory assays (ChEMBL). Of the {{section2.n_programs|int}} programs scored, {{section2.evidence_coverage_ph1.genetic_any|pct0}} of Phase 1 entrants had human genetic evidence for their disease. Dating and matching rules are in the appendix.

### Relative success

*Relative success* is the LOA of programs with the evidence divided by the LOA of programs without it (Nelson et al. 2015; Minikel et al. 2024); the figure in Section 3 shows it for every line.

{{SECTION2_RS}}

### Genetic dose–response

![Likelihood of approval by strength of human genetic support](report/output/figures/genetic_dose_response.png)

### What each line adds once the others are known

The evidence lines overlap, so the figure holds the other lines, disease area, modality, novelty and entry period fixed and shows what each line adds at each phase.

![Relative risk of advancing at each phase, with the other lines, disease area, modality, novelty and entry period held fixed](report/output/figures/joint_by_phase.png)

{{SECTION2_JOINT}}

### By disease area

![Relative success of human genetic evidence by disease area](report/output/figures/genetics_by_area.png)

{{SECTION2_AREA}}

### The drug's own pharmacology

{{SECTION2_DRUG}}

### Does the evidence predict which programs reach approval?

Programs that entered Phase 1 in 2008–2016 were followed for ten years ({{section2.n_prediction|int}} programs, {{section2.n_prediction_positive|int}} approved), and models were tested on targets they had not seen.

![Held-out AUC with and without the evidence lines, and the change in AUC when each line is removed](report/output/figures/prediction.png)

{{SECTION2_PREDICTION}}
