import math

import pandas as pd

from report.evidence_lines import (biomarker_selected, cell_dependency, earlier_safety_stop, failures_by_gene,
                                    molecule_lines, stale_inputs)

GENES = {1: ["GENE1"], 2: ["GENE1"], 9: ["GENE1"], 3: ["GENE2"]}
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


from report.evidence_lines import FACTS, FACT_PREFIX, KINDS, chart_rows, derive, facts, long_form, registry  # noqa: E402

RAW = ["burden", "mendelian", "gwas", "gwas_strong", "mendelian_strong", "somatic", "somatic_gof", "somatic_lof", "reactome", "mgi", "impc", "mgi_strong",
       "impc_strong", "crispr", "cell_dependency", "expression", "expression_up", "b1", "b1_close", "precedent",
       "assay_best", "assay_margin", "drug_like", "brain_penetrant", "lit_animal_disease",
       "lit_animal_healthy", "lit_human_engagement", "constrained", "ko_lethal", "pan_essential", "ko_vital_organ",
       "earlier_safety_stop", "crispr_untimed", "pan_essential_untimed", "cell_functional"]


def raw(*rows: dict) -> pd.DataFrame:
    """Entries as build has them before the facts: an oncology small molecule from 2016 with a target and a disease,
    every raw evidence column 0 unless a row sets it."""
    base = {"moiety_id": 1, "mondo_id": "MONDO:A", "modality": "small_molecule", "bio_area": "oncology",
            "regime": "ONC", "phase": 2, "entry_year": 2016, "has_target_disease": True, "sign": "decrease",
            "loss_effect": "none", "mouse_favours": "none", "protein_level": "none", "protein_level_untimed": "none",
            "side_effect": "no_drug", "side_effect_untimed": "no_drug", **{c: 0.0 for c in RAW}}
    return pd.DataFrame([{**base, "moiety_id": i + 1, **r} for i, r in enumerate(rows)])


def lines_of(d: pd.DataFrame) -> pd.DataFrame:
    from report.evidence_lines import drug_action
    return derive(facts(d), drug_action(d.sign))


def test_each_fact_has_exactly_one_of_its_values_on_every_entry_it_applies_to():
    d = raw({}, {"has_target_disease": False, "modality": "protein", "regime": "COM", "bio_area": "psychiatry",
                 "phase": 1, "entry_year": 2009, "mondo_id": None},
            {"bio_area": "neurology", "regime": "COM", "assay_best": 8.2, "assay_margin": 0.4, "gwas": 1.0},
            {"entry_year": 2012, "cell_dependency": math.nan, "lit_animal_healthy": math.nan})
    from report.evidence_lines import APPLIES
    f = facts(d)
    for fact in FACTS.values():
        applies = APPLIES[fact.applies](d)
        assert f[fact.key].notna().equals(applies & (f[fact.key].notna())), fact.key  # nothing outside its scope
        if not fact.numeric:
            assert f.loc[applies, fact.key].isin([v for v, _ in fact.values]).all(), fact.key


def test_inherited_variants_are_rare_only_common_only_both_or_none():
    d = raw({"burden": 1.0}, {"gwas": 1.0}, {"mendelian": 1.0, "gwas": 1.0}, {})
    assert facts(d).variants.tolist() == ["rare_only", "common_only", "both", "none"]
    out = lines_of(d)
    assert out.g3.tolist() == [1.0, 1.0, 1.0, 0.0]
    assert out[["tier_rare_only", "tier_common_only", "allelic_series"]].sum(axis=1).tolist() == [1, 1, 1, 0]
    assert out.rare_variant.tolist() == [1.0, 0.0, 1.0, 0.0] and out.gwas.tolist() == [0.0, 1.0, 1.0, 0.0]


def test_genetic_support_is_strong_with_a_burden_test_or_a_strong_tier_else_supported_or_none():
    d = raw({"burden": 1.0}, {"gwas": 1.0, "gwas_strong": 1.0}, {"mendelian": 1.0, "mendelian_strong": 1.0},
            {"gwas": 1.0}, {})
    assert facts(d).genetic_strength.tolist() == ["strong", "strong", "strong", "supported", "none"]
    assert lines_of(d).g3.tolist() == [1.0, 1.0, 1.0, 1.0, 0.0]  # strength refines the kind, it does not make it up


def test_approvals_split_at_lin_08_into_validated_and_another_disease():
    d = raw({"b1_close": 1.0, "b1": 1.0, "precedent": 1.0}, {"b1": 1.0, "precedent": 1.0}, {"precedent": 1.0}, {})
    assert facts(d).best_approval.tolist() == ["same_or_close", "related", "unrelated_only", "none"]
    out = lines_of(d)
    assert out.validated_at_entry.tolist() == [1.0, 0.0, 0.0, 0.0]
    assert out.approved_other_disease.tolist() == [0.0, 1.0, 1.0, 0.0]
    assert out.b1.tolist() == [1.0, 1.0, 0.0, 0.0]  # the registered B1 still counts any approval at Lin 0.5 or more


def test_agreement_with_the_drug_is_a_cross_of_the_gene_and_the_drugs_action():
    d = raw({"gwas": 1.0, "loss_effect": "lowers_risk"}, {"gwas": 1.0, "loss_effect": "raises_risk"},
            {"gwas": 1.0, "loss_effect": "raises_risk", "sign": "increase"}, {"gwas": 1.0, "loss_effect": "mixed"},
            {"somatic": 1.0, "somatic_gof": 1.0}, {"mouse_favours": "favours_lowering"})
    out = lines_of(d)
    assert out.genetics_concordant.tolist()[:4] == [1.0, 0.0, 1.0, 0.0]  # a blocker of a gene whose loss protects
    assert out.somatic_concordant[4] == 1.0  # an activating mutation and a drug that blocks
    assert out.animal_concordant[5] == 1.0


def test_protein_genetics_counts_its_dated_direction_and_crosses_it_with_the_drugs_action():
    d = raw({"protein_level": "raises_risk"}, {"protein_level": "lowers_risk"},
            {"protein_level": "lowers_risk", "sign": "increase"}, {"protein_level": "mixed"},
            {"protein_level_untimed": "raises_risk"})
    f, out = facts(d), lines_of(d)
    assert out.pqtl.tolist() == [1.0, 1.0, 1.0, 1.0, 0.0]  # today's pQTLs alone do not make up the kind
    assert f.protein_level_hindsight.tolist() == ["no"] * 4 + ["yes"]
    assert out.pqtl_untimed[4] == 1.0
    # a blocker of a protein whose higher level raises risk agrees; an activator of one whose level protects agrees
    assert out.pqtl_concordant.tolist() == [1.0, 0.0, 1.0, 0.0, 0.0]


def test_a_dated_side_effect_makes_up_clinical_observation_and_argues_for_the_opposite_action():
    d = raw({"side_effect": "lowering", "sign": "increase"}, {"side_effect": "lowering"},
            {"side_effect": "raising"}, {"side_effect": "none", "side_effect_untimed": "raising"},
            {"side_effect": "no_drug"})
    f, out = facts(d), lines_of(d)
    assert out.clinical_observation.tolist()[:4] == [1.0, 1.0, 1.0, 0.0]  # a signal only after entry is no evidence
    assert math.isnan(out.clinical_observation[4])  # no other drug on the target: unknown, not "no"
    assert f.side_effect_hindsight.tolist() == ["no", "no", "no", "yes", "no"] and out.side_effect_untimed[3] == 1.0
    # a blocker of the target causing the disease argues for an activator, and the reverse
    assert out.side_effect_concordant.tolist()[:4] == [1.0, 0.0, 1.0, 0.0] and math.isnan(out.side_effect_concordant[4])


def test_a_cell_measurement_is_yes_no_or_not_measured_and_only_yes_counts():
    d = raw({"assay_best": 7.2, "cell_functional": 1.0}, {"assay_best": 7.2}, {"assay_best": math.nan},
            {"modality": "protein"})
    assert facts(d).cell_functional.tolist()[:3] == ["yes", "no", "not_measured"]
    out = lines_of(d).cell_functional
    assert out.tolist()[:3] == [1.0, 0.0, 0.0] and math.isnan(out[3])  # scored for small molecules only


def test_a_kind_is_any_of_its_counting_facts_and_unknown_when_none_is_known():
    d = raw({"drug_like": math.nan}, {"drug_like": 0.0}, {"bio_area": "psychiatry", "regime": "COM", "drug_like": 0.0,
                                                         "brain_penetrant": 1.0})
    out = lines_of(d)
    assert math.isnan(out.molecule_properties[0]) and out.molecule_properties.tolist()[1:] == [0.0, 1.0]


def test_hindsight_and_exploratory_facts_do_not_make_up_their_kind():
    out = lines_of(raw({"crispr_untimed": 1.0}, {"ko_vital_organ": 1.0, "earlier_safety_stop": 1.0}))
    assert out.cell_line_perturbation[0] == 0.0 and out.crispr_untimed[0] == 1.0
    assert out.liability[1] == 0.0 and out.ko_vital_organ[1] == 1.0


def test_cell_line_perturbation_pools_every_source_on_the_entries_it_reaches():
    d = raw({"cell_dependency": 1.0}, {"crispr": 1.0}, {"cell_dependency": math.nan}, {},
            {"entry_year": 2013, "cell_dependency": 1.0}, {"regime": "COM", "bio_area": "metabolic", "crispr": 1.0})
    assert facts(d).perturbation.tolist() == ["yes", "yes", "not_reached", "no", "not_reached", "not_reached"]
    out = lines_of(d).cell_line_perturbation
    assert out.tolist()[:2] == [1.0, 1.0] and out[3] == 0.0 and out[[2, 4, 5]].isna().all()


def test_a_charts_rows_under_a_kind_do_not_overlap():
    d = raw({"burden": 1.0, "gwas": 1.0, "somatic": 1.0, "somatic_gof": 1.0, "somatic_lof": 1.0, "mgi": 1.0,
             "mgi_strong": 1.0, "expression": 1.0, "expression_up": 1.0, "b1": 1.0, "precedent": 1.0,
             "assay_best": 7.5, "lit_animal_disease": 1.0, "lit_animal_healthy": 1.0}, {})
    out = lines_of(d)
    for kind in KINDS:
        values = [ln.column for _, k, level, ln in chart_rows() if k.key == kind and level == "value"]
        if values:
            assert (out[values].fillna(0).sum(axis=1) <= 1).all(), kind


def test_long_form_stores_each_answer_once_and_measurements_as_numbers():
    d = raw({"assay_best": 7.4}, {"has_target_disease": False, "modality": "protein", "mondo_id": None})
    d = d.join(facts(d).add_prefix(FACT_PREFIX))
    out = long_form(d)
    assert not out.duplicated(["moiety_id", "mondo_id", "phase", "fact_key"]).any()
    first = out[out.moiety_id.eq(1)].set_index("fact_key")
    assert first.at["best_pchembl", "value_num"] == 7.4 and first.at["potency", "value"] == "10_100nm"
    assert set(out[out.moiety_id.eq(2)].fact_key) == {"healthy_animals", "in_people"}  # no target, no small molecule


def test_the_registry_holds_every_kind_fact_and_link():
    kinds, facts_, links = registry()
    assert kinds.kind_key.is_unique and facts_.fact_key.is_unique
    assert set(links.fact_key) <= set(facts_.fact_key) and set(links.kind_key) <= set(kinds.kind_key)
    values = dict(zip(facts_.fact_key, facts_.fact_values))
    assert all(set(v) <= set(values[f]) for f, v in zip(links.fact_key, links.evidence_values))
    assert list(kinds[kinds.category.eq("animals")].kind_key) == [
        "mouse_genetics", "animal_model_pharmacology"]
    assert set(kinds[kinds.about.eq("drug")].kind_key) == {"healthy_animal_studies", "binding", "drug_in_people",
                                                           "molecule_properties"}


def test_a_disease_specific_kind_is_not_applicable_outside_its_scope():
    d = raw({"regime": "COM", "bio_area": "metabolic", "somatic": 1.0}, {"entry_year": 2012, "cell_dependency": 1.0})
    out = lines_of(d)
    assert pd.isna(out.somatic[0]) and pd.isna(out.cell_line_perturbation[1])  # not applicable, never "no"


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


def test_a_literature_line_counts_only_studies_published_before_entry_in_a_related_disease():
    from report.evidence_lines import literature_columns
    q = pd.DataFrame([(1, "p1", 2009, "animal_disease", "MONDO:A", [2010]), (1, "p2", 2012, "animal_disease", "MONDO:A", [2010]),
                      (1, "p3", 2009, "animal_disease", "MONDO:Z", [2010]), (1, "p4", 2010, "animal_healthy", None, [2010]),
                      (1, "p5", None, "human_engagement", None, [2010])],
                     columns=["moiety_id", "pmid", "year", "kind", "mondo_id", "search_cutoffs"])
    d = pd.DataFrame({"moiety_id": [1, 1, 2, 3], "mondo_id": ["MONDO:A", "MONDO:A", "MONDO:A", None],
                      "phase": [2, 1, 2, 2], "entry_year": [2011, 2010, 2011, 2011]})
    out = literature_columns(d, lambda m: frozenset({m, "MONDO:A1"}), q, screened={1: [2010], 3: [2010]},
                             to={1: 1, 2: 2, 3: 3}, last_cutoff=2018)
    assert out.lit_animal_disease.tolist()[:2] == [1.0, 1.0]  # p1 (2009) precedes both entries; p3's disease is unrelated
    assert out.lit_animal_healthy.tolist()[:2] == [1.0, 0.0]  # p4 (2010) is not before a 2010 entry's cutoff (2009)
    assert out.lit_human_engagement.iloc[0] == 0.0 and pd.isna(out.lit_human_engagement.iloc[1])  # undated; Phase 1
    assert out.iloc[2].isna().all()  # drug 2 not screened
    assert pd.isna(out.lit_animal_disease.iloc[3]) and out.lit_animal_healthy.iloc[3] == 0.0  # no disease


def test_a_later_search_leaves_an_earlier_window_as_it_was_and_scores_only_the_entries_it_reaches():
    from report.evidence_lines import literature_columns
    # p1, published in 2015, was retrieved only by the drug's later search
    q = pd.DataFrame([(1, "p1", 2015, "animal_healthy", None, [2021])],
                     columns=["moiety_id", "pmid", "year", "kind", "mondo_id", "search_cutoffs"])
    d = pd.DataFrame({"moiety_id": [1], "mondo_id": [None], "phase": [2], "entry_year": [2017]})
    screened, to = {1: [2016, 2021]}, {1: 1}
    assert literature_columns(d, lambda m: frozenset(), q, screened, to, last_cutoff=2018).lit_animal_healthy.tolist() == [0.0]
    assert literature_columns(d, lambda m: frozenset(), q, screened, to, last_cutoff=2021).lit_animal_healthy.tolist() == [1.0]
    # a drug searched only for a later window is unsearched in an earlier one
    assert literature_columns(d, lambda m: frozenset(), q, {1: [2021]}, to, last_cutoff=2018).isna().all().all()




def test_the_chart_draws_each_category_as_one_block_in_category_order():
    from report.evidence_lines import CATEGORIES, chart_rows
    seen = [category for category, *_ in chart_rows()]
    blocks = [c for i, c in enumerate(seen) if i == 0 or c != seen[i - 1]]
    assert blocks == [c for c in CATEGORIES if c in seen]
