BEGIN;
SET LOCAL lock_timeout = '3s';
COMMENT ON COLUMN preclin.stop.subcause IS
    'Efficacy: not_engaged, engaged_no_benefit, trial_design, toxicity_offset, no_engagement_data or not_attributed (from the efficacy label). Safety, sponsor_decision, operational and positive_not_advanced: one of pipeline.stops.SUBCAUSES for the cause, named from the explanation (stop_description), off_target_toxicity where the efficacy label settles a stop as safety, not_stated where the explanation says no more. Unknown: what the drug and sponsor did next (sponsor_went_quiet, drug_approved_elsewhere, drug_continued_elsewhere, drug_dropped). Null for not_stopped.';
COMMENT ON COLUMN preclin.stop.explanation IS
    'What the row rests on: the efficacy label''s rationale, else the traced source quote or the model''s reasoning for its guess, else the stated reason (or read result) of the trial that gave Section 1 its reason; reworded without failure codes where it used them (stop_description).';
COMMIT;
