"""CBER biologics approvals 2015-2025 -> .cache/cber/letters_index.jsonl.

CBER approvals are not in Drugs@FDA. These steps rebuild them from the CBER
yearly approval pages, the product pages and their letters (fda.gov, with
Wayback captures for pages no longer live); every fetch is cached under
.cache/cber. Run in order:

    python -m pipeline.cber.enumerate_year_pages   # 1  actions on the yearly BLA / supplement pages
    python -m pipeline.cber.crawl_products         # 2  product universe and document links
    python -m pipeline.cber.historic_products      # 2b products no longer on the live master list
    python -m pipeline.cber.download_letters       # 3  approval-letter PDFs linked from product pages
    python -m pipeline.cber.build_letters          # 4  letter <-> product (STN) rows
    python -m pipeline.cber.find_missing           # 5  letters inside approval-history zips / Wayback
    python -m pipeline.cber.find_missing2          # 5b wider Wayback pass
    python -m pipeline.cber.assemble               # 6  in-scope actions in the CDER letter-index format

Scope decisions for yearly-page rows (yearly_decisions), for letters found
only on product pages (extra_decisions) and product classes
(product_classes) were made by reading each row or letter and are recorded
in those modules. pipeline.fda load-cber loads the assembled index.
"""
