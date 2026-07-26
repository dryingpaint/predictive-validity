# What preclinical models predict — and how much is hindsight (Section 5 "nuance")

**The question:** which kinds of in vitro (cell) and in vivo (animal) evidence
actually predict clinical approval — and how much of any apparent predictive power
survives once we require the evidence to have existed *before* the trial?

**The thesis:** preclinical models certify **mechanism engagement** ("the drug does
the expected thing to the biology"), not **disease causality** ("that mechanism is
the right lever for the human endpoint"). So predictiveness tracks how
*mechanism-proximal* a disease is — near-deterministic where the model reads out the
literal disease mechanism (CF: a CFTR channelopathy), collapsing where the mechanism
is far from the clinical endpoint (Alzheimer's), at any level of model sophistication.

We are **not** ranking model types (organoid > primary > immortalized). The data
can't support it and it's disease-specific — see the design spec's out-of-scope note.

## Correction (2026-07-26)

Three data artifacts in the original version were found and fixed (independently
cross-checked in an audit + PR #12/#13). All numbers/readings below are the corrected ones.

1. **De-duplication.** `preclin.evidence_score` carries ~4 rows per (subject, dimension)
   from repeated ingest jobs (line_c/d = 4.02×, drug dims = 3.61×); the original
   left-merges fanned out and distorted RS. Fixed by de-duplicating before merging. (The
   duplicates are *mostly* identical, but ~12/579 targets per line disagree on
   score/citations — `keep="first"`/max resolves those, a small documented tie-break.)
2. **Scored-vs-unscored selection (BOTH tiers).** Only 579 of ~951 Ph2+ targets were
   ever LLM-scored, and only a few hundred drugs carry the efficacy rubric. Left-joining
   onto the full cohort dumped never-scored targets/drugs (lower baseline approval) into
   "not supported", deflating the baseline and inflating RS. Fixed by inner-joining to
   the scored subset on **both** tiers (an earlier pass fixed only the drug tier — the
   literature tier is corrected here). Effect:
   - drug cell 2.70 → **1.54**, non-rodent 2.98 → **1.82** (raw, scored subset)
   - cell literature date-clean → **1.26**, animal → **1.09** (was left-join-inflated 1.75 / 1.54)
3. **Genetics band relabeled.** The comparator is the true spread of genetics RS
   dimensions — **1.12–1.98** (GWAS 1.12, OT-genetic 1.14, Mendelian 1.49, ClinGen 1.74,
   OT-somatic 1.98) — not the earlier cherry-picked "1.44–1.98".

**What survives:** the thesis is unchanged and cleaner. Apparent preclinical-efficacy
signal collapses under date-cleaning (drug pre-trial RS 0.81; animal literature dated
1.09 = null). Dated cell/animal literature (~1.1–1.3) overlaps only the *weakest*
genetics signals (GWAS/OT-genetic ~1.1) and sits below causal genetics (Mendelian/
ClinGen 1.5–1.7). And genetics dominance rests on the multivariate **ablation**
(−17.7pp AUC), not these univariate RS values, so it is unaffected regardless.
**Residual-leakage caveat:** date-cleaning only requires that *one cited paper* predate
the trial; the 0–3 score magnitude was still assigned in 2026 with full-literature
hindsight, so even the dated RS is an upper bound. PR #12 is the authoritative
literature time-slice; PR #13 the drug-efficacy dated re-score.

## Headline result

Split cell/animal evidence into three tiers by how "mechanistic" it is, and measure
Relative Success (RS = P(approved | evidence) ÷ P(approved | none)) **raw** vs.
**date-cleaned** (evidence required to predate the trial). The benchmark is the spread
of genetics RS: **≈1.12–1.98** — weak signals (GWAS 1.12, OT-genetic 1.14) at the
bottom, causal genetics (Mendelian 1.49, ClinGen 1.74) in the middle, OT-somatic 1.98
on top.

**The more a cell/animal measure looks predictive raw, the more of it is hindsight.**

| Tier | Measure | Raw RS | Date-clean RS | Read |
|---|---|---|---|---|
| **Drug-efficacy** (does *this drug* work in the model) | drug cell efficacy (rubric, scored subset) | **1.54** | — | rubric can't be dated (no PMIDs stored) |
| | drug rodent / non-rodent efficacy (rubric, scored subset) | 1.28 / 1.82 | — | " |
| | **pre-first-trial preclinical evidence (PubMed)** | — | **0.81** [0.75,0.87] | date-clean measure: the raw signal collapses to null |
| **Literature** (cell/animal paper, scored subset) | cell literature (line_c) | 1.40 | **1.26** [1.14,1.39] | mostly real, but at the weakest-genetics level |
| | animal literature (line_d) | 1.25 | **1.09** [0.98,1.20] | collapses to null when dated |
| **Structural** (causal-perturbation screens) | DepMap essentiality | **0.24** | (snapshot) | a *liability* — essential genes make bad targets |
| | IMPC KO phenotypes / OT animal-model | 1.11 / 1.17 | (snapshot) | modest |

The field's flagship preclinical deliverable — *"the drug worked in our model"* —
looks predictive raw (drug-efficacy RS ~1.5–1.8, scored subset) but does not reproduce
under date-cleaning: whether genuinely pre-trial preclinical evidence existed gives
**RS 0.81** — no positive association with approval. Cell/animal *literature*, once
restricted to scored targets and dated, lands at ~1.1–1.3 (animal null) — the level of
the *weakest* genetics signals, below causal genetics. Nothing on the cell/animal side,
cleaned, reaches the strong-genetics tier — and the genetics dominance result rests on
the multivariate ablation (−17.7pp AUC) regardless. See `data/nuance_dateclean_collapse*`
and `nuance_tier_overview*`.

## Method

- **Unit:** program (drug × target × indication; Phase 2+; has `first_trial_date` +
  outcome). RS with 2–3k bootstrap CIs.
- **Two cutoffs** (per the spec): **strict** = before `first_trial_date` (what was
  known before humans); **loose** = before `last_trial_date` (pre-final-readout).
  Evidence not positively datable to before the line is treated as absent
  (conservative). The loose numbers sit between raw and strict, as expected
  (cell 1.40 → loose 1.30 → strict 1.26).

### Tier 1 — literature (`nuance_literature_dateclean.py`)
`line_c_lit` / `line_d_lit` are the only cell/animal dims with stored citations.
PMIDs → publication year via NCBI eutils; a target's "high" support (score ≥2) is
kept in the cleaned versions only if ≥1 cited paper predates the program's cutoff.
**Data-quality finding:** the stored `citation_pmids` are *polluted* — a mix of real
PMIDs, raw DOIs, and free-text citations — so even this tier is only partly datable
(2,390 / 3,618 high-score targets have a datable citation; the rest are conservatively
dropped in the cleaned versions). Undatable free-text/DOI citations get a year by
regex where one is embedded.

### Tier 2 — drug-efficacy (`nuance_drug_and_structural.py`)
Melissa's `drug_*_efficacy` rubric scores store **no PMIDs**, so they can't be dated
in place. Raw RS is reported (contaminated). The date-clean measure is different:
per program-linked drug, a PubMed search for any preclinical (cell/animal) paper on
that drug published **before its first trial**; RS of that presence.
**Honest caveat:** rubric-score and paper-presence are *different metrics*, so the
2.70 → 0.81 drop is date **plus** metric change — the correct claim is "the huge raw
rubric number does not reproduce under any date-clean measure," not a clean
apples-to-apples date delta. The paper-presence proxy is crude (drug-name
disambiguation; abstract indexing) — searchable for 2,456 programs.

### Tier 3 — structural (`nuance_drug_and_structural.py`)
DepMap / IMPC / OT-animal RS straight from `v_relative_success_clean`. These are
**present-day snapshots** (IMPC is stamped as a flat 2025 release; DepMap/OT are
undated), so they carry hindsight of a subtler kind — the *screen* may postdate the
trial. Applied here: a resource-existence floor (DepMap/IMPC/OT ~2016; 86% of
programs started ≥2016, and IMPC's 2025 snapshot postdates the whole cohort). **The
full per-gene versioned re-pull of dated DepMap/IMPC/OT releases — the rigorous
treatment — is specified but not run here:** it needs multi-hundred-MB historical
release downloads this environment can't safely hold. It is the top follow-up.

## The exception that proves the thesis: CF organoids

Where a model reads out the *literal disease mechanism*, it is extraordinarily
predictive. In cystic fibrosis — a monogenic channelopathy — the forskolin-induced
swelling (FIS) assay in patient-derived intestinal organoids measures CFTR channel
function directly, i.e. the exact thing a modulator fixes. FIS response has been used
to grant CFTR-modulator access to people with ultra-rare genotypes too infrequent to
trial. This isn't organoid magic; it's that in CF, mechanism-engagement and
disease-causality collapse into one measurement — the monogenic case the thesis
predicts. **Honest nuance:** even here, *individual* long-term clinical prediction is
imperfect — in a real-world F508del cohort, FIS did not reliably predict individual
ppFEV1 decline (according to PubMed, Muilwijk et al., *J Pers Med* 2021,
[DOI](https://doi.org/10.3390/jpm11121376)). The assay is near-deterministic for the
*biochemical* mechanism; translating that to individual long-term outcomes still has
slack. You cannot build the CF-organoid equivalent for schizophrenia or Alzheimer's
at any sophistication, because in those diseases the molecular mechanism is far from
the endpoint — which is exactly why no cell/animal tier here approaches genetics.

## What this bounds (not contradicts)

Section 2 found cell/animal add ~0 marginal over genetics in the multivariate
ablation. This explains *why*: most cell/animal signal is either a proxy (structural,
modest) or hindsight (literature/drug-efficacy, collapses when dated). It does **not**
say models are worthless — it says a model de-risks the *mechanism-engagement* step
only, and is trustworthy in proportion to how tightly the model's readout sits on a
causally-validated path to the human endpoint. That is the same causal chain genetics
speaks to — which is why, on average, genetics wins.

## Reproduce

```bash
DATABASE_URL=... python3 analyses/nuance_literature_dateclean.py   # Tier 1 (eutils dates)
DATABASE_URL=... python3 analyses/nuance_drug_and_structural.py    # Tiers 2-3 (PubMed search)
python3 analyses/plot_nuance_dateclean.py                          # figures
```
Cached intermediates: `data/pmid_pubyear.csv`, `data/drug_pretrial_pubmed.csv`.
Results: `data/nuance_literature_dateclean.csv`, `data/nuance_drug_structural.csv`.

## Limitations (read before citing)

- Structural tier is present-day snapshots; full versioned re-pull is the key TODO.
- Drug-efficacy date-clean is a paper-presence proxy, not Melissa's 0–3 rubric dated.
- `citation_pmids` pollution limits literature-tier datability to ~66% of high-score targets.
- Present-day genetics benchmark (hindsight), consistent with PR #3/#4/#6/#8 disclosures.
- CF-organoid synthesis is curated literature, not from her DB.
