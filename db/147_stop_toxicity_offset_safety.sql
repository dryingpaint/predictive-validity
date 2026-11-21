BEGIN;
SET LOCAL lock_timeout = '3s';
COMMENT ON COLUMN preclin.stop.subcause IS
    'Efficacy: not_engaged, engaged_no_benefit, trial_design, no_engagement_data or not_attributed (from the efficacy label). Safety, sponsor_decision, operational and positive_not_advanced: one of pipeline.stops.SUBCAUSES for the cause, named from the explanation (stop_description); where the efficacy label settles a stop as safety, on_target_toxicity for on-target toxicity that offset the benefit (F5) and off_target_toxicity for off-target toxicity (F6); not_stated where the explanation says no more. Unknown: what the drug and sponsor did next (sponsor_went_quiet, drug_approved_elsewhere, drug_continued_elsewhere, drug_dropped). Null for not_stopped.';
COMMIT;
