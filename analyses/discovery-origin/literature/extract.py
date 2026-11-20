"""Extract the per-drug discovery labels of Swinney & Anthony 2011, Eder et al. 2014 and Sadri 2023 from their supplements.

    .venv/bin/python analyses/discovery-origin/literature/extract.py <folder with the downloaded supplements>

Inputs (download links in README.md): swinney2011_S1.xls (Table S1), eder2014_MOESM9.pdf (Table S1) and
jm2c01737_si_001.pdf (Sadri's Supporting Information 1). Needs xlrd for the .xls and pdftotext (poppler) for the
PDFs. Writes swinney2011_table_s1.csv, eder2014_table_s1.csv and sadri2023_si1.csv beside this file. Swinney's sheet
is copied as published. Eder's PDF text is parsed into one block per drug (a name line followed by "Indication"); the
approach is the block's first line starting "Target-based" or "Systems-based", with a following line naming the type
joined to it. Sadri's SI 1 is set in two columns: each drug is a capitalised 12-point heading at a column's left
edge, its year on the next line, and its category in 9-point type to the right of the heading. Each category is
matched to the nearest heading above it in reading order (it may sit up to 8 points higher) that has no category yet. A drug Sadri left
unclassified keeps, as its note, the line after its year ("Not found", "Secondary", "Levo isomer of ..."). Capitalised
lines inside quoted passages that have neither a year nor a category are dropped.
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


SADRI_COLUMNS = (72, 324)  # left edges of the two text columns, in points
# Abridged label as printed beside each drug ("MoA-informed" extracts without "-informed") -> SI 1's complete label
SADRI_CATEGORIES = {
    "Non-human Phenotype": "Non-Human or ex Vivo Phenotypes",
    "Endogenous Phenotypes": "Phenotypic Effects of Endogenous Molecules",
    "MoA Phenotype": "Mechanism of Action-Informed Phenotypes",
    "Sagacious Phenotypes": "Sagaciously Observed Non-Human or ex Vivo Phenotypes",
    "Human Phenotypes": "Human Phenotypes",
    "Historical": "Historically Used",
    "Target-based": "Target-based Assays",
    "Endogenous Biologic": "Endogenous-based Biopharmaceuticals",
    "Other Biologics": "Other Biopharmaceuticals",
}
SADRI_HEADING = re.compile(r"^[A-Z0-9][A-Z0-9 ,\-()/.'+&]*$")
WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="[\d.]+" yMax="([\d.]+)">(.*?)</word>')


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


def sadri(src: str) -> pd.DataFrame:
    text = subprocess.run(["pdftotext", "-bbox", "-f", "2", os.path.join(src, "jm2c01737_si_001.pdf"), "-"],
                          capture_output=True, text=True, check=True).stdout
    events = []  # (page, column, top, kind, text) in reading order
    for page, body in enumerate(text.split("<page ")[1:], 2):
        words = [(float(x), float(top), float(bottom) - float(top), w.replace("&amp;", "&"))
                 for x, top, bottom, w in WORD.findall(body)]
        for col, x0 in enumerate(SADRI_COLUMNS):
            body_lines: dict[int, list] = {}
            for x, top, height, w in words:
                if x0 - 40 <= x < x0 + 250 and abs(height - 10.8) < 0.3 and x - x0 < 150:
                    body_lines.setdefault(round(top), []).append((x, w))
            tops = sorted(body_lines)
            for k, top in enumerate(tops):
                line = sorted(body_lines[top])
                name = " ".join(w for _, w in line)
                if abs(line[0][0] - x0) < 2 and SADRI_HEADING.match(name) and sum(c.isalpha() for c in name) >= 3:
                    after = [" ".join(w for _, w in sorted(body_lines[t])) for t in tops[k + 1:k + 3]]
                    year = after[0] if after and re.fullmatch(r"\d{3,4}", after[0]) else ""
                    note = after[1] if year and len(after) > 1 and not SADRI_HEADING.match(after[1]) else ""
                    events.append((page, col, top, "drug", (name, year, note)))
            labels = sorted((top, w) for x, top, height, w in words
                            if abs(height - 8.1) < 0.3 and 155 < x - x0 < 190)
            group: list = []
            for top, w in labels + [(1e9, "")]:
                if group and top - group[-1][0] >= 14:
                    label = " ".join(g[1] for g in group)
                    if label in SADRI_CATEGORIES:
                        events.append((page, col, group[0][0] + 8, "category", label))
                    group = []
                group.append((top, w))
    rows: list[dict] = []
    for _, _, _, kind, value in sorted(events, key=lambda e: e[:3]):
        if kind == "drug":
            rows.append({"drug": value[0], "year": value[1], "category": "", "category_full": "", "note": value[2]})
        elif rows and not rows[-1]["category"]:
            rows[-1].update(category=value.replace("MoA ", "MoA-informed "), category_full=SADRI_CATEGORIES[value])
    out = pd.DataFrame(rows)
    out = out[(out.year != "") | (out.category != "")]
    out.loc[out.category != "", "note"] = ""
    return out


if __name__ == "__main__":
    src = sys.argv[1]
    swinney(src).to_csv(os.path.join(HERE, "swinney2011_table_s1.csv"), index=False)
    eder(src).to_csv(os.path.join(HERE, "eder2014_table_s1.csv"), index=False)
    sadri(src).to_csv(os.path.join(HERE, "sadri2023_si1.csv"), index=False)
