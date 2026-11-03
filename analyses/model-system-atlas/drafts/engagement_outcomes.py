"""DB arm of the engagement-tier experiment: for each atlas context (indication x most-developed novel
class), what happened to that class's Phase 2 entrants in the DB (advanced to Phase 3 or not), and later
to its Phase 3 entrants. Read-only. Reuses lists.py's class derivation so the join is exact.

    .venv/bin/python analyses/model-system-atlas/drafts/engagement_outcomes.py

Writes drafts/context_outcomes.csv.
"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ATLAS = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(ATLAS))
sys.path.insert(0, ROOT); sys.path.insert(0, ATLAS)
import lists  # noqa: E402  (lists.py: frame, section1, WINDOW, PHASE, MERGE, DROP, ACTION_PHRASE)
from lists import frame, section1, WINDOW, MERGE, DROP, ACTION_PHRASE  # noqa: E402


def main():
    man = pd.read_csv(os.path.join(HERE, "manifest.csv"), dtype=str).fillna("")
    snap = frame.snapshot()
    progs, trials = frame.programs(), frame.program_trials()
    rows = section1.phase_rows(progs, trials, snap, window=WINDOW)
    rows["mondo_id"] = rows.program_id.map(progs.set_index("program_id").mondo_id)
    rows["disease"] = rows.mondo_id.map(lambda m: MERGE.get(m, m))
    rows = rows[rows.disease.notna() & ~rows.disease.isin(DROP)]
    mt = frame.query("""SELECT mt.moiety_id, t.symbol, mt.action, count(*) OVER (PARTITION BY mt.moiety_id) AS n_primary
                        FROM preclin.moiety_target mt JOIN public.targets t ON t.id = mt.target_id WHERE mt.is_primary""")
    mech = frame.query("""SELECT DISTINCT ON (x.moiety_id) x.moiety_id, cm.mechanism_of_action AS mech
                          FROM preclin.chembl_moiety x JOIN preclin.chembl_mechanism cm ON cm.parent_chembl_id = x.parent_chembl_id
                          WHERE cm.mechanism_of_action IS NOT NULL ORDER BY x.moiety_id, cm.mec_id""")
    e = rows[rows.novel].merge(mt, on="moiety_id", how="left").merge(mech, on="moiety_id", how="left")

    def label(r):
        if pd.notna(r.symbol):
            return ACTION_PHRASE.get(r.action, "{t} " + str(r.action)).format(t=r.symbol)
        return r.mech if pd.notna(r.mech) else None
    e["cls"] = e.apply(label, axis=1)
    out = []
    for m in man.itertuples():
        g = e[(e.disease == m.mondo_id) & (e.cls == m.drug_class)]
        p2 = g[(g.phase == 2) & ~g.credited]; p3 = g[(g.phase == 3) & ~g.credited]
        rec = {"context": m.id, "mondo_id": m.mondo_id, "drug_class": m.drug_class,
               "n_programs_in_class": int(g.program_id.nunique()),
               "ph2_entrants": int(p2.program_id.nunique()),
               "ph2_advanced": int((p2.event == "advanced").sum()), "ph2_suspended": int((p2.event == "suspended").sum()),
               "ph2_censored": int((p2.event == "censored").sum()),
               "ph3_entrants": int(p3.program_id.nunique()),
               "ph3_advanced": int((p3.event == "advanced").sum()), "ph3_suspended": int((p3.event == "suspended").sum())}
        rec["ph2_adv_rate_resolved"] = round(rec["ph2_advanced"] / max(rec["ph2_advanced"] + rec["ph2_suspended"], 1), 2)
        rec["ph3_adv_rate_resolved"] = round(rec["ph3_advanced"] / max(rec["ph3_advanced"] + rec["ph3_suspended"], 1), 2)
        out.append(rec)
    df = pd.DataFrame(out); df.to_csv(os.path.join(HERE, "context_outcomes.csv"), index=False)
    print(df[["context", "ph2_entrants", "ph2_advanced", "ph2_suspended", "ph2_adv_rate_resolved", "ph3_entrants", "ph3_adv_rate_resolved"]].to_string(index=False))
    print("event values:", rows.event.unique().tolist(), "| phases:", sorted(rows.phase.unique().tolist()))


if __name__ == "__main__":
    main()
