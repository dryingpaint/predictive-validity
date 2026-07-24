#!/usr/bin/env python3
"""
Section 1 figures — why industry drug programs fail.

Two views (both matter, they tell different halves of the story):

  (1) TERMINATIONS chart — Stephen's original. Reads `failure_taxonomy.csv`
      (Sonnet-deduped why_stopped classifications over 5,510 terminated
      industry Phase 1–3 trials 2015–2025). Shows the *stated* reason
      trials that stopped early were stopped. Business/operational
      dominates because completed-but-negative trials aren't in this cut.

  (2) HOLISTIC chart — program-level (drug × indication × sponsor),
      denominator = every Phase 2+ program that failed to reach approval
      (35,800 programs). Reads `failure_holistic.csv`. Folds in silent
      efficacy failures (Ph3 completed → no approval) and Ph2 stalls,
      which the terminations chart misses.

Also stratifies the holistic chart by therapeutic area (`failure_holistic_by_ta.csv`)
and by drug modality (`failure_holistic_by_modality.csv`), when known.

Refresh the CSVs with `refresh_failure_data.py`. This script reads only the CSVs.
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
DATA = os.path.join(HERE, "..", "data")
os.makedirs(DATA, exist_ok=True)

# palette
INK, SEC, MUTED = "#14110f", "#5b544e", "#938b82"
SURFACE, RULE = "#fbfaf8", "#d8d3cb"
BIOLOGY, BUSINESS, AMBIG = "#1f6fd0", "#e2673a", "#c7c0b6"

FAMILY = {"biology": BIOLOGY, "business": BUSINESS, "ambiguous": AMBIG}
FAMILY_LABEL = {"biology": "Biology (efficacy / safety / PK)",
                "business": "Business & operational",
                "ambiguous": "Other / undisclosed"}

# ─── Terminations chart categories (trial-level, why_stopped only) ────────
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

# ─── Holistic chart buckets (program-level) ────────────────────────────────
PROG_CATS = {
    "silent_efficacy_ph3":      ("Silent efficacy fail (Ph3 complete, no approval)", "biology"),
    "ph2_stall":                ("Ph2 stall (Ph2 complete, program halted)", "biology"),
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

# Ph2 stalls are the softest inference — completed Ph2 but the program halted.
# Most industry practice is that Ph2 → Ph3 gates on efficacy signal, so the
# common read is "efficacy insufficient." We tag them biology but visually
# distinguish them by cross-hatching (they're the ambiguous end of biology).
BIOLOGY_SOFT = {"ph2_stall"}


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


def ranked_bar(ax, df, disp_col, pct_col, cat_col, cats_map, xlim, label_fs=10.5):
    """Draw ranked horizontal bar chart. df is sorted ascending by pct."""
    y = range(len(df))
    colors = [FAMILY[cats_map[c][1]] for c in df[cat_col]]
    hatches = ["///" if c in BIOLOGY_SOFT else "" for c in df[cat_col]]
    bars = ax.barh(list(y), df[pct_col], height=0.62, color=colors, zorder=3,
                   edgecolor=SURFACE, linewidth=0.5)
    for bar, hatch in zip(bars, hatches):
        if hatch:
            bar.set_hatch(hatch)
            bar.set_edgecolor(SURFACE)
    for yi, pct in enumerate(df[pct_col]):
        ax.text(pct + xlim * 0.015, yi, _pct_label(pct),
                va="center", ha="left", fontsize=label_fs, fontweight="bold", color=INK)
    ax.set_yticks(list(y))
    ax.set_yticklabels(df[disp_col], fontsize=10.5, color=INK)
    ax.set_xticks([]); ax.set_xlim(0, xlim)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.margins(y=0.02)


def _family_share(df, cat_col, pct_col, cats_map):
    df = df.copy()
    df["fam"] = df[cat_col].map(lambda c: cats_map[c][1])
    return df.groupby("fam")[pct_col].sum().to_dict()


def _family_legend(ax, fam_share, loc="lower right"):
    handles = [Patch(facecolor=FAMILY[f], label=f"{FAMILY_LABEL[f]}  ·  {fam_share.get(f, 0):.0f}%")
               for f in ("biology", "business", "ambiguous")]
    leg = ax.legend(handles=handles, loc=loc, frameon=False, fontsize=9.5,
                    handlelength=1.0, handleheight=1.0, borderpad=0, labelspacing=0.6)
    for t in leg.get_texts():
        t.set_color(SEC)
    return leg


# ─── Figure 1: terminations chart (Stephen's original — trial-level) ────────
def fig_terminations():
    df = pd.read_csv(os.path.join(DATA, "failure_taxonomy.csv"))
    df = df[df.category.isin(TRIAL_CATS)].copy()
    df["disp"] = df.category.map(lambda c: TRIAL_CATS[c][0])
    df = df.sort_values("pct_of_all_classified")
    fam_share = _family_share(df, "category", "pct_of_all_classified", TRIAL_CATS)

    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    fig.subplots_adjust(left=0.30, right=0.93, top=0.965, bottom=0.06)
    ranked_bar(ax, df, "disp", "pct_of_all_classified", "category", TRIAL_CATS, xlim=50)
    _family_legend(ax, fam_share)
    stem = "failure_modes_terminations"
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=600)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png + .svg  ({int(df.pct_of_all_classified.sum())}% ≈ trial-level, terminations only)")


# ─── Figure 2: holistic chart (program-level, all Ph2+ failures) ────────────
def fig_holistic():
    df = pd.read_csv(os.path.join(DATA, "failure_holistic.csv"))
    df = df[df.bucket.isin(PROG_CATS)].copy()
    df["disp"] = df.bucket.map(lambda c: PROG_CATS[c][0])
    df = df.sort_values("pct_of_failed_programs")
    fam_share = _family_share(df, "bucket", "pct_of_failed_programs", PROG_CATS)

    fig, ax = plt.subplots(figsize=(10.6, 6.6))
    fig.subplots_adjust(left=0.42, right=0.94, top=0.965, bottom=0.06)
    ranked_bar(ax, df, "disp", "pct_of_failed_programs", "bucket", PROG_CATS, xlim=48)
    _family_legend(ax, fam_share)
    # Hatched-biology marker in legend footer
    ax.text(0.99, -0.08, "hatched bars = weaker inference (program stalled at Ph2, likely efficacy)",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.5, color=MUTED, style="italic")
    stem = "failure_modes_holistic"
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=600)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png + .svg  (n={int(df.n_programs.sum())} failed programs)")


# ─── Figure 3: side-by-side comparison ──────────────────────────────────────
def fig_compare():
    df_t = pd.read_csv(os.path.join(DATA, "failure_taxonomy.csv"))
    df_t = df_t[df_t.category.isin(TRIAL_CATS)].copy()
    df_t["disp"] = df_t.category.map(lambda c: TRIAL_CATS[c][0])
    df_t = df_t.sort_values("pct_of_all_classified")
    fam_t = _family_share(df_t, "category", "pct_of_all_classified", TRIAL_CATS)

    df_p = pd.read_csv(os.path.join(DATA, "failure_holistic.csv"))
    df_p = df_p[df_p.bucket.isin(PROG_CATS)].copy()
    df_p["disp"] = df_p.bucket.map(lambda c: PROG_CATS[c][0])
    df_p = df_p.sort_values("pct_of_failed_programs")
    fam_p = _family_share(df_p, "bucket", "pct_of_failed_programs", PROG_CATS)

    fig, axes = plt.subplots(1, 2, figsize=(15.5, 7.4), gridspec_kw={"width_ratios": [1, 1.3]})
    fig.subplots_adjust(left=0.13, right=0.98, top=0.78, bottom=0.06, wspace=0.75)

    ranked_bar(axes[0], df_t, "disp", "pct_of_all_classified", "category", TRIAL_CATS, xlim=50, label_fs=9.5)
    axes[0].set_title("Terminations only  (n=5,510 trials)\nwhat sponsors state when they stop a trial early",
                      fontsize=11, color=SEC, loc="left", pad=14)
    _family_legend(axes[0], fam_t)

    ranked_bar(axes[1], df_p, "disp", "pct_of_failed_programs", "bucket", PROG_CATS, xlim=48, label_fs=9.5)
    axes[1].set_title(f"All Ph2+ program failures  (n={int(df_p.n_programs.sum()):,} programs)\nwhat actually happens when a drug does not reach approval",
                      fontsize=11, color=SEC, loc="left", pad=14)
    _family_legend(axes[1], fam_p)

    fig.text(0.02, 0.92, "Two ways to count failure — and why the answer changes",
             fontsize=15, fontweight="bold", color=INK)
    fig.text(0.02, 0.878,
             "Left: trial-level, terminations only. Right: program-level (drug x indication x sponsor), "
             "all Ph2+ programs that never reached approval.",
             fontsize=9.5, color=SEC)

    stem = "failure_modes_comparison"
    fig.savefig(os.path.join(DATA, stem + ".png"), bbox_inches="tight", dpi=600)
    fig.savefig(os.path.join(DATA, stem + ".svg"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote data/{stem}.png + .svg")


# ─── Figure 4: stratified by therapeutic area ──────────────────────────────
TA_ORDER = ["oncology", "neuro", "cv", "metabolic", "autoimmune", "infectious", "rare", "other"]
TA_LABEL = {"oncology": "Oncology", "neuro": "Neurology / psych",
            "cv": "Cardiovascular", "metabolic": "Metabolic",
            "autoimmune": "Autoimmune / inflammation", "infectious": "Infectious disease",
            "rare": "Rare disease", "other": "Other / mixed"}


def _family_pct_by_group(df, group_col, cats_map):
    """Group by group_col, split each row's programs into biology/business/ambiguous."""
    df = df.copy()
    df["family"] = df["bucket"].map(lambda c: cats_map.get(c, (None, "ambiguous"))[1])
    total = df.groupby(group_col).n_programs.sum().rename("total")
    grid = df.groupby([group_col, "family"]).n_programs.sum().unstack(fill_value=0)
    for f in ("biology", "business", "ambiguous"):
        if f not in grid.columns:
            grid[f] = 0
    grid = grid[["biology", "business", "ambiguous"]]
    grid = grid.div(grid.sum(axis=1), axis=0) * 100
    return grid, total


def _fam_stacked(ax, groups, grid, totals, title):
    """Stacked bar: biology / business / ambiguous shares per group."""
    order = [g for g in groups if g in grid.index]
    left = [0.0] * len(order)
    for fam in ("biology", "business", "ambiguous"):
        vals = [grid.loc[g, fam] for g in order]
        bars = ax.barh(range(len(order)), vals, left=left, color=FAMILY[fam],
                       height=0.68, edgecolor=SURFACE, linewidth=0.5, zorder=3)
        for i, (v, l) in enumerate(zip(vals, left)):
            if v >= 5:
                ax.text(l + v / 2, i, f"{v:.0f}%", ha="center", va="center",
                        fontsize=9, fontweight="bold", color="white" if fam != "ambiguous" else INK)
        left = [l + v for l, v in zip(left, vals)]
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{TA_LABEL.get(g, g)[:26].ljust(26)}   n={int(totals[g]):>5,}"
                        for g in order],
                       fontsize=10, color=INK, family="monospace")
    ax.invert_yaxis()
    ax.set_xlim(0, 100); ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title(title, fontsize=12, color=INK, loc="left", pad=8)


def fig_stratified():
    df_ta = pd.read_csv(os.path.join(DATA, "failure_holistic_by_ta.csv"))
    df_ta = df_ta[df_ta.bucket.isin(PROG_CATS)].copy()
    grid_ta, totals_ta = _family_pct_by_group(df_ta, "therapeutic_area", PROG_CATS)

    # Normalize modality labels: fold synonyms into canonical groups
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
    grid_mod, totals_mod = _family_pct_by_group(df_mod, "modality", PROG_CATS)
    MIN_N = 50  # suppress modalities with too few failed programs
    keep_mod = [m for m in totals_mod.sort_values(ascending=False).index if totals_mod[m] >= MIN_N]

    MOD_LABEL = {"small_molecule": "Small molecule", "antibody": "Antibody",
                 "ADC": "Antibody-drug conj.", "protein": "Protein / enzyme",
                 "peptide": "Peptide", "oligonucleotide": "Oligonucleotide",
                 "vaccine": "Vaccine", "cell_therapy": "Cell therapy",
                 "gene_therapy": "Gene therapy", "mrna": "mRNA"}

    fig, axes = plt.subplots(1, 2, figsize=(16.5, 5.8), gridspec_kw={"width_ratios": [1, 1]})
    fig.subplots_adjust(left=0.11, right=0.97, top=0.80, bottom=0.09, wspace=0.55)

    _fam_stacked(axes[0], TA_ORDER, grid_ta, totals_ta,
                 "By therapeutic area")
    # Relabel modality rows using MOD_LABEL
    grid_mod_relabel = grid_mod.rename(index=MOD_LABEL)
    totals_mod_relabel = totals_mod.rename(index=MOD_LABEL)
    keep_mod_relabel = [MOD_LABEL.get(m, m) for m in keep_mod]
    # Reuse _fam_stacked but with modality labels
    _fam_stacked(axes[1], keep_mod_relabel, grid_mod_relabel, totals_mod_relabel,
                 f"By drug modality  (drugs with modality known; n≥{MIN_N})")

    fig.text(0.02, 0.945, "How failure modes vary across strata",
             fontsize=14, fontweight="bold", color=INK)
    fig.text(0.02, 0.902,
             "Share of failed Ph2+ programs by family. Biology (efficacy / safety / PK) includes silent Ph3 fails and Ph2 stalls.",
             fontsize=9.5, color=SEC)
    # Family color key
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
    fig_terminations()
    fig_holistic()
    fig_compare()
    fig_stratified()


if __name__ == "__main__":
    main()
