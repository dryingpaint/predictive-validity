"""The atlas at a glance: for each drafted tile and each question, the status of the cell's headline model at its
latest comparison, the year it earned it, and the reason when it failed (issue #76).

    .venv/bin/python analyses/model-system-atlas/glance.py

Reads preclin.atlas_track_entry with its verdicts (the adjudicated status where an adjudicator decided) and
applies report_page.headline, the rule of decision 6: a cell's headline is the best latest status among its
tracks, one per model, that predicted before the patient result; untested when none did; a retrodiction never
sets it. The entry drawn is the latest on the track that set the headline. When a cell is split by modality
the worst strip is shown. A cell whose only tracks are retrodictions is drawn as "retrodiction only". A track
whose latest status is contradicted while the headline is matched is the cell's dissent. Writes glance.png /
.svg and glance.csv beside this file. Read-only.
"""
import json
import os
import sys

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from report import frame  # noqa: E402
from report_page import final_status, headline  # noqa: E402

V3 = os.path.join(HERE, "drafts", "v3")
QUESTIONS = [("engagement", "Target engagement", "Does the drug hit its target?"), ("dose", "Dose", "How much drug is needed?"),
             ("efficacy", "Efficacy", "Will the disease respond?"), ("safety", "Safety", "Will people be harmed?")]
# the report page's palette; neg and other do not occur in the v3 entries
STATUS = {"same": ("#1f86c8", "Matched"), "contra": ("#d13b1f", "Contradicted"),
          "untested": ("#dfe4e0", "Never compared"), "retro": ("#8a5cc8", "Retrodiction only")}
WORST = ["contra", "neg", "same", "other", "retro", "untested"]
MATCHED = {"same", "neg", "other"}
INK, MUTED, RULE, BAND, SURFACE = "#17201d", "#5a6662", "#d6dcd8", "#f5f6f3", "#ffffff"
AREA = {"infectious_disease": "infectious disease"}
SHORT = {"metabolic dysfunction-associated steatohepatitis": "MASH", "paroxysmal nocturnal hemoglobinuria": "PNH",
         "gastroesophageal reflux disease": "GERD", "non-small cell lung carcinoma": "NSCLC",
         "hepatitis C virus infection": "hepatitis C", "HIV infectious disease": "HIV", "plasma cell myeloma": "multiple myeloma",
         "acute myeloid leukemia": "acute myeloid leukaemia"}


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    e = frame.query("""SELECT e.mondo_id, e.mechanism_key, e.question, coalesce(e.modality, '') AS modality, e.seq, e.year, e.status,
                              e.model_id, e.model, e.src_label, e.retrodiction, e.fields, v.adjudicated_status
                       FROM preclin.atlas_track_entry e
                       LEFT JOIN preclin.atlas_track_verdict v USING (mondo_id, mechanism_key, question, modality, seq)""")
    e["fields"] = e.fields.map(lambda f: f or {})
    e["final"] = [final_status({"status": st, "adjudicated_status": adj if isinstance(adj, str) else None})
                  for st, adj in zip(e.status, e.adjudicated_status)]
    e["short"] = e.fields.map(lambda f: f.get("short"))
    tiles = pd.DataFrame(json.load(open(os.path.join(V3, "tiles.json"))))
    return e, tiles


def strip(g: pd.DataFrame) -> tuple[str, dict, dict]:
    """One modality strip: its headline status, the entry that set it, and each track's latest entry."""
    ents = g.to_dict("records")
    st = headline(ents, lambda x: x["final"])
    last = {}
    for x in sorted(ents, key=lambda x: (x["year"], x["seq"])):
        if x["final"] != "drop":
            last[x["model_id"]] = x
    cand = [x for x in last.values() if x["final"] == st] or list(last.values())
    pick = max(cand, key=lambda x: (x["year"], x["seq"]))
    if st == "untested" and last and all(x["final"] == "retro" for x in last.values()):
        st = "retro"
    return st, pick, last


def headline_entry(cell: pd.DataFrame) -> tuple[str, dict, dict] | None:
    """The cell's headline across its modality strips: the worst strip, with every track behind the cell."""
    if cell.empty:
        return None
    strips = [strip(g) for _, g in cell.groupby("modality")]
    st, pick, _ = sorted(strips, key=lambda t: WORST.index(t[0]))[0]
    last = {k: v for _, _, lst in strips for k, v in lst.items()}
    return st, pick, last


def cells(e: pd.DataFrame, tiles: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for t in tiles.itertuples():
        for q, _, _ in QUESTIONS:
            c = e[(e.mondo_id == t.mondo_id) & (e.mechanism_key == t.mechanism_key) & (e.question == q)]
            h = headline_entry(c)
            st, pick, last = h if h else (None, {}, {})
            contra = [x for x in last.values() if x["final"] == "contra"] if st in MATCHED else []
            dissent = max(contra, key=lambda x: (x["year"], x["seq"])) if contra else None
            rows.append({"slug": t.slug, "area": t.area, "disease": t.disease, "mechanism": t.mechanism, "programs": t.class_programs,
                         "share": t.class_share, "question": q, "status": st, "year": pick.get("year"), "model": pick.get("model"),
                         "short": pick.get("short"), "tracks": len(last), "other_tracks": max(len(last) - 1, 0),
                         "derived": pick.get("fields", {}).get("derived_from"), "outcome_tested": pick.get("fields", {}).get("outcome_tested"),
                         "dissent": None if dissent is None else dissent["short"], "dissent_model": None if dissent is None else dissent["model"]})
    df = pd.DataFrame(rows)
    df["year"] = df.year.astype("Int64")
    return df


def trim(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def draw(df: pd.DataFrame, out: str) -> None:
    order = sorted(set(df.area), key=lambda a: (a == "other", a))
    tiles = df.drop_duplicates("slug").sort_values(["area", "disease", "mechanism"])
    ROW, HEAD, TOP, BOTTOM, W = 0.37, 0.3, 3.08, 0.62, 12.6
    fig_h = TOP + sum(HEAD + ROW * (tiles.area == a).sum() for a in order) + BOTTOM
    fig = plt.figure(figsize=(W, fig_h), dpi=200)
    fy = lambda inches: 1 - inches / fig_h  # noqa: E731
    fx = lambda inches: inches / W  # noqa: E731

    fig.text(fx(0.25), fy(0.3), "Did the model the field relied on predict what happened in patients?", fontsize=15, fontweight="bold",
             color=INK, va="top")
    fig.text(fx(0.25), fy(0.62),
             f"{len(tiles)} mechanisms in {tiles.disease.nunique()} diseases, the v3 re-draft. For each question: the cell's headline status, the best "
             "among its model tracks that predicted before the patient result, and the year it was earned.\nIn each cell: that year and the model; "
             "a failure carries its reason on a second line, a retrodiction what it reproduced.\nOther model systems, modality splits and the full "
             "timelines are in the appendix and the interactive atlas.",
             fontsize=8.4, color=MUTED, va="top", linespacing=1.45)

    # summary: one bar per question
    sx0, sw, sy0, sh = 1.55, 4.6, 1.36, 0.19
    fig.text(fx(0.25), fy(sy0 - 0.12), "The verdict, by question", fontsize=8.6, fontweight="bold", color=INK, va="bottom")
    ax = fig.add_axes([fx(sx0), fy(sy0 + 4 * (sh + 0.07)), fx(sw), (4 * (sh + 0.07)) / fig_h])
    ax.set_xlim(0, len(tiles))
    ax.set_ylim(4 * (sh + 0.07), 0)
    ax.axis("off")
    for i, (q, title, _) in enumerate(QUESTIONS):
        y = i * (sh + 0.07)
        fig.text(fx(sx0 - 0.08), fy(sy0 + y + sh / 2), title, fontsize=7.6, color=INK, ha="right", va="center")
        x = 0.0
        d = df[df.question == q]
        for st in ["same", "contra", "retro", "untested"]:
            n = int((d.status == st).sum())
            if n:
                ax.add_patch(Rectangle((x + 0.06, y), n - 0.12, sh, facecolor=STATUS[st][0], edgecolor="none"))
                if n >= 2:
                    ax.text(x + n / 2, y + sh / 2, str(n), fontsize=6.6, ha="center", va="center",
                            color="white" if st in ("same", "contra", "retro") else INK)
                x += n
        blank = int(d.status.isna().sum())
        if blank:
            ax.add_patch(Rectangle((x + 0.06, y), blank - 0.12, sh, facecolor="none", edgecolor=RULE, linewidth=0.6))
            ax.text(x + blank / 2, y + sh / 2, str(blank), fontsize=6.6, ha="center", va="center", color=MUTED)
    # legend
    lx, ly = sx0 + sw + 0.45, sy0
    lg = fig.add_axes([fx(lx), fy(ly + 1.0), fx(2.2), 1.0 / fig_h])
    lg.set_xlim(0, 2.2)
    lg.set_ylim(1.0, 0)
    lg.axis("off")
    for i, st in enumerate(["same", "contra", "retro", "untested"]):
        lg.add_patch(FancyBboxPatch((0, i * 0.2 + 0.03), 0.13, 0.13, boxstyle="round,pad=0,rounding_size=0.025", facecolor=STATUS[st][0], edgecolor="none"))
        lg.text(0.22, i * 0.2 + 0.095, STATUS[st][1], fontsize=7.6, color=INK, va="center")
    lg.add_patch(Rectangle((0, 4 * 0.2 + 0.03), 0.13, 0.13, facecolor="none", edgecolor=RULE, linewidth=0.6))
    lg.text(0.22, 4 * 0.2 + 0.095, "No model relied on", fontsize=7.6, color=INK, va="center")

    # grid
    label_w, cell_w, gap = 2.6, 2.28, 0.08
    x_cells = [0.25 + label_w + i * (cell_w + gap) for i in range(4)]
    body = fig.add_axes([0, fy(fig_h - BOTTOM), 1, (fig_h - TOP - BOTTOM) / fig_h])
    body.set_xlim(0, W)
    body.set_ylim(fig_h - TOP - BOTTOM, 0)
    body.axis("off")
    for i, (q, title, question) in enumerate(QUESTIONS):
        body.text(x_cells[i], -0.3, title, fontsize=9.6, fontweight="bold", color=INK, va="bottom")
        body.text(x_cells[i], -0.13, question, fontsize=7.4, color=MUTED, va="bottom")
    y = 0.0
    for a in order:
        y += HEAD
        body.text(0.25, y - 0.1, AREA.get(a, a).replace("_", " ").capitalize(), fontsize=9.4, fontweight="bold", color=INK, va="center")
        body.plot([0.25, W - 0.25], [y, y], color=RULE, linewidth=0.6)
        for k, t in enumerate(tiles[tiles.area == a].itertuples()):
            y0, y1 = y, y + ROW
            if k % 2 == 0:
                body.add_patch(Rectangle((0.25, y0), W - 0.5, ROW, facecolor=BAND, edgecolor="none", zorder=0))
            body.text(0.3, y0 + 0.11, SHORT.get(t.disease, t.disease), fontsize=8, fontweight="bold", color=INK, va="center")
            body.text(0.3, y0 + 0.235, t.mechanism, fontsize=7.4, color=INK, va="center")
            body.text(0.3 + label_w - 0.14, y0 + 0.11, f"{t.programs} programs · {t.share:.0%}", fontsize=6.4, color=MUTED, va="center", ha="right")
            for i, (q, _, _) in enumerate(QUESTIONS):
                c = df[(df.slug == t.slug) & (df.question == q)].iloc[0]
                x = x_cells[i]
                if c.status is None or pd.isna(c.status):
                    body.add_patch(Rectangle((x, y0 + 0.11), 0.13, 0.13, facecolor="none", edgecolor=RULE, linewidth=0.6))
                    body.text(x + 0.2, y0 + 0.175, "no model relied on", fontsize=6.4, color=MUTED, va="center")
                    continue
                body.add_patch(FancyBboxPatch((x, y0 + 0.11), 0.13, 0.13, boxstyle="round,pad=0,rounding_size=0.025",
                                              facecolor=STATUS[c.status][0], edgecolor="none"))
                first_only = c.status in ("same", "untested")
                ty = y0 + 0.175 if first_only else y0 + 0.115
                body.text(x + 0.2, ty, f"{c.year}", fontsize=6.9, fontweight="bold", color=INK, va="center")
                body.text(x + 0.2 + 0.33, ty, trim(c.model or "", 31), fontsize=6.6, color=MUTED, va="center")
                if not first_only:
                    body.text(x + 0.2, y0 + 0.255, trim(c.short or "", 44), fontsize=6.6, color=INK, va="center")
            y = y1
    n = len(df[df.status.notna()])
    fig.text(fx(0.25), fy(fig_h - 0.16),
             f"{len(tiles)} tiles × 4 questions = {len(df)} cells; {n} have a model. Headline = the best latest status among the cell's tracks "
             f"that predicted before the patient result (decision 6), worst strip when split by modality; adjudicated statuses.\n"
             f"{int(df.other_tracks.sum())} further model-system tracks across {int((df.other_tracks > 0).sum())} cells are not drawn here. "
             "Source: preclin.atlas_track_entry, drafts/v3.",
             fontsize=6.8, color=MUTED, va="bottom", linespacing=1.4)
    fig.savefig(out + ".png", facecolor="white")
    fig.savefig(out + ".svg", facecolor="white")
    plt.close(fig)


def main() -> None:
    e, tiles = load()
    df = cells(e, tiles)
    df.to_csv(os.path.join(HERE, "glance.csv"), index=False)
    draw(df, os.path.join(HERE, "glance"))
    print(pd.crosstab(df.question, df.status.fillna("blank")).to_string())
    print(f"dissent cells {int(df.dissent.notna().sum())}; outcome negative {int((df.outcome_tested == 'negative').sum())}; "
          f"derived dose contras {int(((df.question == 'dose') & (df.status == 'contra') & (df.derived == 'efficacy')).sum())}")


if __name__ == "__main__":
    main()
