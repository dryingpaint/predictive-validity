-- Published estimates behind the two labels registered in #198 (issue #195): each confirmed disease's responder
-- shares or event hazard ratios per drug and regimen, the crossover estimates behind the retained effect, and the
-- risk factor -> outcome read-across. The labels themselves are computed in report.single_target, not stored.

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE preclin.mechanism_response (
    response_id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mondo_id             text NOT NULL,
    question             text NOT NULL CHECK (question IN ('response', 'crossover', 'events', 'pair')),
    risk_factor_mondo_id text,
    regimen              text NOT NULL,
    drugs                text[] NOT NULL CHECK (cardinality(drugs) > 0),
    pathways             text[] NOT NULL CHECK (cardinality(pathways) > 0),
    mechanism_keys       text[] NOT NULL,
    one_drug             boolean NOT NULL,
    endpoint             text NOT NULL,
    measure              text NOT NULL CHECK (measure IN ('share', 'hazard_ratio', 'odds_ratio')),
    population           text NOT NULL CHECK (population IN ('naive', 'prior_failure', 'on_background',
                                                             'lifelong_genetic')),
    failed_pathway       text,
    background_pathways  text[] NOT NULL,
    stack_position       integer CHECK (stack_position >= 1),
    pair_key             text,
    estimate             double precision NOT NULL,
    ci_low               double precision,
    ci_high              double precision,
    trial_weeks          double precision CHECK (trial_weeks > 0),
    per_unit             text,
    source_kind          text NOT NULL CHECK (source_kind IN ('nma', 'pooled_trials', 'trial',
                                                              'mendelian_randomisation')),
    source_name          text NOT NULL,
    pmid                 text CHECK (pmid ~ '^[0-9]+$'),
    sources              text[] NOT NULL CHECK (cardinality(sources) > 0),
    quote                text NOT NULL,
    derivation           text NOT NULL,
    llm_decision_id      bigint NOT NULL REFERENCES pv_evidence.llm_decision,
    CHECK ((population = 'prior_failure') = (failed_pathway IS NOT NULL)),
    CHECK ((question = 'pair') = (risk_factor_mondo_id IS NOT NULL)),
    CHECK ((measure = 'share') = (question IN ('response', 'crossover'))),
    CHECK (measure = 'share' OR estimate > 0),
    CHECK (ci_low IS NULL OR ci_high IS NULL OR ci_low <= ci_high)
);
CREATE INDEX ON preclin.mechanism_response (mondo_id, question);
COMMENT ON TABLE preclin.mechanism_response IS
    'One row per published estimate behind the labels of issue #198, for the diseases #193 confirmed (pipeline.single_target CONFIRMED and EVENTS_CONFIRMED): placebo-adjusted responder shares in patients naive to advanced therapy (question response), the same in patients who failed an earlier pathway beside the naive estimate it is divided by (crossover), event hazard ratios of single drugs and of each pathway added to the background of those before it (events), and for each risk factor -> outcome pair the outcome-event effect of the drug that best solves the risk factor and any Mendelian randomisation estimate (pair). Found and read by an LLM with web search and fetch (task mechanism_response, one decision per disease and question, or per pair). Written by pipeline.single_target responses; a run replaces the table.';
COMMENT ON COLUMN preclin.mechanism_response.response_id IS 'Row id; not stable across runs.';
COMMENT ON COLUMN preclin.mechanism_response.mondo_id IS 'The disease the estimate is read in (MONDO id); for a pair row, the outcome disease.';
COMMENT ON COLUMN preclin.mechanism_response.question IS 'Which decision the row came from: response (single drugs and multi-drug regimens in advanced-therapy-naive patients, responder diseases), crossover (prior-failure and matching naive estimates, responder diseases), events (hazard ratios, event diseases), pair (risk factor -> outcome read-across).';
COMMENT ON COLUMN preclin.mechanism_response.risk_factor_mondo_id IS 'For a pair row, the risk-factor disease whose solving drug is read across to mondo_id''s events; null otherwise.';
COMMENT ON COLUMN preclin.mechanism_response.regimen IS 'The drug, drug class or regimen the estimate is for, as the source names it (a class where a network meta-analysis pools one).';
COMMENT ON COLUMN preclin.mechanism_response.drugs IS 'Generic names of the active drugs in the regimen (every member for a pooled class), lower case.';
COMMENT ON COLUMN preclin.mechanism_response.pathways IS 'Pathways the regimen acts through, named with the canonical names of preclin.mechanism_pathway.';
COMMENT ON COLUMN preclin.mechanism_response.mechanism_keys IS 'preclin.mechanism_pathway.mechanism_key of each drug that resolves to an entity (preclin.moiety name or alias) with a mechanism (preclin.atlas_member or pipeline.single_target.mechanism_keys); empty when none resolves.';
COMMENT ON COLUMN preclin.mechanism_response.one_drug IS 'True when the regimen is one molecule acting through at most 3 pathways (a bispecific or multi-receptor agonist counts; a pooled class of such molecules counts); false for a regimen of two or more separate drugs, including a co-formulation. Conventional background care every arm gets does not count as a drug.';
COMMENT ON COLUMN preclin.mechanism_response.endpoint IS 'The endpoint and time point as the source reports it: the registered endpoint of pipeline.single_target SHORTLIST or EVENT_SHORTLIST where available; a crossover pair may use another responder endpoint, the same for both of its rows.';
COMMENT ON COLUMN preclin.mechanism_response.measure IS 'share: placebo-adjusted percentage points of patients reaching the endpoint (active minus placebo); hazard_ratio: against placebo or against background alone; odds_ratio: a Mendelian randomisation estimate per per_unit.';
COMMENT ON COLUMN preclin.mechanism_response.population IS 'naive: advanced-therapy-naive patients, or for an event estimate against placebo with no background on a specific pathway named in background_pathways; prior_failure: patients who failed failed_pathway; on_background: the regimen added to background_pathways against that background alone; lifelong_genetic: a Mendelian randomisation estimate.';
COMMENT ON COLUMN preclin.mechanism_response.failed_pathway IS 'For a prior_failure row, the pathway the patients had failed (canonical name; TNF for TNF-inadequate responders); null otherwise.';
COMMENT ON COLUMN preclin.mechanism_response.background_pathways IS 'Specific pathways every arm was already receiving (canonical names); empty when none.';
COMMENT ON COLUMN preclin.mechanism_response.stack_position IS 'For an events row, its place in the disease''s best stack: position 1 is a pathway against placebo, position k a pathway added to the background of positions 1..k-1; the stack''s risk reduction is 1 minus the product of their hazard ratios (pipeline.single_target.stacked_rrr). Null when the row is not in the stack.';
COMMENT ON COLUMN preclin.mechanism_response.pair_key IS 'For a crossover row, the comparison it belongs to: one prior_failure row and the naive row it is divided by share it; null otherwise.';
COMMENT ON COLUMN preclin.mechanism_response.estimate IS 'The estimate on measure''s scale: percentage points for share (may be negative), a ratio for hazard_ratio and odds_ratio.';
COMMENT ON COLUMN preclin.mechanism_response.ci_low IS 'Lower bound of the 95% confidence or credible interval; null when not reported.';
COMMENT ON COLUMN preclin.mechanism_response.ci_high IS 'Upper bound of the 95% confidence or credible interval; null when not reported.';
COMMENT ON COLUMN preclin.mechanism_response.trial_weeks IS 'For a share, the week the endpoint was assessed; for a hazard ratio, the trial''s median follow-up in weeks; null for a Mendelian randomisation estimate or when not reported.';
COMMENT ON COLUMN preclin.mechanism_response.per_unit IS 'For an odds_ratio or a pair hazard ratio, the risk-factor change it is scaled to or that the trial achieved (e.g. per 1 mmol/L lower LDL cholesterol); null otherwise.';
COMMENT ON COLUMN preclin.mechanism_response.source_kind IS 'nma: network meta-analysis; pooled_trials: pooled placebo-controlled Phase 3 trials; trial: one randomised trial; mendelian_randomisation.';
COMMENT ON COLUMN preclin.mechanism_response.source_name IS 'The source as cited: first author, year and trial or review name.';
COMMENT ON COLUMN preclin.mechanism_response.pmid IS 'PubMed id of the source, as shown on a retrieved page; null when none was found.';
COMMENT ON COLUMN preclin.mechanism_response.sources IS 'URLs the model retrieved (web search results or fetched pages) that show the estimate; the task rejects a source it did not retrieve.';
COMMENT ON COLUMN preclin.mechanism_response.quote IS 'Text from a source stating the numbers the estimate comes from.';
COMMENT ON COLUMN preclin.mechanism_response.derivation IS 'How estimate was obtained from the quoted numbers (e.g. 71.2% minus 2.4% on placebo; a risk ratio applied to the pooled placebo share).';
COMMENT ON COLUMN preclin.mechanism_response.llm_decision_id IS 'The decision (task mechanism_response) the row was read from.';
COMMIT;
