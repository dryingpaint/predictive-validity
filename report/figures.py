"""Report figures from the Section 1 and Section 2 outputs.

    python -m report.figures

Reads report/output/section*/ CSVs (no database access) and writes PNG and
SVG files to report/output/figures/.
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from report import bio, frame

OUT = os.path.join(frame.REPO, "report", "output")
FIG = os.path.join(OUT, "figures")

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
GRID, BAR, ACCENT = "#e4e3df", "#c3c2b7", "#2a78d6"
FAMILY_COLORS = {  # reference categorical order; each family keeps its hue in every panel
    "Efficacy (stated or measured)": "#2a78d6", "Safety, PK or formulation": "#eb6834",
    "Business or strategy (explicit)": "#1baf7a", "Sponsor decision, no reason": "#eda100",
    "Enrollment, operational, regulatory": "#4a3aa7", "Positive readout, not advanced": "#008300",
    "No reason, no results": "#c3c2b7",
}
REASON_FAMILY = {
    "efficacy: stated": "Efficacy (stated or measured)",
    "efficacy: primary endpoint not met": "Efficacy (stated or measured)",
    "safety": "Safety, PK or formulation", "PK, dose or formulation": "Safety, PK or formulation",
    "business or strategic (explicit)": "Business or strategy (explicit)",
    "sponsor decision, unspecified": "Sponsor decision, no reason",
    "enrollment, operational or regulatory": "Enrollment, operational, regulatory",
    "positive readout, not advanced": "Positive readout, not advanced",
    "completed, no results posted, no reason stated": "No reason, no results",
    "stopped, no reason stated": "No reason, no results",
}


def style(ax):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, length=0)
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.set_axisbelow(True)


def save(fig, name):
    os.makedirs(FIG, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(FIG, f"{name}.{ext}"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def failure_modes():
    progs = pd.read_csv(os.path.join(OUT, "section1", "failure_modes_programs.csv"))
    progs["family"] = progs.reason.map(REASON_FAMILY)
    tab = progs.pivot_table(index="phase", columns="family", values="program_id", aggfunc="count", fill_value=0)
    share = tab.div(tab.sum(axis=1), axis=0)
    fig, ax = plt.subplots(figsize=(9, 3.2))
    for i, ph in enumerate(sorted(share.index, reverse=True)):
        left = 0.0
        for fam, color in FAMILY_COLORS.items():
            w = share.at[ph, fam] if fam in share.columns else 0.0
            ax.barh(i, w, left=left, height=0.55, color=color, edgecolor="white", linewidth=2)
            if w >= 0.07:
                ax.text(left + w / 2, i, f"{w:.0%}", ha="center", va="center", color="white", fontsize=9)
            left += w
    ax.set_yticks(range(len(share)), [f"Phase {ph}\n{int(tab.loc[ph].sum()):,} programs"
                                     for ph in sorted(share.index, reverse=True)], color=INK)
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    style(ax)
    ax.legend(handles=[matplotlib.patches.Patch(color=c, label=f) for f, c in FAMILY_COLORS.items()],
              ncol=4, frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.18))
    ax.set_title("Why suspended programs stopped, by the phase they stopped in", loc="left", color=INK, fontsize=11)
    save(fig, "failure_modes_by_phase")


def loa_bars(csv, title, name, bio, label_fmt):
    df = pd.read_csv(os.path.join(OUT, "section1", csv)).sort_values("loa")
    fig, ax = plt.subplots(figsize=(6.2, 0.38 * len(df) + 1))
    y = np.arange(len(df))
    top = df.loa.idxmax()
    ax.barh(y, df.loa * 100, height=0.6, color=[ACCENT if i == top else BAR for i in df.index])
    ax.errorbar(df.loa * 100, y, xerr=[(df.loa - df.loa_lo) * 100, (df.loa_hi - df.loa) * 100],
                fmt="none", ecolor=INK2, elinewidth=1, capsize=0)
    for yi, (lab, v, hi) in enumerate(zip(df.label, df.loa, df.loa_hi)):
        if lab in bio:
            ax.plot([bio[lab]] * 2, [yi - 0.35, yi + 0.35], color=INK, linewidth=2)
        ax.text(max(hi * 100, bio.get(lab, 0)) + 0.6, yi, f"{v:.1%}", va="center", color=INK2, fontsize=8)
    ax.set_yticks(y, [label_fmt(l) for l in df.label], color=INK)
    ax.set_xlabel("Likelihood of FDA approval from Phase 1 (%), 95% CI; tick = BIO 2011–2020", color=INK2, fontsize=8)
    style(ax)
    ax.set_title(title, loc="left", color=INK, fontsize=11)
    save(fig, name)


def relative_success():
    df = pd.read_csv(os.path.join(OUT, "section2", "relative_success.csv")).dropna(subset=["rs"]).sort_values("rs")
    fig, ax = plt.subplots(figsize=(7, 0.42 * len(df) + 1))
    y = np.arange(len(df))
    genetic = df.feature.str.startswith("genetic")
    ax.barh(y, np.log2(df.rs), height=0.55, color=[ACCENT if g else BAR for g in genetic])
    ax.errorbar(np.log2(df.rs), y, xerr=[np.log2(df.rs) - np.log2(df.rs_lo), np.log2(df.rs_hi) - np.log2(df.rs)],
                fmt="none", ecolor=INK2, elinewidth=1, capsize=0)
    ax.axvline(0, color=INK2, linewidth=1)
    for yi, (v, n) in enumerate(zip(df.rs, df.n_with)):
        ax.text(max(np.log2(df.rs_hi.iloc[yi]), 0) + 0.05, yi, f"{v:.2f}× (n={n:,})", va="center",
                color=INK2, fontsize=8)
    ticks = [0.25, 0.5, 1, 2, 4]
    ax.set_xticks(np.log2(ticks), [f"{t:g}×" for t in ticks])
    ax.set_yticks(y, df.label, color=INK, fontsize=9)
    style(ax)
    ax.set_title("Relative success: LOA with the evidence ÷ LOA without it (95% CI)", loc="left", color=INK, fontsize=10)
    save(fig, "relative_success_by_evidence")


def dose_response():
    df = pd.read_csv(os.path.join(OUT, "section2", "genetic_dose_response.csv"))
    names = {"none": "None", "low": "Lower third", "middle": "Middle third", "high": "Upper third"}
    fig, ax = plt.subplots(figsize=(6.2, 2.6))
    y = np.arange(len(df))[::-1]
    ax.barh(y, df.loa * 100, height=0.6, color=[BAR if b == "none" else ACCENT for b in df.band])
    ax.errorbar(df.loa * 100, y, xerr=[(df.loa - df.loa_lo) * 100, (df.loa_hi - df.loa) * 100],
                fmt="none", ecolor=INK2, elinewidth=1, capsize=0)
    for yi, (v, hi, n) in zip(y, zip(df.loa, df.loa_hi, df.n_programs)):
        ax.text(hi * 100 + 0.4, yi, f"{v:.1%} (n={n:,})", va="center", color=INK2, fontsize=8)
    ax.set_yticks(y, [names[b] for b in df.band], color=INK)
    ax.set_xlabel("Likelihood of FDA approval from Phase 1 (%), 95% CI", color=INK2, fontsize=8)
    style(ax)
    ax.set_title("Likelihood of approval by strength of human genetic support", loc="left", color=INK, fontsize=11)
    save(fig, "genetic_dose_response")


def main():
    failure_modes()
    loa_bars("loa_by_area.csv", "Likelihood of approval by disease area", "loa_by_area", bio.AREA_LOA,
             lambda s: s.replace("_", " ").capitalize())
    loa_bars("loa_by_modality.csv", "Likelihood of approval by modality", "loa_by_modality", bio.MODALITY_LOA,
             lambda s: s.replace("_", " ").replace("rnai", "RNAi").replace("car t", "CAR-T").capitalize())
    if os.path.exists(os.path.join(OUT, "section2", "relative_success.csv")):
        relative_success()
        dose_response()


if __name__ == "__main__":
    main()
