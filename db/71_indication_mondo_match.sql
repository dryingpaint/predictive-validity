-- How each condition's MONDO term was matched (pipeline.indications map):
-- exact (the term names the condition's core disease) or broader (no term
-- names it; the term is its nearest containing disease or grouping).

BEGIN;
SET LOCAL lock_timeout = '90s';
ALTER TABLE preclin.indication
    ADD COLUMN IF NOT EXISTS mondo_match text CHECK (mondo_match IN ('exact', 'broader'));
UPDATE preclin.indication SET mondo_match = 'exact' WHERE mondo_id IS NOT NULL AND mondo_match IS NULL;
COMMIT;
