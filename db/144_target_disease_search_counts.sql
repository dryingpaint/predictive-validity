-- The origin search (pipeline.target_disease search, #146) stores a second PubMed hit count without the gene symbol,
-- so a symbol that is also an English word (AR, KIT, SET) shows as a flood; and two column comments of migration 143
-- are corrected: gene names now include the UniProt and HGNC protein names, and n_hits is the stored count's source,
-- not a flood signal.

BEGIN;
SET LOCAL lock_timeout = '3s';

ALTER TABLE preclin.target_disease_search ADD COLUMN IF NOT EXISTS n_hits_without_symbol integer;
COMMENT ON COLUMN preclin.target_disease_search.n_hits_without_symbol IS
    'PubMed rows only: the hit count of the same query with the gene symbol left out of the gene names. Null when the symbol was not searched (a symbol of three characters or fewer is searched only when no other name exists) or when it was the only name. A count far below n_hits shows the symbol flooding the search.';
COMMENT ON COLUMN preclin.target_disease_search.gene_names IS
    'Names searched for the gene: the HGNC symbol (only when four characters or longer, or the only name), then the HGNC name, the target name and the protein names from UniProt and HGNC that pass pipeline.target_origin.name_usable, then previous and alias symbols that pass pipeline.literature.usable; at most 16.';
COMMENT ON COLUMN preclin.target_disease_search.n_hits IS
    'Hit count the service reported for the query, before any record was dropped for a missing or late year. Compare with n_hits_without_symbol for a flooded symbol.';
COMMIT;
