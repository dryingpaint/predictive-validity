"""The lessons figures in the atlas style (183 mm, Helvetica 5-7 pt, the Capable palette).

atlas_lessons.*          a  tiles whose engagement headline matched, by efficacy headline: by class outcome, by the engagement
                            readout's tier and by area, each with the contradicted share and its Wilson 95 % interval
                         b  the typed safety contradictions by harm class, one count per (model system, harm, type):
                            silent on the harm, said there would be none, false alarm
atlas_lessons_families.* the family forests (efficacy yes-PPV and safety held), supplementary

Called by lessons.py figure; draws from the CSVs beside it."""
from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from families import FAMILIES  # noqa: E402
from glance_nature import INK, MUTED, RC, RULE, STATUS  # noqa: E402

MATCHED, CONTRA, RETRO, UNTESTED = STATUS["same"][0], STATUS["contra"][0], STATUS["retro"][0], STATUS["untested"][0]
HARM_LABEL = {"immune": "Immune-mediated", "liver": "Liver", "cardiovascular": "Cardiovascular", "metabolic_endocrine_bone": "Metabolic, endocrine, bone",
              "haematological": "Haematological", "gastrointestinal": "Gastrointestinal", "cns": "CNS", "skin": "Skin", "ocular": "Ocular",
              "respiratory": "Respiratory", "renal": "Renal", "musculoskeletal": "Musculoskeletal", "other": "Other"}
TYPE_STYLE = {"silent": (CONTRA, None, "Silent on the harm"), "stated_safe": (CONTRA, "////", "Said there would be no harm"),
              "false_alarm": (RETRO, None, "False alarm")}
EFF_STYLE = {"matched": (MATCHED, "Efficacy matched"), "contradicted": (CONTRA, "Efficacy contradicted"), "not_compared": (UNTESTED, "Efficacy never compared")}
GROUP_LABEL = {"outcome": "By class outcome", "tier": "By the engagement readout", "area": "By disease area (3 tiles or more)"}


def clean(ax) -> None:
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_linewidth(0.5)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(axis="x", labelsize=5.5, width=0.5, length=2, colors=MUTED, labelcolor=INK)
    ax.set_yticks([])


def legend(ax, handles, labels, x: float) -> None:
    ax.legend(handles, labels, fontsize=5, frameon=False, loc="upper left", bbox_to_anchor=(x, -0.14), ncol=3, handlelength=1.2,
              handletextpad=0.4, columnspacing=1.0, borderaxespad=0)


def engagement_panel(ax, es: pd.DataFrame, n_tiles: int) -> None:
    """One 100 % stacked bar per row of the engagement summary, grouped, the contradicted share and its interval at the right."""
    y = 0.0
    for group in ["outcome", "tier", "area"]:
        ax.text(-0.02, y - 0.05, GROUP_LABEL[group], fontsize=5, color=MUTED, ha="right", va="center", style="italic")
        y -= 0.8
        for r in es[es.group == group].itertuples():
            x = 0.0
            for key, (color, _) in EFF_STYLE.items():
                n = getattr(r, key)
                if not n:
                    continue
                w = n / r.n
                ax.add_patch(Rectangle((x, y - 0.36), w, 0.72, facecolor=color, edgecolor="white", linewidth=0.5))
                if w > 0.07:
                    ax.text(x + w / 2, y, str(n), fontsize=5, ha="center", va="center", color=INK if key == "not_compared" else "white")
                x += w
            ax.text(-0.02, y, r.label, fontsize=5.5, ha="right", va="center", color=INK)
            ax.text(1.03, y, f"{r.contradicted}/{r.n} · {100 * r.share:.0f} % ({100 * r.lo:.0f}–{100 * r.hi:.0f})", fontsize=5, ha="left", va="center", color=MUTED)
            y -= 1.0
        y -= 0.3
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(y + 0.6, 0.5)
    ax.set_xticks([0, 0.5, 1])
    ax.set_xticklabels(["0", "50 %", "100 %"])
    n_held = int(es[es.group == "outcome"].n.sum())
    ax.set_xlabel(f"Tiles whose engagement headline matched ({n_held} of {n_tiles})", fontsize=6, labelpad=2)
    ax.set_title("a  Target reached, disease still unpredicted", fontsize=7, loc="left", pad=6)
    ax.text(1.03, 0.45, "contradicted (Wilson 95 %)", fontsize=5, color=MUTED, ha="left", va="center", style="italic")
    legend(ax, [Rectangle((0, 0), 1, 1, facecolor=c, edgecolor="white", linewidth=0.5) for c, _ in EFF_STYLE.values()], [l for _, l in EFF_STYLE.values()], -0.5)
    clean(ax)


def safety_panel(ax, u: pd.DataFrame, n_systems: int, n_tracks: int) -> None:
    """Stacked counts per harm class from the unique (system, harm, type) rows."""
    counts = u.harm.value_counts()
    y = 0.0
    by_type = pd.crosstab(u.harm, u.type)
    for harm in counts.index:
        left = 0
        for key, (color, hatch, _) in TYPE_STYLE.items():
            n = int(by_type.loc[harm].get(key, 0))
            if n:
                ax.add_patch(Rectangle((left, y - 0.36), n, 0.72, facecolor=color, edgecolor="white", linewidth=0.5, hatch=hatch))
                left += n
        ax.text(-0.3, y, HARM_LABEL[harm], fontsize=5.5, ha="right", va="center", color=INK)
        ax.text(left + 0.3, y, str(left), fontsize=5, ha="left", va="center", color=MUTED)
        y -= 1.0
    ax.set_xlim(-0.3, counts.max() + 1.5)
    ax.set_ylim(y + 0.4, 0.5)
    ax.set_xticks(range(0, int(counts.max()) + 1, 4))
    ax.set_xlabel(f"Safety contradictions: {n_systems} model systems ({n_tracks} tracks), by harm", fontsize=6, labelpad=2)
    ax.set_title("b  What the safety models missed", fontsize=7, loc="left", pad=6)
    legend(ax, [Rectangle((0, 0), 1, 1, facecolor=c, hatch=hch, edgecolor="white", linewidth=0.5) for c, hch, _ in TYPE_STYLE.values()],
           [l for _, _, l in TYPE_STYLE.values()], -0.52)
    clean(ax)


def save(fig, out: str) -> None:
    for ext in ("png", "pdf", "svg"):
        fig.savefig(f"{out}.{ext}", dpi=300 if ext == "png" else None)
    plt.close(fig)
    print(f"wrote {out}.png/.pdf/.svg")


def draw(es: pd.DataFrame, n_tiles: int, u: pd.DataFrame, n_tracks: int, out: str) -> None:
    plt.rcParams.update(RC)
    fig = plt.figure(figsize=(7.2, 4.1))
    ax_a = fig.add_axes([0.20, 0.17, 0.235, 0.70])
    ax_b = fig.add_axes([0.72, 0.17, 0.24, 0.70])
    engagement_panel(ax_a, es, n_tiles)
    safety_panel(ax_b, u, u.model_id.nunique(), n_tracks)
    fig.text(0.5, 0.012, "Every tile reached Phase 2: a model that said no and was believed is not here. Nothing here is a sensitivity. "
             "Statuses are the atlas's adjudicated statuses.", fontsize=5, color=MUTED, ha="center", va="bottom")
    save(fig, out)


def forest(ax, r: pd.DataFrame, title: str, xlabel: str) -> None:
    """Dot and interval per family, ranked families first, the rest below a rule; matched/compared and n tiles at the right."""
    ranked = r[r.rankable].sort_values(["ppv", "n_tiles"], ascending=[False, False])
    rest = r[~r.rankable].sort_values(["n_tiles", "ppv"], ascending=[False, False])
    rows = pd.concat([ranked, rest]).reset_index(drop=True)
    n_rank = len(ranked)
    ys, y = [], 0.0
    for i in range(len(rows)):
        if i == n_rank:
            y -= 0.7
        ys.append(y)
        y -= 1.0
    pooled = r.pooled.iloc[0]
    ax.axvline(pooled, color=CONTRA, lw=0.6, ls=(0, (3, 2)), zorder=1)
    ax.text(pooled, 1.05, f"all {pooled:.2f}", fontsize=5, color=CONTRA, ha="center", va="bottom")
    for (_, row), yy in zip(rows.iterrows(), ys):
        if row.rankable:
            ax.plot([row.lo, row.hi], [yy, yy], color=MUTED, lw=0.7, solid_capstyle="butt", zorder=2)
            ax.plot(row.ppv, yy, "o", ms=3.2, color=INK, zorder=3)
        else:
            ax.plot(row.ppv, yy, "o", ms=3.0, markerfacecolor="white", markeredgecolor=INK, markeredgewidth=0.6, zorder=3)
        ax.text(-0.05, yy, FAMILIES[row.family][1], fontsize=5.5, ha="right", va="center", color=INK)
        ax.text(1.05, yy, f"{row.matched}/{row.n_tracks} · {row.n_tiles} tiles", fontsize=5, ha="left", va="center", color=MUTED)
    if n_rank < len(rows):
        yr = ys[n_rank] + 0.85
        ax.plot([-0.02, 1.02], [yr, yr], color=RULE, lw=0.5, clip_on=False)
        ax.text(1.05, yr, "fewer than 4 tiles", fontsize=5, color=MUTED, ha="left", va="center", style="italic")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(min(ys) - 0.7, 1.7)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
    ax.set_xticklabels(["0", "", "0.5", "", "1"])
    ax.set_xlabel(xlabel, fontsize=6, labelpad=2)
    ax.set_title(title, fontsize=7, loc="left", pad=6)
    clean(ax)


def draw_families(rates: pd.DataFrame, out: str) -> None:
    """Supplementary: the family forests. A family's rate follows the classes it served; the by-outcome CSV is the control."""
    plt.rcParams.update(RC)
    fig = plt.figure(figsize=(7.2, 4.4))
    ax_a = fig.add_axes([0.20, 0.12, 0.19, 0.78])
    ax_b = fig.add_axes([0.72, 0.12, 0.19, 0.78])
    forest(ax_a, rates[rates.q == "efficacy"], "a  Efficacy: what a model's yes was worth", "Share of positive efficacy predictions the trial confirmed")
    forest(ax_b, rates[rates.q == "safety"], "b  Safety: how often the safety picture held", "Share of safety predictions that held in patients")
    fig.text(0.5, 0.012, "Rates follow the classes each family served (family_rates_by_outcome.csv splits them). Intervals: 95 % cluster bootstrap over tiles. "
             "Nothing here is a sensitivity.", fontsize=5, color=MUTED, ha="center", va="bottom")
    save(fig, out)
