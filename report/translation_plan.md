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

## Amendment, 2026-11-03: evidence categories and new lines

Committed before any line below was computed against an outcome. Coverage
counts were measured on the cohort without outcomes. The results for human
genetics, tumour genetics, diseased tissue, genetically altered animals,
target liability and potency are already reported, so regrouping them is not
blind and their category estimates are not new confirmations.

**Cohort.** Entries with a US-sited industry trial in the phase, entering
2008–2019 (10,012 entries; 7,372 with a single resolved human protein target
and a disease). Outcome S4 as above; the safety-risk category is tested against
safety stops, and every efficacy category is also reported against efficacy
stops. Evidence is frozen at the year before entry.

**Categories.** Efficacy evidence is grouped by the experimental system that
produced it; within a category, subcategories separate claims about the target
from claims about the drug.

1. **Human genetics.** Rare-variant and Mendelian; GWAS; both together;
   direction concordant with the drug; curated disease mechanism (Reactome,
   which shares 81% of its 188 entries with germline genetics for the disease).
2. **Tumour genetics** (ONC). Recurrently mutated in this cancer; mutation
   concordant with the drug.
3. **Human diseased tissue.** RNA level changed (Expression Atlas,
   |log2FC| ≥ 1.1); raised, with a drug that decreases function.
4. **Animal studies.** Genetically altered animals (MGI curated, IMPC screen,
   PhenoDigm top quartile, direction concordant); the drug in an animal model of
   the disease (pilot); the drug's pharmacology in healthy animals (pilot).
   Animal toxicology is unpublished before entry and is not used: FDA reviews of
   it exist only for approved drugs.
5. **Cell studies.** CRISPR screens in cancer cells; first published 2019, so
   scored on current data as hindsight only.
6. **The molecule** (small molecules). Potency on the primary target (best
   pChEMBL ≥ 7, i.e. 100 nM or better, the threshold the report already uses;
   ChEMBL documents dated before entry); selectivity (primary-target
   potency at least 1 log unit above the best off-target potency, among drugs
   measured on both); drug-likeness (at most one Rule-of-5 violation) and, for
   neurology and psychiatry programs, brain-penetrance properties (TPSA < 90,
   MW < 450, H-bond donors ≤ 3), from PubChem computed properties. The potency
   threshold was corrected on 2026-11-04, before any outcome was tested: it first
   read pChEMBL ≥ 8, which is 10 nM, while the stated intent was 100 nM.
7. **Early human pharmacology** (Phase 2 and 3 entries). Target engagement
   measured in people before entry (pilot).

Kept apart from the efficacy categories:

- **Safety risk.** Loss-of-function intolerance, mouse knockout lethal,
  essential in most cell lines (hindsight only). Tested against safety stops.
- **Clinical precedent** (benchmark, outside every Holm family). An approved
  drug on the target for a related disease (B1); for an unrelated disease only;
  an earlier Phase 2/3 trial of another drug on the target in a related disease
  (Lin ≥ 0.5) that missed its primary endpoint or stopped for futility, ending
  within 3 years before entry. The last is scored for 2011–2019 entries only:
  trial-level results are sparse before 2008, and a lookback reaching before
  them makes the line rise with entry year.

**New confirmatory hypotheses (Holm-corrected together, α = 0.05).**

- **N1.** Among small molecules measured on the primary target and an off
  target, selectivity of at least 10-fold raises S4.
- **N2.** Among small molecules, at most one Rule-of-5 violation raises S4;
  among neurology and psychiatry programs, the brain-penetrance properties
  raise S4.
- **N3.** Outside oncology, the molecule category (any of potency, selectivity,
  drug-likeness) raises S4 with human genetics held fixed.

Category-level estimates for categories 1–6 are reported on this cohort with
their intervals and are not tested. A category or subcategory with fewer than
15 distinct exposed targets or 100 exposed entries is described, not estimated.

**Pilot gates.** The literature lines (drug in an animal model of the disease,
drug in healthy animals, human target engagement) run first on 300 seeded
entries: PubMed abstracts searched by every registered name of the drug and the
disease's synonyms and subtypes, each hit screened by an LLM. Agents with web
access, blind to those results, list every qualifying study for 100 of the
entries. A line enters the analysis only if retrieval recall against that list
is at least 80%, a second model agrees with the screen at κ ≥ 0.6, and at least
8% of Phase 2 entries carry it; otherwise it is reported as descriptive.
Full-text search is not used: none of about 25 full-text-only hits checked was
a study of the drug in the disease.
