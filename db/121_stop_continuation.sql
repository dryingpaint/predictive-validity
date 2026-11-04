-- What happened after each stop the tracing found had not stopped (pipeline.stop_causes continued), so Section 1
-- can count it as advanced or still running instead of suspended.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.stop_continuation (
    moiety_id    integer NOT NULL REFERENCES preclin.moiety,
    mondo_id     text NOT NULL,
    phase        integer NOT NULL,
    outcome      text NOT NULL CHECK (outcome IN ('fda_approved', 'later_phase', 'active', 'no_evidence')),
    phase_reached integer CHECK (phase_reached IN (2, 3)),
    on_date      date,
    outside_us   boolean,
    explanation  text,
    sources      text[] NOT NULL DEFAULT '{}',
    decision_id  bigint NOT NULL,
    method_id    text NOT NULL REFERENCES preclin.analysis_method,
    PRIMARY KEY (moiety_id, mondo_id, phase),
    CHECK ((outcome = 'later_phase') = (phase_reached IS NOT NULL)),
    CHECK (outcome = 'no_evidence' OR on_date IS NOT NULL)
);
COMMENT ON TABLE preclin.stop_continuation IS
    'For every preclin.stop row whose cause is not_stopped, what the program did after Section 1 recorded it as suspended, found by an LLM with web search: FDA approval for the disease, a later-phase trial started, development still active in the same phase, or no evidence it went on.';
COMMENT ON COLUMN preclin.stop_continuation.outcome IS
    'fda_approved: the FDA approved the drug for the disease, a subtype or a class containing it; later_phase: a trial of a later phase started in the disease, anywhere; active: development in the disease went on in the same phase (a trial, a licensing deal, a regulatory filing); no_evidence: the sources do not show it went on.';
COMMENT ON COLUMN preclin.stop_continuation.phase_reached IS
    'For later_phase, the highest phase whose trial started; null otherwise.';
COMMENT ON COLUMN preclin.stop_continuation.on_date IS
    'fda_approved: the approval date; later_phase: the start of the first later-phase trial; active: the latest dated sign of development. Day 1 where a source gives only the month, January 1 where it gives only the year.';
COMMENT ON COLUMN preclin.stop_continuation.outside_us IS
    'For later_phase and active, whether the development the sources show ran only outside the United States.';
COMMENT ON COLUMN preclin.stop_continuation.decision_id IS
    'The pv_evidence.llm_decision row (task stop_continuation) the outcome comes from.';

COMMIT;
