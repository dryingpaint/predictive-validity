-- Open Targets evidence keeps its references (the evidence layer of PR #159, 2026-11-22): each row's detail holds the
-- PubMed ids of its supporting papers and the source's own identifiers of the disease and target, so every evidence
-- fact (preclin.evidence_subject_fact) traces to the records behind it. Filled by `python -m pipeline.opentargets
-- evidence`. No data changes here.

BEGIN;
COMMENT ON COLUMN preclin.ot_evidence.detail IS
    'Datasource-specific fields as JSON: the source''s own disease and target identifiers (diseaseFromSourceId, diseaseFromSource, targetFromSourceId), the PubMed ids of the supporting papers (literature; absent when there are none), study id, log2 fold change, clinical significances, Reactome reaction and pathways, matched model phenotypes.';
COMMIT;
