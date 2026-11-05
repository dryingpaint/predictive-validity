# Drug-class audit of the named contexts (PR #81)

`class_audit.py` rebuilds the lists.py cohort (novel Phase 2 entrants 2008–2019 in the 71 named
indications, 2,629 programs) and joins it to a hand review (`reviews.csv`, 706 moieties: every
member of the classes chosen under each earlier rule, every member of every tracked mechanism, and every
unresolved-target program in allergic disease, allergic rhinitis, atopic conjunctivitis, acne,
chronic HBV, HIV, HCV, BPH and dry eye). Each review row cites ChEMBL, an FDA or registry page,
a DOI or a PubMed query. Outputs: `class_members.csv` (one row per program, review columns plus
`db_issue`), `register.csv` (every indication × mechanism) and the tracked tiles,
`lists/named_contexts.csv`.

**The database changed during the audit.** Between runs on 2026-11-04 another session removed
every `dev_program` row for relugolix and cannabidiol, and they are still absent at the last run
(2026-11-05). Their reviews stay in `reviews.csv`. With relugolix, endometriosis would have 3 GnRH
antagonists and a tracked tile; Prader-Willi has none either way. Re-run the script once that write lands.

## 1. Where the database disagrees with the review

Of 665 reviewed moieties with a disclosed mechanism, **24 are flagged as disagreeing with the DB**
on target, action, modality or novelty (`disagrees_with_db`). Two of the 24, lumacaftor and
posenacaftor, are flagged only because the DB action is the vague `other` (they are CFTR
correctors), so 22 are real errors. Another 102 have no DB target at all
(pathogen targets, allergen immunotherapies, siRNAs), and 41 have an undisclosed mechanism.

- **Wrong target (13):** BMS-914392 is an I_KACh blocker, not Kv1.5. JNJ-39588146 is
  stresscopin, a CRF2 agonist, not an NPR1 agonist. ODM-104 is a COMT inhibitor, not a
  dopamine agonist (its action is wrong as well). XP21279 is a levodopa prodrug. "Proinsulin
  human" is most likely the BHT-3021 tolerising vaccine, not an insulin-receptor agonist.
  Tivantinib acts on tubulin, not MET. Pidilizumab binds DLL1, not PD-1. Iniparib is not a PARP
  inhibitor. Rigosertib is not a PLK1 inhibitor. Deudextromethorphan is not a GluN2B
  antagonist. Chromanol (APC-100), propagermanium and (R)-mequitazine are off-class.
  (Cannabidiol was a 14th: it is not a CB1 negative modulator. Its rows dropped out of the last run.)
- **Not novel (6):** aminopterin (marketed in the US by Lederle 1953–1964, before Drugs@FDA;
  RA and psoriasis programs), hydroxyflutamide (flutamide's active metabolite, 1989), FVIII/VWF complex
  (Wilate 2009, Humate-P 1986), ADO09 (pramlintide plus a glargine metabolite), Product 0405
  (a generic-maker corticosteroid) and esketamine (an enantiomer of ketamine, approved 1970).
- **Wrong modality (4):** GB001 is a small molecule, not a peptide. Beti-cel and lovo-cel are
  ex vivo gene therapies. Proinsulin is a DNA vaccine.
- **Wrong FDA date (3):** aminopterin and hydroxyflutamide have none in the DB. Belantamab was
  first approved on 2020-08-05; the DB has the 2025 re-approval.
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
2026-11-05 00:54 UTC) linked them. Today both drop out of the hypertension and eczema
mechanism counts.

The same mechanism remains for salts, esters, prodrugs, metabolites, enantiomers and plasma
products that have no link of their own, and for drugs marketed before Drugs@FDA (the six
not-novel moieties above). Brivanib and
brivanib alaninate, futuximab and modotuximab (both Sym004), CH-1504 and its L-isomer CH-4051,
and "nerve growth factor" and cenegermin (NCT03019627) are also duplicate entities.
`reviews.csv` folds them with `same_entity_as`.

## 3. The register and the tracked tiles

Structure: the atlas **registers every mechanism in every indication**. A mechanism is
(verified target, action), counted across modalities: modality does not define it and is listed per
tile (`modality_groups`). Off-class and no-target members are excluded, non-selective members form
their own mechanism, and duplicate moieties count once (`same_entity_as`). A mechanism with **at
least 3 distinct novel Phase 2 programs is tracked** and gets a tile in `lists/named_contexts.csv`.
**Phase is never a criterion**: ranking or filtering by furthest phase favoured the classes that had
already succeeded, which is the outcome the atlas tests. There is no single winner per indication,
and so no tie-breaks.

**Result: 1,661 register rows (`register.csv`); 118 tracked tiles in 47 of 71
indications (27 with more than one); 24 indications have no tracked tile.**
32 tiles are the mechanism the earlier single-winner rule would have picked.

| indication | novel Phase 2 programs | tiles | tracked mechanisms (programs, modalities when more than one) |
|---|---|---|---|
| allergic disease | 7 | 1 | allergen (immunotherapy) (5, other/peptide) |
| allergic rhinitis | 39 | 2 | allergen (immunotherapy) (8, other/peptide/protein); PTGDR2 antagonists (4) |
| Crohn disease | 36 | 1 | anti-IL23A antibodies (3) |
| psoriasis | 80 | 5 | RORC inverse agonists (4); anti-IL17A antibodies (4, antibody/protein); JAK1 inhibitors (3); PDE4 inhibitors (3); anti-IL23A antibodies (3) |
| rheumatoid arthritis | 96 | 3 | BTK inhibitors (8); SYK inhibitors (3); anti-CSF2 antibodies (3) |
| ulcerative colitis | 70 | 1 | S1PR1 agonists (3) |
| secondary hyperparathyroidism | 6 | 1 | CASR positive modulators (4, peptide/small molecule) |
| type 1 diabetes mellitus | 31 | 1 | SLC5A2 inhibitors (4) |
| type 2 diabetes mellitus | 126 | 10 | GLP1R agonists (12, peptide/protein/small molecule); GCK activators (9); HSD11B1 inhibitors (8); DPP4 inhibitors (7); INSR agonists (6); GCGR/GLP1R agonists (5); SLC5A2 inhibitors (5); GCGR antagonists (4, antibody/small molecule); GPR119 agonists (4); CCR2 antagonists (3) |
| gastroesophageal reflux disease | 11 | 1 | ATP4A blockers (3) |
| metabolic dysfunction-associated steatohepatitis | 75 | 2 | NR1H4 agonists (4); FGF21 analogue (FGFR1c/KLB) agonists (3) |
| primary biliary cholangitis | 15 | 1 | NR1H4 agonists (3) |
| hemophilia A | 15 | 1 | F8 replacement / gene therapy (8, gene therapy/protein) |
| hemophilia B | 10 | 1 | F9 replacement / gene therapy (7, gene therapy/protein) |
| paroxysmal nocturnal hemoglobinuria | 9 | 1 | anti-C5 antibodies (4) |
| HIV infectious disease | 32 | 4 | HIV RT (NNRTI) inhibitors (3); HIV RT (NRTI) inhibitors (3); HIV integrase (INSTI) inhibitors (3); HIV maturation (Gag) inhibitors (3) |
| chronic hepatitis B virus infection | 18 | 2 | HBV RNA antisense / siRNA (3); HBsAg release (NAP) inhibitors (3) |
| hepatitis C virus infection | 52 | 4 | HCV NS3/4A protease inhibitors (13); HCV NS5A inhibitors (10); HCV NS5B (non-nucleoside) inhibitors (10); HCV NS5B (nucleotide) inhibitors (7) |
| hyperlipidemia | 33 | 2 | CETP inhibitors (3); HCAR2 agonists (3) |
| Alzheimer disease | 76 | 5 | BACE1 inhibitors (4); anti-MAPT antibodies (4); HRH3 antagonists (3); HTR6 antagonists (3); anti-APP antibodies (3) |
| migraine disorder | 29 | 2 | CGRP receptor antagonists (4); anti-CALCA/CALCB (CGRP ligand) antibodies (3) |
| acute myeloid leukemia | 78 | 2 | FLT3 inhibitors (4); CD33-directed depleters (3, ADC/antibody/cell therapy) |
| breast cancer | 129 | 9 | CDK4/6 inhibitors (6); ESR1 degrader (5); HSP90AA1/HSP90AB1 inhibitors (5); PI3K/MTOR inhibitors (5); anti-IGF1R antibodies (4); PARP1/2 inhibitors (3); PI3K (pan) inhibitors (3); PIK3CA inhibitors (3); pan-HER inhibitors (3) |
| colorectal cancer | 88 | 3 | KDR (VEGFR) inhibitors (3); VEGFR multikinase inhibitors (3); anti-EGFR antibodies (3) |
| follicular lymphoma | 34 | 2 | CD19-directed depleters (3); PIK3CD inhibitors (3) |
| gastric cancer | 40 | 2 | PARP1/2 inhibitors (3); anti-ERBB2 antibodies (3) |
| hepatocellular carcinoma | 73 | 4 | VEGFR multikinase inhibitors (4); anti-PDCD1 antibodies (4); KDR (VEGFR) inhibitors (3); anti-CD274 antibodies (3) |
| malignant pancreatic neoplasm | 73 | 1 | MAP2K1/2 inhibitors (3) |
| melanoma | 51 | 2 | BRAF inhibitors (3); anti-PDCD1 antibodies (3) |
| myelodysplastic syndrome | 44 | 1 | HDAC (pan) inhibitors (3) |
| non-small cell lung carcinoma | 191 | 9 | EGFR inhibitors (18); ALK inhibitors (6); MET inhibitors (5); anti-IGF1R antibodies (4); anti-PDCD1 antibodies (4); pan-HER inhibitors (4); HSP90AA1/HSP90AB1 inhibitors (3); VEGFR multikinase inhibitors (3); anti-CTLA4 antibodies (3) |
| ovarian cancer | 58 | 1 | PARP1/2 inhibitors (6) |
| plasma cell myeloma | 73 | 2 | TNFRSF17-directed depleters (8, ADC/antibody/cell therapy); PSMB5 inhibitors (3) |
| prostate cancer | 91 | 5 | AR antagonists (5); PARP1/2 inhibitors (5); CYP17A1/AR inhibitors (3); EZH2 inhibitors (3); FOLH1-directed depleters (3, ADC/other) |
| small cell lung carcinoma | 39 | 1 | anti-PDCD1 antibodies (3) |
| diabetic macular edema | 21 | 1 | anti-VEGFA antibodies (3) |
| dry eye syndrome | 51 | 1 | anti-TNF antibodies (3, antibody/protein) |
| open-angle glaucoma | 20 | 1 | ROCK inhibitors (3) |
| atopic eczema | 81 | 3 | PDE4 inhibitors (5); anti-IL33 antibodies (4); HRH4 antagonists (3) |
| diabetic kidney disease | 26 | 1 | NR3C2 antagonists (3) |
| osteoarthritis | 65 | 2 | MAPK14 inhibitors (3); NTRK1 inhibitors (3) |
| insomnia | 11 | 1 | HCRTR1/2 antagonists (6) |
| schizophrenia | 45 | 3 | PDE10A inhibitors (5); SLC6A9 inhibitors (4); CHRNA7 agonists (3) |
| asthma | 84 | 4 | PTGDR2 antagonists (9); ADRB2 agonists (4); NR3C1 agonists (4); anti-IL13 antibodies (4) |
| chronic obstructive pulmonary disease | 47 | 3 | CHRM3 antagonists (6); ADRB2 agonists (4); MAPK14 inhibitors (4) |
| cystic fibrosis | 43 | 2 | CFTR correctors (10); CFTR potentiators (5) |
| interstitial cystitis | 10 | 1 | anti-NGF antibodies (3) |

**No tracked tile (24):** atopic conjunctivitis, eosinophilic esophagitis, atrial fibrillation, coronary artery disorder, heart failure, hypertensive disorder, endometriosis, irritable bowel syndrome, sickle cell disease, influenza, Prader-Willi syndrome, hypertriglyceridemia, obesity disorder, Parkinson disease, diabetic neuropathy, glioblastoma, age-related macular degeneration, acne, attention deficit-hyperactivity disorder, major depressive disorder, idiopathic pulmonary fibrosis, benign prostatic hyperplasia, overactive bladder, premature ejaculation. Their mechanisms stay in the register with fewer
than 3 programs each.

## 4. Recommended DB fixes (not applied)

1. Decide novelty at the active-moiety level (UNII parent, or ChEMBL parent when that mapping is
   right), so that salts, esters, prodrugs, metabolites and enantiomers inherit their sibling's
   approval. Add FDA links for hydroxyflutamide (NDA 018554), the FVIII/VWF complex, the ADO09
   components and Product 0405, and record aminopterin's 1953–1964 US marketing.
2. Correct `moiety_target` for the 13 wrong-target moieties above. Correct `moiety.modality` for
   GB001, beti-cel and lovo-cel, and set Cal-1's (now unknown). Replace the action `other` with
   `positive_modulator` for lumacaftor and posenacaftor.
3. Merge the duplicate moieties: ToleroMune HDM = HDM-SPIRE, ToleroMune Ragweed = Ragweed-SPIRE,
   brivanib alaninate → brivanib, futuximab + modotuximab = Sym004, CH-4051 → CH-1504, and
   "nerve growth factor" → cenegermin.
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
- The mechanisms of AL-38583, CHF5992, EX1000 and SUN-597 (SPARC1316) are undisclosed, and
  the identity of pf-5212372 is unconfirmed; the DB target was kept for each.
- The identity of "proinsulin human" is inferred.
- Many `evidence` entries for code-named compounds are PubMed queries rather than a single
  paper.
