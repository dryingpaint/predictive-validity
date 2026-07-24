#!/usr/bin/env python3
"""
Render BIO-replication figures matching the BIO 2021 report style.

Produces:
  data/bio_replication_transitions.png     — Figure 1 (four bars)
  data/bio_replication_loa_by_area.png     — Figure 5a (LOA from Ph1 by area)
  data/bio_replication_loa_by_modality.png — Figure 10a (LOA by modality)
  data/bio_replication_oncology.png        — Figure 6
  data/bio_replication_novelty.png         — Figure 9 (novel subgroups)

Reads cached CSVs written by `bio_replication.py`.
"""
from __future__ import annotations
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Patch
import pandas as pd
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

INK, SEC, MUTED = "#14110f", "#5b544e", "#938b82"
SURFACE, RULE = "#fbfaf8", "#d8d3cb"
BIO_PINK, BIO_TEAL = "#c4287a", "#33bfbf"   # roughly matches BIO report palette
APPROVED = "#2f8f5b"


def _sans():
    have = {f.name for f in fm.fontManager.ttflist}
    for f in ("Helvetica Neue", "Helvetica", "Arial"):
        if f in have:
            return f
    return "DejaVu Sans"


def style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": _sans(), "text.color": INK, "figure.dpi": 300,
        "svg.fonttype": "none", "axes.linewidth": 0,
    })


def save(fig, stem):
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=600)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png + .svg")


# ─── Figure 1: overall transitions ─────────────────────────────────────────
def fig_transitions():
    df = pd.read_csv(f"{DATA}/bio_replication_overall.csv").iloc[0]
    labels = ["Phase I to II", "Phase II to III", "Phase III to Approval", "Ph1 to Approval (LOA)"]
    vals = [df["pos_ph1_to_2"], df["pos_ph2_to_3"], df["pos_ph3_to_approval"], df["loa_from_ph1"]]
    ns = [int(df["n_ph1"]), int(df["n_ph2"]), int(df["n_ph3"]), int(df["n_ph1"])]

    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    fig.subplots_adjust(left=0.10, right=0.95, top=0.86, bottom=0.15)
    colors = [BIO_PINK, BIO_PINK, BIO_PINK, APPROVED]
    bars = ax.bar(labels, vals, color=colors, width=0.62, zorder=3)
    for b, v, n in zip(bars, vals, ns):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}%",
                ha="center", va="bottom", fontsize=12, fontweight="bold", color=INK)
        ax.text(b.get_x() + b.get_width() / 2, -3, f"n={n:,}",
                ha="center", va="top", fontsize=9, color=SEC)
    ax.set_ylim(0, 100); ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("Probability of success", color=SEC, fontsize=11)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=RULE, lw=0.6)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    fig.text(0.03, 0.94, "Phase transition success rates — our cohort (2015–2025)",
             fontsize=14, fontweight="bold", color=INK)
    fig.text(0.03, 0.90, "Denominator: programs terminated by 2026 (BIO-style advanced-or-suspended).",
             fontsize=9.5, color=SEC)
    save(fig, "bio_replication_transitions")


# ─── Figure 5a: LOA by disease area ────────────────────────────────────────
def fig_loa_by_area():
    df = pd.read_csv(f"{DATA}/bio_replication_by_area.csv")
    df = df.sort_values("loa_from_ph1", ascending=True)
    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    fig.subplots_adjust(left=0.28, right=0.94, top=0.86, bottom=0.06)
    y = range(len(df))
    ax.barh(list(y), df.loa_from_ph1, height=0.62, color=BIO_PINK, zorder=3)
    xmax = max(df.loa_from_ph1.max() * 1.30, 30)
    for yi, (v, n) in enumerate(zip(df.loa_from_ph1, df.n_ph1)):
        ax.text(v + 0.4, yi, f"{v:.1f}%  (n={int(n):,})",
                va="center", fontsize=9.5, color=INK, fontweight="bold")
    ax.set_yticks(list(y))
    ax.set_yticklabels(df.stratum, fontsize=10.5, color=INK)
    ax.set_xlim(0, xmax)
    ax.set_xlabel("Likelihood of Approval from Phase I (%)", color=SEC, fontsize=10)
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=RULE, lw=0.6)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    fig.text(0.02, 0.95, "LOA from Phase I, by therapeutic area", fontsize=13, fontweight="bold")
    fig.text(0.02, 0.92, "Compounded probability across all four phase transitions. Our cohort, 2015-2025.",
             fontsize=9, color=SEC)
    save(fig, "bio_replication_loa_by_area")


# ─── Figure 10a: LOA by modality ───────────────────────────────────────────
MOD_LABEL = {
    "small_molecule": "Small molecule", "antibody": "Antibody",
    "adc": "Antibody-drug conjugate", "protein": "Protein / enzyme",
    "peptide": "Peptide", "oligonucleotide": "Oligonucleotide",
    "vaccine": "Vaccine", "cell_therapy": "Cell therapy",
    "gene_therapy": "Gene therapy", "mrna": "mRNA",
    "other": "Other", "unclassified": "(unclassified)",
}


def fig_loa_by_modality():
    df = pd.read_csv(f"{DATA}/bio_replication_by_modality.csv")
    df = df[df.n_ph1 >= 30].copy()  # suppress tiny modalities
    df["label"] = df.stratum.map(lambda s: MOD_LABEL.get(s, s))
    df = df.sort_values("loa_from_ph1", ascending=True)

    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    fig.subplots_adjust(left=0.28, right=0.94, top=0.83, bottom=0.10)
    y = range(len(df))
    ax.barh(list(y), df.loa_from_ph1, height=0.62, color=BIO_PINK, zorder=3)
    xmax = max(df.loa_from_ph1.max() * 1.30, 25)
    for yi, (v, n) in enumerate(zip(df.loa_from_ph1, df.n_ph1)):
        ax.text(v + 0.3, yi, f"{v:.1f}%  (n={int(n):,})",
                va="center", fontsize=9.5, color=INK, fontweight="bold")
    ax.set_yticks(list(y))
    ax.set_yticklabels(df.label, fontsize=10.5, color=INK)
    ax.set_xlim(0, xmax)
    ax.set_xlabel("Likelihood of Approval from Phase I (%)", color=SEC, fontsize=10)
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=RULE, lw=0.6)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    fig.text(0.02, 0.94, "LOA from Phase I, by drug modality", fontsize=13, fontweight="bold")
    fig.text(0.02, 0.905, "Modalities with n≥30 failed-plus-approved programs. Our cohort, 2015-2025.",
             fontsize=9, color=SEC)
    save(fig, "bio_replication_loa_by_modality")


# ─── Figure 6: oncology vs non-oncology (bars per phase) ────────────────────
def fig_oncology():
    df = pd.read_csv(f"{DATA}/bio_replication_oncology.csv")
    phases = ["Ph I to II", "Ph II to III", "Ph III to Approval", "LOA from Ph I"]
    metric_cols = ["pos_ph1_to_2", "pos_ph2_to_3", "pos_ph3_to_approval", "loa_from_ph1"]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.subplots_adjust(left=0.10, right=0.96, top=0.83, bottom=0.12)
    x = np.arange(len(phases))
    w = 0.38
    for i, cohort in enumerate(["Oncology", "Non-oncology"]):
        row = df[df.stratum == cohort]
        if row.empty:
            continue
        vals = row[metric_cols].iloc[0].tolist()
        n = int(row["n_ph1"].iloc[0])
        offset = (i - 0.5) * w
        color = BIO_PINK if cohort == "Oncology" else BIO_TEAL
        bars = ax.bar(x + offset, vals, w, color=color, label=f"{cohort} (n={n:,})", zorder=3)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 1.2, f"{v:.1f}%",
                    ha="center", fontsize=9, color=INK, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(phases, fontsize=10, color=INK)
    ax.set_ylim(0, max(70, df[metric_cols].values.max() * 1.15))
    ax.set_ylabel("Probability of success (%)", color=SEC, fontsize=10)
    ax.set_axisbelow(True); ax.yaxis.grid(True, color=RULE, lw=0.6)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.legend(frameon=False, loc="upper right", fontsize=10)
    fig.text(0.02, 0.94, "Oncology vs non-oncology  (BIO Figure 6 equivalent)",
             fontsize=13, fontweight="bold")
    save(fig, "bio_replication_oncology")


def fig_novelty():
    df = pd.read_csv(f"{DATA}/bio_replication_novelty_subgroups.csv")
    df = df[df.n_ph1 >= 30].copy()
    df = df.sort_values("loa_from_ph1", ascending=True)

    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    fig.subplots_adjust(left=0.30, right=0.94, top=0.79, bottom=0.13)
    y = range(len(df))
    colors = [BIO_PINK if s in ("NME (small-molecule)", "Biologic", "Vaccine") else BIO_TEAL
              for s in df.stratum]
    ax.barh(list(y), df.loa_from_ph1, height=0.55, color=colors, zorder=3)
    xmax = max(df.loa_from_ph1.max() * 1.30, 30)
    for yi, (v, n) in enumerate(zip(df.loa_from_ph1, df.n_ph1)):
        ax.text(v + 0.3, yi, f"{v:.1f}%  (n={int(n):,})",
                va="center", fontsize=10, color=INK, fontweight="bold")
    ax.set_yticks(list(y)); ax.set_yticklabels(df.stratum, fontsize=10.5)
    ax.set_xlim(0, xmax)
    ax.set_xlabel("LOA from Phase I (%)", color=SEC, fontsize=10)
    ax.xaxis.grid(True, color=RULE, lw=0.6); ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    handles = [Patch(color=BIO_PINK, label="Novel (NME / biologic / vaccine)"),
               Patch(color=BIO_TEAL, label="Off-patent (biosimilar / non-NME)")]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=9)
    fig.text(0.02, 0.92, "Novel-drug subgroups  (BIO Figure 9)", fontsize=13, fontweight="bold")
    fig.text(0.02, 0.87, "LOA from Phase I by drug novelty class.", fontsize=9, color=SEC)
    save(fig, "bio_replication_novelty")


def main():
    style()
    fig_transitions()
    fig_loa_by_area()
    fig_loa_by_modality()
    fig_oncology()
    fig_novelty()


if __name__ == "__main__":
    main()
