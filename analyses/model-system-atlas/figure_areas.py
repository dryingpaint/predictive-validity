"""Draw the area-level model-system figure: for each disease area and question, the share of programs
entering Phase 2 in each period whose context had a model with each track record at entry.

    .venv/bin/python analyses/model-system-atlas/figure_areas.py

Until the context sample and program join in issue #76 exist, the shares are ILLUSTRATIVE: drawn at
random around a plausible profile per area, to show the design only. Approval rates are the report's
current LOA for all programs by area.
"""

import os

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS = [("Target engagement", "Does the drug hit its target?"), ("Dose", "How much drug is needed?"),
             ("Efficacy", "Will the disease respond?"), ("Safety", "Will people be harmed?")]
PERIODS = ["2008–11", "2012–15", "2016–19"]
TRACK = [  # left to right in each bar
    ("neg", "#0b5f69", "Matched patients, including a known failure"),
    ("same", "#3d9ea6", "Matched patients, same mechanism"),
    ("other", "#a9d6d9", "Matched patients, other mechanism only"),
    ("untested", "#e6e8e6", "Never compared with patients"),
    ("contra", "#c63d26", "Contradicted by patients"),
]
# Report LOA, all programs, by area (current render).
AREAS = [("Hematology", 18.4), ("Metabolic", 10.2), ("Oncology", 9.8), ("Infectious disease", 8.6), ("Autoimmune", 7.5),
         ("Allergy", 6.8), ("Neurology", 6.5), ("Endocrine", 6.3), ("Psychiatry", 6.1), ("Respiratory", 4.6),
         ("Ophthalmology", 4.3), ("Other", 3.8), ("Urology", 3.8), ("Gastroenterology", 3.0), ("Cardiovascular", 2.7)]
INK, MUTED, RULE = "#1b2321", "#5c6763", "#c4cbc7"


def illustrative_shares(rng):
    """shares[area][question][period] -> five shares summing to 1. Illustrative only."""
    out = {}
    for a, (name, loa) in enumerate(AREAS):
        strength = 0.15 + 0.6 * (loa - 2.7) / (18.4 - 2.7)
        out[name] = []
        for q in range(4):
            qscale = [1.0, 0.75, 0.6, 0.35][q]
            per = []
            for p in range(3):
                matched = np.clip(strength * qscale * (0.8 + 0.12 * p) + rng.normal(0, 0.04), 0.02, 0.85)
                contra = np.clip((0.22 - 0.1 * strength) * (0.6 if q == 0 else 1) + rng.normal(0, 0.02), 0.01, 0.4)
                split = rng.dirichlet([2 + 3 * strength, 3, 3 - 2 * strength])
                m = matched * split
                per.append(np.array([m[0], m[1], m[2], max(0.0, 1 - matched - contra), contra]))
            out[name].append(per)
    return out


def main():
    shares = illustrative_shares(np.random.default_rng(76))
    row_h, head_h, foot_h = 0.62, 2.15, 0.55
    W = 14.5
    fig_h = head_h + row_h * len(AREAS) + foot_h
    fig = plt.figure(figsize=(W, fig_h), dpi=200)
    fy = lambda inches_from_top: 1 - inches_from_top / fig_h
    label_w, loa_w, gap = 0.145, 0.075, 0.012
    col_w = (1 - label_w - loa_w - 0.012 - gap * 4) / 4

    fig.text(0.012, fy(0.3), "How much drug development rests on a model with a track record", fontsize=17, fontweight="bold", color=INK, va="top")
    fig.text(0.012, fy(0.66), "Programs entering Phase 2, by the track record their context's best model had at entry. "
             "ILLUSTRATIVE NUMBERS: this shows the design, not data.", fontsize=9.5, color=MUTED, va="top")
    handles = [Patch(facecolor=c, edgecolor="none", label=l) for _, c, l in TRACK]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.008, fy(0.9)), ncol=5, frameon=False,
               fontsize=8.8, handlelength=1.4, handleheight=0.9, columnspacing=1.4, labelcolor=INK)

    matrix_h = row_h * len(AREAS)
    base = fy(head_h + matrix_h)
    for j, (title, q) in enumerate(QUESTIONS):
        left = label_w + j * (col_w + gap)
        fig.text(left, fy(head_h - 0.42), title, fontsize=10.5, fontweight="bold", color=INK, va="bottom")
        fig.text(left, fy(head_h - 0.27), q, fontsize=8.2, color=MUTED, va="bottom")
        ax = fig.add_axes([left, base, col_w, matrix_h / fig_h])
        ax.set_xlim(0, 1); ax.set_ylim(len(AREAS), 0); ax.axis("off")
        for i, (name, _) in enumerate(AREAS):
            for p in range(3):
                y = i + 0.1 + p * 0.26
                x = 0.0
                for (key, color, _), s in zip(TRACK, shares[name][j][p]):
                    ax.add_patch(Rectangle((x, y), s, 0.2, facecolor=color, edgecolor="white", lw=0.6))
                    x += s
                if j == 0:
                    pass
            if i < len(AREAS) - 1:
                ax.axhline(i + 1, color=RULE, lw=0.5)
        for xv, lab in ((0, "0%"), (0.5, "50%"), (1, "100%")):
            ax.text(xv, -0.08, lab, fontsize=6.8, color=MUTED, ha="center" if 0 < xv < 1 else ("left" if xv == 0 else "right"), va="bottom")

    lab = fig.add_axes([0, base, label_w, matrix_h / fig_h])
    lab.set_xlim(0, 1); lab.set_ylim(len(AREAS), 0); lab.axis("off")
    for i, (name, _) in enumerate(AREAS):
        lab.text(0.08, i + 0.3, name, fontsize=9, fontweight="bold", color=INK, va="center")
        for p, per in enumerate(PERIODS):
            lab.text(0.96, i + 0.2 + p * 0.26, per, fontsize=6.6, color=MUTED, ha="right", va="center")
        if i < len(AREAS) - 1:
            lab.axhline(i + 1, xmin=0.06, color=RULE, lw=0.5)

    left = label_w + 4 * (col_w + gap)
    fig.text(left, fy(head_h - 0.42), "Approval", fontsize=10.5, fontweight="bold", color=INK, va="bottom")
    fig.text(left, fy(head_h - 0.27), "LOA, all programs", fontsize=8.2, color=MUTED, va="bottom")
    lax = fig.add_axes([left, base, loa_w, matrix_h / fig_h])
    lax.set_xlim(0, 25); lax.set_ylim(len(AREAS), 0); lax.axis("off")
    for i, (name, loa) in enumerate(AREAS):
        lax.add_patch(Rectangle((0, i + 0.38), loa, 0.24, facecolor="#5c6763", edgecolor="none"))
        lax.text(loa + 0.6, i + 0.5, f"{loa:.1f}%", fontsize=7.4, color=INK, va="center")
        if i < len(AREAS) - 1:
            lax.axhline(i + 1, color=RULE, lw=0.5)

    fig.text(0.012, fy(fig_h - 0.14),
             "Each cell: one bar per period of Phase 2 entry; bar length = 100% of that area's programs. A program's context is its disease, the patients its cause defines, "
             "and its drug class.\nRows sorted by approval rate. Status rules and collection protocol: issue #76. Real shares replace the illustrative ones once the context sample is joined to programs.",
             fontsize=7.6, color=MUTED, va="bottom", linespacing=1.4)
    fig.text(0.5, fy(head_h + matrix_h / 2), "ILLUSTRATIVE", fontsize=90, color="#1b2321", alpha=0.05, ha="center", va="center", rotation=20, fontweight="bold")
    out = os.path.join(HERE, "atlas_areas.png")
    fig.savefig(out, facecolor="white")
    print(out)


if __name__ == "__main__":
    main()
