"""The lessons figure: four panels in the atlas style (183 mm, Helvetica 5-7 pt, the Capable palette).

a  efficacy: what a yes was worth per family (matched / compared among positive predictions), cluster-bootstrap interval,
   pooled rate as the reference line; families with fewer than four tiles listed below a rule without an interval
b  safety: the share of each family's safety predictions that held, same layout
c  tiles whose engagement headline matched, by efficacy headline, split by engagement readout tier and by area
d  the typed safety contras by harm class: silent, stated safe, false alarm

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
from families import SHORT  # noqa: E402
from glance_nature import CAPABLE, INK, MUTED, RC, RULE, STATUS  # noqa: E402

CONTRA, RETRO, UNTESTED = STATUS["contra"][0], STATUS["retro"][0], STATUS["untested"][0]
W, H = 7.2, 6.6
MATCHED = {"same", "neg", "other"}
HARM_LABEL = {"immune": "Immune-mediated", "liver": "Liver", "cardiovascular": "Cardiovascular", "metabolic_endocrine_bone": "Metabolic / endocrine",
              "haematological": "Haematological", "gastrointestinal": "Gastrointestinal", "cns": "CNS", "skin": "Skin", "ocular": "Ocular",
              "respiratory": "Respiratory", "renal": "Renal", "musculoskeletal": "Musculoskeletal", "other": "Other"}
TYPE_STYLE = {"silent": (CONTRA, None, "Silent on the harm"), "stated_safe": (CONTRA, "////", "Said there would be no harm"),
              "false_alarm": (RETRO, None, "False alarm")}
EFF_STYLE = {"matched": (CAPABLE, "Efficacy matched"), "contradicted": (CONTRA, "Efficacy contradicted"), "not compared": (UNTESTED, "Efficacy never compared")}
TIERS = [("Direct (occupancy)", "direct"), ("Proximal (product)", "proximal"), ("Downstream biomarker", "downstream")]


def clean(ax) -> None:
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_linewidth(0.5)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(axis="x", labelsize=5.5, width=0.5, length=2, colors=MUTED, labelcolor=INK)
    ax.set_yticks([])


def legend(ax, handles, labels) -> None:
    ax.legend(handles, labels, fontsize=5, frameon=False, loc="upper left", bbox_to_anchor=(-0.62, -0.16), ncol=3, handlelength=1.2,
              handletextpad=0.4, columnspacing=1.0, borderaxespad=0)


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
        ax.text(-0.05, yy, SHORT[row.family], fontsize=5.5, ha="right", va="center", color=INK)
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


def stacked(ax, rows: list[tuple[str, dict | None]], styles: dict) -> float:
    """Horizontal 100 % stacked bars; a row whose counts are None is an italic sub-heading. Returns the lowest y used."""
    y = 0.0
    for name, counts in rows:
        if counts is None:
            ax.text(-0.02, y - 0.1, name, fontsize=5, color=MUTED, ha="right", va="center", style="italic")
            y -= 0.75
            continue
        total = sum(counts.values())
        x = 0.0
        for key, (color, _) in styles.items():
            n = counts.get(key, 0)
            if not n:
                continue
            w = n / total
            ax.add_patch(Rectangle((x, y - 0.36), w, 0.72, facecolor=color, edgecolor="white", linewidth=0.5))
            if w > 0.08:
                ax.text(x + w / 2, y, str(n), fontsize=5, ha="center", va="center", color=INK if key == "not compared" else "white")
            x += w
        ax.text(-0.02, y, name, fontsize=5.5, ha="right", va="center", color=INK)
        ax.text(1.03, y, f"n = {total}", fontsize=5, ha="left", va="center", color=MUTED)
        y -= 1.0
    return y


def engagement_panel(ax, h: pd.DataFrame) -> None:
    held = h[h.engagement.isin(MATCHED)].copy()
    held["eff"] = held.efficacy.fillna("blank").map(lambda s: "matched" if s in MATCHED else ("contradicted" if s == "contra" else "not compared"))
    rows: list[tuple[str, dict | None]] = [("By engagement readout", None)]
    rows += [(lab, held[held.engagement_tier == t].eff.value_counts().to_dict()) for lab, t in TIERS]
    area_n = held.area.value_counts()
    rows.append(("By disease area (3 tiles or more)", None))
    rows += [(a.replace("_", " ").capitalize(), held[held.area == a].eff.value_counts().to_dict()) for a in area_n.index if area_n[a] >= 3]
    styles = {k: (v[0], v[1]) for k, v in EFF_STYLE.items()}
    y = stacked(ax, rows, styles)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(y + 0.4, 0.6)
    ax.set_xticks([0, 0.5, 1])
    ax.set_xticklabels(["0", "50 %", "100 %"])
    ax.set_xlabel(f"Engagement matched ({len(held)} of {len(h)} tiles), by efficacy", fontsize=6, labelpad=2)
    ax.set_title("c  Target reached, disease still unpredicted", fontsize=7, loc="left", pad=6)
    legend(ax, [Rectangle((0, 0), 1, 1, facecolor=c, edgecolor="white", linewidth=0.5) for c, _ in EFF_STYLE.values()], [l for _, l in EFF_STYLE.values()])
    clean(ax)


def safety_panel(ax, s: pd.DataFrame) -> None:
    s = s[s.type.isin({"silent", "stated_safe", "false_alarm", "not_showable"})].copy()
    s["type"] = s.type.replace({"not_showable": "silent"})
    x = s.assign(harm=s.harm_class.str.split(";")).explode("harm").reset_index(drop=True)
    x["harm"] = x.harm.str.strip()
    counts = x.harm.value_counts()
    y = 0.0
    for harm in counts.index:
        g = x[x.harm == harm]
        left = 0
        for key, (color, hatch, _) in TYPE_STYLE.items():
            n = int((g.type == key).sum())
            if n:
                ax.add_patch(Rectangle((left, y - 0.36), n, 0.72, facecolor=color, edgecolor="white", linewidth=0.5, hatch=hatch))
                left += n
        ax.text(-0.3, y, HARM_LABEL[harm], fontsize=5.5, ha="right", va="center", color=INK)
        ax.text(left + 0.3, y, str(left), fontsize=5, ha="left", va="center", color=MUTED)
        y -= 1.0
    ax.set_xlim(-0.3, counts.max() + 1.5)
    ax.set_ylim(y + 0.4, 0.6)
    ax.set_xticks(range(0, int(counts.max()) + 1, 4))
    ax.set_xlabel(f"Safety contradictions ({len(s)} tracks), by harm", fontsize=6, labelpad=2)
    ax.set_title("d  What the safety models missed", fontsize=7, loc="left", pad=6)
    legend(ax, [Rectangle((0, 0), 1, 1, facecolor=c, hatch=hch, edgecolor="white", linewidth=0.5) for c, hch, _ in TYPE_STYLE.values()],
           [l for _, _, l in TYPE_STYLE.values()])
    clean(ax)


def draw(rates: pd.DataFrame, headlines: pd.DataFrame, safety: pd.DataFrame, out: str) -> None:
    plt.rcParams.update(RC)
    fig = plt.figure(figsize=(W, H))
    ax_a = fig.add_axes([0.245, 0.585, 0.19, 0.355])
    ax_b = fig.add_axes([0.245, 0.085, 0.19, 0.355])
    ax_c = fig.add_axes([0.69, 0.585, 0.20, 0.34])
    ax_d = fig.add_axes([0.69, 0.145, 0.20, 0.295])
    forest(ax_a, rates[rates.q == "efficacy"], "a  Efficacy: what a model's yes was worth", "Share of positive efficacy predictions the trial confirmed")
    forest(ax_b, rates[rates.q == "safety"], "b  Safety: how often the model's safety picture held", "Share of safety predictions that held in patients")
    engagement_panel(ax_c, headlines)
    safety_panel(ax_d, safety)
    fig.text(0.5, 0.008, "Every tile reached Phase 2: a model that said no and was believed is not here. Rates are what a yes was worth, not a sensitivity. "
             "Intervals: 95 % cluster bootstrap over tiles.", fontsize=5, color=MUTED, ha="center", va="bottom")
    for ext in ("png", "pdf", "svg"):
        fig.savefig(f"{out}.{ext}", dpi=300 if ext == "png" else None)
    plt.close(fig)
    print(f"wrote {out}.png/.pdf/.svg")
