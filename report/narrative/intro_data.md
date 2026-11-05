This report scores it from primary records. Every interventional drug, biological, genetic or combination-product study on ClinicalTrials.gov ({{section1.scale.ctgov_studies|int}} studies, snapshot of {{section1.snapshot}}) was resolved to the molecular entities it tests and the MONDO diseases it treats, and joined to every FDA approval we could document (Drugs@FDA, {{section1.scale.fda_approved_uses|int}} approved uses read from approval letters, labels, and {{section1.scale.cber_applications|int}} CBER biologics applications). The unit is a *development program*: one molecular entity developed for one indication. Every program that entered a phase in 2008–2019 is counted.

1. **Industry failure modes:** how often programs advance at each phase and why they stop.
2. **Predictive power of preclinical evidence:** which evidence known before a phase predicts approval and Phase 2 success, whether stronger or more specific evidence does better, and where it holds.

Every classification was made by an LLM reading the source record, and the main labels were checked against an independent re-derivation of a seeded sample (Appendix).
