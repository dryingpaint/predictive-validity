"""Draw the atlas disease list from the database (issue #76, task 2).

    .venv/bin/python analyses/model-system-atlas/lists.py

Cohort: programs entering Phase 2 in 2008-2019 under the report's own definition
(report.section1.phase_rows: industry-sponsored entry trial that started, vaccines excluded,
lifecycle programs excluded; phases credited by skipping are not entries). Each program is
one (entity, MONDO disease); its area is preclin.mondo_bio_area.

Diseases: every disease with a Phase 2 entry, after the cleaning rules, applied here as code:
  MERGE   two terms for the same patients (the duplicate counted under the term kept);
  DROP    mapping errors and supportive-care conditions.
A disease's rank is its place in its area by programs.

Writes lists/named_indications.csv and lists/provenance.json. Read-only. Each disease's tracked
mechanisms (its tiles) are drawn by class_audit.py into lists/named_contexts.csv.
"""
import json
import os
import sys
from datetime import date

import pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
from report import frame, section1

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "lists")
WINDOW = (date(2008, 1, 1), date(2019, 12, 31))
PHASE = 2
# duplicate term -> the term counted. Two terms merge only when they name the same patients; a subtype with
# its own patients (triple-negative breast cancer, DLBCL, psoriatic arthritis) stays a disease of its own.
# The term kept is the one a tracked tile already uses where there is one, so no stored track record moves.
MERGE = {
    "MONDO:0005416": "MONDO:0005178",  # knee osteoarthritis -> osteoarthritis
    "MONDO:0005015": "MONDO:0005148",  # diabetes mellitus -> type 2 diabetes mellitus
    "MONDO:0013209": "MONDO:0007027",  # MASLD -> MASH
    "MONDO:0005324": "MONDO:0011786",  # seasonal allergic rhinitis -> allergic rhinitis
    "MONDO:0002050": "MONDO:0002009",  # depressive disorder -> major depressive disorder
    "MONDO:0009348": "MONDO:0004952",  # classic Hodgkin lymphoma -> Hodgkins lymphoma
    "MONDO:0004948": "MONDO:0003864",  # B-cell chronic lymphocytic leukemia -> CLL/SLL
    "MONDO:0004947": "MONDO:0004967",  # B-cell acute lymphoblastic leukemia -> acute lymphoblastic leukemia
    "MONDO:0020511": "MONDO:0004967",  # precursor B-cell acute lymphoblastic leukemia -> acute lymphoblastic leukemia
    "MONDO:0005417": "MONDO:0005150",  # wet macular degeneration -> age-related macular degeneration
    "MONDO:0003004": "MONDO:0005150",  # macular degeneration -> age-related macular degeneration
    "MONDO:0000432": "MONDO:0100280",  # lymphoplasmacytic lymphoma -> Waldenstrom macroglobulinemia
    "MONDO:0006543": "MONDO:0009179",  # epidermolysis bullosa dystrophica -> recessive dystrophic EB
    "MONDO:0011758": "MONDO:0001586",  # Hurler syndrome -> mucopolysaccharidosis type 1
    "MONDO:0004784": "MONDO:0004979",  # allergic asthma -> asthma
    "MONDO:0005344": "MONDO:0005366",  # hepatitis B virus infection -> chronic hepatitis B virus infection
    "MONDO:0005041": "MONDO:0005338",  # glaucoma -> open-angle glaucoma
    "MONDO:0005354": "MONDO:0005231",  # chronic hepatitis C virus infection -> hepatitis C virus infection
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
    counts = counts.sort_values(["n", "disease"], ascending=[False, True]).drop_duplicates("disease")  # a disease in two areas counts in its larger
    counts["rank"] = counts.groupby("bio_area").n.rank(ascending=False, method="first").astype(int)
    named = pd.DataFrame({"area": counts.bio_area, "rank": counts["rank"], "mondo_id": counts.disease,
                          "label": counts.disease.map(lambda d: name.get(d, d)), "n": counts.n,
                          "merged_from": counts.disease.map(lambda d: ";".join(c for c, p in MERGE.items() if p == d))})
    named = named.sort_values(["area", "rank"])
    named.to_csv(os.path.join(OUT, "named_indications.csv"), index=False)

    total = int(ent.program_id.nunique())
    print(f"snapshot {snap}; Phase {PHASE} entries {WINDOW[0].year}-{WINDOW[1].year}: {total:,} programs in {len(named):,} diseases")
    json.dump({"snapshot": str(snap), "window": [str(w) for w in WINDOW], "phase": PHASE, "programs": total,
               "diseases": len(named), "merge": MERGE, "drop": DROP},
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
