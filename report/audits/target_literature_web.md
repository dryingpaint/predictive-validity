# Target-biology literature (#154): web-search second arm

The abstract run (#173, `target_literature_run.md`) searched titles and abstracts. This second arm asked a
web-enabled model to search the web for each cohort pair's studies, the way the pilot's reference did. It could
run several searches, read full text, reviews and supplements, and follow citations. A differently set up model
then built a fresh yardstick to score both arms. **All seven kinds stay descriptive**: #154 allows no third
attempt at the gate. **No kind would have passed anyway.** The union of both arms finds 11–67% of the yardstick's
verified studies, against a bar of 80%.

## What ran (2026-11-24, branch `target-literature-web`, migration 156)

- **Pairs.** The 5,149 cohort pairs and cutoffs, frozen at 03:38 UTC in `target_literature_web_pairs.csv`. The
  9,500 cohort entries are frozen in `target_literature_web_entries.csv`.
- **Web arm.** `pipeline.target_literature web`, one call per pair: Claude Opus 5.5 with web search (≤ 12) and
  fetch (≤ 6), using the pilot reference's prompt. Claude Opus 5 answered where Opus 5.5 refused or gave an invalid
  answer: 342 calls, mostly refusals.
  - Pilot rows 1–200 reuse their stored reference answers (same prompt; `web-import`).
  - 1 pair was refused by both models, and is recorded with no hits.
- **Verification.** Every named study is matched to a record, in this order:
  1. its PMID, kept when the title matches;
  2. otherwise its DOI, through PubMed, batched, or Europe PMC, kept when the title matches;
  3. otherwise a PubMed title search.

| Verification | Web arm | Yardstick |
|---|---|---|
| PMID matched | 16,891 | 194 |
| PMID found by title search | 3,277 | 114 |
| DOI resolved | 7,527 | 85 |
| Unverified (not a hit) | 4,221 | 279 |
| **Total** | **31,916** | **672** |

- **Hits.** Verified studies became 24,053 `web_agent` (pair, record) hits on 3,988 pairs. 5,781 of them were not
  retrieved by the abstract run.
- **Screen.** Web records got the run's screen (Sonnet 5, with Opus 5 as fallback), so every record has one screen
  definition. They skip the prefilter, because a named study always gets the full screen.
- **Related papers.** The 65 pairs whose first qualifying record came from the web arm got the run's
  related-paper search, and those records were screened with their earlier prefilter decisions kept.
- **Yardstick.** 100 seeded cohort pairs outside the pilot (`target_literature_yardstick.csv`), with a different
  prompt (start from reviews, follow citations both ways, prefer full text) and a different model. Sonnet 5
  answered 74 pairs. Opus 5 answered the 26 where Sonnet 5 ran past 900 s.
  - **Both arms and the yardstick are LLM web searches, so the yardstick is not fully independent of the web arm.**

## Recall against the yardstick

Recall is the share of the yardstick's verified studies (393 across the kinds) that are among the records counting
for the kind after the screen.

| Kind | Yardstick studies (verified) | Abstract run | Web arm | Union | Phase 2 coverage (union) |
|---|---|---|---|---|---|
| Perturbation in primary cells or tissue | 70 (34) | 38% | 15% | 38% | 37% |
| Perturbation in a cell line | 125 (88) | 60% | 42% | 60% | 53% |
| Protein differs in patients' tissue | 119 (79) | 66% | 41% | 67% | 55% |
| Animal model pharmacology, any agent | 118 (81) | 53% | 28% | 56% | 66% |
| Animal model pharmacology, other agents | 118 (81) | 47% | 26% | 49% | 62% |
| Knockout or transgene alters a disease model | 113 (66) | 48% | 27% | 48% | 34% |
| Observational biomarker | 63 (27) | 48% | 30% | 48% | 42% |
| Clinical observation | 64 (18) | 11% | 0% | 11% | 29% |

Counting unverified yardstick studies as misses, recall is lower still: 3–45% for the union.
`target_literature_web.json` has both figures. κ is unchanged from the run (0.62–0.77; clinical observation 0.44),
because the screen is the same.

**Where the recall goes.** On the 100 yardstick pairs:
- **The abstract run already retrieved 77% of the yardstick's verified studies,** under any kind.
- **The web arm named 44% of them.** 83% of what it named, the abstract run had already retrieved.
- **The loss is mostly after retrieval.** Of the yardstick studies either arm retrieved, 75% count for some kind
  after the screen. The rest the screen reads as another disease, not original data, or a different kind than the
  yardstick's.

So once identifiers are verified, retrieval is no longer the main bottleneck. The rest is the screen and the
reference disagreeing about what counts. Two independent web searches by models also overlap only partly.

## Pairs gained

These are cohort pairs with a counting record. The web arm added pairs no other source found.

| Kind | Pairs, union | Pairs from the abstract run | Only from the web arm |
|---|---|---|---|
| Perturbation in primary cells or tissue | 1,821 | 1,782 | 39 |
| Perturbation in a cell line | 2,522 | 2,492 | 30 |
| Protein differs in patients' tissue | 2,639 | 2,622 | 17 |
| Animal model pharmacology, any agent | 3,237 | 3,165 | 72 |
| Animal model pharmacology, other agents | 3,026 | 2,957 | 69 |
| Knockout or transgene alters a disease model | 1,577 | 1,552 | 25 |
| Observational biomarker | 2,108 | 2,100 | 8 |
| Clinical observation | 1,436 | 1,389 | 47 |

## Cost

**$993** at list prices:

| Item | USD |
|---|---|
| Web arm | 808 |
| Its fallback | 134 |
| Yardstick, with its fallback | 32 |
| Screening the new records | 19 |

PubMed, Europe PMC and Firecrawl calls are free. Firecrawl's credits did not move.

## Integrity (`integrity --pairs web`): all checks 0

The checks are the run's, plus three for the web arm:
- every frozen cohort pair has a web-arm search row, answered or refused;
- every verified web study has its hit;
- every web hit has a verified study.

| Count | Value |
|---|---|
| Retrieved (pair, record) | 1,113,746, of which `web_agent` 24,053 |
| Screen rows | 950,754 |
| Records refused by both screen models (unread) | 254 |
| Retrieved records without stored text | 0 |

## The cohort snapshot

Session predictive-validity-6e was rebuilding programs and pairs (#185) during this run. The web arm searched the
frozen snapshot above. Nothing stored keys on program ids. Program drug names reach the model prompts only as
context, and `web-score` reads the stored screen rows rather than rebuilding those prompts.

At 06:45 UTC, mid-rebuild, the live cohort had 5,142 pairs against the snapshot's 5,149:
- 10 snapshot pairs had dropped out, 3 pairs were new, and 10 cutoffs had moved;
- the dropped pairs' rows are kept;
- reconcile once 6e's rebuild is done.
