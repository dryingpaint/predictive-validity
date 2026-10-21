-- FDA approval sources: Drugs@FDA applications, products, submissions and
-- approval letters; openFDA structured product labels; and the approved uses
-- an LLM extracted from each letter.
--
-- These tables are the evidence behind indication-level approval outcomes.
-- Each row carries the source release it was loaded from
-- (preclin.evidence_source_release). Loaded by `python -m pipeline.fda`.

BEGIN;

CREATE TABLE IF NOT EXISTS preclin.fda_application (
    appl_no           text PRIMARY KEY,
    appl_type         text NOT NULL CHECK (appl_type IN ('NDA', 'BLA')),
    center            text NOT NULL CHECK (center IN ('CDER', 'CBER')),
    sponsor_name      text,
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release
);

CREATE TABLE IF NOT EXISTS preclin.fda_product (
    appl_no           text NOT NULL REFERENCES preclin.fda_application,
    product_no        text NOT NULL,
    drug_name         text NOT NULL,
    active_ingredient text NOT NULL,
    form              text,
    strength          text,
    PRIMARY KEY (appl_no, product_no)
);

CREATE TABLE IF NOT EXISTS preclin.fda_submission (
    appl_no           text NOT NULL REFERENCES preclin.fda_application,
    submission_type   text NOT NULL CHECK (submission_type IN ('ORIG', 'SUPPL')),
    submission_no     text NOT NULL,
    submission_class  text,
    status            text NOT NULL,
    status_date       date,
    review_priority   text,
    PRIMARY KEY (appl_no, submission_type, submission_no)
);
CREATE INDEX IF NOT EXISTS fda_submission_class_date_idx
    ON preclin.fda_submission (submission_class, status_date);

-- One row per (submission, letter URL). The same letter PDF can approve
-- several applications at once, so letter text is keyed by its SHA-256.
CREATE TABLE IF NOT EXISTS preclin.fda_letter (
    letter_sha256     text PRIMARY KEY CHECK (letter_sha256 ~ '^[0-9a-f]{64}$'),
    letter_text       text NOT NULL,
    n_bytes           integer NOT NULL
);

CREATE TABLE IF NOT EXISTS preclin.fda_submission_letter (
    appl_no           text NOT NULL,
    submission_type   text NOT NULL,
    submission_no     text NOT NULL,
    url               text NOT NULL,
    doc_date          date,
    letter_sha256     text REFERENCES preclin.fda_letter,
    fetch_error       text,
    PRIMARY KEY (appl_no, submission_type, submission_no, url),
    FOREIGN KEY (appl_no, submission_type, submission_no) REFERENCES preclin.fda_submission
);

-- Current structured product label per SPL set, restricted to NDA/BLA labels.
CREATE TABLE IF NOT EXISTS preclin.fda_label (
    set_id              text PRIMARY KEY,
    spl_id              text NOT NULL,
    effective_date      date,
    application_numbers text[] NOT NULL,
    brand_names         text[] NOT NULL,
    generic_names       text[] NOT NULL,
    substance_names     text[] NOT NULL,
    unii                text[] NOT NULL,
    indications_text    text,
    source_release_id   bigint NOT NULL REFERENCES preclin.evidence_source_release
);
CREATE INDEX IF NOT EXISTS fda_label_appl_idx ON preclin.fda_label USING gin (application_numbers);

-- Uses approved by one letter, as extracted by the LLM decision it references.
CREATE TABLE IF NOT EXISTS preclin.fda_approved_use (
    approved_use_id       bigserial PRIMARY KEY,
    letter_sha256         text NOT NULL REFERENCES preclin.fda_letter,
    ordinal               integer NOT NULL,
    disease               text NOT NULL,
    indication_as_written text NOT NULL,
    qualifiers            text[] NOT NULL,
    change_type           text NOT NULL CHECK (change_type IN (
        'original_approval', 'new_indication', 'new_population', 'new_regimen',
        'conversion_to_full', 'efficacy_labeling', 'other')),
    accelerated_approval  boolean NOT NULL,
    llm_decision_id       bigint NOT NULL REFERENCES pv_evidence.llm_decision,
    UNIQUE (letter_sha256, ordinal)
);

COMMENT ON TABLE preclin.fda_application IS
  'NDA/BLA applications from Drugs@FDA (CDER) and CBER licensed biologics. Loaded by pipeline.fda.';
COMMENT ON TABLE preclin.fda_approved_use IS
  'Approved uses stated in FDA approval letters (one row per disease/population per letter), extracted by the referenced pv_evidence.llm_decision. Holds the rows of one extraction run; reloading replaces them. Approval dates come from preclin.fda_submission via fda_submission_letter.';

COMMIT;
