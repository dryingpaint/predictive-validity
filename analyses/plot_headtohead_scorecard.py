#!/usr/bin/env python3
"""
PCSK9 vs. APP vs. CETP — a causal-chain head-to-head scorecard.

Three well-supported programs, one succeeded. The figure walks the causal chain
left to right (human genetics -> target-to-biomarker -> biomarker-to-hard-outcome
causal? -> did the drug move the biomarker?) and colours where each program holds
(green) or breaks (amber/red). The point: all three have genetics and all three
moved their biomarker as designed — they only diverge at the
"is the biomarker actually causal for the hard outcome?" step. PCSK9 clears it
(LDL is causal); APP clears it only for the wrong stage/population; CETP fails it
outright (HDL is a bystander, per Mendelian randomization).

genetic_only_v1 scores + components are pulled once from
preclin.v_target_evidence_wide via benchmark/scorers_rule_based.py::scorer_genetic_only
and baked in below (present-day values — hindsight; see PCSK9_VS_APP_CETP.md).
No DB needed to plot. Writes data/headtohead_scorecard.csv for provenance.
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
GREEN, AMBER, RED, BLUE = "#2e7d47", "#d99a2b", "#b0322a", "#1f6fd0"

# genetic_only_v1 raw score + key components (present-day, from v_target_evidence_wide)
SUPPORT = {
    #             score  tier          clingen mend(dom) gwas  otgen  n_causal
    "PCSK9": dict(score=1.3, tier="Moderate",     clingen=1, mend="4 (2 dom)", gwas=1410, otgen=0.99, ncausal=5),
    "APP":   dict(score=1.6, tier="Strong",       clingen=1, mend="15 (7 dom)", gwas=40,  otgen=0.65, ncausal=3),
    "CETP":  dict(score=0.7, tier="Weak*",        clingen=0, mend="2 (1 dom)", gwas=2498, otgen=0.98, ncausal=3),
}

# (drug, target·indication, genetics_cell(color,label), targ_biomarker, biomarker_causal, drug_moved, outcome)
# each middle cell = (color, top_label, sub_label)
ROWS = [
    ("Anti-PCSK9 mAbs",  "PCSK9 · cardiovascular",
     (GREEN, "Moderate", "score 1.3"),
     (GREEN, "validated", "LDL"),
     (GREEN, "yes", "LDL causal (MR)"),
     (GREEN, "yes", "LDL cut ~60%"),
     (BLUE,  "APPROVED", "")),
    ("Anti-Aβ mAbs (sola/bapi)", "APP · Alzheimer's",
     (GREEN, "Strong", "score 1.6"),
     (GREEN, "validated", "Aβ"),
     (AMBER, "stage-limited", "right node, late"),
     (GREEN, "yes", "Aβ cleared"),
     (RED,   "FAILED", "efficacy")),
    ("Torcetrapib (CETP)", "CETP · cardiovascular",
     (GREEN, "Weak*", "score 0.7 — misread"),
     (GREEN, "validated", "HDL"),
     (RED,   "no", "HDL bystander (MR)"),
     (GREEN, "yes", "HDL up ~60%"),
     (RED,   "FAILED", "efficacy/safety")),
]

COLS = ["Human genetics", "Target-biomarker\nlink", "Biomarker causal\nfor outcome?",
        "Drug moved\nbiomarker?", "Outcome"]


def _sans():
    have = {f.name for f in fm.fontManager.ttflist}
    for f in ("Helvetica Neue", "Helvetica", "Arial"):
        if f in have:
            return f
    return "DejaVu Sans"


def plot(clean=False):
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                         "savefig.facecolor": SURFACE, "font.family": _sans(),
                         "text.color": INK, "figure.dpi": 200, "svg.fonttype": "none"})
    n = len(ROWS)
    ncol = len(COLS)
    fig, ax = plt.subplots(figsize=(11.2, 3.6 if clean else 4.6))
    fig.subplots_adjust(left=0.185, right=0.99, top=0.80 if clean else 0.60, bottom=0.13)

    yrows = list(range(n - 1, -1, -1))          # top row = first entry
    cw = 1.0                                      # column width unit
    for ri, row in enumerate(ROWS):
        y = yrows[ri]
        cells = row[2:]
        for ci, (color, top, sub) in enumerate(cells):
            x = ci * cw
            ax.add_patch(Rectangle((x, y - 0.44), 0.92 * cw, 0.88, facecolor=color,
                                   edgecolor=SURFACE, lw=2, zorder=2))
            ax.text(x + 0.46 * cw, y + (0.11 if sub else 0.0), top, ha="center", va="center",
                    fontsize=10.5, fontweight="bold", color="#fff")
            if sub:
                ax.text(x + 0.46 * cw, y - 0.19, sub, ha="center", va="center",
                        fontsize=7.6, color="#f3efe9")
        ax.text(-0.14, y + 0.12, row[0], ha="right", va="center", fontsize=10.5,
                fontweight="bold", color=INK)
        ax.text(-0.14, y - 0.18, row[1], ha="right", va="center", fontsize=8.3, color=MUTED)

    ytop = max(yrows)
    for ci, name in enumerate(COLS):
        ax.text(ci * cw + 0.46 * cw, ytop + 0.70, name, ha="center", va="bottom",
                fontsize=9.2, fontweight="bold", color=SEC, linespacing=1.15)

    ax.set_xlim(-1.75, ncol * cw + 0.05)
    ax.set_ylim(-0.95, ytop + 1.15)
    ax.axis("off")

    # legend / key
    key = [(GREEN, "holds"), (AMBER, "partial"), (RED, "breaks"), (BLUE, "approved")]
    for i, (c, lab) in enumerate(key):
        ax.add_patch(Rectangle((i * 0.95, -0.86), 0.28, 0.22, facecolor=c, edgecolor=SURFACE, lw=1.2))
        ax.text(i * 0.95 + 0.34, -0.75, lab, ha="left", va="center", fontsize=7.6, color=MUTED)

    if not clean:
        title = "Same causal chain, one break each — and only one approval"
        sub = ("All three targets have human genetics and all three drugs moved their biomarker as designed. "
               "They diverge at one step: is the biomarker actually causal for the hard outcome? "
               "PCSK9 clears it (LDL); APP only for the wrong stage; CETP fails it (HDL is a bystander).")
        src = ("Genetics = genetic_only_v1 on v_target_evidence_wide (present-day; hindsight). "
               "*CETP genetics is present and strong-looking (human LoF carriers) but Mendelian randomization "
               "showed HDL non-causal — misread, not absent.")
        fig.text(0.02, 0.925, title, fontsize=14.5, fontweight="bold", color=INK)
        fig.text(0.02, 0.78, sub, fontsize=9.3, color=SEC, linespacing=1.4)
        fig.add_artist(Line2D([0.02, 0.99], [0.70, 0.70], color=RULE, lw=1, transform=fig.transFigure))
        fig.text(0.02, 0.02, src, fontsize=7.6, color=MUTED, ha="left")

    stem = "headtohead_scorecard" + ("_clean" if clean else "")
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=200)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png (200 dpi) + .svg")


def main():
    rows = []
    for tgt, s in SUPPORT.items():
        rows.append(dict(target=tgt, genetic_only_v1=s["score"], tier=s["tier"],
                         clingen_n_strong=s["clingen"], mendelian_n=s["mend"],
                         gwas_n_sig=s["gwas"], ot_genetic_max=s["otgen"],
                         n_causal_diseases=s["ncausal"]))
    pd.DataFrame(rows).to_csv(os.path.join(DATA, "headtohead_scorecard.csv"), index=False)
    plot(clean=False)
    plot(clean=True)


if __name__ == "__main__":
    main()
