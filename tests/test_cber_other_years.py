import pytest

from pipeline.cber.other_years import in_scope, record, validate

ROW = {"year": 2013, "kind": "BLA", "appl_no": "125398", "stn_suppl": None, "approval_date": "2013-12-23",
       "manufacturer": "Novo Nordisk A/S", "listing_page": "https://www.fda.gov/x/ucm338259.htm",
       "row_text": "TRETTEN | Coagulation Factor XIII A-Subunit (Recombinant) | 125398/0 | 12/23/2013"}


def test_only_therapeutic_originals_and_clinical_supplements_are_in_scope():
    assert in_scope("BLA", "original_bla") and not in_scope("BLA", "blood_establishment")
    assert in_scope("SUPPL", "new_indication") and not in_scope("SUPPL", "strain_or_formula_update")


def test_a_category_must_fit_the_row_kind_and_an_in_scope_row_must_name_its_product():
    with pytest.raises(ValueError):
        validate({"kind": "BLA"}, {"category": "new_indication", "brand": "X", "proper_name": "", "product_class": "vaccine"})
    with pytest.raises(ValueError):
        validate({"kind": "BLA"}, {"category": "original_bla", "brand": "", "proper_name": " ", "product_class": "vaccine"})
    validate({"kind": "BLA"}, {"category": "diagnostic_device", "brand": "", "proper_name": "", "product_class": "other_biologic"})


def test_an_original_approval_is_recorded_as_submission_one_dated_by_its_listing():
    out = {"category": "original_bla", "brand": "TRETTEN", "proper_name": "coagulation factor XIII A-subunit (recombinant)",
           "product_class": "blood_plasma_product"}
    r = record(ROW, out)
    assert (r["submission_type"], r["submission_no"], r["approval_date"]) == ("ORIG", "1", "2013-12-23")
    assert r["text"] == ROW["row_text"] and r["error"] == "no_letter_pdf" and r["center"] == "CBER"


def test_a_cder_letter_is_dated_by_its_last_signature_not_the_submission_it_cites():
    from pipeline.fda import signed_on
    text = ("NDA 022529 NDA APPROVAL Dear Mr. Audet: Please refer to your NDA dated December 18, 2009 ... "
            "final report submission: 12/2016 ... /s/ CURTIS J ROSEBRAUGH 06/27/2012 Reference ID: 3151563")
    assert signed_on(text) == "2012-06-27"
    assert signed_on("no signature here") is None
