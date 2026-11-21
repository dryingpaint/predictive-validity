## Predictive power of preclinical evidence

{{SECTION2_SUMMARY}}

### Evidence and design

Evidence is grouped by the experimental system that produced it: **human genetics**, **tumour genetics**, **human diseased tissue**, **animal studies**, **cell studies**, **the molecule itself** and **early human pharmacology**. Two more kinds are kept apart because neither says the drug will work: the target's **safety risk**, and **clinical precedent**, what earlier drugs on the target did, which serves as the benchmark. Each program is scored for the evidence known **for its disease, as of the year before it entered the phase**. {{section2.evidence_coverage_ph1.genetic_any|pct0}} of Phase 1 entrants had human genetic evidence for their disease.

Two outcomes are measured on programs entering a phase in 2008–2019. *Relative success* is the likelihood of approval with the evidence divided by that without it (Nelson et al. 2015; Minikel et al. 2024). The second is whether a Phase 2 program advanced to Phase 3 or approval within four years: Phase 2 is the first test of efficacy in patients, so it is where the evidence's claim about the disease is first put to the test. The category chart and its figures cover the {{evidence_analysis.cohort.programs|int}} programs developed in the US ({{evidence_analysis.cohort.entries|int}} phase entries); the analyses that follow it cover all {{section2.n_programs|int}} programs, of which {{section3.c2.programs|int}} entered Phase 2 and {{section3.c2.s4|pct0}} advanced. The Phase 2 hypotheses, and the lines and hypotheses the categories added, were registered before their outcomes were examined. Dating, matching, models and robustness checks are in the appendix.

### Which evidence predicts

![Relative success in reaching approval for each area of evidence and its mutually exclusive groups, US-developed programs](report/output/figures/evidence_translates.png)

*How often US-developed programs that entered a phase in 2008–2019 went on to FDA approval when the evidence was known the year before they entered, relative to programs without it: 2× means twice as often. n: programs with the evidence. Bold: an area of evidence, each answering one question; indented: groups of its programs that do not overlap, so each program with the evidence sits in exactly one. Filled dot: the whole 95% range sits on one side of 1×, so the difference is unlikely to be chance. Arrowhead: the range runs past the edge of the chart. †: scored only for 2011–2019 entries, so it is not part of its area. The registered categories, every line tried and the counts are in the appendix.*

{{SECTION2_RS}}

**Published studies of the drug (exploratory).** Programs whose drug had already been studied in animals in the published literature reached approval less often, not more: {{evidence_analysis.areas.area_lit_animal.rs_rs|x2}}× as often for any published animal study, and {{evidence_analysis.lines.lit_animal_disease.rs_rs|x2}}× for a study in an animal model of the disease. In Phase 2 the gap remains when disease area, modality, era, novelty and precedent are held equal ({{evidence_analysis.lines.lit_animal_disease.s4_rr|x2}}×, {{evidence_analysis.lines.lit_animal_disease.s4_lo|x2}}–{{evidence_analysis.lines.lit_animal_disease.s4_hi|x2}}). A published study showing the drug acting on its target in people made no clear difference ({{evidence_analysis.lines.lit_human_engagement.rs_rs|x2}}×). The gap lies with smaller sponsors and with programs that lack human genetic support. Among Phase 2 programs of the 100 largest sponsor companies, those with a published animal-model study advanced as often as those without ({{evidence_analysis.published_strata.large.s4_with|pct0}} against {{evidence_analysis.published_strata.large.s4_without|pct0}}); among smaller sponsors, whose programs more often had one ({{evidence_analysis.published_strata.tiers.smaller.share|pct0}} against {{evidence_analysis.published_strata.large.share|pct0}}), they advanced less often ({{evidence_analysis.published_strata.tiers.smaller.s4_with|pct0}} against {{evidence_analysis.published_strata.tiers.smaller.s4_without|pct0}}). With genetic support a published study went with more advancing ({{evidence_analysis.published_strata.genetic.with.s4_with|pct0}} against {{evidence_analysis.published_strata.genetic.with.s4_without|pct0}}), without it with less ({{evidence_analysis.published_strata.genetic.without.s4_with|pct0}} against {{evidence_analysis.published_strata.genetic.without.s4_without|pct0}}). Holding sponsor size and genetic support fixed as well leaves {{evidence_analysis.published_strata.adjusted.rr|x2}}× ({{evidence_analysis.published_strata.adjusted.lo|x2}}–{{evidence_analysis.published_strata.adjusted.hi|x2}}). So a published animal record marks who develops a drug, and animal efficacy on its own is a weak basis for a program; it does not make one fail. These are comparisons within groups, not tests registered in advance. The searches found about three in four of the animal-model studies a blind hand search found, and fewer of the others (appendix).

### Which failure each kind of evidence prevents

![Which evidence goes with fewer or more Phase 1–3 efficacy stops, split by whether the drug reached its target](report/output/figures/efficacy_risk.png)

*How often programs with the evidence stopped for each kind of efficacy failure, relative to those without it, per phase entry. Here a ratio below 1 means fewer stops. Never adequately reached: tolerability capped the dose, toxicity offset the benefit, the registry gives a dose, exposure or formulation reason, or human evidence shows exposure or engagement too low. Reached without response: the drug engaged its target and the disease did not respond. Adjusted for disease area, modality, entry period, novelty, target precedent and phase; a filled dot is a difference whose 95% range excludes 1.*

**Evidence that the target is right prevents the efficacy failures where the drug reached its target.** Human genetics went with {{evidence_analysis.stop_risk.g3.stop_no_benefit_rr|reduction}} fewer stops where the drug engaged its target without benefit, mouse genetics resembling the disease {{evidence_analysis.stop_risk.altered_animal.stop_no_benefit_rr|reduction}} fewer, and an earlier drug on the target {{evidence_analysis.stop_risk.cat_precedent.stop_no_benefit_rr|reduction}} fewer. None of these changed how often a drug never adequately reached its target, except an earlier drug on the target, with {{evidence_analysis.stop_risk.cat_precedent.stop_not_reached_rr|reduction}} fewer such failures, as later drugs on a target someone has already drugged tend to reach it. A published study of the drug engaging its target in people is not tested against these failures ("not testable"), because they were judged from the same publications.

**Only evidence that the target causes the disease prevents the commonest failure.** Splitting the stops where the drug engaged its target without benefit by failure mode (Section 1), rare-variant human genetics went with {{failure_modes.lines.all.tier_rare_only.mode_not_causal_rr|reduction}} fewer stops where the target was not causal, and a tumour mutation matching the drug with {{failure_modes.lines.all.somatic_concordant.mode_not_causal_rr|reduction}} fewer. Mouse genetics resembling the disease went with {{failure_modes.lines.all.altered_animal.mode_not_causal_rr|reduction}} fewer ({{failure_modes.lines.all.altered_animal.mode_not_causal_rr|x2}}×, {{failure_modes.lines.all.altered_animal.mode_not_causal_lo|x2}}–{{failure_modes.lines.all.altered_animal.mode_not_causal_hi|x2}}), a smaller effect at the edge of chance. Changes in diseased tissue did not clearly lower them ({{failure_modes.lines.all.expression.mode_not_causal_rr|x2}}×), and a measured binding affinity did not lower stops where the target was never reached ({{failure_modes.lines.all.area_measured.stop_not_reached_rr|x2}}×). Leaving out entries that stopped for a business, operational or positive-readout reason, which can no longer fail on efficacy, leaves rare-variant genetics at {{failure_modes.lines.cause_specific.tier_rare_only.mode_not_causal_rr|x2}}×. Rates are per phase entry, adjusted as in the chart above; bold where the 95% range excludes 1.

{{ENGAGED_EVIDENCE_TABLE}}

### What predicts safety failures

![Which safety evidence goes with more Phase 1–3 safety stops, with efficacy stops as a control](report/output/figures/safety_risk.png)

*How often programs with each safety signal stopped for safety, and for efficacy as a control, relative to those without it, per phase entry. Here a ratio above 1 means more stops. Adjusted as in the efficacy chart (exploratory).*

**Nothing measured before entry clearly predicts safety stops.** Safety risk is a property of the target and the drug, not of the target's link to the disease, so it rests on other evidence: people rarely carrying broken copies of the gene or mice without it dying young ({{evidence_analysis.stop_risk.liability.stop_safety_rr|x2}}×, {{evidence_analysis.stop_risk.liability.stop_safety_lo|x2}}–{{evidence_analysis.stop_risk.liability.stop_safety_hi|x2}}), mutant mice with a phenotype in a vital organ ({{evidence_analysis.stop_risk.ko_vital_organ.stop_safety_rr|x2}}×), an earlier drug on the same target stopping for safety ({{evidence_analysis.stop_risk.earlier_safety_stop.stop_safety_rr|x2}}×, {{evidence_analysis.stop_risk.earlier_safety_stop.stop_safety_lo|x2}}–{{evidence_analysis.stop_risk.earlier_safety_stop.stop_safety_hi|x2}}), and a drug binding another protein within 10-fold of its target ({{evidence_analysis.stop_risk.poor_selectivity.stop_safety_rr|x2}}×). Three of the four lean towards more safety stops, but every range includes 1. Only about one program in {{evidence_analysis.stop_risk.liability.stop_safety_rate_without|inverse}} stops for safety, and stops traced to a cause under-count safety, so the data can show only a large effect. Against efficacy stops, which they should not predict, only a vital-organ phenotype differs ({{evidence_analysis.stop_risk.ko_vital_organ.stop_efficacy_rr|x2}}×), most likely because a strong mouse phenotype also marks a target with real biology.

### What programs enter on

Only {{evidence_analysis.basis.predictive|pct0}} of the {{evidence_analysis.basis.entries|int}} US-developed phase entries had any of the evidence that predicts approval: genetic support, a gene recurrently mutated in the cancer, mouse genetics resembling the disease, or a drug on the target approved for a related disease. Most of the rest still had evidence of a kind the field relies on.

| What the program had before entering the phase | Share of entries |
| :---- | :---- |
| Evidence that predicts approval (any of the four above) | {{evidence_analysis.basis.predictive|pct0}} |
| A published study of the drug itself (an animal model of the disease, healthy animals, or target engagement in people) | {{evidence_analysis.basis.published|pct0}} |
| A drug on the same target approved, for any disease | {{evidence_analysis.basis.approved_any|pct0}} |
| Binding to its target measured at 100 nM or better | {{evidence_analysis.basis.potent|pct0}} |

Of the entries with no predictive evidence, {{evidence_analysis.basis.rest.published|pct0}} had a published study of the drug, which in these data goes with less success, not more, and {{evidence_analysis.basis.rest.approved_unrelated|pct0}} were on a target approved only for unrelated diseases, which also goes with less success ({{evidence_analysis.lines.approved_unrelated_only.rs_rs|x2}}×). {{evidence_analysis.basis.rest.none|pct0}} had none of the evidence measured here; they rest on the sponsor's unpublished data or reasoning from mechanism. Entering a trial requires evidence of safety, not of efficacy, and the decision to advance from Phase 2 rests on the sponsor's own trial results, which no public source shows. A line counts here only where it is known to be present.

### Does stronger or more specific evidence help?

![Likelihood of approval by strength of human genetic support](report/output/figures/genetic_dose_response.png)

![Phase 2 programs advancing within four years, by where the target's germline genetic evidence lay](report/output/figures/s3_specificity.png)

{{SECTION2_SPECIFIC}}

### Biology or sponsor commitment?

![A: the risk ratio of advancing from Phase 2 within four years for programs with genetic evidence for their disease, as reported, with sponsor size, with each large sponsor compared with itself, and within sponsor-size tiers. B: for each large sponsor with at least three programs of each kind, the share of its genetically supported Phase 2 programs that advanced against the share of its other programs. C: at the first randomised Phase 2 efficacy trial, the risk ratio of meeting the primary endpoint and of advancing after a met or a missed endpoint](report/output/figures/sponsor_confound.png)

{{SECTION3_COMMITMENT}}

### Confirmatory hypotheses

![The pre-registered hypotheses](report/output/figures/s3_hypotheses.png)

{{SECTION3_HYPOTHESES}}

### By disease area

![Relative success of human genetics and of mouse genetics by disease area](report/output/figures/genetics_by_area.png)

{{SECTION2_AREA}}

### The drug's own pharmacology

{{SECTION2_DRUG}}

### What this means

{{SECTION3_MEANING}}
