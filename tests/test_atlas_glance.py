"""analyses/model-system-atlas/glance.py: a cell's headline from its tracks (decision 6), the dissent, and the
label wrapping of the journal figure. Synthetic entries, no database."""
from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analyses", "model-system-atlas"))
import glance  # noqa: E402
import glance_nature  # noqa: E402


def entry(model_id, year, status, seq=1, modality="", adjudicated=None, **fields):
    return {"mondo_id": "MONDO:1", "mechanism_key": "X|inhibitor", "question": "efficacy", "modality": modality, "seq": seq,
            "year": year, "status": status, "model_id": model_id, "model": model_id.replace("-", " "),
            "src_label": "", "retrodiction": status == "retro", "fields": {"short": f"{model_id} {status}", **fields},
            "adjudicated_status": adjudicated, "final": adjudicated or status, "short": f"{model_id} {status}"}


def cell(*entries):
    return pd.DataFrame(list(entries))


def test_best_track_sets_the_headline_over_a_contradicted_track():
    st, pick, last = glance.headline_entry(cell(entry("a", 2010, "untested"), entry("a", 2015, "contra", seq=2),
                                                entry("b", 2012, "untested"), entry("b", 2018, "same", seq=2)))
    assert st == "same"
    assert pick["model_id"] == "b" and pick["year"] == 2018
    assert {k: v["final"] for k, v in last.items()} == {"a": "contra", "b": "same"}


def test_a_retrodiction_never_sets_the_headline_and_an_all_retro_cell_is_marked():
    st, _, _ = glance.headline_entry(cell(entry("a", 2010, "untested"), entry("b", 2020, "retro")))
    assert st == "untested"
    st, pick, _ = glance.headline_entry(cell(entry("b", 2020, "retro")))
    assert st == "retro" and pick["model_id"] == "b"


def test_adjudicated_status_overrides_the_drafters():
    st, _, _ = glance.headline_entry(cell(entry("a", 2015, "same", adjudicated="contra")))
    assert st == "contra"


def test_modality_strips_show_the_worst():
    st, pick, _ = glance.headline_entry(cell(entry("a", 2015, "same", modality="antibody"),
                                             entry("b", 2016, "contra", modality="small molecule")))
    assert st == "contra" and pick["modality"] == "small molecule"


def test_cells_records_the_dissent_and_the_derived_flag():
    e = cell(entry("a", 2010, "untested"), entry("a", 2015, "contra", seq=2),
             entry("b", 2012, "untested"), entry("b", 2018, "same", seq=2, derived_from="efficacy"))
    tiles = pd.DataFrame([{"slug": "t", "area": "x", "disease": "d", "mondo_id": "MONDO:1", "mechanism_key": "X|inhibitor",
                           "mechanism": "X inhibitors", "class_programs": 3, "class_share": 0.1}])
    df = glance.cells(e, tiles)
    row = df[df.question == "efficacy"].iloc[0]
    assert row.status == "same" and row.year == 2018 and row.derived == "efficacy"
    assert row.dissent == "a contra" and row.dissent_model == "a"
    assert row.tracks == 2 and row.other_tracks == 1
    assert df[df.question == "safety"].status.isna().all()


def test_wrap_never_cuts_what_fits_and_records_what_it_cuts():
    glance_nature.CUT.clear()
    assert glance_nature.wrap("Rat and dog toxicology", 5, 2.0, 1) == ["Rat and dog toxicology"]
    lines = glance_nature.wrap("a long model name that needs several lines of text", 5, 0.6, 2)
    assert len(lines) == 2 and lines[-1].endswith("…")
    assert glance_nature.CUT == ["a long model name that needs several lines of text"]
    assert glance_nature.wrap("", 5, 1.0, 2) == [""]
