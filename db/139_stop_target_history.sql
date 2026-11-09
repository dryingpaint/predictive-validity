-- Why an efficacy stop failed when the drug engaged its target (pipeline.target_history): what other drugs on the
-- same target went on to do, and for the stops that history leaves open, a reading of the sources. Keyed by entity,
-- disease and phase like preclin.stop, so rows survive a programs rebuild.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE IF NOT EXISTS preclin.stop_target_history (
    moiety_id               integer NOT NULL REFERENCES preclin.moiety,
    mondo_id                text NOT NULL,
    phase                   integer NOT NULL,
    target_fate             text NOT NULL CHECK (target_fate IN (
                                'worked_here', 'worked_here_selected', 'worked_related', 'worked_elsewhere_only',
                                'never_worked_tried_again', 'never_worked_single', 'no_target')),
    success_first           boolean,
    drug_approved_elsewhere boolean NOT NULL,
    partners                integer NOT NULL,
    partners_failed         integer NOT NULL,
    method_id               text NOT NULL REFERENCES preclin.analysis_method,
    verdict                 text CHECK (verdict IN ('target_not_causal', 'wrong_stage_or_timing', 'wrong_patients',
                                                    'drug_inadequate', 'trial_inadequate', 'unclear')),
    verdict_evidence        text CHECK (verdict_evidence IN ('explicit', 'results', 'context', 'none')),
    verdict_basis           text,
    quote                   text,
    sources                 text[] NOT NULL DEFAULT '{}',
    llm_decision_id         bigint REFERENCES pv_evidence.llm_decision,
    label_method_id         text REFERENCES preclin.analysis_method,
    PRIMARY KEY (moiety_id, mondo_id, phase),
    CHECK ((verdict IS NULL) = (llm_decision_id IS NULL))
);
COMMENT ON TABLE preclin.stop_target_history IS
    'Every Phase 2/3 efficacy stop in preclin.stop where the drug engaged its target without benefit: what other drugs on the same primary target, acting in a compatible direction, did in the same, related and other diseases, and for the stops that history leaves open a verdict read from the sources.';
COMMENT ON COLUMN preclin.stop_target_history.target_fate IS
    'worked_here: another drug on the target was approved or met a Phase 2/3 primary endpoint in this disease (MONDO Lin >= 0.8); worked_here_selected: it did so only in biomarker-selected trials and this program was not selected; worked_related: only in a related disease (Lin >= 0.5); worked_elsewhere_only: only in unrelated diseases; never_worked_tried_again: never anywhere, and another drug on the target also failed in a related disease; never_worked_single: never anywhere, and no other drug on it failed in a related disease; no_target: the entity has no resolved human primary target.';
COMMENT ON COLUMN preclin.stop_target_history.success_first IS 'For worked_here and worked_here_selected: another drug''s success in this disease came before this program''s last trial ended. Null otherwise.';
COMMENT ON COLUMN preclin.stop_target_history.drug_approved_elsewhere IS 'The entity itself is FDA-approved for some disease.';
COMMENT ON COLUMN preclin.stop_target_history.partners IS 'Other entities sharing a primary target, acting in a compatible direction.';
COMMENT ON COLUMN preclin.stop_target_history.partners_failed IS 'Of those, entities with a missed Phase 2/3 primary endpoint, futility stop or efficacy stop in a related disease.';
COMMENT ON COLUMN preclin.stop_target_history.verdict IS
    'Set for the stops target history leaves open (worked_here, worked_here_selected, never_worked_single; phase entry 2008-2019): target_not_causal (the target or pathway moved, the disease did not), wrong_stage_or_timing, wrong_patients, drug_inadequate (the drug was worse than the drugs that worked: tissue exposure, potency, duration), trial_inadequate (comparator, endpoint, size or duration could not show a benefit), unclear.';
COMMENT ON COLUMN preclin.stop_target_history.verdict_evidence IS 'explicit (a source states it), results (posted or published results show it), context (inferred from circumstances), none (unclear).';
COMMENT ON COLUMN preclin.stop_target_history.sources IS 'NCT ids, PMID:n or URLs the decision cites; every URL was retrieved during the decision.';
COMMIT;
