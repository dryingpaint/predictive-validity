from pipeline.drugs import (
    UNII_CANDIDATES,
    candidate_uniis,
    components,
    disagreements,
    nonproprietary_name,
    render,
    substance_groups,
)
from pipeline.fda import principals


def payload(name, interventions=()):
    return {"name": name, "synonyms": [], "chembl_id": None,
            "trials": [{"title": f"A trial of {name}", "sponsor": "Sponsor",
                        "interventions": [{"name": n, "type": "DRUG", "description": d} for n, d in interventions]}]}


def comp(name, codes=(), biosimilar_of=None):
    return {"name": name, "code_names": list(codes), "biosimilar_of": biosimilar_of, "role": "investigational"}


def test_a_code_name_is_kept_only_without_a_question_mark_and_when_the_input_mentions_it():
    text = render(payload("BIIB078", [("BIIB078", "antisense oligonucleotide, also IONIS-C9Rx")]))
    out = {"kind": "drug", "components": [comp("tadnersen", ["BIIB078", "IONIS C9Rx", "ION363?", "ION541"])]}
    assert components(out, text, {"tadnersen"})[0]["codes"] == ["BIIB078", "IONIS C9Rx"]


def test_a_nonproprietary_name_no_source_carries_gives_way_to_the_sponsor_code():
    text = render(payload("GenSci048"))
    out = {"kind": "drug", "components": [comp("genakumab", ["GenSci048"])]}
    assert components(out, text, set())[0]["name"] == "GenSci048"
    out = {"kind": "drug", "components": [comp("firsekibart", ["GenSci048"])]}
    assert components(out, text, {"firsekibart"})[0]["name"] == "firsekibart"


def test_a_name_the_input_carries_is_kept_though_unregistered():
    text = render(payload("ABC-12", [("ABC-12", "autologous stromal vascular fraction cells")]))
    out = {"kind": "drug", "components": [comp("autologous stromal vascular fraction", ["ABC-12"])]}
    assert components(out, text, set())[0]["name"] == "autologous stromal vascular fraction"


def test_a_biosimilar_is_named_by_its_reference_product():
    text = render(payload("Meperizumab injection"))
    out = {"kind": "drug", "components": [comp("meperizumab", biosimilar_of="mepolizumab")]}
    assert components(out, text, {"mepolizumab"})[0]["name"] == "mepolizumab"


def test_a_vaccine_or_a_study_number_does_not_replace_a_name():
    vaccine = {"kind": "vaccine", "components": [comp("measles, mumps, rubella and varicella vaccine (live)", ["208136"])]}
    assert components(vaccine, "Priorix-Tetra, study 208136", set())[0]["name"] == \
        "measles, mumps, rubella and varicella vaccine (live)"
    drug = {"kind": "drug", "components": [comp("genakumab", ["208136"])]}
    assert components(drug, "Trial 208136 of an anti-IL-1 antibody", set())[0]["name"] == "genakumab"


def test_a_placebo_records_no_components():
    assert components({"kind": "placebo_or_vehicle", "components": [comp("TAK-418")]}, "TAK-418 Placebo", set()) == []


def resolved(*comps, kind="drug"):
    return kind, [{"name": n, "codes": list(c), "role": "investigational", "biosimilar_of": None} for n, c in comps]


def test_a_string_resolving_a_shared_code_against_the_majority_is_decided_again_with_its_siblings():
    names = {"1": "V116517 30-mg tablets", "2": "V116517 50-mg tablets", "3": "V116517 aqueous suspension",
             "4": "V116517 placebo"}
    decided = {"1": resolved(("oxycodone", [])), "2": resolved(("V116517", ["V116517"])),
               "3": resolved(("V116517", ["V116517"])), "4": resolved(kind="placebo_or_vehicle")}
    assert disagreements(names, decided) == {"1": ["2", "3"]}


def test_without_a_majority_every_string_sharing_the_code_is_decided_again():
    names = {"1": "CKD-348 F1", "2": "CKD-348(2)", "3": "CKD-348(6)"}
    decided = {"1": resolved(("CKD-348", ["CKD-348"])),
               "2": resolved(("telmisartan", ["CKD-348"]), ("amlodipine", []), kind="combination"),
               "3": resolved(kind="unclear")}
    again = disagreements(names, decided)
    assert sorted(again) == ["1", "2", "3"] and sorted(again["3"]) == ["1", "2"]


def test_strings_resolving_a_shared_code_alike_are_left_alone():
    names = {"1": "MK-3475 200 mg", "2": "MK-3475 + chemotherapy"}
    decided = {"1": resolved(("pembrolizumab", ["MK-3475"])),
               "2": resolved(("pembrolizumab", []), ("carboplatin", []), kind="combination")}
    assert disagreements(names, decided) == {}


def test_a_dose_unit_or_short_abbreviation_kept_as_a_code_groups_nothing():
    names = {"1": "MG-2 : MG1000mg", "2": "itopride 50 mg", "3": "resveratrol 200 mg", "4": "Hib vaccine",
             "5": "DTaP-Hib"}
    decided = {"1": resolved(("MG", ["MG"])), "2": resolved(("itopride", [])), "3": resolved(("resveratrol", [])),
               "4": resolved(("Hib conjugate", ["Hib"]), kind="vaccine"),
               "5": resolved(("DTaP", []), ("Hib conjugate", []), kind="vaccine")}
    assert disagreements(names, decided) == {}


def test_a_parent_names_only_salts_that_are_still_candidates():
    found = [(f"S{i}", [f"name{i}"]) for i in range(UNII_CANDIDATES + 3)]
    cands = candidate_uniis(found, {"S0": ["P"], f"S{UNII_CANDIDATES + 2}": ["P"]})
    assert len(cands) == UNII_CANDIDATES and cands["P"]["parent_of"] == ["S0"]


def test_a_parent_substance_is_offered_right_after_its_salt():
    found = [("LVM0PK6IHG", ["TAK-418"]), ("N9N6RK0CBN", ["TAK-418 FREE BASE"]), ("XYZ", ["TAK418"])]
    cands = candidate_uniis(found, {"LVM0PK6IHG": ["N9N6RK0CBN"], "XYZ": ["PARENT"]})
    assert list(cands) == ["LVM0PK6IHG", "N9N6RK0CBN", "XYZ", "PARENT"]
    assert cands["N9N6RK0CBN"] == {"matched": ["TAK-418 FREE BASE"], "parent_of": ["LVM0PK6IHG"]}
    assert cands["PARENT"] == {"matched": [], "parent_of": ["XYZ"]}


def test_an_entity_takes_the_substance_nonproprietary_name_never_a_salt_or_hydrate_display_name():
    assert nonproprietary_name("Firsekibart", ["firsekibart [INN]", "Firsekibart [WHO-DD]"]) == "firsekibart"
    assert nonproprietary_name("IMSAPEPIMUT", ["IMSAPEPIMUT [USAN]", "imsamotide [INN]"]) == "imsapepimut"
    assert nonproprietary_name("SODIUM PICOSULFATE ANHYDROUS", []) is None
    assert nonproprietary_name("TAK-418 FREE BASE", []) is None
    assert nonproprietary_name("TADNERSEN SODIUM", ["tadnersen [INN]"]) == "tadnersen"


def test_an_application_links_only_its_principal_ingredients():
    out = {"kind": "combination", "components": [
        {"name": "icodextrin", "biosimilar_of": None, "role": "principal"},
        {"name": "sodium chloride", "biosimilar_of": None, "role": "electrolyte_or_vehicle"},
        {"name": "calcium chloride", "biosimilar_of": None, "role": "electrolyte_or_vehicle"}]}
    assert [c["name"] for c in principals(out)] == ["icodextrin"]
    biosimilar = {"kind": "single", "components": [{"name": "adalimumab-atto", "biosimilar_of": "adalimumab",
                                                    "role": "principal"}]}
    assert [c["name"] for c in principals(biosimilar)] == ["adalimumab"]


def test_a_code_is_reviewed_when_shared_or_registered_to_an_unrelated_substance():
    from pipeline.drugs import review_keys
    holders = {"ain457": {1, 2}, "acz885": {1}, "ym022": {3}, "r13672": {4}, "fx006": {5}}
    unii_of = {1: "CANAK", 2: "SECUK", 3: "NETAZ", 4: "HALOP", 5: "TRIAM"}
    registered = {"ain457": {"SECUK"}, "acz885": {"CANAK"}, "ym022": {"YM022REC"}, "r13672": {"HALDEC"},
                  "fx006": {"TAFAM"}}
    parents = {"HALDEC": {"HALOP"}}  # haloperidol decanoate is a form of haloperidol
    assert review_keys(holders, unii_of, registered, parents) == {"ain457", "ym022", "fx006"}


def test_an_entity_loses_only_the_codes_a_verdict_says_it_does_not_own():
    from pipeline.drugs import owned_codes
    codes = {1: ["ACZ885", "AIN457"], 2: ["AIN457", "AIN-457"], 3: ["GW876008"]}
    keys = {1: "canakinumab", 2: "secukinumab", 3: "gw876008"}
    verdicts = {"ain457": {1: False, 2: True}, "gw876008": {3: False}}
    # every spelling of the code goes; an entity named by its code keeps it whatever the verdict
    assert owned_codes(codes, keys, verdicts) == {1: ["ACZ885"], 2: ["AIN457", "AIN-457"], 3: ["GW876008"]}


def test_a_salt_parent_or_sibling_form_counts_as_the_same_substance():
    from pipeline.drugs import related_substances
    parents = {"SALT": {"BASE"}, "ESTER": {"BASE"}}
    assert related_substances("BASE", "SALT", parents) and related_substances("SALT", "BASE", parents)
    assert related_substances("SALT", "ESTER", parents) and not related_substances("BASE", "OTHER", parents)
    assert not related_substances(None, "BASE", parents)


def test_a_code_leaves_an_entity_only_when_both_models_say_it_is_another_entitys():
    from pipeline.drugs import agreed_verdicts
    first = {"ain457": {1: False, 2: True}, "yh22162": {3: False}, "st067": {4: False}}
    second = {"ain457": {1: False, 2: True}, "yh22162": {3: True}}  # st067: the check failed validation
    assert agreed_verdicts(first, second) == {"ain457": {1: False, 2: True}, "yh22162": {3: True}, "st067": {4: True}}


def test_a_removal_needs_the_registry_to_place_the_code_on_an_unrelated_substance():
    from pipeline.drugs import registry_unconfirmed
    verdicts = {"ain457": {1: False, 2: True}, "scb01a": {3: False}, "u34865": {4: False}, "fx006": {5: False}}
    unii_of = {1: "CANAK", 2: "SECUK", 3: "FOSLI", 4: "HALOB", 5: "TRIAMSALT"}
    registered = {"ain457": {"SECUK"}, "u34865": {"DIFLO"}, "fx006": {"TRIAM"}}  # scb01a: unknown to the registry
    parents = {"TRIAMSALT": {"TRIAM"}}
    assert registry_unconfirmed(verdicts, unii_of, registered, parents) == {
        "ain457": set(), "scb01a": {3}, "u34865": set(), "fx006": {5}}


def test_a_name_whose_decision_gives_another_entitys_code_is_stale():
    from pipeline.drugs import stale
    owners = {"canakinumab": 1, "acz885": 1, "secukinumab": 2, "ain457": 2, "verucerfont": 3, "emicerfont": 4,
              "gw876008": 4}
    resolved = {"a": ("drug", [{"name": "canakinumab", "codes": ["AIN457"], "biosimilar_of": None}]),
                "b": ("drug", [{"name": "canakinumab", "codes": ["ACZ885"], "biosimilar_of": None}]),
                "c": ("drug", [{"name": "verucerfont", "codes": ["GW876008"], "biosimilar_of": None}]),
                "d": ("drug", [{"name": "new entity", "codes": ["GW876008"], "biosimilar_of": None}])}
    assert stale(resolved, owners) == {"a", "c"}  # a component no entity holds yet is not judged


def test_merges_copy_parents_before_children_and_delete_in_reverse():
    from pipeline.drugs import parents_first
    tables = ["evidence_entry_line", "evidence_entry", "literature_hit", "literature_search", "stop"]
    fks = [("evidence_entry_line", "evidence_entry"), ("literature_hit", "literature_search"), ("stop", "moiety")]
    order = parents_first(tables, fks)
    assert order.index("evidence_entry") < order.index("evidence_entry_line")
    assert order.index("literature_search") < order.index("literature_hit") and set(order) == set(tables)


def test_only_the_same_substance_or_a_form_of_it_may_join_another_entitys_substance():
    from pipeline.drugs import MERGE_SCHEMA, merge_allowed
    relations = {1: "same_substance", 2: "salt_or_form", 3: "class_or_family", 4: "combination_or_mixture",
                 5: "different_form", 6: "different_substance"}
    assert set(MERGE_SCHEMA["properties"]["relation"]["enum"]) == set(relations.values())
    assert merge_allowed(relations) == {1, 2}


def test_the_merge_check_shows_the_entity_and_the_substance_it_would_become():
    from pipeline.drugs import render_merge
    text = render_merge({"entity": {"name": "penicillin", "codes": [], "aliases": [], "strings": ["Penicillin"],
                                    "trials": [{"title": "Penicillin for syphilis", "sponsor": "X"}]},
                         "substance": {"unii": "Q42T66VG0C", "display_name": "PENICILLIN G", "substance_type": "chemical",
                                       "holder": "benzylpenicillin"}})
    assert "Entity: penicillin" in text and "PENICILLIN G" in text and "benzylpenicillin" in text
    assert "Candidate substances" not in text


def test_merges_move_every_column_a_foreign_key_ties_to_an_entity_whatever_its_name():
    from pipeline.drugs import entity_columns
    fks = [("preclin.drug_moiety", "preclin.moiety", ["moiety_id"], ["moiety_id"]),
           ("preclin.atlas_pair", "preclin.moiety", ["same_entity_as"], ["moiety_id"]),
           ("preclin.evidence_entry", "preclin.moiety", ["moiety_id"], ["moiety_id"]),
           ("preclin.evidence_entry_line", "preclin.evidence_entry", ["moiety_id", "mondo_id", "phase"],
            ["moiety_id", "mondo_id", "phase"]),
           ("preclin.dev_program", "preclin.moiety", ["moiety_id"], ["moiety_id"]),
           ("preclin.trial_outcome", "preclin.ctgov_study", ["nct_id"], ["nct_id"])]
    assert entity_columns(fks) == {"preclin.drug_moiety": ["moiety_id"], "preclin.atlas_pair": ["same_entity_as"],
                                   "preclin.evidence_entry": ["moiety_id"], "preclin.evidence_entry_line": ["moiety_id"]}


def test_an_entity_resolved_in_a_scoped_run_joins_the_entity_already_holding_its_substance():
    # 41916 (new, scoped) resolves to the UNII 13338 already holds; 13338 was not re-resolved in this run.
    groups = substance_groups({41916: "9B7N7Y96MK"}, {"9B7N7Y96MK": 13338})
    assert sorted(groups["9B7N7Y96MK"]) == [13338, 41916]


def test_a_holder_resolved_in_the_same_run_follows_its_own_decision():
    # In a full run the holder was re-resolved to another substance, so it is not pulled into its old one's group.
    groups = substance_groups({41916: "U1", 13338: "U2"}, {"U1": 13338})
    assert groups["U1"] == [41916] and groups["U2"] == [13338]


def test_an_entity_alone_on_its_substance_stays_alone():
    assert substance_groups({41917: "U3"}, {}) == {"U3": [41917]}
