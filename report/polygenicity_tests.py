"""Polygenicity (#147), the half that joins outcomes: P1-P3, the sensitivities as amended on 2026-11-24, the negative
control, the power simulation and the descriptives.

Imported by report.polygenicity.main only once CUTPOINTS is set (the tertiles fixed in the dated comment). The
definitions: entries with a resolved primary target (has_target_disease); P1 on Phase 2 and 3 entries with
COVARS_23, P2 and P3 on Phase 2 entries with COVARS; the top tertile against the bottom, the middle reported; errors
clustered by disease; p one-sided in the registered direction (SIDES) and Holm across the three, read as the #140
confirmation reads its tests (confirmed, same direction not confirmed, not replicated). P3 is the interaction of
the top tertile with human genetic support (g3 > 0) in one model, estimable when each of its four cells holds at
least MIN_TARGETS target sets and one S4 event.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from pipeline.stops import keys
from report import stop_causes
from report.engaged_modes import engaged_modes
from report.evidence_analysis import COVARS_23, traced_stops
from report.failure_modes import with_modes
from report.section3 import COVARS, MIN_TARGETS, coef, estimate, jsonable, poisson

SIDES = {"P1": 1, "P2": -1, "P3": -1}
OUTCOMES = {"P1": "mode_not_causal", "P2": "s4", "P3": "s4"}
ALPHA = 0.05
CLUSTER = "mondo_id"
PHASES = {"mode_not_causal": (2, 3), "s4": (2, 2)}
UNRELATED = ("sponsor_decision", "operational")   # stop causes unrelated to the disease's biology (the negative control)
EFFECTS = {"P1": (1.25, 1.5, 2.0), "P2": (0.8, 0.67, 0.5), "P3": (0.8, 0.67, 0.5)}   # risk ratios the power simulation posits
GENETICS_RR = 2.0   # the S4 advantage of human genetic support the P3 simulation assumes (about the published twofold)


def frame_with_outcomes(d: pd.DataFrame, u: pd.DataFrame, cuts: tuple[float, float]) -> pd.DataFrame:
    """The unit's US Phase 2 and 3 entries with their traced stops, failure modes and the profile joined, the
    tertiles by the fixed cutpoints, `genetics` (g3 > 0), `top`, the sensitivity columns, and `stop_unrelated`
    (the traced cause is a sponsor decision or operational: the negative control's outcome)."""
    from report.polygenicity import tertile  # noqa: PLC0415
    e = d[d.us_site & d.phase.between(2, 3) & d.mondo_id.isin(u.mondo_id)].copy()
    e = with_modes(traced_stops(e))
    u, _ = alternative_tertiles(u, cuts)
    cols = ["mondo_id", "score", "log10_score", "mendelian_form", "n_eff", "ldsc_status", "scored",
            "k_source", "h2_z", "h2_liab", "loci", "loci_catalog", "gwas_genes_per_10k_cases", "me_log10", "label",
            "tertile_k", "tertile_v3", "tertile_resid"]
    e = e.merge(u[[c for c in cols if c in u.columns]], on="mondo_id", how="left")
    e["tertile"] = tertile(e.score.where(e.scored.fillna(False)), cuts)
    e["genetics"] = (e.g3 > 0).astype(float)
    e["log10_n_eff"] = np.log10(e.n_eff.astype(float))
    e["mendelian_level"] = np.where(e.mendelian_form.fillna(False).astype(bool), "yes", "no")
    e["target"] = e.target.fillna("entity " + e.moiety_id.astype(str))
    h = engaged_modes()
    k = pd.Series(keys(e), index=e.index)
    e["not_causal_basis"] = k.map(dict(zip(h.key, h.not_causal_basis)))
    t = stop_causes.load()
    e["stop_unrelated"] = k.map(dict(zip(t.key, t.likely.isin(UNRELATED)))).fillna(False).astype(float)
    return e


def residual_score(u: pd.DataFrame) -> dict:
    """The post hoc of Melissa's decision of 2026-11-26: log10 score regressed on log10 effective sample size over
    the scored diseases by least squares; the per-disease residual (indexed by mondo_id) and the fit."""
    s = u[u.scored.fillna(False).astype(bool) & u.log10_score.notna() & u.n_eff.notna()]
    x, y = np.log10(s.n_eff.astype(float).values), s.log10_score.astype(float).values
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (intercept + slope * x)
    r2 = float(1 - resid.var() / y.var()) if len(y) > 1 and y.var() > 0 else None
    return {"diseases": int(len(s)), "slope": float(slope), "intercept": float(intercept), "r2": r2,
            "residual": pd.Series(resid, index=s.mondo_id.values)}


def tertile_changes(u: pd.DataFrame, a: str, b: str) -> dict:
    """How many diseases sit in a different tertile under cut `b` than under cut `a`: moves between tertiles,
    diseases scored under `a` but not `b` (lost), under `b` but not `a` (gained), and which."""
    moved = u[u[a].ne(u[b])]
    return {"changed": int(len(moved)), "between_tertiles": int((moved[a].ne("none") & moved[b].ne("none")).sum()),
            "lost_score": int((moved[a].ne("none") & moved[b].eq("none")).sum()),
            "gained_score": int((moved[a].eq("none") & moved[b].ne("none")).sum()), "diseases": sorted(moved.mondo_id)}


def alternative_tertiles(u: pd.DataFrame, cuts: tuple[float, float]) -> tuple[pd.DataFrame, dict]:
    """Per unit disease, beside the registered tertile (`cuts` on the stored score): the corrected-K tertile, re-cut
    over the diseases scored under the corrected K (score_k_corrected, migration 178; the decision of 2026-11-26),
    and the residual tertile, re-cut on the score residualised on GWAS size; with each cut's facts and the diseases
    that change tertile. An unfilled corrected profile is a loud error, not a silent 'none'."""
    from report.polygenicity import cutpoints, tertile  # noqa: PLC0415
    if "score_k_corrected" not in u.columns or u.ldsc_status_k_corrected.isna().all():
        raise RuntimeError("preclin.disease_polygenicity's *_k_corrected columns are not filled: apply migration 178 and run "
                           "`python -m pipeline.polygenicity k-corrected`")
    out = u.copy()
    scored = out.scored.fillna(False).astype(bool)
    out["tertile"] = tertile(out.score.where(scored), cuts)
    scored_k = out.ldsc_status_k_corrected.eq("ok") & out.score_k_corrected.notna()
    cuts_k = cutpoints(out.score_k_corrected[scored_k])
    out["tertile_k"] = tertile(out.score_k_corrected.where(scored_k), cuts_k)
    rs = residual_score(out)
    resid = out.mondo_id.map(rs["residual"])
    cuts_r = cutpoints(resid)
    out["tertile_resid"] = tertile(resid, cuts_r)
    k = {"scored_diseases": int(scored_k.sum()), "cutpoints": {"lower": cuts_k[0], "upper": cuts_k[1]},
         "changes": tertile_changes(out, "tertile", "tertile_k")}
    if "k_corrected_code" in out.columns:   # the real profile: how many scored Pan-UKB codes the corrected rule changes
        ukb = scored & out.k_source.eq("panukb")
        k.update({"panukb_scored": int(ukb.sum()),
                  "code_changed": int((ukb & (out.k_corrected_code.ne(out.k_code) | out.k_corrected_source.ne("panukb"))).sum()),
                  "via_parent": int(out.k_corrected_via_parent.fillna(False).astype(bool)[scored_k].sum()),
                  "k_sources": {str(a): int(b) for a, b in out.k_corrected_source[scored_k].value_counts().items()}})
    # rule v3 (preclin.disease_polygenicity_k, migration 181; announced on #147 2026-11-27 after the independent code check)
    if "score_v3" not in out.columns or out.ldsc_status_v3.isna().all():
        raise RuntimeError("preclin.disease_polygenicity_k has no v3 rows: apply migration 181 and run `python -m pipeline.polygenicity k-rules`")
    scored_v3 = out.ldsc_status_v3.eq("ok") & out.score_v3.notna()
    cuts_v3 = cutpoints(out.score_v3[scored_v3])
    out["tertile_v3"] = tertile(out.score_v3.where(scored_v3), cuts_v3)
    v3 = {"scored_diseases": int(scored_v3.sum()), "cutpoints": {"lower": cuts_v3[0], "upper": cuts_v3[1]},
          "changes": tertile_changes(out, "tertile", "tertile_v3"),
          "category_scored": int((out.category_v3.fillna(False).astype(bool) & scored).sum())}
    if "k_v3_code" in out.columns:
        v3.update({"code_changed": int((scored & (out.k_v3_code.fillna("").ne(out.k_code.fillna("")) | out.k_v3_source.ne(out.k_source))).sum()),
                   "k_sources": {str(a): int(b) for a, b in out.k_v3_source[scored_v3].value_counts().items()}})
    meta = {"k_corrected": k, "k_v3": v3,
            "residual": {**{a: b for a, b in rs.items() if a != "residual"}, "cutpoints": {"lower": cuts_r[0], "upper": cuts_r[1]},
                         "changes": tertile_changes(out, "tertile", "tertile_resid")}}
    return out, meta


def cohort(d: pd.DataFrame, outcome: str, levels: tuple[str, str] = ("top", "bottom"), col: str = "tertile") -> pd.DataFrame:
    """Entries with a resolved target at the exposed and reference levels of `col`, in the outcome's phases, with
    `top` = 1 at the exposed level."""
    lo, hi = PHASES[outcome]
    c = d[d.has_target_disease.fillna(False).astype(bool) & d[col].isin(levels) & d.phase.between(lo, hi)].copy()
    c["top"] = (c[col] == levels[0]).astype(float)
    return c


def one_sided(t: dict, side: int) -> dict:
    if not t or "rr" not in t:
        return t
    on_side = side * np.log(t["rr"]) > 0
    return {**t, "p_one_sided": t["p"] / 2 if on_side else 1 - t["p"] / 2}


def holm_family(p: dict[str, float | None], m: int = 3) -> dict[str, float]:
    """Holm over the registered family of `m` tests: a test that is not estimable keeps its place in the family
    (its p is unknown, not absent), so the others are corrected as if it were there."""
    order = sorted((v, k) for k, v in p.items() if v is not None and np.isfinite(v))
    adj, running = {}, 0.0
    for i, (v, k) in enumerate(order):
        running = max(running, min(1.0, v * (m - i)))
        adj[k] = running
    return adj


def group_counts(c: pd.DataFrame, outcome: str) -> dict:
    return {"exposed_entries": int((c.top > 0).sum()), "exposed_events": int(c.loc[c.top > 0, outcome].sum()),
            "reference_entries": int((c.top <= 0).sum()), "reference_events": int(c.loc[c.top <= 0, outcome].sum())}


def p1(d: pd.DataFrame, covars=COVARS_23, extra: tuple[str, ...] = (), levels=("top", "bottom"), col="tertile") -> dict:
    c = cohort(d, "mode_not_causal", levels, col)
    return {**estimate(c, "mode_not_causal", "top", covars + extra, cluster=CLUSTER), **group_counts(c, "mode_not_causal")}


def p2(d: pd.DataFrame, covars=COVARS, extra: tuple[str, ...] = (), levels=("top", "bottom"), col="tertile") -> dict:
    c = cohort(d, "s4", levels, col)
    return {**estimate(c, "s4", "top", covars + extra, cluster=CLUSTER), **group_counts(c, "s4")}


def p3(d: pd.DataFrame, covars=COVARS, extra: tuple[str, ...] = (), levels=("top", "bottom"), col="tertile") -> dict:
    """The interaction of the top tertile with genetic support on S4, and the genetics ratio within each level."""
    c = cohort(d, "s4", levels, col).assign(top_x_genetics=lambda x: x.top * x.genetics)
    cells = {}
    for name, mask in (("top_genetics", (c.top > 0) & (c.genetics > 0)), ("top_no_genetics", (c.top > 0) & (c.genetics <= 0)),
                       ("bottom_genetics", (c.top <= 0) & (c.genetics > 0)), ("bottom_no_genetics", (c.top <= 0) & (c.genetics <= 0))):
        cells[name] = {"entries": int(mask.sum()), "targets": int(c.target[mask].nunique()), "events": int(c.s4[mask].sum())}
    ok = all(v["targets"] >= MIN_TARGETS and v["events"] >= 1 for v in cells.values())
    within = {}
    for lev in ("top", "bottom"):   # the genetics ratio within a tertile, whenever that tertile's own two cells allow it
        lev_ok = all(cells[f"{lev}_{g}"]["targets"] >= MIN_TARGETS and cells[f"{lev}_{g}"]["events"] >= 1
                     for g in ("genetics", "no_genetics"))
        within[lev] = (estimate(c[c.top == (1.0 if lev == "top" else 0.0)], "s4", "genetics", covars + extra, cluster=CLUSTER)
                       if lev_ok else {"estimable": False})
    out = {"cells": cells, "estimable": ok, **group_counts(c, "s4"), "n": int(len(c)), "n_targets": int(c.target.nunique()),
           "genetics_within": within}
    if not ok:
        return out
    fit = poisson(c, "s4", ["top", "genetics", "top_x_genetics"], covars + extra, cluster=CLUSTER)
    return {**out, **coef(fit, "top_x_genetics")}


def registered(d: pd.DataFrame, extra: tuple[str, ...] = (), col: str = "tertile",
               levels: tuple[str, str] = ("top", "bottom")) -> dict:
    """P1-P3 with one-sided p in the registered direction, Holm across the three, and the reading."""
    tests = {"P1": p1(d, extra=extra, levels=levels, col=col), "P2": p2(d, extra=extra, levels=levels, col=col),
             "P3": p3(d, extra=extra, levels=levels, col=col)}
    for k, t in tests.items():
        tests[k] = one_sided(t, SIDES[k])
    adj = holm_family({k: t.get("p_one_sided") for k, t in tests.items()})
    for k, t in tests.items():
        if "rr" in t:
            t["p_holm"] = adj[k]
            t["reading"] = ("confirmed" if adj[k] < ALPHA else
                            "same direction, not confirmed" if SIDES[k] * np.log(t["rr"]) > 0 else "not replicated")
        else:
            t["reading"] = "not estimable"
    return tests


def negative_control(d: pd.DataFrame, covars=COVARS_23) -> dict:
    """The P1 model with the outcome replaced by a stop whose traced cause is unrelated to the disease's biology
    (sponsor decision or operational), entries with a safety stop left out, p two-sided and outside the Holm
    family: no association is expected, and one would point to confounding by area or sponsor interest."""
    c = cohort(d, "mode_not_causal")
    c = c[c.stop_safety.fillna(0) <= 0]
    t = {**estimate(c, "stop_unrelated", "top", covars, cluster=CLUSTER), **group_counts(c, "stop_unrelated"), "sides": 2}
    t["reading"] = ("association" if t["p"] < ALPHA else "no association") if "rr" in t else "not estimable"
    return t


def sensitivities(d: pd.DataFrame) -> dict:
    """The sensitivities as amended on 2026-11-24: GWAS size and the Mendelian form, each P1-P3 with Holm within
    itself, and the negative control (one two-sided test outside any family); and, from the decision of 2026-11-26,
    the corrected K (tertile_k: the profile rescored under the own-code-first prevalence code, tertiles re-cut),
    P1-P3 with Holm within."""
    if "mendelian_level" not in d.columns:
        d = d.assign(mendelian_level=np.where(d.mendelian_form.fillna(False).astype(bool), "yes", "no"))
    return {"gwas_size": registered(d, extra=("log10_n_eff",)),
            "mendelian_form": registered(d, col="mendelian_level", levels=("no", "yes")),
            "negative_control": {"P1": negative_control(d)},
            "k_corrected": registered(d, col="tertile_k"),
            "k_v3": registered(d, col="tertile_v3")}


def post_hoc(d: pd.DataFrame, col: str = "tertile_resid") -> dict:
    """The post hoc of the decision of 2026-11-26, added after the readings: P1 and P2 on the tertiles of the score
    residualised on GWAS size, top against bottom, p two-sided, no Holm, outside the registered family; the direction
    is read against the registered one."""
    out = {}
    for k, fn in (("P1", p1), ("P2", p2)):
        t = {**fn(d, col=col), "sides": 2}
        if "rr" in t:
            t["reading"] = "association" if t["p"] < ALPHA else "no association"
            t["direction"] = "registered" if SIDES[k] * np.log(t["rr"]) > 0 else "opposite"
        else:
            t["reading"] = "not estimable"
        out[k] = t
    return out


def power_simulation(d: pd.DataFrame, reps: int = 200, seed: int = 0, disease_sd: float = 0.5,
                     effects: dict[str, tuple[float, ...]] = EFFECTS) -> dict:
    """Power of P1-P3 on this unit before any outcome is read by tertile: the entries, their tertiles, genetic
    support, covariates and disease clusters are the real ones; each outcome is drawn afresh per replicate from the
    event rate pooled over the whole unit, a disease random effect (log-scale SD disease_sd) and the posited risk
    ratio (P3: the ratio by which the top tertile's genetics advantage, GENETICS_RR, is multiplied). Power is the
    share of replicates below one-sided 0.05 and below 0.05 / 3, the Holm threshold for the smallest p."""
    rng = np.random.default_rng(seed)
    pooled = {"mode_not_causal": float(cohort(d, "mode_not_causal").mode_not_causal.mean()),
              "s4": float(cohort(d, "s4").s4.mean())}
    base = d.drop(columns=[c for c in ("mode_not_causal", "s4", "stop_unrelated", "stop_no_benefit") if c in d.columns])
    diseases = base.mondo_id.unique()
    top = base.tertile.eq("top").astype(float).values
    gen = base.genetics.fillna(0).astype(float).values
    hits = {k: {str(rr): [] for rr in v} for k, v in effects.items()}
    for _ in range(reps):
        u = dict(zip(diseases, rng.normal(0, disease_sd, len(diseases))))
        cluster = base.mondo_id.map(u).values
        for k, rrs in effects.items():
            for rr in rrs:
                if k == "P1":
                    risk = pooled["mode_not_causal"] * np.exp(cluster) * rr ** top
                elif k == "P2":
                    risk = pooled["s4"] * np.exp(cluster) * rr ** top
                else:
                    risk = pooled["s4"] * np.exp(cluster) * GENETICS_RR ** gen * rr ** (top * gen)
                sim = base.assign(**{OUTCOMES[k]: (rng.random(len(base)) < np.minimum(risk, 1.0)).astype(float)})
                t = one_sided({"P1": p1, "P2": p2, "P3": p3}[k](sim), SIDES[k])
                hits[k][str(rr)].append(t.get("p_one_sided"))
    power = {k: {rr: {"power": float(np.mean([p is not None and p < ALPHA for p in ps])),
                      "power_holm_smallest": float(np.mean([p is not None and p < ALPHA / 3 for p in ps])),
                      "estimable": float(np.mean([p is not None for p in ps]))} for rr, ps in v.items()}
             for k, v in hits.items()}
    return {"reps": reps, "seed": seed, "disease_sd": disease_sd, "genetics_rr": GENETICS_RR, "base_rates": pooled,
            "entries": {str(k): int(v) for k, v in base.tertile.value_counts().items()},
            "genetics_share": float(np.mean(gen)), "power": power}


def rates(d: pd.DataFrame, col: str) -> pd.DataFrame:
    """Per level of `col`, on the tests' denominator (entries with a resolved primary target): diseases, entries,
    not-causal stops and rate (Phase 2 and 3), S4 and rate (Phase 2); and the entries without a resolved target."""
    rows = []
    for level, g in d.groupby(col):
        resolved = g.has_target_disease.fillna(False).astype(bool)
        res = g[resolved]
        p2e = res[res.phase.eq(2)]
        rows.append({col: level, "diseases": int(g.mondo_id.nunique()), "entries": int(len(res)),
                     "phase2_entries": int(len(p2e)), "not_causal": int(res.mode_not_causal.sum()),
                     "not_causal_rate": float(res.mode_not_causal.mean()) if len(res) else None,
                     "s4": int(p2e.s4.sum()), "s4_rate": float(p2e.s4.mean()) if len(p2e) else None,
                     "without_target": int((~resolved).sum())})
    return pd.DataFrame(rows)


def gwas_size_check(u: pd.DataFrame, membership: pd.DataFrame) -> dict:
    """Does the score track GWAS size: Spearman of the score with the chosen study's n_eff over the scored diseases,
    and the median n_eff per tertile (the review finding of 2026-11-25, reported beside the null)."""
    s = u[u.scored & u.score.notna() & u.n_eff.notna()].merge(membership[["mondo_id", "tertile"]].drop_duplicates(),
                                                              on="mondo_id", how="left")
    out = {"n": int(len(s)), "spearman": None, "p": None,
           "median_n_eff": {str(k): float(v) for k, v in s.groupby("tertile").n_eff.median().items()}}
    if len(s) >= 3:
        rho, p = spearmanr(s.score, s.n_eff)
        out.update({"spearman": float(rho), "p": float(p)})
    return out


def panukb_check(u: pd.DataFrame) -> dict:
    """Pan-UKB's own liability-scale heritability of the matching ICD-10 code against ours, over the scored diseases
    with both: a descriptive check on the LDSC runs."""
    s = u[u.scored & u.h2_liab.notna() & u.panukb_h2_liab.notna()]
    out = {"n": int(len(s)), "spearman": None, "p": None}
    if len(s) >= 3:
        rho, p = spearmanr(s.h2_liab, s.panukb_h2_liab)
        out.update({"spearman": float(rho), "p": float(p)})
    return out


def descriptives(d: pd.DataFrame, u: pd.DataFrame) -> dict:
    from report.polygenicity import cutpoints, tertile  # noqa: PLC0415
    out = {"by_tertile": rates(d, "tertile").to_dict("records"),
           "area": d.groupby(["tertile", "bio_area"]).agg(entries=("mondo_id", "size"), diseases=("mondo_id", "nunique"))
                    .reset_index().to_dict("records"),
           "no_score": {"diseases": int((~u.scored).sum()), "entries": int(u.entries[~u.scored].sum()),
                        "status": u[~u.scored].groupby("ldsc_status").agg(diseases=("entries", "size"), entries=("entries", "sum"))
                                   .reset_index().to_dict("records"),
                        **{k: v for k, v in rates(d[d.tertile.eq("none")].assign(g="no_score"), "g").to_dict("records")[0].items()
                           if k != "g"}} if (d.tertile == "none").any() else {"diseases": 0, "entries": 0}}
    # inclusion at z >= 2
    z2 = u[u.h2_z.notna() & (u.h2_z >= 2) & u.h2_liab.notna() & (u.h2_liab > 0) & (u.h2_liab <= 1)
           & u.ldsc_status.isin(["ok", "low_z"])]
    out["z_at_least_2"] = {"diseases": int(len(z2)), "tests": {}}
    if len(z2) >= 6:
        sc = (z2.loci / z2.h2_liab)
        dd = d.merge(z2[["mondo_id"]].assign(score_z2=sc.values), on="mondo_id", how="left")
        dd["tertile_z2"] = tertile(dd.score_z2, cutpoints(sc))
        out["z_at_least_2"]["tests"] = registered(dd, col="tertile_z2")
    # GBD-K diseases only
    gk = d[d.k_source.eq("gbd") & d.scored.fillna(False).astype(bool)]   # scored diseases only: the ones the tests use
    out["gbd_k_only"] = {"diseases": int(gk.mondo_id.nunique()), "tests": registered(gk) if gk.mondo_id.nunique() >= 6 else {}}
    # the Catalog's all-study loci in place of the clumped loci
    cat = u[u.scored & u.loci_catalog.notna() & u.h2_liab.notna()]
    out["catalog_loci"] = {"diseases": int(len(cat)), "tests": {}}
    if len(cat) >= 6:
        sc = cat.loci_catalog / cat.h2_liab
        dd = d.merge(cat[["mondo_id"]].assign(score_cat=sc.values), on="mondo_id", how="left")
        dd["tertile_cat"] = tertile(dd.score_cat, cutpoints(sc))
        out["catalog_loci"]["tests"] = registered(dd, col="tertile_cat")
    # gene counts as the exposure
    gc = u[u.gwas_genes_per_10k_cases.notna()]
    out["gwas_genes"] = {"diseases": int(len(gc)), "tests": {}}
    if len(gc) >= 6:
        dd = d.copy()
        dd["tertile_genes"] = tertile(dd.gwas_genes_per_10k_cases, cutpoints(gc.gwas_genes_per_10k_cases))
        out["gwas_genes"]["tests"] = registered(dd, col="tertile_genes")
    # O'Connor
    me = u[u.me_log10.notna() & u.score.notna()]
    out["oconnor"] = {"n": int(len(me)), "spearman": None, "p": None,
                      "diseases": me[["mondo_id", "label", "score", "me_log10"]].to_dict("records")}
    if len(me) >= 3:
        rho, p = spearmanr(me.score, me.me_log10)
        out["oconnor"].update({"spearman": float(rho), "p": float(p)})
    # the basis of P1's not-causal calls
    c = cohort(d, "mode_not_causal")
    nc = c[c.mode_not_causal > 0]
    out["not_causal_basis"] = nc.groupby(["tertile", "not_causal_basis"]).size().reset_index(name="events").to_dict("records")
    out["gwas_size"] = gwas_size_check(u, d[["mondo_id", "tertile"]].drop_duplicates())
    out["panukb"] = panukb_check(u)
    return out


def results_table(families: dict) -> pd.DataFrame:
    rows = []
    for family, tests in families.items():
        for k, t in tests.items():
            rows.append({"family": family, "test": k, **{c: t.get(c) for c in ("rr", "lo", "hi", "p", "p_one_sided", "p_holm", "reading",
                                                                            "exposed_entries", "exposed_events",
                                                                            "reference_entries", "reference_events")}})
    return pd.DataFrame(rows, columns=["family", "test", "rr", "lo", "hi", "p", "p_one_sided", "p_holm", "reading",
                                       "exposed_entries", "exposed_events", "reference_entries", "reference_events"])


def numbers(e: pd.DataFrame, primary: dict, sens: dict, desc: dict, cuts, extra: dict | None = None,
            build_id: str | None = None, comment_id: str | None = None) -> dict:
    """numbers.json: the cohort, the cutpoints and the per-tertile rates keyed for the narrative, the tests, the
    sensitivities, the descriptives, and any extra block (the DALY descriptive) under its own key."""
    keyed = lambda c: {"lower": c[0], "upper": c[1]} if c is not None else None  # noqa: E731
    n = {"cohort": {"entries": int(len(e)), "phase2": int(e.phase.eq(2).sum()),
                    "with_target": int(e.has_target_disease.fillna(False).sum()),
                    "scored_entries": int(e.scored.fillna(False).sum()), "diseases": int(e.mondo_id.nunique()),
                    "scored_diseases": int(e.mondo_id[e.scored.fillna(False).astype(bool)].nunique())},
         "cutpoints": {"score": keyed(cuts)}, "build_id": build_id,
         "comment_id": comment_id, "covariates": {"P1": list(COVARS_23), "P2": list(COVARS), "P3": list(COVARS)},
         "tertiles": {r["tertile"]: r for r in desc.get("by_tertile", [])},
         "tests": primary, "sensitivities": sens, "descriptives": desc}
    n.update(extra or {})
    return n


def run_tests(d: pd.DataFrame, u: pd.DataFrame, extra: dict | None = None) -> dict:
    from report import polygenicity as pg  # noqa: PLC0415
    e = frame_with_outcomes(d, u, pg.CUTPOINTS)
    u2, alt = alternative_tertiles(u, pg.CUTPOINTS)
    primary = registered(e)
    sens = sensitivities(e)
    post = {"residual_gwas_size": {**alt["residual"], "tests": post_hoc(e)}}
    desc = descriptives(e, u)
    results_table({"primary": primary}).to_csv(os.path.join(pg.OUT, "tests.csv"), index=False)
    results_table({**sens, "post_hoc_residual": post["residual_gwas_size"]["tests"]}).to_csv(os.path.join(pg.OUT, "sensitivities.csv"), index=False)
    rates(e, "tertile").to_csv(os.path.join(pg.OUT, "tertiles.csv"), index=False)
    rates(e, "tertile_k").to_csv(os.path.join(pg.OUT, "tertiles_k_corrected.csv"), index=False)
    rates(e, "tertile_v3").to_csv(os.path.join(pg.OUT, "tertiles_v3.csv"), index=False)
    cols = ["mondo_id", "label", "bio_area", "entries", "ldsc_status", "k", "k_source", "k_code", "k_via_parent", "score", "tertile",
            "k_corrected", "k_corrected_source", "k_corrected_code", "k_corrected_via_parent", "h2_liab_k_corrected",
            "score_k_corrected", "ldsc_status_k_corrected", "tertile_k",
            "k_v3", "k_v3_source", "k_v3_code", "k_v3_via_parent", "h2_liab_v3", "score_v3", "ldsc_status_v3", "category_v3", "tertile_v3",
            "n_eff", "tertile_resid"]
    u2[[c for c in cols if c in u2.columns]].to_csv(os.path.join(pg.OUT, "k_corrected.csv"), index=False)
    pd.DataFrame(desc["area"]).to_csv(os.path.join(pg.OUT, "area.csv"), index=False)
    pd.DataFrame(desc["no_score"].get("status", [])).to_csv(os.path.join(pg.OUT, "no_score.csv"), index=False)
    n = numbers(e, primary, sens, desc, pg.CUTPOINTS,
                {**(extra or {}), "k_corrected": alt["k_corrected"], "k_v3": alt["k_v3"], "post_hoc": post}, pg.BUILD_ID, pg.COMMENT_ID)
    with open(os.path.join(pg.OUT, "numbers.json"), "w") as f:
        json.dump(jsonable(n), f, indent=1)
    for k, t in primary.items():
        print(k, t.get("rr"), t.get("p_one_sided"), t.get("p_holm"), t.get("reading"))
    for fam, tests in sens.items():
        print(fam, {k: t.get("reading") for k, t in tests.items()})
    print("post_hoc residual", {k: (t.get("rr"), t.get("p"), t.get("reading")) for k, t in post["residual_gwas_size"]["tests"].items()})
    for rule in ("k_corrected", "k_v3"):
        print(rule, {k: v for k, v in alt[rule].items() if k != "changes"}, "changed tertile", alt[rule]["changes"]["changed"])
    return n
