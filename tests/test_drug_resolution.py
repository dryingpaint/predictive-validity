from pipeline.drugs import (
    candidate_uniis,
    components,
    disagreements,
    nonproprietary_name,
    render,
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
