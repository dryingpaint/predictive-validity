-- Open Targets Platform direct target-disease associations by data source
-- (pipeline.opentargets load), for the targets of entities with development
-- programs. series_years/series_scores give the association score as each
-- year's evidence accrued, so a feature can be taken as of a date.

BEGIN;
SET LOCAL lock_timeout = '90s';

CREATE TABLE IF NOT EXISTS preclin.ot_disease (
    disease_id        text PRIMARY KEY,
    name              text NOT NULL,
    mondo_ids         text[] NOT NULL,
    therapeutic_areas text[] NOT NULL,
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release
);

CREATE TABLE IF NOT EXISTS preclin.ot_association (
    target_ensembl    text NOT NULL,
    disease_id        text NOT NULL,
    datasource        text NOT NULL,
    datatype          text NOT NULL,
    score             double precision NOT NULL,
    evidence_count    integer,
    first_year        smallint,
    series_years      smallint[] NOT NULL,
    series_scores     real[] NOT NULL,
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release,
    PRIMARY KEY (target_ensembl, disease_id, datasource)
);
CREATE INDEX IF NOT EXISTS ot_association_disease_idx ON preclin.ot_association (disease_id);

COMMIT;
