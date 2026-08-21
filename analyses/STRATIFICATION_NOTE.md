# Section-2 stratification: what we tried, and why we're not taking it into the post

**Status: exploratory, shelved. Recorded for reproducibility so it isn't silently
re-attempted.** No figure. TL;DR: the one robust result mostly *confirms and localizes*
something already in Melissa's rubric; the novel pieces are the least trustworthy; and
the cohort only powers an Oncology-vs-rest contrast, not the disease-area grid Section 2
literally asks for. Net value-add is marginal. The single keeper is a methodology
guardrail (below).

## The question

Melissa's Section-2 outline asks for predictive power "stratified by modality / disease
area." Does the predictive value of an evidence type *depend on* the area/modality?

## The method (this part is right, and worth reusing)

That is a **effect-modification / interaction** question. The rigorous test is a **pooled
logistic model with evidence × stratum interaction terms**, where the interaction block
is the formal test — NOT splitting the cohort and comparing per-stratum ablations
(small strata → underpowered; AUC is rank-only and hides small marginal effects; and
"compare two within-stratum results by eye" isn't a test of the difference). This
generalizes Stephen's `genetic_conditioning_adjusted.py` from a binary genetics axis to
the disease-area / modality axes built on Melissa's BIO-enrichment tables (PR #7:
`indication_bio_class`, `drug_bio_class`).

Cohort + evidence are HER constructs: `runner.load_cohort(min_phase=2)` (the
evidence-complete Phase-2+ T-I cohort), genetics scored with HER `genetic_only_v1`
additive scorer (Strong tier = score ≥ 1.4). `log(n_programs)` added as a shots-on-goal
covariate. Reproduce: `python3 analyses/predictive_power_by_stratum.py`.

## What we found

**Oncology reorganizes the evidence grammar** (LR block χ²=85, df=5, **p=7×10⁻¹⁷**):

| Evidence | main effect (non-onc) | × oncology | net in oncology |
|---|---|---|---|
| Strong genetics (`genetic_only_v1` ≥1.4) | 1.93 (favorable) | **4.37** (p=4e-8) | strongly favorable |
| DepMap **pan-essential** | 0.92 (≈neutral) | **0.08** (p=1e-4) | strong **failure** flag |
| gnomAD LOEUF<0.35 (constraint) | 0.47 (predicts failure) | **3.71** (p=3e-5) | **flips** favorable |
| SM tractability | 1.63 (favorable) | 0.44 (p=3e-3) | ≈neutral |
| Animal-model evidence | 1.31 (ns) | 1.06 (ns) | ns |

Read: outside oncology, hitting a constrained/essential-type gene is a liability and
tractability/genetics help; **in oncology the grammar inverts** — strong causal genetics
matters *more*, LOF-constrained genes become good targets, but **pan-essential** genes
are poison (no therapeutic window: kill the tumor, kill the patient).

## Why the value-add is marginal (the honest part)

1. **The robust result is already known — and already in her rubric.** Pan-essential =
   bad oncology target is textbook (differential dependency is the entire premise of
   DepMap). Melissa's own `scorers_rule_based.py` hard-codes `depmap_pan_essential` at
   RS 0.12 ("very negative"), and the LLM-agent prompt says pan-essential targets are
   "systemically undruggable." We *localize* the penalty to oncology and show it in
   trial outcomes — a confirmation/illustration, not a discovery.
2. **The genetics result just reinforces the existing thesis** (strong genetics helps;
   here, more so in oncology).
3. **The novel piece (LOEUF flip) is the least trustworthy** — constraint ↔ essentiality
   ↔ target-class confounding is exactly where a spurious interaction would appear.
4. **It isn't really "by disease area."** The cohort is n=2,589, **63% oncology**; only
   Oncology-vs-rest is powered. The 15-way area cut is a table of wide CIs.
5. **The modality axis is unstable** — the small "other" bucket separates (e.g.
   `cell_ess × other` CI [0.7, 19,000]). Not reportable.

## The one keeper: a methodology guardrail

The genetics × oncology interaction **flips sign depending on how genetics is coded**:

| genetics coding | prevalence | genetics × oncology |
|---|---|---|
| permissive "any genetic dim" | 83% | aOR **0.27** (looks like genetics matters *less*) |
| HER Strong tier (≥1.4) | 19% | aOR **4.37** (genetics matters *more*) |

The permissive flag is mostly weak OT-associations, which in oncology are near-noise and
dilute the signal to a *negative* — the exact "any-dimension dilution" trap in the
project's methodology rules. **Use the strength tier.** Corollary worth stating in the
post's caveats: the pooled "genetics dominates" headline is *oncology-diluted* under a
permissive flag — but it **survives** stratification under the correct strong-tier
coding. So this exercise's real output is defensive: the thesis held up to a stratified
stress test.

## Decision

Not pursued into the post; no figure. If a reviewer wants a single Section-2 nuance, the
only defensible one is the pan-essential/therapeutic-window point (robust, but known),
best paired with the selective-vs-pan-essential contrast (`depmap_n_dep_lineages`,
`depmap_mean_effect`) to make "differential dependency, not essentiality" explicit — that
richer version was scoped but not built.
