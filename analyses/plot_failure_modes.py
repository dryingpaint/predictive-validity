#!/usr/bin/env python3
"""
Section 1 figure — where drug programs fail, and why.

Composite (three panels stacked) built from cached CSVs in `data/`:

  A) Attrition through the pipeline (`failure_attrition.csv`) — how many Ph1
     entrants make it to Ph2 / Ph3 / approval. Sets the scale for panels B–C.
  B) Overall failure reasons (`failure_holistic.csv`) — ranked bar over all
     69k Ph1+ programs that did not reach approval.
  C) Failure reasons by phase (`failure_holistic_by_phase.csv`) — the same
     buckets, split by which phase the program stalled at. Composition shifts
     from mostly-ambiguous at Ph1 to mostly-efficacy at Ph3.

Companion charts (also produced):
  * `failure_modes_terminations.png` — trial-level, terminations only (Stephen's original)
  * `failure_modes_stratified.png`   — holistic by therapeutic area + modality

Refresh the CSVs with `refresh_failure_data.py`. This script reads only the CSVs.
"""
from __future__ import annotations
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Patch
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
os.makedirs(DATA, exist_ok=True)

INK, SEC, MUTED = "#14110f", "#5b544e", "#938b82"
SURFACE, RULE = "#fbfaf8", "#d8d3cb"
BIOLOGY, BUSINESS, AMBIG = "#1f6fd0", "#e2673a", "#c7c0b6"
APPROVED = "#2f8f5b"

FAMILY = {"biology": BIOLOGY, "business": BUSINESS, "ambiguous": AMBIG}
FAMILY_LABEL = {"biology": "Biology (efficacy / safety / PK)",
                "business": "Business & operational",
                "ambiguous": "Other / undisclosed"}

# Trial-level (Stephen's original chart)
TRIAL_CATS = {
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

# Program-level holistic buckets. Family assignment reflects inference strength:
#   biology         = explicit efficacy/safety/PK, or Ph3 completed → no approval (Ph3 outcomes
#                     are efficacy-gated ~90% of the time in industry practice).
#   biology (soft)  = Ph2 stalls — efficacy-gated but weaker than Ph3 signal. Hatched.
#   ambiguous       = Ph1 stalls (Ph1 measures safety/PK, most stalls are pipeline decisions),
#                     plus planned / unclassified / covid / unknown.
#   business        = commercial / enrollment / regulatory / competitive / manufacturing.
PROG_CATS = {
    "phase1_stall":             ("Phase 1 stall (Ph1 complete, program halted)", "ambiguous"),
    "ph2_stall":                ("Phase 2 stall (Ph2 complete, program halted)", "biology"),
    "silent_efficacy_ph3":      ("Silent efficacy fail (Ph3 complete, no approval)", "biology"),
    "efficacy":                 ("Efficacy (explicit termination)", "biology"),
    "safety":                   ("Safety / toxicity", "biology"),
    "pk_pd":                    ("PK / PD / formulation", "biology"),
    "commercial_strategic":     ("Commercial / strategic", "business"),
    "enrollment_operational":   ("Enrollment / operational", "business"),
    "regulatory_admin":         ("Regulatory / administrative", "business"),
    "competitive_landscape":    ("Competitive landscape", "business"),
    "manufacturing_supply":     ("Manufacturing / supply", "business"),
    "covid":                    ("COVID-19 disruption", "ambiguous"),
    "planned":                  ("Planned (per protocol)", "ambiguous"),
    "unclassified_termination": ("Unclassified termination", "ambiguous"),
    "unknown":                  ("Unknown", "ambiguous"),
}
BIOLOGY_SOFT = {"ph2_stall", "phase1_stall"}   # hatched, weaker inference


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


def _pct_label(pct: float) -> str:
    return f"{pct:.0f}%" if pct >= 1 else f"{pct:.1f}%"


# ─── Panel A: attrition through the pipeline ───────────────────────────────
def panel_attrition(ax):
    df = pd.read_csv(os.path.join(DATA, "failure_attrition.csv"))
    order = ["ph1_entrants", "ph2_entrants", "ph3_entrants", "approved"]
    labels = ["Reached Phase 1", "Reached Phase 2", "Reached Phase 3", "Approved"]
    ns = [int(df[df.phase == k].n.iloc[0]) for k in order]
    base = ns[0]
    pcts = [n / base * 100 for n in ns]
    colors = [BIOLOGY, BIOLOGY, BIOLOGY, APPROVED]

    y = list(range(len(order)))
    ax.barh(y, pcts, height=0.55, color=colors, zorder=3, edgecolor=SURFACE, linewidth=0.5)
    for yi, (n, p) in enumerate(zip(ns, pcts)):
        ax.text(p + 1.5, yi, f"{n:,}   ({p:.0f}% of Ph1 entrants)",
                va="center", ha="left", fontsize=10, color=INK, fontweight="bold")
    trans = [
        (0, 1, f"{ns[1]/ns[0]*100:.0f}% advance to Ph2"),
        (1, 2, f"{ns[2]/ns[1]*100:.0f}% advance to Ph3"),
        (2, 3, f"{ns[3]/ns[2]*100:.0f}% of Ph3 entrants approved"),
    ]
    for i, j, txt in trans:
        ax.annotate(txt, xy=(pcts[j] + 0.2, j - 0.32), xytext=(pcts[i] + 0.2, i + 0.32),
                    fontsize=8.5, color=SEC, style="italic",
                    arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.8))
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=10.5, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 145); ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title("A. Where programs stop  |  attrition through the pipeline",
                 fontsize=11.5, color=INK, fontweight="bold", loc="left", pad=8)


# ─── Panel B: overall failure reasons (ranked bar) ─────────────────────────
def panel_holistic(ax):
    df = pd.read_csv(os.path.join(DATA, "failure_holistic.csv"))
    df = df[df.bucket.isin(PROG_CATS)].copy()
    df["disp"] = df.bucket.map(lambda c: PROG_CATS[c][0])
    df["fam"] = df.bucket.map(lambda c: PROG_CATS[c][1])
    df = df.sort_values("pct_of_failed_programs")
    y = range(len(df))
    colors = [FAMILY[f] for f in df["fam"]]
    hatches = ["///" if b in BIOLOGY_SOFT else "" for b in df["bucket"]]
    bars = ax.barh(list(y), df.pct_of_failed_programs, height=0.66, color=colors, zorder=3,
                   edgecolor=SURFACE, linewidth=0.5)
    for bar, h in zip(bars, hatches):
        if h:
            bar.set_hatch(h); bar.set_edgecolor(SURFACE)
    for yi, pct in enumerate(df.pct_of_failed_programs):
        ax.text(pct + 0.6, yi, _pct_label(pct),
                va="center", ha="left", fontsize=10, fontweight="bold", color=INK)
    ax.set_yticks(list(y))
    ax.set_yticklabels(df.disp, fontsize=10, color=INK)
    ax.set_xticks([]); ax.set_xlim(0, 45)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0); ax.margins(y=0.02)
    fam_share = df.groupby("fam").pct_of_failed_programs.sum().to_dict()
    handles = [Patch(facecolor=FAMILY[f], label=f"{FAMILY_LABEL[f]}  ·  {fam_share.get(f, 0):.0f}%")
               for f in ("biology", "business", "ambiguous")]
    leg = ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=9.5,
                    handlelength=1.0, handleheight=1.0, borderpad=0, labelspacing=0.5)
    for t in leg.get_texts():
        t.set_color(SEC)
    total = int(df.n_programs.sum())
    ax.set_title(f"B. Why they stop  |  overall failure reasons  (n={total:,} programs)",
                 fontsize=11.5, color=INK, fontweight="bold", loc="left", pad=8)
    ax.text(1.0, -0.03, "hatched bars = weaker inference (program stalled, no explicit reason)",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.5, color=MUTED, style="italic")


# ─── Panel C: failure reasons by phase failed at ───────────────────────────
def panel_by_phase(ax):
    df = pd.read_csv(os.path.join(DATA, "failure_holistic_by_phase.csv"))
    df = df[df.bucket.isin(PROG_CATS) & df.highest_phase.isin([1, 2, 3])].copy()
    pivot = df.pivot_table(index="highest_phase", columns="bucket", values="n_programs",
                            aggfunc="sum", fill_value=0)
    row_totals = pivot.sum(axis=1)
    pivot_pct = pivot.div(row_totals, axis=0) * 100

    overall = pivot.sum(axis=0).sort_values(ascending=False)
    fam_order = {"biology": 0, "business": 1, "ambiguous": 2}
    buckets_ordered = sorted(overall.index,
                             key=lambda b: (fam_order[PROG_CATS[b][1]], -overall[b]))

    phases = [1, 2, 3]
    ph_labels = [f"Failed at Ph{p}   n={int(row_totals[p]):>6,}" for p in phases]
    y = list(range(len(phases)))
    left = [0.0] * len(phases)
    for b in buckets_ordered:
        vals = [pivot_pct.loc[p, b] if b in pivot_pct.columns else 0 for p in phases]
        color = FAMILY[PROG_CATS[b][1]]
        hatch = "///" if b in BIOLOGY_SOFT else ""
        ax.barh(y, vals, left=left, color=color, height=0.68, zorder=3,
                edgecolor=SURFACE, linewidth=0.5, hatch=hatch)
        for i, (v, l) in enumerate(zip(vals, left)):
            if v >= 5:
                txt_color = "white" if PROG_CATS[b][1] != "ambiguous" else INK
                ax.text(l + v / 2, i, f"{v:.0f}%", ha="center", va="center",
                        fontsize=9, fontweight="bold", color=txt_color)
        left = [l + v for l, v in zip(left, vals)]
    ax.set_yticks(y)
    ax.set_yticklabels(ph_labels, fontsize=10.5, color=INK, family="monospace")
    ax.invert_yaxis()
    ax.set_xlim(0, 100); ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title("C. Why they stop, by phase  |  reasons for programs that failed at each stage",
                 fontsize=11.5, color=INK, fontweight="bold", loc="left", pad=8)
    ax.text(1.0, -0.12,
            "As programs advance the ambiguous 'stall' bucket shrinks and biology gets more direct: "
            "79% of Ph3 fails are Ph3-completed-no-approval.",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.5, color=MUTED, style="italic")


# ─── Main composite ────────────────────────────────────────────────────────
def fig_main():
    fig = plt.figure(figsize=(11.5, 15.4))
    gs = fig.add_gridspec(3, 1, height_ratios=[0.9, 2.6, 1.2], hspace=0.55,
                          left=0.24, right=0.965, top=0.955, bottom=0.045)
    axA = fig.add_subplot(gs[0])
    axB = fig.add_subplot(gs[1])
    axC = fig.add_subplot(gs[2])
    panel_attrition(axA)
    panel_holistic(axB)
    panel_by_phase(axC)
    stem = "failure_modes_main"
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=600)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png + .svg")


# ─── Companion: trial-level terminations (Stephen's original) ──────────────
def fig_terminations():
    df = pd.read_csv(os.path.join(DATA, "failure_taxonomy.csv"))
    df = df[df.category.isin(TRIAL_CATS)].copy()
    df["disp"] = df.category.map(lambda c: TRIAL_CATS[c][0])
    df["fam"] = df.category.map(lambda c: TRIAL_CATS[c][1])
    df = df.sort_values("pct_of_all_classified")
    y = range(len(df))
    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    fig.subplots_adjust(left=0.30, right=0.93, top=0.965, bottom=0.06)
    ax.barh(list(y), df.pct_of_all_classified, height=0.62,
            color=[FAMILY[f] for f in df["fam"]], zorder=3)
    for yi, pct in enumerate(df.pct_of_all_classified):
        ax.text(pct + 0.7, yi, _pct_label(pct),
                va="center", ha="left", fontsize=10.5, fontweight="bold", color=INK)
    ax.set_yticks(list(y)); ax.set_yticklabels(df.disp, fontsize=11, color=INK)
    ax.set_xticks([]); ax.set_xlim(0, 50)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0); ax.margins(y=0.02)
    fam_share = df.groupby("fam").pct_of_all_classified.sum().to_dict()
    handles = [Patch(facecolor=FAMILY[f], label=f"{FAMILY_LABEL[f]}  ·  {fam_share.get(f, 0):.0f}%")
               for f in ("biology", "business", "ambiguous")]
    leg = ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=9.5,
                    handlelength=1.0, handleheight=1.0, borderpad=0, labelspacing=0.6)
    for t in leg.get_texts():
        t.set_color(SEC)
    stem = "failure_modes_terminations"
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=600)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png + .svg")


# ─── Companion: stratified by therapeutic area + modality ──────────────────
TA_ORDER = ["oncology", "neuro", "cv", "metabolic", "autoimmune", "infectious", "rare", "other"]
TA_LABEL = {"oncology": "Oncology", "neuro": "Neurology / psych",
            "cv": "Cardiovascular", "metabolic": "Metabolic",
            "autoimmune": "Autoimmune / inflammation", "infectious": "Infectious disease",
            "rare": "Rare disease", "other": "Other / mixed"}


def _family_pct_by_group(df, group_col):
    df = df.copy()
    df["family"] = df["bucket"].map(lambda c: PROG_CATS.get(c, (None, "ambiguous"))[1])
    total = df.groupby(group_col).n_programs.sum().rename("total")
    grid = df.groupby([group_col, "family"]).n_programs.sum().unstack(fill_value=0)
    for f in ("biology", "business", "ambiguous"):
        if f not in grid.columns:
            grid[f] = 0
    grid = grid[["biology", "business", "ambiguous"]]
    grid = grid.div(grid.sum(axis=1), axis=0) * 100
    return grid, total


def _fam_stacked(ax, groups, grid, totals, label_map, title):
    order = [g for g in groups if g in grid.index]
    left = [0.0] * len(order)
    for fam in ("biology", "business", "ambiguous"):
        vals = [grid.loc[g, fam] for g in order]
        ax.barh(range(len(order)), vals, left=left, color=FAMILY[fam],
                height=0.68, edgecolor=SURFACE, linewidth=0.5, zorder=3)
        for i, (v, l) in enumerate(zip(vals, left)):
            if v >= 5:
                ax.text(l + v / 2, i, f"{v:.0f}%", ha="center", va="center",
                        fontsize=9, fontweight="bold",
                        color="white" if fam != "ambiguous" else INK)
        left = [l + v for l, v in zip(left, vals)]
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{label_map.get(g, g)[:26].ljust(26)}   n={int(totals[g]):>5,}"
                        for g in order], fontsize=10, color=INK, family="monospace")
    ax.invert_yaxis()
    ax.set_xlim(0, 100); ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title(title, fontsize=12, color=INK, loc="left", pad=8)


def fig_stratified():
    df_ta = pd.read_csv(os.path.join(DATA, "failure_holistic_by_ta.csv"))
    df_ta = df_ta[df_ta.bucket.isin(PROG_CATS)].copy()
    grid_ta, totals_ta = _family_pct_by_group(df_ta, "therapeutic_area")

    MOD_CANON = {
        "small_molecule": "small_molecule",
        "antibody": "antibody", "mAb": "antibody", "bispecific_mAb": "antibody",
        "antibody_drug_conjugate": "ADC", "ADC": "ADC",
        "protein": "protein", "protein_or_enzyme": "protein",
        "peptide": "peptide",
        "oligonucleotide": "oligonucleotide", "oligonucleotide_ASO": "oligonucleotide",
        "oligonucleotide_siRNA": "oligonucleotide",
        "vaccine": "vaccine",
        "cell_therapy": "cell_therapy", "other_cell_therapy": "cell_therapy",
        "CAR_T": "cell_therapy", "TIL": "cell_therapy",
        "gene_therapy": "gene_therapy", "AAV_gene_therapy": "gene_therapy",
        "ex_vivo_gene_therapy": "gene_therapy",
        "mrna": "mrna",
    }
    df_mod = pd.read_csv(os.path.join(DATA, "failure_holistic_by_modality.csv"))
    df_mod["modality"] = df_mod.modality_raw.map(MOD_CANON)
    df_mod = df_mod[df_mod.modality.notna() & df_mod.bucket.isin(PROG_CATS)].copy()
    df_mod = df_mod.groupby(["modality", "bucket"], as_index=False).n_programs.sum()
    grid_mod, totals_mod = _family_pct_by_group(df_mod, "modality")
    MIN_N = 50
    keep_mod = [m for m in totals_mod.sort_values(ascending=False).index if totals_mod[m] >= MIN_N]
    MOD_LABEL = {"small_molecule": "Small molecule", "antibody": "Antibody",
                 "ADC": "Antibody-drug conj.", "protein": "Protein / enzyme",
                 "peptide": "Peptide", "oligonucleotide": "Oligonucleotide",
                 "vaccine": "Vaccine", "cell_therapy": "Cell therapy",
                 "gene_therapy": "Gene therapy", "mrna": "mRNA"}

    fig, axes = plt.subplots(1, 2, figsize=(16.5, 5.8), gridspec_kw={"width_ratios": [1, 1]})
    fig.subplots_adjust(left=0.11, right=0.97, top=0.80, bottom=0.09, wspace=0.55)
    _fam_stacked(axes[0], TA_ORDER, grid_ta, totals_ta, TA_LABEL, "By therapeutic area")
    _fam_stacked(axes[1], keep_mod, grid_mod, totals_mod, MOD_LABEL,
                 f"By drug modality  (drugs with modality known; n>={MIN_N})")

    fig.text(0.02, 0.945, "How failure modes vary across strata",
             fontsize=14, fontweight="bold", color=INK)
    fig.text(0.02, 0.902,
             "Share of failed Ph1+ programs by family. Biology includes silent Ph3 fails and Ph2 stalls; "
             "Ph1 stalls tagged ambiguous.",
             fontsize=9.5, color=SEC)
    handles = [Patch(facecolor=FAMILY[f], label=FAMILY_LABEL[f])
               for f in ("biology", "business", "ambiguous")]
    leg = fig.legend(handles=handles, loc="lower center", frameon=False, ncol=3,
                     fontsize=10, bbox_to_anchor=(0.5, -0.02))
    for t in leg.get_texts():
        t.set_color(SEC)
    stem = "failure_modes_stratified"
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=600)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png + .svg")


def main():
    style()
    fig_main()
    fig_terminations()
    fig_stratified()


if __name__ == "__main__":
    main()
