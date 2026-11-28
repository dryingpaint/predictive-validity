import pandas as pd

from report.single_target import approved_pathways, shortlist_table, tried_by_area

PSORIASIS = "MONDO:0005083"


def test_an_entity_without_a_resolved_target_counts_as_labelled_but_adds_no_pathway():
    labelled = pd.DataFrame({"mondo_id": [PSORIASIS, PSORIASIS], "moiety_id": [1, 2]})
    out = approved_pathways(labelled, {1: ("IL17A|binder_neutralizer", "IL17A", "binder_neutralizer")},
                            {"IL17A|binder_neutralizer": ("specific", ["IL-17"])})
    assert out.set_index("moiety_id").loc[1, "pathways"] == ["IL-17"]
    assert out.set_index("moiety_id").loc[2, "kind"] == "unresolved"


def test_a_disease_stays_with_three_approved_pathways_and_tried_success_is_the_overlap():
    approved = pd.DataFrame({"mondo_id": [PSORIASIS] * 3, "moiety_id": [1, 2, 3], "kind": ["specific"] * 3,
                             "pathways": [["IL-17"], ["IL-23"], ["TNF", "IL-17"]]})
    tried = pd.DataFrame({"mondo_id": [PSORIASIS] * 3, "pathway": ["IL-17", "JAK-STAT", "IL-23"]})
    row = shortlist_table(tried, approved).set_index("mondo_id").loc[PSORIASIS]
    assert (row.approved_pathways, row.tried_pathways, row.tried_approved, bool(row.stays)) == (3, 3, 2, True)


def test_a_disease_with_two_approved_pathways_is_dropped():
    approved = pd.DataFrame({"mondo_id": [PSORIASIS] * 2, "moiety_id": [1, 2], "kind": ["specific"] * 2,
                             "pathways": [["IL-17"], ["IL-23"]]})
    row = shortlist_table(pd.DataFrame(columns=["mondo_id", "pathway"]), approved).set_index("mondo_id").loc[PSORIASIS]
    assert not row.stays


def test_oncology_and_infectious_disease_are_flagged_apart():
    tried = pd.DataFrame({"area": ["oncology", "autoimmune", "autoimmune"], "mondo_id": ["a", "b", "b"],
                          "pathway": ["EGFR", "TNF", "IL-17"]})
    t = tried_by_area(tried).set_index("area")
    assert t.loc["oncology", "reported_apart"] and not t.loc["autoimmune", "reported_apart"]
    assert t.loc["autoimmune", "median_pathways"] == 2
