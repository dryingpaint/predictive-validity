-- Computed physicochemical properties of each molecular entity (pipeline.pubchem properties), so the molecule
-- evidence category can score drug-likeness and brain penetrance. A molecule's structure does not change, so
-- these properties hold as of any phase entry.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.moiety_property (
    moiety_id integer PRIMARY KEY REFERENCES preclin.moiety (moiety_id),
    source text NOT NULL CHECK (source IN ('pubchem', 'chembl')),
    source_id text NOT NULL,
    molecular_weight double precision,
    logp double precision,
    tpsa double precision,
    hbd integer,
    hba integer,
    rotatable_bonds integer,
    ro5_violations integer,
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release (source_release_id)
);
COMMENT ON TABLE preclin.moiety_property IS
    'Computed physicochemical properties of each entity: PubChem for every entity whose UNII carries a PubChem CID, else ChEMBL for small molecules with a development program and a ChEMBL parent (pipeline.pubchem properties)';
COMMENT ON COLUMN preclin.moiety_property.source IS
    'pubchem: PubChem computed properties of the UNII''s CID; chembl: ChEMBL molecule_properties of the entity''s ChEMBL parent';
COMMENT ON COLUMN preclin.moiety_property.source_id IS
    'PubChem CID or ChEMBL parent molecule id the properties were read from';
COMMENT ON COLUMN preclin.moiety_property.molecular_weight IS
    'Molecular weight, g/mol (PubChem MolecularWeight; ChEMBL full_mwt)';
COMMENT ON COLUMN preclin.moiety_property.logp IS
    'Computed octanol-water partition coefficient (PubChem XLogP3; ChEMBL ALogP); null when the source computes none';
COMMENT ON COLUMN preclin.moiety_property.tpsa IS
    'Topological polar surface area, square angstroms (PubChem TPSA; ChEMBL PSA)';
COMMENT ON COLUMN preclin.moiety_property.hbd IS 'Hydrogen-bond donors';
COMMENT ON COLUMN preclin.moiety_property.hba IS 'Hydrogen-bond acceptors';
COMMENT ON COLUMN preclin.moiety_property.rotatable_bonds IS 'Rotatable bonds';
COMMENT ON COLUMN preclin.moiety_property.ro5_violations IS
    'Lipinski Rule-of-5 violations: molecular weight > 500, logP > 5, donors > 5, acceptors > 10 (a missing logP counts as no violation)';

COMMIT;
