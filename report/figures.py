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
from report.render import S3_ENDPOINTS, S3_MAP_ROWS, band_label, s3_types, stratum_name
from report.attribution import SUBCAUSE_LABELS
from report.stop_causes import BREAKDOWN, SHOWN, SUBCAUSE_NAMES

OUT = os.path.join(frame.REPO, "report", "output")
FIG = os.path.join(OUT, "figures")

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
GRID, BAR, ACCENT = "#e4e3df", "#c3c2b7", "#2a78d6"
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


EFFICACY = "#d62828"
ATTRIBUTION_COLORS = {  # report.attribution.SUBCAUSE_LABELS, in stacking order; shades of the efficacy cause color
    "not_engaged": "#7a0e0e", "engaged_no_benefit": EFFICACY, "trial_design": "#ec7a7a", "toxicity_offset": "#f5b3b3",
    "no_engagement_data": "#fbe3e3",
}
SHOWN_COLORS = {  # report.stop_causes.SHOWN, in stacking order; spectrum order, efficacy first
    "efficacy": EFFICACY, "safety": "#f77f00", "sponsor_decision": "#2a9d8f", "operational": "#277da1",
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


REGISTERED = {  # each registry reason (report.section1.REASON_ORDER) as the cause bar's category
    "efficacy: stated": "efficacy", "efficacy: primary endpoint not met": "efficacy",
    "PK, dose or formulation": "efficacy", "safety": "safety",
    "business or strategic (explicit)": "sponsor_decision", "sponsor decision, unspecified": "sponsor_decision",
    "enrollment, operational or regulatory": "operational", "positive readout, not advanced": "positive_not_advanced",
    "other stated reason": "unknown", "results posted, no reason stated, endpoint not assessable": "unknown",
    "results posted, mixed primary endpoint": "unknown",
    "completed, no results posted, no reason stated": "unknown", "stopped, no reason stated": "unknown",
}


def registered_vs_traced():
    """Per phase, the same stopped programs by the cause their registry reason gives and by the cause after tracing."""
    n = json.load(open(os.path.join(OUT, "stop_causes", "numbers.json")))
    traced = pd.read_csv(os.path.join(OUT, "stop_causes", "programs.csv"))
    entry = pd.to_datetime(traced.phase_entry).dt.year
    stopped = traced[entry.between(n["window"]["from"], n["window"]["to"]) & traced.shown.notna()]
    stopped = stopped.assign(registered=stopped.registry_reason.map(REGISTERED))

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    rc = {"font.family": ["Avenir Next", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"], "font.size": 9,
          "hatch.color": "white", "hatch.linewidth": 1.4}
    with plt.rc_context(rc):
        fig, ax = plt.subplots(figsize=(10.5, 5.0))
        fig.subplots_adjust(left=0.2, right=0.97, top=0.82, bottom=0.02)
        ax.set_xlim(0, 1)
        ax.set_ylim(0.15, 8.0)
        ax.axis("off")
        fig.text(0.03, 0.975, "Stop causes as registered and after tracing", fontsize=16, fontweight="demibold",
                 color=INK, va="top")
        fig.text(0.03, 0.92, f"Industry programs that stopped, phase entries {n['window']['from']}–{n['window']['to']}: "
                 "the reason on ClinicalTrials.gov, and the cause once each stop was traced",
                 fontsize=10.5, color=MUTED, va="top")
        for k, phase in enumerate((1, 2, 3)):
            p = stopped[stopped.phase.eq(phase)]
            top = 7.4 - k * 2.25
            for j, (col, label) in enumerate((("registered", "As registered"), ("shown", "After tracing"))):
                y = top - j * 0.82
                stacked(ax, y, [(float((p[col] == c).mean()), color, c == "unknown") for c, color in SHOWN_COLORS.items()],
                        height=0.62)
                ax.text(-0.015, y, label, ha="right", va="center", fontsize=8.5, color=INK2)
            ax.text(-0.135, top - 0.38, f"Phase {phase}", ha="right", va="bottom", fontsize=10.5, color=INK,
                    fontweight="demibold")
            ax.text(-0.135, top - 0.43, f"{len(p):,} programs", ha="right", va="top", fontsize=7.5, color=MUTED)
        ax.legend(handles=[matplotlib.patches.Patch(facecolor=col, edgecolor="white",
                                                    hatch="////" if c == "unknown" else None, label=SHOWN[c])
                           for c, col in SHOWN_COLORS.items()],
                  frameon=False, fontsize=8.5, loc="upper left", handlelength=1.0, handleheight=1.0,
                  columnspacing=1.4, labelspacing=0.5, labelcolor=INK2, ncol=3, bbox_to_anchor=(-0.215, 0.1))
        save(fig, "stop_causes_registered_vs_traced")


def efficacy_attribution():
    """Why programs stop, and why efficacy failed, by phase: one bar per phase in each part."""
    n = json.load(open(os.path.join(OUT, "attribution", "numbers.json")))
    traced = pd.read_csv(os.path.join(OUT, "stop_causes", "programs.csv"))
    entry = pd.to_datetime(traced.phase_entry).dt.year
    in_window = traced[entry.between(n["window"]["from"], n["window"]["to"])]
    years = f"{n['window']['from']}–{n['window']['to']}"
    efficacy_of = {1: n["phase1"], 2: n["by_phase"]["2"], 3: n["by_phase"]["3"]}
    stops, failures = [], []
    for phase in (1, 2, 3):
        shown = in_window[in_window.phase.eq(phase)].shown.dropna()
        stops.append((f"Phase {phase}", f"{len(shown):,} programs",
                      [(float((shown == c).mean()), col, c == "unknown") for c, col in SHOWN_COLORS.items()]))
        e = efficacy_of[phase]
        failures.append((f"Phase {phase}", f"{e['programs']:,} programs",
                         [(e["subcauses"][g]["share"], col, g == "no_engagement_data") for g, col in ATTRIBUTION_COLORS.items()]))

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)  # demibold falls back silently
    rc = {"font.family": ["Avenir Next", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"], "font.size": 9,
          "hatch.color": "white", "hatch.linewidth": 1.4}
    with plt.rc_context(rc):
        fig, ax = plt.subplots(figsize=(10.5, 6.4))
        fig.subplots_adjust(left=0.13, right=0.97, top=0.865, bottom=0.02)
        ax.set_xlim(0, 1)
        ax.set_ylim(2.2, 11)
        ax.axis("off")
        fig.text(0.03, 0.975, "Why Phase 1, 2 and 3 programs stop", fontsize=16, fontweight="demibold", color=INK, va="top")
        fig.text(0.03, 0.922, f"Industry programs that stopped, phase entries {years}", fontsize=10.5, color=MUTED, va="top")
        for header, top, rows in (("ALL STOPS, BY CAUSE", 10.9, stops), ("WHY EFFICACY FAILED", 6.4, failures)):
            ax.text(0, top, header, fontsize=7.5, color=MUTED, fontweight="demibold")
            for k, (label, sub, segments) in enumerate(rows):
                y = top - 0.65 - k * 0.95
                stacked(ax, y, segments, height=0.66)
                ax.text(-0.02, y + 0.03, label, ha="right", va="bottom", fontsize=10.5, color=INK, fontweight="demibold")
                ax.text(-0.02, y - 0.02, sub, ha="right", va="top", fontsize=7.5, color=MUTED)

        legend = dict(frameon=False, fontsize=8.5, loc="upper left", handlelength=1.0, handleheight=1.0,
                      columnspacing=1.4, labelspacing=0.5, labelcolor=INK2, ncol=3)
        cause_handles = [matplotlib.patches.Patch(facecolor=col, edgecolor="white",
                                                  hatch="////" if c == "unknown" else None, label=SHOWN[c])
                         for c, col in SHOWN_COLORS.items()]
        ax.add_artist(ax.legend(handles=cause_handles, bbox_to_anchor=(-0.12, 0.645), **legend))
        eff_handles = [matplotlib.patches.Patch(facecolor=col, edgecolor="white",
                                                hatch="////" if g == "no_engagement_data" else None,
                                                label=SUBCAUSE_LABELS[g][1])
                       for g, col in ATTRIBUTION_COLORS.items()]
        ax.legend(handles=eff_handles, bbox_to_anchor=(-0.12, 0.135), **legend)
        save(fig, "efficacy_attribution")


def stop_subcauses():
    """Each cause of Phase 2 and 3 stops broken down by subcause, one panel per cause in its color from the cause bar;
    not stated in gray. Shares are of all the cause's stops, including the few with no subcause."""
    n = json.load(open(os.path.join(OUT, "stop_causes", "numbers.json")))
    panels = [(c, n["subcauses"][c], n["subcause_programs"][c]) for c in ("sponsor_decision", "safety", "operational", "positive_not_advanced",
                                                "unknown") if c in n["subcauses"]]
    sizes = [len(BREAKDOWN[c]) for c, _, _ in panels]
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    rc = {"font.family": ["Avenir Next", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"], "font.size": 9}
    with plt.rc_context(rc):
        fig, axes = plt.subplots(len(panels), 1, figsize=(8.6, 0.24 * sum(sizes) + 0.42 * len(panels) + 1.0),
                                 gridspec_kw={"height_ratios": sizes, "hspace": 0.5})
        fig.subplots_adjust(left=0.3, right=0.9, top=1 - 1.05 / fig.get_figheight(), bottom=0.02)
        fig.text(0.03, 1 - 0.18 / fig.get_figheight(), "What each cause breaks down into", fontsize=14,
                 fontweight="demibold", color=INK, va="top")
        fig.text(0.03, 1 - 0.46 / fig.get_figheight(),
                 f"Phase 2 and 3 industry programs that stopped, phase entries {n['window']['from']}–{n['window']['to']}",
                 fontsize=9.5, color=MUTED, va="top")
        for ax, (cause, dist, total) in zip(axes, panels):
            order = [x for x in BREAKDOWN[cause] if x != "not_stated"]
            order = sorted(order, key=lambda x: -dist[x]["share"]) + (["not_stated"] if "not_stated" in dist else [])
            y = np.arange(len(order))[::-1]
            color = SHOWN_COLORS[cause] if cause != "unknown" else "#a8a59c"
            for yi, x in zip(y, order):
                w = dist[x]["share"]
                ax.add_patch(matplotlib.patches.Rectangle((0, yi - 0.34), w, 0.68, linewidth=0,
                                                          facecolor="#d9d7d1" if x == "not_stated" else color))
                ax.text(w + 0.008, yi, f"{w:.0%}  ({dist[x]['n']:,})", va="center", fontsize=8.5, color=INK2)
            ax.set_yticks(y, [SUBCAUSE_NAMES[x] for x in order], fontsize=9, color=INK2)
            ax.set_xlim(0, 1)
            ax.set_ylim(-0.6, len(order) - 0.4)
            ax.tick_params(length=0)
            ax.set_xticks([])
            for side in ax.spines.values():
                side.set_visible(False)
            ax.set_title(f"{SHOWN[cause].upper()} · {total:,} programs", loc="left", fontsize=7.5, color=MUTED,
                         fontweight="demibold", x=-0.36)
        save(fig, "stop_subcauses")


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


def genetics_by_area():
    df = pd.read_csv(os.path.join(OUT, "section2", "relative_success_by_area.csv"))
    df = df[df.feature.eq("genetic_any")].dropna(subset=["rs"]).sort_values("rs")
    pooled = pd.read_csv(os.path.join(OUT, "section2", "relative_success.csv")).set_index("feature").loc["genetic_any"]
    fig, ax = plt.subplots(figsize=(7, 0.42 * (len(df) + 1) + 1))
    labels = [*df.group_label, "All areas"]
    rs, lo, hi = [*df.rs, pooled.rs], [*df.rs_lo, pooled.rs_lo], [*df.rs_hi, pooled.rs_hi]
    n = [*df.n_with, pooled.n_with]
    y = np.arange(len(labels))
    ax.errorbar(np.log2(rs), y, xerr=[np.log2(rs) - np.log2(lo), np.log2(hi) - np.log2(rs)], fmt="none",
                ecolor=INK2, elinewidth=1, capsize=0)
    ax.scatter(np.log2(rs), y, s=[28] * len(df) + [60], marker="o", zorder=3,
               color=[ACCENT] * len(df) + [INK], edgecolors="none")
    ax.axvline(0, color=INK2, linewidth=1)
    for yi in y:
        ax.text(max(np.log2(hi[yi]), 0) + 0.08, yi, f"{rs[yi]:.2f}× (n={n[yi]:,})", va="center", color=INK2, fontsize=8)
    ticks = [0.5, 1, 2, 4, 8]
    ax.set_xticks(np.log2(ticks), [f"{t:g}×" for t in ticks])
    ax.set_yticks(y, labels, color=INK, fontsize=9)
    ax.get_yticklabels()[-1].set_fontweight("bold")
    style(ax)
    ax.set_title("Relative success of human genetic evidence, by disease area (95% CI)", loc="left", color=INK,
                 fontsize=10)
    save(fig, "genetics_by_area")


def dose_response():
    df = pd.read_csv(os.path.join(OUT, "section2", "genetic_dose_response.csv"))
    fig, ax = plt.subplots(figsize=(7.4, 2.6))
    y = np.arange(len(df))[::-1]
    ax.barh(y, df.loa * 100, height=0.6, color=[BAR if b == "none" else ACCENT for b in df.band])
    ax.errorbar(df.loa * 100, y, xerr=[(df.loa - df.loa_lo) * 100, (df.loa_hi - df.loa) * 100],
                fmt="none", ecolor=INK2, elinewidth=1, capsize=0)
    for yi, (v, hi, n) in zip(y, zip(df.loa, df.loa_hi, df.n_programs)):
        ax.text(hi * 100 + 0.4, yi, f"{v:.1%} (n={n:,})", va="center", color=INK2, fontsize=8)
    ax.set_yticks(y, [band_label(*b) for b in zip(df.band, df.score_from, df.score_to)], color=INK, fontsize=9)
    ax.set_xlabel("Likelihood of FDA approval from Phase 1 (%), 95% CI", color=INK2, fontsize=8)
    ax.set_ylabel("Genetic association score before entry", color=INK2, fontsize=8)
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
    ax.set_title("Phase 2 programs, 2008–2019: evidence for the disease as of the year before entry",
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
    ax.set_title("Randomised industry Phase 2/3 efficacy trials started 2008–2019, by primary endpoint",
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


# One row per kind of evidence, then its narrower versions. Each row names its Section 2 relative-success
# feature (report.section2.FEATURES) and its Section 3 kind (evidence_types.csv) or refinement (refinements.csv).
EVIDENCE_ROWS = [  # (label, family, Section 2 feature, Section 3 kind or refinement, narrower version)
    ("Germline genetics for the disease", "Human genetics", "genetic_any", "germline", False),
    ("GWAS", "Human genetics", "genetic_gwas", None, True),
    ("Rare-variant or Mendelian", "Human genetics", "genetic_rare", None, True),
    ("GWAS with locus-to-gene ≥ 0.8", "Human genetics", None, "gwas_strong", True),
    ("Mendelian, non-hereditary disease", "Human genetics", None, "mendelian_nonhereditary", True),
    ("GWAS and rare-variant together", "Human genetics", None, "allelic_series", True),
    ("Drug raises function, hereditary disease", "Human genetics", None, "hereditary_activator", True),
    ("Genetics points the drug's way", "Human genetics", None, "mechanism_concordant", True),
    ("Somatic driver for the tumour", "Somatic", "somatic", "somatic", False),
    ("Driver matches the drug", "Somatic", None, "somatic_matching", True),
    ("Mouse model of the disease", "Mouse", "animal_model", "animal", False),
    ("Close phenotype match", "Mouse", None, "animal_close", True),
    ("Mouse model points the drug's way", "Mouse", None, "animal_direction", True),
    ("Expressed differently in the disease", "Expression and pathways", "rna_expression", "expression", False),
    ("Expression up + drug that lowers function", "Expression and pathways", None, "expression_inhibitor", True),
    ("Disease pathway (Reactome)", "Expression and pathways", "affected_pathway", "pathway", False),
    ("Target liability", "Target liability", None, "liability", False),
    ("Intolerant of loss of function", "Target liability", "constrained", None, True),
    ("Liability + drug that lowers function", "Target liability", None, "liability_inhibitor", True),
    ("Drug potent at the target (≤ 100 nM)", "Drug pharmacology", "assay_potent", None, False),
    ("Very potent (≤ 10 nM)", "Drug pharmacology", "assay_very_potent", None, True),
    ("Functional potency measured in cells", "Drug pharmacology", "assay_cell_functional", None, True),
    ("≥ 100-fold selective over off-targets", "Drug pharmacology", "assay_selective", None, True),
    ("Approved drug on the target, related disease", "Clinical precedent", None, "benchmark", False),
]
FAMILY_COLORS = {**S3_GROUP_COLORS, "Drug pharmacology": "#b04a8f"}
# Lines first published in 2019, which no program in the window could have had before entry: scored on
# today's data (Section 2 relative_success_untimed.csv, Section 3 hindsight.csv) and drawn dashed.
HINDSIGHT_ROWS = [("CRISPR screen in cells", "Expression and pathways", "cell_line_screen_untimed", "cell_screen"),
                  ("Essential in most cell lines", "Target liability", "pan_essential_untimed", "pan_essential")]


def evidence_translates():
    """Each kind of evidence and its narrower versions, three ways: relative success to approval from any
    phase; the adjusted risk ratio of advancing from Phase 2 within four years; and the relative risk of
    advancing from Phase 2 with the other evidence lines held fixed (Section 2's joint model). A filled
    dot is a 95% interval clear of 1 (middle panel: a Holm-corrected p below 0.05)."""
    rs = pd.concat([pd.read_csv(os.path.join(OUT, "section2", f)) for f in
                    ("relative_success.csv", "relative_success_untimed.csv")]).set_index("feature")
    joint = pd.read_csv(os.path.join(OUT, "section2", "joint_rr_by_phase.csv"))
    joint = joint[joint.phase == 2].set_index("feature")
    types, refined = s3_types()
    s3 = pd.concat([types.set_index("type"), refined.set_index("refinement")])
    s3.loc["benchmark", "holm_p"] = s3.at["benchmark", "p"]
    late = pd.read_csv(os.path.join(OUT, "section3", "hindsight.csv")).set_index("line")
    rows = []  # (label, family, narrow, approval, Phase 2, Phase 2 held fixed, Section 3 row, hindsight)
    for label, family, f2, f3, narrow in EVIDENCE_ROWS:
        left = rs.loc[f2] if f2 and pd.notna(rs.at[f2, "rs"]) else None
        mid = s3.loc[f3] if f3 and pd.notna(s3.at[f3, "rr"]) else None
        held = joint.loc[f2] if f2 in joint.index else None
        if left is not None or mid is not None:
            rows.append((label, family, narrow, left, mid, held, s3.loc[f3] if f3 else None, False))
    for label, family, f2, f3 in HINDSIGHT_ROWS:
        left = rs.loc[f2] if pd.notna(rs.at[f2, "rs"]) else None
        mid = late.loc[f3] if pd.notna(late.at[f3, "rr"]) else None
        rows.append((label, family, False, left, mid, None, late.loc[f3], True))
    first_late = next(i for i, r in enumerate(rows) if r[7])
    ys, y = [], 0.0
    for i, r in enumerate(rows):
        y -= 1 if i == 0 or r[2] or (r[7] and i != first_late) else 2.3 if i == first_late else 1.5
        ys.append(y)
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(16, 0.34 * len(rows) + 1.8), sharey=True,
                                     gridspec_kw={"wspace": 0.08})
    lim = (np.log2(0.2), np.log2(7))

    def dot(ax, yi, est, lo, hi, color, filled, dashed=False):
        ax.plot([np.log2(max(lo, 0.2)), np.log2(min(hi, 7))], [yi, yi], color=color, linewidth=2,
                solid_capstyle="round", linestyle=(0, (2, 1.5)) if dashed else "-")
        ax.plot(np.log2(est), yi, "o", markersize=6, color=color, markeredgewidth=1.5,
                markerfacecolor=color if filled else "white", markeredgecolor=color)

    def column(x, yi, text):
        a3.text(np.log2(7) + x, yi, text, va="center", ha="right", color=INK2, fontsize=8)

    for yi, (label, family, narrow, left, mid, held, kind, late_row) in zip(ys, rows):
        color = MUTED if late_row else FAMILY_COLORS[family]
        if left is not None:
            dot(a1, yi, left.rs, left.rs_lo, left.rs_hi, color, left.rs_lo > 1 or left.rs_hi < 1, late_row)
            column(0.35, yi, f"{int(left.n_with):,}")
            column(1.45, yi, f"{left.loa_with:.0%} / {left.loa_without:.0%}")
        if mid is not None:
            dot(a2, yi, mid.rr, mid.lo, mid.hi, color, (mid.p if late_row else mid.holm_p) < 0.05, late_row)
        if held is not None:
            dot(a3, yi, held.rr, held.rr_lo, held.rr_hi, color, held.rr_lo > 1 or held.rr_hi < 1)
        if kind is not None:
            column(2.15, yi, f"{int(kind.n):,}")
            column(3.25, yi, f"{kind.ppv:.0%} / {kind.rate_without:.0%}")
    top = ys[0] + 0.7
    for x, head in ((0.35, "Programs"), (1.45, "Approved:\nwith / without"), (2.15, "Phase 2\nprograms"),
                    (3.25, "Advanced:\nwith / without")):
        a3.text(np.log2(7) + x, top, head, ha="right", va="bottom", color=INK2, fontsize=8)
    ticks = [0.25, 0.5, 1, 2, 4]
    for ax, title, xlabel in (
            (a1, "Reaching approval, from any phase", "Relative success: approval with ÷ without (95% CI)"),
            (a2, "Advancing from Phase 2 within 4 years", "Adjusted risk ratio (95% CI)"),
            (a3, "Advancing from Phase 2, other lines held fixed", "Relative risk, all lines in one model (95% CI)")):
        ax.axvline(0, color=INK2, linewidth=1)
        ax.set_xticks(np.log2(ticks), [f"{t:g}×" for t in ticks])
        ax.set_xlim(*lim)
        ax.set_xlabel(xlabel, color=INK2, fontsize=8)
        ax.set_title(title, loc="left", color=INK, fontsize=9)
        style(ax)
    a1.set_yticks(ys, [("      " if narrow else "") + label for label, _, narrow, *_ in rows], color=INK, fontsize=8.5)
    a1.tick_params(axis="y", pad=215)
    for t, (_, _, narrow, *_, late_row) in zip(a1.get_yticklabels(), rows):
        t.set_horizontalalignment("left")
        t.set_color(INK2 if narrow or late_row else INK)
    a1.text(-0.62, ys[first_late] + 0.95, "Known only after entry: first published in 2019, scored on today's data",
            transform=a1.get_yaxis_transform(), color=INK2, fontsize=8, style="italic")
    a1.set_ylim(ys[-1] - 0.7, top + 0.9)
    fig.suptitle("Programs entering a phase in 2008–2019, by evidence known the year before entry. Indented: a "
                 "narrower version (middle panel: against the rest of its kind). Filled: interval clear of 1 "
                 "(middle panel: Holm-corrected p < 0.05)", x=0.01, ha="left", y=0.935, color=INK2, fontsize=8)
    save(fig, "evidence_translates")


# Eras of drug discovery: (from, to, technology, unit of the biological hypothesis, examples).
ERAS = [
    (1820, 1935, "Observation, natural products, physiology", "Therapeutic effect or organismal phenotype",
     "Morphine, quinine, digitalis, aspirin"),
    (1900, 1965, "Quantitative pharmacology and biochemistry", "Receptor activity, enzyme, metabolic pathway",
     "Sulfonamides, receptor theory, enzyme inhibitors"),
    (1950, 1985, "Systematic medicinal chemistry", "Desired pharmacological mechanism",
     "β-blockers, H2 antagonists, antimetabolites"),
    (1970, 1995, "Recombinant DNA and molecular cloning", "Named gene and protein",
     "Recombinant insulin, cloned GPCRs, channels, kinases"),
    (1990, 2005, "Genomics, HTS, automation", "Target plus compound library",
     "Imatinib and kinase programs, genomic target portfolios"),
    (2000, 2015, "Human genetics and functional genomics", "Target–disease association",
     "GWAS, RNAi, CRISPR, dependency maps"),
    (2010, 2026, "Multimodal evidence and predictive modelling", "Target–indication–mechanism–patient context",
     "Open Targets, gnomAD, single-cell perturbation, AlphaFold"),
]


def history():
    fig, ax = plt.subplots(figsize=(10, 5.6))
    shades = plt.get_cmap("Blues")(np.linspace(0.3, 0.85, len(ERAS)))
    for i, ((start, end, tech, unit, examples), shade) in enumerate(zip(ERAS, shades)):
        y = len(ERAS) - 1 - i
        ax.barh(y, end - start, left=start, height=0.5, color=shade)
        ax.text(end + 3, y + 0.25, tech, va="center", fontsize=8, fontweight="bold", color=INK)
        ax.text(end + 3, y, unit, va="center", fontsize=8, color=INK, style="italic")
        ax.text(end + 3, y - 0.25, examples, va="center", fontsize=7, color=INK2)
    ax.set_xlim(1820, 2140)
    ax.set_xticks(range(1850, 2030, 25))
    ax.set_yticks([])
    ax.set_ylim(-0.6, len(ERAS) - 0.4)
    style(ax)
    ax.set_title("Each era narrowed the unit of the biological hypothesis (in italics)", loc="left", color=INK,
                 fontsize=10)
    save(fig, "history")


def phase_funnel():
    """Share of Phase 1 entrants still in development at each later phase, from the product of the
    transition rates; the label on each step is that transition's rate."""
    o = pd.read_csv(os.path.join(OUT, "section1", "loa_overall.csv")).set_index("label")
    cohorts = {"all programs": ("All programs", ACCENT),
               "programs with a US-sited industry trial in the phase": ("Developed in the US", "#1baf7a")}
    stages = ["Phase 1", "Phase 2", "Phase 3", "Approval"]
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    x = np.arange(len(stages))
    bio_steps = [bio.TRANSITIONS[ph] / 100 for ph in (1, 2, 3)]
    ax.plot(x, 100 * np.cumprod([1, *bio_steps]), "_", color=INK, markersize=16, markeredgewidth=2,
            label="BIO 2011–2020")
    for key, (name, color) in cohorts.items():
        steps = [o.at[key, f"ph{ph}_rate"] for ph in (1, 2, 3)]
        y = 100 * np.cumprod([1, *steps])
        ax.plot(x, y, "-o", color=color, linewidth=2, markersize=6, markeredgecolor="white", label=name)
        below = color != ACCENT
        for xi, (a, b, r) in enumerate(zip(y[:-1], y[1:], steps)):
            ax.text(xi + 0.5, (a + b) / 2 + (-9 if below else 9), f"{r:.0%}", ha="center",
                    va="center", color=color, fontsize=8)
        ax.text(x[-1] + 0.12, y[-1] + (4 if below else -4), f"{y[-1]:.1f}%", va="center", color=color,
                fontsize=9, fontweight="bold")
    ax.set_xticks(x, stages, color=INK)
    ax.set_ylim(0, 105)
    ax.set_xlim(-0.2, len(stages) - 0.55)
    ax.set_ylabel("Share of Phase 1 entrants (%)", color=INK2, fontsize=8)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    style(ax)
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.grid(axis="x", visible=False)
    ax.set_title("Programs entering a phase in 2008–2019: share still in development at each phase; "
                 "each step's label is its transition rate", loc="left", color=INK, fontsize=9)
    save(fig, "phase_funnel")



def forest(ax, rows, lim=(0.25, 4)):
    """Dot and 95% interval per (y, estimate, lo, hi, color, filled) on a log2 axis with a line at 1."""
    for y, est, lo, hi, color, filled in rows:
        ax.plot([np.log2(max(lo, lim[0])), np.log2(min(hi, lim[1]))], [y, y], color=color, linewidth=2,
                solid_capstyle="round")
        ax.plot(np.log2(est), y, "o", markersize=6, color=color, markeredgewidth=1.5,
                markerfacecolor=color if filled else "white", markeredgecolor=color)
    ax.axvline(0, color=INK2, linewidth=1)
    ticks = [t for t in (0.25, 0.5, 1, 2, 4) if lim[0] <= t <= lim[1]]
    ax.set_xticks(np.log2(ticks), [f"{t:g}×" for t in ticks])
    ax.set_xlim(np.log2(lim[0]), np.log2(lim[1]))
    style(ax)


def prediction():
    m = pd.read_csv(os.path.join(OUT, "section2", "prediction_metrics.csv"))
    ab = pd.read_csv(os.path.join(OUT, "section2", "prediction_ablation.csv")).sort_values("auc_drop")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 2.9), gridspec_kw={"width_ratios": [1, 1.1], "wspace": 0.9})
    names = {"covariates": "Area, modality, novelty, year", "covariates+evidence": "… plus the evidence lines",
             "evidence": "Evidence lines only"}
    colors = {"covariates": BAR, "covariates+evidence": ACCENT, "evidence": INK2}
    ticks, labels, y = [], [], 0
    n2 = json.load(open(os.path.join(OUT, "section2", "numbers.json")))
    later = f"Later programs held out ({n2['prediction_split_year'] + 1}–{n2['prediction_window'][1]})"
    for split, title in (("grouped_cv", "Targets held out"), ("temporal", later)):
        d = m[m.split == split].set_index("features")
        labels.append(title)
        ticks.append(y)
        y -= 1
        for f in names:
            if f in d.index:
                r = d.loc[f]
                a1.plot([r.auc_lo, r.auc_hi], [y, y], color=colors[f], linewidth=2)
                a1.plot(r.auc, y, "o", color=colors[f], markersize=6, markeredgecolor="white")
                ticks.append(y)
                labels.append("    " + names[f])
                y -= 1
        y -= 0.4
    a1.axvline(0.5, color=INK2, linewidth=1)
    a1.set_yticks(ticks, labels, fontsize=8, color=INK)
    for t, lab in zip(a1.get_yticklabels(), labels):
        t.set_fontweight("normal" if lab.startswith(" ") else "bold")
        t.set_horizontalalignment("left")
    a1.tick_params(axis="y", pad=150)
    a1.set_xlim(0.45, 0.75)
    a1.set_xlabel("Held-out AUC (95% CI); 0.5 = chance", color=INK2, fontsize=8)
    a1.set_title("How well approval is predicted", loc="left", color=INK, fontsize=9)
    style(a1)
    yy = np.arange(len(ab))
    a2.plot([-ab.drop_hi, -ab.drop_lo], [yy, yy], color=ACCENT, linewidth=2)
    a2.plot(-ab.auc_drop, yy, "o", color=ACCENT, markersize=6, markeredgecolor="white")
    a2.axvline(0, color=INK2, linewidth=1)
    a2.set_yticks(yy, ab.label, fontsize=8, color=INK)
    a2.set_xlabel("Change in AUC when the line is removed (95% CI)", color=INK2, fontsize=8)
    a2.set_title("What each line contributes", loc="left", color=INK, fontsize=9)
    style(a2)
    fig.suptitle(f"Programs entering Phase 1 in {n2['prediction_window'][0]}–{n2['prediction_window'][1]}, approval within "
                 f"{n2['prediction_years']} years", x=0.01, y=1.04, ha="left",
                 color=INK2, fontsize=8)
    save(fig, "prediction")


HYPOTHESES = [  # (key, short label, path to its estimate in section3/numbers.json, ratio field)
    ("H1", "Genetics for the disease vs none, outside oncology", ("h1", "g3"), "rr"),
    ("H2", "Same target: diseases its genetics points to vs its other diseases", ("h2",), "or"),
    ("H3", "Genetics and drug point the same way (per step)", ("h3", "trend"), "rr"),
    ("H4", "Genetics' effect on missed endpoints, per step from proximal to distal", ("h4", "fdaaa",
                                                                                     "interaction_per_step"), "rr"),
    ("H5", "Genetics lowers efficacy failure more than business failure", ("h5", "ratio_f_bizops_vs_f_efficacy"),
     "rr"),
    ("H6", "Target liability raises safety failure, outside oncology", ("h6", "safety"), "rr"),
    ("H7", "Oncology: somatic driver matching the drug", ("h7",), "rr"),
]
MEASURES = {"H1": "risk ratio", "H2": "odds ratio", "H3": "risk ratio", "H4": "ratio of risk ratios",
            "H5": "ratio of risk ratios", "H6": "risk ratio", "H7": "risk ratio"}


def s3_hypotheses():
    n = json.load(open(os.path.join(OUT, "section3", "numbers.json")))
    rows, labels = [], []
    for i, (h, label, path, field) in enumerate(HYPOTHESES):
        r = n
        for k in path:
            r = r[k]
        holm_p = n["holm"].get(h, 1)
        rows.append((-i, r[field], r["lo"], r["hi"], ACCENT if holm_p < 0.05 else BAR, holm_p < 0.05))
        labels.append(f"{h}  {label}")
    fig, ax = plt.subplots(figsize=(9, 0.4 * len(rows) + 1.1))
    forest(ax, rows, lim=(0.25, 8))
    ax.set_xticks(np.log2([0.25, 0.5, 1, 2, 4, 8]), ["0.25×", "0.5×", "1×", "2×", "4×", "8×"])
    for y, *_ in rows:
        h = HYPOTHESES[-y][0]
        ax.text(np.log2(8) + 0.15, y, MEASURES[h], va="center", color=INK2, fontsize=8)
    ax.set_yticks([r[0] for r in rows], labels, color=INK, fontsize=8.5)
    ax.set_xlabel("Estimate (95% CI); blue: supported after Holm correction across the seven", color=INK2,
                  fontsize=8)
    ax.set_title("The pre-registered hypotheses", loc="left", color=INK, fontsize=10)
    save(fig, "s3_hypotheses")


def main():
    history()
    phase_funnel()
    loa_bars("loa_by_area.csv", "Likelihood of approval by disease area", "loa_by_area", bio.AREA_LOA)
    loa_bars("loa_by_modality.csv", "Likelihood of approval by modality", "loa_by_modality", bio.MODALITY_LOA)
    if os.path.exists(os.path.join(OUT, "section2", "relative_success.csv")):
        dose_response()
        prediction()
    if os.path.exists(os.path.join(OUT, "section2", "relative_success_by_area.csv")):
        genetics_by_area()
    if os.path.exists(os.path.join(OUT, "attribution", "numbers.json")):
        efficacy_attribution()
    if os.path.exists(os.path.join(OUT, "stop_causes", "numbers.json")):
        stop_subcauses()
        registered_vs_traced()
    if os.path.exists(os.path.join(OUT, "section3", "rules.csv")):
        s3_evidence_map()
        s3_specificity()
        s3_endpoints()
        evidence_translates()
        s3_hypotheses()


if __name__ == "__main__":
    main()
