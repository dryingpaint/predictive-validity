-- Measured potencies of the benchmark's entities from ChEMBL (pipeline.chembl activities): one row per
-- activity, with the targets and documents the activities name, so Section 2 can score each program by
-- what was known of its drug's pharmacology the year before it entered a phase.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.chembl_target (
    target_chembl_id text PRIMARY KEY,
    pref_name text,
    target_type text NOT NULL,
    organism text,
    symbols text[] NOT NULL,
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release (source_release_id)
);
COMMENT ON TABLE preclin.chembl_target IS
    'ChEMBL targets named by preclin.chembl_activity (pipeline.chembl activities)';
COMMENT ON COLUMN preclin.chembl_target.target_type IS
    'ChEMBL target type: SINGLE PROTEIN, PROTEIN COMPLEX, PROTEIN FAMILY, SELECTIVITY GROUP, ...';
COMMENT ON COLUMN preclin.chembl_target.symbols IS
    'HGNC approved symbols of the target''s UniProt components (preclin.hgnc_gene); empty when none maps';

CREATE TABLE preclin.chembl_document (
    document_chembl_id text PRIMARY KEY,
    year integer,
    journal text,
    src_id integer,
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release (source_release_id)
);
COMMENT ON TABLE preclin.chembl_document IS
    'ChEMBL documents (papers, patents, deposited datasets) that report preclin.chembl_activity rows';
COMMENT ON COLUMN preclin.chembl_document.year IS
    'Publication year of a paper, the year ChEMBL gives a patent, or the deposition year of a dataset; null when ChEMBL gives none';
COMMENT ON COLUMN preclin.chembl_document.src_id IS
    'ChEMBL source: 1 scientific literature, 38 patents, other values deposited datasets';

CREATE TABLE preclin.chembl_activity (
    activity_id bigint PRIMARY KEY,
    molecule_chembl_id text NOT NULL,
    parent_chembl_id text NOT NULL,
    target_chembl_id text NOT NULL REFERENCES preclin.chembl_target (target_chembl_id),
    standard_type text NOT NULL,
    pchembl_value numeric(4, 2) NOT NULL,
    assay_chembl_id text NOT NULL,
    assay_type text NOT NULL,
    bao_format text,
    bao_label text,
    document_chembl_id text NOT NULL REFERENCES preclin.chembl_document (document_chembl_id),
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release (source_release_id)
);
CREATE INDEX chembl_activity_parent_idx ON preclin.chembl_activity (parent_chembl_id);
COMMENT ON TABLE preclin.chembl_activity IS
    'ChEMBL activities with a pChEMBL value against a human target, for the parent of every ChEMBL molecule of an entity with a development program; rows ChEMBL flags as doubtful or as potential duplicates are left out';
COMMENT ON COLUMN preclin.chembl_activity.molecule_chembl_id IS
    'The form measured (a salt or the parent itself)';
COMMENT ON COLUMN preclin.chembl_activity.standard_type IS
    'IC50, EC50, Ki, Kd, AC50, Potency, ...: the measurement pchembl_value converts';
COMMENT ON COLUMN preclin.chembl_activity.pchembl_value IS
    '-log10 of the molar half-maximal concentration or affinity (7 = 100 nM)';
COMMENT ON COLUMN preclin.chembl_activity.assay_type IS
    'ChEMBL assay type: B binding, F functional, A ADME, T toxicity, P physicochemical, U unclassified';
COMMENT ON COLUMN preclin.chembl_activity.bao_format IS
    'BioAssay Ontology format: BAO_0000219 cell-based, BAO_0000357 single protein, BAO_0000224 protein, BAO_0000249 cell membrane, ...';

COMMIT;
