"""Step 1: enumerate every action listed on CBER yearly BLA / BLA-supplement pages, 2015-2025."""
import json
import os

from pipeline.cber import fetch
from pipeline.cber import parse_year

BASE = fetch.BASE
LIVE = "https://www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/"
OLD = "www.fda.gov/BiologicsBloodVaccines/DevelopmentApprovalProcess/BiologicalApprovalsbyYear/"
OLD_UCM = {2015: ("ucm434961", "ucm434963"), 2016: ("ucm482397", "ucm482398"),
           2017: ("ucm547553", "ucm547555"), 2018: ("ucm596371", "ucm596373"),
           2019: ("ucm631669", "ucm631673")}


def sources(year, kind):
    slug = (f"{year}-biological-license-application-approvals" if kind == "BLA"
            else f"{year}-biological-license-application-supplement-noteworthy-approvals")
    if year >= 2023:
        return [("live", LIVE + slug)]
    out = []
    cdx = json.load(open(os.path.join(BASE, "cdx_yearpages.json")))
    cands = ["www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/" + slug]
    if year in OLD_UCM:
        cands.append(OLD + OLD_UCM[year][0 if kind == "BLA" else 1] + ".htm")
    for c in cands:
        caps = cdx.get(f"{year}|{kind}|{c}") or []
        if caps:
            cap = caps[-1]
            out.append(("wayback", f"https://web.archive.org/web/{cap['timestamp']}id_/{cap['original']}"))
    return out


def main():
    rows_out = []
    status = []
    for year in range(2015, 2026):
        for kind in ("BLA", "SUPPL"):
            seen = {}
            for src, url in sources(year, kind):
                t, path, final, st = fetch.get_html(url)
                if not t:
                    status.append({"year": year, "kind": kind, "url": url, "status": st, "rows": 0})
                    continue
                rows = parse_year.parse_tables(t, url.split("id_/", 1)[-1] if "id_/" in url else url)
                status.append({"year": year, "kind": kind, "url": url, "status": st, "rows": len(rows),
                               "html": os.path.basename(path)})
                for r in rows:
                    if not r["stn"] and not r["name"]:
                        continue
                    key = (r["stn"].replace(" ", ""), r["approval_date"], r["name"][:30])
                    if key in seen:
                        seen[key]["listing_pages"].append(url)
                        continue
                    appl, sub = parse_year.split_stn(r["stn"])
                    rec = {"list_year": year, "list_kind": kind, "appl_no": appl, "stn_suppl": sub,
                           **r, "listing_page": url, "listing_pages": [url],
                           "listing_html": os.path.basename(path)}
                    seen[key] = rec
            rows_out.extend(seen.values())
            print(year, kind, len(seen), flush=True)
    with open(os.path.join(BASE, "year_page_rows.jsonl"), "w") as f:
        for r in rows_out:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(BASE, "year_page_status.json"), "w") as f:
        json.dump(status, f, indent=1)


if __name__ == "__main__":
    main()
