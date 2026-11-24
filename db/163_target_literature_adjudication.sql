-- The target-biology literature of issue #154, resolved against a confirmed set: one careful reading of every candidate
-- study of the yardstick's pairs (preclin.target_literature_adjudication), from which each search's coverage and
-- precision follow; and versioned screens, so a revised screen adds its readings beside the earlier ones and the
-- evidence view reads each record's latest (report/audits/target_literature.md).

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.target_literature_adjudication (
    ensembl_id                  text NOT NULL,
    mondo_id                    text NOT NULL,
    record_id                   text NOT NULL,
    cutoff_year                 integer NOT NULL,
    year                        integer,
    from_screen                 boolean NOT NULL,
    from_web                    boolean NOT NULL,
    from_yardstick              boolean NOT NULL,
    screened_out_sample         boolean NOT NULL,
    original_data               boolean NOT NULL,
    disease_match               text NOT NULL CHECK (disease_match IN ('same_or_subtype', 'related', 'other', 'none')),
    human_cell_perturbation     boolean NOT NULL,
    cell_line_perturbation      boolean NOT NULL,
    diseased_tissue_protein     boolean NOT NULL,
    animal_model_pharmacology   boolean NOT NULL,
    agent_is_program_drug       boolean,
    mouse_genetic_disease_model boolean NOT NULL,
    observational_biomarker     boolean NOT NULL,
    clinical_observation        boolean NOT NULL,
    full_text_read              boolean NOT NULL,
    quote                       text,
    llm_decision_id             bigint NOT NULL,
    PRIMARY KEY (ensembl_id, mondo_id, record_id),
    FOREIGN KEY (ensembl_id, mondo_id) REFERENCES preclin.target_disease (ensembl_id, mondo_id)
);
COMMENT ON TABLE preclin.target_literature_adjudication IS
    'The confirmed set of #154''s target evidence for the yardstick''s 100 pairs: one careful reading (task target_literature_adjudicate, a stronger model with a strict rubric that reads full text when the abstract cannot decide) of every candidate study any search found for the pair, plus a seeded sample of records the screen read as showing nothing. Each search''s coverage and precision are scored against it (pipeline.target_literature resolve-score). A study counts for a kind when it is original data, its disease is the pair''s or a subtype, it shows the kind, and it was published by the pair''s cutoff year.';
COMMENT ON COLUMN preclin.target_literature_adjudication.ensembl_id IS 'The pair''s gene.';
COMMENT ON COLUMN preclin.target_literature_adjudication.mondo_id IS 'The pair''s disease.';
COMMENT ON COLUMN preclin.target_literature_adjudication.record_id IS 'The record judged: a PMID, or a Europe PMC id (SOURCE:ID).';
COMMENT ON COLUMN preclin.target_literature_adjudication.cutoff_year IS 'The pair''s cutoff as the yardstick asked it: studies published in or before it count.';
COMMENT ON COLUMN preclin.target_literature_adjudication.year IS 'The record''s publication year, from the stored record.';
COMMENT ON COLUMN preclin.target_literature_adjudication.from_screen IS 'The screen read the record as showing at least one kind for the pair (preclin.target_literature_screen).';
COMMENT ON COLUMN preclin.target_literature_adjudication.from_web IS 'The web arm named the record for the pair (preclin.target_literature_web_study, arm web, verified).';
COMMENT ON COLUMN preclin.target_literature_adjudication.from_yardstick IS 'The yardstick named the record for the pair (arm yardstick, verified).';
COMMENT ON COLUMN preclin.target_literature_adjudication.screened_out_sample IS 'Drawn in the seeded sample of retrieved records the screen read as showing no kind, to measure what the screen misses.';
COMMENT ON COLUMN preclin.target_literature_adjudication.original_data IS 'The record reports new experimental or clinical results.';
COMMENT ON COLUMN preclin.target_literature_adjudication.disease_match IS 'same_or_subtype (counts), related, other or none, as in preclin.target_literature_screen.';
COMMENT ON COLUMN preclin.target_literature_adjudication.human_cell_perturbation IS 'Changing the target in primary human cells or tissue changes a disease feature.';
COMMENT ON COLUMN preclin.target_literature_adjudication.cell_line_perturbation IS 'The same in an established cell line.';
COMMENT ON COLUMN preclin.target_literature_adjudication.diseased_tissue_protein IS 'The target''s protein differs in patients'' diseased tissue.';
COMMENT ON COLUMN preclin.target_literature_adjudication.animal_model_pharmacology IS 'A non-genetic change to the target alters an animal model of the disease.';
COMMENT ON COLUMN preclin.target_literature_adjudication.agent_is_program_drug IS 'Under animal_model_pharmacology, whether the only agent is one of the pair''s program drugs; null otherwise.';
COMMENT ON COLUMN preclin.target_literature_adjudication.mouse_genetic_disease_model IS 'A knockout, knock-in or transgene of the target alters an animal model of the disease.';
COMMENT ON COLUMN preclin.target_literature_adjudication.observational_biomarker IS 'The target or its product, measured in patients'' blood, another fluid or by imaging, tracks the disease in an observational study.';
COMMENT ON COLUMN preclin.target_literature_adjudication.clinical_observation IS 'An effect seen in people outside a trial of a drug for this disease implicates the target.';
COMMENT ON COLUMN preclin.target_literature_adjudication.full_text_read IS 'The reader opened the full text (or the publisher page) because the abstract could not decide.';
COMMENT ON COLUMN preclin.target_literature_adjudication.quote IS 'The sentence that decided the reading.';
COMMENT ON COLUMN preclin.target_literature_adjudication.llm_decision_id IS 'The decision (pv_evidence.llm_decision, task target_literature_adjudicate).';

ALTER TABLE preclin.target_literature_screen ADD COLUMN screen_version text NOT NULL DEFAULT 'v2';
ALTER TABLE preclin.target_literature_screen DROP CONSTRAINT target_literature_screen_pkey;
ALTER TABLE preclin.target_literature_screen ADD PRIMARY KEY (ensembl_id, mondo_id, record_id, screen_version);
COMMENT ON COLUMN preclin.target_literature_screen.screen_version IS
    'The screen''s prompt_version: v2, the gated screen; v3, the screen with definitions revised against the adjudication (report/audits/target_literature.md). A revision adds rows beside the earlier ones; preclin.target_literature_evidence reads each record''s latest version.';

CREATE OR REPLACE VIEW preclin.target_literature_evidence AS
WITH origin_year AS (
    SELECT regexp_replace(record_id, '^PMID:', '') AS record_id, min(year) AS year
    FROM preclin.target_disease_source GROUP BY 1
), latest AS (
    SELECT DISTINCT ON (ensembl_id, mondo_id, record_id) *
    FROM preclin.target_literature_screen
    ORDER BY ensembl_id, mondo_id, record_id, screen_version DESC
), counted AS (
    SELECT s.ensembl_id, s.mondo_id, s.record_id, s.agent_is_program_drug,
           coalesce(p.year, r.year, o.year) AS year,
           k.kind
    FROM latest s
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
    'One row per target-disease pair and kind of #154 target evidence with at least one qualifying record (original data, the pair''s disease or a subtype, the kind shown), read from each record''s latest screen version (preclin.target_literature_screen). DESCRIPTIVE: the kinds failed #154''s registered pilot gate; their pair-level coverage and precision against an adjudicated set are in report/audits/target_literature.md. A phase entry has the kind when a record is dated by the year before its entry: compare record_years (or first_year) with the entry year when reading.';

COMMIT;
