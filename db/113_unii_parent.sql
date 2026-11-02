-- The parent substance of each salt, hydrate or solvate UNII, so pipeline.drugs unii can offer the parent
-- when GSRS registers an entity's sponsor code on the salt record only (TAK-418 on its hydrochloride).

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.unii_parent (
    unii text NOT NULL REFERENCES preclin.unii_substance (unii),
    parent_unii text NOT NULL REFERENCES preclin.unii_substance (unii),
    PRIMARY KEY (unii, parent_unii)
);
COMMENT ON TABLE preclin.unii_parent IS
    'Salts, hydrates and solvates (unii) and the parent substance each contains (parent_unii): a carbon-containing component of the substance''s GSRS SMILES equals the parent''s whole SMILES, both with charged O, S and N atoms neutralised; the parent is an ingredient substance of net charge zero (pipeline.unii load)';

COMMIT;
