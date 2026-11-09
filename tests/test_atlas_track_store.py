"""analyses/model-system-atlas/drafts/track_store.py: the rows a stored tile writes, verdicts keyed to the
entries they name. A real draft, a fake cursor, no database."""
from __future__ import annotations

import json
import os
import shutil
import sys

DRAFTS = os.path.join(os.path.dirname(__file__), "..", "analyses", "model-system-atlas", "drafts")
sys.path.insert(0, DRAFTS)
import track_store  # noqa: E402

SLUG = "plasma-cell-myeloma-tnfrsf17-directed-depleters"  # three modalities, so dose seq counts per modality


class Cursor:
    def __init__(self):
        self.sql = []

    def execute(self, sql, params=None):
        self.sql.append((sql, params))

    def fetchone(self):
        return (True,)  # a tracked tile of atlas_register


def test_store_replaces_the_tile_and_keys_each_verdict_to_its_entry(tmp_path, monkeypatch):
    for ext in (".json", ".check.json"):
        shutil.copy(os.path.join(DRAFTS, SLUG + ext), tmp_path / (SLUG + ext))
    written = {}
    monkeypatch.setattr(track_store, "execute_values", lambda cur, sql, rows: written.setdefault(sql.split()[2], rows))
    cur = Cursor()
    n = track_store.store(str(tmp_path / (SLUG + ".json")), "test", cur)

    draft = json.load(open(tmp_path / (SLUG + ".json")))
    check = json.load(open(tmp_path / (SLUG + ".check.json")))
    entries, verdicts = written["preclin.atlas_track_entry"], written["preclin.atlas_track_verdict"]
    assert n == len(entries) == sum(len(v) for v in draft["cells"].values())
    assert any("DELETE FROM preclin.atlas_track_entry" in s for s, _ in cur.sql)

    by_key = {(r[2], r[3], r[4]): r for r in entries}  # (question, modality, seq) -> stored entry row
    assert len(by_key) == len(entries)
    base = int(check.get("index_base", 1))
    for v, row in zip(check["entries"], verdicts):
        named = draft["cells"][v["cell"]][int(v["index"]) - base]
        stored = by_key[(row[2], row[3], row[4])]
        assert (stored[5], stored[6], stored[10]) == (f'{named["model_id"]} / {named["drug"]} / {named["route"]}',
                                                     named["year"], named["quote"])
