# `nelson_tier` is a leaked feature — diagnosis, impact, and two fix paths

**TL;DR:** `nelson_tier` was only ever populated for a curated subset of T-I pairs, and that subset is
drawn from case-series of already-known/approved drugs. So the *presence* of any tier annotation is a
near-perfect proxy for "this is a known successful program," and the trained models put a large weight
on it. Assigning **any** tier (even `T0`, nominally "no genetic evidence") to a novel target inflates
its predicted approval probability to ~0.9-0.99, regardless of the actual biology. This doc diagnoses
it, quantifies it, and lays out the two ways to fix it.

Reproducing diagnostic: `analyses/nelson_tier_leakage_demo.py`.

## The evidence

In the strict Phase 2+ training cohort, `nelson_tier` is null for **97.4%** of rows (7,922 / 8,130),
which sit at the ~2.5-5% base approval rate. The tiny annotated minority looks like this:

| `nelson_tier` | # pairs | approval rate |
|---|---:|---:|
| (null) | 7,922 | ~2.5% |
| T0 | 67 | **97.0%** |
| T1 | 65 | **100%** |
| T2 | 36 | **100%** |
| T3 | 11 | 90.9% |
| T4 | 28 | 96.4% |

**T0 — the weakest tier, nominally "no genetic evidence" — sits at 97% approval.** That is not a
biological signal. It is a selection artifact: the tiers were only curated onto pairs pulled from
lists of known drugs, so "has a tier at all" ≈ "was a known drug."

## The impact on scoring a novel target

Feature vector for a genuinely preclinical target (SIK3), fully credited with its real genetic
evidence, scored every way the repo offers — with and without a tier assigned:

| Model | `nelson_tier` unset | `nelson_tier` = T0 |
|---|---:|---:|
| logreg (L2) | 0.055 | **0.995** |
| logreg (isotonic-calibrated) | 0.005 | 0.926 |
| randomforest | 0.31 | 0.59 |

Without a tier, the pair maxes out around 0.31 across all models. Set `T0` — the choice that *feels*
conservative — and it rockets to ~0.99 on the linear models. The stacked ensemble (which averages
these) lands around ~0.76 with a tier set, which is how a novel target can appear to be a top-decile
bet purely from the annotation.

**The trap is specifically `T0`:** an analyst reaching for "the pair has no genetic evidence yet, so
I'll set the lowest tier" is doing the exact thing that trips the leak, because in this data `T0`
does not mean "no evidence predicts failure" — it means "a curator who only looked at known drugs
assigned this one the lowest grade."

## Why this may also affect the headline AUC claim

`RESULTS.md` reports that genetic evidence accounts for ~18pp of the model's AUC. Some unknown fraction
of that could be `nelson_tier`'s presence/absence leaking outcome rather than tier *value* carrying
genetic signal. Worth an ablation: retrain with `nelson_tier` dropped and see how much of the 18pp
survives. If a lot does, the genetics claim is robust; if a chunk evaporates, part of it was leakage.

## Two fix paths

The leak is not in `nelson_tier` the concept — it's in the *selective* population. Two ways out:

### Path A — drop it and retrain (low effort, recommended default)
Remove `nelson_tier` from the feature set (`NUMERIC/BOOL/one-hot` construction in `scorers_ml.py`) and
retrain. This removes the leak cleanly. **Cost is low because the tier is largely redundant with
features already in the model** — `mendelian_n`, `ot_genetic_max`, `clingen_n_strong`, `gwas_n_sig`
are the raw components a Nelson tier is a hand-weighted composite of. You lose little real signal.

### Path B — populate it systematically and retrain (higher effort, only if you want direction-concordance)
Compute a real tier for **every** T-I pair by one uniform rule, so "has a tier" becomes true of
everything and stops carrying information; then the tier *value* carries the legitimate Nelson signal.
Two hard requirements, both easy to skip:

1. **Uniform rule, pre-outcome evidence only.** Every pair — all ~13k training pairs *and* any novel
   target being scored — must get its tier from the identical rule, using only evidence that predates
   the outcome. Inconsistent application, or deriving the tier from anything that knows the drug
   succeeded, just rebuilds the leak in a new shape.
2. **Retrain.** The currently-trained models have the leaky weights baked in. Repopulating the column
   does nothing until the models are retrained on the honest distribution. Populate-without-retrain =
   zero effect.

**Only worth Path B if the tier is direction-aware.** A plain genetic-strength tier is redundant with
the raw features above. The one thing a Nelson tier adds that the raw counts don't is **direction
concordance** — does the drug's mechanism direction (agonist/antagonist, activator/inhibitor) match
the genetic loss-/gain-of-function direction? That's a real, non-redundant signal (e.g., a SIK3
*inhibitor* mimicking the N783Y loss-of-function short-sleep direction should score higher than one
that opposes it). If you populate, populate a direction-aware tier; a plain one isn't worth the work.

## Recommendation
Default to **Path A** (drop + retrain) — it removes the distortion for near-zero cost. Do **Path B**
only if you specifically want to model MoA-vs-genetic direction concordance, and only as a direction-
aware tier applied uniformly with a retrain. Either way, run the drop-and-retrain ablation first to
quantify how much of the reported genetics-AUC is real signal vs. this leak.

## Interim guidance for anyone scoring novel targets today
Until this is fixed in the model: **leave `nelson_tier` unset** when scoring any target/indication not
already in the curated known-drug set (i.e. essentially all preclinical targets). Setting it — even to
`T0` — produces a leakage artifact, not a prediction.
