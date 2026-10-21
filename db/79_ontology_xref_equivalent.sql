-- Whether the ontology declares a cross-reference to name the same concept
-- (MONDO annotates these source="MONDO:equivalentTo"). pipeline.opentargets maps
-- Open Targets diseases without a MONDO id to MONDO through them.

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.ontology_xref ADD COLUMN IF NOT EXISTS equivalent boolean NOT NULL DEFAULT false;
COMMIT;
