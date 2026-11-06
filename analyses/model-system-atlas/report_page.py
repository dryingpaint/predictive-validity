"""Render the atlas report page from the database: the drafted tiles' track records, the register of every
mechanism, and the drafter-checker agreement.

    .venv/bin/python analyses/model-system-atlas/report_page.py [--interim]

Reads preclin.atlas_* (migration 133) and writes report/atlas.html beside this file from
report/template.html, with the data embedded. --interim labels the page as drawn from a programs build
that was mid-rebuild.
"""
import argparse
import glob
import json
import math
import os
import sys
from collections import Counter
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))

from report import frame

QUESTIONS = ["engagement", "dose", "efficacy", "safety"]
STATUSES = ["same", "neg", "other", "contra", "retro", "untested"]
HEADLINE = ["same", "neg", "other", "contra"]  # statuses a prospective track can set the headline with, best first


def final_status(r) -> str:
    """The adjudicated status when an adjudicator decided, else the drafter's."""
    return r["adjudicated_status"] if r.get("adjudicated_status") else r["status"]


def checked_status(r) -> str:
    """The checker's reading: its proposal on a corrected entry, else the drafter's status."""
    return r["proposed_status"] if r.get("verdict") == "corrected" and r.get("proposed_status") else r["status"]


def kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa over (drafter, checker) labels."""
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n / n
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def headline(entries: list[dict], key) -> str | None:
    """A cell's headline: the best latest status among its tracks (one per model_id) that predicted before the
    patient result; untested when none did. A retrodiction is shown on its track but never sets the headline."""
    last = {}
    for e in sorted(entries, key=lambda e: (e["year"], e["seq"])):
        s = key(e)
        if s != "drop":
            last[e["model_id"]] = s
    if not last:
        return None
    tested = [s for s in last.values() if s in HEADLINE]
    return min(tested, key=HEADLINE.index) if tested else "untested"


def load() -> dict:
    build = frame.query("SELECT snapshot, n_register, n_tracked, built_at FROM preclin.atlas_build ORDER BY built_at DESC LIMIT 1")
    ents = frame.query("""
        SELECT e.mondo_id, e.mechanism_key, e.question, e.modality, e.seq, e.year, e.status, e.model_id, e.model, e.src,
               e.src_label, e.quote, e.source_tier, e.comparison_stated, e.retrodiction,
               e.patient_signal_reversed, e.confidence, e.fields, v.verdict, v.quote_found, v.proposed_status,
               v.proposed_year, v.rule, v.note AS check_note, v.adjudicated_status, v.adjudication_note
        FROM preclin.atlas_track_entry e
        LEFT JOIN preclin.atlas_track_verdict v USING (mondo_id, mechanism_key, question, modality, seq)
        ORDER BY e.mondo_id, e.mechanism_key, e.question, e.modality, e.seq""")
    reg = frame.query("""
        SELECT i.area, i.label AS disease, i.mondo_id, i.n_programs, r.mechanism_key, m.label AS mechanism,
               r.n_entities, r.share::float AS share, r.tracked, r.furthest_phase, r.modality_groups
        FROM preclin.atlas_register r JOIN preclin.atlas_indication i USING (mondo_id)
        JOIN preclin.atlas_mechanism m USING (mechanism_key)
        ORDER BY i.area, i.n_programs DESC, r.n_entities DESC, m.label""")
    drafted = set(zip(ents.mondo_id, ents.mechanism_key)) if len(ents) else set()

    tiles, pairs = [], []
    reg_idx = {(r.mondo_id, r.mechanism_key): r for r in reg.itertuples()}
    for (mondo, mech), g in (ents.groupby(["mondo_id", "mechanism_key"]) if len(ents) else []):
        r = reg_idx.get((mondo, mech))
        recs = [dict(x) for _, x in g.iterrows()]
        for x in recs:
            x["fields"] = x["fields"] or {}
            x["final"] = final_status(x)
            for k, v in list(x.items()):
                if v is not None and hasattr(v, "item"):
                    x[k] = v.item()
                elif isinstance(v, float) and math.isnan(v):
                    x[k] = None
        cells = {}
        for q in QUESTIONS:
            cq = [x for x in recs if x["question"] == q]
            for mod in {x["modality"] for x in cq}:
                cell = [x for x in cq if x["modality"] == mod]
                if any(x.get("verdict") for x in cell):
                    pairs.append((headline(cell, lambda e: e["status"]), headline(cell, checked_status)))
            for x in cq:  # a checker's corrected year stands when the status is unchanged
                if x.get("verdict") == "corrected" and x.get("proposed_year") and x["final"] == x["status"]:
                    x["year"] = int(x["proposed_year"])
            cells[q] = [{"modality": x["modality"], "seq": x["seq"], "year": x["year"], "status": x["final"],
                         "drafted": x["status"], "model": x["model"], "model_id": x["model_id"], "src": x["src"],
                         "src_label": x["src_label"], "quote": x["quote"], "tier": x["source_tier"],
                         "stated": x["comparison_stated"], "retro": x["retrodiction"],
                         "level": x["fields"].get("prediction_level"),
                         "reversed": x["patient_signal_reversed"], "confidence": x["confidence"],
                         "note": x["fields"].get("note"), "short": x["fields"].get("short"),
                         "judgement": x["fields"].get("judgement"), "verdict": x.get("verdict"),
                         "proposed": x.get("proposed_status"), "rule": x.get("rule"), "check_note": x.get("check_note"),
                         "adjudicated": x.get("adjudicated_status"), "adjudication_note": x.get("adjudication_note")}
                        for x in cq if x["final"] != "drop"]
        tiles.append({"mondo_id": mondo, "mechanism_key": mech, "disease": r.disease if r else mondo,
                      "area": r.area if r else "", "mechanism": r.mechanism if r else mech,
                      "n": int(r.n_entities) if r else None, "share": r.share if r else None,
                      "modalities": list(r.modality_groups) if r else [], "cells": cells})

    register = []
    for (area, disease, mondo, n_ind), g in reg.groupby(["area", "disease", "mondo_id", "n_programs"], sort=False):
        register.append({"area": area, "disease": disease, "mondo_id": mondo, "n_programs": int(n_ind),
                         "mechanisms": [{"label": x.mechanism, "key": x.mechanism_key, "n": int(x.n_entities),
                                         "share": round(x.share, 3), "tracked": bool(x.tracked),
                                         "drafted": (mondo, x.mechanism_key) in drafted,
                                         "furthest": None if x.furthest_phase != x.furthest_phase else int(x.furthest_phase),
                                         "modalities": list(x.modality_groups)} for x in g.itertuples()]})
    agree = sum(a == b for a, b in pairs)
    b = build.iloc[0] if len(build) else None
    return {"generated": str(date.today()),
            "build": {"snapshot": str(b.snapshot), "n_register": int(b.n_register), "n_tracked": int(b.n_tracked)} if b is not None else {},
            "tiles": sorted(tiles, key=lambda t: (t["area"], t["disease"], t["mechanism"])),
            "register": register,
            "agreement": {"cells": len(pairs), "agree": agree, "kappa": kappa(pairs)}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interim", action="store_true")
    a = ap.parse_args()
    data = load()
    data["interim"] = a.interim
    checks = [json.load(open(f)) for f in glob.glob(os.path.join(HERE, "drafts", "v3", "*.check.json"))]
    data["open"] = {"rule_questions": sum(len(c.get("rule_questions") or []) for c in checks),
                    "missed": sum(len(c.get("missing") or []) for c in checks)}
    tpl = open(os.path.join(HERE, "report", "template.html")).read()
    out = os.path.join(HERE, "report", "atlas.html")
    open(out, "w").write(tpl.replace("/*__DATA__*/null", json.dumps(data, default=str)))
    print(f"wrote {out}: {len(data['tiles'])} tiles, {len(data['register'])} diseases, agreement {data['agreement']}")


if __name__ == "__main__":
    main()
