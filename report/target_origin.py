"""What first proposed a target for a disease, and how often its programs stopped because the target was not causal:
the registered step 6 of issue #146, hypothesis O1.

    python -m report.target_origin

Cohort: the US-developed Phase 2 and 3 entries 2008-2019 of report.evidence_lines.build, with each entry's traced stop
split into failure modes as in report.failure_modes (with_modes). Phase 1 entries are left out: no Phase 1 stop has a
target-history row (preclin.stop_target_history), so none can stop as "target not causal".

Origin of an entry. An entry's pairs are its entity's primary target genes (pipeline.target_history.targets) crossed
with its program's disease, each a row of preclin.target_disease with its labelled origin
(preclin.target_disease_origin, basis labelled). An entry takes the one origin all its pairs share; otherwise it gets a
status that keeps it out of every origin group (entry_origin, in this order):
- pathogen: the entity acts on a pathogen (preclin.moiety.target_kind), so it has no human target and no pair;
- no_target: no human primary target (no single target, or unknown);
- validated_at_entry: a pair was already validated at entry (preclin.target_disease.validated_at_entry);
- no_pair: its program has no disease, or none of its gene-disease pairs is in preclin.target_disease;
- unlabelled: a pair has no labelled origin (it was first tested before 2008, or is not in the hub);
- mixed: its pairs carry different origins.
A pair's origin enters the test only as stored, which is a stated or pattern label the check supported (any other row
holds unclear, disputed or not_reached).

O1 (registered 2026-11-19): the adjusted risk ratio of a "target not causal" stop (report.engaged_modes) per entry for
entries whose origin is an observational biomarker association or a diseased-tissue change against entries whose origin
is human genetics, each of the two also alone; modified Poisson clustered by primary-target set
(report.section3.estimate), adjusted for disease area, modality, entry period, novelty and phase (COVARS). Sensitivities
(contrasts): unclear entries added to each compared group in turn, and again with the disputed and not_reached entries
(UNSETTLED), which the registration's unclear held before the check stored them apart; Phase 2 entries only; labels from sources of any
date, which also admits the labels the check failed only because a source was dated in or after the pair's first
entry year (any_date_labels). Descriptive: for every origin and status, the entries' failure modes and approval; for
every labelled pair, origin and discovery route by disease area and entry period.

Descriptive, not registered (descriptive_contrasts): the O1 contrasts with two other outcomes, a not-causal stop by the
stop's own verdict (STRICT) and a stop whose target never worked in this disease (NEVER_WORKED). An origin of an earlier
drug for another disease (CIRCULAR_ORIGINS) is the target's record the not-causal rule reads; it is reported alone.

Writes report/output/target_origin/: by_origin.csv, tests.csv, origin_by_area.csv, origin_by_period.csv,
route_by_area.csv, route_by_period.csv and numbers.json.
"""
from __future__ import annotations

import json
import os

import pandas as pd
from statsmodels.stats.proportion import proportion_confint

from pipeline.stops import keys
from pipeline.target_history import targets
from pipeline.target_origin import current_origin
from report import frame
from report.engaged_modes import ENGAGED_MODES, engaged_modes
from report.evidence_analysis import COVARS_23, traced_stops
from report.evidence_lines import build, us
from report.failure_modes import with_modes
from report.section3 import ERA_BINS, ERA_LABELS, estimate, jsonable

OUT = os.path.join(frame.REPO, "report", "output", "target_origin")
COVARS = tuple(c for c in COVARS_23 if c != "precedent")  # the registered set, plus phase for the pooled phases
OUTCOME = "mode_not_causal"
# Descriptive outcomes beside the registered one (history_outcomes), each among the engaged-without-benefit stops:
# not causal by the verdict read from the stop's own sources (target_not_causal), not from the target's fate alone;
# and the target never worked in this disease, by its fate whatever the mode.
STRICT = "not_causal_by_verdict"
NEVER_WORKED = "target_never_worked_here"
NEVER_WORKED_FATES = ("worked_elsewhere_only", "worked_related", "never_worked_single", "never_worked_tried_again")
# An origin that is the target's record the not_causal rule reads: a drug on the target approved for another disease
# is the worked_elsewhere_only fate before entry, so its stops are not causal largely by construction. It is reported
# on its own and left out of any comparison against the other origins.
CIRCULAR_ORIGINS = ("earlier_drug_other_disease",)
MODES = [f"mode_{m}" for m in ENGAGED_MODES]
# Statuses that keep an entry out of every origin group (entry_origin), in the order they are assigned
STATUSES = ("pathogen", "no_target", "validated_at_entry", "no_pair", "unlabelled", "mixed")
# The origins a pair carries when no supported label settles it (they enter the test only in its sensitivities)
UNSETTLED = ("unclear", "disputed", "not_reached")
EXPOSED = ("observational_biomarker", "diseased_tissue")
REFERENCE = ("human_genetics",)
# Registered contrasts: name -> (exposed origins, reference origins)
CONTRASTS = {"o1": (EXPOSED, REFERENCE),
             "observational_biomarker": (("observational_biomarker",), REFERENCE),
             "diseased_tissue": (("diseased_tissue",), REFERENCE)}

ORIGINS_SQL = """SELECT h.ensembl_id, h.mondo_id, h.first_entry, h.validated_at_entry, o.origin, o.grade,
                        o.check_outcome, o.discovery_route, a.bio_area
                 FROM preclin.target_disease h
                 LEFT JOIN preclin.target_disease_origin o
                   ON (o.ensembl_id, o.mondo_id) = (h.ensembl_id, h.mondo_id) AND o.basis = 'labelled'
                 LEFT JOIN preclin.mondo_bio_area a ON a.mondo_id = h.mondo_id"""
# Labels the check failed on the source's year alone: the label as read, from its decision
ANY_DATE_SQL = """SELECT o.ensembl_id, o.mondo_id, d.parsed_output->>'origin' AS origin,
                         d.parsed_output->>'grade' AS grade
                  FROM preclin.target_disease_origin o JOIN pv_evidence.llm_decision d USING (llm_decision_id)
                  WHERE o.basis = 'labelled' AND o.check_fields->>'year' = 'no'
                    AND o.check_fields->>'quote' = 'yes' AND o.check_fields->>'category' = 'yes'"""


def any_date_labels(pairs: pd.DataFrame, year_only: pd.DataFrame) -> pd.DataFrame:
    """pairs with the origin of each label the check failed only on the year field (year_only: ensembl_id, mondo_id,
    origin and grade as read) put back, when the label as read is graded stated or pattern."""
    graded = year_only[year_only.grade.isin(("stated", "pattern"))]
    read = {(e, m): current_origin(o) for e, m, o in zip(graded.ensembl_id, graded.mondo_id, graded.origin)}
    keys = list(zip(pairs.ensembl_id, pairs.mondo_id))
    return pairs.assign(origin=[read.get(k, o) for k, o in zip(keys, pairs.origin)])


def entry_origin(d: pd.DataFrame, genes: dict, pairs: pd.DataFrame) -> pd.DataFrame:
    """d (moiety_id, mondo_id, target_kind) with `pairs`, the keys "ensembl_id|mondo_id" of its gene-disease pairs in
    the hub, and `origin`: the one labelled origin its pairs share, or the first status of STATUSES that applies."""
    hub = {(e, m): (v, o) for e, m, v, o in zip(pairs.ensembl_id, pairs.mondo_id, pairs.validated_at_entry,
                                                 pairs.origin)}
    keys, origin = [], []
    for kind, moiety, mondo in zip(d.target_kind, d.moiety_id, d.mondo_id):
        gs = genes.get(moiety, []) if isinstance(mondo, str) else []
        found = [((g, mondo), hub[(g, mondo)]) for g in gs if (g, mondo) in hub]
        keys.append(tuple(f"{g}|{m}" for (g, m), _ in found))
        labels = {o for _, (_, o) in found}
        origin.append("pathogen" if kind == "pathogen" else
                      "no_target" if not genes.get(moiety) else
                      "validated_at_entry" if any(v for _, (v, _) in found) else
                      "no_pair" if not found else
                      "unlabelled" if len(found) < len(gs) or any(pd.isna(o) for o in labels) else
                      "mixed" if len(labels) > 1 else next(iter(labels)))
    return d.assign(pairs=keys, origin=origin)


def history_outcomes(d: pd.DataFrame, key: pd.Series, h: pd.DataFrame) -> pd.DataFrame:
    """d with STRICT and NEVER_WORKED: 0/1 per entry, from the target-history row (h: key, target_fate, verdict,
    mode) of its traced stop, counted only where the stop engaged the target without benefit (stop_no_benefit)."""
    by_key = h.set_index("key")
    stopped = d.stop_no_benefit > 0
    strict = key.map(by_key["mode"].eq("not_causal") & by_key.verdict.eq("target_not_causal"))
    never = key.map(by_key.target_fate.isin(NEVER_WORKED_FATES))
    return d.assign(**{STRICT: (stopped & strict.fillna(False).astype(bool)).astype(float),
                       NEVER_WORKED: (stopped & never.fillna(False).astype(bool)).astype(float)})


def group(d: pd.DataFrame, outcome: str = OUTCOME) -> dict:
    """Entries, distinct pairs, distinct primary-target sets and events of a group of entries."""
    return {"entries": int(len(d)), "pairs": len({k for ks in d.pairs for k in ks}),
            "targets": int(d.target.nunique()), "events": int(d[outcome].sum()),
            "rate": float(d[outcome].mean()) if len(d) else None}


def contrast(d: pd.DataFrame, exposed: tuple[str, ...], reference: tuple[str, ...], outcome: str = OUTCOME) -> dict:
    """The adjusted risk ratio of `outcome` for entries whose origin is in `exposed` against those in `reference`
    (report.section3.estimate: nothing when too few exposed targets or an arm has no event), with each group's size."""
    x = d[d.origin.isin(exposed + reference)]
    x = x.assign(x=x.origin.isin(exposed).astype(float))
    r = estimate(x, outcome, "x", COVARS)
    return {**{k: r.get(k) for k in ("rr", "lo", "hi", "p")}, "outcome": outcome,
            "exposed": {"origins": list(exposed), **group(x[x.x > 0], outcome)},
            "reference": {"origins": list(reference), **group(x[x.x <= 0], outcome)}}


def contrasts(d: pd.DataFrame, d_any_date: pd.DataFrame) -> dict:
    """Every registered contrast in the primary cohort and each sensitivity."""
    out = {"primary": {k: contrast(d, e, r) for k, (e, r) in CONTRASTS.items()}}
    for name, added in (("unclear", ("unclear",)), ("unsettled", UNSETTLED)):
        out[f"{name}_as_exposed"] = {k: contrast(d, e + added, r) for k, (e, r) in CONTRASTS.items()}
        out[f"{name}_as_reference"] = {k: contrast(d, e, r + added) for k, (e, r) in CONTRASTS.items()}
    out["phase2"] = {k: contrast(d[d.phase.eq(2)], e, r) for k, (e, r) in CONTRASTS.items()}
    out["any_date"] = {k: contrast(d_any_date, e, r) for k, (e, r) in CONTRASTS.items()}
    return out


def descriptive_contrasts(d: pd.DataFrame) -> dict:
    """The O1 contrasts with each descriptive outcome in place of the registered one; not registered."""
    return {name: {k: contrast(d, e, r, name) for k, (e, r) in CONTRASTS.items()} for name in (STRICT, NEVER_WORKED)}


def circular(d: pd.DataFrame, key: pd.Series, h: pd.DataFrame) -> dict:
    """For each CIRCULAR_ORIGINS origin: its entries, its OUTCOME events and how many of them the target's fate
    alone made not causal (worked_elsewhere_only), split by whether the entry has one primary target."""
    fate = key.map(h.set_index("key").target_fate)
    out = {}
    for origin in CIRCULAR_ORIGINS:
        m = d.origin.eq(origin)
        single = m & d.pairs.map(len).eq(1)
        hit = d[OUTCOME] > 0
        out[origin] = {"entries": int(m.sum()), "events": int((m & hit).sum()),
                       "events_by_fate_worked_elsewhere_only": int((m & hit & fate.eq("worked_elsewhere_only")).sum()),
                       "single_target_stops_engaged": int((single & (d.stop_no_benefit > 0)).sum()),
                       "single_target_events": int((single & hit).sum()),
                       "single_target_events_by_fate_worked_elsewhere_only":
                           int((single & hit & fate.eq("worked_elsewhere_only")).sum())}
    return out


def contrasts_table(t: dict) -> pd.DataFrame:
    return pd.DataFrame([{"analysis": a, "contrast": c, **{k: r[k] for k in ("outcome", "rr", "lo", "hi", "p")},
                          **{f"{side}_{k}": r[side][k] for side in ("exposed", "reference")
                             for k in ("entries", "pairs", "targets", "events", "rate")}}
                         for a, cs in t.items() for c, r in cs.items()])


def by_origin(d: pd.DataFrame) -> pd.DataFrame:
    """Per origin or status: entries, pairs, targets, the share stopping in each failure mode (with the Wilson 95%
    interval of OUTCOME's), the share stopping engaged without benefit, and the share whose program reached approval."""
    rows = []
    for origin, g in d.groupby("origin"):  # each origin alone: none is pooled with the others
        k = int(g[OUTCOME].sum())
        lo, hi = proportion_confint(k, len(g), method="wilson")
        rows.append({"origin": origin, **{c: v for c, v in group(g).items() if c != "rate"},
                     **{c: float(g[c].mean()) for c in MODES}, "not_causal_lo": lo, "not_causal_hi": hi,
                     "stop_no_benefit": float(g.stop_no_benefit.mean()),
                     **{c: float(g[c].mean()) for c in (STRICT, NEVER_WORKED)},
                     "circular": origin in CIRCULAR_ORIGINS,
                     "approved": float(g.approval_date.notna().mean())})
    return pd.DataFrame(rows).sort_values("entries", ascending=False).reset_index(drop=True)


def pair_frame(pairs: pd.DataFrame) -> pd.DataFrame:
    """The labelled pairs with origin (validated_at_entry in place of the origin where the pair was), discovery route,
    disease area and entry period."""
    p = pairs[pairs.grade.notna()]
    return p.assign(origin=p.origin.where(~p.validated_at_entry.astype(bool), "validated_at_entry"),
                    bio_area=p.bio_area.fillna("unmapped"),
                    period=pd.cut(pd.to_datetime(p.first_entry).dt.year, ERA_BINS, labels=ERA_LABELS).astype(str))


def shares(p: pd.DataFrame, by: str, of: str) -> pd.DataFrame:
    """Pairs of each value of `of` within each value of `by`, as counts and shares of the `by` group."""
    c = p.groupby([by, of]).size().rename("pairs").reset_index()
    return c.assign(share=c.pairs / c.groupby(by).pairs.transform("sum"))


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    d = us(build())
    d = d.assign(target=d.target.fillna("entity " + d.moiety_id.astype(str)))
    d = with_modes(traced_stops(d[d.phase.between(2, 3)]))
    kind = frame.query("SELECT moiety_id, target_kind FROM preclin.moiety")
    d = d.merge(kind, on="moiety_id", how="left")
    t = targets()[["moiety_id", "ens"]].drop_duplicates()
    genes = t.groupby("moiety_id").ens.apply(lambda s: sorted(set(s))).to_dict()
    pairs = frame.query(ORIGINS_SQL)
    year_only = frame.query(ANY_DATE_SQL)
    h = engaged_modes()
    key = pd.Series(keys(d), index=d.index)
    d = history_outcomes(d, key, h)
    e = entry_origin(d, genes, pairs)
    e_any = entry_origin(d, genes, any_date_labels(pairs, year_only))
    t = contrasts(e, e_any)
    desc = descriptive_contrasts(e)
    contrasts_table({**t, **{f"descriptive_{k}": v for k, v in desc.items()}}).to_csv(
        os.path.join(OUT, "tests.csv"), index=False)
    table = by_origin(e)
    table.to_csv(os.path.join(OUT, "by_origin.csv"), index=False)
    p = pair_frame(pairs)
    for by in ("bio_area", "period"):
        shares(p, by, "origin").to_csv(os.path.join(OUT, f"origin_by_{by.replace('bio_', '')}.csv"), index=False)
        shares(p, by, "discovery_route").to_csv(os.path.join(OUT, f"route_by_{by.replace('bio_', '')}.csv"),
                                                index=False)
    multi = e[e.pairs.map(len) > 1]
    n = {"cohort": {"entries": int(len(e)), "phase2": int(e.phase.eq(2).sum()), "phase3": int(e.phase.eq(3).sum()),
                    "events": int(e[OUTCOME].sum()), "events_phase2": int(e.loc[e.phase.eq(2), OUTCOME].sum())},
         "status": {s: int(e.origin.eq(s).sum()) for s in STATUSES},
         "status_events": {s: int(e.loc[e.origin.eq(s), OUTCOME].sum()) for s in STATUSES},
         "multi_target": {"entries": int(len(multi)), "single_origin": int((~multi.origin.isin(STATUSES)).sum()),
                          "mixed": int(multi.origin.eq("mixed").sum()),
                          "unlabelled": int(multi.origin.eq("unlabelled").sum())},
         "infectious_host_target": int((e.bio_area.eq("infectious_disease") & ~e.origin.isin(STATUSES)).sum()),
         "any_date": {"labels_restored": int(year_only.grade.isin(("stated", "pattern")).sum()),
                      "entries_moved": int((e.origin != e_any.origin).sum())},
         "pairs": {"labelled": int(len(p)), "validated_at_entry": int(p.origin.eq("validated_at_entry").sum()),
                   "origin": p.origin.value_counts().to_dict(),
                   "discovery_route": p.discovery_route.value_counts().to_dict()},
         "covariates": list(COVARS), "outcome": OUTCOME,
         "tests": t,
         "descriptive_tests": {"registered": False,
                               "outcomes": {STRICT: "the stop's own verdict reads the target as not causal "
                                                    "(target_not_causal), not its fate alone",
                                            NEVER_WORKED: "the target never worked in this disease (fate "
                                                          + ", ".join(NEVER_WORKED_FATES) + ")"},
                               "events": {c: int(e[c].sum()) for c in (STRICT, NEVER_WORKED)}, **desc},
         "circular_origins": {"origins": list(CIRCULAR_ORIGINS),
                              "note": "a drug on the target approved for another disease is the worked_elsewhere_only "
                                      "fate the not_causal rule reads; reported alone, in no comparison with the other "
                                      "origins", **circular(e, key, h)},
         "by_origin": {r["origin"]: {k: v for k, v in r.items() if k != "origin"} for r in table.to_dict("records")}}
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(jsonable(n), f, indent=1)
    print(json.dumps(jsonable({k: {c: {f: r.get(f) for f in ("rr", "lo", "hi")} for c, r in v.items()}
                               for k, v in t.items()})), flush=True)


if __name__ == "__main__":
    main()
