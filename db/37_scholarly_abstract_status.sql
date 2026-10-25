-- Make absence of an abstract explicit rather than treating NULL as evidence.

BEGIN;

ALTER TABLE pv_source.scholarly_work
  ADD COLUMN abstract_status TEXT NOT NULL DEFAULT 'retrieval_pending' CHECK (
    abstract_status IN (
      'present', 'retrieval_pending', 'not_provided_by_retrieved_sources'
    )
  );

UPDATE pv_source.scholarly_work
SET abstract_status = 'present'
WHERE abstract_text IS NOT NULL AND btrim(abstract_text) <> '';

COMMIT;
