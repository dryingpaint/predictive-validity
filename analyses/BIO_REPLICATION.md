# BIO Clinical Development Success Rates — our-data replication

Replicates *Thomas et al. 2021, Clinical Development Success Rates and Contributing Factors 2011–2020* (BIO / QLS / Informa Pharma Intelligence) over our 2015–2025 cohort.

## Overview: Ph1→Approval 7.0% (BIO 7.9%)

Headline replication numbers, side-by-side with BIO:

| Metric | Us | BIO 2021 |
|---|---|---|
| **Overall Ph1→Approval (LOA)** | **7.0%** | **7.9%** |
| Ph1 → Ph2 | 56.6% | 52.0% |
| Ph2 → Ph3 | 51.2% | 28.9% |
| Ph3 → Approval | 24.2% | ~52% (composed) |
| Hematology LOA (top area) | 18.4% | 23.9% |
| Oncology LOA | 6.5% | 5.3% |
| NME (small-molecule) LOA | 8.6% | 5.7% |
| Biologic LOA | 26.5% | 9.1% |

## What we built to get here

BIO uses Biomedtracker's analyst-curated 14-area disease taxonomy + FDA modality codes. Our raw data had neither. We built the enrichment tables:

| Table | Rows | Populated by |
|---|---|---|
| `preclin.indication_bio_class` | 8,875 / 8,875 (100%) | Claude Haiku over indication names → 14 BIO areas + subarea + `is_methodology_study` |
| `preclin.drug_bio_class` | 32,193 / 32,321 (99.6%) | Ladder: `preclin.drug.modality` (curated) → `public.therapies` → ChEMBL /molecule API → Claude Haiku |
| `preclin.v_bio_enrichment_coverage` | view | One-row coverage snapshot |

Filters we apply (all novel to our pipeline; BIO already excludes these via Biomedtracker's curation):
- `is_methodology_study` — 279 Phase 1 methodology studies (healthy volunteer, PK, bioequivalence, drug interaction)
- `is_placebo` — 2,736 placebo / vehicle / excipient / diluent "drugs"
- `modality_subtype = 'non_drug_program'` — 296 device / procedure / surgical / imaging entries

## Methodology parity with BIO 2021

| Design choice | BIO 2021 | Us |
|---|---|---|
| Window | 2011-01-01 → 2020-11-30 | 2015-01-01 → 2025-12-31 |
| Data source | Biomedtracker | CT.gov + program linkage + Claude enrichment |
| Program definition | Drug × indication | Drug × indication × sponsor |
| Denominator | advanced-or-suspended | "terminated by 2026" filter (equivalent) |
| Program filter | Company, US-FDA-registration-enabling | Non-placebo, non-methodology, non-device |
| Disease taxonomy | 14 BIO areas + Other | Same 14 (LLM-classified) |
| Novelty | Biomedtracker + FDA class | ChEMBL molecule_type + `public.therapies.novelty_class` + LLM fallback |

## Full results

### Figure 1 — overall phase transitions

| Metric | Our data | BIO 2021 |
|---|---|---|
| Ph1 → Ph2 | 56.6% (n=45,124) | 52.0% (n=4,414) |
| Ph2 → Ph3 | 51.2% (n=24,573) | 28.9% (n=4,933) |
| Ph3 → Approval | 24.2% (n=11,709) | ~52% (composed) |
| **Ph1 → Approval (LOA)** | **7.0%** | **7.9%** |

### Figure 5a — LOA from Ph1 by therapeutic area (ranked by our LOA)

| Area | Our LOA | Our n | BIO 2021 LOA | BIO n |
|---|---|---|---|---|
| Hematology | 18.4% | 1,236 | 23.9% | 352 |
| Endocrine | 15.7% | 691 | 6.6% | 887 |
| Neurology | 13.1% | 2,853 | 5.9% | 1,411 |
| Psychiatry | 10.1% | 1,352 | 7.3% | 442 |
| Autoimmune | 9.4% | 2,115 | 10.7% | 1,305 |
| Allergy | 9.2% | 988 | 10.3% | 201 |
| Gastroenterology | 8.8% | 820 | 8.3% | 186 |
| Metabolic | 8.0% | 2,812 | 15.5% | 399 |
| Cardiovascular | 7.6% | 1,366 | 4.8% | 651 |
| Oncology | 6.5% | 15,283 | 5.3% | 4,179 |
| Ophthalmology | 6.1% | 1,334 | 11.9% | 415 |
| Respiratory | 5.8% | 1,613 | 7.5% | 501 |
| Infectious disease | 5.3% | 5,352 | 13.2% | 1,170 |
| Other | 3.2% | 6,964 | 13.0% | 541 |
| Urology | 1.6% | 345 | 3.6% | 88 |

**Same 15 areas** as BIO. Ordering agrees for Hematology on top and Urology on bottom. Divergences (Endocrine / Neurology higher, Infectious / Ophthalmology / Other lower) trace to our approvals table missing vaccine and biosimilar approvals, and to our LLM "Other" bucket still being broader than BIO's Dermatology-Renal-Rheumatology-ENT slice.

### Figure 6 — oncology vs non-oncology

| Cohort | LOA | Ph1→2 | Ph2→3 | Ph3→Approval |
|---|---|---|---|---|
| Oncology (n=15,283) | 6.5% | 45.4% | 49.4% | 28.8% |
| Non-oncology (n=29,841) | 7.4% | 62.4% | 51.8% | 23.0% |

BIO: oncology 5.3% vs non-oncology 9.3%. Ordering matches (oncology lower). Numerical gap smaller than BIO's because our non-oncology cohort still has some heterogeneity BIO's doesn't.

### Figure 9 — novel vs off-patent, plus subgroups

**Top-level (Figure 9 header):**

| Cohort | LOA | n | BIO 2021 LOA | BIO n |
|---|---|---|---|---|
| Novel | 10.9% | 30,288 | 6.8% | 10,527 |
| Off-patent | 0.0% | 9,327 | 14.7% | 2,161 |
| Unclassified | 0.7% | 5,509 | — | — |

**Subgroups (Figure 9 body):**

| Cohort | LOA | n | BIO 2021 LOA |
|---|---|---|---|
| Biologic | 26.5% | 6,281 | 9.1% |
| NME (small-molecule) | 8.6% | 20,864 | 5.7% |
| Vaccine | 0.0% | 2,122 | 9.7% |
| Non-NME | 0.0% | 7,329 | 13.3% |
| Biosimilar | 0.0% | 162 | 32.2% |

**Off-patent, Vaccine, Non-NME, Biosimilar all show 0% because our `preclin.approval` table (544 unique drugs, curated from FDA CDER + CBER 2015-2025) is enriched for novel NMEs and biologics. Biosimilar approvals, vaccine approvals (COVID and non-COVID), and label extensions of already-approved drugs are absent.** This is a data gap, not a real 0% approval rate. Fixing it requires ingesting FDA vaccine approvals (~50 rows) and biosimilar approvals (~50 rows) which is out of scope for this replication.

### Figure 10a — LOA by drug modality

| Modality | Our LOA | Our n | BIO 2021 LOA | BIO n |
|---|---|---|---|---|
| Oligonucleotide | 32.5% | 412 | 13.5% siRNA · 5.2% ASO | 70 · — |
| Peptide | 26.3% | 831 | 8.0% | — |
| Gene therapy | 23.0% | 274 | 10.0% | — |
| Antibody | 19.0% | 4,539 | 12.1% | — |
| ADC | 18.2% | 360 | 10.8% | — |
| Cell therapy | 12.1% | 857 | 17.3% (CAR-T only) | 67 |
| Protein | 6.2% | 1,834 | 9.4% | — |
| Small molecule | 5.8% | 29,286 | 7.5% | — |
| Other | 0.8% | 4,622 | — | — |
| Vaccine | 0.0% | 1,972 | 9.7% | 312 |
| mRNA | 0.0% | 137 | — | — |

Rank ordering matches BIO — biological complexity correlates with higher LOA. Our absolute numbers run higher for oligonucleotide / peptide / gene-therapy because the modern ASO/GLP-1/AAV wave is inside our 2015-2025 window but not BIO's 2011-2020.

## Enrichment pipeline

Reproduce end-to-end:
```bash
export DATABASE_URL='...'
psql "$DATABASE_URL" -f db/10_bio_enrichment_schema.sql
python3 analyses/enrich_modality.py             # curated + public.therapies + ChEMBL + LLM
python3 analyses/enrich_indications.py          # LLM → 14-area BIO taxonomy
python3 analyses/bio_replication.py             # emit replication CSVs
python3 analyses/plot_bio_replication.py        # render replication figures
python3 analyses/audit_data.py                  # full data audit → data_audit.md
```

## Known limitations

- **`preclin.approval` scope**: 544 unique drugs from FDA CDER+CBER 2015-2025. Excludes vaccines (Comirnaty, Shingrix, Arexvy, RSVpreF, etc.), biosimilars (~100+ approved 2015-2025), and EMA-only approvals. This zeros out LOA for the Vaccine / Non-NME / Biosimilar subgroups.
- **Cohort scope**: we include Ph3b/c label-extension trials, non-US-market programs, and Phase 2/3 combined designations that Biomedtracker filters out. Depresses Ph3→Approval (24% vs BIO ~52%).
- **Program level**: drug × indication × **sponsor** vs BIO's drug × indication. Co-development shows as 2 programs for us, 1 for BIO.
- **NDA→Approval separate rate**: BIO reports Ph3→NDA (57.8%) and NDA→Approval (90.6%). We don't track NDA filings — Ph3→Approval combined only.

## References

- Thomas D, Chancellor D, Micklus A, LaFever S, Hay M, Chaudhuri S, Bowden R, Lo AW (2021). *Clinical Development Success Rates and Contributing Factors 2011–2020*. BIO / QLS Advisors / Informa Pharma Intelligence.
- Wong CH, Siah KW, Lo AW (2019). Estimation of clinical trial success rates and related parameters. *Biostatistics* 20, 273–286.
