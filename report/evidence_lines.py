"""The evidence dataset: every phase entry's answer to each evidence fact, in the structure of the shared list of
evidence kinds (PR #159, 2026-11-20).

    python -m report.evidence_lines                    # write the CSVs
    python -m report.evidence_lines store              # also replace the dataset in Postgres
    python -m report.evidence_lines store --rollback   # run the store's inserts and roll them back
    python -m report.evidence_lines check              # exit 1, naming what changed, when the stored dataset is stale

One row per US-developed phase entry in 2008-2019 (report.section1.phase_rows with a US-sited industry trial in the
phase, skipped phases excluded), keyed by (moiety_id, mondo_id, phase) and carrying the program_id of the current
program build for joins within one run.

The structure has three levels. CATEGORIES: broad categories by the experimental system that produced the evidence
(human genetics, in vitro, animals, human, the drug, target safety risk).
KINDS: the kinds of evidence of the shared list, each in one category and tagged as evidence about the target or the
drug. A disease-specific kind (tumour genetics, cell screen) is compared only within its scope. FACTS: the questions a kind is made of,
each answered by exactly one of its values on every entry it applies to (FACTS[...].applies), frozen at the year
before entry. Only the facts are stored; every line the report estimates is derived from them (derive): a 0/1 column
per evidence value, each kind's any-of column, and aggregates and crosses with the drug's action, such as genetics
agreeing with the drug's direction. Target-level facts come from report.section3.Evidence and do not apply to entries
without a single resolved human protein target and a disease; molecule facts from ChEMBL potency measurements
(report.frame.assays_as_of) and computed properties (preclin.moiety_property) apply to small molecules only.

Writes report/output/evidence_lines/: entries.csv (facts as fact_<key>, and every derived line), and coverage.csv
with each fact value's entries and each line's eligible and exposed entries. No line is compared with an outcome here.

`store` writes the structure (preclin.evidence_kind, evidence_fact, evidence_kind_fact), one row per entry
(preclin.evidence_entry, without outcomes) and every answer (preclin.evidence_entry_fact), recorded in
preclin.evidence_line_build with a fingerprint of its inputs (input_fingerprint), which `check` compares with the
inputs now. Report modules otherwise only read; this one writes because the compiled dataset is what other sessions
and analyses query, and it should not have to be rebuilt from code to be read.
"""
from __future__ import annotations

import os
import sys
import uuid
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd
from psycopg2.extras import Json, execute_values

from pipeline import literature, llm
from report import frame
from report.section3 import ERA_BINS, ERA_LABELS, RELATED, Evidence, cohorts, entries

OUT = os.path.join(frame.REPO, "report", "output", "evidence_lines")
LOOKBACK_YEARS = 3  # earlier failed trials on the target count when they ended this long before entry
FAILURES_FROM = 2011  # first entry year whose lookback lies wholly in the era of registered results
# A target is a dependency in a tumour type when at least this many, and this share, of the type's cell lines
# screened by the cutoff depend on it (the 2026-11-04 comprehensiveness amendment).
DEPENDENT_LINES, DEPENDENT_SHARE = 2, 0.2
CELL_SCREENS_FROM = 2015  # first entry year whose year-before cutoff has published dependency screens (Cowley 2014)
SELECTIVE_MARGIN = 1.0  # log units of primary over best off-target potency: 10-fold
POTENT_100NM, POTENT_10NM = 7.0, 8.0  # best pChEMBL at the primary target: the line, and a descriptive extra
BRAIN = ("neurology", "psychiatry")  # the bio_area values whose programs are scored for brain penetrance
MAX_RO5_VIOLATIONS = 1
BRAIN_TPSA, BRAIN_MW, BRAIN_HBD = 90.0, 450.0, 3  # brain-penetrant: TPSA < 90, MW < 450, donors <= 3
# Mammalian Phenotype classes of the organs a drug's on-target harm most often reaches (the 2026-11-08 safety
# amendment): a target whose mouse mutants show a phenotype in any of them counts.
VITAL_ORGANS = {"MP:0005385": "cardiovascular", "MP:0005370": "liver and biliary", "MP:0005397": "haematopoietic",
                "MP:0005387": "immune", "MP:0003631": "nervous"}
SAFETY_STOP_GAP_YEARS = 1  # an earlier safety stop counts once its trials ended at least this long before entry


LITERATURE_GATE = "v3_final"  # the gate scoring of the retrieval the literature lines are built from


def literature_note(kind: str, exploratory: bool) -> str:
    """The plain-English caveat of a literature line, with its retrieval recall from the gate record."""
    import json
    with open(literature.GATE) as fh:
        k = json.load(fh)[LITERATURE_GATE]["kinds"][kind]
    recall = f"the search found {k['recall']:.1%} of the studies a hand search found ({k['recall_pubmed_indexed']:.0%} of " \
             "those indexed in PubMed)"
    return ("exploratory: " if exploratory else "measured with incomplete retrieval: ") + recall



APPLIES = {
    "all": lambda d: d.index == d.index,
    "target": lambda d: d.has_target_disease,
    "ONC": lambda d: d.has_target_disease & d.regime.eq("ONC"),
    "small_molecule": lambda d: d.modality.eq("small_molecule"),
    "brain": lambda d: d.modality.eq("small_molecule") & d.bio_area.isin(BRAIN),
    "phase_2_3": lambda d: d.phase.ge(2),
    "from_2011": lambda d: d.has_target_disease & d.entry_year.ge(FAILURES_FROM),
    "onc_screened": lambda d: d.has_target_disease & d.regime.eq("ONC") & d.entry_year.ge(CELL_SCREENS_FROM),
    "disease": lambda d: d.mondo_id.fillna("").ne(""),
}

@dataclass(frozen=True)
class Line:
    label: str  # plain English, as the report shows it
    column: str  # entries.csv column
    applies: str = "all"  # entries the line is scored on (APPLIES)
    status: str = ""  # a caveat the report prints with the line


@dataclass(frozen=True)
class Fact:
    """One question about an entry, answered by exactly one of `values` on every entry it applies to."""
    key: str
    label: str  # the question, in plain English
    applies: str  # entries the fact is answered for (APPLIES)
    values: tuple[tuple[str, str], ...] = ()  # (value, plain-English label), mutually exclusive, in display order
    columns: tuple[tuple[str, str], ...] = ()  # (value, the 0/1 column that value gives), for the values that are evidence
    unknown: tuple[str, ...] = ()  # values that leave the entry unknown on the fact rather than without the evidence
    numeric: bool = False  # a raw measurement, stored as a number
    counts: bool = True  # makes up its kind (false for hindsight and exploratory facts)
    hindsight: bool = False  # scored on today's data, not as of entry
    note: str = ""  # caveat printed with the fact


@dataclass(frozen=True)
class Kind:
    """A kind of evidence (the shared list, PR #159): yes when any of its counting facts takes one of its evidence
    values."""
    key: str
    category: str  # the broad category by experimental system (CATEGORIES)
    about: str  # whether the kind is evidence about the target or about the drug
    label: str
    definition: str
    source: str
    column: str | None  # the kind's any-of column; None while the kind is planned and has no facts
    facts: tuple[tuple[str, tuple[str, ...]], ...] = ()  # (fact key, the values that count as this kind's evidence)
    chart: str | None = None  # the fact whose evidence values the chart draws as rows under the kind
    drawn: bool = True  # the evidence chart draws the kind (molecule properties are stored, not drawn)
    rows: tuple[str, ...] = ()  # facts the chart draws as rows of their own after the kind, since they overlap it
    # Aggregates and crosses of the kind's facts, estimated in the appendix; a line split by data source (the MGI and
    # IMPC mice, DepMap and Project Score screens) is read from the source tables, since no fact splits by source.
    derived: tuple[Line, ...] = ()


FACT_PREFIX = "fact_"  # entries.csv column prefix of each fact
YES_NO = (("yes", "Yes"), ("no", "No"))
# Broad categories by the experimental system that produced the evidence, in the chart's order (PR #159, amendment 4,
# 2026-11-20).
CATEGORIES = {"human_genetics": "Human genetics", "in_vitro": "In vitro", "animals": "Animals", "human": "Human",
              "the_drug": "The drug", "safety": "Target safety risk"}

FACTS = {f.key: f for f in [
    Fact("variants", "Which inherited variants link the target's gene to the disease", "target",
         (("rare_only", "Rare variants only"), ("common_only", "Common variants only (genome-wide association studies)"),
          ("both", "Both rare and common variants"), ("none", "None")),
         (("rare_only", "tier_rare_only"), ("common_only", "tier_common_only"), ("both", "allelic_series"))),
    Fact("loss_effect", "What losing the gene does to disease risk, by the labelled mechanism", "target",
         (("raises_risk", "Raises risk"), ("lowers_risk", "Lowers risk"), ("mixed", "Both, in different variants"),
          ("undirected", "Labelled, direction not given"), ("unlabelled", "No mechanism labelled"),
          ("none", "No inherited variants"))),
    Fact("mutation", "How the gene is recurrently mutated in this cancer", "ONC",
         (("activating", "Activating"), ("inactivating", "Inactivating"), ("both", "Both"),
          ("unknown", "Mutated, effect unknown"), ("none", "Not recurrently mutated")),
         (("activating", "somatic_activating"), ("inactivating", "somatic_inactivating"), ("both", "somatic_both"),
          ("unknown", "somatic_effect_unknown"))),
    Fact("pathway", "A curated pathway shows a disease mutation disrupting the target", "target", YES_NO,
         (("yes", "reactome"),)),
    Fact("mouse_match", "How closely mice with the gene altered resemble the disease", "target",
         (("close", "Closely"), ("loose", "Loosely"), ("none", "No such mice")),
         (("close", "animal_close"), ("loose", "tier_mouse_loose"))),
    Fact("mouse_direction", "Which way the mouse models favour moving the gene's function", "target",
         (("favours_raising", "Raising it"), ("favours_lowering", "Lowering it"), ("mixed", "Both"),
          ("none", "No labelled model"))),
    Fact("perturbation", "Changing the target in an established cell line changes a disease feature, by any source "
         "that reaches the entry: today the knockout screens of cancer cell lines (oncology entries from 2015)", "target",
         (("yes", "Yes"), ("no", "No"), ("not_reached", "No source reaches the entry")),
         (("yes", "cell_line_perturbation"),), unknown=("not_reached",)),
    Fact("rna", "How the gene's RNA level differs in diseased tissue", "target",
         (("up", "Higher in disease (in at least one comparison)"), ("down", "Lower in disease only"),
          ("none", "No difference")),
         (("up", "expression_up"), ("down", "expression_down"))),
    Fact("best_approval", "The closest disease a drug on the target was approved for before entry", "target",
         (("same_or_close", "This disease or a very close one (Lin at least 0.8)"),
          ("related", "A related disease (Lin 0.5 to 0.8)"), ("unrelated_only", "Only unrelated diseases"),
          ("none", "No approved drug on the target")),
         (("same_or_close", "validated_at_entry"), ("related", "approved_related"),
          ("unrelated_only", "approved_unrelated_only"))),
    Fact("related_failure", "Another drug on the target failed in a related disease in the 3 years before entry",
         "target", (("yes", "Yes"), ("no", "No"), ("not_scored", "Not scored: entered before 2011")),
         (("yes", "earlier_failure"),), unknown=("not_scored",)),
    Fact("potency", "How strongly the drug binds its primary target, measured before entry", "small_molecule",
         (("le_10nm", "10 nM or better"), ("10_100nm", "10 to 100 nM"), ("weaker", "Weaker than 100 nM"),
          ("not_measured", "Not measured")),
         (("le_10nm", "potent_10nm"), ("10_100nm", "potency_10_100nm"), ("weaker", "tier_weaker"))),
    Fact("selectivity", "How much more strongly it binds its target than other proteins tested", "small_molecule",
         (("ge_10x", "10-fold or more"), ("under_10x", "Less than 10-fold"),
          ("no_offtarget", "No other protein measured"), ("not_measured", "Target not measured")),
         unknown=("no_offtarget", "not_measured")),
    Fact("cell_functional", "Drug's effect measured in living cells", "small_molecule",
         (("yes", "A functional, cell-based assay at a primary target"), ("no", "Measured, but not in living cells"),
          ("not_measured", "No measurement at a primary target")), (("yes", "cell_functional"),)),
    Fact("best_pchembl", "Best potency at the primary target (pChEMBL)", "small_molecule", numeric=True, counts=False),
    Fact("selectivity_margin", "Selectivity margin over the best off-target (log units)", "small_molecule",
         numeric=True, counts=False),
    Fact("drug_like", "Drug-like size and chemistry", "small_molecule",
         (("yes", "Yes"), ("no", "No"), ("unknown", "Structure unknown")), (("yes", "drug_like"),),
         unknown=("unknown",)),
    Fact("brain_suited", "Chemistry suited to entering the brain", "brain",
         (("yes", "Yes"), ("no", "No"), ("unknown", "Structure unknown")), (("yes", "brain_penetrant"),),
         unknown=("unknown",)),
    Fact("animal_studies", "Published studies of the drug in animals", "all",
         (("disease_and_healthy", "In an animal model of the disease, and in healthy animals"),
          ("disease_only", "In an animal model of the disease only"), ("healthy_only", "Only in healthy animals"),
          ("none", "None found"), ("not_searched", "Not searched")),
         (("disease_and_healthy", "lit_animal_both"), ("disease_only", "lit_animal_disease_only"),
          ("healthy_only", "tier_lit_healthy_only")), unknown=("not_searched",),
         note=literature_note("animal_disease", exploratory=True)),
    Fact("in_people", "A published study shows the drug acting on its target in people", "phase_2_3",
         (("yes", "Yes"), ("no", "No"), ("not_searched", "Not searched")), (("yes", "lit_human_engagement"),),
         unknown=("not_searched",), note=literature_note("human_engagement", exploratory=False)),
    Fact("constraint", "People rarely carry broken copies of the gene (gnomAD LOEUF below 0.35)", "target", YES_NO,
         (("yes", "constrained"),)),
    Fact("mice_die_young", "Mice without the gene die before weaning", "target", YES_NO, (("yes", "ko_lethal"),)),
    Fact("most_cells_need_gene", "Most human cell types need the gene (DepMap common essential)", "target", YES_NO,
         (("yes", "pan_essential"),)),
    Fact("vital_organ_phenotype", "Mutant mice show a phenotype in a vital organ (heart, liver, blood, immune or "
         "nervous system)", "target", YES_NO, (("yes", "ko_vital_organ"),), counts=False,
         note="exploratory (the 2026-11-08 safety amendment)"),
    Fact("earlier_safety_stop", "An earlier drug on the same target stopped for safety", "target",
         (("yes", "Yes"), ("no", "No"), ("not_scored", "Not scored: entered before 2011")),
         (("yes", "earlier_safety_stop"),), unknown=("not_scored",), counts=False,
         note="exploratory (the 2026-11-08 safety amendment)"),
    Fact("project_score_hindsight", "A genome-wide knockout screen ranks the target for this cancer, on today's data",
         "target", YES_NO, (("yes", "crispr_untimed"),), counts=False, hindsight=True),
    Fact("most_cells_need_gene_hindsight", "Most human cell types need the gene, on today's list", "target", YES_NO,
         (("yes", "pan_essential_untimed"),), counts=False, hindsight=True),
]}

# The kinds of evidence of the shared list (PR #159), grouped by broad category in CATEGORIES order.
KINDS = {k.key: k for k in [
    Kind("human_genetics", "human_genetics", "target", "Human genetics: inherited variants link the target to the disease",
         "Inherited variants link the target to the disease (GWAS, gene burden, Mendelian): the program's disease, a "
         "subtype of it or a disease at least 0.8 similar on MONDO (Lin)",
         "Open Targets 26.09 (GWAS credible sets, gene burden tests, ClinVar, PanelApp, Orphanet, Gene2Phenotype, "
         "ClinGen, UniProt); each item dated by when it became known", "g3",
         (("variants", ("rare_only", "common_only", "both")), ("loss_effect", ())), chart="variants",
         derived=(Line("Rare inherited variants, including single-gene disease", "rare_variant", "target"),
                  Line("Common variants (genome-wide association studies)", "gwas", "target"),
                  Line("Genetics agrees with the drug's direction", "genetics_concordant", "target"))),
    Kind("tumour_genetics", "human_genetics", "target", "Tumour genetics (oncology): the gene is recurrently mutated in this cancer",
         "The gene is recurrently mutated in this cancer (oncology only)",
         "COSMIC Cancer Gene Census, IntOGen and ClinVar somatic, through Open Targets", "somatic",
         (("mutation", ("activating", "inactivating", "both", "unknown")),), chart="mutation",
         derived=(Line("The mutation's effect matches the drug's action", "somatic_concordant", "ONC"),)),
    Kind("curated_pathway", "human_genetics", "target", "Curated pathway: a disease mutation disrupts the target's pathway",
         "A curated pathway shows a disease mutation disrupting the target", "Reactome, through Open Targets",
         "reactome", (("pathway", ("yes",)),)),
    Kind("human_cell_perturbation", "in_vitro", "target", "Human cell perturbation",
         "Changing the target in primary human cells or tissue changes a disease feature", "Literature (#154)", None),
    Kind("cell_line_perturbation", "in_vitro", "target",
         "Cell lines: changing the target in an established cell line changes a disease feature (oncology, from 2015)",
         "Changing the target in an established cell line changes a disease feature. Today only knockout screens reach "
         "it: in screens published before entry, cancer cell lines of the program's tumour type need the gene "
         "(oncology entries from 2015); the literature is to come (#154)",
         "DepMap and earlier RNAi and CRISPR dependency screens, each line dated by its first public release; Project "
         "Score through Open Targets, 2019 at the earliest", "cell_line_perturbation",
         (("perturbation", ("yes",)), ("project_score_hindsight", ("yes",))),
         derived=(Line("Cancer cells of this type need the gene to grow (dependency screens)", "cell_dependency",
                       "onc_screened"),
                  Line("Gene-knockout screens in human cells (Project Score)", "crispr", "target"))),
    Kind("mouse_genetics", "animals", "target", "Mouse genetics: mice with the gene altered show the disease",
         "A genetic change in an animal links the target to the disease: the mutant shows the disease (a knockout or "
         "transgene altering an animal model of it is to come, #154)",
         "IMPC knockouts (dated by first data release) and MGI lines (dated by first paper), matched by PhenoDigm",
         "mouse_genetics", (("mouse_match", ("close", "loose")), ("mouse_direction", ())),
         chart="mouse_match",
         derived=(Line("Mutant mice from published studies (MGI)", "mgi", "target"),
                  Line("Mouse knockout from a large-scale screen (IMPC)", "impc", "target"),
                  Line("Mouse genetics agrees with the drug's direction", "animal_concordant", "target"))),
    Kind("animal_model_pharmacology", "animals", "target", "Animal model pharmacology",
         "A non-genetic change to the target (drug, antibody, siRNA) alters an animal model of the disease",
         "Literature (#154)", None),
    Kind("drug_animal_studies", "animals", "drug", "Published animal studies of the drug",
         "A published study of the drug itself in animals, in a model of the disease or in healthy animals "
         "(exploratory: the searches miss some of these studies)", "PubMed abstracts, screened by an LLM",
         "area_lit_animal", (("animal_studies", ("disease_and_healthy", "disease_only", "healthy_only")),),
         chart="animal_studies",
         derived=(Line("The drug in an animal model of the disease", "lit_animal_disease", "disease"),
                  Line("The drug tested in healthy animals", "lit_animal_healthy", "all"))),
    Kind("diseased_tissue", "human", "target", "Diseased tissue: the gene's level differs in diseased tissue",
         "The gene's RNA or protein level differs in diseased tissue (protein is to come, #154)",
         "Expression Atlas, through Open Targets (RNA, at least 2.1-fold)", "expression",
         (("rna", ("up", "down")),), chart="rna",
         derived=(Line("Target more active in disease, and the drug blocks it", "expression_up_inhibitor", "target"),)),
    Kind("observational_biomarker", "human", "target", "Observational biomarker",
         "The target or its product, measured in blood, another fluid or by imaging, tracks the disease",
         "Literature (#154)", None),
    Kind("clinical_observation", "human", "target", "Clinical observation", "An effect seen in people, such as a side effect",
         "Literature (#154)", None),
    Kind("validated_at_entry", "human", "target", "Validated at entry: a drug on the target approved for this or a very close "
         "disease", "A drug on the target was already approved for the same or a very close disease (Lin at least "
         "0.8) before entry", "Drugs@FDA approvals", "validated_at_entry", (("best_approval", ("same_or_close",)),)),
    Kind("earlier_drug_other_disease", "human", "target", "A drug on the target approved for another disease",
         "A drug on the target was approved for another disease, one not close enough to make the pair validated at "
         "entry", "Drugs@FDA approvals", "approved_other_disease",
         (("best_approval", ("related", "unrelated_only")),), chart="best_approval",
         derived=(Line("A drug on the target approved for a related disease, Lin at least 0.5 (B1)", "b1", "target"),)),
    Kind("earlier_drug_failure", "human", "target", "Another drug on the target failed in a related disease in the last 3 years",
         "Another drug on the target had a Phase 2 or 3 trial in a related disease (Lin at least 0.5) miss its "
         "primary endpoint or stop for futility in the three years before entry", "ClinicalTrials.gov",
         "earlier_failure", (("related_failure", ("yes",)),)),
    Kind("drug_in_people", "human", "drug", "Drug shown to act on its target in people",
         "A published study showing the drug acting on its target in people (exploratory)",
         "PubMed abstracts, screened by an LLM", "lit_human_engagement", (("in_people", ("yes",)),)),
    Kind("binding", "the_drug", "drug", "Binding to the target measured before entry",
         "The drug's binding or activity at its primary target was measured in laboratory assays before entry "
         "(small molecules)", "ChEMBL 37, each measurement dated by the paper, patent or dataset that reported it",
         "area_measured", (("potency", ("le_10nm", "10_100nm", "weaker")), ("selectivity", ()),
                           ("cell_functional", ("yes",)), ("best_pchembl", ()), ("selectivity_margin", ())),
         chart="potency", rows=("cell_functional",),
         derived=(Line("Drug binds its target strongly (100 nM or better)", "potent_100nm", "small_molecule"),
                  Line("Drug binds its target 10× more strongly than other proteins tested", "selective",
                       "small_molecule"),
                  Line("The drug binds another protein within 10-fold of its target", "poor_selectivity",
                       "small_molecule"))),
    Kind("molecule_properties", "the_drug", "drug", "Molecule properties: drug-like, or suited to the brain",
         "Drug-like size and chemistry (no more than one Lipinski violation); for brain diseases, chemistry suited to "
         "entering the brain (TPSA under 90, weight under 450, at most 3 donors)",
         "PubChem and ChEMBL computed properties", "molecule_properties",
         (("drug_like", ("yes",)), ("brain_suited", ("yes",))), drawn=False),
    Kind("target_safety", "safety", "target", "People rarely carry broken copies of the gene, or mice without it die young",
         "A property of the target, not evidence for the disease: people rarely carry broken copies of the gene "
         "(gnomAD LOEUF below 0.35), mice without it die before weaning, or most human cell types need it",
         "gnomAD v4.1; Mammalian Phenotype ontology, through Open Targets; DepMap", "liability",
         (("constraint", ("yes",)), ("mice_die_young", ("yes",)), ("most_cells_need_gene", ("yes",)),
          ("vital_organ_phenotype", ("yes",)), ("earlier_safety_stop", ("yes",)),
          ("most_cells_need_gene_hindsight", ("yes",)))),
]}
ADJUSTMENTS = [Line("Trial enrolled patients selected by a biomarker", "biomarker_selected", "all")]
# Kinds about earlier drugs on the target: the target-precedent covariate would adjust for the kind itself.
PRECEDENT_KINDS = ("validated_at_entry", "earlier_drug_other_disease", "earlier_drug_failure")
# The 2026-11-08 safety lines, tested against safety and efficacy stops.
SAFETY = [Line("Standard flags: people rarely carry broken copies of the gene, or mice without it die young",
               "liability", "target"),
          Line("Mutant mice show a phenotype in a vital organ (heart, liver, blood, immune or nervous system)",
               "ko_vital_organ", "target"),
          Line("An earlier drug on the same target stopped for safety", "earlier_safety_stop", "target"),
          Line("The drug binds another protein within 10-fold of its target", "poor_selectivity", "small_molecule")]


def counting(kind: Kind) -> list[tuple[Fact, tuple[str, ...]]]:
    """The facts that make up a kind, with the values that count: those whose fact counts and has evidence values."""
    return [(FACTS[f], vals) for f, vals in kind.facts if FACTS[f].counts and vals]


def chart_rows() -> list[tuple[str, Kind, str, Line]]:
    """The evidence chart's rows in order: (category, kind, level, line). A fact the kind names in `rows` follows as a
    row of its own (level fact). Each drawn kind with facts is a row (level
    kind) and, when it names a chart fact, one indented row (level value) per evidence value of that fact; the
    values do not overlap, so a program falls in at most one of them."""
    rows = []
    for k in KINDS.values():
        if not (k.column and k.drawn):
            continue
        rows.append((k.category, k, "kind", Line(k.label, k.column, "all")))
        if k.chart:  # a fact that describes the kind without being its evidence draws every value it has a column for
            fact = FACTS[k.chart]
            labels = dict(fact.values)
            evidence = dict(k.facts)[k.chart] or tuple(v for v, _ in fact.columns)
            rows += [(k.category, k, "value", Line(labels[v], c, fact.applies)) for v, c in fact.columns if v in evidence]
        for f in k.rows:
            fact = FACTS[f]
            rows += [(k.category, k, "fact", Line(fact.label, c, fact.applies)) for v, c in fact.columns if v == "yes"]
    return rows


def report_lines() -> list[tuple[Kind | None, str, Line]]:
    """Every line the analysis estimates, kind by kind: (kind, level, line), level one of kind, value, derived,
    hindsight, exploratory and adjustment. Each column appears once."""
    out, seen = [], set()

    def add(kind, level, line):
        if line.column not in seen:
            seen.add(line.column)
            out.append((kind, level, line))
    for k in KINDS.values():
        if not k.column:
            continue
        add(k, "kind", Line(k.label, k.column, "all"))
        for f, _ in k.facts:
            fact = FACTS[f]
            level = "hindsight" if fact.hindsight else "exploratory" if not fact.counts else "value"
            labels = dict(fact.values)
            for v, c in fact.columns:
                add(k, level, Line(fact.label if len(fact.columns) == 1 else labels[v], c, fact.applies, fact.note))
        for ln in k.derived:
            add(k, "derived", ln)
    for a in ADJUSTMENTS:
        add(None, "adjustment", a)
    return out


def facts(d: pd.DataFrame) -> pd.DataFrame:
    """Each fact's value for every entry it applies to (null elsewhere), from the raw evidence columns of build."""
    def pick(scope: str, conditions: list, default: str = "none") -> pd.Series:
        v = pd.Series(np.select([c.fillna(False).astype(bool) for c, _ in conditions], [x for _, x in conditions],
                                default), index=d.index, dtype=object)
        return v.where(APPLIES[scope](d))

    on = lambda c: d[c].fillna(0).gt(0)  # noqa: E731
    yes_no = lambda c, scope="target": pick(scope, [(on(c), "yes")], "no")  # noqa: E731
    scored = lambda c, scope, missing: pick(scope, [(d[c].isna(), missing), (on(c), "yes")], "no")  # noqa: E731
    rare, common = on("burden") | on("mendelian"), on("gwas")
    gof, lof = on("somatic_gof"), on("somatic_lof")
    close, mouse = on("mgi_strong") | on("impc_strong"), on("mgi") | on("impc")
    best, margin = d.assay_best, d.assay_margin
    disease, healthy = on("lit_animal_disease"), on("lit_animal_healthy")
    b1, b1_close, precedent = on("b1"), on("b1_close"), on("precedent")
    return pd.DataFrame({
        "variants": pick("target", [(rare & common, "both"), (rare, "rare_only"), (common, "common_only")]),
        "loss_effect": d.loss_effect.where(APPLIES["target"](d)),
        "mutation": pick("ONC", [(on("somatic") & gof & lof, "both"), (on("somatic") & gof, "activating"),
                                 (on("somatic") & lof, "inactivating"), (on("somatic"), "unknown")]),
        "pathway": yes_no("reactome"),
        "mouse_match": pick("target", [(close, "close"), (mouse, "loose")]),
        "mouse_direction": d.mouse_favours.where(APPLIES["target"](d)),
        # Each source counts only on the entries it reaches: the screens reach oncology entries from 2015 whose tumour
        # type has a screened line.
        "perturbation": pick("target", [(~APPLIES["onc_screened"](d), "not_reached"),
                                        (on("cell_dependency") | on("crispr"), "yes"),
                                        (d.cell_dependency.isna(), "not_reached")], "no"),
        "rna": pick("target", [(on("expression_up"), "up"), (on("expression"), "down")]),
        "best_approval": pick("target", [(b1_close, "same_or_close"), (b1, "related"), (precedent, "unrelated_only")]),
        "related_failure": scored("earlier_failure", "target", "not_scored"),
        "potency": pick("small_molecule", [(best.isna(), "not_measured"), (best >= POTENT_10NM, "le_10nm"),
                                           (best >= POTENT_100NM, "10_100nm")], "weaker"),
        "cell_functional": pick("small_molecule", [(best.isna(), "not_measured"), (on("cell_functional"), "yes")], "no"),
        "selectivity": pick("small_molecule", [(best.isna(), "not_measured"), (margin.isna(), "no_offtarget"),
                                               (margin >= SELECTIVE_MARGIN, "ge_10x")], "under_10x"),
        "best_pchembl": best.where(APPLIES["small_molecule"](d)),
        "selectivity_margin": margin.where(APPLIES["small_molecule"](d)),
        "drug_like": scored("drug_like", "small_molecule", "unknown"),
        "brain_suited": scored("brain_penetrant", "brain", "unknown"),
        "animal_studies": pick("all", [(d.lit_animal_healthy.isna(), "not_searched"), (disease & healthy,
                                       "disease_and_healthy"), (disease, "disease_only"), (healthy, "healthy_only")]),
        "in_people": scored("lit_human_engagement", "phase_2_3", "not_searched"),
        "constraint": yes_no("constrained"),
        "mice_die_young": yes_no("ko_lethal"),
        "most_cells_need_gene": yes_no("pan_essential"),
        "vital_organ_phenotype": yes_no("ko_vital_organ"),
        "earlier_safety_stop": scored("earlier_safety_stop", "target", "not_scored"),
        "project_score_hindsight": yes_no("crispr_untimed"),
        "most_cells_need_gene_hindsight": yes_no("pan_essential_untimed"),
    }, index=d.index)[list(FACTS)]


def drug_action(sign: pd.Series) -> pd.Series:
    """The drug's action on its primary targets: decreases, increases, or other (ambiguous, depleting or mixed);
    null without a resolved human protein target."""
    return sign.map({"decrease": "decreases", "increase": "increases"}).fillna("other").where(sign.notna())


def derive(f: pd.DataFrame, action: pd.Series, mondo: pd.Series) -> pd.DataFrame:
    """Every line column from the facts `f` and the drug's action: each evidence value's 0/1 column (null where its fact
    is unknown or does not apply), each kind's any-of column (null where none of its counting facts is known), and
    the derived lines (aggregates of a fact's values, and crosses of a fact with the drug's action)."""
    out: dict[str, pd.Series] = {}

    def flag(fact: str, values) -> pd.Series:
        v, unknown = f[fact], FACTS[fact].unknown
        return v.isin(values).astype(float).where(v.notna() & ~v.isin(unknown))
    for fact in FACTS.values():
        for value, column in fact.columns:
            out[column] = flag(fact.key, (value,))
    for k in KINDS.values():
        if k.column:
            parts = pd.DataFrame({fact.key: flag(fact.key, vals) for fact, vals in counting(k)})
            out[k.column] = parts.gt(0).any(axis=1).astype(float).where(parts.notna().any(axis=1))
    dec, inc = action.eq("decreases"), action.eq("increases")
    target = f.variants.notna()
    cross = lambda s, scope=target: s.astype(float).where(scope)  # noqa: E731
    out |= {
        "rare_variant": flag("variants", ("rare_only", "both")), "gwas": flag("variants", ("common_only", "both")),
        "genetics_concordant": cross(out["g3"].gt(0) & ((dec & f.loss_effect.eq("lowers_risk"))
                                                        | (inc & f.loss_effect.eq("raises_risk")))),
        "somatic_concordant": cross((dec & f.mutation.isin(("activating", "both")))
                                    | (inc & f.mutation.isin(("inactivating", "both"))), f.mutation.notna()),
        "expression_up_inhibitor": cross(f.rna.eq("up") & dec),
        "animal_concordant": cross((inc & f.mouse_direction.eq("favours_raising"))
                                   | (dec & f.mouse_direction.eq("favours_lowering"))),
        "b1": flag("best_approval", ("same_or_close", "related")),
        "potent_100nm": flag("potency", ("le_10nm", "10_100nm")),
        "selective": flag("selectivity", ("ge_10x",)),
        "lit_animal_disease": flag("animal_studies", ("disease_and_healthy", "disease_only"))
        .where(mondo.fillna("").ne("")),
        "lit_animal_healthy": flag("animal_studies", ("disease_and_healthy", "healthy_only")),
    }
    out["poor_selectivity"] = 1.0 - out["selective"]
    return pd.DataFrame(out, index=f.index)


def failed_trials() -> pd.DataFrame:
    """Phase 2/3 trials of each entity in a program disease that missed their primary endpoint or
    stopped for futility, with the date they ended (primary completion, else completion)."""
    return frame.query("""
        SELECT DISTINCT p.moiety_id, p.mondo_id, coalesce(s.primary_completion_date, s.completion_date) AS ended
        FROM preclin.trial_outcome o JOIN preclin.ctgov_study s USING (nct_id)
        JOIN preclin.dev_program_trial dt USING (nct_id) JOIN preclin.dev_program p USING (program_id)
        WHERE dt.phase >= 2 AND p.mondo_id IS NOT NULL
          AND (o.primary_endpoint = 'not_met' OR o.stop_reason = 'efficacy_futility')
          AND coalesce(s.primary_completion_date, s.completion_date) IS NOT NULL""")


def failures_by_gene(failed: pd.DataFrame, genes: dict) -> dict:
    """gene -> [(moiety_id, mondo_id, ended)] for failed trials of entities on that primary target."""
    out = defaultdict(list)
    for mid, d, ended in failed.itertuples(index=False):
        for g in genes.get(mid, ()):
            out[g].append((mid, d, pd.Timestamp(ended)))
    return out


def earlier_failure(by_gene: dict, moiety_id, genes, related: frozenset, entry: pd.Timestamp) -> bool | None:
    """Whether another entity on one of `genes` had a Phase 2/3 trial in a disease of `related` fail
    within LOOKBACK_YEARS before `entry`; None for entries before FAILURES_FROM, whose lookback
    reaches back before registered results."""
    if entry.year < FAILURES_FROM:
        return None
    start = entry - pd.DateOffset(years=LOOKBACK_YEARS)
    return any(mid != moiety_id and d in related and start <= ended < entry
               for g in genes for mid, d, ended in by_gene.get(g, ()))


def cell_dependency(genes, related: frozenset, year: int, lines: dict, dep_year: dict, essential: dict) -> float:
    """1 when a gene of `genes` is a dependency in the tumour type, as the screens public by the end of `year`
    show; 0 when lines of the type were screened and none of the genes is; NaN when no line of the type was.
    `lines`: cell line -> (MONDO term, year its first screen became public); `dep_year`: (gene, line) -> year
    its dependency on the gene became public. Genes on that year's common-essential list do not count."""
    typed = [line for line, (mondo, first) in lines.items() if mondo in related and first <= year]
    if not typed:
        return np.nan
    for g in genes:
        if frame.essential_as_of(essential, [g], year):
            continue
        n = sum(1 for line in typed if dep_year.get((g, line), 9999) <= year)
        if n >= DEPENDENT_LINES and n >= DEPENDENT_SHARE * len(typed):
            return 1.0
    return 0.0


def cell_screens() -> tuple[dict, dict]:
    """The dependency screens: cell line -> (MONDO term, first public year), and (Ensembl gene, cell line) ->
    the year its dependency became public."""
    s = frame.query("""SELECT c.depmap_id, c.mondo_id, min(s.public_year) AS year FROM preclin.cell_line c
                       JOIN preclin.cell_screen s USING (depmap_id) WHERE c.mondo_id IS NOT NULL GROUP BY 1, 2""")
    d = frame.query("""SELECT g.ensembl_id, d.depmap_id, min(s.public_year) AS year
                       FROM preclin.cell_dependency d JOIN preclin.cell_screen s USING (depmap_id, dataset)
                       JOIN preclin.hgnc_gene g ON g.entrez_id = d.entrez_id
                       WHERE g.ensembl_id IS NOT NULL GROUP BY 1, 2""")
    return ({r.depmap_id: (r.mondo_id, int(r.year)) for r in s.itertuples()},
            {(r.ensembl_id, r.depmap_id): int(r.year) for r in d.itertuples()})


def molecule_lines(assays: pd.DataFrame, primary: set[str], year: int) -> dict:
    """Potency and selectivity of one entity known by the end of `year`: selectivity is undefined
    (NaN) unless both the primary target and an off-target were measured."""
    a = frame.assays_as_of(assays, primary, year)
    return {"assay_best": a["best"], "assay_margin": a["margin"], "cell_functional": float(a["cell_functional"]),
            "potent_10nm": float(a["best"] >= POTENT_10NM), "potent_100nm": float(a["best"] >= POTENT_100NM),
            "selective": float(a["margin"] >= SELECTIVE_MARGIN) if pd.notna(a["margin"]) else np.nan}


def property_lines(d: pd.DataFrame, props: pd.DataFrame) -> pd.DataFrame:
    """Drug-likeness of small molecules and, for neurology and psychiatry programs (BRAIN), brain-penetrant
    properties, from each entity's computed properties; null where the line does not apply or the
    entity has none. A structure does not change, so the properties hold at any entry."""
    p = d[["moiety_id"]].merge(props, on="moiety_id", how="left").set_index(d.index)
    sm, known = d.modality.eq("small_molecule"), p.moiety_id.isin(props.moiety_id)
    drug_like = (p.ro5_violations <= MAX_RO5_VIOLATIONS).astype(float).where(sm & p.ro5_violations.notna())
    brain = ((p.tpsa < BRAIN_TPSA) & (p.molecular_weight < BRAIN_MW) & (p.hbd <= BRAIN_HBD)).astype(float) \
        .where(sm & d.bio_area.isin(BRAIN) & known & p[["tpsa", "molecular_weight", "hbd"]].notna().all(axis=1))
    return pd.DataFrame({"drug_like": drug_like, "brain_penetrant": brain}, index=d.index)


def literature_inputs(moieties: list[int]) -> tuple[pd.DataFrame, set[int], dict[int, int]]:
    """The qualifying literature screens, the drugs whose retrieval is screened (screen or prefilter rows, or
    nothing retrieved), and each entity's surviving entity."""
    q = literature.qualifying()
    screened = set(frame.query("""SELECT s.moiety_id FROM preclin.literature_search s GROUP BY 1
                                  HAVING NOT EXISTS (SELECT 1 FROM preclin.literature_hit h WHERE h.moiety_id = s.moiety_id)
                                  UNION SELECT moiety_id FROM preclin.literature_screen
                                  UNION SELECT moiety_id FROM preclin.literature_prefilter""").moiety_id)
    return q, screened, literature.survivors(moieties)


def literature_columns(d: pd.DataFrame, related, q: pd.DataFrame, screened: set[int], to: dict[int, int]) -> pd.DataFrame:
    """The three literature lines of each entry, from the version 3 screens of the drug's published abstracts:
    1 when a qualifying study was published by the year before entry (for an animal model, of the entry's disease
    or a disease `related(mondo_id)` returns), 0 when the drug's retrieval was screened and none was, null when it
    has not been searched and screened (or, for engagement, the entry is not Phase 2 or 3). A record with no known
    year cannot be shown to precede entry and does not count."""
    q = q[q.year.notna()]
    by: dict = defaultdict(list)
    for m, year, kind, mondo in zip(q.moiety_id, q.year.astype(int), q.kind, q.mondo_id):
        by[(int(m), kind)].append((year, mondo))
    out: dict[str, list] = {"lit_animal_disease": [], "lit_animal_healthy": [], "lit_human_engagement": []}
    for r in d.itertuples():
        m, cut = to.get(int(r.moiety_id), int(r.moiety_id)), int(r.entry_year) - 1
        if m not in screened:
            for v in out.values():
                v.append(np.nan)
            continue
        disease = r.mondo_id if isinstance(r.mondo_id, str) and r.mondo_id else None
        near = related(disease) if disease else frozenset()
        out["lit_animal_disease"].append(
            float(any(y <= cut and t in near for y, t in by[(m, "animal_disease")])) if disease else np.nan)
        out["lit_animal_healthy"].append(float(any(y <= cut for y, _ in by[(m, "animal_healthy")])))
        out["lit_human_engagement"].append(
            float(any(y <= cut for y, _ in by[(m, "human_engagement")])) if r.phase >= 2 else np.nan)
    return pd.DataFrame(out, index=d.index)


def vital_organ_genes() -> set[str]:
    """Ensembl ids of the genes whose mouse mutants show a phenotype in any VITAL_ORGANS class."""
    return set(frame.query("SELECT DISTINCT target_ensembl FROM preclin.ot_mouse_phenotype WHERE class_ids && %s",
                           (list(VITAL_ORGANS),)).target_ensembl)


def safety_stops() -> pd.DataFrame:
    """Every traced stop whose cause, or likely cause where no source states one, is safety, with the date its
    trials ended (pipeline.stop_causes)."""
    return frame.query("""SELECT c.moiety_id, c.mondo_id, s.stopped_on AS ended FROM preclin.stop c
                          JOIN preclin.stop_signal s USING (moiety_id, mondo_id, phase)
                          WHERE (c.cause = 'safety' OR (c.cause = 'unknown' AND c.guess = 'safety'))
                            AND s.stopped_on IS NOT NULL""")


def earlier_safety_stop(by_gene: dict, moiety_id, genes, entry: pd.Timestamp) -> bool | None:
    """Whether another entity on one of `genes`, in any disease, stopped for safety with its trials ended at least
    SAFETY_STOP_GAP_YEARS before `entry`; None for entries before FAILURES_FROM, which the traced stops (entries
    from 2008) cannot look back far enough for."""
    if entry.year < FAILURES_FROM:
        return None
    cut = entry - pd.DateOffset(years=SAFETY_STOP_GAP_YEARS)
    return any(mid != moiety_id and ended <= cut for g in genes for mid, _, ended in by_gene.get(g, ()))


@frame.held_once
def build() -> pd.DataFrame:
    snap = frame.snapshot()
    progs, trials = frame.programs(), frame.program_trials()
    ev = Evidence(progs)
    rows = entries(progs, trials, snap)
    rows = rows[rows.us_site].copy()
    rows["mondo_id"] = rows.program_id.map(progs.set_index("program_id").mondo_id)
    feats = cohorts(rows.drop(columns="mondo_id"), ev).drop(columns=list(rows.columns.drop(["program_id", "phase"])),
                                                              errors="ignore")
    d = rows.merge(feats, on=["program_id", "phase"], how="left")
    d["has_target_disease"] = d.g3.notna()
    d["regime"] = d.regime.fillna(pd.Series(np.where(d.bio_area.eq("oncology"), "ONC", "COM"), index=d.index))

    by_gene = failures_by_gene(failed_trials(), dict(zip(ev.ent.index, ev.ent.genes)))
    d["earlier_failure"] = pd.Series([
        earlier_failure(by_gene, r.moiety_id, ev.ent.at[r.moiety_id, "genes"], ev.nb.terms(r.mondo_id, RELATED),
                        pd.Timestamp(r.entry)) if r.has_target_disease else None for r in d.itertuples()],
        index=d.index, dtype=object).map({True: 1.0, False: 0.0})

    unsafe = failures_by_gene(safety_stops(), dict(zip(ev.ent.index, ev.ent.genes)))
    d["earlier_safety_stop"] = pd.Series([
        earlier_safety_stop(unsafe, r.moiety_id, ev.ent.at[r.moiety_id, "genes"], pd.Timestamp(r.entry))
        if r.has_target_disease else None for r in d.itertuples()], index=d.index, dtype=object).map({True: 1.0, False: 0.0})

    d = d.join(literature_columns(d, lambda m: ev.nb.terms(m, RELATED),
                                  *literature_inputs(sorted({int(m) for m in d.moiety_id}))))

    lines_by, dep_year = cell_screens()
    essential = frame.common_essentials()
    onc = APPLIES["ONC"](d)
    d["cell_dependency"] = pd.Series([
        cell_dependency(ev.ent.at[r.moiety_id, "genes"], ev.nb.terms(r.mondo_id, RELATED), r.entry_year - 1,
                        lines_by, dep_year, essential) if o else np.nan for r, o in zip(d.itertuples(), onc)],
        index=d.index, dtype=float)

    symbols = frame.query("""SELECT mt.moiety_id, t.symbol FROM preclin.moiety_target mt
                             JOIN public.targets t ON t.id = mt.target_id WHERE mt.is_primary""") \
        .groupby("moiety_id").symbol.apply(set)
    measurements = frame.drug_assays()
    assays, none = dict(iter(measurements.groupby("moiety_id"))), measurements.iloc[:0]
    mol = pd.DataFrame([molecule_lines(assays.get(r.moiety_id, none), symbols.get(r.moiety_id, set()), r.entry_year - 1)
                        if r.modality == "small_molecule" else {} for r in d.itertuples()], index=d.index)
    d = d.join(mol)
    props = frame.query("SELECT moiety_id, molecular_weight, tpsa, hbd, ro5_violations FROM preclin.moiety_property")
    d = d.join(property_lines(d[["moiety_id", "modality", "bio_area"]], props))

    vital = vital_organ_genes()
    d["ko_vital_organ"] = pd.Series([any(g in vital for g in ev.ent.at[m, "genes"]) if t else False
                                     for m, t in zip(d.moiety_id, d.has_target_disease)], index=d.index).astype(float)
    f = facts(d)
    d["drug_action"] = drug_action(d.sign)
    lines_ = derive(f, d.drug_action, d.mondo_id)
    d = d.drop(columns=[c for c in lines_.columns if c in d.columns]).join(lines_).join(f.add_prefix(FACT_PREFIX))
    for kind, _, ln in report_lines():  # lines read from the source tables (by source) rather than from the facts
        if kind and ln.column not in lines_:
            d[ln.column] = d[ln.column].astype(float).where(APPLIES[ln.applies](d))
    d["biomarker_selected"] = biomarker_selected(
        d, trials, frame.query("SELECT nct_id, selected FROM preclin.trial_biomarker_selection"))
    d["entry_date"] = pd.to_datetime(d.entry).dt.date
    d["era"] = pd.cut(d.entry_year, ERA_BINS, labels=ERA_LABELS).astype(str)
    keep = ["moiety_id", "mondo_id", "phase", "program_id", "entry_date", "entry_year", "era", "regime", "bio_area",
            "modality", "novel", "precedent", "target", "sign", "drug_action", "event", "s4", "has_target_disease",
            "assay_best", "assay_margin", *(FACT_PREFIX + k for k in FACTS),
            *(ln.column for _, _, ln in report_lines()), *(ln.column for ln in SAFETY)]
    return d[list(dict.fromkeys(keep))].sort_values(["moiety_id", "mondo_id", "phase"]).reset_index(drop=True)


def biomarker_selected(rows: pd.DataFrame, trials: pd.DataFrame, sel: pd.DataFrame) -> pd.Series:
    """1 when an industry trial that opened the entry's phase on the entry date restricts enrolment by a
    molecular biomarker, 0 when such trials were labelled and none does, null when none was labelled."""
    opening = trials[trials.industry & trials.starts_phase][["program_id", "nct_id", "phase", "start_date"]]
    opening = opening.assign(start_date=pd.to_datetime(opening.start_date)).merge(sel, on="nct_id")
    keyed = rows[["program_id", "phase", "entry"]].assign(entry=pd.to_datetime(rows.entry), _row=rows.index)
    m = keyed.merge(opening, left_on=["program_id", "phase", "entry"], right_on=["program_id", "phase", "start_date"])
    return m.groupby("_row").selected.any().astype(float).reindex(rows.index)


def coverage(d: pd.DataFrame) -> pd.DataFrame:
    """Each fact value's entries (the fact's distribution), and each line's eligible and exposed entries, distinct
    exposed targets and exposed share by phase."""
    rows = []
    for fact in FACTS.values():
        if fact.numeric:
            continue
        v = d[FACT_PREFIX + fact.key]
        rows += [{"kind": "", "level": "fact", "fact": fact.key, "value": value, "line": label,
                  "eligible": int(v.notna().sum()), "exposed": int(v.eq(value).sum())} for value, label in fact.values]
    for kind, level, ln in report_lines():
        v = d[ln.column]
        elig, exp = v.notna(), v.fillna(0) > 0
        rows.append({"kind": kind.key if kind else "", "level": level, "line": ln.label, "column": ln.column,
                     "status": ln.status, "eligible": int(elig.sum()), "exposed": int(exp.sum()),
                     "share": round(exp.sum() / max(elig.sum(), 1), 4),
                     "distinct_targets": int(d.loc[exp, "target"].nunique()),
                     **{f"share_phase_{p}": round((exp & d.phase.eq(p)).sum() / max((elig & d.phase.eq(p)).sum(), 1), 4)
                        for p in (1, 2, 3)}})
    return pd.DataFrame(rows)


ENTRY_COLUMNS = ["entry_date", "entry_year", "regime", "bio_area", "modality", "novel", "target", "has_target_disease",
                 "biomarker_selected", "drug_action"]


def registry() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """The structure as stored: kinds (with broad category, what they are about and definition), facts (with their values) and which facts make up
    which kind, with the values that count as the kind's evidence."""
    kinds = pd.DataFrame([{"kind_key": k.key, "position": i, "category": k.category, "about": k.about,
                           "label": k.label, "definition": k.definition, "source": k.source,
                           "planned": k.column is None, "drawn": k.drawn}
                          for i, k in enumerate(KINDS.values())])
    facts_ = pd.DataFrame([{"fact_key": f.key, "position": i, "label": f.label, "applies": f.applies,
                            "fact_values": [v for v, _ in f.values], "value_labels": [lab for _, lab in f.values],
                            "unknown_values": list(f.unknown), "numeric": f.numeric, "counts": f.counts,
                            "hindsight": f.hindsight, "note": f.note} for i, f in enumerate(FACTS.values())])
    links = pd.DataFrame([{"kind_key": k.key, "fact_key": f, "evidence_values": list(vals)}
                          for k in KINDS.values() for f, vals in k.facts])
    return kinds, facts_, links


def long_form(d: pd.DataFrame) -> pd.DataFrame:
    """Each entry's answer to each fact it applies to: a value for a categorical fact, a number for a measurement."""
    keyed = d.assign(mondo_id=d.mondo_id.fillna(""))
    parts = []
    for fact in FACTS.values():
        v = keyed[FACT_PREFIX + fact.key]
        part = keyed.loc[v.notna(), ["moiety_id", "mondo_id", "phase"]].assign(fact_key=fact.key)
        if fact.numeric:
            part = part.assign(value=None, value_num=v[v.notna()].astype(float))
        else:
            part = part.assign(value=v[v.notna()].astype(str), value_num=np.nan)
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


LABEL_TABLES = ("dev_program_approval", "moiety_target", "trial_outcome", "trial_biomarker_selection")
RELEASE_TABLES = ("chembl_activity", "moiety_property")


def input_fingerprint() -> dict:
    """What the dataset reads beyond the programs build: the programs snapshot; rows and latest decision of each LLM
    label table (a rewrite of approvals or targets changes them, though not the snapshot); the latest source
    release behind the ChEMBL potencies and computed properties; and, once they exist, the rows of
    preclin.cell_dependency and the latest lineage decision of preclin.cell_line (a remapped lineage moves lines
    between tumour types)."""
    fp: dict = {"snapshot": str(frame.snapshot())}
    for table in LABEL_TABLES:
        r = frame.query(f"SELECT count(*) AS n, max(llm_decision_id) AS last FROM preclin.{table}").iloc[0]
        fp[table] = [int(r.n), None if pd.isna(r["last"]) else int(r["last"])]
    for table in RELEASE_TABLES:
        last = frame.query(f"SELECT max(source_release_id) AS last FROM preclin.{table}").iloc[0]["last"]
        fp[table] = None if pd.isna(last) else int(last)
    if frame.query("SELECT to_regclass('preclin.cell_dependency') IS NOT NULL AS present").iloc[0]["present"]:
        r = frame.query("""SELECT (SELECT count(*) FROM preclin.cell_dependency) AS n,
                                  (SELECT max(llm_decision_id) FROM preclin.cell_line) AS last""").iloc[0]
        fp["cell_dependency"] = [int(r.n), None if pd.isna(r["last"]) else int(r["last"])]
    return fp


def stale_inputs(stored: dict, current: dict) -> list[str]:
    """Inputs whose fingerprint differs between the stored dataset and now, or that only one of them has."""
    return sorted(k for k in stored.keys() | current.keys() if stored.get(k) != current.get(k))


def stale() -> list[str]:
    """What changed since the stored dataset was built; ["no stored dataset"] when there is none."""
    last = frame.query("SELECT inputs FROM preclin.evidence_line_build ORDER BY built_at DESC LIMIT 1")
    if last.empty:
        return ["no stored dataset"]
    return stale_inputs(last.iloc[0]["inputs"], input_fingerprint())


def store(d: pd.DataFrame, commit: bool = True) -> str:
    """Replace the dataset in Postgres in one transaction; returns the build id. With commit false the transaction is
    rolled back, which checks the inserts against the schema without changing it."""
    kinds, facts_, links = registry()
    answers = long_form(d)
    e = d.assign(mondo_id=d.mondo_id.fillna(""), entry_date=pd.to_datetime(d.entry_date).dt.date,
                 biomarker_selected=d.biomarker_selected.map({1.0: True, 0.0: False}))
    build_id, fingerprint = str(uuid.uuid4()), input_fingerprint()
    nul = lambda v: None if not isinstance(v, list) and pd.isna(v) else v.item() if hasattr(v, "item") else v  # noqa: E731
    rows = lambda df: [tuple(nul(v) for v in r) + (build_id,) for r in df.itertuples(index=False)]  # noqa: E731
    with llm.connect() as conn, conn.cursor() as cur:
        for table in ("evidence_entry_fact", "evidence_entry", "evidence_kind_fact", "evidence_fact", "evidence_kind"):
            cur.execute(f"DELETE FROM preclin.{table}")
        cur.execute("""INSERT INTO preclin.evidence_line_build (build_id, code_commit, snapshot, n_entries, inputs)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (build_id, llm.git_commit(), frame.snapshot(), len(e), Json(fingerprint)))
        for table, df in (("evidence_kind", kinds), ("evidence_fact", facts_), ("evidence_kind_fact", links)):
            execute_values(cur, f"INSERT INTO preclin.{table} ({', '.join(df.columns)}, build_id) VALUES %s", rows(df))
        execute_values(cur, f"""INSERT INTO preclin.evidence_entry (moiety_id, mondo_id, phase, {", ".join(ENTRY_COLUMNS)},
                                                                    build_id) VALUES %s""",
                       [(int(r.moiety_id), r.mondo_id, int(r.phase), *(nul(getattr(r, c)) for c in ENTRY_COLUMNS),
                         build_id) for r in e.itertuples()], page_size=2000)
        execute_values(cur, """INSERT INTO preclin.evidence_entry_fact (moiety_id, mondo_id, phase, fact_key, value,
                                                                        value_num) VALUES %s""",
                       [(int(r.moiety_id), r.mondo_id, int(r.phase), r.fact_key, r.value, nul(r.value_num))
                        for r in answers.itertuples()], page_size=5000)
        cur.execute("SELECT count(*) FROM preclin.evidence_entry_kind WHERE has_evidence")
        exposed = cur.fetchone()[0]
        conn.commit() if commit else conn.rollback()
    print(f"{'stored' if commit else 'checked, rolled back,'} build {build_id}: {len(kinds)} kinds, {len(facts_)} facts, "
          f"{len(e)} entries, {len(answers)} answers, {exposed} entry-kind pairs with evidence")
    return build_id


def main() -> None:
    if sys.argv[1:] == ["check"]:
        changed = stale()
        print("stored evidence dataset is current" if not changed else
              f"stored evidence dataset is stale: {', '.join(changed)} changed; run python -m report.evidence_lines store")
        sys.exit(1 if changed else 0)
    os.makedirs(OUT, exist_ok=True)
    d = build()
    d.to_csv(os.path.join(OUT, "entries.csv"), index=False)
    cov = coverage(d)
    cov.to_csv(os.path.join(OUT, "coverage.csv"), index=False)
    print(f"entries {len(d)}; with a target and a disease {int(d.has_target_disease.sum())}")
    print(cov.to_string(index=False))
    if sys.argv[1:2] == ["store"]:
        store(d, commit=sys.argv[2:] != ["--rollback"])


if __name__ == "__main__":
    main()
