-- Pre-entry sources for each target-disease hypothesis (pipeline.target_disease search): the PubMed and Europe PMC
-- records that name the gene and the disease and were published before the year of the pair's first entry, kept
-- whole so the origin labelling (issue #146) and the target-literature screen (issue #154) read the same rows.
-- Also the columns the labelling adds to preclin.target_disease_origin: the second model's check of each label and
-- the descriptive discovery route of the pair's first drug (registered #146 step 3).

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE IF NOT EXISTS preclin.target_disease_search (
    ensembl_id     text NOT NULL,
    mondo_id       text NOT NULL,
    service        text NOT NULL CHECK (service IN ('pubmed', 'europepmc', 'firecrawl')),
    cutoff_year    integer NOT NULL,
    gene_names     text[] NOT NULL,
    disease_names  text[] NOT NULL,
    query          text NOT NULL,
    n_hits         integer NOT NULL,
    searched_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (ensembl_id, mondo_id, service),
    FOREIGN KEY (ensembl_id, mondo_id) REFERENCES preclin.target_disease ON DELETE CASCADE
);
COMMENT ON TABLE preclin.target_disease_search IS
    'One search per target-disease pair and service for sources dated before the pair''s first entry (pipeline.target_disease search). Re-searching a pair replaces its rows. Shared by the origin labelling (#146) and the target-literature screen (#154).';
COMMENT ON COLUMN preclin.target_disease_search.ensembl_id IS 'The pair (preclin.target_disease).';
COMMENT ON COLUMN preclin.target_disease_search.mondo_id IS 'The pair (preclin.target_disease).';
COMMENT ON COLUMN preclin.target_disease_search.service IS 'pubmed (E-utilities esearch and efetch), europepmc (records outside MEDLINE with an abstract), or firecrawl (reserved for #154; not written by the origin search).';
COMMENT ON COLUMN preclin.target_disease_search.cutoff_year IS 'Year of the pair''s first_entry. Only records published in an earlier year count, so the search runs to cutoff_year - 1.';
COMMENT ON COLUMN preclin.target_disease_search.gene_names IS 'Names searched for the gene: the HGNC symbol first, then its name, the target name, previous and alias symbols that pass pipeline.literature.usable, at most 12.';
COMMENT ON COLUMN preclin.target_disease_search.disease_names IS 'Names searched for the disease: the MONDO label and its synonyms, shortest first, at most 20. Terms close to the disease are not searched.';
COMMENT ON COLUMN preclin.target_disease_search.query IS 'The query as sent: gene names AND disease names in title or abstract, dated 1900 to cutoff_year - 1; reviews are kept.';
COMMENT ON COLUMN preclin.target_disease_search.n_hits IS 'Hit count the service reported for the query, before any record was dropped for a missing or late year; a count far above the stored rows shows a flooded name.';
COMMENT ON COLUMN preclin.target_disease_search.searched_at IS 'When the search ran.';

CREATE TABLE IF NOT EXISTS preclin.target_disease_source (
    ensembl_id  text NOT NULL,
    mondo_id    text NOT NULL,
    record_id   text NOT NULL,
    service     text NOT NULL CHECK (service IN ('pubmed', 'europepmc', 'firecrawl')),
    title       text NOT NULL,
    abstract    text,
    year        integer NOT NULL,
    doi         text,
    rank        integer NOT NULL,
    PRIMARY KEY (ensembl_id, mondo_id, record_id),
    FOREIGN KEY (ensembl_id, mondo_id) REFERENCES preclin.target_disease ON DELETE CASCADE
);
COMMENT ON TABLE preclin.target_disease_source IS
    'Every record a pair''s search returned, dated before the pair''s first entry (pipeline.target_disease search). The labelling shows the model the earliest 25 and the latest 15 by rank; the hand-check package shows the reader the same rows. Uncapped unless the search was run with --max-records.';
COMMENT ON COLUMN preclin.target_disease_source.ensembl_id IS 'The pair (preclin.target_disease).';
COMMENT ON COLUMN preclin.target_disease_source.mondo_id IS 'The pair (preclin.target_disease).';
COMMENT ON COLUMN preclin.target_disease_source.record_id IS 'PMID:<pmid> for PubMed; <source>:<id> for Europe PMC (its own id scheme, e.g. PPR:PPR12345). The id a label cites.';
COMMENT ON COLUMN preclin.target_disease_source.service IS 'Which search returned the record.';
COMMENT ON COLUMN preclin.target_disease_source.title IS 'Title as the service gives it.';
COMMENT ON COLUMN preclin.target_disease_source.abstract IS 'Abstract as the service gives it; null when the record has none.';
COMMENT ON COLUMN preclin.target_disease_source.year IS 'Publication year the service reports. Always before the pair''s cutoff_year: a record without a year, or dated in or after it, is not stored.';
COMMENT ON COLUMN preclin.target_disease_source.doi IS 'DOI when the service gives one.';
COMMENT ON COLUMN preclin.target_disease_source.rank IS 'Order within the pair by (year, record_id), 1 first; what "earliest" and "latest" mean for the bundle.';

ALTER TABLE preclin.target_disease_origin
    ADD COLUMN IF NOT EXISTS check_outcome text
        CHECK (check_outcome IN ('supported', 'unsupported', 'unverified', 'not_checked')),
    ADD COLUMN IF NOT EXISTS check_decision_id bigint REFERENCES pv_evidence.llm_decision,
    ADD COLUMN IF NOT EXISTS discovery_route text
        CHECK (discovery_route IN ('phenotypic_screen', 'target_screen', 'de_novo_design', 'derived_from_active',
                                   'repurposed_drug', 'unclear')),
    ADD COLUMN IF NOT EXISTS route_quote text,
    ADD COLUMN IF NOT EXISTS route_sources text[] NOT NULL DEFAULT '{}';
ALTER TABLE preclin.target_disease_origin
    ADD CONSTRAINT target_disease_origin_route_labelled_check
        CHECK ((basis = 'labelled') = (discovery_route IS NOT NULL));
COMMENT ON COLUMN preclin.target_disease_origin.check_outcome IS
    'Labelled rows: the second model''s check of the label (pipeline.target_disease check). supported: it found the quote in the cited source and the source''s date before the cutoff, and the origin follows; unsupported: the quote is absent, the date is on or after the cutoff, or the origin does not follow; unverified: it could not open or date a web source and nothing else failed; not_checked: an unclear label, or not yet checked. An unsupported or unverified row is rewritten as unclear (grade none); its original label stays in llm_decision_id''s decision. Null for provisional rows.';
COMMENT ON COLUMN preclin.target_disease_origin.check_decision_id IS 'The check decision behind check_outcome; null when not checked.';
COMMENT ON COLUMN preclin.target_disease_origin.discovery_route IS
    'Labelled rows, descriptive only: where the pair''s first drug came from, read from the same pre-entry sources. phenotypic_screen: a screen in cells or animals with no target hypothesis; target_screen: a high-throughput, fragment or virtual screen against the target, or immunization or display for a biologic; de_novo_design: designed from the sequence or structure (antisense, siRNA, structure-based design); derived_from_active: derived from an existing active (a known drug, an endogenous ligand, a natural product); repurposed_drug: an existing drug tried in this disease; unclear: no source settles it. Null for provisional rows.';
COMMENT ON COLUMN preclin.target_disease_origin.route_quote IS 'Verbatim text behind discovery_route; null when unclear.';
COMMENT ON COLUMN preclin.target_disease_origin.route_sources IS 'Sources behind discovery_route, under the same rule as sources; empty when unclear.';
COMMIT;
