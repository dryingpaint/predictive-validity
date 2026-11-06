"""Atlas lessons: what a preclinical "yes" was worth, by family of model system (lessons/DESIGN.md).

    .venv/bin/python analyses/model-system-atlas/lessons/lessons.py families    # families.csv; fails on any unassigned track
    .venv/bin/python analyses/model-system-atlas/lessons/lessons.py rates       # family_rates.csv, family_rates_by_outcome.csv
    .venv/bin/python analyses/model-system-atlas/lessons/lessons.py engagement  # engagement_vs_efficacy.csv, dose_derived.csv
    .venv/bin/python analyses/model-system-atlas/lessons/lessons.py safety      # safety_misses.csv
    .venv/bin/python analyses/model-system-atlas/lessons/lessons.py robust      # robustness.md: intervals, tests, sensitivity, second coder
    .venv/bin/python analyses/model-system-atlas/lessons/lessons.py figure      # ../atlas_lessons.{png,pdf,svg}
    .venv/bin/python analyses/model-system-atlas/lessons/lessons.py all

Reads the store through glance.load() (read-only; adjudicated statuses), drafts/tiles.json and the hand-typed
inputs beside this file: overrides.csv (family), safety_types.csv (the 76 safety contras), dose_types.csv (the 60
dose contras derived from efficacy). Every tile reached Phase 2, so every rate here is what a positive prediction
was worth once the drug was in patients, never a sensitivity.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ATLAS = os.path.dirname(HERE)
sys.path.insert(0, ATLAS)
sys.path.insert(0, HERE)
import glance  # noqa: E402
from families import FAMILIES, family_of, load_overrides  # noqa: E402

COMPARED = {"same", "neg", "other", "contra"}
MATCHED = {"same", "neg", "other"}
QUESTIONS = ["engagement", "dose", "efficacy", "safety"]
SAFETY_TYPES = {"silent", "stated_safe", "false_alarm", "not_showable", "no_comparison"}
HARM_CLASSES = {"immune", "liver", "cardiovascular", "metabolic_endocrine_bone", "haematological", "gastrointestinal", "cns", "skin",
                "ocular", "respiratory", "renal", "musculoskeletal", "other"}
DOSE_REACHED = {"exposure", "occupancy", "pd_biomarker", "regimen"}
B, SEED, MIN_TILES = 2000, 76, 4
OUT = {k: os.path.join(HERE, f"{k}.csv") for k in ["families", "family_rates", "family_rates_by_outcome", "engagement_vs_efficacy",
                                                    "engagement_summary", "dose_derived", "safety_misses"]}
ROBUST = os.path.join(HERE, "robustness.md")
INPUTS = {k: os.path.join(HERE, f"{k}.csv") for k in ["overrides", "safety_types", "safety_types_coder1", "safety_types_coder2", "dose_types"]}


# ---------------------------------------------------------------- the track table
def prediction(question: str, final: str, derived_from) -> str:
    """What the track's model put forward: a yes (the disease, exposure or target will respond), a no (the model's own data
    fell below the class bar), a safety picture, or a dose verdict derived from efficacy (counted once, under efficacy)."""
    if question == "safety":
        return "safety"
    if question == "dose" and derived_from == "efficacy":
        return "derived"
    return "no" if final == "neg" else "yes"


def tracks(e: pd.DataFrame, tiles: pd.DataFrame) -> pd.DataFrame:
    """One row per (slug, question, modality, model_id): the latest non-drop entry's status and fields, the tile's area and
    outcome, every model text the track used (for the family rules), and the prediction direction."""
    e = e[e.final != "drop"].copy()
    e["modality"] = e.modality.fillna("")
    e = e.merge(tiles[["slug", "area", "mondo_id", "mechanism_key", "furthest_phase", "class_programs"]], on=["mondo_id", "mechanism_key"])
    key = ["slug", "question", "modality", "model_id"]
    e = e.sort_values(key + ["year", "seq"])
    last = e.groupby(key).tail(1).copy()
    f = pd.DataFrame(last.fields.tolist(), index=last.index)
    for c in ["model_kind", "derived_from", "readout_tier", "reason", "note", "magnitude", "product_in_model", "subjects"]:
        last[c] = f[c] if c in f else None
    last["texts"] = e.groupby(key).model.agg(lambda s: " | ".join(dict.fromkeys(str(x) for x in s))).reindex(
        pd.MultiIndex.from_frame(last[key])).to_numpy()
    last["compared"] = last.final.isin(COMPARED)
    last["matched"] = last.final.isin(MATCHED)
    last["approved"] = last.furthest_phase == 4
    last["pred"] = [prediction(q, s, d) for q, s, d in zip(last.question, last.final, last.derived_from)]
    return last.reset_index(drop=True)


def with_families(t: pd.DataFrame) -> pd.DataFrame:
    ov = load_overrides(INPUTS["overrides"])
    fam = [family_of(s, m, k, f"{x} {m}", ov) for s, m, k, x in zip(t.slug, t.model_id, t.model_kind.fillna(""), t.texts)]
    t = t.copy()
    t["family"], t["family_source"] = zip(*fam)
    return t


def load() -> pd.DataFrame:
    e, tiles = glance.load()
    return with_families(tracks(e, tiles))


# ---------------------------------------------------------------- commands
def cmd_families(t: pd.DataFrame) -> None:
    cols = ["slug", "question", "modality", "model_id", "model_kind", "family", "family_source", "final", "pred", "texts"]
    out = t[cols].sort_values(["family", "slug", "question"])
    out.to_csv(OUT["families"], index=False)
    sys_fam = t.groupby(["slug", "model_id"]).family.nunique()
    print(f"tracks {len(t)}, systems {len(sys_fam)}, systems whose tracks fall in more than one family {int((sys_fam > 1).sum())}")
    print(t.groupby("family").agg(tracks=("slug", "size"), tiles=("slug", "nunique"), compared=("compared", "sum"),
                                  overrides=("family_source", lambda s: (s == "override").sum())).to_string())
    un = t[t.family == "unassigned"]
    if len(un):
        print(f"\nUNASSIGNED {len(un)} tracks:")
        for r in un.itertuples():
            print(f"  {r.model_kind} | {r.slug} | {r.model_id} | {r.texts[:120]}")
        sys.exit(1)


def rate(matched: np.ndarray, n: np.ndarray, tile: np.ndarray, b: int = B, seed: int = SEED) -> tuple[float, float, float]:
    """Point estimate and percentile interval of matched/n from a cluster bootstrap over tiles."""
    if n.sum() == 0:
        return float("nan"), float("nan"), float("nan")
    p = matched.sum() / n.sum()
    m_by = pd.Series(matched).groupby(tile).sum().to_numpy()
    n_by = pd.Series(n).groupby(tile).sum().to_numpy()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(n_by), size=(b, len(n_by)))
    boots = m_by[idx].sum(axis=1) / n_by[idx].sum(axis=1)
    return float(p), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def rate_rows(c: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    rows = []
    for keys, g in c.groupby(by, dropna=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        p, lo, hi = rate(g.matched.to_numpy().astype(int), np.ones(len(g), dtype=int), g.slug.to_numpy())
        rows.append({**dict(zip(by, keys)), "n_tracks": len(g), "n_tiles": g.slug.nunique(), "matched": int(g.matched.sum()),
                     "contra": int((~g.matched).sum()), "ppv": round(p, 3), "lo": round(lo, 3), "hi": round(hi, 3),
                     "rankable": g.slug.nunique() >= MIN_TILES})
    return pd.DataFrame(rows)


def rate_table(c: pd.DataFrame) -> pd.DataFrame:
    """Per family and question (dose split into dose and dose (derived)), among compared tracks: the share whose prediction
    held, its interval, and the pooled share of the same question as the reference."""
    c = c.copy()
    c["q"] = np.where(c.pred == "derived", "dose (derived)", c.question)
    c = c[c.pred != "no"]
    fam = rate_rows(c, ["q", "family"])
    pooled = rate_rows(c, ["q"]).set_index("q")
    fam["pooled"] = fam.q.map(pooled.ppv)
    fam["pooled_lo"], fam["pooled_hi"] = fam.q.map(pooled.lo), fam.q.map(pooled.hi)
    fam["label"] = fam.family.map(lambda f: FAMILIES[f][0])
    fam["group"] = fam.family.map(lambda f: FAMILIES[f][1])
    return fam.sort_values(["q", "ppv", "n_tiles"], ascending=[True, False, False]).reset_index(drop=True)


def without_no_comparison(c: pd.DataFrame) -> pd.DataFrame:
    """Safety contras the hand review typed no_comparison (no admissible comparison, or a prediction never tested in
    patients) leave every rate; they are listed in LESSONS.md as a caveat."""
    if not os.path.exists(INPUTS["safety_types"]):
        return c
    ty = read_typed(INPUTS["safety_types"], "safety review")
    drop = ty[ty.type == "no_comparison"][["slug", "model_id"]].assign(question="safety", _drop=True)
    c = c.merge(drop, on=["slug", "model_id", "question"], how="left")
    return c[c._drop.isna()].drop(columns="_drop")


def cmd_rates(t: pd.DataFrame) -> None:
    c = without_no_comparison(t[t.compared])
    no = t[(t.pred == "no") & t.compared]
    if len(no):
        print(f"tracks whose model said no ({len(no)}), kept out of every rate: " + "; ".join(f"{r.slug} {r.model_id} {r.final}" for r in no.itertuples()))
    fam = rate_table(c)
    fam.to_csv(OUT["family_rates"], index=False)
    by = pd.concat([rate_table(c[c.approved == a]).assign(approved=a) for a in (True, False)])
    by.to_csv(OUT["family_rates_by_outcome"], index=False)
    for q, g in fam.groupby("q", sort=False):
        print(f"\n== {q}: pooled {g.pooled.iloc[0]:.2f} ({g.pooled_lo.iloc[0]:.2f}-{g.pooled_hi.iloc[0]:.2f})")
        print(g[["label", "n_tracks", "n_tiles", "matched", "contra", "ppv", "lo", "hi", "rankable"]].to_string(index=False))


def read_typed(path: str, kind: str) -> pd.DataFrame:
    if not os.path.exists(path):
        sys.exit(f"{os.path.basename(path)} is missing: it is the hand-typed {kind} file (DESIGN.md)")
    return pd.read_csv(path, dtype=str).fillna("")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for k of n; (nan, nan) when n is 0."""
    if n == 0:
        return float("nan"), float("nan")
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return float(c - h), float(c + h)


TIERS = [("direct", "Direct (occupancy, free target)"), ("proximal", "Proximal (the target's product)"), ("downstream", "Downstream biomarker")]


def engagement_summary(h: pd.DataFrame, min_area: int = 3) -> pd.DataFrame:
    """Among tiles whose engagement headline matched: the share with a contradicted efficacy headline, with a Wilson interval,
    by class outcome, by the headline engagement readout's tier, and by area (areas with min_area such tiles or more)."""
    held = h[h.engagement.isin(MATCHED)].copy()
    held["eff"] = held.efficacy.fillna("blank").map(lambda s: "matched" if s in MATCHED else ("contradicted" if s == "contra" else "not compared"))
    rows = []

    def add(group, label, g):
        n, k = len(g), int((g.eff == "contradicted").sum())
        lo, hi = wilson(k, n)
        rows.append({"group": group, "label": label, "n": n, "contradicted": k, "matched": int((g.eff == "matched").sum()),
                     "not_compared": int((g.eff == "not compared").sum()), "share": round(k / n, 3) if n else float("nan"),
                     "lo": round(lo, 3), "hi": round(hi, 3)})
    add("outcome", "Class approved", held[held.approved])
    add("outcome", "Class never approved", held[~held.approved])
    for code, label in TIERS:
        add("tier", label, held[held.engagement_tier == code])
    for a, n in held.area.value_counts().items():
        if n >= min_area:
            add("area", a.replace("_", " ").capitalize(), held[held.area == a])
    return pd.DataFrame(rows)


def unique_harm_rows(s: pd.DataFrame) -> pd.DataFrame:
    """The typed safety contras exploded to one row per harm, counted once per (model system, harm, type): a toxicology
    package that served three tiles is one silence, not three. no_comparison rows are left out; not_showable is drawn
    with silent."""
    s = s[s.type.isin({"silent", "stated_safe", "false_alarm", "not_showable"})].copy()
    s["type"] = s.type.replace({"not_showable": "silent"})
    x = s.assign(harm=s.harm_class.str.split(";")).explode("harm").reset_index(drop=True)
    x["harm"] = x.harm.str.strip()
    return x.drop_duplicates(["model_id", "harm", "type"]).reset_index(drop=True)


def cmd_safety(t: pd.DataFrame) -> pd.DataFrame:
    ty = read_typed(INPUTS["safety_types"], "safety review")
    bad = ty[~ty.type.isin(SAFETY_TYPES)]
    if len(bad):
        sys.exit(f"safety_types.csv: unknown type(s) {sorted(bad.type.unique())}")
    harms = ty.harm_class.str.split(";").explode().str.strip()
    bad = sorted(set(harms[harms != ""]) - HARM_CLASSES)
    if bad:
        sys.exit(f"safety_types.csv: unknown harm class(es) {bad}")
    sc = t[(t.question == "safety") & (t.final == "contra")]
    merged = sc.merge(ty, on=["slug", "model_id"], how="left", validate="many_to_one")
    missing = merged[merged.type.isna()]
    if len(missing):
        sys.exit("safety_types.csv lacks a row for: " + "; ".join(f"{r.slug} / {r.model_id}" for r in missing.itertuples()))
    extra = ty.merge(sc[["slug", "model_id"]], on=["slug", "model_id"], how="left", indicator=True)
    extra = extra[extra._merge == "left_only"]
    if len(extra):
        sys.exit("safety_types.csv has rows that are not compared safety contras: " + "; ".join(f"{r.slug} / {r.model_id}" for r in extra.itertuples()))
    cols = ["slug", "area", "approved", "modality", "model_id", "family", "model_kind", "type", "harm_class", "year", "reason", "short", "note_x", "note_y"]
    out = merged[cols].rename(columns={"note_x": "entry_note", "note_y": "review_note"})
    out.to_csv(OUT["safety_misses"], index=False)
    print(f"safety contras {len(out)}; type counts {out.type.value_counts().to_dict()}")
    x = out.assign(harm=out.harm_class.str.split(";")).explode("harm").reset_index(drop=True)
    x["harm"] = x.harm.str.strip()
    print(pd.crosstab(x.harm, x.type).to_string())
    print("\nby family:")
    print(pd.crosstab(out.family.map(lambda f: FAMILIES[f][0]), out.type).to_string())
    return out


def headline_table(t: pd.DataFrame, e: pd.DataFrame | None = None, tiles: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per tile: each question's headline (glance.cells, decision 6), the engagement headline's readout tier and family.
    Pass e and tiles to read the headlines from other statuses (the drafters' statuses in the sensitivity check)."""
    if e is None:
        e, tiles = glance.load()
    cells = glance.cells(e, tiles)
    wide = cells.pivot(index="slug", columns="question", values="status")
    info = tiles.set_index("slug")[["area", "furthest_phase"]]
    out = info.join(wide).reset_index()
    out["approved"] = out.furthest_phase == 4
    eng = cells[cells.question == "engagement"].set_index("slug")
    tier, fam = {}, {}
    for s, row in eng.iterrows():
        tr = t[(t.slug == s) & (t.question == "engagement") & (t.texts.str.contains(str(row.model), regex=False) if isinstance(row.model, str) else False)]
        if len(tr):
            tier[s], fam[s] = tr.readout_tier.iloc[-1], tr.family.iloc[-1]
    out["engagement_tier"] = out.slug.map(tier)
    out["engagement_family"] = out.slug.map(fam)
    return out


def cmd_engagement(t: pd.DataFrame) -> None:
    h = headline_table(t)
    h.to_csv(OUT["engagement_vs_efficacy"], index=False)
    es = engagement_summary(h)
    es.to_csv(OUT["engagement_summary"], index=False)
    print(es.to_string(index=False))
    held = h[h.engagement.isin(MATCHED)]
    eff = held.efficacy.fillna("blank").map(lambda s: "matched" if s in MATCHED else ("contradicted" if s == "contra" else "not compared"))
    print(f"tiles {len(h)}; engagement headline matched {len(held)}")
    print(pd.crosstab(held.area, eff, margins=True).to_string())
    print("\nby engagement readout tier:")
    print(pd.crosstab(held.engagement_tier.fillna("∅"), eff, margins=True).to_string())
    print("\nefficacy headline among tiles whose engagement was contradicted or never compared:")
    rest = h[~h.engagement.isin(MATCHED)]
    print(pd.crosstab(rest.engagement.fillna("blank"), rest.efficacy.fillna("blank"), margins=True).to_string())
    ty = read_typed(INPUTS["dose_types"], "dose review")
    bad = ty[~ty.reached.isin(DOSE_REACHED)]
    if len(bad):
        sys.exit(f"dose_types.csv: unknown reached type(s) {sorted(bad.reached.unique())}")
    d = t[(t.question == "dose") & (t.pred == "derived") & t.compared]
    m = d.merge(ty, on=["slug", "model_id"], how="left", validate="many_to_one")
    missing = m[m.reached.isna()]
    if len(missing):
        sys.exit("dose_types.csv lacks a row for: " + "; ".join(f"{r.slug} / {r.model_id}" for r in missing.itertuples()))
    cols = ["slug", "area", "approved", "modality", "model_id", "family", "model_kind", "reached", "year", "reason", "short", "note_x", "note_y"]
    m[cols].rename(columns={"note_x": "entry_note", "note_y": "review_note"}).to_csv(OUT["dose_derived"], index=False)
    print(f"\nderived dose contras {len(m)}: reached {m.reached.value_counts().to_dict()}")
    print(pd.crosstab(m.area, m.reached, margins=True).to_string())


def kappa(a: pd.Series, b: pd.Series) -> float:
    """Cohen's kappa between two codings of the same rows."""
    po = float((a == b).mean())
    pe = sum(float((a == k).mean()) * float((b == k).mean()) for k in set(a) | set(b))
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def cmd_robust(t: pd.DataFrame) -> None:
    """The checks behind the figure, written to robustness.md: intervals and tests on the engagement panel, the same panel on
    the drafters' statuses instead of the adjudicated ones, the duplicate safety packages, and the agreement of a second,
    blind coder on the safety typing when safety_types_coder2.csv exists."""
    from scipy import stats
    lines = ["# Robustness checks (written by `lessons.py robust`)", ""]
    e, tiles = glance.load()
    h = headline_table(t)
    held = h[h.engagement.isin(MATCHED)]
    tab = pd.crosstab(h.approved, h.engagement.isin(MATCHED))
    p_out = stats.fisher_exact(tab.values)[1]
    lines += ["## Engagement held, by class outcome", "",
              f"Engagement headline matched in {int(tab.loc[True, True])} of {int(tab.loc[True].sum())} approved classes and "
              f"{int(tab.loc[False, True])} of {int(tab.loc[False].sum())} never-approved classes (Fisher p = {p_out:.2f}). "
              f"Among the {len(held)} tiles with engagement held, efficacy was contradicted in "
              f"{int((held[~held.approved].efficacy == 'contra').sum())} of {int((~held.approved).sum())} never-approved and "
              f"{int((held[held.approved].efficacy == 'contra').sum())} of {int(held.approved.sum())} approved classes.", ""]
    es = engagement_summary(h)
    tier = es[es.group == "tier"]
    ct = pd.crosstab(held.engagement_tier, held.efficacy == "contra").reindex([c for c, _ in TIERS]).fillna(0)
    p_tier = stats.chi2_contingency(ct.values)[1]
    p_direct = stats.fisher_exact(pd.crosstab(held.engagement_tier == "direct", held.efficacy == "contra").values)[1]
    lines += ["## Efficacy contradicted among tiles with engagement held, by readout tier (Wilson 95 %)", "",
              "| tier | contradicted / n | share | 95 % |", "|---|---|---|---|"]
    lines += [f"| {r.label} | {r.contradicted}/{r.n} | {r.share:.2f} | {r.lo:.2f}-{r.hi:.2f} |" for r in tier.itertuples()]
    lines += ["", f"Chi-square tier x contradicted p = {p_tier:.2f}; direct vs the rest, Fisher p = {p_direct:.2f}. "
              "The tier is the headline engagement track's. With the best tier among a tile's matched engagement tracks instead:", ""]
    rank = {"direct": 0, "proximal": 1, "downstream": 2}
    best = {}
    for s_ in held.slug:
        tiers_ = [x for x in t[(t.slug == s_) & (t.question == "engagement") & t.matched].readout_tier.dropna() if x in rank]
        if tiers_:
            best[s_] = min(tiers_, key=rank.get)
    hb = held.assign(engagement_tier=held.slug.map(best))
    ctb = pd.crosstab(hb.engagement_tier, hb.efficacy == "contra").reindex([c for c, _ in TIERS]).fillna(0)
    for code, label in TIERS:
        g = hb[hb.engagement_tier == code]
        k, n = int((g.efficacy == "contra").sum()), len(g)
        lo, hi = wilson(k, n)
        lines.append(f"- {label}: {k}/{n} = {k / n:.2f} ({lo:.2f}-{hi:.2f})")
    lines += [f"- chi-square p = {stats.chi2_contingency(ctb.values)[1]:.2f}", ""]
    cns = held.area.isin(["neurology", "psychiatry"])
    d = held.engagement_tier == "direct"
    lines += [f"Direct-tier tiles outside neurology and psychiatry: {int((held[d & ~cns].efficacy == 'contra').sum())} of {int((d & ~cns).sum())} contradicted; "
              f"non-direct outside: {int((held[~d & ~cns].efficacy == 'contra').sum())} of {int((~d & ~cns).sum())}.", ""]
    # drafter statuses
    e2 = e.copy()
    e2["final"] = e2.status
    t2 = with_families(tracks(e2, tiles))
    h2 = headline_table(t2, e2, tiles)
    held2 = h2[h2.engagement.isin(MATCHED)]
    sc1 = set(zip(*[t[(t.question == "safety") & (t.final == "contra")][c] for c in ("slug", "model_id")]))
    sc2 = set(zip(*[t2[(t2.question == "safety") & (t2.final == "contra")][c] for c in ("slug", "model_id")]))
    lines += ["## Sensitivity: the drafters' statuses instead of the adjudicated ones", "",
              f"Engagement held in {len(held2)} tiles (adjudicated: {len(held)}); efficacy contradicted among them in "
              f"{int((held2.efficacy == 'contra').sum())} (adjudicated: {int((held.efficacy == 'contra').sum())}). "
              f"Compared safety contradictions: {len(sc2)} (adjudicated: {len(sc1)}), {len(sc1 & sc2)} in common.", ""]
    # duplicates
    sm = pd.read_csv(OUT["safety_misses"])
    typed = sm[sm.type != "no_comparison"]
    dup = typed.groupby("model_id").slug.nunique()
    dup = dup[dup > 1]
    u = unique_harm_rows(sm)
    lines += ["## Safety packages that serve more than one tile", "",
              f"{len(typed)} typed contradictions on {typed.model_id.nunique()} model systems; systems in more than one tile: "
              + "; ".join(f"`{m}` ({n} tiles)" for m, n in dup.items()) + f". Harm rows: {int(typed.harm_class.str.count(';').sum() + len(typed))} by track, "
              f"{len(u)} unique (system, harm, type); the figure counts the unique rows.", ""]
    # second coder
    if os.path.exists(INPUTS["safety_types_coder2"]) and os.path.exists(INPUTS["safety_types_coder1"]):
        c1 = read_typed(INPUTS["safety_types_coder1"], "first coder")
        c2 = read_typed(INPUTS["safety_types_coder2"], "second coder")
        res = read_typed(INPUTS["safety_types"], "safety review").set_index(["slug", "model_id"])
        m = c1.merge(c2, on=["slug", "model_id"], suffixes=("_1", "_2"), validate="one_to_one")
        first = lambda col: col.str.split(";").str[0].str.strip()  # noqa: E731
        k_type, k_harm = kappa(m.type_1, m.type_2), kappa(first(m.harm_class_1), first(m.harm_class_2))
        agree_t, agree_h = int((m.type_1 == m.type_2).sum()), int((first(m.harm_class_1) == first(m.harm_class_2)).sum())
        shared = int(sum(bool(set(a.split(";")) & set(b.split(";"))) for a, b in zip(m.harm_class_1, m.harm_class_2)))
        dis = m[m.type_1 != m.type_2]
        lines += ["## Second, blind coder on the safety typing", "",
                  f"{len(m)} rows typed independently from the entry text (`safety_types_coder1.csv`, the first coding as written; "
                  f"`safety_types_coder2.csv`, the blind second). Type: {agree_t} agree, kappa {k_type}. Primary harm class: {agree_h} agree, "
                  f"kappa {k_harm}; {shared} share at least one harm class. Disagreements on type (coder 1 / coder 2 -> resolved in `safety_types.csv`):", ""]
        lines += [f"- {r.slug} / `{r.model_id}`: {r.type_1} / {r.type_2} -> {res.loc[(r.slug, r.model_id), 'type']}" for r in dis.itertuples()]
        lines.append("")
    with open(ROBUST, "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


def cmd_figure(t: pd.DataFrame) -> None:
    from lessons_figure import draw, draw_families
    sm = pd.read_csv(OUT["safety_misses"])
    draw(pd.read_csv(OUT["engagement_summary"]), unique_harm_rows(sm), int((sm.type != "no_comparison").sum()), os.path.join(ATLAS, "atlas_lessons"))
    draw_families(pd.read_csv(OUT["family_rates"]), os.path.join(ATLAS, "atlas_lessons_families"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["families", "rates", "engagement", "safety", "robust", "figure", "all"])
    a = ap.parse_args()
    t = load()
    steps = {"families": cmd_families, "rates": cmd_rates, "engagement": cmd_engagement, "safety": cmd_safety, "robust": cmd_robust,
             "figure": cmd_figure}
    for name in (steps if a.command == "all" else [a.command]):
        print(f"\n### {name}")
        steps[name](t)


if __name__ == "__main__":
    main()
