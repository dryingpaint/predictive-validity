-- Whether another drug's success on a stopped drug's target came from the target alone or from the target with a
-- partner drug (pipeline.single_target regimens, issue #194): the regimen of each trial behind such a success, and
-- per stop whether the success needed a partner and whether that partner works on its own. The combination
-- definition is registered in #198.

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE preclin.trial_regimen (
    nct_id            text NOT NULL REFERENCES preclin.ctgov_study(nct_id),
    moiety_id         integer NOT NULL REFERENCES preclin.moiety,
    regimen           text NOT NULL CHECK (regimen IN ('monotherapy', 'add_on_background', 'combination')),
    partner           text,
    partner_moiety_id integer REFERENCES preclin.moiety,
    quote             text NOT NULL,
    llm_decision_id   bigint NOT NULL REFERENCES pv_evidence.llm_decision(llm_decision_id),
    PRIMARY KEY (nct_id, moiety_id),
    CHECK ((regimen = 'combination') = (partner IS NOT NULL)),
    CHECK (partner_moiety_id IS NULL OR regimen = 'combination')
);
COMMENT ON TABLE preclin.trial_regimen IS
    'Phase 2/3 trials that met their primary endpoint and make another drug on a stopped drug''s target a success in the stopped disease (preclin.stop_target_history target_fate worked_here or worked_here_selected), and the met trials in that disease of the partners those successes were paired with: the regimen the drug was tested in. A combination is two active agents on different pathways given together as the tested regimen (a co-formulation, one molecule spanning two pathways, or a protocol-set pairing); background care every arm receives is not one (#198). Judged by an LLM from the title, summary, arm groups and interventions. Written by pipeline.single_target regimens; a run replaces the table.';
COMMENT ON COLUMN preclin.trial_regimen.nct_id IS 'The trial.';
COMMENT ON COLUMN preclin.trial_regimen.moiety_id IS 'The drug whose regimen is read: one trial can test two drugs of interest in different regimens (one alone in one arm, both together in another), so the regimen belongs to the trial and the drug.';
COMMENT ON COLUMN preclin.trial_regimen.regimen IS 'monotherapy: some experimental arm gives the drug without another active agent; add_on_background: the drug is added to background care every arm receives; combination: every experimental arm with the drug pairs it with another active agent on a different pathway.';
COMMENT ON COLUMN preclin.trial_regimen.partner IS 'The agent or agents paired with the drug, as the record names them; null unless the regimen is combination.';
COMMENT ON COLUMN preclin.trial_regimen.partner_moiety_id IS 'The partner as an entity of preclin.moiety, chosen from the entities the trial''s interventions resolve to (preclin.drug_moiety); null when the regimen is not combination or the partner resolves to none. With several partners, the one newest to the regimen.';
COMMENT ON COLUMN preclin.trial_regimen.quote IS 'The record text (title, summary or arm group) showing the regimen, copied exactly.';
COMMENT ON COLUMN preclin.trial_regimen.llm_decision_id IS 'The decision behind the row (task trial_regimen).';

ALTER TABLE preclin.stop_target_history
    ADD COLUMN success_regimen text CHECK (success_regimen IN ('alone', 'with_partner', 'unknown')),
    ADD COLUMN partner_works_alone boolean,
    ADD CONSTRAINT stop_target_history_partner_alone_check
        CHECK (partner_works_alone IS NULL OR success_regimen = 'with_partner');
COMMENT ON COLUMN preclin.stop_target_history.success_regimen IS
    'For worked_here and worked_here_selected, how the other drug on the target succeeded in this disease (preclin.trial_regimen, written by pipeline.single_target regimens): alone when any of its met trials tested it as monotherapy or added to background care; with_partner when every success was a trial testing it in combination; unknown when the rest are combinations and at least one success is an FDA approval with no met Phase 2/3 trial in the database to read. Null for other fates.';
COMMENT ON COLUMN preclin.stop_target_history.partner_works_alone IS
    'For with_partner: true when every partner of those combinations works on its own in this disease (MONDO Lin >= 0.8): FDA-approved for it, or tested as monotherapy or added to background care in a Phase 2/3 trial that met its primary endpoint; false when some resolved partner does not; null when it cannot be told (a partner not resolved to an entity) or the success is not with_partner.';
COMMIT;
