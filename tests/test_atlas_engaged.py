"""analyses/model-system-atlas/lessons/engaged: the coding files agree with the codebook and the case list, the two
codings and the resolution are consistent, and the figure draws from synthetic rows. No database."""
from __future__ import annotations

import os
import sys

import pandas as pd
import pytest

HERE = os.path.dirname(__file__)
ENGAGED = os.path.join(HERE, "..", "analyses", "model-system-atlas", "lessons", "engaged")
sys.path.insert(0, ENGAGED)
sys.path.insert(0, os.path.join(HERE, "..", "analyses", "model-system-atlas"))
sys.path.insert(0, os.path.join(HERE, "..", "analyses", "model-system-atlas", "lessons"))
import figure
import lessons

CODES = pd.read_csv(os.path.join(ENGAGED, "codes.csv"), dtype=str).fillna("")
CODER1 = pd.read_csv(os.path.join(ENGAGED, "codes_coder1.csv"), dtype=str).fillna("")
CODER2 = pd.read_csv(os.path.join(ENGAGED, "codes_coder2.csv"), dtype=str).fillna("")
TILES = pd.read_csv(os.path.join(ENGAGED, "cases_tiles.csv"), dtype=str)
with open(os.path.join(ENGAGED, "CODEBOOK.md")) as _f:
    CODEBOOK = _f.read()


def test_every_code_in_the_files_is_defined_and_every_defined_code_is_in_the_codebook():
    used = set(CODES.primary) | set(CODES.secondary) | set(CODER1.primary) | set(CODER1.secondary) | set(CODER2.primary) | set(CODER2.secondary)
    used.discard("")
    assert used <= set(figure.CODE)
    for code in figure.CODE:
        assert f"| {code} |" in CODEBOOK, code
    assert figure.IN_DRAFT <= set(figure.CODE)
    assert {c[0] for c in figure.CODE} == set(figure.LAYER)


def test_the_three_files_cover_the_same_classes_once_each_and_the_figure_can_name_them():
    slugs = set(TILES.slug)
    for df in (CODES, CODER1, CODER2):
        assert list(df.slug.sort_values()) == sorted(slugs)
        assert df.slug.is_unique
        assert df.confidence.isin({"high", "medium", "low"}).all()
        assert (df.primary != "").all()
    assert slugs <= set(figure.SHORT)
    assert CODES.resolution.isin({"agree", "coder1", "coder2", "rule"}).all()


def test_the_resolution_column_is_true_to_the_two_codings():
    m = CODES.merge(CODER1, on="slug", suffixes=("", "_1")).merge(CODER2, on="slug", suffixes=("", "_2"))
    agree = m[m.resolution == "agree"]
    assert (agree.primary_1 == agree.primary_2).all() and (agree.primary == agree.primary_1).all()
    to1 = m[m.resolution == "coder1"]
    assert (to1.primary == to1.primary_1).all() and (to1.primary_1 != to1.primary_2).all()
    to2 = m[m.resolution == "coder2"]
    assert (to2.primary == to2.primary_2).all() and (to2.primary_1 != to2.primary_2).all()
    rule = m[m.resolution == "rule"]
    assert (rule.primary_1 != rule.primary_2).all()
    assert (CODES.secondary != CODES.primary).all()


def test_agreement_reported_in_the_legend_matches_the_files():
    m = CODER1.merge(CODER2, on="slug", suffixes=("_1", "_2"))
    with open(os.path.join(ENGAGED, "LEGEND.md")) as f:
        legend = f.read()
    agree = int((m.primary_1 == m.primary_2).sum())
    kappa = lessons.kappa(m.primary_1, m.primary_2)
    assert f"{agree} of {len(m)}" in legend
    assert f"kappa {kappa:.2f}" in legend


def test_figure_draws_synthetic_rows_and_shows_the_draft_categories_even_when_empty(tmp_path):
    codes = pd.DataFrame([{"slug": "a", "primary": "A1", "secondary": "", "confidence": "high", "resolution": "agree", "rationale": "x"},
                          {"slug": "b", "primary": "B1", "secondary": "A5", "confidence": "low", "resolution": "coder2", "rationale": "y"}])
    tiles = pd.DataFrame([{"slug": "a", "furthest_phase": 2}, {"slug": "b", "furthest_phase": 4}])
    assert figure.rows_for(codes) == ["A1", "A2", "A3", "B1"]
    out = figure.draw(codes, tiles, str(tmp_path / "f"))
    assert os.path.exists(out) and os.path.getsize(out) > 10_000
    assert figure.layout_height(codes) > 2


@pytest.mark.parametrize("name", ["extract.py", "figure.py", "CODEBOOK.md", "LEGEND.md", "cases_entries.csv", "cases_dossier.txt"])
def test_the_folder_is_complete(name):
    assert os.path.exists(os.path.join(ENGAGED, name))
