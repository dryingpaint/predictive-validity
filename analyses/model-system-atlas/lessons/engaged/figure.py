"""Reasons recorded for efficacy failure after confirmed target engagement: the figure (lessons/engaged).

Reads codes.csv (the resolved coding of the classes whose engagement headline matched and efficacy headline was
contradicted) and cases_tiles.csv, both written here; writes engaged_no_benefit.{png,pdf,svg}. Each class is one chip
under the primary reason the atlas record gives for the failure, in three layers (target hypothesis, modulation,
trial) plus "not stated". Journal format: 183 mm wide, Helvetica 4.5-7 pt, the atlas palette (glance_nature)."""
from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from glance_nature import INK, MUTED, RC, RULE, STATUS

CONTRA, RETRO, NEG = STATUS["contra"][0], STATUS["retro"][0], STATUS["neg"][0]
LAYER = {"A": ("Target hypothesis: the target and the direction of the intended effect", CONTRA),
         "B": ("Modulation: the drug, its dose, or the site of engagement", RETRO),
         "C": ("Trial: endpoint, population, or treatment context", NEG),
         "U": ("Not stated in the record", MUTED)}
CODE = {"A1": "Not causal: output moved, disease did not", "A2": "Causal at another disease stage",
        "A3": "Causal only in a subgroup", "A4": "Causal but compensated or bypassed", "A5": "Causal, effect too small",
        "A6": "Wrong direction of modulation", "B1": "Insufficient degree or duration of engagement", "B2": "Wrong schedule",
        "B3": "Engagement shown outside the disease site", "B4": "Unsuitable modality", "C1": "Endpoint could not show the effect",
        "C2": "Trial too short or underpowered", "C3": "Population or placebo response", "C4": "Combination or comparator context",
        "U": "Not stated in the record"}
IN_DRAFT = {"A1", "A2", "A3"}  # the three categories already in the manuscript draft; marked with a diamond
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
W = 7.2
LABEL_R, CHIP_X0, CHIP_W, CHIP_H, GAP, PER_LINE, LINE = 2.12, 2.24, 0.88, 0.23, 0.05, 5, 0.29


def chip(ax, x: float, y: float, text: str, color: str, hollow: bool) -> None:
    ax.add_patch(FancyBboxPatch((x, y - CHIP_H / 2), CHIP_W, CHIP_H, boxstyle="round,pad=0,rounding_size=0.035",
                                facecolor="white" if hollow else color, edgecolor=color, linewidth=0.8))
    ax.text(x + CHIP_W / 2, y, text, fontsize=4.5, ha="center", va="center", color=color if hollow else "white")


def rows_for(codes: pd.DataFrame) -> list[str]:
    """The codes drawn, in codebook order: every code used plus the three draft categories, shown even when empty."""
    return [c for c in CODE if c in set(codes.primary) or c in IN_DRAFT]


def layout_height(codes: pd.DataFrame) -> float:
    """The figure height the rows need, in inches."""
    order = rows_for(codes)
    h = 0.35 + 0.34 + 0.75
    for layer in LAYER:
        cs = [c for c in order if c[0] == layer]
        if not cs:
            continue
        h += 0.14 + 0.27 + 0.06
        for c in cs:
            n = int((codes.primary == c).sum())
            h += LINE * max((n - 1) // PER_LINE + 1, 1) + 0.09
    return round(h, 1)


def draw(codes: pd.DataFrame, tiles: pd.DataFrame, out: str) -> str:
    """Draws the figure and returns the PNG path."""
    plt.rcParams.update(RC)
    codes = codes.merge(tiles[["slug", "furthest_phase"]], on="slug")
    codes["approved"] = codes.furthest_phase.astype(int) == 4
    order = rows_for(codes)
    H = layout_height(codes)
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    y = H - 0.35
    ax.text(0.25, y, f"Primary reason recorded for efficacy failure in the {len(codes)} drug classes whose target engagement was confirmed in patients",
            fontsize=7, ha="left", va="center", color=INK)
    y -= 0.34
    for layer, (lname, color) in LAYER.items():
        cs = [c for c in order if c[0] == layer]
        if not cs:
            continue
        ax.plot([0.25, W - 0.25], [y + 0.08, y + 0.08], color=RULE, lw=0.5)
        y -= 0.14
        ax.text(0.25, y, lname, fontsize=6, fontweight="bold", color=INK, ha="left", va="center")
        ax.text(W - 0.25, y, f"n = {int(codes.primary.str[0].eq(layer).sum())}", fontsize=6, color=INK, ha="right", va="center")
        y -= 0.27
        for c in cs:
            g = codes[codes.primary == c].sort_values(["approved", "slug"])
            n = len(g)
            if c in IN_DRAFT:
                ax.text(0.28, y, "◆", fontsize=5, color=INK, ha="center", va="center")
            ax.text(LABEL_R, y, f"{CODE[c]} ({n})", fontsize=5.5, ha="right", va="center", color=INK)
            if n == 0:
                ax.text(CHIP_X0, y, "none", fontsize=5, color=MUTED, ha="left", va="center", style="italic")
            for i, r in enumerate(g.itertuples()):
                chip(ax, CHIP_X0 + (i % PER_LINE) * (CHIP_W + GAP), y - (i // PER_LINE) * LINE, SHORT.get(r.slug, r.slug), color, r.approved)
            y -= LINE * max((n - 1) // PER_LINE + 1, 1) + 0.09
        y -= 0.06
    ky = y - 0.08
    ax.add_patch(FancyBboxPatch((0.25, ky - 0.075), 0.26, 0.15, boxstyle="round,pad=0,rounding_size=0.03", facecolor=CONTRA, edgecolor=CONTRA, linewidth=0.8))
    ax.text(0.57, ky, "class never approved in this disease", fontsize=5.5, color=INK, ha="left", va="center")
    ax.add_patch(FancyBboxPatch((2.35, ky - 0.075), 0.26, 0.15, boxstyle="round,pad=0,rounding_size=0.03", facecolor="white", edgecolor=CONTRA, linewidth=0.8))
    ax.text(2.67, ky, "class approved in this disease; the contradicted entry concerns a stage, a population, or one member", fontsize=5.5, color=INK,
            ha="left", va="center")
    ax.text(0.38, ky - 0.24, "◆", fontsize=5, color=INK, ha="center", va="center")
    ax.text(0.57, ky - 0.24, "category present in the current manuscript draft; the remaining categories are added here", fontsize=5.5, color=INK,
            ha="left", va="center")
    for ext in ("png", "pdf", "svg"):
        fig.savefig(f"{out}.{ext}", dpi=300 if ext == "png" else None)
    plt.close(fig)
    return f"{out}.png"


if __name__ == "__main__":
    print("wrote", draw(pd.read_csv(os.path.join(HERE, "codes.csv")), pd.read_csv(os.path.join(HERE, "cases_tiles.csv")),
                        os.path.join(HERE, "engaged_no_benefit")))
