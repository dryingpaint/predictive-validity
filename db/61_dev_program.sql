-- Development programs: one row per (molecular entity, MONDO disease), built
-- by pipeline.programs build from every in-scope ClinicalTrials.gov trial in
-- which the entity is investigational. mondo_id is NULL for entities whose
-- only trials have no disease (healthy-volunteer and methodology studies).
-- Each build replaces the rows; build_id identifies the run.

BEGIN;

CREATE TABLE IF NOT EXISTS preclin.dev_program_build (
    build_id    uuid PRIMARY KEY,
    built_at    timestamptz NOT NULL DEFAULT now(),
    code_commit text,
    snapshot    date NOT NULL,
    parameters  jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS preclin.dev_program (
    program_id          serial PRIMARY KEY,
    moiety_id           integer NOT NULL REFERENCES preclin.moiety,
    mondo_id            text,
    ph1_start           date,
    ph2_start           date,
    ph3_start           date,
    first_start         date NOT NULL,
    highest_phase       integer NOT NULL CHECK (highest_phase BETWEEN 1 AND 3),
    n_trials            integer NOT NULL,
    n_industry_trials   integer NOT NULL,
    first_industry_start date,
    lead_sponsors       text[] NOT NULL,
    last_activity       date NOT NULL,
    n_active_trials     integer NOT NULL,
    build_id            uuid NOT NULL REFERENCES preclin.dev_program_build,
    UNIQUE NULLS NOT DISTINCT (moiety_id, mondo_id)
);
CREATE INDEX IF NOT EXISTS dev_program_mondo_idx ON preclin.dev_program (mondo_id);

-- How each trial attaches to a program: its own disease, a broader condition
-- (e.g. "solid tumors") rolled into the more specific programs of the same
-- entity, or no disease (healthy volunteers) rolled into every program.
CREATE TABLE IF NOT EXISTS preclin.dev_program_trial (
    program_id integer NOT NULL REFERENCES preclin.dev_program ON DELETE CASCADE,
    nct_id     text NOT NULL REFERENCES preclin.ctgov_study,
    phase      integer NOT NULL CHECK (phase BETWEEN 1 AND 3),
    attach     text NOT NULL CHECK (attach IN ('disease', 'broader_condition', 'no_disease')),
    PRIMARY KEY (program_id, nct_id)
);
CREATE INDEX IF NOT EXISTS dev_program_trial_nct_idx ON preclin.dev_program_trial (nct_id);

COMMIT;
