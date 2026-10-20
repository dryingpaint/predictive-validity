"""Manual scope decisions for approval letters found on product pages that are NOT listed on the
CBER yearly 'noteworthy' pages. Each entry was decided by reading the letter's purpose paragraph.
Anything not listed here is out of scope (safety-only labeling, PLLR/format conversions, strain
updates, manufacturing/CMC, presentations, REMS, diagnostics, CBE acknowledgement letters)."""

EXTRA_SUPPL = {
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
}

# Original BLAs approved 2015-2025 that are not on the yearly BLA lists.
EXTRA_ORIG = {
    "125764/0": "original_bla",                  # REGENECYTE (HPC, Cord Blood), 2024-11-20
}
