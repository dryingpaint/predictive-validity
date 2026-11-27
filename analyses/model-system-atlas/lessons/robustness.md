# Robustness checks (written by `lessons.py robust`)

## Engagement held, by class outcome

Engagement headline matched in 37 of 78 approved classes and 41 of 88 never-approved classes (Fisher p = 1.00). Among the 78 tiles with engagement held, efficacy was contradicted in 19 of 41 never-approved and 2 of 37 approved classes.

## Efficacy contradicted among tiles with engagement held, by readout tier (Wilson 95 %)

| tier | contradicted / n | share | 95 % |
|---|---|---|---|
| Direct (occupancy, free target) | 8/21 | 0.38 | 0.21-0.59 |
| Proximal (the target's product) | 5/27 | 0.18 | 0.08-0.37 |
| Downstream biomarker | 6/28 | 0.21 | 0.10-0.40 |

Chi-square tier x contradicted p = 0.26; direct vs the rest, Fisher p = 0.25. The tier is the headline engagement track's. With the best tier among a tile's matched engagement tracks instead:

- Direct (occupancy, free target): 9/24 = 0.38 (0.21-0.57)
- Proximal (the target's product): 5/26 = 0.19 (0.09-0.38)
- Downstream biomarker: 5/25 = 0.20 (0.09-0.39)
- chi-square p = 0.25

Direct-tier tiles outside neurology and psychiatry: 7 of 19 contradicted; non-direct outside: 11 of 52.

## Sensitivity: the drafters' statuses instead of the adjudicated ones

Engagement held in 96 tiles (adjudicated: 78); efficacy contradicted among them in 20 (adjudicated: 21). Compared safety contradictions: 112 (adjudicated: 114), 111 in common.

## Safety packages that serve more than one tile

127 typed contradictions on 108 model systems; systems in more than one tile: `cyno-monkey-ro` (3 tiles); `cynomolgus-toxicology` (2 tiles); `ganetespib-mouse-tox` (2 tiles); `pamiparib-mda-mb-436-xenograft` (2 tiles); `rat-dog-glp-tox` (2 tiles). Harm rows: 157 by track, 139 unique (system, harm, type); the figure counts the unique rows.

## Second, blind coder on the safety typing

113 rows typed independently from the entry text (`safety_types_coder1.csv`, the first coding as written; `safety_types_coder2.csv`, the blind second). Type: 107 agree, kappa 0.917. Primary harm class: 107 agree, kappa 0.941; 112 share at least one harm class. Disagreements on type (coder 1 / coder 2 -> resolved in `safety_types.csv`):

- hepatitis-c-virus-infection-hcv-ns5b-nucleotide-inhibitors / `polrmt-mito-panel-retro`: stated_safe / silent -> stated_safe
- prostate-cancer-folh1-directed-depleters / `human-smg-tissue-autoradiography`: stated_safe / not_showable -> stated_safe
- type-1-diabetes-mellitus-slc5a2-inhibitors / `stz-rat`: silent / stated_safe -> stated_safe
- type-2-diabetes-mellitus-gcgr-glp1r-agonists / `cyno-monkey`: stated_safe / silent -> silent
- hodgkins-lymphoma-anti-pdcd1-antibodies / `nivolumab-cyno-tox`: silent / stated_safe -> silent
- mantle-cell-lymphoma-btk-inhibitors / `ibrutinib-gl-tox-rat-dog`: silent / stated_safe -> silent
