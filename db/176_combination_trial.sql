-- Randomised trials of two pathways against one in each shortlisted disease of #197 (issue #196), read by how the
-- pathways relate: the trial half of the several-targets rule registered in #198 (pipeline.single_target
-- combination_beats_single).

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE preclin.combination_trial (
    mondo_id            text NOT NULL,
    trial_key           text NOT NULL,
    trial_name          text NOT NULL,
    nct_id              text CHECK (nct_id ~ '^NCT[0-9]{8}$'),
    pmid                text CHECK (pmid ~ '^[0-9]+$'),
    year                integer,
    phase               text NOT NULL,
    n_randomised        integer,
    two_pathway_arm     text NOT NULL,
    one_pathway_arm     text NOT NULL,
    comparator_pathways text[] NOT NULL CHECK (cardinality(comparator_pathways) > 0),
    added_pathway       text NOT NULL,
    design              text NOT NULL CHECK (design IN ('combination', 'add_on', 'head_to_head_multi_pathway')),
    relation            text NOT NULL CHECK (relation IN ('same_pathway', 'parallel', 'independent')),
    primary_endpoint    text NOT NULL,
    result              text NOT NULL CHECK (result IN ('met_primary', 'missed_primary')),
    effect_measure      text NOT NULL CHECK (effect_measure IN ('risk_difference', 'hazard_ratio', 'mean_difference', 'other')),
    effect              double precision,
    ci_low              double precision,
    ci_high             double precision,
    effect_text         text NOT NULL,
    limited_by          text NOT NULL CHECK (limited_by IN ('none', 'efficacy', 'safety')),
    stopped_for_safety  boolean NOT NULL,
    sources             text[] NOT NULL CHECK (cardinality(sources) > 0),
    quote               text NOT NULL,
    llm_decision_id     bigint NOT NULL REFERENCES pv_evidence.llm_decision,
    PRIMARY KEY (mondo_id, trial_key),
    CHECK (nct_id IS NOT NULL OR pmid IS NOT NULL),
    CHECK (trial_key = coalesce(nct_id, 'PMID:' || pmid))
);
COMMENT ON TABLE preclin.combination_trial IS
    'One row per randomised trial and shortlisted disease (pipeline.single_target SHORTLIST and EVENT_SHORTLIST) comparing an arm acting through two pathways with an arm acting through one of them (issue #196): a combination against monotherapy, a new pathway added to a fixed background against the background alone, or a multi-pathway drug head to head against a single-pathway one. Found and read by an LLM with web search and fetch (task combination_trial), seeded with known trials. Written by pipeline.single_target combos; a run replaces the table.';
COMMENT ON COLUMN preclin.combination_trial.mondo_id IS 'The shortlisted disease (MONDO id) the trial was run in.';
COMMENT ON COLUMN preclin.combination_trial.trial_key IS 'The trial within the disease: its NCT id, or PMID:n of its primary results paper when it has no NCT id.';
COMMENT ON COLUMN preclin.combination_trial.trial_name IS 'Acronym or first author and year, as the trial is known.';
COMMENT ON COLUMN preclin.combination_trial.nct_id IS 'ClinicalTrials.gov id, as shown on a retrieved page; null when none was found.';
COMMENT ON COLUMN preclin.combination_trial.pmid IS 'PubMed id of the primary results paper, as shown on a retrieved page; null when none was found.';
COMMENT ON COLUMN preclin.combination_trial.year IS 'Year the primary result was published.';
COMMENT ON COLUMN preclin.combination_trial.phase IS 'Trial phase as reported (2, 2b, 3, 4).';
COMMENT ON COLUMN preclin.combination_trial.n_randomised IS 'Patients randomised across all arms; null when not found.';
COMMENT ON COLUMN preclin.combination_trial.two_pathway_arm IS 'The arm acting through two pathways: drugs, doses where stated, and the background they were given on.';
COMMENT ON COLUMN preclin.combination_trial.one_pathway_arm IS 'The comparator arm acting through one of those pathways (for an add-on trial, the background with placebo).';
COMMENT ON COLUMN preclin.combination_trial.comparator_pathways IS 'Pathways of the one-pathway arm, named with the canonical names of preclin.mechanism_pathway wherever one fits. An add-on trial lists the background''s main pathways, which may be several.';
COMMENT ON COLUMN preclin.combination_trial.added_pathway IS 'The pathway the two-pathway arm adds to the comparator''s; for relation same_pathway, the shared pathway itself (it then appears in comparator_pathways).';
COMMENT ON COLUMN preclin.combination_trial.design IS 'combination: two drugs on different pathways together vs one alone; add_on: a drug on a new pathway added to a fixed background vs background alone; head_to_head_multi_pathway: one molecule or co-formulation spanning two pathways vs a drug on one of them.';
COMMENT ON COLUMN preclin.combination_trial.relation IS 'How the added pathway relates to the comparator''s. same_pathway: both arms act on one pathway (IL-17A vs IL-17A plus IL-17F; a second renin-angiotensin blocker); parallel: different pathways converging on the same disease process (IL-17 and TNF; GIP and GLP-1); independent: unrelated disease processes (an anti-inflammatory added to lipid lowering).';
COMMENT ON COLUMN preclin.combination_trial.primary_endpoint IS 'The trial''s primary efficacy endpoint and time point.';
COMMENT ON COLUMN preclin.combination_trial.result IS 'met_primary: the two-pathway arm was statistically superior to the one-pathway arm on the primary efficacy endpoint; missed_primary otherwise, including non-inferiority without superiority and a trial stopped before its primary was read.';
COMMENT ON COLUMN preclin.combination_trial.effect_measure IS 'Scale of effect: risk_difference (percentage points of patients responding, two-pathway minus one-pathway arm), hazard_ratio (two-pathway against one-pathway arm), mean_difference (a continuous primary, in its own units) or other.';
COMMENT ON COLUMN preclin.combination_trial.effect IS 'Primary endpoint estimate on effect_measure''s scale; null when not reported.';
COMMENT ON COLUMN preclin.combination_trial.ci_low IS 'Lower bound of the 95% confidence interval of effect; null when not reported.';
COMMENT ON COLUMN preclin.combination_trial.ci_high IS 'Upper bound of the 95% confidence interval of effect; null when not reported.';
COMMENT ON COLUMN preclin.combination_trial.effect_text IS 'The primary result in words, with endpoint, time point and arm values.';
COMMENT ON COLUMN preclin.combination_trial.limited_by IS 'What held the two-pathway arm back: none (it won and was safe enough to use), efficacy (no or too small a gain), safety (more harm, including a regimen that met its primary but was dropped for harm).';
COMMENT ON COLUMN preclin.combination_trial.stopped_for_safety IS 'True when the trial or its two-pathway arm was stopped early for harm, or the two-pathway regimen was abandoned or advised against because of harm seen in it.';
COMMENT ON COLUMN preclin.combination_trial.sources IS 'URLs the model retrieved (web search results or fetched pages) that show the trial''s design and result; the task rejects a source it did not retrieve.';
COMMENT ON COLUMN preclin.combination_trial.quote IS 'Sentence from a source stating the primary result.';
COMMENT ON COLUMN preclin.combination_trial.llm_decision_id IS 'The decision (task combination_trial, one per disease) the row was read from.';
COMMIT;
