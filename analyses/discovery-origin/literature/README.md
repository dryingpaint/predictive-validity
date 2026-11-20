# Published discovery-origin labels (issue #146)

The per-drug labels from the three published classifications, for the crosswalk and validation in #146.
Only extracted labels are kept here. The articles and supplementary files are the publishers' copyright,
so download them from the links below.

| File | Source | Rows | Labels |
|---|---|---|---|
| `swinney2011_table_s1.csv` | Swinney & Anthony 2011, Nat Rev Drug Discov 10:507, doi:10.1038/nrd3480, Supplementary Table S1 | 259 NMEs approved 1999–2008 | `discovery_approach`: Target-based 100, Phenotypic screening 58, Biologic 56, Natural substance 11, Modified natural substrate 7, other or blank 27. `classification`: First in class 75, Follower 164, Imaging agent 20 |
| `eder2014_table_s1.csv` | Eder, Sedrani & Wiesmann 2014, Nat Rev Drug Discov 13:577, doi:10.1038/nrd4336, Supplementary Table S1 | 113 first-in-class drugs approved 1999–2013 | `approach`: target-based low molecular weight 46, target-based biologic 33, systems-based chemocentric 25, systems-based phenotypic screening 8, not extracted 1 |
| not here | Sadri 2023, J Med Chem 66:12651, doi:10.1021/acs.jmedchem.2c01737, Supporting Information (ACS figshare record 24093652, CC BY-NC 4.0, 28 MB PDF) | all approved small molecules | ACS and figshare refuse scripted downloads; download it in a browser |

Downloads:
- Swinney Table S1 (xls): https://static-content.springer.com/esm/art%3A10.1038%2Fnrd3480/MediaObjects/41573_2011_BFnrd3480_MOESM2_ESM.xls
- Swinney Box S2, the discovery story of each first-in-class drug (pdf): https://static-content.springer.com/esm/art%3A10.1038%2Fnrd3480/MediaObjects/41573_2011_BFnrd3480_MOESM3_ESM.pdf
- Eder Table S1 (pdf): https://static-content.springer.com/esm/art%3A10.1038%2Fnrd4336/MediaObjects/41573_2014_BFnrd4336_MOESM9_ESM.pdf
- Eder Box S2 (pdf) and figures S1–S5 (ppt): the same path with MOESM10 and MOESM4–8.
- Sadri Supporting Information: https://figshare.com/articles/journal_contribution/24093652

Extraction: `extract.py` (run it on a folder holding the downloaded supplements).

Extraction notes:
- Swinney's CSV is the spreadsheet's NMEs sheet with its header rows dropped; labels are as published, including blanks.
- Eder's CSV was parsed from the PDF text. Each drug's approach is the first line of its block that starts "Target-based" or "Systems-based". Aminolevulinic acid's approach did not extract. The paper reports 45 target-based small molecules; the extraction finds 46, so check one row against the PDF before the crosswalk.
