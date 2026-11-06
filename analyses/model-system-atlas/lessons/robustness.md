# Robustness checks (written by `lessons.py robust`)

## Engagement held, by class outcome

Engagement headline matched in 50 of 53 approved classes and 55 of 66 never-approved classes (Fisher p = 0.09). Among the 105 tiles with engagement held, efficacy was contradicted in 23 of 55 never-approved and 1 of 50 approved classes.

## Efficacy contradicted among tiles with engagement held, by readout tier (Wilson 95 %)

| tier | contradicted / n | share | 95 % |
|---|---|---|---|
| Direct (occupancy, free target) | 9/27 | 0.33 | 0.19-0.52 |
| Proximal (the target's product) | 8/39 | 0.20 | 0.11-0.35 |
| Downstream biomarker | 7/37 | 0.19 | 0.10-0.34 |

Chi-square tier x contradicted p = 0.35; direct vs the rest, Fisher p = 0.18. The tier is the headline engagement track's. With the best tier among a tile's matched engagement tracks instead:

- Direct (occupancy, free target): 10/33 = 0.30 (0.17-0.47)
- Proximal (the target's product): 8/38 = 0.21 (0.11-0.36)
- Downstream biomarker: 6/32 = 0.19 (0.09-0.35)
- chi-square p = 0.50

Direct-tier tiles outside neurology and psychiatry: 7 of 22 contradicted; non-direct outside: 13 of 74.

## Sensitivity: the drafters' statuses instead of the adjudicated ones

Engagement held in 103 tiles (adjudicated: 105); efficacy contradicted among them in 25 (adjudicated: 24). Compared safety contradictions: 78 (adjudicated: 76), 71 in common.

## Safety packages that serve more than one tile

72 typed contradictions on 68 model systems; systems in more than one tile: `cyno-monkey-ro` (3 tiles); `cynomolgus-toxicology` (2 tiles); `pamiparib-mda-mb-436-xenograft` (2 tiles). Harm rows: 89 by track, 86 unique (system, harm, type); the figure counts the unique rows.

## Second, blind coder on the safety typing

76 rows typed independently from the entry text (`safety_types_coder1.csv`, the first coding as written; `safety_types_coder2.csv`, the blind second). Type: 70 agree, kappa 0.873. Primary harm class: 71 agree, kappa 0.927; 76 share at least one harm class. Disagreements on type (coder 1 / coder 2 -> resolved in `safety_types.csv`):

- hepatitis-c-virus-infection-hcv-ns5b-nucleotide-inhibitors / `polrmt-mito-panel-retro`: stated_safe / silent -> stated_safe
- interstitial-cystitis-anti-ngf-antibodies / `anti-ngf-3species-tox`: stated_safe / silent -> stated_safe
- primary-biliary-cholangitis-nr1h4-agonists / `mdr2-ko-mouse`: silent / no_comparison -> no_comparison
- prostate-cancer-folh1-directed-depleters / `human-smg-tissue-autoradiography`: stated_safe / not_showable -> stated_safe
- type-1-diabetes-mellitus-slc5a2-inhibitors / `stz-rat`: silent / stated_safe -> stated_safe
- type-2-diabetes-mellitus-gcgr-glp1r-agonists / `cyno-monkey`: stated_safe / silent -> silent
