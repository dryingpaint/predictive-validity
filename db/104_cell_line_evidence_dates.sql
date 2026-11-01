-- DepMap common-essential genes are kept per release year, so the pan-essential flag can be taken as of
-- a program's phase entry; Project Score rows are dated by the first Open Targets release that listed them.

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.depmap_common_essential ADD COLUMN release_year integer;
UPDATE preclin.depmap_common_essential SET release_year = 2024;
ALTER TABLE preclin.depmap_common_essential ALTER COLUMN release_year SET NOT NULL;
ALTER TABLE preclin.depmap_common_essential DROP CONSTRAINT depmap_common_essential_pkey;
ALTER TABLE preclin.depmap_common_essential ADD PRIMARY KEY (release_year, entrez_id);
COMMENT ON TABLE preclin.depmap_common_essential IS
    'DepMap inferred common-essential genes, one list per year from the last public release of that year (pipeline.depmap)';
COMMENT ON COLUMN preclin.depmap_common_essential.release_year IS
    'Year of the DepMap release the list comes from (19Q4 -> 2019)';
COMMENT ON TABLE preclin.evidence_known_year IS
    'Year an evidence item became public, by preclin.ot_evidence_key (ClinVar RCV accession, IMPC allele, study accession or cohort) or, for Project Score (crispr), by "target disease", from the source''s own release history (pipeline.evidence_dates)';
COMMENT ON COLUMN preclin.evidence_known_year.basis IS
    'How the year was found: clinvar_accession (creation year of the RCV record, calibrated from its accession number), clinvar_evaluated (record from ClinVar''s 2013 launch import, dated by its earlier evaluation), impc_release (first IMPC data release with phenotype calls for the allele), geo_public or arrayexpress_public (public date of the experiment), intogen_cohort_year (year in the cohort name), publication (the screen''s paper), opentargets_release (first Open Targets release whose Project Score file listed the target and disease)';
COMMIT;
