## What translates to the clinic

{{SECTION3_SUMMARY}}

### Design

The cohort is programs on a human protein target that entered Phase 2 in the report's window, {{section3.window.start}} to {{section3.window.end}} ({{section3.c2.programs|int}} programs on {{section3.c2.targets|int}} primary-target sets), each followed for four years: a program *advanced* if a Phase 3 trial of its own started, or the FDA approved it for the disease, within four years ({{section3.c2.s4|pct}} did). Phase 2 is where a drug is first tested for efficacy in patients, so it is the first point at which the evidence's claim about the disease is put to the test; a four-year outcome also resolves for every entry in the window. The analysis plan was committed before any of these analyses touched outcomes; departures from it are marked below. The plan registered Phase 2 entries from 2015 to October 2020 and trials started from 2010; both now use the report's 2008–2019 window, so that every section describes the same programs. How evidence was dated and matched, the regimes, the models and the trial-level analysis are in the appendix.

### Confirmatory hypotheses

![The pre-registered hypotheses](report/output/figures/s3_hypotheses.png)

![Specificity of the genetic evidence](report/output/figures/s3_specificity.png)

{{SECTION3_HYPOTHESES}}

### Which evidence translates

The plan registered fifteen rules a sponsor could apply at Phase 2 entry, but they are not fifteen ideas: several are narrower versions of another (every program with a mouse model pointing the drug's way also has a mouse model of the disease), so a flat screen counts the same programs more than once. The rules are therefore grouped by the kind of evidence behind them. Each kind is tested once against programs without it, with a Holm correction across the {{section3.types_family|int}} preclinical kinds that could be tested; the benchmark, an approved drug on the target for a related disease, is shown beside them but is clinical precedent, not preclinical evidence. Each more specific version is then tested only against the rest of its own kind, with a Holm correction across the {{section3.refinements_family|int}} that could be tested. This grouping departs from the plan; the registered screen is in the appendix.

The figure sets each kind beside Section 2's measure for the same evidence: relative success in reaching approval from any phase, over the same entry years.

![Each kind of evidence and its narrower versions: relative success in reaching approval from any phase (left), and the adjusted risk ratio of advancing from Phase 2 within four years (right)](report/output/figures/evidence_translates.png)

{{SECTION3_RULES}}

{{SECTION3_MAP}}

### By endpoint

![Endpoint classes](report/output/figures/s3_endpoints.png)

{{SECTION3_ENDPOINTS}}

### Direction of effect

{{SECTION3_DIRECTION}}

{{SECTION3_CASES}}

### What this means

{{SECTION3_MEANING}}
