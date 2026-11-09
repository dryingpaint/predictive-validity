"""Report figures from the Section 1, Section 2, Section 3 and attribution outputs.

    python -m report.figures

Reads report/output/section*/ CSVs (no database access) and writes PNG and
SVG files to report/output/figures/.
"""
from __future__ import annotations

import json
import logging
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches
import numpy as np
import pandas as pd
from statsmodels.stats.proportion import proportion_confint

from report import bio, frame
from report.evidence_lines import area_alone
from report.render import S3_ENDPOINTS, S3_MAP_ROWS, band_label, stratum_name
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
    # The PNG is what the doc embeds; SVG and PDF are the full-resolution copies. No dates or random ids are
    # written, so a figure whose data did not change is the same file.
    stamp = {"png": {}, "svg": {"Date": None}, "pdf": {"CreationDate": None}}
    with plt.rc_context({"svg.hashsalt": name}):
        for ext in ("png", "svg", "pdf"):
            fig.savefig(os.path.join(FIG, f"{name}.{ext}"), dpi=200, bbox_inches="tight", metadata=stamp[ext])
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


RC = {"font.family": ["Avenir Next", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"], "font.size": 9,
      "hatch.color": "white", "hatch.linewidth": 1.4}


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
    with plt.rc_context(RC):
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


BROKEN_DOWN = ("efficacy", "sponsor_decision", "safety", "operational", "positive_not_advanced")
EFFICACY_PARTS = [*ATTRIBUTION_COLORS, "not_attributed"]  # why efficacy failed, from the efficacy attribution
GRAY_PARTS = ("not_stated", "no_engagement_data", "not_attributed")
LIKELY_ONLY = "cause_likely"  # a stop whose cause is the model's likely cause has no subcause
LIGHT = "#d9d7d1"


def stop_causes_by_phase():
    """Why Phase 1, 2 and 3 programs stop: each phase's stops by cause (sourced or likely), then each cause's stops by
    subcause in one panel per phase (for efficacy, what the evidence shows about target engagement), solid where the
    text or a source states the subcause and pale where the search finds it only likely. Every panel sums to its
    segment of the cause bar."""
    n = json.load(open(os.path.join(OUT, "stop_causes", "numbers.json")))
    d = pd.read_csv(os.path.join(OUT, "stop_causes", "programs.csv"))
    d = d[pd.to_datetime(d.phase_entry).dt.year.between(n["window"]["from"], n["window"]["to"]) & d.shown.notna()]
    d = d.assign(part=d.subcause.where(d.cause.eq(d.shown), LIKELY_ONLY),
                 likely=d.get("subcause_support", pd.Series(index=d.index, dtype=object)).eq("likely"))
    orders = {"efficacy": [x for x in [*EFFICACY_PARTS, LIKELY_ONLY] if d[d.shown.eq("efficacy")].part.eq(x).any()]}
    for c in BROKEN_DOWN[1:]:
        share = d[d.shown.eq(c)].part.value_counts()
        named = [x for x in BREAKDOWN[c] if x not in ("other_stated", "not_stated")]
        orders[c] = [x for x in sorted(named, key=lambda x: -share.get(x, 0)) + ["other_stated", "not_stated", LIKELY_ONLY]
                     if share.get(x, 0)]  # a subcause no stop of the cause has is left out
    names = {**SUBCAUSE_NAMES, **{k: v[1] for k, v in SUBCAUSE_LABELS.items()}, "not_attributed": "Not attributed",
             LIKELY_ONLY: "Cause likely, not sourced"}
    sizes = [len(orders[c]) for c in BROKEN_DOWN]
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    with plt.rc_context(RC):
        fig = plt.figure(figsize=(11, 3.6 + 0.25 * sum(sizes) + 0.45 * len(BROKEN_DOWN)))
        h = fig.get_figheight()
        fig.text(0.03, 0.985, "Why Phase 1, 2 and 3 programs stop", fontsize=16, fontweight="demibold", color=INK,
                 va="top")
        fig.text(0.03, 0.985 - 0.32 / h, f"Industry programs that stopped, phase entries {n['window']['from']}–"
                 f"{n['window']['to']}: the cause of each stop, and what each cause breaks down into",
                 fontsize=10, color=MUTED, va="top")
        top_h = 2.3 / h
        ax = fig.add_axes([0.16, 1 - 0.75 / h - top_h, 0.8, top_h])
        ax.set_xlim(0, 1)
        ax.set_ylim(0.5, 3.0)
        ax.axis("off")
        for k, phase in enumerate((1, 2, 3)):
            shown = d[d.phase.eq(phase)].shown
            y = 2.5 - k * 0.9
            stacked(ax, y, [(float((shown == c).mean()), col, c == "unknown") for c, col in SHOWN_COLORS.items()])
            ax.text(-0.02, y + 0.03, f"Phase {phase}", ha="right", va="bottom", fontsize=10.5, color=INK,
                    fontweight="demibold")
            ax.text(-0.02, y - 0.02, f"{len(shown):,} programs", ha="right", va="top", fontsize=7.5, color=MUTED)
        ax.legend(handles=[matplotlib.patches.Patch(facecolor=col, edgecolor="white",
                                                    hatch="////" if c == "unknown" else None, label=SHOWN[c])
                           for c, col in SHOWN_COLORS.items()],
                  frameon=False, fontsize=8.5, loc="upper left", handlelength=1.0, handleheight=1.0,
                  columnspacing=1.4, labelspacing=0.5, labelcolor=INK2, ncol=6, bbox_to_anchor=(-0.02, -0.02))
        grid = fig.add_gridspec(len(BROKEN_DOWN), 3, left=0.27, right=0.98, top=1 - 1.95 / h - top_h, bottom=0.02,
                                height_ratios=sizes, hspace=0.45, wspace=0.18)
        for i, cause in enumerate(BROKEN_DOWN):
            order = orders[cause]
            for j, phase in enumerate((1, 2, 3)):
                g = d[d.shown.eq(cause) & d.phase.eq(phase)]
                ax = fig.add_subplot(grid[i, j])
                y = np.arange(len(order))[::-1]
                for yi, x in zip(y, order):
                    part = g[g.part.eq(x)]
                    w, w_likely = len(part) / max(len(g), 1), part.likely.sum() / max(len(g), 1)
                    gray = x in (*GRAY_PARTS, LIKELY_ONLY)
                    ax.add_patch(matplotlib.patches.Rectangle((0, yi - 0.34), w - w_likely, 0.68, linewidth=0,
                                                              facecolor=LIGHT if gray else SHOWN_COLORS[cause]))
                    ax.add_patch(matplotlib.patches.Rectangle((w - w_likely, yi - 0.34), w_likely, 0.68, linewidth=0,
                                                              facecolor=SHOWN_COLORS[cause], alpha=0.35))
                    ax.text(w + 0.02, yi, f"{w:.0%}  ({len(part):,})", va="center", fontsize=8, color=INK2)
                ax.set_yticks(y, [names[x] for x in order] if j == 0 else [""] * len(order), fontsize=8.5,
                              color=INK2)
                ax.set_xlim(0, 1.25)
                ax.set_ylim(-0.6, len(order) - 0.4)
                ax.tick_params(length=0)
                ax.set_xticks([])
                for side in ax.spines.values():
                    side.set_visible(False)
                ax.set_title((f"{SHOWN[cause].upper()}\n" if j == 0 else "\n") + f"PHASE {phase} · {len(g):,} programs",
                             loc="left", fontsize=8, color=MUTED, fontweight="demibold")
        save(fig, "stop_causes_by_phase")


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


BY_AREA_LINES = {"genetic_any": "Human genetics", "animal_model": "Mouse genetics"}


def genetics_by_area():
    """Relative success of human genetics and of mouse genetics in each disease-area group, one panel each; a
    group with too few programs carrying the line to estimate shows its count instead of a dot."""
    df = pd.read_csv(os.path.join(OUT, "section2", "relative_success_by_area.csv"))
    pooled = pd.read_csv(os.path.join(OUT, "section2", "relative_success.csv")).set_index("feature")
    groups = list(df[df.feature.eq("genetic_any")].sort_values("rs", na_position="first").group_label)
    labels = [*groups, "All areas"]
    y = np.arange(len(labels))
    fig, axes = plt.subplots(1, len(BY_AREA_LINES), figsize=(10, 0.42 * len(labels) + 1.2), sharey=True,
                             gridspec_kw={"wspace": 0.08})
    for ax, (feature, title) in zip(axes, BY_AREA_LINES.items()):
        d = df[df.feature.eq(feature)].set_index("group_label").reindex(groups)
        p = pooled.loc[feature]
        rs, lo, hi = [*d.rs, p.rs], [*d.rs_lo, p.rs_lo], [*d.rs_hi, p.rs_hi]
        n = [*d.n_with.fillna(0).astype(int), int(p.n_with)]
        for yi in y:
            if pd.isna(rs[yi]):
                ax.text(0.05, yi, f"too few to estimate (n={n[yi]:,})", va="center", color=MUTED, fontsize=8)
                continue
            last = yi == len(labels) - 1
            ax.plot([np.log2(lo[yi]), np.log2(hi[yi])], [yi, yi], color=INK2, linewidth=1)
            ax.scatter(np.log2(rs[yi]), yi, s=60 if last else 28, color=INK if last else ACCENT, zorder=3,
                       edgecolors="none")
            ax.text(max(np.log2(hi[yi]), 0) + 0.08, yi, f"{rs[yi]:.2f}× (n={n[yi]:,})", va="center", color=INK2,
                    fontsize=8)
        ax.axvline(0, color=INK2, linewidth=1)
        ticks = [0.5, 1, 2, 4, 8]
        ax.set_xticks(np.log2(ticks), [f"{t:g}×" for t in ticks])
        ax.set_xlim(np.log2(0.4), np.log2(14))
        style(ax)
        ax.set_title(title, loc="left", color=INK, fontsize=10)
    axes[0].set_yticks(y, labels, color=INK, fontsize=9)
    axes[0].get_yticklabels()[-1].set_fontweight("bold")
    fig.suptitle("Relative success in reaching approval, by disease area (95% CI)", x=0.12, ha="left", color=INK,
                 fontsize=10, y=1.02)
    save(fig, "genetics_by_area")


COMMITMENT_ROWS = {  # (panel, label) -> row label, in drawing order; None leaves a gap
    ("sponsor", "reported"): "As reported", ("sponsor", "size_tier"): "+ sponsor size",
    ("sponsor", "own_baseline"): "+ each large sponsor compared with itself", None: None,
    ("tier", "top20"): "20 largest sponsors only", ("tier", "21-100"): "Sponsors ranked 21–100 only",
    ("tier", "smaller"): "Smaller sponsors only"}
READOUT_ROWS = {"advanced_overall": "Advanced", "met_readout": "Met primary endpoint",
                "advanced_if_met": "Advanced after a met endpoint", "advanced_if_not_met": "Advanced after a miss"}


def sponsor_confound():
    """The Phase 2 genetics risk ratio under sponsor adjustments and within sponsor-size tiers (A), each large
    sponsor's genetically supported against other programs (B), and the advantage split at the Phase 2 readout (C)."""
    c = pd.read_csv(os.path.join(OUT, "section3", "commitment.csv")).set_index(["panel", "label"])
    w = pd.read_csv(os.path.join(OUT, "section3", "within_sponsor.csv"))
    fig, (a, b, cc) = plt.subplots(1, 3, figsize=(16, 5.4), gridspec_kw={"width_ratios": [1, 0.9, 1], "wspace": 1.0})
    rows, ticks, labels, y = [], [], [], len(COMMITMENT_ROWS)
    for key, label in COMMITMENT_ROWS.items():
        y -= 1
        if key is None or key not in c.index or pd.isna(c.loc[key, "rr"]):
            continue
        r = c.loc[key]
        rows.append((y, r.rr, r.lo, r.hi, INK if key[0] == "sponsor" and key[1] == "reported" else
                     ACCENT if key[0] == "sponsor" else INK2, True))
        ticks.append(y)
        labels.append(f"{label} (n={int(r.n):,})")
    forest(a, rows, lim=(0.5, 4))
    a.set_yticks(ticks, labels, color=INK, fontsize=8)
    a.set_xlabel("Risk ratio of advancing from Phase 2 within 4 years,\ngenetics for the disease vs none", color=INK2,
                 fontsize=8)
    a.set_title("A  Sponsor size", loc="left", color=INK, fontsize=10)
    w = w.assign(gap=w.s4_with - w.s4_without).sort_values("gap").reset_index(drop=True)
    for i, r in w.iterrows():
        b.plot([100 * r.s4_without, 100 * r.s4_with], [i, i], color=ACCENT if r.gap > 0 else MUTED, linewidth=1.5,
               alpha=0.6)
        b.scatter(100 * r.s4_without, i, s=10 + (r.programs - r["with"]), color=BAR, edgecolor="white", zorder=3)
        b.scatter(100 * r.s4_with, i, s=10 + 5 * r["with"], color=ACCENT, edgecolor="white", zorder=4)
    b.set_yticks([])
    b.set_xlim(-2, 102)
    b.set_xlabel("Phase 2 programs that advanced within 4 years (%)", color=INK2, fontsize=8)
    style(b)
    b.set_title(f"B  Within each large sponsor: higher at {int((w.gap > 0).sum())} of {len(w)}", loc="left",
                color=INK, fontsize=10)
    b.scatter([], [], s=40, color=ACCENT, label="Genetic evidence for the disease")
    b.scatter([], [], s=40, color=BAR, label="The sponsor's other programs")
    b.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    rows, ticks, labels = [], [], []
    for i, (key, label) in enumerate(READOUT_ROWS.items()):
        if ("readout", key) not in c.index or pd.isna(c.loc[("readout", key), "rr"]):
            continue
        r, yy = c.loc[("readout", key)], len(READOUT_ROWS) - 1 - i
        rows.append((yy, r.rr, r.lo, r.hi, INK if key == "advanced_overall" else ACCENT, True))
        ticks.append(yy)
        labels.append(f"{label} (n={int(r.n):,})")
    forest(cc, rows, lim=(0.5, 4))
    cc.set_yticks(ticks, labels, color=INK, fontsize=8)
    cc.set_xlabel("Risk ratio, genetics for the disease vs none", color=INK2, fontsize=8)
    cc.set_title("C  At the first Phase 2 efficacy readout", loc="left", color=INK, fontsize=10)
    save(fig, "sponsor_confound")


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


# Evidence categories of the plan amendment (report.evidence_lines.CATEGORIES), in its order: efficacy
# evidence by the system that produced it, then safety risk and the clinical-precedent benchmark apart.
CATEGORY_COLORS = {"human_genetics": "#2a78d6", "tumour_genetics": "#eb6834", "diseased_tissue": "#eda100",
                   "pathway": "#7fb0e8",
                   "animal": "#1baf7a", "published_animal": "#76c9a3", "cell": "#8a8984", "molecule": "#b04a8f",
                   "early_human": "#0f8f9a",
                   "safety_risk": "#6b6a65", "precedent": "#4a3aa7"}
# Section 3 evidence-map rows by the category whose colour they take
S3_GROUP = {"g3": "human_genetics", "gwas": "human_genetics", "gwas_strong": "human_genetics",
            "gwas_mid": "human_genetics", "gwas_weak": "human_genetics", "mendelian": "human_genetics",
            "mendelian_strong": "human_genetics", "somatic": "tumour_genetics", "somatic_concordant": "tumour_genetics",
            "mgi": "animal", "mgi_strong": "animal", "expression": "diseased_tissue", "reactome": "human_genetics",
            "b1": "precedent", "precedent": "precedent", "pan_essential": "safety_risk", "constrained": "safety_risk",
            "ko_lethal": "safety_risk"}
MIN_G3_TRIALS = 10  # endpoint classes with fewer genetically supported trials are left out of the figure


def s3_evidence_map():
    df = pd.read_csv(os.path.join(OUT, "section3", "evidence_map.csv"))
    df = df[df.scope == "C2"].set_index("feature")
    rows = [f for f in S3_MAP_ROWS if pd.notna(df.at[f, "rr"])]
    fig, ax = plt.subplots(figsize=(9.5, 0.36 * len(rows) + 1.2))
    for i, f in enumerate(rows):
        y = len(rows) - 1 - i
        r = df.loc[f]
        color = CATEGORY_COLORS[S3_GROUP[f]]
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
    """Share of Phase 2 programs advancing within four years by where the target's germline genetic evidence lay,
    outside and inside oncology, with 95% Wilson intervals."""
    n = json.load(open(os.path.join(OUT, "section3", "numbers.json")))
    names = {"g0": "None (G0)", "g1": "Unrelated diseases only (G1)", "g2": "Related disease only (G2)",
             "g3": "The program's disease (G3)"}
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4), sharex=True, gridspec_kw={"wspace": 0.08})
    for ax, lv, title in zip(axes, (n["h1"], n["levels_onc"]), ("Non-oncology", "Oncology")):
        rows = [(k, lv[k]["ppv"], lv[k]["n"], lv[k].get("rr")) for k in ("g0", "g1", "g2", "g3")]
        y = np.arange(len(rows))[::-1]
        lo, hi = np.array([proportion_confint(round(v * m), m, method="wilson") for _, v, m, _ in rows]).T
        ax.barh(y, [100 * v for _, v, _, _ in rows], height=0.6, color=[BAR, BAR, BAR, ACCENT])
        ax.errorbar([100 * v for _, v, _, _ in rows], y, xerr=[100 * (np.array([v for _, v, _, _ in rows]) - lo),
                                                              100 * (hi - np.array([v for _, v, _, _ in rows]))],
                    fmt="none", ecolor=INK2, elinewidth=1.2, capsize=0)
        for yi, (k, v, m, rr), h in zip(y, rows, hi):
            ax.text(100 * h + 1, yi, f"{v:.0%}" + ("" if rr is None else f"  ({rr:.2f}× G0)"), va="center",
                    color=INK2, fontsize=10)
        ax.set_yticks(y, [f"{names[k]}, {m:,}" for k, _, m, _ in rows], color=INK, fontsize=10.5)
        ax.set_title(title, loc="left", color=INK, fontsize=11.5)
        ax.set_xlim(0, 60)
        ax.tick_params(axis="x", labelsize=10)
        style(ax)
    axes[1].set_yticklabels([])
    axes[1].tick_params(axis="y", length=0)
    fig.suptitle("Phase 2 programs advancing within 4 years, by where the target's germline genetic evidence lay "
                 "before entry (%, 95% interval; label: programs)", x=0.01, y=1.04, ha="left", color=INK2, fontsize=10.5)
    save(fig, "s3_specificity")


BLOCK_HEADERS = {"precedent": "For comparison: whether earlier drugs on the same target had already succeeded"}
LABEL_PAD = 300  # points between the evidence labels, left-aligned, and the first panel


def label_pad(fig, ax) -> float:
    """Points between left-aligned y labels and the plot: LABEL_PAD, or the widest label plus a margin when a label
    would otherwise run into the plot."""
    renderer = fig.canvas.get_renderer()
    widest = max((t.get_window_extent(renderer).width for t in ax.get_yticklabels()), default=0) * 72 / fig.dpi
    return max(LABEL_PAD, widest + 12)


def evidence_translates():
    """Relative success to approval from any phase for each evidence area (report.evidence_lines.AREAS) and its
    mutually exclusive tiers, on US-developed programs; a filled dot is a 95% interval clear of 1. Only lines with an
    estimate are drawn; the registered categories, with every line tried, are in the appendix table. An interval
    that runs past the axis ends in an arrowhead at its edge."""
    lines = pd.read_csv(os.path.join(OUT, "evidence_analysis", "areas.csv"))
    lines = lines[lines.category.isin(CATEGORY_COLORS) & lines.estimated.eq(True)]
    ys, y, prev = [], 0.0, None
    for i, r in enumerate(lines.itertuples()):
        if i:
            y -= 2.6 if r.category in BLOCK_HEADERS and r.category != prev else 1.5 if r.level == "area" else 1
        prev = r.category
        ys.append(y)
    fig, ax = plt.subplots(figsize=(10, 0.4 * len(ys) + 2.6))
    lim = (np.log2(0.2), np.log2(5))
    for yi, r in zip(ys, lines.itertuples()):
        color = CATEGORY_COLORS[r.category]
        ax.plot([np.log2(max(r.rs_rs_lo, 0.2)), np.log2(min(r.rs_rs_hi, 5))], [yi, yi], color=color, linewidth=2,
                solid_capstyle="round")
        for end, beyond, mark in ((lim[0], r.rs_rs_lo < 0.2, "<"), (lim[1], r.rs_rs_hi > 5, ">")):
            if beyond:  # the interval runs past the axis: an arrowhead at the edge says so
                ax.plot(end, yi, mark, markersize=7, color=color, clip_on=False)
        clear = r.rs_rs_lo > 1 or r.rs_rs_hi < 1
        ax.plot(np.log2(r.rs_rs), yi, "o", markersize=7, color=color, markeredgewidth=1.5,
                markerfacecolor=color if clear else "white", markeredgecolor=color)
        ax.text(np.log2(5) + 0.1, yi, f"{r.rs_rs:.2f}×", va="center", color=INK2, fontsize=10)
        ax.text(np.log2(5) + 0.85, yi, f"n={r.exposed:,.0f}", va="center", color=INK2, fontsize=10)
    ticks = [0.25, 0.5, 1, 2, 4]
    ax.axvline(0, color=INK2, linewidth=1)
    ax.set_xticks(np.log2(ticks), [f"{t:g}×" for t in ticks])
    ax.tick_params(axis="x", labelsize=10)
    ax.set_xlim(*lim)
    ax.set_xlabel("How often programs with the evidence reached approval, relative to those without (95% range)",
                  color=INK2, fontsize=10)
    style(ax)
    alone = area_alone()
    labels = [("      " if r.level != "area" else "") + r.label
              + (" †" if r.column in alone else "") for r in lines.itertuples()]
    ax.set_yticks(ys, labels, color=INK, fontsize=10.5)
    for t, r in zip(ax.get_yticklabels(), lines.itertuples()):
        t.set_horizontalalignment("left")
        t.set_color(INK if r.level == "area" else INK2)
        t.set_fontweight("bold" if r.level == "area" else "normal")
    pad = label_pad(fig, ax)
    ax.tick_params(axis="y", pad=pad)
    label_x = -pad / 72 / (fig.get_figwidth() * ax.get_position().width)  # the labels' left edge, in axes
    for cat, header in BLOCK_HEADERS.items():
        first = next(yi for yi, r in zip(ys, lines.itertuples()) if r.category == cat)
        ax.text(label_x, first + 1.1, header, transform=ax.get_yaxis_transform(), color=INK2, fontsize=10,
                style="italic")
    top = ys[0] + 0.7
    ax.set_ylim(ys[-1] - 0.7, top + 0.4)
    save(fig, "evidence_translates")


# The evidence grid's rows (report.evidence_analysis.stop_risk columns), in order: evidence about the target, about the
# drug, then the safety lines below a rule.
GRID_ROWS = {"g3": "Human genetics", "somatic": "Tumour genetics", "altered_animal": "Mouse genetics shows the disease",
             "expression": "RNA change in diseased tissue", "cat_precedent": "Earlier drugs on the same target",
             "area_measured": "Drug binding measured", "area_lit_animal": "Published animal studies of the drug",
             "lit_human_engagement": "Drug shown to engage its target in people",
             "liability": "Standard genetic safety flags", "ko_vital_organ": "Mutant mice: vital-organ phenotype",
             "earlier_safety_stop": "Earlier drug on the target stopped for safety",
             "poor_selectivity": "Drug binds another protein within 10-fold"}
# The model-system atlas's four questions, as stop outcomes (report.evidence_analysis.stop_outcomes)
GRID_COLUMNS = [("stop_engagement", "Engagement"), ("stop_dose", "Dose or exposure"), ("stop_no_benefit", "Efficacy"),
                ("stop_safety", "Safety")]
FEWER, MORE, NEUTRAL = ACCENT, "#eb6834", "#f4f3ef"
# Cells whose evidence is what the stop's label was read from: published human engagement is the evidence the
# efficacy attribution judges engagement on, so it cannot be tested against engagement stops.
CIRCULAR = {("lit_human_engagement", "stop_engagement")}


def evidence_grid():
    """Which evidence goes with fewer or more stops on each of the atlas's four questions: a cell is coloured when the
    adjusted risk ratio's 95% interval clears 1 (report.evidence_analysis.stop_risk) and says by how much, and how many
    stops among the programs with the evidence it rests on."""
    df = pd.read_csv(os.path.join(OUT, "evidence_analysis", "stop_risk.csv"))
    df = df[df.estimated.eq(True)].set_index("column")
    rows = [c for c in GRID_ROWS if c in df.index]
    targetdrug = sum(1 for c in rows if df.at[c, "group"] == "area")
    fig, ax = plt.subplots(figsize=(8.2, 0.48 * len(rows) + 1.0))
    for i, c in enumerate(rows):
        for j, (outcome, _) in enumerate(GRID_COLUMNS):
            rr, lo, hi = (df.at[c, f"{outcome}_{k}"] for k in ("rr", "lo", "hi"))
            if (c, outcome) in CIRCULAR:
                color, text, ink = NEUTRAL, "not testable", MUTED
            elif pd.isna(rr):
                color, text, ink = NEUTRAL, "too few stops", MUTED
            elif hi < 1 or lo > 1:
                stops = round(df.at[c, "exposed"] * df.at[c, f"{outcome}_ppv"])
                change = f"{1 - rr:.0%} fewer" if hi < 1 else f"{rr - 1:.0%} more"
                color, text, ink = FEWER if hi < 1 else MORE, f"{change}\n{stops:,} stops", "white"
            else:
                color, text, ink = NEUTRAL, "no clear effect", MUTED
            ax.add_patch(matplotlib.patches.Rectangle((j, i), 0.96, 0.9, color=color, linewidth=0))
            ax.text(j + 0.48, i + 0.45, text, ha="center", va="center", fontsize=9, color=ink,
                    fontweight="bold" if ink == "white" else "normal")
    ax.axhline(targetdrug - 0.05, color=INK2, linewidth=0.8)
    ax.set_xlim(0, len(GRID_COLUMNS))
    ax.set_ylim(len(rows), -0.1)
    ax.set_xticks([j + 0.48 for j in range(len(GRID_COLUMNS))], [t for _, t in GRID_COLUMNS], fontsize=10.5,
                  color=INK, fontweight="bold")
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    ax.set_yticks([i + 0.45 for i in range(len(rows))], [GRID_ROWS[c] for c in rows], fontsize=10, color=INK)
    for side in ax.spines.values():
        side.set_visible(False)
    save(fig, "evidence_grid")


# The stop drill-down's segments: (key, label, colour, hatched); the first segment of each bar is the next bar's whole.
# Blue is the part carried down (and, in the last bar, the stops whose target worked somewhere); grey shades are the
# other known answers, darkest first; a pale hatched segment is a stop whose answer is not known.
DRILL_GREYS = ("#5f5e5a", "#8f8e88", "#b6b5ae", "#d4d3cd")
DRILL_PALE = "#ecebe6"
DRILL = [
    ("shown", "All Phase 2–3 stops", [
        ("efficacy", "Efficacy", ACCENT, False), ("sponsor_decision", "Sponsor decision", DRILL_GREYS[0], False),
        ("positive_not_advanced", "Positive result, not taken forward", DRILL_GREYS[1], False),
        ("operational", "Operational", DRILL_GREYS[2], False), ("safety", "Safety", DRILL_GREYS[3], False),
        ("unknown", "Unknown", DRILL_PALE, True)]),
    ("efficacy", "Stopped for efficacy", [
        ("engaged_no_benefit", "Engaged the target, no benefit", ACCENT, False),
        ("not_engaged", "Never engaged", DRILL_GREYS[0], False),
        ("trial_design", "Trial couldn't answer", DRILL_GREYS[2], False),
        ("no_engagement_data", "Engagement never measured", DRILL_PALE, True),
        ("not_examined", "Not examined", DRILL_GREYS[3], False)]),
    ("engaged", "Engaged the target, no benefit", [
        ("worked_elsewhere_only", "Target works, but only in other diseases", ACCENT, False),
        ("worked_here", "Another drug on the target already worked here", "#7fb0e8", False),
        ("worked_related", "Works in a related subtype or stage", "#c6dbf4", False),
        ("never_worked_tried_again", "Never worked; tried again", DRILL_GREYS[0], False),
        ("never_worked_single", "Never worked; only attempt", DRILL_GREYS[2], False),
        ("no_target", "No target", DRILL_GREYS[3], False)]),
]


def fit_label(ax, renderer, text: str, width_px: float, max_lines: int = 3, **kw) -> str | None:
    """The label wrapped onto at most max_lines lines that fit in width_px, or None when no wrapping fits."""
    for chars in range(len(text), 3, -1):
        wrapped = textwrap.fill(text, chars, break_long_words=False)
        if wrapped.count("\n") >= max_lines:
            break
        probe = ax.text(0, 0, wrapped, **kw)
        fits = probe.get_window_extent(renderer).width <= width_px
        probe.remove()
        if fits:
            return wrapped
    return None


def why_stop():
    """Phase 2–3 stops among 2008–2019 entries broken down three times (report.stop_causes.drilldown): by cause, the
    efficacy stops by what the evidence shows about engagement, and the engaged-without-benefit stops by what other
    drugs on the target did. A segment too narrow for its label is named in a lane under its bar, which the funnel to
    the next bar leaves clear."""
    n = json.load(open(os.path.join(OUT, "stop_causes", "numbers.json")))["drilldown"]
    fig, ax = plt.subplots(figsize=(12, 6.2))
    height, lane, gap, pad = 0.8, 0.42, 1.95, 0.008
    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(-(len(DRILL) - 1) * gap - height / 2 - lane, height / 2 + 0.45)
    ax.axis("off")
    renderer = fig.canvas.get_renderer()
    px = ax.get_window_extent(renderer).width / (ax.get_xlim()[1] - ax.get_xlim()[0])
    for i, (key, title, segments) in enumerate(DRILL):
        part = n[key]
        total = n["stops"] if key == "shown" else n[key]["stops"]
        y, x, outside = -i * gap, 0.0, []
        ax.text(0, y + height / 2 + 0.08, f"{title}  ({total:,})", color=INK, fontsize=11, fontweight="bold",
                va="bottom")
        for j, (k, label, color, hatched) in enumerate(segments):
            w = part[k]["n"] / total
            ax.barh(y, w - 0.003, left=x, height=height, color=color, hatch="////" if hatched else None,
                    edgecolor="white" if hatched else color, linewidth=0)
            ink = "white" if dark(color) else INK
            room = (w - 2 * pad - 0.003) * px
            wrapped = fit_label(ax, renderer, label, room, fontsize=8, linespacing=1.05)
            share = ax.text(0, 0, f"{w:.0%}", fontsize=12, fontweight="bold")
            if wrapped and share.get_window_extent(renderer).width <= room:
                box = dict(boxstyle="square,pad=0.15", fc=color, ec="none") if hatched else None
                ax.text(x + pad, y + 0.17, f"{w:.0%}", color=ink, fontsize=12, fontweight="bold", va="center", bbox=box)
                ax.text(x + pad, y - 0.02, wrapped, color=ink, fontsize=8, va="top", linespacing=1.05, bbox=box)
            else:
                outside.append((x + w / 2, f"{label} {w:.0%}"))
            share.remove()
            if j == 0:
                drilled = w
            x += w
        # Lane labels sit under their segments, nudged right where they would overlap, then back left to end in the bar.
        widths = []
        for _, text in outside:
            t = ax.text(0, 0, text, fontsize=8)
            widths.append(t.get_window_extent(renderer).width / px)
            t.remove()
        lefts, right = [], 0.0
        for (centre, _), width in zip(outside, widths):
            lefts.append(max(centre - width / 2, right + 0.012))
            right = lefts[-1] + width
        limit = 1.0
        for m in reversed(range(len(outside))):
            lefts[m] = min(lefts[m], limit - widths[m])
            limit = lefts[m] - 0.012
        for (centre, text), left in zip(outside, lefts):
            ax.plot([centre, centre], [y - height / 2, y - height / 2 - 0.1], color=MUTED, linewidth=0.8)
            ax.text(left, y - height / 2 - 0.13, text, color=INK2, fontsize=8, va="top")
        if i < len(DRILL) - 1:
            bottom, top = y - height / 2, -(i + 1) * gap + height / 2 + 0.45
            drop = bottom - lane if outside else bottom
            ax.add_patch(matplotlib.patches.Polygon([(0, bottom), (drilled, bottom), (drilled, drop), (1, top), (0, top)],
                                                    closed=True, color=ACCENT, alpha=0.08, linewidth=0))
    save(fig, "why_stop")


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
    ("H6", "Safety risk of the target raises safety failure, outside oncology", ("h6", "safety"), "rr"),
    ("H7", "Oncology: mutation in the cancer matching the drug", ("h7",), "rr"),
]
MEASURES = {"H1": "risk ratio", "H2": "odds ratio", "H3": "risk ratio", "H4": "ratio of risk ratios",
            "H5": "ratio of risk ratios", "H6": "risk ratio", "H7": "risk ratio"}


def s3_hypotheses():
    """The seven registered hypotheses and, as a second family Holm-corrected on its own, N1-N3 of the
    plan amendment (US-developed programs); N2's two claims are drawn as two rows sharing its Holm p."""
    n = json.load(open(os.path.join(OUT, "section3", "numbers.json")))
    rows, labels, measures = [], [], []
    for i, (h, label, path, field) in enumerate(HYPOTHESES):
        r = n
        for k in path:
            r = r[k]
        holm_p = n["holm"].get(h, 1)
        rows.append((-i, r[field], r["lo"], r["hi"], ACCENT if holm_p < 0.05 else BAR, holm_p < 0.05))
        labels.append(f"{h}  {label}")
        measures.append(MEASURES[h])
    amendment = os.path.join(OUT, "evidence_analysis", "numbers.json")
    first_n = None
    if os.path.exists(amendment):
        a = json.load(open(amendment))
        y = rows[-1][0] - 1.8
        first_n = y
        for h, label, r in amendment_hypotheses(a):
            if r.get("rr") is None:
                continue
            ok = a["holm"].get(h, 1) < 0.05
            rows.append((y, r["rr"], r["lo"], r["hi"], ACCENT if ok else BAR, ok))
            labels.append(f"{h}  {label}")
            measures.append("risk ratio")
            y -= 1
    fig, ax = plt.subplots(figsize=(9, 0.4 * len(rows) + 1.6))
    forest(ax, rows, lim=(0.25, 8))
    ax.set_xticks(np.log2([0.25, 0.5, 1, 2, 4, 8]), ["0.25×", "0.5×", "1×", "2×", "4×", "8×"])
    for (y, *_), m in zip(rows, measures):
        ax.text(np.log2(8) + 0.15, y, m, va="center", color=INK2, fontsize=8)
    ax.set_yticks([r[0] for r in rows], labels, color=INK, fontsize=8.5)
    if first_n is not None:
        ax.text(np.log2(0.25), first_n + 0.75, "Added by the plan amendment before outcomes were seen: "
                "US-developed programs, Holm-corrected across the three", color=INK2, fontsize=8, style="italic")
    ax.set_xlabel("Estimate (95% CI); blue: supported after Holm correction within its family", color=INK2,
                  fontsize=8)
    ax.set_title("The pre-registered hypotheses", loc="left", color=INK, fontsize=10)
    save(fig, "s3_hypotheses")


def amendment_hypotheses(a: dict) -> list[tuple[str, str, dict]]:
    return [("N1", "Small molecules: at least 10-fold selective", a["N1"]),
            ("N2", "Small molecules: drug-like (at most one Rule-of-5 violation)", a["N2"]["drug_like"]),
            ("N2", "Neurology and psychiatry: brain-penetrant properties", a["N2"]["brain_penetrant"]),
            ("N3", "Outside oncology: potent (100 nM), genetics and drug-likeness held fixed", a["N3"])]


def main():
    history()
    loa_bars("loa_by_area.csv", "Likelihood of approval by disease area", "loa_by_area", bio.AREA_LOA)
    loa_bars("loa_by_modality.csv", "Likelihood of approval by modality", "loa_by_modality", bio.MODALITY_LOA)
    if os.path.exists(os.path.join(OUT, "section2", "relative_success.csv")):
        dose_response()
        prediction()
    if os.path.exists(os.path.join(OUT, "section3", "commitment.csv")):
        sponsor_confound()
    if os.path.exists(os.path.join(OUT, "section2", "relative_success_by_area.csv")):
        genetics_by_area()
    if os.path.exists(os.path.join(OUT, "stop_causes", "numbers.json")):
        why_stop()
        stop_causes_by_phase()
        registered_vs_traced()
    if os.path.exists(os.path.join(OUT, "section3", "rules.csv")):
        s3_evidence_map()
        s3_specificity()
        s3_endpoints()
        s3_hypotheses()
    if os.path.exists(os.path.join(OUT, "evidence_analysis", "lines.csv")):
        evidence_translates()
    if os.path.exists(os.path.join(OUT, "evidence_analysis", "stop_risk.csv")):
        evidence_grid()


if __name__ == "__main__":
    main()
