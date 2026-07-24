# Trial failure modes (Section 1)

Factual reference. Prose lives in the post.

## Figures

| File | What it shows |
|---|---|
| `data/failure_modes_main.png` (+`.svg`) | **Main chart** — three-panel composite. **A)** attrition through the pipeline (74k Ph1 entrants → 40k Ph2 → 18k Ph3 → 5.7k approved). **B)** overall failure reasons over all 69k Ph1+ programs that never reached approval, ranked. **C)** the same reasons split by which phase the program stalled at. |
| `data/failure_modes_terminations.png` (+`.svg`) | Stephen's original — 5,510 trials terminated early, split by *stated* reason. Comparable to Cook 2014 and BIO analyses. Kept as a companion to show what the terminations-only lens hides. |
| `data/failure_modes_stratified.png` (+`.svg`) | Holistic view stratified by therapeutic area and by drug modality (small mol / antibody / protein / ADC / oligonucleotide / peptide). |

## Denominators — what's in vs. out

**Universe.** Every CT.gov industry-sponsored Phase 1–3 drug/biological trial with `start_date` 2015-01-01 → 2025-12-31: **41,836 trials**.

**In our cohort (`preclin.program_trial`)**: **28,193 trials** (67% of the universe). The gap of ~13,600 trials are ones we couldn't resolve to a canonical (drug × indication × sponsor) tuple — either the intervention couldn't be mapped to a known drug, or it was a placebo-only / device / procedure arm. These are excluded silently; if the missing 33% is enriched for any particular failure mode, the picture is biased. Best guess: enriched for oncology combinations (dozens of interventions per trial, hard to normalize) and early academic-industry collaborations (weaker drug metadata). Neither should systematically distort the biology / business ratio.

**Trial status in our cohort:** 21,800 completed · 5,537 terminated/withdrawn/suspended · ~800 still running or unknown.

### Terminations chart (`failure_modes_terminations.png`, 5,510 trials)

Denominator: every trial in our cohort with a `why_stopped` classification from Claude Sonnet or Haiku (Sonnet preferred where both exist). Practically this is 4,043 `TERMINATED` + 1,165 `WITHDRAWN` + 109 `SUSPENDED` + a small tail of trials with a stated stop reason despite a non-terminal status.

**What this cut *does not* include** — the reason it under-counts efficacy:
- **Completed trials that missed their endpoint.** A negative Phase 3 that ran to completion is not a "termination." There is no `why_stopped` row for it because the trial didn't stop early.
- **Programs that completed Phase 2 and were quietly dropped.** Same reason: no early stop.
- **Sponsor euphemism.** The `commercial_strategic` bucket (44% of terminations) is known from prior work (Cook 2014) to absorb quiet efficacy failures — sponsors write "portfolio prioritization" rather than "did not work."

### Main chart (`failure_modes_main.png`)

**Panel A — attrition.** Cohort funnel: programs that reached each phase, expressed as % of Ph1 entrants. Transition rates (~53% Ph1→Ph2, ~47% Ph2→Ph3, ~16% Ph3→approval) are on the low side of BIO/Wong 2019 benchmarks; the cohort skews recent (2015+ starts), so some Ph3 entrants haven't had time to read out.

**Panel B — overall failure reasons.** Denominator: every **program** (drug × indication × sponsor, `preclin.program`) with `highest_phase >= 1` and `outcome_broad != 'approved'`. That's **69,029 failed Ph1+ programs**. No arbitrary phase cutoff — Ph1 stalls kept as their own explicit bucket so readers see the composition rather than have it hidden.

**Panel C — reasons by phase failed at.** Same buckets, but conditioned on `highest_phase` (1 / 2 / 3). Composition shifts predictably as programs advance:
- **Ph1 fails** (n=33,229): 76% Ph1 stall (Ph1 tests safety/PK; most stalls here are pipeline decisions or IND-then-quiet-death). Biology inference weak — tagged ambiguous.
- **Ph2 fails** (n=20,248): 71% Ph2 stall. Ph2→Ph3 is industry-efficacy-gated, so tagged biology-soft (hatched).
- **Ph3 fails** (n=15,560): 77% Silent efficacy Ph3. A completed Ph3 followed by no approval is efficacy or safety ~90% of the time. Strongest biology inference of the three.

### Bucketing rule

Per program, in priority order:

1. **Biology, direct signal** — any linked trial classified as `efficacy` / `safety` / `pk_pd_formulation` in `why_stopped` (Sonnet-preferred).
2. **Silent efficacy (Ph3 complete, no approval)** — `outcome_broad = 'presumptive_efficacy_fail_ph3'`. Strong biology inference.
3. **Ph2 stall (Ph2 complete, program halted)** — `outcome_broad = 'presumptive_fail_ph2'`. Efficacy-gated but weaker. Tagged biology, hatched.
4. **Ph1 stall (Ph1 complete, program halted)** — `outcome_broad = 'phase1_only'`. Ph1 doesn't test efficacy, so most Ph1 stalls are pipeline decisions. Tagged ambiguous, hatched.
5. **Business & operational** — commercial / enrollment / regulatory / competitive / manufacturing / covid signals, from either the trial-level classifier or `outcome_broad`.
6. **Other** — planned / unclassified / unknown.

Trial-level reasons take precedence over program-level outcome inference — an explicitly-stated efficacy failure beats a "we couldn't figure it out" bucket. Silent / stall buckets are only invoked when no explicit reason exists.

## Stratification (companion figure)

**By therapeutic area** — `preclin.indication.therapeutic_area`, curated from CT.gov `conditions` strings. Populated for 100% of programs, though 54% land in `other` (mixed / rare / hard-to-categorize conditions). The seven named areas each have 100+ failed Ph1+ programs.

**By modality** — populated for 12,185 / 69,029 failed programs (18%). Sources, in preference order: `preclin.drug.modality` (curated from `approvals.csv`, biased toward approved drugs), `public.therapies.modality` matched by ChEMBL ID, then by normalized name. Only modalities with ≥50 failed programs shown (small mol · antibody · ADC · protein · peptide · oligonucleotide). **Caveat:** modality-known drugs skew toward well-characterized chemistry, so cell / gene / mRNA therapies are almost certainly under-represented in the plot.

## Reproduce

```bash
# From the committed CSVs (no DB access needed):
python3 analyses/plot_failure_modes.py

# Refresh the CSVs from Neon first:
export DATABASE_URL='postgresql://...'
python3 analyses/refresh_failure_data.py
python3 analyses/plot_failure_modes.py
```

## Known limitations

- **Silent efficacy attribution is inference, not measurement.** Ph3 complete → no approval is 90%+ efficacy in industry practice, but the actual rationale is unrecorded. Similarly for Ph2 stalls. If we ever run a targeted extraction pass against Ph3 results + subsequent press releases, we can replace the inference with direct classification.
- **Ph1 stalls are mostly pipeline decisions.** Ph1 does not test efficacy, so a Ph1 stall carries almost no biology signal — we tag them ambiguous. They still dominate Ph1 fails (76%) because ~half of all Ph1 entrants never advance.
- **`commercial_strategic` masking.** Only 805 / 2,434 commercial-strategic classifier calls are high-confidence in the trial-level data. The holistic view partially corrects (silent-efficacy Ph3 outranks commercial in the priority rule), but a program with mixed trial reasons still lands in whichever family got the first hit.
- **Modality coverage is skewed.** Small mol and antibody are well-populated; cell / gene / mRNA therapies are sparse because our modality metadata comes mostly from approvals.
- **Non-CT.gov trials excluded.** ChiCTR (~70K), EU-CTR (~35K), and CTIS are not ingested. Sponsors that mostly file outside CT.gov (Chinese biotechs, some EU academic-industry) are under-weighted.
- **Attrition rates skew low.** Cohort is 2015+ start-date, so some Ph3 entrants are still active or too recent to have read out. Real transition rates will settle a few points higher over time.
