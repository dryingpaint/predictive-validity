"""Why efficacy failed: not engaged, engaged without benefit, or other causes.

    python -m report.attribution

Implements report/attribution_plan.md on preclin.efficacy_failure_attribution
(pipeline.attribution label), the independent re-derivation (pipeline.attribution
check) and the external adjudication in report/audits/attribution_adjudication.json.
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

from pipeline.attribution import CHECK_SAMPLE, CHECK_TASK, cohort
from report import frame
from report.disease_match import Mondo
from report.section1 import SEED, phase_rows
from report.section3 import Evidence

OUT = os.path.join(frame.REPO, "report", "output", "attribution")
ADJUDICATION = os.path.join(frame.REPO, "report", "audits", "attribution_adjudication.json")
N_BOOT = 1000
RELATED_DISEASE = 0.5
# F3 and F4 count as engaged without benefit only when engagement was shown or inferred; otherwise
# they join trial design as a failure of the trial's population or endpoint (see group()).
GROUP = {"F1a": "not_engaged", "F1b": "not_engaged", "F2": "engaged_no_benefit", "F3": "engaged_no_benefit",
         "F4": "engaged_no_benefit", "F5": "toxicity", "F6": "toxicity", "F7": "trial_design",
         "F8": "not_a_failure", "F9": "not_a_failure", "U": "indeterminate"}
GROUPS = ["not_engaged", "engaged_no_benefit", "toxicity", "trial_design", "not_a_failure", "indeterminate"]
CODES = ["F1a", "F1b", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "U"]
ENGAGED = ("adequate", "inferred_adequate")


def group(code: pd.Series, engagement: pd.Series) -> pd.Series:
    g = code.map(GROUP)
    return g.where(~(code.isin(["F3", "F4"]) & ~engagement.isin(ENGAGED)), "trial_design")


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Labelled cohort programs, and the cohort programs without a validated label (refusals)."""
    eff = cohort()
    lab = frame.query("""SELECT a.*, d.input_payload FROM preclin.efficacy_failure_attribution a
                         JOIN pv_evidence.llm_decision d USING (llm_decision_id)""")
    lab["key"] = [f"{m}|{d}|{p}" for m, d, p in zip(lab.moiety_id, lab.mondo_id, lab.phase)]
    d = eff.merge(lab.drop(columns=["moiety_id", "mondo_id", "phase"]), on="key")
    d["group"] = group(d.primary_code, d.engagement)
    d["oncology"] = d.bio_area.eq("oncology")
    d["n_papers"] = [len(p["papers"]) for p in d.input_payload]
    d["n_phase1"] = [len(p["phase1_results"]) for p in d.input_payload]
    d["index_start"] = pd.to_datetime([p["index"]["start"] for p in d.input_payload], errors="coerce")
    return d.drop(columns=["input_payload"]), eff[~eff.key.isin(d.key)][["key", "phase", "modality"]]


def shares(d: pd.DataFrame, col: str, levels: list[str], rng: np.random.Generator) -> pd.DataFrame:
    """Share of programs at each level, with a 95% interval resampling entities."""
    counts = pd.crosstab(d.moiety_id, d[col]).reindex(columns=levels, fill_value=0)
    m = counts.to_numpy()
    draws = np.array([m[rng.integers(0, len(m), len(m))].sum(axis=0) for _ in range(N_BOOT)])
    frac = draws / draws.sum(axis=1, keepdims=True)
    total = m.sum()
    return pd.DataFrame({"level": levels, "n": m.sum(axis=0), "share": m.sum(axis=0) / total,
                         "lo": np.percentile(frac, 2.5, axis=0), "hi": np.percentile(frac, 97.5, axis=0)})


def split(d: pd.DataFrame, rng: np.random.Generator) -> dict:
    """Q2: among programs whose engagement is known either way, not engaged against engaged
    without benefit, with an entity-resampled interval on the not-engaged share."""
    t = d[d.group.isin(["not_engaged", "engaged_no_benefit"])]
    if t.empty:
        return {"n": 0}
    by = pd.crosstab(t.moiety_id, t.group).reindex(columns=["not_engaged", "engaged_no_benefit"], fill_value=0)
    m = by.to_numpy()
    boot = [s[0] / s.sum() for s in (m[rng.integers(0, len(m), len(m))].sum(axis=0) for _ in range(N_BOOT))]
    return {"n": int(m.sum()), "not_engaged": int(m[:, 0].sum()), "engaged_no_benefit": int(m[:, 1].sum()),
            "not_engaged_share": float(m[:, 0].sum() / m.sum()),
            "lo": float(np.percentile(boot, 2.5)), "hi": float(np.percentile(boot, 97.5))}


def summary(d: pd.DataFrame, rng: np.random.Generator) -> dict:
    keyed = lambda df: {r.pop("level"): r for r in df.to_dict("records")}
    return {"programs": int(len(d)), "entities": int(d.moiety_id.nunique()),
            "groups": keyed(shares(d, "group", GROUPS, rng)), "codes": keyed(shares(d, "primary_code", CODES, rng)),
            "testable": split(d, rng)}


def bounds(d: pd.DataFrame, adj: dict) -> dict:
    """Not-engaged share of failures whose mechanism was tested, if indeterminate programs split like
    the indeterminate programs that outside research could decide, and if every one was not engaged."""
    g = d.group.value_counts()
    ne, eng, u = g.get("not_engaged", 0), g.get("engaged_no_benefit", 0), g.get("indeterminate", 0)
    out = {"labelled": ne / (ne + eng), "all_indeterminate_not_engaged": (ne + u) / (ne + eng + u)}
    outside = adj.get("outside_u_groups", {})
    tested = outside.get("not_engaged", 0) + outside.get("engaged_no_benefit", 0)
    if adj.get("pipeline_u") and tested:
        decided = u * tested / adj["pipeline_u"]
        extra_ne = decided * outside.get("not_engaged", 0) / tested
        out["indeterminate_split_as_adjudicated"] = (ne + extra_ne) / (ne + eng + decided)
    return out


def agreement(a: pd.Series, b: pd.Series) -> dict:
    ga, gb = a.map(GROUP), b.map(GROUP)
    three = lambda g: g.where(g.isin(["not_engaged", "engaged_no_benefit"]), "other")
    return {"n": int(len(a)), "code_agree": float((a == b).mean()), "code_kappa": float(cohen_kappa_score(a, b)),
            "group_agree": float((ga == gb).mean()), "group_kappa": float(cohen_kappa_score(ga, gb)),
            "three_way_agree": float((three(ga) == three(gb)).mean()),
            "three_way_kappa": float(cohen_kappa_score(three(ga), three(gb))),
            "confusion": pd.crosstab(ga, gb).to_dict()}


def rederivation(d: pd.DataFrame) -> dict:
    chk = frame.query("""
        SELECT DISTINCT ON (subject_key) subject_key AS key, parsed_output->>'primary_code' AS check_code,
               parsed_output->>'engagement' AS check_engagement
        FROM pv_evidence.llm_decision d JOIN pv_evidence.llm_decision_run r USING (decision_run_id)
        WHERE d.task = %s AND r.prompt_version = %s AND r.status = 'completed'
          AND d.validation_status = 'validated'
        ORDER BY subject_key, d.created_at DESC""", (CHECK_TASK.name, CHECK_TASK.prompt_version))
    m = d.merge(chk, on="key")
    if m.empty:
        return {"n": 0}
    out = agreement(m.primary_code, m.check_code)
    out["sampled"] = CHECK_SAMPLE
    out["engagement_agree"] = float((m.engagement == m.check_engagement).mean())
    out["engaged_agree"] = float((m.engagement.isin(ENGAGED) == m.check_engagement.isin(ENGAGED)).mean())
    return out


def adjudication(d: pd.DataFrame) -> dict:
    if not os.path.exists(ADJUDICATION):
        return {"n": 0}
    adj = pd.DataFrame(json.load(open(ADJUDICATION)))
    m = d.merge(adj[["key", "code"]].rename(columns={"code": "adjudicated"}), on="key")
    m = m[m.adjudicated.isin(CODES)]
    out = agreement(m.primary_code, m.adjudicated)
    out["sampled"] = int(len(adj))
    u = m[m.primary_code == "U"]
    out["pipeline_u"] = int(len(u))
    out["pipeline_u_decided_outside"] = int((u.adjudicated != "U").sum())
    out["outside_u_groups"] = u[u.adjudicated != "U"].adjudicated.map(GROUP).value_counts().to_dict()
    ga, gb = m.primary_code.map(GROUP), m.adjudicated.map(GROUP)
    key = ["not_engaged", "engaged_no_benefit"]
    out["contradictions"] = int((ga.isin(key) & gb.isin(key) & (ga != gb)).sum())
    out["adjudicated_testable"] = int(gb.isin(key).sum())
    out["adjudicated_not_engaged"] = int((gb == "not_engaged").sum())
    out["adjudicated_not_engaged_share"] = float((gb == "not_engaged").sum() / max(gb.isin(key).sum(), 1))
    decided = m[m.primary_code != "U"]
    out["decided_group_agree"] = float((decided.primary_code.map(GROUP) == decided.adjudicated.map(GROUP)).mean()) \
        if len(decided) else None
    return out


def fisher(d: pd.DataFrame, flag: str, a: str = "F2", b: str = "F1a") -> dict:
    x = d[d.primary_code.isin([a, b])]
    tab = [[int(((x.primary_code == c) & x[flag]).sum()), int(((x.primary_code == c) & ~x[flag]).sum())]
           for c in (a, b)]
    odds, p = fisher_exact(tab) if min(map(sum, tab)) else (float("nan"), float("nan"))
    return {"table": {a: tab[0], b: tab[1]}, "n": {a: sum(tab[0]), b: sum(tab[1])}, f"share_{a}": tab[0][0] / max(sum(tab[0]), 1),
            f"share_{b}": tab[1][0] / max(sum(tab[1]), 1), "odds_ratio": float(odds), "p": float(p)}


def construct(d: pd.DataFrame, progs: pd.DataFrame, rows: pd.DataFrame) -> dict:
    """Checks 3a-3c: same-target entities that failed or advanced in a related disease, and
    germline genetic support for the disease at phase entry."""
    targets = frame.query("SELECT moiety_id, target_id FROM preclin.moiety_target WHERE is_primary")
    tset = targets.groupby("moiety_id").target_id.apply(set)
    by_target = targets.groupby("target_id").moiety_id.apply(set)
    mondo = Mondo()
    p = progs[progs.mondo_id.notna()]
    p = p.assign(highest=p.program_id.map(frame.query(
        "SELECT program_id, highest_phase FROM preclin.dev_program").set_index("program_id").highest_phase))
    suspended = set(rows[(rows.event == "suspended") & ~rows.credited].program_id)
    by_entity = defaultdict(list)
    for pid, m, dz, approved, high in zip(p.program_id, p.moiety_id, p.mondo_id, p.approved, p.highest):
        by_entity[m].append((dz, pid in suspended, approved == "yes" or high >= 3))
    failed, advanced = [], []
    for m, dz in zip(d.moiety_id, d.mondo_id):
        others = {o for t in tset.get(m, ()) for o in by_target[t]} - {m}
        near = [x for o in others for x in by_entity[o] if isinstance(dz, str) and mondo.lin(x[0], dz) >= RELATED_DISEASE]
        failed.append(any(x[1] for x in near))
        advanced.append(any(x[2] for x in near))
    d = d.assign(same_target_failed=failed, same_target_advanced=advanced)
    entry = rows[~rows.credited][["program_id", "phase", "entry", "moiety_id"]]
    ev = Evidence(progs).features(entry.merge(d[["program_id", "phase"]], on=["program_id", "phase"]))
    d = d.merge(ev[["program_id", "phase", "g3"]], on=["program_id", "phase"], how="left")
    d["g3"] = d.g3.fillna(0) > 0
    return {"a_same_target_failed": fisher(d, "same_target_failed"),
            "b_same_target_advanced": fisher(d, "same_target_advanced", a="F1a", b="F2"),
            "c_g3": fisher(d, "g3", a="F1a", b="F2")}


def sensitivity(d: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    first = d.sort_values(["moiety_id", "phase", "program_id"]).drop_duplicates("moiety_id")
    before = d.assign(primary_code=np.where(d.primary_code.isin(["F2", "F3", "F4"]) & ~d.engagement_before_index,
                                            "U", d.primary_code))
    variants = {
        "all (Phase 2 and 3)": d, "Phase 2": d[d.phase == 2], "Phase 3": d[d.phase == 3],
        "outside oncology": d[~d.oncology], "oncology": d[d.oncology],
        "sponsor-stated efficacy reason": d[d.reason == "efficacy: stated"],
        "primary endpoint missed": d[d.reason == "efficacy: primary endpoint not met"],
        "direct pillar evidence only (inferred engagement counted as unknown)":
            d.assign(primary_code=np.where(d.engagement.eq("inferred_adequate") & d.primary_code.isin(["F2", "F3", "F4"]),
                                           "U", d.primary_code)),
        "engagement known before the index trial": before,
        "one program per entity": first,
        "high or medium confidence": d[d.confidence.isin(["high", "medium"])],
    }
    out = []
    for name, v in variants.items():
        v = v.assign(group=group(v.primary_code, v.engagement))
        s = shares(v, "group", GROUPS, rng).set_index("level")
        t = split(v, rng)
        out.append({"variant": name, "programs": int(len(v)), **{g: float(s.at[g, "share"]) for g in GROUPS},
                    "testable": t.get("n", 0), "not_engaged_of_testable": t.get("not_engaged_share"),
                    "lo": t.get("lo"), "hi": t.get("hi")})
    return pd.DataFrame(out)


def coverage(d: pd.DataFrame) -> dict:
    has = (d.n_papers > 0) | (d.n_phase1 > 0)
    known = d.engagement.ne("no_human_data")
    return {"any_source": float(has.mean()), "engagement_known": float(known.mean()),
            "engagement_known_by_modality": d.groupby("modality").apply(
                lambda g: {"n": int(len(g)), "known": float(g.engagement.ne("no_human_data").mean())}).to_dict(),
            "engagement_known_by_entry": d.groupby(d.index_start.dt.year.fillna(0).astype(int)).apply(
                lambda g: {"n": int(len(g)), "known": float(g.engagement.ne("no_human_data").mean())}).to_dict(),
            "pillars": {p: d[p].value_counts().to_dict() for p in ("exposure", "engagement", "pathway")},
            "engaged_in_disease": float(d[d.engagement.isin(ENGAGED)].engagement_in_disease.mean()),
            "engaged_before_index": float(d[d.engagement.isin(ENGAGED)].engagement_before_index.mean()),
            "dose_limited": int(d.dose_limited.sum())}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(SEED)
    progs, trials = frame.programs(), frame.program_trials()
    rows = phase_rows(progs, trials, frame.snapshot())
    d, unlabelled = load()
    d.drop(columns=["secondary_codes", "sources"]).to_csv(os.path.join(OUT, "programs.csv"), index=False)
    main_cohort = d[d.phase.isin([2, 3])]
    n = {"phase23": summary(main_cohort, rng), "phase1": summary(d[d.phase == 1], rng),
         "by_phase": {int(p): summary(g, rng) for p, g in main_cohort.groupby("phase")},
         "outside_oncology": summary(main_cohort[~main_cohort.oncology], rng),
         "oncology": summary(main_cohort[main_cohort.oncology], rng),
         "coverage": coverage(main_cohort),
         "unlabelled": {"programs": int(len(unlabelled)), "phase23": int(unlabelled.phase.isin([2, 3]).sum()),
                        "by_modality": unlabelled.modality.value_counts().to_dict()},
         "rederivation": rederivation(main_cohort), "adjudication": adjudication(main_cohort),
         "construct": construct(main_cohort, progs, rows)}
    n["bounds"] = bounds(main_cohort, n["adjudication"])
    sens = sensitivity(main_cohort, rng)
    sens.to_csv(os.path.join(OUT, "sensitivity.csv"), index=False)
    n["sensitivity_range"] = {"lo": float(sens.not_engaged_of_testable.min()),
                              "hi": float(sens.not_engaged_of_testable.max())}
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(n, f, indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x))


if __name__ == "__main__":
    main()
