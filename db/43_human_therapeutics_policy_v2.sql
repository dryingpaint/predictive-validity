-- A verified molecular asset takes precedence over a coarse whole-trial LLM
-- label (for example, a nicotine-patch plus counseling trial).  Vaccines remain
-- a separate track and records without a verified asset remain non-molecular.

BEGIN;

INSERT INTO pv_core.development_scope_policy(policy_version,definition)
VALUES (
  'human_therapeutics_v2',
  jsonb_build_object(
    'supersedes', 'human_therapeutics_v1',
    'raw_ingestion', 'retain_all_selected_trials_and_source_records',
    'main_track', 'verified therapeutic assets acting on human targets or verified human biological mechanisms',
    'mixed_trial_rule', 'a verified in-scope molecular asset overrides a coarse behavioral/device/diagnostic/exercise trial label',
    'excluded', jsonb_build_array(
      'antibiotics',
      'therapeutic-primary bacterial targets',
      'therapeutic-primary viral targets',
      'therapeutic-primary fungal targets',
      'therapeutic-primary parasitic targets'
    ),
    'separate_track', 'vaccines',
    'non_molecular', 'retained without molecular literature expansion when no verified molecular asset exists',
    'unknown', 'no literature expansion until resolved'
  )
);

COMMIT;
