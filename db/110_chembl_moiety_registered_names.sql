-- Name matches of preclin.chembl_moiety use only the entity's registered UNII names.

BEGIN;
SET LOCAL lock_timeout = '3s';
COMMENT ON COLUMN preclin.chembl_moiety.basis IS
    'The first match found, in this order: drug_chembl_id (the ChEMBL id of one of the entity''s preclin.drug names), inchikey (the standard InChIKey of the entity''s UNII substance equals a ChEMBL compound''s), name (an official, common or code name registered for the entity''s UNII equals, ignoring case and punctuation, the preferred name or a synonym of exactly one ChEMBL parent)';
COMMIT;
