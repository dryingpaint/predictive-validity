"""Report figures from the Section 1, Section 2, Section 3 and attribution outputs.

    python -m report.figures

Reads report/output/section*/ CSVs (no database access) and writes PNG and
SVG files to report/output/figures/.
"""
from __future__ import annotations

import json
import logging
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches
import numpy as np
import pandas as pd

from report import bio, frame
from report.render import BAND_NAMES, S3_ENDPOINTS, S3_MAP_ROWS, rule_name, stratum_name
from report.section3 import DISCOVERY_FLOOR
from report.attribution import GROUP_LABELS
from report.stop_causes import SHOWN

OUT = os.path.join(frame.REPO, "report", "output")
FIG = os.path.join(OUT, "figures")

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
GRID, BAR, ACCENT = "#e4e3df", "#c3c2b7", "#2a78d6"
FAMILY_COLORS = {  # reference categorical order; each family keeps its hue in every panel
    "Efficacy (stated or measured)": "#2a78d6", "Safety, PK or formulation": "#eb6834",
    "Business or strategy (explicit)": "#1baf7a", "Sponsor decision, no reason": "#eda100",
    "Enrollment, operational, regulatory": "#4a3aa7", "Positive readout, not advanced": "#008300",
    "Other stated reason": "#6b6a65", "No reason, results posted": "#a5a39a", "No reason, no results": "#d6d5ce",
}
REASON_FAMILY = {
    "efficacy: stated": "Efficacy (stated or measured)",
    "efficacy: primary endpoint not met": "Efficacy (stated or measured)",
    "safety": "Safety, PK or formulation", "PK, dose or formulation": "Safety, PK or formulation",
    "business or strategic (explicit)": "Business or strategy (explicit)",
    "sponsor decision, unspecified": "Sponsor decision, no reason",
    "enrollment, operational or regulatory": "Enrollment, operational, regulatory",
    "positive readout, not advanced": "Positive readout, not advanced",
    "other stated reason": "Other stated reason",
    "results posted, no reason stated, endpoint not assessable": "No reason, results posted",
    "completed, no results posted, no reason stated": "No reason, no results",
    "stopped, no reason stated": "No reason, no results",
}


def style(ax):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, length=0)
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.set_axisbelow(True)


def save(fig, name):
    os.makedirs(FIG, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(FIG, f"{name}.{ext}"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def failure_modes():
    progs = pd.read_csv(os.path.join(OUT, "section1", "failure_modes_programs.csv"))
    progs["family"] = progs.reason.map(REASON_FAMILY)
    tab = progs.pivot_table(index="phase", columns="family", values="program_id", aggfunc="count", fill_value=0)
    share = tab.div(tab.sum(axis=1), axis=0)
    fig, ax = plt.subplots(figsize=(9, 3.2))
    for i, ph in enumerate(sorted(share.index, reverse=True)):
        left = 0.0
        for fam, color in FAMILY_COLORS.items():
            w = share.at[ph, fam] if fam in share.columns else 0.0
            ax.barh(i, w, left=left, height=0.55, color=color, edgecolor="white", linewidth=2)
            if w >= 0.07:
                ax.text(left + w / 2, i, f"{w:.0%}", ha="center", va="center", color="white", fontsize=9)
            left += w
    ax.set_yticks(range(len(share)), [f"Phase {ph}\n{int(tab.loc[ph].sum()):,} programs"
                                     for ph in sorted(share.index, reverse=True)], color=INK)
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    style(ax)
    ax.legend(handles=[matplotlib.patches.Patch(color=c, label=f) for f, c in FAMILY_COLORS.items()],
              ncol=4, frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.18))
    ax.set_title("Why suspended programs stopped, by the phase they stopped in", loc="left", color=INK, fontsize=11)
    save(fig, "failure_modes_by_phase")


EFFICACY = "#d62828"
ATTRIBUTION_COLORS = {  # report.attribution.GROUP_LABELS, in stacking order; shades of the efficacy cause color
    "not_engaged": "#7a0e0e", "engaged_no_benefit": EFFICACY, "trial_design": "#ec7a7a", "toxicity": "#f5b3b3",
    "indeterminate": "#fbe3e3",
}
SHOWN_COLORS = {  # report.stop_causes.SHOWN, in stacking order; spectrum order, efficacy first
    "efficacy": EFFICACY, "safety": "#f77f00", "business_strategic": "#2a9d8f", "operational": "#277da1",
    "positive_not_advanced": "#6a4c93", "unknown": "#e8e6e0",
}


def dark(color: str) -> bool:
    """Whether white text reads better than dark text on this fill."""
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.55


def stacked(ax, y, segments, height=0.62, gap=0.004):
    """One 100% bar of (share, color, hatched) segments with small gaps, labelled where wide enough."""
    start = 0.0
    for w, color, hatched in segments:
        if w > gap:
            ax.add_patch(matplotlib.patches.Rectangle((start + gap / 2, y - height / 2), w - gap, height, facecolor=color,
                                                      hatch="////" if hatched else None,
                                                      edgecolor="white" if hatched else "none", linewidth=0))
        if w >= 0.055:
            ax.text(start + w / 2, y, f"{w:.0%}", ha="center", va="center", fontsize=10, fontweight="bold",
                    color="white" if dark(color) else INK2,
                    bbox=dict(boxstyle="square,pad=0.25", fc=color, ec="none") if hatched else None)
        start += w


def efficacy_attribution():
    n = json.load(open(os.path.join(OUT, "attribution", "numbers.json")))
    shown = pd.read_csv(os.path.join(OUT, "stop_causes", "programs.csv")).shown.dropna()
    total = len(shown)
    after = [(float((shown == c).mean()), col, c == "unknown") for c, col in SHOWN_COLORS.items()]
    e = n["phase23"]
    efficacy = [(e["groups"][g]["share"], col, g == "indeterminate") for g, col in ATTRIBUTION_COLORS.items()]

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)  # demibold falls back silently
    rc = {"font.family": ["Avenir Next", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"], "font.size": 9,
          "hatch.color": "white", "hatch.linewidth": 1.4}
    with plt.rc_context(rc):
        fig, ax = plt.subplots(figsize=(10.5, 4.9))
        fig.subplots_adjust(left=0.17, right=0.97, top=0.82, bottom=0.2)
        ax.set_xlim(0, 1)
        ax.set_ylim(0.4, 5.4)
        ax.axis("off")
        fig.text(0.03, 0.97, "Why Phase 2 and 3 programs stop",
                 fontsize=16, fontweight="demibold", color=INK, va="top")
        fig.text(0.03, 0.895, f"{total:,} industry programs that stopped in Phase 2 or 3, phase entries 2015–2025",
                 fontsize=10.5, color=MUTED, va="top")
        rows = [(4.7, "All stops", f"{total:,} programs", after),
                (1.75, "Efficacy or exposure", f"{e['programs']:,} programs", efficacy)]
        for y, label, sub, segments in rows:
            stacked(ax, y, segments)
            ax.text(-0.025, y + 0.04, label, ha="right", va="bottom", fontsize=11, color=INK, fontweight="demibold")
            ax.text(-0.025, y - 0.02, sub, ha="right", va="top", fontsize=8, color=MUTED)
        ax.text(0, 5.25, "ALL STOPS, BY CAUSE", fontsize=7.5, color=MUTED, fontweight="demibold")
        ax.text(0, 2.3, "WHY EFFICACY FAILED", fontsize=7.5, color=MUTED, fontweight="demibold")

        cause_handles = [matplotlib.patches.Patch(facecolor=col, edgecolor="white",
                                                  hatch="////" if c == "unknown" else None, label=SHOWN[c])
                         for c, col in SHOWN_COLORS.items()]
        leg = ax.legend(handles=cause_handles, ncol=3, frameon=False, fontsize=8.5, loc="upper left",
                        bbox_to_anchor=(-0.18, 0.80), handlelength=1.0, handleheight=1.0, columnspacing=1.4, labelspacing=0.6,
                        labelcolor=INK2)
        ax.add_artist(leg)
        eff_handles = [matplotlib.patches.Patch(facecolor=col, edgecolor="white",
                                                hatch="////" if g == "indeterminate" else None,
                                                label=GROUP_LABELS[g][1])
                       for g, col in ATTRIBUTION_COLORS.items()]
        ax.legend(handles=eff_handles, ncol=3, frameon=False, fontsize=8.5, loc="upper left",
                  bbox_to_anchor=(-0.18, 0.2), handlelength=1.0, handleheight=1.0, columnspacing=1.4,
                  labelspacing=0.6, labelcolor=INK2)
        save(fig, "efficacy_attribution")


def loa_bars(csv, title, name, ref):
    df = pd.read_csv(os.path.join(OUT, "section1", csv)).dropna(subset=["loa"]).sort_values("loa")
    fig, ax = plt.subplots(figsize=(6.2, 0.38 * len(df) + 1))
    y = np.arange(len(df))
    top = df.loa.idxmax()
    ax.barh(y, df.loa * 100, height=0.6, color=[ACCENT if i == top else BAR for i in df.index])
    ax.errorbar(df.loa * 100, y, xerr=[(df.loa - df.loa_lo) * 100, (df.loa_hi - df.loa) * 100],
                fmt="none", ecolor=INK2, elinewidth=1, capsize=0)
    for yi, (lab, v, hi) in enumerate(zip(df.label, df.loa, df.loa_hi)):
        if lab in ref:
            ax.plot([ref[lab]] * 2, [yi - 0.35, yi + 0.35], color=INK, linewidth=2)
        ax.text(max(hi * 100, ref.get(lab, 0)) + 0.6, yi, f"{v:.1%}", va="center", color=INK2, fontsize=8)
    ax.set_yticks(y, [stratum_name(l) for l in df.label], color=INK)
    ax.set_xlabel("Likelihood of FDA approval from Phase 1 (%), 95% CI; tick = BIO 2011–2020", color=INK2, fontsize=8)
    style(ax)
    ax.set_title(title, loc="left", color=INK, fontsize=11)
    save(fig, name)


def relative_success():
    df = pd.read_csv(os.path.join(OUT, "section2", "relative_success.csv")).dropna(subset=["rs"]).sort_values("rs")
    fig, ax = plt.subplots(figsize=(7, 0.42 * len(df) + 1))
    y = np.arange(len(df))
    genetic = df.feature.str.startswith("genetic")
    ax.barh(y, np.log2(df.rs), height=0.55, color=[ACCENT if g else BAR for g in genetic])
    ax.errorbar(np.log2(df.rs), y, xerr=[np.log2(df.rs) - np.log2(df.rs_lo), np.log2(df.rs_hi) - np.log2(df.rs)],
                fmt="none", ecolor=INK2, elinewidth=1, capsize=0)
    ax.axvline(0, color=INK2, linewidth=1)
    for yi, (v, n) in enumerate(zip(df.rs, df.n_with)):
        ax.text(max(np.log2(df.rs_hi.iloc[yi]), 0) + 0.05, yi, f"{v:.2f}× (n={n:,})", va="center",
                color=INK2, fontsize=8)
    ticks = [0.25, 0.5, 1, 2, 4]
    ax.set_xticks(np.log2(ticks), [f"{t:g}×" for t in ticks])
    ax.set_yticks(y, df.label, color=INK, fontsize=9)
    style(ax)
    ax.set_title("Relative success: LOA with the evidence ÷ LOA without it (95% CI)", loc="left", color=INK, fontsize=10)
    save(fig, "relative_success_by_evidence")


def dose_response():
    df = pd.read_csv(os.path.join(OUT, "section2", "genetic_dose_response.csv"))
    fig, ax = plt.subplots(figsize=(6.2, 2.6))
    y = np.arange(len(df))[::-1]
    ax.barh(y, df.loa * 100, height=0.6, color=[BAR if b == "none" else ACCENT for b in df.band])
    ax.errorbar(df.loa * 100, y, xerr=[(df.loa - df.loa_lo) * 100, (df.loa_hi - df.loa) * 100],
                fmt="none", ecolor=INK2, elinewidth=1, capsize=0)
    for yi, (v, hi, n) in zip(y, zip(df.loa, df.loa_hi, df.n_programs)):
        ax.text(hi * 100 + 0.4, yi, f"{v:.1%} (n={n:,})", va="center", color=INK2, fontsize=8)
    ax.set_yticks(y, [BAND_NAMES[b] for b in df.band], color=INK)
    ax.set_xlabel("Likelihood of FDA approval from Phase 1 (%), 95% CI", color=INK2, fontsize=8)
    style(ax)
    ax.set_title("Likelihood of approval by strength of human genetic support", loc="left", color=INK, fontsize=11)
    save(fig, "genetic_dose_response")


S3_GROUP = {"g3": "Human genetics", "gwas": "Human genetics", "gwas_strong": "Human genetics",
            "gwas_mid": "Human genetics", "gwas_weak": "Human genetics", "mendelian": "Human genetics",
            "mendelian_strong": "Human genetics", "somatic": "Somatic", "somatic_concordant": "Somatic",
            "mgi": "Mouse", "mgi_strong": "Mouse", "expression": "Expression and pathways",
            "reactome": "Expression and pathways", "b1": "Clinical precedent", "precedent": "Clinical precedent",
            "pan_essential": "Target liability", "constrained": "Target liability", "ko_lethal": "Target liability"}
S3_GROUP_COLORS = {"Human genetics": "#2a78d6", "Somatic": "#eb6834", "Mouse": "#1baf7a",
                   "Expression and pathways": "#eda100", "Clinical precedent": "#4a3aa7", "Target liability": "#6b6a65"}
MIN_G3_TRIALS = 10  # endpoint classes with fewer genetically supported trials are left out of the figure


def s3_evidence_map():
    df = pd.read_csv(os.path.join(OUT, "section3", "evidence_map.csv"))
    df = df[df.scope == "C2"].set_index("feature")
    rows = [f for f in S3_MAP_ROWS if pd.notna(df.at[f, "rr"])]
    fig, ax = plt.subplots(figsize=(9.5, 0.36 * len(rows) + 1.2))
    for i, f in enumerate(rows):
        y = len(rows) - 1 - i
        r = df.loc[f]
        color = S3_GROUP_COLORS[S3_GROUP[f]]
        ax.plot([np.log2(r.lo), np.log2(r.hi)], [y, y], color=color, linewidth=2, solid_capstyle="round")
        ax.plot(np.log2(r.rr), y, "o", color=color, markersize=6, markeredgecolor="white", markeredgewidth=1)
        ax.text(3.15, y, f"{int(r.n):,}", va="center", ha="right", color=INK2, fontsize=8)
        ax.text(3.9, y, f"{r.ppv:.0%}", va="center", ha="right", color=INK2, fontsize=8)
        ax.text(4.75, y, f"{r.coverage:.0%}", va="center", ha="right", color=INK2, fontsize=8)
    for x, head in ((3.15, "Programs"), (3.9, "Advanced"), (4.75, "Share of all\nadvancers")):
        ax.text(x, len(rows) - 0.45, head, ha="right", va="bottom", color=INK2, fontsize=8)
    ax.set_ylim(-0.6, len(rows) + 0.3)
    ax.axvline(0, color=INK2, linewidth=1)
    ticks = [0.25, 0.5, 1, 2, 4]
    ax.set_xticks(np.log2(ticks), [f"{t:g}×" for t in ticks])
    ax.set_xlim(np.log2(0.2), 4.85)
    ax.set_yticks(range(len(rows)), [df.at[f, "label"] for f in rows][::-1], color=INK, fontsize=9)
    ax.set_xlabel("Risk ratio of reaching Phase 3 or approval within 4 years of Phase 2 entry, "
                  "adjusted; bars: 95% CI", color=INK2, fontsize=8)
    style(ax)
    ax.set_title("Phase 2 programs, 2015–2020: evidence for the disease as of the year before entry",
                 loc="left", color=INK, fontsize=10, pad=24)
    save(fig, "s3_evidence_map")


def s3_endpoints():
    df = pd.read_csv(os.path.join(OUT, "section3", "endpoint_classes.csv"))
    df = df[(df.scope == "all") & df.endpoint_class.isin(S3_ENDPOINTS) & (df.n >= MIN_G3_TRIALS)] \
        .set_index("endpoint_class")
    order = [c for c in S3_ENDPOINTS if c in df.index]
    fig, ax = plt.subplots(figsize=(8.5, 0.42 * len(order) + 1.2))
    for i, c in enumerate(order):
        y = len(order) - 1 - i
        r = df.loc[c]
        ax.plot([r.rate_without * 100, r.ppv * 100], [y, y], color=GRID, linewidth=3, solid_capstyle="round")
        ax.plot(r.rate_without * 100, y, "o", color=BAR, markersize=8, markeredgecolor="white", markeredgewidth=1.5)
        ax.plot(r.ppv * 100, y, "o", color=ACCENT, markersize=8, markeredgecolor="white", markeredgewidth=1.5)
        ax.text(101, y, f"{int(r.n):,} / {int(r.n_cohort):,}", va="center", color=INK2, fontsize=8)
    ax.text(101, len(order) - 0.45, "Trials with genetics\n/ all trials", va="bottom", color=INK2, fontsize=8)
    ax.set_ylim(-0.6, len(order) + 0.3)
    ax.set_yticks(range(len(order)), [S3_ENDPOINTS[c] for c in order][::-1], color=INK, fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Primary endpoint not met (%): grey, no germline genetics for the disease; blue, with it",
                  color=INK2, fontsize=8)
    style(ax)
    ax.set_title("Randomised industry Phase 2/3 efficacy trials since 2010, by primary endpoint",
                 loc="left", color=INK, fontsize=10, pad=24)
    save(fig, "s3_endpoints")


def s3_specificity():
    n = json.load(open(os.path.join(OUT, "section3", "numbers.json")))
    names = {"g0": "None (G0)", "g1": "Unrelated diseases only (G1)", "g2": "Related disease only (G2)",
             "g3": "The program's disease (G3)"}
    fig, axes = plt.subplots(1, 2, figsize=(9, 2.6), sharex=True)
    for ax, lv, title in zip(axes, (n["h1"], n["levels_onc"]), ("Non-oncology", "Oncology")):
        rows = [(k, lv[k]["ppv"], lv[k].get("rr")) for k in ("g0", "g1", "g2", "g3")]
        y = np.arange(len(rows))[::-1]
        ax.barh(y, [100 * v for _, v, _ in rows], height=0.6, color=[BAR, BAR, BAR, ACCENT])
        for yi, (k, v, rr) in zip(y, rows):
            ax.text(100 * v + 0.8, yi, f"{v:.0%}" + ("" if rr is None else f"  ({rr:.2f}× G0)"), va="center",
                    color=INK2, fontsize=8)
        ax.set_yticks(y, [names[k] for k, _, _ in rows], color=INK, fontsize=8)
        ax.set_title(title, loc="left", color=INK, fontsize=9)
        ax.set_xlim(0, 50)
        style(ax)
    axes[1].set_yticklabels([])
    fig.suptitle("Phase 2 programs advancing within 4 years, by where the target's germline genetic evidence lay "
                 "before entry", x=0.01, y=1.06, ha="left", color=INK, fontsize=10)
    save(fig, "s3_specificity")


def s3_rules():
    df = pd.read_csv(os.path.join(OUT, "section3", "rules.csv")).dropna(subset=["discovery_rr", "confirmation_rr"])
    fig, ax = plt.subplots(figsize=(8.5, 0.5 * len(df) + 1.2))
    for i, r in enumerate(df.itertuples()):
        y = len(df) - 1 - i
        for dy, (rr, lo, hi, color) in ((0.14, (r.discovery_rr, r.discovery_lo90, r.discovery_hi90, BAR)),
                                        (-0.14, (r.confirmation_rr, r.confirmation_lo90, r.confirmation_hi90, ACCENT))):
            if rr == 0:
                ax.text(np.log2(0.13), y + dy, "no exposed program advanced", va="center", color=color, fontsize=7)
                continue
            lo, hi = max(lo, 0.125), min(max(hi, 0.125), 16)
            ax.plot([np.log2(lo), np.log2(hi)], [y + dy] * 2, color=color, linewidth=2)
            ax.plot(np.log2(rr), y + dy, "o", color=color, markersize=6, markeredgecolor="white")
    ax.axvline(0, color=INK2, linewidth=1)
    ax.axvline(np.log2(DISCOVERY_FLOOR), color=GRID, linewidth=1, linestyle="--")
    ticks = [0.25, 0.5, 1, 2, 4, 8]
    ax.set_xticks(np.log2(ticks), [f"{t:g}×" for t in ticks])
    ax.set_yticks(range(len(df)), [rule_name(r) for r in df.itertuples()][::-1], color=INK, fontsize=8)
    ax.set_xlabel("Crude risk ratio of advancing within 4 years (90% target bootstrap); grey: discovery targets, "
                  "blue: held-out targets; dashed: the discovery bar", color=INK2, fontsize=8)
    style(ax)
    ax.set_title("Evidence rules applied at Phase 2 entry, discovery and confirmation (* added after the plan)",
                 loc="left", color=INK, fontsize=10)
    save(fig, "s3_rules")


def main():
    failure_modes()
    loa_bars("loa_by_area.csv", "Likelihood of approval by disease area", "loa_by_area", bio.AREA_LOA)
    loa_bars("loa_by_modality.csv", "Likelihood of approval by modality", "loa_by_modality", bio.MODALITY_LOA)
    if os.path.exists(os.path.join(OUT, "section2", "relative_success.csv")):
        relative_success()
        dose_response()
    if os.path.exists(os.path.join(OUT, "attribution", "numbers.json")):
        efficacy_attribution()
    if os.path.exists(os.path.join(OUT, "section3", "rules.csv")):
        s3_evidence_map()
        s3_specificity()
        s3_endpoints()
        s3_rules()


if __name__ == "__main__":
    main()
