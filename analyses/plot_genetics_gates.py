#!/usr/bin/env python3
"""
Genetics protects the FIRST gates of the causal chain — execution and safety are
separate gates it doesn't cover. Two figures, both comparing new cases to PCSK9:

  1. causal_gates_scorecard — PCSK9 (success anchor), ANGPTL3 (2nd success),
     Factor XI (asundexian), APOC3 (volanesorsen) across six gates:
     genetics → target-biomarker link → biomarker causal? → drug engaged target? →
     safety → outcome. All four clear the genetics + causal gates; PCSK9 & ANGPTL3
     clear all six (approved); Factor XI breaks at drug-engagement (dose/indication);
     APOC3 breaks at safety (thrombocytopenia).

  2. genetics_vs_outcome — genetic_only_v1 score for the whole case library,
     coloured by outcome. The point: the approvals sit right among the failures at
     the same or lower score — genetic strength does not separate approved from
     failed; the downstream gates do.

Scores are genetic_only_v1 on preclin.v_target_evidence_wide (present-day; hindsight —
see GENETICS_GATES_ANGPTL3_FXI_APOC3.md). Baked in; no DB needed to plot. Writes
data/genetics_gates_cases.csv for provenance.
"""
from __future__ import annotations
import os
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

INK, SEC, MUTED = "#14110f", "#5b544e", "#938b82"
SURFACE, RULE = "#fbfaf8", "#d8d3cb"
GREEN, AMBER, RED, BLUE, PURPLE = "#2e7d47", "#d99a2b", "#b0322a", "#1f6fd0", "#7a4fa3"

# --- Figure 1: causal-gate scorecard ------------------------------------------
GATES = ["Human genetics", "Target-biomarker\nlink", "Biomarker\ncausal?",
         "Drug engaged\ntarget?", "Safety /\ntolerability", "Outcome"]

# each cell = (color, top_label, sub_label)
GATE_ROWS = [
    ("Anti-PCSK9 mAbs", "PCSK9 · cardiovascular",
     [(GREEN, "Moderate", "1.3"), (GREEN, "yes", "LDL"), (GREEN, "yes", "LDL (MR)"),
      (GREEN, "yes", "LDL cut ~60%"), (GREEN, "clean", ""), (BLUE, "APPROVED", "2015")]),
    ("Evinacumab (ANGPTL3)", "ANGPTL3 · HoFH",
     [(GREEN, "Moderate", "1.3"), (GREEN, "yes", "LDL/TG"), (GREEN, "yes", "lipids"),
      (GREEN, "yes", "LDL cut ~49%"), (GREEN, "clean", ""), (BLUE, "APPROVED", "2021")]),
    ("Asundexian (Factor XI)", "F11 · atrial fibrillation",
     [(GREEN, "Moderate", "1.3"), (GREEN, "yes", "clotting"), (GREEN, "yes", "less stroke"),
      (RED, "no", "dose too low?"), (GREEN, "less bleeding", "thesis held"),
      (RED, "HALTED", "OCEANIC-AF")]),
    ("Volanesorsen (APOC3)", "APOC3 · FCS",
     [(GREEN, "Weak*", "0.7 — undervalued"), (GREEN, "yes", "TG"), (GREEN, "yes", "TG/TRL"),
      (GREEN, "yes", "TG cut ~70%"), (RED, "thrombocytopenia", "76% of pts"),
      (AMBER, "EMA yes", "FDA no")]),
]

# --- Figure 2: genetics score vs outcome (whole case library) -----------------
# (label, target, score, outcome_category)
LIB = [
    ("Anti-Aβ mAbs",       "APP",     1.6, "failed"),
    ("Anti-PCSK9 mAbs",    "PCSK9",   1.3, "approved"),
    ("Evinacumab",         "ANGPTL3", 1.3, "approved"),
    ("Asundexian",         "F11",     1.3, "failed"),
    ("BACE1 inhibitors",   "BACE1",   1.0, "failed"),
    ("Pelacarsen/olpasiran","LPA",    1.0, "pending"),
    ("Torcetrapib",        "CETP",    0.7, "failed"),
    ("Volanesorsen",       "APOC3",   0.7, "mixed"),
    ("Darapladib",         "PLA2G7",  0.5, "failed"),
]
OUTCOME_COLOR = {"approved": BLUE, "failed": RED, "pending": AMBER, "mixed": PURPLE}
OUTCOME_LABEL = {"approved": "approved", "failed": "failed", "pending": "pending", "mixed": "EMA yes / FDA no"}


def _sans():
    have = {f.name for f in fm.fontManager.ttflist}
    for f in ("Helvetica Neue", "Helvetica", "Arial"):
        if f in have:
            return f
    return "DejaVu Sans"


def _rc():
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                         "savefig.facecolor": SURFACE, "font.family": _sans(),
                         "text.color": INK, "figure.dpi": 200, "svg.fonttype": "none"})


def plot_gates(clean=False):
    _rc()
    n = len(GATE_ROWS)
    ncol = len(GATES)
    fig, ax = plt.subplots(figsize=(12.6, 4.0 if clean else 5.0))
    fig.subplots_adjust(left=0.175, right=0.995, top=0.82 if clean else 0.62, bottom=0.12)
    yrows = list(range(n - 1, -1, -1))
    for ri, (drug, sub, cells) in enumerate(GATE_ROWS):
        y = yrows[ri]
        for ci, (color, top, subl) in enumerate(cells):
            ax.add_patch(Rectangle((ci, y - 0.44), 0.92, 0.88, facecolor=color,
                                   edgecolor=SURFACE, lw=2, zorder=2))
            ax.text(ci + 0.46, y + (0.10 if subl else 0.0), top, ha="center", va="center",
                    fontsize=9.6, fontweight="bold", color="#fff")
            if subl:
                ax.text(ci + 0.46, y - 0.20, subl, ha="center", va="center",
                        fontsize=7.0, color="#f3efe9")
        ax.text(-0.14, y + 0.12, drug, ha="right", va="center", fontsize=10.2,
                fontweight="bold", color=INK)
        ax.text(-0.14, y - 0.18, sub, ha="right", va="center", fontsize=8.1, color=MUTED)
    ytop = max(yrows)
    for ci, name in enumerate(GATES):
        ax.text(ci + 0.46, ytop + 0.70, name, ha="center", va="bottom",
                fontsize=8.8, fontweight="bold", color=SEC, linespacing=1.15)
    ax.set_xlim(-1.95, ncol + 0.05)
    ax.set_ylim(-0.95, ytop + 1.15)
    ax.axis("off")
    key = [(GREEN, "holds"), (AMBER, "mixed"), (RED, "breaks"), (BLUE, "approved")]
    for i, (c, lab) in enumerate(key):
        ax.add_patch(Rectangle((i * 1.05, -0.86), 0.30, 0.22, facecolor=c, edgecolor=SURFACE, lw=1.2))
        ax.text(i * 1.05 + 0.38, -0.75, lab, ha="left", va="center", fontsize=7.4, color=MUTED)
    if not clean:
        title = "Genetics guards the first three gates — execution and safety are separate"
        sub = ("All four targets clear the genetics and causal gates. PCSK9 and ANGPTL3 clear all six and are approved. "
               "Factor XI breaks at drug engagement (asundexian under-dosed for AF); APOC3 breaks at safety "
               "(thrombocytopenia) despite working on triglycerides.")
        src = ("Genetics = genetic_only_v1 on v_target_evidence_wide (present-day; hindsight). "
               "*APOC3 genetics is strong (LoF-protective) but the scorer undervalues quantitative-trait genetics — see doc.")
        fig.text(0.015, 0.925, title, fontsize=14.5, fontweight="bold", color=INK)
        fig.text(0.015, 0.80, sub, fontsize=9.2, color=SEC, linespacing=1.4)
        fig.add_artist(Line2D([0.015, 0.995], [0.72, 0.72], color=RULE, lw=1, transform=fig.transFigure))
        fig.text(0.015, 0.02, src, fontsize=7.4, color=MUTED, ha="left")
    stem = "causal_gates_scorecard" + ("_clean" if clean else "")
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=200)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png (200 dpi) + .svg")


def plot_score_vs_outcome(clean=False):
    _rc()
    rows = sorted(LIB, key=lambda r: r[2])          # ascending so highest at top
    n = len(rows)
    fig, ax = plt.subplots(figsize=(9.2, 4.2 if clean else 5.2))
    fig.subplots_adjust(left=0.28, right=0.82, top=0.86 if clean else 0.66, bottom=0.11)
    for i, (label, tgt, score, outc) in enumerate(rows):
        c = OUTCOME_COLOR[outc]
        ax.barh(i, score, height=0.6, color=c, edgecolor=SURFACE, zorder=2)
        ax.text(score + 0.03, i, f"{score:.1f}", va="center", ha="left", fontsize=9,
                fontweight="bold", color=INK)
        ax.text(-0.03, i + 0.16, label, va="center", ha="right", fontsize=9.4, fontweight="bold", color=INK)
        ax.text(-0.03, i - 0.20, f"{tgt} · {OUTCOME_LABEL[outc]}", va="center", ha="right",
                fontsize=7.8, color=MUTED)
    # tier guide lines
    for xv, lab in [(1.0, "Moderate"), (1.4, "Strong")]:
        ax.axvline(xv, color=RULE, lw=1, ls=(0, (4, 3)), zorder=1)
        ax.text(xv, n - 0.35, lab, fontsize=7.2, color=MUTED, ha="center", va="bottom")
    ax.set_xlim(0, 1.85)
    ax.set_ylim(-0.7, n - 0.3)
    ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(axis="x", labelsize=8, colors=MUTED, length=0)
    ax.set_xlabel("genetic_only_v1 score", fontsize=8.5, color=SEC)
    handles = [Line2D([0], [0], marker="s", color="none", markerfacecolor=OUTCOME_COLOR[k],
                      markersize=9, label=OUTCOME_LABEL[k]) for k in ("approved", "failed", "pending", "mixed")]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=8, handletextpad=0.4)
    if not clean:
        title = "Same genetic strength, opposite outcomes"
        sub = ("Genetic score for the case library, coloured by outcome. The approvals (PCSK9, ANGPTL3) sit right among "
               "the failures at equal or lower score — APP failed at a HIGHER score than either approval. Genetic "
               "strength is necessary-ish but does not decide the outcome; the downstream gates do.")
        src = "genetic_only_v1 on v_target_evidence_wide (present-day; hindsight)."
        fig.text(0.015, 0.945, title, fontsize=14, fontweight="bold", color=INK)
        fig.text(0.015, 0.79, sub, fontsize=9, color=SEC, linespacing=1.4)
        fig.add_artist(Line2D([0.015, 0.985], [0.70, 0.70], color=RULE, lw=1, transform=fig.transFigure))
        fig.text(0.015, 0.02, src, fontsize=7.4, color=MUTED, ha="left")
    stem = "genetics_vs_outcome" + ("_clean" if clean else "")
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=200)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png (200 dpi) + .svg")


def main():
    rows = []
    for label, tgt, score, outc in LIB:
        rows.append(dict(drug=label, target=tgt, genetic_only_v1=score, outcome=outc))
    pd.DataFrame(rows).to_csv(os.path.join(DATA, "genetics_gates_cases.csv"), index=False)
    plot_gates(clean=False); plot_gates(clean=True)
    plot_score_vs_outcome(clean=False); plot_score_vs_outcome(clean=True)


if __name__ == "__main__":
    main()
