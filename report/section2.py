"""Section 2: does preclinical evidence predict which programs reach approval?

    python -m report.section2

Unit: the Section 1 phase cohorts (development programs = molecular entity x
development indication, entering a phase in 2008-2019, report.windows.SECTION1), restricted to entities acting on
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
are not disease-specific: pan-essentiality is taken from the latest yearly
DepMap list from before entry (none before 2019), with the current list as a
sensitivity; loss-of-function constraint comes from the current gnomAD release.
Drug pharmacology lines describe the entity itself, not its disease: ChEMBL potency
measurements of its molecules (pipeline.chembl activities) published by the year before
entry, at its primary targets and at other single human proteins (report.frame.assays_as_of),
with every measurement known by 2026 as a sensitivity. They are left out of the
prediction model, which asks about evidence for the disease.

Relative success (RS) for an evidence line = LOA of programs with it / LOA of
programs without it, LOA being the product of BIO-style phase rates; 95%
intervals resample primary-target sets (an entity's primary targets taken
together, so programs on overlapping sets such as EGFR and EGFR+ERBB2 are
separate clusters). Adjusted per-phase relative risks come from a Poisson model
with cluster-robust errors (cluster = primary-target set), adjusting for disease
area, modality, entity novelty and entry period, one evidence line at a time and
all lines jointly. Genetic dose-response: LOA by tertile of the positive genetic
scores. Prediction is evaluated on a fixed-horizon cohort (Phase 1 entry
2008-2016, approval within ten years; 2008-2019 within six years as a check), with the Open Targets evidence and
novelty as of entry, by cross-validation grouped by primary-target set and a
temporal split; each evidence line's contribution is the drop in
cross-validated AUC when it is removed (human genetics: GWAS and rare-variant
evidence together), with a paired bootstrap interval. By disease area: the 15 areas
are pooled into six groups, relative success is estimated within each, and whether
an evidence line's Phase 2 effect differs between groups is a joint Wald test of its
interaction with the group (modality, novelty and period held fixed).
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import date

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
from report.windows import SECTION1, SECTION1_PERIODS, SECTION2_PREDICT

OUT = os.path.join(frame.REPO, "report", "output", "section2")
NAME_AUDIT = os.path.join(frame.REPO, "report", "audits", "chembl_name_matches.json")  # hand check of name matches
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
    "cell_line_screen": {"crispr"},      # Project Score knockout screens in cancer cell lines
    "neuron_screen": {"crispr_screen"},  # CRISPRbrain screens in stem-cell-derived neurons and microglia
}
LIABILITIES = ("pan_essential", "constrained")  # target-level properties, shown apart from the disease evidence
DRUG = ("assay_measured", "assay_potent", "assay_very_potent", "assay_cell_functional", "assay_selective")
DRUG_KEYS = {"assay_measured": "measured", "assay_potent": "potent", "assay_very_potent": "very_potent",
             "assay_cell_functional": "cell_functional", "assay_selective": "selective"}  # assays_as_of's flags
JOINT_DRUG = ("assay_measured", "assay_potent", "assay_cell_functional", "assay_selective")  # very_potent nests in potent
FEATURES = [*EVIDENCE, *LIABILITIES, *DRUG]
LABELS = {
    "genetic_any": "Any human genetics", "genetic_gwas": "GWAS",
    "genetic_rare": "Rare-variant or Mendelian genetics", "somatic": "Somatic cancer driver",
    "animal_model": "Mouse model of the disease", "rna_expression": "Expressed differently in the disease",
    "affected_pathway": "Disease pathway (Reactome)", "cell_line_screen": "CRISPR knockout screen in cancer cell lines",
    "neuron_screen": "CRISPR screen in stem-cell-derived neurons",
    "constrained": "Intolerant of loss of function", "pan_essential": "Essential in most cell lines",
    "assay_measured": "Potency at the target measured", "assay_potent": "Potent at the target (100 nM or better)",
    "assay_very_potent": "Very potent at the target (10 nM or better)",
    "assay_cell_functional": "Functional potency measured in cells",
    "assay_selective": "At least 100-fold selective over measured off-targets",
}
AREA_GROUPS = {"oncology": "oncology",
               "autoimmune": "immunology", "allergy": "immunology", "respiratory": "immunology",
               "gastroenterology": "immunology",
               "neurology": "neuroscience", "psychiatry": "neuroscience",
               "cardiovascular": "cardiometabolic", "metabolic": "cardiometabolic", "endocrine": "cardiometabolic",
               "hematology": "hematology"}  # every other area, and unmapped, is "other"
AREA_GROUP_LABELS = {"oncology": "Oncology", "immunology": "Immunology and inflammation",
                     "neuroscience": "Neuroscience", "cardiometabolic": "Cardiometabolic and endocrine",
                     "hematology": "Hematology", "other": "Other"}
AREA_LINES = ("genetic_any", "genetic_gwas", "genetic_rare", "somatic", "animal_model", "rna_expression",
              "assay_potent")


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
    essential = frame.common_essentials()
    measurements = frame.drug_assays()
    assays, no_assays = dict(iter(measurements.groupby("moiety_id"))), measurements.iloc[:0]

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
        drug = frame.assays_as_of(assays.get(r.moiety_id, no_assays), set(tg.symbol), year)
        drug_untimed = frame.assays_as_of(assays.get(r.moiety_id, no_assays), set(tg.symbol), 9999)
        out.append({"program_id": r.program_id, "phase": r.phase,
                    "target": tg.symbol.iloc[0] if len(tg) == 1 else "+".join(sorted(tg.symbol)),
                    **flags, **untimed, **strict,
                    "constrained": float(bool(lo) and min(lo) < 0.35),
                    "pan_essential": float(frame.essential_as_of(essential, ens, year)),
                    "pan_essential_untimed": float(frame.essential_as_of(essential, ens, max(essential))),
                    **{f: float(drug[k]) for f, k in DRUG_KEYS.items()},
                    **{f"{f}_untimed": float(drug_untimed[k]) for f, k in DRUG_KEYS.items()},
                    "assay_best": drug["best"], "assay_margin": drug["margin"]})
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


PERIOD_BINS = [SECTION1_PERIODS[0][0].year - 1, *(end.year for _, end in SECTION1_PERIODS)]


def poisson_rr(rows: pd.DataFrame, features: list[str]) -> list[dict]:
    """Per-phase relative risks of advancing from one Poisson model holding every
    feature in `features` (each adjusted for the others and for area, modality,
    novelty and entry period), cluster-robust by target; a feature with fewer
    than MIN_PROGRAMS_RR resolved programs in a phase is left out of that phase."""
    out = []
    for ph in (1, 2, 3):
        r = rows[(rows.phase == ph) & rows.event.isin(["advanced", "suspended"])].copy()
        r["y"] = (r.event == "advanced").astype(int)
        r["period"] = pd.cut(r.entry_year, PERIOD_BINS).astype(str)
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


def by_area(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Relative success of each line within each area group; whether its Phase 2 effect
    differs between groups (joint Wald test of the line-by-group interaction, adjusted for
    modality, novelty and period, cluster-robust by target); and the pooled relative
    success of human genetics with each group left out."""
    rows = rows.assign(area_group=rows.bio_area.map(AREA_GROUPS).fillna("other"))
    rs = pd.DataFrame([{**relative_success(g, f), "group": grp, "group_label": AREA_GROUP_LABELS[grp]}
                       for grp, g in rows.groupby("area_group") for f in AREA_LINES])
    r = rows[(rows.phase == 2) & rows.event.isin(["advanced", "suspended"])].copy()
    r["y"] = (r.event == "advanced").astype(int)
    r["period"] = pd.cut(r.entry_year, PERIOD_BINS).astype(str)
    tests = []
    for f in AREA_LINES:
        r["x"] = (r[f] > 0).astype(int)
        # groups where the line is both present and absent among enough programs to estimate its effect
        n_with = r.groupby("area_group").x.sum()
        keep = n_with[(n_with >= MIN_PROGRAMS_RR) & (r.groupby("area_group").x.mean() < 1)].index
        d = r[r.area_group.isin(keep)]
        if len(keep) < 2:
            tests.append({"feature": f, "groups": len(keep), "chi2": np.nan, "df": 0, "p": np.nan})
            continue
        fit = smf.glm("y ~ x * C(area_group) + C(modality) + novel + C(period)", data=d,
                      family=sm.families.Poisson()).fit(cov_type="cluster",
                                                        cov_kwds={"groups": pd.factorize(d.target)[0]})
        terms = [n for n in fit.params.index if n.startswith("x:")]
        w = fit.wald_test(", ".join(f"{t} = 0" for t in terms), scalar=True)
        tests.append({"feature": f, "groups": len(keep), "chi2": float(w.statistic), "df": len(terms),
                      "p": float(w.pvalue)})
    loo = pd.DataFrame([{**relative_success(rows[rows.area_group != grp], "genetic_any"), "left_out": grp,
                         "left_out_label": AREA_GROUP_LABELS[grp]} for grp in AREA_GROUP_LABELS])
    return rs, pd.DataFrame(tests), loo


PREDICT_YEARS, PREDICT_YEARS_CHECK = 10, 6  # approval horizons of the prediction and of its SECTION1 check
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


def temporal_split_year(window: tuple[date, date]) -> int:
    return (window[0].year + window[1].year) // 2


def prediction(progs: pd.DataFrame, trials: pd.DataFrame, snap, window: tuple[date, date],
               years: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fixed-horizon prediction: programs entering Phase 1 in `window`, outcome =
    FDA approval for the disease within `years`; Open Targets evidence and
    novelty as of entry. The temporal split trains on entries up to the window's
    middle year (temporal_split_year) and tests on later ones. Human genetics enters as its parts (GWAS, rare-variant)
    and is removed as a group; a line with fewer than MIN_PROGRAMS_RS programs
    carrying it is left out."""
    rows = phase_rows(progs, trials, snap, window=window)
    rows = rows[rows.phase == 1]
    ev = target_evidence(rows, progs)
    d = rows.merge(ev, on=["program_id", "phase"])
    appr = pd.to_datetime(d.approval_date)
    d["y"] = (appr.notna() & ((appr - d.entry).dt.days <= round(365.25 * years))).astype(int)
    model_features = [f for f in FEATURES if f != "genetic_any" and f not in DRUG
                      and (d[f] > 0).sum() >= MIN_PROGRAMS_RS]
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
        train = np.where(d.entry_year <= temporal_split_year(window))[0]
        test = np.where(d.entry_year > temporal_split_year(window))[0]
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
    rows = phase_rows(progs, trials, snap, window=SECTION1)
    ev = target_evidence(rows, progs)
    data = rows.merge(ev, on=["program_id", "phase"])
    data.to_csv(os.path.join(OUT, "phase_rows_with_evidence.csv"), index=False)

    rs = pd.DataFrame([relative_success(data, f) for f in FEATURES])
    rs.to_csv(os.path.join(OUT, "relative_success.csv"), index=False)
    untimed = pd.DataFrame([relative_success(data, f"{f}_untimed") for f in [*EVIDENCE, "pan_essential", *DRUG]])
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
    joint = pd.DataFrame(poisson_rr(data, [f for f in FEATURES if f != "genetic_any"  # its parts enter instead
                                           and (f not in DRUG or f in JOINT_DRUG)]))
    joint.to_csv(os.path.join(OUT, "joint_rr_by_phase.csv"), index=False)

    area_rs, area_tests, area_loo = by_area(data)
    area_rs.to_csv(os.path.join(OUT, "relative_success_by_area.csv"), index=False)
    area_tests.to_csv(os.path.join(OUT, "area_interaction_tests.csv"), index=False)
    area_loo.to_csv(os.path.join(OUT, "genetics_leave_one_area_out.csv"), index=False)
    groups = data.assign(area_group=data.bio_area.map(AREA_GROUPS).fillna("other")).groupby("area_group")

    metrics, ablation, cohort = prediction(progs, trials, snap, SECTION2_PREDICT, PREDICT_YEARS)
    metrics_check, _, cohort_check = prediction(progs, trials, snap, SECTION1, PREDICT_YEARS_CHECK)
    metrics_check.to_csv(os.path.join(OUT, "prediction_metrics_6y.csv"), index=False)
    metrics.to_csv(os.path.join(OUT, "prediction_metrics.csv"), index=False)
    ablation.to_csv(os.path.join(OUT, "prediction_ablation.csv"), index=False)
    cohort[["program_id", "target", "entry_year", "y"]].to_csv(os.path.join(OUT, "prediction_cohort.csv"), index=False)

    measured = data[data.assay_measured > 0]
    rs_measured = pd.DataFrame([relative_success(measured, f) for f in DRUG if f != "assay_measured"])
    rs_measured.to_csv(os.path.join(OUT, "relative_success_drug_measured.csv"), index=False)
    by_program = data.groupby("program_id").agg(measured=("assay_measured", "max"), modality=("modality", "first"))
    name_audit = json.load(open(NAME_AUDIT))
    matched = frame.query("""
        SELECT coalesce(m.modality, 'unknown') AS modality, b.basis
        FROM preclin.moiety m
        LEFT JOIN (SELECT moiety_id, min(basis) AS basis FROM preclin.chembl_moiety GROUP BY 1) b USING (moiety_id)
        WHERE m.moiety_id IN (SELECT moiety_id FROM preclin.dev_program)""")
    match_table = pd.crosstab(matched.modality, matched.basis.fillna("unmatched")) \
        .reindex(columns=["drug_chembl_id", "inchikey", "name", "unmatched"], fill_value=0)
    match_table = match_table.loc[match_table.sum(axis=1).sort_values(ascending=False).index]
    match_table.to_csv(os.path.join(OUT, "chembl_match_by_modality.csv"))
    keyed = lambda df, *cols: {"_".join(str(r[c]) for c in cols): r for r in df.to_dict(orient="records")}
    numbers = {"n_program_phase_rows": len(data), "n_programs": int(data.program_id.nunique()),
               "n_targets": n_genes(data.target),
               "evidence_coverage_ph1": {f: float((data[data.phase == 1][f] > 0).mean()) for f in FEATURES},
               "rs": keyed(rs, "feature"), "rs_untimed": keyed(untimed, "feature"), "rs_lin_only": keyed(strict, "feature"),
               "adjusted_rr": keyed(adj, "feature", "phase"), "joint_rr": keyed(joint, "feature", "phase"),
               "dose": keyed(dose, "band"), "prediction": keyed(metrics, "split", "features"),
               "ablation": keyed(ablation, "feature"), "n_prediction": int(len(cohort)),
               "n_prediction_positive": int(cohort.y.sum()),
               "prediction_split_year": temporal_split_year(SECTION2_PREDICT), "prediction_years": PREDICT_YEARS,
               "prediction_window": [SECTION2_PREDICT[0].year, SECTION2_PREDICT[1].year],
               "prediction_6y": keyed(metrics_check, "split", "features"), "n_prediction_6y": int(len(cohort_check)),
               "n_prediction_6y_positive": int(cohort_check.y.sum()),
               "rs_drug_measured": keyed(rs_measured, "feature"),
               "area": {"rs": keyed(area_rs, "group", "feature"), "tests": keyed(area_tests, "feature"),
                        "loo": keyed(area_loo, "left_out"),
                        "loo_min": area_loo.loc[area_loo.rs.idxmin()].to_dict(), "loo_max": float(area_loo.rs.max()),
                        "n_programs": {k: int(g.program_id.nunique()) for k, g in groups}}, "min_programs_rs": MIN_PROGRAMS_RS,
               "drug": {"measured": float(by_program.measured.mean()),
                        "measured_by_modality": {m: {"share": float(g.measured.mean()), "n": int(len(g))}
                                                 for m, g in by_program.groupby("modality")},
                        "n_rows_measured": int(len(measured)),
                        "best_median": float(measured.assay_best.median()),
                        "best_median_nm": float(10 ** (9 - measured.assay_best.median())),
                        "potent_of_measured": float((measured.assay_potent > 0).mean()),
                        "selective_of_off_measured": float((measured.assay_selective > 0).sum()
                                                           / max(1, measured.assay_margin.notna().sum())),
                        "off_measured_of_measured": float(measured.assay_margin.notna().mean()),
                        "entities_matched": int((matched.basis.notna()).sum()), "entities": int(len(matched)),
                        "name_audit": {"n": len(name_audit), "correct": sum(r["correct"] for r in name_audit)},
                        "release": frame.query("""SELECT metadata FROM preclin.evidence_source_release
                                                  WHERE source_name = 'chembl_activity'
                                                  ORDER BY source_release_id DESC LIMIT 1""").metadata.iloc[0]},
               "cell_line_screen_somatic": float(data[data.cell_line_screen > 0].groupby("program_id").somatic.max()
                                                 .gt(0).mean()),
               "project_score": {f"n_{y}": int(n) for y, n in frame.query(
                   """SELECT evidence_year, count(*) FROM preclin.ot_evidence WHERE datasource = 'crispr'
                      GROUP BY 1""").itertuples(index=False)}}
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(numbers, f, indent=1, default=float)
    print(rs[["label", "n_with", "loa_with", "loa_without", "rs", "rs_lo", "rs_hi"]].to_string())


if __name__ == "__main__":
    main()
