-- Link rights-reviewed full-text representations to canonical scholarly works.

BEGIN;

CREATE TABLE pv_source.representation (
  representation_id       BIGSERIAL PRIMARY KEY,
  scholarly_work_id       BIGINT NOT NULL
    REFERENCES pv_source.scholarly_work(scholarly_work_id) ON DELETE CASCADE,
  source_record_version_id BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  representation_kind     TEXT NOT NULL CHECK (
    representation_kind IN (
      'full_text_jats', 'full_text_pdf', 'supplement',
      'figure', 'table', 'parsed_text'
    )
  ),
  media_type              TEXT NOT NULL,
  rights_assertion_id     BIGINT NOT NULL
    REFERENCES pv_source.rights_assertion(rights_assertion_id),
  object_blob_id          BIGINT
    REFERENCES pv_source.object_blob(object_blob_id),
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (scholarly_work_id, source_record_version_id, representation_kind)
);

CREATE INDEX pv_representation_work_kind_idx
  ON pv_source.representation (scholarly_work_id, representation_kind);

COMMIT;
