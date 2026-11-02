"""Would ClinicalTrials.gov's own MeSH indexing of conditions give the same diseases as the LLM mapping?

    python -m scripts.mesh_crosswalk_check

ClinicalTrials.gov indexes each study's conditions (and keywords) to MeSH automatically. MeSH terms
are per study, so a term is attributed to a condition string only through studies that list that
condition alone. Each attributed term is carried to MONDO through MONDO's declared MeSH equivalences
and compared with the condition's LLM-chosen MONDO term (preclin.indication.mondo_id): the same term,
a MONDO ancestor of it (MeSH broader), a descendant (MeSH narrower), or another disease. Writes the
counts, with the hand review of a seeded sample of disagreements (REVIEW), to
report/audits/mesh_crosswalk.json, which report.quality reads.
"""
from __future__ import annotations

import collections
import glob
import gzip
import json
import os

import requests

from report import frame

API = "https://clinicaltrials.gov/api/v2/studies"
QUERY = "AREA[StudyType]INTERVENTIONAL AND AREA[InterventionType](DRUG OR BIOLOGICAL)"
FIELDS = ("protocolSection.identificationModule.nctId,protocolSection.conditionsModule.conditions,"
          "derivedSection.conditionBrowseModule")
CACHE = os.path.join(frame.REPO, ".cache", "ctgov_mesh")
OUT = os.path.join(frame.REPO, "report", "audits", "mesh_crosswalk.json")
STATUSES = ("same disease", "MeSH broader", "MeSH narrower", "different disease",
            "MeSH names a disease, the LLM none", "MeSH term has no MONDO equivalent", "no MeSH term",
            "only in multi-condition studies")
SAMPLE_SEED, SAMPLE_N = 3, 20
# Hand review of SAMPLE_N conditions drawn with SAMPLE_SEED from the two disagreeing statuses
# ("different disease" and "MeSH names a disease, the LLM none"): which mapping names the program's disease
# (llm, mesh or tie), or that the condition is not a disease.
REVIEW = {
    "Normal Healthy Volunteers": "not_a_disease", "Surgical Scar": "not_a_disease",
    "Critical Illness": "not_a_disease", "Food Effect": "not_a_disease", "Sex Behavior": "not_a_disease",
    "Safety and Tolerability in Healthy Subjects": "not_a_disease",
    "Healthy Adult Male and Female Volunteers": "not_a_disease", "Post-surgical Pain": "not_a_disease",
    "Primary Disease": "not_a_disease",
    "Patients With Impaired Renal Function and Haemodialysis": "tie", "Rectal or Anal Cancer": "tie",
    "Malignant Peripheral Nerve Sheath Tumors (MPNST)": "tie",
    "HER2 Expressing Breast or Gastric/Stomach Cancers": "tie",
    "Thyroid Associated Ophthalmopathy": "llm", "Acute Decompensated Heart Failure; Renal Dysfunction": "llm",
    "C3G": "llm", "Pain, Chronic": "llm", "Hypothalamic Obesity": "llm",
    "Treatment of Early Pulmonary Infections With P. Aeruginosa in Cystic Fibrosis Patients": "llm",
    "Prostatic Adenoma": "mesh",
}


def fetch() -> None:
    os.makedirs(CACHE, exist_ok=True)
    session, token, page = requests.Session(), None, 0
    while True:
        params = {"filter.advanced": QUERY, "pageSize": 1000, "format": "json", "fields": FIELDS}
        if token:
            params["pageToken"] = token
        r = session.get(API, params=params, timeout=180)
        r.raise_for_status()
        body = r.json()
        with gzip.open(os.path.join(CACHE, f"page_{page:04d}.json.gz"), "wt") as f:
            json.dump(body["studies"], f)
        page, token = page + 1, body.get("nextPageToken")
        if not token:
            return


def studies() -> dict[str, tuple[list[str], list[str]]]:
    if not glob.glob(os.path.join(CACHE, "*.json.gz")):
        fetch()
    out = {}
    for path in sorted(glob.glob(os.path.join(CACHE, "*.json.gz"))):
        for s in json.load(gzip.open(path, "rt")):
            browse = s.get("derivedSection", {}).get("conditionBrowseModule", {})
            out[s["protocolSection"]["identificationModule"]["nctId"]] = (
                s["protocolSection"].get("conditionsModule", {}).get("conditions", []),
                [m["id"] for m in browse.get("meshes", [])])
    return out


def main() -> None:
    by_study = studies()
    link = frame.query("""SELECT si.nct_id, i.indication_id, i.display_name, i.mondo_id
                          FROM preclin.ctgov_study_indication si JOIN preclin.indication i USING (indication_id)""")
    xref = frame.query("""SELECT term_id AS mondo, substring(xref_id FROM 6) AS mesh FROM preclin.ontology_xref
                          WHERE ontology = 'MONDO' AND equivalent AND xref_id LIKE 'MESH:%%'""")
    mesh_mondo = xref.groupby("mesh").mondo.apply(set).to_dict()
    ancestors = frame.query("SELECT term_id, ancestor_id FROM preclin.ontology_ancestor WHERE ontology = 'MONDO'") \
        .groupby("term_id").ancestor_id.apply(set).to_dict()
    rows = []
    for (iid, name, llm), g in link.groupby(["indication_id", "display_name", "mondo_id"], dropna=False):
        single = [n for n in g.nct_id if n in by_study and len(by_study[n][0]) == 1]
        mesh = {m for n in single for m in by_study[n][1]}
        mondo = {t for m in mesh for t in mesh_mondo.get(m, ())}
        if not single:
            status = "only in multi-condition studies"
        elif not mesh:
            status = "no MeSH term"
        elif not mondo:
            status = "MeSH term has no MONDO equivalent"
        elif not isinstance(llm, str):
            status = "MeSH names a disease, the LLM none"
        elif llm in mondo:
            status = "same disease"
        elif mondo & ancestors.get(llm, set()):
            status = "MeSH broader"
        elif any(llm in ancestors.get(t, ()) for t in mondo):
            status = "MeSH narrower"
        else:
            status = "different disease"
        rows.append((name, status, len(g)))
    counts = collections.Counter(s for _, s, _ in rows)
    links = collections.Counter()
    for _, s, n in rows:
        links[s] += n
    reviewed = collections.Counter(REVIEW.values())
    audit = {"conditions": len(rows), "study_condition_links": sum(links.values()),
             "statuses": {s: {"conditions": counts[s], "links": links[s]} for s in STATUSES},
             "review": {"sample": SAMPLE_N, "seed": SAMPLE_SEED, **{k: reviewed[k] for k in
                                                                   ("not_a_disease", "llm", "mesh", "tie")}}}
    with open(OUT, "w") as f:
        json.dump(audit, f, indent=1)
    print(json.dumps(audit, indent=1))


if __name__ == "__main__":
    main()
