-- Why each Phase 2/3 program stopped, where the registry does not say or says wrongly
-- (pipeline.stop_causes). analysis_method records each method as run: what it does, its
-- inputs, parameters and code commit, so every inferred cause points at the procedure behind it.
-- stop_signal holds structured facts per stopped program; stop_cause holds the final cause of
-- every stop Section 1 counts in Phases 2 and 3, from the registry, a correction, or inference.
-- Keyed by entity, disease and phase so rows survive a programs rebuild.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE IF NOT EXISTS preclin.analysis_method (
    method_id    text PRIMARY KEY,
    name         text NOT NULL,
    version      text NOT NULL,
    description  text NOT NULL,
    inputs       text[] NOT NULL,
    parameters   jsonb NOT NULL,
    code_commit  text,
    recorded_at  timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE preclin.analysis_method IS
    'Methodology of each derived analysis as run: a stable id, a prose description of the procedure, the tables and sources it reads, its parameters and the code commit.';
COMMENT ON COLUMN preclin.analysis_method.method_id IS 'name@version, referenced by rows the method produced.';
COMMENT ON COLUMN preclin.analysis_method.description IS 'The procedure in prose: cohort, inputs, decision rules, validation.';

CREATE TABLE IF NOT EXISTS preclin.stop_signal (
    moiety_id                integer NOT NULL REFERENCES preclin.moiety,
    mondo_id                 text NOT NULL,
    phase                    integer NOT NULL,
    stopped_on               date,
    drug_continued_elsewhere boolean NOT NULL,
    drug_approved_anywhere   boolean NOT NULL,
    sponsor_active_after     boolean,
    target_peers_stopped     integer NOT NULL,
    trials_terminated        integer NOT NULL,
    trials_completed         integer NOT NULL,
    has_results              boolean NOT NULL,
    has_publication          boolean NOT NULL,
    method_id                text NOT NULL REFERENCES preclin.analysis_method,
    PRIMARY KEY (moiety_id, mondo_id, phase)
);
COMMENT ON TABLE preclin.stop_signal IS
    'Structured facts about each stopped Phase 2/3 program that bear on why it stopped, computed from the registry and program tables.';
COMMENT ON COLUMN preclin.stop_signal.stopped_on IS 'End of the last trial of the program (completion, else primary completion, else start).';
COMMENT ON COLUMN preclin.stop_signal.drug_continued_elsewhere IS 'Another program of the entity had a trial start or active trial after this program stopped.';
COMMENT ON COLUMN preclin.stop_signal.drug_approved_anywhere IS 'The entity is FDA-approved for any disease.';
COMMENT ON COLUMN preclin.stop_signal.sponsor_active_after IS 'A lead sponsor of the program started any trial more than 12 months after it stopped; null when the sponsor is unknown.';
COMMENT ON COLUMN preclin.stop_signal.target_peers_stopped IS 'Other entities on a shared primary target whose programs in a related disease stopped within 18 months of this one.';

CREATE TABLE IF NOT EXISTS preclin.stop_cause (
    moiety_id        integer NOT NULL REFERENCES preclin.moiety,
    mondo_id         text NOT NULL,
    phase            integer NOT NULL,
    recorded_reason  text NOT NULL,
    cause            text NOT NULL,
    cause_source     text NOT NULL CHECK (cause_source IN ('registry', 'corrected', 'inferred')),
    evidence_kind    text,
    confidence       text,
    sources          text[] NOT NULL DEFAULT '{}',
    llm_decision_id  bigint REFERENCES pv_evidence.llm_decision,
    method_id        text NOT NULL REFERENCES preclin.analysis_method,
    PRIMARY KEY (moiety_id, mondo_id, phase)
);
COMMENT ON TABLE preclin.stop_cause IS
    'Final cause of every Phase 2/3 stop that Section 1 counts: the registry reason where one is stated and stands, a correction where the efficacy attribution found it wrong, or a cause inferred from registry records, structured signals and web sources where none is stated.';
COMMENT ON COLUMN preclin.stop_cause.recorded_reason IS 'The reason Section 1 assigns from the registry (report.section1.failure_modes).';
COMMENT ON COLUMN preclin.stop_cause.cause IS 'efficacy, safety, pk_formulation, business_strategic, company_event, operational, positive_not_advanced, development_continued or unknown.';
COMMENT ON COLUMN preclin.stop_cause.cause_source IS 'registry: stated reason kept; corrected: stated reason replaced after reading the sources; inferred: no stated reason, cause inferred.';
COMMENT ON COLUMN preclin.stop_cause.evidence_kind IS 'explicit_program, explicit_drug, results, context or none: how directly the sources support the cause.';
COMMENT ON COLUMN preclin.stop_cause.sources IS 'NCT ids, PMID:n or URLs the decision cites; every URL was retrieved during the decision.';
COMMIT;
