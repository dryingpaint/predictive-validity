"""Section 1: phase transitions, likelihood of approval and failure modes.

    python -m report.section1

Unit: a development program = (molecular entity, MONDO disease). For each
phase p, the cohort is programs whose first industry-sponsored phase-p trial
started 2015-2025, that had not entered a later phase earlier, and whose
entity was not already FDA-approved for the disease (a lifecycle program).
Each program then either advanced (a later-phase industry trial started, or
FDA approval for the disease), was suspended (none of the program's own
industry trials, those listing its disease, active or active within LAG months
of the snapshot), or is censored (still active or too recent to call). The BIO-style rate is advanced / (advanced + suspended);
the Aalen-Johansen estimate keeps censored programs in the risk set with
suspension as a competing event. LOA is the product over phases. Programs with
no disease (healthy-volunteer, basket or symptom trials only) enter the Phase 1
and Phase 2 cohorts but not Phase 3: FDA approval is judged per disease.
Confidence intervals resample molecular entities (programs of one entity
are not independent).
"""
from __future__ import annotations

import json
import os
from datetime import date

import numpy as np
import pandas as pd
from lifelines import AalenJohansenFitter

from report import frame

OUT = os.path.join(frame.REPO, "report", "output", "section1")
LAG_MONTHS = 24
MATURE_WINDOW = (date(2015, 1, 1), date(2019, 12, 31))
HORIZON_YEARS = 6.0
N_BOOT = 1000
SEED = 20261020


def phase_rows(progs: pd.DataFrame, trials: pd.DataFrame, snap: date, lag_months: int = LAG_MONTHS,
               uncertain_as_approved: bool = False, window: tuple[date, date] = frame.WINDOW,
               shared_entry: bool = False) -> pd.DataFrame:
    """One row per (program, phase) in that phase's cohort; phase entry must fall in `window`.
    shared_entry=True lets every shared trial count for every program, for entry,
    advancement and activity alike (as if each indication began with the entity's
    first trials)."""
    t = trials[trials.start_date.notna()].copy()
    t["active"] = t.overall_status.isin(frame.ACTIVE)
    t["end"] = t.completion_date.fillna(t.primary_completion_date).fillna(t.start_date)
    # A program's own trials list its disease (or, for an entity's disease-unspecified
    # program, are its healthy-volunteer, basket and symptom trials). Shared trials
    # (a healthy-volunteer study, a "solid tumors" basket) count only toward Phase 1
    # entry of the lead indication. Phase entry is industry-sponsored; advancement and
    # whether the disease is still in development come from the program's own trials
    # by any sponsor (a cooperative-group Phase 3 of a company's drug is development).
    unspecified = t.program_id.map(progs.set_index("program_id").mondo_id).isna()
    own = t if shared_entry else t[t.attach.isin(["disease", "non_disease_condition"])
                                   | (t.attach.isin(["no_disease", "basket"]) & unspecified)]
    ind = t[t.industry]
    entry_trials = ind if shared_entry else pd.concat([own[own.industry], ind[(ind.phase == 1) & ind.marks_entry]])
    starts = entry_trials.pivot_table(index="program_id", columns="phase", values="start_date", aggfunc="min")
    later = own.pivot_table(index="program_id", columns="phase", values="start_date", aggfunc="min")
    last = own.assign(end=np.where(own.active, pd.Timestamp(snap), pd.to_datetime(own.end))) \
              .groupby("program_id").end.max()
    active = own.groupby("program_id").active.any()
    us = ind[ind.us_site].groupby("program_id").phase.max()

    p = progs.set_index("program_id")
    approved = p.approved.eq("yes") | (uncertain_as_approved & p.approved.eq("uncertain"))
    appr_date = pd.to_datetime(p.first_approval_date).where(p.date_basis.eq("dated"))
    appr_date = appr_date.where(~(approved & p.date_basis.isin(["before_2015", "undated"])),
                                pd.Timestamp("2014-12-31")).where(approved)
    cutoff = pd.Timestamp(snap) - pd.DateOffset(months=lag_months)

    rows = []
    for pid in starts.index:
        if pid not in p.index:
            continue
        s = starts.loc[pid]
        for phase in (1, 2, 3):
            entry = s.get(phase)
            if pd.isna(entry) or not (window[0] <= entry <= window[1]):
                continue
            if phase == 3 and pd.isna(p.at[pid, "mondo_id"]):
                continue  # approval is judged per disease, so an unspecified program cannot be followed to it
            entry = pd.Timestamp(entry)
            if any(pd.notna(s.get(q)) and pd.Timestamp(s.get(q)) < entry for q in (1, 2, 3) if q > phase):
                continue
            nxt = later.loc[pid] if pid in later.index else pd.Series(dtype=object)
            later_starts = [pd.Timestamp(nxt.get(q)) for q in (2, 3) if q > phase and pd.notna(nxt.get(q))]
            if any(x < entry for x in later_starts):
                continue
            a = appr_date.get(pid)
            if pd.notna(a) and a <= entry:
                continue  # already approved for this disease: lifecycle program
            advance = min([x for x in later_starts if x >= entry] + ([a] if pd.notna(a) else []), default=None)
            if phase == 3:
                advance = a if pd.notna(a) else None
            if advance is not None and advance <= pd.Timestamp(snap):
                event, end = "advanced", advance
            elif active.get(pid, False):
                event, end = "censored", pd.Timestamp(snap)
            elif last.get(pid, entry) <= cutoff:
                event, end = "suspended", last.get(pid, entry)
            else:
                event, end = "censored", pd.Timestamp(snap)
            first_fda = p.at[pid, "moiety_first_fda_approval"]
            rows.append({
                "program_id": pid, "moiety_id": p.at[pid, "moiety_id"], "phase": phase, "entry": entry,
                "event": event, "years": max((end - entry).days, 0) / 365.25,
                "bio_area": p.at[pid, "bio_area"] if pd.notna(p.at[pid, "bio_area"]) else "unmapped",
                "modality": p.at[pid, "modality"] if pd.notna(p.at[pid, "modality"]) else "unknown",
                "novel": pd.isna(first_fda) or pd.Timestamp(first_fda) > entry,
                "us_site": us.get(pid, 0) >= phase, "entry_year": entry.year,
                "approval_date": a if pd.notna(a) else None,
            })
    return pd.DataFrame(rows)


def rates(rows: pd.DataFrame) -> pd.DataFrame:
    """Per phase: counts and the BIO-style advanced / (advanced + suspended)."""
    c = rows.pivot_table(index="phase", columns="event", values="program_id", aggfunc="count", fill_value=0)
    for col in ("advanced", "suspended", "censored"):
        if col not in c:
            c[col] = 0
    c["rate"] = c.advanced / (c.advanced + c.suspended)
    return c[["advanced", "suspended", "censored", "rate"]]


def loa(rate_by_phase: pd.Series) -> float:
    return float(np.prod([rate_by_phase.get(ph, np.nan) for ph in (1, 2, 3)]))


def boot(rows: pd.DataFrame, n: int = N_BOOT, seed: int = SEED) -> pd.DataFrame:
    """Entity-cluster bootstrap of per-phase rates and LOA: 2.5/97.5 percentiles."""
    counts = rows.groupby(["moiety_id", "phase", "event"]).size().unstack(["phase", "event"], fill_value=0)
    rng = np.random.default_rng(seed)
    ids = counts.index.to_numpy()
    out = []
    for _ in range(n):
        w = np.bincount(rng.integers(0, len(ids), len(ids)), minlength=len(ids))
        tot = (counts.to_numpy() * w[:, None]).sum(axis=0)
        s = pd.Series(tot, index=counts.columns)
        r = {}
        for ph in (1, 2, 3):
            adv, sus = s.get((ph, "advanced"), 0), s.get((ph, "suspended"), 0)
            r[ph] = adv / (adv + sus) if adv + sus else np.nan
        r["loa"] = np.prod([r[ph] for ph in (1, 2, 3)])
        out.append(r)
    return pd.DataFrame(out).quantile([0.025, 0.975])


def aalen_johansen(rows: pd.DataFrame, horizon: float = HORIZON_YEARS) -> dict:
    """Cumulative incidence of advancement by `horizon` years per phase, with
    suspension as a competing event and censoring at the snapshot."""
    out = {}
    for ph in (1, 2, 3):
        r = rows[rows.phase == ph]
        if r.empty:
            continue
        code = r.event.map({"advanced": 1, "suspended": 2, "censored": 0})
        ajf = AalenJohansenFitter(calculate_variance=False, seed=SEED)
        ajf.fit(r.years.clip(lower=1 / 365.25), code, event_of_interest=1)
        cif = ajf.cumulative_density_
        out[ph] = float(cif[cif.index <= horizon].iloc[-1, 0]) if (cif.index <= horizon).any() else np.nan
    out["loa"] = float(np.prod([out.get(ph, np.nan) for ph in (1, 2, 3)]))
    return out


def summarize(rows: pd.DataFrame, label: str) -> dict:
    r = rates(rows)
    ci = boot(rows)
    aj = aalen_johansen(rows)
    res = {"label": label}
    for ph in (1, 2, 3):
        if ph in r.index:
            res[f"ph{ph}_n_advanced"] = int(r.at[ph, "advanced"])
            res[f"ph{ph}_n_suspended"] = int(r.at[ph, "suspended"])
            res[f"ph{ph}_n_censored"] = int(r.at[ph, "censored"])
            res[f"ph{ph}_rate"] = float(r.at[ph, "rate"])
            res[f"ph{ph}_lo"], res[f"ph{ph}_hi"] = float(ci.at[0.025, ph]), float(ci.at[0.975, ph])
            res[f"ph{ph}_aj"] = aj.get(ph)
    res["loa"] = loa(r.rate)
    res["loa_lo"], res["loa_hi"] = float(ci.at[0.025, "loa"]), float(ci.at[0.975, "loa"])
    res["loa_aj"] = aj["loa"]
    res["n_entities"] = int(rows.moiety_id.nunique())
    return res


REASON_ORDER = [
    ("efficacy: stated", "biology"), ("efficacy: primary endpoint not met", "biology"),
    ("safety", "biology"), ("PK, dose or formulation", "biology"),
    ("business or strategic (explicit)", "business"), ("sponsor decision, unspecified", "unspecified"),
    ("enrollment, operational or regulatory", "operational"),
    ("positive readout, not advanced", "other"),
    ("completed, no results posted, no reason stated", "unexplained"),
    ("stopped, no reason stated", "unexplained"),
]
OPERATIONAL = {"enrollment_feasibility", "operational_or_site", "regulatory", "manufacturing_supply", "covid19",
               "replaced_by_new_protocol"}


def trial_reason(o: pd.Series | None, status: str) -> str:
    """Reason a single trial of the stopping phase gives, or None if it gives none."""
    if o is None:
        return ("completed, no results posted, no reason stated" if status == "COMPLETED"
                else "stopped, no reason stated")
    if o.stop_reason == "efficacy_futility":
        return "efficacy: stated"
    if o.efficacy_failure or o.primary_endpoint == "not_met":
        return "efficacy: primary endpoint not met"
    if o.stop_reason == "safety_tolerability" or o.safety_signal == "notable":
        return "safety"
    if o.stop_reason == "pk_pd_or_formulation":
        return "PK, dose or formulation"
    if o.stop_reason in ("business_portfolio", "competitive_landscape"):
        return "business or strategic (explicit)"
    if o.stop_reason == "sponsor_decision_unspecified":
        return "sponsor decision, unspecified"
    if o.stop_reason in OPERATIONAL:
        return "enrollment, operational or regulatory"
    if o.primary_endpoint in ("met", "mixed") or o.stop_reason == "objectives_met_or_early_success":
        return "positive readout, not advanced"
    return ("completed, no results posted, no reason stated" if o.execution == "completed"
            else "stopped, no reason stated")


def failure_modes(rows: pd.DataFrame, trials: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    """One reason per suspended program: the highest-priority reason among the
    industry trials of the phase it stopped in."""
    rank = {r: i for i, (r, _) in enumerate(REASON_ORDER)}
    family = dict(REASON_ORDER)
    out = outcomes.set_index("nct_id")
    stopped = rows[rows.event == "suspended"][["program_id", "phase", "moiety_id", "bio_area", "modality"]]
    t = trials[trials.industry].merge(stopped[["program_id", "phase"]], on=["program_id", "phase"])
    t["reason"] = [trial_reason(out.loc[n] if n in out.index else None, st)
                   for n, st in zip(t.nct_id, t.overall_status)]
    t["results_source"] = t.nct_id.map(out.results_source)
    t["rank"] = t.reason.map(rank)
    best = t.sort_values("rank").drop_duplicates(["program_id", "phase"])[
        ["program_id", "phase", "reason", "nct_id", "results_source"]]
    res = stopped.merge(best, on=["program_id", "phase"], how="left")
    res["reason"] = res.reason.fillna("stopped, no reason stated")
    res["family"] = res.reason.map(family)
    return res


def scale(rows: pd.DataFrame, progs: pd.DataFrame, trials: pd.DataFrame) -> dict:
    """Size of the data behind Section 1."""
    q = frame.query("""
        SELECT (SELECT count(*) FROM preclin.ctgov_study) AS ctgov_studies,
               (SELECT count(*) FROM preclin.ctgov_study s WHERE s.lead_sponsor_class = 'INDUSTRY'
                  AND s.start_date BETWEEN %s AND %s AND s.overall_status <> 'WITHDRAWN'
                  AND s.phases && ARRAY['EARLY_PHASE1','PHASE1','PHASE2','PHASE3']) AS industry_trials_window,
               (SELECT count(*) FROM preclin.fda_approved_use) AS fda_approved_uses,
               (SELECT count(DISTINCT letter_sha256) FROM preclin.fda_approved_use) AS fda_letters_with_uses,
               (SELECT count(*) FROM preclin.fda_application WHERE center = 'CBER') AS cber_applications,
               (SELECT count(*) FROM preclin.moiety) AS entities,
               (SELECT count(*) FROM preclin.dev_program) AS programs""", frame.WINDOW).iloc[0]
    out = {k: int(v) for k, v in q.items()}
    out.update({"cohort_programs": int(rows.program_id.nunique()), "cohort_entities": int(rows.moiety_id.nunique()),
                "cohort_rows_by_phase": {int(k): int(v) for k, v in rows.phase.value_counts().sort_index().items()},
                "cohort_approved_programs": int(rows[rows.approval_date.notna()].program_id.nunique())})
    return out


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    snap = frame.snapshot()
    progs, trials = frame.programs(), frame.program_trials()
    rows = phase_rows(progs, trials, snap)
    rows.to_csv(os.path.join(OUT, "phase_cohort_rows.csv"), index=False)

    results = [summarize(rows, "all programs")]
    results.append(summarize(rows[rows.us_site], "programs with a US site in the phase"))
    results.append(summarize(rows[rows.novel], "entity not yet FDA-approved at phase entry"))
    results.append(summarize(rows[~rows.novel], "entity already FDA-approved for another disease"))
    for lag in (12, 18, 36):
        results.append(summarize(phase_rows(progs, trials, snap, lag_months=lag), f"suspension lag {lag} months"))
    results.append(summarize(phase_rows(progs, trials, snap, uncertain_as_approved=True),
                             "uncertain approvals counted as approved"))
    results.append(summarize(phase_rows(progs, trials, snap, shared_entry=True),
                             "shared trials mark entry for every program of the entity"))
    mature = phase_rows(progs, trials, snap, window=MATURE_WINDOW)
    results.append(summarize(mature, "phase entry 2015-2019 (at least six years of follow-up)"))
    results.append(summarize(mature[mature.us_site], "phase entry 2015-2019, developed in the US"))
    pd.DataFrame(results).to_csv(os.path.join(OUT, "loa_overall.csv"), index=False)

    by_area = [summarize(g, a) for a, g in rows.groupby("bio_area")
               if a != "unmapped" and g.moiety_id.nunique() >= 20]
    pd.DataFrame(by_area).sort_values("loa", ascending=False).to_csv(os.path.join(OUT, "loa_by_area.csv"), index=False)
    by_mod = [summarize(g, m) for m, g in rows.groupby("modality")
              if m != "unknown" and g.moiety_id.nunique() >= 20]
    pd.DataFrame(by_mod).sort_values("loa", ascending=False).to_csv(os.path.join(OUT, "loa_by_modality.csv"),
                                                                   index=False)
    by_year = rows[rows.phase == 1].groupby("entry_year").event.value_counts().unstack(fill_value=0)
    by_year.to_csv(os.path.join(OUT, "ph1_outcome_by_entry_year.csv"))

    modes = failure_modes(rows, trials, frame.trial_outcomes())
    modes.to_csv(os.path.join(OUT, "failure_modes_programs.csv"), index=False)
    tab = modes.pivot_table(index="reason", columns="phase", values="program_id", aggfunc="count", fill_value=0)
    tab.to_csv(os.path.join(OUT, "failure_modes_by_phase.csv"))
    share = lambda col: {str(k): {r: float(v) for r, v in g.value_counts(normalize=True).items()}
                         for k, g in modes.groupby("phase")[col]} | {"all": {
                             r: float(v) for r, v in modes[col].value_counts(normalize=True).items()}}
    endpoint = modes[modes.reason == "efficacy: primary endpoint not met"]
    failure_numbers = {"n_suspended": int(len(modes)), "reason_share": share("reason"),
                       "family_share": share("family"),
                       "endpoint_not_met_from_publication": float((endpoint.results_source == "publication").mean())}

    overall = results[0]
    numbers = {"snapshot": str(snap), "lag_months": LAG_MONTHS, "horizon_years": HORIZON_YEARS,
               "scale": scale(rows, progs, trials), "overall": overall, "us_site": results[1],
               "novel": results[2], "not_novel": results[3],
               "lag": {r["label"].split()[-2]: r for r in results[4:7]}, "uncertain_as_approved": results[7],
               "shared_entry": results[8], "mature": results[9], "mature_us": results[10],
               "failure_modes": failure_numbers}
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(numbers, f, indent=1, default=float)
    print(json.dumps(overall, indent=1, default=float))


if __name__ == "__main__":
    main()
