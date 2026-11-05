## Predictive power of preclinical evidence

{{SECTION2_SUMMARY}}

### Evidence and design

Evidence is grouped by the experimental system that produced it: **human genetics**, **tumour genetics**, **human diseased tissue**, **animal studies**, **cell studies**, **the molecule itself** and **early human pharmacology**. Two more kinds are kept apart because neither says the drug will work: the target's **safety risk**, and **clinical precedent**, what earlier drugs on the target did, which serves as the benchmark. Each program is scored for the evidence known **for its disease, as of the year before it entered the phase**. {{section2.evidence_coverage_ph1.genetic_any|pct0}} of Phase 1 entrants had human genetic evidence for their disease.

Two outcomes are measured on programs entering a phase in 2008–2019. *Relative success* is the likelihood of approval with the evidence divided by that without it (Nelson et al. 2015; Minikel et al. 2024). The second is whether a Phase 2 program advanced to Phase 3 or approval within four years: Phase 2 is the first test of efficacy in patients, so it is where the evidence's claim about the disease is first put to the test. The category chart and its figures cover the {{evidence_analysis.cohort.programs|int}} programs developed in the US ({{evidence_analysis.cohort.entries|int}} phase entries); the analyses that follow it cover all {{section2.n_programs|int}} programs, of which {{section3.c2.programs|int}} entered Phase 2 and {{section3.c2.s4|pct0}} advanced. The Phase 2 hypotheses, and the lines and hypotheses the categories added, were registered before their outcomes were examined. Dating, matching, models and robustness checks are in the appendix.

### Which evidence predicts

![Relative success in reaching approval for each area of evidence and its mutually exclusive groups, US-developed programs](report/output/figures/evidence_translates.png)

*How often US-developed programs that entered a phase in 2008–2019 went on to FDA approval when the evidence was known the year before they entered, relative to programs without it: 2× means twice as often. n: programs with the evidence. Bold: an area of evidence, each answering one question; indented: groups of its programs that do not overlap, so each program with the evidence sits in exactly one. Filled dot: the whole 95% range sits on one side of 1×, so the difference is unlikely to be chance. Arrowhead: the range runs past the edge of the chart. †: scored only for 2011–2019 entries, so it is not part of its area. The registered categories, every line tried and the counts are in the appendix.*

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
