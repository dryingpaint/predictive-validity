"""The evidence-line dataset of the 2026-11-03 plan amendment (report/translation_plan.md).

    python -m report.evidence_lines         # write the CSVs
    python -m report.evidence_lines store   # also replace the dataset in Postgres
    python -m report.evidence_lines check   # exit 1, naming what changed, when the stored dataset is stale

One row per US-developed phase entry in 2008-2019 (report.section1.phase_rows with a US-sited
industry trial in the phase, skipped phases excluded), keyed by (moiety_id, mondo_id, phase) and carrying the
program_id of the current program build for joins within one run, with
every category and subcategory of CATEGORIES frozen at the year before entry, and the outcome
columns event and s4. Target-level lines come from report.section3.Evidence and are null for
entries without a single resolved human protein target and a disease; molecule lines from ChEMBL
potency measurements (report.frame.assays_as_of) and computed properties (preclin.moiety_property),
and are null outside small molecules. Descriptive lines (10 nM potency, hindsight lines) are shown
in coverage but do not make up their category.

Writes report/output/evidence_lines/: entries.csv, and coverage.csv with each line's eligible
and exposed entries, distinct exposed targets and exposed share by phase. No line is compared
with an outcome here.

`store` writes the same dataset to preclin.evidence_line (the registry), preclin.evidence_entry (one
row per entry, without outcomes) and preclin.evidence_entry_line (each non-null value in long form),
recorded in preclin.evidence_line_build with a fingerprint of its inputs (input_fingerprint), which `check`
compares with the inputs now. Report modules otherwise only read; this one writes because
the compiled dataset is what other sessions and analyses query, and it should not have to be rebuilt
from code to be read.
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


@dataclass(frozen=True)
class Line:
    label: str  # plain English, as the report shows it
    column: str | None  # entries.csv column; None while its source table is still being built
    applies: str = "all"  # entries the line is scored on (APPLIES)
    status: str = ""  # why a line has no column
    descriptive: bool = False  # shown in coverage but not part of its category
    key: str | None = None  # the registry key of a line with no column, fixed so that rewording the label keeps it


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
    "small_molecule_profiled": lambda d: d.modality.eq("small_molecule") & d.drug_like.notna(),
    "brain": lambda d: d.modality.eq("small_molecule") & d.bio_area.isin(BRAIN),
    "phase_2_3": lambda d: d.phase.ge(2),
    "from_2011": lambda d: d.has_target_disease & d.entry_year.ge(FAILURES_FROM),
    "onc_screened": lambda d: d.has_target_disease & d.regime.eq("ONC") & d.entry_year.ge(CELL_SCREENS_FROM),
    "disease": lambda d: d.mondo_id.fillna("").ne(""),
}
WITHIN = {"small_molecule_profiled": "small_molecule", "onc_screened": "target"}  # an APPLIES key whose entries all lie in another's

# Category -> (category line, subcategories), efficacy categories grouped by the experimental system that
# produced the evidence. A category line is rolled up from its subcategories (category_columns).
CATEGORIES: dict[str, tuple[Line, list[Line]]] = {
    "human_genetics": (Line("Human genetics", "cat_human_genetics", "target"), [
        Line("Inherited variants linked to the disease", "g3", "target"),
        Line("Rare inherited variants, including single-gene disease", "rare_variant", "target"),
        Line("Common variants (genome-wide association studies)", "gwas", "target"),
        Line("Both common and rare variants", "allelic_series", "target"),
        Line("Genetics agrees with the drug's direction", "genetics_concordant", "target"),
        Line("A curated pathway shows a disease mutation disrupting the target", "reactome", "target"),
    ]),
    "tumour_genetics": (Line("Tumour genetics", "cat_tumour_genetics", "ONC"), [
        Line("Gene recurrently mutated in this cancer", "somatic", "ONC"),
        Line("The mutation's effect matches the drug's action", "somatic_concordant", "ONC"),
    ]),
    "diseased_tissue": (Line("Human diseased tissue", "cat_diseased_tissue", "target"), [
        Line("The gene's RNA level differs in diseased tissue", "expression", "target"),
        Line("Target more active in disease, and the drug blocks it", "expression_up_inhibitor", "target"),
    ]),
    "animal": (Line("Animal studies", "cat_animal", "target"), [
        Line("Mice with the gene altered show the disease", "altered_animal", "target"),
        Line("Mouse model from published studies", "mgi", "target"),
        Line("Mouse knockout from a large-scale screen", "impc", "target"),
        Line("Mouse symptoms closely match the disease", "animal_close", "target"),
        Line("Mouse result agrees with the drug's direction", "animal_concordant", "target"),
        Line("The drug in an animal model of the disease", "lit_animal_disease", "disease",
             literature_note("animal_disease", exploratory=True), key="the_drug_in_an_animal_model_of_the_disease"),
        Line("The drug tested in healthy animals", "lit_animal_healthy", "all",
             literature_note("animal_healthy", exploratory=False), key="the_drug_s_pharmacology_in_healthy_animals"),
    ]),
    "cell": (Line("Cell studies", "cat_cell", "onc_screened"), [
        Line("Gene-knockout screens in human cells", "crispr", "target"),
        Line("Cancer cells of this type need the gene to grow", "cell_dependency", "onc_screened"),
        Line("Gene-knockout screens in human cells, with hindsight", "crispr_untimed", "target", descriptive=True),
    ]),
    "molecule": (Line("The molecule", "cat_molecule", "small_molecule_profiled"), [
        Line("Drug binds its target strongly (100 nM or better)", "potent_100nm", "small_molecule"),
        Line("Drug binds its target very strongly (10 nM or better)", "potent_10nm", "small_molecule",
             descriptive=True),
        Line("Drug binds its target 10× more strongly than other proteins tested", "selective", "small_molecule"),
        Line("Drug-like size and chemistry", "drug_like", "small_molecule"),
        Line("Chemistry suited to entering the brain (brain diseases)", "brain_penetrant", "brain"),
    ]),
    "early_human": (Line("Early studies of the drug in people", None, "phase_2_3",
                         literature_note("human_engagement", exploratory=False), key="early_human_pharmacology"), [
        Line("Drug shown to act on its target in people", "lit_human_engagement", "phase_2_3",
             literature_note("human_engagement", exploratory=False), key="target_engagement_measured_in_people"),
    ]),
    "safety_risk": (Line("Safety risk", "liability", "target"), [
        Line("People rarely carry broken copies of the gene", "constrained", "target"),
        Line("Mice without the gene die young", "ko_lethal", "target"),
        Line("Most human cell types need the gene", "pan_essential", "target"),
        Line("Most human cell types need the gene, with hindsight", "pan_essential_untimed", "target",
             descriptive=True),
    ]),
    "precedent": (Line("Earlier drugs on the same target", "cat_precedent", "target"), [
        Line("A drug on the target already approved for a related disease", "b1", "target"),
        Line("A drug on the target approved only for unrelated diseases", "approved_unrelated_only", "target"),
        Line("Another drug on the target failed in a related disease in the last 3 years", "earlier_failure",
             "from_2011"),
    ]),
}
ADJUSTMENTS = [Line("Trial enrolled patients selected by a biomarker", "biomarker_selected", "all")]

# The evidence chart's grouping (exploratory, added 2026-11-05; report/translation_plan.md): one question per area, its
# tiers mutually exclusive. The registered CATEGORIES above stay the confirmatory grouping and the appendix table's.
AREAS: dict[str, tuple[Line, list[Line]]] = {
    "human_genetics": (Line("Human genetics: inherited variants link the target to the disease", "g3", "target"), [
        Line("Rare variants only", "tier_rare_only", "target"),
        Line("Common variants only (genome-wide association studies)", "tier_common_only", "target"),
        Line("Both rare and common variants", "allelic_series", "target"),
    ]),
    "pathway": (Line("Curated pathways: a disease mutation is shown disrupting the target's pathway", "reactome",
                     "target"), []),
    "tumour_genetics": (Line("Tumour genetics: the gene is recurrently mutated in this cancer", "somatic", "ONC"), [
        Line("The mutation's effect matches the drug's action", "somatic_concordant", "ONC"),
        Line("It does not, or its effect is unknown", "tier_mutation_other", "ONC"),
    ]),
    "diseased_tissue": (Line("Diseased tissue: the gene's RNA level differs in diseased tissue", "expression",
                             "target"), []),
    "animal": (Line("Mouse models: mice with the gene altered show the disease", "altered_animal", "target"), [
        Line("Mouse symptoms closely match the disease", "animal_close", "target"),
        Line("Looser match", "tier_mouse_loose", "target"),
    ]),
    "molecule": (Line("The drug: its binding to the target was measured before entry", "area_measured",
                      "small_molecule"), [
        Line("Binds strongly (100 nM or better) and selectively", "tier_strong_selective", "small_molecule"),
        Line("Binds strongly, selectivity not shown", "tier_strong_only", "small_molecule"),
        Line("Binds more weakly than 100 nM", "tier_weaker", "small_molecule"),
    ]),
    "published_animal": (Line("Published animal studies of the drug before entry (exploratory)", "area_lit_animal", "all"), [
        Line("In an animal model of the disease", "lit_animal_disease", "all"),
        Line("Only in healthy animals", "tier_lit_healthy_only", "all"),
    ]),
    "early_human": (Line("Published study of the drug acting on its target in people (exploratory)", "lit_human_engagement",
                         "phase_2_3"), []),
    "safety_risk": (Line("Target safety risk", "liability", "target"), [
        Line("Only: people rarely carry broken copies of the gene", "tier_constrained_only", "target"),
        Line("Only: mice without the gene die young", "tier_lethal_only", "target"),
        Line("Both", "tier_constrained_and_lethal", "target"),
    ]),
    "precedent": (Line("Earlier drugs on the same target", "cat_precedent", "target"), [
        Line("Approved for a related disease", "b1", "target"),
        Line("Approved only for unrelated diseases", "approved_unrelated_only", "target"),
        Line("No approval, but another drug failed in a related disease in the last 3 years", "tier_failure_only",
             "from_2011"),
    ]),
}


def area_lines() -> list[Line]:
    return [ln for line, tiers in AREAS.values() for ln in (line, *tiers)]


def area_alone() -> set[str]:
    """Columns of the area tiers scored on fewer entries than their area, which the chart marks."""
    return {t.column for line, tiers in AREAS.values() for t in tiers if t.applies != line.applies}


def area_columns(d: pd.DataFrame) -> pd.DataFrame:
    """The columns AREAS adds to the entries: each tier that no line already gives, so that an area's tiers are
    mutually exclusive, and the areas no line already gives. Null outside the entries a line applies to."""
    t = d.has_target_disease
    flag = lambda s, scope=t: s.astype(float).where(scope)  # noqa: E731
    rare, common, potent = d.rare_variant.gt(0), d.gwas.gt(0), d.potent_100nm.gt(0)
    measured, small = d.assay_best.notna(), APPLIES["small_molecule"](d)
    screened = d.lit_animal_healthy.notna()  # the drug's literature was retrieved and screened
    return pd.DataFrame({
        "tier_rare_only": flag(rare & ~common),
        "tier_common_only": flag(common & ~rare),
        "tier_mutation_other": flag(d.somatic.gt(0) & ~d.somatic_concordant.gt(0), APPLIES["ONC"](d)),
        "tier_mouse_loose": flag(d.altered_animal.gt(0) & ~d.animal_close.gt(0)),
        "area_measured": flag(measured, small),
        "tier_strong_selective": flag(potent & d.selective.gt(0), small),
        "tier_strong_only": flag(potent & ~d.selective.gt(0), small),
        "tier_weaker": flag(measured & ~potent, small),
        "tier_constrained_only": flag(d.constrained.gt(0) & ~d.ko_lethal.gt(0)),
        "tier_lethal_only": flag(d.ko_lethal.gt(0) & ~d.constrained.gt(0)),
        "tier_constrained_and_lethal": flag(d.constrained.gt(0) & d.ko_lethal.gt(0)),
        "tier_failure_only": flag(d.earlier_failure.gt(0) & ~d.precedent.gt(0), APPLIES["from_2011"](d)),
        "area_lit_animal": flag(d.lit_animal_disease.gt(0) | d.lit_animal_healthy.gt(0), screened),
        "tier_lit_healthy_only": flag(d.lit_animal_healthy.gt(0) & ~d.lit_animal_disease.gt(0), screened),
    }, index=d.index)


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
    return {"assay_best": a["best"], "assay_margin": a["margin"],
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
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT s.moiety_id FROM preclin.literature_search s GROUP BY 1
                       HAVING NOT EXISTS (SELECT 1 FROM preclin.literature_hit h WHERE h.moiety_id = s.moiety_id)
                       UNION SELECT moiety_id FROM preclin.literature_screen
                       UNION SELECT moiety_id FROM preclin.literature_prefilter""")
        screened = {r[0] for r in cur.fetchall()}
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

    t = d.has_target_disease
    flag = lambda s: s.astype(float).where(t)  # noqa: E731
    d["rare_variant"] = flag((d.burden > 0) | (d.mendelian > 0))
    d["allelic_series"] = flag((d.gwas > 0) & ((d.burden > 0) | (d.mendelian > 0)))
    d["genetics_concordant"] = flag(d.mechanism.eq("concordant"))
    d["expression_up_inhibitor"] = flag((d.expression_up > 0) & d.sign.eq("decrease"))
    d["altered_animal"] = flag((d.mgi > 0) | (d.impc > 0))
    d["animal_close"] = flag((d.mgi_strong > 0) | (d.impc_strong > 0))
    d["animal_concordant"] = flag(d.mouse_direction.eq("concordant"))
    d["approved_unrelated_only"] = flag((d.precedent > 0) & ~(d.b1 > 0))
    d = d.join(category_columns(d))
    d = d.join(area_columns(d))
    d["biomarker_selected"] = biomarker_selected(
        d, trials, frame.query("SELECT nct_id, selected FROM preclin.trial_biomarker_selection"))
    d["entry_date"] = pd.to_datetime(d.entry).dt.date
    d["era"] = pd.cut(d.entry_year, ERA_BINS, labels=ERA_LABELS).astype(str)
    keep = ["moiety_id", "mondo_id", "phase", "program_id", "entry_date", "entry_year", "era", "regime", "bio_area",
            "modality", "novel", "precedent", "target", "sign", "event", "s4", "has_target_disease", "assay_best",
            "assay_margin",
            *(ln.column for ln in lines() if ln.column), *(ln.column for ln in area_lines())]
    return d[list(dict.fromkeys(keep))].sort_values(["moiety_id", "mondo_id", "phase"]).reset_index(drop=True)


def in_category(line: Line, sub: Line) -> bool:
    """Whether a subcategory makes up its category: it has a column, is not descriptive, and is scored on every
    entry the category applies to."""
    return bool(sub.column) and not sub.descriptive and sub.applies in (line.applies, WITHIN.get(line.applies))


def category_columns(d: pd.DataFrame) -> pd.DataFrame:
    """Each category line: 1 when any of its subcategories is, 0 when none is, among the entries the category
    applies to. Only subcategories scored on all of those entries (the same APPLIES key, or the one WITHIN names)
    make it up, so a category means the same thing across its scope: a line scored on later entries or on some
    disease areas only stays out. An entry on which none of them is known is null rather than 0."""
    out = {}
    for line, subs in CATEGORIES.values():
        if not (line.column and line.column.startswith("cat_")):
            continue
        cols = [s.column for s in subs if in_category(line, s)]
        known = d[cols].notna().any(axis=1)
        out[line.column] = d[cols].gt(0).any(axis=1).astype(float).where(APPLIES[line.applies](d) & known)
    return pd.DataFrame(out, index=d.index)


def biomarker_selected(rows: pd.DataFrame, trials: pd.DataFrame, sel: pd.DataFrame) -> pd.Series:
    """1 when an industry trial that opened the entry's phase on the entry date restricts enrolment by a
    molecular biomarker, 0 when such trials were labelled and none does, null when none was labelled."""
    opening = trials[trials.industry & trials.starts_phase][["program_id", "nct_id", "phase", "start_date"]]
    opening = opening.assign(start_date=pd.to_datetime(opening.start_date)).merge(sel, on="nct_id")
    keyed = rows[["program_id", "phase", "entry"]].assign(entry=pd.to_datetime(rows.entry), _row=rows.index)
    m = keyed.merge(opening, left_on=["program_id", "phase", "entry"], right_on=["program_id", "phase", "start_date"])
    return m.groupby("_row").selected.any().astype(float).reindex(rows.index)


def lines() -> list[Line]:
    return [ln for line, subs in CATEGORIES.values() for ln in (line, *subs)] + ADJUSTMENTS


def coverage(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups = [(cat, [("category", line), *(("descriptive" if s.descriptive else "subcategory", s) for s in subs)])
              for cat, (line, subs) in CATEGORIES.items()] + [("adjustment", [("adjustment", a) for a in ADJUSTMENTS])]
    for cat, members in groups:
        for level, ln in members:
            row = {"category": cat, "level": level, "line": ln.label, "column": ln.column, "applies": ln.applies,
                   "status": ln.status}
            if ln.column:
                v = d[ln.column].where(APPLIES[ln.applies](d))
                elig, exp = v.notna(), v.fillna(0) > 0
                row |= {"eligible": int(elig.sum()), "exposed": int(exp.sum()),
                        "share": round(exp.sum() / max(elig.sum(), 1), 4),
                        "distinct_targets": int(d.loc[exp, "target"].nunique()),
                        **{f"share_phase_{p}": round((exp & d.phase.eq(p)).sum() / max((elig & d.phase.eq(p)).sum(), 1), 4)
                           for p in (1, 2, 3)}}
            rows.append(row)
    return pd.DataFrame(rows)


MEASUREMENTS = [  # raw values behind the molecule lines, stored alongside them
    Line("Best potency at the primary target (pChEMBL)", "assay_best", "small_molecule"),
    Line("Selectivity margin over the best off-target (log units)", "assay_margin", "small_molecule"),
]
ENTRY_COLUMNS = ["entry_date", "entry_year", "regime", "bio_area", "modality", "novel", "target", "has_target_disease",
                 "biomarker_selected"]


def slug(label: str) -> str:
    return "_".join("".join(c if c.isalnum() else " " for c in label.lower()).split())


def registry() -> pd.DataFrame:
    """One row per line in display order: line_key, category, level, label, applies, status."""
    rows = []
    for cat, (line, subs) in CATEGORIES.items():
        rows.append((line, cat, "category"))
        rows += [(s, cat, "descriptive" if s.descriptive else "subcategory") for s in subs]
    rows += [(a, "adjustment", "adjustment") for a in ADJUSTMENTS]
    rows += [(m, "molecule", "measurement") for m in MEASUREMENTS]
    return pd.DataFrame([{"line_key": ln.column or ln.key or slug(ln.label), "position": i, "category": cat,
                          "level": level,
                          "label": ln.label, "applies": ln.applies, "status": ln.status}
                         for i, (ln, cat, level) in enumerate(rows)])


def long_form(d: pd.DataFrame, reg: pd.DataFrame) -> pd.DataFrame:
    """Each entry's non-null value on each line with values, masked to the entries the line applies to.
    The adjustment lives on preclin.evidence_entry, so it is not repeated here."""
    keyed = d.assign(mondo_id=d.mondo_id.fillna(""))
    parts = []
    for r in reg[reg.level.ne("adjustment") & reg.line_key.isin(d.columns)].itertuples():
        v = keyed[r.line_key].astype(float).where(APPLIES[r.applies](keyed))
        part = keyed.loc[v.notna(), ["moiety_id", "mondo_id", "phase"]].assign(line_key=r.line_key, value=v[v.notna()])
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


def store(d: pd.DataFrame) -> str:
    """Replace the dataset in Postgres in one transaction; returns the build id."""
    reg = registry()
    lines_long = long_form(d, reg)
    e = d.assign(mondo_id=d.mondo_id.fillna(""), entry_date=pd.to_datetime(d.entry_date).dt.date,
                 biomarker_selected=d.biomarker_selected.map({1.0: True, 0.0: False}))
    build_id, fingerprint = str(uuid.uuid4()), input_fingerprint()
    nul = lambda v: None if pd.isna(v) else v.item() if hasattr(v, "item") else v  # noqa: E731  numpy scalars
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.evidence_entry_line")
        cur.execute("DELETE FROM preclin.evidence_entry")
        cur.execute("DELETE FROM preclin.evidence_line")
        cur.execute("""INSERT INTO preclin.evidence_line_build (build_id, code_commit, snapshot, n_entries, inputs)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (build_id, llm.git_commit(), frame.snapshot(), len(e), Json(fingerprint)))
        execute_values(cur, """INSERT INTO preclin.evidence_line (line_key, position, category, level, label, applies,
                                                                  status, build_id) VALUES %s""",
                       [(*r, build_id) for r in reg.itertuples(index=False)])
        execute_values(cur, f"""INSERT INTO preclin.evidence_entry (moiety_id, mondo_id, phase, {", ".join(ENTRY_COLUMNS)},
                                                                    build_id) VALUES %s""",
                       [(int(r.moiety_id), r.mondo_id, int(r.phase), *(nul(getattr(r, c)) for c in ENTRY_COLUMNS),
                         build_id) for r in e.itertuples()], page_size=2000)
        execute_values(cur, """INSERT INTO preclin.evidence_entry_line (moiety_id, mondo_id, phase, line_key, value)
                               VALUES %s""",
                       [(int(r.moiety_id), r.mondo_id, int(r.phase), r.line_key, float(r.value))
                        for r in lines_long.itertuples()], page_size=5000)
        conn.commit()
    print(f"stored build {build_id}: {len(reg)} lines, {len(e)} entries, {len(lines_long)} values")
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
    print(cov.drop(columns=["applies"]).to_string(index=False))
    if sys.argv[1:] == ["store"]:
        store(d)


if __name__ == "__main__":
    main()
