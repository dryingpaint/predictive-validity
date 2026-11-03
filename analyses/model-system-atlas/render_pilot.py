"""Render the pilot drafts through figure.py without touching contexts/ or atlas.png.

    .venv/bin/python analyses/model-system-atlas/render_pilot.py [--raw]

Reads drafts/*.json (skipping *.check.json), applies each draft's checker corrections
(entries with verdict "corrected" carrying proposed_status / proposed_year) unless --raw, and writes
drafts/pilot_render/atlas.png.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import figure  # noqa: E402

DRAFTS = os.path.join(HERE, "drafts")
OUT = os.path.join(DRAFTS, "pilot_render")


def index_base(check: dict) -> int:
    """Checkers were told to number from 1; some numbered from 0. Honour `index_base`, else infer."""
    if check.get("index_base") is not None:
        return int(check["index_base"])
    return 0 if any(e.get("index") == 0 for e in check.get("entries", [])) else 1


def apply_check(row: dict, check: dict) -> dict:
    base = index_base(check)
    for e in check.get("entries", []):
        if e.get("verdict") != "corrected" or e.get("index") is None:
            continue
        cell = row["cells"].get(e["cell"], [])
        i = int(e["index"]) - base
        if 0 <= i < len(cell):
            if str(e.get("proposed_status", "")).startswith("drop"):
                cell[i]["_drop"] = True
                continue
            if e.get("proposed_status"):
                cell[i]["status"] = e["proposed_status"]
            if e.get("proposed_year"):
                cell[i]["year"] = int(e["proposed_year"])
            cell[i]["reason"] = (cell[i].get("reason") or "") + " [checked]"
    for q, cell in row["cells"].items():
        row["cells"][q] = [e for e in cell if not e.get("_drop")]
    return row


def load_pilot(raw: bool = False) -> list[dict]:
    rows = []
    for path in sorted(glob.glob(os.path.join(DRAFTS, "*.json"))):
        if path.endswith(".check.json"):
            continue
        row = json.load(open(path))
        check_path = path[:-5] + ".check.json"
        if not raw and os.path.exists(check_path):
            row = apply_check(row, json.load(open(check_path)))
            row["label"] = row.get("label", row["disease"]) + " ✓"
        rows.append(row)
    return sorted(rows, key=lambda r: r["order"])


if __name__ == "__main__":
    raw = "--raw" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    figure.load = lambda: load_pilot(raw)
    figure.HERE = OUT
    figure.main()
    print(os.path.join(OUT, "atlas.png"))
