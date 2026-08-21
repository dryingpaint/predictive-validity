#!/usr/bin/env python3
"""
Section 3/4 bridge figure — the mirror image of the case-study scorecard.

Same rubric (Genetics + Mechanistic + Cell-pathway + Animal in-vivo + Human PD,
0-3 each) as plot_case_scorecard.py, but here the two rows have opposite
genetics status and opposite outcomes:

  - Anti-Abeta mAbs (APP, Alzheimer's) - genetics STRONG, FAILED (from CASE_STUDIES.md)
  - Exenatide (GLP1R, type 2 diabetes) - genetics ABSENT, SUCCEEDED

Every score is time-sliced to what was known when each program actually
started (early-2000s for anti-Abeta; early-to-mid-1990s for exenatide), not
present-day Open Targets/GWAS data - GWAS technology itself postdates
exenatide's approval (2005), so scoring "genetics" with today's data would
be the same hindsight leakage already excluded from the Section 2 figures.
Sources are in analyses/GENETICS_MIRROR.md.

Saves data/genetics_mirror.csv for provenance.
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm, cm
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
CURATED = os.path.join(HERE, "..", "data")
FIGDIR = os.path.join(HERE, "..", "data")
os.makedirs(FIGDIR, exist_ok=True)
os.makedirs(CURATED, exist_ok=True)

INK, SEC, MUTED = "#14110f", "#5b544e", "#938b82"
SURFACE, RULE, NA = "#fbfaf8", "#d8d3cb", "#e6e3dd"
FAILRED = "#b0322a"
SUCCESSBLUE = "#1f6fd0"

COLS = ["Genetics", "Mechanistic", "Cell-pathway", "Animal in-vivo", "Human PD"]

# (drug, target/era, genetics_0_3, gen_tier, mech, cell, animal, pd, outcome_label, outcome_kind)
CASES = [
    ("Anti-Aβ mAbs (sola/bapi)", "APP · Alzheimer's — program start ~2000s",
     3, "Strong", 3, 3, 3, 2, "FAILED", "fail"),
    ("Exenatide (Byetta)", "GLP1R · type 2 diabetes — program start ~1990s",
     0, "Absent", 2, 2, 3, 3, "SUCCESS", "success"),
]


def _sans():
    have = {f.name for f in fm.fontManager.ttflist}
    for f in ("Helvetica Neue", "Helvetica", "Arial"):
        if f in have:
            return f
    return "DejaVu Sans"


def plot(clean=False):
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                         "savefig.facecolor": SURFACE, "font.family": _sans(),
                         "text.color": INK, "figure.dpi": 300, "svg.fonttype": "none"})
    cmap = cm.get_cmap("RdYlGn"); norm = Normalize(0, 3)
    n = len(CASES)
    out_x = len(COLS)
    fig, ax = plt.subplots(figsize=(10.2, 3.2 if clean else 4.0))
    fig.subplots_adjust(left=0.235, right=0.985, top=0.80 if clean else 0.64, bottom=0.14)

    yrows = [1.0, 0.0]
    for ri, c in enumerate(CASES):
        y = yrows[ri]
        vals = [c[2], c[4], c[5], c[6], c[7]]
        for ci, val in enumerate(vals):
            face = cmap(norm(val))
            ax.add_patch(Rectangle((ci, y - 0.44), 0.92, 0.88, facecolor=face,
                                   edgecolor=SURFACE, lw=2, zorder=2))
            if ci == 0:
                ax.text(ci + 0.46, y, c[3], ha="center", va="center", fontsize=9,
                        fontweight="bold", color=INK if val >= 2 else "#fff")
            else:
                ax.text(ci + 0.46, y, str(val), ha="center", va="center", fontsize=11,
                        fontweight="bold", color=INK)
        outcome_color = FAILRED if c[9] == "fail" else SUCCESSBLUE
        ax.add_patch(Rectangle((out_x, y - 0.44), 1.35, 0.88, facecolor=outcome_color,
                               edgecolor=SURFACE, lw=2, zorder=2))
        ax.text(out_x + 0.675, y, c[8], ha="center", va="center", fontsize=10.5,
                fontweight="bold", color="#fff")
        ax.text(-0.15, y + 0.12, c[0], ha="right", va="center", fontsize=10.5, fontweight="bold", color=INK)
        ax.text(-0.15, y - 0.18, c[1], ha="right", va="center", fontsize=8.5, color=MUTED)

    for ci, name in enumerate(COLS):
        ax.text(ci + 0.46, 1.72, name, ha="center", va="bottom",
                fontsize=9.5, fontweight="bold", color=SEC)
    ax.text(out_x + 0.675, 1.72, "Outcome", ha="center", va="bottom",
            fontsize=9.5, fontweight="bold", color=SEC)

    ax.set_xlim(-2.0, out_x + 1.75); ax.set_ylim(-0.85, 2.05)
    ax.axis("off")
    for i, (lab, v) in enumerate([("absent 0", 0), ("1", 1), ("2", 2), ("strong 3", 3)]):
        ax.add_patch(Rectangle((0.3 + i * 0.9, -0.72), 0.5, 0.24, facecolor=cmap(norm(v)),
                               edgecolor=SURFACE, lw=1.5))
        ax.text(0.55 + i * 0.9, -0.78, lab, ha="center", va="top", fontsize=7.5, color=MUTED)

    if not clean:
        title = "Same evidence rubric, opposite result"
        sub = ("Scored against the mechanistic / cell / animal / human-PD rubric plus a genetics column "
               "(genetic_only_v1), using evidence available at each program's OWN start — not present-day "
               "data. Anti-Aβ antibodies had strong human genetics and failed on the causal hypothesis; "
               "exenatide had none and succeeded on convergent mechanistic + animal + human-PD evidence.")
        src = "Anti-Aβ scores from CASE_STUDIES.md. Exenatide scores + sources in GENETICS_MIRROR.md."
        fig.text(0.035, 0.90, title, fontsize=15, fontweight="bold", color=INK)
        fig.text(0.035, 0.77, sub, fontsize=9.5, color=SEC, linespacing=1.4)
        fig.add_artist(Line2D([0.035, 0.985], [0.685, 0.685], color=RULE, lw=1, transform=fig.transFigure))
        fig.text(0.035, 0.025, src, fontsize=8, color=MUTED, ha="left")

    stem = "genetics_mirror" + ("_clean" if clean else "")
    fig.savefig(os.path.join(FIGDIR, stem + ".png"), bbox_inches="tight", dpi=600)
    fig.savefig(os.path.join(FIGDIR, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png (600 dpi) + .svg")


def main():
    pd.DataFrame([{"drug": c[0], "target_era": c[1], "genetics_0_3": c[2], "genetic_tier": c[3],
                   "mechanistic": c[4], "cell_pathway": c[5], "animal_invivo": c[6], "human_pd": c[7],
                   "outcome": c[8]} for c in CASES]).to_csv(
        os.path.join(CURATED, "genetics_mirror.csv"), index=False)
    plot(clean=False)
    plot(clean=True)


if __name__ == "__main__":
    main()
