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
lists/sample.csv, and prints the issue's table for comparison. Read-only. Each named indication's
mechanism (its tile) is drawn by class_audit.py into lists/named_contexts.csv.
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



# Label for a (target, action) mechanism, e.g. "BTK inhibitors".
ACTION_PHRASE = {
    "inhibitor": "{t} inhibitors", "antagonist": "{t} antagonists", "agonist": "{t} agonists",
    "binder_neutralizer": "anti-{t} antibodies", "depleter": "{t}-directed depleters",
    "replacement": "{t} replacement / gene therapy", "positive_modulator": "{t} positive modulators",
    "negative_modulator": "{t} negative modulators", "gene_expression_reduction": "{t} antisense / siRNA",
    "gene_expression_increase": "{t} gene therapy", "blocker": "{t} blockers", "activator": "{t} activators",
    "opener": "{t} openers", "inverse_agonist": "{t} inverse agonists", "other": "{t}-targeted agents",
}

if __name__ == "__main__":
    main()
