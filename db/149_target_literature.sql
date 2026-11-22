-- The target-biology literature of issue #154 (pipeline.target_literature): for each target-disease pair, the
-- searches run, every record they returned, the cheap prefilter of large literatures and the screen of each record
-- for the seven kinds of evidence. Records carry their publication year, so each phase entry counts only what was
-- published by the year before it entered.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.target_literature_search (
    ensembl_id  text NOT NULL,
    mondo_id    text NOT NULL,
    cutoff_year integer NOT NULL,
    source      text NOT NULL CHECK (source IN ('pubmed', 'europepmc', 'firecrawl', 'firecrawl_related')),
    kind        text NOT NULL DEFAULT '',
    names       jsonb NOT NULL,
    query       text NOT NULL,
    n_hits      integer NOT NULL,
    searched_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (ensembl_id, mondo_id, cutoff_year, source, kind),
    FOREIGN KEY (ensembl_id, mondo_id) REFERENCES preclin.target_disease (ensembl_id, mondo_id)
);
COMMENT ON TABLE preclin.target_literature_search IS
    'Each search for the target-biology literature of one target-disease pair (pipeline.target_literature search, issue #154): PubMed and Europe PMC by the vetted gene names and the disease names and experimental-model terms, and Firecrawl''s research index once per pair and kind plus a related-paper expansion. Re-searching a pair at the same cutoff replaces its rows.';
COMMENT ON COLUMN preclin.target_literature_search.ensembl_id IS 'The pair''s gene (preclin.target_disease).';
COMMENT ON COLUMN preclin.target_literature_search.mondo_id IS 'The pair''s disease (preclin.target_disease).';
COMMENT ON COLUMN preclin.target_literature_search.cutoff_year IS
    'Last publication year searched: the year before the latest 2008-2019 phase entry of a program on the pair.';
COMMENT ON COLUMN preclin.target_literature_search.source IS
    'pubmed, europepmc (records outside MEDLINE), firecrawl (one semantic search per kind) or firecrawl_related (papers related to the pair''s first screened-in record).';
COMMENT ON COLUMN preclin.target_literature_search.kind IS 'For a firecrawl search, the kind of evidence it asked for; empty otherwise.';
COMMENT ON COLUMN preclin.target_literature_search.names IS
    'The names searched: {"gene": [...], "disease": [...], "models": [...]}.';
COMMENT ON COLUMN preclin.target_literature_search.query IS 'The query as sent.';
COMMENT ON COLUMN preclin.target_literature_search.n_hits IS 'Records the service reported for the query.';
COMMENT ON COLUMN preclin.target_literature_search.searched_at IS 'When the search ran.';

CREATE TABLE preclin.target_literature_hit (
    ensembl_id  text NOT NULL,
    mondo_id    text NOT NULL,
    cutoff_year integer NOT NULL,
    source      text NOT NULL,
    record_id   text NOT NULL,
    PRIMARY KEY (ensembl_id, mondo_id, cutoff_year, source, record_id),
    FOREIGN KEY (ensembl_id, mondo_id) REFERENCES preclin.target_disease (ensembl_id, mondo_id)
);
CREATE INDEX target_literature_hit_record_idx ON preclin.target_literature_hit (record_id);
COMMENT ON TABLE preclin.target_literature_hit IS
    'Every record a target-literature search returned for a pair, by source. A record several sources returned has a row for each. PubMed records are read from public.publications, others from preclin.literature_record.';
COMMENT ON COLUMN preclin.target_literature_hit.ensembl_id IS 'The pair''s gene.';
COMMENT ON COLUMN preclin.target_literature_hit.mondo_id IS 'The pair''s disease.';
COMMENT ON COLUMN preclin.target_literature_hit.cutoff_year IS 'The search''s cutoff year (preclin.target_literature_search).';
COMMENT ON COLUMN preclin.target_literature_hit.source IS 'The source that returned it, as in preclin.target_literature_search.';
COMMENT ON COLUMN preclin.target_literature_hit.record_id IS 'A PMID, or a Europe PMC record id (SOURCE:ID) for a record outside PubMed.';

CREATE TABLE preclin.target_literature_prefilter (
    ensembl_id      text NOT NULL,
    mondo_id        text NOT NULL,
    record_id       text NOT NULL,
    possibly        boolean NOT NULL,
    llm_decision_id bigint NOT NULL,
    PRIMARY KEY (ensembl_id, mondo_id, record_id),
    FOREIGN KEY (ensembl_id, mondo_id) REFERENCES preclin.target_disease (ensembl_id, mondo_id)
);
COMMENT ON TABLE preclin.target_literature_prefilter IS
    'For a pair with more records than the prefilter threshold, a cheap model''s first reading of each record: whether it possibly reports original data on the gene in the disease of any of the seven kinds. Only records read as possibly are screened.';
COMMENT ON COLUMN preclin.target_literature_prefilter.ensembl_id IS 'The pair''s gene.';
COMMENT ON COLUMN preclin.target_literature_prefilter.mondo_id IS 'The pair''s disease.';
COMMENT ON COLUMN preclin.target_literature_prefilter.record_id IS 'The record read.';
COMMENT ON COLUMN preclin.target_literature_prefilter.possibly IS 'False only when the record clearly reports none of the kinds for this gene and disease.';
COMMENT ON COLUMN preclin.target_literature_prefilter.llm_decision_id IS 'The decision (pv_evidence.llm_decision, task target_literature_prefilter).';

CREATE TABLE preclin.target_literature_screen (
    ensembl_id                    text NOT NULL,
    mondo_id                      text NOT NULL,
    record_id                     text NOT NULL,
    original_data                 boolean NOT NULL,
    disease_match                 text NOT NULL CHECK (disease_match IN ('same_or_subtype', 'related', 'other', 'none')),
    human_cell_perturbation       boolean NOT NULL,
    cell_line_perturbation        boolean NOT NULL,
    diseased_tissue_protein       boolean NOT NULL,
    animal_model_pharmacology     boolean NOT NULL,
    agent_is_program_drug         boolean,
    mouse_genetic_disease_model   boolean NOT NULL,
    observational_biomarker       boolean NOT NULL,
    clinical_observation          boolean NOT NULL,
    quote                         text,
    llm_decision_id               bigint NOT NULL,
    PRIMARY KEY (ensembl_id, mondo_id, record_id),
    FOREIGN KEY (ensembl_id, mondo_id) REFERENCES preclin.target_disease (ensembl_id, mondo_id)
);
COMMENT ON TABLE preclin.target_literature_screen IS
    'An LLM''s reading of one record for one target-disease pair (task target_literature_screen, issue #154): whether it reports original data, whether its disease is the pair''s, and which of the seven kinds of target evidence it shows for the gene. A record counts for a phase entry when it is original data, its disease is the same or a subtype, it shows the kind, and it was published by the year before entry.';
COMMENT ON COLUMN preclin.target_literature_screen.ensembl_id IS 'The pair''s gene.';
COMMENT ON COLUMN preclin.target_literature_screen.mondo_id IS 'The pair''s disease.';
COMMENT ON COLUMN preclin.target_literature_screen.record_id IS 'The record read.';
COMMENT ON COLUMN preclin.target_literature_screen.original_data IS 'The record reports new experimental or clinical results (not a review, commentary or protocol).';
COMMENT ON COLUMN preclin.target_literature_screen.disease_match IS
    'same_or_subtype (the pair''s disease, a subtype or a disease near-identical to it, which counts), related (a related but distinct disease), other, or none (no disease studied).';
COMMENT ON COLUMN preclin.target_literature_screen.human_cell_perturbation IS 'Kind 8: changing the target in primary human cells or tissue (patient-derived cells, organoids, iPSC-derived cells, tissue from patients) changes a disease feature.';
COMMENT ON COLUMN preclin.target_literature_screen.cell_line_perturbation IS 'The same in an established cell line (the literature part of cell-line perturbation).';
COMMENT ON COLUMN preclin.target_literature_screen.diseased_tissue_protein IS 'Kind 6, protein tier: the target''s protein level, activity, location, modification or single-cell state differs in patients'' diseased tissue (bulk RNA does not count).';
COMMENT ON COLUMN preclin.target_literature_screen.animal_model_pharmacology IS 'Kind 9: a non-genetic change to the target (tool compound, antibody, antisense, siRNA, vector or a drug) alters an animal model of the disease.';
COMMENT ON COLUMN preclin.target_literature_screen.agent_is_program_drug IS
    'For animal_model_pharmacology: true when the only agent is a drug of one of the pair''s programs, false when another agent was used; null otherwise. The registered L2 counts only false.';
COMMENT ON COLUMN preclin.target_literature_screen.mouse_genetic_disease_model IS 'Kind 4, disease-model tier: a knockout, knock-in or transgene of the target alters an animal model of the disease.';
COMMENT ON COLUMN preclin.target_literature_screen.observational_biomarker IS 'Kind 7: the target or its product, measured in blood, another fluid or by imaging, tracks the disease''s presence, severity, progression or outcome in an observational study (genetic association does not count).';
COMMENT ON COLUMN preclin.target_literature_screen.clinical_observation IS 'Kind 10: an effect seen in people that implicates the target in the disease, such as a side effect of another drug acting on the target.';
COMMENT ON COLUMN preclin.target_literature_screen.quote IS 'The sentence that decided the reading.';
COMMENT ON COLUMN preclin.target_literature_screen.llm_decision_id IS 'The decision (pv_evidence.llm_decision, task target_literature_screen).';

COMMIT;
