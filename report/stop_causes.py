"""Why Phase 2/3 programs stopped, after correcting and inferring the causes the registry leaves out.

    python -m report.stop_causes

Reads preclin.stop_cause (pipeline.stop_causes assemble), preclin.stop_signal and the held-out
validation decisions; writes report/output/stop_causes/numbers.json and programs.csv. Intervals
resample entities.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from pipeline.stop_causes import CAUSES, REGISTRY_CAUSE, TASK
from report import frame
from report.section1 import SEED

OUT = os.path.join(frame.REPO, "report", "output", "stop_causes")
N_BOOT = 1000


def load() -> pd.DataFrame:
    d = frame.query("""SELECT c.*, s.drug_continued_elsewhere, s.drug_approved_anywhere, s.sponsor_active_after,
                              s.target_peers_stopped, s.has_results
                       FROM preclin.stop_cause c JOIN preclin.stop_signal s USING (moiety_id, mondo_id, phase)""")
    d["recorded_cause"] = d.recorded_reason.map(REGISTRY_CAUSE).fillna("unknown")
    d["likely"] = d.likely_cause.fillna(d.cause)
    return d


def distribution(d: pd.DataFrame, col: str, rng: np.random.Generator) -> dict:
    counts = pd.crosstab(d.moiety_id, d[col]).reindex(columns=CAUSES, fill_value=0).to_numpy()
    draws = np.array([counts[rng.integers(0, len(counts), len(counts))].sum(axis=0) for _ in range(N_BOOT)])
    frac = draws / draws.sum(axis=1, keepdims=True)
    total = counts.sum()
    return {c: {"n": int(counts[:, i].sum()), "share": float(counts[:, i].sum() / total),
                "lo": float(np.percentile(frac[:, i], 2.5)), "hi": float(np.percentile(frac[:, i], 97.5))}
            for i, c in enumerate(CAUSES)}


def validation() -> dict:
    v = frame.query("""
        SELECT DISTINCT ON (d.subject_key) d.subject_key, d.parsed_output
        FROM pv_evidence.llm_decision d JOIN pv_evidence.llm_decision_run r USING (decision_run_id)
        WHERE d.task = %s AND r.prompt_version = %s AND d.validation_status = 'validated'
          AND d.subject_key LIKE '%%|heldout'
        ORDER BY d.subject_key, d.created_at DESC""", (TASK.name, TASK.prompt_version))
    if v.empty:
        return {"n": 0}
    v["key"] = v.subject_key.str.removesuffix("|heldout")
    reasons = frame.query("""SELECT moiety_id, mondo_id, phase, recorded_reason FROM preclin.stop_cause
                             WHERE cause_source = 'registry'""")
    reasons["key"] = [f"{m}|{d}|{p}" for m, d, p in zip(reasons.moiety_id, reasons.mondo_id, reasons.phase)]
    v = v.merge(reasons[["key", "recorded_reason"]], on="key")
    v["truth"] = v.recorded_reason.map(REGISTRY_CAUSE)
    v["cause"] = [o["cause"] for o in v.parsed_output]
    v["likely"] = [o["likely_cause"] for o in v.parsed_output]
    v["evidence"] = [o["evidence_kind"] for o in v.parsed_output]
    known = v[v.cause != "unknown"]
    out = {"n": int(len(v)), "resolved": float((v.cause != "unknown").mean()),
           "cause_accuracy_resolved": float((known.cause == known.truth).mean()) if len(known) else None,
           "cause_kappa_resolved": float(cohen_kappa_score(known.truth, known.cause)) if len(known) > 1 else None,
           "likely_accuracy": float((v.likely == v.truth).mean()),
           "likely_kappa": float(cohen_kappa_score(v.truth, v.likely)),
           "by_truth": {t: {"n": int(len(g)), "resolved": float((g.cause != "unknown").mean()),
                            "cause_correct": float((g.cause == t).mean()), "likely_correct": float((g.likely == t).mean())}
                        for t, g in v.groupby("truth")},
           "by_evidence": {e: {"n": int(len(g)), "correct": float((g.cause == g.truth).mean())}
                           for e, g in known.groupby("evidence")},
           "confusion_likely": pd.crosstab(v.truth, v.likely).to_dict()}
    return out


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(SEED)
    d = load()
    d.drop(columns=["sources"]).to_csv(os.path.join(OUT, "programs.csv"), index=False)
    infer = d[d.cause_source != "registry"]
    n = {"stops": int(len(d)), "entities": int(d.moiety_id.nunique()),
         "recorded": distribution(d, "recorded_cause", rng),
         "evidence": distribution(d, "cause", rng),
         "likely": distribution(d, "likely", rng),
         "inferred": {"programs": int(len(infer)),
                      "by_reason": infer.recorded_reason.value_counts().to_dict(),
                      "resolved": float((infer.cause != "unknown").mean()),
                      "resolved_n": int((infer.cause != "unknown").sum()),
                      "likely_resolved": float((infer.likely != "unknown").mean()),
                      "evidence": infer.evidence_kind.value_counts().to_dict(),
                      "cause": infer.cause.value_counts().to_dict(),
                      "likely": infer.likely.value_counts().to_dict(),
                      "no_decision": int(infer.llm_decision_id.isna().sum())},
         "corrected": {"programs": int((d.cause_source == "corrected").sum()),
                       "to": d[d.cause_source == "corrected"].likely.value_counts().to_dict()},
         "signals": {c: {"sponsor_inactive": float((g.sponsor_active_after == False).mean()),  # noqa: E712
                         "drug_continued": float(g.drug_continued_elsewhere.mean()), "n": int(len(g))}
                     for c, g in infer.groupby("likely")},
         "validation": validation()}
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(n, f, indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x))


if __name__ == "__main__":
    main()
