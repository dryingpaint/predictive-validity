# Effect sizes v3 — enriched with genome-browser DB

Dataset: `drug_evidence_full_enriched.csv` (1479 programs, resolved n=1339, approved n=544).
Bootstrap 95% CI, 500 draws. Resolved cohort excludes in-development programs.

## Approval-odds effects (resolved cohort)

| Dimension | n covered | exposed → approved | unexposed → approved | OR | 95% CI |
|---|---|---|---|---|---|
| ClinGen Strong/Definitive ≥1 | 285 | 116/233 (50%) | 15/52 (29%) | 2.45 | [1.29, 4.88] |
| Mendelian associations ≥5 | 621 | 70/132 (53%) | 162/489 (33%) | 2.28 | [1.58, 3.36] |
| GWAS significant hits ≥50 | 614 | 95/290 (33%) | 133/324 (41%) | 0.70 | [0.51, 1.00] |
| Open Targets genetic score ≥0.3 | 630 | 219/574 (38%) | 16/56 (29%) | 1.54 | [0.88, 2.99] |
| Tractable — small mol | 648 | 203/564 (36%) | 35/84 (42%) | 0.79 | [0.51, 1.27] |
| Tractable — antibody | 648 | 205/550 (37%) | 33/98 (34%) | 1.17 | [0.75, 1.76] |
| DepMap pan-essential | 618 | 1/27 (4%) | 228/591 (39%) | 0.06 | [0.02, 0.23] |
| DepMap dependent lineages ≥5 | 618 | 12/47 (26%) | 217/571 (38%) | 0.56 | [0.28, 1.01] |
| OT animal model score ≥0.3 | 559 | 195/532 (37%) | 15/27 (56%) | 0.46 | [0.17, 1.03] |
| gnomAD pLI ≥0.9 (LoF-intol.) | 598 | 69/223 (31%) | 147/375 (39%) | 0.69 | [0.49, 1.01] |
| gnomAD LOEUF <0.35 (constrained) | 598 | 32/112 (29%) | 184/486 (38%) | 0.66 | [0.42, 1.02] |
| SIDER ≥5 unique AEs | 451 | 8/16 (50%) | 409/435 (94%) | 0.06 | [0.02, 0.18] |
| OT known-drug score ≥0.3 | 25 | 3/11 (27%) | 2/14 (14%) | 2.25 | [0.26, 19.80] |
| OT overall score ≥0.3 | 646 | 231/617 (37%) | 6/29 (21%) | 2.29 | [0.95, 10.01] |

## Safety failure enrichment (safety_fail vs approved)

n_safety_fail = 22, n_approved = 544

| Metric | safety-fail median | approved median | safety n | appr n |
|---|---|---|---|---|
| gb_gnomad_pli | 0.72139 | 0.01296 | 12 | 216 |
| gb_gnomad_loeuf | 0.565 | 0.711 | 12 | 216 |
| gb_depmap_mean_effect | -0.010612551 | -0.038002037 | 12 | 229 |
| gb_depmap_n_dep_lineages | 0.0 | 0.0 | 12 | 229 |
| gb_clingen_n_strong | 0.0 | 1.0 | 4 | 131 |
| gb_mendelian_n | 2.0 | 3.0 | 12 | 232 |
| gb_gwas_n_sig | 95.0 | 37.0 | 12 | 228 |
| gb_ot_overall_max | 0.66909915 | 0.70344126 | 12 | 237 |
| gb_ot_animal_model_max | 0.53129745 | 0.57696885 | 12 | 210 |
| gb_sider_n_uniq_ae | — | 0.0 | 0 | 417 |

## Efficacy failure enrichment (efficacy_fail vs approved)

n_efficacy_fail = 95

| Metric | eff-fail median | approved median | ef n | appr n |
|---|---|---|---|---|
| gb_ot_genetic_max | 0.78826946 | 0.7447152 | 53 | 235 |
| gb_mendelian_n | 2.0 | 3.0 | 52 | 232 |
| gb_clingen_n_strong | 1.0 | 1.0 | 22 | 131 |
| gb_ot_overall_max | 0.6560718 | 0.70344126 | 57 | 237 |
| gb_ot_animal_model_max | 0.53129745 | 0.57696885 | 45 | 210 |
| gb_ot_known_drug_max | 0.2 | 1.0 | 5 | 5 |
| gb_depmap_mean_effect | -0.016235726 | -0.038002037 | 52 | 229 |
