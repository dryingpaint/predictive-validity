# Coverage matrix + effect sizes
Master dataset: **1479 programs**.
## Outcome distribution
| Outcome | n |
|---|---|
| approved | 544 |
| efficacy_fail | 95 |
| safety_fail | 22 |
| other_fail | 302 |
| phase_complete_no_approval | 376 |
| in_development | 136 |

## D2. Coverage matrix (evidence × outcome slice)
| Category | Dimension | approved | efficacy_fail | safety_fail | other_fail | phase-complete | in-dev |
|---|---|---|---|---|---|---|---|
| A. genetics | Nelson tier | 544/544 (100%) | 16/95 (17%) | 3/22 (14%) | 46/302 (15%) | 53/376 (14%) | 16/136 (12%) |
| A. genetics | Open Targets #associations | 344/544 (63%) | 45/95 (47%) | 11/22 (50%) | 117/302 (39%) | 152/376 (40%) | 43/136 (32%) |
| B. mechanistic biology | lit-derived structural score | 337/544 (62%) | 48/95 (51%) | 13/22 (59%) | 135/302 (45%) | 182/376 (48%) | 50/136 (37%) |
| C. cell-pathway | lit-derived cell score | 337/544 (62%) | 48/95 (51%) | 13/22 (59%) | 135/302 (45%) | 182/376 (48%) | 50/136 (37%) |
| C. cell-pathway | drug-specific cell efficacy | 36/544 (7%) | 0/95 (0%) | 0/22 (0%) | 0/302 (0%) | 0/376 (0%) | 0/136 (0%) |
| D. animal in vivo | lit-derived animal score | 337/544 (62%) | 48/95 (51%) | 13/22 (59%) | 135/302 (45%) | 182/376 (48%) | 50/136 (37%) |
| D. animal in vivo | drug-specific rodent efficacy | 36/544 (7%) | 0/95 (0%) | 0/22 (0%) | 0/302 (0%) | 0/376 (0%) | 0/136 (0%) |
| D. animal in vivo | drug-specific non-rodent efficacy | 36/544 (7%) | 0/95 (0%) | 0/22 (0%) | 0/302 (0%) | 0/376 (0%) | 0/136 (0%) |
| D. animal in vivo | IMPC significant KO phenotypes | 101/544 (19%) | 27/95 (28%) | 4/22 (18%) | 51/302 (17%) | 74/376 (20%) | 23/136 (17%) |
| E. human PD engagement | lit-derived PD score | 337/544 (62%) | 48/95 (51%) | 13/22 (59%) | 135/302 (45%) | 182/376 (48%) | 50/136 (37%) |
| E. human PD engagement | drug-specific target engagement | 36/544 (7%) | 0/95 (0%) | 0/22 (0%) | 0/302 (0%) | 0/376 (0%) | 0/136 (0%) |
| G. chemistry / structure | drug structural biology score | 36/544 (7%) | 0/95 (0%) | 0/22 (0%) | 0/302 (0%) | 0/376 (0%) | 0/136 (0%) |
| H. safety (LoF) | gnomAD LOEUF | 198/544 (36%) | 51/95 (54%) | 12/22 (55%) | 146/302 (48%) | 167/376 (44%) | 46/136 (34%) |
| I. landscape | prior approvals against target | 180/544 (33%) | 43/95 (45%) | 9/22 (41%) | 100/302 (33%) | 143/376 (38%) | 36/136 (26%) |
| I. landscape | prior approvals against family | 0/544 (0%) | 0/95 (0%) | 0/22 (0%) | 0/302 (0%) | 0/376 (0%) | 0/136 (0%) |

## D3. Effect sizes (high vs low evidence, resolved cohort)

`OR > 1`: high evidence → higher approval odds. CI excludes 1 → significant.

| Category | Dimension | n covered | coverage | high→approval | low→approval | OR (95% CI) | note |
|---|---|---|---|---|---|---|---|
| A. genetics | Nelson tier | 659 | 49.2% | 300/388 | 241/271 | 0.42 [0.28, 0.67] |  |
| A. genetics | Open Targets #associations | 669 | 50.0% | 0/0 | 344/669 | — | one arm empty |
| B. mechanistic biology | lit-derived structural score | 715 | 53.4% | 335/711 | 2/4 | 0.89 [0.10, 3.32] |  |
| C. cell-pathway | lit-derived cell score | 715 | 53.4% | 292/617 | 45/98 | 1.06 [0.72, 1.62] |  |
| C. cell-pathway | drug-specific cell efficacy | 36 | 2.7% | 8/8 | 28/28 | — |  |
| D. animal in vivo | lit-derived animal score | 715 | 53.4% | 284/602 | 53/113 | 1.01 [0.67, 1.51] |  |
| D. animal in vivo | drug-specific rodent efficacy | 36 | 2.7% | 11/11 | 25/25 | — |  |
| D. animal in vivo | drug-specific non-rodent efficacy | 36 | 2.7% | 1/1 | 35/35 | — |  |
| D. animal in vivo | IMPC significant KO phenotypes | 257 | 19.2% | 76/209 | 25/48 | 0.53 [0.29, 1.05] |  |
| E. human PD engagement | lit-derived PD score | 715 | 53.4% | 290/544 | 47/171 | 3.01 [2.12, 4.47] |  |
| E. human PD engagement | drug-specific target engagement | 36 | 2.7% | 11/11 | 25/25 | — |  |
| G. chemistry / structure | drug structural biology score | 36 | 2.7% | 4/4 | 32/32 | — |  |
| H. safety (LoF) | gnomAD LOEUF | 574 | 42.9% | 29/108 | 169/466 | 0.65 [0.36, 1.00] |  |
| I. landscape | prior approvals against target | 475 | 35.5% | 115/324 | 65/151 | 0.73 [0.49, 1.09] |  |
| I. landscape | prior approvals against family | 0 | 0.0% | 0/0 | 0/0 | — | underpowered |

## Q4. Efficacy failures — evidence coverage vs approved

For each dimension: what fraction of efficacy-fails vs approvals had (any evidence) and (high evidence).

| Category | Dimension | Eff-fail covered | Eff-fail high | Approved covered | Approved high |
|---|---|---|---|---|---|
| A. genetics | Nelson tier | 16/95 | 11/95 | 544/544 | 300/544 |
| A. genetics | Open Targets #associations | 45/95 | 0/95 | 344/544 | 0/544 |
| B. mechanistic biology | lit-derived structural score | 48/95 | 47/95 | 337/544 | 335/544 |
| C. cell-pathway | lit-derived cell score | 48/95 | 41/95 | 337/544 | 292/544 |
| C. cell-pathway | drug-specific cell efficacy | 0/95 | 0/95 | 36/544 | 8/544 |
| D. animal in vivo | lit-derived animal score | 48/95 | 42/95 | 337/544 | 284/544 |
| D. animal in vivo | drug-specific rodent efficacy | 0/95 | 0/95 | 36/544 | 11/544 |
| D. animal in vivo | drug-specific non-rodent efficacy | 0/95 | 0/95 | 36/544 | 1/544 |
| D. animal in vivo | IMPC significant KO phenotypes | 27/95 | 21/95 | 101/544 | 76/544 |
| E. human PD engagement | lit-derived PD score | 48/95 | 33/95 | 337/544 | 290/544 |
| E. human PD engagement | drug-specific target engagement | 0/95 | 0/95 | 36/544 | 11/544 |
| G. chemistry / structure | drug structural biology score | 0/95 | 0/95 | 36/544 | 4/544 |
| H. safety (LoF) | gnomAD LOEUF | 51/95 | 14/95 | 198/544 | 29/544 |
| I. landscape | prior approvals against target | 43/95 | 27/95 | 180/544 | 115/544 |
| I. landscape | prior approvals against family | 0/95 | 0/95 | 0/544 | 0/544 |

## Q5. Safety failures — LoF safety markers

n_safety_fail = 22, n_approved = 544

| Dimension | safety-fail median | approved median | safety n | approved n |
|---|---|---|---|---|
| H_loeuf | 0.615 | 0.706 | 12 | 198 |
| H_pli | 0.24489 | 0.01296 | 12 | 198 |
| D_impc_n_phenotypes | 16.0 | 5.0 | 4 | 101 |
| I_gene_approved_count | 7.0 | 4.0 | 9 | 180 |
