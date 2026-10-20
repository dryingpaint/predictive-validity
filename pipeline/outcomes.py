"""What happened in a trial: posted results and the stated reason for stopping.

    python -m pipeline.outcomes results   # cached CT.gov results sections -> preclin.ctgov_result_summary

The results summary keeps, for up to three primary outcome measures, the
measured values per group and every statistical comparison (p-value, method,
estimate, confidence interval), plus deaths and serious adverse events per arm,
so an LLM can judge whether the primary endpoint was met.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os

from psycopg2.extras import Json, execute_values

from pipeline import llm
from pipeline.ctgov import CACHE as CTGOV_CACHE

MAX_PRIMARY = 3
MAX_CHARS = 6000


def summarize(results: dict) -> tuple[str, list[dict]]:
    lines, analyses = [], []
    measures = [m for m in (results.get("outcomeMeasuresModule") or {}).get("outcomeMeasures", [])
                if m.get("type") == "PRIMARY"]
    for m in measures[:MAX_PRIMARY]:
        groups = {g["id"]: g.get("title", "") for g in m.get("groups", [])}
        n = {c["groupId"]: c.get("value") for d in m.get("denoms", []) for c in d.get("counts", [])}
        lines.append(f"PRIMARY: {m.get('title')} [{m.get('timeFrame', '')}] "
                     f"({m.get('paramType', '')}, {m.get('unitOfMeasure', '')})")
        for cls in m.get("classes", [])[:4]:
            for cat in cls.get("categories", [])[:4]:
                vals = "; ".join(f"{groups.get(x['groupId'], x['groupId'])[:40]} (n={n.get(x['groupId'])}): "
                                 f"{x.get('value')}" + (f" ±{x['spread']}" if x.get("spread") else "")
                                 for x in cat.get("measurements", []))
                label = " / ".join(filter(None, [cls.get("title"), cat.get("title")]))
                lines.append(f"  {label + ': ' if label else ''}{vals}")
        for a in m.get("analyses", [])[:4]:
            row = {k: a.get(k) for k in ("pValue", "statisticalMethod", "paramType", "paramValue",
                                          "ciLowerLimit", "ciUpperLimit", "nonInferiorityType")}
            row["groups"] = [groups.get(g, g)[:40] for g in a.get("groupIds", [])]
            analyses.append(row)
            lines.append(f"  analysis {' vs '.join(row['groups'])}: p={row['pValue']} {row['statisticalMethod'] or ''} "
                         f"{row['paramType'] or ''} {row['paramValue'] or ''} "
                         f"[{row['ciLowerLimit']}, {row['ciUpperLimit']}] {row['nonInferiorityType'] or ''}")
    for g in (results.get("adverseEventsModule") or {}).get("eventGroups", [])[:6]:
        lines.append(f"AE {g.get('title', '')[:40]}: deaths {g.get('deathsNumAffected')}/{g.get('deathsNumAtRisk')}, "
                     f"serious {g.get('seriousNumAffected')}/{g.get('seriousNumAtRisk')}")
    return "\n".join(lines)[:MAX_CHARS], analyses


def results(_args) -> None:
    snap = sorted(glob.glob(os.path.join(CTGOV_CACHE, "*")))[-1]
    rows = []
    for path in sorted(glob.glob(os.path.join(snap, "page_*.json.gz"))):
        with gzip.open(path, "rt") as f:
            for study in json.load(f)["studies"]:
                if not study.get("resultsSection"):
                    continue
                text, analyses = summarize(study["resultsSection"])
                nct = study["protocolSection"]["identificationModule"]["nctId"]
                rows.append((nct, text, len(analyses), Json(analyses)))
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.ctgov_result_summary")
        execute_values(cur, """INSERT INTO preclin.ctgov_result_summary (nct_id, summary, n_analyses, analyses)
                               VALUES %s""", rows, page_size=2000)
        conn.commit()
    print(f"studies with results={len(rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("results").set_defaults(fn=results)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
