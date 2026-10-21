-- Open Targets evidence rows behind the associations in preclin.ot_association, for the
-- targets of entities with programs: one row per evidence item, with its date, the
-- direction of the genetic effect on the target and on the trait where the source gives
-- it, the source's confidence, and source-specific detail (burden test statistics,
-- ClinVar significance, mouse model and phenotypes, expression contrast). Also each
-- target's mouse mutant phenotypes (MGI and IMPC), with their Mammalian Phenotype classes.

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE IF NOT EXISTS preclin.ot_evidence (
    evidence_id          text PRIMARY KEY,
    target_ensembl       text NOT NULL,
    disease_id           text NOT NULL,
    datasource           text NOT NULL,
    score                real,
    resource_score       real,
    evidence_year        integer,
    direction_on_target  text,
    direction_on_trait   text,
    confidence           text,
    allelic_requirements text[],
    variant_consequence  text,
    detail               jsonb NOT NULL,
    source_release_id    bigint NOT NULL REFERENCES preclin.evidence_source_release
);
CREATE INDEX IF NOT EXISTS ot_evidence_target_idx ON preclin.ot_evidence (target_ensembl, datasource);
CREATE TABLE IF NOT EXISTS preclin.ot_mouse_phenotype (
    target_ensembl     text NOT NULL,
    phenotype_id       text NOT NULL,
    phenotype_label    text NOT NULL,
    class_ids          text[] NOT NULL,
    models             text[] NOT NULL,
    source_release_id  bigint NOT NULL REFERENCES preclin.evidence_source_release,
    PRIMARY KEY (target_ensembl, phenotype_id)
);
COMMIT;
