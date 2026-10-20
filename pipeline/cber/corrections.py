"""Corrections to the assembled CBER index from the independent verification
(a second enumeration built from the yearly pages, about 700 product pages,
Wayback captures of 214 retired product pages and 968 letters, each purpose
paragraph read; it matched 318 of 325 records and all 112 original BLAs).

Each entry is keyed by (BLA, supplement) and records why.
"""

DROP = {
    ("125769", "26"): "ABRYSVO administrative supplement aligning the 125769 label with the maternal indication "
                      "approved the same day as original BLA 125768; counting it would double-count that indication",
    ("125408", "575"): "FLUCELVAX trivalent formula: a strain/formula composition change, which every other "
                       "strain update in the index is excluded as (and the parallel Flublok supplement is not listed)",
}

LETTER = {  # (BLA, supplement) -> the letter that is actually for this action
    ("125324", "1371"): {
        "url": "https://www.fda.gov/downloads/BiologicsBloodVaccines/Vaccines/ApprovedProducts/UCM518906.pdf",
        "wayback_pdf": "https://web.archive.org/web/20190208122749id_/https://www.fda.gov/downloads/"
                       "BiologicsBloodVaccines/Vaccines/ApprovedProducts/UCM518906.pdf",
        "sha256": "1254134071c7c999e411e3c22a9a50687e414e9260ead7e2d0d697585113d353",
        "why": "the index carried the letter for 125324/1373 (UCM518910)"},
    ("125285", "194"): {
        "url": "https://www.fda.gov/downloads/BiologicsBloodVaccines/Vaccines/ApprovedProducts/UCM524732.pdf",
        "wayback_pdf": "https://web.archive.org/web/20190208122228id_/https://www.fda.gov/downloads/"
                       "BiologicsBloodVaccines/Vaccines/ApprovedProducts/UCM524732.pdf",
        "sha256": "ea8242a9ad407b74c88186a69c567409d6800e22c88958165bb0db48af687240",
        "why": "letter exists (its text layer is font-shifted, so the parser missed it)"},
}

ADD = [  # actions on no yearly page whose letter the product-page crawl did not reach
    {"appl_no": "103914", "submission_no": "5909", "approval_date": "2016-05-05",
     "change_category": "clinical_data_labeling", "product_brand": "Fluzone Quadrivalent",
     "proper_name": "Influenza Vaccine", "sponsor": "Sanofi Pasteur Inc.", "product_class": "vaccine",
     "url": "https://www.fda.gov/downloads/BiologicsBloodVaccines/Vaccines/ApprovedProducts/UCM500043.pdf",
     "sha256": "28d3c60953db242ed9fd500dd72d23db9442cb38b19bba6af05be1f1c3e40f05",
     "source_page": "Wayback capture of product page ucm356091.htm",
     "letter_note": "adds efficacy data to the package insert, carried over from 103914/5752"},
]
