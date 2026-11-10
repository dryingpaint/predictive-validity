"""Why did drug classes that engaged their target still fail? One figure from the atlas store (lessons/engaged).

Reads codes.csv (the resolved coding of the engaged-but-failed classes) and cases_tiles.csv here and ../dose_derived.csv; writes engaged_no_benefit.{png,pdf,svg}. Each class is one labelled chip under its primary reason; rows tagged
1-3 are Melissa's three reasons, rows tagged + are the additions. Atlas style: 183 mm, Helvetica, Capable palette."""
from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from glance_nature import CAPABLE, INK, MUTED, RC, RULE, STATUS  # noqa: E402

CONTRA, RETRO = STATUS["contra"][0], STATUS["retro"][0]
LAYER = {"A": ("Target hypothesis: the target, with the sign of the intended effect (target selection)", CONTRA),
         "B": ("Modulation: the drug, its dose or where it acted, not the target", RETRO),
         "C": ("Trial: the test, not the target or the drug", CAPABLE), "U": ("Unclear from the record", MUTED)}
CODE = {"A1": "Output moved, disease did not: not causal", "A2": "Causal, but at another disease stage",
        "A3": "Causal only in a subgroup", "A4": "Causal but compensated or bypassed", "A5": "Causal, effect too small to matter",
        "A6": "Right target, wrong direction", "B1": "Engagement not deep or long enough", "B2": "Wrong schedule",
        "B3": "Engaged in blood, not at the disease site", "B4": "Wrong modality", "C1": "Endpoint could not show it",
        "C2": "Trial too short or too small", "C3": "Population or placebo response",
        "C4": "Combination or comparator context", "U": "Unclear from the record"}
HER = {"A1": "1", "A2": "2", "A3": "3"}  # Melissa's three reasons; every other row is an addition
SHORT = {"rheumatoid-arthritis-btk-inhibitors": "BTK inh. · RA", "alzheimer-disease-bace1-inhibitors": "BACE1 inh. · AD",
         "breast-cancer-cdk4-6-inhibitors": "CDK4/6 inh. · breast", "non-small-cell-lung-carcinoma-anti-igf1r-antibodies": "anti-IGF-1R · NSCLC",
         "schizophrenia-pde10a-inhibitors": "PDE10A inh. · schizophr.", "asthma-ptgdr2-antagonists": "DP2 antag. · asthma",
         "allergic-disease-allergen-immunotherapy": "allergen peptides · allergy", "allergic-rhinitis-ptgdr2-antagonists": "DP2 antag. · rhinitis",
         "allergic-rhinitis-allergen-immunotherapy": "allergen IT · rhinitis", "rheumatoid-arthritis-anti-csf2-antibodies": "anti-GM-CSF · RA",
         "type-2-diabetes-mellitus-gpr119-agonists": "GPR119 agon. · T2D", "type-2-diabetes-mellitus-hsd11b1-inhibitors": "11β-HSD1 inh. · T2D",
         "hiv-infectious-disease-hiv-rt-nrti-inhibitors": "new NRTIs · HIV", "hyperlipidemia-hcar2-agonists": "HCAR2 agon. · lipids",
         "alzheimer-disease-hrh3-antagonists": "H3 antag. · AD", "alzheimer-disease-htr6-antagonists": "5-HT6 antag. · AD",
         "migraine-disorder-anti-calca-calcb-cgrp-ligand-antibodies": "anti-CGRP · migraine", "breast-cancer-hsp90aa1-hsp90ab1-inhibitors": "HSP90 inh. · breast",
         "breast-cancer-pi3k-pan-inhibitors": "pan-PI3K inh. · breast", "breast-cancer-pi3k-mtor-inhibitors": "PI3K/mTOR inh. · breast",
         "colorectal-cancer-anti-egfr-antibodies": "new anti-EGFR · CRC", "malignant-pancreatic-neoplasm-map2k1-2-inhibitors": "MEK inh. · pancreatic",
         "myelodysplastic-syndrome-hdac-pan-inhibitors": "HDAC inh. · MDS", "plasma-cell-myeloma-psmb5-inhibitors": "proteasome inh. · myeloma",
         "atopic-eczema-anti-il33-antibodies": "anti-IL-33 · eczema", "asthma-anti-il13-antibodies": "anti-IL-13 · asthma",
         "chronic-obstructive-pulmonary-disease-mapk14-inhibitors": "p38 inh. · COPD"}
W, H = 7.2, 8.5
LABEL_R, CHIP_X0, CHIP_W, CHIP_H, GAP, PER_LINE = 2.45, 2.62, 0.86, 0.24, 0.05, 5
LINE = 0.30


def draw(codes: pd.DataFrame, tiles: pd.DataFrame, dose: pd.DataFrame, out: str) -> None:
    plt.rcParams.update(RC)
    codes = codes.merge(tiles[["slug", "furthest_phase"]], on="slug")
    codes["approved"] = codes.furthest_phase == 4
    order = [c for c in CODE if c in set(codes.primary) or c in HER]  # Melissa's three rows always show, even when empty
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    y = H - 0.42
    ax.text(0.3, y, "Why an engaged target still failed: the 27 atlas classes whose engagement held and whose efficacy was contradicted",
            fontsize=7, fontweight="bold", color=INK, ha="left", va="center")
    tot = codes.primary.str[0].value_counts()
    hers = int(codes.primary.isin(HER).sum())
    y -= 0.24
    ax.text(0.3, y, f"Target hypothesis {tot.get('A', 0)} · Modulation {tot.get('B', 0)} · Trial {tot.get('C', 0)}"
            + (f" · Unclear {tot.get('U', 0)}" if tot.get("U", 0) else "")
            + f"      Rows 1–3 are Melissa's three reasons: {hers} of {len(codes)} classes. Rows marked + are the additions: {len(codes) - hers}.",
            fontsize=5.5, color=INK, ha="left", va="center")
    y -= 0.3
    for layer, (lname, color) in LAYER.items():
        cs = [c for c in order if c[0] == layer]
        if not cs:
            continue
        ax.plot([0.3, W - 0.3], [y + 0.06, y + 0.06], color=RULE, lw=0.5)
        y -= 0.16
        ax.text(0.3, y, lname, fontsize=6, fontweight="bold", color=INK, ha="left", va="center")
        y -= 0.26
        for c in cs:
            g = codes[codes.primary == c].sort_values(["approved", "confidence"])
            n = len(g)
            lines = max((n - 1) // PER_LINE + 1, 1)
            if n == 0:
                ax.text(CHIP_X0, y, "none of the 27", fontsize=5, color=MUTED, ha="left", va="center", style="italic")
            y_top = y
            tag = HER.get(c, "+")
            ax.text(0.42, y_top, tag, fontsize=6.5 if tag != "+" else 6, fontweight="bold", color=INK if tag != "+" else MUTED, ha="center", va="center")
            ax.text(LABEL_R, y_top, f"{CODE[c]}  ({n})", fontsize=5.5, ha="right", va="center", color=INK)
            for i, r in enumerate(g.itertuples()):
                cx = CHIP_X0 + (i % PER_LINE) * (CHIP_W + GAP)
                cy = y_top - (i // PER_LINE) * LINE
                face = "white" if r.approved else color
                ax.add_patch(FancyBboxPatch((cx, cy - CHIP_H / 2), CHIP_W, CHIP_H, boxstyle="round,pad=0,rounding_size=0.04",
                                            facecolor=face, edgecolor=color, linewidth=0.8))
                ax.text(cx + CHIP_W / 2, cy, SHORT[r.slug], fontsize=4.6, ha="center", va="center", color=color if r.approved else "white")
            y -= LINE * lines + 0.1
        y -= 0.08
    # key and footnote
    react = dose.reached.value_counts()
    ky = y - 0.05
    ax.add_patch(FancyBboxPatch((0.3, ky - 0.08), 0.28, 0.16, boxstyle="round,pad=0,rounding_size=0.03", facecolor=CONTRA, edgecolor=CONTRA, linewidth=0.8))
    ax.add_patch(FancyBboxPatch((0.66, ky - 0.08), 0.28, 0.16, boxstyle="round,pad=0,rounding_size=0.03", facecolor="white", edgecolor=CONTRA, linewidth=0.8))
    ax.text(1.02, ky, "filled: class never approved in this disease    hollow: class approved; the contradiction is a stage, a population or one weak member",
            fontsize=5, color=INK, ha="left", va="center")
    foot = [
        "Every class here went into patients, so this is what a positive engagement result was worth, never a sensitivity. One primary reason per class, coded from",
        "the atlas's written reasons by two coders, the second blind to the first; statuses are the atlas's adjudicated statuses. Codes.csv lists each class with its",
        f"secondary reason and rationale. Of the 60 dose tracks the atlas scored \"reached the model's target, not enough\", what had been reached was the regimen",
        f"({react.get('regimen', 0)}), the exposure ({react.get('exposure', 0)}), a PD biomarker ({react.get('pd_biomarker', 0)}) or receptor occupancy ({react.get('occupancy', 0)}): "
        "exposure prediction held, the declared sufficient level did not.",
    ]
    for i, line in enumerate(foot):
        ax.text(0.3, ky - 0.26 - i * 0.15, line, fontsize=4.8, color=MUTED, ha="left", va="center")
    for ext in ("png", "pdf", "svg"):
        fig.savefig(f"{out}.{ext}", dpi=300 if ext == "png" else None)
    plt.close(fig)
    print(f"wrote {out}.png/.pdf/.svg; bottom at {ky - 0.26 - 0.15 * len(foot):.2f} in")


if __name__ == "__main__":
    draw(pd.read_csv(os.path.join(HERE, "codes.csv")), pd.read_csv(os.path.join(HERE, "cases_tiles.csv")),
         pd.read_csv(os.path.join(os.path.dirname(HERE), "dose_derived.csv")), os.path.join(HERE, "engaged_no_benefit"))
