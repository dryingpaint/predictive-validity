import math

import pandas as pd

from report.evidence_lines import biomarker_selected, earlier_failure, failures_by_gene, molecule_lines

RELATED = frozenset({"MONDO:A", "MONDO:A1"})
FAILED = pd.DataFrame([
    (1, "MONDO:A", "2014-06-30"),   # another entity on GENE1, related disease
    (2, "MONDO:B", "2015-01-31"),   # another entity on GENE1, unrelated disease
    (9, "MONDO:A1", "2015-03-31"),  # the entity itself
], columns=["moiety_id", "mondo_id", "ended"])
GENES = {1: ["GENE1"], 2: ["GENE1"], 9: ["GENE1"], 3: ["GENE2"]}
BY_GENE = failures_by_gene(FAILED, GENES)


def test_a_related_failure_within_three_years_before_entry_counts():
    assert earlier_failure(BY_GENE, 9, ["GENE1"], RELATED, pd.Timestamp("2016-01-01")) is True


def test_failures_more_than_three_years_before_entry_or_after_it_do_not_count():
    assert earlier_failure(BY_GENE, 9, ["GENE1"], RELATED, pd.Timestamp("2017-07-01")) is False
    assert earlier_failure(BY_GENE, 9, ["GENE1"], RELATED, pd.Timestamp("2014-06-30")) is False


def test_the_entitys_own_failures_and_unrelated_diseases_do_not_count():
    only_own = failures_by_gene(FAILED[FAILED.moiety_id.isin([2, 9])], GENES)
    assert earlier_failure(only_own, 9, ["GENE1"], RELATED, pd.Timestamp("2016-01-01")) is False


def test_entries_before_2011_have_no_value():
    assert earlier_failure(BY_GENE, 9, ["GENE1"], RELATED, pd.Timestamp("2010-12-31")) is None


ASSAYS = pd.DataFrame([
    ("T1", ["GENE1"], "SINGLE PROTEIN", "Ki", 8.5, False, False, 2012),
    ("T2", ["OFF1"], "SINGLE PROTEIN", "Ki", 7.8, False, False, 2012),
    ("T2", ["OFF1"], "SINGLE PROTEIN", "Ki", 6.0, False, False, 2015),
    ("T3", ["OFF2"], "SINGLE PROTEIN", "IC50", 6.5, False, False, 2016),
], columns=["target_chembl_id", "symbols", "target_type", "standard_type", "pchembl", "functional", "cell_based", "year"])


def test_selectivity_is_undefined_without_an_off_target_measurement():
    r = molecule_lines(ASSAYS[ASSAYS.target_chembl_id == "T1"], {"GENE1"}, 2013)
    assert r["potent_10nm"] == 1.0 and math.isnan(r["selective"])


def test_selectivity_needs_a_tenfold_margin_over_the_best_off_target_known_by_the_cutoff():
    assert molecule_lines(ASSAYS, {"GENE1"}, 2012)["selective"] == 0.0  # 8.5 against 7.8
    assert molecule_lines(ASSAYS, {"GENE1"}, 2015)["selective"] == 1.0  # OFF1 median falls to 6.9


def test_nothing_measured_before_the_first_document():
    r = molecule_lines(ASSAYS, {"GENE1"}, 2011)
    assert r["potent_100nm"] == 0.0 and math.isnan(r["selective"])


from report.evidence_lines import property_lines  # noqa: E402

ENTRIES = pd.DataFrame({
    "moiety_id": [1, 2, 3, 4, 5],
    "modality": ["small_molecule", "small_molecule", "small_molecule", "monoclonal_antibody", "small_molecule"],
    "bio_area": ["neurology", "psychiatry", "oncology", "neurology", "neurology"]})
PROPS = pd.DataFrame({
    "moiety_id": [1, 2, 3, 4],
    "molecular_weight": [320.0, 520.0, 610.0, 150000.0], "tpsa": [60.0, 70.0, 140.0, 0.0],
    "hbd": [1, 2, 6, 0], "ro5_violations": [0, 1, 2, 3]})


def test_drug_likeness_allows_one_rule_of_five_violation_and_only_scores_small_molecules_with_properties():
    r = property_lines(ENTRIES, PROPS)
    assert list(r.drug_like.iloc[:3]) == [1.0, 1.0, 0.0]
    assert r.drug_like.iloc[3:].isna().all()  # an antibody; a small molecule with no properties


def test_brain_penetrance_is_scored_only_for_neurology_and_psychiatry_small_molecules():
    r = property_lines(ENTRIES, PROPS)
    assert r.brain_penetrant.iloc[0] == 1.0
    assert r.brain_penetrant.iloc[1] == 0.0  # MW 520
    assert r.brain_penetrant.iloc[2:].isna().all()  # oncology; antibody; no properties


TRIALS = pd.DataFrame([
    {"program_id": 1, "nct_id": "NCT1", "phase": 2, "start_date": "2012-03-01", "industry": True, "starts_phase": True},
    {"program_id": 1, "nct_id": "NCT2", "phase": 2, "start_date": "2013-01-01", "industry": True, "starts_phase": True},
    {"program_id": 2, "nct_id": "NCT3", "phase": 2, "start_date": "2014-05-01", "industry": True, "starts_phase": True},
    {"program_id": 2, "nct_id": "NCT4", "phase": 2, "start_date": "2014-05-01", "industry": True, "starts_phase": True},
    {"program_id": 3, "nct_id": "NCT5", "phase": 1, "start_date": "2015-01-01", "industry": False, "starts_phase": True},
])
SELECTED = pd.DataFrame({"nct_id": ["NCT1", "NCT2", "NCT3", "NCT4", "NCT5"],
                         "selected": [False, True, False, True, True]})


def test_an_entry_is_biomarker_selected_by_the_trials_that_opened_its_phase():
    rows = pd.DataFrame({"program_id": [1, 2, 3], "phase": [2, 2, 1],
                         "entry": ["2012-03-01", "2014-05-01", "2015-01-01"]})
    out = biomarker_selected(rows, TRIALS, SELECTED)
    assert out.tolist()[:2] == [0.0, 1.0]  # a later selected trial does not count; any opening trial does
    assert pd.isna(out.iloc[2])  # no labelled industry trial opened the phase
