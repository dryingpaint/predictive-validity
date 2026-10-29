"""Why efficacy failed: not engaged, engaged without benefit, or other causes.

    python -m report.attribution

Implements report/methods_stops_and_engagement.md. The cohort is every Phase 2/3 stop, phase entry in the Section 1
headline window (report.windows.SECTION1; the recent window and SECTION1_PERIODS alongside), whose final cause
(preclin.stop) is efficacy and that has an efficacy-attribution label (pipeline.stops.labels: the web-search label
where the bundle label was U), grouped by why efficacy failed (pipeline.stops.subcause, the subcause preclin.stop
holds); labelled stops whose final cause is something else are counted as reclassified. The independent
re-derivation (pipeline.attribution check) and the external adjudication
(report/audits/attribution_adjudication.json) are scored against the bundle-only labels they were designed for.
Intervals resample entities, since one entity's programs share its pharmacology.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact
from sklearn.metrics import cohen_kappa_score

from pipeline import llm
from pipeline.attribution import CHECK_SAMPLE, CHECK_TASK, CODES, check_sample
from pipeline.stops import (EFFICACY_SUBCAUSES, ENGAGED, SameTarget, cohort, detail, keys, labels, pillar_code, stops,
                            subcause)
from report import frame
from report.section1 import N_BOOT, SEED
from report.windows import RECENT, SECTION1, SECTION1_PERIODS, TRACING
from report.section3 import Evidence, jsonable

OUT = os.path.join(frame.REPO, "report", "output", "attribution")
ADJUDICATION = os.path.join(frame.REPO, "report", "audits", "attribution_adjudication.json")
# Each subcause of an efficacy stop with its label in the report table and in the figure legend, in stacking order.
SUBCAUSE_LABELS = {
    "not_engaged": ("Not engaged: exposure or engagement too low, or another drug on the target worked",
                    "Not engaged"),
    "engaged_no_benefit": ("Engaged, no benefit: target or mechanism wrong for the disease as tested",
                           "Engaged, no benefit"),
    "trial_design": ("Trial design, population or endpoint, mechanism not in question",
                     "Trial design, population, endpoint"),
    "toxicity_offset": ("On-target toxicity offset efficacy", "Toxicity offset efficacy"),
    "no_engagement_data": ("No engagement data: no human evidence of engagement either way", "No engagement data"),
}
DETAILS = ["exposure_or_engagement_too_low", "dose_capped", "other_drug_on_target_worked", "wrong_population",
           "wrong_endpoint_or_timing", "trial_could_not_answer"]
TESTED = ["not_engaged", "engaged_no_benefit"]
NOT_EFFICACY = "not_an_efficacy_failure"  # the subcause compared for F6, F8 and F9 from any labeller
MAIN_PHASES = (2, 3)  # the headline breakdown; Phase 1, whose trials rarely test efficacy, is reported apart
NAMES = {"F1a": "not_engaged", "F2": "engaged"}  # the codes the construct checks compare


def named(code: pd.Series, engagement: pd.Series) -> pd.Series:
    """Why efficacy failed, for any labeller's code (the pipeline's, the re-derivation's or the adjudication's)."""
    return subcause(code, engagement).fillna(NOT_EFFICACY)


def three_way(g: pd.Series) -> pd.Series:
    return g.where(g.isin(TESTED), "other")


def within(d: pd.DataFrame, window) -> pd.Series:
    return pd.to_datetime(d.entry).between(pd.Timestamp(window[0]), pd.Timestamp(window[1]))


def load(modes: pd.DataFrame, window, phases=MAIN_PHASES) -> tuple[pd.DataFrame, int, int]:
    """Stops in `phases` for efficacy or exposure with phase entry in `window`, with their labels; the number of such
    stops with no validated label (refusals), and the number of labelled stops whose final cause is not efficacy or
    exposure."""
    eff = cohort(modes)
    eff = eff[eff.phase.isin(phases) & within(eff, window)]
    final = frame.query("SELECT moiety_id, mondo_id, phase, cause FROM preclin.stop")
    cause = dict(zip(keys(final), final.cause))
    in_breakdown = eff.key.map(cause).eq("efficacy")
    d = eff.merge(labels(), on="key")
    stays = d.key.map(cause).eq("efficacy")
    reclassified = int((~stays).sum())
    d = d[stays].copy()
    d["primary_code"] = pillar_code(d)
    d["subcause"] = named(d.primary_code, d.engagement)
    d["detail"] = detail(d.primary_code, d.dose_limited)
    d["bundle_subcause"] = named(d.bundle_code, d.bundle_engagement)
    d["oncology"] = d.bio_area.eq("oncology")
    unlabelled = int((in_breakdown & ~eff.key.isin(d.key)).sum())
    return d, unlabelled, reclassified


def bundle_only(d: pd.DataFrame) -> pd.DataFrame:
    """The labels before the web search."""
    return d.assign(primary_code=d.bundle_code, engagement=d.bundle_engagement, subcause=d.bundle_subcause)


def adjudicated(d: pd.DataFrame) -> pd.DataFrame:
    """d's programs that the blind adjudication labelled, with its code, engagement and subcause."""
    adj = pd.DataFrame(json.load(open(ADJUDICATION)))
    m = d.merge(adj[["key", "code", "engagement"]].rename(columns={"code": "adjudicated",
                                                                   "engagement": "adjudicated_engagement"}), on="key")
    m = m[m.adjudicated.isin(CODES)]
    return m.assign(adjudicated_subcause=named(m.adjudicated, m.adjudicated_engagement))


def counts(d: pd.DataFrame, col: str, levels: list[str]) -> dict:
    c = d[col].value_counts().reindex(levels, fill_value=0)
    return {lv: {"n": int(n), "share": float(n / max(len(d), 1))} for lv, n in c.items()}


def split(d: pd.DataFrame, rng: np.random.Generator) -> dict:
    """Among programs whose engagement is known either way, not engaged against engaged without benefit, with an
    entity-resampled interval on the not-engaged share."""
    t = d[d.subcause.isin(TESTED)]
    if t.empty:
        return {"n": 0}
    m = pd.crosstab(t.moiety_id, t.subcause).reindex(columns=TESTED, fill_value=0).to_numpy()
    draws = m[rng.integers(0, len(m), (N_BOOT, len(m)))].sum(axis=1)
    boot = draws[:, 0] / draws.sum(axis=1)
    return {"n": int(m.sum()), "not_engaged": int(m[:, 0].sum()), "engaged_no_benefit": int(m[:, 1].sum()),
            "not_engaged_share": float(m[:, 0].sum() / m.sum()),
            "lo": float(np.percentile(boot, 2.5)), "hi": float(np.percentile(boot, 97.5))}


def summary(d: pd.DataFrame, rng: np.random.Generator) -> dict:
    return {"programs": int(len(d)), "entities": int(d.moiety_id.nunique()), "subcauses": counts(d, "subcause", EFFICACY_SUBCAUSES),
            "details": counts(d, "detail", DETAILS), "testable": split(d, rng),
            "other_drug_worked_no_engagement_data": int((d.detail.eq("other_drug_on_target_worked")
                                                          & d.engagement.eq("no_human_data")).sum())}


def search_summary(d: pd.DataFrame) -> dict:
    """What the web search decided among the programs the bundle left indeterminate, and how its labels agree with
    the blind adjudication on the programs both labelled."""
    s = d[d.searched]
    t = s[s.subcause.isin(TESTED)]
    out = {"searched": int(len(s)), "decided": int((s.primary_code != "U").sum()), "testable": int(len(t)),
           "not_engaged": int((t.subcause == "not_engaged").sum()),
           "not_engaged_share": float((t.subcause == "not_engaged").mean()) if len(t) else None}
    m = adjudicated(s)
    if len(m):
        both = (m.primary_code != "U") & (m.adjudicated != "U")
        open_here = (m.primary_code == "U") & (m.adjudicated != "U")
        out["adjudicated"] = {
            "n": int(len(m)), "both_decided": int(both.sum()),
            "three_way_agree_both_decided": float((three_way(m.subcause) == three_way(m.adjudicated_subcause))[both].mean())
            if both.any() else None,
            "outside_decided_search_u": int(open_here.sum()),
            "outside_decided_search_u_subcauses": m.adjudicated_subcause[open_here].value_counts().to_dict()}
    return out


def agreement(ga: pd.Series, gb: pd.Series) -> dict:
    return {"n": int(len(ga)), "three_way_agree": float((three_way(ga) == three_way(gb)).mean()),
            "three_way_kappa": float(cohen_kappa_score(three_way(ga), three_way(gb)))}


def rederivation(d: pd.DataFrame, sample: set[str]) -> dict:
    """Agreement with CHECK_TASK on the current check sample."""
    chk = llm.latest_decisions(CHECK_TASK.name, CHECK_TASK.prompt_version)
    chk = chk[chk.key.isin(sample)]
    chk["check_code"] = [o["primary_code"] for o in chk.parsed_output]
    chk["check_engagement"] = [o["engagement"] for o in chk.parsed_output]
    m = d.merge(chk[["key", "check_code", "check_engagement"]], on="key")
    if m.empty:
        return {"n": 0}
    return {**agreement(m.subcause, named(m.check_code, m.check_engagement)), "sampled": CHECK_SAMPLE,
            "engaged_agree": float((m.engagement.isin(ENGAGED) == m.check_engagement.isin(ENGAGED)).mean())}


def adjudication(d: pd.DataFrame) -> dict:
    m = adjudicated(d)
    ga, gb = m.subcause, m.adjudicated_subcause
    tested = gb.isin(TESTED)
    decided = m.primary_code != "U"
    return {**agreement(ga, gb), "sampled": len(json.load(open(ADJUDICATION))),
            "contradictions": int((ga.isin(TESTED) & tested & (ga != gb)).sum()),
            "adjudicated_testable": int(tested.sum()), "adjudicated_not_engaged": int((gb == "not_engaged").sum()),
            "adjudicated_not_engaged_share": float((gb == "not_engaged").sum() / max(tested.sum(), 1)),
            "decided_subcause_agree": float((ga[decided] == gb[decided]).mean()) if decided.any() else None}


def fisher(d: pd.DataFrame, flag: str, a: str = "F2", b: str = "F1a") -> dict:
    """Two-sided Fisher test of `flag` between code a and code b, reported under their names (NAMES)."""
    x = d[d.primary_code.isin([a, b])]
    tab = [[int(((x.primary_code == c) & x[flag]).sum()), int(((x.primary_code == c) & ~x[flag]).sum())]
           for c in (a, b)]
    odds, p = fisher_exact(tab) if min(map(sum, tab)) else (float("nan"), float("nan"))
    return {"n": {NAMES[a]: sum(tab[0]), NAMES[b]: sum(tab[1])}, f"share_{NAMES[a]}": tab[0][0] / max(sum(tab[0]), 1),
            f"share_{NAMES[b]}": tab[1][0] / max(sum(tab[1]), 1), "odds_ratio": float(odds), "p": float(p)}


def construct(d: pd.DataFrame, progs: pd.DataFrame, rows: pd.DataFrame) -> dict:
    """Same-target entities that failed or advanced in a related disease, and germline genetic support for the
    disease at phase entry, compared between programs not engaged because exposure or engagement was shown too low
    (F1a) and programs engaged without benefit (F2)."""
    evidence = Evidence(progs)
    same = SameTarget(evidence.mondo)
    p = progs[progs.mondo_id.notna()]
    p = p.assign(highest=p.program_id.map(frame.query(
        "SELECT program_id, highest_phase FROM preclin.dev_program").set_index("program_id").highest_phase))
    suspended = set(rows[(rows.event == "suspended") & ~rows.credited].program_id)
    by_entity = defaultdict(list)
    for pid, m, dz, approved, high in zip(p.program_id, p.moiety_id, p.mondo_id, p.approved, p.highest):
        by_entity[m].append((dz, pid in suspended, approved == "yes" or high >= 3))
    failed, advanced = [], []
    for m, dz in zip(d.moiety_id, d.mondo_id):
        near = [x for o in same.others(m) for x in by_entity[o] if same.related(x[0], dz)]
        failed.append(any(x[1] for x in near))
        advanced.append(any(x[2] for x in near))
    d = d.assign(same_target_failed=failed, same_target_advanced=advanced)
    entry = rows[~rows.credited][["program_id", "phase", "entry", "moiety_id"]]
    ev = evidence.features(entry.merge(d[["program_id", "phase"]], on=["program_id", "phase"]))
    d = d.merge(ev[["program_id", "phase", "g3"]], on=["program_id", "phase"], how="left")
    d["g3"] = d.g3.fillna(0) > 0
    return {"a_same_target_failed": fisher(d, "same_target_failed"),
            "b_same_target_advanced": fisher(d, "same_target_advanced", a="F1a", b="F2"),
            "c_g3": fisher(d, "g3", a="F1a", b="F2")}


def sensitivity(d: pd.DataFrame, traced: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Variants of the headline-window cohort d, and the other windows of the traced cohort."""
    first = d.sort_values(["moiety_id", "phase", "program_id"]).drop_duplicates("moiety_id")
    unknown_unless = lambda keep: d.assign(primary_code=np.where(d.primary_code.isin(["F2", "F3", "F4"]) & ~keep,
                                                                 "U", d.primary_code))
    variants = {
        "all (Phase 2 and 3)": d, "Phase 2": d[d.phase == 2], "Phase 3": d[d.phase == 3],
        "efficacy recorded in the registry": d[d.origin == "registry_efficacy"],
        "traced from unexplained stops": d[d.origin.str.startswith("traced")],
        "outside oncology": d[~d.oncology], "oncology": d[d.oncology],
        "sponsor-stated efficacy reason": d[d.reason == "efficacy: stated"],
        "primary endpoint missed": d[d.reason == "efficacy: primary endpoint not met"],
        "direct pillar evidence only (inferred engagement counted as unknown)":
            unknown_unless(d.engagement.ne("inferred_adequate")),
        "engaged only if shown before the index trial": unknown_unless(d.engagement_before_index.astype(bool)),
        "one program per entity": first,
        "high or medium confidence": d[d.confidence.isin(["high", "medium"])],
        "bundle only (before the web search)": bundle_only(d),
        f"entries {RECENT[0].year}-{RECENT[1].year}": traced[within(traced, RECENT)],
        f"all traced entries {TRACING[0].year}-{TRACING[1].year}": traced,
    }
    out = []
    for name, v in variants.items():
        v = v.assign(subcause=named(v.primary_code, v.engagement))
        s, t = counts(v, "subcause", EFFICACY_SUBCAUSES), split(v, rng)
        out.append({"variant": name, "programs": int(len(v)), **{g: s[g]["share"] for g in EFFICACY_SUBCAUSES},
                    "testable": t.get("n", 0), "not_engaged_of_testable": t.get("not_engaged_share"),
                    "lo": t.get("lo"), "hi": t.get("hi")})
    return pd.DataFrame(out)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(SEED)
    modes, rows, progs, _ = stops()
    d, unlabelled, reclassified = load(modes, SECTION1)
    traced = load(modes, TRACING)[0]
    p1, p1_unlabelled, p1_reclassified = load(modes, SECTION1, phases=(1,))
    p1_traced = load(modes, TRACING, phases=(1,))[0]
    engaged = d[d.engagement.isin(ENGAGED)]
    g = d.subcause.value_counts()
    ne, eng, u = g.get("not_engaged", 0), g.get("engaged_no_benefit", 0), g.get("no_engagement_data", 0)
    n = {"phase23": summary(d, rng),
         "by_phase": {int(p): summary(x, rng) for p, x in d.groupby("phase")},
         "outside_oncology": summary(d[~d.oncology], rng),
         "by_origin": {o: {"programs": int(len(x))} for o, x in d.groupby("origin")},
         "coverage": {"engaged_in_disease": float(engaged.engagement_in_disease.mean()),
                      "engaged_before_index": float(engaged.engagement_before_index.mean())},
         "reclassified": {"programs": reclassified}, "unlabelled": {"phase23": unlabelled},
         "window": {"from": SECTION1[0].year, "to": SECTION1[1].year},
         "recent": {"from": RECENT[0].year, "to": RECENT[1].year,
                    **summary(traced[within(traced, RECENT)], rng)},
         "by_period": {f"{lo.year}-{hi.year}": summary(traced[within(traced, (lo, hi))], rng) for lo, hi in SECTION1_PERIODS},
         "phase1": {**summary(p1, rng), "unlabelled": p1_unlabelled, "reclassified": p1_reclassified,
                    "by_origin": {o: {"programs": int(len(x))} for o, x in p1.groupby("origin")},
                    "recent": summary(p1_traced[within(p1_traced, RECENT)], rng)},
         "search": search_summary(d),
         "bundle_only": {"subcauses": counts(bundle_only(d), "subcause", EFFICACY_SUBCAUSES),
                         "testable": split(bundle_only(d), rng)},
         "rederivation": rederivation(bundle_only(traced), check_sample(cohort(modes))),
         "adjudication": adjudication(bundle_only(traced)),
         "construct": construct(d, progs, rows),
         "bounds": {"labelled": ne / (ne + eng), "all_no_data_not_engaged": (ne + u) / (ne + eng + u)}}
    sens = sensitivity(d, traced, rng)
    sens.to_csv(os.path.join(OUT, "sensitivity.csv"), index=False)
    n["sensitivity_range"] = {"lo": float(sens.not_engaged_of_testable.min()),
                              "hi": float(sens.not_engaged_of_testable.max())}
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(n, f, indent=1, default=jsonable)


if __name__ == "__main__":
    main()
