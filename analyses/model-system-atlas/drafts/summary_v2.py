"""Second attempt at the summary: one grid, three colours, read top to bottom.

    .venv/bin/python analyses/model-system-atlas/drafts/summary_v2.py

Rows = the 71 contexts grouped by what kind of thing the disease is (not the DB area), columns = the four
questions, cell = latest checker-corrected status in three colours (matched / never compared /
contradicted). A one-line bar above each column gives the column's split. Reads from matrix_cells.csv.
"""
import csv
import os
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
SURFACE, INK, MUTED, RULE = "#fcfcfb", "#1b2321", "#5c6763", "#c4cbc7"
COL = {"matched": "#256abf", "never": "#e4e3df", "contra": "#e34948", "empty": "#fcfcfb"}
Q = [("engagement", "Hits the target?"), ("dose", "Dose right?"), ("efficacy", "Disease responds?"), ("safety", "Harm predicted?")]

GROUPS = {
    "Cancer": ["Non-small cell lung carcinoma", "breast cancer", "Prostate cancer", "colorectal cancer", "acute myeloid leukemia",
               "Hepatocellular carcinoma", "Plasma cell myeloma", "malignant pancreatic neoplasm", "Ovarian cancer", "melanoma",
               "Glioblastoma", "Myelodysplastic syndrome", "Gastric cancer", "Small cell lung carcinoma", "follicular lymphoma"],
    "Infection": ["HIV infectious disease", "chronic hepatitis B virus infection", "hepatitis C virus infection", "influenza"],
    "Heart and vessels": ["Atrial fibrillation", "Heart failure", "Hypertensive disorder", "coronary artery disorder"],
    "Metabolism and diabetes": ["Type 1 diabetes mellitus", "Type 2 diabetes mellitus", "obesity disorder", "Hyperlipidemia", "Hypertriglyceridemia",
                                "metabolic dysfunction-associated steatohepatitis", "Prader-Willi syndrome", "diabetic kidney disease",
                                "diabetic neuropathy", "Secondary hyperparathyroidism"],
    "Immune and inflammatory": ["Rheumatoid arthritis", "Psoriasis", "Crohn disease", "Ulcerative colitis", "Asthma",
                                "Chronic obstructive pulmonary disease", "Idiopathic pulmonary fibrosis", "allergic rhinitis",
                                "atopic conjunctivitis", "eosinophilic esophagitis", "atopic eczema", "acne", "Dry eye syndrome"],
    "Monogenic and blood": ["Hemophilia A", "hemophilia B", "Sickle cell disease", "Paroxysmal nocturnal hemoglobinuria", "cystic fibrosis"],
    "Brain and pain": ["Alzheimer disease", "Parkinson disease", "migraine disorder", "Major depressive disorder", "Schizophrenia",
                       "attention deficit-hyperactivity disorder", "Insomnia", "osteoarthritis", "interstitial cystitis"],
    "Eye": ["age-related macular degeneration", "diabetic macular edema", "Open-angle glaucoma"],
    "Gut and liver": ["Irritable bowel syndrome", "gastroesophageal reflux disease", "Primary biliary cholangitis"],
    "Urology and reproductive": ["overactive bladder", "benign prostatic hyperplasia", "premature ejaculation", "Endometriosis"],
}


def tri(s):
    if s in ("same", "neg", "other"):
        return "matched"
    if s == "contra":
        return "contra"
    if s == "untested":
        return "never"
    return "empty"


def main():
    rows = [r for r in csv.DictReader(open(os.path.join(HERE, "matrix_cells.csv"))) if r["checked"] == "True"]
    by = defaultdict(dict); mech = {}; disease_of = {}
    for r in rows:
        by[r["context"]][r["question"]] = tri(r["status_checked"])
        mech[r["context"]] = r["mechanism"]; disease_of[r["context"]] = r["disease"]
    ctx_by_disease = defaultdict(list)
    for c, d in disease_of.items():
        ctx_by_disease[d].append(c)
    groups = {g: [c for d in ds for c in sorted(ctx_by_disease.get(d, []))] for g, ds in GROUPS.items()}
    placed = {c for cs in groups.values() for c in cs}
    missing = sorted(set(by) - placed)
    if missing:
        groups["Unplaced"] = missing
    GROUPS.clear(); GROUPS.update(groups)

    # order within group: most matched first, most contradicted last
    def key(d):
        c = Counter(by[d].values()); return (-c["matched"], c["contra"], disease_of[d].lower())
    order = []
    for g, ds in GROUPS.items():
        ds = [d for d in ds if d in by]
        order.append((g, sorted(ds, key=key)))

    n = sum(len(ds) for _, ds in order); ngroups = len(order)
    rh = 0.21; top_h = 2.7; fig_h = top_h + n * rh + ngroups * 0.3 + 0.8
    fig = plt.figure(figsize=(10.5, fig_h), dpi=200, facecolor=SURFACE)
    ax = fig.add_axes([0.5, 0.02, 0.48, 1 - (top_h + 0.1) / fig_h])
    ax.set_facecolor(SURFACE)
    y = 0
    ylabels = []
    for g, ds in order:
        ax.text(-0.02, y + 0.5, g.upper(), ha="right", va="center", fontsize=7.2, fontweight="bold", color=MUTED, transform=ax.transData)
        y += 1
        for d in ds:
            for j, (q, _) in enumerate(Q):
                s = by[d].get(q, "empty")
                ax.add_patch(Rectangle((j + 0.04, y + 0.06), 0.92, 0.88, facecolor=COL[s], edgecolor=SURFACE if s != "empty" else RULE,
                                       linewidth=0.6, linestyle="-" if s != "empty" else ":"))
            dis = disease_of[d]; m = (mech.get(d) or "").replace(" antibodies", " mAbs")
            dis = dis if len(dis) <= 30 else dis[:29] + "…"
            m = m if len(m) <= 26 else m[:25] + "…"
            ax.text(-0.02, y + 0.5, dis, ha="right", va="center", fontsize=7.2, color=INK)
            ax.text(-0.02, y + 0.5, m + "   " + " " * len(dis) * 2, ha="right", va="center", fontsize=5.6, color=MUTED, alpha=0) if False else None
            ax.text(-1.55, y + 0.5, m, ha="right", va="center", fontsize=6, color=MUTED)
            y += 1
        y += 0.4
    ax.set_xlim(0, 4); ax.set_ylim(y, 0)
    ax.set_xticks([]); ax.set_yticks([]); ax.tick_params(length=0)
    for sp in ax.spines.values(): sp.set_visible(False)

    # column splits above the grid
    tot = Counter(); split = {q: Counter(tri(r["status_checked"]) for r in rows if r["question"] == q) for q, _ in Q}
    bx = fig.add_axes([0.5, 1 - (top_h - 0.35) / fig_h, 0.48, 0.75 / fig_h]); bx.set_facecolor(SURFACE)
    for j, (q, _) in enumerate(Q):
        c = split[q]; N = sum(c.values()); x = j + 0.04; w = 0.92
        for s in ("matched", "never", "contra"):
            f = c[s] / N
            bx.add_patch(Rectangle((x, 0), w * f, 1, facecolor=COL[s], edgecolor=SURFACE, linewidth=0.8))
            if f > 0.09:
                bx.text(x + w * f / 2, 0.5, f"{100*f:.0f}%", ha="center", va="center", fontsize=7.5,
                        color=SURFACE if s != "never" else INK)
            x += w * f
    bx.set_xlim(0, 4); bx.set_ylim(0, 1); bx.set_xticks([]); bx.set_yticks([])
    for sp in bx.spines.values(): sp.set_visible(False)
    bx.text(-0.02, 0.5, f"all {n} contexts", ha="right", va="center", fontsize=7.5, color=MUTED, transform=bx.transData)
    for j, (_, t) in enumerate(Q):
        bx.text(j + 0.5, 1.25, t, ha="center", va="bottom", fontsize=8.5, color=INK, fontweight="bold", clip_on=False)

    fig.text(0.03, 1 - 0.28 / fig_h, "Did the preclinical model get it right?", fontsize=14, fontweight="bold", color=INK, va="top")
    fig.text(0.03, 1 - 0.62 / fig_h, f"{n} disease × drug-class contexts (industry Phase 2 entrants 2008–2019, most-developed novel class per "
             "indication). One cell per question:\nthe best model's latest record against patients, after a second reader checked every source.",
             fontsize=8, color=MUTED, va="top", linespacing=1.4)
    handles = [Patch(facecolor=COL["matched"], label="matched patients"), Patch(facecolor=COL["never"], label="never compared with patients"),
               Patch(facecolor=COL["contra"], label="contradicted by patients"),
               Patch(facecolor=SURFACE, edgecolor=RULE, linestyle=":", label="no model was used")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.03, 1 - 1.12 / fig_h), ncol=2, frameon=False, fontsize=7.5,
               handlelength=1.2, columnspacing=1.2)
    out = os.path.join(HERE, "summary_v2.png"); fig.savefig(out, facecolor=SURFACE); print(out)
    if missing:
        print("unplaced:", missing)


if __name__ == "__main__":
    main()
