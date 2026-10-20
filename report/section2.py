"""Section 2: does preclinical evidence predict which programs reach approval?

    python -m report.section2

Unit: the Section 1 phase cohorts (development programs = molecular entity x
MONDO disease, entering a phase in 2015-2025), restricted to entities acting on
human protein targets. Each program carries evidence about its entity's
primary targets *for its disease*: Open Targets associations (26.09) whose
disease matches the program's disease on MONDO (same term, a subtype, or Lin
similarity >= 0.8), scored as of the year before the program entered the
phase. Target-level properties (loss-of-function constraint, pan-essentiality)
are not disease-specific.

Relative success (RS) for an evidence line = LOA of programs with it / LOA of
programs without it, LOA being the product of BIO-style phase rates; 95%
intervals resample targets. Adjusted per-phase relative risks come from a
Poisson model with cluster-robust errors (cluster = primary target), adjusting
for disease area, modality, entity novelty and entry period. Prediction is
evaluated on a fixed-horizon cohort (Phase 1 entry 2008-2016, approval within
ten years), with features frozen at entry, by target-grouped cross-validation
and a temporal split.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from report import frame
from report.disease_match import Mondo
from report.section1 import N_BOOT, SEED, phase_rows

OUT = os.path.join(frame.REPO, "report", "output", "section2")

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
        SELECT mt.moiety_id, t.id AS target_id, t.symbol, t.ensembl_id
        FROM preclin.moiety_target mt JOIN public.targets t ON t.id = mt.target_id
        JOIN preclin.moiety m USING (moiety_id)
        WHERE mt.is_primary AND m.target_kind = 'human_protein'""")
    assoc = frame.query("""
        SELECT a.target_ensembl, a.datasource, a.series_years, a.series_scores, d.mondo_ids
        FROM preclin.ot_association a JOIN preclin.ot_disease d USING (disease_id)""")
    by_target = defaultdict(list)
    for ens, src, ys, ss, mids in assoc.itertuples(index=False):
        if mids:
            by_target[ens].append((src, ys, ss, mids))
    constraint = frame.query("""SELECT t.ensembl_id, min(g.loeuf) AS loeuf
                                FROM public.gene_constraint g JOIN public.targets t ON t.id = g.target_id
                                GROUP BY 1""").set_index("ensembl_id").loeuf
    essential = set(frame.query("""SELECT t.ensembl_id FROM public.gene_essentiality_summary e
                                   JOIN public.targets t ON t.id = e.target_id
                                   WHERE e.pan_essential""").ensembl_id)

    disease = progs.set_index("program_id").mondo_id
    tmap = targets.groupby("moiety_id")
    match_cache: dict[tuple[str, str], bool] = {}
    out = []
    for r in rows.itertuples(index=False):
        d = disease.get(r.program_id)
        if r.moiety_id not in tmap.groups or not isinstance(d, str):
            continue
        tg = tmap.get_group(r.moiety_id)
        year = r.entry_year - 1
        flags = {k: 0.0 for k in EVIDENCE}
        for ens in tg.ensembl_id.dropna():
            for src, ys, ss, mids in by_target.get(ens, ()):
                hit = False
                for g in mids:
                    key = (g, d)
                    if key not in match_cache:
                        match_cache[key] = mondo.matches(g, d)
                    if match_cache[key]:
                        hit = True
                        break
                if not hit:
                    continue
                sc = score_as_of(ys, ss, year)
                for k, srcs in EVIDENCE.items():
                    if src in srcs:
                        flags[k] = max(flags[k], sc)
        ens = list(tg.ensembl_id.dropna())
        lo = [constraint.get(e) for e in ens if pd.notna(constraint.get(e))]
        out.append({"program_id": r.program_id, "phase": r.phase,
                    "target": tg.symbol.iloc[0] if len(tg) == 1 else "+".join(sorted(tg.symbol)),
                    **{k: v for k, v in flags.items()},
                    "constrained": float(bool(lo) and min(lo) < 0.35),
                    "pan_essential": float(any(e in essential for e in ens))})
    return pd.DataFrame(out)


def loa_by(rows: pd.DataFrame) -> float:
    rate = {}
    for ph in (1, 2, 3):
        r = rows[rows.phase == ph]
        adv, sus = (r.event == "advanced").sum(), (r.event == "suspended").sum()
        rate[ph] = adv / (adv + sus) if adv + sus else np.nan
    return float(np.prod([rate[ph] for ph in (1, 2, 3)]))


def relative_success(rows: pd.DataFrame, feature: str, threshold: float = 0.0, n: int = N_BOOT) -> dict:
    with_ = rows[rows[feature] > threshold]
    without = rows[rows[feature] <= threshold]
    rs = loa_by(with_) / loa_by(without)
    rng = np.random.default_rng(SEED)
    targets = rows.target.unique()
    groups = {t: g for t, g in rows.groupby("target")}
    draws = []
    for _ in range(n):
        sample = pd.concat([groups[t] for t in rng.choice(targets, len(targets))], ignore_index=True)
        w, wo = sample[sample[feature] > threshold], sample[sample[feature] <= threshold]
        a, b = loa_by(w), loa_by(wo)
        draws.append(a / b if b else np.nan)
    lo, hi = np.nanpercentile(draws, [2.5, 97.5])
    return {"feature": feature, "label": LABELS.get(feature, feature), "threshold": threshold,
            "n_with": int(with_.program_id.nunique()), "n_without": int(without.program_id.nunique()),
            "n_targets_with": int(with_.target.nunique()),
            "loa_with": loa_by(with_), "loa_without": loa_by(without), "rs": rs, "rs_lo": lo, "rs_hi": hi}


def adjusted_rr(rows: pd.DataFrame, feature: str) -> list[dict]:
    """Per-phase relative risk of advancing, Poisson with cluster-robust SE by target."""
    out = []
    for ph in (1, 2, 3):
        r = rows[(rows.phase == ph) & rows.event.isin(["advanced", "suspended"])].copy()
        r["y"] = (r.event == "advanced").astype(int)
        r["x"] = (r[feature] > 0).astype(int)
        r["period"] = pd.cut(r.entry_year, [2014, 2017, 2020, 2025]).astype(str)
        if r.x.nunique() < 2:
            continue
        model = smf.glm("y ~ x + C(bio_area) + C(modality) + novel + C(period)", data=r,
                        family=sm.families.Poisson())
        fit = model.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(r.target)[0]})
        b, se = fit.params["x"], fit.bse["x"]
        out.append({"feature": feature, "phase": ph, "n": len(r), "rr": float(np.exp(b)),
                    "rr_lo": float(np.exp(b - 1.96 * se)), "rr_hi": float(np.exp(b + 1.96 * se)),
                    "p": float(fit.pvalues["x"])})
    return out


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    snap = frame.snapshot()
    progs, trials = frame.programs(), frame.program_trials()
    rows = phase_rows(progs, trials, snap)
    ev = target_evidence(rows, progs)
    data = rows.merge(ev, on=["program_id", "phase"])
    data.to_csv(os.path.join(OUT, "phase_rows_with_evidence.csv"), index=False)

    features = list(EVIDENCE) + ["constrained", "pan_essential"]
    rs = pd.DataFrame([relative_success(data, f) for f in features])
    rs.to_csv(os.path.join(OUT, "relative_success.csv"), index=False)
    adj = pd.DataFrame([x for f in features for x in adjusted_rr(data, f)])
    adj.to_csv(os.path.join(OUT, "adjusted_rr_by_phase.csv"), index=False)

    ph3 = data[data.phase == 3]
    table = []
    for f in features:
        w, wo = ph3[ph3[f] > 0], ph3[ph3[f] <= 0]
        rw = (w.event == "advanced").sum() / max(1, w.event.isin(["advanced", "suspended"]).sum())
        rwo = (wo.event == "advanced").sum() / max(1, wo.event.isin(["advanced", "suspended"]).sum())
        table.append({"feature": f, "label": LABELS[f], "n_with": int(w.event.isin(["advanced", "suspended"]).sum()),
                      "approved_with": float(rw), "approved_without": float(rwo)})
    pd.DataFrame(table).to_csv(os.path.join(OUT, "phase3_approval_by_evidence.csv"), index=False)

    numbers = {"n_program_phase_rows": len(data), "n_programs": int(data.program_id.nunique()),
               "n_targets": int(data.target.nunique()), "relative_success": rs.to_dict(orient="records")}
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(numbers, f, indent=1, default=float)
    print(rs[["label", "n_with", "loa_with", "loa_without", "rs", "rs_lo", "rs_hi"]].to_string())


if __name__ == "__main__":
    main()
