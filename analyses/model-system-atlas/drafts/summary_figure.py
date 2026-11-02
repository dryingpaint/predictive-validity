"""Summary charts for the 70-context run: where the atlas lands before any redesign.

    .venv/bin/python analyses/model-system-atlas/drafts/matrix.py        # first
    .venv/bin/python analyses/model-system-atlas/drafts/summary_figure.py

Reads drafts/matrix_cells.csv and writes drafts/summary.png: diverging stacked bars centred on
`untested` (contra to the left, same / neg to the right, `other` as the pale right step), one
panel per cut. Checked contexts only, checker corrections applied, latest status per cell.
"""
import csv
import os
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
SURFACE, INK, MUTED, RULE = "#fcfcfb", "#1b2321", "#5c6763", "#c4cbc7"
# diverging: red arm (contradicted) | neutral (never compared) | blue arm (matched)
COL = {"contra": "#e34948", "untested": "#e4e3df", "other": "#6da7ec", "same": "#256abf", "neg": "#0d366b"}
LABEL = {"contra": "Contradicted", "untested": "Never compared", "other": "Matched, other mechanism",
         "same": "Matched, same mechanism", "neg": "Matched, incl. a known failure"}
LEFT, RIGHT = ["contra"], ["other", "same", "neg"]
QORDER = ["engagement", "dose", "efficacy", "safety"]
QLABEL = {"engagement": "Target engagement", "dose": "Dose", "efficacy": "Efficacy", "safety": "Safety"}


def load():
    with open(os.path.join(HERE, "matrix_cells.csv")) as f:
        rows = [r for r in csv.DictReader(f) if r["checked"] == "True"]
    return rows


def counts(rows, key, col="status_checked"):
    g = defaultdict(Counter)
    for r in rows:
        g[key(r)][r[col]] += 1
    return g


def panel(ax, groups, order, title, sublabel=None, show_pct=True):
    """Likert-style: the neutral `untested` share sits centred on zero; contra grows left, matched right."""
    ys = list(range(len(order)))[::-1]
    for y, g in zip(ys, order):
        c = groups.get(g, Counter()); n = sum(c.values()) or 1
        u = c.get("untested", 0) / n
        ax.barh(y, u, left=-u / 2, color=COL["untested"], height=0.62, edgecolor=SURFACE, linewidth=1.5)
        x = -u / 2
        for s in LEFT:
            w = c.get(s, 0) / n
            ax.barh(y, -w, left=x, color=COL[s], height=0.62, edgecolor=SURFACE, linewidth=1.5)
            x -= w
        left_end = x
        x = u / 2
        for s in RIGHT:
            w = c.get(s, 0) / n
            ax.barh(y, w, left=x, color=COL[s], height=0.62, edgecolor=SURFACE, linewidth=1.5)
            x += w
        right_end = x
        if show_pct:
            l = c.get("contra", 0) / n; r = sum(c.get(s, 0) for s in RIGHT) / n
            if l: ax.text(left_end - 0.015, y, f"{100*l:.0f}%", ha="right", va="center", fontsize=8, color=INK)
            if r: ax.text(right_end + 0.015, y, f"{100*r:.0f}%", ha="left", va="center", fontsize=8, color=INK)
        lab = sublabel(g, c) if sublabel else g
        ax.text(-1.12, y, lab, ha="right", va="center", fontsize=8.5, color=INK)
    ax.set_xlim(-1.12, 1.12); ax.set_ylim(-0.6, len(order) - 0.4)
    ax.axvline(0, color=RULE, linewidth=0.8, zorder=0)
    ax.set_yticks([]); ax.set_xticks([-1, -0.5, 0, 0.5, 1])
    ax.set_xticklabels(["100%", "50%", "0", "50%", "100%"], fontsize=7.5, color=MUTED)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title(title, loc="left", fontsize=9.5, fontweight="bold", color=INK, pad=6)


def main():
    rows = load()
    nctx = len({r["context"] for r in rows})
    fig = plt.figure(figsize=(13.5, 9.2), dpi=200, facecolor=SURFACE)
    gs = fig.add_gridspec(2, 2, left=0.19, right=0.985, top=0.855, bottom=0.085, hspace=0.42, wspace=0.62,
                          height_ratios=[1, 2.2])
    fig.text(0.02, 0.965, "Where the best preclinical model stands, by question", fontsize=15,
             fontweight="bold", color=INK)
    fig.text(0.02, 0.935,
             f"Latest status per context x question after the checker pass, {nctx} named contexts (industry Phase 2 entrants "
             "2008-2019, most-developed novel drug class per indication).",
             fontsize=8.6, color=MUTED)
    fig.text(0.02, 0.912, "Grey = never compared with patients, centred on zero; contradicted grows left, matched grows right. "
             "End labels give the contradicted and matched shares.", fontsize=8.6, color=MUTED)

    # A: by question, checker-corrected
    a = fig.add_subplot(gs[0, 0])
    g = counts(rows, lambda r: r["question"])
    panel(a, g, QORDER, "A  By question (checker-corrected)", sublabel=lambda q, c: f"{QLABEL[q]}  (n={sum(c.values())})")

    # B: drafter vs checker per question
    b = fig.add_subplot(gs[0, 1])
    gd = counts(rows, lambda r: r["question"], col="status_draft"); gc = counts(rows, lambda r: r["question"])
    order = []; merged = {}
    for q in QORDER:
        merged[f"{q}|draft"] = gd[q]; merged[f"{q}|check"] = gc[q]; order += [f"{q}|draft", f"{q}|check"]
    panel(b, merged, order, "B  Drafter's call vs checker's", show_pct=False,
          sublabel=lambda k, c: f"{QLABEL[k.split('|')[0]]} - {'drafter' if k.endswith('draft') else 'checker'}")

    # C: stated comparison vs juxtaposition, per question
    c = fig.add_subplot(gs[1, 0])
    def stated(r):
        v = r["latest_comparison_stated"]
        return "stated" if v == "True" else ("juxtaposed" if v == "False" else "unrecorded")
    gs_ = counts(rows, lambda r: f"{r['question']}|{stated(r)}")
    order = [f"{q}|{s}" for q in QORDER for s in ("stated", "juxtaposed")]
    panel(c, gs_, order, "C  Comparison stated by the source vs juxtaposed by the drafter",
          sublabel=lambda k, cc: f"{QLABEL[k.split('|')[0]].replace('Target engagement', 'Engagement')} - {k.split('|')[1]}  (n={sum(cc.values())})")

    # D: by area, all four questions pooled
    d = fig.add_subplot(gs[1, 1])
    ga = counts(rows, lambda r: r["area"])
    areas = sorted(ga, key=lambda k: -sum(ga[k].values()))
    panel(d, ga, areas, "D  By disease area (four questions pooled)", sublabel=lambda k, cc: f"{k}  (n={sum(cc.values())})")

    handles = [Patch(facecolor=COL[s], edgecolor=SURFACE, label=LABEL[s]) for s in ["contra", "untested", "other", "same", "neg"]]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, fontsize=8.2, bbox_to_anchor=(0.5, 0.005),
               handlelength=1.4, columnspacing=1.6)
    out = os.path.join(HERE, "summary.png")
    fig.savefig(out, facecolor=SURFACE)
    print(out)


if __name__ == "__main__":
    main()
