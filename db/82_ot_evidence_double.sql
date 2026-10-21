-- Evidence scores in double precision: gene-burden resource scores are p-values down to 1e-300.

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.ot_evidence ALTER COLUMN score TYPE double precision,
                                ALTER COLUMN resource_score TYPE double precision;
COMMIT;
