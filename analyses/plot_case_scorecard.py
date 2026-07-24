#!/usr/bin/env python3
"""
Section 3 figure — evidence scorecard for drugs with strong preclinical evidence that FAILED.

Rows: the six case studies from Melissa's CASE_STUDIES.md, split into efficacy failures
and safety / species-specific failures. Columns: the evidence categories, with GENETICS
added (her CASE_STUDIES.md rubric omitted it) — scored from her DB via her own
genetic_only_v1 scorer on the target. Cells coloured by evidence strength; final column =
clinical outcome (all FAILED).

The point: mechanistic / cell / animal / PD scores are maxed across the board, yet every
drug failed — and genetics (the one category that predicts, per §2) was only moderate,
weak, or (CETP) misleading. Genetics improves odds; it does not guarantee success.

Reads/writes nothing from the DB (scores are baked in from CASE_STUDIES.md + the
genetic_only_v1 values pulled once). Saves data/case_scorecard.csv for provenance.
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

# columns of evidence (0-3); genetics carries a tier label too
COLS = ["Genetics", "Mechanistic", "Cell-pathway", "Animal in-vivo", "Human PD"]

# (drug, target·indication, group, genetics_display_0_3, gen_tier, mech, cell, animal, pd, outcome)
# NOTE: element [3] is a 0-3 value used only to drive the figure's cell colour intensity.
# The REAL underlying score is the genetic_only_v1 raw score in GENETIC_ONLY_V1 below,
# which is what the tier labels and the accompanying doc quote — that raw score is what
# gets written to the provenance CSV (see main()).
CASES = [
    ("BACE1 inhibitors",           "BACE1 · Alzheimer's",   "efficacy", 2, "Moderate",  3, 3, 3, 3,   "efficacy"),
    ("γ-secretase (semagacestat)", "PSEN1 · Alzheimer's",   "efficacy", 2, "Moderate",  3, 3, 3, 3,   "efficacy"),
    ("Anti-Aβ mAbs (sola/bapi)",   "APP · Alzheimer's",     "efficacy", 3, "Strong",    3, 3, 3, 2,   "efficacy"),
    ("Torcetrapib (CETP)",         "CETP · cardiovascular", "efficacy", 1, "Weak*",     3, 3, 3, 3,   "efficacy"),
    ("TGN1412 (CD28 superagonist)","CD28 · Phase 1",        "safety",   2, "Moderate",  3, 3, 3, None, "safety"),
    ("Fialuridine (FIAU)",         "HBV pol · hepatitis B", "safety",   None, "n/a",     3, 2, 3, None, "safety"),
]

# Real genetic_only_v1 raw scores, pulled from preclin.v_target_evidence_wide via the
# repo's own scorer (benchmark/scorers_rule_based.py::scorer_genetic_only). These are the
# numbers the tier labels and CASE_SCORECARD.md quote. HBV polymerase is viral (n/a).
GENETIC_ONLY_V1 = {
    "BACE1 inhibitors": 1.0,
    "γ-secretase (semagacestat)": 1.0,
    "Anti-Aβ mAbs (sola/bapi)": 1.6,
    "Torcetrapib (CETP)": 0.7,
    "TGN1412 (CD28 superagonist)": 1.0,
    "Fialuridine (FIAU)": None,
}


def _sans():
    have = {f.name for f in fm.fontManager.ttflist}
    for f in ("Helvetica Neue", "Helvetica", "Arial"):
        if f in have:
            return f
    return "DejaVu Sans"


def plot(with_genetics=True, clean=False):
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                         "savefig.facecolor": SURFACE, "font.family": _sans(),
                         "text.color": INK, "figure.dpi": 300, "svg.fonttype": "none"})
    cmap = cm.get_cmap("RdYlGn"); norm = Normalize(0, 3)
    n = len(CASES)
    cols = COLS if with_genetics else COLS[1:]                 # drop Genetics column for "hers"
    out_x = len(cols)
    w = 11.0 if with_genetics else 9.7
    fig, ax = plt.subplots(figsize=(w, 5.0) if clean else (w, 6.0))
    left = 0.235 if with_genetics else 0.275
    fig.subplots_adjust(left=left, right=0.985, top=0.905 if clean else 0.74, bottom=0.10)

    groups = [c[2] for c in CASES]
    ygap, yrows, yy = 0.55, [], 0.0
    for i in range(n - 1, -1, -1):
        yrows.append(yy); yy += 1.0
        if i > 0 and groups[i] != groups[i - 1]:
            yy += ygap
    yrows = yrows[::-1]

    for ri, c in enumerate(CASES):
        y = yrows[ri]
        vals = [c[3], c[5], c[6], c[7], c[8]] if with_genetics else [c[5], c[6], c[7], c[8]]
        for ci, val in enumerate(vals):
            face = NA if val is None else cmap(norm(val))
            ax.add_patch(Rectangle((ci, y - 0.44), 0.92, 0.88, facecolor=face,
                                   edgecolor=SURFACE, lw=2, zorder=2))
            if with_genetics and ci == 0:                      # genetics: tier word
                ax.text(ci + 0.46, y, c[4], ha="center", va="center", fontsize=9,
                        fontweight="bold", color=INK if val and val >= 2 else "#3a3632")
            elif val is not None:
                ax.text(ci + 0.46, y, str(val), ha="center", va="center", fontsize=11,
                        fontweight="bold", color=INK)
            else:
                ax.text(ci + 0.46, y, "—", ha="center", va="center", fontsize=11, color=MUTED)
        ax.add_patch(Rectangle((out_x, y - 0.44), 1.35, 0.88, facecolor=FAILRED,
                               edgecolor=SURFACE, lw=2, zorder=2))
        ax.text(out_x + 0.675, y + 0.11, "FAILED", ha="center", va="center", fontsize=10,
                fontweight="bold", color="#fff")
        ax.text(out_x + 0.675, y - 0.17, c[9], ha="center", va="center", fontsize=8, color="#f4d6d3")
        ax.text(-0.15, y + 0.12, c[0], ha="right", va="center", fontsize=10.5, fontweight="bold", color=INK)
        ax.text(-0.15, y - 0.18, c[1], ha="right", va="center", fontsize=8.5, color=MUTED)

    ytop = max(yrows)
    for ci, name in enumerate(cols):
        ax.text(ci + 0.46, ytop + 0.72, name, ha="center", va="bottom",
                fontsize=9.5, fontweight="bold", color=SEC)
    ax.text(out_x + 0.675, ytop + 0.72, "Outcome", ha="center", va="bottom",
            fontsize=9.5, fontweight="bold", color=SEC)

    eff_ys = [yrows[i] for i in range(n) if CASES[i][2] == "efficacy"]
    saf_ys = [yrows[i] for i in range(n) if CASES[i][2] == "safety"]
    ax.text(-1.95, np.mean(eff_ys), "EFFICACY\nFAILURES", ha="left", va="center",
            fontsize=8.5, fontweight="bold", color=MUTED)
    ax.text(-1.95, np.mean(saf_ys), "SAFETY /\nSPECIES", ha="left", va="center",
            fontsize=8.5, fontweight="bold", color=MUTED)

    ax.set_xlim(-2.0, out_x + 1.75); ax.set_ylim(-1.15, ytop + 1.15)
    ax.axis("off")
    for i, (lab, v) in enumerate([("absent 0", 0), ("1", 1), ("2", 2), ("strong 3", 3)]):
        ax.add_patch(Rectangle((0.3 + i * 0.9, -0.95), 0.5, 0.26, facecolor=cmap(norm(v)),
                               edgecolor=SURFACE, lw=1.5))
        ax.text(0.55 + i * 0.9, -1.02, lab, ha="center", va="top", fontsize=7.5, color=MUTED)

    if not clean:
        if with_genetics:
            title = "A maxed-out preclinical scorecard did not stop these drugs failing"
            sub = ("Six drugs with strong mechanistic / cell / animal / PD evidence that failed in humans. "
                   "Genetics (added here from Melissa Du's genetic_only_v1) is the one column that varies — "
                   "and even the well-supported ones failed.")
            src = ("Preclinical scores from CASE_STUDIES.md; genetics from her DB (target-level). "
                   "*CETP: genetics weak AND misleading — Mendelian randomization later showed HDL is not causal.")
        else:
            title = "Strong preclinical evidence — every one still failed"
            sub = ("The six case studies on the original rubric (mechanistic / cell / animal / PD). "
                   "All scored near-maximal, all failed in humans — but the rubric never scored human genetics.")
            src = "Preclinical scores from Melissa Du's CASE_STUDIES.md rubric."
        fig.text(0.035, 0.925, title, fontsize=15.5, fontweight="bold", color=INK)
        fig.text(0.035, 0.845, sub, fontsize=10, color=SEC, linespacing=1.4)
        fig.add_artist(Line2D([0.035, 0.985], [0.795, 0.795], color=RULE, lw=1, transform=fig.transFigure))
        fig.text(0.035, 0.02, src, fontsize=8, color=MUTED, ha="left")
    stem = ("case_scorecard_genetics" if with_genetics else "case_scorecard_hers") + ("_clean" if clean else "")
    fig.savefig(os.path.join(FIGDIR, stem + ".png"), bbox_inches="tight", dpi=600)
    fig.savefig(os.path.join(FIGDIR, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png (600 dpi) + .svg")


def main():
    pd.DataFrame([{"drug": c[0], "target": c[1], "group": c[2],
                   "genetic_only_v1": GENETIC_ONLY_V1[c[0]], "genetic_tier": c[4],
                   "genetics_display_0_3": c[3], "mechanistic": c[5], "cell_pathway": c[6],
                   "animal_invivo": c[7], "human_pd": c[8], "outcome": "FAILED (%s)" % c[9]}
                  for c in CASES]).to_csv(os.path.join(CURATED, "case_scorecard.csv"), index=False)
    for wg in (False, True):
        plot(with_genetics=wg, clean=False)
        plot(with_genetics=wg, clean=True)


if __name__ == "__main__":
    main()
