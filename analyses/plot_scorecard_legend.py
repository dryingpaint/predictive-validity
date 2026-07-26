"""Scorecard legend / rubric key — how to read the 0–3 evidence cells and the
genetics tier used in the case-study scorecards (genetics_mirror, case_scorecard,
causal-gates head-to-head).

Deliberately matches those figures' encoding exactly: the RdYlGn ramp normalized
0→3, the same ink/surface tokens, and the numeral drawn in every cell (so the score
is legible independent of colour — important because red/green alone is not
colourblind-safe; here the number is the primary encoding and colour is redundant).

Two scales:
  1. Evidence strength (Mechanistic / Cell-pathway / Animal in-vivo / Human PD),
     each scored 0–3 on how direct/definitive the evidence is.
  2. Genetics — the repo's `genetic_only_v1` score, mapped onto the same 0–3 colour
     scale by tier (Absent / Weak / Moderate / Strong).

Writes clean (publication-grade) PNG + editable SVG. No DB needed.
"""
import os
os.environ.setdefault("MPLCONFIGDIR", ".mplconfig")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import matplotlib.font_manager as fm

INK, SEC, MUTED = "#14110f", "#5b544e", "#938b82"
SURFACE, RULE = "#fbfaf8", "#d8d3cb"
CMAP = cm.get_cmap("RdYlGn")
NORM = Normalize(0, 3)

# 0–3 anchors for the evidence columns (how the case studies were actually scored)
EVIDENCE = [
    (0, "Absent",   "none / not assessed"),
    (1, "Weak",     "indirect or single result"),
    (2, "Moderate", "solid, one key gap"),
    (3, "Strong",   "direct & reproduced"),
]
# genetics tier -> same 0–3 colour, keyed to genetic_only_v1 score cutoffs
GENETICS = [
    (0, "Absent",   "no human genetics"),
    (1, "Weak",     "score 0.1 – 0.9"),
    (2, "Moderate", "score 1.0 – 1.3"),
    (3, "Strong",   "score ≥ 1.4"),
]
GEN_FORMULA = ("Genetics = genetic_only_v1: ClinGen ≥1 (+0.6) · Mendelian ≥5 (+0.5) / ≥1 (+0.2) · "
               "OT-genetic ≥0.5 (+0.5) / ≥0.3 (+0.3) · OT-somatic ≥0.3 (+0.3) · Nelson tier.")


def _sans():
    for f in ("Helvetica Neue", "Helvetica", "Arial", "Liberation Sans", "DejaVu Sans"):
        if any(f.lower() == x.name.lower() for x in fm.fontManager.ttflist):
            return f
    return "DejaVu Sans"


def _row(ax, items, y, sw=0.82, gap=1.95, x0=0.0):
    """Draw a labelled swatch row; return the x of the right edge."""
    for i, (val, tier, desc) in enumerate(items):
        x = x0 + i * gap
        ax.add_patch(Rectangle((x, y - sw / 2), sw, sw, facecolor=CMAP(NORM(val)),
                               edgecolor=SURFACE, lw=2, zorder=2))
        ax.text(x + sw / 2, y, str(val), ha="center", va="center", fontsize=15,
                fontweight="bold", color=INK if val >= 2 else "#ffffff")
        ax.text(x + sw + 0.12, y + 0.17, tier, ha="left", va="center",
                fontsize=10.5, fontweight="bold", color=INK)
        ax.text(x + sw + 0.12, y - 0.19, desc, ha="left", va="center",
                fontsize=8.6, color=MUTED)
    return x0 + len(items) * gap


def plot(clean=True):
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                         "savefig.facecolor": SURFACE, "font.family": _sans(),
                         "text.color": INK, "figure.dpi": 300, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(10.8, 4.6))
    ax.set_xlim(-0.3, 7.9); ax.set_ylim(-0.2, 5.2); ax.axis("off")

    # section headers + swatch rows
    ax.text(0.0, 4.35, "EVIDENCE STRENGTH", fontsize=10, fontweight="bold", color=SEC)
    ax.text(0.0, 4.05, "Mechanistic · Cell-pathway · Animal in-vivo · Human PD — each 0–3",
            fontsize=8.6, color=MUTED)
    _row(ax, EVIDENCE, 3.30)
    ax.text(0.0, 2.55,
            "The 2-vs-3 line is directness: e.g. Mechanistic 3 = pharmacology + solved structure; "
            "2 = pharmacology known, structure not yet solved.",
            fontsize=7.8, color=MUTED, style="italic")

    ax.text(0.0, 2.15, "GENETICS", fontsize=10, fontweight="bold", color=SEC)
    ax.text(0.0, 1.85, "genetic_only_v1, mapped onto the same 0–3 colour scale",
            fontsize=8.6, color=MUTED)
    _row(ax, GENETICS, 1.05)

    ax.text(0.0, 0.05, GEN_FORMULA, fontsize=7.6, color=MUTED, va="top")
    ax.text(0.0, -0.30, "The numeral is shown in every cell, so the score reads independent of colour.",
            fontsize=7.6, color=MUTED, va="top", style="italic")

    if not clean:
        fig.suptitle("How to read the scorecard", x=0.035, y=0.985, ha="left",
                     fontsize=15, fontweight="bold", color=INK)
        fig.add_artist(Line2D([0.035, 0.985], [0.93, 0.93], color=RULE, lw=1,
                              transform=fig.transFigure))

    fig.tight_layout()
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data",
                        "scorecard_legend" + ("_clean" if clean else ""))
    for ext in ("png", "svg"):
        fig.savefig(f"{base}.{ext}", bbox_inches="tight", dpi=300)
        print(f"wrote {os.path.relpath(base)}.{ext}")
    plt.close(fig)


if __name__ == "__main__":
    plot(clean=False)
    plot(clean=True)
