"""The engaged-but-failed classes: every tile whose engagement headline matched and whose efficacy headline was
contradicted, with every engagement, efficacy and dose entry the atlas holds for it, written for hand coding.

    .venv/bin/python analyses/model-system-atlas/lessons/engaged/extract.py

Writes cases_tiles.csv (one row per class), cases_entries.csv (one row per entry) and cases_dossier.txt (the same entries
as readable text, the file the coders read). Read-only on the database; statuses are the adjudicated statuses."""
from __future__ import annotations

import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import glance  # noqa: E402
import lessons  # noqa: E402

MATCHED = {"same", "neg", "other"}
FIELDS = ["reason", "note", "judgement", "quote", "model_kind", "readout_tier", "magnitude", "source_calls_it", "endpoint_role",
          "outcome_tested", "population", "derived_from", "subjects"]


def main() -> None:
    e, tiles = glance.load()
    cells = glance.cells(e, tiles)
    wide = cells.pivot(index="slug", columns="question", values="status")
    info = tiles.set_index("slug")[["area", "disease", "mechanism", "furthest_phase", "class_programs"]]
    h = info.join(wide).reset_index()
    cases = h[h.engagement.isin(MATCHED) & (h.efficacy == "contra")].copy()
    cases.to_csv(os.path.join(HERE, "cases_tiles.csv"), index=False)
    e2 = e[e.final != "drop"].merge(tiles[["slug", "mondo_id", "mechanism_key"]], on=["mondo_id", "mechanism_key"])
    f = pd.DataFrame(e2.fields.tolist(), index=e2.index)
    for c in FIELDS:
        e2[c] = f[c] if c in f else None
    ent = e2[e2.slug.isin(cases.slug) & e2.question.isin(["engagement", "efficacy", "dose"])].sort_values(["slug", "question", "model_id", "year", "seq"])
    ent = ent[["slug", "question", "model_id", "year", "status", "final", "model", "short"] + FIELDS]
    ent.to_csv(os.path.join(HERE, "cases_entries.csv"), index=False)
    with open(os.path.join(HERE, "cases_dossier.txt"), "w") as fh:
        for c in cases.itertuples():
            fh.write(f"\n==================== {c.slug}  [{c.area}; furthest phase {c.furthest_phase}; {c.class_programs} programs]\n")
            for q in ["engagement", "efficacy", "dose"]:
                g = ent[(ent.slug == c.slug) & (ent.question == q)]
                fh.write(f"-- {q} (cell headline {getattr(c, q)})\n")
                for r in g.itertuples():
                    if r.final == "untested" and q != "efficacy":
                        continue
                    fh.write(f"   {r.year} {r.final:8} {str(r.model)[:90]}\n")
                    for k in ("reason", "note"):
                        v = getattr(r, k)
                        if isinstance(v, str) and v:
                            fh.write(f"      {k}: {v}\n")
                    if q == "efficacy":
                        for k, n in (("judgement", 400), ("quote", 300)):
                            v = getattr(r, k)
                            if isinstance(v, str) and v:
                                fh.write(f"      {k}: {v[:n]}\n")
    print(f"classes {len(cases)} (approved {int((cases.furthest_phase == 4).sum())}); entries {len(ent)}")


if __name__ == "__main__":
    main()
