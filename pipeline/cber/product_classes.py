"""Brand, proper name and product class for every in-scope CBER BLA (manually curated).

product_class: vaccine | cell_therapy | gene_therapy | blood_plasma_product | allergenic | other_biologic
  cell_therapy  = unmodified or genetically modified cells given as cells (CAR-T/TCR-T, cord blood,
                  MACI, keratinocyte/fibroblast constructs, islets, thymus tissue, TIL, MSC)
  gene_therapy  = in vivo vectors (AAV, HSV, adenovirus) and ex vivo gene-modified HSC / keratinocyte grafts
  blood_plasma_product = plasma-derived and recombinant plasma-protein analogues (IG, hyperimmune IG,
                  coagulation factors, C1-INH, A1PI, albumin, fibrin sealants, fibrinogen, PCC, plasma,
                  COVID-19 convalescent plasma)
  other_biologic = animal-derived antivenoms/anti-thymocyte globulin, fecal microbiota, acellular tissue grafts
"""
import json
import os
import re

from pipeline.cber import fetch

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

_pages = None


def _page_by_appl():
    global _pages
    if _pages is None:
        _pages = {}
        for fn in ("products.jsonl", "products_historic.jsonl"):
            for line in open(os.path.join(fetch.BASE, fn)):
                p = json.loads(line)
                for s in p.get("stns") or []:
                    _pages.setdefault(s, p)
    return _pages


_ADDR = re.compile(
    r"\s{2,}|\s(?=\d)|\(b\)|-{2,}| Lic\.| Attention| Attn|\sP\.\s?O\.|\s#|"
    r"\s(?:One|Five|Rue|Oberlaaer|Calzada|Campus|Clarendon|Dagger|Discovery Drive|Parker Plaza|Darwinweg|Langebjerg)\b|"
    r"\s[A-Z][a-z]+(?:strasse|straße|weg)\b|"
    r"\s(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d")


def _clean_mfr(s):
    s = re.sub(r"[ \t]+(?=\S)", " ", (s or "").replace("\n", " ")).strip()
    s = _ADDR.split(s)[0].strip(" ,;")
    return s or None


def product_info(appl, listing=None, letter=None):
    cls, brand, proper = PRODUCTS[appl]
    sponsor = None
    if listing is not None:
        sponsor = _clean_mfr(listing.get("manufacturer"))
    if not sponsor and letter is not None and letter.get("sponsor"):
        sp = _clean_mfr(letter["sponsor"]) or ""
        if re.match(r"^[A-Z][A-Za-z]", sp) and not re.match(r"^(Attention|Attn|ATTENTION|Our STN|Dear)", sp):
            sponsor = sp
    if appl in SPONSOR_OVERRIDE and (not sponsor or sponsor.startswith("D Biomedical")):
        sponsor = SPONSOR_OVERRIDE[appl]
    if not sponsor:
        p = _page_by_appl().get(appl)
        if p:
            sponsor = _clean_mfr(p.get("manufacturer") or p.get("list_manufacturer"))
    return {"product_class": cls, "brand": brand, "proper_name": proper, "sponsor": sponsor}
