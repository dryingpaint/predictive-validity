-- Pinned ontology releases used to place indications and genetic traits
-- (pipeline.ontology): terms, is_a edges, transitive ancestors with is_a
-- distance, and cross-references. One set of tables holds every ontology.

BEGIN;

CREATE TABLE IF NOT EXISTS preclin.ontology_term (
    term_id           text PRIMARY KEY,
    ontology          text NOT NULL,
    label             text NOT NULL,
    definition        text,
    synonyms          text[] NOT NULL DEFAULT '{}',
    is_obsolete       boolean NOT NULL,
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release
);

CREATE TABLE IF NOT EXISTS preclin.ontology_is_a (
    ontology  text NOT NULL,
    child_id  text NOT NULL,
    parent_id text NOT NULL,
    PRIMARY KEY (child_id, parent_id)
);

CREATE TABLE IF NOT EXISTS preclin.ontology_ancestor (
    ontology    text NOT NULL,
    term_id     text NOT NULL,
    ancestor_id text NOT NULL,
    distance    integer NOT NULL CHECK (distance > 0),
    PRIMARY KEY (term_id, ancestor_id)
);
CREATE INDEX IF NOT EXISTS ontology_ancestor_anc_idx ON preclin.ontology_ancestor (ancestor_id);

CREATE TABLE IF NOT EXISTS preclin.ontology_xref (
    ontology text NOT NULL,
    term_id  text NOT NULL,
    xref_id  text NOT NULL,
    PRIMARY KEY (term_id, xref_id)
);
CREATE INDEX IF NOT EXISTS ontology_xref_xref_idx ON preclin.ontology_xref (xref_id);

COMMIT;
