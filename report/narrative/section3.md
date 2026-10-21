## What translates to the clinic

{{SECTION3_SUMMARY}}

### Design

The analysis plan ([report/translation_plan.md](report/translation_plan.md)) was committed before any of these analyses touched outcomes; departures from it are marked below.

* **Cohort and outcome.** Programs on a human protein target that entered Phase 2 from 2015-01-01 to 2020-10-20 ({{section3.cohorts.C2.all.programs|int}} programs on {{section3.cohorts.C2.all.targets|int}} primary-target sets). Each has at least four years of follow-up before the 24-month inactivity cutoff, so the outcome needs no inferred suspension: a program *advanced* if a Phase 3 trial of its own started, or the FDA approved it for the disease, within four years of entering Phase 2 ({{section3.cohorts.C2.all.s4|pct}} did). The same is done for Phase 1 entrants (a negative control: genetics should matter little for safety and dosing studies) and Phase 3 entrants (approval within four years).
* **Evidence.** Every Open Targets 26.09 evidence row for the program's primary targets, each carrying its own date, frozen at the year before entry and matched to the program's disease on MONDO: the same term, a subtype, or Lin similarity ≥ 0.8 (*G3*, genetics for the disease); a disease at Lin 0.5–0.8 only (*G2*); germline evidence only for unrelated diseases (*G1*); none (*G0*). Evidence is split by family and strength (the best GWAS locus-to-gene score, ≥ 0.8, 0.5–0.8 or below; ClinVar pathogenic with multiple submitters or expert review, ClinGen or Gene2Phenotype definitive or strong, PanelApp green; mouse phenotype match in the top quartile), and mouse models are split into IMPC high-throughput knockouts and literature-curated MGI models.
* **Regimes.** Oncology; *hereditary* (the disease is a MONDO hereditary disease and the target has curated Mendelian evidence for it); and every other disease (*non-oncology*, the regime of the headline hypothesis).
* **Models.** Modified Poisson regression (risk ratios) with standard errors clustered by primary-target set, adjusted for disease area, modality, entity novelty, entry period and target precedent (an FDA-approved entity on the target before entry). The seven confirmatory hypotheses are Holm-corrected together.
* **Trials.** Randomised industry Phase 2/3 trials since 2010 whose governing primary endpoint measures efficacy and whose result is readable ({{section3.trials.n|int}} trials; an LLM classified each trial's governing primary endpoint from its registry entry, without the drug's name). Outcome: primary endpoint not met (a mixed result counts as not met).

### Confirmatory hypotheses

{{S3_HYPOTHESES_TABLE}}

{{SECTION3_HYPOTHESES}}

### Which evidence translates

{{S3_MAP_TABLE}}

![Evidence map](report/output/figures/s3_evidence_map.png)

{{SECTION3_MAP}}

### By endpoint

{{S3_ENDPOINT_TABLE}}

![Endpoint classes](report/output/figures/s3_endpoints.png)

{{SECTION3_ENDPOINTS}}

### Direction of effect

{{SECTION3_DIRECTION}}

### Models that predict: rules applied at Phase 2 entry

A *model* here is a rule a sponsor could have applied at Phase 2 entry without knowing the outcome: an evidence family, strength, direction and drug action. Rules M1–M11 and the precedent benchmark B1 were fixed in the plan; P1–P3 (marked \*) were added after the plan, once the direction labels existed. Target sets were split 60/40 at random; a rule counts as *particularly predictive* when, on the discovery targets, its risk ratio's 90% bootstrap lower bound is above 1.3, and, on the held-out targets, its risk ratio is at least 1.2 with a one-sided 95% lower bound above 1, and it stays at least 1.2 without its most influential target.

{{S3_RULES_TABLE}}

![Rule screen](report/output/figures/s3_rules.png)

{{SECTION3_RULES}}

{{SECTION3_CASES}}

### What this means

{{SECTION3_MEANING}}
