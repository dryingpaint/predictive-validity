# Trial failure modes (Section 1)

Factual reference. Prose lives in the post.

## Figures

| File | What it shows |
|---|---|
| `data/failure_modes_holistic.png` (+`.svg`) | **Main chart.** Program-level "why did the drug fail?" — 35,800 Ph2+ programs that never reached approval. Fold-in of silent efficacy failures (Ph3 completed, no approval) and Ph2 stalls that the terminations chart misses. |
| `data/failure_modes_terminations.png` (+`.svg`) | Stephen's original — 5,510 trials terminated early, split by *stated* reason. Comparable to Cook 2014 and BIO analyses. |
| `data/failure_modes_comparison.png` (+`.svg`) | Both charts side-by-side. Makes the point directly: terminations report 61% business / 18% biology, holistic reports 15% business / 79% biology. |
| `data/failure_modes_stratified.png` (+`.svg`) | Holistic view stratified by therapeutic area and by drug modality (small-molecule / antibody / protein / ADC / oligonucleotide). |

## Denominators — what's in vs. out

**Universe.** Every CT.gov industry-sponsored Phase 1–3 drug/biological trial with `start_date` 2015-01-01 → 2025-12-31: **41,836 trials**.

**In our cohort (`preclin.program_trial`)**: **28,193 trials** (67% of the universe). The gap of ~13,600 trials are ones we couldn't resolve to a canonical (drug × indication × sponsor) tuple — either the intervention couldn't be mapped to a known drug, or it was a placebo-only / device / procedure arm. These are excluded silently; if the missing 33% is enriched for any particular failure mode, the picture is biased. Best guess: enriched for oncology combinations (dozens of interventions per trial, hard to normalize) and early academic-industry collaborations (weaker drug metadata). Neither should systematically distort the biology / business ratio.

**Trial status in our cohort:** 21,800 completed · 5,537 terminated/withdrawn/suspended · ~800 still running or unknown.

### Terminations chart (5,510 trials)

Denominator: every trial in our cohort with a `why_stopped` classification from Claude Sonnet or Haiku (Sonnet preferred where both exist). Practically this is 4,043 `TERMINATED` + 1,165 `WITHDRAWN` + 109 `SUSPENDED` + a small tail of trials with a stated stop reason despite a non-terminal status.

**What this cut *does not* include** — the reason it under-counts efficacy:
- **Completed trials that missed their endpoint.** A negative Phase 3 that ran to completion is not a "termination." There is no `why_stopped` row for it because the trial didn't stop early.
- **Programs that completed Phase 2 and were quietly dropped.** Same reason: no early stop.
- **Sponsor euphemism.** The `commercial_strategic` bucket (44% of terminations) is known from prior work (Cook 2014) to absorb quiet efficacy failures — sponsors write "portfolio prioritization" rather than "did not work."

### Holistic chart (35,800 programs)

Denominator: every **program** (drug × indication × sponsor tuple, `preclin.program`) whose `highest_phase >= 2` and `outcome_broad != 'approved'` — i.e., every drug attempt that reached Phase 2 or beyond and did not result in an approval.

Excluded from this denominator:
- **Ph1-only stalls** (26,301 programs). Half of Ph1 attrition is pipeline reprioritization rather than a real clinical failure signal. Including them would swamp the chart in noise; a program that never left Ph1 tells you very little about the drug.
- **`unknown` outcome** with no phase reached (5,532 programs). Programs where we couldn't determine even the highest phase.

### Bucketing rule (holistic chart)

Per program, in priority order:

1. **Biology, direct signal** — any linked trial classified as `efficacy` / `safety` / `pk_pd_formulation` in `why_stopped` (Sonnet-preferred).
2. **Silent efficacy (Ph3 complete, no approval)** — `outcome_broad = 'presumptive_efficacy_fail_ph3'`. Strong biology inference: a completed Ph3 followed by no approval is efficacy or safety ~90%+ of the time in the industry.
3. **Ph2 stall (Ph2 complete, program halted)** — `outcome_broad = 'presumptive_fail_ph2'`. Weaker inference (could be pipeline decision), so shown with hatched fill on the chart. Industry Ph2→Ph3 transitions are typically efficacy-gated, so still tagged biology, but reader should discount.
4. **Business & operational** — commercial / enrollment / regulatory / competitive / manufacturing signals, from either the trial-level classifier or `outcome_broad`.
5. **Other** — planned / unclassified / unknown / COVID.

Trial-level reasons take precedence over program-level outcome inference (an explicitly-stated efficacy failure beats a "we couldn't figure it out" bucket). Silent efficacy is only invoked when no explicit reason exists.

## Stratification

**By therapeutic area** — `preclin.indication.therapeutic_area`, curated from CT.gov `conditions` strings. Populated for 100% of programs, though 54% land in `other` (mixed / rare / hard-to-categorize conditions). The seven named areas each have 100+ failed Ph2+ programs.

**By modality** — populated for 6,694 / 35,800 failed programs (19%). Sources, in preference order: `preclin.drug.modality` (curated from `approvals.csv`, biased toward approved drugs), `public.therapies.modality` matched by ChEMBL ID, then by normalized name. Only modalities with ≥50 failed programs shown (small mol · antibody · ADC · protein · peptide · oligonucleotide). **Caveat:** modality-known drugs skew toward well-characterized chemistry, so cell / gene / mRNA therapies are almost certainly under-represented in the plot.

## Reproduce

```bash
# From the committed CSVs (no DB access needed):
python3 analyses/plot_failure_modes.py

# Refresh the CSVs from Neon first:
export DATABASE_URL='postgresql://…'
python3 analyses/refresh_failure_data.py
python3 analyses/plot_failure_modes.py
```

## Known limitations

- **Silent efficacy attribution is inference, not measurement.** Ph3 complete → no approval is 90%+ efficacy in industry practice, but the actual rationale is unrecorded. Similarly Ph2 stalls. If we ever run a targeted extraction pass against Ph3 results + subsequent press releases, we can replace the inference with direct classification.
- **`commercial_strategic` masking.** Only 805 / 2,434 commercial-strategic classifier calls are high-confidence in the trial-level data. The holistic view partially corrects for this (silent-efficacy Ph3 fails outrank commercial in the ordering rule), but a program with mixed trial reasons still lands in whichever family got the first hit.
- **Modality coverage is skewed.** Small mol and antibody are well-populated; cell / gene / mRNA therapies are sparse in the failed cohort because our modality metadata comes mostly from approvals.
- **Non-CT.gov trials excluded.** ChiCTR (~70K), EU-CTR (~35K), and CTIS are not ingested. Sponsors that mostly file outside CT.gov (Chinese biotechs, some EU academic-industry) are under-weighted.
