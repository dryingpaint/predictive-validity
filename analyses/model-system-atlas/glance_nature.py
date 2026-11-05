"""The atlas at a glance as a journal figure: a full-page, double-column (183 × 247 mm) version of glance.py in
the Nature Portfolio format, with the Capable house palette (issue #76).

    .venv/bin/python analyses/model-system-atlas/glance_nature.py

Same data and headline rule as glance.py (imported from it). No in-figure title: the caption in
atlas_glance_caption.md carries it. Panel a: the verdict by question. Panel b: one row per tile, one cell per
question; the mark is the status, the bold year is when it was earned, then the model; a failure or a
retrodiction carries its reason. Text is 5–7 pt Helvetica, lines 0.25–0.5 pt, fonts embedded editable.
Writes atlas_glance.png (300 dpi), .svg and .pdf beside this file. Read-only.
"""
import os
import sys

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402
from matplotlib.textpath import TextPath  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from glance import QUESTIONS, SHORT, cells, load  # noqa: E402

# capable-plots: INK, CAPABLE (muted blue), PLACEBO (muted grey), VIBRANT coral and violet
INK, CAPABLE, PLACEBO = "#1a1a1a", "#83a9bc", "#b2b8b8"
MUTED, RULE, RULE_AREA = "#6b7372", "#dcdfdf", "#9aa1a1"
STATUS = {"same": (CAPABLE, "Matched"), "contra": ("#F0563D", "Contradicted"), "retro": ("#7C5CFC", "Retrodiction only"),
          "untested": ("#e2e5e5", "Never compared")}
AREA = {"infectious_disease": "Infectious disease", "other": "Other"}
AREA_SHORT = {"Infectious disease": "Infectious", "Metabolic": "Metab.", "Ophthalmology": "Ophth.", "Gastroenterology": "GI", "Hematology": "Hemat."}
RC = {"hatch.linewidth": 0.6, "font.family": ["Helvetica", "Arial", "DejaVu Sans"], "svg.fonttype": "none", "pdf.fonttype": 42, "ps.fonttype": 42,
      "figure.facecolor": "white", "savefig.facecolor": "white", "text.color": INK}

W, H = 7.2, 9.65  # 183 × 245 mm

# Model names that do not fit their cell, shortened by hand; nothing is cut with an ellipsis
MODEL_SHORT = {
    "Human atrial cardiomyocyte IKACh (GIRK) patch clamp": "Human atrial myocytes",
    "2-year rat carcinogenicity bioassay": "2-year rat carcinogenicity",
    "tg-ArcSwe mice given mAb158, lecanemab's murine version": "tg-ArcSwe mice, mAb158",
    "hAPP(V717I)/PS1 mice and microglia assays with crenezumab": "hAPP/PS1 mice, crenezumab",
    "Rat, mouse and monkey GLP toxicology (MK-3207)": "Rat, mouse, monkey GLP tox",
    "Rhesus CIDV exposure target, translated to human CIDV PK/PD": "Rhesus CIDV PK/PD target",
    "MV4-11 xenografts, gilteritinib plus azacitidine": "MV4-11 AML xenografts",
    "hERG assay with rat and dog toxicology and dog cardiovascular telemetry": "hERG, rat and dog tox, dog telemetry",
    "Rodent antipsychotic-like dose and occupancy": "Rodent occupancy dosing",
    "Patient F508del bronchial cells (Ussing chamber)": "Patient F508del airway cells",
    "Rat and dog toxicology (vanzacaftor)": "Rat and dog tox (vanzacaftor)",
    "Human eosinophil DP2 potency scaled to human exposure": "Eosinophil DP2 potency",
    "Mouse chronic asthma with rhinovirus exacerbation, on corticosteroid": "Asthma mice on steroid",
    "Chemical cystitis in rats/mice with NGF sequestration": "Rodent chemical cystitis",
    "Primate, rat and mouse toxicology with bone and joint histology": "Primate and rodent joint tox",
    "Primary human keratinocytes stimulated with IL-17 and TNF (synergistic gene set)": "Human keratinocytes stimulated with IL-17 and TNF",
    "Cynomolgus monkey repeat-dose toxicology (only cross-reactive species)": "Cynomolgus repeat-dose toxicology",
    "Psoriasis patients' blood cells ex vivo (IL-17-secreting cells, sponsor report bTDR80)": "Psoriasis patients' blood cells ex vivo",
    "People with inborn errors of IL-17 immunity (IL-17RA, IL-17F deficiency)": "People with inborn errors of IL-17 immunity",
    "Human whole-blood ex vivo IL-17 secretion assay (IC90 target), VTP-43742/AGN-242428": "Human whole-blood IL-17 secretion assay",
    "Histamine- and pentagastrin-stimulated gastric acid secretion in dogs": "Stimulated gastric acid secretion in dogs",
    "Rat reflux-oesophagitis model (esophageal injury and acid secretion), vs esomeprazole": "Rat reflux oesophagitis vs esomeprazole",
    "Rat 1-4 week repeat dosing: gastrin, gastric emptying, small-intestinal microbiota": "Rat repeat dosing: gastrin, emptying, microbiota",
    "Hemophilia B dogs given liver-directed AAV8-canine FIX-Padua (R338L)": "Hemophilia B dogs, AAV8 canine FIX-Padua",
    "Juvenile hemophilia B dogs given the canine surrogate AAVRh74var-cFIX-R338L": "Juvenile hemophilia B dogs, canine surrogate vector",
    "Cynomolgus monkey PK/PD (crovalimab cross-reacts with monkey C5)": "Cynomolgus PK/PD (crovalimab)",
    "In-vitro complement hemolysis assay in human serum (no animal model of PNH)": "Complement hemolysis assay in human serum",
    "In-vitro drug-target-drug complex formation (crovalimab + eculizumab + human C5)": "Drug–target–drug complex assay, human C5",
    "Human CETP/apoA-I transgenic mouse; rat blood pressure": "CETP/apoA-I mouse; rat blood pressure",
    "Aged APP transgenic mice given 2H6, ponezumab's murine parent": "Aged APP mice given 2H6 (ponezumab parent)",
    "Abemaciclib xenograft PK/PD model (phospho-Rb to tumour growth)": "Abemaciclib xenograft PK/PD (pRb to growth)",
    "T790M/sensitising-mutant NSCLC cells, xenografts and transgenic mice": "T790M/sensitising-mutant NSCLC cells and mice",
    "Human tumour cells and xenografts treated with h7C10 (dalotuzumab)": "Tumour cells and xenografts given h7C10",
    "BCMA+ human myeloma xenografts in immunodeficient (NSG) mice, CAR-T": "BCMA+ myeloma xenografts in NSG mice, CAR-T",
    "BCMA+ human myeloma xenografts in immunodeficient mice, ADC": "BCMA+ myeloma xenografts in mice, ADC",
    "Dog repeat dosing with food-enrichment cataplexy trigger (suvorexant)": "Dog repeat dosing, cataplexy trigger (suvorexant)",
    "Cynomolgus monkeys given AAVRh74var-hFIX-Padua (fidanacogene predecessor), GLP toxicology": "Cynomolgus GLP tox, fidanacogene predecessor",
    "In-vitro hemolysis assay with recombinant C5 R885H variant (picks eculizumab-resistant genotype patients)": "Hemolysis assay with C5 R885H variant",
    "APP A673T protective variant carriers (Icelandic genetics)": "A673T variant carriers",
    "EGFR-mutant PC9 mouse brain-metastasis model with cynomolgus [11C]osimertinib microdose PET": "PC9 brain-metastasis mice; monkey osimertinib PET",
    "Cynomolgus monkey repeat-dose toxicology of R1507/teprotumumab": "Cynomolgus repeat-dose tox (R1507)",
    "Decision-tree / exposure-safety model of NOVA patients (niraparib individualized starting dose)": "NOVA exposure–safety model (niraparib)",
    "Healthy-volunteer ketamine challenge (fMRI BOLD/EEG)": "Ketamine challenge",
    "Inhaled allergen challenge in mild atopic asthmatics (late asthmatic response)": "Allergen challenge",
    "ASP6294 (PEG-Fab') vs anti-NGF IgG in adjuvant-arthritis mice and MIA-arthritis rats": "ASP6294 vs anti-NGF IgG in arthritic rodents",
    "High-fat-diet mouse ALT/cholesterol screen (Px-102-calibrated)": "High-fat-diet mouse ALT/cholesterol screen",
    "Human CETP loss-of-function genotypes (common variants, truncating variants)": "Human CETP loss-of-function genotypes",
    "Wild-type mice chronically dosed with BACE1 inhibitors (spines, LTP, behaviour)": "Mice chronically dosed with BACE1 inhibitors",
    "Mouse transient middle cerebral artery occlusion (gepant pretreatment)": "Mouse MCAO stroke, gepant pretreatment",
    "Ba/F3 FLT3-ITD saturation mutagenesis resistance screen (in vitro)": "Ba/F3 FLT3-ITD resistance screen",
    "Patient-derived lung cancer organoids from malignant effusions, drug sensitivity test": "Patient-derived lung cancer organoids",
    "Mouse emotion-induced (chocolate) cataplexy, wild-type vs preproorexin knockout (lemborexant)": "Mouse emotion-induced cataplexy (lemborexant)",
    "Fischer rat thyroid cells expressing CFTR variants (Ussing chamber)": "FRT cells expressing CFTR variants",
}
DISSENT_SHORT = {"Human NTD signal gone; mouse harm unconfirmed": "Mouse NTD; human signal gone",
                 "CNS exposure reached; response failed": "Brain exposure OK, no response",
                 "Engagement in explant; primary failed": "Explant engaged; primary failed",
                 "Clarity AD: excess microbleeds missed": "Excess microbleeds missed",
                 "Human exposure far below prediction": "Exposure far below prediction",
                 "Brain-metastasis trial misses iORR": "Brain-metastasis trial missed",
                 "No IL-17 biomarker change in treated plaques": "No IL-17 change in plaques",
                 "S1P3-sparing ozanimod still slows the heart": "Ozanimod still slows the heart",
                 "Cilofexor: no lipid change in humans": "Cilofexor: no lipid change",
                 "Animal tox silent on MK-3207 liver injury": "Animal tox missed MK-3207 liver",
                 "Gilteritinib + azacitidine: no survival gain": "Combination: no survival gain",
                 "Third corrector added nothing in patients": "Third corrector added nothing"}
CUT = []  # strings that still needed an ellipsis; printed at the end so none ships unnoticed
ROW = 0.27


def width_in(s: str, size: float, weight: str = "normal") -> float:
    """Rendered width of a string in inches, measured from the glyph outlines."""
    if not s:
        return 0.0
    fp = FontProperties(family=RC["font.family"], size=size, weight=weight)
    return TextPath((0, 0), s, size=size, prop=fp).get_extents().width / 72.0


def wrap(s: str, size: float, max_w: float, max_lines: int, first_w: float | None = None) -> list[str]:
    """Greedy word wrap to measured widths; the last allowed line is cut with an ellipsis if needed."""
    words, lines, cur = (s or "").split(), [], ""
    for w in words:
        limit = first_w if (first_w is not None and not lines) else max_w
        trial = (cur + " " + w).strip()
        if width_in(trial, size) <= limit or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if len(lines) < max_lines:
        lines.append(cur)
    rest = " ".join(words[sum(len(l.split()) for l in lines):])
    if rest:
        limit = max_w if len(lines) > 1 or first_w is None else first_w
        last = lines[-1]
        while last and width_in(last + "…", size) > limit:
            last = last[:-1].rstrip()
        lines[-1] = last + "…"
        CUT.append(s)
    return lines


def draw(df: pd.DataFrame, out: str) -> None:
    plt.rcParams.update(RC)
    tiles = df.drop_duplicates("slug").sort_values(["area", "disease", "mechanism"])
    order = sorted(set(tiles.area), key=lambda a: (a == "other", a))
    fig = plt.figure(figsize=(W, H), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    T = dict(va="center", color=INK)

    # ── panel a: the verdict by question ───────────────────────────────────────────
    ax.text(0.08, 0.2, "a", fontsize=8, fontweight="bold", **T)
    bx0, bw, by0, bh, bgap = 1.2, 3.75, 0.3, 0.115, 0.05
    n_tiles = len(tiles)
    for i, (q, title, _) in enumerate(QUESTIONS):
        y = by0 + i * (bh + bgap)
        ax.text(bx0 - 0.08, y + bh / 2, title, fontsize=6, ha="right", **T)
        d = df[df.question == q]
        x = 0.0
        for st, derived in [("same", False), ("contra", False), ("contra", True), ("retro", False), ("untested", False)]:
            sel = (d.status == st) & ((d.derived == "efficacy") if derived else (d.derived != "efficacy"))
            n = int(sel.sum())
            if not n:
                continue
            w = n / n_tiles * bw
            ax.add_patch(Rectangle((bx0 + x + 0.012, y), w - 0.024, bh, facecolor=STATUS[st][0], edgecolor="white" if derived else "none",
                                   linewidth=0, hatch="////" if derived else None))
            if w > 0.16:
                ax.text(bx0 + x + w / 2, y + bh / 2, str(n), fontsize=5.5, ha="center", **T)
            x += w
    ax.text(bx0, by0 + 4 * (bh + bgap) + 0.03, f"of {n_tiles} tiles", fontsize=5, color=MUTED, va="center")
    lx, ly = 5.35, by0 + 0.01
    items = [("same", False, "Matched"), ("contra", False, "Contradicted"), ("contra", True, "Contradicted through efficacy (dose)"),
             ("retro", False, "Retrodiction only"), ("untested", False, "Never compared")]
    items = [it for it in items if ((df.status == it[0]) & ((df.derived == "efficacy") if it[1] else (df.derived != "efficacy"))).any()]
    for i, (st, derived, label) in enumerate(items):
        yy = ly + i * 0.115
        ax.add_patch(FancyBboxPatch((lx, yy), 0.1, 0.1, boxstyle="round,pad=0,rounding_size=0.018", facecolor=STATUS[st][0],
                                    edgecolor="white" if derived else "none", linewidth=0, hatch="////" if derived else None))
        ax.text(lx + 0.16, yy + 0.05, label, fontsize=5.5, **T)
    yy = ly + len(items) * 0.115 + 0.015
    ax.add_patch(Rectangle((lx + 0.025, yy + 0.025), 0.05, 0.05, facecolor=STATUS["contra"][0], edgecolor="none"))
    ax.text(lx + 0.16, yy + 0.05, "Matched, but another model contradicted", fontsize=5.5, **T)
    yy += 0.115
    ax.add_patch(Rectangle((lx + 0.025, yy + 0.025), 0.05, 0.05, facecolor="white", edgecolor=INK, linewidth=0.5))
    ax.text(lx + 0.16, yy + 0.05, "Surrogate matched, outcome trial negative", fontsize=5.5, **T)

    # ── panel b: the tiles ─────────────────────────────────────────────────────────
    top = 1.2
    ax.text(0.08, top, "b", fontsize=8, fontweight="bold", **T)
    area_x, label_x, label_w = 0.1, 0.34, 1.36
    cell_x = [1.78 + i * 1.36 for i in range(4)]
    cell_w = 1.3
    for i, (q, title, _) in enumerate(QUESTIONS):
        ax.text(cell_x[i], top + 0.14, title, fontsize=6.5, fontweight="bold", **T)
    y = top + 0.26
    ax.plot([area_x, W - 0.06], [y, y], color=RULE_AREA, linewidth=0.5)
    mark, pad = 0.095, 0.05
    text_x = lambda i: cell_x[i] + mark + pad  # noqa: E731
    text_w = cell_w - mark - pad - 0.02
    for a in order:
        g = tiles[tiles.area == a]
        ya = y
        for k, t in enumerate(g.itertuples()):
            y0 = y
            if k:
                ax.plot([label_x, W - 0.06], [y0, y0], color=RULE, linewidth=0.25)
            ax.text(label_x, y0 + 0.065, SHORT.get(t.disease, t.disease), fontsize=6, fontweight="bold", **T)
            ax.text(label_x, y0 + 0.14, wrap(f"{t.mechanism} ({t.programs})", 5.5, label_w - 0.04, 1)[0], fontsize=5.5, **T)
            for i, (q, _, _) in enumerate(QUESTIONS):
                c = df[(df.slug == t.slug) & (df.question == q)].iloc[0]
                x = cell_x[i]
                if c.status is None or pd.isna(c.status):
                    ax.add_patch(Rectangle((x, y0 + 0.065 - mark / 2), mark, mark, facecolor="none", edgecolor=RULE_AREA, linewidth=0.4))
                    ax.text(text_x(i), y0 + 0.065, "no model relied on", fontsize=5, color=MUTED, va="center")
                    continue
                derived = c.status == "contra" and c.derived == "efficacy"
                ax.add_patch(FancyBboxPatch((x, y0 + 0.065 - mark / 2), mark, mark, boxstyle="round,pad=0,rounding_size=0.018",
                                            facecolor=STATUS[c.status][0], edgecolor="white" if derived else "none", linewidth=0,
                                            hatch="////" if derived else None))
                year = str(c.year)
                yw = width_in(year, 5.5, "bold") + 0.045
                L = (0.065, 0.135, 0.205)
                model = MODEL_SHORT.get(c.model or "", c.model or "")
                ax.text(text_x(i), y0 + L[0], year, fontsize=5.5, fontweight="bold", **T)
                reason = [] if c.status in ("same", "untested") else wrap(c.short or "", 5, text_w, 2)
                extra = int(c.status == "same" and (c.outcome_tested == "negative" or isinstance(c.dissent, str)))
                lines = wrap(model, 5, text_w, 3 - len(reason) - extra, first_w=text_w - yw)
                ax.text(text_x(i) + yw, y0 + L[0], lines[0], fontsize=5, color=MUTED, va="center")
                for j, line in enumerate(lines[1:], 1):
                    ax.text(text_x(i), y0 + L[j], line, fontsize=5, color=MUTED, va="center")
                for j, line in enumerate(reason, len(lines)):
                    ax.text(text_x(i), y0 + L[j], line, fontsize=5, **T)
                j = len(lines) + len(reason)
                if extra:
                    assert j < 3, (t.slug, q)
                    sq = (0.05, 0.05)
                    if c.outcome_tested == "negative":
                        ax.add_patch(Rectangle((text_x(i), y0 + L[j] - 0.025), *sq, facecolor="white", edgecolor=INK, linewidth=0.5))
                        note = "Outcome trial negative"
                    else:
                        ax.add_patch(Rectangle((text_x(i), y0 + L[j] - 0.025), *sq, facecolor=STATUS["contra"][0], edgecolor="none"))
                        note = DISSENT_SHORT.get(c.dissent, c.dissent)
                    ax.text(text_x(i) + 0.075, y0 + L[j], wrap(note, 5, text_w - 0.075, 1)[0], fontsize=5, **T)
            y += ROW
        # area: a vertical label and a bracket spanning its rows
        ax.plot([area_x + 0.05, area_x + 0.05], [ya + 0.03, y - 0.03], color=RULE_AREA, linewidth=0.5)
        name = AREA.get(a, a.capitalize())
        if width_in(name, 5) > (y - ya) - 0.08:
            name = AREA_SHORT.get(name, name)
        ax.text(area_x - 0.02, (ya + y) / 2, name, fontsize=5, color=MUTED, rotation=90, ha="center", va="center")
        ax.plot([label_x, W - 0.06], [y, y], color=RULE_AREA, linewidth=0.5)
    fig.savefig(out + ".png", dpi=300)
    fig.savefig(out + ".svg")
    fig.savefig(out + ".pdf")
    plt.close(fig)
    print(f"rows end at {y:.2f} in of {H} in; {len(CUT)} strings cut" + ("".join("\n  " + c for c in CUT)))


def main() -> None:
    e, tiles = load()
    df = cells(e, tiles)
    draw(df, os.path.join(HERE, "atlas_glance"))


if __name__ == "__main__":
    main()
