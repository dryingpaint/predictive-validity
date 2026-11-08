"""analyses/model-system-atlas/glance.py: a cell's headline from its tracks, the dissent, and the
label wrapping of the journal figure. Synthetic entries, no database."""
from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analyses", "model-system-atlas"))
import glance  # noqa: E402
import glance_nature  # noqa: E402
import report_page  # noqa: E402


def entry(model_id, year, status, seq=1, modality="", adjudicated=None, retrodiction=None, **fields):
    return {"mondo_id": "MONDO:1", "mechanism_key": "X|inhibitor", "question": "efficacy", "modality": modality, "seq": seq,
            "year": year, "status": status, "model_id": model_id, "model": model_id.replace("-", " "),
            "src_label": "", "retrodiction": status == "retro" if retrodiction is None else retrodiction, "fields": {"short": f"{model_id} {status}", **fields},
            "adjudicated_status": adjudicated, "final": adjudicated or status, "short": f"{model_id} {status}"}


def cell(*entries):
    return pd.DataFrame(list(entries))


def test_best_track_sets_the_headline_over_a_contradicted_track():
    st, pick, last = glance.headline_entry(cell(entry("a", 2010, "untested"), entry("a", 2015, "contra", seq=2),
                                                entry("b", 2012, "untested"), entry("b", 2018, "same", seq=2)))
    assert st == "same"
    assert pick["model_id"] == "b" and pick["year"] == 2018
    assert {v["model_id"]: v["final"] for v in last.values()} == {"a": "contra", "b": "same"}


def test_a_retrodiction_never_sets_the_headline_and_an_all_retro_cell_is_marked():
    st, _, _ = glance.headline_entry(cell(entry("a", 2010, "untested"), entry("b", 2020, "retro")))
    assert st == "untested"
    st, pick, _ = glance.headline_entry(cell(entry("b", 2020, "retro")))
    assert st == "retro" and pick["model_id"] == "b"


def test_a_retrodiction_after_a_match_on_the_same_track_leaves_the_match_standing():
    st, pick, _ = glance.headline_entry(cell(entry("a", 2017, "same"), entry("a", 2026, "retro", seq=2)))
    assert st == "same" and pick["year"] == 2017


def test_a_retrodiction_scored_contradicted_never_sets_the_headline():
    st, _, _ = glance.headline_entry(cell(entry("a", 2015, "same"), entry("b", 2020, "contra", retrodiction=True)))
    assert st == "same"


def test_one_model_in_two_modality_strips_is_two_tracks():
    _, _, last = glance.headline_entry(cell(entry("a", 2015, "same", modality="antibody"),
                                            entry("a", 2016, "same", modality="small molecule")))
    assert len(last) == 2


def test_a_cell_whose_entries_were_all_dropped_has_no_headline():
    assert glance.headline_entry(cell(entry("a", 2015, "same", adjudicated="drop"))) is None


def test_the_checkers_corrected_year_stands_only_when_the_status_does():
    r = {"status": "same", "year": 2014, "verdict": "corrected", "proposed_year": 2011, "adjudicated_status": None}
    assert report_page.final_year(r) == 2011
    assert report_page.final_year({**r, "adjudicated_status": "contra"}) == 2014
    assert report_page.final_year({**r, "verdict": "confirmed"}) == 2014


def test_adjudicated_status_overrides_the_drafters():
    st, _, _ = glance.headline_entry(cell(entry("a", 2015, "same", adjudicated="contra")))
    assert st == "contra"


def test_modality_strips_show_the_worst():
    st, pick, _ = glance.headline_entry(cell(entry("a", 2015, "same", modality="antibody"),
                                             entry("b", 2016, "contra", modality="small molecule")))
    assert st == "contra" and pick["modality"] == "small molecule"


def test_cells_records_the_dissent():
    e = cell(entry("a", 2010, "untested"), entry("a", 2015, "contra", seq=2),
             entry("b", 2012, "untested"), entry("b", 2018, "same", seq=2))
    tiles = pd.DataFrame([{"slug": "t", "area": "x", "disease": "d", "mondo_id": "MONDO:1", "mechanism_key": "X|inhibitor",
                           "mechanism": "X inhibitors", "class_programs": 3, "class_share": 0.1}])
    df = glance.cells(e, tiles)
    row = df[df.question == "efficacy"].iloc[0]
    assert row.status == "same" and row.year == 2018 and pd.isna(row.untested_reason)
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


def test_order_tiles_main_cut_is_one_tile_per_ranked_disease_with_the_most_programs(tmp_path, monkeypatch):
    burden = pd.DataFrame([{"mondo_id": "MONDO:T2D", "rank": 1}, {"mondo_id": "MONDO:COPD", "rank": 2}, {"mondo_id": "MONDO:CF", "rank": None}])
    (tmp_path / "lists").mkdir()
    burden.to_csv(tmp_path / "lists" / "burden.csv", index=False)
    monkeypatch.setattr(glance_nature, "HERE", str(tmp_path))
    tiles = pd.DataFrame([
        {"slug": "t2d-a", "area": "endocrine", "mondo_id": "MONDO:T2D", "disease": "type 2 diabetes mellitus", "mechanism": "A", "programs": 3},
        {"slug": "t2d-b", "area": "endocrine", "mondo_id": "MONDO:T2D", "disease": "type 2 diabetes mellitus", "mechanism": "B", "programs": 12},
        {"slug": "copd-c", "area": "respiratory", "mondo_id": "MONDO:COPD", "disease": "COPD", "mechanism": "C", "programs": 6},
        {"slug": "cf-d", "area": "respiratory", "mondo_id": "MONDO:CF", "disease": "cystic fibrosis", "mechanism": "D", "programs": 10},
    ])
    df = pd.concat([tiles.assign(question=q) for q in ("engagement", "dose", "efficacy", "safety")])
    main = glance_nature.order_tiles(df, "burden", top=15, one_per_disease=True)
    assert list(main.slug) == ["t2d-b", "copd-c"] and list(main.group) == ["#1", "#2"]
    supplement = glance_nature.order_tiles(df, "burden")
    assert list(supplement.slug) == ["t2d-b", "t2d-a", "copd-c", "cf-d"] and list(supplement.group) == ["#1", "#1", "#2", "Respiratory"]
    by_area = glance_nature.order_tiles(df, "area")
    assert list(by_area.group) == ["Endocrine", "Endocrine", "Respiratory", "Respiratory"]


def test_a_never_compared_cell_carries_the_reason_of_the_entry_drawn():
    e = cell(entry("a", 2010, "untested", untested_reason="not_measured"), entry("b", 2020, "retro"))
    tiles = pd.DataFrame([{"slug": "t", "area": "x", "disease": "d", "mondo_id": "MONDO:1", "mechanism_key": "X|inhibitor",
                           "mechanism": "X inhibitors", "class_programs": 3, "class_share": 0.1}])
    row = glance.cells(e, tiles).query("question == 'efficacy'").iloc[0]
    assert row.status == "untested" and row.untested_reason == "not_measured"
    assert set(glance_nature.UNTESTED_REASON) == {"no_prediction", "not_measured", "unpublished", "unsettled"}


def test_every_headline_status_the_data_can_carry_has_a_figure_style():
    assert set(glance.WORST) <= set(glance_nature.STATUS)
    assert glance_nature.style("neg")["hatch"] and glance_nature.style("contra")["hatch"] is None
    assert glance_nature.style("same")["hatch"] is None
