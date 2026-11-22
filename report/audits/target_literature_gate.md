# Target-biology literature (#154): pilot gate

Issue #154 admits a kind of target evidence from the literature into the analysis only if, on a seeded pilot, its
retrieval recall against a blind reference is at least 80%, a second model agrees with the screen at κ ≥ 0.6, and at
least 8% of Phase 2 entries carry it. A failing kind may be revised once and scored on fresh pairs; if it fails again
it is descriptive. **No kind passed either version, so all seven are descriptive and the full run is not made.**

**Pilot.** 300 seeded target–disease pairs (`target_literature_pilot.csv`) drawn from the 5,149 pairs in
`preclin.target_disease` with a 2008–2019 US-sited phase entry in the stored evidence dataset. Each pair was searched
up to the year before its latest such entry (`pipeline.target_literature`):
- PubMed and Europe PMC titles and abstracts naming the gene (LLM-vetted names) and the disease (MONDO names and
  LLM-listed experimental-model terms), reviews excluded;
- Firecrawl's research index, once per pair and kind, and once for papers related to each pair's first screened-in record.

Claude Haiku 4.5 prefiltered pairs with very large literatures. Claude Sonnet 5 screened every record for the seven
kinds. Claude Opus 5.5 relabelled a seeded sample (about 25 screened in and 25 screened out per kind).

**Reference.** For each scored pair, Claude Opus 5.5 with web search and fetch, given only the gene, the disease,
the program drugs and the cutoff, listed up to 15 qualifying studies per kind (Claude Opus 5 answered the pairs Opus 5.5
refused: 1 of rows 1–100, 7 of rows 101–200). Every PMID was checked against the title the model gave; 12% of
version 1's were wrong (a real title with another paper's PMID) and were corrected by title search or dropped.

## Version 1 (rows 1–100, reference after PMID verification)

| Kind | Reference studies (in PubMed) | Recall | Recall, PubMed-indexed | Retrieved at all | κ (pairs) | Phase 2 coverage | Passes |
|---|---|---|---|---|---|---|---|
| Perturbation in primary human cells or tissue (row 8, L1) | 34 (23) | 59% | 70% | 85% | 0.20 (337) | 43% | no |
| Perturbation in a cell line (literature part) | 124 (87) | 71% | 80% | 79% | 0.60 (337) | 64% | no |
| Protein differs in patients' tissue (row 6 tier, L3) | 107 (74) | 61% | 70% | 75% | 0.45 (337) | 67% | no |
| Animal model pharmacology, any agent (row 9, pooled) | 138 (84) | 62% | 69% | 72% | 0.70 (337) | 73% | no |
| Animal model pharmacology, other agents only (L2) | 138 (84) | 61% | 68% | 72% | 0.65 (337) | 71% | no |
| Knockout or transgene alters a disease model (row 4 tier) | 62 (29) | 69% | 72% | 77% | 0.76 (337) | 36% | no |
| Observational biomarker (row 7, L4) | 51 (23) | 51% | 70% | 57% | 0.56 (337) | 59% | no |
| Clinical observation (row 10) | 96 (62) | 28% | 42% | 39% | 0.37 (337) | 40% | no |

## Version 2, the single revision (rows 101–200, fresh reference)

Fixed before its reference was built:
- **Gene names** may add the receptor or complex names papers use for the protein.
- **Disease names** add the disease's direct MONDO subtypes.
- **The prefilter** applies above 3,000 records, as registered (version 1 used 500).
- **The screen** names the experimental system of each finding first, at medium effort, with tighter definitions.
  Clinical observations now exclude efficacy trials in the disease.

| Kind | Reference studies (in PubMed) | Recall | Recall, PubMed-indexed | Retrieved at all | κ (pairs) | Phase 2 coverage | Passes |
|---|---|---|---|---|---|---|---|
| Perturbation in primary human cells or tissue (row 8, L1) | 56 (31) | 29% | 39% | 62% | 0.63 (334) | 37% | no |
| Perturbation in a cell line (literature part) | 115 (66) | 47% | 55% | 60% | 0.72 (334) | 56% | no |
| Protein differs in patients' tissue (row 6 tier, L3) | 104 (72) | 58% | 64% | 74% | 0.69 (334) | 57% | no |
| Animal model pharmacology, any agent (row 9, pooled) | 129 (78) | 55% | 58% | 68% | 0.79 (334) | 68% | no |
| Animal model pharmacology, other agents only (L2) | 129 (78) | 54% | 58% | 68% | 0.71 (334) | 65% | no |
| Knockout or transgene alters a disease model (row 4 tier) | 57 (45) | 47% | 56% | 74% | 0.76 (334) | 34% | no |
| Observational biomarker (row 7, L4) | 61 (42) | 59% | 64% | 82% | 0.64 (334) | 46% | no |
| Clinical observation (row 10) | 41 (25) | 27% | 36% | 41% | 0.34 (334) | 25% | no |

## Why studies are missed

Retrieval is the main loss. "Retrieved at all" is the share of reference studies among the records the searches
returned, whatever the screen said.
- **Retrieval misses.** Most missed PubMed studies name neither the gene's names nor the disease's in their title or
  abstract. They use a class or complex name (GPIIb/IIIa antagonists, GABA-A receptor subtypes), a model rather than
  the disease, or a related disease.
- **Clinical observations are the worst.** They are rarely written up with the target named next to the disease.
- **Screen losses.** The screen loses a further 6–33 points, mostly by reading a kind as absent.
- **Coverage is not the constraint.** It is far above 8%; the screen marks a kind for 25–73% of Phase 2 entries.
- **The prefilter misses little.** A full screen of 300 seeded records the version 1 prefilter dropped found 12
  qualifying for some kind.

## Cost

Measured from the stored usage of every decision (Batch API at its discount), at list prices.

| | USD |
|---|---|
| Version 1 run (names, prefilter, screen, check) | 79 |
| Version 2 run (names, prefilter, screen, check) | 92 |
| Blind references (both sets, with web search) | 40 |
| **Pilot total** | **about 210** |

Firecrawl's 2,357 research-index calls left the credit balance unchanged (993,122).

**Full-run extrapolation, version 2 per pair ($0.30):**
- the 5,149 cohort pairs: about **$1,550**;
- all 11,311 target–disease pairs: about **$3,400**.

The PubMed searches run at NCBI's three requests a second, about 45 minutes per 300 pairs, so roughly 13 hours for
the cohort.
