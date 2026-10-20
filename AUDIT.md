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

## Claim register

| ID | Report section | Claim | Status | Verified value / note |
|---|---|---|---|---|
| C01 | Intro | Drugs per $bn R&D halved ~every 9 years since 1950 (Scannell 2012) | open | |
| C02 | Intro | 7.9% of Phase 1 entrants reach FDA approval (BIO 2021) | open | |
| C03 | Intro | "The 92% of programs that fail" | open | |
| C04 | Intro | Genetic support 2.6× Ph1→approval (Minikel 2024), 2× (Nelson 2015) | open | |
| C05 | Intro | Efficacy ~52% and safety ~24% of Ph2/Ph3 failures (Harrison 2016) | open | |
| C06 | Intro | AZ 5R programs far more likely to succeed (Cook 2014) | open | |
| C07 | Intro | Scannell coined Eroom's Law; Scannell & Bosley 2016 introduced predictive validity; "landmark study names four reasons" | open | |
| C08 | History | Seven-era history table | open | |
| C09 | Intro | 28,193 industry trials "started after 2015 and ended before 2026" | open | |
| C10 | Intro | Six core lines of evidence compiled from databases and literature classification | open | |
| C11 | S1 | 7.4% of Ph1 programs reached FDA approval, within 0.5pt of BIO | open | |
| C12 | S1 | Only 1 in 20 failed programs records an efficacy or safety reason | open | |
| C13 | S1 | 28,193 trials = 67% of 41,836 industry Ph1–3 drug trials started 2015–2025 | open | |
| C14 | S1 | 84,117 programs; 13,639 T-I pairs with ≥1 Ph1 trial | open | |
| C15 | S1 | Transitions 55.9 / 51.0 / 26.1 / 7.4% vs BIO 52.0 / 28.9 / ~52 / 7.9% | open | |
| C16 | S1 | Mid-phase gap explained by Ph3b, non-US, Ph2/3 designs | open | |
| C17 | S1 | 42,984 Ph1+ programs settled by 2026, vaccines and mRNA excluded | open | |
| C18 | S1 | 55,133 failed programs; silent efficacy = 73% of Ph3 failures | open | |
| C19 | S1 | 5,510 early terminations with a reason; 44% commercial/strategic; Cook 2014 says this masks efficacy failures | open | |
| C20 | S1 | Figure 1: failure reasons by phase | open | |
| C21 | S1 | Ph1 failures mostly non-advancement after safety/PK; Ph3 failures mostly completed trials without approval | open | |
| C22 | S1 | LOA varies ~10× by area: 18.4% hematology → 1.6% urology | open | |
| C23 | S1 | Oligonucleotides 32.5%, small molecules 5.8%; same rank order as BIO | open | |
| C24 | S1 | Modality rates above BIO because of ASO/GLP-1/AAV approvals; infectious/Other lower for missing vaccines/biosimilars | open | |
| C25 | S1 | Figure 2: LOA by area and modality vs BIO | open | |
| C26 | S2 | Genetics is the only line that adds predictive power once the others are known | open | |
| C27 | S2 | Strong genetic support 45% approval vs 11% for none | open | |
| C28 | S2 | 8,144 Ph2+ T-I pairs, base approval rate 23% | open | |
| C29 | S2 | Figure 3: relative success per evidence dimension | open | |
| C30 | S2 | Pathway/GO counts are study-depth proxies | open | |
| C31 | S2 | Genetic dose–response table (8,392 pairs) | open | |
| C32 | S2 | Ablation: genetics −17.7pp; cell/animal 0.0; mechanistic −0.6; PD −0.3; safety −0.2 | open | |
| C33 | S2 | AUC 0.825 on held-out targets, 13,639 Ph1+ pairs | open | |
| C34 | S2 | Time-split AUC 0.769 (train pre-2019) on Ph2+ pairs | open | |
| C35 | S2 | DepMap pan-essential targets RS 0.24 | open | |
| C36 | S2 | gnomAD LoF-intolerant genes RS 0.82–0.84 | open | |
| C37 | Cases | 1,182 Ph3 T-I pairs; strong single-line evidence still fails 73–85% | open | |
| C38 | Cases | Ph3 strong-evidence table (8 rows) | open | |
| C39 | Cases | Best profile (C∧D∧E∧genetics) approves 22% of 422 Ph3 pairs | open | |
| C40 | Cases | BACE1 inhibitors (CSF Aβ42 −50–80%, cognition worsened, ~$4bn) | open | |
| C41 | Cases | Torcetrapib/CETP (HDL +60%, mortality +25%, aldosterone; successors failed) | open | |
| C42 | Cases | Semagacestat (faster decline, Notch → skin cancer, GI) | open | |
| C43 | Cases | Solanezumab/bapineuzumab (no benefit; mouse models overpredicted) | open | |
| C44 | Cases | TGN1412 (500× monkey margin; 6/6 cytokine storm) | open | |
| C45 | Cases | Fialuridine (clean 4-species tox; 5/15 deaths; human-specific transporter) | open | |
| C46 | Appendix | why_stopped category counts (11 categories, n=5,510) | open | |
| C47 | Appendix | Sonnet and Haiku classified every trial; Sonnet kept on disagreement | open | |
| C48 | Appendix | Silent efficacy = efficacy or safety ~90% of the time | open | |
| C49 | Appendix | 18-month rule matches BIO's advanced-or-suspended denominator | open | |
| C50 | Appendix | Limitations list (modality known for 18%; approvals exclude vaccines, mRNA, biosimilars; features not time-frozen except precedent) | open | |

## Data issues register

| ID | Issue | Effect | Status |
|---|---|---|---|
| D01 | `program_outcome.outcome_broad='approved'` is drug-level: any program whose drug is in the 544-row novel-approval table counts as approved, whatever its indication. `approved_elsewhere` is likewise drug-level (ChEMBL max_phase=4). | Every LOA, transition rate and RS in Section 1; the base rate in Section 2 | open |
| D02 | Two conflicting LOA definitions in circulation: committed `bio_replication.py` (approved only → 7.4%) and local working copy (approved + approved_elsewhere → 16.1%) | C11, C15 | open |
| D03 | `preclin.approval` holds 544 novel FDA approvals 2015–2025 with one indication each; supplemental indications, pre-2015 approvals and biosimilars are absent | Strict per-T-I outcome; C11–C25, C27–C39 | open |
| D04 | Report cites the leaked Nelson-tier model (AUC 0.825, genetics −17.7pp); `origin/main` RESULTS.md has the corrected AUC 0.570 and genetics −1.9pp | C26, C32–C34 | open |
| D06 | Drug entity resolution: 79% of 31,405 `preclin.drug` rows are `unresolved` strings; one molecule appears as many drugs (pembrolizumab: `keytruda`, `pembrolizumab 200 mg`, `Pembrolizumab Dose A`, `Pembrolizumab (MK-3475)`, `Keytruda-EU`, …) and placebo arms appear as drugs (`Tirzepatide-Placebo`). Programs are keyed on these strings. | Program counts, LOA denominators, drug-level labels | fixing (pipeline.drugs → preclin.moiety) |
| D07 | `preclin.indication.mondo_id`/`efo_id` empty for all 8,875 indications; `canonical_disease` (90% filled) has case/synonym duplicates | Disease-level units, approval matching | fixing (pipeline.indications) |
| D08 | 6,687 drugs flagged `is_globally_approved` with no ChEMBL ID (approval status from earlier LLM name classification) drive 14,669 `approved_elsewhere` programs | Outcome labels | open |
| D05 | Migration numbering collision: local untracked `db/10`–`db/23` vs `origin/main` `db/10`–`db/26`; some local files were applied to the DB outside the ledger | Reproducibility | open |

## Work log

- 2026-10-20 — Exported the report; mapped DB (`ep-late-smoke`); found main ahead
  of the report (PRs #20–#26). Created worktree, merged Section 1 and Section 2
  branches. Logged D01–D05.
- 2026-10-20 — Launched read-only audit workflow (10 claim clusters, each
  adversarially verified). Scraped FDA sources: Drugs@FDA (6,389 NDA/BLA
  applications, 87,337 submissions), 3,821 approval letters for every 2015–2025
  original approval and efficacy supplement (3,410 unique PDFs, text extracted),
  openFDA labels (5,273 NDA/BLA SPLs), ChEMBL 37 drug_indication (60,055 rows).
  Migrations 53–55: `preclin.fda_*`, indication MONDO columns, `preclin.moiety` /
  `preclin.drug_moiety`. Started three claude-opus-5 batch jobs, all recorded in
  `pv_evidence.llm_decision`: letter → approved uses (3,410), indication → MONDO
  (8,875), intervention name → molecular entities (31,405). Logged D06–D08.
