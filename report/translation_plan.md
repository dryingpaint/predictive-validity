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

**Category roll-up, corrected 2026-11-04.** The plan does not say how a
category is formed from its subcategories. The first build counted an entry as
having a category when any subcategory was present and as lacking it otherwise.
That treated "not known" as "absent", against the subcategories' own null
definitions, and it let a subcategory scored on only part of a category's
entries define the category there. It was corrected before the category
results were published, after the first estimates had been seen, because the
molecule category (2.74×) exceeded every one of its subcategories (0.86–1.59×):
582 of the 1,283 small-molecule entries counted as lacking it had no known
structure and no measurement at all. The corrected rule:
- A category is formed only from subcategories scored on all of its entries.
  Brain-penetrant properties (neurology and psychiatry only) and the earlier
  failed trial (2011–2019 entries only) are reported alone.
- The molecule category covers small molecules with known computed properties.
- An entry on which none of a category's subcategories is known is null,
  not 0.

The other five categories are unchanged entry for entry. The corrected precedent
category, an approved drug on the target for any disease, is the same variable
as the target-precedent covariate of the Phase 2 model, so the precedent lines
are no longer adjusted for it. Before this, they had been adjusted for
themselves.

**Display areas, added 2026-11-05 (exploratory).** After the category results had been seen, the
evidence chart was regrouped for readability into areas that each answer one question, with mutually
exclusive groups of programs inside each: human genetics (rare variants only, common only, both),
curated pathways (a disease mutation shown disrupting the target's pathway), tumour genetics
(mutation matches the drug, or not), diseased tissue (RNA level changed), mouse models (close symptom
match, looser), the drug
(strong and selective, strong only, weaker), target safety risk (constraint only, knockout lethality
only, both) and earlier drugs on the target (approved for a related disease, for unrelated diseases
only, a failure with no approval). Because the grouping was chosen knowing the results, its estimates
are exploratory. Cancer-cell dependency is left off the chart, its interval too wide to read. The categories above remain the registered analysis, the appendix table reports
them, and N1-N3 are unchanged.

**New confirmatory hypotheses (Holm-corrected together, α = 0.05).**

- **N1.** Among small molecules measured on the primary target and an off
  target, selectivity of at least 10-fold raises S4.
- **N2.** Among small molecules, at most one Rule-of-5 violation raises S4;
  among neurology and psychiatry programs, the brain-penetrance properties
  raise S4.
- **N3.** Outside oncology, among small molecules, potency of 100 nM or better
  on the primary target raises S4 with human genetics and drug-likeness held
  fixed. Potency's unadjusted effect is already reported; this tests whether it
  holds independently of genetics.

N3 was narrowed on 2026-11-04, before any outcome was tested. As first written
it tested the whole molecule category, but drug-likeness alone passes 84% of
small-molecule entries, so the category covered 79% of them and would have
measured drug-likeness rather than the drug's pharmacology. Drug-likeness keeps
its own test in N2.

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

**Second literature attempt, 2026-11-04.** The first version failed the gate on
retrieval (recall 22–25%), not screening (κ 0.59–0.95, and no study reported where
the reference found none); its results are in `report/audits/literature_gate.md`.
One second version is allowed, fixed here before it runs:

- Retrieval by the drug's names alone, with no disease, species or kind terms.
  The names are the INN, code names, FDA substance-registry names, and PubChem
  and ChEMBL synonyms. Searches cover publications up to the year before entry,
  excluding reviews, and keep up to 200 results per drug in PubMed relevance
  order. The LLM screen decides the kind, and for animal models which disease
  is modelled. A screened model counts for an entry when its disease is the
  entry's disease or within Lin ≥ 0.5 of it.
- It is scored only against a fresh blind reference set: entries 101–200 of
  `report/audits/literature_pilot_sample.csv`, researched by new agents under
  the same instructions, with no access to either version's results. The gates
  are unchanged. A line that fails stays descriptive, and no third version is
  run.

**Comprehensiveness amendment, 2026-11-04.** The user asked for every new line to be as
comprehensive as public data allows. Two changes are fixed here before any data for them is
pulled or any outcome is looked at.

- **Literature lines, third attempt (user-directed).** This overrides the stop rule above, which
  allowed no third version. Any line that passes is labelled in the report as passing on a
  third, user-directed attempt, not as a clean confirmation. Retrieval is by every name of the
  drug, as in version 2, but with no cap on abstracts per drug. It also adds abstracts outside
  MEDLINE (preprints and conference abstracts indexed by Europe PMC) up to the year before
  entry. The screen and the disease matching are as in version 2. The attempt is scored only
  against a new blind reference set: entries 201–300 of
  `report/audits/literature_pilot_sample.csv`, researched under the same instructions by agents
  with no access to any version's results. The gates are unchanged. A line that fails stays
  descriptive, with no further attempt.
  Addendum, same day, before the pilot ran, at the user's direction: retrieval also uses Firecrawl's
  research index. That means semantic search over about 43M PubMed, bioRxiv and medRxiv abstracts, by the
  drug's names and by the drug with each kind of evidence, plus citation-graph expansion from hits
  already found, kept to publications up to the year before entry. Hits pass through the same screen.
  The pilot reports Firecrawl credits per entry; a full-cohort run waits for the user to approve its cost.
- **Cell studies before 2019 (oncology).** A new subcategory: the target is a dependency in
  cancer cell lines of the program's tumour type, in genome-wide RNAi or CRISPR screens
  published before entry. The sources are the DEMETER2 combined RNAi scores (Achilles,
  Project DRIVE, Marcotte breast screens) and the Avana CRISPR screens. Each screen's cell
  lines are dated by the year their source paper was published. A gene is a dependency in a
  tumour type when its score is −0.5 or lower in at least two screened cell lines of that type
  and in at least 20% of them. Cell-line lineages are matched to the program's disease within
  Lin ≥ 0.5, by the same MONDO neighbourhood as the other lines. Genes on DepMap's
  common-essential list of the same year are excluded, so the line marks selective dependency.
  The CRISPR line first published in 2019 (Project Score) stays a hindsight line.

**Cell studies scope, 2026-11-04.** Fixed before the dependency line was compared with any outcome. Cell-line
evidence for a disease exists only in oncology, and the earliest dependency screens were published in 2014, so
the Cell studies category and its dependency subcategory are scored on oncology entries from 2015 on. Both its
lines are known for every one of those entries, so the category means the same thing across its scope. The
dependency scores are DEMETER2 and CERES reprocessings (2018–19) of screens published 2014–2017: the screen data
existed before entry, but the exact scores were computed later.
**Name vetting, 2026-11-05, added after the third attempt's pilot gate.** The cohort search showed that the
synonyms taken from PubChem and ChEMBL included common words, generic class and protein names, and other drugs'
names (for spinosad "Success", "Justice" and "Tracer"; for elinzanetant "Compound A"; for colestipol "POLY" and
reserpine brand names; for albumin human "Bovine serum albumin"), so retrieval pulled in tens to hundreds of
thousands of unrelated records. An LLM now vets each drug's candidate names before searching, given its
nonproprietary and registry names, modality and targets, and keeps only names that unambiguously denote the drug;
a second model re-vets a seeded sample. Drugs whose vetted names differ are searched again. Records the screen
already read as reporting none of the three kinds stay out; records it read as qualifying, and new records, are
screened again under the vetted names. The gate is re-scored on rows 201–300 against the same blind reference
set with the same metrics, and both the pre- and post-vetting results are reported. A drug still returning more
than 100,000 records is held from the paid prefilter until approved. The reference set's files, lost from
temporary storage, were rebuilt from the reference agents' recorded steps; re-scoring the pre-vetting pipeline
against them reproduces the recorded gate (one healthy-animal reference study more: 149 against 148).

**Reporting the literature lines, 2026-11-05, after the full-cohort run and before its estimates were published.**
No kind passed the gate on the final retrieval (v3_final: recall 74%, 67% and 39%). At the user's direction the
three lines are reported as exploratory, not left out: the evidence chart draws them in their own marked areas
(published animal studies of the drug, with the disease-model and healthy-animal-only groups; a published study
of target engagement in people), the main text states the result with the recall caveat, and no conclusion of
the report rests on them. Drugs whose generic name is an endogenous molecule with no product-specific name
(alcohol, nitric oxide, ademetionine) were searched by product names and codes only, a vetting exception recorded
in report/audits/literature_name_vet.json.

**Safety lines, 2026-11-08, exploratory, fixed before any of the new lines was compared with an outcome.** The
standard genetic flags (loss-of-function intolerance, mouse knockout lethal before weaning) showed no association
with safety stops. Each measures complete, lifelong loss of the gene, which a drug's partial, adult inhibition does
not reproduce. Three lines are added, chosen after that result and so reported as exploratory, each tested against
stops for efficacy or exposure and stops for safety (traced causes, Phase 1-3 entries, adjusted as in the Models
section with phase added):

- **A vital-organ phenotype in mutant mice.** Any Open Targets mouse phenotype of the target in the Mammalian
  Phenotype classes cardiovascular (MP:0005385), liver and biliary (MP:0005370), haematopoietic (MP:0005397),
  immune (MP:0005387) or nervous system (MP:0003631). Undated, like knockout lethality.
- **An earlier safety stop on the target.** Another entity on one of the entry's primary targets, in any
  disease, stopped for safety (the traced cause, or the likely cause where no source states one), with its trials
  ended at least a year before entry. Scored on entries from 2011, since the traced stops begin with 2008 entries.
- **Poor selectivity.** A small molecule whose best off-target potency known the year before entry is within
  10-fold of its primary-target potency (the selectivity line's complement, where an off-target was measured).

The evidence chart shows the two standard flags as one line; each flag stays in the registered categories and
the appendix table.

**Stops by the model-system atlas's four questions, 2026-11-09, exploratory.** Each evidence area and safety line is
also tested against stops split the way the atlas splits its questions: dose (tolerability capped the dose, toxicity
offset the benefit, or a registered PK, dose or formulation reason), engagement (human evidence shows exposure or
engagement too low), efficacy (the target was engaged without benefit) and safety. A stop coded as another drug on the
target having worked where this one was not shown to engage counts as none of these: its code follows from the
target's record, so it would make target evidence predict engagement failure by construction (checked: with it,
genetic support went with 1.7× the engagement stops; without it, no clear difference). Published human engagement is
not tested against engagement stops, which were judged from the same publications.
After the literature result was seen (2026-11-09), the report added two exploratory splits of the animal-model
line at Phase 2: by the size of the sponsor's company (report.section3.sponsors) and by human genetic support. They
were chosen to test explanations of a result already known, so they are not confirmations.

## Amendment, 2026-11-09: target biology in the literature

Fixed before any data for these lines is retrieved and before any of them is compared with an outcome.

**Why.** The categories of the 2026-11-03 amendment follow the structured sources the report already used (Open
Targets, MGI and IMPC, DepMap, ChEMBL, PubChem), and literature was searched only for evidence about the drug. Evidence
about the target's biology in the disease that lives only in papers was never collected: perturbing the target in
human cells or tissue, perturbing it in animals by means other than genetics, finding it altered in patients'
tissue, and finding it tracks the disease in patients. Curated pathways count only a pathway with a disease mutation
in it, which is a genetic line. Without these lines the report cannot say whether the evidence most often used to
pick a novel target predicts anything.

**Unit.** A pair of a human gene and a disease: every gene of an entry's primary-target set with the entry's MONDO
disease. The cohort's entries with a target and a disease give 7,193 gene–disease pairs over 1,217 genes and 997
diseases (3,857 pairs at Phase 2). Each pair is searched up to the year before its latest entry; each entry counts
only records published no later than the year before its own entry. An entry is exposed to a kind when any gene of
its target set has a qualifying record for the entry's disease, a subtype of it, or a disease within Lin ≥ 0.8,
the same neighbourhood as G3.

**Kinds**, each about the target, not the program's drug, and each needing original data (no reviews):

1. **Perturbed in human cells or tissue.** The gene or its protein is knocked down, knocked out, overexpressed or
   acted on by any agent other than the program's drug, in primary or patient-derived human cells, organoids,
   iPSC-derived cells or ex vivo human tissue, and a phenotype of the disease changes. Established cell lines count
   as a separate subcategory (1b), since they are the commonest and weakest form.
2. **Perturbed in animals, other than by genetics.** A tool compound, antibody, antisense, RNAi or viral vector
   other than the program's drug acts on the target in an animal model of the disease and changes a disease
   phenotype. Germline knockouts and mutants are the mouse genetics line and are excluded here.
3. **Altered in patients' tissue.** The protein's level, activity, localisation or modification differs between
   patients' diseased tissue and control tissue, or single-cell data place the gene in a cell state that differs
   in the disease. Bulk RNA differences are the diseased-tissue line and are excluded here.
4. **Tracks the disease in patients.** In an observational study of patients, the target's level or activity
   (in tissue or circulation) goes with the disease's presence, severity, progression or outcome. Genetic
   association is excluded (human genetics).

Interventional studies in people are excluded: a drug on the target that worked in people is clinical precedent.

**Retrieval**, per pair, up to its cutoff year:
- PubMed titles and abstracts matching any vetted name of the gene or protein and any name of the disease, its
  synonyms and its subtypes, every hit kept;
- Europe PMC records outside MEDLINE, by the same query;
- Firecrawl's research index: one semantic search per pair and kind, and related-paper expansion from each record
  that qualifies.
Gene names are vetted as drug names were: an LLM keeps only HGNC symbols, aliases and protein names that
unambiguously denote the gene (aliases such as CAT, MET, SET or PC are dropped), and a second model re-vets a seeded
sample. Records already stored (public.publications, preclin.literature_record) are reused.

**Screen.** An LLM reads each record with the gene, the disease and the four kinds, and says whether it reports
original data and which kinds it shows for that gene in that disease (or a named related disease, mapped to MONDO
as the drug lines' disease models were). Pairs with more than 3,000 records pass a cheaper prefilter first, as in
literature version 3. A second model relabels a seeded check sample.

**Pilot gate.** 300 seeded pairs first. Agents with web access, blind to the pipeline's results, list every
qualifying study for pairs 1–100. A kind enters the analysis only if, against that list, retrieval recall is at
least 80%, the check agrees at κ ≥ 0.6, and at least 8% of Phase 2 entries carry it. A kind that fails may be
revised once, scored on a fresh blind reference set (pairs 101–200); if it fails again it is reported as
descriptive. There is no third attempt.

**Analysis**, for each kind that passes and for the category (any kind), as for the 2026-11-03 categories:
relative success to approval, the adjusted risk ratio of S4 at Phase 2, the risk ratio of an efficacy stop at
Phases 2–3, and the stop outcomes of the evidence grid. Lines that fail the gate are shown as exploratory, as the
drug literature lines are.

**Confirmatory hypotheses** (Holm-corrected together; each tested only if its kind passes the gate):
- **T1.** Perturbation in human cells or tissue (kind 1, primary and patient-derived systems) raises S4.
- **T2.** Non-genetic perturbation in an animal model of the disease (kind 2) raises S4.
- **T3.** Altered protein in patients' tissue (kind 3) raises S4.
- **T4.** Tracking the disease in patients (kind 4) raises S4.
Each is also estimated holding human genetics fixed, which says whether the literature adds to genetics.

**Storage.** New tables keyed by gene (Ensembl id) and MONDO disease, beside the drug-keyed literature tables:
`preclin.target_literature_search`, `_firecrawl`, `_hit`, `_prefilter` and `_screen`, then
`preclin.target_literature_evidence`, one row per gene, disease, kind and record with its publication year, shaped
like `preclin.ot_evidence` so the as-of and MONDO matching code applies unchanged. The lines join
`preclin.evidence_line` and `preclin.evidence_entry_line` through `report.evidence_lines store`. No existing table
changes.

**Cost.** Measured in the pilot, which reports tokens and Firecrawl credits per pair; the full run waits for
approval of its cost. As a scale: literature version 3 cost about $560 in model tokens over 4,620 drugs, and
Firecrawl about 0.21 credits per call (here about 30,000 searches plus expansions). A pair returning more than
100,000 records is held from the paid prefilter until approved.

**Not covered.** Evidence that is not public before entry (sponsors' internal data, how a target was found in a
phenotypic screen) cannot be scored. Structured sources without dates before entry (Human Protein Atlas pathology)
or that begin late (single-cell atlases, from about 2018) are not used for these kinds; they may be added later as
hindsight lines.
