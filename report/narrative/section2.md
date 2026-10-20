## Predictive power of preclinical evidence

{{SECTION2_SUMMARY}}

### Evidence lines and how they are matched

Each program aimed at a human protein (the entity's primary targets, resolved by an LLM from the entity's mechanism records and trial descriptions) is scored for the evidence its targets had **for the program's disease** in Open Targets Platform 26.09, **as of the year before the program entered the phase**. A target–disease association counts for the program's disease when the evidence disease is the same MONDO term, a subtype of it, or similar to it (Lin similarity ≥ 0.8, the criterion Minikel et al. used). Open Targets publishes a yearly series of each association's score, so evidence is taken as it stood before phase entry, not as it stands today. Evidence lines:

* **Human germline genetics:** GWAS credible sets (with locus-to-gene scores), gene burden tests, ClinVar, Genomics England PanelApp, Orphanet, Gene2Phenotype, ClinGen and UniProt; split into GWAS and rare-variant/Mendelian sources.
* **Somatic drivers:** COSMIC Cancer Gene Census, IntOGen and ClinVar somatic.
* **Mouse models:** IMPC phenotypes. **Expression:** differential expression in the disease (Expression Atlas). **Pathways:** Reactome. **Functional screens:** CRISPR screens.
* **Target-level properties** that are not disease-specific: loss-of-function intolerance (gnomAD LOEUF < 0.35) and pan-essentiality across DepMap cell lines.

Sources that encode clinical outcomes or literature co-mention (ChEMBL clinical precedence, Europe PMC) are not used. These programs (vaccines, cell and gene therapies and other entities without a single human protein target fall outside) reach approval more often than the full Section 1 cohort. Of the {{section2.n_programs|int}} programs on {{section2.n_targets|int}} targets scored, {{section2.evidence_coverage_ph1.genetic_any|pct}} of Phase 1 entrants had human genetic evidence for their disease at entry.

### Relative success

*Relative success* is the LOA of programs with the evidence divided by the LOA of programs without it (Nelson et al. 2015; Minikel et al. 2024). The 95% intervals resample targets, since programs on the same target are not independent.

{{RS_TABLE}}

![Relative success by evidence line](report/output/figures/relative_success_by_evidence.png)

{{SECTION2_RS}}

### Genetic dose–response

{{DOSE_TABLE}}

![Likelihood of approval by strength of human genetic support](report/output/figures/genetic_dose_response.png)

### What each line adds once the others are known

Programs with genetic evidence differ from programs without it in disease area, modality and era, and the evidence lines overlap. The table gives, for each phase, the relative risk of advancing for programs with each line, from one Poisson model containing every line together with disease area, modality, entity novelty and entry period (standard errors clustered by target).

{{JOINT_TABLE}}

{{SECTION2_JOINT}}

### Does the evidence predict which programs reach approval?

We followed programs that entered Phase 1 in 2008–2016 for ten years ({{section2.n_prediction|int}} programs, {{section2.n_prediction_positive|int}} approved), with every feature frozen at entry, and fitted logistic models on disease area, modality, novelty and entry year alone, and with the evidence lines added. Performance is measured on held-out targets (5-fold cross-validation grouped by target) and on a temporal split (trained on 2008–2012 entries, tested on 2013–2016).

{{PREDICTION_TABLE}}

Change in held-out AUC when each line is removed from the full model (paired target bootstrap):

{{ABLATION_TABLE}}

{{SECTION2_PREDICTION}}
