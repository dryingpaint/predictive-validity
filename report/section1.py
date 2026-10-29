"""Section 1: phase transitions, likelihood of approval and failure modes.

    python -m report.section1

Unit: a development program = (molecular entity, development indication). For
each phase p, the cohort is programs whose first industry-sponsored phase-p
trial started in WINDOW (2008-2019, so every entry has at least six years to
the snapshot), that had not entered a later phase earlier, and whose entity was
not already FDA-approved for the disease (a lifecycle program).
Each program then either advanced (a later-phase trial of its own, by any
sponsor, started, or FDA approval for the disease), was suspended (none of its
own trials, by any sponsor, or of the trials that marked its Phase 1 entry,
active or active within LAG months of the snapshot), or is censored (still
active or too recent to call). A phase a program skipped on its way to a later
phase or to approval counts as a success in that phase, as in BIO's report. The
BIO-style rate is advanced / (advanced + suspended); the Aalen-Johansen
estimate keeps censored programs in the risk set with suspension as a competing
event. LOA is the product over phases. Programs with no disease
(healthy-volunteer, basket or symptom trials only) enter the Phase 1 and Phase
2 cohorts but not Phase 3: FDA approval is judged per disease. Confidence
intervals resample molecular entities (programs of one entity are not
independent); a cohort with fewer than MIN_RESOLVED_ENTITIES entities resolved
in a phase gets no LOA.
"""
from __future__ import annotations

import json
import os
from datetime import date

import numpy as np
import pandas as pd
from lifelines import AalenJohansenFitter
from scipy.stats import spearmanr

from pipeline.fda import LETTERS_FROM
from report import bio, frame

OUT = os.path.join(frame.REPO, "report", "output", "section1")
LAG_MONTHS = 24
WINDOW = (date(2008, 1, 1), date(2019, 12, 31))  # headline phase entries: at least six years to the snapshot
RECENT_WINDOW = frame.WINDOW  # entries through 2025, many of them still running at the snapshot
PERIODS = [(date(2008, 1, 1), date(2011, 12, 31)), (date(2012, 1, 1), date(2015, 12, 31)),
           (date(2016, 1, 1), date(2019, 12, 31))]
HORIZON_YEARS = 6.0
N_BOOT = 1000
SEED = 20261020
MIN_RESOLVED_ENTITIES = 10  # per phase, below which a cohort's LOA and intervals are not estimated


BEFORE_LETTERS = pd.Timestamp(LETTERS_FROM) - pd.Timedelta(days=1)  # the latest date an approval that predates the letters can carry


def approval_dates(p: pd.DataFrame, approved: pd.Series) -> pd.Series:
    """Approval date of each approved program (p indexed by program_id). An approval known
    only to predate the first approval letter read, or undated, is placed at the earliest
    date it could have happened, the entity's first FDA approval, so that a program
    entering after it is treated as a lifecycle program."""
    dated = pd.to_datetime(p.first_approval_date).where(p.date_basis.eq("dated"))
    earliest = pd.to_datetime(p.moiety_first_fda_approval).clip(upper=BEFORE_LETTERS).fillna(BEFORE_LETTERS)
    return dated.where(~(approved & p.date_basis.isin(["before_letters", "undated"])), earliest).where(approved)


def own_trials(progs: pd.DataFrame, trials: pd.DataFrame) -> pd.Series:
    """Whether each trial row is one of its program's own trials: it lists the program's
    disease, or, for an entity's disease-unspecified program, it is one of the entity's
    healthy-volunteer, basket and symptom trials."""
    unspecified = trials.program_id.map(progs.set_index("program_id").mondo_id).isna()
    return (trials.attach.isin(["disease", "non_disease_condition"])
            | (trials.attach.isin(["no_disease", "basket"]) & unspecified))


def activity(trials: pd.DataFrame, snap: date) -> tuple[pd.Series, pd.Series]:
    """Per program: when its last trial ended (the snapshot for an active trial), and whether one is active."""
    end = trials.assign(end=np.where(trials.active, pd.Timestamp(snap), pd.to_datetime(trials.end)))
    return end.groupby("program_id").end.max(), trials.groupby("program_id").active.any()


def phase_rows(progs: pd.DataFrame, trials: pd.DataFrame, snap: date, lag_months: int = LAG_MONTHS,
               uncertain_as_approved: bool = False, window: tuple[date, date] = frame.WINDOW,
               shared_entry: bool = False, vaccines: bool = False) -> pd.DataFrame:
    """One row per (program, phase) in that phase's cohort; phase entry must fall in `window`.
    shared_entry=True lets every shared trial count for every program, for entry,
    advancement and activity alike (as if each indication began with the entity's
    first trials). Vaccines are left out unless vaccines=True: strain-updated
    formulations are licensed under the parent product and never approved under
    their own names, so their programs cannot be followed to approval."""
    t = trials[trials.start_date.notna()].copy()
    t["active"] = t.overall_status.isin(frame.ACTIVE)
    # A trial that has not started (not yet recruiting, or gone silent before its estimated start date)
    # neither marks phase entry nor advances a program; it still counts as activity.
    t["started"] = ~(t.overall_status.eq("NOT_YET_RECRUITING")
                     | (t.overall_status.eq("UNKNOWN") & t.start_date_type.eq("ESTIMATED")
                        & (pd.to_datetime(t.last_update_posted) < pd.to_datetime(t.start_date))))
    t["end"] = t.completion_date.fillna(t.primary_completion_date).fillna(t.start_date)
    # Shared trials (a healthy-volunteer study, a "solid tumors" basket) count only toward
    # Phase 1 entry of the lead indication, and keep that Phase 1 program active while
    # they run. Phase entry is industry-sponsored; advancement and whether the disease is
    # still in development come from the program's own trials by any sponsor (a
    # cooperative-group Phase 3 of a company's drug is development). A later-phase trial
    # advances a program once it has started, not while it is only registered.
    own = t if shared_entry else t[own_trials(progs, t)]
    # An extension study, or a trial the entity joins only after its main period, neither enters nor
    # advances a phase (starts_phase); it still counts as activity.
    starting = own[own.starts_phase]
    ind = t[t.industry & t.starts_phase]
    entry_trials = ind if shared_entry else pd.concat([starting[starting.industry], ind[(ind.phase == 1) & ind.marks_entry]])
    entered = entry_trials[entry_trials.started]
    starts = entered.pivot_table(index="program_id", columns="phase", values="start_date", aggfunc="min")
    later = starting[starting.started].pivot_table(
        index="program_id", columns="phase", values="start_date", aggfunc="min")
    last, active = activity(own, snap)
    last1, active1 = activity(pd.concat([own, entry_trials[entry_trials.phase == 1]])
                              .drop_duplicates(["program_id", "nct_id"]), snap)
    us = set(zip(entered.program_id[entered.us_site], entered.phase[entered.us_site]))

    p = progs.set_index("program_id")
    appr_date = approval_dates(p, p.approved.eq("yes") | (uncertain_as_approved & p.approved.eq("uncertain")))
    cutoff = pd.Timestamp(snap) - pd.DateOffset(months=lag_months)

    rows = []
    for pid in starts.index:
        if pid not in p.index or (not vaccines and p.at[pid, "modality"] == "vaccine"):
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
            on, end_at = (active1, last1) if phase == 1 else (active, last)
            if advance is not None and advance <= pd.Timestamp(snap):
                event, end = "advanced", advance
            elif on.get(pid, False):
                event, end = "censored", pd.Timestamp(snap)
            elif end_at.get(pid, entry) <= cutoff:
                event, end = "suspended", end_at.get(pid, entry)
            else:
                event, end = "censored", pd.Timestamp(snap)
            first_fda = p.at[pid, "moiety_first_fda_approval"]
            row = {
                "program_id": pid, "moiety_id": p.at[pid, "moiety_id"], "phase": phase, "entry": entry,
                "event": event, "event_date": end, "years": max((end - entry).days, 0) / 365.25,
                "credited": False,
                "bio_area": p.at[pid, "bio_area"] if pd.notna(p.at[pid, "bio_area"]) else "unmapped",
                "modality": p.at[pid, "modality"] if pd.notna(p.at[pid, "modality"]) else "unknown",
                "novel": pd.isna(first_fda) or pd.Timestamp(first_fda) > entry,
                "us_site": (pid, phase) in us, "entry_year": entry.year,
                "approval_date": a if pd.notna(a) else None,
            }
            rows.append(row)
            if event == "advanced":  # phases skipped on the way count as successes in them
                to = next((q for q in (2, 3) if q > phase and pd.notna(nxt.get(q))
                           and pd.Timestamp(nxt.get(q)) == advance), 4)  # 4: approval
                rows += [{**row, "phase": q, "credited": True} for q in range(phase + 1, to)
                         if pd.isna(s.get(q)) and not (q == 3 and pd.isna(p.at[pid, "mondo_id"]))]
    # Rows are ordered by (entity, disease, phase), which a rebuild of the programs
    # keeps, rather than by program id, which each build reassigns.
    out = pd.DataFrame(rows)
    return out.assign(_disease=out.program_id.map(p.mondo_id).fillna("")) \
              .sort_values(["moiety_id", "_disease", "phase"]).drop(columns="_disease").reset_index(drop=True)


def rates(rows: pd.DataFrame) -> pd.DataFrame:
    """Per phase: counts and the BIO-style advanced / (advanced + suspended)."""
    c = rows.pivot_table(index="phase", columns="event", values="program_id", aggfunc="count", fill_value=0)
    for col in ("advanced", "suspended", "censored"):
        if col not in c:
            c[col] = 0
    c["rate"] = c.advanced / (c.advanced + c.suspended)
    return c[["advanced", "suspended", "censored", "rate"]]


def loa(rows: pd.DataFrame) -> float:
    """Likelihood of approval from Phase 1: the product of the BIO-style phase rates."""
    rate = rates(rows).rate
    return float(np.prod([rate.get(ph, np.nan) for ph in (1, 2, 3)]))


def resolved_counts(rows: pd.DataFrame, cluster: np.ndarray, group: pd.Series) -> tuple[np.ndarray, list]:
    """Advanced and suspended counts per cluster (codes 0..k-1, one per row), for
    each group and phase: array [cluster, group, phase, (advanced, suspended)]."""
    groups = sorted(group.unique())
    counts = np.zeros((cluster.max() + 1, len(groups), 3, 2))
    r = rows.event.isin(["advanced", "suspended"]).to_numpy()
    np.add.at(counts, (cluster[r], group[r].map({g: i for i, g in enumerate(groups)}).to_numpy(),
                       rows.phase.to_numpy()[r] - 1, (rows.event[r] == "suspended").to_numpy().astype(int)), 1)
    return counts, groups


def boot_rates(counts: np.ndarray) -> np.ndarray:
    """Cluster bootstrap of the BIO-style rates from resolved_counts: array
    [draw, group, phase] over N_BOOT resamples of the clusters."""
    rng = np.random.default_rng(SEED)
    k = len(counts)
    c = np.stack([np.tensordot(np.bincount(rng.integers(0, k, k), minlength=k), counts, axes=1)
                  for _ in range(N_BOOT)])
    with np.errstate(invalid="ignore", divide="ignore"):
        return c[..., 0] / (c[..., 0] + c[..., 1])


def aalen_johansen(rows: pd.DataFrame) -> dict:
    """Cumulative incidence of advancement by HORIZON_YEARS per phase, with
    suspension as a competing event and censoring at the snapshot; programs that
    skipped the phase have no time in it and are left out."""
    out = {}
    for ph in (1, 2, 3):
        r = rows[(rows.phase == ph) & ~rows.credited]
        if r.empty:
            continue
        code = r.event.map({"advanced": 1, "suspended": 2, "censored": 0})
        ajf = AalenJohansenFitter(calculate_variance=False, seed=SEED)
        ajf.fit(r.years.clip(lower=1 / 365.25), code, event_of_interest=1)
        cif = ajf.cumulative_density_
        out[ph] = float(cif[cif.index <= HORIZON_YEARS].iloc[-1, 0]) if (cif.index <= HORIZON_YEARS).any() else np.nan
    out["loa"] = float(np.prod([out.get(ph, np.nan) for ph in (1, 2, 3)]))
    return out


def summarize(rows: pd.DataFrame, label: str) -> dict:
    r = rates(rows)
    counts, _ = resolved_counts(rows, pd.factorize(rows.moiety_id, sort=True)[0], pd.Series(True, index=rows.index))
    resolved = (counts[:, 0].sum(axis=2) > 0).sum(axis=0)  # entities with a resolved program, per phase
    estimable = bool((resolved >= MIN_RESOLVED_ENTITIES).all())
    d = boot_rates(counts)[:, 0]
    ci = pd.DataFrame({1: d[:, 0], 2: d[:, 1], 3: d[:, 2], "loa": d.prod(axis=1)}).quantile([0.025, 0.975])
    aj = aalen_johansen(rows)
    res = {"label": label}
    for ph in (1, 2, 3):
        if ph in r.index:
            res[f"ph{ph}_n_advanced"] = int(r.at[ph, "advanced"])
            res[f"ph{ph}_n_suspended"] = int(r.at[ph, "suspended"])
            res[f"ph{ph}_n_censored"] = int(r.at[ph, "censored"])
            res[f"ph{ph}_n_entities_resolved"] = int(resolved[ph - 1])
            res[f"ph{ph}_rate"] = float(r.at[ph, "rate"])
            ok = resolved[ph - 1] >= MIN_RESOLVED_ENTITIES
            res[f"ph{ph}_lo"] = float(ci.at[0.025, ph]) if ok else np.nan
            res[f"ph{ph}_hi"] = float(ci.at[0.975, ph]) if ok else np.nan
            res[f"ph{ph}_aj"] = aj.get(ph)
    res["loa"] = loa(rows) if estimable else np.nan
    res["loa_lo"] = float(ci.at[0.025, "loa"]) if estimable else np.nan
    res["loa_hi"] = float(ci.at[0.975, "loa"]) if estimable else np.nan
    res["loa_aj"] = aj["loa"]
    res["n_entities"] = int(rows.moiety_id.nunique())
    return res


REASON_ORDER = [
    ("efficacy: stated", "biology"), ("efficacy: primary endpoint not met", "biology"),
    ("safety", "biology"), ("PK, dose or formulation", "biology"),
    ("business or strategic (explicit)", "business"), ("sponsor decision, unspecified", "unspecified"),
    ("enrollment, operational or regulatory", "operational"),
    ("positive readout, not advanced", "positive_readout"), ("other stated reason", "other"),
    ("results posted, no reason stated, endpoint not assessable", "results_unread"),
    ("completed, no results posted, no reason stated", "unexplained"),
    ("stopped, no reason stated", "unexplained"),
]
OPERATIONAL = {"enrollment_feasibility", "operational_or_site", "regulatory", "manufacturing_supply", "covid19",
               "replaced_by_new_protocol"}


def trial_reason(o: pd.Series | None, status: str, has_results: bool) -> str:
    """Reason one trial of the stopping phase gives; a trial with no outcome row or
    no stated reason falls into a "no reason stated" category, split by whether it
    posted results."""
    unstated = ("results posted, no reason stated, endpoint not assessable" if has_results
                else "completed, no results posted, no reason stated" if status == "COMPLETED"
                else "stopped, no reason stated")
    if o is None:
        return unstated
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
    if o.stop_reason == "other":
        return "other stated reason"
    return unstated


def failure_modes(rows: pd.DataFrame, progs: pd.DataFrame, trials: pd.DataFrame,
                  outcomes: pd.DataFrame) -> pd.DataFrame:
    """One reason per suspended program: the highest-priority reason among its own
    industry trials of the phase it stopped in (in Phase 1, also the trials that
    marked its entry), the first such trial by NCT id."""
    rank = {r: i for i, (r, _) in enumerate(REASON_ORDER)}
    family = dict(REASON_ORDER)
    out = outcomes.set_index("nct_id")
    stopped = rows[(rows.event == "suspended") & ~rows.credited][["program_id", "phase", "moiety_id", "bio_area",
                                                                  "modality"]]
    counted = own_trials(progs, trials) | ((trials.phase == 1) & trials.marks_entry)
    t = trials[trials.industry & counted].merge(stopped[["program_id", "phase"]], on=["program_id", "phase"])
    t["reason"] = [trial_reason(out.loc[n] if n in out.index else None, st, bool(hr))
                   for n, st, hr in zip(t.nct_id, t.overall_status, t.has_results)]
    t["results_source"] = t.nct_id.map(out.results_source)
    t["rank"] = t.reason.map(rank)
    best = t.sort_values(["rank", "nct_id"]).drop_duplicates(["program_id", "phase"])[
        ["program_id", "phase", "reason", "nct_id", "results_source"]]
    res = stopped.merge(best, on=["program_id", "phase"], how="left")
    res["reason"] = res.reason.fillna("stopped, no reason stated")
    res["family"] = res.reason.map(family)
    return res


TERMINATION_GROUPS = {"efficacy_futility": "efficacy", "safety_tolerability": "safety",
                      "pk_pd_or_formulation": "pk_formulation", "business_portfolio": "business",
                      "competitive_landscape": "business", "sponsor_decision_unspecified": "sponsor_decision",
                      "enrollment_feasibility": "enrollment_operational", "operational_or_site": "enrollment_operational",
                      "regulatory": "regulatory", "manufacturing_supply": "enrollment_operational", "covid19": "covid19",
                      "replaced_by_new_protocol": "planned_or_replaced", "objectives_met_or_early_success": "planned_or_replaced",
                      "other": "other"}


def termination_reasons() -> dict:
    """Stated reasons of industry Phase 1-3 trials started in WINDOW that stopped
    early or were withdrawn with a reason given: the trial-level denominator the
    draft report used."""
    t = frame.query("""SELECT o.stop_reason FROM preclin.trial_outcome o JOIN preclin.ctgov_study s USING (nct_id)
                       WHERE o.execution <> 'completed' AND o.stop_reason NOT IN ('not_stated', 'not_applicable')
                         AND s.lead_sponsor_class = 'INDUSTRY' AND s.start_date BETWEEN %s AND %s""", WINDOW)
    groups = t.stop_reason.map(TERMINATION_GROUPS).value_counts(normalize=True)
    return {"n": int(len(t)), **{g: float(v) for g, v in groups.items()}}


def scale(rows: pd.DataFrame) -> dict:
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
               (SELECT count(*) FROM preclin.dev_program) AS programs,
               (SELECT count(*) FROM preclin.dev_program_approval) AS approval_judgements,
               (SELECT count(*) FROM preclin.dev_program_approval WHERE approved = 'uncertain') AS approvals_uncertain
        """, WINDOW).iloc[0]
    out = {k: int(v) for k, v in q.items()}
    out.update({"cohort_programs": int(rows.program_id.nunique()), "cohort_entities": int(rows.moiety_id.nunique()),
                "cohort_rows_by_phase": {int(k): int(v) for k, v in rows[~rows.credited].phase.value_counts().sort_index().items()},
                "cohort_approved_programs": int(rows[rows.approval_date.notna()].program_id.nunique()),
                "credited_rows_by_phase": {int(k): int(v) for k, v in rows[rows.credited].phase.value_counts().sort_index().items()}})
    return out


def by_period(rows: pd.DataFrame) -> pd.DataFrame:
    """Phase rates and LOA of the programs entering a phase in each of PERIODS, for all
    programs and for US-developed ones (us_ columns)."""
    out = []
    for lo, hi in PERIODS:
        g = rows[rows.entry.between(pd.Timestamp(lo), pd.Timestamp(hi))]
        us = {f"us_{k}": v for k, v in summarize(g[g.us_site], "").items() if k != "label"}
        out.append({**summarize(g, f"{lo.year}-{hi.year}"), **us})
    return pd.DataFrame(out)


def by_year(rows: pd.DataFrame) -> pd.DataFrame:
    """Per phase and entry year: advanced, suspended and still-running programs, and the
    BIO-style rate among the resolved."""
    r = rows.groupby(["phase", "entry_year"]).event.value_counts().unstack(fill_value=0)
    for col in ("advanced", "suspended", "censored"):
        if col not in r:
            r[col] = 0
    r = r.assign(rate=r.advanced / (r.advanced + r.suspended),
                 censored_share=r.censored / (r.advanced + r.suspended + r.censored))
    return r.reset_index()[["phase", "entry_year", "advanced", "suspended", "censored", "rate", "censored_share"]]


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    snap = frame.snapshot()
    progs, trials = frame.programs(), frame.program_trials()
    rows = phase_rows(progs, trials, snap, window=WINDOW)
    rows.to_csv(os.path.join(OUT, "phase_cohort_rows.csv"), index=False)

    results = [summarize(rows, "all programs")]
    results.append(summarize(rows[rows.us_site], "programs with a US-sited industry trial in the phase"))
    results.append(summarize(rows[rows.novel], "entity not yet FDA-approved at phase entry"))
    results.append(summarize(rows[~rows.novel], "entity already FDA-approved for another disease"))
    for lag in (12, 18, 36):
        results.append(summarize(phase_rows(progs, trials, snap, lag_months=lag, window=WINDOW),
                                 f"suspension lag {lag} months"))
    results.append(summarize(phase_rows(progs, trials, snap, uncertain_as_approved=True, window=WINDOW),
                             "uncertain approvals counted as approved"))
    results.append(summarize(phase_rows(progs, trials, snap, shared_entry=True, window=WINDOW),
                             "shared trials mark entry for every program of the entity"))
    results.append(summarize(phase_rows(progs, trials, snap, vaccines=True, window=WINDOW), "including vaccines"))
    recent = phase_rows(progs, trials, snap, window=RECENT_WINDOW)
    results.append(summarize(recent, "phase entry 2015-2025 (many programs still running)"))
    results.append(summarize(recent[recent.us_site], "phase entry 2015-2025, developed in the US"))
    pd.DataFrame(results).to_csv(os.path.join(OUT, "loa_overall.csv"), index=False)

    for column, name, skip in (("bio_area", "area", "unmapped"), ("modality", "modality", "unknown")):
        strata = []
        for value, g in rows.groupby(column):
            if value == skip or g.moiety_id.nunique() < 20:
                continue
            us = g[g.us_site]
            strata.append({**summarize(g, value), **{f"us_{k}": v for k, v in summarize(us, value).items()
                                                      if k != "label"}} if us.moiety_id.nunique() >= 20
                          else summarize(g, value))
        pd.DataFrame(strata).sort_values("loa", ascending=False).to_csv(
            os.path.join(OUT, f"loa_by_{name}.csv"), index=False)
    periods = by_period(rows)
    periods.to_csv(os.path.join(OUT, "loa_by_period.csv"), index=False)
    by_year(rows).to_csv(os.path.join(OUT, "rates_by_entry_year.csv"), index=False)

    modes = failure_modes(rows, progs, trials, frame.trial_outcomes())
    modes.to_csv(os.path.join(OUT, "failure_modes_programs.csv"), index=False)
    tab = modes.pivot_table(index="reason", columns="phase", values="program_id", aggfunc="count", fill_value=0)
    tab.to_csv(os.path.join(OUT, "failure_modes_by_phase.csv"))
    share = lambda col: {str(k): {r: float(v) for r, v in g.value_counts(normalize=True).items()}
                         for k, g in modes.groupby("phase")[col]} | {"all": {
                             r: float(v) for r, v in modes[col].value_counts(normalize=True).items()}}
    endpoint = modes[modes.reason == "efficacy: primary endpoint not met"]
    biology = {}
    for ph, g in modes.groupby("phase"):
        eff = g.reason.isin(["efficacy: stated", "efficacy: primary endpoint not met"]).sum()
        saf = (g.reason == "safety").sum()
        biology[str(ph)] = {"efficacy": float(eff / len(g)), "safety": float(saf / len(g)),
                            "safety_of_efficacy_or_safety": float(saf / (eff + saf)) if eff + saf else None}
    terminations = termination_reasons()
    failure_numbers = {"n_suspended": int(len(modes)), "reason_share": share("reason"),
                       "family_share": share("family"),
                       "endpoint_not_met_from_publication": float((endpoint.results_source == "publication").mean()),
                       "biology": biology, "terminations": terminations}

    overall = results[0]
    strata = {name: {r["label"]: r for r in pd.read_csv(os.path.join(OUT, f"loa_by_{name}.csv")).to_dict(orient="records")}
              for name in ("area", "modality")}
    rank_bio = {}  # Spearman correlation of stratum LOA with BIO's, over the strata BIO also reports
    for name, ref in (("area", bio.AREA_LOA), ("modality", bio.MODALITY_LOA)):
        for col in ("loa", "us_loa"):
            shared = [k for k in ref if pd.notna(strata[name].get(k, {}).get(col, np.nan))]
            rank_bio[f"{name}_{col}"] = float(spearmanr([strata[name][k][col] for k in shared],
                                                        [ref[k] for k in shared]).statistic)
            rank_bio[f"{name}_{col}_n"] = len(shared)
    numbers = {"snapshot": str(snap), "lag_months": LAG_MONTHS, "horizon_years": HORIZON_YEARS,
               "scale": scale(rows), "overall": overall, "us_site": results[1],
               "purpose": dict(frame.query("SELECT purpose, count(*)::int AS n FROM preclin.trial_purpose GROUP BY 1")
                               .itertuples(index=False)),
               "novel": results[2], "not_novel": results[3],
               "lag": {r["label"].split()[-2]: r for r in results[4:7]}, "uncertain_as_approved": results[7],
               "shared_entry": results[8], "with_vaccines": results[9], "recent": results[10],
               "recent_us": results[11], "periods": {r["label"]: r for r in periods.to_dict(orient="records")},
               "failure_modes": failure_numbers, "rank_correlation_with_bio": rank_bio, **strata}
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(numbers, f, indent=1, default=float)
    print(json.dumps(overall, indent=1, default=float))


if __name__ == "__main__":
    main()
