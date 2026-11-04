-- Column comments for the cell-line dependency tables of migration 125.

BEGIN;
SET LOCAL lock_timeout = '3s';

COMMENT ON COLUMN preclin.cell_line.depmap_id IS
    'DepMap''s stable cell-line id (ACH-…); for the one line Meyers et al. 2017 screened that DepMap never re-released, its CCLE name.';
COMMENT ON COLUMN preclin.cell_line.ccle_name IS
    'The line''s CCLE name: its stripped name and tissue, e.g. A549_LUNG.';
COMMENT ON COLUMN preclin.cell_line.llm_decision_id IS
    'The pv_evidence.llm_decision (task cell_line_lineage_mondo) that chose mondo_id; null until pipeline.depmap lineages runs.';

COMMENT ON COLUMN preclin.cell_screen.depmap_id IS 'The screened line (preclin.cell_line).';
COMMENT ON COLUMN preclin.cell_screen.dataset IS
    'demeter2: DEMETER2 combined RNAi scores (19Q3 re-release); avana_2017: Avana CRISPR scored by CERES in Meyers et al. 2017; avana_18q4: the Avana lines DepMap 18Q4 first released, with their 18Q4 CERES scores.';
COMMENT ON COLUMN preclin.cell_screen.public_year IS
    'Year the line''s screen data became public: the earliest publication year of the source papers of its screens (pipeline.depmap SCREEN_YEARS).';
COMMENT ON COLUMN preclin.cell_screen.source_release_id IS
    'The pulled files (preclin.evidence_source_release), whose metadata lists the source papers and their years.';

COMMENT ON COLUMN preclin.cell_dependency.depmap_id IS 'The cell line.';
COMMENT ON COLUMN preclin.cell_dependency.dataset IS 'The dataset of the score (preclin.cell_screen.dataset).';
COMMENT ON COLUMN preclin.cell_dependency.entrez_id IS 'The gene''s NCBI Entrez id, joined to Ensembl through preclin.hgnc_gene.';
COMMENT ON COLUMN preclin.cell_dependency.symbol IS 'The gene symbol as the source wrote it.';
COMMENT ON COLUMN preclin.cell_dependency.score IS
    'Gene effect: DEMETER2 or CERES, scaled so the median common-essential gene is -1; only scores of -0.5 or lower are stored.';

COMMIT;
