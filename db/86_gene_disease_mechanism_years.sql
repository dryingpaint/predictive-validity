-- A gene-disease mechanism carries two dates: when the risk mechanism and when the
-- protective effect were first shown for that disease. One combined year let a
-- protective finding published after a program's entry count before it.

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.gene_disease_mechanism
    DROP COLUMN IF EXISTS established_year,
    ADD COLUMN IF NOT EXISTS risk_year integer,
    ADD COLUMN IF NOT EXISTS protective_year integer;
COMMIT;
