-- Every PubMed search pipeline.attribution literature ran, with its hit count, so a search that found nothing is
-- not repeated. preclin.moiety_publication holds only the hits.

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE IF NOT EXISTS preclin.pubmed_search (
    moiety_id   integer NOT NULL REFERENCES preclin.moiety,
    mondo_id    text NOT NULL,
    query_kind  text NOT NULL,
    query       text NOT NULL,
    n_hits      integer NOT NULL,
    searched_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (moiety_id, mondo_id, query_kind)
);
COMMENT ON TABLE preclin.pubmed_search IS
    'The latest PubMed search per entity, program disease (empty for a pharmacology search) and kind, as run by pipeline.attribution literature, with how many results it kept.';
INSERT INTO preclin.pubmed_search (moiety_id, mondo_id, query_kind, query, n_hits)
SELECT moiety_id, mondo_id, query_kind, min(query), count(*) FROM preclin.moiety_publication
GROUP BY 1, 2, 3
ON CONFLICT DO NOTHING;
COMMIT;
