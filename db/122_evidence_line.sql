-- The compiled evidence-line dataset of the 2026-11-03 plan amendment (report/translation_plan.md), stored by
-- `python -m report.evidence_lines store`: the registry of lines, one row per US-developed phase entry of
-- 2008-2019, and each entry's value on each line in long form. Every store replaces all four tables at once.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.evidence_line_build (
    build_id    uuid PRIMARY KEY,
    built_at    timestamptz NOT NULL DEFAULT now(),
    code_commit text,
    snapshot    date NOT NULL,
    n_entries   integer NOT NULL
);
COMMENT ON TABLE preclin.evidence_line_build IS
    'Each store of the evidence-line dataset (report.evidence_lines store): the programs snapshot it was built from and the code commit. The other evidence-line tables hold the latest build only.';

CREATE TABLE preclin.evidence_line (
    line_key   text PRIMARY KEY,
    position   integer NOT NULL,
    category   text NOT NULL,
    level      text NOT NULL CHECK (level IN ('category', 'subcategory', 'descriptive', 'adjustment', 'measurement')),
    label      text NOT NULL,
    applies    text NOT NULL,
    status     text NOT NULL DEFAULT '',
    build_id   uuid NOT NULL REFERENCES preclin.evidence_line_build (build_id)
);
COMMENT ON TABLE preclin.evidence_line IS
    'Registry of evidence lines (report.evidence_lines.CATEGORIES): efficacy categories grouped by the experimental system that produced the evidence, then safety risk and clinical precedent, the biomarker-selection adjustment, and two raw measurements.';
COMMENT ON COLUMN preclin.evidence_line.line_key IS
    'The line''s key: its column in entries.csv, or a slug of its label for a line with no values.';
COMMENT ON COLUMN preclin.evidence_line.position IS 'Display order, categories first then their subcategories.';
COMMENT ON COLUMN preclin.evidence_line.level IS
    'category (exposed when any non-descriptive subcategory is), subcategory, descriptive (shown but not part of its category), adjustment, or measurement (a raw value behind a line).';
COMMENT ON COLUMN preclin.evidence_line.applies IS
    'The entries a line is scored on (report.evidence_lines.APPLIES): all, target (a single resolved human protein target and a disease), ONC, small_molecule, brain, phase_2_3 or from_2011.';
COMMENT ON COLUMN preclin.evidence_line.status IS
    'Why a line has no values, empty when it has them (the literature lines are descriptive after failing their gate).';

CREATE TABLE preclin.evidence_entry (
    moiety_id          integer NOT NULL REFERENCES preclin.moiety (moiety_id),
    mondo_id           text NOT NULL,
    phase              integer NOT NULL CHECK (phase IN (1, 2, 3)),
    entry_date         date NOT NULL,
    entry_year         integer NOT NULL,
    regime             text,
    bio_area           text,
    modality           text,
    novel              boolean NOT NULL,
    target             text,
    has_target_disease boolean NOT NULL,
    biomarker_selected boolean,
    build_id           uuid NOT NULL REFERENCES preclin.evidence_line_build (build_id),
    PRIMARY KEY (moiety_id, mondo_id, phase)
);
COMMENT ON TABLE preclin.evidence_entry IS
    'One row per US-developed phase entry of 2008-2019: a program entering a phase with a US-sited industry trial (report.section1.phase_rows, skipped phases excluded). Keyed by entity, disease and phase, since program ids change when programs are rebuilt. Outcomes are not stored here; the report derives them.';
COMMENT ON COLUMN preclin.evidence_entry.mondo_id IS 'The program disease; empty for an entity''s disease-unspecified program.';
COMMENT ON COLUMN preclin.evidence_entry.regime IS
    'ONC (oncology), DD (hereditary disease with curated Mendelian evidence on the target) or COM (everything else).';
COMMENT ON COLUMN preclin.evidence_entry.novel IS 'The entity had no FDA approval for any disease before entry.';
COMMENT ON COLUMN preclin.evidence_entry.target IS 'Symbols of the entity''s primary human protein targets, joined with +.';
COMMENT ON COLUMN preclin.evidence_entry.has_target_disease IS
    'The entry has a single resolved human protein target set and a disease, so target-level lines apply.';
COMMENT ON COLUMN preclin.evidence_entry.biomarker_selected IS
    'An industry trial that opened the phase on the entry date restricts enrolment by a molecular biomarker (preclin.trial_biomarker_selection); null when none was labelled.';

CREATE TABLE preclin.evidence_entry_line (
    moiety_id integer NOT NULL,
    mondo_id  text NOT NULL,
    phase     integer NOT NULL,
    line_key  text NOT NULL REFERENCES preclin.evidence_line (line_key),
    value     double precision NOT NULL,
    PRIMARY KEY (moiety_id, mondo_id, phase, line_key),
    FOREIGN KEY (moiety_id, mondo_id, phase) REFERENCES preclin.evidence_entry
);
COMMENT ON TABLE preclin.evidence_entry_line IS
    'Each entry''s value on each evidence line, frozen at the year before entry. A line is exposed when its value is above 0. A missing row means the line does not apply to the entry or was not measured for it.';
COMMENT ON COLUMN preclin.evidence_entry_line.value IS
    'A flag (0 or 1), an evidence count or tier for the source lines, or a raw measurement (best pChEMBL, selectivity margin in log units).';

COMMIT;
