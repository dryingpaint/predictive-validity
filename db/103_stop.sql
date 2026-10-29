BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE IF NOT EXISTS preclin.stop (
    moiety_id        integer NOT NULL REFERENCES preclin.moiety,
    mondo_id         text NOT NULL,
    phase            integer NOT NULL,
    registry_reason  text NOT NULL,
    cause            text NOT NULL CHECK (cause IN ('efficacy', 'safety', 'sponsor_decision', 'operational',
                                                   'positive_not_advanced', 'unknown', 'not_stopped')),
    subcause         text,
    detail           text,
    guess            text CHECK (guess IN ('efficacy', 'safety', 'sponsor_decision', 'operational',
                                           'positive_not_advanced', 'not_stopped')),
    explanation      text,
    sources          text[] NOT NULL DEFAULT '{}',
    decision_ids     bigint[] NOT NULL DEFAULT '{}',
    method_id        text NOT NULL REFERENCES preclin.analysis_method,
    PRIMARY KEY (moiety_id, mondo_id, phase),
    CHECK (guess IS NULL OR cause = 'unknown')
);
COMMENT ON TABLE preclin.stop IS
    'Every program Section 1 records as stopped, keyed by (entity, disease, phase), with why it stopped: the registry reason where it stands, otherwise the cause traced from web sources, and for efficacy stops why efficacy failed.';
COMMENT ON COLUMN preclin.stop.registry_reason IS 'The reason Section 1 assigns from ClinicalTrials.gov (report.section1.failure_modes).';
COMMENT ON COLUMN preclin.stop.cause IS 'efficacy (including exposure, PK, dose or formulation), safety, sponsor_decision, operational, positive_not_advanced, unknown (no source states it), or not_stopped (development continued under another registry, region, name or combination).';
COMMENT ON COLUMN preclin.stop.subcause IS 'Efficacy: not_engaged, engaged_no_benefit, trial_design, toxicity_offset, no_engagement_data or not_attributed. Safety: off_target_toxicity. Sponsor decision: company_event. Unknown: what the drug and sponsor did next (sponsor_went_quiet, drug_approved_elsewhere, drug_continued_elsewhere, drug_dropped). Null where none applies.';
COMMENT ON COLUMN preclin.stop.detail IS 'Efficacy only: exposure_or_engagement_too_low, dose_capped, other_drug_on_target_worked, wrong_population, wrong_endpoint_or_timing or trial_could_not_answer.';
COMMENT ON COLUMN preclin.stop.guess IS 'Where cause is unknown, the model''s best guess at it from context and signals; null otherwise.';
COMMENT ON COLUMN preclin.stop.explanation IS 'What the row rests on: the quoted source, or the model''s reasoning for the efficacy breakdown or the guess.';
COMMENT ON COLUMN preclin.stop.sources IS 'NCT ids, PMID:n or URLs the decisions cite; every URL was retrieved during its decision.';
COMMENT ON COLUMN preclin.stop.decision_ids IS 'The pv_evidence.llm_decision rows the cause and the efficacy breakdown come from.';
COMMIT;
