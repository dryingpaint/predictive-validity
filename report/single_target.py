"""Which diseases the target-based drugging paradigm solves (#197): pathways tried and approved per disease, and the
shortlists confirmed by #198's inclusion rule (#193).

    python -m report.single_target

Pathways tried: the pathways (preclin.mechanism_pathway, kind specific) of every novel Phase 2 entry of 2008-2019 that
counts toward a mechanism in its atlas disease (preclin.atlas_member, excluded null). A tried pathway is approved in
the disease when an FDA-labelled entity acting through it is indicated for the disease (preclin.label_indication); the
labels are read only for the shortlisted diseases, so success is reported for those alone.

Pathways approved: every pathway of an entity whose current FDA label is indicated for the disease, any approval
year. An entity with no resolvable target counts toward the disease's labelled entities but no pathway, and the share
is reported. A shortlisted disease stays only with at least MIN_APPROVED_PATHWAYS approved pathways.

Writes report/output/single_target/: shortlist.csv, tried_by_area.csv and numbers.json.
"""
from __future__ import annotations

import json
import os

import pandas as pd

from pipeline.single_target import AREAS_APART, EVENT_SHORTLIST, MIN_APPROVED_PATHWAYS, SHORTLIST, mechanism_keys
from report import frame

OUT = os.path.join(frame.REPO, "report", "output", "single_target")

TRIED_SQL = """SELECT a.mondo_id, i.label, i.area, a.entity_id, unnest(mp.pathways) AS pathway
               FROM preclin.atlas_member a JOIN preclin.atlas_indication i USING (mondo_id)
               JOIN preclin.mechanism_pathway mp ON mp.mechanism_key = a.mechanism_key
               WHERE a.excluded IS NULL AND mp.kind = 'specific'"""
LABELLED_SQL = """SELECT DISTINCT li.mondo_id, m.moiety_id
                  FROM preclin.label_indication li JOIN preclin.fda_label l USING (set_id)
                  JOIN preclin.moiety m ON m.unii = ANY(l.unii)"""
PATHWAYS_SQL = "SELECT mechanism_key, kind, pathways FROM preclin.mechanism_pathway"


def approved_pathways(labelled: pd.DataFrame, keys: dict[int, tuple[str, str, str]],
                      pathways: dict[str, tuple[str, list[str]]]) -> pd.DataFrame:
    """One row per disease and labelled entity: its pathways (empty when its target is unresolved or not specific)."""
    rows = []
    for mondo_id, moiety_id in labelled.itertuples(index=False):
        kind, ps = pathways.get(keys.get(moiety_id, ("",))[0], ("unresolved", []))
        rows.append({"mondo_id": mondo_id, "moiety_id": moiety_id, "kind": kind, "pathways": ps})
    return pd.DataFrame(rows, columns=["mondo_id", "moiety_id", "kind", "pathways"])


def shortlist_table(tried: pd.DataFrame, approved: pd.DataFrame) -> pd.DataFrame:
    """Per shortlisted disease: pathways tried in 2008-2019 and how many reached approval, approved pathways of any
    year, labelled entities without a pathway, and whether the disease stays (MIN_APPROVED_PATHWAYS)."""
    out = []
    for mondo_id, e in {**SHORTLIST, **EVENT_SHORTLIST}.items():
        a = approved[approved.mondo_id == mondo_id]
        ok = sorted({p for ps in a.pathways for p in ps})
        t = sorted(set(tried.loc[tried.mondo_id == mondo_id, "pathway"]))
        out.append({"mondo_id": mondo_id, "disease": e.disease,
                    "endpoint": "event" if mondo_id in EVENT_SHORTLIST else "responder",
                    "tried_pathways": len(t), "tried_approved": len(set(t) & set(ok)),
                    "approved_pathways": len(ok), "labelled_entities": len(a),
                    "labelled_without_pathway": int((a.kind != "specific").sum()),
                    "stays": len(ok) >= MIN_APPROVED_PATHWAYS, "approved": "; ".join(ok)})
    return pd.DataFrame(out)


def tried_by_area(tried: pd.DataFrame) -> pd.DataFrame:
    """Per disease area: diseases, and the median and range of distinct pathways tried per disease in 2008-2019, with
    AREAS_APART flagged."""
    per = tried.groupby(["area", "mondo_id"]).pathway.nunique().rename("pathways").reset_index()
    g = per.groupby("area").pathways
    t = pd.DataFrame({"diseases": g.size(), "median_pathways": g.median(), "max_pathways": g.max()}).reset_index()
    t["reported_apart"] = t.area.isin(AREAS_APART)
    return t.sort_values(["reported_apart", "diseases"], ascending=[True, False])


def main() -> None:
    tried = frame.query(TRIED_SQL)
    labelled = frame.query(LABELLED_SQL)
    with frame.connection().cursor() as cur:
        keys = mechanism_keys(cur)
    pathways = {k: (kind, ps) for k, kind, ps in frame.query(PATHWAYS_SQL).itertuples(index=False)}
    approved = approved_pathways(labelled, keys, pathways)
    short = shortlist_table(tried, approved)
    area = tried_by_area(tried)
    os.makedirs(OUT, exist_ok=True)
    short.to_csv(os.path.join(OUT, "shortlist.csv"), index=False)
    area.to_csv(os.path.join(OUT, "tried_by_area.csv"), index=False)
    numbers = {"shortlisted": len(short), "stay": int(short.stays.sum()),
               "dropped": short.loc[~short.stays, "disease"].tolist(),
               "atlas_diseases": int(tried.mondo_id.nunique()),
               "labelled_entities": int(approved.moiety_id.nunique()),
               "labelled_without_pathway": int(approved.loc[approved.kind != "specific", "moiety_id"].nunique())}
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(numbers, f, indent=2)
    print(short.drop(columns="approved").to_string(index=False))
    print(area.to_string(index=False))
    print(json.dumps(numbers, indent=2))


if __name__ == "__main__":
    main()
