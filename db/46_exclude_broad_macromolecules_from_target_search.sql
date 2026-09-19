-- DNA/RNA-wide ChEMBL mechanisms are broader mechanisms, not specific targets.
-- Retain their structured asset-target rows but keep them out of the specific
-- target-to-phenotype literature queue until mechanism-scoped search is used.

BEGIN;

CREATE OR REPLACE VIEW pv_core.v_target_phenotype_literature_scope AS
SELECT DISTINCT
  scoped.nct_id,
  scoped.asset_entity_id,
  ata.target_entity_id,
  scoped.phenotype_entity_id,
  scoped.indication_role,
  scoped.policy_version
FROM pv_core.v_asset_indication_literature_scope scoped
JOIN pv_evidence.asset_target_assertion ata
  ON ata.asset_entity_id=scoped.asset_entity_id
JOIN pv_core.target target ON target.entity_id=ata.target_entity_id
WHERE ata.role='therapeutic_primary'
  AND target.taxon_id=9606
  AND target.target_kind <> 'nucleic_acid';

COMMIT;
