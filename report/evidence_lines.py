"""The evidence-line dataset of the 2026-11-03 plan amendment (report/translation_plan.md).

    python -m report.evidence_lines

One row per US-developed phase entry in 2008-2019 (report.section1.phase_rows with a US-sited
industry trial in the phase, skipped phases excluded), keyed by (moiety_id, mondo_id, phase), with
every category and subcategory of CATEGORIES frozen at the year before entry, and the outcome
columns event and s4. Target-level lines come from report.section3.Evidence and are null for
entries without a single resolved human protein target and a disease; molecule lines from ChEMBL
potency measurements (report.frame.assays_as_of) and computed properties (preclin.moiety_property),
and are null outside small molecules. Descriptive lines (10 nM potency, hindsight lines) are shown
in coverage but do not make up their category.

Writes report/output/evidence_lines/: entries.csv, and coverage.csv with each line's eligible
and exposed entries, distinct exposed targets and exposed share by phase. No line is compared
with an outcome here.
"""
from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd

from report import frame
from report.section3 import RELATED, Evidence, cohorts, entries

OUT = os.path.join(frame.REPO, "report", "output", "evidence_lines")
LOOKBACK_YEARS = 3  # earlier failed trials on the target count when they ended this long before entry
FAILURES_FROM = 2011  # first entry year whose lookback lies wholly in the era of registered results
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
    pending: str = ""  # the migration that will supply a line with no column yet
    descriptive: bool = False  # shown in coverage but not part of its category


APPLIES = {
    "all": lambda d: d.index == d.index,
    "target": lambda d: d.has_target_disease,
    "ONC": lambda d: d.has_target_disease & d.regime.eq("ONC"),
    "small_molecule": lambda d: d.modality.eq("small_molecule"),
    "brain": lambda d: d.modality.eq("small_molecule") & d.bio_area.isin(BRAIN),
    "phase_2_3": lambda d: d.phase.ge(2),
    "from_2011": lambda d: d.has_target_disease & d.entry_year.ge(FAILURES_FROM),
}

# Category -> (category line, subcategories). The category line is exposed when any subcategory is;
# efficacy categories are grouped by the experimental system that produced the evidence.
CATEGORIES: dict[str, tuple[Line, list[Line]]] = {
    "human_genetics": (Line("Human genetics", "cat_human_genetics", "target"), [
        Line("Germline genetics for the disease", "g3", "target"),
        Line("Rare-variant or Mendelian", "rare_variant", "target"),
        Line("GWAS", "gwas", "target"),
        Line("GWAS and rare-variant evidence together", "allelic_series", "target"),
        Line("Genetics points the same way as the drug", "genetics_concordant", "target"),
        Line("Curated disease mechanism (Reactome)", "reactome", "target"),
    ]),
    "tumour_genetics": (Line("Tumour genetics", "cat_tumour_genetics", "ONC"), [
        Line("Gene recurrently mutated in this cancer", "somatic", "ONC"),
        Line("Mutation matches the drug", "somatic_concordant", "ONC"),
    ]),
    "diseased_tissue": (Line("Human diseased tissue", "cat_diseased_tissue", "target"), [
        Line("Target's RNA level changed in diseased tissue", "expression", "target"),
        Line("RNA raised, with a drug that lowers function", "expression_up_inhibitor", "target"),
    ]),
    "animal": (Line("Animal studies", "cat_animal", "target"), [
        Line("Genetically altered animals with the disease's phenotype", "altered_animal", "target"),
        Line("Literature-curated mouse model (MGI)", "mgi", "target"),
        Line("Systematic knockout screen (IMPC)", "impc", "target"),
        Line("Close phenotype match (top quartile)", "animal_close", "target"),
        Line("Altered animal points the same way as the drug", "animal_concordant", "target"),
        Line("The drug in an animal model of the disease", None, "all", "119 literature screens (pilot)"),
        Line("The drug's pharmacology in healthy animals", None, "all", "119 literature screens (pilot)"),
    ]),
    "cell": (Line("Cell studies", "cat_cell", "target"), [
        Line("CRISPR screen in cells", "crispr", "target"),
        Line("CRISPR screen in cells, on today's data (hindsight)", "crispr_untimed", "target", descriptive=True),
    ]),
    "molecule": (Line("The molecule", "cat_molecule", "small_molecule"), [
        Line("Potency at the primary target, 100 nM or better", "potent_100nm", "small_molecule"),
        Line("Potency at the primary target, 10 nM or better", "potent_10nm", "small_molecule", descriptive=True),
        Line("At least 10-fold selective over measured off-targets", "selective", "small_molecule"),
        Line("Drug-like (at most one Rule-of-5 violation)", "drug_like", "small_molecule"),
        Line("Brain-penetrant properties (neurology and psychiatry)", "brain_penetrant", "brain"),
    ]),
    "early_human": (Line("Early human pharmacology", None, "phase_2_3", "119 literature screens (pilot)"), [
        Line("Target engagement measured in people", None, "phase_2_3", "119 literature screens (pilot)"),
    ]),
    "safety_risk": (Line("Safety risk", "liability", "target"), [
        Line("Intolerant of loss of function", "constrained", "target"),
        Line("Mouse knockout dies before weaning", "ko_lethal", "target"),
        Line("Essential in most cell lines", "pan_essential", "target"),
        Line("Essential in most cell lines, on today's data (hindsight)", "pan_essential_untimed", "target",
             descriptive=True),
    ]),
    "precedent": (Line("Clinical precedent (benchmark)", "cat_precedent", "target"), [
        Line("Approved drug on the target, related disease", "b1", "target"),
        Line("Approved drug on the target, unrelated disease only", "approved_unrelated_only", "target"),
        Line("Earlier failed trial on the target, related disease, within 3 years", "earlier_failure", "from_2011"),
    ]),
}
ADJUSTMENTS = [Line("Biomarker-selected enrollment", "biomarker_selected", "all")]


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
    for cat, (line, subs) in CATEGORIES.items():
        cols = [s.column for s in subs if s.column and not s.descriptive]
        if line.column and line.column.startswith("cat_"):
            d[line.column] = d[cols].gt(0).any(axis=1).astype(float).where(APPLIES[line.applies](d))
    d["biomarker_selected"] = biomarker_selected(
        d, trials, frame.query("SELECT nct_id, selected FROM preclin.trial_biomarker_selection"))
    d["entry_date"] = pd.to_datetime(d.entry).dt.date
    keep = ["moiety_id", "mondo_id", "phase", "entry_date", "entry_year", "regime", "bio_area", "modality", "novel",
            "target", "sign", "event", "s4", "has_target_disease", "assay_best", "assay_margin",
            *(ln.column for ln in lines() if ln.column)]
    return d[list(dict.fromkeys(keep))].sort_values(["moiety_id", "mondo_id", "phase"]).reset_index(drop=True)


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
                   "pending": ln.pending}
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


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    d = build()
    d.to_csv(os.path.join(OUT, "entries.csv"), index=False)
    cov = coverage(d)
    cov.to_csv(os.path.join(OUT, "coverage.csv"), index=False)
    print(f"entries {len(d)}; with a target and a disease {int(d.has_target_disease.sum())}")
    print(cov.drop(columns=["applies"]).to_string(index=False))


if __name__ == "__main__":
    main()
