-- The target-biology literature of issue #154 is documented in one record, report/audits/target_literature.md (the
-- method, the gate, the full run, the web arm and the reconciliation). Comments that named the separate gate record
-- or the pilot's reference files now name that record and the database rows that hold the data. Comments only.

BEGIN;
SET LOCAL lock_timeout = '3s';

COMMENT ON VIEW preclin.target_literature_evidence IS
    'One row per target-disease pair and kind of #154 target evidence with at least one qualifying record (original data, the pair''s disease or a subtype, the kind shown; preclin.target_literature_screen), from every retrieval source including the web arm (source web_agent). DESCRIPTIVE ONLY: no kind passed the registered pilot gate (recall below 80%; report/audits/target_literature.md), so these are counts of what the search found, not complete evidence, and are not tested. A phase entry has the kind when a record is dated by the year before its entry: compare record_years (or first_year) with the entry year when reading. Years come from public.publications, preclin.literature_record or preclin.target_disease_source.';

COMMENT ON COLUMN preclin.target_literature_web_study.llm_decision_id IS
    'The model''s decision (pv_evidence.llm_decision) the study comes from. Null for the pilot''s reference studies (arm web, pilot rows 1-200 in report/audits/target_literature_pilot.csv): their answers are the pv_evidence.llm_decision rows of task target_literature_reference or target_literature_reference_fallback for the pair.';

COMMIT;
