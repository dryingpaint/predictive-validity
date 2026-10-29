"""Section 2: does preclinical evidence predict which programs reach approval?

    python -m report.section2

Unit: the Section 1 phase cohorts (development programs = molecular entity x
development indication, entering a phase in 2015-2025), restricted to entities acting on
human protein targets. Each program carries evidence about its entity's
primary targets *for its disease*: Open Targets associations (26.09) whose
disease matches the program's disease on MONDO (same term, a subtype, or Lin
similarity >= 0.8), scored as of the year before the program entered the
phase, from yearly series rebuilt from the evidence items dated by the year
each became known (pipeline.opentargets evidence). Undated items are left out
of the series, so as-of scores undercount; a sensitivity analysis uses the
release score (evidence known by 2026, dated or not); another counts only evidence diseases
with Lin similarity >= 0.8 (Minikel et al.'s criterion), dropping the subtype
rule, which is permissive for broad program diseases. Target-level properties
(loss-of-function constraint, pan-essentiality) are not disease-specific and
come from the current gnomAD and DepMap releases, not as of entry.

Relative success (RS) for an evidence line = LOA of programs with it / LOA of
programs without it, LOA being the product of BIO-style phase rates; 95%
intervals resample primary-target sets (an entity's primary targets taken
together, so programs on overlapping sets such as EGFR and EGFR+ERBB2 are
separate clusters). Adjusted per-phase relative risks come from a Poisson model
with cluster-robust errors (cluster = primary-target set), adjusting for disease
area, modality, entity novelty and entry period, one evidence line at a time and
all lines jointly. Genetic dose-response: LOA by tertile of the positive genetic
scores. Prediction is evaluated on a fixed-horizon cohort (Phase 1 entry
2008-2016, approval within ten years), with the Open Targets evidence and
novelty as of entry, by cross-validation grouped by primary-target set and a
temporal split; each evidence line's contribution is the drop in
cross-validated AUC when it is removed (human genetics: GWAS and rare-variant
evidence together), with a paired bootstrap interval.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from report import frame
from report.disease_match import Mondo
from report.section1 import N_BOOT, SEED, boot_rates, loa, phase_rows, resolved_counts
from report.windows import RECENT, SECTION2_PREDICT

OUT = os.path.join(frame.REPO, "report", "output", "section2")
MIN_PROGRAMS_RS = 100  # programs with the evidence below which relative success is not estimated
MIN_PROGRAMS_RR = 20   # resolved programs with the evidence, per phase, below which no relative risk is fitted

EVIDENCE = {
    "genetic_any": {"gwas_credible_sets", "gene_burden", "eva", "genomics_england", "orphanet",
                    "uniprot_literature", "uniprot_variants", "gene2phenotype", "clingen"},
    "genetic_gwas": {"gwas_credible_sets"},
    "genetic_rare": {"gene_burden", "eva", "genomics_england", "orphanet", "uniprot_literature",
                     "uniprot_variants", "gene2phenotype", "clingen"},
    "somatic": {"cancer_gene_census", "intogen", "eva_somatic"},
    "animal_model": {"impc"},
    "rna_expression": {"expression_atlas"},
    "affected_pathway": {"reactome"},
    "functional_screen": {"crispr", "crispr_screen"},
}
FEATURES = [*EVIDENCE, "constrained", "pan_essential"]
LABELS = {
    "genetic_any": "Human genetics (any germline source)", "genetic_gwas": "GWAS credible set",
    "genetic_rare": "Rare-variant / Mendelian (ClinVar, Orphanet, G2P, ClinGen, burden)",
    "somatic": "Somatic driver (COSMIC CGC, IntOGen, ClinVar somatic)", "animal_model": "Mouse model (IMPC)",
    "rna_expression": "Differential expression in disease (Expression Atlas)",
    "affected_pathway": "Pathway (Reactome)", "functional_screen": "CRISPR screen",
    "constrained": "LoF-intolerant target (gnomAD LOEUF < 0.35)", "pan_essential": "Pan-essential (DepMap)",
}


def score_as_of(years: list[int], scores: list[float], year: int) -> float:
    s = 0.0
    for y, v in zip(years, scores):
        if y <= year:
            s = v
        else:
            break
    return s


def target_evidence(rows: pd.DataFrame, progs: pd.DataFrame) -> pd.DataFrame:
    """Evidence flags per (program, phase) row, as of the year before phase entry."""
    mondo = Mondo()
    targets = frame.query("""
        SELECT mt.moiety_id, t.symbol, t.ensembl_id
        FROM preclin.moiety_target mt JOIN public.targets t ON t.id = mt.target_id
        JOIN preclin.moiety m USING (moiety_id)
        WHERE mt.is_primary AND m.target_kind = 'human_protein'""")
    assoc = frame.query_paged("""
        SELECT a.target_ensembl, a.datasource, a.series_years, a.series_scores, a.score, d.mondo_ids
        FROM preclin.ot_association a JOIN preclin.ot_disease d USING (disease_id)""", "target_ensembl")
    by_target = defaultdict(list)
    for ens, src, ys, ss, final, mids in assoc.itertuples(index=False):
        if mids:
            by_target[ens].append((src, ys, ss, final, mids))
    constraint = frame.query("""SELECT t.ensembl_id, min(g.loeuf) AS loeuf
                                FROM public.gene_constraint g JOIN public.targets t ON t.id = g.target_id
                                GROUP BY 1""").set_index("ensembl_id").loeuf
    essential = set(frame.query("""SELECT g.ensembl_id FROM preclin.depmap_common_essential e
                                   JOIN preclin.hgnc_gene g USING (entrez_id)
                                   WHERE g.ensembl_id IS NOT NULL""").ensembl_id)

    disease = progs.set_index("program_id").mondo_id
    tmap = targets.groupby("moiety_id")
    match_cache: dict[tuple[str, str], tuple[bool, bool]] = {}
    out = []
    for r in rows.itertuples(index=False):
        d = disease.get(r.program_id)
        if r.moiety_id not in tmap.groups or not isinstance(d, str):
            continue
        tg = tmap.get_group(r.moiety_id)
        year = r.entry_year - 1
        flags = {k: 0.0 for k in EVIDENCE}
        untimed = {f"{k}_untimed": 0.0 for k in EVIDENCE}
        strict = {f"{k}_strict": 0.0 for k in EVIDENCE}
        ens = list(tg.ensembl_id.dropna())
        for e in ens:
            for src, ys, ss, final, mids in by_target.get(e, ()):
                hit = close = False
                for g in mids:
                    key = (g, d)
                    if key not in match_cache:
                        match_cache[key] = mondo.matches(g, d)
                    hit, close = hit or match_cache[key][0], close or match_cache[key][1]
                if not hit:
                    continue
                sc = score_as_of(ys, ss, year)
                for k, srcs in EVIDENCE.items():
                    if src in srcs:
                        flags[k] = max(flags[k], sc)
                        untimed[f"{k}_untimed"] = max(untimed[f"{k}_untimed"], final or 0.0)
                        if close:
                            strict[f"{k}_strict"] = max(strict[f"{k}_strict"], sc)
        lo = [constraint.get(e) for e in ens if pd.notna(constraint.get(e))]
        out.append({"program_id": r.program_id, "phase": r.phase,
                    "target": tg.symbol.iloc[0] if len(tg) == 1 else "+".join(sorted(tg.symbol)),
                    **flags, **untimed, **strict,
                    "constrained": float(bool(lo) and min(lo) < 0.35),
                    "pan_essential": float(any(e in essential for e in ens))})
    return pd.DataFrame(out)


def n_genes(targets: pd.Series) -> int:
    """Distinct genes among primary-target sets ("EGFR+ERBB2" holds two)."""
    return len({g for t in targets.dropna() for g in t.split("+")})


def relative_success(rows: pd.DataFrame, feature: str) -> dict:
    has = rows[feature] > 0
    if rows[has].program_id.nunique() < MIN_PROGRAMS_RS or has.all():
        return {"feature": feature, "label": LABELS.get(feature, feature), "threshold": 0.0,
                "n_with": int(rows[has].program_id.nunique()), "n_without": int(rows[~has].program_id.nunique()),
                "n_targets_with": n_genes(rows[has].target),
                "loa_with": np.nan, "loa_without": np.nan, "rs": np.nan, "rs_lo": np.nan, "rs_hi": np.nan}
    counts, groups = resolved_counts(rows, pd.factorize(rows.target, use_na_sentinel=False)[0], has)
    draws = boot_rates(counts).prod(axis=-1)
    i_with, i_wo = groups.index(True), groups.index(False)
    with np.errstate(invalid="ignore", divide="ignore"):
        rs_draws = draws[:, i_with] / draws[:, i_wo]
    lo, hi = np.nanpercentile(rs_draws, [2.5, 97.5])
    with_, without = rows[has], rows[~has]
    loa_with, loa_without = loa(with_), loa(without)
    label = LABELS.get(feature.removesuffix("_untimed").removesuffix("_strict"), feature)
    return {"feature": feature, "label": label, "threshold": 0.0,
            "n_with": int(with_.program_id.nunique()), "n_without": int(without.program_id.nunique()),
            "n_targets_with": n_genes(with_.target),
            "loa_with": loa_with, "loa_without": loa_without, "rs": loa_with / loa_without,
            "rs_lo": float(lo), "rs_hi": float(hi)}


def dose_response(rows: pd.DataFrame, feature: str) -> pd.DataFrame:
    """LOA by strength of one evidence line: none, then tertiles of the positive
    scores (cut points set by the score distribution, not by outcomes); 95%
    intervals resample targets."""
    pos = rows.loc[rows[feature] > 0, feature]
    cuts = [0.0, *pos.quantile([1 / 3, 2 / 3]).tolist(), float("inf")]
    labels = ["none", "low", "middle", "high"]
    band = pd.Series("none", index=rows.index)
    for lab, lo, hi in zip(labels[1:], cuts[:-1], cuts[1:]):
        band[(rows[feature] > lo) & (rows[feature] <= hi)] = lab
    counts, groups = resolved_counts(rows, pd.factorize(rows.target, use_na_sentinel=False)[0], band)
    draws = boot_rates(counts).prod(axis=-1)
    out = []
    for lab, lo, hi in zip(labels, [0.0, *cuts[:-1]], cuts):
        g = rows[band == lab]
        d = draws[:, groups.index(lab)] if lab in groups else np.array([np.nan])
        out.append({"feature": feature, "band": lab, "score_from": lo, "score_to": hi,
                    "n_programs": int(g.program_id.nunique()), "n_targets": n_genes(g.target), "loa": loa(g),
                    "loa_lo": float(np.nanpercentile(d, 2.5)), "loa_hi": float(np.nanpercentile(d, 97.5))})
    return pd.DataFrame(out)


def poisson_rr(rows: pd.DataFrame, features: list[str]) -> list[dict]:
    """Per-phase relative risks of advancing from one Poisson model holding every
    feature in `features` (each adjusted for the others and for area, modality,
    novelty and entry period), cluster-robust by target; a feature with fewer
    than MIN_PROGRAMS_RR resolved programs in a phase is left out of that phase."""
    out = []
    for ph in (1, 2, 3):
        r = rows[(rows.phase == ph) & rows.event.isin(["advanced", "suspended"])].copy()
        r["y"] = (r.event == "advanced").astype(int)
        r["period"] = pd.cut(r.entry_year, [2014, 2017, 2020, 2025]).astype(str)
        present = [f for f in features if (r[f] > 0).sum() >= MIN_PROGRAMS_RR and (r[f] > 0).nunique() == 2]
        if not present:
            continue
        for f in present:
            r[f"x_{f}"] = (r[f] > 0).astype(int)
        formula = "y ~ " + " + ".join(f"x_{f}" for f in present) + " + C(bio_area) + C(modality) + novel + C(period)"
        fit = smf.glm(formula, data=r, family=sm.families.Poisson()).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(r.target)[0]})
        for f in present:
            b, se = fit.params[f"x_{f}"], fit.bse[f"x_{f}"]
            out.append({"feature": f, "phase": ph, "n": len(r), "rr": float(np.exp(b)),
                        "rr_lo": float(np.exp(b - 1.96 * se)), "rr_hi": float(np.exp(b + 1.96 * se)),
                        "p": float(fit.pvalues[f"x_{f}"])})
    return out


HORIZON_DAYS = 3653
CV_REPEATS = 20  # repetitions of the grouped 5-fold split; one split's AUC moves by several points with the folds


def resample_targets(groups: np.ndarray, y: np.ndarray, rng: np.random.Generator):
    """Row indices of N_BOOT target-cluster resamples, skipping a draw whose
    outcomes are all one class; every draw takes one rng.choice."""
    uniq = np.unique(groups)
    members = {u: np.where(groups == u)[0] for u in uniq}
    for _ in range(N_BOOT):
        m = np.concatenate([members[u] for u in rng.choice(uniq, len(uniq))])
        if y[m].min() < y[m].max():
            yield m


def prediction(progs: pd.DataFrame, trials: pd.DataFrame, snap) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fixed-horizon prediction: programs entering Phase 1 in 2008-2016, outcome =
    FDA approval for the disease within ten years; Open Targets evidence and
    novelty as of entry. Human genetics enters as its parts (GWAS, rare-variant)
    and is removed as a group; a line with fewer than MIN_PROGRAMS_RS programs
    carrying it is left out."""
    rows = phase_rows(progs, trials, snap, window=SECTION2_PREDICT)
    rows = rows[rows.phase == 1]
    ev = target_evidence(rows, progs)
    d = rows.merge(ev, on=["program_id", "phase"])
    appr = pd.to_datetime(d.approval_date)
    d["y"] = (appr.notna() & ((appr - d.entry).dt.days <= HORIZON_DAYS)).astype(int)
    model_features = [f for f in FEATURES if f != "genetic_any" and (d[f] > 0).sum() >= MIN_PROGRAMS_RS]
    ablations = {f: [f] for f in model_features}
    ablations["genetic_any"] = [f for f in ("genetic_gwas", "genetic_rare") if f in model_features]
    X_ev = (d[model_features] > 0).astype(float)
    X_cov = pd.get_dummies(d[["bio_area", "modality"]], drop_first=False).astype(float)
    X_cov["novel"] = d.novel.astype(float)
    X_cov["entry_year"] = d.entry_year - 2008
    sets = {"covariates": X_cov, "covariates+evidence": pd.concat([X_cov, X_ev], axis=1), "evidence": X_ev}
    for f, cols in ablations.items():
        sets[f"covariates+evidence-{f}"] = pd.concat([X_cov, X_ev.drop(columns=cols)], axis=1)
    groups = pd.factorize(d.target, sort=True)[0]

    def fit_predict(X, train, test):
        model = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=2000))
        model.fit(X.iloc[train], d.y.iloc[train])
        return model.predict_proba(X.iloc[test])[:, 1]

    splits = [list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED + r).split(d, d.y, groups))
              for r in range(CV_REPEATS)]
    preds = {}
    for name, X in sets.items():
        oof = np.zeros(len(d))  # out-of-fold prediction averaged over the repetitions
        for folds in splits:
            for train, test in folds:
                oof[test] += fit_predict(X, train, test) / CV_REPEATS
        preds[("grouped_cv", name)] = (np.arange(len(d)), oof)
        train = np.where(d.entry_year <= 2012)[0]
        test = np.where(d.entry_year >= 2013)[0]
        preds[("temporal", name)] = (test, fit_predict(X, train, test))

    rng = np.random.default_rng(SEED)
    metrics = []
    for (split, name), (idx, p) in preds.items():
        y = d.y.to_numpy()[idx]
        auc, ap = roc_auc_score(y, p), average_precision_score(y, p)
        draws = np.array([(roc_auc_score(y[m], p[m]), average_precision_score(y[m], p[m]))
                          for m in resample_targets(groups[idx], y, rng)])
        metrics.append({"split": split, "features": name, "n": len(idx), "n_positive": int(y.sum()),
                        "auc": auc, "auc_lo": np.percentile(draws[:, 0], 2.5), "auc_hi": np.percentile(draws[:, 0], 97.5),
                        "pr_auc": ap, "pr_lo": np.percentile(draws[:, 1], 2.5), "pr_hi": np.percentile(draws[:, 1], 97.5),
                        "base_rate": float(y.mean())})
    full = preds[("grouped_cv", "covariates+evidence")][1]
    y = d.y.to_numpy()
    ablation = []
    for f in [f for f in FEATURES if f in ablations]:
        reduced = preds[("grouped_cv", f"covariates+evidence-{f}")][1]
        delta = roc_auc_score(y, full) - roc_auc_score(y, reduced)
        diffs = [roc_auc_score(y[m], full[m]) - roc_auc_score(y[m], reduced[m])
                 for m in resample_targets(groups, y, rng)]
        ablation.append({"feature": f, "label": LABELS[f], "auc_drop": delta,
                         "drop_lo": float(np.percentile(diffs, 2.5)), "drop_hi": float(np.percentile(diffs, 97.5))})
    metrics = pd.DataFrame(metrics)
    metrics = metrics[~metrics.features.str.contains("-")]
    return metrics, pd.DataFrame(ablation), d


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    snap = frame.snapshot()
    progs, trials = frame.programs(), frame.program_trials()
    rows = phase_rows(progs, trials, snap, window=RECENT)
    ev = target_evidence(rows, progs)
    data = rows.merge(ev, on=["program_id", "phase"])
    data.to_csv(os.path.join(OUT, "phase_rows_with_evidence.csv"), index=False)

    rs = pd.DataFrame([relative_success(data, f) for f in FEATURES])
    rs.to_csv(os.path.join(OUT, "relative_success.csv"), index=False)
    untimed = pd.DataFrame([relative_success(data, f"{f}_untimed") for f in EVIDENCE])
    untimed.to_csv(os.path.join(OUT, "relative_success_untimed.csv"), index=False)
    strict = pd.DataFrame([relative_success(data, f"{f}_strict") for f in EVIDENCE])
    strict.to_csv(os.path.join(OUT, "relative_success_lin_only.csv"), index=False)
    adj = pd.DataFrame([x for f in FEATURES for x in poisson_rr(data, [f])])
    adj.to_csv(os.path.join(OUT, "adjusted_rr_by_phase.csv"), index=False)

    ph3 = data[data.phase == 3]
    table = []
    for f in FEATURES:
        w, wo = ph3[ph3[f] > 0], ph3[ph3[f] <= 0]
        rw = (w.event == "advanced").sum() / max(1, w.event.isin(["advanced", "suspended"]).sum())
        rwo = (wo.event == "advanced").sum() / max(1, wo.event.isin(["advanced", "suspended"]).sum())
        table.append({"feature": f, "label": LABELS[f], "n_with": int(w.event.isin(["advanced", "suspended"]).sum()),
                      "approved_with": float(rw), "approved_without": float(rwo)})
    pd.DataFrame(table).to_csv(os.path.join(OUT, "phase3_approval_by_evidence.csv"), index=False)

    dose = dose_response(data, "genetic_any")
    dose.to_csv(os.path.join(OUT, "genetic_dose_response.csv"), index=False)
    joint = pd.DataFrame(poisson_rr(data, [f for f in FEATURES if f != "genetic_any"]))  # its parts enter instead
    joint.to_csv(os.path.join(OUT, "joint_rr_by_phase.csv"), index=False)

    metrics, ablation, cohort = prediction(progs, trials, snap)
    metrics.to_csv(os.path.join(OUT, "prediction_metrics.csv"), index=False)
    ablation.to_csv(os.path.join(OUT, "prediction_ablation.csv"), index=False)
    cohort[["program_id", "target", "entry_year", "y"]].to_csv(os.path.join(OUT, "prediction_cohort.csv"), index=False)

    keyed = lambda df, *cols: {"_".join(str(r[c]) for c in cols): r for r in df.to_dict(orient="records")}
    numbers = {"n_program_phase_rows": len(data), "n_programs": int(data.program_id.nunique()),
               "n_targets": n_genes(data.target),
               "evidence_coverage_ph1": {f: float((data[data.phase == 1][f] > 0).mean()) for f in FEATURES},
               "rs": keyed(rs, "feature"), "rs_untimed": keyed(untimed, "feature"), "rs_lin_only": keyed(strict, "feature"),
               "adjusted_rr": keyed(adj, "feature", "phase"), "joint_rr": keyed(joint, "feature", "phase"),
               "dose": keyed(dose, "band"), "prediction": keyed(metrics, "split", "features"),
               "ablation": keyed(ablation, "feature"), "n_prediction": int(len(cohort)),
               "n_prediction_positive": int(cohort.y.sum())}
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(numbers, f, indent=1, default=float)
    print(rs[["label", "n_with", "loa_with", "loa_without", "rs", "rs_lo", "rs_hi"]].to_string())


if __name__ == "__main__":
    main()
