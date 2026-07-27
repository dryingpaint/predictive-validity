#!/usr/bin/env python3
"""
Nuance / Section 5 figures.

1. nuance_dateclean_collapse — the headline: cell & animal LITERATURE evidence,
   raw vs. date-cleaned (pre-first-trial) Relative Success, as a dumbbell. Most of
   the apparent predictive power is hindsight — it collapses toward the null (RS=1)
   once the supporting papers must predate the trial. Genetics benchmark band + RS=1
   reference shown for scale.

2. nuance_tier_overview — RS for every cell/animal measure across the three tiers
   (structural / literature / drug-efficacy), raw and date-cleaned where available,
   against the RS=1 null and the genetics band. Shows no cell/animal measure — clean —
   approaches genetics.

Reads data/nuance_literature_dateclean.csv + data/nuance_drug_structural.csv.
"""
from __future__ import annotations
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
INK, SEC, MUTED = "#14110f", "#5b544e", "#938b82"
SURFACE, RULE = "#fbfaf8", "#d8d3cb"
BLUE, ORANGE, GREEN, GREY = "#1f6fd0", "#e2673a", "#2e7d47", "#b9b2a8"
GEN_LO, GEN_HI = 1.12, 1.98   # genetics dims RS spread (from v_relative_success_clean:
                              # GWAS 1.12, OT-genetic 1.14, Mendelian 1.49, ClinGen 1.74, OT-somatic 1.98)


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


def _genetics_band(ax, y0, y1):
    ax.axvspan(GEN_LO, GEN_HI, color=BLUE, alpha=0.08, zorder=0)
    ax.axvline(1.0, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=1)


def plot_collapse(clean=False):
    _rc()
    lit = pd.read_csv(os.path.join(DATA, "nuance_literature_dateclean.csv"))
    order = ["Cell literature (line_c)", "Animal literature (line_d)"]
    fig, ax = plt.subplots(figsize=(9.4, 3.4 if clean else 4.4))
    fig.subplots_adjust(left=0.20, right=0.965, top=0.80 if clean else 0.60, bottom=0.17)
    ys = [1, 0]
    for y, dim in zip(ys, order):
        sub = lit[lit.dimension == dim].set_index("cutoff")
        raw = sub.loc["raw (any date)", "rs"]
        strict = sub.loc["clean_strict (pre-first-trial)", "rs"]
        loose = sub.loc["clean_loose (pre-last-trial)", "rs"]
        ax.plot([strict, raw], [y, y], color=GREY, lw=3, zorder=2, solid_capstyle="round")
        ax.scatter([raw], [y], s=130, color=ORANGE, zorder=3, edgecolor=SURFACE, lw=1.5)
        ax.scatter([loose], [y], s=70, color="#caa14a", zorder=3, edgecolor=SURFACE, lw=1.5)
        ax.scatter([strict], [y], s=130, color=BLUE, zorder=3, edgecolor=SURFACE, lw=1.5)
        ax.text(raw + 0.03, y + 0.12, f"raw {raw}", fontsize=8.5, color=ORANGE, va="center", fontweight="bold")
        ax.text(strict - 0.03, y + 0.12, f"pre-trial {strict}", fontsize=8.5, color=BLUE, va="center",
                ha="right", fontweight="bold")
        ax.text(-0.02, y, dim.split(" (")[0], fontsize=10.5, ha="right", va="center",
                fontweight="bold", color=INK, transform=ax.get_yaxis_transform())
    _genetics_band(ax, -0.5, 1.5)
    ax.text(1.0, 1.62, "no signal", fontsize=7.5, color=MUTED, ha="center")
    ax.text((GEN_LO+GEN_HI)/2, 1.62, "genetics", fontsize=7.5, color=BLUE, ha="center", fontweight="bold")
    ax.set_xlim(0.9, 2.05); ax.set_ylim(-0.6, 1.75)
    ax.set_yticks([])
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.set_xlabel("Relative Success (approval with ÷ without evidence)", fontsize=9, color=SEC)
    ax.tick_params(axis="x", labelsize=8, colors=MUTED, length=0)
    handles = [Line2D([0],[0],marker="o",color="none",markerfacecolor=ORANGE,markersize=9,label="raw (any-date papers)"),
               Line2D([0],[0],marker="o",color="none",markerfacecolor="#caa14a",markersize=7,label="pre-last-trial"),
               Line2D([0],[0],marker="o",color="none",markerfacecolor=BLUE,markersize=9,label="pre-first-trial (clean)")]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=8, handletextpad=0.3)
    if not clean:
        fig.text(0.02, 0.925, "Half the apparent power of cell/animal literature is hindsight",
                 fontsize=14.5, fontweight="bold", color=INK)
        fig.text(0.02, 0.79,
                 "Relative Success of target-level cell and animal literature evidence, before vs. after requiring the "
                 "supporting papers to predate the trial. When only pre-first-trial papers count, the signal collapses "
                 "toward the null — animal evidence nearly to 1.0 — and stays well below genetics.",
                 fontsize=9.2, color=SEC, linespacing=1.4, wrap=True)
        fig.add_artist(Line2D([0.02, 0.965], [0.70, 0.70], color=RULE, lw=1, transform=fig.transFigure))
        fig.text(0.02, 0.03, "Source: preclin line_c_lit/line_d_lit + NCBI eutils publication dates. Ph2+ programs.",
                 fontsize=7.4, color=MUTED)
    stem = "nuance_dateclean_collapse" + ("_clean" if clean else "")
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=200)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig); print(f"wrote data/{stem}.png + .svg")


def plot_drug_collapse(clean=False):
    """Drug-specific efficacy rubric: present-day vs pre-trial re-score (N=425)."""
    _rc()
    df = pd.read_csv(os.path.join(DATA, "drug_efficacy_pretrial_comparison_full.csv")).set_index("measure")
    pairs = [("Drug cell efficacy", "present cell", "time-sliced cell"),
             ("Drug animal efficacy", "present animal", "time-sliced animal")]
    fig, ax = plt.subplots(figsize=(9.4, 3.2 if clean else 4.3))
    fig.subplots_adjust(left=0.22, right=0.965, top=0.80 if clean else 0.58, bottom=0.18)
    for y, (lab, pk, tk) in zip([1, 0], pairs):
        pres = round(float(df.loc[pk, "rs"]), 2)
        dat = round(float(df.loc[tk, "rs"]), 2)
        ax.plot([dat, pres], [y, y], color=GREY, lw=3, zorder=2, solid_capstyle="round")
        ax.scatter([pres], [y], s=130, color=ORANGE, zorder=3, edgecolor=SURFACE, lw=1.5)
        ax.scatter([dat], [y], s=130, color=BLUE, zorder=3, edgecolor=SURFACE, lw=1.5)
        ax.text(pres + 0.03, y + 0.12, f"present {pres}", fontsize=8.5, color=ORANGE, va="center", fontweight="bold")
        ax.text(dat - 0.03, y + 0.12, f"pre-trial {dat}", fontsize=8.5, color=BLUE, va="center", ha="right", fontweight="bold")
        ax.text(-0.02, y, lab, fontsize=10.5, ha="right", va="center", fontweight="bold",
                color=INK, transform=ax.get_yaxis_transform())
    _genetics_band(ax, -0.5, 1.5)
    ax.text(1.0, 1.62, "no signal", fontsize=7.5, color=MUTED, ha="center")
    ax.text((GEN_LO + GEN_HI) / 2, 1.62, "genetics", fontsize=7.5, color=BLUE, ha="center", fontweight="bold")
    ax.set_xlim(0.55, 2.05); ax.set_ylim(-0.6, 1.75)
    ax.set_yticks([])
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.set_xlabel("Relative Success (approval with ÷ without evidence)", fontsize=9, color=SEC)
    ax.tick_params(axis="x", labelsize=8, colors=MUTED, length=0)
    handles = [Line2D([0], [0], marker="o", color="none", markerfacecolor=ORANGE, markersize=9, label="present-day rubric"),
               Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE, markersize=9, label="pre-trial re-score (N=425)")]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=8, handletextpad=0.3)
    if not clean:
        fig.text(0.02, 0.925, '"The drug worked in a model" does not survive date-cleaning',
                 fontsize=14.5, fontweight="bold", color=INK)
        fig.text(0.02, 0.78,
                 "Drug-specific preclinical efficacy (Melissa's 0–3 rubric), present-day vs. re-scored on pre-trial "
                 "abstracts only (N=425 drugs, Haiku-subagent scored). The modest present-day signal collapses to the "
                 "null once only evidence predating the trial counts — a model certifies mechanism engagement, not "
                 "disease causality.",
                 fontsize=9.2, color=SEC, linespacing=1.4)
        fig.add_artist(Line2D([0.02, 0.965], [0.70, 0.70], color=RULE, lw=1, transform=fig.transFigure))
        fig.text(0.02, 0.03, "Source: preclin drug_*_efficacy rubric (present) + pre-trial PubMed abstracts re-scored on "
                 "the same rubric via Haiku subagents. Drug-level, Ph2+.", fontsize=7.4, color=MUTED)
    stem = "nuance_drug_efficacy_collapse" + ("_clean" if clean else "")
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=200)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig); print(f"wrote data/{stem}.png + .svg")


def plot_overview(clean=False):
    _rc()
    lit = pd.read_csv(os.path.join(DATA, "nuance_literature_dateclean.csv"))
    ds = pd.read_csv(os.path.join(DATA, "nuance_drug_structural.csv"))
    bars = []  # (label, rs, color)
    for _, r in ds[ds.tier == "structural"].iterrows():
        bars.append((r.measure.replace(" (raw)", " · structural"), r.rs, GREEN))
    for dim in ["Cell literature (line_c)", "Animal literature (line_d)"]:
        s = lit[lit.dimension == dim].set_index("cutoff")
        bars.append((dim.split(" (")[0] + " · lit (raw)", s.loc["raw (any date)","rs"], "#d9b38c"))
        bars.append((dim.split(" (")[0] + " · lit (pre-trial)", s.loc["clean_strict (pre-first-trial)","rs"], ORANGE))
    dfull = pd.read_csv(os.path.join(DATA, "drug_efficacy_pretrial_comparison_full.csv")).set_index("measure")
    for lab, pk, tk in [("Drug cell efficacy", "present cell", "time-sliced cell"),
                        ("Drug animal efficacy", "present animal", "time-sliced animal")]:
        bars.append((lab + " · drug (present)", round(float(dfull.loc[pk, "rs"]), 2), "#d9b38c"))
        bars.append((lab + " · drug (pre-trial re-score)", round(float(dfull.loc[tk, "rs"]), 2), ORANGE))
    bars = [(l, v, c) for l, v, c in bars if pd.notna(v)]
    fig, ax = plt.subplots(figsize=(9.8, 5.2 if clean else 6.2))
    fig.subplots_adjust(left=0.42, right=0.965, top=0.88 if clean else 0.72, bottom=0.10)
    ys = list(range(len(bars)))[::-1]
    for y, (lab, v, c) in zip(ys, bars):
        ax.barh(y, v, height=0.62, color=c, edgecolor=SURFACE, zorder=2)
        ax.text(v + 0.02, y, f"{v}", va="center", fontsize=8.5, fontweight="bold", color=INK)
        ax.text(-0.02, y, lab, va="center", ha="right", fontsize=8.6, color=INK,
                transform=ax.get_yaxis_transform())
    _genetics_band(ax, min(ys)-1, max(ys)+1)
    ax.text(1.0, max(ys)+0.75, "no signal", fontsize=7.5, color=MUTED, ha="center")
    ax.text((GEN_LO+GEN_HI)/2, max(ys)+0.75, "genetics band", fontsize=7.5, color=BLUE, ha="center", fontweight="bold")
    ax.set_xlim(0, 3.25); ax.set_ylim(min(ys)-0.6, max(ys)+1.1)
    ax.set_yticks([])
    for s in ("top","right","left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.set_xlabel("Relative Success", fontsize=9, color=SEC)
    ax.tick_params(axis="x", labelsize=8, colors=MUTED, length=0)
    if not clean:
        fig.text(0.02, 0.945, "No clean cell/animal measure comes near genetics",
                 fontsize=14.5, fontweight="bold", color=INK)
        fig.text(0.02, 0.79,
                 "Relative Success for every cell/animal evidence measure, across the three tiers (structural screens, "
                 "literature, drug-specific efficacy), raw and date-cleaned where possible. Genetics band shown for scale. "
                 "The raw literature/drug numbers are inflated by hindsight; the clean ones sit near the null.",
                 fontsize=9, color=SEC, linespacing=1.4)
        fig.add_artist(Line2D([0.02, 0.965], [0.735, 0.735], color=RULE, lw=1, transform=fig.transFigure))
        fig.text(0.02, 0.02, "Structural raw = preclin v_relative_success_clean; literature date-clean via eutils; "
                 "drug pre-trial via PubMed search. Present-day snapshots for structural (see doc).",
                 fontsize=7.2, color=MUTED)
    stem = "nuance_tier_overview" + ("_clean" if clean else "")
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=200)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig); print(f"wrote data/{stem}.png + .svg")


def main():
    for fn in (plot_collapse, plot_drug_collapse, plot_overview):
        fn(clean=False); fn(clean=True)


if __name__ == "__main__":
    main()
