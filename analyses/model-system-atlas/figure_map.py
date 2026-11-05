"""Draw the model-system map: the Phase 2 pipeline as a treemap, one box per indication sized by programs
entering Phase 2 in 2008–2019 and coloured by the track record of its most-developed drug class's best
model for efficacy. Each area's long tail is one box, filled later from the program sample.

    .venv/bin/python analyses/model-system-atlas/figure_map.py

Reads volumes_pre_rebuild.json (indication volumes from the database, before the #70 rebuild) and
contexts/*.json (track records researched so far; indications without one are drawn as not yet researched).
"""

import json
import os

import matplotlib.pyplot as plt
from figure import load, spans
from matplotlib.patches import Patch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
TRACK = {
    "neg": ("#0b5f69", "Matched patients, including a known failure"),
    "same": ("#3d9ea6", "Matched patients, same mechanism"),
    "other": ("#a9d6d9", "Matched patients, other mechanism only"),
    "untested": ("#d9dcd9", "Never compared with patients"),
    "contra": ("#c63d26", "Contradicted by patients"),
}
TODO = "#f1f2f0"
INK, MUTED = "#1b2321", "#5c6763"
AREA_NAMES = {"infectious_disease": "Infectious disease"}


def squarify(values, x, y, w, h):
    """Squarified treemap layout: one (x, y, w, h) per value, values sorted descending."""
    total = sum(values)
    values = [v * w * h / total for v in values]
    rects, row = [], []

    def worst(r, side):
        s = sum(r)
        return max(max(side * side * v / (s * s), (s * s) / (side * side * v)) for v in r)

    def lay(r, x, y, w, h):
        s = sum(r)
        if w >= h:
            cw = s / h
            yy = y
            for v in r:
                rects.append((x, yy, cw, v / cw)); yy += v / cw
            return x + cw, y, w - cw, h
        ch = s / w
        xx = x
        for v in r:
            rects.append((xx, y, v / ch, ch)); xx += v / ch
        return x, y + ch, w, h - ch

    for v in values:
        side = min(w, h)
        if not row or worst(row + [v], side) <= worst(row, side):
            row.append(v)
        else:
            x, y, w, h = lay(row, x, y, w, h)
            row = [v]
    if row:
        lay(row, x, y, w, h)
    return rects


def efficacy_status(rows):
    """Latest efficacy status per MONDO id, from researched contexts (seed: one context per disease)."""
    out = {}
    for r in rows:
        hist = r["cells"].get("efficacy", [])
        if hist and r.get("mondo_id"):
            out.setdefault(r["mondo_id"], (spans(hist)[-1][2], r["mechanism"]))
    return out


def main():
    areas = json.load(open(os.path.join(HERE, "volumes_pre_rebuild.json")))
    status = efficacy_status(load())
    for a in areas:
        a["total"] = sum(i["n"] for i in a["indications"]) + a["rest"]
    areas.sort(key=lambda a: -a["total"])
    grand = sum(a["total"] for a in areas)
    shown = sum(sum(i["n"] for i in a["indications"]) for a in areas)

    W, H = 15, 10.5
    fig = plt.figure(figsize=(W, H + 1.9), dpi=200)
    fig.text(0.012, 0.985, "How much of the pipeline rests on a model that has matched patients", fontsize=17, fontweight="bold", color=INK, va="top")
    fig.text(0.012, 0.955, f"Programs entering Phase 2 in 2008–2019 ({grand:,}), one box per disease sized by programs, coloured by the efficacy track record "
             "of its most-developed drug class's best model.\nEach area's remaining diseases form one box, filled from a random sample of programs. "
             f"Named diseases cover {shown / grand:.0%} of entries.", fontsize=9.5, color=MUTED, va="top", linespacing=1.4)
    handles = [Patch(facecolor=c, edgecolor="none", label=l) for c, l in TRACK.values()]
    handles.append(Patch(facecolor=TODO, edgecolor="#c4cbc7", label="Not yet researched"))
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.008, 0.915), ncol=6, frameon=False, fontsize=8.6,
               handlelength=1.4, handleheight=0.9, columnspacing=1.2, labelcolor=INK)

    ax = fig.add_axes([0.012, 0.012, 0.976, H / (H + 1.9) - 0.01])
    ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
    for a, (ax0, ay0, aw, ah) in zip(areas, squarify([a["total"] for a in areas], 0, 0, W, H)):
        pad = 0.04
        name = AREA_NAMES.get(a["area"], a["area"].capitalize())
        head = 0.24 if ah > 0.7 and aw > 1.0 else 0
        ax.add_patch(Rectangle((ax0, ay0), aw, ah, facecolor="white", edgecolor="white", lw=2))
        if head:
            ax.text(ax0 + 0.06, ay0 + 0.13, f"{name}  {a['total']:,}", fontsize=8.6 if aw > 2 else 7, fontweight="bold", color=INK, va="center")
        items = [(i["n"], i) for i in a["indications"]] + [(a["rest"], None)]
        items.sort(key=lambda t: -t[0])
        for (n, ind), (x, y, w, h) in zip(items, squarify([t[0] for t in items], ax0 + pad, ay0 + head + pad, aw - 2 * pad, ah - head - 2 * pad)):
            if ind is None:
                ax.add_patch(Rectangle((x, y), w, h, facecolor=TODO, edgecolor="white", lw=1.2, hatch="////"))
                label, sub, ink = f"{len_rest(a)} other diseases", f"{n:,} programs · from sample", MUTED
            else:
                st = status.get(ind["mondo_id"])
                face = TRACK[st[0]][0] if st else TODO
                ax.add_patch(Rectangle((x, y), w, h, facecolor=face, edgecolor="white", lw=1.2))
                label = ind["label"][0].upper() + ind["label"][1:]
                sub = f"{n:,}" + (f" · {st[1]}" if st else "")
                ink = "white" if st and st[0] in ("neg", "same", "contra") else INK
            if w > 0.55 and h > 0.28:
                fs = 7.2 if w > 1.1 else 6
                ax.text(x + 0.05, y + 0.07, wrap(label, w, fs), fontsize=fs, color=ink, va="top", linespacing=1.1)
                if h > 0.55:
                    ax.text(x + 0.05, y + h - 0.06, wrap(sub, w, 5.8), fontsize=5.8, color=ink, va="bottom", alpha=0.9)

    out = os.path.join(HERE, "map.png")
    fig.savefig(out, facecolor="white")
    print(out)


def len_rest(a):
    return a.get("n_rest_indications", "All")


def wrap(text, width_in, fs):
    per_line = max(6, int(width_in * 72 / (fs * 0.56)))
    words, lines, cur = text.split(), [], ""
    for wd in words:
        if len(cur) + len(wd) + 1 > per_line and cur:
            lines.append(cur); cur = wd
        else:
            cur = (cur + " " + wd).strip()
    lines.append(cur)
    return "\n".join(lines[:3])


if __name__ == "__main__":
    main()
