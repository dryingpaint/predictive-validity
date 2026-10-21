"""CBER biologics approvals 2015-2025 -> .cache/cber/letters_index.jsonl.

CBER approvals are not in Drugs@FDA. These steps rebuild them from the CBER
yearly approval pages, the product pages and their letters (fda.gov, with
Wayback captures for pages no longer live); every page fetch is cached under
.cache/cber. Run in order:

    python -m pipeline.cber.enumerate_year_pages   # 1  actions on the yearly BLA / supplement pages
    python -m pipeline.cber.crawl_products         # 2  product universe and document links
    python -m pipeline.cber.historic_products      # 2b products no longer on the live master list
    python -m pipeline.cber.download_letters       # 3  approval-letter PDFs linked from product pages
    python -m pipeline.cber.build_letters          # 4  letter <-> product (STN) rows
    python -m pipeline.cber.find_missing           # 5  Wayback captures of the product page taken after the action date
    python -m pipeline.cber.find_missing2          # 5b wider Wayback pass
    python -m pipeline.cber.assemble               # 6  in-scope actions in the CDER letter-index format

fetch holds the HTTP and cache helpers, letters the letter download, parsing and
letter-to-action matching. Scope decisions for yearly-page rows and for letters
found only on product pages, the corrections from the independent verification
and the product classes were made by reading each row or letter and are recorded
in pipeline.cber.decisions. pipeline.fda load-cber loads the assembled index.

Two inputs come from outside these steps. pipeline/cber/historic_missing.json
(read by historic_products) is pinned: master-list rows from the Wayback
snapshots of 2014-2025 whose product pages the live list no longer links.
.cache/cber/cdx_yearpages.json (read by enumerate_year_pages) holds the CDX
capture lists of the pre-2023 yearly pages; enumerate_year_pages queries them
when the file is absent.
"""
