# Drug-class audit of the atlas diseases

`class_audit.py` rebuilds the lists.py cohort (novel Phase 2 entrants 2008–2019 in every disease with a
Phase 2 entrant, after lists.py's merge and drop rules: 935 diseases, 5,814 Phase 2 programs, 5,080 of them
novel) and joins it to a hand review (`reviews.csv`, 847 moieties: every member of every tracked mechanism,
the unresolved-target programs of several diseases, and members of some untracked mechanisms). Each review
row cites ChEMBL, an FDA or registry page, a DOI or a PubMed query. Outputs: `class_members.csv` (one row
per novel program, review columns plus `db_issue`), `register.csv` (every disease × mechanism) and the
tracked tiles, `lists/named_contexts.csv`.

**Snapshot.** The cohort is drawn on the database snapshot of 2026-11-02 (`lists/provenance.json`, which
records no programs build). No reviewed moiety is a merge loser in `preclin.moiety_merge`.

## 1. Where the database disagrees with the review

Of 805 reviewed moieties with a disclosed mechanism, **40 are flagged as disagreeing with the DB**
on target, action, modality or novelty (`disagrees_with_db`). Two of the 40, lumacaftor and
posenacaftor, are flagged only because the DB action is the vague `other` (they are CFTR
correctors), so 38 are real errors. Another 99 have no DB target at all
(pathogen targets, allergen immunotherapies, siRNAs), and 42 have an undisclosed mechanism.

- **Wrong target (18):** BMS-914392 is an I_KACh blocker, not Kv1.5. JNJ-39588146 is
  stresscopin, a CRF2 agonist, not an NPR1 agonist. ODM-104 is a COMT inhibitor, not a
  dopamine agonist (its action is wrong as well). XP21279 is a levodopa prodrug. "Proinsulin
  human" is most likely the BHT-3021 tolerising vaccine, not an insulin-receptor agonist.
  Tivantinib acts on tubulin, not MET. Pidilizumab binds DLL1, not PD-1. Iniparib is not a PARP
  inhibitor. Rigosertib is not a PLK1 inhibitor. Deudextromethorphan is not a GluN2B
  antagonist. Cannabidiol is not a CB1 negative modulator. AXP1275 is a CCR3 antagonist, not a
  CRTH2 antagonist. Arbekacin reads through premature stop codons at the ribosome; it does not act
  on dystrophin. Topsalysin (PRX302) is a PSA-activated pore-forming toxin. Vixotrigine is a
  broad-spectrum Nav blocker, not Nav1.7-selective. Chromanol (APC-100), propagermanium and
  (R)-mequitazine are off-class.
- **Not novel (11):** aminopterin (marketed in the US by Lederle 1953–1964, before Drugs@FDA;
  RA and psoriasis programs), hydroxyflutamide (flutamide's active metabolite, 1989), FVIII/VWF complex
  (Wilate 2009, Humate-P 1986), ADO09 (pramlintide plus a glargine metabolite), Product 0405
  (a generic-maker corticosteroid), esketamine (an enantiomer of ketamine, approved 1970), three
  conjugates of interferon alfa-2b (HM10660A, ropeginterferon, ypeginterferon), idursulfase beta
  (the enzyme of Elaprase, 2006) and lonapegsomatropin (a prodrug releasing somatropin).
- **Wrong modality (10):** GB001 is a small molecule, not a peptide. Beti-cel, lovo-cel,
  azamidugene autotemcel, voxeralgagene autotemcel, dabocemagene autoficel, prademagene zamikeracel
  and Hologene 7 are ex vivo gene therapies. Di-Leu16-IL2 is an antibody–IL-2 fusion, not an ADC.
  Proinsulin is a DNA vaccine.
- **Wrong FDA date (3):** aminopterin and hydroxyflutamide have none in the DB. Belantamab was
  first approved on 2020-08-05; the DB has the 2025 re-approval.
- **Lumping by the rule, not by the data:** the DB lists the right targets for multi-target drugs
  (103 of the 617 moieties in tracked tiles have more than one primary target), but a 1/k weighting
  over them would put them into single-target classes. The register places them by the review
  instead: 18 dual-target and 18 pan or multikinase moieties form mechanisms of their own, e.g.
  tofacitinib in JAK (pan), brepocitinib in TYK2/JAK1, ritlecitinib in JAK3/TEC and tirzepatide in
  GIPR/GLP1R. 25 tracked tiles in 22 diseases also mix modality groups.

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
products that have no link of their own, and for drugs marketed before Drugs@FDA (the eleven
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

**Result (snapshot 2026-11-02): 3,232 register rows (`register.csv`); 166 tracked tiles in 85 of 935
diseases (33 with more than one); 850 diseases have no tracked tile.**

| indication | Phase 2 programs | tiles | tracked mechanisms (programs, modalities when more than one) |
|---|---|---|---|
| allergic disease | 7 | 1 | allergen (immunotherapy) (5, other/peptide) |
| allergic rhinitis | 39 | 2 | allergen (immunotherapy) (8, other/peptide/protein); PTGDR2 antagonists (4) |
| Crohn disease | 36 | 1 | anti-IL23A antibodies (3) |
| Sjogren syndrome | 17 | 2 | BTK inhibitors (3); PIK3CD inhibitors (3) |
| psoriasis | 78 | 5 | RORC inverse agonists (4); anti-IL17A antibodies (4, antibody/protein); JAK1 inhibitors (3); PDE4 inhibitors (3); anti-IL23A antibodies (3) |
| rheumatoid arthritis | 96 | 3 | BTK inhibitors (8); SYK inhibitors (3); anti-CSF2 antibodies (3) |
| systemic lupus erythematosus | 36 | 1 | BTK inhibitors (3) |
| ulcerative colitis | 70 | 1 | S1PR1 agonists (3) |
| acute coronary syndrome | 9 | 1 | APOA1 replacement / gene therapy (3) |
| endometriosis | 13 | 1 | GNRHR antagonists (3) |
| hypopituitarism | 6 | 1 | GHR agonists (3) |
| pituitary dwarfism | 3 | 1 | GHR agonists (3) |
| secondary hyperparathyroidism | 6 | 1 | CASR positive modulators (4, peptide/small molecule) |
| type 1 diabetes mellitus | 31 | 1 | SLC5A2 inhibitors (4) |
| type 2 diabetes mellitus | 125 | 10 | GLP1R agonists (12, peptide/protein/small molecule); GCK activators (9); HSD11B1 inhibitors (8); DPP4 inhibitors (7); INSR agonists (6); GCGR/GLP1R agonists (5); SLC5A2 inhibitors (5); GCGR antagonists (4, antibody/small molecule); GPR119 agonists (4); CCR2 antagonists (3) |
| exocrine pancreatic insufficiency | 4 | 1 | PNLIP replacement / gene therapy (3) |
| gastroesophageal reflux disease | 11 | 1 | ATP4A blockers (3) |
| metabolic dysfunction-associated steatohepatitis | 76 | 2 | NR1H4 agonists (4); FGF21 analogue (FGFR1c/KLB) agonists (3) |
| opioid-induced constipation | 5 | 1 | OPRM1 antagonists (4) |
| primary biliary cholangitis | 15 | 1 | NR1H4 agonists (3) |
| hemophilia A | 15 | 1 | F8 replacement / gene therapy (8, gene therapy/protein) |
| hemophilia B | 10 | 1 | F9 replacement / gene therapy (7, gene therapy/protein) |
| paroxysmal nocturnal hemoglobinuria | 9 | 1 | anti-C5 antibodies (4) |
| HIV infectious disease | 32 | 4 | HIV RT (NNRTI) inhibitors (3); HIV RT (NRTI) inhibitors (3); HIV integrase (INSTI) inhibitors (3); HIV maturation (Gag) inhibitors (3) |
| chronic hepatitis B virus infection | 32 | 3 | HBV RNA antisense / siRNA (3); HBsAg release (NAP) inhibitors (3); TLR7 agonists (3) |
| hepatitis C virus infection | 70 | 5 | HCV NS3/4A protease inhibitors (13); HCV NS5A inhibitors (10); HCV NS5B (non-nucleoside) inhibitors (10); HCV NS5B (nucleotide) inhibitors (7); IFNAR1/IFNAR2 agonists (3) |
| Fabry disease | 5 | 1 | GLA replacement / gene therapy (4, gene therapy/protein) |
| glycogen storage disease II | 5 | 1 | GAA replacement / gene therapy (3) |
| hyperlipidemia | 33 | 2 | CETP inhibitors (3); HCAR2 agonists (3) |
| mucopolysaccharidosis type 1 | 6 | 1 | IDUA replacement / gene therapy (4, gene therapy/protein) |
| mucopolysaccharidosis type 3B | 4 | 1 | NAGLU replacement / gene therapy (3, gene therapy/protein) |
| Alzheimer disease | 76 | 5 | BACE1 inhibitors (4); anti-MAPT antibodies (4); HRH3 antagonists (3); HTR6 antagonists (3); anti-APP antibodies (3) |
| Duchenne muscular dystrophy | 24 | 1 | DMD (8) |
| Huntington disease | 15 | 1 | HTT antisense / siRNA (4, gene therapy/oligo) |
| fragile X syndrome | 8 | 1 | GRM5 negative modulators (3) |
| migraine disorder | 29 | 2 | CGRP receptor antagonists (4); anti-CALCA/CALCB (CGRP ligand) antibodies (3) |
| multiple sclerosis | 26 | 1 | MS4A1-directed depleters (4) |
| primary erythermalgia | 4 | 1 | SCN9A blockers (3) |
| B-cell non-Hodgkin lymphoma | 8 | 1 | MS4A1-directed depleters (3, antibody/cell therapy) |
| Hodgkins lymphoma | 22 | 2 | anti-PDCD1 antibodies (6); anti-CD274 antibodies (3) |
| Waldenstrom macroglobulinemia | 8 | 1 | MS4A1-directed depleters (3) |
| acute lymphoblastic leukemia | 17 | 1 | CD19-directed depleters (6, ADC/cell therapy) |
| acute myeloid leukemia | 79 | 2 | FLT3 inhibitors (4); CD33-directed depleters (3, ADC/antibody/cell therapy) |
| breast cancer | 129 | 9 | CDK4/6 inhibitors (6); ESR1 degrader (5); HSP90AA1/HSP90AB1 inhibitors (5); PI3K/MTOR inhibitors (5); anti-IGF1R antibodies (4); PARP1/2 inhibitors (3); PI3K (pan) inhibitors (3); PIK3CA inhibitors (3); pan-HER inhibitors (3) |
| cervical cancer | 8 | 1 | anti-PDCD1 antibodies (4) |
| chronic lymphocytic leukemia/small lymphocytic lymphoma | 29 | 3 | BTK inhibitors (4); CD19-directed depleters (4, antibody/cell therapy); MS4A1-directed depleters (4, antibody/protein) |
| chronic myeloid leukemia | 11 | 1 | ABL1 inhibitors (3) |
| colorectal cancer | 88 | 3 | KDR (VEGFR) inhibitors (3); VEGFR multikinase inhibitors (3); anti-EGFR antibodies (3) |
| diffuse large B-cell lymphoma | 31 | 2 | MS4A1-directed depleters (5, antibody/protein); CD19-directed depleters (4, ADC/antibody/cell therapy) |
| extranodal nasal NK/T cell lymphoma | 6 | 1 | anti-PDCD1 antibodies (3) |
| follicular lymphoma | 34 | 3 | MS4A1-directed depleters (4); CD19-directed depleters (3); PIK3CD inhibitors (3) |
| gastric cancer | 40 | 2 | PARP1/2 inhibitors (3); anti-ERBB2 antibodies (3) |
| gastrointestinal stromal tumor | 12 | 1 | HSP90AA1/HSP90AB1 inhibitors (3) |
| hepatocellular carcinoma | 73 | 4 | VEGFR multikinase inhibitors (4); anti-PDCD1 antibodies (4); KDR (VEGFR) inhibitors (3); anti-CD274 antibodies (3) |
| large B-cell lymphoma | 4 | 1 | CD19-directed depleters (3) |
| malignant pancreatic neoplasm | 74 | 1 | MAP2K1/2 inhibitors (3) |
| mantle cell lymphoma | 15 | 2 | BTK inhibitors (4); CD19-directed depleters (3, ADC/cell therapy) |
| marginal zone lymphoma | 9 | 1 | MS4A1-directed depleters (3) |
| melanoma | 52 | 2 | BRAF inhibitors (3); anti-PDCD1 antibodies (3) |
| myelodysplastic syndrome | 44 | 1 | HDAC (pan) inhibitors (3) |
| myelofibrosis | 21 | 1 | JAK2 inhibitors (3) |
| non-small cell lung carcinoma | 191 | 9 | EGFR inhibitors (18); ALK inhibitors (6); MET inhibitors (5); anti-IGF1R antibodies (4); anti-PDCD1 antibodies (4); pan-HER inhibitors (4); HSP90AA1/HSP90AB1 inhibitors (3); VEGFR multikinase inhibitors (3); anti-CTLA4 antibodies (3) |
| ovarian cancer | 58 | 1 | PARP1/2 inhibitors (6) |
| plasma cell myeloma | 73 | 2 | TNFRSF17-directed depleters (8, ADC/antibody/cell therapy); PSMB5 inhibitors (3) |
| prostate cancer | 91 | 5 | AR antagonists (5); PARP1/2 inhibitors (5); CYP17A1/AR inhibitors (3); EZH2 inhibitors (3); FOLH1-directed depleters (3, ADC/other) |
| renal cell carcinoma | 29 | 1 | VEGFR multikinase inhibitors (4) |
| small cell lung carcinoma | 39 | 1 | anti-PDCD1 antibodies (3) |
| age-related macular degeneration | 52 | 1 | anti-VEGFA antibodies (5, antibody/cell therapy/gene therapy/protein) |
| diabetic macular edema | 21 | 1 | anti-VEGFA antibodies (3) |
| dry eye syndrome | 51 | 1 | anti-TNF antibodies (3, antibody/protein) |
| open-angle glaucoma | 27 | 2 | ROCK inhibitors (6); PTGER2 agonists (3) |
| retinitis pigmentosa | 14 | 1 | RPGR replacement / gene therapy (3) |
| atopic eczema | 81 | 3 | PDE4 inhibitors (5); anti-IL33 antibodies (4); HRH4 antagonists (3) |
| diabetic kidney disease | 26 | 1 | NR3C2 antagonists (3) |
| gout | 20 | 1 | SLC22A12 inhibitors (5) |
| osteoarthritis | 65 | 2 | MAPK14 inhibitors (3); NTRK1 inhibitors (3) |
| osteoporosis | 5 | 1 | anti-SOST antibodies (3) |
| recessive dystrophic epidermolysis bullosa | 7 | 1 | COL7A1 replacement / gene therapy (5, gene therapy/protein) |
| insomnia | 11 | 1 | HCRTR1/2 antagonists (6) |
| schizophrenia | 45 | 3 | PDE10A inhibitors (5); SLC6A9 inhibitors (4); CHRNA7 agonists (3) |
| asthma | 87 | 4 | PTGDR2 antagonists (9); ADRB2 agonists (4); NR3C1 agonists (4); anti-IL13 antibodies (4) |
| chronic obstructive pulmonary disease | 46 | 3 | CHRM3 antagonists (6); ADRB2 agonists (4); MAPK14 inhibitors (4) |
| cystic fibrosis | 43 | 2 | CFTR correctors (10); CFTR potentiators (5) |
| pulmonary arterial hypertension | 14 | 1 | PTGIR agonists (3) |
| interstitial cystitis | 10 | 1 | anti-NGF antibodies (3) |

**No tracked tile:** 850 of 935 diseases, none with a mechanism of 3 or more programs.

## 4. Recommended DB fixes (not applied)

1. Decide novelty at the active-moiety level (UNII parent, or ChEMBL parent when that mapping is
   right), so that salts, esters, prodrugs, metabolites and enantiomers inherit their sibling's
   approval. Add FDA links for hydroxyflutamide (NDA 018554), the FVIII/VWF complex, the ADO09
   components and Product 0405, and record aminopterin's 1953–1964 US marketing.
2. Correct `moiety_target` for the 18 wrong-target moieties above. Correct `moiety.modality` for
   the wrong-modality moieties above. Replace the action `other` with
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

- 42 moieties (44 programs) have an undisclosed mechanism (e.g. AL-53817, BLI1100-x, SPARC codes) and are
  marked `unknown`.
- The mechanisms of AL-38583, CHF5992, EX1000 and SUN-597 (SPARC1316) are undisclosed, and
  the identity of pf-5212372 is unconfirmed; the DB target was kept for each.
- The identity of "proinsulin human" is inferred.
- Many `evidence` entries for code-named compounds are PubMed queries rather than a single
  paper.
