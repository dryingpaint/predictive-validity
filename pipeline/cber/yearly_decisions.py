"""Manual scope/category decisions for every row of the CBER yearly approval pages.

Each decision was made by reading the row (product, indication text) on the yearly page.
Keys are row indices into year_page_rows.jsonl (fixed by enumerate_year_pages.py ordering);
the script writes them out keyed by STN|date so they survive re-ordering.

Categories for supplements:
  new_indication, indication_revision, population_expansion, dosing_regimen,
  accelerated_to_traditional, new_formulation_clinical, clinical_data_labeling   -> in scope
  cmc_manufacturing, diagnostic_device, blood_establishment, duplicate_row      -> out of scope
Originals: original_bla (in scope) or diagnostic_device / blood_establishment /
  further_manufacturing (out of scope).
"""
import json
import os

from pipeline.cber import fetch

_BE = "blood_establishment"
_DX = "diagnostic_device"
_FM = "further_manufacturing"
# Original-BLA rows that are out of scope, keyed by the first BLA number in the row's STN cell.
OUT_ORIG = {
    "125367": _BE, "125396": _BE, "125756": _BE, "125751": _BE, "125749": _BE, "125766": _BE,
    "125801": _BE, "125790": _BE, "125762": _BE, "125767": _BE, "125765": _BE, "125783": _BE,
    "125580": _FM, "125581": _FM, "125660": _FM,
}
for _a in ("125575 125532 125529 125533 125550 125551 125576 125465 125653 125464 125463 125637 125638 "
           "125583 125500 125567 125667 125662 125658 125652 125589 125588 125599 125615 125616 125617 "
           "125618 125699 125670 125689 125680 125669 125681 125679 125677 125675 125674 125684 125686 "
           "125687 125688 125673 125664 125665 125715 125716 125710 125759 125705 125707 125708 125711 "
           "125792 125778 125808 125803 125804 125802 125799 125855 125854 125853 125852 125851 125850 "
           "125849 125848 125753").split():
    OUT_ORIG[_a] = _DX

DUP_ROWS = {94}  # FIBRYNA: same STN 125612/0 and date as the FIBRYGA row (typo on the 2017 page)

SUPPL = {
    13: "population_expansion", 14: "population_expansion", 15: "new_indication", 16: "clinical_data_labeling",
    17: "new_indication", 18: "population_expansion", 19: "new_indication", 20: "accelerated_to_traditional",
    21: "clinical_data_labeling", 22: "clinical_data_labeling", 23: "new_indication", 24: "dosing_regimen",
    25: "clinical_data_labeling",
    41: "dosing_regimen", 42: "population_expansion", 43: "cmc_manufacturing", 44: "population_expansion",
    45: "diagnostic_device", 46: "diagnostic_device", 47: "diagnostic_device", 48: "diagnostic_device",
    49: "diagnostic_device", 50: "diagnostic_device", 51: "diagnostic_device", 52: "diagnostic_device",
    53: "diagnostic_device", 54: "diagnostic_device",
    55: "new_formulation_clinical", 56: "dosing_regimen", 57: "new_indication", 58: "clinical_data_labeling",
    59: "clinical_data_labeling", 60: "population_expansion", 61: "clinical_data_labeling",
    62: "clinical_data_labeling", 63: "new_formulation_clinical", 64: "population_expansion",
    65: "population_expansion", 66: "population_expansion", 67: "new_formulation_clinical",
    68: "dosing_regimen", 69: "population_expansion", 70: "new_indication", 71: "clinical_data_labeling",
    95: "clinical_data_labeling", 96: "new_indication", 97: "new_formulation_clinical",
    98: "population_expansion", 99: "population_expansion", 100: "clinical_data_labeling",
    101: "diagnostic_device", 102: "diagnostic_device", 103: "diagnostic_device", 104: "diagnostic_device",
    105: "diagnostic_device", 106: "clinical_data_labeling", 107: "new_indication",
    108: "clinical_data_labeling", 109: "cmc_manufacturing", 110: "cmc_manufacturing",
    111: "accelerated_to_traditional", 112: "diagnostic_device", 113: "new_indication",
    114: "cmc_manufacturing", 115: "new_formulation_clinical",
    137: "indication_revision", 138: "population_expansion", 139: "population_expansion",
    140: "dosing_regimen", 141: "population_expansion", 142: "new_indication", 143: "diagnostic_device",
    144: "population_expansion", 145: "diagnostic_device", 146: "new_indication", 147: "new_indication",
    148: "population_expansion", 149: "duplicate_row",
    174: "dosing_regimen", 175: "diagnostic_device", 176: "new_formulation_clinical",
    177: "clinical_data_labeling", 178: "new_indication", 179: "diagnostic_device",
    180: "clinical_data_labeling", 181: "diagnostic_device", 182: "diagnostic_device",
    183: "diagnostic_device", 184: "diagnostic_device", 185: "diagnostic_device", 186: "diagnostic_device",
    187: "diagnostic_device", 188: "dosing_regimen", 189: "dosing_regimen",
    198: "population_expansion", 199: "population_expansion", 200: "clinical_data_labeling",
    201: "new_indication", 202: "population_expansion", 203: "dosing_regimen",
    204: "clinical_data_labeling", 205: "new_indication", 206: "new_indication", 207: "new_indication",
    208: "diagnostic_device", 209: "cmc_manufacturing", 210: "new_formulation_clinical",
    211: "clinical_data_labeling", 212: "clinical_data_labeling",
    226: "accelerated_to_traditional", 227: "population_expansion", 228: "population_expansion",
    229: "new_indication", 230: "population_expansion", 231: "new_indication",
    232: "clinical_data_labeling", 233: "clinical_data_labeling", 234: "clinical_data_labeling",
    235: "dosing_regimen", 236: "clinical_data_labeling", 237: "population_expansion",
    238: "new_indication", 239: "population_expansion", 240: "new_indication",
    241: "clinical_data_labeling",
    256: "cmc_manufacturing", 257: "cmc_manufacturing", 258: "new_indication",
    259: "clinical_data_labeling", 260: "new_indication", 261: "clinical_data_labeling",
    262: "clinical_data_labeling", 263: "clinical_data_labeling", 264: "population_expansion",
    265: "new_indication", 266: "population_expansion", 267: "new_indication", 268: "new_indication",
    269: "new_indication",
    295: "clinical_data_labeling", 296: "clinical_data_labeling", 297: "population_expansion",
    298: "dosing_regimen", 299: "population_expansion", 300: "population_expansion",
    301: "population_expansion", 302: "clinical_data_labeling", 303: "dosing_regimen",
    304: "clinical_data_labeling", 305: "clinical_data_labeling", 306: "clinical_data_labeling",
    307: "new_indication", 308: "population_expansion", 309: "dosing_regimen", 310: "dosing_regimen",
    311: "dosing_regimen", 312: "clinical_data_labeling", 313: "population_expansion",
    314: "new_indication",
    333: "new_indication", 334: "population_expansion", 335: "clinical_data_labeling",
    336: "population_expansion", 337: "clinical_data_labeling", 338: "clinical_data_labeling",
    339: "new_indication", 340: "dosing_regimen", 341: "clinical_data_labeling",
    342: "accelerated_to_traditional", 343: "new_indication", 344: "population_expansion",
    345: "dosing_regimen", 346: "population_expansion", 347: "population_expansion",
    348: "new_indication", 349: "new_indication", 350: "clinical_data_labeling", 351: "new_indication",
    352: "new_indication", 353: "population_expansion", 354: "new_indication",
    355: "new_formulation_clinical", 356: "new_indication", 357: "new_indication",
    379: "clinical_data_labeling", 380: "new_indication", 381: "new_indication",
    382: "clinical_data_labeling", 383: "new_indication", 384: "population_expansion",
    385: "new_indication", 386: "strain_or_formula_update", 387: "strain_or_formula_update",
    388: "strain_or_formula_update", 389: "indication_revision", 390: "clinical_data_labeling",
    391: "clinical_data_labeling", 392: "dosing_regimen", 393: "population_expansion",
    394: "new_formulation_clinical", 395: "population_expansion", 396: "clinical_data_labeling",
    397: "population_expansion", 398: "clinical_data_labeling", 399: "population_expansion",
    400: "population_expansion", 401: "cmc_manufacturing", 402: "clinical_data_labeling",
    403: "population_expansion", 404: "diagnostic_device",
}

IN_SCOPE_SUPPL = {"new_indication", "indication_revision", "population_expansion", "dosing_regimen",
                  "accelerated_to_traditional", "new_formulation_clinical", "clinical_data_labeling"}


def decisions():
    rows = [json.loads(l) for l in open(os.path.join(fetch.BASE, "year_page_rows.jsonl"))]
    out = {}
    for i, r in enumerate(rows):
        if r["list_kind"] == "BLA":
            from pipeline.cber import parse_year
            appl, _ = parse_year.split_stn(r["stn"])
            cat = OUT_ORIG.get(appl, "original_bla")
            if i in DUP_ROWS:
                cat = "duplicate_row"
            scope = cat == "original_bla"
        else:
            cat = SUPPL[i]
            scope = cat in IN_SCOPE_SUPPL
        out[i] = {"row": i, "stn": r["stn"], "approval_date": r["approval_date"], "name": r["name"],
                  "category": cat, "in_scope": scope}
    return out


if __name__ == "__main__":
    d = decisions()
    import collections
    print(collections.Counter((v["category"], v["in_scope"]) for v in d.values()))
