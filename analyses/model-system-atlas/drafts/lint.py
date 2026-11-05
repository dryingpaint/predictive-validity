"""Schema lint for drafts/*.json against figure.py's assumptions and the drafter briefs.

    .venv/bin/python analyses/model-system-atlas/drafts/lint.py [draft.json ...]

Every draft: empty cells (no model relied on), consecutive same-status entries on one track, unknown
keys, unsorted years. A track is one model system's entries in a cell (its `model_id`; v2 drafts have one
track per cell), kept apart per modality where a multi-modality tile splits dose and safety.
A draft that declares `"schema": 3` is also held to the v3 rules (`RULES_V3_PROPOSAL.md`): the v3
fields are present, and each status carries the fields its decision requires.
"""
import glob
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS = ("engagement", "dose", "efficacy", "safety")
STAT = {"same", "other", "neg", "contra", "untested"}
KEYS = {"year", "status", "model", "note", "short", "src", "srcLabel", "quote", "confidence", "subjects",
        "comparison_stated", "epub_year", "print_year", "registry_date", "model_filed", "product_in_model",
        "magnitude", "source_calls_it", "population", "model_first_use_year", "judgement", "reason",
        "patient_trials"}

STAT_V3 = STAT | {"retro"}
MATCHED = {"same", "neg", "other", "retro"}
KEYS_V3 = KEYS | {"strengthens", "prediction_level", "modality", "model_id", "source_tier", "model_src", "model_src_tier", "trial_unreported", "patient_signal_reversed",
                  "model_kind", "retrodiction", "imported_from", "magnitude_basis",
                  "confidence_note", "readout_tier", "derived_from", "blocked_by", "margin_stated",
                  "effect_size", "class_threshold", "endpoint_role", "outcome_tested"}
REQUIRED_V3 = ("model_id", "subjects", "comparison_stated", "source_tier", "model_kind", "retrodiction",
               "confidence", "magnitude", "source_calls_it")
ENUM_V3 = {
    "confidence": {"high", "medium", "low"},
    "subjects": {"patients", "healthy_volunteers", "mixed", None},
    "model_kind": {"animal", "human_challenge", "ex_vivo", "in_silico", "human_genetic", "cross_indication"},
    "magnitude": {"within_2x", "off_by_2-5x", "off_by_>5x", "direction_only", "null", "opposite", None},
    "source_calls_it": {"match", "miss", "scaling", "partial", "unresolved", "over_predicted", None},
    "readout_tier": {"direct", "proximal", "downstream", None},
    "derived_from": {"efficacy", None},
    "blocked_by": {"toxicity", None},
    "endpoint_role": {"primary", "poc_gate", None},
    "outcome_tested": {None, "positive", "negative", "negative_confounded"},
    "prediction_level": {"class", "patient", None},
}
ONLY_IN = {"readout_tier": "engagement", "derived_from": "dose", "blocked_by": "dose", "margin_stated": "dose",
           "endpoint_role": "efficacy", "outcome_tested": "efficacy", "imported_from": "safety"}
MODALITY = {"small molecule", "antibody", "ADC", "protein", "peptide", "oligo", "cell therapy", "gene therapy", "other"}


def v3_entry(q: str, e: dict, prev: dict | None) -> list[str]:
    """The v3 rules one entry breaks, given the entry before it on the same track."""
    out = [f"v3 field missing: {k}" for k in REQUIRED_V3 if k not in e]
    out += [f"v3 {k}={e[k]!r} not in enum" for k, allowed in ENUM_V3.items() if k in e and e[k] not in allowed]
    out += [f"{k} only belongs on {cell}" for k, cell in ONLY_IN.items() if e.get(k) not in (None, False) and q != cell]
    s, tier = e.get("status"), e.get("source_tier")
    if tier not in (1, 2, 3, 4, 5):
        out.append(f"source_tier {tier!r} not 1-5")
    if (tier in (4, 5) or e.get("comparison_stated") is False) and s not in ("untested", None):
        if not e.get("model_src"):
            out.append("paired or tier 4-5 comparison without model_src")
        if e.get("model_src_tier") not in (1, 2, 3):
            out.append("model_src_tier must be 1-3 (decision 2)")
    if tier == 5 and e.get("trial_unreported") is not True:
        out.append("tier 5 source without trial_unreported (decision 2)")
    if s == "retro" and e.get("retrodiction") is not True:
        out.append("retro without retrodiction: true (decision 10)")
    if e.get("retrodiction") is True and s not in ("retro", "contra"):
        out.append(f"retrodiction scored {s!r}; must be retro or contra (decision 10)")
    if s == "neg" and (e.get("effect_size") is None or e.get("class_threshold") is None):
        out.append("neg without effect_size and class_threshold (decision 13)")
    if s == "other" and q != "safety":
        out.append("other outside safety (decision 13)")
    if e.get("blocked_by") == "toxicity" and e.get("margin_stated") is not True:
        out.append("blocked_by toxicity without margin_stated (decision 16)")
    if e.get("blocked_by") and e.get("derived_from"):
        out.append("a toxicity block is never derived_from efficacy (decision 16)")
    if q == "engagement" and s not in ("untested", None) and "readout_tier" not in e:
        out.append("engagement entry without readout_tier (decision 15)")
    if prev and prev.get("status") == "contra" and s in MATCHED:
        if e.get("patient_signal_reversed") is not True:
            out.append("contra -> matched on one track without patient_signal_reversed (decision 6)")
        if e.get("patient_signal_reversed") is True and tier not in (1, 2, 3, 4):
            out.append("patient_signal_reversed needs a tier 1-4 source (decision 6)")
    return out


def lint(paths: list[str]) -> tuple[Counter, list[tuple[str, str, str]]]:
    extra, issues = Counter(), []
    for p in paths:
        d = json.load(open(p))
        cid = os.path.basename(p)[:-5]
        v3 = d.get("schema") == 3
        for k in ("order", "area", "disease", "mondo_id", "population", "mechanism", "label", "cells"):
            if k not in d:
                issues.append((cid, "top-level", f"missing {k}"))
        if v3:
            if not d.get("mechanism_key"):
                issues.append((cid, "top-level", "mechanism_key missing (the tile's key in preclin.atlas_register)"))
            groups = d.get("modality_groups")
            if not isinstance(groups, list) or not groups or not set(groups) <= MODALITY:
                issues.append((cid, "top-level", f"modality_groups {groups!r} (decision 12)"))
            if not isinstance(d.get("class_share"), (int, float)):
                issues.append((cid, "top-level", "class_share missing (decision 12)"))
        split = v3 and isinstance(d.get("modality_groups"), list) and len(d["modality_groups"]) > 1

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
                if v3 and e.get("modality") is not None and e["modality"] not in (d.get("modality_groups") or []):
                    issues.append((cid, q, f"entry {i}: modality {e['modality']!r} not in modality_groups (decision 12)"))
                if split and q == "dose" and e.get("modality") is None:
                    issues.append((cid, q, f"entry {i}: dose entry without modality in a multi-modality tile (decision 12)"))
                if e.get("status") not in (STAT_V3 if v3 else STAT):
                    issues.append((cid, q, f"bad status {e.get('status')!r}"))
                if not isinstance(e.get("year"), int):
                    issues.append((cid, q, f"year not int: {e.get('year')!r}"))
                if prev and e.get("status") == prev.get("status") and not (v3 and e.get("strengthens")):
                    issues.append((cid, q, f"same-status entry {i} ({e['status']}) on one track without strengthens"))
                if v3:
                    issues += [(cid, q, f"entry {i}: {m}") for m in v3_entry(q, e, prev)]
                last[track(e)] = e
                extra.update(k for k in e if k not in (KEYS_V3 if v3 else KEYS))
            for key in {track(e) for e in strip}:
                ys = [e.get("year") for e in strip if track(e) == key]
                if sorted(y for y in ys if isinstance(y, int)) != ys:
                    issues.append((cid, q, "years not sorted" + (f" {key}" if key != (None, None) else "")))
    return extra, issues


def main():
    paths = sys.argv[1:] or sorted(p for p in glob.glob(os.path.join(HERE, "*.json")) if not p.endswith(".check.json"))
    extra, issues = lint(paths)
    print("unknown keys:", dict(extra))
    for i in issues:
        print(*i, sep=" | ")
    print(len(issues), "findings")


if __name__ == "__main__":
    main()
