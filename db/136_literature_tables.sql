-- One set of literature evidence tables (pipeline.literature). The tables of the first two versions (migrations
-- 119, 120) are dropped: their pilot gate results are archived in report/audits/literature_gate.json and .md, and
-- no code reads them. The current version's tables (migration 123) take the canonical names, and every table and
-- column carries a comment.

BEGIN;
SET LOCAL lock_timeout = '3s';

DROP TABLE preclin.literature_hit, preclin.literature_screen, preclin.literature_search;
DROP TABLE preclin.literature_drug_hit, preclin.literature_drug_screen, preclin.literature_drug_search;

ALTER TABLE preclin.literature_v3_search RENAME TO literature_search;
ALTER TABLE preclin.literature_v3_firecrawl RENAME TO literature_firecrawl;
ALTER TABLE preclin.literature_v3_hit RENAME TO literature_hit;
ALTER TABLE preclin.literature_v3_prefilter RENAME TO literature_prefilter;
ALTER TABLE preclin.literature_v3_screen RENAME TO literature_screen;
ALTER INDEX preclin.literature_v3_search_pkey RENAME TO literature_search_pkey;
ALTER INDEX preclin.literature_v3_firecrawl_pkey RENAME TO literature_firecrawl_pkey;
ALTER INDEX preclin.literature_v3_hit_pkey RENAME TO literature_hit_pkey;
ALTER INDEX preclin.literature_v3_prefilter_pkey RENAME TO literature_prefilter_pkey;
ALTER INDEX preclin.literature_v3_screen_pkey RENAME TO literature_screen_pkey;
ALTER TABLE preclin.literature_search RENAME CONSTRAINT literature_v3_search_moiety_id_fkey TO literature_search_moiety_id_fkey;
ALTER TABLE preclin.literature_search RENAME CONSTRAINT literature_v3_search_source_check TO literature_search_source_check;
ALTER TABLE preclin.literature_firecrawl RENAME CONSTRAINT literature_v3_firecrawl_moiety_id_fkey TO literature_firecrawl_moiety_id_fkey;
ALTER TABLE preclin.literature_firecrawl RENAME CONSTRAINT literature_v3_firecrawl_mode_check TO literature_firecrawl_mode_check;
ALTER TABLE preclin.literature_hit RENAME CONSTRAINT literature_v3_hit_moiety_id_fkey TO literature_hit_moiety_id_fkey;
ALTER TABLE preclin.literature_hit RENAME CONSTRAINT literature_v3_hit_source_check TO literature_hit_source_check;
ALTER TABLE preclin.literature_prefilter RENAME CONSTRAINT literature_v3_prefilter_moiety_id_fkey TO literature_prefilter_moiety_id_fkey;
ALTER TABLE preclin.literature_prefilter RENAME CONSTRAINT literature_v3_prefilter_llm_decision_id_fkey TO literature_prefilter_llm_decision_id_fkey;
ALTER TABLE preclin.literature_screen RENAME CONSTRAINT literature_v3_screen_moiety_id_fkey TO literature_screen_moiety_id_fkey;
ALTER TABLE preclin.literature_screen RENAME CONSTRAINT literature_v3_screen_llm_decision_id_fkey TO literature_screen_llm_decision_id_fkey;

COMMENT ON TABLE preclin.literature_record IS
    'Abstracts outside MEDLINE that a literature search retrieved from Europe PMC or Firecrawl''s research index (preprints, patents, theses, Agricola and other sources), keyed "<Europe PMC source>:<id>". PubMed abstracts are in public.publications.';
COMMENT ON COLUMN preclin.literature_record.record_id IS 'Europe PMC source and id, e.g. PPR:PPR123456 or PAT:WO2010033993.';
COMMENT ON COLUMN preclin.literature_record.source IS 'Europe PMC source code: PPR preprint, PAT patent, AGR Agricola, ETH thesis, and others.';
COMMENT ON COLUMN preclin.literature_record.title IS 'Title as Europe PMC gives it.';
COMMENT ON COLUMN preclin.literature_record.abstract IS 'Abstract as Europe PMC gives it.';
COMMENT ON COLUMN preclin.literature_record.year IS 'Publication year; an entry counts the record only when this is no later than its cutoff year.';
COMMENT ON COLUMN preclin.literature_record.doi IS 'DOI, used to match reference studies outside PubMed.';

COMMENT ON TABLE preclin.literature_search IS
    'Each search of a drug by its names alone (INN, code names, ChEMBL and PubChem synonyms, FDA substance-registry names), up to the latest cutoff of its entries, reviews excluded: PubMed titles and abstracts, every hit kept, and Europe PMC titles and abstracts outside MEDLINE that have an abstract.';
COMMENT ON COLUMN preclin.literature_search.moiety_id IS 'The drug (molecular entity) searched.';
COMMENT ON COLUMN preclin.literature_search.cutoff_year IS 'Last publication year searched: the year before the drug''s latest phase entry in the entry set.';
COMMENT ON COLUMN preclin.literature_search.source IS 'pubmed or europepmc.';
COMMENT ON COLUMN preclin.literature_search.names IS 'The names searched, in the order pipeline.literature.drug_names keeps them.';
COMMENT ON COLUMN preclin.literature_search.query IS 'The query sent (PubMed esearch term or Europe PMC query); a PubMed set over 9,999 is fetched in date slices of this query.';
COMMENT ON COLUMN preclin.literature_search.n_hits IS 'Number of records the source reported for the query.';
COMMENT ON COLUMN preclin.literature_search.searched_at IS 'When the search ran.';

COMMENT ON TABLE preclin.literature_firecrawl IS
    'Each call to Firecrawl''s research index: a semantic search for one entry (the drug''s names, its disease and the three kinds of evidence, papers up to the cutoff year) or a citation-graph expansion (related papers, mode similar) from one qualifying record of the drug, its results kept up to the cutoff year.';
COMMENT ON COLUMN preclin.literature_firecrawl.moiety_id IS 'The drug.';
COMMENT ON COLUMN preclin.literature_firecrawl.mondo_id IS 'The entry''s disease for a search; empty for a related-papers expansion, which is per drug.';
COMMENT ON COLUMN preclin.literature_firecrawl.cutoff_year IS 'Last publication year kept.';
COMMENT ON COLUMN preclin.literature_firecrawl.mode IS 'search (search-papers) or related (related-papers, mode similar).';
COMMENT ON COLUMN preclin.literature_firecrawl.query IS 'The natural-language query, or the seed record and intent of an expansion.';
COMMENT ON COLUMN preclin.literature_firecrawl.n_results IS 'Results the call returned, before the cutoff filter.';
COMMENT ON COLUMN preclin.literature_firecrawl.searched_at IS 'When the call ran.';

COMMENT ON TABLE preclin.literature_hit IS
    'Every record a literature retrieval returned for a drug, by source. A record returned by several sources has a row for each.';
COMMENT ON COLUMN preclin.literature_hit.moiety_id IS 'The drug.';
COMMENT ON COLUMN preclin.literature_hit.cutoff_year IS 'The latest cutoff of the drug''s entries; each entry filters its records by its own cutoff.';
COMMENT ON COLUMN preclin.literature_hit.source IS 'pubmed, europepmc or firecrawl.';
COMMENT ON COLUMN preclin.literature_hit.record_id IS 'A PMID (public.publications) or a preclin.literature_record id.';

COMMENT ON TABLE preclin.literature_prefilter IS
    'For a drug with more than PREFILTER_ABOVE retrieved records, a first reading of each by a cheaper model: whether it possibly reports original data on the drug of any of the three kinds. Only records read as possibly reach preclin.literature_screen.';
COMMENT ON COLUMN preclin.literature_prefilter.moiety_id IS 'The drug.';
COMMENT ON COLUMN preclin.literature_prefilter.record_id IS 'A PMID or a preclin.literature_record id.';
COMMENT ON COLUMN preclin.literature_prefilter.possibly IS 'True unless the record clearly reports none of the three kinds about this drug.';
COMMENT ON COLUMN preclin.literature_prefilter.llm_decision_id IS 'The decision (task literature_prefilter).';

COMMENT ON TABLE preclin.literature_screen IS
    'An LLM''s reading of one record about one drug (task literature_drug_screen): whether it reports original data on the drug, tests it for efficacy in an animal model of a disease, reports its pharmacology in healthy animals, or measures its target engagement in people.';
COMMENT ON COLUMN preclin.literature_screen.moiety_id IS 'The drug.';
COMMENT ON COLUMN preclin.literature_screen.record_id IS 'A PMID or a preclin.literature_record id.';
COMMENT ON COLUMN preclin.literature_screen.original_data IS 'The record reports new experimental or clinical results involving the drug.';
COMMENT ON COLUMN preclin.literature_screen.animal_disease IS 'The drug was tested for efficacy in vivo in animals that model a human disease.';
COMMENT ON COLUMN preclin.literature_screen.modelled_diseases IS 'The human diseases the animal models stand for, as named; mapped in preclin.literature_model_disease. Empty unless animal_disease.';
COMMENT ON COLUMN preclin.literature_screen.animal_healthy IS 'The drug''s pharmacokinetics, distribution, metabolism or pharmacodynamics was measured in animals that model no disease.';
COMMENT ON COLUMN preclin.literature_screen.human_engagement IS 'Target engagement or a pharmacodynamic biomarker of the drug''s mechanism was measured in people.';
COMMENT ON COLUMN preclin.literature_screen.species IS 'Species of the deciding study.';
COMMENT ON COLUMN preclin.literature_screen.detail IS 'What was measured, in a few words.';
COMMENT ON COLUMN preclin.literature_screen.quote IS 'The sentence that decides it, copied from the abstract.';
COMMENT ON COLUMN preclin.literature_screen.llm_decision_id IS 'The decision (task literature_drug_screen).';

COMMENT ON COLUMN preclin.literature_model_disease.modelled_disease IS 'A disease an animal model was said to model, as preclin.literature_screen names it.';
COMMENT ON COLUMN preclin.literature_model_disease.mondo_id IS 'The MONDO term chosen; null when match is none.';
COMMENT ON COLUMN preclin.literature_model_disease.match IS 'exact (a term names the disease), broader (the narrowest term containing it) or none.';
COMMENT ON COLUMN preclin.literature_model_disease.llm_decision_id IS 'The decision (task literature_model_disease_mondo).';

COMMIT;
