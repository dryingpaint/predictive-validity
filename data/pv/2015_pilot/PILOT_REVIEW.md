# PV 2015 five-trial pilot readiness

Generated: `2026-09-19T00:46:41.279505+00:00`

Cohort: `pv_2015_actual_completed_drug_biological_pilot5_v1`

## Summary

| Item | Count |
|---|---:|
| candidate trials | 10 |
| included trials | 5 |
| excluded trials | 5 |
| llm decisions | 5 |
| included trials in scope | 5 |
| target bridge rows | 101 |
| phenotype bridge rows | 52999 |
| structured target phenotype rows | 37362 |
| structured target context rows | 107775 |
| scholarly works global | 362436 |
| document candidate relations global | 498236 |
| historical pilot asset preclinical relations | 89172 |
| historical pilot asset preclinical unique works | 83700 |
| pilot asset mention relations | 357439 |
| pilot asset mention unique works | 317199 |
| retained jats | 7 |
| retained pdfs | 0 |
| gcs objects | 0 |
| preclinical experiments extracted | 0 |

## Quality gates

| Gate | Status | Value |
|---|---|---:|
| ten deterministic candidates retained | PASS | 10 |
| five reviewed inclusions | PASS | 5 |
| one LLM decision per inclusion | PASS | 5 |
| all five inclusions in development scope | PASS | 5 |
| no unresolved latest asset proposal | PASS | 0 |
| no unresolved latest indication proposal | PASS | 0 |
| literature queue complete | FAIL | 23 |
| no duplicate literature work keys | PASS | 0 |
| no duplicate canonical document candidates | PASS | 0 |
| asset mention corpus contains every historical preclinical pair | PASS | 0 |
| no PMID-backed abstract remains pending | FAIL | 915 |
| no unfinished acquisition runs | PASS | 0 |
| GCS configured and populated | WARN | 0 |
| narrative preclinical experiment extraction | WARN | 0 |

## Trial review

### 0. NCT00711230 — Repeated DermaVir Immunizations in HIV-1 Infected Treatment-naïve Patients

- Cohort: `excluded` (`vaccine`)
- Completion: `2015-01-01` (`ACTUAL`)

### 1. NCT00911183 — Diffuse Large B Cell Non-Hodgkin's Lymphoma in the Vulnerable/Frail Elderly. A Multicentric Randomized Phase II Trial

- Cohort: `included` (`reviewed_therapeutic_candidate`)
- Completion: `2015-01-01` (`ACTUAL`)
- Scope: `included` / `human_therapeutic`
- Assets: cyclophosphamide (anhydrous), doxorubicin, filgrastim, pegfilgrastim, prednisone, rituximab, vincristine
- Indications: diffuse large B-cell lymphoma [MONDO:0018905; treatment]
- Targets: cyclophosphamide (anhydrous) → DNA (inhibits), doxorubicin → DNA (inhibits), doxorubicin → TOP2A (inhibits), filgrastim → CSF3R (agonizes), pegfilgrastim → CSF3R (agonizes), prednisone → NR3C1 (agonizes), rituximab → MS4A1 (unknown), vincristine → Tubulin (inhibits)
- Literature: asset_indication_preclinical=465 works, asset_indication_v2=3 works, asset_mention=185538 works, asset_preclinical_wide=53717 works, effective_target_only_v1=3 works, target_phenotype=911 works, target_wide_phenotype=14366 works

### 2. NCT01272466 — Vaccination With Peptides From Anti-apoptotic Proteins in Relapsed Multiple Myeloma

- Cohort: `excluded` (`vaccine`)
- Completion: `2015-01-01` (`ACTUAL`)

### 3. NCT01434342 — Feasibility of Delivering a Quitline Based Smoking Cessation Intervention in Cancer Patients

- Cohort: `included` (`reviewed_therapeutic_candidate`)
- Completion: `2015-01-01` (`ACTUAL`)
- Scope: `included` / `human_therapeutic`
- Assets: nicotine
- Indications: cancer [MONDO:0004992; background_condition], nicotine dependence [MONDO:0008575; treatment]
- Targets: nicotine → Neuronal acetylcholine receptor; alpha4/beta2 (agonizes)
- Literature: asset_indication_preclinical=541 works, asset_mention=59943 works, asset_preclinical_wide=12649 works, target_phenotype=108 works, target_wide_phenotype=283 works

### 4. NCT01507974 — Examination of the Efficacy of Preventive Antibiotic Treatment During the Puerperium Among Pregnant Women With Recurrent Urinary Tract Infections

- Cohort: `excluded` (`antibiotic`)
- Completion: `2015-01-01` (`ACTUAL`)

### 5. NCT01882166 — Time-lapse Monitoring of Early Embryo Development After Ovarian Stimulation During Infertility Treatment

- Cohort: `included` (`reviewed_therapeutic_candidate`)
- Completion: `2015-01-01` (`ACTUAL`)
- Scope: `included` / `human_therapeutic`
- Assets: choriogonadotropin alfa, follitropin, follitropin beta, urofollitropin
- Indications: female infertility [MONDO:0021124; treatment]
- Targets: choriogonadotropin alfa → LHCGR (agonizes), follitropin → FSHR (agonizes), follitropin beta → FSHR (agonizes), urofollitropin → FSHR (agonizes)
- Literature: asset_indication_preclinical=2 works, asset_indication_v2=1 works, asset_mention=865 works, asset_preclinical_wide=348 works, target_phenotype=829 works, target_wide_phenotype=972 works

### 6. NCT02046239 — Suture vs Staples for Skin Closure After Liver Resection

- Cohort: `excluded` (`non_therapeutic_registry_misclassification`)
- Completion: `2015-01-01` (`ACTUAL`)

### 7. NCT02231931 — Drug-drug Interaction Between Digoxin, Furosemide, Metformin, and Rosuvastatin

- Cohort: `included` (`reviewed_therapeutic_candidate`)
- Completion: `2015-01-01` (`ACTUAL`)
- Scope: `included` / `human_therapeutic`
- Assets: digoxin, furosemide, metformin, rosuvastatin
- Indications: none (healthy-volunteer/non-disease study)
- Targets: digoxin → Sodium/potassium-transporting ATPase (inhibits), furosemide → SLC12A1 (inhibits), metformin → GPD2 (inhibits), metformin → Mitochondrial complex I (NADH dehydrogenase) (inhibits), rosuvastatin → HMGCR (inhibits)
- Literature: asset_mention=70672 works, asset_preclinical_wide=17159 works

### 8. NCT03998215 — Diphtheria Vaccination in Adolescents With Inflammatory Bowel Disease

- Cohort: `excluded` (`vaccine`)
- Completion: `2015-01-01` (`ACTUAL`)

### 9. NCT00082719 — Short-Term Low-Dose Interferon Alfa in Treating Patients With Cancer of the Urothelium

- Cohort: `included` (`reviewed_therapeutic_candidate`)
- Completion: `2015-01` (`ACTUAL`)
- Scope: `included` / `human_therapeutic`
- Assets: interferon alfa-2b
- Indications: carcinoma of urethra [MONDO:0021327; treatment], urinary bladder carcinoma [MONDO:0004986; treatment], urothelial carcinoma [MONDO:0040679; treatment]
- Targets: interferon alfa-2b → Interferon alpha/beta receptor (agonizes)
- Literature: asset_mention=1034 works, asset_preclinical_wide=86 works, target_phenotype=273 works, target_wide_phenotype=789 works

## Boundary

Asset-mention retrieval is raw ingestion. A mention is not a preclinical claim. Document relevance classification and extraction of individual models, assays, endpoints, criteria, and positive/negative/null results are separate downstream enrichments over the frozen documents.

A query hit remains a candidate relation, not a biological assertion. Legacy structured sources preserve their originating row and are not counted as independent evidence merely because Open Targets also aggregates them.
