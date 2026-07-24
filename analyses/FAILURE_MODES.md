# Trial failure modes (Section 1)

Factual reference. Prose lives in the post.

## Figures

| File | What it shows |
|---|---|
| `data/failure_modes_main.png` (+`.svg`) | **Main chart** — three-panel composite. **A)** attrition through the pipeline (60k Ph1 entrants → 32k Ph2 → 15k Ph3 → 5.4k approved). **B)** overall failure reasons over 55k Ph1+ programs terminated by 2026, ranked. **C)** the same reasons split by which phase the program stalled at. |
| `data/failure_modes_terminations.png` (+`.svg`) | Stephen's original — 5,510 trials terminated early, split by *stated* reason. Comparable to Cook 2014 and BIO analyses. Kept as a companion to show what the terminations-only lens hides. |
| `data/failure_modes_stratified.png` (+`.svg`) | Holistic view stratified by therapeutic area and by drug modality (small mol / antibody / protein / ADC / oligonucleotide / peptide). |

## Universe and cohort

**Universe.** Every CT.gov industry-sponsored Phase 1–3 drug/biological trial with `start_date` 2015-01-01 → 2025-12-31: **41,836 trials**.

**In our cohort (`preclin.program_trial`)**: **28,193 trials** (67% of the universe). The gap of ~13,600 trials are ones we couldn't resolve to a canonical (drug × indication × sponsor) tuple — either the intervention couldn't be mapped to a known drug, or it was a placebo-only / device / procedure arm.

**Trial status in cohort:** 21,800 completed · 5,537 terminated/withdrawn/suspended · ~800 still running or unknown.

## Denominator: "terminated by 2026"

The main-chart denominator restricts to programs whose fate is settled — advanced-to-approval or definitively-stopped — matching BIO's `advanced / (advanced + suspended)` methodology. A program qualifies as terminated by 2026 if **all** of:

1. No currently-active trial (no status `RECRUITING` / `ACTIVE_NOT_RECRUITING` / `ENROLLING_BY_INVITATION` / `NOT_YET_RECRUITING`).
2. `outcome_broad != 'unknown'` — we could determine what happened.
3. Either explicit outcome (`approved` / `efficacy_fail` / `safety_fail` / `commercial_fail` / `enrollment_fail` / `unclassified_termination` / `planned_termination`), **or** presumptive outcome (`phase1_only` / `presumptive_fail_ph2` / `presumptive_efficacy_fail_ph3`) with last trial activity ≥ 18 months ago (`latest_date < 2024-07-01`, given today is 2026-07-24). The 18-month window is a rough gate for how long a sponsor typically takes to advance-or-suspend after a phase reads out.

Removes ~14k programs vs. the raw Ph1+ pool: 8k with active trials, 5.9k with `unknown` outcome, some presumptive-fails with recent activity.

## Comparison to published benchmarks

BIO 2021 (Thomas et al., *Clinical Development Success Rates 2011–2020*, n=12,728 phase transitions from Biomedtracker) is the closest published comparator. Their methodology: analyst-curated tracking of US-market FDA-registration-enabling programs, transition = advanced-or-suspended.

| Metric | BIO 2011-2020 | Us 2015-2025 (terminated-by-2026) |
|---|---|---|
| Ph1 → Ph2 | 52.0% | 53.3% |
| Ph2 → Ph3 | 28.9% | 46.8% |
| Ph3 → Approval | 52.4% (composed) | 18.9% |
| **Ph1 → Approval** | **7.9%** | **9.0%** |

- **Ph1 → Ph2** and **Ph1 → approval** match BIO within a point. Load-bearing.
- **Ph2 → Ph3** and **Ph3 → approval** are structurally off. The "terminated by 2026" filter closes some of the gap (Ph3→approval went from 16% → 19%) but the residual is CT.gov cohort composition: our Ph3 denominator includes label-extension Ph3b/c trials, non-US-market programs, Phase 2/3 combined designations, and investigator-initiated confirmatory trials — all of which BIO filters out. At **drug** level (deduplicating indications), our Ph3→approval is ~8% vs. BIO's ~52%.
- **Failure reason** breakdown is not published in BIO 2021; the closest benchmarks are Cook 2014 (AstraZeneca) and DiMasi 2013/2020. Cook says Ph3 fails are ~66% efficacy, ~21% safety, ~8% strategic — shape matches ours once silent-efficacy is folded in.

Bottom line: the headline Ph1→approval number is credible. Middle-phase transition rates should be caveated with "our cohort is broader than BIO's; drug-level rates converge."

## Chart details

### Terminations chart (`failure_modes_terminations.png`, 5,510 trials)

Trial-level, `why_stopped` classifications from Claude Sonnet or Haiku (Sonnet preferred). Kept as a companion because it shows the sponsor-euphemism problem: 44% of stated reasons are `commercial_strategic`, which Cook 2014 shows absorbs quiet efficacy failures.

### Main chart (`failure_modes_main.png`)

**Panel A — attrition.** Cohort funnel among terminated-by-2026 programs: 60,070 Ph1 → 32,015 Ph2 (53%) → 14,993 Ph3 (25%) → 5,436 approved (9%). See benchmark comparison above.

**Panel B — overall failure reasons.** Denominator: 55,133 Ph1+ programs terminated by 2026 that didn't reach approval. No arbitrary phase cutoff — Ph1 stalls kept as their own explicit bucket. Family shares: 40% biology · 17% business & operational · 43% other/undisclosed (dominated by Ph1 stall).

**Panel C — reasons by phase failed at.** Composition shifts predictably as programs advance:
- **Ph1 fails** (n=26,841): 76% Ph1 stall (ambiguous — Ph1 tests safety/PK, most stalls are pipeline decisions).
- **Ph2 fails** (n=16,139): 66% Ph2 stall (biology-soft, hatched). Ph2→Ph3 is efficacy-gated.
- **Ph3 fails** (n=12,153): 73% Silent efficacy Ph3 (strong biology). Ph3 complete → no approval is efficacy or safety ~90% of the time.

### Bucketing rule

Per program, in priority order:

1. **Biology, direct signal** — trial classified `efficacy` / `safety` / `pk_pd_formulation` in `why_stopped` (Sonnet-preferred).
2. **Silent efficacy (Ph3 complete, no approval)** — `outcome_broad = 'presumptive_efficacy_fail_ph3'`. Strong biology inference.
3. **Ph2 stall (Ph2 complete, program halted)** — `outcome_broad = 'presumptive_fail_ph2'`. Efficacy-gated, biology-soft, hatched.
4. **Ph1 stall (Ph1 complete, program halted)** — `outcome_broad = 'phase1_only'`. Ph1 doesn't test efficacy, tagged ambiguous, hatched.
5. **Business & operational** — commercial / enrollment / regulatory / competitive / manufacturing / covid.
6. **Other** — planned / unclassified.

Trial-level reasons take precedence over program-level outcome inference. Silent / stall buckets only invoked when no explicit reason exists.

## Stratification (companion figure)

**By therapeutic area** — `preclin.indication.therapeutic_area`, curated from CT.gov `conditions`. Populated for 100% of programs, 54% land in `other`. Seven named areas each have 100+ failed programs.

**By modality** — populated for 10,172 / 55,133 failed programs (18%). Sources, preference order: `preclin.drug.modality` (curated from `approvals.csv`, biased toward approved drugs), `public.therapies.modality` matched by ChEMBL ID or normalized name. Only modalities with ≥50 failed programs shown. **Caveat:** modality-known drugs skew toward well-characterized chemistry — cell / gene / mRNA therapies are under-represented.

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

- **Silent efficacy is inference, not measurement.** Ph3 complete → no approval is ~90% efficacy in industry practice, but the rationale is unrecorded. Same for Ph2 stalls.
- **Ph1 stalls carry weak biology signal.** Ph1 tests safety/PK, so a Ph1 stall is mostly pipeline decision. We tag them ambiguous. Still 76% of Ph1 fails — half of Ph1 entrants never advance.
- **Cohort broader than BIO.** We include label-extension Ph3s, non-US programs, and investigator-initiated confirmatory trials. Inflates Ph3 denominator and drags the transition rate down. Drug-level rates converge.
- **18-month cutoff is a heuristic.** Some programs classified as "terminated by 2026" may re-emerge (e.g., a sponsor decides to reformulate); some excluded as "still active" may quietly die without a status update.
- **`commercial_strategic` masking.** Only 805 / 2,434 commercial-strategic classifier calls are high-confidence — the holistic view partially corrects (silent-efficacy Ph3 outranks commercial), but a program with mixed trial reasons lands wherever the priority rule matches first.
- **Modality skewed.** Small mol and antibody well-populated; cell / gene / mRNA sparse.
- **Non-CT.gov trials excluded.** ChiCTR (~70K), EU-CTR (~35K), CTIS not ingested. Chinese biotechs under-weighted.

## References

- Thomas D, Chancellor D, Micklus A, LaFever S, Hay M, Chaudhuri S, Bowden R, Lo AW (2021). *Clinical Development Success Rates and Contributing Factors 2011–2020*. BIO / QLS Advisors / Informa Pharma Intelligence.
- Cook D, Brown D, Alexander R, March R, Morgan P, Satterthwaite G, Pangalos MN (2014). Lessons learned from the fate of AstraZeneca's drug pipeline: a five-dimensional framework. *Nature Reviews Drug Discovery* 13, 419–431.
- Wong CH, Siah KW, Lo AW (2019). Estimation of clinical trial success rates and related parameters. *Biostatistics* 20, 273–286.
