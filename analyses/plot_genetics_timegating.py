"""Genetics under the same date-cleaning filter as literature/drug-efficacy.
Present -> time-gated (pre-first-trial) Relative Success, per genetics dimension.
Causal genetics (Mendelian, ClinGen) survives; weak GWAS-association collapses to null.
Clean editorial style, matching the nuance figures. No genetics band; no-signal line at RS=1.
"""
import os, csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.font_manager as fm

INK, SEC, MUTED = "#14110f", "#5b544e", "#938b82"
SURFACE, RULE, GREY = "#fbfaf8", "#d8d3cb", "#b9b2a8"
ORANGE, BLUE = "#e2673a", "#1f6fd0"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def _sans():
    for f in ("Helvetica Neue", "Helvetica", "Arial", "Liberation Sans", "DejaVu Sans"):
        if any(f.lower() == x.name.lower() for x in fm.fontManager.ttflist):
            return f
    return "DejaVu Sans"


def plot(clean=False):
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                         "savefig.facecolor": SURFACE, "font.family": _sans(),
                         "text.color": INK, "svg.fonttype": "none"})
    rows = {r["dimension"]: r for r in csv.DictReader(open(os.path.join(DATA, "genetics_timegating.csv")))}
    # top = causal (survives), bottom = association (collapses)
    order = [("Mendelian", "Mendelian ≥5", "causal"),
             ("ClinGen", "ClinGen ≥1", "causal"),
             ("GWAS", "GWAS ≥50", "association")]
    fig, ax = plt.subplots(figsize=(9.4, 3.3 if clean else 4.3))
    fig.subplots_adjust(left=0.24, right=0.965, top=0.80 if clean else 0.58, bottom=0.17)
    for y, (key, lab, kind) in zip([2, 1, 0], order):
        r = rows[key]; pres = float(r["present_rs"]); tg = float(r["timegated_rs"])
        if abs(pres - tg) < 0.02:  # unchanged (Mendelian)
            ax.scatter([pres], [y], s=150, color=BLUE, zorder=3, edgecolor=SURFACE, lw=1.5)
            ax.text(pres + 0.04, y + 0.14, f"{pres:.2f} (unchanged — pre-trial)", fontsize=8.5,
                    color=BLUE, va="center", fontweight="bold")
        else:
            ax.plot([tg, pres], [y, y], color=GREY, lw=3, zorder=2, solid_capstyle="round")
            ax.scatter([pres], [y], s=140, color=ORANGE, zorder=3, edgecolor=SURFACE, lw=1.5)
            ax.scatter([tg], [y], s=140, color=BLUE, zorder=3, edgecolor=SURFACE, lw=1.5)
            # splay labels outward: label the lower point to its LEFT, the higher to its RIGHT
            items = [(pres, "present", ORANGE), (tg, "pre-trial", BLUE)]
            (lv, ll, lc), (hv, hl, hc) = sorted(items, key=lambda x: x[0])
            ax.text(lv - 0.05, y + 0.14, f"{ll} {lv:.2f}", fontsize=8.5, color=lc, va="center", ha="right", fontweight="bold")
            ax.text(hv + 0.05, y + 0.14, f"{hl} {hv:.2f}", fontsize=8.5, color=hc, va="center", ha="left", fontweight="bold")
        ax.text(-0.02, y + 0.08, lab, fontsize=10.5, ha="right", va="center", fontweight="bold",
                color=INK, transform=ax.get_yaxis_transform())
        ax.text(-0.02, y - 0.16, kind, fontsize=8, ha="right", va="center",
                color=(MUTED if kind == "association" else SEC), style="italic",
                transform=ax.get_yaxis_transform())
    ax.axvline(1.0, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(1.0, 2.62, "no signal", fontsize=7.5, color=MUTED, ha="center")
    ax.set_xlim(0.5, 2.5); ax.set_xticks([0.5, 1.0, 1.5, 2.0, 2.5]); ax.set_ylim(-0.55, 2.8)
    ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.set_xlabel("Relative Success (approval with ÷ without evidence)", fontsize=9, color=SEC)
    ax.tick_params(axis="x", labelsize=8, colors=MUTED, length=0)
    handles = [Line2D([0], [0], marker="o", color="none", markerfacecolor=ORANGE, markersize=9, label="present-day"),
               Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE, markersize=9, label="pre-first-trial (date-cleaned)")]
    leg = ax.legend(handles=handles, loc="lower right", frameon=True, fontsize=8, handletextpad=0.3)
    leg.get_frame().set_facecolor(SURFACE); leg.get_frame().set_edgecolor("none"); leg.get_frame().set_alpha(1.0)
    if not clean:
        fig.text(0.02, 0.925, "Causal genetics survives date-cleaning; weak GWAS-association doesn't",
                 fontsize=14, fontweight="bold", color=INK)
        fig.text(0.02, 0.78,
                 "Genetics under the SAME pre-first-trial filter that collapsed cell/animal literature and "
                 "drug-efficacy. Causal, curated genetics (Mendelian, ClinGen) holds; the weak GWAS-association "
                 "signal drops to the null — GWAS-catalogue hits accrete after the trial, like literature.",
                 fontsize=9.2, color=SEC, linespacing=1.4)
        fig.add_artist(Line2D([0.02, 0.965], [0.70, 0.70], color=RULE, lw=1, transform=fig.transFigure))
        fig.text(0.02, 0.03, "GWAS dated by study PMID; ClinGen by classified_date (conservative — curation postdates discovery); "
                 "Mendelian pre-trial (25/25 sample validated). Ph2+ T-I pairs with a first-trial date.",
                 fontsize=7.2, color=MUTED)
    stem = "genetics_timegating" + ("_clean" if clean else "")
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=200)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig); print(f"wrote data/{stem}.png + .svg")


if __name__ == "__main__":
    plot(clean=False); plot(clean=True)
