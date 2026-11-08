"""Model-system families for the atlas lessons (lessons/DESIGN.md): an ordered keyword rule set over a system's
model text and model_id, gated by its model_kind, with a hand-written override file applied on top.

A system is one (tile, model_id). The first rule whose kind gate admits the system and whose pattern matches
wins; overrides.csv (slug, model_id, family, note) replaces the rule's answer and is the hand-review record.
No database access; lessons.py feeds it rows."""
from __future__ import annotations

import csv
import re

# code -> (label, short label for the forest panels at 5.5 pt); the order is the order the figure lists them in
FAMILIES: dict[str, tuple[str, str]] = {
    "tox_repeat_dose": ("Toxicology in standard species", "Toxicology, standard species"),
    "tox_cv_safety_pharm": ("Cardiovascular safety pharmacology", "CV safety pharmacology"),
    "xenograft_cell_line": ("Cell-line xenograft", "Cell-line xenograft"),
    "xenograft_pdx": ("Patient-derived xenograft", "Patient-derived xenograft"),
    "syngeneic_tumour": ("Syngeneic mouse tumour", "Syngeneic mouse tumour"),
    "gemm_tumour": ("Engineered mouse tumour (GEMM)", "Engineered mouse tumour (GEMM)"),
    "humanised_mouse": ("Humanised or knock-in mouse", "Humanised or knock-in mouse"),
    "target_knockout": ("Target knockout or mutant animal", "Target knockout animal"),
    "genetic_disease_model": ("Transgenic or genetic disease model", "Transgenic disease model"),
    "infected_or_chimeric_liver": ("Infected or human-liver-chimeric animal", "Infected / chimeric-liver animal"),
    "inflammatory_disease_model": ("Induced inflammatory or joint disease model", "Induced inflammatory model"),
    "metabolic_disease_model": ("Rodent metabolic, renal or endocrine model", "Rodent metabolic / renal model"),
    "behaviour_cns_model": ("Rodent behaviour, cognition or pain model", "Rodent behaviour / pain model"),
    "pkpd_occupancy_animal": ("PK, occupancy or PET in animals", "PK, occupancy or PET in animals"),
    "organ_pharmacology_animal": ("Organ-level evoked pharmacology", "Organ-level evoked pharmacology"),
    "nonrodent_disease_model": ("Non-rodent disease or pharmacology model", "Non-rodent disease model"),
    "patient_material_ex_vivo": ("Patient-derived cells, organoids or tissue", "Patient cells or organoids"),
    "donor_primary_human": ("Donor primary human cells, blood or tissue", "Donor human cells or tissue"),
    "cell_line_assay": ("Cell line, replicon or cell panel", "Cell line or replicon"),
    "biochemical_assay": ("Biochemical, binding or transporter assay", "Biochemical / binding assay"),
    "allergen_challenge_human": ("Allergen challenge in people", "Allergen challenge in people"),
    "pharmacological_challenge_human": ("Pharmacological challenge in people", "Drug challenge in people"),
    "target_lof_genetics": ("Target loss-of-function carriers", "Target LoF carriers (human)"),
    "pharmacogenetic_stratification": ("Pharmacogenetic stratification", "Pharmacogenetic stratification"),
    "pbpk_translational": ("PBPK or translational PK from preclinical data", "PBPK / translational PK"),
    "poppk_exposure_response": ("Population PK / exposure-response from clinical data", "Population PK, clinical data"),
    "qsp_mechanistic": ("QSP or mechanistic disease model", "QSP / mechanistic model"),
    "expression_classifier": ("Expression or structure classifier", "Expression / structure classifier"),
    "cross_indication": ("Cross-indication import", "Cross-indication import"),
}


def _r(*pats: str) -> re.Pattern:
    return re.compile("|".join(pats), re.I)


BENCH = frozenset({"ex_vivo", "animal"})  # the bench rules also catch animal-coded systems that matched no animal rule

# (family, kind gate: a kind, a set of kinds or None, pattern); first match wins
RULES: list[tuple[str, str | frozenset | None, re.Pattern]] = [
    ("tox_cv_safety_pharm", "animal", _r(r"\bhERG\b", r"telemetr", r"cardiovascular safety", r"\bQTc?\b", r"heart.?rate", r"bleeding.time",
                                        r"\bECG\b")),
    ("tox_repeat_dose", "animal", _r(r"toxicolog", r"\btox\b", r"\bGLP\b", r"repeat.dose", r"carcinogenicity", r"safety pharm", r"IND.enabling",
                                    r"embryo.fetal", r"periconception", r"skin irritation", r"lymph node assay", r"neurotox", r"biocompatib",
                                    r"abuse.liability", r"self.administration", r"C.cell", r"irritation", r"cataplexy", r"retinal (damage|toxicity)",
                                    r"bioactivation", r"\bemesis\b", r"tolerability", r"phototox")),
    ("infected_or_chimeric_liver", "animal", _r(r"chimeric", r"chimpanzee", r"woodchuck", r"\bduck", r"DHBV", r"\bWHV\b", r"infected",
                                               r"influenza", r"tuberculosis", r"Mycobacterium", r"SCID-hu", r"HBV.{0,15}(transgenic|genome|mice|mouse)",
                                               r"\bPXB\b", r"uPA/SCID", r"TK-NOG", r"\bBCG\b", r"Salmonella", r"Listeria", r"humani[sz]ed.liver")),
    ("humanised_mouse", "animal", _r(r"knock.in", r"humani[sz]ed", r"human.{0,12}(PD-1|CTLA4|CCR2|GnRHR|GLP-1R|CETP|LDLR|IL-13|IL-33|OX2R|CD16A).{0,16}(mouse|mice|rat)",
                                    r"\bhPD-?1", r"hGCGR", r"hOX2R", r"HuGEMM", r"human PBMC", r"PBMC.{0,20}(engrafted|reconstituted|humanised)",
                                    r"NSG.{0,40}(human|allogeneic)", r"HuSGM3", r"human T-cell co-implant", r"human.{0,10}transgenic",
                                    r"CD16A.{0,20}transgenic", r"IL-13-humanised", r"human-IL-33", r"human IL-2[3]", r"human IL-17A",
                                    r"\bhIL-?\d", r"human.{0,6}CETP")),
    ("xenograft_pdx", "animal", _r(r"\bPDX", r"patient.derived.{0,40}xenograft", r"xenograft.{0,40}patient.derived", r"avatar",
                                  r"primary.blast xenograft", r"primary human melanoma xenograft", r"xenografts from", r"SCID-hu LAG")),
    ("syngeneic_tumour", "animal", _r(r"syngeneic", r"\bMC38\b", r"\bCT26\b", r"\bB16", r"\bA20\b", r"38c13", r"allograft", r"\bLLC\b",
                                     r"Lewis lung", r"immunocompetent", r"homograft", r"S180", r"J558", r"RP-48", r"\bRPP\b")),
    ("gemm_tumour", "animal", _r(r"\bGEMM\b", r"autochthonous", r"K14cre", r"\bKPC\b", r"Kras.{0,20}driven", r"Kras G12D", r"Rb1/Trp53",
                                r"\bRPM\b", r"Pten/Rb1", r"c-myc/OVA", r"transposon", r"transgenic.{0,30}(tumou?r|HCC|mammary)",
                                r"lineage plasticity")),
    ("xenograft_cell_line", "animal", _r(r"xenograft", r"xenotrial", r"nude mice", r"athymic", r"\bNSG\b", r"NOD/SCID", r"\bSCID\b")),
    ("target_knockout", "animal", _r(r"knock.?out", r"-/-", r"null mouse", r"null (mice|mouse)", r"kinase.dead", r"deficient (mouse|mice)",
                                    r"\bKO\b", r"Sweet Pee", r"p75NTR", r"\+/-", r"FGF21-transgenic", r"gain-of-function")),
    ("genetic_disease_model", "animal", _r(r"transgenic", r"Tg2576", r"PDAPP", r"P301", r"THY-Tau", r"ArcSwe", r"hAPP", r"\bAPP\b",
                                          r"[Hh]emophilia [AB] (mice|mouse)", r"F[89]-knockout", r"FIX-knockout", r"FVIII-knockout", r"f[89]ko",
                                          r"Mdr2", r"NC/Nga", r"Stat6VT", r"Akita")),
    ("inflammatory_disease_model", "animal", _r(r"\bOVA\b", r"ovalbumin", r"collagen.induced", r"\bCIA\b", r"adjuvant", r"\bAIA\b", r"K/BxN",
                                               r"colitis", r"imiquimod", r"\bIMQ\b", r"MC903", r"oxazolone", r"DNCB", r"hapten", r"\bTPA\b",
                                               r"phorbol", r"dermatitis", r"\bLPS\b", r"endotoxin", r"allergic", r"allergen", r"zymosan",
                                               r"carrageenan", r"streptococcal cell wall", r"\bEAE\b", r"arthritis", r"psoriasis", r"asthma",
                                               r"minicircle", r"ear.swelling", r"IL-23-induced", r"IL-23 mouse", r"dry eye", r"desiccating",
                                               r"keratoconjunctivitis", r"antigen challenge", r"skin PD", r"splenocyte", r"\bKC\b",
                                               r"cigarette", r"tobacco", r"neutrophilia", r"TNF-alpha PD", r"PGPS", r"flare", r"cystitis",
                                               r"reflux", r"oesophagitis", r"esophagitis", r"meniscal", r"\bMIA\b", r"\bMNX\b",
                                               r"iodoacetate", r"knee", r"osteoarthritis")),
    ("metabolic_disease_model", "animal", _r(r"db/db", r"ob/ob", r"\bDIO\b", r"diet.induced", r"\bSTZ\b", r"streptozotocin", r"\bZDF\b",
                                            r"Zucker", r"KK-?Ay", r"Goto", r"\bGK\b", r"high.fat", r"\bHFD\b", r"CDAHFD", r"choline.deficient",
                                            r"\bSTAM\b", r"AMLN", r"NASH", r"\bOGTT\b", r"diabetic (mice|mouse|rat)", r"type 2 diabetes",
                                            r"diabetes", r"obese", r"uremic", r"nephrectom", r"Dahl", r"DOCA", r"Munich Wistar", r"albuminuric",
                                            r"natriuresis", r"insulinopenic", r"glucose", r"\bFFA\b", r"NEFA", r"lipoprotein", r"cholesterol",
                                            r"flush", r"glucagon", r"DPP-4 inhibition", r"islets", r"clamp", r"\bbone\b", r"microCT", r"\bBDL\b",
                                            r"bile.duct", r"cholangiopathy", r"FXR", r"gastrin", r"acid secretion", r"euDKA", r"HPG axis",
                                            r"endometriosis", r"oestrous", r"steroidogenesis", r"\bLH\b", r"\bE2\b", r"C5-supplemented",
                                            r"insulin")),
    ("behaviour_cns_model", "animal", _r(r"cognition", r"cognitive", r"water maze", r"object recognition", r"\bNOR\b", r"\bPPI\b", r"prepulse",
                                        r"hyperlocomotion", r"catalepsy", r"avoidance", r"social", r"nest.building", r"MK-801", r"\bPCP\b",
                                        r"ketamine", r"scopolamine", r"behaviou?r", r"allodynia", r"\bpain\b", r"hyperalgesia", r"grimace",
                                        r"light aversion", r"headache", r"migraine", r"\bEEG\b", r"sleep", r"radial arm", r"operant",
                                        r"delayed response", r"psychostimulant", r"antipsychotic", r"\bCAR\b", r"trigeminovascular",
                                        r"spreading depression", r"\bERG\b", r"oscillat", r"theta", r"stroke", r"MCAO",
                                        r"seizure", r"\bEPS\b", r"prolactin", r"schizophrenia screens", r"procognitive", r"drug discrimination",
                                        r"learning", r"CNS")),
    ("pkpd_occupancy_animal", "animal", _r(r"\bPET\b", r"occupancy", r"PK/?PD", r"PK-PD", r"pharmacokinetic", r"\bPK\b", r"brain.penetration",
                                          r"brain:plasma", r"brain/plasma", r"\bCSF\b", r"exposure", r"allometr", r"bioavailab", r"loading",
                                          r"half.life", r"tissue.distribution", r"autoradiography", r"biodistribution", r"ADME", r"imaging",
                                          r"disposition", r"PD assay", r"PD model", r"\bPD\b", r"target.gene", r"phospho", r"microperfusion")),
    ("organ_pharmacology_animal", "animal", _r(r"guinea.pig", r"bronch", r"trache", r"airway", r"capsaicin", r"dermal blood flow", r"vasodilat",
                                              r"facial blood flow", r"CIDV", r"CIDBF", r"blood.flow", r"uterine", r"uterus", r"organ.bath",
                                              r"isolated (right|left|atrium|atria|heart)", r"papillary", r"methacholine", r"histamine",
                                              r"acetylcholine", r"pilocarpine", r"blood pressure", r"\bBP\b", r"hypertension", r"permeability",
                                              r"VEGF-induced", r"challenge", r"stimulated", r"evoked", r"induced", r"\beye\b", r"ocular",
                                              r"outflow", r"episcleral", r"intravitreal", r"retina")),
    ("nonrodent_disease_model", "animal", _r(r"\bdogs?\b", r"canine", r"beagle", r"\bsheep\b", r"\bpigs?\b", r"minipig", r"\bcats?\b", r"rabbit",
                                            r"marmoset", r"monkey", r"cynomolgus", r"rhesus", r"macaque", r"primate", r"baboon", r"\bNHP\b")),
    ("patient_material_ex_vivo", BENCH, _r(r"patient", r"organoid", r"explant", r"\bPDO\b", r"PDTX", r"PDTC", r"primary (AML|CD138|parathyroid|myeloma)",
                                         r"primary.blast", r"lesional", r"tumou?r fragments", r"spheroid", r"tumoroid", r"rectal", r"\bHBE\b",
                                         r"\bHNE\b", r"brushings", r"AD.brain", r"AD/PSP", r"\bCAA\b", r"leptomeningeal", r"circulating.tumou?r",
                                         r"\bCTC\b", r"LuCaP", r"\bLAG", r"submandibular", r"biobank", r"alveolar macrophage", r"COPD-patient",
                                         r"psoriasis patients", r"human (donor )?eyes?", r"enucleated", r"T.cell clones", r"HLA-typed",
                                         r"donor", r"disease.specific", r"sera\b")),
    ("donor_primary_human", BENCH, _r(r"whole.blood", r"PBMC", r"basophil", r"\bhuman\b", r"iPSC", r"islet", r"keratinocyte", r"hepatocyte",
                                    r"neutrophil", r"eosinophil", r"platelet", r"atrial", r"cardiomyocyte", r"skin\b", r"bronch", r"arter",
                                    r"InflammaSkin", r"sRICA", r"EpiIntestinal", r"HepatoPac", r"L-cell", r"colonic", r"Treg", r"T-cell",
                                    r"NK cells", r"blood cells", r"bone marrow", r"primary cells")),
    ("cell_line_assay", BENCH, _r(r"cell.line", r"Ba/F3", r"\bCCLE\b", r"\bFRT\b", r"Fischer rat thyroid", r"HEK293", r"replicon", r"Huh-?7",
                                r"HepG2", r"HepaRG", r"MT-4", r"\bCEM\b", r"MCF10A", r"isogenic", r"biosensor", r"cell culture", r"K562", r"NK-92",
                                r"L6-hIR", r"Saos", r"HMEC", r"PC-3", r"NUGC", r"cells engineered", r"siRNA", r"\blines?\b", r"cell models",
                                r"cell assays", r"cellular assays", r"cell panel", r"in vitro", r"in-vitro", r"HIV-1 replication", r"HBsAg",
                                r"hypoxic", r"site-directed", r"clones", r"susceptibility", r"cytotoxicity", r"\bcells\b")),
    ("biochemical_assay", BENCH, _r(r"\bhERG\b", r"transporter", r"OCT2", r"\bOAT", r"MRP4", r"\bCYP", r"enzyme", r"binding", r"\bSPR\b",
                                  r"ELISA", r"receptor.proteome", r"mitochondrial", r"microsom", r"kinetics", r"complex formation", r"DTDC",
                                  r"polymerase", r"POLRMT", r"recombinant", r"biochemical", r"affinity", r"selectivity", r"potency", r"IVIVE",
                                  r"metabolism", r"immunodepletion", r"seeding assay", r"shape.change", r"migration", r"autoradiography",
                                  r"inhibition assay", r"inhibition panel")),
    ("allergen_challenge_human", "human_challenge", _r(r"allergen", r"chamber", r"\bEEC\b", r"provocation", r"\bCPT\b", r"LPSR", r"late.phase",
                                                      r"late asthmatic", r"\bLAR\b", r"\bAMP\b", r"house.dust.mite", r"\bHDM\b", r"nasal")),
    ("pharmacological_challenge_human", "human_challenge", _r(r".")),
    ("target_lof_genetics", "human_genetic", _r(r"Mendelian", r"loss.of.function", r"\bLoF\b", r"deficiency", r"inborn", r"Mahvash",
                                                 r"protective variant", r"truncating", r"kinase.dead", r"null p110", r"autoantibod",
                                                 r"cortisone reductase", r"glucosuria", r"\bCIPA\b", r"HSAN", r"R381Q", r"A673T", r"GWAS locus",
                                                 r"activating")),
    ("pharmacogenetic_stratification", "human_genetic", _r(r".")),
    ("pbpk_translational", "in_silico", _r(r"PBPK", r"Simcyp", r"GastroPlus", r"allometr", r"IVIVE", r"physiologically based",
                                            r"translational.{0,20}(PK|pharmacokinetic)", r"\brabbit", r"\brat\b", r"\bdog\b", r"\bmouse\b",
                                            r"monkey", r"animal", r"xenograft", r"preclinical", r"decay model", r"superposition")),
    ("poppk_exposure_response", "in_silico", _r(r"population", r"popPK", r"NONMEM", r"phase (1|2|3)", r"healthy.volunteer", r"patient data",
                                                 r"patients\b", r"clinical", r"C-?QTc", r"concentration.QTc", r"single.ascending",
                                                 r"exposure.response", r"exposure.safety", r"Markov", r"decision.tree", r"\bMBMA\b",
                                                 r"meta-analysis", r"regimen", r"trial simulation", r"Emax")),
    ("qsp_mechanistic", "in_silico", _r(r"\bQSP\b", r"systems pharmacology", r"mechanistic", r"viral.kinetic", r"kinetic model", r"glucose.insulin",
                                        r"Monte Carlo", r"mathematical model", r"DILIsym", r"\bCFD\b", r"computational fluid", r"4GI",
                                        r"virtual", r"dynamics", r"homeostasis", r"MCell", r"intragastric", r"glucose regulation")),
    ("expression_classifier", "in_silico", _r(r"signature", r"classifier", r"\bDRP\b", r"structure.based", r"classification", r"\bgene\b",
                                              r"stem.cell clones", r"predictor")),
    ("cross_indication", "cross_indication", _r(r".")),
]


def assign(model_kind: str, text: str) -> tuple[str, str]:
    """The first rule that admits the kind and matches the text: (family, 'rule'); ('unassigned', '') when none."""
    for fam, kind, rx in RULES:
        if model_kind not in (kind if isinstance(kind, frozenset) else {kind}):
            continue
        if rx.search(text):
            return fam, "rule"
    return "unassigned", ""


def load_overrides(path: str) -> dict[tuple[str, str], str]:
    """(slug, model_id) -> family; an unknown family code is an error, not a silent new family."""
    out = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            fam = row["family"].strip()
            if fam not in FAMILIES:
                raise ValueError(f"overrides.csv: unknown family {fam!r} for {row['slug']} / {row['model_id']}")
            out[(row["slug"], row["model_id"])] = fam
    return out


def family_of(slug: str, model_id: str, model_kind: str, text: str, overrides: dict) -> tuple[str, str]:
    """(family, source) with source 'override' or 'rule'; 'unassigned' when neither decides."""
    if (slug, model_id) in overrides:
        return overrides[(slug, model_id)], "override"
    return assign(model_kind, text)
