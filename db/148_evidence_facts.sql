-- The evidence dataset in the structure of the shared list of evidence kinds (PR #159, 2026-11-20): broad categories
-- by experimental system, kinds of evidence, and the facts each kind is made of. Each entry's answer to each fact replaces its value on each evidence
-- line; every line the report estimates is derived from the facts (report.evidence_lines.derive), and
-- preclin.evidence_entry_kind derives whether each entry has each kind. Stored by `python -m report.evidence_lines
-- store`, which replaces every table but evidence_line_build at once.

BEGIN;
SET LOCAL lock_timeout = '3s';

DROP TABLE preclin.evidence_entry_line;
DROP TABLE preclin.evidence_line;

ALTER TABLE preclin.evidence_entry
    ADD COLUMN drug_action text CHECK (drug_action IN ('decreases', 'increases', 'other'));
COMMENT ON COLUMN preclin.evidence_entry.drug_action IS
    'What the entity does to its primary targets: decreases or increases their function, or other (ambiguous, depleting, or targets acted on differently); null without a resolved human protein target. Crossed with the direction facts to derive whether evidence agrees with the drug.';

CREATE TABLE preclin.evidence_kind (
    kind_key   text PRIMARY KEY,
    position   integer NOT NULL,
    category   text NOT NULL CHECK (category IN ('human_genetics', 'in_vitro', 'animals', 'human', 'the_drug',
                                                 'safety')),
    about      text NOT NULL CHECK (about IN ('target', 'drug')),
    label      text NOT NULL,
    definition text NOT NULL,
    source     text NOT NULL,
    planned    boolean NOT NULL,
    drawn      boolean NOT NULL,
    build_id   uuid NOT NULL REFERENCES preclin.evidence_line_build (build_id)
);
COMMENT ON TABLE preclin.evidence_kind IS
    'The kinds of evidence of the shared list (PR #159; report.evidence_lines.KINDS), the single grouping of the report''s chart, appendix and the target-origin label.';
COMMENT ON COLUMN preclin.evidence_kind.kind_key IS 'The kind''s key, as the shared list names it.';
COMMENT ON COLUMN preclin.evidence_kind.position IS 'Display order: broad categories in the chart''s order, kinds within each.';
COMMENT ON COLUMN preclin.evidence_kind.category IS
    'The broad category by the experimental system that produced the evidence: human_genetics, in_vitro (primary cells or tissue, and established cell lines), animals, human (patients, their tissue, and earlier drugs on the target in people), the_drug, or safety (target safety risk).';
COMMENT ON COLUMN preclin.evidence_kind.about IS
    'Whether the kind is evidence about the target (that it is right for the disease, or its safety) or about the drug.';
COMMENT ON COLUMN preclin.evidence_kind.label IS 'Plain-English label as the report shows it.';
COMMENT ON COLUMN preclin.evidence_kind.definition IS 'What counts as this kind of evidence.';
COMMENT ON COLUMN preclin.evidence_kind.source IS 'Where the evidence comes from and how it is dated.';
COMMENT ON COLUMN preclin.evidence_kind.planned IS 'The kind is on the list but has no facts yet (issue #154).';
COMMENT ON COLUMN preclin.evidence_kind.drawn IS
    'The report''s evidence chart draws the kind; molecule properties are stored but not drawn.';
COMMENT ON COLUMN preclin.evidence_kind.build_id IS 'The store that wrote the row (preclin.evidence_line_build).';

CREATE TABLE preclin.evidence_fact (
    fact_key       text PRIMARY KEY,
    position       integer NOT NULL,
    label          text NOT NULL,
    applies        text NOT NULL,
    fact_values    text[] NOT NULL,
    value_labels   text[] NOT NULL,
    unknown_values text[] NOT NULL,
    numeric        boolean NOT NULL,
    counts         boolean NOT NULL,
    hindsight      boolean NOT NULL,
    note           text NOT NULL,
    build_id       uuid NOT NULL REFERENCES preclin.evidence_line_build (build_id),
    CHECK (cardinality(fact_values) = cardinality(value_labels)),
    CHECK (numeric = (cardinality(fact_values) = 0))
);
COMMENT ON TABLE preclin.evidence_fact IS
    'The questions the kinds of evidence are made of (report.evidence_lines.FACTS). Each is answered by exactly one of its values on every entry it applies to, frozen at the year before entry; a measurement is answered by a number.';
COMMENT ON COLUMN preclin.evidence_fact.fact_key IS 'The fact''s key.';
COMMENT ON COLUMN preclin.evidence_fact.position IS 'Display order.';
COMMENT ON COLUMN preclin.evidence_fact.label IS 'The question, in plain English.';
COMMENT ON COLUMN preclin.evidence_fact.applies IS
    'The entries the fact is answered for (report.evidence_lines.APPLIES): all, target (a single resolved human protein target and a disease), ONC, onc_screened (oncology entries from 2015), small_molecule, brain (small molecules for neurology and psychiatry) or phase_2_3.';
COMMENT ON COLUMN preclin.evidence_fact.fact_values IS
    'The values that answer the fact, mutually exclusive and covering every entry it applies to, in display order; empty for a measurement.';
COMMENT ON COLUMN preclin.evidence_fact.value_labels IS 'Plain-English label of each value, in the order of fact_values.';
COMMENT ON COLUMN preclin.evidence_fact.unknown_values IS
    'Values that leave the entry unknown on the fact (not measured, not searched, not scored) rather than without the evidence.';
COMMENT ON COLUMN preclin.evidence_fact.numeric IS 'A raw measurement, answered in evidence_entry_fact.value_num.';
COMMENT ON COLUMN preclin.evidence_fact.counts IS
    'The fact makes up its kind; false for hindsight facts, exploratory safety facts and measurements.';
COMMENT ON COLUMN preclin.evidence_fact.hindsight IS 'Scored on today''s data, not as of entry.';
COMMENT ON COLUMN preclin.evidence_fact.note IS 'Caveat the report prints with the fact; empty when none.';
COMMENT ON COLUMN preclin.evidence_fact.build_id IS 'The store that wrote the row (preclin.evidence_line_build).';

CREATE TABLE preclin.evidence_kind_fact (
    kind_key        text NOT NULL REFERENCES preclin.evidence_kind (kind_key),
    fact_key        text NOT NULL REFERENCES preclin.evidence_fact (fact_key),
    evidence_values text[] NOT NULL,
    build_id        uuid NOT NULL REFERENCES preclin.evidence_line_build (build_id),
    PRIMARY KEY (kind_key, fact_key)
);
COMMENT ON TABLE preclin.evidence_kind_fact IS
    'Which facts each kind of evidence is made of. One fact can serve two kinds (best_approval: validated at entry, and a drug approved for another disease).';
COMMENT ON COLUMN preclin.evidence_kind_fact.kind_key IS 'The kind (preclin.evidence_kind).';
COMMENT ON COLUMN preclin.evidence_kind_fact.fact_key IS 'The fact (preclin.evidence_fact).';
COMMENT ON COLUMN preclin.evidence_kind_fact.evidence_values IS
    'The fact''s values that count as this kind''s evidence; empty for a fact that describes the kind (such as a direction) without being evidence of it.';
COMMENT ON COLUMN preclin.evidence_kind_fact.build_id IS 'The store that wrote the row (preclin.evidence_line_build).';

CREATE TABLE preclin.evidence_entry_fact (
    moiety_id integer NOT NULL,
    mondo_id  text NOT NULL,
    phase     integer NOT NULL,
    fact_key  text NOT NULL REFERENCES preclin.evidence_fact (fact_key),
    value     text,
    value_num double precision,
    PRIMARY KEY (moiety_id, mondo_id, phase, fact_key),
    FOREIGN KEY (moiety_id, mondo_id, phase) REFERENCES preclin.evidence_entry,
    CHECK ((value IS NULL) <> (value_num IS NULL))
);
CREATE INDEX evidence_entry_fact_fact_idx ON preclin.evidence_entry_fact (fact_key, value);
COMMENT ON TABLE preclin.evidence_entry_fact IS
    'Each entry''s answer to each fact it applies to, frozen at the year before entry. A missing row means the fact does not apply to the entry.';
COMMENT ON COLUMN preclin.evidence_entry_fact.moiety_id IS 'The entry''s entity.';
COMMENT ON COLUMN preclin.evidence_entry_fact.mondo_id IS 'The entry''s program disease; empty for a disease-unspecified program.';
COMMENT ON COLUMN preclin.evidence_entry_fact.phase IS 'The entry''s phase.';
COMMENT ON COLUMN preclin.evidence_entry_fact.fact_key IS 'The fact (preclin.evidence_fact).';
COMMENT ON COLUMN preclin.evidence_entry_fact.value IS 'One of the fact''s values; null for a measurement.';
COMMENT ON COLUMN preclin.evidence_entry_fact.value_num IS 'The measurement; null for a categorical fact.';

CREATE VIEW preclin.evidence_entry_kind AS
SELECT a.moiety_id, a.mondo_id, a.phase, kf.kind_key,
       CASE WHEN bool_or(a.value = ANY (kf.evidence_values)) THEN true
            WHEN bool_and(a.value = ANY (f.unknown_values)) THEN NULL
            ELSE false END AS has_evidence
FROM preclin.evidence_entry_fact a
JOIN preclin.evidence_fact f USING (fact_key)
JOIN preclin.evidence_kind_fact kf USING (fact_key)
WHERE f.counts AND cardinality(kf.evidence_values) > 0
GROUP BY a.moiety_id, a.mondo_id, a.phase, kf.kind_key;
COMMENT ON VIEW preclin.evidence_entry_kind IS
    'Whether each entry has each kind of evidence: true when any fact that makes up the kind takes one of the kind''s evidence values, null when every such fact is unknown for the entry, else false. An entry no such fact applies to has no row.';

-- The shared list merged the cell-screen kind into cell-line perturbation (PR #159, amendment 3): the provisional
-- origins that named it take the merged kind's name.
ALTER TABLE preclin.target_disease_origin DROP CONSTRAINT target_disease_origin_origin_check;
UPDATE preclin.target_disease_origin SET origin = 'cell_line_perturbation' WHERE origin = 'cell_screen';
UPDATE preclin.target_disease_origin SET secondary_origin = 'cell_line_perturbation'
WHERE secondary_origin = 'cell_screen';
ALTER TABLE preclin.target_disease_origin ADD CONSTRAINT target_disease_origin_origin_check
    CHECK (origin IN ('human_genetics', 'tumour_genetics', 'diseased_tissue', 'mouse_genetics', 'curated_pathway',
                      'cell_line_perturbation', 'earlier_drug_other_disease', 'observational_biomarker',
                      'human_cell_perturbation', 'animal_model_pharmacology', 'clinical_observation',
                      'phenotypic_screen', 'unclear'));

COMMENT ON TABLE preclin.evidence_line_build IS
    'Each store of the evidence dataset (report.evidence_lines store): the programs snapshot it was built from, the code commit and a fingerprint of its inputs. The other evidence tables hold the latest build only.';

COMMIT;
