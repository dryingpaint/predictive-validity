### Why programs stop

For {{stop_causes.inferred.programs|int}} of the {{stop_causes.stops|int}} Phase 2 and 3 stops among 2008–2019 entries, the registry gives no usable reason: none at all, only "sponsor decision", an unspecified "other" reason, a mixed primary endpoint, or an efficacy reason that the reading of efficacy failures below found wrong. An LLM traced each of these through the program's trials and a web search of company releases, filings and news. It found a sourced cause for {{stop_causes.inferred.resolved|pct0}} and a likely cause for {{stop_causes.inferred.likely_resolved|pct0}}. How it works, and how well it does on stops whose reason is known, is in the appendix.

**Some recorded stops were not stops.** Tracing found that {{stop_causes.not_a_stop.not_stopped|int}} Phase 2 and 3 programs the registry shows as stopped had carried on: under another registry, region, name or combination, or through FDA approval for the disease. Another {{stop_causes.not_a_stop.not_a_program|int}} were never development programs: academic studies using an approved drug as a research tool, or drug-interaction and dosing studies. The cause shares in this section leave all of them out, and the success rates above count what tracing found: a later phase as advancing, development still under way as still running, and non-programs not at all. Read from ClinicalTrials.gov alone, counting them all as stops, the likelihood of approval would be {{section1.registry.loa|pct}} across all programs rather than {{section1.overall.loa|pct}}, and {{section1.registry_us.loa|pct}} for programs developed in the US rather than {{section1.us_site.loa|pct}}.

**Efficacy is the main reason programs stop in Phases 2 and 3.** Counting sourced and likely causes, efficacy or exposure ended {{stop_causes.by_phase.2.shown.efficacy.share|pct0}} of Phase 2 stops and {{stop_causes.by_phase.3.shown.efficacy.share|pct0}} of Phase 3 stops, against {{stop_causes.recorded.efficacy.share|pct0}} of Phase 2 and 3 stops as the registry records them. Sponsor decisions are the next largest cause in Phase 2 ({{stop_causes.by_phase.2.shown.sponsor_decision.share|pct0}}) and the largest in Phase 1 ({{stop_causes.by_phase.1.shown.sponsor_decision.share|pct0}}). In Phase 3, {{stop_causes.by_phase.3.shown.positive_not_advanced.share|pct0}} of stops followed a positive readout. Safety is rare once only stops whose sponsor gives a safety reason count: {{stop_causes.by_phase.2.shown.safety.share|pct0}} in Phase 2 and {{stop_causes.by_phase.3.shown.safety.share|pct0}} in Phase 3.

**What each cause breaks down into.** Shares are of Phase 2 and 3 stops whose cause is sourced.

* **Sponsor decisions**: a source names the decision for {{stop_causes.sourced.sponsor_decision|pct0}} of these stops; the other {{stop_causes.likely_only.sponsor_decision|pct0}} are the likely cause where no source gives one, and have no subcause. Where a source gives it, by subcause:
    * Other programs put first: {{stop_causes.subcauses.sponsor_decision.portfolio_prioritisation.share|pct0}}
    * Sponsor ran out of money or closed: {{stop_causes.subcauses.sponsor_decision.funding_or_closure.share|pct0}}
    * Partner left: {{stop_causes.subcauses.sponsor_decision.partner_exit.share|pct0}}
    * Commercial or competitive reasons: {{stop_causes.subcauses.sponsor_decision.commercial_or_competitive.share|pct0}}
    * Only "business reasons" given: {{stop_causes.subcauses.sponsor_decision.not_stated.share|pct0}}
* **Positive readouts that went no further**, by subcause:
    * Sponsor's own reasons: {{stop_causes.positive_discontinued|pct0}} in all, chiefly other programs put first ({{stop_causes.subcauses.positive_not_advanced.portfolio_prioritisation.share|pct0}})
    * Approved outside the US: {{stop_causes.subcauses.positive_not_advanced.approved_outside_us.share|pct0}}
    * Regulator declined it: {{stop_causes.subcauses.positive_not_advanced.regulator_declined.share|pct0}}
    * No reason given: {{stop_causes.subcauses.positive_not_advanced.not_stated.share|pct0}}
    * {{stop_causes.named.positive_not_advanced.likely|pct0}} have a likely rather than a sourced reason
* **Safety stops**, by subcause:
    * Harms in patients, mechanism not stated: {{stop_causes.subcauses.safety.harm_mechanism_not_stated.share|pct0}}
    * Off-target toxicity: {{stop_causes.subcauses.safety.off_target_toxicity.share|pct0}}
    * Animal toxicology findings: {{stop_causes.subcauses.safety.animal_toxicology.share|pct0}}
    * On-target toxicity: {{stop_causes.subcauses.safety.on_target_toxicity.share|pct0}}
* **Operational stops**, by subcause:
    * Slow enrollment: {{stop_causes.subcauses.operational.enrollment.share|pct0}}
    * COVID-19: {{stop_causes.subcauses.operational.covid_19.share|pct0}}
    * Trials redesigned or replaced: {{stop_causes.subcauses.operational.trial_redesigned.share|pct0}}
* **Efficacy failures**, by what the evidence shows about target engagement (shares of all Phase 2 and 3 programs that stopped for efficacy or exposure):
    * Engaged its target, but the disease did not respond: {{attribution.phase23.subcauses.engaged_no_benefit.share|pct0}}
    * No human evidence of engagement either way: {{attribution.phase23.subcauses.no_engagement_data.share|pct0}}
    * Never engaged its target or reached adequate exposure: {{attribution.phase23.subcauses.not_engaged.share|pct0}}
    * Trial design, population or endpoint: {{attribution.phase23.subcauses.trial_design.share|pct0}}
    * Toxicity offset any efficacy: {{attribution.phase23.subcauses.toxicity_offset.share|pct0}}

    Where engagement is known, {{attribution.phase23.testable.not_engaged_share|pct0}} ({{attribution.phase23.testable.lo|pct0}}–{{attribution.phase23.testable.hi|pct0}}) were never engaged, as often in Phase 3 ({{attribution.by_phase.3.testable.not_engaged_share|pct0}}) as in Phase 2 ({{attribution.by_phase.2.testable.not_engaged_share|pct0}}); in {{attribution.phase23.details.other_drug_on_target_worked.n|int}} of them this is inferred because another drug on the same target worked. The first kind points to a gap in models of the disease, the third to a gap in models of dose and engagement.
* **Stops no source explains**, by signal:
    * Sponsor started no later trial: {{stop_causes.subcauses.unknown.sponsor_went_quiet.share|pct0}}
    * Drug dropped while its sponsor carried on: {{stop_causes.subcauses.unknown.drug_dropped.share|pct0}}

![Top: Phase 1, 2 and 3 stops by cause, phase entries 2008–2019, leaving out programs that did not actually stop or were not development programs; where no source states the cause, the likely cause is counted. Below: each cause broken down by subcause, one panel per phase. Solid: the stop's own text or a source states the subcause; pale: the search found it likely but no source says it; "not stated": the sources say no more than the cause; "cause likely, not sourced": the cause itself is only likely, so it has no subcause. For efficacy, the panels show what the evidence says about target engagement; programs whose efficacy failure was not attributed are those without an efficacy label](report/output/figures/stop_causes_by_phase.png)

**Over time.** Counting sourced and likely causes, and leaving out records that were not stops, efficacy or exposure was the cause of {{stop_causes.by_period.2008-2011.shown.efficacy.share|pct0}} of stops among programs entering in 2008–2011, {{stop_causes.by_period.2012-2015.shown.efficacy.share|pct0}} in 2012–2015 and {{stop_causes.by_period.2016-2019.shown.efficacy.share|pct0}} in 2016–2019; sponsor decisions {{stop_causes.by_period.2008-2011.shown.sponsor_decision.share|pct0}}, {{stop_causes.by_period.2012-2015.shown.sponsor_decision.share|pct0}} and {{stop_causes.by_period.2016-2019.shown.sponsor_decision.share|pct0}}, and a positive readout not yet advanced {{stop_causes.by_period.2008-2011.shown.positive_not_advanced.share|pct0}}, {{stop_causes.by_period.2012-2015.shown.positive_not_advanced.share|pct0}} and {{stop_causes.by_period.2016-2019.shown.positive_not_advanced.share|pct0}}. Among entries from 2015 to 2025 ({{stop_causes.recent.stops|int}} stops, many later programs still running), the shares are {{stop_causes.recent.shown.efficacy.share|pct0}} efficacy or exposure, {{stop_causes.recent.shown.sponsor_decision.share|pct0}} sponsor decision and {{stop_causes.recent.shown.positive_not_advanced.share|pct0}} positive readouts.

Safety counts only stops whose sponsor states a safety reason, and the classifier, tested on stops whose reason is known, often read safety stops as efficacy. Safety is therefore under-counted and the efficacy share is an upper estimate.
