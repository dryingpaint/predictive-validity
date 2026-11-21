# Published discovery-origin labels (issue #146)

The per-drug labels from the three published classifications, for the crosswalk and validation in #146.
Only extracted labels are kept here. The articles and supplementary files are the publishers' copyright,
so download them from the links below.

| File | Source | Rows | Labels |
|---|---|---|---|
| `swinney2011_table_s1.csv` | Swinney & Anthony 2011, Nat Rev Drug Discov 10:507, doi:10.1038/nrd3480, Supplementary Table S1 | 259 NMEs approved 1999–2008 | `discovery_approach`: Target-based 100, Phenotypic screening 58, Biologic 56, Natural substance 11, Modified natural substrate 7, other or blank 27. `classification`: First in class 75, Follower 164, Imaging agent 20 |
| `eder2014_table_s1.csv` | Eder, Sedrani & Wiesmann 2014, Nat Rev Drug Discov 13:577, doi:10.1038/nrd4336, Supplementary Table S1 | 113 first-in-class drugs approved 1999–2013 | `approach`: target-based low molecular weight 46, target-based biologic 33, systems-based chemocentric 25, systems-based phenotypic screening 8, not extracted 1 |
| `sadri2023_si1.csv` | Sadri 2023, J Med Chem 66:12651, doi:10.1021/acs.jmedchem.2c01737, Supporting Information 1 (CC BY-NC 4.0) | 1,457 FDA-approved drugs, 652 to 2020, in SI 1's order | `category` (abridged, as printed) and `category_full` (SI 1's legend): Non-human Phenotype 518, Endogenous Phenotypes 150, Human Phenotypes 130, Target-based 120, Other Biologics 95, Historical 88, MoA-informed Phenotype 79, Endogenous Biologic 67, Sagacious Phenotypes 39, unclassified 171. `note`: why an unclassified drug has no category, as printed ("Secondary", "Contrast agent", "Not found") |

Downloads:
- Swinney Table S1 (xls): https://static-content.springer.com/esm/art%3A10.1038%2Fnrd3480/MediaObjects/41573_2011_BFnrd3480_MOESM2_ESM.xls
- Swinney Box S2, the discovery story of each first-in-class drug (pdf): https://static-content.springer.com/esm/art%3A10.1038%2Fnrd3480/MediaObjects/41573_2011_BFnrd3480_MOESM3_ESM.pdf
- Eder Table S1 (pdf): https://static-content.springer.com/esm/art%3A10.1038%2Fnrd4336/MediaObjects/41573_2014_BFnrd4336_MOESM9_ESM.pdf
- Eder Box S2 (pdf) and figures S1–S5 (ppt): the same path with MOESM10 and MOESM4–8.
- Sadri Supporting Information: https://figshare.com/articles/journal_contribution/24093652 (save SI 1 as `jm2c01737_si_001.pdf`). The same files, with SI 1 and SI 3 carrying the highlighted evidence behind each call, are on OSF: https://doi.org/10.17605/osf.io/hs79u. SI 2 (per-drug citation exports), SI 3 (off-target mechanisms of target-based drugs) and SI 4–5 (each drug's affinity percentile among its target's ChEMBL ligands) are not extracted.

Extraction: `extract.py` (run it on a folder holding the downloaded supplements).

Extraction notes:
- Sadri's CSV was parsed from SI 1's word positions (`pdftotext -bbox`): each drug is a capitalised heading at a column's left edge with its year below, and its category sits beside it in smaller type. All 120 "Target-based" and 79 "MoA-informed" labels in the PDF were assigned, and ten random rows matched the PDF by eye. Thirty labelled drugs have no year because the heading's next line is not one (the year sits at the top of the next column). Sodium picosulfate's heading is split across a line and extracted as "DIUM PICOSULFATE". Sadri's 9.4% target-based figure is close to, not equal to, 120 of the 1,286 classified drugs (9.3%).
- On the 247 drugs Swinney and Sadri share, Sadri never calls target-based a drug Swinney calls phenotypic (0 of 47), and calls 26 of Swinney's 89 target-based drugs target-based; it puts most of the rest in a phenotypic category (non-human phenotype 28, endogenous molecule 10), often noting the drug is an analog of an earlier one. The two papers measure different things: Swinney the screen that found the molecule, Sadri the first observation behind its chemical line.
- Swinney's CSV is the spreadsheet's NMEs sheet with its header rows dropped; labels are as published, including blanks.
- Eder's CSV was parsed from the PDF text. Each drug's approach is the first line of its block that starts "Target-based" or "Systems-based". Aminolevulinic acid's approach did not extract. The paper reports 45 target-based small molecules; the extraction finds 46, so check one row against the PDF before the crosswalk.
