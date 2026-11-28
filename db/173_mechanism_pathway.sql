-- The signalling pathway each atlas mechanism acts through (pipeline.single_target pathways), so the limits of
-- single-target drugs (#197) count pathways rather than targets: IL-17A and IL-17A/F antibodies share one pathway,
-- and an IL-17A/TNF bispecific spans two. Definitions registered in #198.

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE preclin.mechanism_pathway (
    mechanism_key     text PRIMARY KEY,
    kind              text NOT NULL CHECK (kind IN ('specific', 'broad', 'no_target')),
    pathways          text[] NOT NULL,
    llm_decision_id   bigint NOT NULL REFERENCES pv_evidence.llm_decision,
    merge_decision_id bigint REFERENCES pv_evidence.llm_decision,
    CHECK ((kind = 'specific') = (cardinality(pathways) > 0))
);
COMMENT ON TABLE preclin.mechanism_pathway IS
    'One row per mechanism of preclin.atlas_mechanism: the signalling pathways its drugs act through (issue #198). Written by pipeline.single_target pathways; a run replaces the table.';
COMMENT ON COLUMN preclin.mechanism_pathway.mechanism_key IS
    'preclin.atlas_mechanism.mechanism_key (target_label|action). Not a foreign key, so an atlas rebuild is not blocked; a key the atlas drops is left until the next run.';
COMMENT ON COLUMN preclin.mechanism_pathway.kind IS
    'specific: the drugs act through one to three named pathways; broad: they act through more than three, or through a process rather than a pathway (multikinase inhibitors, cytotoxic chemotherapy, cell therapy without a defined antigen); no_target: no human target is resolved.';
COMMENT ON COLUMN preclin.mechanism_pathway.pathways IS
    'Canonical pathway names (task pathway_names merges spelling variants of one pathway). A pathway is a ligand or hormone with its receptors (IL-17: IL-17A, IL-17F, IL-17RA, IL-17RC; GLP-1), an intracellular cascade when the target sits inside it (JAK-STAT), a cell population a depleting drug removes (B cells), or the target''s own family when none of these fits. Upstream and downstream cytokines are separate pathways (IL-23, IL-17). Direction of action is ignored; the mechanism key keeps it. Empty unless kind is specific.';
COMMENT ON COLUMN preclin.mechanism_pathway.llm_decision_id IS 'The decision behind kind and the pathways as first named (task mechanism_pathway).';
COMMENT ON COLUMN preclin.mechanism_pathway.merge_decision_id IS 'The decision that mapped the first-named pathways to canonical names (task pathway_names); null when kind is not specific.';
COMMIT;
