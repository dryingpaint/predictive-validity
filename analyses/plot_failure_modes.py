#!/usr/bin/env python3
"""
Section 1 figure — why industry trials stop.

Reads the cached failure taxonomy (data/failure_taxonomy.csv, from
preclin.v_failure_taxonomy: Sonnet-deduped why_stopped classifications over
5,510 terminated industry trials 2015–2025) and renders a clean ranked bar
chart, colored by failure family.

Caveat carried in the subtitle: this is why trials are *terminated early*, so it
under-counts efficacy (a completed-but-negative Phase 3 is not a "stop"), and the
sponsor "strategic" bucket is known to absorb quiet efficacy failures.
"""
from __future__ import annotations
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CURATED = os.path.join(HERE, "..", "data")
FIGDIR = os.path.join(HERE, "..", "data")
os.makedirs(FIGDIR, exist_ok=True)

# palette
INK, SEC, MUTED = "#14110f", "#5b544e", "#938b82"
SURFACE, RULE = "#fbfaf8", "#d8d3cb"
BIOLOGY, BUSINESS, AMBIG = "#1f6fd0", "#e2673a", "#c7c0b6"

FAMILY = {"biology": BIOLOGY, "business": BUSINESS, "ambiguous": AMBIG}
FAMILY_LABEL = {"biology": "Biology (efficacy / safety / PK)",
                "business": "Business & operational",
                "ambiguous": "Other / undisclosed"}

# category -> (display, family)
CATS = {
    "commercial_strategic":   ("Commercial / strategic", "business"),
    "unclear":                ("Unclear / undisclosed", "ambiguous"),
    "efficacy":               ("Efficacy", "biology"),
    "enrollment_operational": ("Enrollment / operational", "business"),
    "regulatory_admin":       ("Regulatory / administrative", "business"),
    "planned_termination":    ("Planned (per protocol)", "ambiguous"),
    "covid":                  ("COVID-19 disruption", "ambiguous"),
    "safety":                 ("Safety / toxicity", "biology"),
    "competitive_landscape":  ("Competitive landscape", "business"),
    "manufacturing_supply":   ("Manufacturing / supply", "business"),
    "pk_pd_formulation":      ("PK / PD / formulation", "biology"),
}


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


def main():
    style()
    df = pd.read_csv(os.path.join(CURATED, "failure_taxonomy.csv"))
    df = df[df.category.isin(CATS)].copy()
    df["disp"] = df.category.map(lambda c: CATS[c][0])
    df["fam"] = df.category.map(lambda c: CATS[c][1])
    df["color"] = df.fam.map(FAMILY)
    df = df.sort_values("pct_of_all_classified")            # smallest first -> top of chart after barh
    fam_share = df.groupby("fam").pct_of_all_classified.sum()

    fig, ax = plt.subplots(figsize=(9.6, 6.4))
    fig.subplots_adjust(left=0.30, right=0.93, top=0.66, bottom=0.11)
    y = range(len(df))
    ax.barh(list(y), df.pct_of_all_classified, height=0.62, color=df.color, zorder=3)
    for yi, (pct, n) in enumerate(zip(df.pct_of_all_classified, df.n_trials)):
        ax.text(pct + 0.7, yi, f"{pct:.0f}%" if pct >= 1 else f"{pct:.1f}%",
                va="center", ha="left", fontsize=10.5, fontweight="bold", color=INK)

    ax.set_yticks(list(y))
    ax.set_yticklabels(df.disp, fontsize=11, color=INK)
    ax.set_xticks([]); ax.set_xlim(0, 50)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.margins(y=0.02)

    # legend keyed to family (with family shares)
    handles = [Patch(facecolor=FAMILY[f], label=f"{FAMILY_LABEL[f]}  ·  {fam_share[f]:.0f}%")
               for f in ("biology", "business", "ambiguous")]
    leg = ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=9.5,
                    handlelength=1.0, handleheight=1.0, borderpad=0, labelspacing=0.6)
    for t in leg.get_texts():
        t.set_color(SEC)

    # title block
    fig.text(0.035, 0.92, "Why industry trials are terminated",
             fontsize=19, fontweight="bold", color=INK, ha="left")
    fig.text(0.035, 0.855,
             "Classified reason for stopping, across 5,510 terminated industry Phase 1–3 trials (2015–2025).",
             fontsize=11, color=SEC, ha="left", linespacing=1.4)
    fig.add_artist(Line2D([0.035, 0.965], [0.75, 0.75], color=RULE, lw=1, transform=fig.transFigure))
    fig.text(0.035, 0.028,
             "Source: Melissa Du predictive-validity benchmark — why_stopped classifications "
             "(Claude Sonnet) over industry Phase 1–3 trials, 2015–2025.",
             fontsize=8, color=MUTED, ha="left")

    fig.savefig(os.path.join(FIGDIR, "failure_modes.png"), bbox_inches="tight", dpi=600)
    fig.savefig(os.path.join(FIGDIR, "failure_modes.svg"), bbox_inches="tight")
    plt.close(fig)
    print("wrote data/failure_modes.png (600 dpi) + .svg")


if __name__ == "__main__":
    main()
