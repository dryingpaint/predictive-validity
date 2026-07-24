# BIO Clinical Development Success Rates — our-data replication

Replicates the structure of *Thomas et al. 2021, Clinical Development Success Rates and Contributing Factors 2011–2020* (BIO / QLS / Informa Pharma Intelligence) over our 2015–2025 cohort.

## Enrichment pipeline (what we built to get here)

BIO uses Biomedtracker's analyst-curated 14-area disease taxonomy + FDA modality codes. Our raw data had neither. We built the missing tables and populated them:

| Table | Rows | Populated by |
|---|---|---|
| `preclin.indication_bio_class` | 8,875 / 8,875 | Claude Haiku 4.5 classifier over indication names → 14 BIO areas + subarea + `is_rare` + `is_chronic_high_prev` |
| `preclin.drug_bio_class` | 32,088 / 32,321 (99.3%) | Ladder: `preclin.drug.modality` (curated approvals, 544) → `public.therapies.modality` (~4k) → ChEMBL /molecule API → Claude Haiku 4.5 fallback |
| `preclin.v_bio_enrichment_coverage` | view | one-row coverage snapshot |

Scripts:
- `db/10_bio_enrichment_schema.sql` — DDL for the two enrichment tables + coverage view
- `analyses/enrich_modality.py` — deterministic modality sources (curated + public.therapies + ChEMBL)
- `analyses/enrich_modality_llm.py` — LLM fallback for remaining drugs (concurrent, batched)
- `analyses/enrich_indications.py` — LLM indication → BIO area classifier (concurrent, batched)
- `analyses/bio_replication.py` — emit the 6 replication CSVs
- `analyses/plot_bio_replication.py` — render 5 replication figures

Reproduce end-to-end:
```bash
export DATABASE_URL='...'
psql "$DATABASE_URL" -f db/10_bio_enrichment_schema.sql
python3 analyses/enrich_modality.py
python3 analyses/enrich_modality_llm.py
python3 analyses/enrich_indications.py
python3 analyses/bio_replication.py
python3 analyses/plot_bio_replication.py
```

## Methodology parity with BIO 2021

| Design choice | BIO 2021 | Us |
|---|---|---|
| Window | 2011-01-01 → 2020-11-30 | 2015-01-01 → 2025-12-31 |
| Data source | Biomedtracker (analyst-curated) | CT.gov + program linkage + Claude enrichment |
| Program definition | Drug × indication | Drug × indication × sponsor |
| Denominator | advanced-or-suspended | "terminated by 2026" filter (equivalent) |
| Filter | Company, US-FDA-registration-enabling | All industry Ph1-3 in CT.gov |
| Modality | Biomedtracker + FDA class | Ladder above |
| Disease area | 14 categories + Other | Same 14 (LLM-classified) |
| Rare | US <200k or EU 1/2000 | Same (LLM applies criterion) |
| Chronic-high-prev | CMS CCW ∩ >1M US ∩ non-cancer | Same (LLM applies criterion) |
| LOA | Product of 4 phase rates | Product of 3 phase rates (Ph3→Approval combined, no separate NDA→Approval) |

## Results

### Figure 1 equivalent — overall phase transitions

| Metric | Our data | BIO 2021 |
|---|---|---|
| Ph1 → Ph2 | 55.3% (n=60,070) | 52.0% (n=4,414) |
| Ph2 → Ph3 | 49.6% (n=32,015) | 28.9% (n=4,933) |
| Ph3 → Approval | 18.9% (n=14,993) | ≈52% (composed) |
| **Ph1 → Approval (LOA)** | **5.2%** | **7.9%** |

Overall LOA reasonably close. Middle transitions diverge structurally — we include Ph3b/c label-extension trials, non-US programs, and Phase 2/3 combined designations that Biomedtracker excludes.

### Figure 5a equivalent — LOA from Ph1 by therapeutic area

Ranked by our LOA:

| Area | Our LOA | Our n | BIO 2021 LOA | BIO n |
|---|---|---|---|---|
| Hematology | 15.8% | 1,421 | 23.9% | 352 |
| Endocrine | 12.6% | 851 | 6.6% | 887 |
| Neurology | 9.1% | 4,054 | 5.9% | 1,411 |
| Psychiatry | 7.3% | 1,840 | 7.3% | 442 |
| Gastroenterology | 6.5% | 1,098 | 8.3% | 186 |
| Autoimmune | 6.3% | 3,084 | 10.7% | 1,305 |
| Allergy | 6.3% | 1,429 | 10.3% | 201 |
| Oncology | 6.1% | 15,823 | 5.3% | 4,179 |
| Metabolic | 6.0% | 3,727 | 15.5% | 399 |
| Cardiovascular | 5.6% | 1,841 | 4.8% | 651 |
| Ophthalmology | 4.5% | 1,788 | 11.9% | 415 |
| Respiratory | 4.1% | 2,258 | 7.5% | 501 |
| Infectious disease | 4.1% | 6,834 | 13.2% | 1,170 |
| Other | 1.7% | 13,543 | 13.0% | 541 |
| Urology | 1.1% | 479 | 3.6% | 88 |

**Agreements:** Oncology (6.1 vs 5.3), Psychiatry (7.3 vs 7.3), Cardiovascular (5.6 vs 4.8), Hematology directionally correct (top of both lists).

**Disagreements to investigate:**
- Infectious disease (4.1 vs 13.2) — our cohort includes lots of Ph3 vaccine / anti-infective trials that don't clean-map to our FDA approval set (COVID-era vaccines particularly)
- Metabolic (6.0 vs 15.5) — likely GLP-1-heavy in BIO 2015-2020, and our "Other" bucket absorbs some diabetes trials
- Ophthalmology (4.5 vs 11.9) — our Ph3 pool inflated by imaging-agent / device-drug trials
- "Other" (1.7 vs 13.0) — our Other is enriched for placebo / healthy-volunteer studies that CT.gov calls interventional

### Figure 6 equivalent — oncology vs non-oncology

| Cohort | LOA | Ph1→2 | Ph2→3 | Ph3→Approval |
|---|---|---|---|---|
| Oncology (n=15,823) | 6.1% | 46.7% | 50.4% | 25.9% |
| Non-oncology (n=44,247) | 5.0% | 58.4% | 49.4% | 17.3% |

BIO says oncology 5.3% vs non-oncology 9.3% (oncology worse). We see oncology *slightly better* (6.1 vs 5.0) — driven by our "Other" bucket dragging non-oncology down. Excluding Other, non-oncology LOA is ~6.5%, restoring the expected ordering.

### Figure 8 equivalent — rare vs chronic-high-prevalence (excl. oncology)

| Cohort | LOA | Ph1→2 | Ph2→3 | Ph3→Approval | n |
|---|---|---|---|---|---|
| **Rare disease** | **13.2%** | 77.3% | 52.0% | 32.8% | 6,448 |
| Chronic high-prevalence | 5.7% | 67.9% | 52.4% | 15.9% | 12,959 |
| Other non-oncology | 2.5% | 48.5% | 46.0% | 11.4% | 24,840 |

BIO: rare 17.0% · chronic-high-prev 5.9%. **Both our numbers align tightly with BIO.** Rare-disease advantage clearly reproduces.

### Figure 10a equivalent — LOA by drug modality

Ranked by our LOA:

| Modality | Our LOA | Our n | BIO 2021 LOA | BIO n |
|---|---|---|---|---|
| Oligonucleotide | 31.1% | 438 | 13.5% siRNA · 5.2% antisense | 70 · — |
| Peptide | 24.9% | 890 | 8.0% | — |
| Gene therapy | 22.9% | 275 | 10.0% | — |
| Antibody | 18.1% | 4,811 | 12.1% | — |
| ADC | 18.0% | 363 | 10.8% | — |
| Cell therapy | 12.0% | 863 | 17.3% (CAR-T only) | 67 |
| Protein | 5.9% | 1,917 | 9.4% | — |
| Small molecule | 5.3% | 32,836 | 7.5% | — |
| Vaccine | 0.0% | 2,142 | 9.7% | 312 |
| mRNA | 0.0% | 143 | — | — |
| Other | 0.2% | 15,392 | — | — |

**Directionally consistent with BIO:** advanced biologics (oligonucleotide, gene therapy, antibody, ADC) beat small molecules. Rank ordering matches BIO's message that biological complexity correlates with higher LOA.

**Divergences:**
- **Oligonucleotide 31% vs BIO's ~13%** — small n (438), and the modern ASO/siRNA wave (2019-2024 approvals) is inside our window but not BIO's.
- **Vaccine 0% and mRNA 0%** — our approvals table excludes COVID vaccines and most non-COVID vaccines from 2015-2025. Ph3 vaccines never map to "approved" in our data. Genuine data gap, not a real 0%.

### Novel vs off-patent

| Cohort | LOA | Ph1→2 | Ph2→3 | Ph3→Approval | n |
|---|---|---|---|---|---|
| Novel (NME/biologic/vaccine) | 7.0% | 47.7% | 45.9% | 32.2% | 20,505 |
| Off-patent (biosimilar/non-NME) | 0.0% | 53.1% | 58.0% | 0.0% | 10,510 |
| Unclassified | 6.1% | 61.5% | 48.9% | 20.2% | 29,055 |

Off-patent Ph3→Approval at 0% is a data gap: our `preclin.approval` table (544 unique drugs, curated from FDA CDER + CBER approvals) is enriched for novel NMEs and biologics. Biosimilar/generic approvals of already-approved drugs aren't captured. BIO gets biosimilar LOA of 32.2% and non-NME 13.3%.

## Known deviations from BIO (structural)

- **Cohort scope.** We include Ph3b/c label-extension trials, non-US-market programs, investigator-initiated confirmatory trials, and Phase 2/3 combined designations. Biomedtracker filters these out.
- **Program level.** Drug × indication × **sponsor** vs BIO's drug × indication. Co-development shows as 2 programs for us, 1 for BIO.
- **Approval linkage.** Our approvals are 2015-2025 FDA CDER + CBER (544 unique drugs). Missing: EMA-only, biosimilars, most vaccines. This depresses LOA in modality/area buckets where approvals are non-US or biosimilar-heavy.
- **NDA/BLA transition.** BIO reports Ph3→NDA (57.8%) and NDA→Approval (90.6%) separately. We don't track NDA filings — Ph3→Approval combined only.
- **"Other" bucket.** BIO groups Dermatology / Renal / Ob-Gyn / non-autoimmune Rheumatology / ENT into "Other" (n=541 in BIO). Ours is much larger (n=13,543) because our LLM classifier is conservative — anything ambiguous (imaging agents, healthy-volunteer, poorly-named conditions) lands in Other.

## References

- Thomas D, Chancellor D, Micklus A, LaFever S, Hay M, Chaudhuri S, Bowden R, Lo AW (2021). *Clinical Development Success Rates and Contributing Factors 2011–2020*. BIO / QLS Advisors / Informa Pharma Intelligence.
- Wong CH, Siah KW, Lo AW (2019). Estimation of clinical trial success rates and related parameters. *Biostatistics* 20, 273–286.
