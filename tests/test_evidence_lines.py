import math

import pandas as pd

from report.evidence_lines import (AREAS, area_alone, area_columns, biomarker_selected, cell_dependency,
                                    earlier_failure, earlier_safety_stop, failures_by_gene, molecule_lines,
                                    stale_inputs)

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


UNSAFE = failures_by_gene(pd.DataFrame([
    (1, "MONDO:Z", "2012-06-30"),   # another entity on GENE1, any disease
    (9, "MONDO:A", "2010-01-31"),   # the entity itself
], columns=["moiety_id", "mondo_id", "ended"]), GENES)


def test_another_drugs_safety_stop_in_any_disease_counts_a_year_after_its_trials_ended():
    assert earlier_safety_stop(UNSAFE, 9, ["GENE1"], pd.Timestamp("2013-07-01")) is True
    assert earlier_safety_stop(UNSAFE, 9, ["GENE1"], pd.Timestamp("2013-06-01")) is False


def test_the_entitys_own_safety_stop_and_entries_before_2011_do_not_count():
    assert earlier_safety_stop(UNSAFE, 9, ["GENE2"], pd.Timestamp("2016-01-01")) is False
    own = failures_by_gene(pd.DataFrame([(9, "MONDO:A", "2010-01-31")], columns=["moiety_id", "mondo_id", "ended"]),
                           GENES)
    assert earlier_safety_stop(own, 9, ["GENE1"], pd.Timestamp("2016-01-01")) is False
    assert earlier_safety_stop(UNSAFE, 9, ["GENE1"], pd.Timestamp("2010-12-31")) is None


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


def test_long_form_keeps_each_applicable_non_null_value_once():
    from report.evidence_lines import long_form, registry
    d = pd.DataFrame({
        "moiety_id": [1, 2, 3], "mondo_id": ["MONDO:A", None, "MONDO:B"], "phase": [2, 1, 3],
        "has_target_disease": [True, False, True], "modality": ["small_molecule", "small_molecule", "protein"],
        "regime": ["COM", "COM", "ONC"], "bio_area": ["metabolic", None, "oncology"], "entry_year": [2012, 2009, 2016],
        "g3": [1.0, 2.0, None], "potent_100nm": [0.0, 1.0, 1.0], "biomarker_selected": [1.0, 0.0, None]})
    out = long_form(d, registry())
    got = set(map(tuple, out[["moiety_id", "mondo_id", "phase", "line_key", "value"]].itertuples(index=False)))
    assert got == {(1, "MONDO:A", 2, "g3", 1.0),  # entry 2 has no target and disease, so g3 does not apply to it
                   (1, "MONDO:A", 2, "potent_100nm", 0.0), (2, "", 1, "potent_100nm", 1.0)}  # entry 3 is no small molecule
    assert not out.line_key.eq("biomarker_selected").any()  # the adjustment is stored on the entry


def test_every_registry_line_has_a_unique_key():
    from report.evidence_lines import registry
    reg = registry()
    assert reg.line_key.is_unique and set(reg.level) <= {"category", "subcategory", "descriptive", "adjustment",
                                                          "measurement"}


from report.evidence_lines import category_columns, lines  # noqa: E402


def entries(*rows: dict) -> pd.DataFrame:
    """Entries with every line column null unless a row sets it."""
    base = {"modality": "small_molecule", "bio_area": "oncology", "regime": "ONC", "phase": 2, "entry_year": 2015,
            "has_target_disease": True, **{ln.column: math.nan for ln in lines() if ln.column}}
    return pd.DataFrame([{**base, **r} for r in rows])


def test_a_molecule_with_no_known_properties_is_not_counted_as_lacking_the_molecule_evidence():
    d = entries({"potent_100nm": 0.0, "drug_like": math.nan},   # nothing known about the structure
                {"potent_100nm": 0.0, "drug_like": 0.0},        # known, and neither potent nor drug-like
                {"potent_100nm": 1.0, "drug_like": 0.0})
    assert category_columns(d).cat_molecule.tolist()[1:] == [0.0, 1.0]
    assert math.isnan(category_columns(d).cat_molecule[0])


def test_a_subcategory_scored_on_fewer_entries_than_its_category_does_not_make_it_up():
    d = entries({"bio_area": "psychiatry", "potent_100nm": 0.0, "drug_like": 0.0, "brain_penetrant": 1.0},
                {"b1": 0.0, "approved_unrelated_only": 0.0, "earlier_failure": 1.0})
    out = category_columns(d)
    assert out.cat_molecule[0] == 0.0  # brain penetrance is scored for neurology and psychiatry only
    assert out.cat_precedent[1] == 0.0  # earlier failures are scored for 2011+ entries only


STORED = {"snapshot": "2026-11-02", "dev_program_approval": [21628, 3360783], "moiety_property": 93}


def test_a_store_is_current_when_its_inputs_are_unchanged():
    assert stale_inputs(STORED, dict(STORED)) == []


def test_a_rewritten_label_table_or_new_input_makes_a_store_stale():
    now = {**STORED, "dev_program_approval": [21700, 3700000], "cell_dependency": 120000}
    assert stale_inputs(STORED, now) == ["cell_dependency", "dev_program_approval"]


def test_a_store_made_before_fingerprinting_is_stale_on_every_input():
    assert stale_inputs({}, STORED) == sorted(STORED)


LINES = {"L1": ("MONDO:LUAD", 2014), "L2": ("MONDO:LUAD", 2014), "L3": ("MONDO:LUAD", 2017),
         "L4": ("MONDO:LUAD", 2017), "L5": ("MONDO:AML", 2014)}
LUNG = frozenset({"MONDO:LUAD"})


def test_a_target_two_lines_and_a_fifth_of_its_type_depend_on_is_a_dependency():
    dep = {("G1", "L1"): 2014, ("G1", "L2"): 2014}
    assert cell_dependency(["G1"], LUNG, 2015, LINES, dep, {}) == 1.0


def test_one_dependent_line_or_too_small_a_share_is_not_a_dependency():
    assert cell_dependency(["G1"], LUNG, 2015, LINES, {("G1", "L1"): 2014}, {}) == 0.0
    many = {line: ("MONDO:LUAD", 2014) for line in (f"X{i}" for i in range(11))}
    assert cell_dependency(["G1"], LUNG, 2015, many, {("G1", "X0"): 2014, ("G1", "X1"): 2014}, {}) == 0.0


def test_screens_published_after_the_cutoff_do_not_count():
    dep = {("G1", "L3"): 2017, ("G1", "L4"): 2017}
    assert cell_dependency(["G1"], LUNG, 2016, LINES, dep, {}) == 0.0
    assert cell_dependency(["G1"], LUNG, 2017, LINES, dep, {}) == 1.0


def test_no_screened_line_of_the_type_is_unknown_not_absent():
    assert pd.isna(cell_dependency(["G1"], frozenset({"MONDO:GBM"}), 2018, LINES, {}, {}))
    assert pd.isna(cell_dependency(["G1"], LUNG, 2013, LINES, {}, {}))


def test_a_common_essential_gene_of_that_year_does_not_count():
    dep = {("G1", line): 2014 for line in ("L1", "L2", "L3", "L4")}
    assert cell_dependency(["G1"], LUNG, 2019, LINES, dep, {2019: {"G1"}}) == 0.0
    assert cell_dependency(["G1"], LUNG, 2018, LINES, dep, {2019: {"G1"}}) == 1.0


def test_an_areas_tiers_are_mutually_exclusive_and_make_up_the_area():
    d = entries({"rare_variant": 1.0, "gwas": 0.0, "g3": 1.0}, {"rare_variant": 0.0, "gwas": 1.0, "g3": 1.0},
                {"rare_variant": 1.0, "gwas": 1.0, "g3": 1.0, "allelic_series": 1.0},
                {"rare_variant": 0.0, "gwas": 0.0, "g3": 0.0})
    for col in ("somatic", "somatic_concordant", "expression", "reactome", "altered_animal", "animal_close",
                "potent_100nm", "selective", "earlier_failure", "precedent"):
        d[col] = d[col].fillna(0.0) if col in d else 0.0
    d["assay_best"] = math.nan
    out = d.join(area_columns(d))
    tiers = [t.column for t in AREAS["human_genetics"][1]]
    assert out[tiers].sum(axis=1).tolist() == [1, 1, 1, 0]  # each linked entry in exactly one tier, unlinked in none


def test_only_a_tier_scored_on_fewer_entries_than_its_area_is_marked():
    assert area_alone() == {"tier_failure_only"}


def test_a_literature_line_counts_only_studies_published_before_entry_in_a_related_disease():
    from report.evidence_lines import literature_columns
    q = pd.DataFrame([(1, "p1", 2009, "animal_disease", "MONDO:A"), (1, "p2", 2012, "animal_disease", "MONDO:A"),
                      (1, "p3", 2009, "animal_disease", "MONDO:Z"), (1, "p4", 2010, "animal_healthy", None),
                      (1, "p5", None, "human_engagement", None)],
                     columns=["moiety_id", "pmid", "year", "kind", "mondo_id"])
    d = pd.DataFrame({"moiety_id": [1, 1, 2, 3], "mondo_id": ["MONDO:A", "MONDO:A", "MONDO:A", None],
                      "phase": [2, 1, 2, 2], "entry_year": [2011, 2010, 2011, 2011]})
    out = literature_columns(d, lambda m: frozenset({m, "MONDO:A1"}), q, screened={1, 3}, to={1: 1, 2: 2, 3: 3})
    assert out.lit_animal_disease.tolist()[:2] == [1.0, 1.0]  # p1 (2009) precedes both entries; p3's disease is unrelated
    assert out.lit_animal_healthy.tolist()[:2] == [1.0, 0.0]  # p4 (2010) is not before a 2010 entry's cutoff (2009)
    assert out.lit_human_engagement.iloc[0] == 0.0 and pd.isna(out.lit_human_engagement.iloc[1])  # undated; Phase 1
    assert out.iloc[2].isna().all()  # drug 2 not screened
    assert pd.isna(out.lit_animal_disease.iloc[3]) and out.lit_animal_healthy.iloc[3] == 0.0  # no disease
