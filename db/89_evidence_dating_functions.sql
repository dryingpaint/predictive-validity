-- Evidence dating in the database: preclin.ot_evidence_key gives the key preclin.evidence_known_year
-- dates a row by, preclin.harmonic_series rebuilds a yearly association score from dated rows, and
-- preclin.clinvar_accession_calibration holds the sampled ClinVar records that date every RCV record
-- by its creation. ot_evidence.source_year keeps the row's own Open Targets date, so dating is
-- repeatable. Replaces the ClinVar snapshot design described in 88.

BEGIN;
SET LOCAL lock_timeout = '3s';

-- The key under which preclin.evidence_known_year dates an evidence row: the ClinVar RCV accession,
-- the IMPC-consortium allele of a mouse model, the study accession or the IntOGen cohort; null for
-- rows dated only by their own publication.
CREATE OR REPLACE FUNCTION preclin.ot_evidence_key(datasource text, detail jsonb) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN datasource IN ('eva', 'eva_somatic', 'expression_atlas', 'crispr_screen') THEN detail->>'studyId'
        WHEN datasource = 'intogen' THEN detail->>'cohortShortName'
        WHEN datasource = 'impc' THEN (  -- an allele may carry a note after it ("hom early")
            SELECT split_part(trim(a), ' ', 1)
            FROM unnest(string_to_array(detail->>'biologicalModelAllelicComposition', '/')) AS a
            WHERE a ~ '[(](EUCOMM|KOMP|IMPC|EUCOMMTools|NCOM)[)]' LIMIT 1)
    END
$$;

-- Yearly association score of one target-disease-datasource from its dated items (years ascending,
-- scores in the same order): at each year an item was dated, the score Open Targets computes from
-- the items dated by then, the harmonic sum of their scores (the i-th largest weighted 1/i^2, at
-- most 1000 items) over the largest such sum, sum(1/i^2) for i <= 1000.
CREATE OR REPLACE FUNCTION preclin.harmonic_series(ys integer[], ss double precision[],
                                                   OUT years smallint[], OUT scores real[])
LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE AS $$
DECLARE
    norm CONSTANT double precision := 1.6439345666815615;
    known double precision[] := '{}';
    total double precision;
    n integer := cardinality(ys);
BEGIN
    years := '{}';
    scores := '{}';
    FOR i IN 1 .. n LOOP
        known := known || ss[i];
        IF i = n OR ys[i + 1] <> ys[i] THEN
            known := ARRAY(SELECT unnest(known) ORDER BY 1 DESC);
            total := 0;
            FOR j IN 1 .. least(cardinality(known), 1000) LOOP
                total := total + known[j] / (j * j);
            END LOOP;
            years := years || ys[i]::smallint;
            scores := scores || (total / norm)::real;
        END IF;
    END LOOP;
END
$$;

COMMENT ON TABLE preclin.evidence_known_year IS
    'Year an evidence item became public, by preclin.ot_evidence_key (ClinVar RCV accession, IMPC '
    'allele, study accession or cohort), from the source''s own release history (pipeline.evidence_dates)';
COMMENT ON COLUMN preclin.evidence_known_year.basis IS
    'How the year was found: clinvar_accession (creation year of the RCV record, calibrated from its '
    'accession number), clinvar_evaluated (record from ClinVar''s 2013 launch import, dated by its '
    'earlier evaluation), impc_release (first IMPC data release with phenotype calls for the '
    'allele), geo_public or arrayexpress_public (public date of the experiment), intogen_cohort_year '
    '(year in the cohort name), publication (the screen''s paper)';

CREATE TABLE IF NOT EXISTS preclin.clinvar_accession_calibration (
    rcv_number         bigint PRIMARY KEY,
    created            date NOT NULL,
    source_release_id  bigint NOT NULL REFERENCES preclin.evidence_source_release
);
COMMENT ON TABLE preclin.clinvar_accession_calibration IS
    'ClinVar RCV records sampled across the accession range with the date of their first submission; '
    'accessions are issued in order of creation, so these date every record (pipeline.evidence_dates clinvar)';

ALTER TABLE preclin.ot_evidence ADD COLUMN IF NOT EXISTS source_year integer;
ALTER TABLE preclin.ot_evidence ADD COLUMN IF NOT EXISTS year_basis text;
UPDATE preclin.ot_evidence SET source_year = evidence_year WHERE source_year IS NULL AND year_basis IS NULL;
COMMENT ON COLUMN preclin.ot_evidence.source_year IS
    'Year of the row''s own publication, evidence or release date in Open Targets';
COMMENT ON COLUMN preclin.ot_evidence.evidence_year IS
    'Year the evidence became known: the year preclin.evidence_known_year holds for its key where there '
    'is one, else source_year';
COMMENT ON COLUMN preclin.ot_evidence.year_basis IS
    'open_targets (evidence_year is source_year) or the basis of its preclin.evidence_known_year row; '
    'null when the row is undated';
COMMENT ON COLUMN preclin.ot_association.series_years IS
    'Years at which the association score changed, rebuilt from the dated rows of preclin.ot_evidence '
    '(preclin.harmonic_series); undated rows count only in the release score';
COMMIT;
