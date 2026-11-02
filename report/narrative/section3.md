## What translates to the clinic

{{SECTION3_SUMMARY}}

### Design

The cohort is programs on a human protein target that entered Phase 2 from {{section3.window.start}} to {{section3.window.end}} ({{section3.c2.programs|int}} programs on {{section3.c2.targets|int}} primary-target sets), each followed for four years: a program *advanced* if a Phase 3 trial of its own started, or the FDA approved it for the disease, within four years ({{section3.c2.s4|pct}} did). The analysis plan was committed before any of these analyses touched outcomes; departures from it are marked below. How evidence was dated and matched, the regimes, the models and the trial-level analysis are in the appendix.

### Confirmatory hypotheses

{{S3_HYPOTHESES_TABLE}}

![Specificity of the genetic evidence](report/output/figures/s3_specificity.png)

{{SECTION3_HYPOTHESES}}

### Which evidence translates

![Evidence map](report/output/figures/s3_evidence_map.png)

{{SECTION3_MAP}}

### By endpoint

![Endpoint classes](report/output/figures/s3_endpoints.png)

{{SECTION3_ENDPOINTS}}

### Direction of effect

{{SECTION3_DIRECTION}}

### Which kinds of evidence predict, and whether being more specific helps

The plan registered fifteen rules a sponsor could apply at Phase 2 entry, but they are not fifteen ideas: several are narrower versions of another (every program with a mouse model pointing the drug's way also has a mouse model of the disease), so a flat screen counts the same programs more than once. The rules are therefore grouped by the kind of evidence behind them. Each kind is tested once against programs without it, with a Holm correction across the {{section3.types_family|int}} preclinical kinds that could be tested; the benchmark, an approved drug on the target for a related disease, is shown beside them but is clinical precedent, not preclinical evidence. Each more specific version is then tested only against the rest of its own kind, with a Holm correction across the {{section3.refinements_family|int}} that could be tested. This grouping departs from the plan; the registered screen is in the appendix.

![Kinds of evidence and their more specific versions](report/output/figures/s3_evidence_types.png)

{{SECTION3_RULES}}

{{SECTION3_CASES}}

### What this means

{{SECTION3_MEANING}}
