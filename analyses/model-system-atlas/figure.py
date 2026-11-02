"""Draw the model-system atlas: for each context of use and each decision, the status of the best
available preclinical model in every year from 1985 to 2026.

    .venv/bin/python analyses/model-system-atlas/figure.py

Reads one JSON file per context from contexts/ and writes atlas.png beside this file. Each context
file holds `cells`: for each decision, a list of {year, status, note, src} entries, each the year the
best model reached that status. A cell's status in a year is that of the latest entry at or before it.
"""

import glob
import json
import os

import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
YEAR0, YEAR1 = 1985, 2026
DECISIONS = [("engagement", "Target engagement"), ("dose", "Dose"), ("efficacy", "Efficacy"), ("safety", "Safety")]
STATUS = {
    "cal": ("#00707d", "Calibrated against clinical outcomes"),
    "cause": ("#11a9b3", "Carries the human cause, not calibrated"),
    "pheno": ("#d6982a", "Phenotype only"),
    "misled": ("#c63d26", "Misled in this context"),
    "none": ("#ebedeb", "No model, or not assessed"),
}
INK, MUTED, RULE = "#1b2321", "#5c6763", "#c4cbc7"


def load():
    rows = []
    for path in glob.glob(os.path.join(HERE, "contexts", "*.json")):
        with open(path) as f:
            rows.append(json.load(f))
    return sorted(rows, key=lambda r: r["order"])


def spans(history):
    """(start, end, status) runs covering YEAR0..YEAR1+1 for one cell."""
    out, cur, start = [], "none", YEAR0
    for h in sorted(history, key=lambda h: h["year"]):
        y = max(h["year"], YEAR0)
        if y > start:
            out.append((start, y, cur))
        cur, start = h["status"], y
    out.append((start, YEAR1 + 1, cur))
    return out


def main():
    rows = load()
    layout = []  # ("area", name) or ("ctx", row)
    for r in rows:
        if not any(k == "area" and v == r["area"] for k, v in layout):
            layout.append(("area", r["area"]))
        layout.append(("ctx", r))

    row_h = 0.36
    fig_h = 2.1 + row_h * len(layout)
    fig = plt.figure(figsize=(13.5, fig_h), dpi=200)
    top = 1 - 1.9 / fig_h
    bottom = 0.55 / fig_h
    label_w = 0.31
    gap = 0.012
    panel_w = (1 - label_w - 0.02 - gap * 3) / 4

    fig.text(0.012, 1 - 0.32 / fig_h, "Where preclinical models predict, and since when", fontsize=17, fontweight="bold", color=INK, va="top")
    fig.text(0.012, 1 - 0.68 / fig_h,
             "Best available model for each context of use (disease × the patients its cause defines × mechanism) and decision, by year. "
             "Hand-curated seed of 15 contexts; every status change cites a source.",
             fontsize=9.5, color=MUTED, va="top")
    handles = [Patch(facecolor=c, edgecolor="none", label=l) for c, l in STATUS.values()]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.008, 1 - 0.92 / fig_h), ncol=5, frameon=False,
               fontsize=9, handlelength=1.4, handleheight=1.0, columnspacing=1.6, labelcolor=INK)

    n = len(layout)
    for j, (key, title) in enumerate(DECISIONS):
        left = label_w + j * (panel_w + gap)
        ax = fig.add_axes([left, bottom, panel_w, top - bottom])
        ax.set_xlim(YEAR0, YEAR1 + 1)
        ax.set_ylim(n, 0)
        ax.set_title(title, fontsize=10.5, fontweight="bold", color=INK, loc="left", pad=16)
        ax.xaxis.tick_top()
        ax.set_xticks([1990, 2000, 2010, 2020])
        ax.tick_params(axis="x", labelsize=8, colors=MUTED, length=0, pad=2)
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        for i, (kind, item) in enumerate(layout):
            if kind == "area":
                continue
            for a, b, st in spans(item["cells"].get(key, [])):
                ax.add_patch(Rectangle((a, i + 0.14), b - a, 0.72, facecolor=STATUS[st][0], edgecolor="none", zorder=2))
            for h in item["cells"].get(key, []):
                if YEAR0 < h["year"] <= YEAR1:
                    ax.add_patch(Rectangle((h["year"] - 0.15, i + 0.14), 0.3, 0.72, facecolor="white", edgecolor="none", zorder=4))

    lab = fig.add_axes([0.0, bottom, label_w - 0.008, top - bottom])
    lab.set_xlim(0, 1)
    lab.set_ylim(n, 0)
    lab.axis("off")
    for i, (kind, item) in enumerate(layout):
        if kind == "area":
            lab.text(0.04, i + 0.62, item, fontsize=10, fontweight="bold", color=INK, va="center")
            continue
        lab.text(0.07, i + 0.42, f"{item['disease']}, {item['population']}", fontsize=8.6, color=INK, va="center")
        lab.text(0.07, i + 0.80, item["mechanism"], fontsize=7.2, color=MUTED, va="center")

    fig.text(0.012, 0.18 / fig_h,
             "A white notch marks the year a cell's status changed. Status is a judgement per context; sources and notes are in contexts/*.json. "
             "Program counts and approval rates per context come later from the Predictive Validity database.",
             fontsize=7.8, color=MUTED, va="bottom")
    out = os.path.join(HERE, "atlas.png")
    fig.savefig(out, facecolor="white")
    print(out)


if __name__ == "__main__":
    main()
