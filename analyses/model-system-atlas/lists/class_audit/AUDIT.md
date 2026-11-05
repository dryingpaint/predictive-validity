# Drug-class audit of the named contexts (PR #81)

`class_audit.py` rebuilds the lists.py cohort (novel Phase 2 entrants 2008–2019 in the 71 named
indications, 2,634 programs) and joins it to a hand review (`reviews.csv`, 632 moieties: every
member of each currently chosen class, both top classes under the proposed rule, and every
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

## 3. The selection rule and what changes (43 of 71 contexts)

Rule: class = (verified target, action, modality group). Off-class and no-target members are
excluded, pan members form their own class, and duplicate moieties count once
(`same_entity_as`). Classes rank by **distinct entities first**, then by furthest phase reached
in the indication, then by entities at that phase. A class needs **at least 2 entities**.

Count comes first because ranking by furthest phase favoured classes that had already succeeded
(an approved member wins), which biases a "most-developed class" toward the successes the
atlas is meant to test. The minimum of 2 keeps small indications in the atlas while still
rejecting a class of one.

The 42 moieties that came into scope under this rule (GCK and HSD11B1 in T2D, RORγt in
psoriasis, CTLA-4 in SCLC, CRF1/V1b in MDD, factor D, IDH1, AKT, TLR3, COMT, NGF, EP1 and
multichannel blockers) were reviewed. All are novel at entry:

- ipilimumab entered SCLC in 2008-02, before its 2011-03 approval;
- opicapone entered Parkinson's in 2009, before its 2020 approval;
- cenegermin entered dry eye in 2014, before its 2018 approval;
- ivosidenib entered AML in 2016-06, before its 2018-07 approval.

The DB's "nerve growth factor" (NCT03019627) is Dompé's cenegermin, a duplicate moiety now
folded. Rintatolimod's ChEMBL id is the one shared with imatinib. No other DB disagreement.

**Same class, narrowed or relabelled (15).** Other modalities or targets were removed, or the
class was renamed:

- Relabelled by modality: sickle cell (gene therapy), hemophilia A and B (AAV gene
  therapy; recombinant factor protein is the runner-up), obesity (GLP-1R peptides) and
  hypertriglyceridemia (APOC3 oligos).
- HCV: "HCV NS3/4A protease inhibitors"; the label has no comma.
- HIV: "HIV integrase (INSTI)".
- Migraine: the CGRP receptor.
- Myeloma: BCMA cell therapies.
- Pancreatic cancer: MEK1/2.
- Ovarian cancer: PARP1/2.
- Follicular lymphoma: CD19 CAR-T.
- DME: VEGF-trap proteins.
- Insomnia: dual orexin antagonists.
- Cystic fibrosis: CFTR correctors.

**A different class (21):**

- Allergic disease: unresolved → peptide allergen immunotherapy (3).
- Psoriasis: IL-17A antibodies (3) → RORγt inverse agonists (4). The label reads "RORC
  inverse_agonist" because lists.ACTION_PHRASE has no phrase for that action.
- Crohn: JAK1 → anti-IL-23p19 (3). Tofacitinib and brepocitinib are excluded, leaving 2 JAK1.
- AF: Kv1.5 → multichannel blockers (2). BMS-914392 is an I_KACh blocker, so Kv1.5 has 1 entity.
- T2D: GLP-1R → GCK activators (9 vs 7 GLP-1R peptides, once co-agonists, small molecules
  and Fc fusions split out). HSD11B1 is second with 8.
- Influenza: HA → TLR3 agonists (2). Tied with HA-stem antibodies; broken alphabetically.
- Chronic HBV: core → HBV siRNA (3). Tied with nucleic-acid polymers.
- Alzheimer: anti-tau → BACE1 (4, phase 3). Ties anti-tau on count; wins on phase.
- Parkinson: anti-α-syn → COMT inhibitors (2, phase 4 with opicapone).
- Breast: ERBB2 → CDK4/6 (6).
- Prostate: AR → PARP1/2. Both have 5; PARP has more approved members.
- CRC: anti-EGFR antibodies → VEGFR-selective TKIs (3).
- HCC: anti-PD-1 → VEGFR multikinase (4, phase 4). Ties PD-1 at 4.
- Glioblastoma: tubulin → PI3K/mTOR (2, phase 3).
- MDS: CD33 → pan-HDAC (3).
- Gastric: ERBB2 mixed → HER2 antibodies (3). Tied with PARP1/2.
- Dry eye: anti-TNF → glucocorticoid agonists (2). Tied with anti-TNF; one member, AL-38583,
  is undisclosed.
- Glaucoma: A2A → ROCK (3).
- Atopic eczema: NR3C1 → PDE4 (5). Mometasone is not novel.
- Osteoarthritis: TrkA → p38α (3). Tied with TrkA.
- MDD: GluN2B → V1b antagonists (2). Tied with CRF1; esketamine and deudextromethorphan are
  excluded.

**No qualifying class (7):** eosinophilic esophagitis, heart failure, hypertension,
Prader-Willi, AMD, acne and premature ejaculation. In each, every class has one entity.

**Unchanged (28),** e.g. RA (BTK, 8), MASH (FXR, 4), schizophrenia (PDE10A, 5), asthma, COPD,
NSCLC and AML. Allergic rhinitis keeps PTGDR2 only on the alphabetical tie-break against peptide
allergen immunotherapy (4 each, phase 3). Ties broken alphabetically are flagged in `reason`.

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
