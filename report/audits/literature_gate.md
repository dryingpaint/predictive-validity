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
