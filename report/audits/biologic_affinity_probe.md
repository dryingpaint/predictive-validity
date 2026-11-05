# Biologic potency: feasibility probe (2026-11-05)

The molecule category scores potency for small molecules only, from ChEMBL. This probe asked whether a
potency line could be added for biologics, so that antibodies and proteins are not left without one.

**ChEMBL holds none.** Of the entities with a Phase 2 or later program, 701 of 1,114 monoclonal antibodies,
113 of 291 multispecific antibodies and 95 of 287 antibody–drug conjugates match a ChEMBL molecule, but
none of them has a pChEMBL measurement at a human target. Proteins have 2 and peptides 68.

**Probe.** `python -m scripts.biologic_affinity_probe`: 40 seeded US-developed Phase 2 entries of monoclonal
antibodies and proteins with a resolved target (seed 20261105). For each, an LLM with web search looked for
the earliest published binding affinity (KD, or IC50/EC50 of binding or neutralisation) of the drug for its
primary target, published by the year before entry. Results: `biologic_affinity_probe.json`.

| | Entries |
|---|---|
| Decided | 39 |
| Affinity published before entry | 19 (49%), 6 of them from patents |
| Published only after entry | 13 |
| Values at 100 nM or better | 16 of 17 |
| Values at 1 nM or better | 10 of 17 (median 1.0 nM) |

**Decision: no biologic potency line.** At the 100 nM threshold the small-molecule line uses, 16 of the
17 published values qualify, so the line would mark whether an affinity was published, not how potent the
drug is: a marker of how disclosed a program is, which the report already cautions against for the
small-molecule "any measurement" line. A tighter threshold (1 nM, 0.1 nM) would be chosen after seeing
these values, and the plan's other literature lines show that web and PubMed retrieval of dated studies
falls short of the 80% recall gate. The probe is not an estimate of recall: it has no blind reference.
