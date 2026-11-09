-- Atlas track records in typed columns. A track is one model system used for one member drug by one route
-- (preclin.atlas_track); each entry points to its track and carries its scored attributes as columns with
-- their allowed values, replacing the free-form fields column. The tiles are re-stored from the drafts by
-- drafts/track_store.py right after this migration, so the old rows are cleared here.

BEGIN;
SET LOCAL lock_timeout = '3s';

DELETE FROM preclin.atlas_track_verdict;
DELETE FROM preclin.atlas_track_entry;

CREATE TABLE preclin.atlas_track (
    mondo_id             text    NOT NULL,
    mechanism_key        text    NOT NULL,
    track_id             text    NOT NULL,
    model_id             text    NOT NULL,
    model                text    NOT NULL,
    model_kind           text    NOT NULL CHECK (model_kind IN ('animal', 'human_challenge', 'ex_vivo', 'in_silico',
                                                                'human_genetic', 'cross_indication')),
    prediction_level     text    NOT NULL CHECK (prediction_level IN ('class', 'patient')),
    model_first_use_year integer,
    drug                 text    NOT NULL,
    moiety_id            integer REFERENCES preclin.moiety (moiety_id),
    route                text    NOT NULL CHECK (route IN ('oral', 'iv', 'sc', 'im', 'inhaled', 'intranasal', 'topical',
                                                           'ocular_topical', 'intravitreal', 'subretinal', 'suprachoroidal',
                                                           'intrathecal', 'intracerebral', 'intra_articular', 'intradermal',
                                                           'sublingual', 'transdermal', 'ex_vivo_cells', 'not_applicable',
                                                           'mixed')),
    PRIMARY KEY (mondo_id, mechanism_key, track_id),
    UNIQUE (mondo_id, mechanism_key, model_id, drug, route),
    CHECK ((drug = 'class') = (moiety_id IS NULL))
);

ALTER TABLE preclin.atlas_track_entry
    DROP COLUMN fields,
    DROP COLUMN model_id,
    DROP COLUMN model,
    ADD COLUMN track_id          text NOT NULL,
    ADD COLUMN population        text,
    ADD COLUMN population_group  text NOT NULL CHECK (population_group IN ('unselected', 'biomarker_selected',
                                                                           'stage_or_line', 'other_disease')),
    ADD COLUMN combination_with  text,
    ADD COLUMN imported_from     text,
    ADD COLUMN subjects          text CHECK (subjects IN ('patients', 'healthy_volunteers', 'mixed')),
    ADD COLUMN untested_reason   text CHECK (untested_reason IN ('no_prediction', 'not_measured', 'unpublished', 'unsettled')),
    ADD COLUMN magnitude         text CHECK (magnitude IN ('within_2x', 'off_by_2-5x', 'off_by_>5x', 'direction_only',
                                                           'null', 'opposite')),
    ADD COLUMN magnitude_basis   text,
    ADD COLUMN source_calls_it   text CHECK (source_calls_it IN ('match', 'miss', 'scaling', 'partial', 'unresolved',
                                                                 'over_predicted')),
    ADD COLUMN readout_tier      text CHECK (readout_tier IN ('direct', 'proximal', 'downstream')),
    ADD COLUMN endpoint_role     text CHECK (endpoint_role IN ('primary', 'poc_gate')),
    ADD COLUMN outcome_tested    text CHECK (outcome_tested IN ('positive', 'negative', 'negative_confounded')),
    ADD COLUMN blocked_by        text CHECK (blocked_by IN ('toxicity')),
    ADD COLUMN margin_stated     boolean,
    ADD COLUMN product_in_model  boolean,
    ADD COLUMN model_filed       boolean,
    ADD COLUMN trial_unreported  boolean NOT NULL,
    ADD COLUMN strengthens       boolean,
    ADD COLUMN effect_size       text,
    ADD COLUMN class_threshold   text,
    ADD COLUMN model_src         text,
    ADD COLUMN model_src_tier    smallint CHECK (model_src_tier BETWEEN 1 AND 3),
    ADD COLUMN registry_date     date,
    ADD COLUMN epub_year         integer,
    ADD COLUMN print_year        integer,
    ADD COLUMN short             text,
    ADD COLUMN note              text,
    ADD COLUMN judgement         text,
    ADD COLUMN reason            text,
    ADD COLUMN confidence_note   text,
    ADD COLUMN patient_trials    jsonb,
    ADD FOREIGN KEY (mondo_id, mechanism_key, track_id) REFERENCES preclin.atlas_track (mondo_id, mechanism_key, track_id),
    ADD CHECK (untested_reason IS NULL OR status = 'untested'),
    ADD CHECK (imported_from IS NULL OR population_group = 'other_disease');

COMMENT ON TABLE preclin.atlas_track IS
    'One model system used for one member drug by one route in a tracked tile (drafter brief: a track is model_id x drug x route). drug is the member as the tile lists it, or ''class'' for a system tied to no drug (human genetics, a target knockout); moiety_id is that member''s moiety. Stored by drafts/track_store.py with the tile.';
COMMENT ON COLUMN preclin.atlas_track.track_id IS 'model_id, drug and route joined by '' / ''; unique within the tile.';
COMMENT ON COLUMN preclin.atlas_track.route IS 'How the drug was given to the patients the track is compared with.';
COMMENT ON TABLE preclin.atlas_track_entry IS
    'A tracked tile''s model track records: one row per entry, a dated status of one track (atlas_track) for one question. A cell''s tracks are its entries grouped by track_id, and by modality where a multi-modality tile splits dose and safety. Stored by drafts/track_store.py from a draft that passes drafts/lint.py; a store replaces the tile.';
COMMENT ON COLUMN preclin.atlas_track_entry.population IS 'The patients compared, in words; population_group codes them.';
COMMENT ON COLUMN preclin.atlas_track_entry.population_group IS 'unselected; biomarker_selected (genotype or biomarker); stage_or_line (disease stage or line of therapy); other_disease (a harm imported from another disease, imported_from names it).';
COMMENT ON COLUMN preclin.atlas_track_entry.combination_with IS 'The partner drug when the patients compared got a member drug in combination with another active drug.';
COMMENT ON COLUMN preclin.atlas_track_entry.untested_reason IS 'Why a track''s latest never-compared entry was never compared (drafter brief rule 5).';
COMMENT ON COLUMN preclin.atlas_track_entry.patient_trials IS 'Trials that change no status: a list of {nct, registry_date, doi, quote}.';
COMMIT;
