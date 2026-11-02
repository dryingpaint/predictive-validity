"""Draw the atlas lists from the database (issue #76, task 2): the named indications and the
long-tail program sample.

    .venv/bin/python analyses/model-system-atlas/lists.py

Cohort: programs entering Phase 2 in 2008-2019 under the report's own definition
(report.section1.phase_rows: industry-sponsored entry trial that started, vaccines excluded,
lifecycle programs excluded; phases credited by skipping are not entries). Each program is
one (entity, MONDO disease); its area is preclin.mondo_bio_area.

Named indications: the top 15 diseases in oncology and the top 4 in every other area, after
the cleaning rules in the issue, applied here as code so a re-run after #70 reproduces them:
  MERGE   parent/child duplicates (child counted under the parent);
  DROP    mapping errors and supportive-care conditions;
  then rank, so the next-ranked disease backfills each dropped one.

Long tail: SAMPLE_N programs drawn without replacement, seed SEED, from entries whose disease is
not a named indication.

Writes lists/named_indications.csv, lists/volumes.json (shape of volumes_pre_rebuild.json) and
lists/sample.csv, and prints the issue's table for comparison. Read-only.
"""
import json
import os
import sys
from datetime import date

import pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
from report import frame, section1  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "lists")
WINDOW = (date(2008, 1, 1), date(2019, 12, 31))
PHASE = 2
TOP = {"oncology": 15}
TOP_DEFAULT = 4
SAMPLE_N = 200
SEED = 20261102

# child -> parent (issue #76: "merged parent/child duplicates")
MERGE = {
    "MONDO:0005416": "MONDO:0005178",  # knee osteoarthritis -> osteoarthritis
    "MONDO:0005015": "MONDO:0005148",  # diabetes mellitus -> type 2 diabetes mellitus
    "MONDO:0013209": "MONDO:0007027",  # MASLD -> MASH
    "MONDO:0005324": "MONDO:0011786",  # seasonal allergic rhinitis -> allergic rhinitis
    "MONDO:0002050": "MONDO:0002009",  # depressive disorder -> major depressive disorder
}
# dropped outright (issue #76): a mapping error and supportive-care conditions
DROP = {
    "MONDO:0037829": "purine metabolism disease: mapping error (DATA_FIXES.md #5)",
    "MONDO:0001475": "neutropenia: supportive care, no disease model of its own",
    "MONDO:0002280": "anemia: supportive care, no disease model of its own",
}


def labels(mondo_ids: list[str]) -> dict[str, str]:
    df = frame.query("SELECT term_id, label FROM preclin.ontology_term WHERE ontology = 'MONDO' AND term_id = ANY(%s)",
                     (list(mondo_ids),)) if hasattr(frame, "query") else None
    return dict(zip(df.term_id, df.label)) if df is not None else {}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    snap = frame.snapshot()
    progs, trials = frame.programs(), frame.program_trials()
    rows = section1.phase_rows(progs, trials, snap, window=WINDOW)
    ent = rows[(rows.phase == PHASE) & ~rows.credited][["program_id", "moiety_id", "bio_area", "novel", "modality", "entry_year"]].copy()
    ent["mondo_id"] = ent.program_id.map(progs.set_index("program_id").mondo_id)
    ent = ent[ent.mondo_id.notna()]
    ent["disease"] = ent.mondo_id.map(lambda m: MERGE.get(m, m))
    ent = ent[~ent.disease.isin(DROP)]
    name = labels(sorted(ent.disease.unique()))

    counts = ent.groupby(["bio_area", "disease"]).program_id.nunique().reset_index(name="n")
    named, areas = [], []
    for area, g in counts.groupby("bio_area"):
        g = g.sort_values("n", ascending=False)
        k = TOP.get(area, TOP_DEFAULT)
        head = g.head(k)
        for rank, r in enumerate(head.itertuples(), 1):
            named.append({"area": area, "rank": rank, "mondo_id": r.disease, "label": name.get(r.disease, r.disease), "n": int(r.n),
                          "merged_from": ";".join(c for c, p in MERGE.items() if p == r.disease)})
        areas.append({"area": area,
                      "indications": [{"mondo_id": r.disease, "label": name.get(r.disease, r.disease), "n": int(r.n)} for r in head.itertuples()],
                      "rest": int(g.n[k:].sum()), "n_rest_indications": int(len(g) - k)})
    named_df = pd.DataFrame(named)
    named_df.to_csv(os.path.join(OUT, "named_indications.csv"), index=False)
    json.dump(areas, open(os.path.join(OUT, "volumes.json"), "w"), indent=1)

    classes(ent, named_df).to_csv(os.path.join(OUT, "named_contexts.csv"), index=False)

    tail = ent[~ent.disease.isin(set(named_df.mondo_id))]
    sample = tail.sample(n=min(SAMPLE_N, len(tail)), random_state=SEED)[["program_id", "moiety_id", "mondo_id", "disease", "bio_area", "modality", "entry_year"]]
    sample["label"] = sample.disease.map(name)
    sample.to_csv(os.path.join(OUT, "sample.csv"), index=False)

    total = int(ent.program_id.nunique())
    simple = int(frame.query("SELECT count(*) AS n FROM preclin.dev_program WHERE ph2_start BETWEEN %s AND %s", (WINDOW[0], WINDOW[1])).n[0])
    print(f"(for comparison: {simple:,} programs have dev_program.ph2_start in the window, the pre-rebuild treemap's simpler count)")
    print(f"snapshot {snap}; Phase {PHASE} entries {WINDOW[0].year}-{WINDOW[1].year}: {total:,} programs, "
          f"{ent.disease.nunique():,} diseases; named {len(named_df)} cover {named_df.n.sum() / total:.0%}; "
          f"sample {len(sample)} (seed {SEED})")
    print("\n| Area | Indications |\n|---|---|")
    for a in sorted(areas, key=lambda a: -(sum(i['n'] for i in a['indications']) + a['rest'])):
        print(f"| {a['area']} ({len(a['indications'])}) | " + ", ".join(f"{i['label']} ({i['n']})" for i in a["indications"]) + " |")
    json.dump({"snapshot": str(snap), "window": [str(w) for w in WINDOW], "phase": PHASE, "programs": total,
               "diseases": int(ent.disease.nunique()), "seed": SEED, "sample_n": len(sample), "merge": MERGE, "drop": DROP},
              open(os.path.join(OUT, "provenance.json"), "w"), indent=1)



# ---------------------------------------------------------------------------
# Most-developed drug class per named indication (issue #76: "each is assessed for its
# most-developed drug class"). Deterministic from the database:
#   - cohort as above, restricted to entities that were NOVEL at Phase 2 entry (not yet
#     FDA-approved for anything), so reformulations of marketed drugs do not define a class;
#   - class = (primary target symbol, action) from preclin.moiety_target; a program with k
#     primary targets contributes 1/k to each, so multikinase inhibitors do not dominate;
#   - pathogen-target and other unresolved entities have no moiety_target rows; their class
#     comes from ChEMBL mechanism text (preclin.chembl_mechanism via chembl_moiety) when present;
#   - the class with the largest weighted program count wins; class_basis records which path.
# Decided 2026-11-02 (Stephen): follow the DB rule; hand overrides only where nothing resolves.
# ---------------------------------------------------------------------------
ACTION_PHRASE = {
    "inhibitor": "{t} inhibitors", "antagonist": "{t} antagonists", "agonist": "{t} agonists",
    "binder_neutralizer": "anti-{t} antibodies", "depleter": "{t}-directed depleters",
    "replacement": "{t} replacement / gene therapy", "positive_modulator": "{t} positive modulators",
    "negative_modulator": "{t} negative modulators", "gene_expression_reduction": "{t} antisense / siRNA",
    "gene_expression_increase": "{t} gene therapy", "blocker": "{t} blockers", "activator": "{t} activators",
    "opener": "{t} openers", "other": "{t}-targeted agents",
}
OVERRIDE = {  # mondo_id -> class label, used only when no target or mechanism resolves for the plurality
}


def classes(ent: pd.DataFrame, named: pd.DataFrame) -> pd.DataFrame:
    """One row per named indication: the most-developed drug class, its weighted program
    count, example entities, and how the class was resolved."""
    mt = frame.query("""SELECT mt.moiety_id, t.symbol, mt.action,
                               count(*) OVER (PARTITION BY mt.moiety_id) AS n_primary
                        FROM preclin.moiety_target mt JOIN public.targets t ON t.id = mt.target_id
                        WHERE mt.is_primary""")
    mech = frame.query("""SELECT DISTINCT ON (x.moiety_id) x.moiety_id, cm.mechanism_of_action AS mech
                          FROM preclin.chembl_moiety x JOIN preclin.chembl_mechanism cm
                            ON cm.parent_chembl_id = x.parent_chembl_id
                          WHERE cm.mechanism_of_action IS NOT NULL ORDER BY x.moiety_id, cm.mec_id""")
    names = frame.query("SELECT moiety_id, name, modality FROM preclin.moiety").set_index("moiety_id")
    e = ent[ent.novel].merge(mt, on="moiety_id", how="left").merge(mech, on="moiety_id", how="left")
    e["weight"] = 1 / e.n_primary.fillna(1)
    e["cls"] = e.apply(lambda r: f"target|{r.symbol}|{r.action}" if pd.notna(r.symbol)
                       else (f"chembl|{r.mech}" if pd.notna(r.mech) else None), axis=1)
    out = []
    for r in named.itertuples():
        g = e[e.disease == r.mondo_id]
        ranked = g.dropna(subset=["cls"]).groupby("cls").weight.sum().sort_values(ascending=False)
        if r.mondo_id in OVERRIDE:
            label, basis, n, ex = OVERRIDE[r.mondo_id], "override", 0, ""
        elif len(ranked):
            cls = ranked.index[0]
            kind, val = cls.split("|", 1)
            if kind == "chembl":
                label, basis = val, "chembl_mechanism"
            else:
                t, a = val.split("|")
                label, basis = ACTION_PHRASE.get(a, "{t} " + a).format(t=t), "target_action"
            n = float(ranked.iloc[0])
            ex = "; ".join(names.name[m] for m in g[g.cls == cls].moiety_id.drop_duplicates().head(5) if m in names.index)
        else:
            label, basis, n, ex = "(unresolved)", "unresolved", 0, ""
        out.append({"area": r.area, "mondo_id": r.mondo_id, "label": r.label, "n_programs": int(r.n),
                    "class": label, "class_programs": round(n, 1), "class_basis": basis,
                    "share_unresolved": round(float(g.cls.isna().mean()) if len(g) else 1.0, 2),
                    "example_entities": ex})
    return pd.DataFrame(out)


if __name__ == "__main__":
    main()
