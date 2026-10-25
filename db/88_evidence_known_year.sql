-- The year each Open Targets evidence item became known, where the item's own date is missing or
-- is not that year: ClinVar records carry their latest evaluation date, IMPC-consortium mouse models
-- none (or the gene's first literature year), and some Expression Atlas, IntOGen and CRISPR-screen
-- rows no publication. pipeline.evidence_dates fills preclin.evidence_known_year from the sources'
-- own release history; pipeline.opentargets evidence dates each row from it and records how.

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE IF NOT EXISTS preclin.evidence_known_year (
    datasource         text NOT NULL,
    key                text NOT NULL,
    year               integer NOT NULL,
    basis              text NOT NULL,
    source_release_id  bigint NOT NULL REFERENCES preclin.evidence_source_release,
    PRIMARY KEY (datasource, key)
);
COMMENT ON TABLE preclin.evidence_known_year IS
    'Year an evidence item became public, by source key (ClinVar RCV accession, IMPC allele symbol, '
    'study accession or cohort), from the source''s own release history (pipeline.evidence_dates)';
COMMENT ON COLUMN preclin.evidence_known_year.basis IS
    'How the year was found: clinvar_snapshot (first yearly ClinVar snapshot showing the record with '
    'its current significance), clinvar_evaluated (record already in the earliest snapshot, Feb 2015, '
    'dated by its evaluation), impc_release (first IMPC data release with phenotype calls for the '
    'allele), geo_public (GEO public date of the experiment), publication (the cohort''s or screen''s paper)';

ALTER TABLE preclin.ot_evidence ADD COLUMN IF NOT EXISTS year_basis text;
COMMENT ON COLUMN preclin.ot_evidence.evidence_year IS
    'Year the evidence became known: the year in preclin.evidence_known_year for its source key where '
    'there is one, else the source''s publication or evidence date; null when neither exists';
COMMENT ON COLUMN preclin.ot_evidence.year_basis IS
    'open_targets (the row''s own publication or evidence date) or the basis of its '
    'preclin.evidence_known_year row';
COMMENT ON COLUMN preclin.ot_association.series_years IS
    'Years at which the association score changed, rebuilt from the dated rows of preclin.ot_evidence '
    '(pipeline.opentargets evidence); undated rows count only in the release score';
COMMIT;
