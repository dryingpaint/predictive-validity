# Report audit — claims, data, analysis

Audit of every claim in the draft report *Predictive Validity in Drug Development*
(Google Doc `1rpmxP0Mv33dyBusDHcA4wIkqqCthiOmSGtSEEj15G0U`, exported 2026-10-20)
against the live database and the code that produced each number.

Status values: `open` (not yet checked) · `confirmed` (reproduces, method sound) ·
`wrong` (does not reproduce or method invalid; corrected value given) ·
`revised` (number changed after a data or method fix) · `unsupported`
(no data or citation backs it) · `removed` (claim dropped from the report).

## Workspace

- Branch `audit/report-claims`, worktree `../predictive-validity-audit`.
- Base `origin/codex/pv-ingestion-publication` (PR #26), whose `db/` migrations
  1–52 match `preclin.schema_migration` in the live database. It contains
  `origin/main`, including the merged PRs #20–#24 (Nelson-tier exclusion,
  held-out-target ablation, consensus-target cohort).
- Merged `origin/section-1-failure-modes` (PR #7, Section 1) and
  `section-2-predictive-power` (PR #2 plus local fixes, Section 2).
- Database: Neon `ep-late-smoke-amionchh` (`preclin.*`, `public.*`, `pv_*`).
  The `ep-weathered-dust` database holds Capable lab data and none of this
  project's tables.

## Rebuild: definitions

These replace the legacy `preclin.program` / `program_outcome` / `approval`
layer for every number in the report.

- **Trials.** ClinicalTrials.gov snapshot of 2026-10-20 (`preclin.ctgov_study`): every
  interventional study with a drug, biological, genetic or combination-product
  intervention, any sponsor, any date. In scope: studies listing Early Phase 1, Phase 1,
  2 or 3. A Phase 1/2 trial counts as Phase 2 and Phase 2/3 as Phase 3 (the
  Biomedtracker convention BIO uses). Withdrawn trials never enrolled and are left out
  of phase entry.
- **Molecular entity.** Each intervention name is resolved by an LLM (with the trials it
  appears in) to its active entities under nonproprietary names; doses, salts, brands and
  sponsor codes collapse to one entity, placebo and non-drug interventions drop out
  (`preclin.moiety`, `preclin.drug_moiety`). Names identical to a known entity name,
  code or alias are linked directly. Each entity is then resolved to its FDA UNII
  substance (GSRS 2026-08-04 names, including sponsor codes and brands); entities that
  are the same substance are merged under its official name, the other names kept as
  aliases (`moiety.unii`, `moiety.aliases`).
- **Role in a trial.** An entity counts toward a program only in trials where it is
  investigational (`preclin.ctgov_study_moiety`): comparators and background therapy do
  not. Single-entity trials are decided from arm types; industry trials with several
  entities by an LLM reading the arms.
- **Disease.** Each condition string maps to the MONDO term for its core disease, without
  line, stage, biomarker or age qualifiers (`preclin.indication.mondo_id`; pinned MONDO
  2026-10-06). A disease MONDO does not name gets its nearest containing term
  (`mondo_match = 'broader'`).
- **Program.** One row per (entity, development indication) (`preclin.dev_program`). A trial whose
  condition is broader than another of the entity's diseases (e.g. "solid tumors") rolls
  into the more specific programs; healthy-volunteer trials roll into every program of the
  entity. Such a shared trial marks phase entry only for programs already under way when it
  started and for the program(s) begun next (the lead indication then); an indication added
  later enters at its own first trial (`dev_program_trial.marks_entry`; attach-all is a
  sensitivity). The disease of a program is a development indication: an LLM groups each
  entity's MONDO diseases into the indications a sponsor runs as programs
  (`preclin.program_indication`). Trials whose conditions are only symptoms or procedures without a MONDO term
  (pain, contraception) form the entity's condition-unspecified program instead. Each industry
  trial's purpose is classified by an LLM (`preclin.trial_purpose`): product-support trials
  (bioequivalence, formulation bridging, food effect, interactions, generic or biosimilar PK)
  belong to no program; a multi-indication basket attaches to the programs of the diseases it
  lists (else to the unspecified program), and early-development trials are shared like
  healthy-volunteer trials. Sponsors are attributes, not part of the key.
- **Approval.** FDA approval for the program's disease and its first date, judged by an
  LLM from the entity's 2015–2026 approval letters (5,034 extracted approved uses; pages
  without a text layer OCRed; labeling-only changes are not approval events), its
  original-approval dates and current label indications (`preclin.dev_program_approval`).
  Approvals before 2015 are taken from the label and placed at the entity's first FDA
  approval, the earliest date they could have happened.
- **Phase cohorts and outcomes.** For phase p, programs whose first industry-sponsored
  phase-p trial started 2015–2025 (shared trials count only for Phase 1 of the lead
  indication), had not already entered a later phase, and were not already approved for the
  disease (lifecycle programs are excluded). Advanced = a later-phase trial of the program's
  own disease started (any sponsor: a cooperative-group trial of a company's drug is
  development; a trial registered but not yet recruiting does not count), or FDA approval
  for the disease. Suspended = none of the program's own trials, nor the trial that marked
  its Phase 1 entry, active or active within 24 months of the snapshot. Otherwise censored.
  A phase skipped on the way to a later phase or to approval counts as a success in it (as
  in BIO). BIO-style rate = advanced / (advanced + suspended); a competing-risks
  (Aalen–Johansen) estimate keeps censored programs. LOA = product of phase rates.
  Confidence intervals resample molecular entities (1,000 draws); no LOA for a cohort with
  fewer than 10 entities resolved in a phase. US-developed = a US-sited industry trial
  among those marking entry to the phase. Sensitivity: lag 12/18/36 months, novel vs
  already-approved entities, uncertain approvals, shared-trial entry, vaccines, 2015–2019
  entrants.
- **Why programs stop.** Each industry trial since 2010 that stopped early, or completed
  Phase 2/3 with posted results or a results paper, is classified (`preclin.trial_outcome`)
  on separate axes: execution, stated stop reason (with "sponsor decision, unspecified"
  kept apart from explicit business reasons), primary-endpoint result (from posted results,
  else from the abstracts of PubMed papers linked to the NCT id), and safety signal. A
  suspended program's reason comes from its own industry trials of the phase it stopped in
  (in Phase 1 also the trial that marked its entry); posted results without a readable
  endpoint and other stated reasons are kept apart from "no reason, no result".

## Claim register

| ID | Report section | Claim | Status | Verified value / note |
|---|---|---|---|---|
| C01 | Intro | Drugs per $bn R&D halved ~every 9 years since 1950 (Scannell 2012) | revised | Verbatim in Scannell 2012 (halved ~9y, ~80×, 1950–2010). The four causes come from the 2012 paper, not Scannell & Bosley 2016; trend flattened after 2010 (Ringel 2020). |
| C02 | Intro | 7.9% of Phase 1 entrants reach FDA approval (BIO 2021) | revised | BIO 7.9% is an all-program LOA incl. non-NME and biosimilars; the like-for-like novel-drug LOA is 6.8% (NME 5.7%, biologic 9.1%). |
| C03 | Intro | "The 92% of programs that fail" | revised | 92% = 1 − LOA; 'hundreds of billions' uncited. |
| C04 | Intro | Genetic support 2.6× Ph1→approval (Minikel 2024), 2× (Nelson 2015) | revised | Minikel 2.6× is Ph1→launch (any market, Pharmaprojects), not FDA approval; Nelson ~2×. |
| C05 | Intro | Efficacy ~52% and safety ~24% of Ph2/Ph3 failures (Harrison 2016) | confirmed | 52%/24% of 174 Ph2/Ph3 failures with a disclosed reason (Harrison 2016). |
| C06 | Intro | AZ 5R programs far more likely to succeed (Cook 2014) | wrong | Cook 2014 derived the 5Rs; the improvement after adoption (4%→19%) is Morgan 2018. |
| C07 | Intro | Scannell coined Eroom's Law; Scannell & Bosley 2016 introduced predictive validity; "landmark study names four reasons" | revised | Eroom's Law coined by the four 2012 authors; 'predictive validity' predates Scannell (Willner 1984); S&B 2016 present it as a hypothesis. |
| C08 | History | Seven-era history table | revised | Dates fine; lead-in says '50 years' for a table starting pre-1900; sulfonamides were a phenotypic discovery. |
| C09 | Intro | 28,193 industry trials "started after 2015 and ended before 2026" | wrong | Cohort = 28,0xx closed industry trials started 2015-01-01..2025-12-31 (3,065 started in 2015); no 'ended before 2026' filter exists. |
| C10 | Intro | Six core lines of evidence compiled from databases and literature classification | revised | The literature-classified lines (B–E) used scores later found to rest on hallucinated PMIDs (v1) or post-outcome citations (v2); only the database lines are usable as stated. |
| C11 | S1 | 7.4% of Ph1 programs reached FDA approval, within 0.5pt of BIO | wrong | 7.4% ≈ BIO only through offsetting errors (1,908 approval-seeded phantom programs, drug-level labels, comparators). LLM-corrected sample estimate 10.0% [5.4, 15.8]. Rebuild pending. |
| C12 | S1 | Only 1 in 20 failed programs records an efficacy or safety reason | revised | 4.5–7% depending on cohort; qualitative claim holds. |
| C13 | S1 | 28,193 trials = 67% of 41,836 industry Ph1–3 drug trials started 2015–2025 | wrong | 41,836 includes EARLY_PHASE1 and non-drug trials (in-definition: 40,218 on CT.gov 2026-10-20); the 33% gap is closed vs active status, not failed resolution. |
| C14 | S1 | 84,117 programs; 13,639 T-I pairs with ≥1 Ph1 trial | wrong | Program rows include 7,425 duplicates (NULL sponsor_id), placebo/comparator/background arms and healthy-volunteer pseudo-indications; 13,639 T-I pairs is the leaked-era cohort. |
| C15 | S1 | Transitions 55.9 / 51.0 / 26.1 / 7.4% vs BIO 52.0 / 28.9 / ~52 / 7.9% | wrong | Transitions depend on label convention (3.2–16.1% LOA); corrected sample Ph3→approval ≈42% [24, 62]. |
| C16 | S1 | Mid-phase gap explained by Ph3b, non-US, Ph2/3 designs | wrong | The mid-phase gap comes from mislabelled non-development programs and combined phases coded as phase 0, not Ph3b designs. |
| C17 | S1 | 42,984 Ph1+ programs settled by 2026, vaccines and mRNA excluded | wrong | Not reproducible from committed code after out-of-ledger relabel (db/11); includes phantoms and duplicates. |
| C18 | S1 | 55,133 failed programs; silent efficacy = 73% of Ph3 failures | wrong | Failure set (55,133) is not nested in the LOA cohort: 30.6% placebo/methodology/vaccine/non-drug; 'silent efficacy' bucket is mostly approved drugs and placebo arms. |
| C19 | S1 | 5,510 early terminations with a reason; 44% commercial/strategic; Cook 2014 says this masks efficacy failures | revised | 5,510 confirmed (21% withdrawn before enrolment). 44% commercial is mostly boilerplate 'sponsor decision'; Cook 2014 attribution unsupported. |
| C20 | S1 | Figure 1: failure reasons by phase | wrong | Arithmetic reproduces; bars inherit C18 cohort errors. |
| C21 | S1 | Ph1 failures mostly non-advancement after safety/PK; Ph3 failures mostly completed trials without approval | wrong | Ph1 stalls include healthy-volunteer/PK studies and approved drugs; commercial-prioritization inference untested. |
| C22 | S1 | LOA varies ~10× by area: 18.4% hematology → 1.6% urology | wrong | Spread survives but levels driven by phantom approvals; Urology rests on 5 approvals; taxonomy departs from BIO (renal/OB-GYN, heme malignancies). |
| C23 | S1 | Oligonucleotides 32.5%, small molecules 5.8%; same rank order as BIO | wrong | Oligo 32.5% is pre-vaccine-exclusion and drug-level; BIO's rank order differs (antisense below small molecules). |
| C24 | S1 | Modality rates above BIO because of ASO/GLP-1/AAV approvals; infectious/Other lower for missing vaccines/biosimilars | wrong | Gaps driven by drug-level crediting and phantom programs, not the approval window. |
| C25 | S1 | Figure 2: LOA by area and modality vs BIO | wrong | Figure mixes two cohort vintages (pre/post vaccine exclusion); no CIs. |
| C26 | S2 | Genetics is the only line that adds predictive power once the others are known | wrong | Rests on leaked ablation; corrected ablations show no category with a robust increment. |
| C27 | S2 | Strong genetic support 45% approval vs 11% for none | wrong | 'None' bin is 233/266 pathogen/pseudogene targets; outcome drug-level; Strong vs Weak adjusted RR ≈1.6. |
| C28 | S2 | 8,144 Ph2+ T-I pairs, base approval rate 23% | wrong | 23% is a drug-level any-indication rate; strict per-indication 5.2–9.9%. |
| C29 | S2 | Figure 3: relative success per evidence dimension | wrong | Literature bars from invalidated v1 scores; Reactome bar pre-dates gap fill; no CIs; ~34% wrong drug→target links. |
| C30 | S2 | Pathway/GO counts are study-depth proxies | revised | Reactome ≥5 not a study-depth proxy here and null under strict outcome. |
| C31 | S2 | Genetic dose–response table (8,392 pairs) | revised | Reproduces on loose outcome; target-clustered CIs 3–8× wider; step at Strong only. |
| C32 | S2 | Ablation: genetics −17.7pp; cell/animal 0.0; mechanistic −0.6; PD −0.3; safety −0.2 | wrong | −17.7pp came from Nelson one-hots inside 'genetics' (leaked) with random-split CV. |
| C33 | S2 | AUC 0.825 on held-out targets, 13,639 Ph1+ pairs | wrong | 0.825 is the leaked run; corrected 0.570 [0.515, 0.620]; 75% of positives are trial-less phantom pairs. |
| C34 | S2 | Time-split AUC 0.769 (train pre-2019) on Ph2+ pairs | wrong | 0.769 leaked; corrected time split ≈0.51 (24 test positives). |
| C35 | S2 | DepMap pan-essential targets RS 0.24 | revised | Arithmetic reproduces; driven by old cytotoxics; adjusted ≈0.4, n.s. under strict outcome (41 targets). |
| C36 | S2 | gnomAD LoF-intolerant genes RS 0.82–0.84 | wrong | Not distinguishable from 1 under clustering; null after adjustment. |
| C37 | Cases | 1,182 Ph3 T-I pairs; strong single-line evidence still fails 73–85% | wrong | 1,182 were programs not T-I pairs; generating script missing; 73–85% fail ≈ base Ph3 failure rate. |
| C38 | Cases | Ph3 strong-evidence table (8 rows) | wrong | Rows mix runs; literature rows used hallucinated-PMID v1 scores. |
| C39 | Cases | Best profile (C∧D∧E∧genetics) approves 22% of 422 Ph3 pairs | wrong | Convergent rows include Phase 2 programs; no comparator. |
| C40 | Cases | BACE1 inhibitors (CSF Aβ42 −50–80%, cognition worsened, ~$4bn) | revised | CSF Aβ −50–90%; worsening in some trials, reversible; '$4bn' unsupported; amyloid-causal claim contradicted by lecanemab/donanemab. |
| C41 | Cases | Torcetrapib/CETP (HDL +60%, mortality +25%, aldosterone; successors failed) | wrong | Torcetrapib deaths +58% (HR 1.58), MACE +25%; anacetrapib met its endpoint (RR 0.91). |
| C42 | Cases | Semagacestat (faster decline, Notch → skin cancer, GI) | revised | Functional (not cognitive) worsening significant; Phase 2 CSF Aβ not reduced. |
| C43 | Cases | Solanezumab/bapineuzumab (no benefit; mouse models overpredicted) | revised | Solanezumab did not clear plaque; bapineuzumab ARIA-capped; failure better explained by insufficient engagement. |
| C44 | Cases | TGN1412 (500× monkey margin; 6/6 cytokine storm) | confirmed | Facts correct; framing overstated (in vitro human assays/MABEL would have flagged it). |
| C45 | Cases | Fialuridine (clean 4-species tox; 5/15 deaths; human-specific transporter) | confirmed | 7/15 severe hepatotoxicity, 5 deaths, 2 transplants; mitochondrial hENT1. |
| C46 | Appendix | why_stopped category counts (11 categories, n=5,510) | revised | Counts reproduce; 360 Sonnet API failures stored as 'unclear'; κ(Haiku,Sonnet)=0.81 on valid pairs. |
| C47 | Appendix | Sonnet and Haiku classified every trial; Sonnet kept on disagreement | revised | 480 failed calls; Sonnet preferred unconditionally; prompts not committed. |
| C48 | Appendix | Silent efficacy = efficacy or safety ~90% of the time | unsupported | No source for ~90%; literature gives 69–87% among disclosed failures, not 'Ph3 completed, no approval'. |
| C49 | Appendix | 18-month rule matches BIO's advanced-or-suspended denominator | wrong | BIO counts dated Biomedtracker transitions (advanced/suspended, curated); no inactivity rule. LOA moves 14.5→19.2% (current labels) as the lag goes 6→36 months; use competing-risks censoring instead. |
| C50 | Appendix | Limitations list (modality known for 18%; approvals exclude vaccines, mRNA, biosimilars; features not time-frozen except precedent) | wrong | 18% modality figure is stale/other source; limitations omit supplemental and pre-2015 approvals. |

## Report claims after the rebuild

The rebuilt report (`REPORT.md`, rendered from `report/output/`) replaces the draft's numbers.
Each quantitative claim, with the value the rebuild gives:

| Claim | Draft | Rebuilt |
|---|---|---|
| C02, C11 Phase 1 → FDA approval | 7.4%, "within 0.5pt of BIO's 7.9%" | 10.4% (9.2–11.8) for US-developed programs; 7.3% (6.5–8.2) for all registered industry programs; 5.3–12.4% across defensible definitions (sensitivity table) |
| C09, C13 Trials analysed | 28,193 industry trials "started after 2015 and ended before 2026" (67% of 41,836) | 39,348 industry Phase 1–3 trials started 2015–2025 (not withdrawn); every in-scope trial is used, none dropped for failing to resolve |
| C14 Programs | 84,117 programs; 13,639 T-I pairs | 53,948 (entity, indication) programs from all trials; 16,562 entered a phase in 2015–2025 (a trial counts once it has started) |
| C15 Transitions | 55.9 / 51.0 / 26.1% | US-developed 56.5 / 34.7 / 53.2%; all programs 56.2 / 34.4 / 37.9% (BIO 52.0 / 28.9 / 52.4%), skipped phases credited as in BIO |
| C16 Mid-phase gap | Ph3b, non-US and Ph2/3 designs | The gap came from labelling errors; with the rebuild Phase 2→3 is 34.4% (BIO 28.9%), and the remaining Phase 3 gap is approvals outside the US (53.2% for US-developed programs vs 37.9% for all) |
| C18, C20, C21 Why programs fail | 55,133 failed programs; "silent efficacy" 73% of Ph3 failures | 6,604 suspended programs: no reason and no result 64% (Ph1), 31% (Ph2), 31% (Ph3); efficacy 26% (Ph2), 30% (Ph3); positive Phase 3 readout without US approval 19% of Ph3 stops |
| C19 Early terminations | 5,510 with a reason; 44% commercial/strategic | 5,557 with a reason: explicit business/portfolio/competitive 36%, bare "sponsor decision" 19%, efficacy 14%, enrollment/operational 14%, safety 4% |
| C22 Disease areas | 18.4% hematology to 1.6% urology | All programs: hematology 19.6%, metabolic 17.8%, oncology 17.8% down to urology 1.3%; US-developed: endocrine 27.4%, metabolic 25.8%, oncology 21.2%, hematology 18.5% down to infectious disease 5.9%. The ordering does not follow BIO's (rank correlation 0.26 all programs, −0.26 US-developed) |
| C23, C24 Modalities | Oligonucleotides 32.5%, small molecules 5.8% | All programs: multispecifics 22.7%, ADCs 21.0%, mAbs 14.1% … proteins 4.5%; siRNA and CAR-T not estimable (fewer than 10 entities resolved in Phase 3; most approvals came from Phase 2); vaccines not estimable from registry data |
| C26, C32 What genetics adds | Only genetics adds; ablation −17.7pp | Joint model: GWAS and rare-variant evidence keep independent effects at Phase 2, rare-variant at Phase 3, GWAS a small one at Phase 1; removing human genetics (both parts) lowers held-out AUC by 0.028 (0.002–0.053) |
| C27, C28 Genetic support | 45% vs 11%; 8,144 pairs, base rate 23% | LOA 30.8% with vs 11.0% without (relative success 2.80, 2.16–3.61) on 9,993 human-protein programs |
| C31 Dose–response | 10.9 / 19.7 / 23.0 / 45.0% | LOA 11.0 / 21.4 / 36.0 / 37.8% (none, then tertiles of the Open Targets genetic score at phase entry) |
| C33, C34 Model AUC | 0.825 held-out targets; 0.769 time split | 0.665 (0.602–0.723) on held-out target sets with all evidence vs 0.611 without; time split 0.655 vs 0.617 |
| C35 Pan-essential | RS 0.24 | 0.40 (0.17–0.73); penalised at Phase 2 in the joint model (Phase 1: 0.79, 0.62–1.01) |
| C36 LoF-intolerant | RS 0.82–0.84 | 1.01 (0.71–1.48): no detectable penalty |
| C37–C39 Phase 3 with strong evidence | 73–85% still fail; best profile 22% | Phase 3 programs with human genetic evidence were approved 64% of the time (n=195) vs 43% without |

## Data issues register

| ID | Issue | Effect | Status |
|---|---|---|---|
| D01 | `program_outcome.outcome_broad='approved'` is drug-level: any program whose drug is in the 544-row novel-approval table counts as approved, whatever its indication. `approved_elsewhere` is likewise drug-level (ChEMBL max_phase=4). | Every LOA, transition rate and RS in Section 1; the base rate in Section 2 | confirmed; replaced by indication-level FDA events (pipeline.fda) and the program rebuild |
| D02 | Two conflicting LOA definitions in circulation: committed `bio_replication.py` (approved only → 7.4%) and local working copy (approved + approved_elsewhere → 16.1%) | C11, C15 | confirmed; both superseded by the rebuild |
| D03 | `preclin.approval` holds 544 novel FDA approvals 2015–2025 with one indication each; supplemental indications, pre-2015 approvals and biosimilars are absent | Strict per-T-I outcome; C11–C25, C27–C39 | confirmed; fixed: 3,410 letters → 4,281 dated approved uses (2015–2025) + labels |
| D04 | Report cites the leaked Nelson-tier model (AUC 0.825, genetics −17.7pp); `origin/main` RESULTS.md has the corrected AUC 0.570 and genetics −1.9pp | C26, C32–C34 | confirmed; leaked numbers removed from the report |
| D06 | Drug entity resolution: 79% of 31,405 `preclin.drug` rows are `unresolved` strings; one molecule appears as many drugs (pembrolizumab: `keytruda`, `pembrolizumab 200 mg`, `Pembrolizumab Dose A`, `Pembrolizumab (MK-3475)`, `Keytruda-EU`, …) and placebo arms appear as drugs (`Tirzepatide-Placebo`). Programs are keyed on these strings. | Program counts, LOA denominators, drug-level labels | fixing (pipeline.drugs → preclin.moiety) |
| D07 | `preclin.indication.mondo_id`/`efo_id` empty for all 8,875 indications; `canonical_disease` (90% filled) has case/synonym duplicates | Disease-level units, approval matching | fixing (pipeline.indications) |
| D08 | 6,687 drugs flagged `is_globally_approved` with no ChEMBL ID (approval status from earlier LLM name classification) drive 14,669 `approved_elsewhere` programs | Outcome labels | confirmed (Haiku name-only guesses); superseded by moiety-level FDA linkage |
| D09 | 1,908 approval-seeded 'phantom' programs with no trials (n_trials=0, highest_phase=4), ~1,500 of them duplicates because a NULL `sponsor_id` defeats the unique key on every ingest run; they enter every cohort as successes | LOA (+~5pp), area/modality LOA, 75% of model positives | fixing: programs rebuilt from trials only |
| D10 | Every intervention on a trial becomes a program: comparators, background chemo, premedication, placebo-coded strings | Failure counts, LOA denominators | fixing: per-trial investigational role (arm types + LLM) |
| D11 | Combined-phase trials (Ph1/2, Ph2/3) stored as phase 0 / lower phase | Transitions | fixing: phases array from snapshot |
| D12 | Program roster holds only trials closed by the CSV snapshot; `n_active = 0` everywhere, `public.trials` status from 2026-04-06 | Right-censoring | fixed: CT.gov snapshot 2026-10-20 (222,915 studies) |
| D13 | ~34% of drug→target links wrong (`therapy_targets_public` alias collisions: PD-1 mAbs→GM2A, atezolizumab→MAT1A, semaglutide→ALPL) | Every Section 2 number | superseded by the rebuild: targets come from `pipeline.targets resolve` (`preclin.moiety_target`); no code reads the legacy drug→target links |
| D14 | Genetic and other evidence is target-level (any disease), not matched to the indication; indication ontology IDs empty | Section 2 interpretation | fixing: MONDO mapping + ontology-based matching |
| D15 | Literature lines B–E: v1 from hallucinated PMIDs; v2 mostly cites papers after first trial, overlaps the drugs' own programs | Figure 3, Ph3 table, model | superseded: the rebuilt report has no literature lines and no code reads the legacy scores; their leakage is measured in D66 |
| D16 | 360 Sonnet + 120 Haiku why_stopped calls failed and were stored as 'unclear'; Sonnet preferred even when it errored; prompts not committed | C46, C47, failure figure | superseded: stop reasons come from `pipeline.outcomes classify`; the legacy why_stopped labels serve only as a comparison in `report.quality`, which excludes failed calls |
| D17 | Owner DB password hard-coded in 4 scripts on the public GitHub repo (origin/section-1-failure-modes) | Security | removed from code on this branch; rotation needed (owner decision) |
| D18 | Methodology filter misses indication 'Healthy' (4,101 programs); modality from Haiku name guesses for 85% of drugs; placeholder `public.therapies` rows type biologics as small molecules; two modality columns disagree for 2,551 drugs | Section 1 strata | fixing: moiety modality + per-trial methodology |
| D19 | Figure 2 / BIO_REPLICATION.md mix pre- and post-vaccine-exclusion cohorts; leaked benchmark runs stored under canonical scorer names (runs 187–192) | Reproducibility | superseded: BIO_REPLICATION.md and the legacy benchmark runs were removed in #28; the Section 1 figures are rebuilt from one cohort |
| D20 | Development codes left unresolved when an INN exists (label audit: 5 of 100 names, e.g. E7046 = palupiprant, IO102-IO103 = imsapepimut + etimupepimut). A molecule run in Phase 1 under its code and later under its INN splits into two entities, and the code entity looks like a Phase 1 failure. | Program counts, transition rates, LOA | fixing: entities resolved to FDA UNII substances (1.05M registered names incl. codes) and merged when they are the same substance (pipeline.drugs unii) |
| D21 | 2,238 of 34,092 disease conditions (6.6%) had no MONDO term because none named them exactly (label audit: all 6 errors in 100); trials with only such conditions lose their disease | Programs, disease matching | fixing: nearest containing MONDO term, flagged `indication.mondo_match = 'broader'` |
| D22 | 147 of 3,669 FDA letters have pages with no text layer (scanned letterheads), so the indication paragraph of e.g. Asparlas and Imjudo original approvals was missing | Approved uses, approval dates | fixed: pages without text are OCRed (pdftoppm + tesseract); 147 letters re-extracted, 4,639 approved uses |
| D23 | Labeling-only supplements were extracted as `efficacy_labeling` uses (label audit: 5 of 60 letters); dated as approval events they could move a disease's first approval to a later labeling update | Approval dates | fixed: excluded from approval events |
| D24 | 7,497 completed industry Phase 2/3 trials (start ≥ 2010) posted no results, so their primary-endpoint outcome was unknown | Failure modes (efficacy failures among completed trials) | fixed where possible: 2,284 have a linked results paper (registry reference or PubMed secondary id); classified from abstracts by a separate task. The rest stay "no results" (published results skew positive, so the paper-based rate is not the rate for unpublished trials) |
| D25 | `benchmark/` (scorer framework, RESULTS.md) still takes ground truth from the legacy views (`preclin.v_target_indication_strict_outcome` over `preclin.program`/`preclin.approval`), so its cohort and AUCs disagree with the report's Section 2 | Second source of truth for predictiveness | fixed: `benchmark/`, RESULTS.md and the analyses built on them deleted; the report's Section 2 is the only predictiveness analysis |
| D26 | Shared trials (healthy-volunteer Phase 1, "solid tumors" baskets) counted as Phase 1 entry for every later indication of the entity, so each indication expansion started at Phase 2 scored as a Phase 1 success | Phase 1→2 rate, LOA | fixed: shared trials mark entry only for programs under way or begun next (lead indication); attach-all reported as a sensitivity |
| D27 | 845 stopped or withdrawn industry trials have an empty whyStopped; some give the reason only in the brief summary, which the outcome classifier did not see (trial-outcome audit: 1 of 30 stop reasons) | Failure-reason shares ("no reason stated") | fixed: brief summary stored and shown to the classifier when whyStopped is empty |
| D28 | Trials whose only conditions are symptoms or procedures without a MONDO term (pain, cough, contraception; 1,337 industry trials 2015–2025, 3.4%) were treated like healthy-volunteer trials and attached to every disease program of the entity, so a Phase 3 in low back pain could count as advancement of the same drug's osteoarthritis program | Phase transitions | fixed: they form the entity's condition-unspecified program; symptoms with a MONDO term form their own programs. Limitation: pain and similar indications are not separate programs or disease-area strata |
| D29 | Registry-derived Phase 1 cohorts included trials that are not development programs: bioequivalence, formulation, food-effect and interaction studies of marketed drugs (Phase 1 programs of already-approved entities advanced 8% of the time), and oncology dose escalations that list many tumor types, each counted as its own Phase 1 program (entry trials listing 5+ diseases advanced 10% of the time). BIO's unit is a disclosed Biomedtracker program, and generics are excluded | Phase 1 rate, LOA | fixing: LLM trial-purpose classification of all 75,774 in-scope industry trials; product-support trials leave the programs, baskets are shared |
| D30 | Shared trials (healthy-volunteer studies, "solid tumors" baskets) kept every program of a multi-indication entity "active", so programs never read as suspended (616 of 916 Phase 3 entrants of 2017 still censored in 2026) | Suspension, all transition rates | fixed: whether a disease is still in development is read from the program's own trials |
| D31 | Advancement counted only industry-sponsored later-phase trials; investigator and cooperative-group trials of a company's drug in the same disease were ignored (Phase 1→2 22.6% vs 34.6% when counted) | Transition rates | fixed: advancement and activity from the program's own trials of any sponsor |
| D32 | Approval judge: 8 of 25 dated first approvals were the original approval of a later application (505(b)(2), reformulation) for a use an older application already had before 2015, and 6 of 15 'uncertain' calls were clear yes (old drugs whose labels were not among the five shown). A wrong post-2015 date turns a lifecycle program into an approval | Phase 3→approval, LOA | fixing: prompt v2 with up to 12 labels ordered by application age and dated, the repeat-use rule, and knowledge of pre-2015 labelling (flagged in evidence); re-audit after rerun |
| D33 | Vaccine co-administration trials labelled the licensed vaccine given alongside as investigational, creating programs such as (influenza vaccine, RSV infection) and (HPV vaccine, dengue) | Vaccine and infectious-disease strata | fixed: trial-role prompt v2 makes a co-administered licensed product background; all 27,480 multi-entity trials re-decided |
| D34 | The same product under two entities where UNII does not connect them: salt and parent registered separately (aclidinium vs aclidinium bromide, so Tudorza's 2012 COPD approval never reached the program) and vaccine naming variants | Lifecycle exclusion, approvals, program counts | fixed: same-entity pass in `pipeline.drugs unii` (nearest-name candidates, LLM decides, merge only where every decision that saw the pair agrees) |
| D35 | FDA-side and trial-side names of vaccines, cell and gene therapies never met (Gardasil 9 split into nine antigens; trials name a "9-valent HPV vaccine"), so their approvals were invisible (vaccine Phase 3→approval 2.7%) | Vaccine, biologic strata | fixed: `fda link` matches each application with no trial-named entity to the trial entities that are the same product (750 applications, 78 links) |
| D36 | Programs keyed on single MONDO terms split one development indication into several programs (Pluvicto: castration-resistant, metastatic and adenocarcinoma of the prostate), and a Phase 3 listing the parent term (VISION: "Prostate Cancer") counted for none of them, or for all of them if broader trials were credited. LOA moved from 3.9% to 7.9% (all programs) between the two crediting rules | Every transition rate and LOA | fixed: an LLM groups each entity's diseases into development indications (`preclin.program_indication`); programs are keyed on the indication |
| D37 | Run-to-run nondeterminism. `programs build` attached broader-condition trials in hash-seed set order. Payload queries had no total order: approvals (events, labels, parent terms; 1,861 of 2,293 payloads hashed differently once ordered), UNII trial context (200–330 payloads changed on every run), MONDO candidate parents (10,103 of 43,390 mappings re-hashed after the ontology tables were reloaded), and `LIMIT` subsets of context trials (modality, targets, same-entity, product match). Unchanged inputs were re-asked on every run, and the report's row order followed program ids, which each build reassigns (failure-mode trial ties, cross-validation folds) | Reproducibility; repeated LLM spend | fixed: sorted iteration, total orderings (latest trials by start date, then NCT id), report rows ordered by (entity, disease, phase); Sections 1 and 2 are unchanged when input rows are shuffled |
| D38 | Role and purpose prompts joined entities and conditions with commas or semicolons. Names that contain commas ("diphtheria, tetanus and acellular pertussis vaccine", "Chronic Obstructive Pulmonary Disease, COPD") made the model split or merge them, failing the copied-exactly check: 367 trials had no purpose (defaulting to indication development; 87 would differ) and 14 had no roles | Programs, baskets | fixed: one item per line (roles prompt v3, purposes v2). All 27,370 multi-entity trials and 75,777 industry trials were re-decided; agreement with the previous version is 98.6% of entity roles and 98.5% of purposes; failures fell to 1 and 4 |
| D39 | Output caps cut answers on every run: the Keytruda Qlex letter (BLA 761467: 35 approved uses) at 6,000 tokens, and the indication grouping of entities with hundreds of diseases (cyclophosphamide 664, nivolumab 623, bevacizumab 554, carboplatin 548, aldesleukin, prednisone) at 16,000, which left each of their diseases a separate program, with broader-condition links to all its subtypes | Approved uses; program and link counts | fixed: caps raised to 32,000 and direct calls streamed; trial links fell from 704,049 to 574,254 in the final build |
| D40 | The model declines to answer for some products derived from pathogens, toxins or live vectors (botulinum, plague and Ebola antigens, oncolytic viruses, engineered bacteria) on every attempt; in the latest runs, 162 entities have no target, 53 no modality, 21 intervention names no entity and 10 entities no indication grouping | Those entities have no target or modality and fall out of Section 2 and the modality strata | disclosed (report Limitations; `report.quality` counts them) |
| D41 | Open Targets diseases keyed by EFO, HP or Orphanet ids had no MONDO id, because the 26.09 cross-references hold only 19 MONDO ids. Their evidence never matched a program: all of OT's idiopathic pulmonary fibrosis genetics sits under EFO:0000768 | Section 2 evidence coverage | fixed: migration 79 stores MONDO's `equivalentTo` flag. An OT disease maps through MONDO's equivalence to its own id (42 diseases) or, when unambiguous, to its DOID, Orphanet, NCIT or MeSH ids (261); traits and measurements stay unmapped |
| D42 | Held-out-target AUCs from one grouped 5-fold split moved by 0.03 with the fold assignment alone (evidence model 0.604 vs 0.640 on the same data), so "what the evidence adds" depended on the split | C33, C34, ablation | fixed: out-of-fold predictions averaged over 20 stratified grouped splits; two seeds agree within 0.006 |
| D43 | Statements in the narrative that the numbers did not support: "the ordering of disease areas broadly follows BIO's" (rank correlation 0.30; endocrine and oncology far above BIO), cardiovascular among the lowest areas, small molecules and proteins the lowest modalities, genetics' ablation "small but real", "the temporal split tells the same story", and uncertain approvals "defensible 60% of the time" | Report text | fixed: rewritten from the outputs, and every static statement checked against `numbers.json` by script |
| D44 | Runner and approval writes. A chunk with no validated approval decision left up to 30 programs without a row, which read as "not approved" (anastrozole and methylprednisolone in the rebuild). A dropped stream or database connection aborted a run and discarded results already paid for, and such runs were never marked failed. Reused decisions were stamped with the current task's model parameters. Target kinds of re-decided entities went stale | Approvals; provenance | fixed: unjudged calls are reported and re-asked until none remain. The runner stores decisions on fresh connections with replay, retries dropped streams, marks failed runs, and keeps the original model parameters; target kinds are reset on each rebuild |
| D45 | The "US-developed" cohort looked ahead. A row counted as US when the program had a US-sited industry trial in that phase or in any later phase, and a later phase exists mostly for programs that advanced: 513 Phase 1 rows were US only through a later trial, 452 of which advanced | Headline US LOA, US strata | fixed: a US-sited industry trial among the trials that mark entry to that phase |
| D46 | A Phase 1 program that entered through a shared trial (a first-in-human or basket study) could be "suspended" while that trial was still recruiting: activity was read only from its own trials. 365 Phase 1 suspensions had a duration of zero | Phase 1 rate | fixed: the trial that marked the program's Phase 1 entry counts toward its activity |
| D47 | Phases a program skipped were not credited. A Phase 2 program approved directly, or one that went from Phase 1 straight to Phase 3, still had its LOA discounted by the skipped phase's rate, which BIO counts as a success | LOA (about 12% too low) | fixed: skipped phases count as successes (397 Phase 2 and 55 Phase 3 credits) |
| D48 | Approvals dated only as "before 2015" were placed at 2014-12-31. In the 2008–2016 prediction cohort this turned programs of already-approved drugs into ten-year successes: 43 of 199 positives were entities approved before their Phase 1 entry (vincristine, dexamethasone, cytarabine) | Prediction metrics | fixed: such an approval sits at the entity's first FDA approval, the earliest it could have happened, so a program entering after it is a lifecycle program |
| D49 | The genetics ablation removed only the union column and left GWAS and rare-variant evidence in the model, so "removing genetics barely changes AUC" was untested | C26, C32, prediction narrative | fixed: genetics enters as its parts and is removed as a group |
| D50 | The "no reason, no result" failure category included trials that had posted results (609 programs) or stated another reason (32) | Failure-mode shares | fixed: separate categories for posted results without a readable endpoint and for other stated reasons |
| D51 | Strata with very few resolved programs got bootstrap intervals from the draws in which they happened to resolve (CAR-T: one resolved Phase 3 program, 36% of draws empty), so their intervals were too narrow | Area and modality tables | fixed: no LOA for a cohort with fewer than 10 entities resolved in a phase |
| D52 | A registered but not-yet-recruiting later-phase trial counted as advancement (247 rows) | Transition rates | fixed: a later-phase trial advances a program once it has started; while registered it keeps the program active |
| D53 | A trial that never started (status UNKNOWN, estimated start date, no update since before it) still marked phase entry and advancement; not-yet-recruiting trials marked entry | Section 1 cohorts and transitions; Section 3 cohorts | fixed: such trials mark neither entry nor advancement (16,562 cohort programs instead of 17,047; US LOA 10.4% instead of 10.5%) |
| D54 | Open Targets' direction-of-effect fields follow variant consequence, so a few truncating ClinVar variants make gain-of-function disease genes (PCSK9, MYH7, TTR) read as loss of function | Section 3 H3 | disclosed; H3 reported as registered and direction re-derived from drug-blind mechanism labels (`preclin.gene_disease_mechanism`) |
| D55 | 89% of GWAS rows are on measurement traits with no MONDO disease (LDL cholesterol, blood pressure), so they cannot match a program's disease | Section 3 G3, Section 2 genetics | partly fixed: they now count as germline evidence on the target (G1), not as 'none'; disclosed that G3 undercounts trait-found genetics |
| D56 | IMPC-consortium mouse models carry no date in Open Targets, and MGI models carry the gene's earliest literature year | Section 3 mouse evidence; rule M7 | superseded by D62 |
| D57 | Open Targets exports burden results only at p < 2.5e-6 and expression changes only at abs(log2FC) >= 1.1, so the plan's strength tiers for those sources equal the family | Section 3 evidence map | disclosed; the tiers are left out of the map |
| D58 | First-pass gene-disease mechanism labels counted somatic tumour mutations as germline and dated some pairs by another disease's paper (9 of 30 audited pairs wrong) | Section 3 direction | fixed: prompt v3 requires an established germline link and separate risk and protective years for the disease |
| D59 | An open-label extension study registered as Phase 2/3 counts as a Phase 3 start (amlitelimab, RIVER-AD) | Transition rates; Section 3 S4 | fixed: pipeline.programs build asks trial_phase_role (migration 91) whether each phase-start candidate is an extension; 14,428 trials judged, 404 extensions, 6,639 program-trial links no longer start a phase |
| D60 | Another sponsor's Phase 3 trial of a different drug linked to a program (zigakibart credited with atrasentan's ALIGN trial) | Transition rates; Section 3 S4 | fixed: the same check records which entities each trial's main period tests; 921 entities that join only a later period no longer take its start (zigakibart is not credited with ALIGN) |
| D61 | Open Targets dates ClinVar records by their latest evaluation, which moves forward at every re-review (a quarter of rows dated 2025) and can precede a late submission; Mendelian evidence that existed at entry looked absent, and some looked older than it was | Section 2 rare-variant line and genetics; Section 3 G3 and Mendelian tiers | fixed: each RCV record dated by its creation year, from a calibration of first-submission dates against accession order (`pipeline.evidence_dates clinvar`); launch-import records keep their earlier evaluation year. A record reclassified pathogenic after creation still counts from creation (rate reported by the run) |
| D62 | IMPC-consortium knockouts (125k rows, 720 alleles) carry no date or the gene's first literature year; the latter leaked into Section 2's mouse-model line through Open Targets' yearly series | Section 2 animal-model line; Section 3 M7 | fixed: dated by the first yearly IMPC data release with calls for the allele (656 of 720 alleles; the rest stay undated). D56's statement that MGI models carry the gene's literature year was wrong: 695 of 987 genes with several MGI models have different years across them, so the year is the model's first paper |
| D63 | Section 2 read Open Targets' precomputed yearly association series, which inherit the dates in D61-D62 | Section 2 as-of scores | fixed: series rebuilt in the database from the dated rows (`preclin.harmonic_series`, Open Targets' harmonic sum over sum(1/i^2), i <= 1000); on the original dates it reproduces Open Targets' series at 99.8% of points |
| D64 | Rows without a publication date: Expression Atlas (62 experiments), IntOGen (60 cohorts), CRISPR screens (3) | Section 2/3 expression, somatic, screen lines | fixed: GEO/ArrayExpress public dates, the year in the cohort name, the screen's paper. Cancer Gene Census, Orphanet, UniProt, Reactome and PanelApp rows without literature have no source history (PanelApp's activity logs run to hundreds of MB) and stay undated |
| D65 | 1,676 interventional drug studies that ran (completed, terminated, suspended) register no start date and were left out of every program, hiding earlier history of 532 entities | Program entry and novelty; cohorts | fixed: start date set to the latest it can be (first submission or completion, `UPPER_BOUND`); 583 withdrawn, unknown-status or not-yet-recruiting studies stay undated |
| D66 | The legacy literature scores (cell, animal, mechanistic, human PD) cited papers from any year: 803 of 945 human-PD citations, and 1,109–1,157 of ~1,550 per other line, were published in or after the year of the target's first trial, and 329 human-PD scores cite only such papers | Legacy benchmark only (removed in #28; C29) | confirmed; not used by the rebuilt report |
| D67 | The trial-outcome summary gave each result row the outcome-wide number analysed, not the row's own (STEP 1: n=1306 shown where 1212 were analysed in-trial and 1059 on treatment) | Trial outcomes (primary endpoint judgement) | fixed: each row's own count in the unit the measure selects; outcomes re-classified |
| D68 | The trial-outcome and endpoint classifiers saw only the first 3 (endpoints: 8) primary outcomes, 4 result rows, 4 analyses and 6 adverse-event groups, cut at 6,000 characters (brief summaries and abstracts at 3,000); 14% of trials with posted results have more than 3 primaries | Trial outcomes, endpoints; failure modes | fixed: every primary outcome and all text, untruncated (PR #34); re-classified |
| D69 | Target assignment rejected symbols the catalogue spells differently from HGNC: previous symbols and aliases such as TDGF1 (CRIPTO), CTGF (CCN2), RON (MST1R), TIM3 (HAVCR2), CD20 (MS4A1); 77 decisions failed on 18 such symbols | Entity targets; Sections 2–3 | fixed: symbols resolve through HGNC approved, previous and alias symbols (`pipeline.hgnc`, release recorded) |
| D70 | Target hints came from a ChEMBL bulk file with no recorded release that kept one gene per drug name (tirzepatide: GIPR only) | Entity targets | fixed: every ChEMBL 37 mechanism of the parent molecule, all genes of each target (`pipeline.chembl`) |
| D71 | The pan-essential flag came from a DepMap table with no recorded release or rule | Section 2 covariate; Section 3 liability | fixed: DepMap Public 24Q4 CRISPR inferred common essentials (`pipeline.depmap`; 1,523 genes, 1,278 of the 1,284 previously flagged) |
| D72 | The PubMed results-paper step recorded no retrieval date or content | Publication-based outcomes provenance | fixed: each run registers a release with its date and content hash |
| D73 | Section 3 case verification (33 new cases) found: topiroxostat's Phase 2 entry taken from a trial of another drug (dotinurad, NCT02837198) in which topiroxostat is only a combination partner; padsevonil's action at GABRA1 recorded as ambiguous (a partial agonist increases function); pruxelutamide's Phase 3 trials registered only in China, so the pipeline sees no advance | Entity trial roles; target actions; outcome for non-CT.gov trials | open: trial-role labelling for combination arms; the action label; non-CT.gov registries remain a stated limitation |
| D74 | A cough trial abbreviated "CRC" (chronic refractory cough) mapped to colorectal carcinoma: nedizantrep (GDC-6599, NCT05660850) | Program disease; Section 1 failure modes; attribution | open: found by the efficacy-attribution adjudication; disease mapping |
| D75 | Orvepitant's Phase 2 chronic refractory cough program carries no disease (NCT02993822) | Program disease; Phase 3 cohort and attribution | open: found by the efficacy-attribution adjudication; disease mapping |
| D76 | The attribution model refuses to label some gene therapies, engineered cell therapies, live biotherapeutics and viral-vector products (31 Phase 2/3 efficacy failures) | Section 1 efficacy attribution | disclosed: reported as unlabelled, not worked around (as for targets) |
| D05 | Migration numbering collision: local untracked `db/10`–`db/23` vs `origin/main` `db/10`–`db/26`; some local files were applied to the DB outside the ledger | Reproducibility | confirmed; new work uses ledgered migrations 53+ |

## Work log

- 2026-10-26 — Why efficacy failed (Section 1). Plan committed before labelling
  (`report/attribution_plan.md`). New data: PubMed searches on each failed entity's human
  pharmacology and on the entity in each program disease (`preclin.moiety_publication`, reviews
  excluded), and a three-pillar reading (exposure, engagement, pathway) with a failure code for
  every program Section 1 records as stopped for efficacy (`preclin.efficacy_failure_attribution`,
  LLM, sources limited to the bundle and validated). Checks: a stepwise re-derivation by a second
  model on a seeded sample of 150, and a blind web adjudication of a seeded sample of 66 by agents
  (`report/audits/attribution_adjudication.json`), which also found D73–D74.

- 2026-10-21 — Section 3, which evidence translates. Plan committed before any outcome analysis
  (`report/translation_plan.md`). New data: primary outcome measures for every trial
  (`ctgov_study.primary_outcomes`), Open Targets 26.09 evidence rows with dates, direction and
  confidence (`preclin.ot_evidence`, 3.3 million rows) and mouse phenotypes, the Mammalian
  Phenotype ontology, the governing primary endpoint of 31,802 industry Phase 2/3 trials
  (`preclin.trial_endpoint`, LLM, drug-blind), drug-blind germline mechanism labels for 1,887
  target-disease pairs (`preclin.gene_disease_mechanism`, v3) and orientation labels for 7,676
  mouse models (`preclin.mouse_model_relation`, v2). An adversarial review of the analysis (six
  dimensions, each finding verified) led to D53–D58 and to fixes in the analysis itself: a
  separate sentinel for absent evidence in the 'known today' comparison, the permutation null
  fitted with the H1 model, outcome-specific covariates in the stacked H5/H6 models, rare
  covariate levels given their own indicator, the endpoint stratum taken only from trials that
  started within a year of entry and before the program advanced, and the case protocol of
  the plan. Case studies verified by agents against primary sources (outcome blind to evidence,
  evidence blind to outcome, a second failure coder, adjudication).

- 2026-10-21 — PR #27 split into five stacked PRs (legacy removal; LLM runner and sources; entities,
  diseases and programs; labels and evidence; report). Code consolidated without behaviour change
  (same LLM payload hashes, written rows and report outputs on the same database): one Anthropic
  runner, one CBER HTTP/cache layer and corrections module, no duplicated readers. Two independent
  reviews (pipeline stack; report code) found the problems recorded as D37–D52, all fixed. The
  rebuild ran twice from indication mapping onward: roles (prompt v3) and purposes (v2) were
  re-decided for every trial (98.6% of entity roles and 98.5% of purposes as before); 42,876
  disease mappings were re-decided once their candidate lists were ordered (same MONDO term for
  92%); 1,241 calls of that run failed when the API credit balance ran out and were re-asked (the
  runner now stops such a run instead of completing it). The identity steps converge over passes
  (entities merged: 145, then 69) and a rerun still re-asks a few hundred product matches and
  same-entity checks. The approval audit was re-scored against the final judgements (85 programs;
  5 left the sample as no longer programs; changed judgements adjudicated against the auditors'
  notes). Final report: US-developed LOA 10.5% (9.4–11.8), all programs 7.2%; human genetic
  evidence relative success 2.83 (2.21–3.64); held-out AUC 0.611 without and 0.665 with evidence.
  Every static statement in the narrative is checked against the outputs by script.

- 2026-10-20 — Repository cleanup: deleted the legacy benchmark (`benchmark/`, RESULTS.md and 17
  one-off `analyses/*.py` scripts; D25), the superseded classifiers (why_stopped, silent_kill,
  nelson_tier_*, score_target_literature), the 8 tests that exercised only those, 10 stale
  `data/` snapshots and `db/QUESTIONS.md`. Of `report/output/` only the figure PNGs stay tracked;
  `make report` regenerates the rest. `make programs` now runs `pipeline.programs purposes`
  and `indications` before `build`, which reads their tables, and `make evidence` runs
  `pipeline.opentargets fetch` before `load`.

- 2026-10-20 — Post-fix re-audit on fresh seeded samples: condition → MONDO 99/100 defensible
  (pattern: some containing terms flagged `exact` instead of `broader`); intervention → entity
  92/100 (scattered: a code resolved to the wrong UNII, a salt UNII over its parent, one wrong
  molecule); program approvals v2 by stratum: dated approvals 25/25, dates 24/25 (was 17/25),
  pre-2015 15/15, not-approved 35/35, uncertain 9/15. Programs are keyed on LLM-grouped
  development indications (D36); vaccines are out of the headline cohorts (strain updates are
  never approved under their own names). Report rendered (`REPORT.md`): US-developed LOA 9.4%
  (8.4–10.5), all programs 5.6%; human genetic evidence relative success 3.50 (2.65–4.53).

- 2026-10-20 — Trial purpose classified for all 75,774 in-scope industry trials (49,364
  indication development, 10,772 product support, 8,635 early development, 6,287
  multi-indication, 349 other); programs rebuilt from it (D29). Approval audit (90
  programs, four strata): approval calls 88/90 defensible but 8 of 25 dated first approvals
  wrong (D32), fixed in approvals v2. Publication-outcome audit v1: 17/20; prompt v2 (only the
  abstracts given; descriptive safety primaries not assessable) re-audited on 30 fresh
  trials: 29/30 primary endpoint, 30/30 safety and efficacy failure. Section 1 on the
  purpose-based build: Phase 1→2 53.2% (BIO 52.0%); US-developed LOA 6.3% (BIO 7.9%, novel
  6.8%). D33–D35 found from the vaccine and Phase 3 strata and fixed.

- 2026-10-20 — CBER index verified by an independent enumeration (yearly pages, ~700 live and
  214 archived product pages, the Purple Book, 968 letters read): 318 of 325 records and all
  112 original BLAs (with dates) match. Its fixes are recorded in `pipeline/cber/decisions.py`
  (two dropped supplements, two corrected letters, one added action; index now 324 actions).
  Estimated recall ≥ 0.94 per year, lowest for 2015–2016 supplements absent from the
  noteworthy lists. PDF pages with a mis-encoded text layer are now OCRed too. Batch queue
  stalls (no batch started after 45 min) moved LLM steps to direct calls (`LLM_DIRECT_MAX`).

- 2026-10-20 — Trial-outcome audit (60 seeded trials, 30 stopped/withdrawn and 30 completed
  with posted results, re-derived by agents from the CT.gov API before reading the stored
  labels; `.cache/outcome_audit/results.json`): stop reason 28 correct / 1 acceptable /
  1 wrong of 30; primary endpoint 58 / 2 / 0 of 60; safety signal 58 / 2 / 0; efficacy
  failure 60 / 60. The one error led to D27. CBER biologics approvals (177 BLAs, 325
  actions 2015–2025, built by `pipeline.cber` from yearly pages, product pages, approval
  zips and Wayback captures) loaded into `preclin.fda_*`. Program build revised (D26).

- 2026-10-20 — Label audit (independent re-derivation of seeded samples by agents with
  web access, results in `.cache/label_audit/results.json`, reported by `report.quality`):
  condition → MONDO 88 correct / 6 acceptable / 6 wrong of 100; intervention → entities
  91 / 4 / 5 of 100; FDA application → entities 96 / 2 / 2 of 100; letter → approved uses
  55 / 5 / 0 of 60. Every error class was fixed in the pipeline (D20–D23) rather than
  patched in place. Migrations 62–72 add program approvals, modality and BIO area,
  CT.gov results summaries, entity targets, Open Targets associations, trial outcomes,
  results papers (`preclin.trial_publication`, abstracts in `public.publications`),
  `indication.mondo_match`, and the UNII substance lists with `moiety.unii`/`aliases`.
  Fixed `llm.run` reuse: with `reuse_by="input"` it compared only the latest decision per
  subject, so subjects decided twice (two retrieval rounds) were re-sent; a duplicate run
  was stopped and its batches cancelled (run 82a29a32 marked failed).

- 2026-10-20 — Rebuild layer (ledgered migrations 53–61): FDA approval sources and
  letter-extracted approved uses (`preclin.fda_*`); pinned MONDO 2026-10-06 and EFO 3.95
  (`preclin.ontology_*`); ClinicalTrials.gov snapshot 2026-10-20, 222,915 interventional
  drug/biological studies (`preclin.ctgov_study`), of which 167,601 list Early Ph1–Ph3;
  trial↔intervention/condition links; molecular entities (`preclin.moiety`,
  `preclin.drug_moiety`); per-trial entity roles; development programs
  (`preclin.dev_program`). LLM decisions are recorded in `pv_evidence.llm_decision` with
  prompt, schema, model, provider and code commit. The Anthropic API key in use
  (radical-numerics account) ran out of credit mid-run; batches already submitted completed.
  Remaining decisions run on OpenRouter (Capable key; 20 requests/min per model) or on
  Claude Code workflow agents (`LLM_PROVIDER=agent`), recorded with their provider.

- 2026-10-20 — Exported the report; mapped DB (`ep-late-smoke`); found main ahead
  of the report (PRs #20–#26). Created worktree, merged Section 1 and Section 2
  branches. Logged D01–D05.
- 2026-10-20 — Audit verdicts recorded for C01–C50 (clusters: universe, approval
  labels, failure reasons, classification quality, relative success, model,
  Phase 3 table, literature; adversarial verification upheld or refined each).
  Evidence for every verdict is under the audit scratch directories listed in
  the workflow results. Numbers marked wrong or revised are recomputed in the
  rebuild below; this register keeps the audit verdict.
- 2026-10-20 — Launched read-only audit workflow (10 claim clusters, each
  adversarially verified). Scraped FDA sources: Drugs@FDA (6,389 NDA/BLA
  applications, 87,337 submissions), 3,821 approval letters for every 2015–2025
  original approval and efficacy supplement (3,410 unique PDFs, text extracted),
  openFDA labels (5,273 NDA/BLA SPLs), ChEMBL 37 drug_indication (60,055 rows).
  Migrations 53–55: `preclin.fda_*`, indication MONDO columns, `preclin.moiety` /
  `preclin.drug_moiety`. Started three claude-opus-5 batch jobs, all recorded in
  `pv_evidence.llm_decision`: letter → approved uses (3,410), indication → MONDO
  (8,875), intervention name → molecular entities (31,405). Logged D06–D08.
