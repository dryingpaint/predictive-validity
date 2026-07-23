# Effect sizes — FINAL (comprehensive with presumptive failure classification)

Dataset: `drug_evidence_master_v2_broad.csv` (30,517 programs).

## Outcome_broad distribution

| outcome_broad | n | % |
|---|---|---|
| approved | 544 | 1.8% |
| efficacy_fail | 1,002 | 3.3% |
| safety_fail | 232 | 0.8% |
| commercial_fail | 2,157 | 7.1% |
| enrollment_fail | 609 | 2.0% |
| presumptive_efficacy_fail_ph3 | 4,950 | 16.2% |
| presumptive_fail_ph2 | 5,152 | 16.9% |
| unclassified_termination | 2,725 | 8.9% |
| phase1_only | 12,974 | 42.5% |
| planned_termination | 172 | 0.6% |

## Approval OR — TIGHT cohort (approved vs high-confidence failures)

n = 4544 (approved=544, tight failures=4000)

| Dimension | n covered | exposed → appr | unexposed → appr | OR | 95% CI |
|---|---|---|---|---|---|
| Nelson tier T1+ | 742 | 300/419 (72%) | 241/323 (75%) | 0.86 | [0.61, 1.18] |
| ClinGen Strong/Definitive ≥1 | 457 | 115/362 (32%) | 15/95 (16%) | 2.48 | [1.43, 4.75] |
| Mendelian associations ≥5 | 971 | 70/205 (34%) | 157/766 (20%) | 2.01 | [1.46, 2.74] |
| GWAS significant hits ≥50 | 962 | 92/421 (22%) | 131/541 (24%) | 0.88 | [0.65, 1.21] |
| OT genetic score ≥0.3 | 958 | 212/862 (25%) | 16/96 (17%) | 1.63 | [1.00, 3.09] |
| OT overall score ≥0.5 | 1006 | 202/833 (24%) | 28/173 (16%) | 1.66 | [1.09, 2.60] |
| OT animal model score ≥0.3 | 860 | 191/821 (23%) | 15/39 (38%) | 0.49 | [0.24, 1.00] |
| Tractable — small mol | 1006 | 199/858 (23%) | 31/148 (21%) | 1.14 | [0.76, 1.80] |
| Tractable — antibody | 1006 | 200/846 (24%) | 30/160 (19%) | 1.34 | [0.91, 2.22] |
| DepMap pan-essential | 961 | 1/42 (2%) | 223/919 (24%) | 0.08 | [0.03, 0.28] |
| DepMap ≥5 dep lineages | 961 | 12/91 (13%) | 212/870 (24%) | 0.47 | [0.20, 0.81] |
| gnomAD pLI ≥0.9 | 916 | 68/339 (20%) | 143/577 (25%) | 0.76 | [0.53, 1.03] |
| gnomAD LOEUF <0.35 | 916 | 32/161 (20%) | 179/755 (24%) | 0.80 | [0.51, 1.17] |
| Line C lit high (≥2) | 1056 | 292/918 (32%) | 45/138 (33%) | 0.96 | [0.66, 1.43] |
| Line D lit high (≥2) | 1056 | 284/874 (32%) | 53/182 (29%) | 1.17 | [0.81, 1.69] |
| Line E lit high (≥2) | 1056 | 290/727 (40%) | 47/329 (14%) | 3.98 | [2.80, 6.00] |
| IMPC KO ≥3 phenotypes | 426 | 76/321 (24%) | 25/105 (24%) | 0.99 | [0.60, 1.69] |

## Approval OR — BROAD cohort (approved vs ALL failures incl. silent kills)

n = 14646 (approved=544, all failures=14102)

| Dimension | n covered | exposed → appr | unexposed → appr | OR | 95% CI |
|---|---|---|---|---|---|
| Nelson tier T1+ | 941 | 300/547 (55%) | 241/394 (61%) | 0.77 | [0.57, 1.00] |
| ClinGen Strong/Definitive ≥1 | 756 | 115/604 (19%) | 15/152 (10%) | 2.15 | [1.30, 4.36] |
| Mendelian associations ≥5 | 1842 | 70/325 (22%) | 157/1517 (10%) | 2.38 | [1.71, 3.26] |
| GWAS significant hits ≥50 | 1829 | 92/806 (11%) | 131/1023 (13%) | 0.88 | [0.65, 1.17] |
| OT genetic score ≥0.3 | 1856 | 212/1618 (13%) | 16/238 (7%) | 2.09 | [1.35, 3.80] |
| OT overall score ≥0.5 | 1931 | 202/1570 (13%) | 28/361 (8%) | 1.76 | [1.20, 2.83] |
| OT animal model score ≥0.3 | 1616 | 191/1550 (12%) | 15/66 (23%) | 0.48 | [0.26, 0.96] |
| Tractable — small mol | 1931 | 199/1648 (12%) | 31/283 (11%) | 1.12 | [0.74, 1.72] |
| Tractable — antibody | 1931 | 200/1621 (12%) | 30/310 (10%) | 1.31 | [0.88, 2.04] |
| DepMap pan-essential | 1826 | 1/63 (2%) | 223/1763 (13%) | 0.11 | [0.05, 0.40] |
| DepMap ≥5 dep lineages | 1826 | 12/133 (9%) | 212/1693 (13%) | 0.69 | [0.33, 1.14] |
| gnomAD pLI ≥0.9 | 1749 | 68/621 (11%) | 143/1128 (13%) | 0.85 | [0.60, 1.13] |
| gnomAD LOEUF <0.35 | 1749 | 32/286 (11%) | 179/1463 (12%) | 0.90 | [0.58, 1.30] |
| Line C lit high (≥2) | 1932 | 292/1656 (18%) | 45/276 (16%) | 1.10 | [0.81, 1.61] |
| Line D lit high (≥2) | 1932 | 284/1585 (18%) | 53/347 (15%) | 1.21 | [0.88, 1.72] |
| Line E lit high (≥2) | 1932 | 290/1245 (23%) | 47/687 (7%) | 4.14 | [3.00, 5.62] |
| IMPC KO ≥3 phenotypes | 795 | 76/619 (12%) | 25/176 (14%) | 0.85 | [0.52, 1.54] |

## Efficacy failures — full cohort (efficacy_fail + presumptive Ph3)

n_efficacy_all = 5952, n_approved = 544

| Metric | ef-all median | approved median | ef-all n | appr n |
|---|---|---|---|---|
| gb_ot_genetic_max | 0.7447152 | 0.74572486 | 731 | 228 |
| gb_ot_overall_max | 0.65 | 0.71237946 | 759 | 230 |
| gb_ot_animal_model_max | 0.60674524 | 0.57696885 | 629 | 206 |
| gb_mendelian_n | 2.0 | 3.0 | 720 | 227 |
| gb_clingen_n_strong | 1.0 | 1.0 | 282 | 130 |
| gb_depmap_mean_effect | -0.010612551 | -0.038002037 | 713 | 224 |
| line_c_lit | 2.0 | 2.0 | 720 | 337 |
| line_d_lit | 2.0 | 2.0 | 720 | 337 |
| line_e_lit | 2.0 | 3.0 | 720 | 337 |
| impc_n_phenotypes | 5.0 | 5.0 | 307 | 101 |

## Safety failures

n_safety_fail = 232, n_approved = 544

| Metric | safety-fail median | approved median | safety n | appr n |
|---|---|---|---|---|
| gb_gnomad_pli | 0.66126 | 0.01296 | 34 | 211 |
| gb_gnomad_loeuf | 0.565 | 0.706 | 34 | 211 |
| gb_depmap_mean_effect | -0.035870247 | -0.038002037 | 35 | 224 |
| gb_clingen_n_strong | 1.0 | 1.0 | 16 | 130 |
| gb_mendelian_n | 2.0 | 3.0 | 35 | 227 |
| gb_gwas_n_sig | 60.0 | 37.0 | 34 | 223 |
| gb_ot_overall_max | 0.65 | 0.71237946 | 36 | 230 |
| gb_ot_animal_model_max | 0.59162176 | 0.57696885 | 33 | 206 |
| impc_n_phenotypes | 7.0 | 5.0 | 17 | 101 |

## Q4 — evidence coverage delta (ALL efficacy failures vs approved)

Uses `efficacy_fail + presumptive_efficacy_fail_ph3` as full efficacy cohort.

| Dimension | ef-all high | approved high | delta |
|---|---|---|---|
| Nelson tier T1+ | 64% | 55% | -9pp |
| ClinGen Strong/Definitive ≥1 | 79% | 88% | +9pp |
| Mendelian associations ≥5 | 16% | 31% | +15pp |
| GWAS significant hits ≥50 | 44% | 41% | -3pp |
| OT genetic score ≥0.3 | 85% | 93% | +8pp |
| OT overall score ≥0.5 | 84% | 88% | +4pp |
| OT animal model score ≥0.3 | 96% | 93% | -4pp |
| Tractable — small mol | 87% | 87% | -1pp |
| Tractable — antibody | 84% | 87% | +3pp |
| DepMap pan-essential | 4% | 0% | -3pp |
| DepMap ≥5 dep lineages | 6% | 5% | -1pp |
| gnomAD pLI ≥0.9 | 37% | 32% | -4pp |
| gnomAD LOEUF <0.35 | 18% | 15% | -3pp |
| Line C lit high (≥2) | 85% | 87% | +2pp |
| Line D lit high (≥2) | 83% | 84% | +1pp |
| Line E lit high (≥2) | 64% | 86% | +22pp |
| IMPC KO ≥3 phenotypes | 77% | 75% | -1pp |

## Q5 — evidence coverage delta (safety failures vs approved)

| Dimension | safety-fail high | approved high | delta |
|---|---|---|---|
| Nelson tier T1+ | 60% | 55% | -5pp |
| ClinGen Strong/Definitive ≥1 | 50% | 88% | +38pp |
| Mendelian associations ≥5 | 17% | 31% | +14pp |
| GWAS significant hits ≥50 | 59% | 41% | -18pp |
| OT genetic score ≥0.3 | 94% | 93% | -1pp |
| OT overall score ≥0.5 | 78% | 88% | +10pp |
| OT animal model score ≥0.3 | 100% | 93% | -7pp |
| Tractable — small mol | 83% | 87% | +3pp |
| Tractable — antibody | 89% | 87% | -2pp |
| DepMap pan-essential | 3% | 0% | -2pp |
| DepMap ≥5 dep lineages | 11% | 5% | -6pp |
| gnomAD pLI ≥0.9 | 35% | 32% | -3pp |
| gnomAD LOEUF <0.35 | 9% | 15% | +6pp |
| Line C lit high (≥2) | 92% | 87% | -6pp |
| Line D lit high (≥2) | 87% | 84% | -3pp |
| Line E lit high (≥2) | 67% | 86% | +19pp |
| IMPC KO ≥3 phenotypes | 82% | 75% | -7pp |
