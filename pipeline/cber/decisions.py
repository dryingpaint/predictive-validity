"""Every manual decision behind the CBER index, each made by reading the source it names.

Yearly-page rows (OUT_ORIG, DUP_ROWS, SUPPL): each decision was made by reading the row (product,
indication text) on the yearly page. Keys are row indices into year_page_rows.jsonl, fixed by
enumerate_year_pages ordering.

Categories for supplements:
  new_indication, indication_revision, population_expansion, dosing_regimen,
  accelerated_to_traditional, new_formulation_clinical, clinical_data_labeling   -> in scope
  cmc_manufacturing, diagnostic_device, blood_establishment, strain_or_formula_update,
  duplicate_row                                                                 -> out of scope
Originals: original_bla (in scope) or diagnostic_device / blood_establishment /
  further_manufacturing / duplicate_row (out of scope).

Product-page letters not on the yearly pages (EXTRA): each entry was decided by reading the
letter's purpose paragraph.

Corrections to the assembled index (DROP, LETTER, ADD): fixes from the independent verification;
each entry says why.

Products (PRODUCTS, SPONSOR_OVERRIDE): brand, proper name and product class for every in-scope BLA.
product_class: vaccine | cell_therapy | gene_therapy | blood_plasma_product | allergenic | other_biologic
  cell_therapy  = unmodified or genetically modified cells given as cells (CAR-T/TCR-T, cord blood,
                  MACI, keratinocyte/fibroblast constructs, islets, thymus tissue, TIL, MSC)
  gene_therapy  = in vivo vectors (AAV, HSV, adenovirus) and ex vivo gene-modified HSC / keratinocyte grafts
  blood_plasma_product = plasma-derived and recombinant plasma-protein analogues (IG, hyperimmune IG,
                  coagulation factors, C1-INH, A1PI, albumin, fibrin sealants, fibrinogen, PCC, plasma,
                  COVID-19 convalescent plasma)
  other_biologic = animal-derived antivenoms/anti-thymocyte globulin, fecal microbiota, acellular tissue grafts
"""

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

# Approval letters found on product pages that are not on the CBER yearly "noteworthy" pages, keyed
# "BLA/supplement". Anything not listed here is out of scope (safety-only labeling, PLLR/format
# conversions, strain updates, manufacturing/CMC, presentations, REMS, diagnostics, CBE
# acknowledgement letters).
EXTRA = {
    "103196/6012": "population_expansion",       # THROMBATE III: pediatric use established
    "103980/6252": "new_indication",             # TISSEEL: adult+pediatric, prevent colonic anastomosis leakage
    "103677/6937": "indication_revision",        # BeneFIX: routine prophylaxis removed <16 y (partial rescission)
    "101447/6129": "dosing_regimen",             # FEIBA: higher infusion rate, reduced reconstitution volume
    "101447/6157": "dosing_regimen",             # FEIBA: regular volume, infusion rate up to 10 U/kg/min
    "125020/2982": "dosing_regimen",             # FluMist: self/caregiver administration
    "125123/2058": "clinical_data_labeling",     # ZOSTAVAX: longer-term effectiveness data
    "125127/992": "clinical_data_labeling",      # Fluarix Quadrivalent: co-administration with Shingrix
    "125251/382": "new_indication",              # WILATE: VWD routine prophylaxis
    "125251/389": "clinical_data_labeling",      # WILATE: WIL-30 pediatric hemophilia A data (PREA)
    "125266/563": "new_indication",              # ARTISS: burns skin grafts adult+pediatric, rhytidectomy flaps
    "125280/235": "clinical_data_labeling",      # IXIARO: study IC51-322 and long-term pediatric data
    "125325/584": "clinical_data_labeling",      # GLASSIA: Study 471101 data (sections 1, 6, 12, 14)
    "125329/176": "population_expansion",        # Gammaplex 10%: PI in children >=2 y
    "125347/309": "accelerated_to_traditional",  # HIBERIX: booster-phase data verifying clinical benefit
    "125416/140": "clinical_data_labeling",      # Octaplas: pediatric PMR study labeling
    "125416/167": "clinical_data_labeling",      # Octaplas: pediatric assessment final study report
    "125426/193": "indication_revision",         # IXINITY: adolescent routine prophylaxis removed (rescission)
    "125426/209": "indication_revision",         # IXINITY: routine prophylaxis >12 y re-instated
    "125444/793": "clinical_data_labeling",      # ALPROLIX: study 998HB303 (previously untreated patients)
    "125488/107": "new_indication",              # ANAVIP: expanded to all North American snake envenomation
    "125510/191": "clinical_data_labeling",      # FLUAD: pediatric use (8.4) from pediatric trials
    "125549/911": "clinical_data_labeling",      # TRUMENBA: pediatric effectiveness statement (8.4)
    "125555/318": "population_expansion",        # NUWIQ: children <2 y
    "125563/274": "clinical_data_labeling",      # VAXELIS: section 6.1 clinical trials experience
    "125566/1034": "clinical_data_labeling",     # ADYNOVATE: final CSR, immunogenicity/PK
    "125574/424": "clinical_data_labeling",      # KOVALTRY: PMC CSR + LEOPOLD Kids extension
    "125577/118": "new_indication",              # VONVENDI: perioperative management of bleeding
    "125582/336": "clinical_data_labeling",      # IDELVION: sections 6 and 14
    "125582/484": "clinical_data_labeling",      # IDELVION: previously untreated patients study
    "125586/512": "clinical_data_labeling",      # ANDEXXA: sections 2, 5, 6, 8, 12.6, 14 revised
    "125591/383": "clinical_data_labeling",      # AFSTYLA: previously untreated patients study
    "125641/67": "clinical_data_labeling",       # SEVENFACT: pediatric use (PREA)
    "125643/362": "clinical_data_labeling",      # YESCARTA: ZUMA-1 cohort 6 safety data
    "125646/429": "clinical_data_labeling",      # KYMRIAH: updated B2202/C2201 study data
    "125671/197": "clinical_data_labeling",      # ESPEROCT: NN7088-3908 trial safety data
    "125690/51": "clinical_data_labeling",       # ERVEBO: study V920-018 in frontline workers
    "125692/16": "accelerated_to_traditional",   # AUDENZ: confirmatory clinical benefit data
    "125694/444": "clinical_data_labeling",      # ZOLGENSMA: study COAV101A12306 safety results
    "125731/189": "population_expansion",        # PREVNAR 20: extended to individuals >=6 weeks
    "125755/91": "indication_revision",          # SKYSONA: safety labeling change revising section 1
    "125769/26": "indication_revision",          # ABRYSVO (BLA 125769): adds maternal indication approved under 125768/0
    "125777/117": "indication_revision",         # IXCHIQ: safety labeling change revising Indications and Usage
    "125781/189": "indication_revision",         # ELEVIDYS: indication limited to ambulatory patients
    # Original BLAs approved 2015-2025 that are not on the yearly BLA lists.
    "125764/0": "original_bla",                  # REGENECYTE (HPC, Cord Blood), 2024-11-20
}

# Corrections to the assembled index, keyed (BLA, supplement).
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

# Product class, brand and proper name of every in-scope BLA.
V, CT, GT, BP, AL, OB = "vaccine", "cell_therapy", "gene_therapy", "blood_plasma_product", "allergenic", "other_biologic"

PRODUCTS = {
    "101069": (V, "M-M-R II", "Measles, Mumps, and Rubella Virus Vaccine Live"),
    "101094": (V, "PNEUMOVAX 23", "Pneumococcal Vaccine Polyvalent"),
    "101447": (BP, "FEIBA", "Anti-Inhibitor Coagulant Complex"),
    "101766": (BP, "Convalescent Plasma, High Titer, Anti-SARS-CoV-2", "Whole Blood and blood components (COVID-19 convalescent plasma)"),
    "103174": (BP, "Prolastin-C", "Alpha1-Proteinase Inhibitor (Human)"),
    "103196": (BP, "THROMBATE III", "Antithrombin III (Human)"),
    "103239": (V, "ENGERIX-B", "Hepatitis B Vaccine (Recombinant)"),
    "103552": (V, "VARIVAX", "Varicella Virus Vaccine Live"),
    "103666": (V, "DAPTACEL", "Diphtheria and Tetanus Toxoids and Acellular Pertussis Vaccine Adsorbed"),
    "103677": (BP, "BeneFIX", "Coagulation Factor IX (Recombinant)"),
    "103738": (AL, "T.R.U.E. TEST", "Thin-Layer Rapid Use Epicutaneous Patch Test"),
    "103788": (OB, "CroFab", "Crotalidae Polyvalent Immune Fab (Ovine)"),
    "103821": (V, "BioThrax", "Anthrax Vaccine Adsorbed"),
    "103869": (OB, "THYMOGLOBULIN", "Anti-thymocyte Globulin (Rabbit)"),
    "103914": (V, "Fluzone", "Influenza Vaccine"),
    "103931": (V, "IMOVAX RABIES", "Rabies Vaccine"),
    "103980": (BP, "TISSEEL", "Fibrin Sealant"),
    "125020": (V, "FluMist", "Influenza Vaccine Live, Intranasal"),
    "125046": (BP, "GAMUNEX-C", "Immune Globulin Injection (Human), 10% Caprylate/Chromatography Purified"),
    "125062": (BP, "OCTAGAM", "Immune Globulin Intravenous (Human)"),
    "125077": (BP, "Flebogamma DIF", "Immune Globulin Intravenous (Human)"),
    "125089": (V, "Menactra", "Meningococcal (Groups A, C, Y and W-135) Polysaccharide Diphtheria Toxoid Conjugate Vaccine"),
    "125105": (BP, "GAMMAGARD LIQUID", "Immune Globulin Infusion (Human)"),
    "125106": (V, "BOOSTRIX", "Tetanus Toxoid, Reduced Diphtheria Toxoid and Acellular Pertussis Vaccine, Adsorbed"),
    "125108": (V, "ProQuad", "Measles, Mumps, Rubella and Varicella Virus Vaccine Live"),
    "125111": (V, "ADACEL", "Tetanus Toxoid, Reduced Diphtheria Toxoid and Acellular Pertussis Vaccine Adsorbed"),
    "125122": (V, "RotaTeq", "Rotavirus Vaccine, Live, Oral, Pentavalent"),
    "125123": (V, "ZOSTAVAX", "Zoster Vaccine Live"),
    "125126": (V, "GARDASIL", "Human Papillomavirus Quadrivalent (Types 6, 11, 16, 18) Vaccine, Recombinant"),
    "125127": (V, "Fluarix", "Influenza Vaccine"),
    "125145": (V, "Pentacel", "DTaP-IPV/Hib Vaccine"),
    "125158": (V, "ACAM2000", "Smallpox and Mpox (Vaccinia) Vaccine, Live"),
    "125163": (V, "FluLaval", "Influenza Vaccine"),
    "125201": (BP, "PRIVIGEN", "Immune Globulin Intravenous (Human), 10% Liquid"),
    "125251": (BP, "WILATE", "von Willebrand Factor/Coagulation Factor VIII Complex (Human)"),
    "125254": (V, "AFLURIA", "Influenza Vaccine"),
    "125264": (BP, "XYNTHA", "Antihemophilic Factor (Recombinant)"),
    "125266": (BP, "ARTISS", "Fibrin Sealant (Human)"),
    "125267": (BP, "CINRYZE", "C1 Esterase Inhibitor (Human)"),
    "125280": (V, "IXIARO", "Japanese Encephalitis Vaccine, Inactivated, Adsorbed"),
    "125285": (V, "Flublok", "Influenza Vaccine"),
    "125287": (BP, "Berinert", "C1 Esterase Inhibitor (Human)"),
    "125297": (V, "Agriflu", "Influenza Virus Vaccine"),
    "125300": (V, "MENVEO", "Meningococcal (Groups A, C, Y, and W-135) Oligosaccharide Diphtheria CRM197 Conjugate Vaccine"),
    "125317": (BP, "RiaSTAP", "Fibrinogen Concentrate (Human)"),
    "125324": (V, "Prevnar 13", "Pneumococcal 13-valent Conjugate Vaccine (Diphtheria CRM197 Protein)"),
    "125325": (BP, "GLASSIA", "Alpha-1-Proteinase Inhibitor (Human)"),
    "125329": (BP, "Gammaplex", "Immune Globulin Intravenous (Human)"),
    "125347": (V, "HIBERIX", "Haemophilus b Conjugate Vaccine (Tetanus Toxoid Conjugate)"),
    "125350": (BP, "HIZENTRA", "Immune Globulin Subcutaneous (Human), 20% Liquid"),
    "125351": (BP, "TachoSil", "Fibrin Sealant Patch"),
    "125389": (BP, "BIVIGAM", "Immune Globulin Intravenous (Human), 10% Liquid"),
    "125392": (BP, "EVARREST", "Fibrin Sealant Patch"),
    "125396": (BP, "Convalescent Plasma, High Titer, Anti-SARS-CoV-2", "Whole Blood and Blood Components (COVID-19 convalescent plasma)"),
    "125402": (BP, "HYQVIA", "Immune Globulin Infusion 10% (Human) with Recombinant Human Hyaluronidase"),
    "125408": (V, "Flucelvax", "Influenza Vaccine"),
    "125416": (BP, "Octaplas", "Pooled Plasma (Human), Solvent/Detergent Treated"),
    "125419": (V, "AREPANRIX (Q-Pan H5N1)", "Influenza A (H5N1) Virus Monovalent Vaccine, Adjuvanted"),
    "125426": (BP, "IXINITY", "Coagulation Factor IX (Recombinant)"),
    "125428": (V, "HEPLISAV-B", "Hepatitis B Vaccine (Recombinant), Adjuvanted"),
    "125444": (BP, "ALPROLIX", "Coagulation Factor IX (Recombinant), Fc Fusion Protein"),
    "125466": (BP, "NOVOEIGHT", "Antihemophilic Factor (Recombinant)"),
    "125471": (AL, "ORALAIR", "Sweet Vernal, Orchard, Perennial Rye, Timothy, and Kentucky Blue Grass Mixed Pollens Allergen Extract"),
    "125478": (AL, "RAGWITEK", "Short Ragweed Pollen Allergen Extract"),
    "125487": (BP, "ELOCTATE", "Antihemophilic Factor (Recombinant), Fc Fusion Protein"),
    "125488": (OB, "ANAVIP", "Crotalidae Immune F(ab')2 (Equine)"),
    "125506": (BP, "COAGADEX", "Coagulation Factor X (Human)"),
    "125508": (V, "GARDASIL 9", "Human Papillomavirus 9-valent Vaccine, Recombinant"),
    "125510": (V, "FLUAD", "Influenza Vaccine, Adjuvanted"),
    "125518": (GT, "IMLYGIC", "talimogene laherparepvec"),
    "125523": (BP, "RAPLIXA", "Fibrin Sealant (Human)"),
    "125525": (V, "QUADRACEL", "Diphtheria and Tetanus Toxoids and Acellular Pertussis Adsorbed and Inactivated Poliovirus Vaccine"),
    "125546": (V, "BEXSERO", "Meningococcal Group B Vaccine"),
    "125549": (V, "TRUMENBA", "Meningococcal Group B Vaccine"),
    "125555": (BP, "NUWIQ", "Antihemophilic Factor (Recombinant)"),
    "125562": (BP, "ANTHRASIL", "Anthrax Immune Globulin Intravenous (Human)"),
    "125563": (V, "VAXELIS", "DTaP-IPV-Hib-HepB Vaccine"),
    "125566": (BP, "ADYNOVATE", "Antihemophilic Factor (Recombinant), PEGylated"),
    "125574": (BP, "KOVALTRY", "Antihemophilic Factor (Recombinant)"),
    "125577": (BP, "VONVENDI", "von Willebrand Factor (Recombinant)"),
    "125579": (AL, "Rubber Panel T.R.U.E. TEST", "Rubber Panel Thin-Layer Rapid Use Epicutaneous Patch Test"),
    "125582": (BP, "IDELVION", "Coagulation Factor IX (Recombinant), Albumin Fusion Protein"),
    "125585": (CT, "HPC, Cord Blood (Bloodworks)", "HPC, Cord Blood"),
    "125586": (BP, "ANDEXXA", "coagulation factor Xa (recombinant), inactivated-zhzo"),
    "125587": (BP, "PANZYGA", "Immune Globulin Intravenous (Human)-ifas"),
    "125590": (BP, "ASCENIV", "Immune Globulin Intravenous, Human-slra"),
    "125591": (BP, "AFSTYLA", "Antihemophilic Factor (Recombinant), Single Chain"),
    "125592": (AL, "ODACTRA", "House Dust Mite (Dermatophagoides farinae and D. pteronyssinus) Allergen Extract"),
    "125594": (CT, "CLEVECORD", "HPC, Cord Blood"),
    "125596": (BP, "CUVITRU", "Immune Globulin Subcutaneous (Human), 20% Solution"),
    "125597": (V, "VAXCHORA", "Cholera Vaccine, Live, Oral"),
    "125603": (CT, "MACI", "autologous cultured chondrocytes on porcine collagen membrane"),
    "125606": (BP, "HAEGARDA", "C1 Esterase Inhibitor Subcutaneous (Human)"),
    "125610": (GT, "LUXTURNA", "voretigene neparvovec-rzyl"),
    "125611": (BP, "REBINYN", "Coagulation Factor IX (Recombinant), GlycoPEGylated"),
    "125612": (BP, "FIBRYGA", "Fibrinogen (Human)"),
    "125613": (BP, "KEDRAB", "Rabies Immune Globulin (Human)"),
    "125614": (V, "SHINGRIX", "Zoster Vaccine Recombinant, Adjuvanted"),
    "125640": (BP, "VISTASEAL", "Fibrin Sealant (Human)"),
    "125641": (BP, "SEVENFACT", "coagulation factor VIIa (recombinant)-jncw"),
    "125643": (CT, "YESCARTA", "axicabtagene ciloleucel"),
    "125644": (BP, "ALBUMINEX", "Albumin (Human)"),
    "125646": (CT, "KYMRIAH", "tisagenlecleucel"),
    "125657": (CT, "HPC, Cord Blood (MD Anderson Cord Blood Bank)", "HPC, Cord Blood"),
    "125659": (BP, "RYPLAZIM", "plasminogen, human-tvmh"),
    "125661": (BP, "JIVI", "Antihemophilic Factor (Recombinant), PEGylated-aucl"),
    "125668": (BP, "CUTAQUIG", "Immune Globulin Subcutaneous (Human)-hipp"),
    "125671": (BP, "ESPEROCT", "Antihemophilic Factor (Recombinant), GlycoPEGylated-exei"),
    "125678": (V, "JYNNEOS", "Smallpox and Mpox Vaccine, Live, Non-replicating"),
    "125682": (V, "DENGVAXIA", "Dengue Tetravalent Vaccine, Live"),
    "125683": (BP, "XEMBIFY", "Immune Globulin Subcutaneous (Human)-klhw"),
    "125685": (CT, "RETHYMIC", "allogeneic processed thymus tissue-agdc"),
    "125690": (V, "ERVEBO", "Ebola Zaire Vaccine, Live"),
    "125692": (V, "AUDENZ", "Influenza A (H5N1) Monovalent Vaccine, Adjuvanted"),
    "125694": (GT, "ZOLGENSMA", "onasemnogene abeparvovec-xioi"),
    "125696": (AL, "PALFORZIA", "Peanut (Arachis hypogaea) Allergen Powder-dnfp"),
    "125700": (GT, "ADSTILADRIN", "nadofaragene firadenovec-vncg"),
    "125701": (V, "MenQuadfi", "Meningococcal (Groups A, C, Y, W) Conjugate Vaccine"),
    "125703": (CT, "TECARTUS", "brexucabtagene autoleucel"),
    "125706": (CT, "RYONCIL", "remestemcel-L-rknd"),
    "125714": (CT, "BREYANZI", "lisocabtagene maraleucel"),
    "125717": (GT, "ZYNTEGLO", "betibeglogene autotemcel"),
    "125720": (GT, "ROCTAVIAN", "valoctocogene roxaparvovec-rvox"),
    "125722": (GT, "KEBILIDI", "eladocagene exuparvovec-tneq"),
    "125730": (CT, "STRATAGRAFT", "allogeneic cultured keratinocytes and dermal fibroblasts in murine collagen-dsat"),
    "125731": (V, "PREVNAR 20", "Pneumococcal 20-valent Conjugate Vaccine"),
    "125734": (CT, "LANTIDRA", "donislecel-jujn"),
    "125736": (CT, "ABECMA", "idecabtagene vicleucel"),
    "125737": (V, "PREHEVBRIO", "Hepatitis B Vaccine (Recombinant)"),
    "125738": (CT, "OMISIRGE", "omidubicel-onlv"),
    "125739": (OB, "REBYOTA", "fecal microbiota, live-jslm"),
    "125740": (V, "TICOVAC", "Tick-Borne Encephalitis Vaccine"),
    "125741": (V, "VAXNEUVANCE", "Pneumococcal 15-valent Conjugate Vaccine"),
    "125742": (V, "COMIRNATY", "COVID-19 Vaccine, mRNA"),
    "125743": (BP, "ALYGLO", "immune globulin intravenous, human-stwk"),
    "125746": (CT, "CARVYKTI", "ciltacabtagene autoleucel"),
    "125748": (V, "PRIORIX", "Measles, Mumps, and Rubella Vaccine, Live"),
    "125752": (V, "SPIKEVAX", "COVID-19 Vaccine, mRNA"),
    "125755": (GT, "SKYSONA", "elivaldogene autotemcel"),
    "125757": (OB, "VOWST", "fecal microbiota spores, live-brpk"),
    "125758": (GT, "LENMELDY", "atidarsagene autotemcel"),
    "125761": (V, "CYFENDUS", "Anthrax Vaccine Adsorbed, Adjuvanted"),
    "125764": (CT, "REGENECYTE", "HPC, Cord Blood"),
    "125768": (V, "ABRYSVO", "Respiratory Syncytial Virus Vaccine"),
    "125769": (V, "ABRYSVO", "Respiratory Syncytial Virus Vaccine"),
    "125770": (V, "PENBRAYA", "Meningococcal Groups A, B, C, W, and Y Vaccine"),
    "125771": (BP, "ALTUVIIIO", "antihemophilic factor (recombinant), Fc-VWF-XTEN fusion protein-ehtl"),
    "125772": (GT, "HEMGENIX", "etranacogene dezaparvovec-drlb"),
    "125773": (CT, "AMTAGVI", "lifileucel"),
    "125774": (GT, "VYJUVEK", "beremagene geperpavec-svdt"),
    "125775": (V, "AREXVY", "Respiratory Syncytial Virus Vaccine, Adjuvanted"),
    "125776": (BP, "BALFAXAR", "prothrombin complex concentrate, human-lans"),
    "125777": (V, "IXCHIQ", "Chikungunya Vaccine, Live"),
    "125781": (GT, "ELEVIDYS", "delandistrogene moxeparvovec-rokl"),
    "125785": (GT, "CASGEVY", "exagamglogene autotemcel"),
    "125786": (GT, "BEQVEZ", "fidanacogene elaparvovec-dzkt"),
    "125787": (GT, "CASGEVY", "exagamglogene autotemcel"),
    "125788": (GT, "LYFGENIA", "lovotibeglogene autotemcel"),
    "125789": (CT, "TECELRA", "afamitresgene autoleucel"),
    "125795": (BP, "ADZYNMA", "ADAMTS13, recombinant-krhn"),
    "125796": (V, "MRESVIA", "Respiratory Syncytial Virus Vaccine"),
    "125798": (GT, "ENCELTO", "revakinagene taroretcel-lwey"),
    "125807": (GT, "ZEVASKYN", "prademagene zamikeracel"),
    "125810": (BP, "YIMMUGO", "immune globulin intravenous, human-dira"),
    "125812": (OB, "SYMVESS", "acellular tissue engineered vessel-tyod"),
    "125813": (CT, "AUCATZYL", "obecabtagene autoleucel"),
    "125814": (V, "CAPVAXIVE", "Pneumococcal 21-valent Conjugate Vaccine"),
    "125816": (OB, "AVANCE", "acellular nerve allograft-arwx"),
    "125817": (V, "NUVAXOVID", "COVID-19 Vaccine, Adjuvanted"),
    "125819": (V, "PENMENVY", "Meningococcal Groups A, B, C, W, and Y Vaccine"),
    "125820": (V, "VIMKUNYA", "Chikungunya Vaccine, Recombinant"),
    "125822": (BP, "QIVIGY", "immune globulin intravenous, human-kthm"),
    "125832": (GT, "PAPZIMEOS", "zopapogene imadenovec-drba"),
    "125833": (BP, "FESILTY", "fibrinogen, human-chmt"),
    "125835": (V, "MNEXSPIKE", "COVID-19 Vaccine, mRNA"),
    "125846": (GT, "WASKYRA", "etuvetidigene autotemcel"),
    "125856": (GT, "ITVISMA", "onasemnogene abeparvovec-brve"),
}

# Sponsor where neither the yearly listing, the letter header nor the product page gives a clean name.
SPONSOR_OVERRIDE = {
    "125419": "ID Biomedical Corporation of Quebec",
    "125641": "Laboratoire Francais du Fractionnement et des Biotechnologies S.A. (LFB S.A.)",
}


def decisions(rows):
    """(category, in_scope) for each row of year_page_rows.jsonl, aligned to rows."""
    out = []
    for i, r in enumerate(rows):
        if r["list_kind"] == "BLA":
            cat = "duplicate_row" if i in DUP_ROWS else OUT_ORIG.get(r["appl_no"], "original_bla")
            out.append((cat, cat == "original_bla"))
        else:
            out.append((SUPPL[i], SUPPL[i] in IN_SCOPE_SUPPL))
    return out
