"""Store each checked v3 tile whose verdicts are settled; list the ones still waiting for adjudication.

    .venv/bin/python analyses/model-system-atlas/drafts/v3/route_store.py [slug ...]

A tile is settled when every corrected verdict either keeps the drafter's status or carries an
adjudicated_status. Settled tiles are stored with drafts/track_store.py, which replaces the tile, so a
re-run after new tracks or verdicts is safe. With no slugs, every tile with a <slug>.check.json
is routed.
"""
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, "..", "track_store.py")
DRAFTED_BY = "DRAFTER_BRIEF_v3 / atlas-v3-2026-11-05"


def open_corrections(slug: str) -> list[str]:
    d = json.load(open(os.path.join(HERE, f"{slug}.json")))
    c = json.load(open(os.path.join(HERE, f"{slug}.check.json")))
    base = int(c.get("index_base", 1))
    out = []
    for v in c.get("entries", []):
        if v.get("verdict") != "corrected" or v.get("adjudicated_status"):
            continue
        try:
            e = d["cells"][v["cell"]][int(v["index"]) - base]
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        if v.get("proposed_status") and v["proposed_status"] != e.get("status"):
            out.append(f'{v["cell"]}#{v["index"]} {e.get("status")}->{v["proposed_status"]}')
    return out


def main() -> None:
    slugs = sys.argv[1:] or sorted(os.path.basename(p)[:-11] for p in glob.glob(os.path.join(HERE, "*.check.json")))
    for slug in slugs:
        pending = open_corrections(slug)
        if pending:
            print("ADJUDICATE", slug, pending)
            continue
        r = subprocess.run([sys.executable, STORE, os.path.join(HERE, f"{slug}.json"), "--drafted-by", DRAFTED_BY],
                           capture_output=True, text=True)
        tail = [line for line in (r.stdout + r.stderr).splitlines() if "RuntimeWarn" not in line and line.strip()]
        print("STORE" if r.returncode == 0 else "FAILED", slug, "|", tail[-1] if tail else "")


if __name__ == "__main__":
    main()
