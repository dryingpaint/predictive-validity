-- Point the atlas comments from 133 and 135 at the briefs in analyses/model-system-atlas/drafts/
-- (DRAFTER_BRIEF.md, CHECKER_BRIEF.md) and state each rule in place of a decision number.

BEGIN;
SET LOCAL lock_timeout = '3s';

COMMENT ON COLUMN preclin.atlas_build.min_programs IS 'Distinct entities a mechanism needs in an indication to be tracked.';
COMMENT ON TABLE preclin.atlas_mechanism IS
    'Mechanisms of the atlas: a verified (target, action), across modalities. A non-selective entity carries its own target label, so it forms its own mechanism.';
COMMENT ON VIEW preclin.atlas_register IS
    'Every mechanism of every named indication, counted across modalities. tracked: at least atlas_build.min_programs distinct entities, so the tile''s model track record is drafted. Phase never decides tracking.';

COMMENT ON TABLE preclin.atlas_track_entry IS
    'A tracked tile''s model track records (analyses/model-system-atlas/drafts/DRAFTER_BRIEF.md): one row per entry, a dated status of one model system (model_id) for one question. A cell''s tracks are its entries grouped by model_id, and by modality where a multi-modality tile splits dose and safety. Stored by drafts/track_store.py from a draft that passes drafts/lint.py; a store replaces the tile.';
COMMENT ON COLUMN preclin.atlas_track_entry.modality IS 'The modality sub-strip for a dose or platform-safety entry of a multi-modality tile; empty for a pooled entry.';
COMMENT ON COLUMN preclin.atlas_track_entry.year IS 'Earliest year the comparison was public: registry results, epub, label or print. A checker''s corrected year (atlas_track_verdict.proposed_year) replaces it when the entry''s status stands.';
COMMENT ON COLUMN preclin.atlas_track_entry.status IS
    'untested (model used, never compared), same (matched), neg (matched, incl. a known failure), other (safety: matched on another molecule of the platform), contra (contradicted), retro (a retrodiction that reproduced the known result).';
COMMENT ON COLUMN preclin.atlas_track_entry.retrodiction IS 'The comparison came after the patient result was known. A retrodiction is shown on its track but never sets the cell''s headline.';
COMMENT ON COLUMN preclin.atlas_track_entry.model_id IS 'Slug of the model system within the tile; a cell''s track is its entries with one model_id.';
COMMENT ON COLUMN preclin.atlas_track_entry.source_tier IS '1 paper, 2 regulator document, 3 registry results, 4 meta-analysis, 5 press release or SEC filing (4-5 patient side only).';
COMMENT ON COLUMN preclin.atlas_track_entry.patient_signal_reversed IS 'The early patient signal attenuated, so the model was right after a contradicted entry on the same track.';
COMMENT ON COLUMN preclin.atlas_track_entry.fields IS 'The entry''s other draft fields (note, judgement, magnitude, dates, readout_tier, derived_from, blocked_by, margin_stated, effect_size, class_threshold, outcome_tested, patient_trials, ...).';
COMMENT ON COLUMN preclin.atlas_track_entry.drafted_by IS 'Who drafted the entry: the agent brief and run, e.g. "DRAFTER_BRIEF / atlas-2026-11-05".';

COMMENT ON TABLE preclin.atlas_track_verdict IS
    'The checker''s verdict on each track-record entry (analyses/model-system-atlas/drafts/CHECKER_BRIEF.md) and, for a corrected one, the adjudicator''s decision. The entry''s final status is adjudicated_status when set, else status.';
COMMENT ON COLUMN preclin.atlas_track_verdict.rule IS 'The rule of DRAFTER_BRIEF.md a correction rests on, as the checker named it.';

COMMIT;
