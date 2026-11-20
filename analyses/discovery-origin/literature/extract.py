"""Extract the per-drug discovery labels of Swinney & Anthony 2011 and Eder et al. 2014 from their supplements.

    .venv/bin/python analyses/discovery-origin/literature/extract.py <folder with the downloaded supplements>

Inputs (download links in README.md): swinney2011_S1.xls (Table S1) and eder2014_MOESM9.pdf (Table S1). Needs xlrd
for the .xls and pdftotext (poppler) for the PDF. Writes swinney2011_table_s1.csv and eder2014_table_s1.csv beside
this file. Swinney's sheet is copied as published. Eder's PDF text is parsed into one block per drug (a name line
followed by "Indication"); the approach is the block's first line starting "Target-based" or "Systems-based", with a
following line naming the type joined to it.
"""
import os
import re
import subprocess
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = {"Indication", "Molecule", "Structure", "First Patent", "Approved", "Target/MoA", "Approach",
          "First published", "Discovered"}
PAGE_FURNITURE = ("NATURE REVIEWS", "www.nature.com", "SUPPLEMENTARY INFORMATION", "In format provided", "Table S1")


def swinney(src: str) -> pd.DataFrame:
    x = pd.read_excel(os.path.join(src, "swinney2011_S1.xls"), sheet_name="NMEs", header=None).iloc[2:, :5]
    x.columns = ["generic_name", "brand_name", "year_approved", "discovery_approach", "classification"]
    return x.dropna(subset=["generic_name"])


def eder(src: str) -> pd.DataFrame:
    text = subprocess.run(["pdftotext", os.path.join(src, "eder2014_MOESM9.pdf"), "-"], capture_output=True,
                          text=True, check=True).stdout
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln and not ln.startswith(PAGE_FURNITURE)]
    starts = [i for i in range(len(lines) - 1) if lines[i + 1] == "Indication" and lines[i] not in FIELDS]
    rows = []
    for k, s in enumerate(starts):
        block = lines[s + 1:(starts[k + 1] if k + 1 < len(starts) else len(lines))]

        def after(field: str) -> str:
            if field not in block:
                return ""
            j, out = block.index(field) + 1, []
            while j < len(block) and block[j] not in FIELDS:
                out.append(block[j])
                j += 1
            return " ".join(out)
        found = [b for b in block if re.match(r"^(Target-based|Systems-based)", b)]
        approach = found[0] if found else ""
        if approach and len(approach) < 40:
            nxt = block[block.index(approach) + 1] if block.index(approach) + 1 < len(block) else ""
            if re.match(r"^(low molecular weight|biologic|phenotypic|chemocentric)", nxt, re.I):
                approach += " " + nxt
        rows.append({"drug": lines[s], "approach": approach, "molecule": after("Molecule"),
                     "indication": after("Indication"), "approved": after("Approved"),
                     "target_moa": after("Target/MoA")})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    src = sys.argv[1]
    swinney(src).to_csv(os.path.join(HERE, "swinney2011_table_s1.csv"), index=False)
    eder(src).to_csv(os.path.join(HERE, "eder2014_table_s1.csv"), index=False)
