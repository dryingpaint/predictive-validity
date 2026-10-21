# PV legacy ten-trial pilot review

Generated: `2026-09-17T09:36:18.668015+00:00`

This report preserves the original first-posted-2025 pilot. It is now a legacy formatting checkpoint and is not the cohort definition for expansion. The current definition uses INTERVENTIONAL DRUG/BIOLOGICAL studies with an ACTUAL Study Completion Date from 2015 through 2025; a replacement pilot must be run before full ingestion.

## Collection summary

| Item | Count |
|---|---:|
| focal trials | 10 |
| canonical assets | 3 |
| canonical targets | 6 |
| normalized trial indication links | 6 |
| structured asset target rows | 7 |
| scholarly works | 11205 |
| works with abstract | 11035 |
| works without provider abstract | 154 |
| works abstract pending | 16 |
| document candidate relations | 14285 |
| target literature candidate relations | 8738 |
| asset preclinical candidate relations | 5547 |
| retained jats | 7 |
| retained pdfs | 0 |
| gcs objects | 0 |
| preclinical experiments extracted | 0 |
| unfinished acquisition runs | 0 |
| main track trials | 3 |
| separate vaccine trials | 1 |
| excluded non human trials | 0 |
| non molecular trials | 6 |
| unresolved scope trials | 0 |

## Quality gates

| Gate | Status | Value |
|---|---|---:|
| ten legacy focal trials | PASS | 10 |
| one LLM decision per focal trial | PASS | 10 |
| no unfinished acquisition runs | PASS | 0 |
| related PIMPARK trial resolved | PASS | NCT03947216 |
| uncapped target literature retained | PASS | 8738 |
| asset preclinical candidates retained | PASS | 5547 |
| repeat HTR2A search created no new versions | PASS | stored=0 reused=906 |
| repeat pimavanserin preclinical search created no new versions | PASS | stored=0 reused=73 |
| licensed full-text path exercised | PASS | 7 |
| GCS configured and populated | WARN | 0 |
| PDF path populated | WARN | 0 |
| narrative preclinical extraction | WARN | 0 |
| vaccines routed to separate track | PASS | 1 |
| non-human targets admitted to main track | PASS | 0 |
| all legacy pilot trials have scope decisions | PASS | 0 |

## Trial-level format

### NCT06754514 — Organ Retractor Device Study

- Registry/semantic type: `OBSERVATIONAL` / `device`
- Registry dates: first posted `2025-01-01`; completion `2025-01` (ESTIMATED)
- Development scope: `not_applicable` / `non_molecular_intervention` (non_molecular_trial_kind; policy `human_therapeutics_v1`)
- Literal registry conditions: Liver Retraction During Bariatric Surgery
- Canonical assets: none (non-drug or unresolved)
- Normalized indications: none promoted

### NCT06754527 — Options for Navigating Talking About Risk and Adolescent Choices

- Registry/semantic type: `INTERVENTIONAL` / `behavioral`
- Registry dates: first posted `2025-01-01`; completion `2029-02-01` (ESTIMATED)
- Development scope: `not_applicable` / `non_molecular_intervention` (non_molecular_trial_kind; policy `human_therapeutics_v1`)
- Literal registry conditions: Substance Use (Drugs, Alcohol), Substance Use Risk, Substance Use, Emotion Regulation, Risk Reduction Behavior, Risk Reduction
- Canonical assets: none (non-drug or unresolved)
- Normalized indications: none promoted
- Review queue: indication $.indications[0].concepts[0]=unresolved; indication $.indications[1].concepts[1]=unresolved

### NCT06754540 — Azacitidine Combined with Donor Lymphocyte Infusion for Acute Myeloid Leukemia Post-transplant Relapse Prevention.

- Registry/semantic type: `INTERVENTIONAL` / `therapeutic_drug`
- Registry dates: first posted `2025-01-01`; completion `2027-01-01` (ESTIMATED)
- Development scope: `included` / `human_therapeutic` (all_resolved_assets_in_scope; policy `human_therapeutics_v1`)
- Literal registry conditions: Acute Myeloid Leukemia (AML), Relapse
- Canonical assets: azacitidine (registered_intervention; ChEMBL:CHEMBL1489, PubChem CID:9444)
- Normalized indications: acute myeloid leukemia [MONDO:0018874, prevention]
- Complete structured pharmacology: azacitidine inhibits DNA (ChEMBL mechanism:1873); azacitidine inhibits DNMT1 (ChEMBL mechanism:654); azacitidine inhibits DNMT3A (ChEMBL mechanism:652); azacitidine inhibits RNA (ChEMBL mechanism:1894)
- Raw literature candidates: asset_indication_preclinical=318 works/316 abstracts/0 retained full texts; asset_preclinical_wide=2704 works/2647 abstracts/0 retained full texts; target_phenotype=2291 works/2230 abstracts/0 retained full texts; target_wide_phenotype=3875 works/3848 abstracts/0 retained full texts
- Review queue: asset $.assets[1]=unresolved; pharmacology $.pharmacology[1]=partially_verified; pharmacology $.pharmacology[2]=unsupported

### NCT06754553 — Trial Evaluating the Efficacy of Pimavanserin, a Selective Serotonin 5-HydroxyTryptamine-2A (5HT2A) Inverse Agonist, to Treat Impulse Control Disorders in Parkinson's Disease.

- Registry/semantic type: `OBSERVATIONAL` / `therapeutic_drug`
- Registry dates: first posted `2025-01-01`; completion `2026-02` (ESTIMATED)
- Development scope: `included` / `human_therapeutic` (all_resolved_assets_in_scope; policy `human_therapeutics_v1`)
- Literal registry conditions: Parkinson Disease
- Canonical assets: pimavanserin (historical_exposure; ChEMBL:CHEMBL2111101, PubChem CID:10071196)
- Normalized indications: Parkinson disease [MONDO:0005180, background_condition]; impulse control disorder [MONDO:0001162, treatment]
- Complete structured pharmacology: pimavanserin inverse_agonizes HTR2A (ChEMBL mechanism:5389)
- Raw literature candidates: asset_preclinical_wide=73 works/73 abstracts/0 retained full texts; target_phenotype=311 works/310 abstracts/2 retained full texts; target_wide_phenotype=595 works/593 abstracts/5 retained full texts

### NCT06754566 — A Caregiver-Assisted Rehabilitation With Strategy Training (CAR-ST) for Stroke Patients

- Registry/semantic type: `INTERVENTIONAL` / `behavioral`
- Registry dates: first posted `2025-01-01`; completion `2028-12-31` (ESTIMATED)
- Development scope: `not_applicable` / `non_molecular_intervention` (non_molecular_trial_kind; policy `human_therapeutics_v1`)
- Literal registry conditions: Stroke
- Canonical assets: none (non-drug or unresolved)
- Normalized indications: Stroke [HP:0001297, treatment]
- Review queue: indication $.indications[0].concepts[1]=unresolved

### NCT06754579 — Impact of High-Volume Upper Limb Training on Physical and Cognitive Outcomes

- Registry/semantic type: `INTERVENTIONAL` / `exercise`
- Registry dates: first posted `2025-01-01`; completion `2026-12-30` (ESTIMATED)
- Development scope: `not_applicable` / `non_molecular_intervention` (non_molecular_trial_kind; policy `human_therapeutics_v1`)
- Literal registry conditions: Sedentary Behavior
- Canonical assets: none (non-drug or unresolved)
- Normalized indications: none promoted
- Review queue: indication $.indications[0].concepts[0]=unresolved

### NCT06754592 — Role of Dynamic Ultrasound in Assessment of Shoulder Impingement Syndrome

- Registry/semantic type: `OBSERVATIONAL` / `diagnostic`
- Registry dates: first posted `2025-01-01`; completion `2025-06-30` (ESTIMATED)
- Development scope: `not_applicable` / `non_molecular_intervention` (non_molecular_trial_kind; policy `human_therapeutics_v1`)
- Literal registry conditions: Shoulder Impingement Syndrome
- Canonical assets: none (non-drug or unresolved)
- Normalized indications: shoulder impingement syndrome [MONDO:0006968, diagnosis]

### NCT06754605 — A Study to Evaluate the Safety, Tolerability, and Immunogenicity of a Recombinant Respiratory Syncytial Virus Vaccine

- Registry/semantic type: `INTERVENTIONAL` / `vaccine`
- Registry dates: first posted `2025-01-01`; completion `2027-07-30` (ESTIMATED)
- Development scope: `separate` / `vaccine` (vaccine_separate_track; policy `human_therapeutics_v1`)
- Literal registry conditions: Respiratory Syncytial Virus
- Canonical assets: none (non-drug or unresolved)
- Normalized indications: none promoted
- Review queue: asset $.assets[0]=unresolved; indication $.indications[0].concepts[0]=unresolved; pharmacology $.pharmacology[0]=unsupported

### NCT06754618 — The Influences of Single Chamber Vs. Multi-chamber Blood Flow Restriction Cuffs with Bicep Curls

- Registry/semantic type: `INTERVENTIONAL` / `exercise`
- Registry dates: first posted `2025-01-01`; completion `2024-12-20` (ACTUAL)
- Development scope: `not_applicable` / `non_molecular_intervention` (non_molecular_trial_kind; policy `human_therapeutics_v1`)
- Literal registry conditions: Blood Vessel Disease, Muscle Edema
- Canonical assets: none (non-drug or unresolved)
- Normalized indications: none promoted

### NCT06754631 — Efficacy and Safety of Continuous Versus Intermittent Nebulization of Salbutamol in Acute Severe Asthma in Children Under 12 Years of Age

- Registry/semantic type: `INTERVENTIONAL` / `therapeutic_drug`
- Registry dates: first posted `2025-01-01`; completion `2024-09-30` (ACTUAL)
- Development scope: `included` / `human_therapeutic` (all_resolved_assets_in_scope; policy `human_therapeutics_v1`)
- Literal registry conditions: Asthma in Children
- Canonical assets: salbutamol (active_comparator; ChEMBL:CHEMBL714, PubChem CID:2083); salbutamol (registered_intervention; ChEMBL:CHEMBL714, PubChem CID:2083)
- Normalized indications: asthma [MONDO:0004979, treatment]
- Complete structured pharmacology: salbutamol agonizes ADRB2 (ChEMBL mechanism:1338); salbutamol agonizes ADRB2 (ChEMBL mechanism:1351)
- Raw literature candidates: asset_indication_preclinical=360 works/360 abstracts/0 retained full texts; asset_preclinical_wide=2092 works/2073 abstracts/0 retained full texts; target_phenotype=370 works/359 abstracts/2 retained full texts; target_wide_phenotype=855 works/851 abstracts/2 retained full texts
- Review queue: pharmacology $.pharmacology[1]=unsupported

## Interpretation

A literature query hit is a raw candidate, not a target–phenotype assertion and not a passed preclinical test. The later extraction layer must cite exact model, assay, endpoint, result, and reported criterion passages. Missing source abstracts remain explicit rather than being fabricated.

Development scope never deletes raw records. Policy `human_therapeutics_v1` permits literature expansion only for verified human-biology therapeutics, excludes antibiotics and non-human therapeutic targets, routes vaccines to a separate track, and holds unknown target domains unresolved.

GCS/PDF rows remain empty when `PV_GCS_BUCKET` is not configured. The ingestion code uploads only after an explicit rights decision and stores immutable `gs://` object coordinates, not signed URLs.
