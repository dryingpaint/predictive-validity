"""Merge a tile's added model systems (<slug>.models.json) into its draft as parallel tracks.

    .venv/bin/python analyses/model-system-atlas/drafts/v3/merge_models.py <slug> [--check]

Each added model's entries are appended to their cells with `parallel: true` and the model's `model_id`,
`model` and `model_kind` filled in where the entry leaves them out. Entries already in the draft keep their
positions, so the indices in <slug>.check.json still point at them. With --check the merged draft is linted
in a temporary file and nothing is written; without it the merged draft replaces <slug>.json, after which
the added entries carry their own checker verdicts.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LINT = os.path.join(HERE, "..", "lint.py")
DEFAULTS = {"model_change": False, "retrodiction": False, "patient_signal_reversed": False}


def merged(slug: str) -> dict:
    d = json.load(open(os.path.join(HERE, f"{slug}.json")))
    added = json.load(open(os.path.join(HERE, f"{slug}.models.json"))).get("added_models") or []
    have = {(q, e.get("model_id"), e.get("year"), e.get("status")) for q, s in d["cells"].items() for e in s}
    for m in added:
        for q, entries in (m.get("cells") or {}).items():
            for e in entries:
                e = {**DEFAULTS, **e, "parallel": True}
                e.setdefault("model_id", m["model_id"])
                e.setdefault("model", m.get("model"))
                e.setdefault("model_kind", m.get("model_kind"))
                e.setdefault("prediction_level", m.get("prediction_level"))
                e.setdefault("model_first_use_year", m.get("model_first_use_year"))
                if (q, e["model_id"], e.get("year"), e.get("status")) not in have:
                    d["cells"].setdefault(q, []).append(e)
    return d


def main() -> None:
    slug, check = sys.argv[1], "--check" in sys.argv[2:]
    d = merged(slug)
    if check:
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, f"{slug}.json")
            json.dump(d, open(p, "w"), indent=1)
            r = subprocess.run([sys.executable, LINT, p], capture_output=True, text=True)
            print(r.stdout.strip())
        return
    json.dump(d, open(os.path.join(HERE, f"{slug}.json"), "w"), indent=1, ensure_ascii=False)
    n = sum(1 for s in d["cells"].values() for e in s if e.get("parallel"))
    print(f"{slug}: {n} parallel entries merged")


if __name__ == "__main__":
    main()
