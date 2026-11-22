from pipeline.opentargets import evidence_row


def test_an_evidence_row_keeps_its_papers_and_the_sources_own_ids():
    r = {"id": "e1", "targetId": "ENSG1", "diseaseId": "Orphanet_558", "datasourceId": "orphanet",
         "diseaseFromSourceId": "Orphanet_558", "diseaseFromSource": "Marfan syndrome", "targetFromSourceId": "FBN1",
         "literature": ["1852208", "1852206"], "publicationDate": "1991-07-25", "alleleOrigins": ["germline"]}
    row = evidence_row(r, release=1)
    detail = row[12].adapted
    assert detail["literature"] == ["1852208", "1852206"]
    assert detail["diseaseFromSourceId"] == "Orphanet_558" and detail["targetFromSourceId"] == "FBN1"
    assert row[6] == 1991


def test_an_evidence_row_without_papers_has_no_literature_field():
    r = {"id": "e2", "targetId": "ENSG1", "diseaseId": "MONDO_1", "datasourceId": "reactome", "reactionId": "R-HSA-1",
         "pathways": [{"id": "R-HSA-9", "name": "Signalling"}]}
    detail = evidence_row(r, release=1)[12].adapted
    assert "literature" not in detail and detail["reactionId"] == "R-HSA-1"
    assert detail["pathways"] == [{"id": "R-HSA-9", "name": "Signalling"}]
