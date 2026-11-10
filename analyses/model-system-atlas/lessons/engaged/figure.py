"""Reasons recorded for efficacy failure after confirmed target engagement: the figure (lessons/engaged).

Reads codes.csv (the resolved coding of the classes whose engagement headline matched and efficacy headline was
contradicted), cases_tiles.csv, and ../dose_derived.csv; writes engaged_no_benefit.{png,pdf,svg}. Panel a places each
class under the primary reason the atlas record gives for the failure, in three layers (target hypothesis, modulation,
trial). Panel b gives the 60 dose tracks scored "target reached, not enough" by the kind of target that was reached.
Journal format: 183 mm wide, Helvetica 5-7 pt, the atlas palette (glance_nature)."""
from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from glance_nature import CAPABLE, INK, MUTED, RC, RULE, STATUS  # noqa: E402

CONTRA, RETRO = STATUS["contra"][0], STATUS["retro"][0]
LAYER = {"A": ("Target hypothesis: the target and the direction of the intended effect", CONTRA),
         "B": ("Modulation: the drug, its dose, or the site of engagement", RETRO),
         "C": ("Trial: endpoint, population, or treatment context", CAPABLE),
         "U": ("Not stated in the record", MUTED)}
CODE = {"A1": "Not causal: output moved, disease did not", "A2": "Causal at another disease stage",
        "A3": "Causal only in a subgroup", "A4": "Causal but compensated or bypassed", "A5": "Causal, effect too small",
        "A6": "Wrong direction of modulation", "B1": "Insufficient degree or duration of engagement", "B2": "Wrong schedule",
        "B3": "Engagement shown outside the disease site", "B4": "Unsuitable modality", "C1": "Endpoint could not show the effect",
        "C2": "Trial too short or underpowered", "C3": "Population or placebo response", "C4": "Combination or comparator context",
        "U": "Not stated in the record"}
IN_DRAFT = {"A1", "A2", "A3"}  # the three categories already in the manuscript draft; marked in panel a
SHORT = {"rheumatoid-arthritis-btk-inhibitors": "BTK inhibitors · RA", "alzheimer-disease-bace1-inhibitors": "BACE1 inhibitors · AD",
         "breast-cancer-cdk4-6-inhibitors": "CDK4/6 inhibitors · breast", "non-small-cell-lung-carcinoma-anti-igf1r-antibodies": "anti-IGF-1R · NSCLC",
         "schizophrenia-pde10a-inhibitors": "PDE10A inhibitors · SCZ", "asthma-ptgdr2-antagonists": "DP2 antagonists · asthma",
         "allergic-disease-allergen-immunotherapy": "allergen peptides · allergy", "allergic-rhinitis-ptgdr2-antagonists": "DP2 antagonists · rhinitis",
         "allergic-rhinitis-allergen-immunotherapy": "allergen IT · rhinitis", "rheumatoid-arthritis-anti-csf2-antibodies": "anti-GM-CSF · RA",
         "type-2-diabetes-mellitus-gpr119-agonists": "GPR119 agonists · T2D", "type-2-diabetes-mellitus-hsd11b1-inhibitors": "11β-HSD1 inh. · T2D",
         "hiv-infectious-disease-hiv-rt-nrti-inhibitors": "NRTIs (new) · HIV", "hyperlipidemia-hcar2-agonists": "HCAR2 agonists · lipids",
         "alzheimer-disease-hrh3-antagonists": "H3 antagonists · AD", "alzheimer-disease-htr6-antagonists": "5-HT6 antagonists · AD",
         "migraine-disorder-anti-calca-calcb-cgrp-ligand-antibodies": "anti-CGRP · migraine", "breast-cancer-hsp90aa1-hsp90ab1-inhibitors": "HSP90 inhibitors · breast",
         "breast-cancer-pi3k-pan-inhibitors": "pan-PI3K inhibitors · breast", "breast-cancer-pi3k-mtor-inhibitors": "PI3K/mTOR inh. · breast",
         "colorectal-cancer-anti-egfr-antibodies": "anti-EGFR (new) · CRC", "malignant-pancreatic-neoplasm-map2k1-2-inhibitors": "MEK inhibitors · pancreas",
         "myelodysplastic-syndrome-hdac-pan-inhibitors": "HDAC inhibitors · MDS", "plasma-cell-myeloma-psmb5-inhibitors": "proteasome inh. · myeloma",
         "atopic-eczema-anti-il33-antibodies": "anti-IL-33 · atopic eczema", "asthma-anti-il13-antibodies": "anti-IL-13 · asthma",
         "chronic-obstructive-pulmonary-disease-mapk14-inhibitors": "p38 inhibitors · COPD"}
REACHED = [("regimen", "Regimen"), ("exposure", "Exposure"), ("pd_biomarker", "PD biomarker"), ("occupancy", "Receptor occupancy")]
W, H = 7.2, 7.4
LABEL_R, CHIP_X0, CHIP_W, CHIP_H, GAP, PER_LINE, LINE = 2.12, 2.24, 0.83, 0.23, 0.045, 4, 0.29
PANEL_B_X = 5.78


def chip(ax, x, y, text, color, hollow):
    ax.add_patch(FancyBboxPatch((x, y - CHIP_H / 2), CHIP_W, CHIP_H, boxstyle="round,pad=0,rounding_size=0.035",
                                facecolor="white" if hollow else color, edgecolor=color, linewidth=0.8))
    ax.text(x + CHIP_W / 2, y, text, fontsize=4.5, ha="center", va="center", color=color if hollow else "white")


def panel_a(ax, codes: pd.DataFrame, top: float) -> float:
    """Each class under its primary reason; returns the y where the panel ends."""
    order = [c for c in CODE if c in set(codes.primary) or c in IN_DRAFT]
    y = top
    ax.text(0.25, y, "a", fontsize=8, fontweight="bold", ha="left", va="center")
    ax.text(0.45, y, f"Primary reason recorded for efficacy failure in the {len(codes)} classes whose target engagement was confirmed in patients",
            fontsize=7, ha="left", va="center", color=INK)
    y -= 0.34
    for layer, (lname, color) in LAYER.items():
        cs = [c for c in order if c[0] == layer]
        if not cs:
            continue
        n_layer = int(codes.primary.str[0].eq(layer).sum())
        ax.plot([0.25, PANEL_B_X - 0.25], [y + 0.08, y + 0.08], color=RULE, lw=0.5)
        y -= 0.14
        ax.text(0.25, y, lname, fontsize=6, fontweight="bold", color=INK, ha="left", va="center")
        ax.text(PANEL_B_X - 0.25, y, f"n = {n_layer}", fontsize=6, color=INK, ha="right", va="center")
        y -= 0.27
        for c in cs:
            g = codes[codes.primary == c].sort_values(["approved", "slug"])
            n = len(g)
            lines = max((n - 1) // PER_LINE + 1, 1)
            if c in IN_DRAFT:
                ax.text(0.28, y, "◆", fontsize=5, color=INK, ha="center", va="center")
            ax.text(LABEL_R, y, f"{CODE[c]} ({n})", fontsize=5.5, ha="right", va="center", color=INK)
            if n == 0:
                ax.text(CHIP_X0, y, "none", fontsize=5, color=MUTED, ha="left", va="center", style="italic")
            for i, r in enumerate(g.itertuples()):
                chip(ax, CHIP_X0 + (i % PER_LINE) * (CHIP_W + GAP), y - (i // PER_LINE) * LINE, SHORT[r.slug], color, r.approved)
            y -= LINE * lines + 0.09
        y -= 0.06
    return y


def panel_b(ax, dose: pd.DataFrame, top: float) -> None:
    """The 60 derived dose contradictions by the kind of target that had been reached; labels above the bars so the
    panel stays inside its own column."""
    x0, w = PANEL_B_X, 7.2 - 0.3 - PANEL_B_X
    y = top
    ax.text(PANEL_B_X, y, "b", fontsize=8, fontweight="bold", ha="left", va="center")
    ax.text(PANEL_B_X + 0.2, y, "Dose tracks scored", fontsize=6.5, ha="left", va="center")
    ax.text(PANEL_B_X + 0.2, y - 0.16, "\"reached, not enough\"", fontsize=6.5, ha="left", va="center")
    ax.text(PANEL_B_X + 0.2, y - 0.32, f"by target reached (n = {len(dose)})", fontsize=6.5, ha="left", va="center")
    y -= 0.66
    counts = dose.reached.value_counts()
    vmax = counts.max()
    for key_, label in REACHED:
        n = int(counts.get(key_, 0))
        ax.text(x0, y, label, fontsize=5.5, ha="left", va="center", color=INK)
        bw = (w - 0.3) * n / vmax
        ax.add_patch(Rectangle((x0, y - 0.3), bw, 0.17, facecolor=CONTRA, edgecolor="none"))
        ax.text(x0 + bw + 0.05, y - 0.215, str(n), fontsize=5.5, ha="left", va="center", color=INK)
        y -= 0.56
    base = y + 0.2
    ax.plot([x0, x0 + (w - 0.3)], [base, base], color=MUTED, lw=0.5)
    for v in (0, 10, 20):
        xv = x0 + (w - 0.3) * v / vmax
        ax.plot([xv, xv], [base, base - 0.04], color=MUTED, lw=0.5)
        ax.text(xv, base - 0.08, str(v), fontsize=5, ha="center", va="top", color=INK)
    ax.text(x0 + (w - 0.3) / 2, base - 0.24, "tracks", fontsize=5.5, ha="center", va="top", color=INK)


def key(ax, y: float) -> None:
    ax.add_patch(FancyBboxPatch((0.25, y - 0.075), 0.26, 0.15, boxstyle="round,pad=0,rounding_size=0.03", facecolor=CONTRA, edgecolor=CONTRA, linewidth=0.8))
    ax.text(0.57, y, "class never approved in this disease", fontsize=5.5, color=INK, ha="left", va="center")
    ax.add_patch(FancyBboxPatch((2.35, y - 0.075), 0.26, 0.15, boxstyle="round,pad=0,rounding_size=0.03", facecolor="white", edgecolor=CONTRA, linewidth=0.8))
    ax.text(2.67, y, "class approved in this disease; the contradiction is a stage, a population, or one member", fontsize=5.5, color=INK, ha="left", va="center")
    ax.text(0.38, y - 0.24, "◆", fontsize=5, color=INK, ha="center", va="center")
    ax.text(0.57, y - 0.24, "category present in the current manuscript draft; the remaining categories are added here", fontsize=5.5, color=INK, ha="left", va="center")


def draw(codes: pd.DataFrame, tiles: pd.DataFrame, dose: pd.DataFrame, out: str) -> None:
    plt.rcParams.update(RC)
    codes = codes.merge(tiles[["slug", "furthest_phase"]], on="slug")
    codes["approved"] = codes.furthest_phase == 4
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    top = H - 0.35
    y_end = panel_a(ax, codes, top)
    panel_b(ax, dose, top)
    key(ax, y_end - 0.1)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(f"{out}.{ext}", dpi=300 if ext == "png" else None)
    plt.close(fig)
    print(f"wrote {out}.png/.pdf/.svg; key at {y_end - 0.1:.2f} in")


if __name__ == "__main__":
    draw(pd.read_csv(os.path.join(HERE, "codes.csv")), pd.read_csv(os.path.join(HERE, "cases_tiles.csv")),
         pd.read_csv(os.path.join(os.path.dirname(HERE), "dose_derived.csv")), os.path.join(HERE, "engaged_no_benefit"))
