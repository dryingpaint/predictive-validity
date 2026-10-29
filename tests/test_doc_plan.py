"""report.doc: the sections and figures a publish writes into the doc."""
from __future__ import annotations

import json

from report import doc, frame

TAB = """# Report

<!-- not published -->

## Results

LOA is 9.8%.

![Rates](report/output/figures/rates.png)

## Methods

Programs are counted once.
"""


def setup(tmp_path, monkeypatch, tab: str, figure: bytes = b"png-1"):
    (tmp_path / "report/output/figures").mkdir(parents=True)
    (tmp_path / "report/output/figures/rates.png").write_bytes(figure)
    (tmp_path / "REPORT.md").write_text(tab)
    monkeypatch.setattr(frame, "REPO", str(tmp_path))
    monkeypatch.setattr(doc, "STATE", str(tmp_path / "doc.json"))
    monkeypatch.setattr(doc, "PLAN", str(tmp_path / "plan.json"))


def publish(tmp_path):
    """The state after publishing TAB, with its figure uploaded as blob/1."""
    sections = {s["key"]: s["hash"] for s in doc.sections(TAB)}
    state = {"doc": {"id": "d"}, "tabs": {"REPORT.md": {"node": "n", "rev": 5, "sections": sections}},
             "figures": {"report/output/figures/rates.png": {"hash": doc.sha(b"png-1"), "blob": "blob/1",
                                                             "published": "blob/1"}}}
    (tmp_path / "doc.json").write_text(json.dumps(state))


def plan(tmp_path) -> dict:
    doc.plan(None)
    return json.loads((tmp_path / "plan.json").read_text())


def test_unchanged_report_writes_nothing(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, TAB)
    publish(tmp_path)
    assert plan(tmp_path)["sections"] == []


def test_changed_new_and_removed_sections(tmp_path, monkeypatch):
    tab = TAB.replace("9.8%", "8.9%").replace("## Methods\n\nPrograms are counted once.\n",
                                                "## Change over time\n\nSuccess rose.\n")
    setup(tmp_path, monkeypatch, tab)
    publish(tmp_path)
    steps = {(s["action"], s.get("heading") or s["key"]): s for s in plan(tmp_path)["sections"]}
    assert set(steps) == {("replace", "Results"), ("insert", "Change over time"), ("delete", "Report > Methods")}
    assert steps[("insert", "Change over time")]["after"] == "Report > Results"
    assert "![Rates](blob/1)" in steps[("replace", "Results")]["markdown"]


def test_changed_figure_is_uploaded_before_its_section(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, TAB, figure=b"png-2")
    publish(tmp_path)
    first = plan(tmp_path)
    assert [f["path"] for f in first["figures"]] == ["report/output/figures/rates.png"] and first["sections"] == []
    doc.blob(type("Args", (), {"blobs": ["report/output/figures/rates.png=blob/2"]}))
    second = plan(tmp_path)
    assert second["figures"] == []
    assert [(s["action"], s["heading"]) for s in second["sections"]] == [("replace", "Results")]
    assert "![Rates](blob/2)" in second["sections"][0]["markdown"]
