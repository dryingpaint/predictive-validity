-- Compact text of each snapshot study's posted results (pipeline.outcomes
-- results): primary outcome values and statistical comparisons, and deaths
-- and serious adverse events per arm. analyses holds the comparisons as data.

BEGIN;
SET LOCAL lock_timeout = '90s';
CREATE TABLE IF NOT EXISTS preclin.ctgov_result_summary (
    nct_id     text PRIMARY KEY REFERENCES preclin.ctgov_study,
    summary    text NOT NULL,
    n_analyses integer NOT NULL,
    analyses   jsonb NOT NULL
);
COMMIT;
