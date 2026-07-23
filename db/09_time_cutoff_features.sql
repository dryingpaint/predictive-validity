-- Time-cutoff-aware evidence features.
-- Computes family/gene precedent at any given cutoff year.
-- Fixes residual leakage in family_approved_count.

BEGIN;

-- v_target_family_precedent_by_year: how many approvals against this target's
-- family or gene existed BY a given year?
DROP VIEW IF EXISTS preclin.v_target_family_precedent_by_year CASCADE;
CREATE VIEW preclin.v_target_family_precedent_by_year AS
WITH target_family AS (
  SELECT id AS target_id, family FROM public.targets WHERE family IS NOT NULL
),
approvals_by_target AS (
  SELECT
    dt.target_id, a.approval_year, a.approval_id
  FROM preclin.approval a
  JOIN preclin.v_drug_target dt ON dt.drug_id = a.drug_id
  WHERE a.approval_year IS NOT NULL
),
family_appr AS (
  SELECT
    tf.family, a.approval_year, COUNT(DISTINCT a.approval_id) AS n_approvals_this_year
  FROM approvals_by_target a
  JOIN target_family tf ON tf.target_id = a.target_id
  GROUP BY tf.family, a.approval_year
),
gene_appr AS (
  SELECT
    a.target_id, a.approval_year, COUNT(DISTINCT a.approval_id) AS n_approvals_this_year
  FROM approvals_by_target a
  GROUP BY a.target_id, a.approval_year
)
SELECT tf.target_id, tf.family, y.year,
       COALESCE((SELECT SUM(n_approvals_this_year)
                 FROM family_appr WHERE family = tf.family AND approval_year < y.year), 0)
         AS family_approved_before_year,
       COALESCE((SELECT SUM(n_approvals_this_year)
                 FROM gene_appr WHERE target_id = tf.target_id AND approval_year < y.year), 0)
         AS gene_approved_before_year
FROM target_family tf
CROSS JOIN (SELECT generate_series(2015, 2026) AS year) y;

COMMENT ON VIEW preclin.v_target_family_precedent_by_year IS
'Time-cutoff family + gene approval counts. Query: SELECT * FROM view WHERE target_id=X AND year=2019.';

COMMIT;
