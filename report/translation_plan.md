# Which evidence translates: analysis plan

Committed before any of these analyses was run on outcomes (`report/section3.py`
implements it). The headline genetics result of Section 2 was already known; the
hypotheses below test where it comes from, on which endpoints it holds, and which
evidence rules predict well enough to call a "model".

## Cohorts and outcomes

- **C2 (primary).** Programs on a human protein target entering Phase 2 from
  2015-01-01 to 2020-10-20, so every one has four years of follow-up before
  2024-10-20 (the snapshot minus the 24-month inactivity window). Outcome
  **S4**: the program advanced (a Phase 3 trial of its own started, or FDA
  approval for the disease) within four years of Phase 2 entry. S4 needs no
  inferred suspension, so advancing and failing programs are observed alike.
- **C1, C3.** The same for Phase 1 and Phase 3 entries (C1 is a negative-control
  transition; C3 carries the selection of programs that reached it).
- **T (trials).** Industry Phase 2/3 randomised trials since 2010 whose
  governing primary is an efficacy endpoint (`preclin.trial_endpoint`) and whose
  primary result is readable (`preclin.trial_outcome`: met, not met, mixed =
  not met). Outcome: **NOT MET**.
- **Regimes.** ONC: oncology area. DD (disease-defining): the program disease
  is a MONDO hereditary disease (descendant of MONDO:0003847) and the target
  has curated Mendelian evidence for it. COM: everything else (common non-cancer
  disease, the headline regime).

## Exposures (all frozen at the year before phase entry or trial start)

- **Germline genetics, by specificity.** G3: evidence for the program disease
  (same term, subtype, or Lin ≥ 0.8). G2: best Lin 0.5–0.8. G1: the target has
  germline genetic evidence only for diseases with Lin < 0.5. G0: none.
- **Families and strength** (evidence rows, `preclin.ot_evidence`): GWAS
  (locus-to-gene ≥ 0.8 / 0.5–0.8 / < 0.5); gene burden (p < 2.5e-6 / weaker);
  curated Mendelian (ClinGen definitive or strong, PanelApp green, Gene2Phenotype
  definitive or strong, ClinVar pathogenic; Orphanet; UniProt); somatic drivers
  (CGC, IntOGen, ClinVar somatic); mouse models, split into IMPC
  high-throughput knockouts and literature-curated MGI models, with PhenoDigm
  score quartiles; Expression Atlas (|log2FC| ≥ 1 / smaller); Reactome; CRISPR.
- **Direction.** Drug action from `moiety_target.action`: decreases function
  (inhibitor, antagonist, blocker, negative modulator, inverse agonist,
  degrader, ligand-neutralising binder, expression reduction), increases
  function (agonist, partial agonist, activator, positive modulator, opener,
  replacement, expression increase), or address-only (cell-depleting). Genetic
  direction from `direction_on_target` × `direction_on_trait` (gene burden,
  ClinVar, Orphanet, Gene2Phenotype): loss of function protective, or gain of
  function raising risk, is concordant with decreasing function; loss of
  function raising risk is concordant with increasing function. A program is
  concordant, discordant, mixed, or undirected (genetic evidence without
  direction).
- **Target liability** (current values): pan-essential (DepMap), loss-of-function
  intolerant (gnomAD LOEUF < 0.35), mouse knockout lethal before weaning (MP
  descendants of MP:0010770).
- **Endpoint class** of each trial's governing primary: proximal (B1 target
  engagement, B2 exploratory biomarker, B3 regulatory surrogate), intermediate
  (B4 objective physiological, B5 clinician scale, B6 patient-reported), distal
  (B7 disease events, B8 hard outcomes); oncology O1 response, O2 progression,
  O3 survival.

## Confirmatory hypotheses (Holm-corrected together, α = 0.05)

- **H1.** In COM, G3 raises S4 against G0.
- **H2.** Within target: among Phase 2 programs of the same target that differ
  on G3, those with G3 have higher S4 (conditional logit, target strata).
- **H3.** Among C2 programs with directional genetic evidence or undirected
  genetic evidence, S4 rises across discordant < undirected < concordant
  (1-df trend).
- **H4.** In T outside oncology, the effect of G3 on NOT MET differs between
  proximal and distal endpoints (1-df trend across proximal, intermediate,
  distal; two-sided).
- **H5.** G3 lowers efficacy failure more than it lowers business or
  operational failure (cause-specific risk ratios among C2 and C3 programs).
- **H6.** Outside oncology, target liability raises safety failure, and not
  efficacy failure.
- **H7.** In ONC, a concordant somatic driver for the program's tumour raises S4.

## Models

Modified Poisson (log link, robust errors clustered by primary-target set),
adjusted for disease area, modality, entity novelty, entry period and target
precedent (an FDA-approved entity on the target before entry). Every estimate
reports programs, distinct targets, the exposed success rate (PPV), coverage
(share of successes with the exposure) and the risk ratio with its 95% CI.
Descriptive maps (families, strength, freeze dates) use the same model and are
not tested for significance beyond their intervals. Cells need at least 15
distinct exposed targets to be shown.

## Controls and robustness

- **Freeze curve.** Each family's risk ratio with evidence frozen at entry−1
  against all evidence known today; a rise flags hindsight.
- **Disease-matching null.** Programs' diseases permuted within disease area
  (target kept); G3's risk ratio over 200 permutations.
- **Negative controls.** G1 (target genetics for unrelated diseases); the Phase 1
  transition; PK/operational failure as an outcome.
- **Influence.** Leave the most influential target out; leave each of the five
  largest target families out.
- **Trials.** Registry-posted results only, with a US site and primary
  completion from 2017-01-18 (FDAAA reporting) as the primary set; all readable
  trials as the secondary set; mixed results as met; the program-level S4
  stratified by the endpoint class of the program's first randomised Phase 2
  efficacy trial (needs no posted results).

## Case studies: predictive models

A model is a rule applicable at entry: evidence family × strength × direction ×
drug action. Rules, fixed now:

- M1 protective loss-of-function burden + a drug that decreases function;
- M2 Mendelian evidence for the disease + a drug that increases function or
  replaces the gene (DD regime);
- M3 Mendelian evidence extrapolated to a common disease (COM, G3 curated);
- M4 GWAS locus-to-gene ≥ 0.8 for the indication;
- M5 GWAS and rare-variant evidence for the same disease (allelic series);
- M6 concordant somatic driver + a drug that decreases function (ONC);
- M7 IMPC knockout phenotype matching the disease (PhenoDigm top quartile);
- M8 literature-curated mouse model of the disease;
- M9 expression up in disease + a drug that decreases function (expected weak);
- M10 Reactome pathway evidence (expected weak);
- M11 target liability + a drug that decreases function (expected negative);
- B1 precedent: an approved drug on the target for a disease within Lin 0.5.

Targets are split 60/40 (seeded) into discovery and confirmation. A rule is
"particularly predictive" when, in discovery, its S4 risk ratio has a 90%
target-bootstrap lower bound above 1.3, and, in confirmation, its point
estimate is at least 1.2 with a one-sided 95% lower bound above 1, and the
estimate holds without its most influential target. For each such rule, four
successes and four failures are drawn at random (seeded), plus its three most
influential targets, plus every strong-evidence program that failed for
efficacy with a readable not-met randomised trial. Each case is checked by
agents against primary sources (evidence dated before entry; outcome in the
registry, publications and FDA letters), and failures are coded F1 (exposure
or engagement never shown) to F8 (commercial).
