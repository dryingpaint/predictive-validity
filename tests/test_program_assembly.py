"""Which programs a trial's conditions seed, and the trial context the disease mapper reads."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

import pytest

from pipeline.indications import trial_context
from pipeline.programs import PURPOSE_TASK, assemble_programs, trial_disease_sets

GOUT, PURINE, ARDS, COVID, CANCER, NSCLC, CRC, OVARIAN = ("MONDO:gout", "MONDO:purine", "MONDO:ards",
                                                         "MONDO:covid", "MONDO:cancer", "MONDO:nsclc",
                                                         "MONDO:colorectal", "MONDO:ovarian")
ANCESTORS = defaultdict(set, {NSCLC: {CANCER}})


def programs(conditions, purpose=None, title_disease=None, by_moiety=None, starts=None, indication=None,
             misread=None):
    purpose = purpose or {}
    diseases, demoted, other = trial_disease_sets(conditions, purpose, title_disease or {}, misread or {})
    ncts = sorted({c[0] for c in conditions})
    trials = {n: {"start": (starts or {}).get(n, date(2020, 1, 1))} for n in ncts}
    baskets = {n for n, (p, _) in purpose.items() if p == "multi_indication"}
    return assemble_programs(by_moiety or {1: ncts}, trials, diseases, demoted, other, baskets, indication or {},
                             ANCESTORS)


def test_a_broader_mapped_condition_beside_an_exact_disease_starts_no_program():
    got = programs([("NCT1", GOUT, "exact", "Gout Chronic"), ("NCT1", PURINE, "broader", "Hyperuricemia")])
    assert got == {(1, GOUT): {"NCT1": ("disease", True)}}


def test_it_attaches_as_broader_condition_where_other_trials_seed_its_program():
    got = programs([("NCT1", GOUT, "exact", "Gout"), ("NCT1", PURINE, "broader", "Hyperuricemia"),
                    ("NCT2", PURINE, "broader", "Hyperuricemia")],
                   starts={"NCT1": date(2021, 1, 1), "NCT2": date(2019, 1, 1)})
    assert got[(1, PURINE)] == {"NCT2": ("disease", True), "NCT1": ("broader_condition", True)}
    assert got[(1, GOUT)] == {"NCT1": ("disease", True)}


def test_a_trial_with_only_broader_mapped_conditions_still_seeds_its_program():
    assert programs([("NCT1", PURINE, "broader", "Hyperuricemia")]) == {(1, PURINE): {"NCT1": ("disease", True)}}


def test_a_disease_mapped_exactly_by_one_string_and_broadly_by_another_counts_as_exact():
    got = programs([("NCT1", GOUT, "exact", "Gout"), ("NCT1", PURINE, "broader", "Hyperuricemia"),
                    ("NCT1", PURINE, "exact", "Purine metabolism disorder")])
    assert set(got) == {(1, GOUT), (1, PURINE)}


def test_the_title_disease_replaces_complications_listed_as_conditions():
    purpose = {"NCT1": ("indication_development", {"ARDS"})}
    got = programs([("NCT1", ARDS, "exact", "ARDS")], purpose, {"NCT1": COVID})
    assert got == {(1, COVID): {"NCT1": ("disease", True)}}


def test_an_early_development_trial_ignores_the_title_disease():
    purpose = {"NCT1": ("early_development", set())}
    got = programs([("NCT1", ARDS, "exact", "ARDS")], purpose, {"NCT1": COVID})
    assert got == {(1, None): {"NCT1": ("no_disease", True)}}


def test_an_ancestor_condition_still_attaches_to_the_specific_program():
    got = programs([("NCT1", NSCLC, "exact", "NSCLC"), ("NCT2", CANCER, "exact", "Cancer")])
    assert got == {(1, NSCLC): {"NCT1": ("disease", True), "NCT2": ("broader_condition", True)}}


@pytest.mark.parametrize("title, purpose, ok", [("COVID-19", "indication_development", True),
                                                (None, "multi_indication", True),
                                                ("COVID-19", "early_development", False)])
def test_a_title_disease_is_accepted_only_for_indication_development(title, purpose, ok):
    payload = {"conditions": ["ARDS"]}
    out = {"purpose": purpose, "development_conditions": [], "title_disease": title, "misread_conditions": [],
           "rationale": ""}
    if ok:
        PURPOSE_TASK.validate(payload, out)
    else:
        with pytest.raises(ValueError):
            PURPOSE_TASK.validate(payload, out)


def test_a_development_condition_spelled_unlike_its_registered_string_still_counts():
    purpose = {"NCT1": ("indication_development", {"Recurrent Platinum-resistant Ovarian Cancer"})}
    got = programs([("NCT1", OVARIAN, "exact", "Recurrent Platinum Resistant Ovarian Cancer")], purpose)
    assert got == {(1, OVARIAN): {"NCT1": ("disease", True)}}


def test_a_misread_condition_counts_as_what_the_trial_means_by_it():
    conditions = [("NCT1", CRC, "exact", "CRC With Atopic Asthma"), ("NCT2", CRC, "exact", "CRC")]
    got = programs(conditions, misread={"NCT1": {"crcwithatopicasthma": (None, None)}})
    assert got == {(1, CRC): {"NCT2": ("disease", True)}, (1, None): {"NCT1": ("non_disease_condition", True)}}
    got = programs([("NCT1", CRC, "exact", "AS")], misread={"NCT1": {"as": (GOUT, "exact")}})
    assert got == {(1, GOUT): {"NCT1": ("disease", True)}}


@pytest.mark.parametrize("condition, ok", [("CRC With Atopic Asthma", True), ("Unexplained Chronic Cough", False),
                                           ("Asthma", False)])
def test_only_a_listed_condition_with_a_mapped_disease_can_be_misread(condition, ok):
    payload = {"conditions": ["CRC With Atopic Asthma", "Unexplained Chronic Cough"],
               "mapped": {"CRC With Atopic Asthma": "colorectal carcinoma", "Unexplained Chronic Cough": None}}
    out = {"purpose": "indication_development", "development_conditions": [], "title_disease": None,
           "misread_conditions": [{"condition": condition, "meaning": "chronic refractory cough"}], "rationale": ""}
    if ok:
        PURPOSE_TASK.validate(payload, out)
    else:
        with pytest.raises(ValueError):
            PURPOSE_TASK.validate(payload, out)


def test_trial_context_gives_the_year_range_and_titles_spread_over_start_order():
    trials = [(date(2000 + k, 1, 1), f"T{k}") for k in range(12)] + [(None, "undated")]
    got = trial_context(trials)
    assert (got["n"], got["first_year"], got["last_year"], got["median_year"]) == (13, 2000, 2011, 2006)
    assert got["titles"] == ["T2", "T6", "T10"]
    assert trial_context(list(reversed(trials))) == got


def test_trial_context_of_a_string_no_trial_lists():
    assert trial_context([]) == {"n": 0, "first_year": None, "last_year": None, "median_year": None, "titles": []}
