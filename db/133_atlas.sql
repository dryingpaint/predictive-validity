-- The model-system atlas (issue #76, PR #81): the reviewed drug-class table, every mechanism of every named
-- indication (the register) with the tracked ones (decision 12), each tile's model-versus-patient track record
-- and its checker verdicts, and the FDA review documents the drafters read.
--
-- analyses/model-system-atlas/class_audit.py store replaces the build tables (atlas_indication,
-- atlas_moiety_review, atlas_mechanism, atlas_member) in one transaction; fetch_sources.py store upserts
-- atlas_source_document; drafts/track_store.py replaces one tile's track record at a time. Track records are
-- keyed by (mondo_id, mechanism_key), which survives rebuilds, so they are not tied to a build.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.atlas_build (
    build_id     uuid PRIMARY KEY,
    built_at     timestamptz NOT NULL DEFAULT now(),
    code_commit  text,
    snapshot     date NOT NULL,
    min_programs integer NOT NULL CHECK (min_programs >= 1),
    n_members    integer NOT NULL,
    n_register   integer NOT NULL,
    n_tracked    integer NOT NULL,
    method_id    text NOT NULL REFERENCES preclin.analysis_method
);
COMMENT ON TABLE preclin.atlas_build IS
    'Each store of the atlas class register (analyses/model-system-atlas/class_audit.py store): the programs snapshot, the code commit and the tracking floor. atlas_indication, atlas_moiety_review, atlas_mechanism and atlas_member hold the latest build only.';
COMMENT ON COLUMN preclin.atlas_build.min_programs IS 'Distinct entities a mechanism needs in an indication to be tracked (decision 12).';
COMMENT ON COLUMN preclin.atlas_build.n_members IS 'Rows of atlas_member: novel Phase 2 entries of 2008-2019 in the named indications.';
COMMENT ON COLUMN preclin.atlas_build.n_register IS 'Rows of atlas_register: indication x mechanism pairs.';
COMMENT ON COLUMN preclin.atlas_build.n_tracked IS 'Register rows with at least min_programs entities.';

CREATE TABLE preclin.atlas_indication (
    mondo_id   text PRIMARY KEY,
    label      text NOT NULL,
    area       text NOT NULL,
    area_rank  integer NOT NULL,
    n_programs integer NOT NULL,
    merged_from text[] NOT NULL DEFAULT '{}',
    build_id   uuid NOT NULL REFERENCES preclin.atlas_build (build_id)
);
COMMENT ON TABLE preclin.atlas_indication IS
    'The named indications of the atlas (lists.py): the top diseases of each area by Phase 2 entrants of 2008-2019 under report.section1.phase_rows, after the MERGE and DROP cleaning rules.';
COMMENT ON COLUMN preclin.atlas_indication.n_programs IS 'Phase 2 entrant programs of 2008-2019 in the indication, novel or not; the denominator of a mechanism''s share.';
COMMENT ON COLUMN preclin.atlas_indication.merged_from IS 'MONDO terms counted under this one (lists.MERGE).';

CREATE TABLE preclin.atlas_moiety_review (
    moiety_id          integer PRIMARY KEY REFERENCES preclin.moiety (moiety_id),
    same_entity_as     integer REFERENCES preclin.moiety (moiety_id),
    target_label       text NOT NULL,
    action             text,
    selectivity        text CHECK (selectivity IN ('selective', 'dual', 'pan', 'off-class', 'no target')),
    modality_group     text CHECK (modality_group IN ('small molecule', 'antibody', 'ADC', 'protein', 'peptide', 'oligo',
                                                      'cell therapy', 'gene therapy', 'other')),
    first_fda_approval date,
    novel_override     boolean,
    evidence           text NOT NULL,
    note               text,
    build_id           uuid NOT NULL REFERENCES preclin.atlas_build (build_id)
);
COMMENT ON TABLE preclin.atlas_moiety_review IS
    'The hand review behind the atlas''s mechanisms (analyses/model-system-atlas/lists/class_audit/reviews.csv, the curated source, stored with each build): one row per reviewed entity, checked against ChEMBL, FDA labels and primary literature. Where it disagrees with preclin.moiety_target or preclin.moiety the review governs the atlas; AUDIT.md lists the disagreements.';
COMMENT ON COLUMN preclin.atlas_moiety_review.same_entity_as IS 'A duplicate entity this row folds into (the review counts both once); null when the entity stands alone.';
COMMENT ON COLUMN preclin.atlas_moiety_review.target_label IS
    'Verified target: a gene symbol, a family ("JAK (pan)", "HIV integrase (INSTI)"), or "unknown" when the mechanism is undisclosed.';
COMMENT ON COLUMN preclin.atlas_moiety_review.action IS 'Verified action, in preclin.moiety_target''s vocabulary (inhibitor, agonist, binder_neutralizer, ...).';
COMMENT ON COLUMN preclin.atlas_moiety_review.selectivity IS
    'selective; dual (two targets, the mechanism''s among them); pan (a family); off-class (the database''s target is wrong for it); no target (no molecular target: a lubricant, barrier or photosensitiser).';
COMMENT ON COLUMN preclin.atlas_moiety_review.first_fda_approval IS 'First FDA approval of the active ingredient for anything, verified; null when never approved.';
COMMENT ON COLUMN preclin.atlas_moiety_review.novel_override IS 'Novelty at Phase 2 entry when the approval date alone does not decide it (a metabolite, enantiomer or plasma product); null otherwise.';
COMMENT ON COLUMN preclin.atlas_moiety_review.evidence IS 'Source for the row: a ChEMBL, FDA or registry URL, a DOI, or a PubMed query for a code-named compound.';

CREATE TABLE preclin.atlas_mechanism (
    mechanism_key text PRIMARY KEY,
    target_label  text NOT NULL,
    action        text NOT NULL,
    label         text NOT NULL,
    build_id      uuid NOT NULL REFERENCES preclin.atlas_build (build_id)
);
COMMENT ON TABLE preclin.atlas_mechanism IS
    'Mechanisms of the atlas: a verified (target, action), across modalities (decision 12). A non-selective entity carries its own target label, so it forms its own mechanism.';
COMMENT ON COLUMN preclin.atlas_mechanism.mechanism_key IS 'target_label|action; the key track records use, stable across builds while the review is.';
COMMENT ON COLUMN preclin.atlas_mechanism.label IS 'Display label, e.g. "BTK inhibitors".';

CREATE TABLE preclin.atlas_member (
    moiety_id        integer NOT NULL REFERENCES preclin.moiety (moiety_id),
    mondo_id         text NOT NULL REFERENCES preclin.atlas_indication (mondo_id),
    program_mondo_id text NOT NULL,
    entity_id        integer NOT NULL REFERENCES preclin.moiety (moiety_id),
    mechanism_key    text REFERENCES preclin.atlas_mechanism (mechanism_key),
    excluded         text CHECK (excluded IN ('no_target', 'undisclosed', 'not_novel')),
    modality_group   text NOT NULL,
    entry_date       date NOT NULL,
    furthest_phase   integer,
    reviewed         boolean NOT NULL,
    build_id         uuid NOT NULL REFERENCES preclin.atlas_build (build_id),
    PRIMARY KEY (moiety_id, mondo_id, program_mondo_id),
    CHECK ((mechanism_key IS NULL) <> (excluded IS NULL))
);
COMMENT ON TABLE preclin.atlas_member IS
    'One row per novel Phase 2 entry of 2008-2019 in a named indication, keyed by entity and disease since program ids change when programs are rebuilt: the mechanism it counts toward, or why it counts toward none.';
COMMENT ON COLUMN preclin.atlas_member.mondo_id IS 'The named indication (after lists.MERGE); program_mondo_id is the program''s own disease.';
COMMENT ON COLUMN preclin.atlas_member.entity_id IS 'The entity counted: moiety_id, or the entity a duplicate folds into (atlas_moiety_review.same_entity_as).';
COMMENT ON COLUMN preclin.atlas_member.excluded IS 'no_target, undisclosed (mechanism not public) or not_novel (FDA-approved before entry); null when the entry counts toward mechanism_key.';
COMMENT ON COLUMN preclin.atlas_member.modality_group IS 'Reviewed modality group, else the database''s modality mapped to the same groups.';
COMMENT ON COLUMN preclin.atlas_member.furthest_phase IS 'Highest phase the program reached, 4 when approved for this indication. Reported, never used to choose what is tracked.';
COMMENT ON COLUMN preclin.atlas_member.reviewed IS 'The entity has a row in atlas_moiety_review; when false its target and action are the database''s.';

CREATE VIEW preclin.atlas_register AS
SELECT m.mondo_id,
       m.mechanism_key,
       count(DISTINCT m.entity_id)                           AS n_entities,
       count(DISTINCT m.entity_id)::numeric / i.n_programs   AS share,
       array_agg(DISTINCT m.modality_group)                  AS modality_groups,
       max(m.furthest_phase)                                 AS furthest_phase,
       count(DISTINCT m.entity_id) >= b.min_programs         AS tracked
FROM preclin.atlas_member m
JOIN preclin.atlas_indication i USING (mondo_id)
JOIN preclin.atlas_build b ON b.build_id = m.build_id
WHERE m.mechanism_key IS NOT NULL
GROUP BY m.mondo_id, m.mechanism_key, i.n_programs, b.min_programs;
COMMENT ON VIEW preclin.atlas_register IS
    'Every mechanism of every named indication, counted across modalities (decision 12). tracked: at least atlas_build.min_programs distinct entities, so the tile''s model track record is drafted. Phase never decides tracking.';

CREATE TABLE preclin.atlas_track_entry (
    mondo_id                text NOT NULL,
    mechanism_key           text NOT NULL,
    question                text NOT NULL CHECK (question IN ('engagement', 'dose', 'efficacy', 'safety')),
    modality                text NOT NULL DEFAULT '',
    seq                     integer NOT NULL,
    year                    integer NOT NULL,
    status                  text NOT NULL CHECK (status IN ('untested', 'same', 'neg', 'other', 'contra', 'retro')),
    model_id                text NOT NULL,
    model                   text NOT NULL,
    src                     text,
    src_label               text,
    quote                   text,
    source_tier             smallint CHECK (source_tier BETWEEN 1 AND 5),
    comparison_stated       boolean,
    retrodiction            boolean NOT NULL DEFAULT false,
    model_change            boolean NOT NULL DEFAULT false,
    patient_signal_reversed boolean NOT NULL DEFAULT false,
    confidence              text CHECK (confidence IN ('high', 'medium', 'low')),
    fields                  jsonb NOT NULL DEFAULT '{}',
    drafted_by              text NOT NULL,
    stored_at               timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (mondo_id, mechanism_key, question, modality, seq),
    CHECK (status <> 'retro' OR retrodiction),
    CHECK (status <> 'other' OR question = 'safety')
);
COMMENT ON TABLE preclin.atlas_track_entry IS
    'A tracked tile''s model track record (drafter brief v3, RULES_V3_PROPOSAL.md): one row per entry of a cell''s strip, each a dated status of the best model for one question. Stored by drafts/track_store.py from a draft that passes drafts/lint.py; a store replaces the tile.';
COMMENT ON COLUMN preclin.atlas_track_entry.mondo_id IS 'The named indication (preclin.atlas_indication).';
COMMENT ON COLUMN preclin.atlas_track_entry.mechanism_key IS 'The tile''s mechanism (preclin.atlas_mechanism).';
COMMENT ON COLUMN preclin.atlas_track_entry.modality IS 'The modality sub-strip for a dose or platform-safety entry of a multi-modality tile (decision 12); empty for a pooled entry.';
COMMENT ON COLUMN preclin.atlas_track_entry.seq IS 'Position in the strip, from 1, in year order within the modality.';
COMMENT ON COLUMN preclin.atlas_track_entry.year IS 'Earliest year the comparison was public: registry results, epub, label or print (decision 7).';
COMMENT ON COLUMN preclin.atlas_track_entry.status IS
    'untested (model used, never compared), same (matched), neg (matched, incl. a known failure), other (safety: matched on another molecule of the platform), contra (contradicted), retro (a retrodiction that reproduced the known result; decision 10).';
COMMENT ON COLUMN preclin.atlas_track_entry.model_id IS 'Stable slug of the model system; each model''s own record (decision 6) groups on it.';
COMMENT ON COLUMN preclin.atlas_track_entry.source_tier IS '1 paper, 2 regulator document, 3 registry results, 4 meta-analysis, 5 press release or SEC filing (decision 2; 4-5 patient side only).';
COMMENT ON COLUMN preclin.atlas_track_entry.comparison_stated IS 'The source itself compares model and patients; false when the drafter paired a model source (fields.model_src) with a patient source.';
COMMENT ON COLUMN preclin.atlas_track_entry.model_change IS 'A different best model took over at this entry (decision 6a).';
COMMENT ON COLUMN preclin.atlas_track_entry.patient_signal_reversed IS 'The early patient signal attenuated, so the model was right (decision 6b).';
COMMENT ON COLUMN preclin.atlas_track_entry.fields IS 'The entry''s other schema-v3 fields (note, judgement, magnitude, dates, readout_tier, derived_from, blocked_by, margin_stated, effect_size, class_threshold, outcome_tested, patient_trials, ...).';
COMMENT ON COLUMN preclin.atlas_track_entry.drafted_by IS 'Who drafted the entry: the agent brief and run, e.g. "DRAFTER_BRIEF_v3 / kappa-2026-11".';

CREATE TABLE preclin.atlas_track_verdict (
    mondo_id           text NOT NULL,
    mechanism_key      text NOT NULL,
    question           text NOT NULL,
    modality           text NOT NULL DEFAULT '',
    seq                integer NOT NULL,
    verdict            text NOT NULL CHECK (verdict IN ('confirmed', 'corrected', 'unverified')),
    source_resolves    boolean,
    quote_found        text CHECK (quote_found IN ('verbatim', 'near', 'not_found', 'abstract_only')),
    proposed_status    text CHECK (proposed_status IN ('untested', 'same', 'neg', 'other', 'contra', 'retro', 'drop')),
    proposed_year      integer,
    rule               text,
    note               text,
    adjudicated_status text CHECK (adjudicated_status IN ('untested', 'same', 'neg', 'other', 'contra', 'retro', 'drop')),
    adjudication_note  text,
    checked_by         text NOT NULL,
    stored_at          timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (mondo_id, mechanism_key, question, modality, seq),
    FOREIGN KEY (mondo_id, mechanism_key, question, modality, seq) REFERENCES preclin.atlas_track_entry ON DELETE CASCADE
);
COMMENT ON TABLE preclin.atlas_track_verdict IS
    'The checker''s verdict on each track-record entry (CHECKER_BRIEF_v3.md) and, for a corrected one, the adjudicator''s decision. The entry''s final status is adjudicated_status when set, else status.';
COMMENT ON COLUMN preclin.atlas_track_verdict.rule IS 'The decision of RULES_V3_PROPOSAL.md a correction rests on.';

CREATE TABLE preclin.atlas_source_document (
    appl_no    text NOT NULL,
    filename   text NOT NULL,
    kind       text NOT NULL,
    url        text NOT NULL,
    sha256     text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    n_bytes    integer NOT NULL,
    ocr        boolean NOT NULL,
    text       text NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (appl_no, filename)
);
COMMENT ON TABLE preclin.atlas_source_document IS
    'FDA review documents of the original approval of each tracked mechanism''s approved members, as text (analyses/model-system-atlas/fetch_sources.py store): the source bundle drafters grep. Members join through preclin.fda_application_moiety.';
COMMENT ON COLUMN preclin.atlas_source_document.kind IS 'label, PharmR (non-clinical), MedR (clinical), ClinPharmR, MultidisciplineR, IntegratedR, SumR, CrossR, StatR or ODMemo.';
COMMENT ON COLUMN preclin.atlas_source_document.sha256 IS 'SHA-256 of the PDF.';
COMMENT ON COLUMN preclin.atlas_source_document.ocr IS 'The PDF was scanned and the text is tesseract OCR, page by page.';

COMMIT;
