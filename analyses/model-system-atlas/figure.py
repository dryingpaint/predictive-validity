"""Draw the model-system atlas: for each context of use and each decision, the status of the best
available preclinical model in every year from 1985 to 2026.

    .venv/bin/python analyses/model-system-atlas/figure.py

Reads one JSON file per context from contexts/ and writes atlas.png beside this file. Rows are grouped by
the disease area the report uses (preclin.mondo_bio_area for the context's MONDO term). Each context
file holds `cells`: for each decision, a list of {year, status, note, src} entries, each the year the
best model reached that status. A cell's status in a year is that of the latest entry at or before it.
Each tile names the cell's best model, gives the year and reason for its latest status with the source, and shows a strip
of its status by year.
"""

import glob
import json
import os

import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
YEAR0, YEAR1 = 1985, 2026
DECISIONS = [("engagement", "Target engagement"), ("dose", "Dose"), ("efficacy", "Efficacy"), ("safety", "Safety")]
QUESTIONS = {"engagement": "Does the drug hit its target?", "dose": "How much drug is needed?",
             "efficacy": "Will the disease respond?", "safety": "Will people be harmed?"}
STATUS = {
    "neg": ("#0b5f69", "Matched patients, including a known failure"),
    "same": ("#3d9ea6", "Matched patients, same mechanism"),
    "other": ("#a9d6d9", "Matched patients, other mechanism only"),
    "untested": ("#e6e8e6", "Never compared with patients"),
    "contra": ("#c63d26", "Contradicted by patients"),
}
TILE, TILE_EMPTY = "#f1f3f1", "#f8f9f8"
INK, MUTED, RULE = "#1b2321", "#5c6763", "#c4cbc7"


def load():
    rows = []
    for path in glob.glob(os.path.join(HERE, "contexts", "*.json")):
        with open(path) as f:
            rows.append(json.load(f))
    return sorted(rows, key=lambda r: r["order"])


def spans(history):
    """(start, end, status) runs covering YEAR0..YEAR1+1 for one cell."""
    out, cur, start = [], "untested", YEAR0
    for h in sorted(history, key=lambda h: h["year"]):
        y = max(h["year"], YEAR0)
        if y > start:
            out.append((start, y, cur))
        cur, start = h["status"], y
    out.append((start, YEAR1 + 1, cur))
    return out


def main():
    rows = load()
    layout = []  # ("area", name) or ("ctx", row), each with its height in inches
    for r in rows:
        if not any(k == "area" and v == r["area"] for k, v, _ in layout):
            layout.append(("area", r["area"], 0.42))
        layout.append(("ctx", r, 0.9))

    head_h, foot_h = 2.1, 0.45
    matrix_h = sum(h for _, _, h in layout)
    W = 14.5
    fig_h = head_h + matrix_h + foot_h
    fig = plt.figure(figsize=(W, fig_h), dpi=200)
    fy = lambda inches_from_top: 1 - inches_from_top / fig_h
    label_w, gap = 0.235, 0.008
    col_w = (1 - label_w - 0.012 - gap * 3) / 4

    fig.text(0.012, fy(0.3), "Where preclinical models predict, and since when", fontsize=17, fontweight="bold", color=INK, va="top")
    fig.text(0.012, fy(0.66),
             "For each disease, patient group and drug class: the best preclinical model for each question, why it has its status, "
             "and how that status changed from 1985 to 2026.",
             fontsize=9.3, color=MUTED, va="top")
    handles = [Patch(facecolor=c, edgecolor="none", label=l) for k, (c, l) in STATUS.items()]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.008, fy(0.9)), ncol=5, frameon=False,
               fontsize=9, handlelength=1.4, handleheight=0.9, columnspacing=1.6, labelcolor=INK)

    lab = fig.add_axes([0, fy(head_h + matrix_h), label_w, (matrix_h) / fig_h])
    lab.set_xlim(0, 1); lab.set_ylim(matrix_h, 0); lab.axis("off")
    axes = []
    for j, (key, title) in enumerate(DECISIONS):
        ax = fig.add_axes([label_w + j * (col_w + gap), fy(head_h + matrix_h), col_w, matrix_h / fig_h])
        ax.set_xlim(0, 1); ax.set_ylim(matrix_h, 0); ax.axis("off")
        fig.text(label_w + j * (col_w + gap), fy(head_h - 0.42), title, fontsize=10.5, fontweight="bold", color=INK, va="bottom")
        fig.text(label_w + j * (col_w + gap), fy(head_h - 0.27), QUESTIONS[key], fontsize=8.2, color=MUTED, va="bottom")
        axes.append((key, ax))

    x0, x1 = 0.035, 0.965
    yx = lambda yr: x0 + (x1 - x0) * (yr - YEAR0) / (YEAR1 + 1 - YEAR0)
    top = 0.0
    for kind, item, h in layout:
        if kind == "area":
            lab.text(0.05, top + h * 0.62, item, fontsize=10, fontweight="bold", color=INK, va="center")
            top += h
            continue
        t0, t1 = top + 0.05, top + h - 0.05
        lab.text(0.07, t0 + 0.12, item["disease"], fontsize=8.6, fontweight="bold", color=INK, va="center")
        lab.text(0.07, t0 + 0.3, item["population"], fontsize=8, color=INK, va="center")
        lab.text(0.07, t0 + 0.48, item["mechanism"], fontsize=7, color=MUTED, va="center")
        for key, ax in axes:
            hist = sorted(item["cells"].get(key, []), key=lambda e: e["year"])
            ax.add_patch(Rectangle((0, t0), 1, t1 - t0, facecolor=TILE if hist else TILE_EMPTY, edgecolor="none"))
            if not hist:
                continue
            last = hist[-1]
            ax.text(x0, t0 + 0.15, last.get("model", ""), fontsize=7.6, fontweight="bold", color=INK, va="center")
            ax.text(x0, t0 + 0.33, f"{last['year']}: {last.get('reason', last['short'])}", fontsize=6.9, color=INK, va="center")
            ax.text(x0, t0 + 0.5, last.get("srcLabel", ""), fontsize=6.4, color=MUTED, va="center", style="italic")
            sy, sh = t1 - 0.17, 0.1
            for a, b, st in spans(hist):
                ax.add_patch(Rectangle((yx(a), sy), yx(b) - yx(a), sh, facecolor=STATUS[st][0], edgecolor="none"))
            for e in hist[:-1]:
                ax.plot([yx(e["year"])] * 2, [sy - 0.03, sy + sh + 0.03], color=TILE, lw=1.2)
        top += h

    for key, ax in axes:
        for yr in (1990, 2000, 2010, 2020):
            ax.text(yx(yr), -0.04, str(yr), fontsize=6.6, color=MUTED, ha="center", va="bottom")

    fig.text(0.012, fy(fig_h - 0.12),
             "Strip ticks mark earlier changes of status. Status is a judgement under the rules in issue #76; the earlier changes, full notes and links are in contexts/*.json. "
             "Hand-curated seed of 15 contexts, not a sample.",
             fontsize=7.6, color=MUTED, va="bottom")
    out = os.path.join(HERE, "atlas.png")
    fig.savefig(out, facecolor="white")
    print(out)


if __name__ == "__main__":
    main()
