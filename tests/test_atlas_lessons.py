"""analyses/model-system-atlas/lessons: the family rules and overrides, the prediction reading, the track table, the
cluster-bootstrap rate and the hand-typed safety merge. Synthetic rows, no database."""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analyses", "model-system-atlas", "lessons"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analyses", "model-system-atlas"))
import families  # noqa: E402
import lessons  # noqa: E402


def test_rules_fire_on_their_keyword_and_respect_the_kind_gate():
    assert families.assign("animal", "Rat and dog repeat-dose toxicology") == ("tox_repeat_dose", "rule")
    assert families.assign("animal", "MC38 colon carcinoma in human PD-1 knock-in mice") == ("humanised_mouse", "rule")
    assert families.assign("animal", "Collagen-induced arthritis (rodent)") == ("inflammatory_disease_model", "rule")
    assert families.assign("ex_vivo", "Patient rectal organoids, forskolin-induced swelling") == ("patient_material_ex_vivo", "rule")
    assert families.assign("human_challenge", "Allergen exposure chamber (EEC)") == ("allergen_challenge_human", "rule")
    assert families.assign("human_genetic", "People with SLC5A2 loss-of-function") == ("target_lof_genetics", "rule")
    assert families.assign("in_silico", "Simcyp PBPK model") == ("pbpk_translational", "rule")
    # a human-challenge text never falls into the bench rules, whatever it says about patients
    assert families.assign("human_challenge", "Nasal allergen challenge in patients") == ("allergen_challenge_human", "rule")
    assert families.assign("in_silico", "a model nobody named") == ("unassigned", "")


def test_an_override_wins_over_a_rule_and_an_unknown_family_is_refused(tmp_path):
    p = tmp_path / "overrides.csv"
    p.write_text("slug,model_id,family,note\nt,m,xenograft_cell_line,the knock-in is in the cell line\n")
    ov = families.load_overrides(str(p))
    assert families.family_of("t", "m", "animal", "MCF7 ESR1 knock-in xenografts", ov) == ("xenograft_cell_line", "override")
    assert families.family_of("t", "other", "animal", "MCF7 ESR1 knock-in xenografts", ov) == ("humanised_mouse", "rule")
    p.write_text("slug,model_id,family,note\nt,m,no_such_family,\n")
    with pytest.raises(ValueError):
        families.load_overrides(str(p))
    assert set(families.SHORT) == set(families.FAMILIES)


def test_prediction_reads_safety_derived_dose_and_a_model_that_said_no():
    assert lessons.prediction("efficacy", "contra", None) == "yes"
    assert lessons.prediction("efficacy", "neg", None) == "no"
    assert lessons.prediction("dose", "contra", "efficacy") == "derived"
    assert lessons.prediction("dose", "same", None) == "yes"
    assert lessons.prediction("safety", "contra", None) == "safety"


def entry(slug, question, model_id, year, status, seq=1, final=None, **fields):
    return {"mondo_id": "M:" + slug, "mechanism_key": "X", "question": question, "modality": None, "seq": seq, "year": year, "status": status,
            "model_id": model_id, "model": "Rat and dog toxicology", "src_label": "", "retrodiction": status == "retro", "fields": {"model_kind": "animal", **fields},
            "adjudicated_status": None, "final": final or status, "short": ""}


def tiles_for(*slugs):
    return pd.DataFrame([{"slug": s, "area": "x", "mondo_id": "M:" + s, "mechanism_key": "X", "furthest_phase": 4 if s == "a" else 2, "class_programs": 3}
                         for s in slugs])


def test_tracks_take_the_latest_entry_and_never_count_retro_untested_or_drop_as_compared():
    e = pd.DataFrame([entry("a", "efficacy", "m1", 2010, "untested"), entry("a", "efficacy", "m1", 2015, "contra", seq=2),
                      entry("a", "efficacy", "m2", 2012, "retro"), entry("b", "efficacy", "m3", 2011, "same", final="drop"),
                      entry("b", "dose", "m4", 2013, "contra", derived_from="efficacy"), entry("b", "safety", "m5", 2014, "same")])
    t = lessons.tracks(e, tiles_for("a", "b"))
    assert len(t) == 4 and set(t.model_id) == {"m1", "m2", "m4", "m5"}
    m1 = t[t.model_id == "m1"].iloc[0]
    assert m1.final == "contra" and m1.year == 2015 and m1.compared and not m1.matched and m1.pred == "yes" and m1.approved
    assert not t[t.model_id == "m2"].iloc[0].compared
    assert "m3" not in set(t.model_id)
    assert t[t.model_id == "m4"].iloc[0].pred == "derived" and not t[t.model_id == "m4"].iloc[0].approved
    assert t[t.model_id == "m5"].iloc[0].pred == "safety"


def test_cluster_bootstrap_rate_matches_the_point_estimate_and_is_wider_than_a_track_level_interval():
    # two tiles: one with four matched tracks, one with four contradicted; the point estimate is 0.5 either way,
    # a track-level Wilson interval on 4/8 is 0.22-0.78, the tile-level bootstrap must reach 0 and 1
    matched = np.array([1, 1, 1, 1, 0, 0, 0, 0])
    tile = np.array(["a"] * 4 + ["b"] * 4)
    p, lo, hi = lessons.rate(matched, np.ones(8, dtype=int), tile)
    assert p == 0.5 and lo == 0.0 and hi == 1.0
    p, lo, hi = lessons.rate(np.array([1, 1, 1, 0]), np.ones(4, dtype=int), np.array(["a", "b", "c", "d"]))
    assert p == 0.75 and 0.0 <= lo < 0.75 < hi <= 1.0
    assert all(np.isnan(lessons.rate(np.array([]), np.array([]), np.array([]))))


def test_rate_table_splits_derived_dose_keeps_the_pooled_reference_and_ranks_at_four_tiles():
    rows = []
    for i in range(5):
        rows.append({"slug": f"t{i}", "question": "efficacy", "family": "xenograft_cell_line", "matched": i % 2 == 0, "pred": "yes"})
    rows.append({"slug": "t0", "question": "dose", "family": "xenograft_cell_line", "matched": False, "pred": "derived"})
    rows.append({"slug": "t1", "question": "dose", "family": "xenograft_cell_line", "matched": True, "pred": "yes"})
    rows.append({"slug": "t9", "question": "efficacy", "family": "gemm_tumour", "matched": False, "pred": "no"})
    r = lessons.rate_table(pd.DataFrame(rows))
    eff = r[(r.q == "efficacy") & (r.family == "xenograft_cell_line")].iloc[0]
    assert eff.n_tracks == 5 and eff.n_tiles == 5 and eff.matched == 3 and eff.ppv == 0.6 and eff.rankable and eff.pooled == 0.6
    assert set(r.q) == {"efficacy", "dose", "dose (derived)"}
    assert r[r.q == "dose (derived)"].ppv.iloc[0] == 0.0 and not r[r.q == "dose"].rankable.iloc[0]
    assert "gemm_tumour" not in set(r.family)  # the model that said no is not a yes


def test_safety_review_must_cover_every_compared_contra(tmp_path, monkeypatch, capsys):
    e = pd.DataFrame([entry("a", "safety", "m1", 2015, "contra", reason="silent"), entry("a", "safety", "m2", 2016, "same")])
    t = lessons.with_families(lessons.tracks(e, tiles_for("a")))
    p = tmp_path / "safety_types.csv"
    p.write_text("slug,model_id,type,harm_class,note\n")
    monkeypatch.setitem(lessons.INPUTS, "safety_types", str(p))
    monkeypatch.setitem(lessons.OUT, "safety_misses", str(tmp_path / "out.csv"))
    with pytest.raises(SystemExit):
        lessons.cmd_safety(t)
    p.write_text("slug,model_id,type,harm_class,note\na,m1,silent,liver;immune,x\n")
    out = lessons.cmd_safety(t)
    assert len(out) == 1 and out.type.iloc[0] == "silent" and out.harm_class.iloc[0] == "liver;immune"
    p.write_text("slug,model_id,type,harm_class,note\na,m1,silent,nonsense,x\n")
    with pytest.raises(SystemExit):
        lessons.cmd_safety(t)
