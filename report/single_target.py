"""Which diseases the target-based drugging paradigm solves (#197): pathways tried and approved per disease, the
shortlists confirmed by #198's inclusion rule (#193), and each confirmed disease's two labels from the published
estimates (#195).

    python -m report.single_target

Pathways tried: the pathways (preclin.mechanism_pathway, kind specific) of every novel Phase 2 entry of 2008-2019 that
counts toward a mechanism in its atlas disease (preclin.atlas_member, excluded null). A tried pathway is approved in
the disease when an FDA-labelled entity acting through it is indicated for the disease (preclin.label_indication); the
labels are read only for the shortlisted diseases, so success is reported for those alone.

Pathways approved: every pathway of an entity whose current FDA label is indicated for the disease, any approval
year. An entity with no resolvable target counts toward the disease's labelled entities but no pathway, and the share
is reported. A shortlisted disease stays only with at least MIN_APPROVED_PATHWAYS approved pathways.

Labels (rules in pipeline.single_target, registered in #198), computed here and not stored. Subgroup estimates are left
out, since #198 reads a network meta-analysis, pooled trials or a whole trial; a stack position held by a subgroup
estimate takes the same pathway's whole-trial estimate instead (whole_trial). One drug's effect is the
placebo-adjusted share of a one-drug response estimate in naive patients (percentage points / 100) or 1 - HR of a
one-drug events estimate; the stack's is the best multi-drug regimen's share in naive patients or stacked_rrr() of the
events stack (preclin.mechanism_response). how_solved() is read at SOLVED_AT and SOLVED_SENSITIVITY. For a disease one
drug does not solve at SOLVED_AT, why_not_one_drug() takes the retained effect of each crossover comparison (prior
failure share / naive share, naive share above zero) and combination_beats_single() over the disease's
preclin.combination_trial rows. Each risk factor -> outcome pair is read across from the pair estimates.

Sensitivity, not part of the registered rule: how_solved at SOLVED_AT using only estimates whose drugs all have an FDA
approval (an entity of preclin.fda_application_moiety, matched by name or alias).

Writes report/output/single_target/: shortlist.csv, tried_by_area.csv, labels.csv, crossover.csv, pairs.csv,
estimates.csv and numbers.json.
"""
from __future__ import annotations

import json
import os

import pandas as pd

from pipeline.single_target import (AREAS_APART, CONFIRMED, EVENT_SHORTLIST, EVENTS_CONFIRMED, MIN_APPROVED_PATHWAYS,
                                    PAIRS, SHORTLIST, SOLVED_AT, SOLVED_SENSITIVITY, combination_beats_single,
                                    how_solved, mechanism_keys, stacked_rrr, why_not_one_drug)
from report import frame

OUT = os.path.join(frame.REPO, "report", "output", "single_target")

TRIED_SQL = """SELECT a.mondo_id, i.label, i.area, a.entity_id, unnest(mp.pathways) AS pathway
               FROM preclin.atlas_member a JOIN preclin.atlas_indication i USING (mondo_id)
               JOIN preclin.mechanism_pathway mp ON mp.mechanism_key = a.mechanism_key
               WHERE a.excluded IS NULL AND mp.kind = 'specific'"""
LABELLED_SQL = """SELECT DISTINCT li.mondo_id, m.moiety_id
                  FROM preclin.label_indication li JOIN preclin.fda_label l USING (set_id)
                  JOIN preclin.moiety m ON m.unii = ANY(l.unii)"""
PATHWAYS_SQL = "SELECT mechanism_key, kind, pathways FROM preclin.mechanism_pathway"
RESPONSES_SQL = """SELECT mondo_id, question, risk_factor_mondo_id, regimen, pathways, one_drug, endpoint, measure,
                          population, failed_pathway, background_pathways, stack_position, pair_key, estimate, ci_low,
                          ci_high, trial_weeks, per_unit, source_kind, source_name, pmid, drugs, subgroup
                   FROM preclin.mechanism_response ORDER BY mondo_id, question, response_id"""
APPROVED_NAMES_SQL = """SELECT DISTINCT lower(n) AS name FROM preclin.moiety m, unnest(m.name || coalesce(m.aliases, '{}')) n
                        WHERE EXISTS (SELECT 1 FROM preclin.fda_application_moiety a WHERE a.moiety_id = m.moiety_id)"""
SOURCE_RANK = {"nma": 0, "pooled_trials": 1, "trial": 2}
COMBOS_SQL = "SELECT mondo_id, relation, result, stopped_for_safety FROM preclin.combination_trial"
THRESHOLDS = (SOLVED_AT, *SOLVED_SENSITIVITY)


def approved_pathways(labelled: pd.DataFrame, keys: dict[int, tuple[str, str, str]],
                      pathways: dict[str, tuple[str, list[str]]]) -> pd.DataFrame:
    """One row per disease and labelled entity: its pathways (empty when its target is unresolved or not specific)."""
    rows = []
    for mondo_id, moiety_id in labelled.itertuples(index=False):
        kind, ps = pathways.get(keys.get(moiety_id, ("",))[0], ("unresolved", []))
        rows.append({"mondo_id": mondo_id, "moiety_id": moiety_id, "kind": kind, "pathways": ps})
    return pd.DataFrame(rows, columns=["mondo_id", "moiety_id", "kind", "pathways"])


def shortlist_table(tried: pd.DataFrame, approved: pd.DataFrame) -> pd.DataFrame:
    """Per shortlisted disease: pathways tried in 2008-2019 and how many reached approval, approved pathways of any
    year, labelled entities without a pathway, and whether the disease stays (MIN_APPROVED_PATHWAYS)."""
    out = []
    for mondo_id, e in {**SHORTLIST, **EVENT_SHORTLIST}.items():
        a = approved[approved.mondo_id == mondo_id]
        ok = sorted({p for ps in a.pathways for p in ps})
        t = sorted(set(tried.loc[tried.mondo_id == mondo_id, "pathway"]))
        out.append({"mondo_id": mondo_id, "disease": e.disease,
                    "endpoint": "event" if mondo_id in EVENT_SHORTLIST else "responder",
                    "tried_pathways": len(t), "tried_approved": len(set(t) & set(ok)),
                    "approved_pathways": len(ok), "labelled_entities": len(a),
                    "labelled_without_pathway": int((a.kind != "specific").sum()),
                    "stays": len(ok) >= MIN_APPROVED_PATHWAYS, "approved": "; ".join(ok)})
    return pd.DataFrame(out)


def tried_by_area(tried: pd.DataFrame) -> pd.DataFrame:
    """Per disease area: diseases, and the median and range of distinct pathways tried per disease in 2008-2019, with
    AREAS_APART flagged."""
    per = tried.groupby(["area", "mondo_id"]).pathway.nunique().rename("pathways").reset_index()
    g = per.groupby("area").pathways
    t = pd.DataFrame({"diseases": g.size(), "median_pathways": g.median(), "max_pathways": g.max()}).reset_index()
    t["reported_apart"] = t.area.isin(AREAS_APART)
    return t.sort_values(["reported_apart", "diseases"], ascending=[True, False])


def effect(measure: str, estimate: float) -> float:
    """An estimate on the labels' common scale: a share in percentage points as a fraction, a hazard ratio as 1 - HR."""
    return estimate / 100 if measure == "share" else 1 - estimate


def whole_trial(rows: pd.DataFrame) -> pd.DataFrame:
    """A disease's estimates without subgroup estimates. A stack position held by a subgroup estimate takes the
    whole-trial estimate of the same pathways instead: the preferred source kind (network meta-analysis, pooled trials,
    trial), then the longest trial; the position is dropped when there is none."""
    whole = rows[~rows.subgroup]
    out = [whole]
    for _, r in rows[rows.subgroup & rows.stack_position.notna()].iterrows():
        same = whole[whole.question.eq(r.question) & whole.stack_position.isna()
                     & whole.pathways.map(lambda ps: sorted(ps) == sorted(r.pathways)).astype(bool)]
        if len(same):
            best = same.assign(rank=same.source_kind.map(SOURCE_RANK), weeks=-same.trial_weeks.fillna(0)) \
                       .sort_values(["rank", "weeks"]).iloc[0]
            out.append(best.drop(["rank", "weeks"]).to_frame().T.assign(stack_position=r.stack_position))
    return pd.concat(out).astype({"one_drug": bool, "estimate": float})


def one_drug_effects(rows: pd.DataFrame) -> pd.DataFrame:
    """A disease's one-drug estimates that count toward how_solved, with their effect, largest first: response rows in
    naive patients and every events row (each against placebo, on whatever background)."""
    r = rows[rows.one_drug & ((rows.question.eq("response") & rows.population.eq("naive"))
                              | rows.question.eq("events"))].copy()
    r["effect"] = [effect(m, e) for m, e in zip(r.measure, r.estimate)]
    return r.sort_values("effect", ascending=False)


def stack_effect(rows: pd.DataFrame) -> tuple[float | None, str]:
    """The best multi-drug regimen's effect and its description: for events, stacked_rrr() of the stack's hazard
    ratios in position order; otherwise the largest share of a multi-drug response regimen in naive patients."""
    chain = rows[rows.question.eq("events") & rows.stack_position.notna()].sort_values("stack_position")
    if len(chain):
        return stacked_rrr(list(chain.estimate)), " + ".join(chain.regimen)
    multi = rows[rows.question.eq("response") & rows.population.eq("naive") & ~rows.one_drug]
    if multi.empty:
        return None, ""
    best = multi.loc[multi.estimate.idxmax()]
    return best.estimate / 100, best.regimen


def crossover_pairs(rows: pd.DataFrame) -> pd.DataFrame:
    """One row per crossover comparison: the pathway failed, the next regimen, its prior-failure and naive shares, and
    the retained effect (prior / naive; null when the naive share is not above zero)."""
    out = []
    for key, g in rows[rows.question.eq("crossover")].groupby("pair_key"):
        prior = g[g.population.eq("prior_failure")]
        naive = g[g.population.eq("naive")]
        if prior.empty or naive.empty:
            continue
        p, n = prior.iloc[0], naive.iloc[0]
        out.append({"pair_key": key, "failed_pathway": p.failed_pathway, "regimen": p.regimen,
                    "pathways": "; ".join(p.pathways), "endpoint": p.endpoint, "prior_failure": p.estimate,
                    "naive": n.estimate, "retained": p.estimate / n.estimate if n.estimate > 0 else None,
                    "source": f"{p.source_name} / {n.source_name}"})
    return pd.DataFrame(out, columns=["pair_key", "failed_pathway", "regimen", "pathways", "endpoint",
                                      "prior_failure", "naive", "retained", "source"])


def disease_labels(rows: pd.DataFrame, combos: list[dict]) -> dict:
    """Both labels of one disease from its estimates and its combination trials: how solved at each threshold, the
    best one drug and the pathways it spans, the stack, and why one drug is not enough where it is not at SOLVED_AT."""
    rows = whole_trial(rows)
    ones = one_drug_effects(rows)
    stack, stack_regimen = stack_effect(rows)
    best = ones.iloc[0] if len(ones) else None
    labels = {t: how_solved(list(ones.effect), stack, t) for t in THRESHOLDS}
    retained = [r for r in crossover_pairs(rows).retained if r is not None and not pd.isna(r)]
    beats = combination_beats_single(combos)
    solved_alone = labels[SOLVED_AT] == "solved_by_one_drug"
    return {**{f"how_solved_{round(t * 100)}": labels[t] for t in THRESHOLDS},
            "best_one_drug": best.regimen if best is not None else None,
            "best_one_drug_effect": round(float(best.effect), 3) if best is not None else None,
            "best_one_drug_pathways": len(best.pathways) if best is not None else None,
            "stack": stack_regimen or None, "stack_effect": round(stack, 3) if stack is not None else None,
            "crossover_pairs": len(retained),
            "median_retained": round(float(pd.Series(retained).median()), 2) if retained else None,
            "combination_beats_single": beats,
            "why_not_one_drug": None if solved_alone else why_not_one_drug(retained, beats)}


def fda_approved(drugs: list[str], approved: set[str]) -> bool:
    """Whether every drug of an estimate has an FDA approval (approved: lower-case names and aliases of approved
    entities)."""
    return all(d.strip().lower() in approved for d in drugs)


def label_table(responses: pd.DataFrame, combos: pd.DataFrame, approved: set[str]) -> pd.DataFrame:
    """labels.csv: disease_labels() for every confirmed disease, and the sensitivity label at SOLVED_AT from estimates
    whose drugs all have an FDA approval."""
    out = []
    for mondo_id, e in {**CONFIRMED, **EVENTS_CONFIRMED}.items():
        rows = responses[responses.mondo_id.eq(mondo_id) & responses.question.ne("pair")]
        trials = combos[combos.mondo_id.eq(mondo_id)].to_dict("records")
        fda = disease_labels(rows[rows.drugs.map(lambda d: fda_approved(d, approved)).astype(bool)], trials)
        out.append({"mondo_id": mondo_id, "disease": e.disease,
                    "endpoint": "event" if mondo_id in EVENTS_CONFIRMED else "responder",
                    **disease_labels(rows, trials),
                    "how_solved_50_fda_approved_only": fda["how_solved_50"],
                    "best_one_drug_fda_approved_only": fda["best_one_drug"]})
    return pd.DataFrame(out)


def pair_table(responses: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    """pairs.csv: per risk factor -> outcome pair, the risk factor's label and best one drug, the outcome-event effect
    of the drug read across (with trial length and the risk-factor change it achieved), the outcome's own label, and
    the Mendelian randomisation estimates of lifelong lowering."""
    by = labels.set_index("mondo_id")
    out = []
    for risk, outcome in PAIRS:
        p = responses[responses.question.eq("pair") & responses.mondo_id.eq(outcome)
                      & responses.risk_factor_mondo_id.eq(risk)]
        trial = p[p.population.ne("lifelong_genetic") & ~p.subgroup]
        mr = p[p.population.eq("lifelong_genetic")]
        t = trial.iloc[0] if len(trial) else None
        out.append({"risk_factor": by.loc[risk, "disease"], "outcome": by.loc[outcome, "disease"],
                    "risk_factor_label": by.loc[risk, "how_solved_50"],
                    "risk_factor_best": by.loc[risk, "best_one_drug"],
                    "risk_factor_effect": by.loc[risk, "best_one_drug_effect"],
                    "outcome_drug": t.regimen if t is not None else None,
                    "outcome_hr": t.estimate if t is not None else None,
                    "outcome_risk_reduction": round(1 - t.estimate, 3) if t is not None else None,
                    "trial_weeks": t.trial_weeks if t is not None else None,
                    "risk_factor_change": t.per_unit if t is not None else None,
                    "outcome_label": by.loc[outcome, "how_solved_50"],
                    "mendelian_randomisation": "; ".join(
                        f"{m.measure} {m.estimate:g} {m.per_unit or ''} ({m.source_name})".replace("  ", " ")
                        for m in mr.itertuples()) or None})
    return pd.DataFrame(out)


def main() -> None:
    tried = frame.query(TRIED_SQL)
    labelled = frame.query(LABELLED_SQL)
    with frame.connection().cursor() as cur:
        keys = mechanism_keys(cur)
    pathways = {k: (kind, ps) for k, kind, ps in frame.query(PATHWAYS_SQL).itertuples(index=False)}
    approved = approved_pathways(labelled, keys, pathways)
    short = shortlist_table(tried, approved)
    area = tried_by_area(tried)
    stays = set(short.loc[short.stays, "mondo_id"])
    if stays != set(CONFIRMED) | set(EVENTS_CONFIRMED):
        raise SystemExit(f"the inclusion rule now keeps {sorted(stays)}, not pipeline.single_target's confirmed list")
    responses = frame.query(RESPONSES_SQL)
    labels = label_table(responses, frame.query(COMBOS_SQL), set(frame.query(APPROVED_NAMES_SQL).name))
    pairs = pair_table(responses, labels)
    crossover = pd.concat([crossover_pairs(responses[responses.mondo_id.eq(m) & ~responses.subgroup]).assign(mondo_id=m)
                           for m in CONFIRMED])
    os.makedirs(OUT, exist_ok=True)
    short.to_csv(os.path.join(OUT, "shortlist.csv"), index=False)
    area.to_csv(os.path.join(OUT, "tried_by_area.csv"), index=False)
    labels.to_csv(os.path.join(OUT, "labels.csv"), index=False)
    pairs.to_csv(os.path.join(OUT, "pairs.csv"), index=False)
    crossover.to_csv(os.path.join(OUT, "crossover.csv"), index=False)
    responses.to_csv(os.path.join(OUT, "estimates.csv"), index=False)
    numbers = {"shortlisted": len(short), "stay": int(short.stays.sum()),
               "dropped": short.loc[~short.stays, "disease"].tolist(),
               "atlas_diseases": int(tried.mondo_id.nunique()),
               "labelled_entities": int(approved.moiety_id.nunique()),
               "labelled_without_pathway": int(approved.loc[approved.kind != "specific", "moiety_id"].nunique()),
               "estimates": len(responses), "estimates_by_question": responses.question.value_counts().to_dict(),
               **{f"how_solved_{round(t * 100)}": labels[f"how_solved_{round(t * 100)}"].value_counts().to_dict()
                  for t in THRESHOLDS},
               "why_not_one_drug": labels.why_not_one_drug.dropna().value_counts().to_dict(),
               "subgroup_estimates": int(responses.subgroup.sum()),
               "how_solved_50_fda_approved_only": labels.how_solved_50_fda_approved_only.value_counts().to_dict(),
               "crossover_comparisons": int(crossover.retained.notna().sum())}
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(numbers, f, indent=2)
    print(short.drop(columns="approved").to_string(index=False))
    print(area.to_string(index=False))
    print(labels.drop(columns="mondo_id").to_string(index=False))
    print(pairs.to_string(index=False))
    print(json.dumps(numbers, indent=2))


if __name__ == "__main__":
    main()
