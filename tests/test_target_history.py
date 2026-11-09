import pandas as pd

from pipeline.target_history import Success, agreement, fate, partner_map


def win(selected=False):
    return Success(1, "MONDO:A", "met", selected, pd.Timestamp("2015-01-01"))


def test_a_success_in_this_disease_comes_first():
    assert fate([win()], [win()], [win()], 2, False) == "worked_here"


def test_success_only_in_biomarker_selected_trials_counts_when_this_program_was_not_selected():
    assert fate([win(True)], [], [], 0, False) == "worked_here_selected"
    assert fate([win(True)], [], [], 0, True) == "worked_here"
    assert fate([win(True), win(False)], [], [], 0, False) == "worked_here"


def test_without_a_success_here_related_then_other_diseases_then_failures_decide():
    assert fate([], [win()], [win()], 0, False) == "worked_related"
    assert fate([], [], [win()], 3, False) == "worked_elsewhere_only"
    assert fate([], [], [], 1, False) == "never_worked_tried_again"
    assert fate([], [], [], 0, False) == "never_worked_single"


def test_partners_share_a_target_in_a_compatible_direction():
    t = pd.DataFrame({"moiety_id": [1, 2, 3, 4], "ens": ["G", "G", "G", "H"], "sign": ["-", "-", "+", "-"]})
    p = partner_map(t.assign(action=None))
    assert p[1] == {2} and p[3] == set() and p[4] == set()
    p = partner_map(pd.DataFrame({"moiety_id": [1, 2], "ens": ["G", "G"], "sign": ["-", "?"]}))
    assert p[1] == {2} and p[2] == {1}


def test_agreement_counts_decided_verdicts_history_allows():
    blind = pd.DataFrame({"target_fate": ["worked_here", "worked_here", "worked_elsewhere_only", "worked_related"],
                          "verdict": ["drug_inadequate", "target_not_causal", "target_not_causal", "unclear"]})
    a = agreement(blind)
    assert a["decided"] == 3 and abs(a["agree"] - 2 / 3) < 1e-9
    assert a["per_fate"]["worked_related"]["agree"] is None
