import numpy as np
import pandas as pd

from report.target_origin import (NEVER_WORKED, OUTCOME, STRICT, any_date_labels, by_origin, circular, contrast,
                                  contrasts, contrasts_table, descriptive_contrasts, entry_origin, history_outcomes,
                                  origin_counts, pair_frame, shares)
from report.engaged_modes import ENGAGED_MODES


def hub(rows):
    return pd.DataFrame(rows, columns=["ensembl_id", "mondo_id", "validated_at_entry", "origin"])


def entries(rows):
    return pd.DataFrame(rows, columns=["moiety_id", "mondo_id", "target_kind"])


GENES = {1: ["G1"], 2: ["G1", "G2"], 3: ["G1", "G3"], 4: ["G1", "G4"], 5: ["G5"], 7: ["G1", "G7"]}
PAIRS = hub([("G1", "M1", False, "human_genetics"), ("G2", "M1", False, "human_genetics"),
             ("G3", "M1", False, "diseased_tissue"), ("G4", "M1", False, None), ("G5", "M1", True, "unclear"),
             ("G7", "M1", True, "human_genetics")])


def origins(rows):
    return list(entry_origin(entries(rows), GENES, PAIRS).origin)


def test_a_single_target_entry_takes_its_pairs_origin():
    assert origins([(1, "M1", "human_protein")]) == ["human_genetics"]


def test_a_multi_target_entry_enters_only_when_its_pairs_share_one_origin():
    assert origins([(2, "M1", "human_protein"), (3, "M1", "human_protein")]) == ["human_genetics", "mixed"]


def test_an_entry_with_a_pair_without_a_labelled_origin_is_unlabelled():
    assert origins([(4, "M1", "human_protein")]) == ["unlabelled"]


def test_validated_at_entry_on_any_pair_sets_the_entry_apart():
    assert origins([(5, "M1", "human_protein"), (7, "M1", "human_protein")]) == ["validated_at_entry"] * 2


def test_pathogen_untargeted_and_unpaired_entries_get_their_status():
    assert origins([(9, "M1", "pathogen"), (9, "M1", "no_single_target"), (1, "M2", "human_protein"),
                    (1, None, "human_protein")]) == ["pathogen", "no_target", "no_pair", "no_pair"]


def test_the_entry_records_its_pairs():
    e = entry_origin(entries([(2, "M1", "human_protein")]), GENES, PAIRS)
    assert e.pairs.iloc[0] == ("G1|M1", "G2|M1")


def test_any_date_restores_a_graded_label_failed_only_on_the_year():
    pairs = hub([("G1", "M1", False, "unclear"), ("G2", "M1", False, "unclear"), ("G3", "M1", False, "human_genetics")])
    year_only = pd.DataFrame({"ensembl_id": ["G1", "G2"], "mondo_id": ["M1", "M1"],
                              "origin": ["cell_screen", "diseased_tissue"], "grade": ["stated", "none"]})
    assert list(any_date_labels(pairs, year_only).origin) == ["cell_line_perturbation", "unclear", "human_genetics"]


def cohort(rate_exposed: float, rate_reference: float, n: int = 40, seed: int = 0) -> pd.DataFrame:
    """n targets per group, three entries each, with OUTCOME at the given rates, origins split between diseased tissue,
    observational biomarker and human genetics, and some unclear entries that never stop."""
    rng = np.random.default_rng(seed)
    rows = []
    for g, (origin, rate) in enumerate([("diseased_tissue", rate_exposed), ("observational_biomarker", rate_exposed),
                                        ("human_genetics", rate_reference), ("unclear", 0.0)]):
        for t in range(n):
            for i in range(3):
                rows.append({"origin": origin, "target": f"T{g}-{t}", "pairs": (f"G{g}-{t}|M{i}",),
                             "phase": 2 + (i == 2), "bio_area": "oncology" if t % 2 else "neurology",
                             "modality": "small_molecule", "era": "2008-11", "novel": 1.0,
                             OUTCOME: float(rng.random() < rate)})
    return pd.DataFrame(rows)


def test_contrast_estimates_a_higher_rate_in_the_exposed_origins():
    r = contrast(cohort(0.4, 0.1), ("diseased_tissue", "observational_biomarker"), ("human_genetics",))
    assert r["rr"] > 2 and r["lo"] < r["rr"] < r["hi"]
    assert r["exposed"]["entries"] == 240 and r["exposed"]["targets"] == 80 and r["exposed"]["pairs"] == 240
    assert r["reference"]["entries"] == 120 and r["reference"]["events"] == cohort(0.4, 0.1).query(
        "origin == 'human_genetics'")[OUTCOME].sum()


def test_contrast_gives_no_ratio_when_the_reference_has_no_event():
    r = contrast(cohort(0.4, 0.0), ("diseased_tissue",), ("human_genetics",))
    assert r["rr"] is None and r["reference"]["events"] == 0


def test_the_unclear_sensitivities_move_unclear_entries_into_each_group():
    d = cohort(0.4, 0.1)
    t = contrasts(d, d)
    assert t["unclear_as_exposed"]["o1"]["exposed"]["entries"] == 360
    assert t["unclear_as_reference"]["o1"]["reference"]["entries"] == 240
    assert t["phase2"]["o1"]["exposed"]["entries"] == 160
    table = contrasts_table(t)
    assert set(table.analysis) == {"primary", "unclear_as_exposed", "unclear_as_reference", "unsettled_as_exposed",
                                   "unsettled_as_reference", "phase2", "any_date"}


def test_by_origin_gives_each_modes_share_and_approval():
    d = pd.DataFrame({"origin": ["a", "a", "b"], "target": ["T1", "T2", "T3"], "pairs": [("p1",), ("p1",), ("p2",)],
                      **{f"mode_{m}": [0.0, 0.0, 0.0] for m in ENGAGED_MODES},
                      "stop_no_benefit": [1.0, 0.0, 0.0], "approval_date": [None, "2015-01-01", None],
                      STRICT: [0.0, 0.0, 0.0], NEVER_WORKED: [1.0, 0.0, 0.0]})
    d.loc[0, OUTCOME] = 1.0
    t = by_origin(d).set_index("origin")
    assert t.at["a", "entries"] == 2 and t.at["a", "pairs"] == 1 and t.at["a", OUTCOME] == 0.5
    assert t.at["a", "approved"] == 0.5 and t.at["b", "events"] == 0
    assert t.at["a", "not_causal_lo"] < 0.5 < t.at["a", "not_causal_hi"]
    assert t.at["a", NEVER_WORKED] == 0.5 and not t.at["a", "circular"]


def test_history_outcomes_count_only_engaged_stops_and_split_verdict_from_fate():
    d = pd.DataFrame({"stop_no_benefit": [1.0, 1.0, 1.0, 0.0, 1.0]})
    key = pd.Series(["k1", "k2", "k3", "k4", "k5"])
    h = pd.DataFrame({"key": ["k1", "k2", "k3", "k4"],
                      "target_fate": ["never_worked_single", "worked_elsewhere_only", "worked_here", "worked_related"],
                      "verdict": ["target_not_causal", None, "target_not_causal", None],
                      "mode": ["not_causal", "not_causal", "unresolved", "not_causal"]})
    out = history_outcomes(d, key, h)
    assert list(out[STRICT]) == [1.0, 0.0, 0.0, 0.0, 0.0]
    assert list(out[NEVER_WORKED]) == [1.0, 1.0, 0.0, 0.0, 0.0]


def test_descriptive_contrasts_use_their_own_outcome():
    d = cohort(0.4, 0.1).assign(**{STRICT: 0.0, NEVER_WORKED: 0.0})
    d.loc[d.origin.eq("diseased_tissue"), NEVER_WORKED] = 1.0
    r = descriptive_contrasts(d)
    assert r[NEVER_WORKED]["diseased_tissue"]["exposed"]["events"] == 120
    assert r[STRICT]["o1"]["exposed"]["events"] == 0 and r[STRICT]["o1"]["rr"] is None


def test_the_circular_origin_counts_its_events_from_the_worked_elsewhere_fate():
    d = pd.DataFrame({"origin": ["earlier_drug_other_disease"] * 3 + ["human_genetics"],
                      "pairs": [("a",), ("b", "c"), ("d",), ("e",)], OUTCOME: [1.0, 1.0, 0.0, 1.0],
                      "stop_no_benefit": [1.0, 1.0, 1.0, 1.0]})
    key = pd.Series(["k1", "k2", "k3", "k4"])
    h = pd.DataFrame({"key": ["k1", "k2", "k3", "k4"],
                      "target_fate": ["worked_elsewhere_only", "worked_elsewhere_only", "worked_here",
                                      "worked_elsewhere_only"]})
    c = circular(d, key, h)["earlier_drug_other_disease"]
    assert c["entries"] == 3 and c["events"] == 2 and c["events_by_fate_worked_elsewhere_only"] == 2
    assert c["single_target_stops_engaged"] == 2 and c["single_target_events_by_fate_worked_elsewhere_only"] == 1


def test_pair_descriptives_mark_validated_pairs_and_share_within_each_group():
    pairs = pd.DataFrame({"ensembl_id": ["G1", "G2", "G3", "G4"], "mondo_id": ["M1"] * 4,
                          "first_entry": pd.to_datetime(["2009-05-01", "2013-01-01", "2018-01-01", "2005-01-01"]),
                          "validated_at_entry": [False, True, False, False],
                          "origin": ["human_genetics", "unclear", "diseased_tissue", None],
                          "grade": ["stated", "none", "pattern", None],
                          "discovery_route": ["target_screen", "unclear", "target_screen", None],
                          "bio_area": ["oncology", "oncology", None, "oncology"]})
    p = pair_frame(pairs)
    assert list(p.origin) == ["human_genetics", "validated_at_entry", "diseased_tissue"]
    assert list(p.period) == ["2008-11", "2012-15", "2016-19"] and list(p.bio_area)[-1] == "unmapped"
    s = shares(p, "bio_area", "origin").set_index(["bio_area", "origin"])
    assert s.at[("oncology", "human_genetics"), "share"] == 0.5


def test_origin_counts_take_shares_of_the_settled_pairs_and_pool_the_genetic_origins():
    pairs = pd.DataFrame({"origin": ["human_genetics", "mouse_genetics", "diseased_tissue", "diseased_tissue",
                                     "unclear", "disputed", "not_reached", None]})
    t, n = origin_counts(pairs)
    assert (n["labelled"], n["settled"], n["unclear"], n["disputed"], n["not_reached"]) == (7, 4, 1, 1, 1)
    assert n["genetic_share"] == 0.5 and n["share"]["diseased_tissue"] == 0.5
    assert t.set_index("origin").settled_share.isna().to_dict()["unclear"]
