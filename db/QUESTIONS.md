# Questions you can now ask this dataset

Every question is one SQL query. All against `preclin.*` in Neon.

## Coverage of past-10-year trials

**What we cover:**
- Every CT.gov industry Phase 1-3 drug/biological trial 2015-2025 (441,876 trials in `public.trials`, ~28K industry-drug subset filtered into our programs)
- Every FDA approval CDER + CBER 2015-2025 (544 → `preclin.approval` + rolled up via program_outcome)
- Every drug appearing in those trials (52,694 in `preclin.drug`)
- 82,014 programs at (drug × indication × sponsor) level
- 88,999 program-trial linkages

**What we don't cover:**
- Non-CT.gov international trials (ChiCTR ~70K, EU-CTR ~35K) — not yet ingested
- Preclinical / IND-stage kills — never enter CT.gov
- Terminated trials with no `why_stopped` text (~50% of terminations) — remain in `unclassified_termination` outcome
- Pre-2015 trials (out of our 10-year scope)

---

## 1. Which evidence types actually predict approval? (Pheiron-style)

```sql
SELECT category, dimension, n_supported, supported_pct_approved,
       not_supported_pct_approved, relative_success
FROM preclin.v_relative_success
ORDER BY relative_success DESC NULLS LAST;
```

**Live answer** (top 5, Phase 2+ T-I pairs):
- Reactome pathways ≥5: RS 2.90
- Human PD engagement lit (Line E): RS 2.20
- ClinGen Strong/Definitive: RS 1.75
- Cell-pathway lit (Line C): RS 1.67
- OT somatic cancer: RS 1.62

## 2. How often does strong evidence still fail?

```sql
SELECT dimension, is_high_evidence, n_total, approved_pct, efficacy_fail_pct, any_fail_pct
FROM preclin.v_pathway_wrongness
WHERE dimension IN ('Line E (human PD) high (≥2)', 'ClinGen Strong/Def ≥1', 'Mendelian ≥5')
ORDER BY dimension, is_high_evidence DESC;
```

**Live answer** (Phase 3+ T-I pairs):
- Line E high: 46% approved, 44% efficacy_fail
- ClinGen high: 43% approved, 44% efficacy_fail
- Mendelian ≥5: 47% approved, 42% efficacy_fail

Even with strong evidence, **~50% of Phase 3 attempts still fail**.

## 3. What combination of evidence works best?

```sql
SELECT ev_a, ev_b, rs_combined, combined_approval_pct, n_ab
FROM preclin.v_combination_evidence
ORDER BY combined_approval_pct DESC NULLS LAST;
```

**Live answer:**
- Mendelian + Line E = **43.3% approval** (best combo)
- ClinGen + Tissue-specific = 35.5%
- OT genetic + Reactome pathways = 35.0%

## 4. Failure taxonomy — why do industry trials terminate?

```sql
SELECT * FROM preclin.v_failure_taxonomy ORDER BY n_trials DESC;
```

Split by Sonnet vs Haiku classifier where disagreement:
```sql
SELECT haiku.category AS haiku_cat, sonnet.category AS sonnet_cat, COUNT(*) AS n_trials
FROM preclin.classification haiku
JOIN preclin.classification sonnet
  ON haiku.subject_key = sonnet.subject_key
 AND haiku.subject_type = 'trial' AND sonnet.subject_type = 'trial'
 AND haiku.classifier_model = 'claude-haiku'
 AND sonnet.classifier_model = 'claude-sonnet'
 AND haiku.classifier_task = 'why_stopped'
 AND sonnet.classifier_task = 'why_stopped'
GROUP BY haiku.category, sonnet.category
ORDER BY n_trials DESC;
```

## 5. Selection bias — is our target-matched cohort representative?

```sql
SELECT resolved_via,
       COUNT(*) AS n_drugs,
       COUNT(*) FILTER (WHERE approved_us OR approved_ex_us) AS n_approved,
       ROUND(100.0 * COUNT(*) FILTER (WHERE approved_us OR approved_ex_us) / COUNT(*), 1) AS approval_pct
FROM preclin.v_drug_coverage
GROUP BY resolved_via
ORDER BY n_drugs DESC;
```

Answers: Are ChEMBL-catalogued drugs disproportionately approved? (Yes — 10× the baseline rate.)

## 6. Per-therapeutic-area approval rates by evidence

```sql
SELECT i.therapeutic_area,
       COUNT(*) FILTER (WHERE po.approved_us) AS n_approved,
       COUNT(*) AS n_programs,
       ROUND(100.0 * COUNT(*) FILTER (WHERE po.approved_us) / COUNT(*), 1) AS approval_pct
FROM preclin.program p
JOIN preclin.program_outcome po ON po.program_id = p.program_id
JOIN preclin.indication i ON i.indication_id = p.indication_id
WHERE p.highest_phase >= 2
GROUP BY i.therapeutic_area
ORDER BY n_programs DESC;
```

## 7. Nelson tier × approval per therapeutic area

```sql
SELECT ti.nelson_tier, i.therapeutic_area,
       COUNT(*) AS n, COUNT(*) FILTER (WHERE po.approved_us) AS n_approved,
       ROUND(100.0 * COUNT(*) FILTER (WHERE po.approved_us) / COUNT(*), 1) AS pct
FROM preclin.v_program_evidence_wide ti
JOIN preclin.indication i ON i.indication_id = ti.indication_id
JOIN preclin.program_outcome po ON po.program_id = ti.program_id
WHERE ti.nelson_tier IS NOT NULL AND ti.highest_phase >= 2
GROUP BY ti.nelson_tier, i.therapeutic_area
ORDER BY i.therapeutic_area, ti.nelson_tier;
```

## 8. Sponsor performance — top-10 by unique drug approvals

```sql
SELECT p.sponsor_name,
       COUNT(DISTINCT p.drug_id) AS n_unique_drugs,
       COUNT(DISTINCT p.drug_id) FILTER (WHERE po.approved_us) AS n_approved_drugs,
       ROUND(100.0 * COUNT(DISTINCT p.drug_id) FILTER (WHERE po.approved_us)
                    / COUNT(DISTINCT p.drug_id), 1) AS pct_approved
FROM preclin.program p
JOIN preclin.program_outcome po ON po.program_id = p.program_id
WHERE p.sponsor_name IS NOT NULL
GROUP BY p.sponsor_name
HAVING COUNT(DISTINCT p.drug_id) >= 15
ORDER BY pct_approved DESC
LIMIT 20;
```

## 9. Case studies — approved drugs with weak genetic support

```sql
SELECT DISTINCT d.display_name, p.indication_id AS ind, tw.gene_approved_count, tw.mendelian_n
FROM preclin.program p
JOIN preclin.program_outcome po ON po.program_id = p.program_id
JOIN preclin.drug d ON d.drug_id = p.drug_id
JOIN preclin.v_drug_target dt ON dt.drug_id = p.drug_id AND dt.role = 'primary'
JOIN preclin.v_target_evidence_wide tw ON tw.target_id = dt.target_id
WHERE po.approved_us
  AND (tw.mendelian_n IS NULL OR tw.mendelian_n = 0)
  AND (tw.clingen_n_strong IS NULL OR tw.clingen_n_strong = 0)
LIMIT 20;
```

## 10. Case studies — high-evidence targets with only failures

```sql
SELECT t.symbol AS target,
       ti.n_programs, ti.n_drugs,
       tw.mendelian_n, tw.clingen_n_strong, tw.line_e_lit
FROM preclin.v_target_indication_program ti
JOIN preclin.v_target_evidence_wide tw ON tw.target_id = ti.target_id
JOIN public.targets t ON t.id = ti.target_id
WHERE NOT ti.any_approved
  AND ti.max_phase_reached >= 3
  AND (tw.mendelian_n >= 5 OR tw.clingen_n_strong >= 1)
ORDER BY ti.n_programs DESC
LIMIT 20;
```

## 11. Tissue specificity × approval — Pheiron's combination

```sql
SELECT
  CASE
    WHEN tw.sc_tau_specificity >= 0.75 THEN 'tissue-specific'
    WHEN tw.sc_tau_specificity >= 0.4  THEN 'moderate'
    ELSE 'broad'
  END AS tissue_class,
  CASE WHEN tw.mendelian_n >= 5 THEN 'mendelian-supported' ELSE 'no-mendelian' END AS gen_class,
  COUNT(*) AS n_ti,
  COUNT(*) FILTER (WHERE ti.any_approved) AS n_approved,
  ROUND(100.0 * COUNT(*) FILTER (WHERE ti.any_approved) / COUNT(*), 1) AS approval_pct
FROM preclin.v_target_indication_program ti
JOIN preclin.v_target_evidence_wide tw ON tw.target_id = ti.target_id
WHERE ti.max_phase_reached >= 2 AND tw.sc_tau_specificity IS NOT NULL
GROUP BY tissue_class, gen_class
ORDER BY tissue_class, gen_class;
```

## 12. GO functional depth × approval

```sql
SELECT
  CASE
    WHEN tw.n_go_biological_process >= 20 THEN 'deep functional annotation'
    WHEN tw.n_go_biological_process >= 5  THEN 'moderate'
    ELSE 'shallow'
  END AS annotation_depth,
  COUNT(*) AS n_targets_with_ti,
  COUNT(*) FILTER (WHERE ti.any_approved) AS n_approved
FROM preclin.v_target_indication_program ti
JOIN preclin.v_target_evidence_wide tw ON tw.target_id = ti.target_id
WHERE ti.max_phase_reached >= 2
GROUP BY annotation_depth;
```

## 13. Silent-kill audit — which Phase 3 completions never approved?

```sql
SELECT d.display_name, i.display_name AS indication, t.symbol AS target,
       p.n_completed, p.last_trial_date, po.outcome_broad
FROM preclin.program p
JOIN preclin.drug d ON d.drug_id = p.drug_id
JOIN preclin.indication i ON i.indication_id = p.indication_id
JOIN preclin.program_outcome po ON po.program_id = p.program_id
LEFT JOIN preclin.v_drug_target dt ON dt.drug_id = p.drug_id AND dt.role='primary'
LEFT JOIN public.targets t ON t.id = dt.target_id
WHERE po.outcome_broad = 'presumptive_efficacy_fail_ph3'
  AND t.symbol IS NOT NULL
ORDER BY p.last_trial_date DESC
LIMIT 30;
```

## 14. Publication-verified silent-kill outcomes

```sql
SELECT c.subject_key AS drug_key, c.category AS verified_outcome, c.confidence, c.rationale
FROM preclin.classification c
WHERE c.classifier_task = 'silent_kill_verify'
  AND c.category IN ('efficacy_fail', 'safety_fail', 'inconclusive_stopped')
ORDER BY c.confidence DESC
LIMIT 20;
```

## 15. Diagnose disagreement between classifiers

```sql
SELECT h.subject_key AS nct,
       h.category AS haiku, s.category AS sonnet,
       s.confidence, s.rationale
FROM preclin.classification h
JOIN preclin.classification s
  ON h.subject_key = s.subject_key
 AND h.subject_type = 'trial' AND s.subject_type = 'trial'
 AND h.classifier_task = 'why_stopped'
 AND s.classifier_task = 'why_stopped'
 AND h.classifier_model = 'claude-haiku'
 AND s.classifier_model = 'claude-sonnet'
WHERE h.category != s.category
  AND (h.category = 'commercial_strategic' OR s.category = 'efficacy')
LIMIT 30;
```

## 16. Drugs against essential genes that DID get approved (exceptions)

```sql
SELECT DISTINCT d.display_name, t.symbol,
       ges.mean_effect, ges.pan_essential
FROM preclin.program p
JOIN preclin.program_outcome po ON po.program_id = p.program_id
JOIN preclin.drug d ON d.drug_id = p.drug_id
JOIN preclin.v_drug_target dt ON dt.drug_id = p.drug_id AND dt.role='primary'
JOIN public.gene_essentiality_summary ges ON ges.target_id = dt.target_id
JOIN public.targets t ON t.id = dt.target_id
WHERE ges.pan_essential = TRUE AND po.approved_us
LIMIT 10;
```

## 17. Every dimension coverage across cohorts

```sql
SELECT ed.category, ed.dimension,
       COUNT(*) FILTER (WHERE es.subject_type = 'target') AS n_targets_scored,
       COUNT(DISTINCT es.subject_id) FILTER (WHERE es.subject_type = 'target') AS n_uniq_targets
FROM preclin.evidence_dimension ed
LEFT JOIN preclin.evidence_score es ON es.dimension = ed.dimension
GROUP BY ed.category, ed.dimension
ORDER BY ed.category, ed.dimension;
```

## 18. Drug's full evidence dossier (for any given drug)

```sql
SELECT es.dimension, ed.category, ed.description,
       es.value_numeric, es.value_text, es.value_boolean,
       es.source, es.confidence, es.extracted_by
FROM preclin.evidence_score es
JOIN preclin.evidence_dimension ed ON ed.dimension = es.dimension
JOIN preclin.drug d ON
  (es.subject_type = 'drug' AND es.subject_id = d.drug_id)
  OR (es.subject_type = 'target' AND es.subject_id IN (
    SELECT target_id FROM preclin.v_drug_target WHERE drug_id = d.drug_id
  ))
WHERE d.normalized_name = 'pembrolizumab'
ORDER BY ed.category, es.dimension;
```

## 19. Sponsor's full portfolio + evidence quality

```sql
SELECT p.sponsor_name,
       COUNT(DISTINCT p.drug_id) AS n_drugs,
       AVG(tw.line_e_lit) AS avg_line_e,
       AVG(tw.mendelian_n) AS avg_mendelian,
       COUNT(*) FILTER (WHERE po.approved_us) AS n_approved
FROM preclin.program p
JOIN preclin.program_outcome po ON po.program_id = p.program_id
LEFT JOIN preclin.v_drug_target dt ON dt.drug_id = p.drug_id AND dt.role='primary'
LEFT JOIN preclin.v_target_evidence_wide tw ON tw.target_id = dt.target_id
WHERE p.sponsor_name IN ('GlaxoSmithKline','Novartis Pharmaceuticals','Pfizer','Merck Sharp & Dohme LLC')
GROUP BY p.sponsor_name;
```

## 20. Time trend — approval rate by year

```sql
SELECT approval_year, COUNT(*) AS n_approvals,
       COUNT(*) FILTER (WHERE nelson_tier IS NOT NULL AND nelson_tier != 'T0') AS n_genetic_supported,
       ROUND(100.0 * COUNT(*) FILTER (WHERE nelson_tier != 'T0') /
             NULLIF(COUNT(*) FILTER (WHERE nelson_tier IS NOT NULL), 0), 1) AS pct_genetic
FROM preclin.approval
WHERE region = 'US' AND approval_year BETWEEN 2015 AND 2025
GROUP BY approval_year
ORDER BY approval_year;
```

## 21. Peer-review PMID citations behind any evidence claim

```sql
SELECT es.dimension, es.value_numeric, es.citation_pmids, ed.description
FROM preclin.evidence_score es
JOIN preclin.evidence_dimension ed ON ed.dimension = es.dimension
JOIN public.targets t ON t.id = es.subject_id
WHERE t.symbol = 'BACE1' AND es.subject_type = 'target'
ORDER BY es.dimension;
```

## 22. Deep dive — one drug's full failure/approval story

```sql
WITH d AS (SELECT drug_id FROM preclin.drug WHERE normalized_name = 'verubecestat')
SELECT
  p.indication_id, i.display_name AS indication, p.sponsor_name,
  p.highest_phase, po.outcome_broad, po.failure_reasons,
  ARRAY(SELECT nct_id FROM preclin.program_trial WHERE program_id = p.program_id) AS trials,
  ARRAY(
    SELECT c.category || ' (' || c.classifier_model || ')'
    FROM preclin.classification c
    JOIN preclin.program_trial pt ON pt.nct_id = c.subject_key
    WHERE pt.program_id = p.program_id AND c.classifier_task = 'why_stopped'
  ) AS termination_reasons
FROM d
JOIN preclin.program p ON p.drug_id = d.drug_id
JOIN preclin.indication i ON i.indication_id = p.indication_id
JOIN preclin.program_outcome po ON po.program_id = p.program_id;
```

## 23. Which drug classes have the highest silent-kill rate?

```sql
SELECT d.modality,
       COUNT(*) FILTER (WHERE po.outcome_broad = 'presumptive_efficacy_fail_ph3') AS n_silent_kill,
       COUNT(*) FILTER (WHERE p.highest_phase >= 3) AS n_ph3,
       ROUND(100.0 * COUNT(*) FILTER (WHERE po.outcome_broad = 'presumptive_efficacy_fail_ph3')
                    / NULLIF(COUNT(*) FILTER (WHERE p.highest_phase >= 3), 0), 1) AS silent_kill_pct
FROM preclin.program p
JOIN preclin.program_outcome po ON po.program_id = p.program_id
JOIN preclin.drug d ON d.drug_id = p.drug_id
WHERE d.modality IS NOT NULL
GROUP BY d.modality
ORDER BY n_ph3 DESC LIMIT 15;
```

## 24. Cross-species efficacy: OT animal model score vs approval

```sql
SELECT
  CASE
    WHEN tw.ot_animal_model_max >= 0.5 THEN 'strong (≥0.5)'
    WHEN tw.ot_animal_model_max >= 0.3 THEN 'moderate (0.3-0.5)'
    WHEN tw.ot_animal_model_max >= 0.1 THEN 'weak (0.1-0.3)'
    ELSE 'none (<0.1)'
  END AS animal_evidence,
  COUNT(*) AS n_ti,
  COUNT(*) FILTER (WHERE ti.any_approved) AS n_approved,
  ROUND(100.0 * COUNT(*) FILTER (WHERE ti.any_approved) / COUNT(*), 1) AS pct
FROM preclin.v_target_indication_program ti
JOIN preclin.v_target_evidence_wide tw ON tw.target_id = ti.target_id
WHERE ti.max_phase_reached >= 2 AND tw.ot_animal_model_max IS NOT NULL
GROUP BY animal_evidence
ORDER BY animal_evidence DESC;
```

## 25. Ingest audit trail

```sql
SELECT source_file, target_table, rows_inserted, notes, finished_at
FROM preclin.ingest_log
ORDER BY ingest_id DESC LIMIT 30;
```

---

## Adding a new question type

Every question runs against 3 tables:
- `preclin.v_program_evidence_wide` — one row per program with all dims
- `preclin.v_target_evidence_wide` — one row per target with all dims
- `preclin.v_target_indication_program` — Pheiron unit (T-I pair)

Or the fact tables directly:
- `preclin.evidence_score` — long-form (subject × dimension)
- `preclin.classification` — long-form (LLM outputs)

Or genome-browser primary sources (via `public.*`):
- `public.trials` — all 441,876 CT.gov trials
- `public.target_evidence` — 700K Open Targets rows
- `public.gene_essentiality` — 21M DepMap Chronos scores per (gene × cell line)
