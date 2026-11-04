-- Correct comments from 127 that a check against the data showed to overstate: moiety modality and
-- target_kind are also null for entities the model declined to classify, and fda_submission_letter's
-- no_letter_pdf rows hold a CBER listing entry rather than marking a failed fetch.

BEGIN;
SET LOCAL lock_timeout = '3s';

COMMENT ON COLUMN preclin.moiety.modality IS 'Modality (task moiety_modality): small_molecule, monoclonal_antibody, protein, peptide, vaccine, antibody_drug_conjugate, multispecific_antibody, gene_therapy, other_cell_therapy, ...; null for entities without a development program and those the model declined to classify (some pathogen- or toxin-derived products).';
COMMENT ON COLUMN preclin.moiety.target_kind IS 'human_protein, pathogen, no_single_target or unknown (task moiety_targets); null for entities without an industry development program and those the model declined to classify.';
COMMENT ON COLUMN preclin.fda_submission_letter.letter_sha256 IS 'The stored document text (preclin.fda_letter); null when the fetch failed.';
COMMENT ON COLUMN preclin.fda_submission_letter.fetch_error IS '404 (the document could not be fetched; letter_sha256 is null) or no_letter_pdf (a CBER approval with no letter PDF: the stored text is its entry on the CBER approvals listing, and url is that page); null otherwise.';

COMMIT;
