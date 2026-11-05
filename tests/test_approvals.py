"""What the approval judge is shown and which answers it may give: the documents read for an
efficacy supplement with no letter, the trials and ontology context of each disease, and the
efficacy-supplement dates admitted as first approvals."""
from __future__ import annotations

from datetime import date

import pytest

from pipeline.approvals import BEFORE, INCLUSION_CHARS, inclusion, payloads, render, validate
from pipeline.ctgov import COLUMNS, row
from pipeline.fda import action_documents


def doc(type_id: str, appl: str, sub_type: str, no: str, url: str) -> dict:
    return {"ApplicationDocsTypeID": type_id, "ApplNo": appl, "SubmissionType": f"{sub_type}      ",
            "SubmissionNo": no, "ApplicationDocsURL": url, "ApplicationDocsDate": "2018-10-11 00:00:00"}


def test_supplement_without_letter_is_read_from_its_label_else_its_review():
    wanted = {("202439", "SUPPL", "25"), ("202439", "SUPPL", "35"), ("202439", "SUPPL", "40"),
              ("202439", "SUPPL", "41"), ("300000", "ORIG", "1")}
    docs = [doc("2", "202439", "SUPPL", "25", "http://x/label/2018/202439s025lbl.pdf"),
            doc("1", "202439", "SUPPL", "35", "http://x/appletter/2021/202439s035ltr.pdf"),
            doc("2", "202439", "SUPPL", "35", "http://x/label/2021/202439s035lbl.pdf"),
            doc("3", "202439", "SUPPL", "40", "http://x/nda/2022/202439toc.html"),
            doc("21", "202439", "SUPPL", "40", "http://x/nda/2022/202439s040sumr.pdf"),
            doc("3", "202439", "SUPPL", "41", "http://x/nda/2022/202439s041toc.html"),
            doc("2", "300000", "ORIG", "1", "http://x/label/2020/300000lbl.pdf"),
            doc("1", "202439", "SUPPL", "99", "http://x/appletter/2023/202439s099ltr.pdf")]
    got = sorted(d["ApplicationDocsURL"].rsplit("/", 1)[1] for d in action_documents(wanted, docs))
    assert got == ["202439s025lbl.pdf", "202439s035ltr.pdf", "202439s040sumr.pdf"]


def test_inclusion_keeps_the_inclusion_criteria_only():
    text = "Inclusion Criteria:\n\n* Histologically proven,\n  dMMR/MSI-H solid tumors\n\nExclusion Criteria:\n\n* Prior PD-1"
    assert inclusion(text) == "Inclusion Criteria: * Histologically proven, dMMR/MSI-H solid tumors"
    assert inclusion(None) == ""
    assert len(inclusion("Inclusion Criteria: " + "x " * INCLUSION_CHARS)) == INCLUSION_CHARS + 4


def test_eligibility_criteria_are_loaded_from_the_registry_record():
    study = {"protocolSection": {"identificationModule": {"nctId": "NCT06333314"},
                                 "eligibilityModule": {"eligibilityCriteria": "Inclusion Criteria: dMMR"}}}
    assert dict(zip(COLUMNS, row(study, 7)))["eligibility_criteria"] == "Inclusion Criteria: dMMR"


def disease(mondo: str, label: str, trials: list[str]) -> dict:
    return {"mondo_id": mondo, "label": label, "definition": f"{label} definition",
            "ancestors": ["adrenal carcinoma", "cancer"], "conditions": [label], "trials": trials}


def entity_payload() -> dict:
    entities = {1: {"name": "dostarlimab", "apps": {"BLA 761174": date(2021, 4, 22), "BLA 761223": date(2021, 8, 17)}}}
    events = {1: {(date(2021, 8, 17), "dMMR solid tumors"): {
        "date": "2021-08-17", "appl": "BLA 761223", "kind": "original_approval", "use": "dMMR solid tumors",
        "disease": "solid tumor", "qualifiers": ["dMMR"], "partners": [], "source": "letter"}}}
    supplements = {1: [{"date": "2023-07-31", "appl": "BLA 761174", "submission": "S-6"},
                       {"date": "2021-08-17", "appl": "BLA 761223", "submission": "S-1"},
                       {"date": "2022-02-09", "appl": "BLA 761174", "submission": "S-2"}]}
    diseases = {1: [disease("MONDO:0006639", "adrenal cortex carcinoma", ["NCT06333314"]),
                    disease("MONDO:0003060", "biliary tract cancer", ["NCT04779151", "NCT06333314"])]}
    trials = {"NCT06333314": {"title": "Dostarlimab in dMMR/MSI tumours", "inclusion": "dMMR/MSI-H solid tumors"},
              "NCT04779151": {"title": "Niraparib and dostarlimab basket", "inclusion": "bi-allelic BRCA1/2 loss"},
              "NCT09999999": {"title": "another entity's trial", "inclusion": "-"}}
    work = payloads(entities, events, supplements, {}, {}, diseases, trials)
    assert list(work) == ["1:0"]
    return work["1:0"]


def test_payload_lists_each_named_trial_once_with_its_inclusion_criteria():
    p = entity_payload()
    assert list(p["trials"]) == ["NCT04779151", "NCT06333314"]
    text = render(p)
    assert text.count("NCT06333314: Dostarlimab in dMMR/MSI tumours | inclusion: dMMR/MSI-H solid tumors") == 1
    assert "| ancestors: adrenal carcinoma; cancer |" in text
    assert "trials: NCT04779151, NCT06333314" in text


def test_supplements_without_a_read_use_are_listed_and_admitted_as_first_approvals():
    p = entity_payload()
    text = render(p)
    other = text.split("Other efficacy supplements")[1].split("Applications:")[0]
    assert "2022-02-09 BLA 761174 S-2" in other and "2023-07-31 BLA 761174 S-6" in other
    assert "2021-08-17" not in other  # its use is shown as an event
    decision = {"mondo_id": "MONDO:0003060", "approved": "no", "first_approval": "none",
                "relation": "none", "evidence": ""}
    for answer in ("2022-02-09", "2021-08-17", "2021-04-22", BEFORE):
        validate(p, {"decisions": [decision, {**decision, "mondo_id": "MONDO:0006639", "approved": "yes",
                                              "first_approval": answer}]})
    with pytest.raises(ValueError, match="not an event date"):
        validate(p, {"decisions": [decision, {**decision, "mondo_id": "MONDO:0006639", "approved": "yes",
                                              "first_approval": "2022-02-10"}]})


def test_an_original_approval_the_payload_does_not_record_may_predate_its_first_action():
    p = {"events": [{"date": "2016-04-14", "appl": "BLA 125549"}], "supplements": [], "originals": [],
         "diseases": [{"mondo_id": "MONDO:1"}]}
    validate(p, {"decisions": [{"mondo_id": "MONDO:1", "first_approval": "2014-10-29", "approved": "yes"}]})
    with pytest.raises(ValueError):  # after the first listed action: not an original approval
        validate(p, {"decisions": [{"mondo_id": "MONDO:1", "first_approval": "2017-01-02", "approved": "yes"}]})
    recorded = {**p, "originals": [("BLA 125549", "2016-04-14")]}
    with pytest.raises(ValueError):  # the original is recorded, so only listed dates count
        validate(recorded, {"decisions": [{"mondo_id": "MONDO:1", "first_approval": "2014-10-29", "approved": "yes"}]})
