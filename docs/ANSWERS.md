# Preclinical Evidence → Clinical Efficacy: Answers to the 5 Core Questions

**Comprehensive dataset:** `drug_evidence_master_v2_enriched.csv` — **30,517 unique drug programs**, every industry Phase 1–3 drug/biological trial 2015–2025 (approved + not-approved). Enriched with genome-browser Neon DB (DepMap, gnomAD, ClinGen, Mendelian, GWAS, Open Targets, SIDER).

**Method:** target-level evidence dimensions × drug outcome. Bootstrap 95% CIs, 500 draws. Outcome resolved per drug from failure-reason classifier (Sonnet/Haiku why_stopped) + FDA approvals join.

**Coverage-analyzable subset:** 2,770 of 30,517 (9%) map to a target in genome-browser DB; remaining 91% are placebos, combinations, cell/gene therapies, or unresolvable compound codes.

---

## Outcome distribution across all 30,517 programs

| Outcome | n | % | Notes |
|---|---|---|---|
| approved | 544 | 1.8% | FDA CDER + CBER 2015-2025 |
| efficacy_fail | 1,002 | 3.3% | ≥1 trial classified `efficacy` |
| safety_fail | 232 | 0.8% | ≥1 trial classified `safety` |
| commercial_fail | 2,157 | 7.1% | ≥1 trial `commercial_strategic` (~60% disguised efficacy per Cook 2014) |
| enrollment_fail | 609 | 2.0% | ≥1 trial `enrollment_operational` |
| other_fail | 2,725 | 8.9% | Terminated without why_stopped text or unclear reason |
| phase_complete_no_approval | 10,102 | 33.1% | **Silent kills** — completed Phase 2+ but never approved |
| phase1_complete_no_advance | 12,974 | 42.5% | Only Phase 1 (mostly formulation / PK / biosimilar) |
| planned_termination | 172 | 0.6% | Not a real failure |

Total resolved (excluding planned): 30,345. **Base approval rate = 1.8%** across the entire industry Phase 1-3 landscape 2015-2025.

---

## Q1. What are the tiers of *in vivo* evidence and to what extent do they predict clinical efficacy?

**Tier scheme** (Line D lit + Open Targets animal model + IMPC KO):
- **Tier 0**: no animal data / PK only
- **Tier 1**: single rodent efficacy study
- **Tier 2**: solid rodent + IMPC phenotype match
- **Tier 3**: multi-species (rodent + non-rodent) + replicated

**Effect sizes** (Phase 3+ cohort, n=7,077):

| Dimension | n covered | high → approved | low → approved | OR | 95% CI |
|---|---|---|---|---|---|
| Line D lit high (≥2) | 1,217 | 22% | 19% | 1.15 | [0.78, 1.71] |
| OT animal model score ≥0.3 | 992 | 15% | 33% | **0.38** | **[0.20, 0.74]** |
| IMPC KO ≥3 phenotypes | 445 | 18% | 15% | 1.16 | [0.68, 2.30] |

**Answer:** target-level published animal-in-vivo evidence is **null-to-negative**. Open Targets animal-model score (Phenodigm) being *negatively* associated (OR 0.38) is striking — well-studied mouse-KO targets are less likely to produce approved drugs. This reflects that pleiotropic, phenotype-rich targets often prove undruggable (see Q5 safety) or don't translate.

**Publication-bias caveat:** both approved and failed drugs' targets accumulate positive published animal data. The signal saturates at target level. Drug-level in vivo scoring (`drug_evidence.jsonl`) is in progress and will differentiate individual drug candidates.

---

## Q2. What are the tiers of *in vitro* evidence and to what extent do they predict clinical efficacy?

**Tier scheme** (Line C lit + DepMap essentiality):
- **Tier 0**: no cell data
- **Tier 1**: cell-line pharmacology
- **Tier 2**: primary human cells respond
- **Tier 3**: iPSC/organoid rescue

**Effect sizes** (Phase 3+ cohort):

| Dimension | n covered | high → approved | low → approved | OR | 95% CI |
|---|---|---|---|---|---|
| Line C lit high (≥2) | 1,217 | 21% | 23% | 0.89 | [0.61, 1.32] |
| DepMap pan-essential | 1,116 | 3% | 16% | **0.18** | **[0.07, 0.65]** |
| DepMap ≥5 dep lineages | 1,116 | 10% | 16% | **0.56** | **[0.21, 0.99]** |

**Answer:** target-level cell-pathway evidence is **null**. DepMap essentiality gives a **strong negative** signal — you cannot systemically drug pan-essential genes (3% approval rate vs 16% non-essential). Broadly-dependent targets (≥5 dependent lineages) are also disfavored.

**Actionable takeaway:** DepMap Chronos scoring is a real filter — but it filters *out*, not in. It says "avoid pan-essentials," not "positive cell-line effect predicts approval."

---

## Q3. What are all classes of preclinical evidence compiled before clinical trials?

**Taxonomy** — 8 categories, ~45 dimensions total. See `PRECLINICAL_EVIDENCE_SPEC.md` §1 for full definitions. Coverage in the 2,770-target-matched subset:

| Category | Dimension | Source | Coverage |
|---|---|---|---|
| A. Genetics | Nelson tier | FDA approvals + tier batches | 1,164 (42%) |
| A. Genetics | ClinGen Strong/Definitive | genome-browser | 1,099 (40%) |
| A. Genetics | Mendelian associations | genome-browser (OMIM+Orphanet) | 2,618 (95%) |
| A. Genetics | GWAS significant hits | genome-browser | 2,604 (94%) |
| A. Genetics | OT genetic score | genome-browser (Open Targets) | 2,652 (96%) |
| B. Mechanistic | Structural / binding lit | literature_scores.jsonl | 2,680 (97%) |
| B. Mechanistic | Tractability flags | genome-browser | 2,747 (99%) |
| C. Cell-pathway | Cell lit score | literature_scores.jsonl | 2,680 (97%) |
| C. Cell-pathway | DepMap essentiality | genome-browser | 2,596 (94%) |
| C. Cell-pathway | Drug-specific cell efficacy | drug_evidence.jsonl (in progress) | 81 (3%) |
| D. Animal | Animal lit score | literature_scores.jsonl | 2,680 (97%) |
| D. Animal | IMPC KO phenotypes | IMPC Solr | 1,110 (40%) |
| D. Animal | OT animal model score | genome-browser (Phenodigm) | 2,291 (83%) |
| D. Animal | Drug-specific rodent | drug_evidence.jsonl (in progress) | 81 (3%) |
| E. Human PD | PD engagement lit | literature_scores.jsonl | 2,680 (97%) |
| E. Human PD | Drug-specific engagement | drug_evidence.jsonl (in progress) | 81 (3%) |
| F. Clinical | Trial results (10,490 trials) | CT.gov | 100% |
| G. Pharmacology | (deferred — ChEMBL molecule props) | ChEMBL | — |
| H. Safety | gnomAD pLI/LOEUF | genome-browser | 2,491 (90%) |
| H. Safety | SIDER adverse events | genome-browser | 3,114 (~100% approved) |
| I. Landscape | Family precedent | derived | 2,197 (79%) |
| I. Landscape | Gene prior approvals | derived | 2,197 (79%) |

---

## Q4. Within efficacy failures, what types of evidence did or did not exist?

**Cohort:** 1,002 programs with ≥1 trial classified `efficacy`. Compared against 544 approved.

**Coverage deltas** (approved% minus eff-fail%):

| Dimension | eff-fail high | approved high | delta |
|---|---|---|---|
| **Line E lit (human PD engagement)** | 61% | 86% | **+25pp** — biggest single gap |
| **Mendelian associations ≥5** | 16% | 31% | **+14pp** |
| ClinGen Strong/Definitive | 79% | 88% | +10pp |
| Nelson tier T1+ | 51% | 55% | +5pp |
| OT genetic score ≥0.3 | 88% | 93% | +5pp |
| Tractable — antibody | 81% | 87% | +6pp |
| Line C lit (cell-pathway) | 87% | 87% | 0pp |
| Line D lit (animal) | 86% | 84% | -2pp |
| DepMap pan-essential | 7% | 0% | -7pp (efficacy failures ARE MORE essential) |

**Median metric comparison:**

| Metric | eff-fail median | approved median |
|---|---|---|
| Mendelian n | 2 | 3 |
| OT overall score | 0.65 | 0.71 |
| OT genetic score | 0.73 | 0.75 |
| Line E lit score | 2 | **3** |

**Answer:** the two dominant evidence gaps for efficacy failures are:
1. **Human PD engagement literature** — 25pp coverage deficit
2. **Mendelian association burden** — 14pp deficit

Efficacy failures had **similar target-level Line C/D coverage** as approvals, confirming that publication-bias-saturated target-level scores don't discriminate. What did discriminate was: (a) whether the target has strong human genetic backing, and (b) whether human clinical PD engagement had already been demonstrated for the target class.

---

## Q5. Within safety failures, what types of safety evidence did or did not exist?

**Cohort:** 232 programs with ≥1 trial classified `safety`. Compared against 544 approved.

**Coverage deltas:**

| Dimension | safety-fail high | approved high | delta |
|---|---|---|---|
| **ClinGen Strong/Definitive** | 50% | 88% | **+38pp** — safety failures had far weaker validity |
| **Line E lit (PD engagement)** | 67% | 86% | +19pp |
| **GWAS ≥50 hits** | 59% | 41% | **-18pp** — safety fails MORE pleiotropic |
| Mendelian ≥5 | 17% | 31% | +14pp |
| IMPC ≥3 phenotypes | 82% | 75% | -7pp (more pleiotropic mouse KOs) |
| DepMap ≥5 dep lineages | 11% | 5% | -6pp (more essential lineages) |
| gnomAD pLI ≥0.9 | 35% | 32% | -3pp |

**Median metric comparison:**

| Metric | safety-fail median | approved median | Ratio |
|---|---|---|---|
| gnomAD pLI | 0.661 | 0.013 | **51× higher** — LoF-intolerant |
| GWAS significant hits | 60 | 37 | 1.6× more pleiotropic |
| IMPC phenotypes | 7 | 5 | 1.4× more pleiotropic |
| gnomAD LOEUF | 0.57 | 0.71 | more constrained |

**Answer:** safety failures are enriched for targets that are:
1. **Pleiotropic** — more GWAS hits (60 vs 37), more IMPC KO phenotypes (7 vs 5)
2. **LoF-intolerant** — pLI 0.66 vs 0.013 (51× higher)
3. **Broadly essential** — more dependent lineages in DepMap
4. **Poorly validated** — 50% ClinGen coverage vs 88% approved

**Interpretation:** the H1+H2+H4 combination (LoF intolerance + essentiality + pleiotropy) is a predictable safety-liability profile. Together they explain the biology-driven mechanism of safety failure: hitting the target well causes off-target biology to break down.

---

## Effect-size headline table — FINAL comprehensive analysis

**Cohorts:**
- **TIGHT** (n=4,544): 544 approved vs 4,000 high-confidence failures (efficacy + safety + commercial + enrollment)
- **BROAD** (n=14,646): 544 approved vs 14,102 all failures (adds silent-kill presumptive labels)

**Top positive predictors (all CIs exclude 1):**

| Dimension | TIGHT OR [CI] | BROAD OR [CI] |
|---|---|---|
| **Line E lit (human PD engagement) high** | **3.98** [2.80, 6.00] | **4.14** [3.00, 5.62] |
| **ClinGen Strong/Definitive ≥1** | **2.48** [1.43, 4.75] | 2.15 [1.30, 4.36] |
| **Mendelian associations ≥5** | 2.01 [1.46, 2.74] | **2.38** [1.71, 3.26] |
| **OT genetic score ≥0.3** | 1.63 [1.00, 3.09] | **2.09** [1.35, 3.80] |
| **OT overall score ≥0.5** | 1.66 [1.09, 2.60] | 1.76 [1.20, 2.83] |

**Top negative predictors:**

| Dimension | TIGHT OR [CI] | BROAD OR [CI] |
|---|---|---|
| **DepMap pan-essential target** | **0.08** [0.03, 0.28] | **0.11** [0.05, 0.40] |
| **DepMap ≥5 dep lineages** | 0.47 [0.20, 0.81] | 0.69 [0.33, 1.14] |
| **OT animal model score ≥0.3** | 0.49 [0.24, 1.00] | 0.48 [0.26, 0.96] |

**Null (target-level literature):** Line C lit OR 0.96–1.10, Line D lit OR 1.17–1.21, IMPC KO count OR 0.85–0.99, tractability flags. Publication-bias saturation.

**Note on Nelson tier direction:** T1+ has OR 0.77-0.86 in this cohort (crosses 1 in tight). Reflects TA confounding — T0 approved drugs dominated by cytotoxic oncology / checkpoint / anti-infectives that have no meaningful human disease genetics. **ClinGen and Mendelian counts are more direct genetic-support measures** and both show clean OR ≈ 2.

**Null/inconclusive:** Line B/C/D lit scores, IMPC KO count, tractability flags — all target-level literature scores. Reflect publication bias saturation.

**Note on Nelson tier direction:** T0 approved drugs are dominated by cytotoxic oncology, checkpoint inhibitors, and anti-infectives (targets have no human genetics because they're microbial or immune-cell-surface antigens). T0's high approval rate in this cohort reflects those categories. **Within a specific therapeutic area, genetic support still helps** (see REPORT.md §3 per-TA tables).

---

## Definition of "fully complete" — status check

1. **"If a drug has strong human genetic support (Nelson T1), how much does that increase its odds of approval vs T0?"**
   → Direction is TA-dependent. **ClinGen Strong/Definitive: OR 2.34** and **Mendelian ≥5: OR 2.13** are the cleanest positive genetic predictors. Nelson T1+ in the raw pooled cohort is OR 0.53 [0.37, 0.72] because T0 approvals are dominated by cytotoxic/immunology categories where genetics don't apply.

2. **"If a drug has strong drug-specific animal-model efficacy (Tier 3), how much does that predict approval?"**
   → At target level: **OR 1.15 [0.78, 1.71]** at Phase 3+. Drug-specific extraction is 81/1,541 complete. **OT animal model score ≥0.3: OR 0.38 [0.20, 0.74]** — well-studied mouse-KO targets are less likely approved (pleiotropy signal).

3. **"Of drugs that failed for efficacy, what fraction had strong Category C (cell-pathway) evidence?"**
   → **87%** of efficacy-failed programs had high Line C lit score — matching **87%** of approvals. **Zero differentiation.** Cell-pathway target-level literature does NOT predict approval.

4. **"For approved drugs with no human genetic support (T0), what other evidence carried them through?"**
   → 240 of 423 T0 drugs approved (57%). Dominated by:
   - **Cytotoxic oncology** — kill dividing cells (no target genetics)
   - **Checkpoint inhibitors / CAR-T** — immune-cell surface antigens (no human disease genetics)
   - **Anti-infectives** — bacterial/viral targets (not human)
   - **Imaging agents / vaccines**
   Full breakdown in REPORT.md §9.4.

5. **"Which evidence dimension has the highest odds ratio for approval?"**
   → **Line E lit (human PD engagement) high: OR 3.98 [2.80, 6.00]** (tight) / **4.14 [3.00, 5.62]** (broad) — highest of any single dimension. **ClinGen Strong/Definitive: OR 2.48** and **Mendelian ≥5: OR 2.38** are next. In the negative direction: **DepMap pan-essential: OR 0.08 [0.03, 0.28]** is the strongest single negative filter.

---

## Caveats

1. **91% of programs (27,747 of 30,517) unmatched to genome-browser target** — mostly placebos, combinations, cell/gene therapies, unresolvable compound codes. Analyses restrict to the 2,770 target-mapped subset.
2. **Drug-specific evidence extraction is 5% complete** — target-level scores still dominate. Will replace when done (est. 50h).
3. **Publication bias** — negative preclinical data for failed drugs largely absent from PubMed.
4. **Silent kill classification** — 10,102 "phase-complete-no-approval" programs are heuristically labeled without failure reason. Tier 2 publication cross-reference (`FAILURE_AUDIT_PLAN.md`) is next enrichment.
5. **Nelson tier direction reversal** in raw pooled cohort reflects therapeutic-area confounding; stratify by TA (REPORT.md §3) for causal reading.

---

## Files generated

- **`drug_evidence_master_v2.csv`** — 30,517 program-level rows (new comprehensive)
- **`drug_evidence_master_v2_enriched.csv`** — + 22 genome-browser columns
- `drug_evidence_full_enriched.csv` — earlier 1,479-row master (preserved)
- **`EFFECT_SIZES_COMPREHENSIVE.md`** — full effect-size analysis on 30,517 cohort
- `EFFECT_SIZES_V3.md` — earlier 1,479-cohort analysis
- `EFFECT_SIZES_V2.md` — 24,706 program × line-score analysis
- `PRECLINICAL_EVIDENCE_SPEC.md` — full evidence taxonomy
- `ANSWERS.md` (this doc) — direct answers to the 5 core questions

## Regenerate

```bash
python3 build_master_v2.py              # → drug_evidence_master_v2.csv
DATABASE_URL=... python3 enrich_from_genomebrowser.py drug_evidence_master_v2.csv drug_evidence_master_v2_enriched.csv
python3 effect_sizes_comprehensive.py   # → EFFECT_SIZES_COMPREHENSIVE.md
```
