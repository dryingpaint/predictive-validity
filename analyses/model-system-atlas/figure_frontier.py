"""Draw the model-system frontier as radial charts: one per question, one spoke per context, and the
best model's track record as distance from the centre, outlined for 1995, 2005, 2015 and 2026.

    .venv/bin/python analyses/model-system-atlas/figure_frontier.py

Reads the same contexts/*.json as figure.py and writes frontier.png beside this file.
"""

import os

import matplotlib.pyplot as plt
import numpy as np

from figure import DECISIONS, QUESTIONS, load, spans

HERE = os.path.dirname(os.path.abspath(__file__))
RADIUS = {"contra": 0.5, "untested": 1.5, "other": 2.5, "same": 3.5, "neg": 4.5}
RINGS = [(0.5, "Contradicted"), (1.5, "Never compared"), (2.5, "Other mechanism"), (3.5, "Same mechanism"), (4.5, "Incl. a failure")]
YEARS = [(1995, "#cfe4e6", 1.2), (2005, "#93c6ca", 1.3), (2015, "#4b9ca3", 1.5), (2026, "#0b5f69", 2.4)]
INK, MUTED, RULE, RED, FILL = "#1b2321", "#5c6763", "#d3d8d5", "#c63d26", "#e3f0f1"


def radius_at(history, year):
    r = RADIUS["untested"]
    for a, _, st in spans(history):
        if a <= year:
            r = RADIUS[st]
    return r


def main():
    rows = load()
    n = len(rows)
    theta = np.pi / 2 - np.linspace(0, 2 * np.pi, n, endpoint=False)  # clockwise from 12 o'clock
    W, H = 14, 12.6
    fig = plt.figure(figsize=(W, H), dpi=200)
    fig.text(0.03, 0.975, "The jagged frontier of preclinical prediction", fontsize=19, fontweight="bold", color=INK, va="top")
    fig.text(0.03, 0.947, "Each spoke is a context (disease, patient group, drug class). Distance from the centre is how far its best model's "
             "track record against patients had got;\noutlines show 1995, 2005, 2015 and 2026. Red dots: contradicted by patients.",
             fontsize=10, color=MUTED, va="top", linespacing=1.4)
    for k, (yr, c, lw) in enumerate(YEARS):
        x = 0.03 + k * 0.085
        fig.add_artist(plt.Line2D([x, x + 0.025], [0.898, 0.898], color=c, lw=lw + 0.6))
        fig.text(x + 0.03, 0.898, str(yr), fontsize=10, color=INK, va="center")

    spots = [(0.115, 0.455), (0.615, 0.455), (0.115, 0.045), (0.615, 0.045)]
    circle = np.linspace(0, 2 * np.pi, 361)
    for (key, title), (x0, y0) in zip(DECISIONS, spots):
        ax = fig.add_axes([x0, y0, 0.27, 0.36], projection="polar")
        cy, rfrac = y0 + 0.18, 0.27 * W / 2 / H
        ax.set_ylim(0, 4.8)
        ax.set_yticks([])
        ax.set_xticks([])
        ax.spines["polar"].set_visible(False)
        ax.grid(False)
        for r, label in RINGS:
            ax.plot(circle, [r] * len(circle), color=RED if r == 0.5 else RULE, lw=0.7, alpha=0.5 if r == 0.5 else 1, zorder=0)
            ax.text(np.pi / 2 - 0.035, r + 0.06, label, fontsize=6, color=MUTED, ha="left", va="bottom", zorder=7)
        for t in theta:
            ax.plot([t, t], [0, 4.6], color=RULE, lw=0.5, zorder=0)
        closed = np.append(theta, theta[0])
        for yr, c, lw in YEARS:
            rs = np.array([radius_at(r["cells"].get(key, []), yr) for r in rows])
            rc = np.append(rs, rs[0])
            if yr == 2026:
                ax.fill(closed, rc, color=FILL, zorder=1)
            ax.plot(closed, rc, color=c, lw=lw, zorder=3 + (yr == 2026), solid_joinstyle="round")
        for t, r in zip(theta, rows):
            if radius_at(r["cells"].get(key, []), 2026) == RADIUS["contra"]:
                ax.plot(t, RADIUS["contra"], "o", ms=6.5, color=RED, zorder=6, mec="white", mew=0.8)
            c = np.cos(t)
            ha = "left" if c > 0.15 else ("right" if c < -0.15 else "center")
            ax.text(t, 5.05, r["label"], fontsize=7.4, color=INK, ha=ha, va="center")
        fig.text(x0 + 0.135, cy + rfrac + 0.05, title, fontsize=12.5, fontweight="bold", color=INK, ha="center", va="bottom")
        fig.text(x0 + 0.135, cy + rfrac + 0.045, QUESTIONS[key], fontsize=9, color=MUTED, ha="center", va="top")

    fig.text(0.03, 0.008, "Spokes run clockwise from the top in the report's disease-area order; the outline's shape depends on that order, and the rings are "
             "ranked, not equally spaced.\nHand-curated seed of 15 contexts, not a sample. Model, reason and source for each point: companion tile figure "
             "and contexts/*.json.", fontsize=7.8, color=MUTED, va="bottom", linespacing=1.4)
    out = os.path.join(HERE, "frontier.png")
    fig.savefig(out, facecolor="white")
    print(out)


if __name__ == "__main__":
    main()
