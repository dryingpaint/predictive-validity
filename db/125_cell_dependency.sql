-- Cancer cell-line dependency screens published before 2019 (pipeline.depmap dependencies, pipeline.depmap
-- lineages): the screened lines with the year their data became public, each line's lineage mapped to MONDO,
-- and every gene a line depends on. They supply the Cell studies line of the 2026-11-04 comprehensiveness
-- amendment (report/translation_plan.md).

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.cell_line (
    depmap_id       text PRIMARY KEY,
    ccle_name       text NOT NULL,
    lineage         text NOT NULL,
    mondo_id        text,
    llm_decision_id bigint REFERENCES pv_evidence.llm_decision (llm_decision_id)
);
COMMENT ON TABLE preclin.cell_line IS
    'Cancer cell lines screened in the dependency datasets of preclin.cell_screen, with the lineage their source annotates and the MONDO term of that cancer (pipeline.depmap lineages).';
COMMENT ON COLUMN preclin.cell_line.lineage IS
    'The source''s lineage, subtype and sub-subtype joined by "|" (DEMETER2 sample info, else the DepMap 18Q4 primary, secondary and tertiary tissue).';
COMMENT ON COLUMN preclin.cell_line.mondo_id IS
    'The MONDO term of the cancer the lineage names, chosen by an LLM among retrieved MONDO candidates; null when none names it.';

CREATE TABLE preclin.cell_screen (
    depmap_id         text NOT NULL REFERENCES preclin.cell_line (depmap_id),
    dataset           text NOT NULL CHECK (dataset IN ('demeter2', 'avana_2017', 'avana_18q4')),
    screens           text[] NOT NULL,
    public_year       integer NOT NULL,
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release (source_release_id),
    PRIMARY KEY (depmap_id, dataset)
);
COMMENT ON TABLE preclin.cell_screen IS
    'Each cell line''s scores in one dependency dataset and the year the line''s screen data became public: DEMETER2 combined RNAi (the earliest source paper of the screens the line was in: Achilles 2014 for the 216 lines of Achilles v2.4, else Achilles 2017, Marcotte 2016, Project DRIVE 2017), Avana CRISPR scored by CERES in Meyers et al. 2017 (2017), and the lines DepMap 18Q4 added (2018).';
COMMENT ON COLUMN preclin.cell_screen.screens IS
    'The screens behind the line''s scores: achilles, drive, marcotte (RNAi) or avana (CRISPR).';

CREATE TABLE preclin.cell_dependency (
    depmap_id text NOT NULL,
    dataset   text NOT NULL,
    entrez_id integer NOT NULL,
    symbol    text NOT NULL,
    score     double precision NOT NULL,
    PRIMARY KEY (depmap_id, dataset, entrez_id),
    FOREIGN KEY (depmap_id, dataset) REFERENCES preclin.cell_screen ON DELETE CASCADE
);
COMMENT ON TABLE preclin.cell_dependency IS
    'Genes a screened cell line depends on: gene effect scores of -0.5 or lower (the amendment''s threshold; DEMETER2 and CERES both scale the median common-essential gene to -1). Higher scores are not stored, so a screened line absent here for a gene does not depend on it. Gene families DEMETER2 scores jointly are left out.';

COMMIT;
