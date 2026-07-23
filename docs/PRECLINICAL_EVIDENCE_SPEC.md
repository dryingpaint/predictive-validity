# Preclinical Evidence → Clinical Efficacy: Comprehensive Spec

**Core question:** how do different kinds of preclinical evidence predict clinical efficacy, and what are the effect sizes?

**Scope:** every industry-sponsored Phase 1–3 drug/biological clinical trial 2015–2025 (28,286 trials), joined against ~1,700 unique drug programs, ~1,050 unique gene targets, and every relevant preclinical evidence source.

**Data sources available:** genome-browser Neon DB (24+ tables, 9 external sources ingested) + our session's JSONL products + PubMed direct queries.

---

## Part 1 — Taxonomy of preclinical evidence

Grouped by decision-relevant category. Every dimension has (a) definition, (b) data source, (c) tier definition (0-3 or categorical), (d) known predictive-power benchmark.

### Category A — Human genetic evidence (per target × indication)

Answers: **is the target causally implicated in the disease by human genetics?**

| Dimension | Definition | Source | Tiers |
|---|---|---|---|
| A1. **Mendelian evidence** | LoF/GoF variants in the gene cause a monogenic form of the disease, direction concordant with drug MoA | Orphanet + OMIM (`mendelian_associations` in gb) | 0=none / 1=distant / 2=related / 3=causal-matched |
| A2. **GWAS coding variant** | Missense/LoF variant reaches genome-wide significance for the trait | GWAS Catalog (`gwas_associations` in gb) | 0=none / 1=weak / 2=coding-matched / 3=coding + effect direction |
| A3. **GWAS non-coding L2G** | Non-coding hit with confident locus-to-gene assignment | Open Targets L2G | 0/1/2/3 |
| A4. **Gene burden test** | Rare-variant burden significant for indication | UK Biobank / gnomAD ExWAS | 0/1/2/3 |
| A5. **Direction concordance** | Drug MoA direction (agonist vs antagonist) matches human LoF/GoF direction | Derived | boolean |
| A6. **ClinGen validity** | Expert curation of gene-disease causality | ClinGen (`clingen_validity` in gb) | Definitive / Strong / Moderate / Limited / Disputed / Refuted |

**Composite:** Nelson tier T0-T4. Predictive effect: **~2.6× approval odds (Minikel 2024)**.

### Category B — Mechanistic biology (per target, some drug-level)

Answers: **do we understand the target well enough to drug it precisely?**

| Dimension | Definition | Source | Tiers |
|---|---|---|---|
| B1. **Structural biology** | Crystal structures of target ± drug complex | PDB (`protein_structure` in gb, ready but not ingested) | Count of PDB IDs, count with ligand |
| B2. **Binding characterization** | Kd, Ki, kon/koff published | ChEMBL activity | Full / partial / none |
| B3. **Selectivity panel** | Off-target activity across related targets | ChEMBL activity (multiple targets), DGIdb | 0/1/2/3 |
| B4. **Enzyme kinetics** | For enzymes: catalytic mechanism, allostery | UniProt EC + literature | 0/1/2/3 |
| B5. **Isoform / splice variant coverage** | Which isoform is targeted; consequences of hitting others | UniProt + genome-browser targets.ip_type | qualitative |
| B6. **PTM regulation** | Phosphorylation / methylation / etc. regulating target | PhosphoSitePlus / literature | 0/1/2/3 |

**Composite:** structural-biology score. Predictive effect: **saturated at high for approved drug targets** (weak marginal signal per current data).

### Category C — Cell-pathway validation (per target + per drug)

Answers: **do human-relevant cells respond to perturbation as predicted for the disease?**

| Dimension | Definition | Source | Tiers |
|---|---|---|---|
| C1. **Cell-line pharmacology** | Drug tested in cancer / immortalized cell lines with IC50 | ChEMBL activity | 0=none / 1=basic / 2=multiple / 3=full panel |
| C2. **iPSC-derived models** | Drug or perturbation tested in iPSC-derived disease-relevant cells | PubMed extraction | 0/1/2/3 |
| C3. **Organoid models** | 3D organoid recapitulation of disease phenotype ± drug rescue | PubMed extraction | 0/1/2/3 |
| C4. **Primary human cells** | Drug tested in patient-derived primary cells (blood, biopsy, resected tissue) | PubMed extraction | 0/1/2/3 |
| C5. **CRISPR essentiality** | For oncology: does gene KO kill the relevant cancer cell line? | DepMap (`gene_essentiality` in gb, ~21M scores) | Chronos score |
| C6. **Perturbation-rescue** | Direct target modulation rescues disease phenotype in human cells | PubMed extraction | 0/1/2/3 |
| C7. **Pathway convergence** | Multiple perturbations in target's pathway produce same phenotype | STRING PPI (`protein_interactions` in gb) + literature | derived |

**Composite:** cell-pathway validation score. Predictive effect: **currently null at target-level (OR 0.90 [0.83, 1.00])**. Drug-level TBD (pipeline running).

### Category D — Animal in vivo (per target + per drug)

Answers: **does the drug or KO reproduce the disease-modifying effect in animals?**

| Dimension | Definition | Source | Tiers |
|---|---|---|---|
| D1. **Mouse KO phenotype** | IMPC / MGI: does gene KO give disease-relevant phenotype? | IMPC Solr + MGI | 0/1/2/3, phenotype relevance |
| D2. **Rodent drug efficacy** | Drug tested in rodent disease model, effect size | PubMed extraction | 0/1/2/3 |
| D3. **Non-rodent efficacy** | Dog, monkey, non-human primate efficacy | PubMed extraction | 0/1/2/3 |
| D4. **Model relevance** | Disease model recapitulates human disease (not just symptomatic proxy) | Literature curation | 0/1/2/3 |
| D5. **Independent replication** | Multiple labs reproduce the finding | PubMed extraction | 0/1/2 |
| D6. **Humanized models** | Humanized mouse with human target expressed | Literature | binary |
| D7. **Dose-response coherence** | PK/PD in animal predictive of expected human dose | Literature | 0/1/2/3 |
| D8. **Chronic dosing safety** | Long-term (30-day+) dosing in animals without emergent tox | Regulatory summaries | 0/1/2/3 |
| D9. **Preclinical tox flags (multi)** | Cardiovascular, hepatic, hematological, neurological, genotoxic, reprotoxic | Regulatory + literature | per-organ 0-3 |

**Composite:** animal in vivo score. Predictive effect: **null at target-level (OR 1.01 [0.93, 1.09])**. Drug-level TBD.

### Category E — Human PD engagement (drug-specific, Phase 1+)

Answers: **does the drug engage its target in humans and move pharmacodynamic markers as predicted?**

| Dimension | Definition | Source | Tiers |
|---|---|---|---|
| E1. **PD biomarker movement** | Downstream biomarker changes in direction and magnitude predicted | CT.gov results + PubMed | 0/1/2/3 |
| E2. **Target-engagement (direct)** | PET / receptor occupancy imaging showing drug at target | Literature | 0/1/2/3 |
| E3. **Dose-response coherence** | Human dose-response matches preclinical PK/PD | Literature | 0/1/2/3 |
| E4. **Cross-species PK translation** | Preclinical allometric predictions accurate in humans | Literature | 0/1/2 |
| E5. **Immunogenicity** (for biologics) | ADA formation, neutralizing antibodies | CT.gov + literature | 0/1/2/3 |
| E6. **Chronic-dose safety window** | Human tolerability at exposures needed for efficacy | Regulatory + literature | 0/1/2/3 |
| E7. **Companion Dx / biomarker strategy** | Predictive biomarker for responders exists and validated | `therapy_biomarkers` in gb (PharmGKB) | boolean + role |

### Category F — Human clinical efficacy (outcome — post-hoc)

Answers: **did the drug meet its primary endpoint?**

Directly derived from CT.gov `resultsSection` + FDA labels + published trials. Includes:

- F1. Phase 2 primary endpoint met (Y/N/mixed)
- F2. Phase 3 primary endpoint met (Y/N/mixed)
- F3. Effect size vs comparator
- F4. Subgroup consistency
- F5. Independent replication (multiple confirmatory trials)
- F6. Long-term durability

### Category G — Pharmacology / DMPK / chemistry

Answers: **is the drug drug-like enough to work in humans?**

| Dimension | Source | Notes |
|---|---|---|
| G1. Ro5 compliance | ChEMBL molecule properties | Small molecules only |
| G2. Half-life (h) | Literature + FDA labels | — |
| G3. Oral bioavailability | Literature + FDA labels | — |
| G4. Protein binding | Literature | — |
| G5. CYP profile | Literature | Metabolism liabilities |
| G6. Route of administration | ChEMBL / FDA labels | — |

Predictive effect: covered 4-10% of failures per Waring 2015.

### Category H — Safety (multi-dimensional)

Answers: **will hitting this target cause harm we can't dose around?**

| Dimension | Source | Notes |
|---|---|---|
| H1. LoF safety (LOEUF) | gnomAD (`gene_constraint` in gb) | See rubric §lof_safety |
| H2. Essentiality (DepMap) | DepMap (`gene_essentiality_summary`) | Chronos score |
| H3. On-target adverse event class | SIDER (`adverse_events` in gb) | 8 MedDRA-PT SOC keyword classes |
| H4. Off-target liability panel | ChEMBL selectivity data | — |
| H5. Cardiovascular (hERG) | Literature + regulatory | — |
| H6. Hepatotoxicity (DILI) | Literature + regulatory | — |
| H7. Immunotoxicity | Literature + regulatory | — |
| H8. Reproductive tox | Literature + regulatory | — |

### Category I — Landscape / commercial (ancillary)

- I1. Prior approvals against same target (family precedent)
- I2. First-in-class flag
- I3. Competitive intensity (# active programs on same target)
- I4. Regulatory pathway used (orphan, breakthrough, accelerated)
- I5. Indication difficulty (baseline LOA by therapeutic area)

---

## Part 2 — The 5 core questions and how to answer each

### Q1: What are the tiers of *in vivo* evidence and to what extent do they predict clinical efficacy?

**Tiers** (Category D):
- **Tier 0:** No animal data (never tested in vivo, or PK-only)
- **Tier 1:** Rodent efficacy in one disease model
- **Tier 2:** Rodent efficacy + non-rodent species (dog / primate)
- **Tier 3:** Multi-species + independent replication + humanized model
- **Kill flag:** In vivo tox signals in 2+ organ systems

**Analysis:**
- Population: 5,510 failed + 2,120 completed-approved programs
- For each program: score in vivo tier per drug-specific PubMed extraction
- Compute P(approved | tier) with 95% bootstrap CI
- Compare against baseline P(approved) = ~15%
- Effect size = odds ratio tier N vs tier 0
- Stratify by therapeutic area (in vivo evidence more predictive in some TAs)

**Current best data:** Line D scores from `literature_scores.jsonl` (target-level, OR 1.01 [0.93, 1.09] — null). Drug-level pipeline running.

**Extension needed:** join genome-browser `target_evidence.animal_model_score` (Open Targets phenodigm) for validation of Tier 3 assignments.

### Q2: What are the tiers of *in vitro* evidence and to what extent do they predict clinical efficacy?

**Tiers** (Category C):
- **Tier 0:** No cell data (target ID only)
- **Tier 1:** Cell-line pharmacology (IC50 in immortalized lines)
- **Tier 2:** Primary human cells respond
- **Tier 3:** iPSC / organoid disease-model rescue demonstrated
- **Tier 3+:** Cross-lab replication with matched-patient cells

**Analysis:** Same shape as Q1 with C-dimension scores.

**Current best data:** Line C scores from `literature_scores.jsonl`. OR 0.90 [0.83, 1.00] at target-level. Drug-level pipeline running.

**Extension needed:** DepMap essentiality (`gene_essentiality` in gb) as sub-signal for cancer targets. STRING PPI convergence for pathway-level Tier 3.

### Q3: What are all classes of preclinical evidence compiled before clinical trials?

**Answer:** the 8 categories A–H above. Complete taxonomy in Part 1. Every dimension has:
- Data source
- Tier definition
- Public availability assessment
- Coverage rate in our current data

**Report deliverable:** matrix of (dimension × drug) showing evidence coverage. Sparse across most drugs — reflects public-data limitations.

### Q4: Within efficacy failures, what types of evidence did or did not exist?

**Analysis:**
- Filter to trials classified `efficacy` (Haiku or Sonnet, high-confidence)
- For each drug in this set, compute evidence coverage across A–H
- Compare against evidence coverage for approved drugs matched on therapeutic area
- **Key question:** what evidence dimensions systematically differ between efficacy-failures and approvals?

**Expected findings:**
- Efficacy failures likely have low or missing Category A (human genetics) — the strongest predictor
- Similar Category B/C/D coverage across both (i.e., preclinical work is equally rigorous whether or not it translates)
- Category E (PD engagement) may distinguish (approved drugs = target-engaged in humans; efficacy failures = often achieved engagement but no benefit)

**Deliverable:** side-by-side coverage matrix + odds-ratio-like heatmap showing which evidence types matter for avoiding efficacy failure.

### Q5: Within safety failures, what safety evidence did or did not exist?

**Analysis:**
- Filter to trials classified `safety` (Haiku or Sonnet, high-confidence)
- For each drug: extract Category H dimensions from all sources
- Compare against approved-drug safety profiles matched on target class

**Expected findings:**
- Safety failures likely have deficits in Category H4 (off-target liability panel) — many preclinical safety programs use limited off-target screens
- Species-specific safety (H3-H8 in humans absent from H1-H7 in animals) → common cause per TGN1412, fialuridine case studies
- Cardiovascular (H5) and hepatotoxicity (H6) most common causes per FAERS analyses

**Deliverable:** categorical breakdown of safety failure modes with evidence-gap analysis.

---

## Part 3 — Data source unification map

For each evidence category, the primary source table (in genome-browser or our JSONL):

| Category | Genome-browser table | Our JSONL | External (PubMed / API) |
|---|---|---|---|
| A. Human genetics | `mendelian_associations`, `gwas_associations`, `clingen_validity`, `target_evidence.genetic_score` | `nelson_tiers_batch_*.csv`, `opentargets_associations.jsonl`, `tier_validation.csv` | Open Targets GraphQL |
| B. Mechanistic biology | `targets.ip_type`, `targets.family`, `targets.tractability_*`, `target_evidence.literature_score` | `chembl_mechanisms.json`, `chembl_targets.json` | PDB REST, PubMed |
| C. Cell-pathway | `gene_essentiality` (DepMap), `single_cell_expression` (HPA), `protein_interactions` (STRING) | `literature_scores.jsonl` (Line C, target-level), `drug_evidence.jsonl` (Line C, drug-level, in progress) | PubMed |
| D. Animal in vivo | `target_evidence.animal_model_score` (Open Targets phenodigm) | `gene_impc_summary.csv` (67K IMPC records), `literature_scores.jsonl` (Line D), `drug_evidence.jsonl` (Line D) | IMPC Solr, PubMed |
| E. Human PD engagement | `trials.result_pmids`, `therapy_biomarkers` | `trials_results.jsonl`, `literature_scores.jsonl` (Line E), `drug_evidence.jsonl` (Line E) | PubMed |
| F. Clinical efficacy | `trials`, `approvals` | `approvals.csv`, `trials_industry_drug.csv`, `trials_results.jsonl`, `why_stopped_haiku.jsonl`, `why_stopped_sonnet.jsonl` | CT.gov API |
| G. Chemistry / DMPK | `targets.tractability_sm`, `therapies.route_of_administration` | `chembl_drugs.json` | ChEMBL |
| H. Safety | `gene_constraint` (gnomAD), `gene_essentiality_summary` (DepMap), `adverse_events` (SIDER), `target_evidence.somatic_score` | — | ChEMBL activity panels |
| I. Landscape | `approvals`, `sponsors`, `trials` | `approvals.csv`, `sponsors.csv`, `program_master.csv` | — |

---

## Part 4 — Effect-size analysis specification

For each Q1-Q5, the analytical output should be:

1. **Coverage table** — % of drugs with data for each dimension
2. **Effect-size table** — for each dimension, OR for approval (Q1-Q3) or contribution to failure mode (Q4-Q5), with 95% CI
3. **Interaction analysis** — where two dimensions co-occur, joint OR
4. **Therapeutic-area stratification** — do effect sizes vary by TA?
5. **Case examples** — 5-10 named examples per finding (drug + why it exemplifies the finding)

Statistical methodology:
- Bootstrap CIs on all rates (already implemented)
- Correction for multiple comparisons on effect-size tests
- Adjust for cohort composition (some sponsors overweight in oncology; correct for TA imbalance)

---

## Part 5 — Deliverables

### D1. Master evidence dataset
- Table `drug_evidence_full` — one row per (drug × indication) with all A-I dimensions
- Sources:
  - Genome-browser Neon DB (via SQL)
  - Our JSONL products (via CSV export)
  - PubMed direct extraction (for missing drug-specific data)
- Persistence: CSV export + optional Neon insertion for genome-browser integration

### D2. Coverage matrix
- Rows: 8 categories (A-H, I ancillary)
- Columns: 3 slices (approved, efficacy-failed, safety-failed)
- Cells: % coverage of each dimension

### D3. Effect-size report
- One table per question Q1-Q5
- One-page summary with headline numbers
- Full table with bootstrap CIs
- Interaction plots

### D4. Case studies (extension of `CASE_STUDIES.md`)
- 5 more high-signal examples covering:
  - Efficacy failures with strong Category A (e.g., ARN-509 → androgen receptor, well-validated but tox)
  - Efficacy failures with strong Category C/D (BACE1 already covered)
  - Safety failures with weak Category H4 (TGN1412 already covered)
  - Successful drugs with weak Category A (many antibiotics, imaging agents)
  - Programs that succeeded on Category E alone

### D5. Report integration
- Rewrite REPORT.md §2 with drug-specific evidence-line odds ratios
- Add new section §6 "Evidence-type effect sizes"
- Update `MODEL_SPEC.md` with the full 60+ feature list from the taxonomy

---

## Part 6 — Publication bias handling

Every finding must be explicitly caveated for:
1. **Preclinical publication bias** — negative animal/cell data for failed drugs largely absent
2. **Selection bias** — analysis restricted to drugs that reached Phase 1
3. **Sponsor euphemism** — commercial/strategic bucket contains ~60% disguised efficacy failures per Cook 2014
4. **Circular LLM knowledge** — Haiku knows if a drug was approved; scores may be biased toward positive for approved drugs

Where possible, use structured database sources (genome-browser tables) rather than LLM extraction to avoid circular bias.

---

## Part 7 — Integration with genome-browser

The genome-browser DB provides ~80% of the evidence dimensions we need. Our contributions add:
- Drug-specific evidence extraction (Category C/D/E at drug level, not just target level)
- Failure classification with sponsor-euphemism correction (Category F)
- Full failed-trial taxonomy with confidence-weighted labels
- Multi-model verification (Haiku + Sonnet agreement)

Recommended: our new artifacts feed into genome-browser as:
- New table `drug_preclinical_evidence` (per-drug scoring)
- New columns on `trials`: `failure_reason_llm`, `failure_reason_publication`, `failure_confidence`
- New view `approval_predictor_features` — flat table joining all evidence dimensions for ML

---

## Part 8 — What "fully complete" looks like

The task is complete when we can answer, with a citation and effect size:

1. **"If a drug has strong human genetic support (Nelson T1), how much does that increase its odds of approval vs Nelson T0?"**
   - Answer: current data says 1.21× [1.07, 1.35] at trial-cohort level, ~2.6× at program level (Minikel 2024)

2. **"If a drug has strong drug-specific animal-model efficacy (Tier 3), how much does that predict approval?"**
   - Pending: `drug_evidence.jsonl` pipeline output

3. **"Of drugs that failed for efficacy, what fraction had strong Category C (cell-pathway) evidence?"**
   - Pending: coverage-matrix analysis on Sonnet-verified failure classifications

4. **"For approved drugs with no human genetic support (T0), what other evidence carried them through?"**
   - Partial answer in current report §9.4 (family precedent, immunology, cytotoxics)

5. **"Which evidence dimension has the highest odds ratio for approval?"**
   - Current: human genetic support (Nelson T1) and human PD engagement (Line E). Full ranking pending drug-level evidence completion.

The task is complete when all five have quantitative answers with CIs, effect-size comparisons, and case-study anchors.
