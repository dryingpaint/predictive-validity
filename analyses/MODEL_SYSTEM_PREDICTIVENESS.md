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

## Headline result

Split cell/animal evidence into three tiers by how "mechanistic" it is, and measure
Relative Success (RS = P(approved | evidence) ÷ P(approved | none)) **raw** vs.
**date-cleaned** (evidence required to predate the trial). Genetics RS ≈ 1.44–1.98 is
the benchmark.

**The more a cell/animal measure looks predictive raw, the more of it is hindsight.**

| Tier | Measure | Raw RS | Date-clean RS | Read |
|---|---|---|---|---|
| **Drug-efficacy** (does *this drug* work in the model) | drug cell efficacy (rubric) | **2.70** | — | rubric can't be dated (no PMIDs stored) |
| | drug rodent / non-rodent efficacy (rubric) | 2.01 / 2.98 | — | " |
| | **pre-first-trial preclinical evidence (PubMed)** | — | **0.81** [0.75,0.87] | date-clean measure: the huge raw signal **vanishes** |
| **Literature** (is there a cell/animal paper) | cell literature (line_c) | 1.83 | **1.40** [1.33,1.46] | ~half was hindsight |
| | animal literature (line_d) | 1.63 | **1.21** [1.15,1.27] | ~two-thirds was hindsight; nearly null |
| **Structural** (causal-perturbation screens) | DepMap essentiality | **0.24** | (snapshot) | a *liability* — essential genes make bad targets |
| | IMPC KO phenotypes / OT animal-model | 1.11 / 1.17 | (snapshot) | modest |

The field's flagship preclinical deliverable — *"the drug worked in our model"* —
looks like the **single strongest predictor of anything** (RS ~2.7–3.0, above
genetics). But that is almost entirely leakage: a date-clean measure of whether
genuinely pre-trial preclinical evidence existed gives **RS 0.81** — no positive
association with approval at all. Genetics, which is structural and hard to
retro-fit, holds. See `data/nuance_dateclean_collapse*` and `nuance_tier_overview*`.

## Method

- **Unit:** program (drug × target × indication; Phase 2+; has `first_trial_date` +
  outcome). RS with 2–3k bootstrap CIs.
- **Two cutoffs** (per the spec): **strict** = before `first_trial_date` (what was
  known before humans); **loose** = before `last_trial_date` (pre-final-readout).
  Evidence not positively datable to before the line is treated as absent
  (conservative). The loose numbers sit between raw and strict, as expected
  (cell 1.83 → loose 1.52 → strict 1.40).

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
