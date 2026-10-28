# Why efficacy failed: analysis plan

Committed before any attribution was run (`pipeline.attribution` labels the
programs and `report.attribution` analyses them). The question is what share of
efficacy failures come from a drug that never engaged its target adequately in
patients, from a target that was engaged and did not move the disease, and
from other causes.

## Cohort

Every program that Section 1 records as suspended for efficacy ("efficacy:
stated" or "efficacy: primary endpoint not met") in the phase it stopped in,
for phase entries 2015–2025. A program is an (entity, disease) pair, keyed by
`(moiety_id, mondo_id, phase)` so labels survive a programs rebuild. Phase 2
and Phase 3 are the primary cohort; Phase 1 efficacy stops are reported apart.
The trial that gave the program its reason is the **index trial**.

## Labels

An LLM reads, for each program, only the sources assembled for it, and
cites them by id:

- the index trial's registry record, posted results and linked results papers;
- the entity's other trials (every phase, any disease) with their classified
  outcome and governing endpoint class;
- PubMed abstracts on the entity's human pharmacology (exposure, receptor
  occupancy, target engagement, pharmacodynamic biomarkers), and on the entity
  in the program's disease;
- structured facts: the entity's primary targets and action, its FDA
  approvals, and other entities on the same primary target in the same or a
  related disease (Lin ≥ 0.5) with their furthest phase and approval.

It answers the three pillars of Morgan et al. (2012) for humans, each as
*shown adequate*, *shown inadequate* (or limited by toxicity before adequate
exposure), or *no human data*: (1) exposure at the site of action, (2)
binding/engagement of the target, (3) the expected functional or pathway
effect. It records whether pillar evidence came from the program's own disease
population and whether it predates the index trial's start.

It then gives one primary failure code, the Section 3 taxonomy with F1 split:

| Code | Meaning |
| --- | --- |
| F1a | Exposure or engagement shown inadequate, or dose capped by tolerability below adequate engagement |
| F1b | Molecule, not target: another entity on the same target succeeded in this disease, and no pillar evidence shows this one engaged adequately |
| F2 | Pillars 1–3 shown adequate (at least 2 of the 3, engagement among them), no benefit: the target or mechanism does not drive the disease as tested |
| F3 | Wrong population or subtype: benefit confined to a subgroup, or the sources attribute failure to patient selection |
| F4 | Wrong endpoint or timing: a proximal effect was shown and the clinical endpoint, duration or disease stage was the stated problem |
| F5 | Efficacy offset by on-target toxicity |
| F6 | Off-target or molecule-specific toxicity ended the program |
| F7 | Trial design or execution: high placebo response, underpowered, operational |
| F8 | Commercial: the sources show the program was stopped for business reasons, not a failed readout |
| F9 | Not an efficacy failure of the drug: met its endpoint, lost a non-inferiority comparison only on margin, or the index label is wrong |
| U | Indeterminate: no human pillar evidence, so non-engagement and a wrong target cannot be told apart |

U is a first-class answer: the model is told to use it whenever the sources
do not show engagement either way, and never to fill a gap from memory.

## Questions and estimands

- **Q1.** Share of efficacy failures in each code, Phase 2 and 3 together and
  by phase, with 95% intervals from a bootstrap that resamples entities.
- **Q2.** Among failures whose mechanism was testable (pillar 2 known either
  way), the share not engaged (F1a + F1b) against engaged without benefit (F2
  + F3 + F4).
- **Q3.** The same, outside oncology, where "engagement" is least confounded
  with tumour biology.
- **Q4.** How often adequate engagement was known **before** the index trial
  started (could a sponsor have tested the mechanism before Phase 2/3?).

## Checks, decided in advance

1. **Independent re-derivation.** A seeded random sample of 150 programs is
   labelled again under a second prompt that asks the pillar questions one at
   a time before any code, by a different model. Report agreement and Cohen's
   kappa on the primary code and on the three-way grouping (not engaged /
   engaged-no-benefit / other-or-indeterminate).
2. **External adjudication.** A seeded random sample of 60 programs is
   researched from scratch by agents with web access (company releases,
   publications, conference reports), blind to the pipeline's label, and coded
   with the same taxonomy. Report agreement and how often the pipeline said U
   where outside sources could decide.
3. **Construct validity, from data the labeller does not use as a rule.**
   (a) F2 programs should more often share their target with other entities
   whose programs in the same or a related disease were also suspended than
   F1a programs; (b) F1a programs should more often have a same-target entity
   that reached Phase 3 or approval in the disease than F2 programs (F1b uses
   that fact as a rule, so it is left out); (c) F2 should be rarer with
   germline genetic support for the disease (G3, Section 3) than F1a. Each is
   a two-sided Fisher test; a reversal is reported as evidence against the
   labels.
4. **Sensitivity.** Phase 2 only; Phase 3 only; oncology excluded; programs
   whose index reason is the sponsor's stated reason against a missed endpoint;
   only pillar evidence predating the index trial; one program per entity
   (first by phase entry); entity-level instead of program-level counting.
5. **Source coverage.** Share of programs with any human pillar source, by
   modality and entry year, so U can be read as a gap in public data rather
   than in biology.

## Amendment, 2026-10-27: web search for the indeterminate programs

Added after the bundle-only labels and the checks above had been run and read.
The blind adjudication decided a third of the programs the bundle left U, so
the U share measured what the bundle lacked as much as what is public. Every
Phase 2/3 program coded U is labelled again (`pipeline.attribution search`)
from the same bundle plus web search for human pharmacology and stated reasons
for failure: full-text papers, conference reports, FDA and EMA reviews,
company releases. The rubric, codes and validation rules are unchanged, and a
cited URL must be one the decision's own searches returned. The search label
replaces U in the main estimates; the bundle-only labels are reported as a
variant, and the re-derivation and adjudication stay scored against them.
Agreement between search and adjudication labels is reported on the programs
both labelled. Because the search can only resolve U, and engaged programs
leave more to find, the direction of any bias is stated alongside the result.
