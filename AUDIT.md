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
- **Program.** One row per (entity, MONDO disease) (`preclin.dev_program`). A trial whose
  condition is broader than another of the entity's diseases (e.g. "solid tumors") rolls
  into the more specific programs; healthy-volunteer trials roll into every program of the
  entity. Such a shared trial marks phase entry only for programs already under way when it
  started and for the program(s) begun next (the lead indication then); an indication added
  later enters at its own first trial (`dev_program_trial.marks_entry`; attach-all is a
  sensitivity). Trials whose conditions are only symptoms or procedures without a MONDO term
  (pain, contraception) form the entity's condition-unspecified program instead. Each industry
  trial's purpose is classified by an LLM (`preclin.trial_purpose`): product-support trials
  (bioequivalence, formulation bridging, food effect, interactions, generic or biosimilar PK)
  belong to no program; multi-indication baskets and early-development trials are shared like
  healthy-volunteer trials. Sponsors are attributes, not part of the key.
- **Approval.** FDA approval for the program's disease and its first date, judged by an
  LLM from the entity's 2015–2026 approval letters (4,639 extracted approved uses; pages
  without a text layer OCRed; labeling-only changes are not approval events), its
  original-approval dates and current label indications (`preclin.dev_program_approval`).
  Approvals before 2015 are taken from the label.
- **Phase cohorts and outcomes.** For phase p, programs whose first industry-sponsored
  phase-p trial started 2015–2025 (shared trials count only for Phase 1 of the lead
  indication), had not already entered a later phase, and were not already approved for the
  disease (lifecycle programs are excluded). Advanced = a later-phase trial of the program's
  own disease started (any sponsor: a cooperative-group trial of a company's drug is
  development), or FDA approval for the disease. Suspended = none of the program's own
  trials active, or active within 24 months of the snapshot. Otherwise censored. BIO-style rate = advanced / (advanced + suspended); a competing-risks
  (Aalen–Johansen) estimate keeps censored programs. LOA = product of phase rates.
  Confidence intervals resample molecular entities (1,000 draws). Sensitivity: lag 12/18/36
  months, US-site programs, novel vs already-approved entities, uncertain approvals.
- **Why programs stop.** Each industry trial since 2010 that stopped early, or completed
  Phase 2/3 with posted results or a results paper, is classified (`preclin.trial_outcome`)
  on separate axes: execution, stated stop reason (with "sponsor decision, unspecified"
  kept apart from explicit business reasons), primary-endpoint result (from posted results,
  else from the abstracts of PubMed papers linked to the NCT id), and safety signal. A
  suspended program's reason comes from the trials of the phase it stopped in.

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
| D13 | ~34% of drug→target links wrong (`therapy_targets_public` alias collisions: PD-1 mAbs→GM2A, atezolizumab→MAT1A, semaglutide→ALPL) | Every Section 2 number | open: moiety→target rebuild |
| D14 | Genetic and other evidence is target-level (any disease), not matched to the indication; indication ontology IDs empty | Section 2 interpretation | fixing: MONDO mapping + ontology-based matching |
| D15 | Literature lines B–E: v1 from hallucinated PMIDs; v2 mostly cites papers after first trial, overlaps the drugs' own programs | Figure 3, Ph3 table, model | open: exclude from headline or time-gate |
| D16 | 360 Sonnet + 120 Haiku why_stopped calls failed and were stored as 'unclear'; Sonnet preferred even when it errored; prompts not committed | C46, C47, failure figure | open: reclassification |
| D17 | Owner DB password hard-coded in 4 scripts on the public GitHub repo (origin/section-1-failure-modes) | Security | removed from code on this branch; rotation needed (owner decision) |
| D18 | Methodology filter misses indication 'Healthy' (4,101 programs); modality from Haiku name guesses for 85% of drugs; placeholder `public.therapies` rows type biologics as small molecules; two modality columns disagree for 2,551 drugs | Section 1 strata | fixing: moiety modality + per-trial methodology |
| D19 | Figure 2 / BIO_REPLICATION.md mix pre- and post-vaccine-exclusion cohorts; leaked benchmark runs stored under canonical scorer names (runs 187–192) | Reproducibility | open |
| D20 | Development codes left unresolved when an INN exists (label audit: 5 of 100 names, e.g. E7046 = palupiprant, IO102-IO103 = imsapepimut + etimupepimut). A molecule run in Phase 1 under its code and later under its INN splits into two entities, and the code entity looks like a Phase 1 failure. | Program counts, transition rates, LOA | fixing: entities resolved to FDA UNII substances (1.05M registered names incl. codes) and merged when they are the same substance (pipeline.drugs unii) |
| D21 | 2,238 of 34,092 disease conditions (6.6%) had no MONDO term because none named them exactly (label audit: all 6 errors in 100); trials with only such conditions lose their disease | Programs, disease matching | fixing: nearest containing MONDO term, flagged `indication.mondo_match = 'broader'` |
| D22 | 147 of 3,669 FDA letters have pages with no text layer (scanned letterheads), so the indication paragraph of e.g. Asparlas and Imjudo original approvals was missing | Approved uses, approval dates | fixed: pages without text are OCRed (pdftoppm + tesseract); 147 letters re-extracted, 4,639 approved uses |
| D23 | Labeling-only supplements were extracted as `efficacy_labeling` uses (label audit: 5 of 60 letters); dated as approval events they could move a disease's first approval to a later labeling update | Approval dates | fixed: excluded from approval events |
| D24 | 7,497 completed industry Phase 2/3 trials (start ≥ 2010) posted no results, so their primary-endpoint outcome was unknown | Failure modes (efficacy failures among completed trials) | fixed where possible: 2,284 have a linked results paper (registry reference or PubMed secondary id); classified from abstracts by a separate task. The rest stay "no results" (published results skew positive, so the paper-based rate is not the rate for unpublished trials) |
| D25 | `benchmark/` (scorer framework, RESULTS.md) still takes ground truth from the legacy views (`preclin.v_target_indication_strict_outcome` over `preclin.program`/`preclin.approval`), so its cohort and AUCs disagree with the report's Section 2 | Second source of truth for predictiveness | open: point the benchmark's ground truth at `preclin.dev_program` + `dev_program_approval` + `moiety_target` |
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
| D05 | Migration numbering collision: local untracked `db/10`–`db/23` vs `origin/main` `db/10`–`db/26`; some local files were applied to the DB outside the ledger | Reproducibility | confirmed; new work uses ledgered migrations 53+ |

## Work log

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
  112 original BLAs (with dates) match. Its fixes are recorded in `pipeline/cber/corrections.py`
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
