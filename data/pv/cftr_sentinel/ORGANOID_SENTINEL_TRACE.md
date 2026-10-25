# CFTR organoid sentinel trace

Checked 2026-09-18 against `pv_literature_v2`.

## Sentinel paper

- Title: *Patient-derived cell models for personalized medicine approaches in cystic fibrosis*
- DOI: `10.1016/j.jcf.2022.11.007`
- PMID: `36529661`
- PMCID: `PMC9992303`
- Canonical `scholarly_work_id`: `492287`

The therapeutic narrative explicitly names ivacaftor (`VX-770`, Kalydeco),
tezacaftor (`VX-661`), and elexacaftor (`VX-445`), including the triple
combination Trikafta/Kaftrio. Forskolin is an assay reagent and was not treated
as a therapeutic asset.

## Trial and normalization path

The bounded sentinel cohort uses `NCT02934698`, a completed 2018 interventional
study with the exact registered drug literal `Ivacaftor` and exact condition
literal `Cystic Fibrosis`.

The deterministic source chain is:

```text
NCT02934698
  -> ivacaftor (ChEMBL/PubChem normalized asset)
  -> CFTR (two complete ChEMBL mechanism rows; HGNC/UniProt target)
  -> MONDO:0009061 cystic fibrosis
```

Cohort: `pv_cftr_organoid_sentinel_v1`.

No LLM was called. Resolution required a unique exact registry intervention,
a unique exact ChEMBL parent, complete ChEMBL mechanism enumeration, and a
unique exact native OLS disease identifier.

## Retrieval results

| Stage | Query ID | Complete hits | Sentinel present? | Sentinel rank |
|---|---:|---:|---|---:|
| Asset + indication | 1208 | 2,268 | No | — |
| Effective target only | 1209 | 15,880 | Yes | 4,575 |
| Local target + indication projection | derived from 1209 | — | Yes | 4,575 |

The asset query used the verified ivacaftor aliases plus safe cystic-fibrosis
aliases. The target query used `CFTR`, `CF transmembrane conductance regulator`,
and `Cystic fibrosis transmembrane conductance regulator` without phenotype or
preclinical vocabulary.

The paper is absent from asset + indication because its title and abstract do
not name ivacaftor or another verified ivacaftor alias. It is present in the
target-only inventory because the abstract names CFTR, and the local projection
links it to cystic fibrosis because the title/abstract names that indication.

This is the intended reason for retaining both provider-query families. An
asset-only policy would miss the known organoid/theratyping review.

## Full text and classification boundary

Europe PMC metadata currently marks the work `is_open_access=false`, despite a
PMCID and a publicly readable author manuscript. The rights-aware full-text
adapter therefore did not select it. No JATS/PDF representation or GCS object
was stored; representation-specific reuse rights require review.

The abstract itself contains `organoids`, patient-derived culture models,
theratyping, and prediction of clinical efficacy. The ingestion layer stores
that abstract but does not yet classify the paper as preclinical evidence or
extract its assays and endpoints. That remains a downstream, passage-backed
enrichment.

## Replay checks

- Replanning inserted zero work items.
- Both work items completed with expected, returned, and committed totals equal.
- Duplicate work keys: `0`.
- Duplicate canonical candidates: `0`.
- Stale running leases: `0`.
