# Effect sizes — evidence lines × approval
Cohort: 24,706 drug programs (ChEMBL + FDA approvals union), joined to target-level literature scores.
Bucket: line score 2-3 = **high**, 0-1 = **low**. Bootstrap 95% CI (500 draws).

## All programs (incl. preclinical only)

n = 24705, approved = 2112 (8.5%)

| Line | n covered | high → approved | low → approved | OR | 95% CI |
|---|---|---|---|---|---|
| line_b | 2358 | 1282/2334 (55%) | 24/24 (100%) | 0.02 | [0.02, 0.04] |
| line_c | 2358 | 1101/2018 (55%) | 205/340 (60%) | 0.79 | [0.62, 1.01] |
| line_d | 2358 | 1058/1908 (55%) | 248/450 (55%) | 1.01 | [0.81, 1.23] |
| line_e | 2358 | 857/1408 (61%) | 449/950 (47%) | 1.74 | [1.48, 2.07] |

## Reached Phase 1+

n = 5176, approved = 2112 (40.8%)

| Line | n covered | high → approved | low → approved | OR | 95% CI |
|---|---|---|---|---|---|
| line_b | 2358 | 1282/2334 (55%) | 24/24 (100%) | 0.02 | [0.02, 0.04] |
| line_c | 2358 | 1101/2018 (55%) | 205/340 (60%) | 0.79 | [0.63, 1.02] |
| line_d | 2358 | 1058/1908 (55%) | 248/450 (55%) | 1.01 | [0.82, 1.25] |
| line_e | 2358 | 857/1408 (61%) | 449/950 (47%) | 1.74 | [1.44, 2.05] |

## Reached Phase 2 or 3

n = 4746, approved = 2112 (44.5%)

| Line | n covered | high → approved | low → approved | OR | 95% CI |
|---|---|---|---|---|---|
| line_b | 2338 | 1282/2314 (55%) | 24/24 (100%) | 0.03 | [0.02, 0.04] |
| line_c | 2338 | 1101/2000 (55%) | 205/338 (61%) | 0.79 | [0.62, 0.99] |
| line_d | 2338 | 1058/1895 (56%) | 248/443 (56%) | 0.99 | [0.82, 1.22] |
| line_e | 2338 | 857/1398 (61%) | 449/940 (48%) | 1.73 | [1.48, 2.05] |

## Reached Phase 3

n = 3182, approved = 2112 (66.4%)

| Line | n covered | high → approved | low → approved | OR | 95% CI |
|---|---|---|---|---|---|
| line_b | 1820 | 1282/1796 (71%) | 24/24 (100%) | 0.05 | [0.04, 0.08] |
| line_c | 1820 | 1101/1547 (71%) | 205/273 (75%) | 0.82 | [0.61, 1.10] |
| line_d | 1820 | 1058/1466 (72%) | 248/354 (70%) | 1.11 | [0.85, 1.43] |
| line_e | 1820 | 857/1143 (75%) | 449/677 (66%) | 1.52 | [1.21, 1.88] |

## Nelson tier × approval, per slice

| Slice | n_programs | n_approved | n_by_tier | T1+ approved | T0 approved | OR (T1+ vs T0) | 95% CI |
|---|---|---|---|---|---|---|---|
| All programs (incl. preclinical only) | 24705 | 2112 | 1214 | 531/791 (67%) | 240/423 (57%) | 1.56 | [1.21, 1.95] |
| Reached Phase 1+ | 5176 | 2112 | 1198 | 531/782 (68%) | 240/416 (58%) | 1.55 | [1.21, 1.96] |
| Reached Phase 2 or 3 | 4746 | 2112 | 1188 | 531/775 (69%) | 240/413 (58%) | 1.57 | [1.22, 2.05] |
| Reached Phase 3 | 3182 | 2112 | 1008 | 531/664 (80%) | 240/344 (70%) | 1.73 | [1.29, 2.32] |

## Line E (human PD engagement) × Nelson interaction — Phase 2+ cohort

| Line E | Nelson tier | n | approved | rate |
|---|---|---|---|---|
| high | T0 | 283 | 137 | 48% |
| high | T1+ | 615 | 405 | 66% |
| low | T0 | 46 | 31 | 67% |
| low | T1+ | 104 | 81 | 78% |
