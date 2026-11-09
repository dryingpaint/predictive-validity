# Robustness checks (written by `lessons.py robust`)

## Engagement held, by class outcome

Engagement headline matched in 73 of 78 approved classes and 73 of 88 never-approved classes (Fisher p = 0.05). Among the 146 tiles with engagement held, efficacy was contradicted in 29 of 73 never-approved and 6 of 73 approved classes.

## Efficacy contradicted among tiles with engagement held, by readout tier (Wilson 95 %)

| tier | contradicted / n | share | 95 % |
|---|---|---|---|
| Direct (occupancy, free target) | 14/40 | 0.35 | 0.22-0.51 |
| Proximal (the target's product) | 10/55 | 0.18 | 0.10-0.30 |
| Downstream biomarker | 11/49 | 0.22 | 0.13-0.36 |

Chi-square tier x contradicted p = 0.16; direct vs the rest, Fisher p = 0.08. The tier is the headline engagement track's. With the best tier among a tile's matched engagement tracks instead:

- Direct (occupancy, free target): 15/47 = 0.32 (0.20-0.46)
- Proximal (the target's product): 10/54 = 0.18 (0.10-0.31)
- Downstream biomarker: 10/43 = 0.23 (0.13-0.38)
- chi-square p = 0.29

Direct-tier tiles outside neurology and psychiatry: 11 of 35 contradicted; non-direct outside: 18 of 98.

## Sensitivity: the drafters' statuses instead of the adjudicated ones

Engagement held in 146 tiles (adjudicated: 146); efficacy contradicted among them in 34 (adjudicated: 35). Compared safety contradictions: 100 (adjudicated: 100), 92 in common.

## Safety packages that serve more than one tile

96 typed contradictions on 92 model systems; systems in more than one tile: `cyno-monkey-ro` (3 tiles); `cynomolgus-toxicology` (2 tiles); `pamiparib-mda-mb-436-xenograft` (2 tiles). Harm rows: 120 by track, 117 unique (system, harm, type); the figure counts the unique rows.

## Second, blind coder on the safety typing

100 rows typed independently from the entry text (`safety_types_coder1.csv`, the first coding as written; `safety_types_coder2.csv`, the blind second). Type: 92 agree, kappa 0.874. Primary harm class: 94 agree, kappa 0.933; 100 share at least one harm class. Disagreements on type (coder 1 / coder 2 -> resolved in `safety_types.csv`):

- hepatitis-c-virus-infection-hcv-ns5b-nucleotide-inhibitors / `polrmt-mito-panel-retro`: stated_safe / silent -> stated_safe
- interstitial-cystitis-anti-ngf-antibodies / `anti-ngf-3species-tox`: stated_safe / silent -> stated_safe
- primary-biliary-cholangitis-nr1h4-agonists / `mdr2-ko-mouse`: silent / no_comparison -> no_comparison
- prostate-cancer-folh1-directed-depleters / `human-smg-tissue-autoradiography`: stated_safe / not_showable -> stated_safe
- type-1-diabetes-mellitus-slc5a2-inhibitors / `stz-rat`: silent / stated_safe -> stated_safe
- type-2-diabetes-mellitus-gcgr-glp1r-agonists / `cyno-monkey`: stated_safe / silent -> silent
- hodgkins-lymphoma-anti-pdcd1-antibodies / `nivolumab-cyno-tox`: silent / stated_safe -> silent
- mantle-cell-lymphoma-btk-inhibitors / `ibrutinib-gl-tox-rat-dog`: silent / stated_safe -> silent
