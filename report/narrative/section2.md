## Predictive power of preclinical evidence

{{SECTION2_SUMMARY}}

### Evidence lines and how they are matched

Each program aimed at a human protein (the entity's primary targets, resolved by an LLM from the entity's mechanism records and trial descriptions) is scored for the evidence its targets had **for the program's disease** in Open Targets Platform 26.09, **as of the year before the program entered the phase**. A target–disease association counts for the program's disease when the evidence disease is the same MONDO term, a subtype of it, or similar to it (Lin similarity ≥ 0.8, the criterion Minikel et al. used). Each association's score is rebuilt year by year from its evidence items, each dated by when it became known (ClinVar records by their creation rather than their latest review, IMPC knockouts by their first data release), so evidence is taken as it stood before phase entry, not as it stands today. Evidence lines:

* **Human germline genetics:** GWAS credible sets (with locus-to-gene scores), gene burden tests, ClinVar, Genomics England PanelApp, Orphanet, Gene2Phenotype, ClinGen and UniProt; split into GWAS and rare-variant/Mendelian sources.
* **Somatic drivers:** COSMIC Cancer Gene Census, IntOGen and ClinVar somatic.
* **Mouse models:** IMPC phenotypes. **Expression:** differential expression in the disease (Expression Atlas). **Pathways:** Reactome. **Functional screens:** CRISPR screens.
* **Target-level properties** that are not disease-specific: loss-of-function intolerance (gnomAD v4.1 LOEUF < 0.35) and pan-essentiality (DepMap Public 24Q4 common-essential genes), taken from those releases rather than as of phase entry.

Sources that encode clinical outcomes or literature co-mention (ChEMBL clinical precedence, Europe PMC) are not used. Vaccines, cell and gene therapies and other entities without a single human protein target fall outside this analysis, so its programs reach approval more often than the Section 1 cohort as a whole. Of the {{section2.n_programs|int}} programs on {{section2.n_targets|int}} targets scored, {{section2.evidence_coverage_ph1.genetic_any|pct}} of Phase 1 entrants had human genetic evidence for their disease at entry.

### Relative success

*Relative success* is the LOA of programs with the evidence divided by the LOA of programs without it (Nelson et al. 2015; Minikel et al. 2024). The 95% intervals resample primary-target sets (an entity's primary targets taken together), since programs on the same targets are not independent.

{{RS_TABLE}}

![Relative success by evidence line](report/output/figures/relative_success_by_evidence.png)

{{SECTION2_RS}}

### Genetic dose–response

{{DOSE_TABLE}}

![Likelihood of approval by strength of human genetic support](report/output/figures/genetic_dose_response.png)

### What each line adds once the others are known

Programs with genetic evidence differ from programs without it in disease area, modality and era, and the evidence lines overlap. The table gives, for each phase, the relative risk of advancing for programs with each line, from one Poisson model containing every line together with disease area, modality, entity novelty and entry period (standard errors clustered by primary-target set).

{{JOINT_TABLE}}

{{SECTION2_JOINT}}

### Does the evidence predict which programs reach approval?

We followed programs that entered Phase 1 in 2008–2016 for ten years ({{section2.n_prediction|int}} programs, {{section2.n_prediction_positive|int}} approved), with the Open Targets evidence lines and novelty taken as of entry (loss-of-function constraint and pan-essentiality come from current releases), and fitted logistic models on disease area, modality, novelty and entry year alone, and with the evidence lines added. Performance is measured on held-out primary-target sets (out-of-fold predictions averaged over 20 repetitions of 5-fold cross-validation grouped by primary-target set and stratified by outcome; a single split moves the AUC by several points) and on a temporal split (trained on 2008–2012 entries, tested on 2013–2016).

{{PREDICTION_TABLE}}

Change in held-out AUC when each line is removed from the full model (human genetics: GWAS and rare-variant evidence removed together; lines carried by fewer than 100 programs are not modelled; paired bootstrap over target sets):

{{ABLATION_TABLE}}

{{SECTION2_PREDICTION}}
