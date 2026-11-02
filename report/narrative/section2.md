## Predictive power of preclinical evidence

{{SECTION2_SUMMARY}}

### Evidence and design

Each program on a human protein target is scored for the evidence its targets had **for the program's disease, as of the year before it entered the phase**: human germline genetics (GWAS and rare-variant), somatic cancer drivers, mouse models, expression in the disease, pathways and CRISPR screens (from Open Targets); two properties of the target itself (essential in most cells, intolerant of loss of function); and the drug's own potency and selectivity in laboratory assays (ChEMBL). {{section2.evidence_coverage_ph1.genetic_any|pct0}} of Phase 1 entrants had human genetic evidence for their disease.

Two outcomes are measured on programs entering a phase in 2008–2019. *Relative success* is the likelihood of approval with the evidence divided by that without it, across all {{section2.n_programs|int}} programs (Nelson et al. 2015; Minikel et al. 2024). The second is whether a Phase 2 program advanced to Phase 3 or approval within four years ({{section3.c2.s4|pct0}} of {{section3.c2.programs|int}} did): Phase 2 is the first test of efficacy in patients, so it is where the evidence's claim about the disease is first put to the test. The Phase 2 analysis was registered before any outcome was examined; it named 2015–2020 entries and was widened to the report's window. Dating, matching, models and robustness checks are in the appendix.

### Which evidence predicts

![Each kind of evidence and its narrower versions: relative success in reaching approval (left), the adjusted risk ratio of advancing from Phase 2 within four years (middle), and the same with the other evidence lines held fixed (right)](report/output/figures/evidence_translates.png)

{{SECTION2_RS}}

### Does stronger or more specific evidence help?

![Likelihood of approval by strength of human genetic support](report/output/figures/genetic_dose_response.png)

![Phase 2 programs advancing within four years, by where the target's germline genetic evidence lay](report/output/figures/s3_specificity.png)

{{SECTION2_SPECIFIC}}

### Confirmatory hypotheses

![The pre-registered hypotheses](report/output/figures/s3_hypotheses.png)

{{SECTION3_HYPOTHESES}}

### By disease area

![Relative success of human genetic evidence by disease area](report/output/figures/genetics_by_area.png)

{{SECTION2_AREA}}

### By endpoint

![Endpoint classes](report/output/figures/s3_endpoints.png)

{{SECTION3_ENDPOINTS}}

### The drug's own pharmacology

{{SECTION2_DRUG}}

### Can the evidence pick individual programs?

Programs that entered Phase 1 in 2008–2016 were followed for ten years ({{section2.n_prediction|int}} programs, {{section2.n_prediction_positive|int}} approved), and models were tested on targets they had not seen.

![Held-out AUC with and without the evidence lines, and the change in AUC when each line is removed](report/output/figures/prediction.png)

{{SECTION2_PREDICTION}}

### What this means

{{SECTION3_MEANING}}
