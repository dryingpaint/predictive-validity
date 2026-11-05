BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.stop DROP CONSTRAINT stop_cause_check;
ALTER TABLE preclin.stop ADD CONSTRAINT stop_cause_check
    CHECK (cause IN ('efficacy', 'safety', 'sponsor_decision', 'operational', 'positive_not_advanced', 'unknown',
                     'not_stopped', 'not_a_program'));
COMMENT ON COLUMN preclin.stop.cause IS 'efficacy (including exposure, PK, dose or formulation), safety, sponsor_decision, operational, positive_not_advanced, unknown (no source states it), not_stopped (development continued under another registry, region, name or combination, or the drug was approved in the disease), or not_a_program (no one was developing the drug for the disease: an academic or investigator study using it as a research tool, or a drug-interaction or dosing study of an approved drug).';
COMMIT;
