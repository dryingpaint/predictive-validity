# Robustness checks (written by `lessons.py robust`)

## Engagement held, by class outcome

Engagement headline matched in 40 of 78 approved classes and 43 of 88 never-approved classes (Fisher p = 0.88). Among the 83 tiles with engagement held, efficacy was contradicted in 18 of 43 never-approved and 1 of 40 approved classes.

## Efficacy contradicted among tiles with engagement held, by readout tier (Wilson 95 %)

| tier | contradicted / n | share | 95 % |
|---|---|---|---|
| Direct (occupancy, free target) | 7/21 | 0.33 | 0.17-0.55 |
| Proximal (the target's product) | 5/31 | 0.16 | 0.07-0.33 |
| Downstream biomarker | 6/29 | 0.21 | 0.10-0.38 |

Chi-square tier x contradicted p = 0.33; direct vs the rest, Fisher p = 0.23. The tier is the headline engagement track's. With the best tier among a tile's matched engagement tracks instead:

- Direct (occupancy, free target): 8/24 = 0.33 (0.18-0.53)
- Proximal (the target's product): 5/30 = 0.17 (0.07-0.34)
- Downstream biomarker: 5/26 = 0.19 (0.09-0.38)
- chi-square p = 0.31

Direct-tier tiles outside neurology and psychiatry: 6 of 19 contradicted; non-direct outside: 10 of 57.

## Sensitivity: the drafters' statuses instead of the adjudicated ones

Engagement held in 99 tiles (adjudicated: 83); efficacy contradicted among them in 19 (adjudicated: 19). Compared safety contradictions: 112 (adjudicated: 114), 110 in common.

## Safety packages that serve more than one tile

127 typed contradictions on 107 model systems; systems in more than one tile: `cyno-monkey-ro` (3 tiles); `cynomolgus-toxicology` (2 tiles); `ganetespib-mouse-tox` (2 tiles); `pamiparib-mda-mb-436-xenograft` (2 tiles); `rat-dog-glp-tox` (2 tiles). Harm rows: 157 by track, 137 unique (system, harm, type); the figure counts the unique rows.

## Second, blind coder on the safety typing

114 rows typed independently from the entry text (`safety_types_coder1.csv`, the first coding as written; `safety_types_coder2.csv`, the blind second). Type: 107 agree, kappa 0.904. Primary harm class: 107 agree, kappa 0.932; 113 share at least one harm class. Disagreements on type (coder 1 / coder 2 -> resolved in `safety_types.csv`):

- hepatitis-c-virus-infection-hcv-ns5b-nucleotide-inhibitors / `polrmt-mito-panel-retro`: stated_safe / silent -> stated_safe
- primary-biliary-cholangitis-nr1h4-agonists / `mdr2-ko-mouse`: silent / no_comparison -> no_comparison
- prostate-cancer-folh1-directed-depleters / `human-smg-tissue-autoradiography`: stated_safe / not_showable -> stated_safe
- type-1-diabetes-mellitus-slc5a2-inhibitors / `stz-rat`: silent / stated_safe -> stated_safe
- type-2-diabetes-mellitus-gcgr-glp1r-agonists / `cyno-monkey`: stated_safe / silent -> silent
- hodgkins-lymphoma-anti-pdcd1-antibodies / `nivolumab-cyno-tox`: silent / stated_safe -> silent
- mantle-cell-lymphoma-btk-inhibitors / `ibrutinib-gl-tox-rat-dog`: silent / stated_safe -> silent
