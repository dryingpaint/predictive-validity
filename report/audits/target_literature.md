# Target-biology literature (#154)

Published evidence about each target's biology in its disease, as known the year before a phase entry. Code:
`pipeline.target_literature`. **All seven kinds are descriptive.** None passed the registered gate in its two
allowed attempts, so the counts here say what the searches found. They do not measure the evidence that exists,
and none of the kinds is tested.

## Design

**Unit.** A target–disease pair (`preclin.target_disease`) with a 2008–2019 US-sited phase entry in the stored
evidence dataset. A pair is searched up to its cutoff, the year before its latest such entry. Each entry counts
only records published by the year before its own entry; this cutoff is applied when the data is read.

**Kinds.** Each needs original data on the target in the pair's disease, a subtype or a near-identical disease.
The definitions are `KIND_TEXT` in the code.

| Kind | #159 row | Registered hypothesis |
|---|---|---|
| Perturbation in primary human cells or tissue | 8 | L1 |
| Perturbation in an established cell line (literature part) | 8b | — |
| Protein differs in patients' diseased tissue | 6 (tier) | L3 |
| Animal model pharmacology: a non-genetic change to the target alters an animal model (the screen flags whether the only agent is the program's drug; L2 counts other agents) | 9 | L2 |
| Knockout or transgene alters an animal model of the disease | 4 (tier) | — |
| Observational biomarker in blood, another fluid or imaging | 7 | L4 |
| Clinical observation (an effect seen in people that implicates the target) | 10 | — |

**Retrieval per pair.**
- **Origin search:** records of the origin search (#146, `preclin.target_disease_source`), linked as hits, not copied.
- **PubMed and Europe PMC** (outside MEDLINE): titles and abstracts naming an LLM-vetted gene, receptor or complex
  name, together with a MONDO disease name, a direct subtype or an LLM-listed model term. Reviews are excluded.
- **Firecrawl's research index:** once per pair and kind, and once for papers related to the pair's first screened-in
  record.
- **The web arm:** a web-enabled model asked for the pair's studies of every kind (added later; see below).

**Screen.** A Haiku 4.5 prefilter reads pairs with more than 3,000 records, except records the web arm named. Then a
Sonnet 5 screen reads every record, with Opus 5 reading whatever Sonnet refused or answered invalidly. A seeded
sample was relabelled by Opus 5.5 (`check`).

**Registered gate.** On a seeded pilot, a kind enters the analysis only if:
- retrieval recall against a blind reference is at least 80%;
- κ against the check model is at least 0.6;
- at least 8% of Phase 2 entries carry it.

A failing kind may be revised once and scored on fresh pairs; if it fails again, it is descriptive.

**Seeds.** The pilot is 300 pairs drawn with seed 20261122 from the cohort of 2026-11-22, which has since changed.
It can't be redrawn, so it is kept as `target_literature_pilot.csv`, with rows 1–100 for version 1 and 101–200 for
version 2. The yardstick is 100 pairs outside the pilot, drawn with seed 20261124 on 2026-11-24. Its pairs and the
cutoff each was asked at are in the yardstick task's logged decisions (`pv_evidence.llm_decision`); the studies it named are in `preclin.target_literature_web_study` (arm `yardstick`).

## The gate

**Reference.** For each scored pair, Opus 5.5 with web search and fetch was given only the gene, the disease, the
program drugs and the cutoff, and listed up to 15 qualifying studies per kind. Opus 5 answered where Opus 5.5
refused: 1 of rows 1–100 and 7 of rows 101–200. Every PMID was checked against its stated title. 12% of version 1's
pointed to another paper and were corrected or dropped.

### Version 1: rows 1–100

| Kind | Reference studies (in PubMed) | Recall | Recall, PubMed-indexed | Retrieved at all | κ | Phase 2 coverage |
|---|---|---|---|---|---|---|
| Primary cells or tissue | 34 (23) | 59% | 70% | 85% | 0.20 | 43% |
| Cell line | 124 (87) | 71% | 80% | 79% | 0.60 | 64% |
| Protein in patients' tissue | 107 (74) | 61% | 70% | 75% | 0.45 | 67% |
| Animal model pharmacology, any agent | 138 (84) | 62% | 69% | 72% | 0.70 | 73% |
| Animal model pharmacology, other agents | 138 (84) | 61% | 68% | 72% | 0.65 | 71% |
| Knockout or transgene, disease model | 62 (29) | 69% | 72% | 77% | 0.76 | 36% |
| Observational biomarker | 51 (23) | 51% | 70% | 57% | 0.56 | 59% |
| Clinical observation | 96 (62) | 28% | 42% | 39% | 0.37 | 40% |

### Version 2: the single revision, rows 101–200 with a fresh reference

Version 2 made these changes before its reference was built:
- receptor and complex names were added to gene names, and direct MONDO subtypes to disease names;
- the prefilter applies above 3,000 records, as registered (version 1 used 500);
- the screen now names the experimental system first and uses tighter definitions;
- clinical observations exclude efficacy trials in the disease.

| Kind | Reference studies (in PubMed) | Recall | Recall, PubMed-indexed | Retrieved at all | κ | Phase 2 coverage |
|---|---|---|---|---|---|---|
| Primary cells or tissue | 56 (31) | 29% | 39% | 62% | 0.63 | 37% |
| Cell line | 115 (66) | 47% | 55% | 60% | 0.72 | 56% |
| Protein in patients' tissue | 104 (72) | 58% | 64% | 74% | 0.69 | 57% |
| Animal model pharmacology, any agent | 129 (78) | 55% | 58% | 68% | 0.79 | 68% |
| Animal model pharmacology, other agents | 129 (78) | 54% | 58% | 68% | 0.71 | 65% |
| Knockout or transgene, disease model | 57 (45) | 47% | 56% | 74% | 0.76 | 34% |
| Observational biomarker | 61 (42) | 59% | 64% | 82% | 0.64 | 46% |
| Clinical observation | 41 (25) | 27% | 36% | 41% | 0.34 | 25% |

**No kind passed either version.** Most missed studies name neither the gene nor the disease in their abstract:
they use a class or complex name, a model, or a related disease. A full screen of 300 seeded records the
prefilter dropped found 12 that qualify, so the prefilter misses little. **The pilot cost about $210.**

## The full descriptive run (2026-11-23)

Version 2 exactly as gated, over the 5,149 cohort pairs, reusing the pilot's 300.

| Count | Value |
|---|---|
| Retrieved (pair, record) | 1,107,052 |
| Screen decisions | 943,306 |
| Prefilter decisions, possibly / not | 125,936 / 162,764 |

**Cost: $1,889.** Screen $1,764, prefilter $116, fallback $7, check $2, names $2. The integrity checks were all 0.

## The web arm (2026-11-24)

This second retrieval arm asked Opus 5.5, with web search (up to 12 searches) and fetch (up to 6 pages), for each
pair's studies, using the pilot reference's prompt. Opus 5 answered where Opus 5.5 refused. Pilot rows 1–200 reuse
their stored reference answers.
- **Verification.** Every named study was matched to a record: first its PMID when the title matches, then its DOI
  through PubMed or Europe PMC when the title matches, then a PubMed title search. Verified studies became
  `web_agent` hits and got the same screen as every other record.
- **The yardstick.** It scored both arms: a different prompt (start from reviews, follow citations both ways,
  prefer full text) run on Sonnet 5, with Opus 5 answering the 26 pairs where Sonnet 5 ran past 900 s. **Both arms
  and the yardstick are model web searches, so the yardstick is not fully independent of the web arm.**

**Recall against the yardstick's verified studies** (393 in all; 672 named, of which 279 could not be verified):

| Kind | Yardstick studies (verified) | Abstract run | Web arm | Union | Union, counting unverified as misses |
|---|---|---|---|---|---|
| Primary cells or tissue | 70 (34) | 38% | 15% | 38% | 19% |
| Cell line | 125 (88) | 60% | 42% | 60% | 42% |
| Protein in patients' tissue | 119 (79) | 66% | 41% | 67% | 45% |
| Animal model pharmacology, any agent | 118 (81) | 53% | 28% | 56% | 38% |
| Animal model pharmacology, other agents | 118 (81) | 47% | 26% | 49% | 34% |
| Knockout or transgene, disease model | 113 (66) | 48% | 27% | 48% | 28% |
| Observational biomarker | 63 (27) | 48% | 30% | 48% | 21% |
| Clinical observation | 64 (18) | 11% | 0% | 11% | 3% |

**The gap is mainly classification, not retrieval.** On the yardstick pairs:
- the abstract run had already retrieved 77% of the yardstick's verified studies, under any kind;
- the web arm named 44% of them, and the abstract run had already retrieved 83% of what the web arm named;
- 75% of the retrieved yardstick studies count for some kind after the screen. The rest the screen reads as
  another disease, as not original data, or as a different kind from the yardstick's.

Even with both arms, no kind would pass the gate.

**Cost: $993.** Web arm $808, its fallback $134, yardstick $32, screens $19.

## Reconciliation to the rebuilt cohort (2026-11-24)

The #185 rebuild of programs and pairs changed the cohort. The final evidence build is
`8c666830-2fbb-497a-85fe-a70a5985d21e` (08:23 UTC). Compared with the cohort the web arm searched:

| Change | Pairs | What was done |
|---|---|---|
| New to the cohort | 132 | The full pipeline (`--pairs new`) |
| Cutoff moved later | 37 | Old rows linked to the new cutoff, plus searches of the gap years in every source |
| Cutoff moved earlier | 1 | Old rows linked to the new cutoff |
| Left the cohort | 16 | Rows kept |

- **The gap searches** found 1,271 PubMed, 32 Europe PMC and 5,180 Firecrawl hits, plus 112 web-arm studies dated in
  the gap.
- **No stored row was deleted or re-keyed** (`reconcile` adds only). Linking added 446 search rows and 9,987 hits.
- **Cost: $87.**

## Current state (build 8c666830; 5,265 cohort pairs)

**Pairs with each kind:**

| Kind | Pairs with any | Before the first entry | Before the latest entry | Only from the web arm | Phase 2 coverage |
|---|---|---|---|---|---|
| Primary cells or tissue | 1,868 | 1,666 | 1,856 | 39 | 38% |
| Cell line | 2,600 | 2,415 | 2,589 | 31 | 54% |
| Protein in patients' tissue | 2,711 | 2,514 | 2,701 | 18 | 55% |
| Animal model pharmacology, any agent | 3,326 | 3,048 | 3,308 | 75 | 66% |
| Animal model pharmacology, other agents | 3,113 | — | 3,097 | 70 | 63% |
| Knockout or transgene, disease model | 1,613 | 1,418 | 1,606 | 25 | 34% |
| Observational biomarker | 2,156 | 1,978 | 2,144 | 8 | 42% |
| Clinical observation | 1,469 | 1,275 | 1,459 | 49 | 28% |

**Retrieved (pair, record): 1,135,815**, by source:

| Source | Count |
|---|---|
| PubMed | 585,971 |
| Firecrawl | 458,379 |
| Origin PubMed | 195,896 |
| Firecrawl related | 75,267 |
| Europe PMC | 35,172 |
| Web arm | 24,770 |
| Origin Europe PMC | 12,324 |

**Screen decisions: 975,104.** No record is left without text, and none is left unread.

**Web-arm studies by verification:**

| Verification | Count |
|---|---|
| PMID matched | 17,416 |
| DOI resolved | 7,805 |
| Found by title search | 3,399 |
| Unverified (not hits) | 4,392 |

**Integrity** (`integrity --pairs cohort`) is all 0. The checks cover:
- **Completeness:** every pair has each search at its cutoff, and a related-paper search wherever it has evidence;
  every record with text is screened, filtered out by the prefilter, or refused by both models; every pair has a
  web-arm row.
- **Consistency:** every hit has its search; every decision is a validated decision for that pair and record;
  web studies and web hits match.

Rows kept from earlier cutoffs (446 search rows) and from the 16 pairs that left are counted, not flagged.

**Total cost** for the pilot, run, web arm and reconciliation: **about $3,180.**

## Where the data is

| Data | Location |
|---|---|
| Searches, hits, prefilter and screen | `preclin.target_literature_search`, `_hit`, `_prefilter`, `_screen` (with each decision's `pv_evidence.llm_decision` id) |
| Every study the web arm, the yardstick or the pilot reference named, with its verification | `preclin.target_literature_web_study` |
| The pilot reference's answers | `pv_evidence.llm_decision`, tasks `target_literature_reference` and `_fallback` |
| Per-pair results | the view `preclin.target_literature_evidence` |
| Record text and years | `public.publications`, `preclin.literature_record` or `preclin.target_disease_source` |

**Final prompts by task.** These are in `pipeline/target_literature.py`. Earlier versions are in git history and in
the logged decisions' runs.

| Task | prompt_version | Model | Prompt |
|---|---|---|---|
| `target_literature_gene_vet` | v2 | Sonnet 5 | `GENE_VET_SYSTEM` |
| `target_literature_model_terms` | v1 | Sonnet 5 | `MODEL_TERMS_SYSTEM` |
| `target_literature_prefilter` | v1 | Haiku 4.5 | `PREFILTER_SYSTEM` |
| `target_literature_screen` / `_fallback` / `_check` | v2 | Sonnet 5 / Opus 5 / Opus 5.5 | `SCREEN_SYSTEM` |
| `target_literature_reference` / `_fallback` (pilot, logged) | v2 | Opus 5.5 / Opus 5 | `REFERENCE_SYSTEM` |
| `target_literature_web` / `_fallback` | v1 | Opus 5.5 / Opus 5 | `REFERENCE_SYSTEM` (the reference's prompt) |
| `target_literature_yardstick` / `_fallback` | v1 | Sonnet 5 / Opus 5 | `YARDSTICK_SYSTEM` |
