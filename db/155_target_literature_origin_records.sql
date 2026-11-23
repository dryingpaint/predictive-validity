-- One literature store per target-disease pair: the target-biology literature of #154 reads the pre-entry records
-- of the origin search (#146, preclin.target_disease_source) as hits, linked rather than copied, and takes their
-- publication year from there. A record's text lives once: public.publications (PubMed), preclin.literature_record
-- (Europe PMC outside MEDLINE) or preclin.target_disease_source (the origin search's own copy).

BEGIN;
SET LOCAL lock_timeout = '3s';

ALTER TABLE preclin.target_literature_search DROP CONSTRAINT target_literature_search_source_check;
ALTER TABLE preclin.target_literature_search ADD CONSTRAINT target_literature_search_source_check
    CHECK (source IN ('pubmed', 'europepmc', 'firecrawl', 'firecrawl_related', 'origin_pubmed', 'origin_europepmc'));
COMMENT ON COLUMN preclin.target_literature_search.source IS
    'pubmed, europepmc (records outside MEDLINE), firecrawl (one semantic search per kind), firecrawl_related (papers related to the pair''s first screened-in record), or origin_pubmed / origin_europepmc: the origin search''s records for the pair (preclin.target_disease_search and preclin.target_disease_source), read as hits up to this search''s cutoff; query and names are the origin search''s, run to the year before the pair''s first Phase 2 or 3 entry.';
COMMENT ON COLUMN preclin.target_literature_hit.record_id IS
    'A PMID, or a Europe PMC id (SOURCE:ID) for a record outside PubMed. The origin search''s PMID:N ids are stored as N. Text and year: public.publications, else preclin.literature_record, else preclin.target_disease_source.';

CREATE OR REPLACE VIEW preclin.target_literature_evidence AS
WITH origin_year AS (
    SELECT regexp_replace(record_id, '^PMID:', '') AS record_id, min(year) AS year
    FROM preclin.target_disease_source GROUP BY 1
), counted AS (
    SELECT s.ensembl_id, s.mondo_id, s.record_id, s.agent_is_program_drug,
           coalesce(p.year, r.year, o.year) AS year,
           k.kind
    FROM preclin.target_literature_screen s
    LEFT JOIN public.publications p ON p.pmid = s.record_id
    LEFT JOIN preclin.literature_record r ON r.record_id = s.record_id
    LEFT JOIN origin_year o ON o.record_id = s.record_id
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
    'One row per target-disease pair and kind of #154 target evidence with at least one qualifying record (original data, the pair''s disease or a subtype, the kind shown; preclin.target_literature_screen). DESCRIPTIVE ONLY: no kind passed the registered pilot gate (retrieval recall below 80%; report/audits/target_literature_gate.md), so these are counts of what the search found, not complete evidence, and are not tested. A phase entry has the kind when a record is dated by the year before its entry: compare record_years (or first_year) with the entry year when reading. Years come from public.publications, preclin.literature_record or preclin.target_disease_source.';

COMMIT;
