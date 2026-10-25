"""ClinicalTrials.gov snapshot -> preclin.ctgov_study.

    python -m pipeline.ctgov fetch   # every interventional study with a DRUG or BIOLOGICAL intervention
    python -m pipeline.ctgov load    # cached pages -> preclin.ctgov_study (one row per NCT id)

The snapshot covers all sponsors and all dates so that a molecule's full
trial history (earlier phases, later or still-active trials) is visible when
programs are assembled. Raw API pages are kept gzipped under .cache/ctgov.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import os
from datetime import date, datetime, timezone

import requests
from psycopg2.extras import Json, execute_values

from pipeline import llm

CACHE = os.path.join(llm.REPO, ".cache", "ctgov")
API = "https://clinicaltrials.gov/api/v2/studies"
QUERY = "AREA[StudyType]INTERVENTIONAL AND AREA[InterventionType](DRUG OR BIOLOGICAL)"


def fetch(_args) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = os.path.join(CACHE, stamp)
    os.makedirs(out, exist_ok=True)
    session = requests.Session()
    token, page = None, 0
    while True:
        params = {"filter.advanced": QUERY, "pageSize": 1000, "format": "json", "countTotal": "true"}
        if token:
            params["pageToken"] = token
        for attempt in range(6):
            try:
                r = session.get(API, params=params, timeout=180)
                r.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 5:
                    raise
        body = r.json()
        with gzip.open(os.path.join(out, f"page_{page:04d}.json.gz"), "wt") as f:
            json.dump(body, f)
        page += 1
        token = body.get("nextPageToken")
        if page == 1:
            print(f"total studies: {body.get('totalCount')}", flush=True)
        if not token:
            break
    print(f"pages={page} -> {out}")


def parse_date(struct: dict | None) -> tuple[date | None, str | None]:
    """CT.gov dates are YYYY-MM-DD or YYYY-MM; a month-only date maps to the 1st."""
    if not struct or not struct.get("date"):
        return None, None
    value = struct["date"]
    parts = value.split("-")
    if len(parts) == 2:
        parts.append("01")
    return date(int(parts[0]), int(parts[1]), int(parts[2])), struct.get("type")


# row() returns values in this order.
COLUMNS = ("nct_id", "brief_title", "official_title", "overall_status", "why_stopped", "phases",
           "start_date", "start_date_type", "primary_completion_date", "primary_completion_date_type",
           "completion_date", "completion_date_type", "first_posted", "last_update_posted",
           "results_first_posted", "has_results", "lead_sponsor", "lead_sponsor_class", "collaborators",
           "enrollment", "allocation", "intervention_model", "masking", "primary_purpose",
           "healthy_volunteers", "conditions", "keywords", "interventions", "arm_groups", "references_",
           "countries", "brief_summary", "source_release_id")
UPSERT = (f"INSERT INTO preclin.ctgov_study ({', '.join(COLUMNS)}) VALUES %s ON CONFLICT (nct_id) DO UPDATE SET "
          + ", ".join(f"{c} = EXCLUDED.{c}" for c in COLUMNS[1:]))


def row(study: dict, release: int) -> tuple:
    p = study.get("protocolSection", {})
    ident, status = p.get("identificationModule", {}), p.get("statusModule", {})
    sponsor, design = p.get("sponsorCollaboratorsModule", {}), p.get("designModule", {})
    arms, cond = p.get("armsInterventionsModule", {}), p.get("conditionsModule", {})
    elig, refs = p.get("eligibilityModule", {}), p.get("referencesModule", {})
    locations = (p.get("contactsLocationsModule") or {}).get("locations") or []
    start, start_t = parse_date(status.get("startDateStruct"))
    pcd, pcd_t = parse_date(status.get("primaryCompletionDateStruct"))
    comp, comp_t = parse_date(status.get("completionDateStruct"))
    first, _ = parse_date(status.get("studyFirstPostDateStruct"))
    last, _ = parse_date(status.get("lastUpdatePostDateStruct"))
    res_first, _ = parse_date(status.get("resultsFirstPostDateStruct"))
    info = design.get("designInfo", {})
    lead = sponsor.get("leadSponsor", {})
    return (
        ident.get("nctId"), ident.get("briefTitle"), ident.get("officialTitle"),
        status.get("overallStatus"), status.get("whyStopped"), design.get("phases") or [],
        start, start_t, pcd, pcd_t, comp, comp_t, first, last, res_first, bool(study.get("hasResults")),
        lead.get("name"), lead.get("class"), Json(sponsor.get("collaborators") or []),
        (design.get("enrollmentInfo") or {}).get("count"), info.get("allocation"),
        info.get("interventionModel"), (info.get("maskingInfo") or {}).get("masking"), info.get("primaryPurpose"),
        elig.get("healthyVolunteers"), cond.get("conditions") or [], cond.get("keywords") or [],
        Json(arms.get("interventions") or []), Json(arms.get("armGroups") or []),
        Json(refs.get("references") or []), sorted({l["country"] for l in locations if l.get("country")}),
        (p.get("descriptionModule") or {}).get("briefSummary"), release,
    )


def load(_args) -> None:
    snap = sorted(glob.glob(os.path.join(CACHE, "*")))[-1]
    pages = sorted(glob.glob(os.path.join(snap, "page_*.json.gz")))
    digest = hashlib.sha256()
    for path in pages:
        digest.update(open(path, "rb").read())
    with llm.connect() as conn, conn.cursor() as cur:
        release = llm.register_release(
            cur, "clinicaltrials_gov_api_v2", os.path.basename(snap), API, digest.hexdigest(),
            {"filter.advanced": QUERY, "pages": len(pages), "sha256_of": "concatenated gzipped page files"})
        n = 0
        for path in pages:
            with gzip.open(path, "rt") as f:
                studies = json.load(f)["studies"]
            execute_values(cur, UPSERT, [row(s, release) for s in studies], page_size=1000)
            n += len(studies)
            conn.commit()
    print(f"loaded {n} studies from {snap}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in [("fetch", fetch), ("load", load)]:
        sub.add_parser(name).set_defaults(fn=fn)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
