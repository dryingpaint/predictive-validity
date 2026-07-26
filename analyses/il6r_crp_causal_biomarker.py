#!/usr/bin/env python3
"""
IL-6R vs CRP — "which biomarker is causal for the outcome" case study.

Companion to analyses/PCSK9_VS_APP_CETP.md (PR #6) and CASE_STUDIES.md (PR #8).
Same causal-gates frame: a program clears
  genetics -> target->biomarker -> biomarker-causal-for-outcome ->
  drug engages target -> safety -> approval.

Teaching point: CRP and IL-6/IL-6R are BOTH inflammation biomarkers associated
with cardiovascular disease and BOTH have genetic support. The repo's own
genetics scorer cannot separate them (all three land on the SAME genetic_only_v1
score). They diverge at exactly one gate: "is the biomarker causal for the hard
outcome?" — IL-6R clears it by Mendelian randomization; CRP fails it. That gate
is what separates a viable target from a dead end.

Genetics are scored with the repo's own benchmark/scorers_rule_based.py
::scorer_genetic_only ("genetic_only_v1"), on evidence pulled from
preclin.v_target_evidence_wide (present-day, 2026 — hindsight, same caveat as the
case-scorecard and head-to-head PRs). Run with DATABASE_URL set to re-pull;
otherwise the last-pulled values (baked in below) are used so the figure renders
with no DB.

Outputs (lean — commit the _clean figure variants + the CSV):
  data/il6r_crp_causal_biomarker.csv          provenance (scores + DB components)
  data/il6r_crp_causal_biomarker_clean.png    200-dpi editorial figure
  data/il6r_crp_causal_biomarker_clean.svg    editable vector
"""
from __future__ import annotations
import os
import sys

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
os.makedirs(DATA, exist_ok=True)
sys.path.insert(0, os.path.join(HERE, "..", "benchmark"))
from scorers_rule_based import score_ti  # noqa: E402  (repo's own genetic_only_v1)

# ------------------------------------------------------------------
# Evidence from preclin.v_target_evidence_wide (present-day, 2026).
# Column names mirror benchmark/runner.py::row_to_evidence_context so the
# genetic_only_v1 scorer sees exactly the fields it sees in the benchmark.
# ------------------------------------------------------------------
WIDE = {
    #                 tid   clingen mend  gwas  ot_gen   ot_som ot_animal n_causal loeuf   pli
    "CRP":  dict(target_id=1124, clingen_n_strong=0, mendelian_n=1, gwas_n_sig=142,
                 ot_genetic_max=0.703, ot_somatic_score_max=None, ot_animal_model_max=None,
                 n_causal_diseases=0, gnomad_loeuf=1.932, gnomad_pli=0.0005),
    "IL6R": dict(target_id=77,   clingen_n_strong=0, mendelian_n=2, gwas_n_sig=269,
                 ot_genetic_max=0.877, ot_somatic_score_max=None, ot_animal_model_max=0.771,
                 n_causal_diseases=3, gnomad_loeuf=0.965, gnomad_pli=6.9e-08),
    "IL6":  dict(target_id=406,  clingen_n_strong=0, mendelian_n=4, gwas_n_sig=66,
                 ot_genetic_max=0.900, ot_somatic_score_max=None, ot_animal_model_max=0.653,
                 n_causal_diseases=0, gnomad_loeuf=0.881, gnomad_pli=0.200),
}

WIDE_SQL = """
SELECT t.symbol, tw.target_id, tw.clingen_n_strong, tw.mendelian_n, tw.gwas_n_sig,
       tw.ot_genetic_max, tw.ot_somatic_score_max, tw.ot_animal_model_max,
       tw.n_causal_diseases, tw.gnomad_loeuf, tw.gnomad_pli
FROM preclin.v_target_evidence_wide tw
JOIN public.targets t ON t.id = tw.target_id
WHERE t.symbol IN ('IL6R','IL6','CRP');
"""


def repull_from_db():
    """Optional live re-pull (read-only SELECT). Returns dict or None if no DB."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        return None
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        return None
    out = {}
    with psycopg2.connect(url) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(WIDE_SQL)
            for r in cur.fetchall():
                f = lambda v: float(v) if v is not None else None  # noqa: E731
                out[r["symbol"]] = dict(
                    target_id=r["target_id"], clingen_n_strong=r["clingen_n_strong"],
                    mendelian_n=r["mendelian_n"], gwas_n_sig=r["gwas_n_sig"],
                    ot_genetic_max=f(r["ot_genetic_max"]),
                    ot_somatic_score_max=f(r["ot_somatic_score_max"]),
                    ot_animal_model_max=f(r["ot_animal_model_max"]),
                    n_causal_diseases=f(r["n_causal_diseases"]),
                    gnomad_loeuf=f(r["gnomad_loeuf"]), gnomad_pli=f(r["gnomad_pli"]))
    return out or None


def to_evidence(w: dict) -> dict:
    """Same shape as runner.py::row_to_evidence_context (A_genetics slice)."""
    return {"A_genetics": {
        "nelson_tier": None,
        "mendelian_n": w["mendelian_n"],
        "clingen_n_strong": w["clingen_n_strong"],
        "gwas_n_sig": w["gwas_n_sig"],
        "ot_genetic_max": w["ot_genetic_max"],
        "ot_somatic_score_max": w["ot_somatic_score_max"],
    }}


# genetic_only_v1 raw-score tier bands (Melissa's; used in PCSK9_VS_APP_CETP.md):
#   None < 0.1 | Weak 0.1-0.9 | Moderate 1.0-1.3 | Strong >= 1.4
def raw_tier(score: float) -> str:
    if score < 0.1:
        return "None"
    if score < 1.0:
        return "Weak"
    if score < 1.4:
        return "Moderate"
    return "Strong"


def _invert_sigmoid_to_score(p: float) -> float:
    """genetic_only_v1 maps score->p via _sigmoid(score*0.6 - 1.4); invert to
    recover the raw additive genetic score the tier bands are defined on."""
    import math
    x = math.log(p / (1.0 - p))          # logit(p) = score*0.6 - 1.4
    return (x + 1.4) / 0.6


# ------------------------------------------------------------------
# Scorecard content (the causal gates). One cell = (color, top, sub).
# ------------------------------------------------------------------
INK, SEC, MUTED = "#14110f", "#5b544e", "#938b82"
SURFACE, RULE = "#fbfaf8", "#d8d3cb"
GREEN, AMBER, RED, BLUE, GREY = "#2e7d47", "#d99a2b", "#b0322a", "#1f6fd0", "#8a8279"

COLS = ["Human genetics\n(genetic_only_v1)", "Target-biomarker\nlink",
        "Biomarker causal\nfor outcome? (MR)", "Drug engages\ntarget",
        "Safety", "Approval / outcome"]


def build_rows(scores: dict):
    """scores: {symbol: (raw_score, tier)}. Returns figure ROWS."""
    g = lambda s: (GREEN, s[1], f"score {s[0]:.1f}")  # noqa: E731  genetics cell
    return [
        ("CRP", "CRP · cardiovascular",
         g(scores["CRP"]),
         (GREEN, "is the marker", "CRP itself"),
         (RED,   "no", "not causal (MR)"),
         (RED,   "no CV agent", "none cut events"),
         (GREY,  "n/a", ""),
         (RED,   "DEAD END", "no CVD drug")),
        ("IL-6R", "IL6R · cardiovascular / RA",
         g(scores["IL6R"]),
         (GREEN, "validated", "-> CRP / IL-6"),
         (GREEN, "yes", "IL-6R -> CHD (MR)"),
         (GREEN, "yes", "tocilizumab; ziltiv."),
         (GREEN, "acceptable", "approved in RA"),
         (BLUE,  "APPROVED", "RA; CV: ZEUS ph3")),
        ("IL-6", "IL6 · cardiovascular",
         g(scores["IL6"]),
         (GREEN, "validated", "-> CRP"),
         (GREEN, "yes", "IL-6 axis (MR)"),
         (GREEN, "yes", "ziltivekimab"),
         (AMBER, "TBD", "outcomes trial"),
         (AMBER, "IN DEV", "RESCUE ph2 -> ZEUS")),
    ]


def _sans():
    have = {f.name for f in fm.fontManager.ttflist}
    for f in ("Helvetica Neue", "Helvetica", "Arial"):
        if f in have:
            return f
    return "DejaVu Sans"


def plot(rows, clean=False):
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                         "savefig.facecolor": SURFACE, "font.family": _sans(),
                         "text.color": INK, "figure.dpi": 200, "svg.fonttype": "none"})
    n, ncol = len(rows), len(COLS)
    fig, ax = plt.subplots(figsize=(12.4, 3.6 if clean else 4.7))
    fig.subplots_adjust(left=0.16, right=0.99, top=0.80 if clean else 0.58, bottom=0.13)

    yrows = list(range(n - 1, -1, -1))
    cw = 1.0
    for ri, row in enumerate(rows):
        y = yrows[ri]
        for ci, (color, top, sub) in enumerate(row[2:]):
            x = ci * cw
            ax.add_patch(Rectangle((x, y - 0.44), 0.92 * cw, 0.88, facecolor=color,
                                   edgecolor=SURFACE, lw=2, zorder=2))
            ax.text(x + 0.46 * cw, y + (0.11 if sub else 0.0), top, ha="center",
                    va="center", fontsize=10.0, fontweight="bold", color="#fff")
            if sub:
                ax.text(x + 0.46 * cw, y - 0.19, sub, ha="center", va="center",
                        fontsize=7.3, color="#f3efe9")
        ax.text(-0.12, y + 0.12, row[0], ha="right", va="center", fontsize=11,
                fontweight="bold", color=INK)
        ax.text(-0.12, y - 0.18, row[1], ha="right", va="center", fontsize=8.0, color=MUTED)

    ytop = max(yrows)
    for ci, name in enumerate(COLS):
        ax.text(ci * cw + 0.46 * cw, ytop + 0.70, name, ha="center", va="bottom",
                fontsize=8.8, fontweight="bold", color=SEC, linespacing=1.15)

    ax.set_xlim(-1.55, ncol * cw + 0.05)
    ax.set_ylim(-0.95, ytop + 1.15)
    ax.axis("off")

    key = [(GREEN, "holds"), (AMBER, "partial"), (RED, "breaks"),
           (BLUE, "approved"), (GREY, "n/a")]
    for i, (c, lab) in enumerate(key):
        ax.add_patch(Rectangle((i * 0.95, -0.86), 0.26, 0.22, facecolor=c,
                               edgecolor=SURFACE, lw=1.2))
        ax.text(i * 0.95 + 0.32, -0.75, lab, ha="left", va="center", fontsize=7.4, color=MUTED)

    if not clean:
        title = "Same genetics score, one gate decides — CRP is a marker, IL-6R is causal"
        sub = ("CRP and IL-6/IL-6R are all inflammation biomarkers linked to CVD, and the repo's genetic_only_v1 "
               "scorer gives all three the SAME score — genetics alone cannot separate them. They diverge at one "
               "gate: is the biomarker causal for the hard outcome? IL-6R/IL-6 clear it by Mendelian randomisation; "
               "CRP fails it (genetically elevated CRP does not raise CHD risk).")
        src = ("Genetics = genetic_only_v1 on v_target_evidence_wide (present-day; hindsight). "
               "MR: Swerdlow/IL6R-MR Consortium Lancet 2012 (IL-6R causal); CCGC BMJ 2011, Elliott JAMA 2009, "
               "Zacho NEJM 2008 (CRP non-causal). Clinical: CANTOS (NEJM 2017), RESCUE (Lancet 2021).")
        fig.text(0.015, 0.925, title, fontsize=13.5, fontweight="bold", color=INK)
        fig.text(0.015, 0.76, sub, fontsize=9.0, color=SEC, linespacing=1.4)
        fig.add_artist(Line2D([0.015, 0.99], [0.68, 0.68], color=RULE, lw=1,
                              transform=fig.transFigure))
        fig.text(0.015, 0.02, src, fontsize=7.3, color=MUTED, ha="left")

    stem = "il6r_crp_causal_biomarker" + ("_clean" if clean else "")
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=200)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png (200 dpi) + .svg")


def main():
    live = repull_from_db()
    wide = live if live else WIDE
    print("evidence source:", "LIVE DB re-pull" if live else "baked-in (last DB pull, 2026)")

    scores, prov = {}, []
    for sym in ("CRP", "IL6R", "IL6"):
        w = wide[sym]
        res = score_ti("genetic_only_v1", to_evidence(w), {})
        raw = _invert_sigmoid_to_score(res["predicted_p_approval"])
        tier = raw_tier(raw)
        scores[sym] = (raw, tier)
        print(f"  {sym:5} genetic_only_v1 raw={raw:.2f} ({tier})  "
              f"p={res['predicted_p_approval']:.3f}  support={res['top_supporting_dims']}")
        prov.append(dict(
            target=sym, target_id=w["target_id"], genetic_only_v1_raw=round(raw, 2),
            genetic_tier=tier, predicted_p_approval=round(res["predicted_p_approval"], 3),
            clingen_n_strong=w["clingen_n_strong"], mendelian_n=w["mendelian_n"],
            gwas_n_sig=w["gwas_n_sig"], ot_genetic_max=w["ot_genetic_max"],
            ot_animal_model_max=w["ot_animal_model_max"],
            n_causal_diseases=w["n_causal_diseases"], gnomad_loeuf=w["gnomad_loeuf"]))

    pd.DataFrame(prov).to_csv(os.path.join(DATA, "il6r_crp_causal_biomarker.csv"), index=False)
    print("wrote data/il6r_crp_causal_biomarker.csv")

    rows = build_rows(scores)
    plot(rows, clean=False)   # full (title+source) — for review, not committed
    plot(rows, clean=True)    # clean variant — commit this one


if __name__ == "__main__":
    main()
