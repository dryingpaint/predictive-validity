-- Results papers linked to ClinicalTrials.gov studies (pipeline.outcomes
-- publications): PMIDs the registry lists as RESULT/DERIVED references, and
-- PubMed articles that index the NCT id as a secondary identifier. Article
-- metadata stays in public.publications, which gains the abstract.

BEGIN;
SET LOCAL lock_timeout = '90s';
ALTER TABLE public.publications ADD COLUMN IF NOT EXISTS abstract text;
CREATE TABLE IF NOT EXISTS preclin.trial_publication (
    nct_id      text NOT NULL REFERENCES preclin.ctgov_study,
    pmid        text NOT NULL REFERENCES public.publications (pmid),
    link_source text NOT NULL CHECK (link_source IN ('ctgov_reference', 'pubmed_secondary_id')),
    PRIMARY KEY (nct_id, pmid, link_source)
);
COMMIT;
