"""The evidence-category analysis of the 2026-11-03 plan amendment (report/translation_plan.md, removed; last version at 8e02c3e).

    python -m report.evidence_analysis

Cohort: the US-developed phase entries 2008-2019 of report.evidence_lines.build (us). For every line of
report.evidence_lines.report_lines (each kind of evidence, each evidence value of its facts, and the aggregates and
crosses derived from them), among the entries it is known for:
- relative success: likelihood of approval from Phase 1 with the line over without it (report.section2
  relative_success), on the entries' BIO-style phase rows, skipped phases counted as successes with the
  features of the entry that skipped them;
- the adjusted risk ratio of S4 among Phase 2 entries (report.section3: modified Poisson, errors clustered
  by primary-target set, adjusted for disease area, modality, entry period, novelty and target precedent, the
  last left out for the clinical-precedent lines, which it would adjust for themselves; an entry with no
  resolved target is its own cluster and has no precedent),
  again with biomarker-selected enrolment added as a sensitivity;
- for every kind but target safety risk, the adjusted risk ratio of an efficacy stop among Phase 2 and 3 entries;
  for target safety risk, of a safety stop among Phase 1-3 entries.
For the stop-risk figure, each kind of evidence and each safety line (report.evidence_lines.SAFETY) is also tested
against the traced cause of each stop (report.stop_causes: the cause, or the likely cause where no source states
one): the adjusted risk ratio of stopping for efficacy or exposure and for safety, and of the efficacy stop split
into whether the drug adequately reached its target and, where it did, efficacy proper (stop_outcomes), among Phase 1-3 entries,
adjusted as above with phase added. A stop for any other reason is not an event of either.
A line exposed in fewer than MIN_ENTRIES entries or MIN_TARGETS distinct target sets is described, not
estimated. Hindsight and exploratory facts are estimated alongside but make up no kind.
N1-N3 are tested as the plan words them and Holm-corrected together.

The published-animal-study finding is then tested on the later entries of report.windows.CONFIRM, as registered in
issue #140 (published_confirmation).

Writes report/output/evidence_analysis/: lines.csv (every line, kind by kind), chart.csv (the evidence chart's rows,
report.evidence_lines.chart_rows), stop_risk.csv (the stop-risk figure's rows) and
numbers.json, which also carries the literature
gate results (report/audits/literature_gate.json) that leave the literature lines descriptive.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from report import frame
from pipeline.stops import keys
from report import stop_causes
from report.evidence_lines import APPROVAL_SPLIT, KINDS, PRECEDENT_KINDS, SAFETY, build, chart_rows, loa_rows, report_lines, stale, us
from report.section1 import failure_modes, phase_rows
from report.section2 import relative_success
from report.section3 import COVARS, MIN_TARGETS, adjusted, cause_outcomes, coef, describe, estimate, holm, jsonable, poisson, sponsors
from report.windows import CONFIRM, SECTION1

OUT = os.path.join(frame.REPO, "report", "output", "evidence_analysis")
LITERATURE_GATE = os.path.join(frame.REPO, "report", "audits", "literature_gate.json")  # pipeline.literature
MIN_ENTRIES = 100  # exposed entries below which a line is described, not estimated
COVARS_23 = (*COVARS, "phase")


def exposed_enough(desc: dict) -> bool:
    return desc["n"] >= MIN_ENTRIES and desc["n_targets"] >= MIN_TARGETS


def line_row(kind: str, category: str, about: str, level: str, line, d: pd.DataFrame, lr: pd.DataFrame) -> dict:
    """One line's estimates. `kind` decides the covariates (the precedent kinds leave out the target-precedent
    covariate) and `category` the stop outcome (a safety stop for target safety risk, else an efficacy stop)."""
    row = {"category": category, "about": about, "kind": kind, "level": level, "label": line.label,
           "column": line.column, "status": line.status}
    elig = d[line.column].notna()
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
    # a precedent kind leaves out the target-precedent covariate, which would adjust for the exposure itself
    base, base_23 = (tuple(c for c in covars if not (kind in PRECEDENT_KINDS and c == "precedent"))
                     for covars in (COVARS, COVARS_23))
    for prefix, part, outcome, covars in (
            ("s4", c2, "s4", base),
            ("s4_biomarker", c2.assign(biomarker_selected=c2.biomarker_selected.fillna(0)), "s4",
             (*base, "biomarker_selected")) if level != "adjustment" else (None,) * 4,  # it is the exposure there
            ("efficacy_stop", x[x.phase >= 2], "f_efficacy", base_23) if category != "safety" else (None,) * 4,
            ("safety_stop", x, "f_safety", base_23) if category == "safety" else (None,) * 4):
        if prefix is None:
            continue
        r = estimate(part, outcome, "x", covars)
        row |= {f"{prefix}_{k}": r.get(k) for k in ("n", "n_targets", "ppv", "rate_without", "rr", "lo", "hi", "p")}
    return row


DOSE_REASON = "PK, dose or formulation"  # the registry reason a dose stop can carry (report.section1.REASON_ORDER)


def stop_outcomes(t: pd.DataFrame) -> dict[str, pd.Series]:
    """Outcome column -> whether each traced stop (report.stop_causes.load) counts. Efficacy and safety are the
    causes; the efficacy stop is then split in two: the target was never adequately reached (tolerability capped the
    dose, the registry gives a PK, dose or formulation reason, or human evidence shows exposure or engagement too
    low) and efficacy proper (the target was engaged without benefit). A stop coded as
    another drug on the target having worked where this one was not shown to engage is neither: the code follows from
    the target's record, so counting it would make target evidence predict a missed target by construction."""
    eff = t.likely.eq("efficacy")
    dose = eff & (t.detail.eq("dose_capped") | t.registry_reason.eq(DOSE_REASON))
    engagement = eff & t.subcause.eq("not_engaged") & t.detail.ne("other_drug_on_target_worked")
    return {"stop_efficacy": eff, "stop_safety": t.likely.eq("safety"), "stop_not_reached": dose | engagement,
            "stop_no_benefit": eff & t.subcause.eq("engaged_no_benefit") & ~dose}


def traced_stops(d: pd.DataFrame) -> pd.DataFrame:
    """d with one column per stop_outcomes: 1 where the entry's traced stop counts, else 0."""
    t = stop_causes.load()
    k = pd.Series(keys(d), index=d.index)
    return d.assign(**{col: k.map(dict(zip(t.key, hit))).fillna(False).astype(float)
                       for col, hit in stop_outcomes(t).items()})


def stop_risk(d: pd.DataFrame) -> pd.DataFrame:
    """For each kind of target and drug evidence and each safety line, the adjusted risk ratio of each stop outcome
    (traced_stops) among the entries it is known for (Phase 1-3), when the line is exposed enough to estimate."""
    out = []
    for group, cat, line in [*(("kind", k.key, ln) for _, k, level, ln in chart_rows()
                               if level == "kind" and k.category != "safety"),
                             *(("kind", "earlier_approval", ln) for ln in APPROVAL_SPLIT),
                             *(("safety", "target_safety", ln) for ln in SAFETY)]:
        elig = d[line.column].notna()
        x = d.loc[elig].assign(x=d.loc[elig, line.column].astype(float))
        desc = describe(x.assign(any_outcome=1.0), "any_outcome", "x")
        row = {"group": group, "category": cat, "label": line.label, "column": line.column, "exposed": desc["n"],
               "targets": desc["n_targets"], "estimated": exposed_enough(desc)}
        covars = tuple(c for c in COVARS_23 if not (cat in PRECEDENT_KINDS and c == "precedent"))
        for outcome in [c for c in d.columns if c.startswith("stop_")] if row["estimated"] else ():
            r = estimate(x, outcome, "x", covars)
            row |= {f"{outcome}_{k}": r.get(k) for k in ("ppv", "rate_without", "rr", "lo", "hi", "p")}
        out.append(row)
    return pd.DataFrame(out)


def hypotheses(d: pd.DataFrame) -> dict:
    """N1-N3 as worded in the plan, on Phase 2 entries; N2's two claims are tested together by
    taking the larger p (intersection-union)."""
    c2 = d[(d.phase == 2) & d.modality.eq("small_molecule")]
    n = {"N1": estimate(c2[c2.selective.notna()], "s4", "selective"),
         "N2": {"drug_like": estimate(c2[c2.drug_like.notna()], "s4", "drug_like"),
                "brain_penetrant": estimate(c2[c2.brain_penetrant.notna()], "s4", "brain_penetrant")}}
    n["N2"]["p"] = max(n["N2"]["drug_like"].get("p", 1.0), n["N2"]["brain_penetrant"].get("p", 1.0))
    n3 = c2[c2.regime.ne("ONC") & c2.has_target_disease & c2.drug_like.notna()]
    n3 = n3.assign(human_genetics=genetic(n3))
    n["N3"] = {**describe(n3, "s4", "potent_100nm"),
               **adjusted(n3, "s4", ["potent_100nm", "human_genetics", "drug_like"])}
    n["holm"] = holm({"N1": n["N1"].get("p"), "N2": n["N2"]["p"], "N3": n["N3"].get("p")})
    n["holm_min"] = min(n["holm"].values())
    return n


def genetic(d: pd.DataFrame) -> pd.Series:
    """Human genetic or curated-pathway support, the adjustment N3 registered (its human-genetics category, which held
    the curated pathway)."""
    return (d.g3.fillna(0).gt(0) | d.reactome.fillna(0).gt(0)).astype(float)


# The lines the chart shows predicting approval: genetic support, a recurrent tumour mutation, a genetically altered
# mouse model, and an approved drug on the target for a related disease.
PREDICTIVE = ("g3", "somatic", "mouse_genetics", "b1")
PUBLISHED = ("lit_animal_disease", "lit_animal_healthy", "lit_human_engagement")


def evidence_basis(d: pd.DataFrame) -> dict:
    """What the entries had before entry: shares of all entries with a predictive line, a published study of the
    drug, an approved drug on the target for any disease, and potent binding; and, among entries with no predictive
    line, the shares with a published study, an approval for unrelated diseases only, and none of these. An unknown
    line counts as absent."""
    has = lambda cols: d[list(cols)].fillna(0).gt(0).any(axis=1)  # noqa: E731
    predictive, published = has(PREDICTIVE), has(PUBLISHED)
    approved, potent = has(("b1", "approved_unrelated_only")), has(("potent_100nm",))
    rest = ~predictive
    return {"entries": int(len(d)), "predictive": float(predictive.mean()), "published": float(published.mean()),
            "approved_any": float(approved.mean()), "potent": float(potent.mean()),
            "rest": {"entries": int(rest.sum()), "published": float(published[rest].mean()),
                     "approved_unrelated": float(has(("approved_unrelated_only",))[rest].mean()),
                     "none": float((~(published | approved | potent))[rest].mean())}}


def analyse(d: pd.DataFrame, rows: pd.DataFrame, fm: pd.DataFrame, trials: pd.DataFrame) \
        -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """The lines table (report_lines), the chart table (chart_rows), the stop-risk table (stop_risk) and numbers from
    the evidence-line dataset, the phase rows and the failure modes."""
    d = d.assign(precedent=d.precedent.fillna(0),  # no resolved target: no approved drug known on it
                 target=d.target.fillna("entity " + d.moiety_id.astype(str)))  # and it is its own cluster
    d = cause_outcomes(d.merge(fm[["program_id", "phase", "reason"]], on=["program_id", "phase"], how="left"))
    lr = loa_rows(d, rows[rows.us_site])
    out = [line_row(k.key if k else "", k.category if k else "adjustment", k.about if k else "", level, ln, d, lr)
           for k, level, ln in report_lines()]
    by_column = {r["column"]: r for r in out}
    chart = [by_column[ln.column] | {"kind": k.key, "category": category, "about": k.about, "level": level,
                                     "label": ln.label} for category, k, level, ln in chart_rows()]
    c2 = d[d.phase == 2]
    n = {"cohort": {"entries": int(len(d)), "programs": int(d.program_id.nunique()),
                    "with_target_disease": int(d.has_target_disease.sum()), "phase2": int(len(c2)),
                    "phase2_s4": float(c2.s4.mean()), "biomarker_selected": float(d.biomarker_selected.mean()),
                    "min_entries": MIN_ENTRIES, "min_targets": MIN_TARGETS},
         "lines": {r["column"]: {k: v for k, v in r.items() if k != "column"} for r in out if r.get("column")},
         "kinds": {k.key: k.label for k in KINDS.values()},
         "literature_gate": literature_gate(),
         "basis": evidence_basis(d),
         "published_strata": published_strata(strata_frame(d, sponsors(rows, trials))),
         **hypotheses(d)}
    stops = stop_risk(traced_stops(d))
    n["stop_risk"] = {r["column"]: {k: v for k, v in r.items() if k != "column"} for r in stops.to_dict("records")}
    return pd.DataFrame(out), pd.DataFrame(chart), stops, n


ANIMAL = "lit_animal_disease"  # the published-animal-study line whose gap published_strata locates


def strata_frame(d: pd.DataFrame, tiers: pd.DataFrame) -> pd.DataFrame:
    """Phase 2 entries of d with S4 and ANIMAL known, with the sponsor tier of report.section3.sponsors (`tiers`; an
    entry without one is "smaller"), whether it is outside the 100 largest sponsors (smaller), human genetic support
    (genetic) and the entry year as a level (year)."""
    p2 = d[(d.phase == 2) & d.s4.notna() & d[ANIMAL].notna()].merge(
        tiers[["program_id", "sponsor_tier"]], on="program_id", how="left")
    tier = p2.sponsor_tier.fillna("smaller")
    return p2.assign(**{ANIMAL: p2[ANIMAL].astype(float), "sponsor_tier": tier,
                        "smaller": tier.eq("smaller").astype(float),
                        "genetic": genetic(p2),
                        "year": p2.entry_year.astype(str)})


def published_strata(p2: pd.DataFrame, covars: tuple[str, ...] = COVARS) -> dict:
    """Where the gap at Phase 2 for a published study of the drug in an animal model of the disease lies, among the
    entries of strata_frame: advancing with and without it by sponsor size tier and by human genetic support, and the
    adjusted risk ratio with both held fixed."""
    group = lambda g: {"n": int(len(g)), "share": float(g[ANIMAL].mean()),  # noqa: E731
                       "s4_with": float(g[g[ANIMAL] > 0].s4.mean()), "s4_without": float(g[g[ANIMAL] <= 0].s4.mean())}
    return {"tiers": {t: group(g) for t, g in p2.groupby("sponsor_tier")},
            "large": group(p2[p2.sponsor_tier.ne("smaller")]),
            "genetic": {"with": group(p2[p2.genetic > 0]), "without": group(p2[p2.genetic <= 0])},
            "adjusted": adjusted(p2, "s4", [ANIMAL], (*covars, "sponsor_tier", "genetic"))}


# The confirmation of issue #140, as registered there on 2026-11-19: the side of 1 each ratio lies on in the
# discovery entries, and the significance level of the Holm-corrected one-sided tests.
CONFIRM_SIDES = {"C1": -1, "C2": -1, "C3": 1}
CONFIRM_ALPHA = 0.05
CONFIRM_COVARS = ("bio_area", "modality", "year", "novel", "precedent")  # its entries all fall in one era bin


def interactions(p2: pd.DataFrame, covars: tuple[str, ...]) -> dict:
    """The registered tests on the entries of strata_frame: C1, the adjusted risk ratio of ANIMAL holding sponsor size
    (smaller) and genetic support fixed; C2 and C3, the ratios of its interactions with them in a model with both.
    Each carries its one-sided p in its CONFIRM_SIDES direction, the Holm-corrected p and how it reads."""
    x = p2.assign(animal_x_smaller=p2[ANIMAL] * p2.smaller, animal_x_genetic=p2[ANIMAL] * p2.genetic)
    main = poisson(x, "s4", [ANIMAL, "smaller", "genetic"], covars)
    full = poisson(x, "s4", [ANIMAL, "smaller", "genetic", "animal_x_smaller", "animal_x_genetic"], covars)
    tests = {"C1": coef(main, ANIMAL), "C2": coef(full, "animal_x_smaller"), "C3": coef(full, "animal_x_genetic")}
    for k, t in tests.items():
        if t:
            t["p_one_sided"] = t["p"] / 2 if CONFIRM_SIDES[k] * np.log(t["rr"]) > 0 else 1 - t["p"] / 2
    adj = holm({k: t.get("p_one_sided") for k, t in tests.items()})
    for k, t in tests.items():
        if t:
            t["p_holm"] = adj[k]
            t["reading"] = ("confirmed" if adj[k] < CONFIRM_ALPHA else
                            "same direction, not confirmed" if CONFIRM_SIDES[k] * np.log(t["rr"]) > 0 else "not replicated")
    return {"n": int(len(x)), "n_targets": int(x.target.nunique()), "tests": tests}


def published_confirmation(c: pd.DataFrame, d: pd.DataFrame, rows_c: pd.DataFrame, rows_d: pd.DataFrame,
                           trials: pd.DataFrame) -> dict:
    """The registered confirmation (issue #140) of published_strata on the CONFIRM entries `c` (phase rows `rows_c`),
    sponsor size ranked on the discovery entries `d` (phase rows `rows_d`): the cohort, the stratum table, the tests
    (interactions), the same model on the discovery entries for reference, and the sensitivity with sponsor size ranked
    on both windows. A program whose sponsor is unresolved counts as smaller. The registered biomarker sensitivity is
    not computed: biomarker selection is labelled only for trials started through 2019."""
    prep = lambda x: x.assign(precedent=x.precedent.fillna(0),  # noqa: E731
                              target=x.target.fillna("entity " + x.moiety_id.astype(str)))
    unresolved = lambda t: t.assign(sponsor_tier=t.sponsor_tier.where(t.sponsor.ne("unresolved"), "smaller"))  # noqa: E731
    c, d = prep(c), prep(d)
    frozen = unresolved(sponsors(rows_c, trials, ranked_by=rows_d))
    p2 = strata_frame(c, frozen)
    both = strata_frame(c, unresolved(sponsors(rows_c, trials, ranked_by=pd.concat([rows_d, rows_c]))))
    ph2 = c[c.phase == 2]
    return {"cohort": {"phase2": int(len(ph2)), "with_line": int(len(p2)), "line_known": float(ph2[ANIMAL].notna().mean()),
                       "unresolved_sponsor": float(frozen.sponsor.eq("unresolved").mean()), "s4": float(p2.s4.mean())},
            "strata": published_strata(p2, CONFIRM_COVARS),
            **interactions(p2, CONFIRM_COVARS),
            "discovery": interactions(strata_frame(d, unresolved(sponsors(rows_d, trials))), COVARS),
            "sensitivity": {"ranked_on_both": interactions(both, CONFIRM_COVARS)["tests"]}}


def literature_gate() -> dict:
    """Recall of each literature version and kind against its blind reference set, and the gates."""
    g = json.load(open(LITERATURE_GATE))
    return {v: {"gates": g[v]["gates"], **{k: {f: r[f] for f in ("recall", "recall_pubmed_indexed", "passes")}
                                           for k, r in g[v]["kinds"].items()}} for v in ("v1", "v2", "v3", "v3_final") if v in g}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    if changed := stale():  # the analysis builds its own rows; the stored copy others query should match them
        print(f"[evidence_analysis] warning: the stored evidence dataset is stale ({', '.join(changed)}); "
              "run python -m report.evidence_lines store", flush=True)
    snap = frame.snapshot()
    progs, trials, outcomes = frame.programs(), frame.program_trials(), frame.trial_outcomes()
    rows = phase_rows(progs, trials, snap, window=SECTION1)
    d = us(build())
    lines, chart, stops, n = analyse(d, rows, failure_modes(rows, progs, trials, outcomes), trials)
    n["published_confirmation"] = published_confirmation(us(build(CONFIRM)), d, phase_rows(progs, trials, snap, window=CONFIRM),
                                                         rows, trials)
    lines.to_csv(os.path.join(OUT, "lines.csv"), index=False)
    chart.to_csv(os.path.join(OUT, "chart.csv"), index=False)
    stops.to_csv(os.path.join(OUT, "stop_risk.csv"), index=False)
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(jsonable(n), f, indent=1)


if __name__ == "__main__":
    main()
