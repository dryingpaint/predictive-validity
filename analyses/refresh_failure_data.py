#!/usr/bin/env python3
"""
Rebuild the cached CSVs powering the Section-1 failure-mode figures.

Reads from Neon (`preclin.*` schema) and writes:
  data/failure_taxonomy.csv          — trial-level, terminations only (Stephen's original)
  data/failure_holistic.csv          — program-level, all Ph2+ failures
  data/failure_holistic_by_ta.csv    — same, stratified by therapeutic area
  data/failure_holistic_by_modality.csv  — same, stratified by drug modality
  data/failure_modes_audit.csv       — cohort-size audit trail

Requires DATABASE_URL. Otherwise the plotting script runs on the committed CSVs.
"""
from __future__ import annotations
import os, warnings
import psycopg2
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


CTE = """
WITH trial_class AS (
  -- Latest classification per trial, Sonnet preferred over Haiku
  SELECT DISTINCT ON (c.subject_key) c.subject_key AS nct_id, c.category
  FROM preclin.classification c
  WHERE c.classifier_task = 'why_stopped' AND c.subject_type = 'trial'
  ORDER BY c.subject_key,
    CASE c.classifier_model WHEN 'claude-sonnet' THEN 1 ELSE 2 END
),
program_reasons AS (
  -- Roll trial-level reasons up to program level
  SELECT pt.program_id,
    BOOL_OR(tc.category = 'efficacy') AS r_eff,
    BOOL_OR(tc.category = 'safety') AS r_safety,
    BOOL_OR(tc.category = 'pk_pd_formulation') AS r_pkpd,
    BOOL_OR(tc.category = 'commercial_strategic') AS r_comm,
    BOOL_OR(tc.category = 'enrollment_operational') AS r_enr,
    BOOL_OR(tc.category = 'regulatory_admin') AS r_reg,
    BOOL_OR(tc.category = 'competitive_landscape') AS r_compet,
    BOOL_OR(tc.category = 'manufacturing_supply') AS r_mfg,
    BOOL_OR(tc.category = 'covid') AS r_covid
  FROM preclin.program_trial pt
  LEFT JOIN trial_class tc ON tc.nct_id = pt.nct_id
  GROUP BY pt.program_id
),
drug_modality AS (
  -- One row per drug. Prefer preclin.drug.modality (curated from approvals),
  -- fall back to public.therapies via chembl_id, then by normalized name.
  SELECT d.drug_id,
    COALESCE(d.modality,
      (SELECT modality FROM public.therapies th WHERE th.chembl_id = d.chembl_id LIMIT 1),
      (SELECT modality FROM public.therapies th WHERE LOWER(th.name) = LOWER(d.normalized_name) LIMIT 1)
    ) AS modality_raw
  FROM preclin.drug d
),
classified AS (
  SELECT p.program_id, i.therapeutic_area, dm.modality_raw,
    CASE
      -- Biology signals from trial-level termination reason take priority
      WHEN pr.r_eff THEN 'efficacy'
      WHEN pr.r_safety THEN 'safety'
      WHEN pr.r_pkpd THEN 'pk_pd'
      -- Silent efficacy: Ph3 completed but no approval — strong biology inference
      WHEN po.outcome_broad = 'presumptive_efficacy_fail_ph3' THEN 'silent_efficacy_ph3'
      -- Ph2 stall: Ph2 complete but program halted — ambiguous but usually efficacy-gated
      WHEN po.outcome_broad = 'presumptive_fail_ph2' THEN 'ph2_stall'
      -- Business & operational
      WHEN pr.r_comm OR po.outcome_broad = 'commercial_fail' THEN 'commercial_strategic'
      WHEN pr.r_enr OR po.outcome_broad = 'enrollment_fail' THEN 'enrollment_operational'
      WHEN pr.r_reg THEN 'regulatory_admin'
      WHEN pr.r_compet THEN 'competitive_landscape'
      WHEN pr.r_mfg THEN 'manufacturing_supply'
      WHEN pr.r_covid THEN 'covid'
      -- Other / undisclosed
      WHEN po.outcome_broad = 'planned_termination' THEN 'planned'
      WHEN po.outcome_broad = 'unclassified_termination' THEN 'unclassified_termination'
      ELSE 'unknown'
    END AS bucket
  FROM preclin.program p
  JOIN preclin.program_outcome po ON po.program_id = p.program_id
  JOIN preclin.indication i ON i.indication_id = p.indication_id
  LEFT JOIN program_reasons pr ON pr.program_id = p.program_id
  LEFT JOIN drug_modality dm ON dm.drug_id = p.drug_id
  -- Denominator: Ph2+ programs that did not reach approval, excluding Ph1-only stalls
  -- (Ph1-only stalls are dominated by pipeline reprioritization, not clinical failure).
  WHERE po.outcome_broad NOT IN ('approved','phase1_only')
    AND p.highest_phase >= 2
)
"""


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL not set. Cached CSVs are committed; you don't need this "
                         "script unless you're refreshing the analysis.")
    conn = psycopg2.connect(url)

    # (1) Trial-level terminations chart (Stephen's original) — refreshed same query
    q_taxonomy = """
      WITH classified AS (
        SELECT DISTINCT ON (subject_key)
          subject_key AS nct_id, category, classifier_model, confidence
        FROM preclin.classification
        WHERE classifier_task = 'why_stopped' AND subject_type = 'trial'
        ORDER BY subject_key, CASE classifier_model WHEN 'claude-sonnet' THEN 1 ELSE 2 END
      )
      SELECT category, COUNT(*) AS n_trials,
             ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_all_classified
      FROM classified GROUP BY category ORDER BY n_trials DESC;
    """
    df = pd.read_sql(q_taxonomy, conn)
    df.to_csv(os.path.join(DATA, "failure_taxonomy.csv"), index=False)
    print(f"failure_taxonomy.csv           {df.n_trials.sum():>7,} trials")

    # (2) Holistic program-level chart
    df = pd.read_sql(CTE + """
      SELECT bucket, COUNT(*) AS n_programs,
             ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_failed_programs
      FROM classified GROUP BY bucket ORDER BY n_programs DESC;
    """, conn)
    df.to_csv(os.path.join(DATA, "failure_holistic.csv"), index=False)
    print(f"failure_holistic.csv           {df.n_programs.sum():>7,} programs")

    # (3) Stratified by therapeutic area
    df = pd.read_sql(CTE + """
      SELECT COALESCE(therapeutic_area,'other') AS therapeutic_area, bucket,
             COUNT(*) AS n_programs
      FROM classified GROUP BY therapeutic_area, bucket
      ORDER BY therapeutic_area, n_programs DESC;
    """, conn)
    df.to_csv(os.path.join(DATA, "failure_holistic_by_ta.csv"), index=False)
    print(f"failure_holistic_by_ta.csv     {df.n_programs.sum():>7,} programs")

    # (4) Stratified by modality
    df = pd.read_sql(CTE + """
      SELECT modality_raw, bucket, COUNT(*) AS n_programs
      FROM classified WHERE modality_raw IS NOT NULL
      GROUP BY modality_raw, bucket ORDER BY modality_raw, n_programs DESC;
    """, conn)
    df.to_csv(os.path.join(DATA, "failure_holistic_by_modality.csv"), index=False)
    print(f"failure_holistic_by_modality.csv {df.n_programs.sum():>5,} programs (subset w/ modality known)")

    # (5) Audit: cohort sizes at every filter step
    df = pd.read_sql("""
      SELECT 'ctgov_industry_ph1_3_2015_2025' AS metric,
             COUNT(*) AS value FROM public.trials
       WHERE sponsor_type='INDUSTRY' AND phase ~ '(PHASE1|PHASE2|PHASE3)'
         AND start_date >= '2015-01-01' AND start_date < '2026-01-01'
      UNION ALL SELECT 'n_trials_in_cohort',
        COUNT(DISTINCT nct_id) FROM preclin.program_trial
      UNION ALL SELECT 'n_trials_terminated_or_withdrawn',
        COUNT(DISTINCT t.nct_id) FROM public.trials t
        JOIN preclin.program_trial pt ON pt.nct_id=t.nct_id
        WHERE t.status IN ('TERMINATED','WITHDRAWN','SUSPENDED')
      UNION ALL SELECT 'n_trials_completed',
        COUNT(DISTINCT t.nct_id) FROM public.trials t
        JOIN preclin.program_trial pt ON pt.nct_id=t.nct_id
        WHERE t.status='COMPLETED'
      UNION ALL SELECT 'n_trials_why_stopped_classified',
        COUNT(DISTINCT subject_key) FROM preclin.classification
        WHERE classifier_task='why_stopped' AND subject_type='trial'
      UNION ALL SELECT 'n_programs_total', COUNT(*) FROM preclin.program
      UNION ALL SELECT 'n_programs_ph2plus',
        COUNT(*) FROM preclin.program WHERE highest_phase >= 2
      UNION ALL SELECT 'n_programs_approved',
        COUNT(*) FROM preclin.program_outcome WHERE outcome_broad='approved'
      UNION ALL SELECT 'n_programs_failed_ph2plus',
        COUNT(*) FROM preclin.program p
        JOIN preclin.program_outcome po ON po.program_id=p.program_id
        WHERE p.highest_phase >= 2 AND po.outcome_broad NOT IN ('approved','phase1_only');
    """, conn)
    df.to_csv(os.path.join(DATA, "failure_modes_audit.csv"), index=False)
    print(f"failure_modes_audit.csv        {len(df)} rows")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
