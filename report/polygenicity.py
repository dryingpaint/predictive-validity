"""Polygenicity and failure (issue #147): do targets fail more often in more polygenic diseases.

Registered by Melissa on 2026-11-19 (#147, the registration comment), with her dated decisions of 2026-11-23: diseases
without a heritability estimate form a descriptive group outside the tertiles (IC_...qDb0FA); infectious diseases are
out of the unit (IC_...qFfZeg); heritability A, our LDSC on the largest European GWAS with public summary statistics,
loci and heritability from the same GWAS; K from GBD with the Pan-UKB case fraction as fallback; four registered
sensitivities (issuecomment-7123250021). The definitions used, the unit counts, the build id and the tertile
cutpoints are fixed in a dated comment before any outcome is joined (report/audits/polygenicity_definitions.md); the
cutpoints are the constant CUTPOINTS below, committed with that comment. Her decision of 2026-11-24
(issuecomment-7149832720) amended the rest: zero loci and a heritability z below 4 are the no-score group; gene counts
read every gene of the Open Targets association file; the sensitivities are GWAS size, the Mendelian form and a
negative control; the share of score variance within disease area and a power simulation are posted with the tertiles.

Unit (unit): non-oncology, non-infectious diseases with a US-developed Phase 2 entry in 2008-2019, each disease one
observation. Scored diseases (an estimate: preclin.disease_polygenicity.ldsc_status ok) form the tertiles of the
score (loci per unit of liability-scale SNP heritability); the rest are the no-score group, reported, never tested.

Registered tests (registered, second half of this module, run only once CUTPOINTS is set): P1, more "target not
causal" stops per entry in the top tertile than the bottom (Phase 2 and 3 entries, COVARS_23); P2, lower Phase 2
advance (S4, COVARS); P3, a smaller S4 risk ratio of human genetic support in the top tertile (interaction, COVARS).
Entries with a resolved primary target; modified Poisson clustered by disease; one-sided p in the registered
direction, Holm across the three, as the #140 confirmation reads its tests. Sensitivities (amended 2026-11-24): GWAS
size (log10 effective N as a covariate) and a Mendelian form over all unit diseases (no Mendelian form in place of the
top tertile), each P1-P3 with Holm within; and the negative control, P1's model on stops unrelated to the disease's
biology, two-sided, outside any family. Descriptive, not registered: tertile by disease area, the no-score group,
entries without a target, and the checks named in the appendix.

Writes report/output/polygenicity/: unit.csv, membership.csv, then tests.csv, sensitivities.csv, tertiles.csv,
area.csv, no_score.csv, daly.csv and numbers.json.
"""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal

import numpy as np
import pandas as pd

from pipeline.stops import keys
from report import frame
from report.engaged_modes import engaged_modes
from report.evidence_analysis import traced_stops
from report.evidence_lines import build, us
from report.failure_modes import with_modes
from report.section3 import jsonable

OUT = os.path.join(frame.REPO, "report", "output", "polygenicity")
AUDITS = os.path.join(frame.REPO, "report", "audits")
AUDIT_TERTILES = os.path.join(AUDITS, "polygenicity_tertiles.csv")   # the registered membership, fixed by the gate
EXCLUDED_AREAS = ("oncology", "infectious_disease")
LEVELS = ("bottom", "middle", "top")
# Fixed before any outcome was joined (the dated comment on #147 named in polygenicity_definitions.md); None until then.
CUTPOINTS: tuple[float, float] | None = (164.37305314732993, 796.2935736638328)      # score: 33.3rd and 66.7th percentiles over scored unit diseases
BUILD_ID: str | None = "5945a7e4-1b7d-4f1c-9767-2c3424b76512"                       # preclin.dev_program_build.build_id the unit was counted on
COMMENT_ID: str | None = "7181532783"                     # the dated comment


def floats(t: pd.DataFrame) -> pd.DataFrame:
    """Numeric columns psycopg2 returned as decimal.Decimal become float64 (NULL as NaN); every other column stays."""
    out = t.copy()
    for c in out.columns:
        if out[c].dtype == object and any(isinstance(v, Decimal) for v in out[c].dropna().head(20)):
            out[c] = out[c].map(lambda v: float(v) if isinstance(v, Decimal) else (np.nan if v is None else v)).astype(float)
    return out


def profile() -> pd.DataFrame:
    """preclin.disease_polygenicity, one row per candidate disease; NUMERIC columns as float64."""
    return floats(frame.query("SELECT * FROM preclin.disease_polygenicity ORDER BY mondo_id"))


K_RULE_COLS = ("k", "k_source", "k_code", "k_via_parent", "h2_liab", "score", "ldsc_status", "category")


def k_rule(rule: str, rows: pd.DataFrame | None = None) -> pd.DataFrame:
    """One rule's rows of preclin.disease_polygenicity_k (migration 181; `pipeline.polygenicity k-rules`) as columns
    suffixed with the rule (k_v3, k_v3_source, k_v3_code, k_v3_via_parent, h2_liab_v3, score_v3, ldsc_status_v3,
    category_v3), to sit beside the profile's registered columns."""
    if rows is None:
        rows = floats(frame.query(f"SELECT mondo_id, {', '.join(K_RULE_COLS)} FROM preclin.disease_polygenicity_k "
                                  "WHERE rule = %s ORDER BY mondo_id", (rule,)))
    names = {"k": f"k_{rule}", "k_source": f"k_{rule}_source", "k_code": f"k_{rule}_code", "k_via_parent": f"k_{rule}_via_parent",
             "h2_liab": f"h2_liab_{rule}", "score": f"score_{rule}", "ldsc_status": f"ldsc_status_{rule}", "category": f"category_{rule}"}
    return rows[["mondo_id", *names]].rename(columns=names)


def unit(d: pd.DataFrame, prof: pd.DataFrame) -> pd.DataFrame:
    """One row per disease in the unit: its Phase 2 entries, the profile's status, `scored`; a disease the profile
    lacks is `not_profiled` (the pre-comment check fails on it)."""
    p2 = d[d.us_site & d.phase.eq(2) & d.mondo_id.notna() & ~d.bio_area.isin(EXCLUDED_AREAS)]
    u = p2.groupby("mondo_id").size().reset_index(name="entries")
    u = u.merge(prof.drop(columns=["entries"], errors="ignore"), on="mondo_id", how="left")
    u["ldsc_status"] = u.ldsc_status.fillna("not_profiled")
    u["scored"] = u.ldsc_status.eq("ok")
    return u.sort_values("mondo_id").reset_index(drop=True)


def cutpoints(score: pd.Series) -> tuple[float, float]:
    s = score.dropna()
    return float(np.percentile(s, 100 / 3)), float(np.percentile(s, 200 / 3))


def tertile(score: pd.Series, cuts: tuple[float, float]) -> pd.Series:
    """bottom, middle, top by the two cutpoints (a value on a cut goes down); none where the score is missing."""
    out = pd.Series("none", index=score.index, dtype=object)
    out[score <= cuts[0]] = "bottom"
    out[(score > cuts[0]) & (score <= cuts[1])] = "middle"
    out[score > cuts[1]] = "top"
    return out


def membership(u: pd.DataFrame, cuts: tuple[float, float] | None) -> pd.DataFrame:
    """The unit with its tertiles: the audit file and the comment's membership list."""
    m = u.copy()
    m["tertile"] = tertile(m.score, cuts) if cuts else "none"
    cols = ["mondo_id", "label", "bio_area", "entries", "ldsc_status", "gcst", "trait_level", "n_cases", "n_controls",
            "h2_obs", "h2_z", "k", "k_source", "k_code", "k_via_parent", "h2_liab", "loci", "score", "tertile",
            "mendelian_form"]
    return m[[c for c in cols if c in m.columns]]


def within_area_variance(u: pd.DataFrame) -> dict:
    """Melissa's first pre-join check: the share of the log10 score's variance that lies within disease area over
    the scored unit diseases (1 - between-area sum of squares / total). Small means the area adjustment leaves
    little to test."""
    s = u[u.scored.fillna(False).astype(bool) & u.log10_score.notna()]
    out = {"diseases": int(len(s)), "areas": int(s.bio_area.nunique()), "share": None}
    if len(s) < 2:
        return out
    total = float(((s.log10_score - s.log10_score.mean()) ** 2).sum())
    within = float((s.log10_score - s.groupby("bio_area").log10_score.transform("mean")).pow(2).sum())
    out["share"] = within / total if total > 0 else None
    return out


def pinned_unit(check: dict, build_id: str | None, membership: pd.DataFrame, audit: pd.DataFrame) -> None:
    """After the gate a report run sits on the registered unit: the programme build the comment named, no disease the
    profile lacks, and every disease in the tertile the committed membership file gives it; otherwise a loud error
    rather than a silently re-formed cohort."""
    if build_id and check.get("build_id") != build_id:
        raise RuntimeError(f"programme build {check.get('build_id')} is not the registered build {build_id}: the unit would re-form")
    if check.get("not_profiled"):
        raise RuntimeError(f"{len(check['not_profiled'])} unit diseases are not profiled: {check['not_profiled'][:5]}")
    now, was = membership.set_index("mondo_id").tertile, audit.set_index("mondo_id").tertile
    moved = [m for m in was.index.union(now.index) if now.get(m) != was.get(m)]
    if moved:
        raise RuntimeError(f"{len(moved)} diseases are not in their registered tertile ({moved[:5]}): the profile changed after the gate")


def evidence_line_build() -> dict:
    """The latest stored evidence-line build, the provenance of the genetic-support line P3 reads (g3)."""
    b = frame.query("SELECT build_id::text, built_at, code_commit FROM preclin.evidence_line_build ORDER BY built_at DESC LIMIT 1")
    return {"build_id": b.build_id.iloc[0], "built_at": str(b.built_at.iloc[0]), "code_commit": b.code_commit.iloc[0]}


def current_build() -> dict:
    b = frame.query("SELECT build_id::text, built_at, snapshot FROM preclin.dev_program_build ORDER BY built_at DESC LIMIT 1")
    return {"build_id": b.build_id.iloc[0], "built_at": str(b.built_at.iloc[0]), "snapshot": str(b.snapshot.iloc[0])}


def pre_comment_check(d: pd.DataFrame, u: pd.DataFrame) -> dict:
    """What the definitions comment needs and what must be clean before it: the build, the unit's counts, diseases
    not profiled, and engaged-without-benefit stops among the unit's Phase 2 and 3 entries with no target-history
    row. Reads no outcome by tertile."""
    scored = u[u.scored]
    out = {**current_build(), "diseases": int(len(u)), "entries": int(u.entries.sum()),
           "scored_diseases": int(len(scored)), "scored_entries": int(scored.entries.sum()),
           "not_profiled": sorted(u.mondo_id[u.ldsc_status.eq("not_profiled")]),
           "zero_loci_diseases": int(u.ldsc_status.eq("zero_loci").sum()),
           "k_via_parent_diseases": int(u.k_via_parent.fillna(False).astype(bool).sum()) if "k_via_parent" in u.columns else None,
           "within_area_variance": within_area_variance(u) if "log10_score" in u.columns else None,
           "evidence_line_build": evidence_line_build()}
    e = d[d.us_site & d.phase.between(2, 3) & d.mondo_id.isin(u.mondo_id)]
    e = with_modes(traced_stops(e))
    history = set(engaged_modes().key)
    k = pd.Series(keys(e), index=e.index)
    engaged = e[e.stop_no_benefit > 0]
    out["engaged_stops"] = int(len(engaged))
    out["engaged_stops_without_history"] = int((~k[engaged.index].isin(history)).sum())
    return out


WHO_FILE = os.path.join(frame.REPO, "analyses", "model-system-atlas", "lists", "who_ghe_2021_global_dalys.csv")
WHO_MAP = os.path.join(frame.REPO, "pipeline", "data", "who_ghe_cause_mondo.csv")


def who_map() -> pd.DataFrame:
    """The hand map of WHO causes to MONDO (code, cause, mondo_id, relation, note), extending burden.py's."""
    return pd.read_csv(WHO_MAP, dtype={"code": int, "mondo_id": str})


def leaves(who: pd.DataFrame) -> pd.DataFrame:
    """The causes with no children: the file lists each cause's children right after it, one level deeper."""
    depth = who.depth.tolist()
    keep = [i == len(depth) - 1 or depth[i + 1] <= depth[i] for i in range(len(depth))]
    return who[keep]


def daly_share(who: pd.DataFrame, m: pd.DataFrame, flags: pd.DataFrame) -> dict:
    """Shares of DALYs (all causes; non-communicable diseases) in leaf causes mapped to a disease with a Mendelian
    form, with a drugged large-effect gene, or either; and the largest flagged causes."""
    f = flags.set_index("mondo_id")
    out = {}
    cause_flags = {}
    for code, g in m[m.relation.isin(["exact", "broader"])].groupby("code"):
        ids = [i for i in g.mondo_id if i in f.index]
        cause_flags[code] = {"mendelian_form": bool(f.mendelian_form[ids].any()) if ids else False,
                             "drugged_large_effect": bool(f.drugged_large_effect[ids].any()) if ids else False}
    lf = leaves(who)
    for name, total in (("all", float(who.dalys_2021[who.code == 0].iloc[0])),
                        ("ncd", float(who.dalys_2021[who.cause.str.startswith("Noncommunicable")].sum()))):
        if name == "ncd":
            start = who.index[who.cause.str.startswith("Noncommunicable")]
            if not len(start):
                continue
            i = start[0]
            after = who.loc[i + 1:]
            stop = after.index[after.depth <= who.depth[i]]
            sub = who.loc[i + 1:(stop[0] - 1) if len(stop) else None]
            rows = lf[lf.code.isin(sub.code)]
        else:
            rows = lf
        shares = {}
        for flag in ("mendelian_form", "drugged_large_effect", "either"):
            hit = rows.code.map(lambda c: (cause_flags.get(c, {}).get("mendelian_form", False) or cause_flags.get(c, {}).get("drugged_large_effect", False))
                                if flag == "either" else cause_flags.get(c, {}).get(flag, False)).astype(bool)
            shares[flag] = float(rows.dalys_2021[hit].sum() / total) if total else None
        shares["total"] = total
        flagged = rows.code.map(lambda c: cause_flags.get(c, {}).get("mendelian_form", False)
                                or cause_flags.get(c, {}).get("drugged_large_effect", False)).astype(bool)
        shares["largest"] = rows[flagged].sort_values("dalys_2021", ascending=False).head(10)[["code", "cause", "dalys_2021"]] \
            .to_dict("records")
        out[name] = shares
    return out


def drugged_sets(td: pd.DataFrame, approved: pd.DataFrame) -> dict[str, set[str]]:
    """Per disease, the genes that are a primary target of a programme that entered Phase 2 or 3 there (the
    target-disease pairs) or of a programme approved for it; both frames carry ensembl_id and mondo_id."""
    drugged = td.groupby("mondo_id").ensembl_id.apply(set).to_dict()
    for r in approved.itertuples():
        drugged.setdefault(r.mondo_id, set()).add(r.ensembl_id)
    return drugged


def approved_targets() -> pd.DataFrame:
    """Primary human targets of programmes judged approved for their disease (the FDA approval judgement the
    phase cohorts use), as ensembl_id and mondo_id."""
    return frame.query("""SELECT DISTINCT t.ensembl_id, p.mondo_id
                          FROM preclin.dev_program p JOIN preclin.dev_program_approval ap USING (program_id)
                          JOIN preclin.moiety_target mt USING (moiety_id) JOIN public.targets t ON t.id = mt.target_id
                          WHERE ap.approved = 'yes' AND mt.is_primary AND p.mondo_id IS NOT NULL AND t.ensembl_id IS NOT NULL""")


def drugged_large_effect(prof: pd.DataFrame, drugged: dict[str, set[str]] | None = None) -> pd.DataFrame:
    """Per profiled disease: whether a gene with rare or Mendelian evidence for it (the same match as the profile's
    mendelian genes) is a primary target of a programme in the disease that entered Phase 2 or 3, or was approved on
    that target for the disease."""
    from pipeline.polygenicity import descendants_table, evidence_frame, members  # noqa: PLC0415
    from report.disease_match import Mondo, mondo_tables  # noqa: PLC0415
    from report.section3 import FAMILY  # noqa: PLC0415
    ev = evidence_frame()
    ev = ev[ev.datasource.map(FAMILY).isin(["burden", "mendelian"])]
    if drugged is None:
        drugged = drugged_sets(frame.query("SELECT ensembl_id, mondo_id FROM preclin.target_disease"), approved_targets())
    desc, mondo = descendants_table(mondo_tables()[0]), Mondo()
    rows = []
    for mondo_id in prof.mondo_id:
        mem = members(mondo_id, desc)
        close = {d for d in ev.mondo_id.unique() if d not in mem and mondo.matches(d, mondo_id)[1]}
        genes = set(ev.target_ensembl[ev.mondo_id.isin(mem | close)])
        rows.append({"mondo_id": mondo_id, "drugged_large_effect": bool(genes & drugged.get(mondo_id, set()))})
    return pd.DataFrame(rows)


def daly_flags(prof: pd.DataFrame) -> pd.DataFrame:
    """The two flags per profiled disease from the stored profile: the Mendelian form and the drugged large-effect gene
    (`pipeline.polygenicity drugged`, migration 172); an unfilled drugged column is a loud error, not a silent False."""
    if "drugged_large_effect" not in prof or prof.drugged_large_effect.isna().all():
        raise RuntimeError("preclin.disease_polygenicity.drugged_large_effect is not filled: apply migration 172 and run "
                           "`python -m pipeline.polygenicity drugged`")
    f = prof[["mondo_id", "mendelian_form", "drugged_large_effect"]].copy()
    f["mendelian_form"] = f.mendelian_form.map(lambda v: bool(v) if v is not None and v == v else False)
    f["drugged_large_effect"] = f.drugged_large_effect.map(lambda v: bool(v) if v is not None and v == v else False)
    return f


def daly(prof: pd.DataFrame) -> dict:
    who = pd.read_csv(WHO_FILE)
    flags = daly_flags(prof)
    s = daly_share(who, who_map(), flags)
    pd.DataFrame([{"denominator": k, **{kk: vv for kk, vv in v.items() if kk != "largest"}} for k, v in s.items()]) \
        .to_csv(os.path.join(OUT, "daly.csv"), index=False)
    return {"shares": s, "flags": {"diseases": int(len(flags)), "mendelian_form": int(flags.mendelian_form.sum()),
                                   "drugged_large_effect": int(flags.drugged_large_effect.sum())}}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    if BUILD_ID and current_build()["build_id"] != BUILD_ID:   # the unit was counted and registered on one build (review of 2026-11-27)
        raise frame.StandAside(f"the latest programme build is not the registered build {BUILD_ID[:8]}; the registered "
                               "outputs carry forward, and a recount needs that build")
    d = build()
    prof = profile().merge(k_rule("v3"), on="mondo_id", how="left")   # rule v3 beside the registered and corrected columns
    u = unit(d, prof)
    u.to_csv(os.path.join(OUT, "unit.csv"), index=False)
    m = membership(u, CUTPOINTS)
    m.to_csv(os.path.join(OUT, "membership.csv"), index=False)
    check = pre_comment_check(d, u)
    print(json.dumps(jsonable(check), indent=1))
    with open(os.path.join(OUT, "check.json"), "w") as f:
        json.dump(jsonable(check), f, indent=1)
    if "--power" in sys.argv:   # the second pre-join check, on the candidate cutpoints; slow, so only when asked
        from report.polygenicity_tests import frame_with_outcomes, power_simulation  # noqa: PLC0415
        reps = int(sys.argv[sys.argv.index("--power") + 1]) if len(sys.argv) > sys.argv.index("--power") + 1 else 200
        cuts = CUTPOINTS or cutpoints(u.score[u.scored])
        power = power_simulation(frame_with_outcomes(d, u, cuts), reps=reps)
        with open(os.path.join(OUT, "power.json"), "w") as f:
            json.dump(jsonable({"cutpoints": list(cuts), **power}), f, indent=1)
        print(json.dumps(jsonable(power["power"]), indent=1))
    if CUTPOINTS is None:
        print("CUTPOINTS not set: the tertiles are not fixed; no outcome is joined.")
        return
    pinned_unit(check, BUILD_ID, m, pd.read_csv(AUDIT_TERTILES, dtype={"mondo_id": str}))
    from report.polygenicity_tests import run_tests  # noqa: PLC0415  (the second half, after the dated comment)
    extra = {"daly": daly(prof), "check": check}
    if os.path.exists(os.path.join(OUT, "power.json")):   # the second pre-join check, run before the comment
        extra["power"] = json.load(open(os.path.join(OUT, "power.json")))
    run_tests(d, u, extra=extra)


if __name__ == "__main__":
    try:
        main()
    except frame.StandAside as e:
        raise SystemExit(f"polygenicity stands aside: {e}") from e
