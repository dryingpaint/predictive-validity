"""Lint the tile drafts in drafts/ against the rules in `DRAFTER_BRIEF.md`.

    .venv/bin/python analyses/model-system-atlas/drafts/lint.py [draft.json ...]

Findings: empty cells (no model relied on), consecutive same-status
entries on one track, unknown keys, unsorted years, missing fields, and a status without the fields
its decision requires. A track is one model system's entries in a cell (its `model_id`), kept apart per
modality where a multi-modality tile splits dose and safety.
"""
import glob
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS = ("engagement", "dose", "efficacy", "safety")
STAT = {"same", "other", "neg", "contra", "untested", "retro"}
MATCHED = {"same", "neg", "other", "retro"}
KEYS = {"year", "status", "model", "note", "short", "src", "srcLabel", "quote", "confidence", "subjects",
        "comparison_stated", "epub_year", "print_year", "registry_date", "model_filed", "product_in_model",
        "magnitude", "source_calls_it", "population", "model_first_use_year", "judgement", "reason",
        "patient_trials", "strengthens", "prediction_level", "modality", "model_id", "source_tier", "model_src",
        "model_src_tier", "trial_unreported", "patient_signal_reversed", "model_kind", "retrodiction",
        "imported_from", "magnitude_basis", "confidence_note", "readout_tier", "blocked_by",
        "margin_stated", "effect_size", "class_threshold", "endpoint_role", "outcome_tested", "untested_reason"}
REQUIRED = ("model_id", "subjects", "comparison_stated", "source_tier", "model_kind", "retrodiction",
            "confidence", "magnitude", "source_calls_it")
ENUM = {
    "confidence": {"high", "medium", "low"},
    "subjects": {"patients", "healthy_volunteers", "mixed", None},
    "model_kind": {"animal", "human_challenge", "ex_vivo", "in_silico", "human_genetic", "cross_indication"},
    "magnitude": {"within_2x", "off_by_2-5x", "off_by_>5x", "direction_only", "null", "opposite", None},
    "source_calls_it": {"match", "miss", "scaling", "partial", "unresolved", "over_predicted", None},
    "readout_tier": {"direct", "proximal", "downstream", None},
    "blocked_by": {"toxicity", None},
    "endpoint_role": {"primary", "poc_gate", None},
    "outcome_tested": {None, "positive", "negative", "negative_confounded"},
    "prediction_level": {"class", "patient", None},
    "untested_reason": {"no_prediction", "not_measured", "unpublished", "unsettled", None},
}
ONLY_IN = {"readout_tier": "engagement", "blocked_by": "dose", "margin_stated": "dose",
           "endpoint_role": "efficacy", "outcome_tested": "efficacy", "imported_from": "safety"}
MODALITY = {"small molecule", "antibody", "ADC", "protein", "peptide", "oligo", "cell therapy", "gene therapy", "other"}


def rule_findings(q: str, e: dict, prev: dict | None) -> list[str]:
    """The rules one entry breaks, given the entry before it on the same track."""
    out = [f"field missing: {k}" for k in REQUIRED if k not in e]
    out += [f"{k}={e[k]!r} not in enum" for k, allowed in ENUM.items() if k in e and e[k] not in allowed]
    out += [f"{k} only belongs on {cell}" for k, cell in ONLY_IN.items() if e.get(k) not in (None, False) and q != cell]
    s, tier = e.get("status"), e.get("source_tier")
    if tier not in (1, 2, 3, 4, 5):
        out.append(f"source_tier {tier!r} not 1-5")
    if (tier in (4, 5) or e.get("comparison_stated") is False) and s not in ("untested", None):
        if not e.get("model_src"):
            out.append("paired or tier 4-5 comparison without model_src")
        if e.get("model_src_tier") not in (1, 2, 3):
            out.append("model_src_tier must be 1-3")
    if tier == 5 and e.get("trial_unreported") is not True:
        out.append("tier 5 source without trial_unreported")
    if s == "retro" and e.get("retrodiction") is not True:
        out.append("retro without retrodiction: true")
    if e.get("retrodiction") is True and s not in ("retro", "contra"):
        out.append(f"retrodiction scored {s!r}; must be retro or contra")
    if s == "neg" and (e.get("effect_size") is None or e.get("class_threshold") is None):
        out.append("neg without effect_size and class_threshold")
    if s == "other" and q != "safety":
        out.append("other outside safety")
    if e.get("blocked_by") == "toxicity" and e.get("margin_stated") is not True:
        out.append("blocked_by toxicity without margin_stated")
    if q == "engagement" and s not in ("untested", None) and "readout_tier" not in e:
        out.append("engagement entry without readout_tier")
    if prev and prev.get("status") == "contra" and s in MATCHED:
        if e.get("patient_signal_reversed") is not True:
            out.append("contra -> matched on one track without patient_signal_reversed")
        if e.get("patient_signal_reversed") is True and tier not in (1, 2, 3, 4):
            out.append("patient_signal_reversed needs a tier 1-4 source")
    return out


def lint(paths: list[str]) -> tuple[Counter, list[tuple[str, str, str]]]:
    extra, issues = Counter(), []
    for p in paths:
        d = json.load(open(p))
        cid = os.path.basename(p)[:-5]
        for k in ("order", "area", "disease", "mondo_id", "population", "mechanism", "label", "cells"):
            if k not in d:
                issues.append((cid, "top-level", f"missing {k}"))
        if not d.get("mechanism_key"):
            issues.append((cid, "top-level", "mechanism_key missing (the tile's key in preclin.atlas_register)"))
        groups = d.get("modality_groups")
        if not isinstance(groups, list) or not groups or not set(groups) <= MODALITY:
            issues.append((cid, "top-level", f"modality_groups {groups!r}"))
        if not isinstance(d.get("class_share"), (int, float)):
            issues.append((cid, "top-level", "class_share missing"))
        split = isinstance(groups, list) and len(groups) > 1

        def track(e: dict):
            """The track an entry belongs to: its model system, per modality in a split cell."""
            return (e.get("modality") if split and q in ("dose", "safety") else None, e.get("model_id"))

        for q in QUESTIONS:
            strip = d.get("cells", {}).get(q)
            if strip is None:
                issues.append((cid, q, "cell missing"))
                continue
            if not strip:
                issues.append((cid, q, "empty cell (no model relied on)"))
                continue
            last: dict = {}
            for i, e in enumerate(strip, 1):
                prev = last.get(track(e))
                if e.get("modality") is not None and e["modality"] not in (groups or []):
                    issues.append((cid, q, f"entry {i}: modality {e['modality']!r} not in modality_groups"))
                if split and q == "dose" and e.get("modality") is None:
                    issues.append((cid, q, f"entry {i}: dose entry without modality in a multi-modality tile"))
                if e.get("status") not in STAT:
                    issues.append((cid, q, f"bad status {e.get('status')!r}"))
                if not isinstance(e.get("year"), int):
                    issues.append((cid, q, f"year not int: {e.get('year')!r}"))
                if prev and e.get("status") == prev.get("status") and not e.get("strengthens"):
                    issues.append((cid, q, f"same-status entry {i} ({e['status']}) on one track without strengthens"))
                issues += [(cid, q, f"entry {i}: {m}") for m in rule_findings(q, e, prev)]
                last[track(e)] = e
                extra.update(k for k in e if k not in KEYS)
            for key in {track(e) for e in strip}:
                ys = [e.get("year") for e in strip if track(e) == key]
                if sorted(y for y in ys if isinstance(y, int)) != ys:
                    issues.append((cid, q, "years not sorted" + (f" {key}" if key != (None, None) else "")))
    return extra, issues


def main():
    paths = sys.argv[1:] or sorted(p for p in glob.glob(os.path.join(HERE, "*-*.json"))
                                   if not p.endswith((".check.json", ".models.json")))
    extra, issues = lint(paths)
    print("unknown keys:", dict(extra))
    for i in issues:
        print(*i, sep=" | ")
    print(len(issues), "findings")


if __name__ == "__main__":
    main()
