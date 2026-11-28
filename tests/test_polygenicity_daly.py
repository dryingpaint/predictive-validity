import pytest
"""Polygenicity (#147): the share of 2021 WHO DALYs in diseases with a Mendelian form or a drugged large-effect gene."""
import importlib.util
import os

import pandas as pd

from report import frame
from report.polygenicity import daly_share, leaves, who_map

WHO = os.path.join(frame.REPO, "analyses", "model-system-atlas", "lists", "who_ghe_2021_global_dalys.csv")


def burden_map():
    spec = importlib.util.spec_from_file_location("burden", os.path.join(frame.REPO, "analyses", "model-system-atlas", "burden.py"))
    burden = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(burden)
    return burden.MAP


def test_map_covers_every_who_cause():
    who = pd.read_csv(WHO)
    m = who_map()
    assert set(m.code) == set(who.code) and set(m.relation) <= {"exact", "broader", "none"}
    assert m[m.relation.ne("none")].mondo_id.notna().all()


def test_map_agrees_with_burden_py():
    pairs = set(zip(who_map().code.astype(int), who_map().mondo_id.fillna("")))
    for mondo, (grade, codes, _) in burden_map().items():
        if grade in ("exact", "broader"):
            for c in codes:
                assert (c, mondo) in pairs, (c, mondo)


def test_leaves_are_rows_without_children():
    who = pd.DataFrame({"code": [0, 10, 11, 12, 20], "depth": [1, 2, 3, 3, 2], "cause": ["All", "NCD", "A", "B", "Inj"],
                        "dalys_2021": [100, 60, 40, 20, 40]})
    assert list(leaves(who).code) == [11, 12, 20]


def test_daly_share_sums_leaf_causes_with_a_flag():
    who = pd.DataFrame({"code": [0, 10, 11, 12, 20], "depth": [1, 2, 3, 3, 2],
                        "cause": ["All Causes", "Noncommunicable diseases", "A", "B", "Injuries"],
                        "dalys_2021": [100, 60, 40, 20, 40]})
    m = pd.DataFrame({"code": [11, 12, 20], "relation": ["exact", "broader", "none"], "mondo_id": ["M1", "M2", None]})
    flags = pd.DataFrame({"mondo_id": ["M1", "M2"], "mendelian_form": [True, False], "drugged_large_effect": [False, True]})
    s = daly_share(who, m, flags)
    assert s["all"]["mendelian_form"] == 0.4 and s["all"]["drugged_large_effect"] == 0.2 and s["all"]["either"] == 0.6
    assert abs(s["ncd"]["either"] - 1.0) < 1e-9 and s["all"]["total"] == 100


def test_drugged_sets_join_entered_and_approved_targets():
    from report.polygenicity import drugged_sets
    td = pd.DataFrame({"ensembl_id": ["E1", "E2"], "mondo_id": ["M1", "M1"]})
    approved = pd.DataFrame({"ensembl_id": ["E3"], "mondo_id": ["M2"]})
    assert drugged_sets(td, approved) == {"M1": {"E1", "E2"}, "M2": {"E3"}}


@pytest.mark.db
def test_approved_targets_reads_the_yes_judgement_of_the_text_column():
    """preclin.dev_program_approval.approved is text (yes / no / uncertain), not boolean; the query takes 'yes',
    as pipeline.target_history and pipeline.attribution do."""
    from report.polygenicity import approved_targets
    a = approved_targets()
    assert list(a.columns) == ["ensembl_id", "mondo_id"] and len(a) > 0 and not a.duplicated().any()


def test_who_file_depth_separates_parents_from_leaf_causes():
    """The committed WHO file carries the GHE hierarchy in depth (All Causes 1, the three groups 2, their
    sub-groups 3, causes 4 and 5): noncommunicable diseases (600) and malignant neoplasms (610) are parents,
    road injury (1530) is a leaf. A flat depth column made every cause a leaf and emptied the NCD subtree."""
    who = pd.read_csv(WHO)
    lf = set(leaves(who).code)
    assert who.depth.max() >= 4 and 600 not in lf and 610 not in lf and 1530 in lf


def test_daly_share_with_a_group_that_has_no_leaf_rows_reports_zero_shares():
    """A denominator group with no leaf causes under it yields zero shares and no largest causes, not a crash
    (an empty boolean mask must still select rows, not columns)."""
    who = pd.DataFrame({"code": [0, 10, 20, 600], "depth": [1, 2, 3, 2],
                        "cause": ["All Causes", "Communicable", "A", "Noncommunicable diseases"], "dalys_2021": [100, 60, 60, 40]})
    m = pd.DataFrame({"code": [20], "relation": ["exact"], "mondo_id": ["M1"]})
    flags = pd.DataFrame({"mondo_id": ["M1"], "mendelian_form": [True], "drugged_large_effect": [False]})
    s = daly_share(who, m, flags)
    assert s["ncd"]["either"] == 0.0 and s["ncd"]["largest"] == [] and s["all"]["mendelian_form"] == 0.6


def test_daly_flags_come_from_the_stored_profile_not_the_raw_association_file():
    """The report reads the drugged-gene flag from preclin.disease_polygenicity (filled by `pipeline.polygenicity
    drugged`), so a report build needs no local Open Targets download; an unfilled column is a loud error."""
    from report.polygenicity import daly_flags
    prof = pd.DataFrame({"mondo_id": ["a", "b"], "mendelian_form": [True, None], "drugged_large_effect": [False, True]})
    f = daly_flags(prof)
    assert f.mendelian_form.tolist() == [True, False] and f.drugged_large_effect.tolist() == [False, True]
    with pytest.raises(RuntimeError, match="drugged"):
        daly_flags(prof.assign(drugged_large_effect=None))
