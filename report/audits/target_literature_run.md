# Target-biology literature (#154): full descriptive run

All seven kinds are **descriptive**. None passed the registered pilot gate, because retrieval recall was below 80%
(`target_literature_gate.md`). The counts below say what the search found; they do not measure evidence that exists,
and nothing here is tested.

**Run.** Version 2 of `pipeline.target_literature`, exactly as gated, over the 5,149 cohort pairs: target–disease pairs
with a 2008–2019 US-sited phase entry in the stored evidence dataset. It started 2026-11-23T00:52:25Z, and the pilot's 300 pairs were reused.
- **Retrieval.**
  - The origin search's records (#146, `preclin.target_disease_source`) are linked as hits, not copied.
  - PubMed and Europe PMC are searched by vetted gene, receptor and complex names, plus disease names, MONDO subtypes and model terms.
  - Firecrawl runs once per pair and kind, plus a related-paper pass.
- **Screen.** A Haiku 4.5 prefilter for pairs above 3,000 records, then the Sonnet 5 screen. Claude Opus 5 read the records Sonnet 5 refused or answered invalidly.
- **Check.** Opus 5.5 relabelled a seeded sample.

**Where the data lives.**
- `preclin.target_literature_search`, `_hit`, `_prefilter` and `_screen` hold the raw data: every query, every record link, every decision with its `pv_evidence.llm_decision` id.
- `preclin.target_literature_evidence` (view) holds the per-pair result: one row per pair and kind, with the first year, the record ids and their years, and, for animal pharmacology, whether only the program's drug was used.
- Record text and years are stored once, in `public.publications`, `preclin.literature_record` or `preclin.target_disease_source`.

## Records
- **Retrieved (pair, record): 1,107,052.** By source: europepmc 34,551, firecrawl 445,856, firecrawl_related 72,540, origin_europepmc 12,152, origin_pubmed 191,863, pubmed 577,798. Only the origin search returned 39,927 of them.
- **Screen rows:** 943,306.
- **Prefilter rows (possibly / not):** 125936 / 162764.
- **Records without stored text:** 705, so they were never screened. **Records with no publication year:** 705.
- **Records refused by both models:** 257. Both models' safety classifiers declined them, so no reading exists.

## Pairs with each kind
"Before entry" means a qualifying record published by the year before the pair's first, or latest, 2008–2019 entry.

| Kind | Pairs with any qualifying record | Before the first entry | Before the latest entry |
|---|---|---|---|
| Perturbation in primary human cells or tissue (row 8) | 1,782 (35%) | 1,598 | 1,773 |
| Perturbation in a cell line, literature part | 2,491 (48%) | 2,318 | 2,482 |
| Protein differs in patients' tissue (row 6 tier) | 2,620 (51%) | 2,432 | 2,611 |
| Animal model pharmacology, any agent (row 9) | 3,162 (61%) | 2,900 | 3,143 |
| Knockout or transgene alters a disease model (row 4 tier) | 1,552 (30%) | 1,368 | 1,546 |
| Observational biomarker (row 7) | 2,100 (41%) | 1,925 | 2,088 |
| Clinical observation (row 10) | 1,382 (27%) | 1,200 | 1,374 |

Animal model pharmacology with an agent other than the program's drug (the registered L2's kind):
2,953 pairs, of which 2,936 before the latest entry.

## Agreement check
Claude Opus 5.5 relabelled a seeded sample of 334 run records, about 25 screened in and 25 out per kind. The κ values below combine those with the pilot's 334 relabels: primary-cell perturbation 0.73, cell-line perturbation 0.69, protein in tissue 0.64, animal model pharmacology 0.75 (other agents 0.71), knockout or transgene alters a disease model 0.77, observational biomarker 0.62, clinical observation 0.44.

## Integrity checks
`python -m pipeline.target_literature integrity --pairs cohort`. Every check must be 0.

| Check | Count | Result |
|---|---|---|
| cohort pairs missing a pubmed, europepmc or per-kind firecrawl search at their cutoff | 0 | pass |
| pairs with a qualifying record but no related-paper search | 0 | pass |
| retrieved records with stored text but no screen row, no prefilter-out row and no refusal by both models | 0 | pass |
| screen or prefilter rows for a record the pair's searches do not return | 0 | pass |
| hits without their search row | 0 | pass |
| searches of a pair outside the cohort, or at another cutoff | 0 | pass |
| screen rows whose decision is not a validated version 2 screen (or its fallback) of that pair and record | 0 | pass |
| prefilter rows whose decision is not a validated prefilter of that pair and record | 0 | pass |
| prefilter rows of a pair at or below the prefilter threshold | 0 | pass |

Primary keys prevent duplicate rows in every table. A crash resumes without duplicates: searches are keyed by pair, cutoff, source and kind, and each screen chunk replaces its pairs' rows in one transaction after its model calls return.

## Cost
Model calls made since the run started, at list prices (Batch API discount on batched runs):

| Task | USD |
|---|---|
| target_literature_gene_vet | 1.04 |
| target_literature_model_terms | 0.71 |
| target_literature_prefilter | 115.61 |
| target_literature_screen | 1,763.57 |
| target_literature_screen_check | 1.63 |
| target_literature_screen_fallback | 6.57 |
| **Run total** | **1,889.13** |

The pilot, before the run, cost 210.36. Firecrawl research-index calls did not change the credit balance.
