# Drug-class audit of the named contexts (PR #81)

`class_audit.py` rebuilds the lists.py cohort (novel Phase 2 entrants 2008–2019 in the 71 named
indications, 2,634 programs) and joins it to a hand review (`reviews.csv`, 632 moieties: every
member of each currently chosen class, the top two mechanisms under the proposed rule, and every
unresolved-target program in allergic disease, allergic rhinitis, atopic conjunctivitis, acne,
chronic HBV, HIV, HCV, BPH and dry eye). Each review row cites ChEMBL, an FDA or registry page,
a DOI or a PubMed query. Outputs: `class_members.csv` (one row per program, review columns plus
`db_issue`), `current_on_db.csv` (lists.classes() on today's DB) and `proposed_contexts.csv`.

**The database changed during the audit.** Between runs on 2026-11-04 another session removed
every `dev_program` row for relugolix and cannabidiol, and they are still absent at the last run
(2026-11-05). Their reviews stay in `reviews.csv`. Endometriosis still qualifies with 2 GnRH
antagonists; Prader-Willi has no class either way. Re-run the script once that write lands.

## 1. Where the database disagrees with the review

Of 591 reviewed moieties with a disclosed mechanism, **21 disagree with the DB** on target,
action, modality or novelty (`disagrees_with_db`). Another 102 have no DB target at all
(pathogen targets, allergen immunotherapies, siRNAs), and 41 have an undisclosed mechanism.

- **Wrong target (13):** BMS-914392 is an I_KACh blocker, not Kv1.5. JNJ-39588146 is
  stresscopin, a CRF2 agonist, not an NPR1 agonist. ODM-104 is a COMT inhibitor, not a
  dopamine agonist (its action is wrong as well). XP21279 is a levodopa prodrug. "Proinsulin
  human" is most likely the BHT-3021 tolerising vaccine, not an insulin-receptor agonist.
  Tivantinib acts on tubulin, not MET. Pidilizumab binds DLL1, not PD-1. Iniparib is not a PARP
  inhibitor. Rigosertib is not a PLK1 inhibitor. Deudextromethorphan is not a GluN2B
  antagonist. Chromanol (APC-100), propagermanium and (R)-mequitazine are off-class.
  (Cannabidiol was a 14th: it is not a CB1 negative modulator. Its rows dropped out of the last run.)
- **Not novel (5):** hydroxyflutamide (flutamide's active metabolite, 1989), FVIII/VWF complex
  (Wilate 2009, Humate-P 1986), ADO09 (pramlintide plus a glargine metabolite), Product 0405
  (a generic-maker corticosteroid) and esketamine (an enantiomer of ketamine, approved 1970).
- **Wrong modality (4):** GB001 is a small molecule, not a peptide. Beti-cel and lovo-cel are
  ex vivo gene therapies. Proinsulin is a DNA vaccine.
- **Wrong FDA date (3):** belantamab was first approved on 2020-08-05; the DB has the 2025
  re-approval.
- **Lumping by the rule, not by the data:** the DB lists the right targets, but the 1/k
  weighting still puts multi-target drugs into single-target classes. Of the 301 moieties in
  the current classes, 28 are dual-target and 15 are pan or multikinase. Examples: tofacitinib
  and brepocitinib in JAK1; ritlecitinib (JAK3/TEC) in BTK; esketamine in GRIN2B; pan-HER TKIs
  in ERBB2; GLP-1/glucagon and GLP-1/GIP co-agonists in GLP1R. Eleven current classes also mix
  modality groups: breast, gastric, myeloma, T2D, hemophilia A and B, DME, dry eye, psoriasis,
  MDS and SHPT.

Problem 1 checks out: trabodenoson (the A1 agonist) is a separate glaucoma program. The
A2A class has only evodenoson and OPA-6566.

## 2. Why the novelty leaks happen

`novel` (section1.phase_rows) is decided per moiety: it is false only if *that* `moiety_id` has
an ORIG/AP FDA submission through `fda_application_moiety`. Candesartan (6975) and mometasone
(1141) duplicate the moieties that carry the FDA applications: candesartan cilexetil (1157) and
mometasone furoate (868). When named_contexts.csv was drawn (2026-11-02), the bare moieties had
no FDA link, so they counted as novel. #109's `trial_entity_fda_application` decisions (written
2026-11-05 00:54 UTC) linked them. Today both drop out: hypertension and eczema now resolve to
other classes in `current_on_db.csv`.

The same mechanism remains for salts, esters, prodrugs, metabolites, enantiomers and plasma
products that have no link of their own (the five not-novel moieties above). Brivanib and
brivanib alaninate, and futuximab and modotuximab (both Sym004), are also duplicate entities.
`reviews.csv` folds them with `same_entity_as`.

## 3. The selection rule and what it gives

Rule (decision 12): a tile is indication × **mechanism**, (verified target, action), counted across
modalities. Off-class and no-target members are excluded, non-selective members form their own
mechanism, and duplicate moieties count once (`same_entity_as`). The indication's mechanism is the
one with the most distinct entities, **at least 3**; phase is never a criterion. Mechanisms tied on
count each get a tile. Modality does not define the tile: it splits the dose cell and the
platform-safety sub-strip inside it (`modality_groups`).

Two alternatives were run and rejected. Ranking by furthest phase first prefers the classes that had
already succeeded (RA showed the anti-GM-CSF antibodies, 3 programs, over the BTK inhibitors, 8).
Putting modality in the unit fragments mechanisms (T2D fell to glucokinase activators once the
GLP-1R agonists split into peptides, small molecules and Fc fusions). A floor of 2 leaves 7
indications blank but gives 98 tiles, up to 7 in one indication (MDD); the floor of 3 was chosen and
the blanks accepted: no mechanism dominated those indications, and the random program sample, not
the named tiles, carries the statistics.

**Result: 62 tiles in 47 indications (12 with tied mechanisms); 24 indications blank.**

| indication | novel Phase 2 programs | tile(s): mechanism (programs, modalities when more than one) |
|---|---|---|
| allergic disease | 7 | allergen (immunotherapy) (5, other/peptide) |
| allergic rhinitis | 39 | allergen (immunotherapy) (8, other/peptide/protein) |
| Crohn disease | 36 | anti-IL23A antibodies (3) |
| psoriasis | 80 | anti-IL17A antibodies (4, antibody/protein); RORC inverse agonists (4) |
| rheumatoid arthritis | 96 | BTK inhibitors (8) |
| ulcerative colitis | 70 | S1PR1 agonists (3) |
| secondary hyperparathyroidism | 6 | CASR positive modulators (4, peptide/small molecule) |
| type 1 diabetes mellitus | 31 | SLC5A2 inhibitors (4) |
| type 2 diabetes mellitus | 126 | GLP1R agonists (12, peptide/protein/small molecule) |
| gastroesophageal reflux disease | 11 | ATP4A blockers (3) |
| metabolic dysfunction-associated steatohepatitis | 75 | NR1H4 agonists (4) |
| primary biliary cholangitis | 15 | NR1H4 agonists (3) |
| hemophilia A | 15 | F8 replacement / gene therapy (8, gene therapy/protein) |
| hemophilia B | 10 | F9 replacement / gene therapy (7, gene therapy/protein) |
| paroxysmal nocturnal hemoglobinuria | 9 | anti-C5 antibodies (4) |
| HIV infectious disease | 32 | HIV RT (NNRTI) inhibitors (3); HIV RT (NRTI) inhibitors (3); HIV integrase (INSTI) inhibitors (3); HIV maturation (Gag) inhibitors (3) |
| chronic hepatitis B virus infection | 18 | HBV RNA antisense / siRNA (3); HBsAg release (NAP) inhibitors (3) |
| hepatitis C virus infection | 52 | HCV NS3/4A protease inhibitors (13) |
| hyperlipidemia | 33 | CETP inhibitors (3); HCAR2 agonists (3) |
| Alzheimer disease | 76 | BACE1 inhibitors (4); anti-MAPT antibodies (4) |
| migraine disorder | 29 | CGRP receptor antagonists (4) |
| acute myeloid leukemia | 78 | FLT3 inhibitors (4) |
| breast cancer | 129 | CDK4/6 inhibitors (6) |
| colorectal cancer | 88 | anti-EGFR antibodies (3); KDR (VEGFR) inhibitors (3); VEGFR multikinase inhibitors (3) |
| follicular lymphoma | 34 | CD19-directed depleters (3); PIK3CD inhibitors (3) |
| gastric cancer | 40 | anti-ERBB2 antibodies (3); PARP1/2 inhibitors (3) |
| hepatocellular carcinoma | 73 | anti-PDCD1 antibodies (4); VEGFR multikinase inhibitors (4) |
| malignant pancreatic neoplasm | 73 | MAP2K1/2 inhibitors (3) |
| melanoma | 51 | BRAF inhibitors (3); anti-PDCD1 antibodies (3) |
| myelodysplastic syndrome | 44 | HDAC (pan) inhibitors (3) |
| non-small cell lung carcinoma | 191 | EGFR inhibitors (18) |
| ovarian cancer | 58 | PARP1/2 inhibitors (6) |
| plasma cell myeloma | 73 | TNFRSF17-directed depleters (8, ADC/antibody/cell therapy) |
| prostate cancer | 91 | AR antagonists (5); PARP1/2 inhibitors (5) |
| small cell lung carcinoma | 39 | anti-PDCD1 antibodies (3) |
| diabetic macular edema | 21 | anti-VEGFA antibodies (3) |
| dry eye syndrome | 51 | anti-TNF antibodies (3, antibody/protein) |
| open-angle glaucoma | 20 | ROCK inhibitors (3) |
| atopic eczema | 81 | PDE4 inhibitors (5) |
| diabetic kidney disease | 26 | NR3C2 antagonists (3) |
| osteoarthritis | 65 | MAPK14 inhibitors (3); NTRK1 inhibitors (3) |
| insomnia | 11 | HCRTR1/2 antagonists (6) |
| schizophrenia | 45 | PDE10A inhibitors (5) |
| asthma | 84 | PTGDR2 antagonists (9) |
| chronic obstructive pulmonary disease | 47 | CHRM3 antagonists (6) |
| cystic fibrosis | 43 | CFTR correctors (8) |
| interstitial cystitis | 10 | anti-NGF antibodies (3) |

**Blank (24):** atopic conjunctivitis, eosinophilic esophagitis, heart failure, hypertensive disorder, atrial fibrillation, coronary artery disorder, endometriosis, irritable bowel syndrome, sickle cell disease, influenza, obesity disorder, hypertriglyceridemia, Prader-Willi syndrome, Parkinson disease, diabetic neuropathy, glioblastoma, age-related macular degeneration, acne, major depressive disorder, attention deficit-hyperactivity disorder, idiopathic pulmonary fibrosis, overactive bladder, benign prostatic hyperplasia, premature ejaculation. Each has no mechanism with 3 programs; `reason`
names the largest.

## 4. Recommended DB fixes (not applied)

1. Decide novelty at the active-moiety level (UNII parent, or ChEMBL parent when that mapping is
   right), so that salts, esters, prodrugs, metabolites and enantiomers inherit their sibling's
   approval. Add FDA links for hydroxyflutamide (NDA 018554), the FVIII/VWF complex, the ADO09
   components and Product 0405.
2. Correct `moiety_target` for the 13 wrong-target moieties above. Correct `moiety.modality` for
   GB001, beti-cel and lovo-cel, and set Cal-1's (now unknown).
3. Merge the duplicate moieties: ToleroMune HDM = HDM-SPIRE, ToleroMune Ragweed = Ragweed-SPIRE,
   brivanib alaninate → brivanib, and futuximab + modotuximab = Sym004.
4. Fix the wrong `chembl_moiety` maps:
   - valoctocogene → CHEMBL154 (naproxen)
   - sunvozertinib → CHEMBL4594535 (shared with sugemalimab)
   - tozadenant → CHEMBL2105747 (shared with anti-TB drugs; inchikey basis)
   - rintatolimod → imatinib's parent
   - melphalan flufenamide → CHEMBL459 (methyldopa)

   These feed the ChEMBL-mechanism fallback and the potency frames.
5. Add belantamab's 2020-08-05 approval.

## Not verified

- 41 programs have an undisclosed mechanism (e.g. AL-53817, BLI1100-x, SPARC codes) and are
  marked `unknown`.
- The mechanisms of AL-38583, CHF5992 and EX1000 are undisclosed; the DB target was kept.
- The identity of "proinsulin human" is inferred.
- Many `evidence` entries for code-named compounds are PubMed queries rather than a single
  paper.
