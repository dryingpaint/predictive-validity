-- Atlas cells hold one track per model system; the cell headline is computed from the tracks, so no
-- entry marks a hand-over between models.
ALTER TABLE preclin.atlas_track_entry DROP COLUMN model_change;

COMMENT ON TABLE preclin.atlas_track_entry IS
    'A tracked tile''s model track records (drafter brief v3, RULES_V3_PROPOSAL.md): one row per entry, a dated status of one model system (model_id) for one question. A cell''s tracks are its entries grouped by model_id, and by modality where a multi-modality tile splits dose and safety. Stored by drafts/track_store.py from a draft that passes drafts/lint.py; a store replaces the tile.';
COMMENT ON COLUMN preclin.atlas_track_entry.seq IS 'Position in the draft''s list for the question and modality, from 1; it orders entries within a track by year.';
COMMENT ON COLUMN preclin.atlas_track_entry.model_id IS 'Slug of the model system within the tile; a cell''s track is its entries with one model_id.';
