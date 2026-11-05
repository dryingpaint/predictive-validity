# Literature lines: pilot gate

The plan amendment of 2026-11-03 (`report/translation_plan.md`) admits a literature line into the analysis only if,
on a seeded pilot, its retrieval recall against a blind reference set is at least 80%, a second model agrees with the
screen at κ ≥ 0.6, and at least 8% of Phase 2 entries carry it. Otherwise the line is reported as descriptive.
No line passed, so none was run on the full cohort.

**Pilot.** 300 seeded US-sited phase entries of 2008–2019 with a disease (`literature_pilot_sample.csv`). For each,
`pipeline.literature` searched PubMed titles and abstracts up to the year before entry, reviews excluded, by the
drug's name, code names and FDA substance-registry names, and the disease's MONDO label, synonyms and direct subtypes.
It kept the top 20 results per search. Claude Sonnet 5 screened each abstract and quoted the sentence that decided
it. Claude Opus 5.5 relabelled a seeded 50 abstracts per kind.

**Reference.** For the first 100 entries, agents with web access listed every study of each kind dated up to the
cutoff year: PubMed, Europe PMC, conference abstracts and company releases. They had no access to the pipeline's
searches or labels. They found studies of at least one kind for 65 of the 100 entries. 353 of 388 studies are in
PubMed; the rest are conference abstracts (29) and other sources (6).

| Kind | Reference studies | Recall | Recall, PubMed-indexed | κ (pairs) | Phase 2 coverage | Passes |
|---|---|---|---|---|---|---|
| Drug in an animal model of the disease | 85 | 22% | 24% | 0.95 (49) | 7.1% | no |
| Drug in healthy animals | 189 | 22% | 24% | 0.69 (100) | 20% | no |
| Human target engagement (Phase 2/3) | 114 | 25% | 30% | 0.59 (100) | 20% | no |

For every entry where the reference found no study of a kind, the pipeline found none either. So the
pipeline does not invent studies, but it misses most real ones.

**Why studies were missed.** These are the PubMed-indexed reference studies, by kind:

| Kind | Not matched by the query | Matched, ranked below the 20 kept | Kept, screened out | Found |
|---|---|---|---|---|
| Animal model of the disease | 59 | 0 | 1 | 19 |
| Healthy animals | 98 | 24 | 12 | 42 |
| Human engagement | 43 | 19 | 7 | 29 |

The screen is not the bottleneck; retrieval is. Animal studies name the model by its assay or induction (a
forced-swim test, a xenograft line), not by the disease. Older papers use names the substance registry does not
list (flavopiridol for alvocidib, interleukin-2 for aldesleukin). Pharmacology abstracts say "transport" or
"distribution" without the exposure terms searched. Well-studied drugs have more results than the 20 kept.

Retuning the queries against these 100 entries and scoring again on them would fit the gate to its own
reference. A second version needs a fresh blind reference set. The three lines stay descriptive: the counts above
and the pilot labels in `preclin.literature_screen`.

## Version 2 (2026-11-04)

The second and last attempt, fixed in `report/translation_plan.md` before it ran: one PubMed search per drug by its
names alone, keeping up to 200 abstracts. The names are INN, code names, ChEMBL and PubChem synonyms and FDA
substance-registry names, filtered of identifiers and chemical names. Claude Sonnet 5 read each abstract once and
decided every kind, naming the disease of any animal model. A second step mapped that disease to MONDO, and a model
counts for an entry when its term is within Lin 0.5 of the entry's disease. Claude Opus 5.5 relabelled 149 abstracts
(about half screened in and half screened out per kind).

**Scored only on the fresh blind reference**: pilot rows 101–200, researched by new agents with no access to either
version. They found 308 studies. All four agents lost general web search partway through, so conference abstracts
and company sources are under-covered; recall over PubMed-indexed studies is the fairer measure.

| Kind | Reference studies (in PubMed) | Recall | Recall, PubMed-indexed | κ (pairs) | Phase 2 coverage | Passes |
|---|---|---|---|---|---|---|
| Drug in an animal model of the disease | 60 (27) | 22% | 48% | 0.74 (149) | 28% | no |
| Drug in healthy animals | 171 (161) | 27% | 29% | 0.81 (149) | 31% | no |
| Human target engagement (Phase 2/3) | 76 (56) | 43% | 59% | 0.76 (149) | 28% | no |

**Why studies were missed.** These are the PubMed-indexed reference studies on the fresh rows:

| Kind | Not matched by the names | Matched, below the 200 kept | Kept, screened out | Other disease | Found |
|---|---|---|---|---|---|
| Animal model of the disease | 10 | 2 | 1 | 1 | 13 |
| Healthy animals | 16 | 68 | 30 | 0 | 46 |
| Human engagement | 6 | 12 | 5 | 0 | 33 |

Searching by drug name fixed most of version 1's vocabulary misses. The remaining loss is volume: for well-studied
drugs, PubMed's relevance order puts the reference studies below the 200 kept. Raising the cap or reranking would be
a third version, which the plan does not allow.

**Secondary: the version 1 reference rows (1–100)** were seen while designing version 2, so they are not a test.
Recall there was 18% / 37% / 58% (PubMed-indexed) for the three kinds.

**Input errors found.** Two entities in the pilot carry another drug's code name in `preclin.moiety.code_names`, and
version 2 searched them:
- canakinumab lists AIN457 (secukinumab). None of its 8 kept abstracts names it.
- nelonicline lists TC-5619 (a different α7 agonist) beside its own ABT-126. Its one qualifying abstract is about
  TC-5619, so it is a wrong-drug positive.

These codes come from entity resolution upstream of this step.

**Result.** No kind passes, so none runs on the cohort, and under the plan no third version is run. The three lines
stay descriptive: the pilot counts above, and the screens in `preclin.literature_drug_screen` (version 2) and
`preclin.literature_screen` (version 1).

**Cost.**
- Screen: 7.86M input / 1.64M output tokens, Sonnet 5.
- Check: 0.10M / 0.02M tokens, Opus 5.5.
- Disease mapping: 3.52M / 0.03M tokens, Sonnet 5.
