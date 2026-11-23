-- The target-biology literature of issue #154, per pair: the Firecrawl kind that returned each hit, and one view of
-- each pair's qualifying studies per kind. The seven kinds failed the registered pilot gate (recall below 80%;
-- report/audits/target_literature_gate.md), so they are descriptive: labelled, never tested.

BEGIN;
SET LOCAL lock_timeout = '3s';

ALTER TABLE preclin.target_literature_hit ADD COLUMN kind text NOT NULL DEFAULT '';
ALTER TABLE preclin.target_literature_hit DROP CONSTRAINT target_literature_hit_pkey;
ALTER TABLE preclin.target_literature_hit ADD PRIMARY KEY (ensembl_id, mondo_id, cutoff_year, source, kind, record_id);
COMMENT ON COLUMN preclin.target_literature_hit.kind IS
    'For a firecrawl hit, the kind of evidence its search asked for (the query is preclin.target_literature_search at the same pair, cutoff, source and kind); empty for pubmed, europepmc and firecrawl_related, and for the pilot''s firecrawl hits, stored before this column existed.';

CREATE VIEW preclin.target_literature_evidence AS
WITH counted AS (
    SELECT s.ensembl_id, s.mondo_id, s.record_id, s.agent_is_program_drug,
           coalesce(p.year, r.year) AS year,
           k.kind
    FROM preclin.target_literature_screen s
    LEFT JOIN public.publications p ON p.pmid = s.record_id
    LEFT JOIN preclin.literature_record r ON r.record_id = s.record_id
    CROSS JOIN LATERAL (VALUES ('human_cell_perturbation', s.human_cell_perturbation),
                               ('cell_line_perturbation', s.cell_line_perturbation),
                               ('diseased_tissue_protein', s.diseased_tissue_protein),
                               ('animal_model_pharmacology', s.animal_model_pharmacology),
                               ('mouse_genetic_disease_model', s.mouse_genetic_disease_model),
                               ('observational_biomarker', s.observational_biomarker),
                               ('clinical_observation', s.clinical_observation)) k(kind, shown)
    WHERE s.original_data AND s.disease_match = 'same_or_subtype' AND k.shown
)
SELECT ensembl_id, mondo_id, kind,
       min(year) AS first_year,
       min(year) FILTER (WHERE kind <> 'animal_model_pharmacology' OR agent_is_program_drug IS FALSE) AS first_year_other_agent,
       count(*) AS records,
       array_agg(record_id ORDER BY year NULLS LAST, record_id) AS record_ids,
       array_agg(year ORDER BY year NULLS LAST, record_id) AS record_years,
       CASE WHEN kind = 'animal_model_pharmacology' THEN bool_and(agent_is_program_drug) END AS program_drug_only
FROM counted
GROUP BY ensembl_id, mondo_id, kind;

COMMENT ON VIEW preclin.target_literature_evidence IS
    'One row per target-disease pair and kind of #154 target evidence with at least one qualifying record (original data, the pair''s disease or a subtype, the kind shown; preclin.target_literature_screen). DESCRIPTIVE ONLY: no kind passed the registered pilot gate (retrieval recall below 80%; report/audits/target_literature_gate.md), so these are counts of what the search found, not complete evidence, and are not tested. A phase entry has the kind when a record is dated by the year before its entry: compare record_years (or first_year) with the entry year when reading.';
COMMENT ON COLUMN preclin.target_literature_evidence.ensembl_id IS 'The pair''s gene (preclin.target_disease).';
COMMENT ON COLUMN preclin.target_literature_evidence.mondo_id IS 'The pair''s disease (preclin.target_disease).';
COMMENT ON COLUMN preclin.target_literature_evidence.kind IS
    'human_cell_perturbation (primary human cells or tissue), cell_line_perturbation (established cell lines, literature part), diseased_tissue_protein (protein in patients'' tissue), animal_model_pharmacology (a non-genetic change to the target alters an animal model, any agent), mouse_genetic_disease_model (a knockout or transgene alters a disease model), observational_biomarker or clinical_observation. Descriptive only (see the view''s comment).';
COMMENT ON COLUMN preclin.target_literature_evidence.first_year IS 'Publication year of the earliest qualifying record; null when no qualifying record has a year.';
COMMENT ON COLUMN preclin.target_literature_evidence.first_year_other_agent IS
    'For animal_model_pharmacology, the earliest year of a qualifying record whose agent was not one of the pair''s program drugs (the registered L2''s other agents); for other kinds, the same as first_year.';
COMMENT ON COLUMN preclin.target_literature_evidence.records IS 'Qualifying records.';
COMMENT ON COLUMN preclin.target_literature_evidence.record_ids IS 'The qualifying records (PMIDs, or Europe PMC ids SOURCE:ID), earliest first.';
COMMENT ON COLUMN preclin.target_literature_evidence.record_years IS 'Each record''s publication year, in record_ids order; null when unknown.';
COMMENT ON COLUMN preclin.target_literature_evidence.program_drug_only IS
    'For animal_model_pharmacology: true when every qualifying record''s only agent was one of the pair''s program drugs, false when any used another agent; null for other kinds.';

COMMIT;
