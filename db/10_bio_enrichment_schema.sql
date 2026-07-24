-- BIO-replication enrichment tables
--
-- Two long-form fact tables + one coverage view. Populated by:
--   analyses/enrich_modality.py         (curated → ChEMBL API sources)
--   analyses/enrich_modality_llm.py     (Claude Haiku fallback for names)
--   analyses/enrich_indications.py      (Claude Haiku indication → 14-area classifier)
--
-- Idempotent: `CREATE TABLE IF NOT EXISTS` + `ON CONFLICT DO UPDATE` in the loaders.

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────
-- preclin.indication_bio_class — one row per indication, 14 BIO areas + rare/chronic flags
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS preclin.indication_bio_class (
  indication_id         INTEGER PRIMARY KEY REFERENCES preclin.indication(indication_id),
  bio_area              TEXT    NOT NULL,     -- Allergy | Autoimmune | Cardiovascular |
                                              -- Endocrine | Gastroenterology | Hematology |
                                              -- Infectious disease | Metabolic | Neurology |
                                              -- Oncology | Ophthalmology | Psychiatry |
                                              -- Respiratory | Urology | Other
  bio_subarea           TEXT,                 -- free-text; a short canonical name
  is_rare               BOOLEAN NOT NULL DEFAULT FALSE,
  is_chronic_high_prev  BOOLEAN NOT NULL DEFAULT FALSE,
  source                TEXT    NOT NULL,     -- 'llm_haiku_4_5' | 'curated' | 'ct_gov_conditions'
  confidence            TEXT,                 -- 'high' | 'medium' | 'low'
  rationale             TEXT,                 -- source display_name (audit)
  extracted_at          TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ibc_area    ON preclin.indication_bio_class (bio_area);
CREATE INDEX IF NOT EXISTS idx_ibc_rare    ON preclin.indication_bio_class (is_rare);
CREATE INDEX IF NOT EXISTS idx_ibc_chronic ON preclin.indication_bio_class (is_chronic_high_prev);

COMMENT ON TABLE preclin.indication_bio_class IS
  'BIO 2021 replication: canonical 14-area classification + rare/chronic-high-prev flags. Populated by Claude Haiku over indication display names.';


-- ─────────────────────────────────────────────────────────────────────────
-- preclin.drug_bio_class — one row per drug, canonical modality + novelty
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS preclin.drug_bio_class (
  drug_id           INTEGER PRIMARY KEY REFERENCES preclin.drug(drug_id),
  modality          TEXT    NOT NULL,        -- small_molecule | antibody | adc | protein |
                                             -- peptide | oligonucleotide | cell_therapy |
                                             -- gene_therapy | vaccine | mrna | other
  modality_subtype  TEXT,                    -- 'CAR-T' | 'bispecific mAb' | 'siRNA' | ...
  is_novel          BOOLEAN,                 -- true = NME/biologic/vaccine/cell/gene/mrna
  novelty_class     TEXT,                    -- NME | biologic | vaccine | biosimilar | non_NME | unknown
  source            TEXT    NOT NULL,        -- 'curated_approvals' | 'public_therapies' |
                                             -- 'chembl_api' | 'llm_haiku_4_5'
  confidence        TEXT,                    -- 'high' | 'medium' | 'low'
  extracted_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dbc_modality ON preclin.drug_bio_class (modality);
CREATE INDEX IF NOT EXISTS idx_dbc_novelty  ON preclin.drug_bio_class (novelty_class);

COMMENT ON TABLE preclin.drug_bio_class IS
  'BIO 2021 replication: canonical drug modality + novelty class. Source ladder in loader: curated approvals → public.therapies → ChEMBL /molecule API → Claude Haiku.';


-- ─────────────────────────────────────────────────────────────────────────
-- Coverage view — one-row snapshot of how much of the corpus is enriched.
-- Useful in CI/regression: if this view shows a coverage regression, the
-- downstream BIO replication numbers can't be trusted.
-- ─────────────────────────────────────────────────────────────────────────
DROP VIEW IF EXISTS preclin.v_bio_enrichment_coverage;
CREATE VIEW preclin.v_bio_enrichment_coverage AS
SELECT
  (SELECT COUNT(*) FROM preclin.indication)           AS n_indications_total,
  (SELECT COUNT(*) FROM preclin.indication_bio_class) AS n_indications_classified,
  (SELECT COUNT(*) FROM preclin.drug)                 AS n_drugs_total,
  (SELECT COUNT(*) FROM preclin.drug_bio_class)       AS n_drugs_classified,
  (SELECT COUNT(*) FROM preclin.drug d
    JOIN preclin.program p ON p.drug_id = d.drug_id)  AS n_drugs_in_cohort,
  (SELECT COUNT(*) FROM preclin.drug d
    JOIN preclin.program p ON p.drug_id = d.drug_id
    JOIN preclin.drug_bio_class dbc ON dbc.drug_id = d.drug_id)
                                                       AS n_drugs_in_cohort_classified;

COMMENT ON VIEW preclin.v_bio_enrichment_coverage IS
  'Coverage snapshot for the BIO-replication enrichment pipeline. Query this before running bio_replication.py.';

COMMIT;
