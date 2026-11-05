"""The atlas at a glance as a journal figure, double-column (183 mm) in the Nature Portfolio format with the
Capable house palette (issue #76).

    .venv/bin/python analyses/model-system-atlas/glance_nature.py main          # atlas_glance_main.*
    .venv/bin/python analyses/model-system-atlas/glance_nature.py supplement    # atlas_glance_supplement_p*.*

main: the top 15 diseases by global DALYs in 2021 (lists/burden.csv), one tile each, the mechanism with the most
programs. supplement: every drafted tile, diseases in DALY order then the rest by area, paginated. Panel a (the
verdict by question) is over every drafted tile on both.

Same data and headline rule as glance.py (imported from it). No in-figure title: the caption in
atlas_glance_caption.md carries it. Panel a: the verdict by question. Panel b: one row per tile, one cell per
question; the mark is the status, the bold year is when it was earned, then the model; a failure or a
retrodiction carries its reason. Text is 5–7 pt Helvetica, lines 0.25–0.5 pt, fonts embedded editable.
Writes atlas_glance.png (300 dpi), .svg and .pdf beside this file. Read-only.
"""
import json
import os
import sys

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.textpath import TextPath

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from glance import QUESTIONS, SHORT, cells, load

# capable-plots: INK, CAPABLE (muted blue), PLACEBO (muted grey), VIBRANT coral and violet
INK, CAPABLE, PLACEBO = "#1a1a1a", "#83a9bc", "#b2b8b8"
MUTED, RULE, RULE_AREA = "#6b7372", "#dcdfdf", "#9aa1a1"
STATUS = {"same": (CAPABLE, "Matched"), "contra": ("#F0563D", "Contradicted"), "retro": ("#7C5CFC", "Retrodiction only"),
          "untested": ("#e2e5e5", "Never compared")}
AREA = {"infectious_disease": "Infectious disease", "other": "Other"}
# gutter labels for groups too short to carry the full name (a one-row group is 0.27 in)
AREA_SHORT = {"Infectious disease": "Inf.", "Metabolic": "Met.", "Ophthalmology": "Oph.", "Gastroenterology": "GI", "Hematology": "Hem.",
              "Psychiatry": "Psy.", "Respiratory": "Resp.", "Urology": "Uro.", "Autoimmune": "Aut.", "Endocrine": "End.", "Neurology": "Neu.",
              "Oncology": "Onc.", "Allergy": "All.", "Other": "Oth."}
RC = {"svg.hashsalt": "atlas", "hatch.linewidth": 0.6, "font.family": ["Helvetica", "Arial", "DejaVu Sans"], "svg.fonttype": "none", "pdf.fonttype": 42, "ps.fonttype": 42,
      "figure.facecolor": "white", "savefig.facecolor": "white", "text.color": INK}

W, H = 7.2, 9.65  # 183 × 245 mm

# Model names that do not fit their cell, shortened by hand; nothing is cut with an ellipsis
LABELS = os.path.join(HERE, "drafts", "v3", "short_labels.json")
with open(LABELS) as _f:
    _labels = json.load(_f)
MODEL_SHORT, DISSENT_SHORT = _labels["model"], _labels["dissent"]  # hand-shortened; see the file's _comment
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


PAGE_ROWS_FIRST, PAGE_ROWS_NEXT = 30, 33  # rows that fit under panel a, and on a page with only the column header


def order_tiles(df: pd.DataFrame, order: str, top: int | None = None, one_per_disease: bool = False) -> pd.DataFrame:
    """One row per tile. `area`: grouped by area, then disease and mechanism. `burden`: diseases by WHO DALY rank
    (lists/burden.csv), tiles within a disease by programs; the top N diseases when `top` is set; one tile per
    disease, the mechanism with the most programs, when `one_per_disease`; diseases without a rank follow, by area."""
    tiles = df.drop_duplicates("slug").copy()
    tiles["area_name"] = tiles.area.map(lambda a: AREA.get(a, a.capitalize()))
    tiles["area_order"] = tiles.area.map(lambda a: (a == "other", a))
    if order == "area":
        tiles["group"] = tiles.area_name
        return tiles.sort_values(["area_order", "disease", "mechanism"]).drop(columns=["area_order", "area_name"])
    burden = pd.read_csv(os.path.join(HERE, "lists", "burden.csv")).dropna(subset=["rank"])
    rank = dict(zip(burden.mondo_id, burden["rank"].astype(int)))
    tiles["rank"] = tiles.mondo_id.map(rank)
    tiles = tiles.sort_values(["rank", "programs", "mechanism"], ascending=[True, False, True], na_position="last")
    if one_per_disease:
        tiles = tiles.drop_duplicates("mondo_id")
    ranked = tiles[tiles["rank"].notna()]
    if top:
        ranked = ranked[ranked["rank"] <= top]
    ranked = ranked.assign(group=ranked["rank"].map(lambda r: f"#{int(r)}"))
    rest = tiles[tiles["rank"].isna()].sort_values(["area_order", "disease", "mechanism"]).assign(group=lambda t: t.area_name)
    out = ranked if top else pd.concat([ranked, rest])
    return out.drop(columns=["area_order", "area_name"])


def draw(df: pd.DataFrame, out: str, order: str = "area", top: int | None = None, one_per_disease: bool = False, note: str = "") -> list[str]:
    """Panel a over every drafted tile; panel b over the ordered selection, paginated. Returns the files written."""
    plt.rcParams.update(RC)
    tiles = order_tiles(df, order, top, one_per_disease)
    n_all = df.slug.nunique()
    pages, start = [], 0
    while start < len(tiles):
        n = PAGE_ROWS_FIRST if not pages else PAGE_ROWS_NEXT
        pages.append(tiles.iloc[start:start + n])
        start += n
    written = []
    for pi, page in enumerate(pages):
        first = pi == 0
        H_page = H if len(pages) > 1 else min(H, (1.46 if first else 0.62) + ROW * len(page) + 0.12)
        fig = plt.figure(figsize=(W, H_page), dpi=300)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, W)
        ax.set_ylim(H_page, 0)
        ax.axis("off")
        T = {"va": "center", "color": INK}
        if first:
            draw_verdict(ax, df, n_all, T)
            if note:
                ax.text(0.08, 1.1, note, fontsize=5.5, color=MUTED, va="center")
        top_y = 1.2 if first else 0.2
        ax.text(0.08, top_y, "b" if first else "", fontsize=8, fontweight="bold", **T)
        if len(pages) > 1:
            ax.text(W - 0.08, top_y, f"page {pi + 1} of {len(pages)}", fontsize=5.5, color=MUTED, ha="right", va="center")
        draw_rows(ax, df, page, top_y, T)
        suffix = f"_p{pi + 1}" if len(pages) > 1 else ""
        meta = {"Date": None}  # no timestamp, so a re-render of the same data is byte-identical
        fig.savefig(out + suffix + ".png", dpi=300, metadata=meta)
        fig.savefig(out + suffix + ".svg", metadata=meta)
        fig.savefig(out + suffix + ".pdf", metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)
        written.append(out + suffix)
    return written


def draw_verdict(ax, df: pd.DataFrame, n_tiles: int, T: dict) -> None:
    """Panel a: the verdict by question over every drafted tile, with the legend."""
    ax.text(0.08, 0.2, "a", fontsize=8, fontweight="bold", **T)
    bx0, bw, by0, bh, bgap = 1.2, 3.75, 0.3, 0.115, 0.05
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
    ax.text(bx0, by0 + 4 * (bh + bgap) + 0.03, f"of {n_tiles} drafted tiles", fontsize=5, color=MUTED, va="center")
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


def draw_rows(ax, df: pd.DataFrame, tiles: pd.DataFrame, top: float, T: dict) -> None:
    """Panel b on one page: the column header, then one row per tile, grouped in the gutter by `group`."""
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
    for g in tiles.group.unique():
        rows = tiles[tiles.group == g]
        ya = y
        for k, t in enumerate(rows.itertuples()):
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
        name = str(g)
        if width_in(name, 5) > (y - ya) - 0.06:
            name = AREA_SHORT.get(name, name)
        ax.plot([area_x + 0.05, area_x + 0.05], [ya + 0.03, y - 0.03], color=RULE_AREA, linewidth=0.5)
        ax.text(area_x - 0.02, (ya + y) / 2, name, fontsize=5, color=MUTED, rotation=90, ha="center", va="center")
        ax.plot([label_x, W - 0.06], [y, y], color=RULE_AREA, linewidth=0.5)


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="The atlas at a glance as a journal figure: the main cut or the full supplement.")
    p.add_argument("figure", choices=["main", "supplement"],
                   help="main: the top 15 diseases by WHO 2021 DALYs, one tile each (the mechanism with the most programs); "
                        "supplement: every drafted tile, diseases by DALY rank, then those without a WHO cause by area")
    p.add_argument("--top", type=int, default=15, help="main: how many diseases")
    a = p.parse_args()
    e, tiles = load()
    df = cells(e, tiles)
    if a.figure == "main":
        note = (f"Panel b: the top {a.top} diseases by global DALYs in 2021 (WHO Global Health Estimates), "
                "each with the mechanism that had the most programs; drafted tiles only.")
        written = draw(df, os.path.join(HERE, "atlas_glance_main"), order="burden", top=a.top, one_per_disease=True, note=note)
    else:
        note = "Panel b: every drafted tile; diseases by global DALYs in 2021 (WHO Global Health Estimates), then those without a WHO cause by area."
        written = draw(df, os.path.join(HERE, "atlas_glance_supplement"), order="burden", note=note)
    print(f"{len(written)} page(s): " + ", ".join(os.path.basename(w) for w in written) + f"; {len(CUT)} strings cut" + "".join("\n  " + c for c in CUT))


if __name__ == "__main__":
    main()
