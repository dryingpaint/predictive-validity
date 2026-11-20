-- Target-disease hypotheses (pipeline.target_disease): one row per primary target and program disease that reached
-- Phase 2, and what first proposed each, so the evidence for a hypothesis, its origin and how its programs failed join
-- on one key. Issue #146; the target-literature lines registered in #143 add a child table on the same key.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE IF NOT EXISTS preclin.target_disease (
    ensembl_id          text NOT NULL,
    mondo_id            text NOT NULL,
    symbol              text,
    first_entry         date NOT NULL,
    programs            integer NOT NULL CHECK (programs > 0),
    validated_at_entry  boolean NOT NULL,
    method_id           text NOT NULL REFERENCES preclin.analysis_method,
    PRIMARY KEY (ensembl_id, mondo_id)
);
COMMENT ON TABLE preclin.target_disease IS
    'One row per target-disease hypothesis that reached Phase 2: a human primary target (preclin.moiety_target, is_primary) and the disease of a development program on it that entered Phase 2 or 3 with an industry trial (report.section1.phase_rows). Rebuilt by pipeline.target_disease build; a pair that no longer qualifies is dropped unless it carries a labelled origin.';
COMMENT ON COLUMN preclin.target_disease.ensembl_id IS 'Ensembl gene id of the target (public.targets.ensembl_id).';
COMMENT ON COLUMN preclin.target_disease.mondo_id IS 'MONDO term of the program disease.';
COMMENT ON COLUMN preclin.target_disease.symbol IS 'Gene symbol, for reading; public.targets.symbol.';
COMMENT ON COLUMN preclin.target_disease.first_entry IS 'Earliest Phase 2 or Phase 3 entry of any program on the target in this disease: the date the hypothesis was first tested in patients, and the cutoff for what could have proposed it.';
COMMENT ON COLUMN preclin.target_disease.programs IS 'Programs on the target in this disease that entered Phase 2 or 3.';
COMMENT ON COLUMN preclin.target_disease.validated_at_entry IS 'An entity on the target was FDA-approved for this disease (MONDO Lin >= 0.8) before first_entry: the hypothesis was already proven, so its origin is not tested.';

CREATE TABLE IF NOT EXISTS preclin.target_disease_origin (
    ensembl_id        text NOT NULL,
    mondo_id          text NOT NULL,
    basis             text NOT NULL CHECK (basis IN ('provisional', 'labelled')),
    origin            text NOT NULL CHECK (origin IN (
                          'human_genetics', 'tumour_genetics', 'diseased_tissue', 'mouse_genetics',
                          'curated_pathway', 'cell_screen', 'earlier_drug_other_disease',
                          'observational_biomarker', 'human_cell_perturbation', 'animal_model_pharmacology',
                          'clinical_observation', 'phenotypic_screen', 'unclear')),
    origin_year       integer,
    secondary_origin  text,
    grade             text CHECK (grade IN ('stated', 'pattern', 'none')),
    sources           text[] NOT NULL DEFAULT '{}',
    quote             text,
    llm_decision_id   bigint REFERENCES pv_evidence.llm_decision,
    method_id         text NOT NULL REFERENCES preclin.analysis_method,
    PRIMARY KEY (ensembl_id, mondo_id, basis),
    FOREIGN KEY (ensembl_id, mondo_id) REFERENCES preclin.target_disease,
    CHECK ((basis = 'labelled') = (grade IS NOT NULL))
);
COMMENT ON TABLE preclin.target_disease_origin IS
    'What first proposed each target-disease hypothesis (issue #146). provisional: the earliest dated evidence item for the pair before its first entry, from the evidence the report already holds (pipeline.target_disease provisional). labelled: a reading of sources dated before first entry that states or shows what motivated the target (pipeline.target_disease label).';
COMMENT ON COLUMN preclin.target_disease_origin.basis IS 'provisional (earliest dated evidence item) or labelled (read from pre-entry sources).';
COMMENT ON COLUMN preclin.target_disease_origin.origin IS
    'human_genetics: germline variants link the target to the disease (GWAS, gene burden, Mendelian); tumour_genetics: the gene is recurrently mutated in the cancer; diseased_tissue: the gene''s RNA level differs in diseased tissue; mouse_genetics: knocked-out or mutant mice show the disease; curated_pathway: a curated pathway shows a disease mutation disrupting the target; cell_screen: a gene-knockout screen in cells; earlier_drug_other_disease: a drug on the target was approved for another disease; observational_biomarker: the target or its product tracks the disease in patients; human_cell_perturbation: perturbing the target in human cells or tissue changes a disease phenotype; animal_model_pharmacology: modulating the target in an animal disease model changes it; clinical_observation: an effect seen in people, such as a side effect; phenotypic_screen: a molecule found without a target hypothesis came first; unclear: no source settles it. The last six exist only for labelled rows.';
COMMENT ON COLUMN preclin.target_disease_origin.origin_year IS 'Year the origin''s evidence became public: for provisional rows the earliest dated item, for labelled rows the source''s publication year. Before the year of first_entry.';
COMMENT ON COLUMN preclin.target_disease_origin.secondary_origin IS 'A second origin from the same list where the sources show two; null otherwise.';
COMMENT ON COLUMN preclin.target_disease_origin.grade IS 'Labelled rows only: stated (a source says why the target was chosen), pattern (a source shows the reasoning without saying so), none (unclear). Null for provisional rows.';
COMMENT ON COLUMN preclin.target_disease_origin.sources IS 'Labelled rows: PMIDs, patent numbers or URLs the decision cites, each retrieved during the decision and dated before first entry. Provisional rows: empty.';
COMMENT ON COLUMN preclin.target_disease_origin.llm_decision_id IS 'The decision behind a labelled row; null for provisional rows.';
COMMIT;
