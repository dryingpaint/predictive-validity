#!/usr/bin/env python3
"""
Figure for the full B-E time-slice: raw -> date-cleaned Relative Success for all
four LLM literature lines (mechanistic / cell / animal / PD), as a dumbbell.

Editorial matplotlib, CB-safe palette, reuses the house style of PR #9's
plot_nuance_dateclean.py. Writes only the _clean (lean) variant: 200-dpi PNG +
editable SVG. Genetics band + RS=1 null shown for scale.

Reads data/line_be_timeslice.csv.
"""
from __future__ import annotations
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
INK, SEC, MUTED = "#14110f", "#5b544e", "#938b82"
SURFACE, RULE = "#fbfaf8", "#d8d3cb"
BLUE, ORANGE, AMBER = "#1f6fd0", "#e2673a", "#caa14a"
GREY = "#b9b2a8"
GEN_LO, GEN_HI = 1.44, 1.98   # strong-genetics RS band (v_relative_success_clean)

ORDER = [
    "Mechanistic literature (line_b)",
    "Cell literature (line_c)",
    "Animal literature (line_d)",
    "PD literature (line_e)",
]


def _sans():
    have = {f.name for f in fm.fontManager.ttflist}
    for f in ("Helvetica Neue", "Helvetica", "Arial"):
        if f in have:
            return f
    return "DejaVu Sans"


def main():
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                         "savefig.facecolor": SURFACE, "font.family": _sans(),
                         "text.color": INK, "figure.dpi": 200, "svg.fonttype": "none"})
    df = pd.read_csv(os.path.join(DATA, "line_be_timeslice.csv"))
    if "population" in df.columns:   # plot the full-cohort RS (headline)
        df = df[df.population == "full_cohort"]

    fig, ax = plt.subplots(figsize=(9.6, 5.3))
    fig.subplots_adjust(left=0.24, right=0.965, top=0.66, bottom=0.135)
    ys = list(range(len(ORDER)))[::-1]
    for y, dim in zip(ys, ORDER):
        sub = df[df.dimension == dim].set_index("cutoff")
        raw = sub.loc["raw (any date)", "rs"]
        strict = sub.loc["clean_strict (pre-first-trial)", "rs"]
        loose = sub.loc["clean_loose (pre-last-trial)", "rs"]
        ax.plot([strict, raw], [y, y], color=GREY, lw=3, zorder=2,
                solid_capstyle="round")
        ax.scatter([raw], [y], s=140, color=ORANGE, zorder=4,
                   edgecolor=SURFACE, lw=1.5)
        ax.scatter([loose], [y], s=72, color=AMBER, zorder=3,
                   edgecolor=SURFACE, lw=1.5)
        ax.scatter([strict], [y], s=140, color=BLUE, zorder=4,
                   edgecolor=SURFACE, lw=1.5)
        ax.text(raw + 0.03, y + 0.20, f"raw {raw}", fontsize=8.5, color=ORANGE,
                va="center", fontweight="bold")
        ax.text(strict - 0.03, y + 0.20, f"pre-trial {strict}", fontsize=8.5,
                color=BLUE, va="center", ha="right", fontweight="bold")
        ax.text(-0.02, y, dim.split(" (")[0], fontsize=10.5, ha="right",
                va="center", fontweight="bold", color=INK,
                transform=ax.get_yaxis_transform())

    ax.axvspan(GEN_LO, GEN_HI, color=BLUE, alpha=0.08, zorder=0)
    ax.axvline(1.0, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(1.0, max(ys) + 0.72, "no signal", fontsize=7.5, color=MUTED, ha="center")
    ax.text((GEN_LO+GEN_HI)/2, max(ys) + 0.72, "genetics band", fontsize=7.5,
            color=BLUE, ha="center", fontweight="bold")

    ax.set_xlim(0.9, 2.55); ax.set_ylim(min(ys) - 0.6, max(ys) + 1.0)
    ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.set_xlabel("Relative Success (approval with ÷ without evidence)",
                  fontsize=9, color=SEC)
    ax.tick_params(axis="x", labelsize=8, colors=MUTED, length=0)

    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=ORANGE,
               markersize=9, label="raw (any-date papers)"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=AMBER,
               markersize=7, label="pre-last-trial (loose)"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE,
               markersize=9, label="pre-first-trial (strict, clean)"),
    ]
    ax.legend(handles=handles, loc="center right", frameon=False, fontsize=8,
              handletextpad=0.3, bbox_to_anchor=(1.0, 0.42))

    fig.text(0.02, 0.945,
             "Date-cleaning removes a third to over half of the literature signal",
             fontsize=14, fontweight="bold", color=INK)
    fig.text(0.02, 0.895,
             "Relative Success of the four LLM literature evidence lines (mechanistic, cell, "
             "animal, PD), before vs. after requiring the cited papers to predate the trial. "
             "The raw scores are hindsight-inflated; once only pre-first-trial papers count the "
             "signal drops sharply. The date-cleaned points look like they land in the genetics "
             "band — but a second, selection confound remains: only well-studied targets were "
             "LLM-scored at all, and within that scored subset the clean signal is near-null "
             "(B 1.06, D 0.98; C/E ~1.2–1.3). See report.",
             fontsize=9.0, color=SEC, linespacing=1.4, wrap=True, va="top")
    fig.add_artist(Line2D([0.02, 0.965], [0.70, 0.70], color=RULE, lw=1,
                          transform=fig.transFigure))
    fig.text(0.02, 0.025,
             "Source: preclin line_b/c/d/e_lit + NCBI eutils publication dates. "
             "Ph2+ dated programs; support = score ≥2; ~74% of high-support programs datable.",
             fontsize=7.2, color=MUTED)

    stem = "line_be_timeslice_clean"
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=200)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png + .svg")


if __name__ == "__main__":
    main()
