# Effect sizes — comprehensive (30,517-program cohort)

Dataset: `drug_evidence_master_v2_enriched.csv` — every industry Phase 1-3 drug 2015-2025.

## Outcome distribution (all 30,517 programs)

| Outcome | n | % |
|---|---|---|
| approved | 544 | 1.8% |
| efficacy_fail | 1,002 | 3.3% |
| safety_fail | 232 | 0.8% |
| commercial_fail | 2,157 | 7.1% |
| enrollment_fail | 609 | 2.0% |
| other_fail | 2,725 | 8.9% |
| phase_complete_no_approval | 10,102 | 33.1% |
| phase1_complete_no_advance | 12,974 | 42.5% |
| planned_termination | 172 | 0.6% |
| in_development | 0 | 0.0% |
| unknown | 0 | 0.0% |

## Approval OR — Resolved (all outcomes with a decision)

n = 30345

| Dimension | n covered | exposed → appr | unexposed → appr | OR | 95% CI |
|---|---|---|---|---|---|
| Nelson tier T1+ | 1164 | 300/706 (42%) | 241/458 (53%) | 0.67 | [0.53, 0.85] |
| ClinGen Strong/Definitive ≥1 | 1099 | 115/871 (13%) | 15/228 (7%) | 2.16 | [1.30, 4.47] |
| Mendelian associations ≥5 | 2618 | 70/511 (14%) | 157/2107 (7%) | 1.97 | [1.46, 2.62] |
| GWAS significant hits ≥50 | 2604 | 92/1161 (8%) | 131/1443 (9%) | 0.86 | [0.65, 1.16] |
| OT genetic score ≥0.3 | 2652 | 212/2307 (9%) | 16/345 (5%) | 2.08 | [1.31, 3.98] |
| OT overall score ≥0.3 | 2747 | 225/2627 (9%) | 5/120 (4%) | 2.15 | [1.07, 10.28] |
| OT animal model score ≥0.3 | 2291 | 191/2210 (9%) | 15/81 (19%) | 0.42 | [0.24, 0.85] |
| Tractable — small mol | 2747 | 199/2344 (8%) | 31/403 (8%) | 1.11 | [0.76, 1.76] |
| Tractable — antibody | 2747 | 200/2296 (9%) | 30/451 (7%) | 1.34 | [0.89, 2.08] |
| DepMap pan-essential | 2596 | 1/84 (1%) | 223/2512 (9%) | 0.12 | [0.05, 0.45] |
| DepMap ≥5 dep lineages | 2596 | 12/188 (6%) | 212/2408 (9%) | 0.71 | [0.33, 1.22] |
| gnomAD pLI ≥0.9 | 2491 | 68/911 (7%) | 143/1580 (9%) | 0.81 | [0.60, 1.11] |
| gnomAD LOEUF <0.35 | 2491 | 32/415 (8%) | 179/2076 (9%) | 0.89 | [0.55, 1.23] |
| Line B lit high (≥2) | 2680 | 335/2664 (13%) | 2/16 (12%) | 1.01 | [0.31, 5.09] |
| Line C lit high (≥2) | 2680 | 292/2295 (13%) | 45/385 (12%) | 1.10 | [0.80, 1.68] |
| Line D lit high (≥2) | 2680 | 284/2195 (13%) | 53/485 (11%) | 1.21 | [0.89, 1.77] |
| Line E lit high (≥2) | 2680 | 290/1697 (17%) | 47/983 (5%) | 4.10 | [2.97, 5.84] |
| IMPC KO ≥3 phenotypes | 1110 | 76/851 (9%) | 25/259 (10%) | 0.92 | [0.59, 1.64] |
| Family precedent ≥2 approvals | 2197 | 0/0 | 180/2197 | — |  |
| Gene prior approvals ≥1 | 2197 | 180/2197 | 0/0 | — |  |

## Approval OR — Phase 2+ (reached efficacy testing)

n = 14429

| Dimension | n covered | exposed → appr | unexposed → appr | OR | 95% CI |
|---|---|---|---|---|---|
| Nelson tier T1+ | 918 | 271/542 (50%) | 221/376 (59%) | 0.70 | [0.55, 0.91] |
| ClinGen Strong/Definitive ≥1 | 809 | 106/634 (17%) | 15/175 (9%) | 2.14 | [1.24, 4.03] |
| Mendelian associations ≥5 | 1974 | 62/345 (18%) | 144/1629 (9%) | 2.26 | [1.66, 3.16] |
| GWAS significant hits ≥50 | 1962 | 83/851 (10%) | 120/1111 (11%) | 0.89 | [0.65, 1.19] |
| OT genetic score ≥0.3 | 1990 | 191/1728 (11%) | 16/262 (6%) | 1.91 | [1.15, 3.58] |
| OT overall score ≥0.3 | 2068 | 204/1974 (10%) | 5/94 (5%) | 2.05 | [0.98, 9.20] |
| OT animal model score ≥0.3 | 1727 | 172/1655 (10%) | 15/72 (21%) | 0.44 | [0.26, 0.87] |
| Tractable — small mol | 2068 | 180/1769 (10%) | 29/299 (10%) | 1.05 | [0.70, 1.61] |
| Tractable — antibody | 2068 | 181/1744 (10%) | 28/324 (9%) | 1.22 | [0.83, 1.93] |
| DepMap pan-essential | 1958 | 1/63 (2%) | 202/1895 (11%) | 0.14 | [0.06, 0.52] |
| DepMap ≥5 dep lineages | 1958 | 9/132 (7%) | 194/1826 (11%) | 0.62 | [0.23, 1.11] |
| gnomAD pLI ≥0.9 | 1881 | 56/657 (9%) | 134/1224 (11%) | 0.76 | [0.54, 1.01] |
| gnomAD LOEUF <0.35 | 1881 | 27/296 (9%) | 163/1585 (10%) | 0.88 | [0.56, 1.33] |
| Line B lit high (≥2) | 2050 | 301/2039 (15%) | 1/11 (9%) | 1.73 | [0.37, 5.43] |
| Line C lit high (≥2) | 2050 | 257/1755 (15%) | 45/295 (15%) | 0.95 | [0.70, 1.31] |
| Line D lit high (≥2) | 2050 | 254/1683 (15%) | 48/367 (13%) | 1.18 | [0.86, 1.62] |
| Line E lit high (≥2) | 2050 | 260/1306 (20%) | 42/744 (6%) | 4.15 | [3.07, 5.82] |
| IMPC KO ≥3 phenotypes | 836 | 69/652 (11%) | 21/184 (11%) | 0.92 | [0.54, 1.62] |
| Family precedent ≥2 approvals | 1672 | 0/0 | 162/1672 | — |  |
| Gene prior approvals ≥1 | 1672 | 162/1672 | 0/0 | — |  |

## Approval OR — Phase 3+ (pivotal-stage cohort)

n = 7077

| Dimension | n covered | exposed → appr | unexposed → appr | OR | 95% CI |
|---|---|---|---|---|---|
| Nelson tier T1+ | 659 | 243/403 (60%) | 190/256 (74%) | 0.53 | [0.37, 0.72] |
| ClinGen Strong/Definitive ≥1 | 487 | 91/378 (24%) | 13/109 (12%) | 2.34 | [1.34, 4.89] |
| Mendelian associations ≥5 | 1124 | 53/211 (25%) | 124/913 (14%) | 2.13 | [1.45, 3.01] |
| GWAS significant hits ≥50 | 1113 | 72/485 (15%) | 102/628 (16%) | 0.90 | [0.64, 1.20] |
| OT genetic score ≥0.3 | 1135 | 163/978 (17%) | 15/157 (10%) | 1.89 | [1.10, 3.72] |
| OT overall score ≥0.3 | 1173 | 176/1138 (15%) | 4/35 (11%) | 1.42 | [0.61, 6.87] |
| OT animal model score ≥0.3 | 992 | 146/946 (15%) | 15/46 (33%) | 0.38 | [0.20, 0.74] |
| Tractable — small mol | 1173 | 155/1036 (15%) | 25/137 (18%) | 0.79 | [0.51, 1.30] |
| Tractable — antibody | 1173 | 156/995 (16%) | 24/178 (13%) | 1.19 | [0.77, 1.84] |
| DepMap pan-essential | 1116 | 1/31 (3%) | 173/1085 (16%) | 0.18 | [0.07, 0.65] |
| DepMap ≥5 dep lineages | 1116 | 7/73 (10%) | 167/1043 (16%) | 0.56 | [0.21, 0.99] |
| gnomAD pLI ≥0.9 | 1078 | 41/391 (10%) | 123/687 (18%) | 0.54 | [0.36, 0.77] |
| gnomAD LOEUF <0.35 | 1078 | 19/183 (10%) | 145/895 (16%) | 0.60 | [0.34, 0.95] |
| Line B lit high (≥2) | 1217 | 259/1207 (21%) | 1/10 (10%) | 2.46 | [0.58, 7.70] |
| Line C lit high (≥2) | 1217 | 220/1044 (21%) | 40/173 (23%) | 0.89 | [0.61, 1.32] |
| Line D lit high (≥2) | 1217 | 217/996 (22%) | 43/221 (19%) | 1.15 | [0.78, 1.71] |
| Line E lit high (≥2) | 1217 | 228/848 (27%) | 32/369 (9%) | 3.87 | [2.64, 5.86] |
| IMPC KO ≥3 phenotypes | 445 | 61/348 (18%) | 15/97 (15%) | 1.16 | [0.68, 2.30] |
| Family precedent ≥2 approvals | 1056 | 0/0 | 138/1056 | — |  |
| Gene prior approvals ≥1 | 1056 | 138/1056 | 0/0 | — |  |

## Efficacy-failure enrichment (efficacy_fail vs approved)

n_efficacy_fail = 1002, n_approved = 544

| Metric | eff-fail median | approved median | eff-fail n | appr n |
|---|---|---|---|---|
| gb_ot_genetic_max | 0.7303158 | 0.74572486 | 266 | 228 |
| gb_ot_overall_max | 0.65 | 0.71237946 | 283 | 230 |
| gb_ot_known_drug_max | 0.2 | 0.0 | 10 | 3 |
| gb_ot_animal_model_max | 0.5611455 | 0.57696885 | 232 | 206 |
| gb_mendelian_n | 2.0 | 3.0 | 273 | 227 |
| gb_clingen_n_strong | 1.0 | 1.0 | 122 | 130 |
| gb_gwas_n_sig | 39.0 | 37.0 | 272 | 223 |
| gb_depmap_mean_effect | -0.010612551 | -0.038002037 | 269 | 224 |
| line_c_lit | 2.0 | 2.0 | 255 | 337 |
| line_d_lit | 2.0 | 2.0 | 255 | 337 |
| line_e_lit | 2.0 | 3.0 | 255 | 337 |
| impc_n_phenotypes | 5.0 | 5.0 | 134 | 101 |

## Safety-failure enrichment (safety_fail vs approved)

n_safety_fail = 232, n_approved = 544

| Metric | safety-fail median | approved median | safety n | appr n |
|---|---|---|---|---|
| gb_gnomad_pli | 0.66126 | 0.01296 | 34 | 211 |
| gb_gnomad_loeuf | 0.565 | 0.706 | 34 | 211 |
| gb_depmap_mean_effect | -0.035870247 | -0.038002037 | 35 | 224 |
| gb_depmap_n_dep_lineages | 0.0 | 0.0 | 35 | 224 |
| gb_clingen_n_strong | 1.0 | 1.0 | 16 | 130 |
| gb_mendelian_n | 2.0 | 3.0 | 35 | 227 |
| gb_gwas_n_sig | 60.0 | 37.0 | 34 | 223 |
| gb_ot_overall_max | 0.65 | 0.71237946 | 36 | 230 |
| gb_ot_animal_model_max | 0.59162176 | 0.57696885 | 33 | 206 |
| impc_n_phenotypes | 7.0 | 5.0 | 17 | 101 |

## Q4 — evidence-coverage delta between efficacy failures and approvals

For each dimension: **fraction with high evidence** in efficacy-failures vs approvals.

| Dimension | eff-fail high | approved high | delta |
|---|---|---|---|
| Nelson tier T1+ | 51% | 55% | +5pp |
| ClinGen Strong/Definitive ≥1 | 79% | 88% | +10pp |
| Mendelian associations ≥5 | 16% | 31% | +14pp |
| GWAS significant hits ≥50 | 43% | 41% | -2pp |
| OT genetic score ≥0.3 | 88% | 93% | +5pp |
| OT overall score ≥0.3 | 96% | 98% | +2pp |
| OT animal model score ≥0.3 | 95% | 93% | -3pp |
| Tractable — small mol | 86% | 87% | +1pp |
| Tractable — antibody | 81% | 87% | +6pp |
| DepMap pan-essential | 7% | 0% | -7pp |
| DepMap ≥5 dep lineages | 11% | 5% | -6pp |
| gnomAD pLI ≥0.9 | 37% | 32% | -5pp |
| gnomAD LOEUF <0.35 | 18% | 15% | -3pp |
| Line B lit high (≥2) | 98% | 99% | +1pp |
| Line C lit high (≥2) | 87% | 87% | -0pp |
| Line D lit high (≥2) | 86% | 84% | -2pp |
| Line E lit high (≥2) | 61% | 86% | +25pp |
| IMPC KO ≥3 phenotypes | 74% | 75% | +1pp |
| Family precedent ≥2 approvals | 0% | 0% | +0pp |
| Gene prior approvals ≥1 | 100% | 100% | +0pp |

## Q5 — evidence-coverage delta between safety failures and approvals

| Dimension | safety-fail high | approved high | delta |
|---|---|---|---|
| Nelson tier T1+ | 60% | 55% | -5pp |
| ClinGen Strong/Definitive ≥1 | 50% | 88% | +38pp |
| Mendelian associations ≥5 | 17% | 31% | +14pp |
| GWAS significant hits ≥50 | 59% | 41% | -18pp |
| OT genetic score ≥0.3 | 94% | 93% | -1pp |
| OT overall score ≥0.3 | 94% | 98% | +3pp |
| OT animal model score ≥0.3 | 100% | 93% | -7pp |
| Tractable — small mol | 83% | 87% | +3pp |
| Tractable — antibody | 89% | 87% | -2pp |
| DepMap pan-essential | 3% | 0% | -2pp |
| DepMap ≥5 dep lineages | 11% | 5% | -6pp |
| gnomAD pLI ≥0.9 | 35% | 32% | -3pp |
| gnomAD LOEUF <0.35 | 9% | 15% | +6pp |
| Line B lit high (≥2) | 100% | 99% | -1pp |
| Line C lit high (≥2) | 92% | 87% | -6pp |
| Line D lit high (≥2) | 87% | 84% | -3pp |
| Line E lit high (≥2) | 67% | 86% | +19pp |
| IMPC KO ≥3 phenotypes | 82% | 75% | -7pp |
| Family precedent ≥2 approvals | 0% | 0% | +0pp |
| Gene prior approvals ≥1 | 100% | 100% | +0pp |
