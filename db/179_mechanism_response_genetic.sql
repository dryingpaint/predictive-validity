-- A Mendelian randomisation estimate of preclin.mechanism_response is about genetically lower risk factor, not a
-- drug, so its drugs and pathways may be empty (issue #195).

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.mechanism_response
    DROP CONSTRAINT mechanism_response_drugs_check,
    DROP CONSTRAINT mechanism_response_pathways_check,
    ADD CONSTRAINT mechanism_response_drug_check
        CHECK (population = 'lifelong_genetic' OR (cardinality(drugs) > 0 AND cardinality(pathways) > 0));
COMMENT ON COLUMN preclin.mechanism_response.drugs IS 'Generic names of the active drugs in the regimen (every member for a pooled class), lower case; empty for a Mendelian randomisation estimate of genetically lower risk factor.';
COMMENT ON COLUMN preclin.mechanism_response.pathways IS 'Pathways the regimen acts through, named with the canonical names of preclin.mechanism_pathway; for a Mendelian randomisation estimate, the pathway of the target gene whose variants it uses, or empty when it uses variants across the genome.';
COMMENT ON COLUMN preclin.mechanism_response.regimen IS 'The drug, drug class or regimen the estimate is for, as the source names it (a class where a network meta-analysis pools one); for a Mendelian randomisation estimate, the genetic exposure.';
COMMIT;
