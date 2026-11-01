-- Which ChEMBL parent molecules each entity is, so the entity's measured potencies can be read from
-- preclin.chembl_activity: preclin.drug carries a ChEMBL id for only some entities (none for imatinib,
-- aspirin or pembrolizumab), so pipeline.chembl activities also matches the entity's UNII structure
-- and its names.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.chembl_moiety (
    moiety_id integer NOT NULL REFERENCES preclin.moiety (moiety_id),
    parent_chembl_id text NOT NULL,
    basis text NOT NULL CHECK (basis IN ('drug_chembl_id', 'inchikey', 'name')),
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release (source_release_id),
    PRIMARY KEY (moiety_id, parent_chembl_id)
);
COMMENT ON TABLE preclin.chembl_moiety IS
    'ChEMBL parent molecules of each entity with a development program (pipeline.chembl activities)';
COMMENT ON COLUMN preclin.chembl_moiety.basis IS
    'The first match found, in this order: drug_chembl_id (the ChEMBL id of one of the entity''s preclin.drug names), inchikey (the standard InChIKey of the entity''s UNII substance equals a ChEMBL compound''s), name (the entity''s name, alias, code or UNII official, common or code name equals, ignoring case and punctuation, the preferred name or a synonym of exactly one ChEMBL parent)';

COMMIT;
