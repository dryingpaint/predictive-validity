"""The evidence-category analysis of the 2026-11-03 plan amendment (report/translation_plan.md).

    python -m report.evidence_analysis

Cohort: report.evidence_lines.build(), US-developed phase entries 2008-2019. For every category and
subcategory of report.evidence_lines.CATEGORIES, among the entries it applies to:
- relative success: likelihood of approval from Phase 1 with the line over without it (report.section2
  relative_success), on the entries' BIO-style phase rows, skipped phases counted as successes with the
  features of the entry that skipped them;
- the adjusted risk ratio of S4 among Phase 2 entries (report.section3: modified Poisson, errors clustered
  by primary-target set, adjusted for disease area, modality, entry period, novelty and target precedent, the
  last left out for the clinical-precedent lines, which it would adjust for themselves; an entry with no
  resolved target is its own cluster and has no precedent),
  again with biomarker-selected enrolment added as a sensitivity;
- for efficacy categories, the adjusted risk ratio of an efficacy stop among Phase 2 and 3 entries; for
  safety risk, of a safety stop among Phase 1-3 entries.
A line exposed in fewer than MIN_ENTRIES entries or MIN_TARGETS distinct target sets is described, not
estimated. Descriptive lines (hindsight, 10 nM potency) are estimated alongside but make up no category.
N1-N3 are tested as the plan words them and Holm-corrected together.

Writes report/output/evidence_analysis/: lines.csv and numbers.json, which also carries the literature
gate results (report/audits/literature_gate.json) that leave the literature lines descriptive.
"""
from __future__ import annotations

import json
import os

import pandas as pd

from report import frame
from report.evidence_lines import ADJUSTMENTS, APPLIES, CATEGORIES, build, stale
from report.section1 import failure_modes, phase_rows
from report.section2 import relative_success
from report.section3 import COVARS, MIN_TARGETS, adjusted, cause_outcomes, describe, estimate, holm, jsonable
from report.windows import SECTION1

OUT = os.path.join(frame.REPO, "report", "output", "evidence_analysis")
LITERATURE_GATE = os.path.join(frame.REPO, "report", "audits", "literature_gate.json")  # pipeline.literature
MIN_ENTRIES = 100  # exposed entries below which a line is described, not estimated
NOT_EFFICACY = ("safety_risk", "precedent")  # categories that are not evidence the drug will work
COVARS_23 = (*COVARS, "phase")


def loa_rows(d: pd.DataFrame, rows: pd.DataFrame) -> pd.DataFrame:
    """The entries' phase rows (report.section1.phase_rows) for likelihood of approval: each entry, plus the
    phases it skipped on the way to its next phase or approval, which carry the skipping entry's features."""
    cols = [c for c in d.columns if c not in rows.columns or c in ("program_id", "phase")]
    own = rows[~rows.credited].merge(d[cols], on=["program_id", "phase"])
    first = d.sort_values("phase").drop_duplicates(["program_id", "entry_date"])
    skipped = rows[rows.credited].assign(entry_date=pd.to_datetime(rows.entry).dt.date) \
        .merge(first[[c for c in cols if c != "phase"]], on=["program_id", "entry_date"])
    return pd.concat([own, skipped], ignore_index=True)


def exposed_enough(desc: dict) -> bool:
    return desc["n"] >= MIN_ENTRIES and desc["n_targets"] >= MIN_TARGETS


def line_row(cat: str, level: str, line, d: pd.DataFrame, lr: pd.DataFrame) -> dict:
    row = {"category": cat, "level": level, "label": line.label, "column": line.column, "applies": line.applies,
           "status": line.status}
    if not line.column:
        return row
    elig = d[line.column].notna() & APPLIES[line.applies](d)
    x = d.loc[elig].assign(x=d.loc[elig, line.column].astype(float))
    desc = describe(x.assign(any_outcome=1.0), "any_outcome", "x")
    row |= {"eligible": int(elig.sum()), "exposed": desc["n"], "targets": desc["n_targets"],
            "estimated": exposed_enough(desc)}
    if not row["estimated"]:
        return row
    keys = x[["program_id", "entry_date", "x"]].drop_duplicates(["program_id", "entry_date"])
    rs = relative_success(lr.merge(keys, on=["program_id", "entry_date"]), "x")
    row |= {f"rs_{k}": rs[k] for k in ("rs", "rs_lo", "rs_hi", "loa_with", "loa_without")}
    c2 = x[x.phase == 2]
    base = tuple(c for c in COVARS if not (cat == "precedent" and c == "precedent"))  # not the exposure itself
    for prefix, part, outcome, covars in (
            ("s4", c2, "s4", base),
            ("s4_biomarker", c2.assign(biomarker_selected=c2.biomarker_selected.fillna(0)), "s4",
             (*base, "biomarker_selected")) if cat != "adjustment" else (None,) * 4,  # it is the exposure there
            ("efficacy_stop", x[x.phase >= 2], "f_efficacy", COVARS_23) if cat not in NOT_EFFICACY else (None,) * 4,
            ("safety_stop", x, "f_safety", COVARS_23) if cat == "safety_risk" else (None,) * 4):
        if prefix is None:
            continue
        r = estimate(part, outcome, "x", covars)
        row |= {f"{prefix}_{k}": r.get(k) for k in ("n", "n_targets", "ppv", "rate_without", "rr", "lo", "hi", "p")}
    return row


def hypotheses(d: pd.DataFrame) -> dict:
    """N1-N3 as worded in the plan, on Phase 2 entries; N2's two claims are tested together by
    taking the larger p (intersection-union)."""
    c2 = d[(d.phase == 2) & d.modality.eq("small_molecule")]
    n = {"N1": estimate(c2[c2.selective.notna()], "s4", "selective"),
         "N2": {"drug_like": estimate(c2[c2.drug_like.notna()], "s4", "drug_like"),
                "brain_penetrant": estimate(c2[c2.brain_penetrant.notna()], "s4", "brain_penetrant")}}
    n["N2"]["p"] = max(n["N2"]["drug_like"].get("p", 1.0), n["N2"]["brain_penetrant"].get("p", 1.0))
    n3 = c2[c2.regime.ne("ONC") & c2.has_target_disease & c2.drug_like.notna()]
    n["N3"] = {**describe(n3, "s4", "potent_100nm"),
               **adjusted(n3, "s4", ["potent_100nm", "cat_human_genetics", "drug_like"])}
    n["holm"] = holm({"N1": n["N1"].get("p"), "N2": n["N2"]["p"], "N3": n["N3"].get("p")})
    n["holm_min"] = min(n["holm"].values())
    return n


def analyse(d: pd.DataFrame, rows: pd.DataFrame, fm: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """The lines table and numbers from the evidence-line dataset, the phase rows and the failure modes."""
    d = d.assign(precedent=d.precedent.fillna(0),  # no resolved target: no approved drug known on it
                 target=d.target.fillna("entity " + d.moiety_id.astype(str)))  # and it is its own cluster
    d = cause_outcomes(d.merge(fm[["program_id", "phase", "reason"]], on=["program_id", "phase"], how="left"))
    lr = loa_rows(d, rows[rows.us_site])
    out = []
    for cat, (line, subs) in CATEGORIES.items():
        out.append(line_row(cat, "category", line, d, lr))
        out += [line_row(cat, "descriptive" if s.descriptive else "subcategory", s, d, lr) for s in subs]
    out += [line_row("adjustment", "adjustment", a, d, lr) for a in ADJUSTMENTS]
    c2 = d[d.phase == 2]
    n = {"cohort": {"entries": int(len(d)), "programs": int(d.program_id.nunique()),
                    "with_target_disease": int(d.has_target_disease.sum()), "phase2": int(len(c2)),
                    "phase2_s4": float(c2.s4.mean()), "biomarker_selected": float(d.biomarker_selected.mean()),
                    "min_entries": MIN_ENTRIES, "min_targets": MIN_TARGETS},
         "lines": {r["column"]: {k: v for k, v in r.items() if k != "column"} for r in out if r.get("column")},
         "literature_gate": literature_gate(),
         **hypotheses(d)}
    return pd.DataFrame(out), n


def literature_gate() -> dict:
    """Recall of each literature version and kind against its blind reference set, and the gates."""
    g = json.load(open(LITERATURE_GATE))
    return {v: {"gates": g[v]["gates"], **{k: {f: r[f] for f in ("recall", "recall_pubmed_indexed", "passes")}
                                           for k, r in g[v]["kinds"].items()}} for v in ("v1", "v2")}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    if changed := stale():  # the analysis builds its own rows; the stored copy others query should match them
        print(f"[evidence_analysis] warning: the stored evidence dataset is stale ({', '.join(changed)}); "
              "run python -m report.evidence_lines store", flush=True)
    snap = frame.snapshot()
    progs, trials, outcomes = frame.programs(), frame.program_trials(), frame.trial_outcomes()
    rows = phase_rows(progs, trials, snap, window=SECTION1)
    lines, n = analyse(build(), rows, failure_modes(rows, progs, trials, outcomes))
    lines.to_csv(os.path.join(OUT, "lines.csv"), index=False)
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(jsonable(n), f, indent=1)


if __name__ == "__main__":
    main()
