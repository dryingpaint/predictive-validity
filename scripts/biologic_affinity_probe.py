"""Feasibility probe: is a binding affinity published before phase entry findable for biologics, and would a
potency threshold separate them? Results and the decision it supports: report/audits/biologic_affinity_probe.md.

    python -m scripts.biologic_affinity_probe
"""
from __future__ import annotations

import json
import os

from pipeline import llm
from report import frame

OUT = os.path.join(frame.REPO, "report", "audits", "biologic_affinity_probe.json")
SAMPLE, SEED = 40, 20261105
SYSTEM = """You look for the earliest published binding affinity of a biologic drug for its primary target.
Search the web (PubMed, journal articles, conference abstracts, patents, company publications). Find a measured affinity (KD, Kd, KD by SPR/BLI, IC50 or EC50 of binding or neutralisation) of this drug (or its parent antibody under a code name) for the named target, published in or before the cutoff year. Report the earliest such source.
found: true if a value published by the cutoff year exists. value_nm: the value in nM (convert pM etc.). measure: KD, IC50, EC50 or other. year: publication year. source: a URL your searches returned. If only later publications report it, found is false and give later_year. rationale: at most 40 words."""
SCHEMA = {"type": "object", "properties": {
    "found": {"type": "boolean"}, "value_nm": {"type": ["number", "null"]}, "measure": {"type": "string"},
    "year": {"type": ["integer", "null"]}, "later_year": {"type": ["integer", "null"]}, "source": {"type": "string"},
    "rationale": {"type": "string"}},
    "required": ["found", "value_nm", "measure", "year", "later_year", "source", "rationale"],
    "additionalProperties": False}
TASK = llm.Task(name="probe_biologic_affinity", prompt_version="v1", schema_version="v1", system=SYSTEM, schema=SCHEMA,
                render=lambda p: (f"Drug: {p['drug']} (codes: {', '.join(p['codes']) or '-'})\n"
                                  f"Primary target: {p['target']}\nCutoff year: {p['cutoff']}"),
                subject_type="probe", model="claude-sonnet-5", effort="medium", max_tokens=12000,
                tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}])


def main() -> None:
    e = frame.query("""SELECT e.moiety_id, e.entry_year, e.target, m.name, m.code_names
                       FROM preclin.evidence_entry e JOIN preclin.moiety m USING (moiety_id)
                       WHERE e.phase = 2 AND e.modality IN ('monoclonal_antibody', 'protein')
                         AND e.target IS NOT NULL""").drop_duplicates("moiety_id")
    items = {f"{r.moiety_id}|{r.entry_year}": {"drug": r.name, "codes": list(r.code_names)[:4], "target": r.target,
                                                "cutoff": int(r.entry_year) - 1}
             for r in e.sample(SAMPLE, random_state=SEED).itertuples()}
    res = [{**items[k], **o} for k, _, o in llm.decisions(llm.run(TASK, items))]
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1)
    found = [r for r in res if r["found"]]
    vals = sorted(r["value_nm"] for r in found if r["value_nm"] is not None)
    print(f"decided {len(res)} of {len(items)}; published before entry {len(found)}; "
          f"only later {sum(1 for r in res if not r['found'] and r['later_year'])}")
    print(f"values (nM) {vals}; <=100 nM {sum(v <= 100 for v in vals)}, <=1 nM {sum(v <= 1 for v in vals)}")


if __name__ == "__main__":
    main()
