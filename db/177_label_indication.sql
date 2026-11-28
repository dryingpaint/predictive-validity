-- Which shortlisted diseases (#198) each current FDA label is indicated for (pipeline.single_target indications), so
-- approved pathways per disease count drugs of every approval year, not only those with trials since 2008 (#193).
-- mechanism_pathway now also covers the mechanisms of labelled drugs outside the atlas.

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE preclin.label_indication (
    set_id          text NOT NULL,
    mondo_id        text NOT NULL,
    llm_decision_id bigint NOT NULL REFERENCES pv_evidence.llm_decision,
    PRIMARY KEY (set_id, mondo_id)
);
COMMENT ON TABLE preclin.label_indication IS
    'One row per current FDA label (preclin.fda_label) and shortlisted disease of pipeline.single_target (SHORTLIST, EVENT_SHORTLIST) that the label''s Indications and Usage section treats or prevents. A label indicated for none has no row. Written by pipeline.single_target indications; a run replaces the table.';
COMMENT ON COLUMN preclin.label_indication.set_id IS 'preclin.fda_label.set_id.';
COMMENT ON COLUMN preclin.label_indication.mondo_id IS 'The shortlisted disease: the label treats it, or for an event disease reduces its events (a statin reducing myocardial infarction counts for coronary artery disease; an anticoagulant reducing stroke in nonvalvular atrial fibrillation counts for atrial fibrillation).';
COMMENT ON COLUMN preclin.label_indication.llm_decision_id IS 'The decision behind the row (task label_indication), made once per distinct indications text.';

COMMENT ON TABLE preclin.mechanism_pathway IS
    'One row per mechanism of preclin.atlas_mechanism and per mechanism of an FDA-labelled entity outside the atlas: the signalling pathways its drugs act through (issue #198). Written by pipeline.single_target pathways; a run replaces the table.';
COMMENT ON COLUMN preclin.mechanism_pathway.mechanism_key IS
    'target_label|action: preclin.atlas_mechanism.mechanism_key for an atlas mechanism; for a labelled entity outside the atlas, its reviewed target and action (preclin.atlas_moiety_review) or else its primary targets'' symbols and actions from preclin.moiety_target, each joined with ";" (pipeline.single_target.mechanism_keys). Not a foreign key, so an atlas rebuild is not blocked.';
COMMIT;
