#!/usr/bin/env python3
"""
Section 2, part 1 — predictive power of each evidence flavor, individually.

Reads data/relative_success_by_dimension.csv (from preclin.v_relative_success_clean:
Relative Success = approval rate WITH vs WITHOUT each evidence type, over Phase 2+
target-indication pairs). Adds a bootstrap CI on each RS and renders a forest plot
grouped by evidence family, colored by whether the flavor is a significant
positive / null / negative predictor of approval.

RS and the 2x2 counts come verbatim from her view; only the CI + plot are added.
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
CURATED = os.path.join(HERE, "..", "data")
FIGDIR = os.path.join(HERE, "..", "data")
os.makedirs(FIGDIR, exist_ok=True)

INK, SEC, MUTED = "#14110f", "#5b544e", "#938b82"
SURFACE, RULE, GRID, AXLINE = "#fbfaf8", "#d8d3cb", "#ece8e1", "#c3bcb2"
POS, NEG, NULLC = "#1f6fd0", "#e2673a", "#b4ada3"   # predicts approval / failure / null

RNG = np.random.default_rng(7)
N_BOOT = 4000

FAM_ORDER = ["A_genetics", "B_mechanistic", "C_cell", "D_animal", "E_pd", "H_safety", "I_landscape"]
FAM_NAME = {
    "A_genetics": "Human genetics", "B_mechanistic": "Mechanistic / tractability",
    "C_cell": "Cell", "D_animal": "Animal", "E_pd": "Human PD engagement",
    "H_safety": "Safety / constraint", "I_landscape": "Landscape / precedent",
}


def _sans():
    have = {f.name for f in fm.fontManager.ttflist}
    for f in ("Helvetica Neue", "Helvetica", "Arial"):
        if f in have:
            return f
    return "DejaVu Sans"


def rs_ci(a, b, c, d):
    """Relative success (a/(a+b))/(c/(c+d)) with bootstrap 95% CI over the 2x2."""
    n_sup, n_not = a + b, c + d
    rs = (a / n_sup) / (c / n_not)
    cells = np.array([a, b, c, d], float)
    draws = RNG.multinomial(int(cells.sum()), cells / cells.sum(), size=N_BOOT).astype(float)
    aa, bb, cc, dd = draws.T
    with np.errstate(divide="ignore", invalid="ignore"):
        boot = (aa / (aa + bb)) / (cc / (cc + dd))
    boot = boot[np.isfinite(boot)]
    return rs, float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def plot_genetics_dose_response(clean=False):
    """Approval rate binned by Melissa's exact genetic_only_v1 score."""
    df = pd.read_csv(os.path.join(CURATED, "genetics_dose_response.csv"))
    colors = ["#b9b7af", "#9ec5f4", "#3987e5", "#12467e"]   # none -> strong (sequential)
    fig, ax = plt.subplots(figsize=(8.2, 5.0) if clean else (8.2, 5.4))
    fig.subplots_adjust(left=0.12, right=0.96, top=0.955 if clean else 0.78, bottom=0.13 if clean else 0.17)
    xs = list(range(len(df)))
    for i, (_, r) in enumerate(df.iterrows()):
        ax.bar(i, r.approval, 0.62, color=colors[i], zorder=3)
        ax.plot([i, i], [r.lo, r.hi], color=INK, lw=1.6, zorder=4, solid_capstyle="round")
        ax.text(i, r.hi + 1.0, f"{r.approval:.0f}%", ha="center", va="bottom",
                fontsize=14, fontweight="bold", color=INK)
    ax.set_xticks(xs); ax.set_xticklabels(df.tier, fontsize=11 if clean else 10, color=INK)
    ax.set_ylim(0, 50); ax.set_yticks([0, 10, 20, 30, 40])
    ax.set_yticklabels(["0", "10", "20", "30", "40"])
    ax.set_ylabel("Programs approved (%)", color=SEC, fontsize=11)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    for yv in [10, 20, 30, 40]:
        ax.axhline(yv, color=GRID, lw=0.6, zorder=0)
    if not clean:
        fig.text(0.035, 0.925, "Approval rate by strength of genetic evidence",
                 fontsize=16, fontweight="bold", color=INK)
        fig.text(0.035, 0.855,
                 "Binned by Melissa Du's genetic_only_v1 score (ClinGen / Mendelian / OT-genetic / somatic), "
                 "8,179 Phase 2+ pairs. Error bars 95% CI.", fontsize=10.5, color=SEC)
        fig.add_artist(Line2D([0.035, 0.965], [0.83, 0.83], color=RULE, lw=1, transform=fig.transFigure))
        fig.text(0.035, 0.02,
                 "Source: Melissa Du predictive-validity benchmark — her exact genetic_only_v1 additive scorer. "
                 "Strong (score ≥ 1.4) approves ≈ 6× the no-evidence rate.",
                 fontsize=8, color=MUTED, ha="left")
    stem = "genetics_dose_response" + ("_clean" if clean else "")
    fig.savefig(os.path.join(FIGDIR, stem + ".png"), bbox_inches="tight", dpi=600)
    fig.savefig(os.path.join(FIGDIR, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png (600 dpi) + .svg")


def plot_category_ablation(clean=False):
    """Category importance from Melissa's leave-one-category-out ablation (her numbers)."""
    df = pd.read_csv(os.path.join(CURATED, "category_ablation.csv"))
    df["importance"] = -df.delta_auc_pp                 # AUC lost when category removed
    df = df.sort_values("importance")                  # smallest at bottom -> genetics on top
    fig, ax = plt.subplots(figsize=(9.0, 5.0) if clean else (9.2, 5.6))
    fig.subplots_adjust(left=0.32, right=0.92, top=0.955 if clean else 0.79, bottom=0.12)
    ys = list(range(len(df)))
    for yy, (_, r) in zip(ys, df.iterrows()):
        col = POS if r.importance >= 5 else NULLC
        ax.barh(yy, r.importance, height=0.6, color=col, zorder=3)
        ax.text(r.importance + 0.3, yy, f"{r.importance:.1f}" if r.importance >= 0.05 else "0.0",
                va="center", ha="left", fontsize=10.5, fontweight="bold", color=INK)
    ax.set_xlim(0, 20)
    ax.set_yticks(ys); ax.set_yticklabels(df.category, fontsize=11.5 if clean else 11, color=INK)
    ax.set_ylim(-0.6, len(df) - 0.4)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    for xv in [5, 10, 15]:
        ax.axvline(xv, color=GRID, lw=0.6, zorder=0)
    ax.set_xticks([0, 5, 10, 15]); ax.set_xticklabels(["0", "5", "10", "15"], color=MUTED)
    ax.set_xlabel("AUC lost when the category is removed  (percentage points)", color=SEC, fontsize=11)
    if not clean:
        fig.text(0.035, 0.925, "What the trained model actually relies on: genetics",
                 fontsize=16, fontweight="bold", color=INK)
        fig.text(0.035, 0.855,
                 "Leave-one-category-out from the full model (Melissa Du's ablation; strict Phase 2+, LogReg, "
                 "full AUC 0.829). Cell & animal literature add ≈ 0 on top of genetics.", fontsize=10.5, color=SEC)
        fig.add_artist(Line2D([0.035, 0.965], [0.83, 0.83], color=RULE, lw=1, transform=fig.transFigure))
        fig.text(0.035, 0.02,
                 "Source: Melissa Du predictive-validity benchmark — analyses/ablation.py (RESULTS.md). "
                 "Multivariate: importance = AUC drop, not univariate association.",
                 fontsize=8, color=MUTED, ha="left")
    stem = "category_ablation" + ("_clean" if clean else "")
    fig.savefig(os.path.join(FIGDIR, stem + ".png"), bbox_inches="tight", dpi=600)
    fig.savefig(os.path.join(FIGDIR, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png (600 dpi) + .svg")


def main():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": _sans(), "text.color": INK, "figure.dpi": 300, "svg.fonttype": "none",
    })
    df = pd.read_csv(os.path.join(CURATED, "relative_success_by_dimension.csv"))
    df = df[df.relative_success.notna() & (df.n_supported > 0)].copy()
    df = df[~df.dimension.str.contains("Line C|Line D|Line E")]   # drop LLM-extracted lit from headline
    df["a"] = df.n_supported_approved
    df["b"] = df.n_supported - df.n_supported_approved
    df["c"] = df.n_not_supported_approved
    df["d"] = df.n_not_supported - df.n_not_supported_approved
    cis = df.apply(lambda r: rs_ci(r.a, r.b, r.c, r.d), axis=1, result_type="expand")
    df[["rs", "lo", "hi"]] = cis
    stripped = df.dimension.str.replace(r"^[A-Z]\.\s*", "", regex=True)
    LABEL_MAP = {
        "Line C lit high (≥2)": "Cell-pathway literature ≥2",
        "Line D lit high (≥2)": "Animal in-vivo literature ≥2",
        "Line E lit high (≥2)": "Human PD-engagement lit ≥2",
        "SC Tau ≥0.75": "Tissue-specific, single-cell ≥0.75",
        "Bulk Tau ≥0.75": "Tissue-specific, bulk ≥0.75",
        "OT somatic ≥0.3": "OT somatic (cancer) ≥0.3",
        "GO-BP ≥20 terms": "GO biological-process ≥20",
        "PPI hub (≥50 partners)": "PPI hub ≥50 partners",
        "Causal disease pleiotropy ≥3": "Causal-disease pleiotropy ≥3",
    }
    df["label"] = stripped.map(lambda s: LABEL_MAP.get(s, s))

    # build positions top->down: each family gets its own header row, then its dims (RS desc)
    rows, ticks, ticklab, headers = [], [], [], []
    yc = 0.0
    for fam in FAM_ORDER:
        sub = df[df.category == fam].sort_values("rs", ascending=False)
        if sub.empty:
            continue
        headers.append((yc, FAM_NAME[fam]))
        yc -= 1.15
        for _, r in sub.iterrows():
            rows.append((r, yc)); ticks.append(yc); ticklab.append(r.label); yc -= 1.0
        yc -= 0.55
    ybot = yc + 0.4

    for clean in (False, True):
        fig, ax = plt.subplots(figsize=(9.8, 11.6) if clean else (9.8, 12.2))
        fig.subplots_adjust(left=0.33, right=0.82, top=0.965 if clean else 0.90,
                            bottom=0.075 if clean else 0.105)
        for r, yy in rows:
            col = POS if r.lo > 1 else (NEG if r.hi < 1 else NULLC)
            ax.plot([r.lo, r.hi], [yy, yy], color=col, lw=2.4, solid_capstyle="round", zorder=2)
            ax.plot(r.rs, yy, "o", color=col, ms=8.5, mec=SURFACE, mew=1.3, zorder=3)
            ax.text(2.62, yy, f"{r.rs:.2f}", va="center", ha="left", fontsize=9.5,
                    fontweight="bold", color=INK)
        ax.axvline(1, color=AXLINE, lw=1.3, zorder=1)
        ax.set_xscale("log"); ax.set_xlim(0.13, 2.6)
        ax.set_xticks([0.2, 0.35, 0.5, 0.7, 1, 1.4, 2]); ax.set_xticklabels(["0.2","0.35","0.5","0.7","1","1.4","2"])
        for x in ax.get_xticks():
            ax.axvline(x, color=GRID, lw=0.6, zorder=0)
        ax.set_yticks(ticks); ax.set_yticklabels(ticklab, fontsize=10, color=INK)
        ax.set_ylim(ybot, 1.0)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.tick_params(length=0)
        for yy, name in headers:
            ax.text(-0.31, yy, name.upper(), transform=ax.get_yaxis_transform(),
                    fontsize=9, fontweight="bold", color=SEC, va="center", ha="left")
        ax.set_xlabel("Relative success — approval rate with ÷ without the evidence  (log scale)",
                      color=SEC, fontsize=10)
        handles = [Patch(color=POS, label="Predicts approval (CI > 1)"),
                   Patch(color=NULLC, label="No clear signal (CI spans 1)"),
                   Patch(color=NEG, label="Predicts failure (CI < 1)")]
        leg = fig.legend(handles=handles, loc="lower center",
                         bbox_to_anchor=(0.5, 0.02 if clean else 0.045),
                         ncol=3, frameon=False, fontsize=9.5, columnspacing=2.0,
                         handlelength=1.0, handleheight=1.0)
        for t in leg.get_texts():
            t.set_color(SEC)
        if not clean:
            fig.text(0.035, 0.945, "How much each kind of evidence moves the odds of approval",
                     fontsize=17, fontweight="bold", color=INK, ha="left")
            fig.text(0.035, 0.905,
                     "Relative success of each evidence type on its own, across Phase 2+ target–indication pairs. "
                     "95% bootstrap CI.", fontsize=10.5, color=SEC, ha="left")
            fig.add_artist(Line2D([0.035, 0.965], [0.885, 0.885], color=RULE, lw=1, transform=fig.transFigure))
            fig.text(0.035, 0.010,
                     "Source: Melissa Du predictive-validity benchmark — preclin.v_relative_success_clean "
                     "(placebos filtered, canonical sponsors). Each flavor measured over its own available pairs. "
                     "Line B–E are LLM-extracted literature scores.", fontsize=8, color=MUTED, ha="left")
        stem = "predictive_power_by_evidence" + ("_clean" if clean else "")
        fig.savefig(os.path.join(FIGDIR, stem + ".png"), bbox_inches="tight", dpi=600)
        fig.savefig(os.path.join(FIGDIR, stem + ".svg"), bbox_inches="tight")
        plt.close(fig)
        print(f"wrote data/{stem}.png (600 dpi) + .svg")
    plot_genetics_dose_response(); plot_genetics_dose_response(clean=True)
    plot_category_ablation(); plot_category_ablation(clean=True)


if __name__ == "__main__":
    main()
