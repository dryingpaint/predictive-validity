"""Do the stop subcause lists hold up? Two independent passes over a seeded sample of stops.

    python -m scripts.subcause_audit           # the text-only pass, twice
    python -m scripts.subcause_audit search    # a pilot of the search-based pass

Draws SAMPLE stops per cause from the stops pipeline.stop_causes describe would label (half whose cause was traced,
half whose cause came from the registry, where both exist), decides each with the stop_subcause task twice (the
second pass a copy of the task under a retest prompt version, so it is not reused from the first), and writes to
report/audits/subcause_audit.json: per cause, how often the two passes agree and Cohen's kappa, the subcause pairs
they split on, the shares labelled not_stated and other_stated with every other_stated reason, and how often the text
contradicts the cause. The decisions are kept for a hand review of the first pass.

The search mode draws SEARCH_SAMPLE stops per cause that the text pass leaves without a subcause, runs the
stop_subcause_search task on them, and writes to report/audits/subcause_search_pilot.json how often it finds a stated
or likely subcause and which, which other causes its sources give, with the decisions kept for a hand review.
"""
from __future__ import annotations

import collections
import dataclasses
import json
import os
import sys

import numpy as np
import pandas as pd

from pipeline import llm
from pipeline.stop_causes import (SEARCH_TASK, SUBCAUSE_TASK, apply_text, describe_items, recast_items,
                                  search_items, stop_rows)
from report import frame

SAMPLE = {"safety": 35, "sponsor_decision": 45, "operational": 20, "positive_not_advanced": 50}
SEED = 11
OUT = os.path.join(frame.REPO, "report", "audits", "subcause_audit.json")
REVIEW = os.path.join(frame.REPO, "report", "output", "stop_causes", "subcause_audit_items.csv")
SEARCH_SAMPLE = {"positive_not_advanced": 25, "sponsor_decision": 20, "safety": 10, "operational": 5}
SEARCH_OUT = os.path.join(frame.REPO, "report", "audits", "subcause_search_pilot.json")
SEARCH_REVIEW = os.path.join(frame.REPO, "report", "output", "stop_causes", "subcause_search_pilot_items.csv")


def kappa(a: list[str], b: list[str]) -> float | None:
    """Cohen's kappa of two labellings of the same items."""
    n = len(a)
    if n == 0:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = collections.Counter(a), collections.Counter(b)
    expected = sum(ca[k] * cb[k] for k in ca) / n ** 2
    return None if expected == 1 else (observed - expected) / (1 - expected)


def sample(items: dict[str, dict], traced: dict[str, bool]) -> dict[str, dict]:
    rng = np.random.default_rng(SEED)
    out = {}
    for cause, n in SAMPLE.items():
        traced_keys, registry_keys = (sorted(k for k, p in items.items() if p["cause"] == cause and traced[k] == t)
                                      for t in (True, False))
        n_registry = min(len(registry_keys), n // 2)  # half from each route, topped up from the other when one is short
        n_traced = min(len(traced_keys), n - n_registry)
        n_registry = min(len(registry_keys), n - n_traced)
        for keys, m in ((traced_keys, n_traced), (registry_keys, n_registry)):
            out.update({k: items[k] for k in rng.choice(keys, size=m, replace=False)})
    return out


def main() -> None:
    rows = stop_rows()
    traced = {key: row["traced"] for key, *_, row in rows}
    items = sample(describe_items(rows)[0], traced)
    first = {k: o for k, _, o in llm.decisions(llm.run(SUBCAUSE_TASK, items))}
    retest = dataclasses.replace(SUBCAUSE_TASK, prompt_version=f"{SUBCAUSE_TASK.prompt_version}-retest")
    second = {k: o for k, _, o in llm.decisions(llm.run(retest, items))}
    both = sorted(set(first) & set(second))
    d = pd.DataFrame([{"key": k, "cause": items[k]["cause"], "traced": traced[k], "a": first[k]["subcause"],
                       "b": second[k]["subcause"], "other": first[k]["other_reason"],
                       "contradicted": first[k]["text_cause"] not in (items[k]["cause"], "unclear"), "text_cause": first[k]["text_cause"],
                       "basis": first[k]["basis"], "explanation": items[k]["explanation"]} for k in both])
    d.to_csv(REVIEW, index=False)
    audit = {"sample": {c: int((d.cause == c).sum()) for c in SAMPLE}, "seed": SEED, "causes": {}}
    for cause, g in d.groupby("cause"):
        splits = collections.Counter(tuple(sorted((a, b))) for a, b in zip(g.a, g.b) if a != b)
        audit["causes"][cause] = {
            "n": int(len(g)), "agree": float((g.a == g.b).mean()), "kappa": kappa(list(g.a), list(g.b)),
            "not_stated": float((g.a == "not_stated").mean()), "other_stated": float((g.a == "other_stated").mean()),
            "other_reasons": sorted(g.loc[g.a == "other_stated", "other"].tolist()),
            "splits": [{"pair": list(p), "n": n} for p, n in splits.most_common()],
            "contradicted": float(g.contradicted.mean()),
            "contradicted_by_route": {("traced" if t else "registry"): float(h.contradicted.mean())
                                      for t, h in g.groupby("traced")},
            "text_causes": g.loc[g.contradicted, "text_cause"].value_counts().to_dict(),
            "first_pass": g.a.value_counts().to_dict()}
    with open(OUT, "w") as f:
        json.dump(audit, f, indent=1)
    print(json.dumps(audit, indent=1))


def search() -> None:
    rows = stop_rows()
    items = describe_items(rows)[0]
    decided = llm.current_decisions(SUBCAUSE_TASK, items)
    apply_text(rows, decided, llm.current_decisions(SUBCAUSE_TASK, recast_items(items, decided)))
    rng = np.random.default_rng(SEED)
    picked = set()
    for cause, n in SEARCH_SAMPLE.items():
        keys = sorted(key for key, *_, row in rows
                      if row["cause"] == cause and row["subcause"] in (None, "not_stated"))
        picked.update(rng.choice(keys, size=min(n, len(keys)), replace=False))
    bundles = search_items([r for r in rows if r[0] in picked])
    found = {k: o for k, _, o in llm.decisions(llm.run(SEARCH_TASK, bundles))}
    d = pd.DataFrame([{"key": k, "drug": bundles[k]["drug"], "disease": bundles[k]["disease"],
                       "cause": bundles[k]["cause"], "cause_found": o["cause_found"],
                       "subcause": o["subcause"], "support": o["support"],
                       "other": o["other_reason"], "quote": o["quote"], "sources": " ".join(o["sources"]),
                       "rationale": o["rationale"]} for k, o in found.items()])
    d.to_csv(SEARCH_REVIEW, index=False)
    pilot = {"sample": {c: int((d.cause == c).sum()) for c in SEARCH_SAMPLE}, "seed": SEED, "causes": {
        cause: {"n": int(len(g)), "support": g.support.value_counts().to_dict(),
                "cause_found": g.loc[g.cause_found != cause, "cause_found"].value_counts().to_dict(),
                "subcauses": g[g.support != "not_found"].subcause.value_counts().to_dict(),
                "other_reasons": sorted(g.loc[g.subcause == "other_stated", "other"].tolist())}
        for cause, g in d.groupby("cause")}}
    with open(SEARCH_OUT, "w") as f:
        json.dump(pilot, f, indent=1)
    print(json.dumps(pilot, indent=1))


if __name__ == "__main__":
    search() if sys.argv[1:] == ["search"] else main()
