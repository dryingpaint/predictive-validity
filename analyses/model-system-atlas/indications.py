"""Each named disease, its programs, and the indications those programs were tested in (issue #76).

    .venv/bin/python analyses/model-system-atlas/indications.py

A program is one (entity, MONDO disease). Its indications are the stage, patient subtype and line of
therapy its trials were registered under inside that disease: the ClinicalTrials.gov condition rows
(preclin.indication, classified fields disease_stage / patient_subset / line_of_therapy) of every trial
attached to the program (preclin.dev_program_trial), kept when the row's MONDO term is the disease or a
descendant of it. A trial that names a specific indication does not also count as the general one; a
program counts once in every indication it was tested in, so a disease's indication counts add to more
than its program count. A classified stage counts only when the condition name carries a cue for it (the classifier calls bare
"Glioblastoma" advanced and bare "Acute myeloid leukemia" acute) and the word is not part of the
disease's own name; condition rows the classifier never saw (about a fifth, mostly oncology stage and
recurrence names) and rows whose stage was dropped are read from the name with the keyword map below
(`basis` = name). "chronic" is the default state of a chronic disease and, like a subtype that only
restates the disease (HIV-1, plaque psoriasis), is folded into the general indication.

Cohort and disease list as lists.py: Phase 2 entries 2008-2019, the 71 named indications in
lists/named_indications.csv. Read-only. Writes lists/indications.csv (one row per disease x
indication), lists/indications_by_disease.csv, and disease_indications.png / .svg beside this file.
"""
import os
import sys
from collections import Counter

import matplotlib
import pandas as pd

matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "atlas"  # stable ids, so a re-render of the same data is byte-identical
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import NullLocator

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from lists import DROP, MERGE, PHASE, WINDOW

from report import frame, section1

LISTS = os.path.join(HERE, "lists")
INK, MUTED, RULE, BAND = "#1b2321", "#5c6763", "#c4cbc7", "#f3f5f4"
HUE = "#3d9ea6"

# Condition names the classifier never saw: stage and subtype read from the name, first match wins.
STAGE_WORDS = [
    ("relapsed", r"recurrent|relapsed|refractory"),
    ("metastatic", r"metastatic|stage iv"),
    ("locally_advanced", r"stage iii|locally advanced"),
    ("advanced", r"\badvanced"),
    ("early", r"\bearly\b|\bstage ii?\b"),
    ("acute", r"\bacute\b"),
]
SUBSET_WORDS = [
    ("castration-resistant", r"castrat"),
    ("TNBC", r"triple.negative|tnbc"),
    ("HER2+", r"her2.positive|her2\+"),
    ("HER2-", r"her2.negative|her2-\b"),
    ("HR+", r"hormone receptor.positive|\bhr\+"),
    ("ER+", r"estrogen receptor.positive|\ber\+"),
    ("EGFR+", r"\begfr\b"),
    ("ALK+", r"\balk\b"),
    ("non-squamous", r"non.squamous"),
    ("squamous", r"(?<!non-)(?<!non )squamous"),
]
# a classified stage is believed only when the condition name says something beyond the disease
CUE = (r"metasta|advanced|recurren|relaps|refractor|\bstage\b|early|newly|acute|unresectable|inoperable|progress|persistent|"
       r"resistant|severe|moderate|mild|untreated|naive|line\b|\b[123]l\b|adjuvant|maintenance|exacerbat|decompensat|\bactive\b")
# subtypes that restate the disease, folded into general
RESTATES = {"HIV infectious disease": {"hiv-1"}, "diabetic kidney disease": {"diabetic nephropathy"},
            "psoriasis": {"plaque psoriasis", "plaque", "chronic plaque psoriasis"}}
NOT_A_SUBSET = {"null", "none", "nos", "unspecified", "n/a"}
SUBSET_SYNONYM = {"castrate-resistant": "castration-resistant", "crpc": "castration-resistant",
                  "mcrpc": "castration-resistant", "her2 positive": "her2+", "her2 negative": "her2-",
                  "hormone receptor-positive": "hr+", "estrogen-receptor positive": "er+",
                  "triple negative": "tnbc", "triple-negative": "tnbc"}
STAGE_LABEL = {"locally_advanced": "locally advanced", "relapsed_refractory": "relapsed"}
SHORT = {"metabolic dysfunction-associated steatohepatitis": "MASH", "attention deficit-hyperactivity disorder": "ADHD",
         "chronic obstructive pulmonary disease": "COPD", "non-small cell lung carcinoma": "non-small cell lung cancer",
         "small cell lung carcinoma": "small cell lung cancer", "paroxysmal nocturnal hemoglobinuria": "PNH",
         "age-related macular degeneration": "AMD", "hepatitis C virus infection": "hepatitis C",
         "chronic hepatitis B virus infection": "chronic hepatitis B", "HIV infectious disease": "HIV",
         "idiopathic pulmonary fibrosis": "IPF", "gastroesophageal reflux disease": "GERD",
         "malignant pancreatic neoplasm": "pancreatic cancer", "plasma cell myeloma": "multiple myeloma",
         "benign prostatic hyperplasia": "BPH", "major depressive disorder": "major depression",
         "secondary hyperparathyroidism": "secondary hyperparathyroidism"}
AREA = {"infectious_disease": "infectious disease"}


def cohort(named: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Phase 2 entries 2008-2019 in the named diseases, as lists.py draws them."""
    snap = frame.snapshot()
    progs, trials = frame.programs(), frame.program_trials()
    rows = section1.phase_rows(progs, trials, snap, window=WINDOW)
    ent = rows[(rows.phase == PHASE) & ~rows.credited][["program_id", "moiety_id"]].copy()
    ent["mondo_id"] = ent.program_id.map(progs.set_index("program_id").mondo_id)
    ent = ent[ent.mondo_id.notna()]
    ent["disease"] = ent.mondo_id.map(lambda m: MERGE.get(m, m))
    ent = ent[~ent.disease.isin(DROP) & ent.disease.isin(set(named.mondo_id))]
    return ent.drop_duplicates("program_id"), str(snap)


def condition_rows(ent: pd.DataFrame, named: pd.DataFrame) -> pd.DataFrame:
    """One row per (program, trial, condition) whose MONDO term sits inside the program's disease."""
    tr = frame.query("SELECT program_id, nct_id, phase FROM preclin.dev_program_trial WHERE program_id = ANY(%s)",
                     (list(map(int, ent.program_id)),))
    ind = frame.query("""
        SELECT s.nct_id, i.indication_id, i.display_name, i.mondo_id AS ind_mondo, i.canonical_disease,
               i.disease_stage, i.patient_subset, i.line_of_therapy
        FROM preclin.ctgov_study_indication s JOIN preclin.indication i USING (indication_id)
        WHERE s.nct_id = ANY(%s) AND i.indication_kind = 'disease' AND i.mondo_id IS NOT NULL""",
                      (list(tr.nct_id.unique()),))
    roots = list(named.mondo_id) + [c for c, p in MERGE.items() if p in set(named.mondo_id)]
    anc = frame.query("SELECT term_id, ancestor_id FROM preclin.ontology_ancestor WHERE ontology = 'MONDO' AND ancestor_id = ANY(%s)",
                      (roots,))
    anc = pd.concat([anc, pd.DataFrame({"term_id": roots, "ancestor_id": roots})])
    anc["disease"] = anc.ancestor_id.map(lambda m: MERGE.get(m, m))
    anc = anc[["term_id", "disease"]].drop_duplicates().rename(columns={"term_id": "ind_mondo"})
    x = tr.merge(ind, on="nct_id").merge(ent[["program_id", "disease"]], on="program_id")
    return x.merge(anc, on=["ind_mondo", "disease"], how="inner")


def classify(x: pd.DataFrame, named: pd.DataFrame) -> pd.DataFrame:
    """Stage, subtype and line per condition row; from the classifier where it ran and the name backs it, else from the name."""
    x = x.merge(named[["mondo_id", "label"]].rename(columns={"mondo_id": "disease", "label": "disease_label"}), on="disease")
    x["basis"] = "classified"
    name = x.display_name.fillna("").str.lower()
    dlabel = x.disease_label.str.lower()
    stage = x.disease_stage.replace(STAGE_LABEL).where(x.disease_stage != "chronic")
    stage = stage.where(~stage.fillna("").str.lower().isin(NOT_A_SUBSET))
    line = x.line_of_therapy.where(~x.line_of_therapy.fillna("").str.lower().isin(NOT_A_SUBSET))
    stage = stage.where(line != "relapsed_refractory", "relapsed")
    line = line.where(line != "relapsed_refractory")
    seen = x.canonical_disease.notna()
    cued = name.str.contains(CUE, regex=True)
    in_label = pd.Series(False, index=x.index)
    for key, pat in STAGE_WORDS:
        in_label |= (stage == STAGE_LABEL.get(key, key)) & dlabel.str.contains(pat, regex=True)
    dropped = seen & stage.notna() & (~cued | in_label)
    stage = stage.where(~dropped)
    for key, pat in STAGE_WORDS:
        hit = stage.isna() & name.str.contains(pat, regex=True) & ~dlabel.str.contains(pat, regex=True)
        stage = stage.where(~hit, STAGE_LABEL.get(key, key))
    subset = x.patient_subset.str.strip().str.lower().replace(SUBSET_SYNONYM)
    restates = pd.Series([bool(s) and (s in NOT_A_SUBSET or s in d or d in s or s in RESTATES.get(lab, set()))
                          for s, d, lab in zip(subset.fillna(""), dlabel, x.disease_label)], index=x.index)
    subset = subset.where(~restates)
    for key, pat in SUBSET_WORDS:
        hit = subset.isna() & name.str.contains(pat, regex=True) & ~dlabel.str.contains(pat, regex=True)
        subset = subset.where(~hit, key.lower())
    x.loc[~seen | dropped, "basis"] = "name"
    x["stage"], x["subset"], x["line"] = stage, subset, line
    # a subtype's display spelling: the commonest original casing of each lower-cased key
    spell = {}
    spelled = pd.DataFrame({"k": subset, "orig": x.patient_subset.str.strip()}).dropna()
    for k, g in spelled.groupby("k"):
        spell[k] = Counter(g.orig).most_common(1)[0][0]
    for key, _ in SUBSET_WORDS:
        spell.setdefault(key.lower(), key)
    x["subset_label"] = x.subset.map(spell)
    parts = [x.stage.fillna(""), x.subset_label.fillna(""), x.line.fillna("")]
    x["indication"] = [" · ".join(p for p in ps if p) or "general" for ps in zip(*parts)]
    return x


def tabulate(ent: pd.DataFrame, x: pd.DataFrame, named: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    # a trial that names a specific indication is not also a general trial
    specific = x[x.indication != "general"]
    general = x[(x.indication == "general") & ~x.nct_id.isin(set(specific.nct_id))]
    rows = pd.concat([specific, general])
    # programs with no condition row inside their disease are general
    missing = ent[~ent.program_id.isin(set(rows.program_id))]
    rows = pd.concat([rows, missing.assign(indication="general", stage=None, subset_label=None, line=None, basis="no_row")])
    per = (rows.groupby(["disease", "indication"])
           .agg(programs=("program_id", "nunique"), stage=("stage", "first"), subset=("subset_label", "first"), line=("line", "first"))
           .reset_index())
    # programs an indication owes to the name reading alone
    sup = rows.groupby(["disease", "indication", "program_id"]).basis.agg(lambda s: "classified" if "classified" in set(s) else "name")
    by_name = sup[sup == "name"].reset_index().groupby(["disease", "indication"]).program_id.nunique().rename("programs_from_name")
    per = per.merge(by_name, on=["disease", "indication"], how="left").fillna({"programs_from_name": 0})
    per["programs_from_name"] = per.programs_from_name.astype(int)
    per = per.merge(named[["area", "rank", "mondo_id", "label"]], left_on="disease", right_on="mondo_id")
    per = per.sort_values(["area", "rank", "programs"], ascending=[True, True, False])
    per = per[["area", "rank", "mondo_id", "label", "indication", "stage", "subset", "line", "programs", "programs_from_name"]]
    spec = per[per.indication != "general"]
    largest = spec.sort_values("programs", ascending=False).drop_duplicates("mondo_id").set_index("mondo_id")
    by = named.copy()
    by["programs"] = by.mondo_id.map(ent.groupby("disease").program_id.nunique()).fillna(0).astype(int)
    by["n_indications"] = by.mondo_id.map(per.groupby("mondo_id").indication.nunique()).fillna(0).astype(int)
    by["n_specific"] = by.mondo_id.map(spec.groupby("mondo_id").indication.nunique()).fillna(0).astype(int)
    by["programs_general"] = by.mondo_id.map(per[per.indication == "general"].set_index("mondo_id").programs).fillna(0).astype(int)
    by["largest_specific"] = by.mondo_id.map(largest.indication)
    by["largest_specific_programs"] = by.mondo_id.map(largest.programs).fillna(0).astype(int)
    return per, by


def draw(per: pd.DataFrame, by: pd.DataFrame, snap: str, share_name: float, out: str) -> None:
    ROW, HEAD, GAP = 0.27, 0.36, 0.08
    areas = list(dict.fromkeys(by.area))
    height = {a: HEAD + ROW * (by.area == a).sum() + GAP for a in areas}
    cols, run, total = [[]], 0.0, sum(height.values())
    for a in areas:
        if run + height[a] / 2 > total / 2 and len(cols) == 1:
            cols.append([])
            run = 0.0
        cols[-1].append(a)
        run += height[a]
    col_h = max(sum(height[a] for a in c) for c in cols)
    TOP, BOTTOM, W = 1.72, 0.74, 12.6
    fig_h = TOP + col_h + BOTTOM
    fig = plt.figure(figsize=(W, fig_h), dpi=200)
    fy = lambda inches: 1 - inches / fig_h

    n_ind = int(by.n_indications.sum())
    fig.text(0.012, fy(0.28), "Seventy-one diseases, their programs, and the indications those programs were tested in",
             fontsize=15, fontweight="bold", color=INK, va="top")
    fig.text(0.012, fy(0.62),
             "Programs entering Phase 2 in 2008–2019 in the atlas's 71 named diseases. An indication is the stage, patient subtype or line of therapy a "
             "program's trials were registered under within the disease;\n\"general\" is the disease with none stated. A program counts in every "
             "indication it was tested in, so a disease's indications add to more than its programs. Each axis is a number of programs, log scale.",
             fontsize=8.4, color=MUTED, va="top", linespacing=1.45)
    handles = [Line2D([], [], marker="|", color=INK, markersize=9, markeredgewidth=1.8, linestyle="none", label="all programs in the disease"),
               Line2D([], [], marker="o", markerfacecolor="white", markeredgecolor=HUE, markeredgewidth=1.3, markersize=6.5, linestyle="none",
                      label="the general indication"),
               Line2D([], [], marker="o", markerfacecolor=HUE, markeredgecolor="white", markeredgewidth=0.9, markersize=6.5, linestyle="none",
                      label="a specific indication (stage, subtype or line); the largest is named under the disease; ×n marks n indications with the same count")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.009, fy(1.08)), ncol=3, frameon=False, fontsize=8.2,
               handletextpad=0.5, columnspacing=1.8, labelcolor=INK)

    col_w = 0.5 - 0.012
    label_w, num_w = 0.19, 0.045
    for ci, col in enumerate(cols):
        x0 = 0.012 + ci * 0.5
        bg = fig.add_axes([x0, fy(TOP + col_h), col_w, col_h / fig_h])
        bg.set_xlim(0, 1)
        bg.set_ylim(col_h, 0)
        bg.axis("off")
        ax_x0 = x0 + label_w + 2 * num_w + 0.012
        ax_w = x0 + col_w - 0.018 - ax_x0
        ax = fig.add_axes([ax_x0, fy(TOP + col_h), ax_w, col_h / fig_h])
        ax.set_xscale("log")
        ax.set_xlim(0.75, 320)
        ax.set_ylim(col_h, 0)
        ax.patch.set_alpha(0)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_yticks([])
        ticks = [1, 3, 10, 30, 100]
        ax.set_xticks(ticks)
        ax.set_xticklabels([str(t) for t in ticks], fontsize=7, color=MUTED)
        ax.xaxis.set_minor_locator(NullLocator())
        ax.tick_params(axis="x", which="both", length=0, pad=2)
        ax.grid(axis="x", color=RULE, linewidth=0.5, alpha=0.7, zorder=0)
        # column headings
        hx = (label_w + num_w - 0.004) / col_w
        bg.text(hx, -0.07, "programs", fontsize=7, color=MUTED, ha="right", va="bottom")
        bg.text((label_w + 2 * num_w - 0.004) / col_w, -0.07, "indications", fontsize=7, color=MUTED, ha="right", va="bottom")
        ax.text(0.75, -0.07, "programs per indication", fontsize=7, color=MUTED, ha="left", va="bottom")
        y = 0.0
        for a in col:
            y += HEAD
            bg.text(0.0, y - 0.12, AREA.get(a, a).replace("_", " ").capitalize(), fontsize=9.6, fontweight="bold", color=INK, va="center")
            bg.plot([0, 1], [y - 0.01, y - 0.01], color=RULE, linewidth=0.6)
            for i, r in enumerate(by[by.area == a].itertuples()):
                y0, y1 = y, y + ROW
                yc = y + ROW / 2
                if i % 2 == 0:
                    bg.axhspan(y0, y1, color=BAND, zorder=0)
                bg.text(0.004, y0 + 0.095, SHORT.get(r.label, r.label), fontsize=8, fontweight="bold", color=INK, va="center")
                sub = (f"{r.largest_specific} · {r.largest_specific_programs}" if r.n_specific else "no specific indication")
                bg.text(0.004, y0 + 0.2, sub, fontsize=6.5, color=MUTED, va="center")
                bg.text(hx, yc, f"{r.programs}", fontsize=7.8, color=INK, ha="right", va="center")
                bg.text((label_w + 2 * num_w - 0.004) / col_w, yc, f"{r.n_indications}", fontsize=7.8, color=MUTED, ha="right", va="center")
                d = per[per.mondo_id == r.mondo_id]
                spec = d[d.indication != "general"].groupby("programs").size()
                ax.plot(spec.index, [yc] * len(spec), "o", markersize=5.6, markerfacecolor=HUE, markeredgecolor="white",
                        markeredgewidth=0.9, linestyle="none", zorder=3)
                flip = 0
                for v, k in spec.items():
                    if k > 1:  # labels alternate above and below so neighbours do not collide
                        ax.text(v * 1.14, yc + (-0.075, 0.08)[flip % 2], f"×{k}", fontsize=5.8, color=MUTED, ha="left", va="center", zorder=6)
                        flip += 1
                gen = d[d.indication == "general"]
                ax.plot(gen.programs, [yc] * len(gen), "o", markersize=6.2, markerfacecolor="white", markeredgecolor=HUE,
                        markeredgewidth=1.3, linestyle="none", zorder=4)
                ax.plot([r.programs], [yc], marker="|", color=INK, markersize=8, markeredgewidth=1.6, linestyle="none", zorder=5)
                y = y1
            y += GAP
    fig.text(0.012, fy(fig_h - 0.16),
             f"{len(by)} diseases · {n_ind} disease × indication pairs, {int(by.n_specific.sum())} of them specific · {by.programs.sum():,} programs. "
             f"Database snapshot {snap}.\nCondition rows read from the condition name rather than the classifier: {share_name:.0%} "
             f"(lists/indications.csv records how many programs each indication owes to that reading).",
             fontsize=7.2, color=MUTED, va="bottom", linespacing=1.4)
    fig.savefig(out + ".png", facecolor="white", metadata={"Date": None})
    fig.savefig(out + ".svg", facecolor="white", metadata={"Date": None})
    plt.close(fig)


def main() -> None:
    named = pd.read_csv(os.path.join(LISTS, "named_indications.csv"))
    ent, snap = cohort(named)
    x = classify(condition_rows(ent, named), named)
    per, by = tabulate(ent, x, named)
    per.to_csv(os.path.join(LISTS, "indications.csv"), index=False)
    by.to_csv(os.path.join(LISTS, "indications_by_disease.csv"), index=False)
    share_name = float((x.basis == "name").mean())
    draw(per, by, snap, share_name, os.path.join(HERE, "disease_indications"))
    print(f"snapshot {snap}: {len(by)} diseases, {by.programs.sum():,} programs, {int(by.n_indications.sum())} disease × indication pairs "
          f"({int(by.n_specific.sum())} specific); {(by.n_specific == 0).sum()} diseases have only the general indication; "
          f"{share_name:.0%} of condition rows read from the name")
    print(by[["area", "label", "programs", "n_indications", "largest_specific", "largest_specific_programs"]].to_string(index=False))


if __name__ == "__main__":
    main()
