# Drug-class audit of the named contexts (PR #81)

`class_audit.py` rebuilds the lists.py cohort (novel Phase 2 entrants 2008–2019 in the 71 named
indications, 2,635 programs) and joins it to a hand review (`reviews.csv`, 590 moieties: every
member of each currently chosen class, both top classes under the proposed rule, and every
unresolved-target program in allergic disease, allergic rhinitis, atopic conjunctivitis, acne,
chronic HBV, HIV, HCV, BPH and dry eye). Each review row cites ChEMBL, an FDA or registry page,
a DOI or a PubMed query. Outputs: `class_members.csv` (one row per program, review columns plus
`db_issue`), `current_on_db.csv` (lists.classes() on today's DB) and `proposed_contexts.csv`.

**The database changed during the audit.** Between runs on 2026-11-04 another session removed
every `dev_program` row for relugolix and cannabidiol. The files reflect the last run (23:20 PST).
With relugolix back, endometriosis keeps "GNRHR antagonists" (3 entities, phase 4). Re-run the
script after that write lands.

## 1. Where the database disagrees with the review

Of 549 reviewed moieties with a disclosed mechanism, **21 disagree with the DB** on target,
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

## 3. Contexts that change under the proposed rule (54 of 71)

Proposed rule: class = (verified target, action, modality group). Off-class, pan and
no-target members are excluded. Classes rank by furthest phase, then entity count, with at
least 3 entities required.

**Same class, narrowed or relabelled (13).** In each case members of another modality or
target were removed, or the class was renamed:

- T2D: GLP-1R peptides. Dual agonists, small molecules and Fc fusions are split out.
- Hemophilia A and B: AAV gene therapy. Recombinant factor proteins are a separate class.
- HCV: "HCV NS3/4A protease inhibitors". The label has no comma; the file is properly quoted.
- HIV: "HIV integrase (INSTI)". It ties with NNRTIs on phase 4 and is ahead on members
  approved for HIV.
- Migraine: the CGRP receptor (CALCRL+RAMP1). The ligand antibodies are a separate class.
- Pancreatic cancer: MEK1/2.
- Ovarian cancer: PARP1/2. Iniparib is dropped.
- Myeloma: BCMA cell therapies. The belantamab ADC, the vonsetamig T-cell engager and dual
  AUTO2 are excluded.
- Follicular lymphoma: CD19 CAR-T. The CD19 ADC denintuzumab mafodotin is coded with action
  `other`, so it never joined the class; there is no mix today.
- DME: VEGF-trap proteins. Faricimab (dual) and brolucizumab (scFv) are excluded.
- Insomnia: dual orexin antagonists. Seltorexant (OX2-selective) is excluded.
- Cystic fibrosis: CFTR correctors, split from potentiators.

**A different class, mostly because furthest phase now ranks first (17):**

- Allergic disease: unresolved → peptide allergen immunotherapy.
- RA: BTK (8, phase 2) → anti-GM-CSF antibodies (3, phase 3).
- Crohn: JAK1 → anti-IL-23p19. Only 2 selective JAK1 members are left.
- MASH: FXR (phase 2) → FGF21 analogues (phase 3).
- Alzheimer: anti-tau → anti-amyloid. Lecanemab is approved.
- Breast: ERBB2 → CDK4/6. ERBB2 splits by modality and pan-HER.
- Prostate: AR → PARP1/2. Losing chromanol and hydroxyflutamide leaves AR tied at 5; PARP has
  more approved members.
- CRC: anti-EGFR antibodies → VEGFR-selective TKIs. Fruquintinib is approved.
- HCC: anti-PD-1 → VEGFR multikinase inhibitors. Pidilizumab is excluded.
- MDS: CD33 (2 entities) → pan-HDAC.
- Gastric: ERBB2 mixed → HER2 antibodies only. It ties with PARP1/2.
- Glaucoma: A2A → ROCK. Netarsudil is approved.
- Eczema: NR3C1 → PDE4. Crisaborole is approved; mometasone is not novel.
- OA: TrkA → p38α. It ties with TrkA; ONO-4474 (pan-Trk) is excluded.
- Schizophrenia: PDE10A (phase 2) → GlyT1 (phase 3).
- Chronic HBV: core → HBV siRNA. It ties with nucleic-acid polymers, all from one sponsor.
- Endometriosis: no class. This is the DB-flux artefact described at the top.

**No qualifying class, fewer than 3 entities (24):** atopic conjunctivitis, EoE, heart failure,
hypertension, AF (BMS-914392 is not Kv1.5), CAD, IBS, sickle cell, influenza, obesity, HTG,
Prader-Willi, Parkinson (ODM-104 and XP21279 are off-class), diabetic neuropathy, glioblastoma,
dry eye (lubricants have no target), AMD, acne, MDD (esketamine and deudextromethorphan are
excluded), ADHD, IPF, OAB, BPH and premature ejaculation.

Allergic rhinitis keeps PTGDR2, but only on the alphabetical tie-break against peptide allergen
immunotherapy (4 vs 4, both phase 3).

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
