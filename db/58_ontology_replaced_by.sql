-- Obsolete ontology terms point to their replacement (EFO moved many disease
-- terms to MONDO; GWAS Catalog traits still cite some of the old ids).

BEGIN;
ALTER TABLE preclin.ontology_term ADD COLUMN IF NOT EXISTS replaced_by text;
COMMIT;
