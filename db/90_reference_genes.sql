-- Reference sources for drug targets, each tied to a recorded release.
-- hgnc_gene (pipeline.hgnc): approved human genes with their previous and alias symbols, so a target
--   named by an older or alias symbol (TDGF1, CTGF, CD20) resolves to its current gene.
-- depmap_common_essential (pipeline.depmap): DepMap's CRISPR inferred common-essential genes.
-- chembl_mechanism, chembl_molecule (pipeline.chembl): ChEMBL drug mechanisms of action with each
--   target's human genes, and the parent of every ChEMBL molecule preclin.drug names.

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE IF NOT EXISTS preclin.hgnc_gene (
    hgnc_id           text PRIMARY KEY,
    symbol            text NOT NULL UNIQUE,
    name              text NOT NULL,
    locus_group       text NOT NULL,
    entrez_id         integer,
    ensembl_id        text,
    uniprot_ids       text[] NOT NULL,
    prev_symbols      text[] NOT NULL,
    alias_symbols     text[] NOT NULL,
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release
);
CREATE INDEX IF NOT EXISTS hgnc_gene_entrez_idx ON preclin.hgnc_gene (entrez_id);

CREATE TABLE IF NOT EXISTS preclin.depmap_common_essential (
    entrez_id         integer PRIMARY KEY,
    symbol            text NOT NULL,
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release
);

CREATE TABLE IF NOT EXISTS preclin.chembl_mechanism (
    mec_id              integer PRIMARY KEY,
    molecule_chembl_id  text NOT NULL,
    parent_chembl_id    text NOT NULL,
    target_chembl_id    text,
    target_name         text,
    action_type         text,
    mechanism_of_action text,
    symbols             text[] NOT NULL,
    source_release_id   bigint NOT NULL REFERENCES preclin.evidence_source_release
);
CREATE INDEX IF NOT EXISTS chembl_mechanism_parent_idx ON preclin.chembl_mechanism (parent_chembl_id);

CREATE TABLE IF NOT EXISTS preclin.chembl_molecule (
    molecule_chembl_id text PRIMARY KEY,
    parent_chembl_id   text NOT NULL,
    source_release_id  bigint NOT NULL REFERENCES preclin.evidence_source_release
);
COMMIT;
