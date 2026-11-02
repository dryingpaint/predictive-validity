"""Draw the model-system frontier: for each context and question, how far the best model's track record
reached by 1995, 2005, 2015 and 2026. Rows are contexts; the line joining them is the frontier.

    .venv/bin/python analyses/model-system-atlas/figure_frontier.py

Reads the same contexts/*.json as figure.py and writes frontier.png beside this file.
"""

import os

import matplotlib.pyplot as plt

from figure import DECISIONS, QUESTIONS, load, spans

HERE = os.path.dirname(os.path.abspath(__file__))
LEVEL = {"contra": -1, "untested": 0, "other": 1, "same": 2, "neg": 3}
TICKS = [(-1, "Contra-\ndicted"), (0, "Never\ncompared"), (1, "Other\nmechanism"), (2, "Same\nmechanism"), (3, "Incl. a\nfailure")]
YEARS = [(1995, "#d4e7e8"), (2005, "#9ccacd"), (2015, "#4f9fa6"), (2026, "#0b5f69")]
INK, MUTED, RULE, RED = "#1b2321", "#5c6763", "#c4cbc7", "#c63d26"


def level_at(history, year):
    lv = 0
    for a, _, st in spans(history):
        if a <= year:
            lv = LEVEL[st]
    return lv


def main():
    rows = load()
    layout, areas = [], []
    for r in rows:
        if not areas or areas[-1][0] != r["area"]:
            areas.append((r["area"], len(layout)))
        layout.append(r)
    n = len(layout)
    row_h, head_h, foot_h = 0.42, 2.25, 0.55
    fig_h = head_h + row_h * n + foot_h
    fig = plt.figure(figsize=(14.5, fig_h), dpi=200)
    fy = lambda inches: 1 - inches / fig_h
    label_w, gap = 0.25, 0.02
    col_w = (1 - label_w - 0.015 - gap * 3) / 4
    bottom, height = fy(head_h + row_h * n), row_h * n / fig_h

    fig.text(0.012, fy(0.3), "The jagged frontier of preclinical prediction", fontsize=17, fontweight="bold", color=INK, va="top")
    fig.text(0.012, fy(0.66), "How far each context's best model had got against patient results by 1995, 2005, 2015 and 2026. "
             "Further right = a stronger track record; red = contradicted by patients.", fontsize=9.5, color=MUTED, va="top")
    for k, (yr, c) in enumerate(YEARS):
        fig.add_artist(plt.Line2D([0.012 + k * 0.075, 0.032 + k * 0.075], [fy(1.08), fy(1.08)], color=c, lw=2.2 if yr == 2026 else 1.4))
        fig.text(0.036 + k * 0.075, fy(1.08), str(yr), fontsize=9.5, color=INK, va="center")

    for j, (key, title) in enumerate(DECISIONS):
        ax = fig.add_axes([label_w + j * (col_w + gap), bottom, col_w, height])
        ax.set_ylim(n - 0.5, -0.5)
        ax.set_xlim(-1.5, 3.4)
        ax.set_yticks([])
        ax.set_xticks([t for t, _ in TICKS])
        ax.set_xticklabels([l for _, l in TICKS], fontsize=6.4, color=MUTED)
        ax.xaxis.tick_top()
        ax.tick_params(axis="x", length=0, pad=3)
        for s in ax.spines.values():
            s.set_visible(False)
        for t in range(0, 4):
            ax.axvline(t, color=RULE, lw=0.5, zorder=1)
        for _, start in areas[1:]:
            ax.axhline(start - 0.5, color=RULE, lw=0.6, zorder=1)
        for yr, c in YEARS:
            xs = [level_at(r["cells"].get(key, []), yr) for r in layout]
            px, py = [], []
            for i, x in enumerate(xs):
                px += [x, x]; py += [i - 0.5, i + 0.5]
                if yr == 2026:
                    lo, hi = (min(x, 0), max(x, 0))
                    ax.add_patch(plt.Rectangle((lo, i - 0.5), hi - lo, 1, facecolor="#e3f0f1" if x > 0 else "#f6d9d3", edgecolor="none", zorder=1))
            ax.plot(px, py, color=c, lw=2.2 if yr == 2026 else 1.4, zorder=3 + (yr == 2026), solid_joinstyle="miter")
        fig.text(label_w + j * (col_w + gap), fy(head_h - 0.62), title, fontsize=10.5, fontweight="bold", color=INK, va="bottom")
        fig.text(label_w + j * (col_w + gap), fy(head_h - 0.47), QUESTIONS[key], fontsize=8.2, color=MUTED, va="bottom")

    lab = fig.add_axes([0, bottom, label_w - 0.01, height])
    lab.set_xlim(0, 1); lab.set_ylim(n - 0.5, -0.5); lab.axis("off")
    for area, start in areas:
        lab.text(0.05, start - 0.18, area.upper(), fontsize=6.6, color=MUTED, va="bottom", fontweight="bold")
    for i, r in enumerate(layout):
        lab.text(0.05, i + 0.12, f"{r['disease']}, {r['population']}", fontsize=7.8, color=INK, va="center")

    fig.text(0.012, fy(fig_h - 0.14),
             "Rows are grouped by disease area; the frontier's shape depends on that order, and the track-record levels are ranked, not equally spaced.\n"
             "Hand-curated seed of 15 contexts, not a sample. The model, reason and source behind each point are in the companion tile figure and contexts/*.json.",
             fontsize=7.6, color=MUTED, va="bottom", linespacing=1.4)
    out = os.path.join(HERE, "frontier.png")
    fig.savefig(out, facecolor="white")
    print(out)


if __name__ == "__main__":
    main()
