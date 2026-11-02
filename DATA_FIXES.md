# Data fixes: known label errors, their causes, and the plan

Every error the audits found that is still in the database, traced to the code that produced it.
The audits are in `report/audits/`: the label audits, the approval audit, the outcome, publication
and endpoint audits, and the Section 3 case audit. Each fix goes in at the source (a prompt, a rule,
an ingestion filter), and the affected labels are re-derived. No row is patched by hand. Counts were
taken from the live database on 2026-11-02. Counts marked ≈ come from name-matching screens and are
upper bounds.

## Summary

| # | Error | Example | Scope | Stage |
| - | ----- | ------- | ----- | ----- |
| 1 | Trials whose only interventions are combination products or genetic agents are never fetched | eneboparatide's Phase 3 CALYPSO (NCT05778071) | 1,991 Early Phase 1–3 trials (789 industry) | `sources` |
| 2 | Development codes resolve to the wrong substance, a salt, a hydrate or a formulation | ION363 → tadnersen sodium; TAK-418 → its hydrochloride | ≈282 salt UNIIs with a parent (≈224 with programs); 101 hydrate/anhydrous names; 18 formulation UNIIs | `identity` |
| 3 | FDA products link inactive components as entities | Extraneal → icodextrin + 4 electrolytes | 60 applications | `identity` |
| 4 | Condition strings are mapped without trial context; COVID-19 maps to SARS | "SARS-CoV Infection" → SARS (MONDO:0005091) | 124 trials from 2020 on under SARS | `identity` |
| 5 | A condition mapped to a broader term starts its own program | pegadricase: gout + purine metabolism disease | 321 programs (286 at Phase 2+) | `programs` |
| 6 | Approval judgements: supplements with no letter, tumour-agnostic approvals judged without the trial population, supportive uses counted | rivaroxaban/PAD dated 2021, not 2018; dostarlimab/biliary "yes" | 147 letterless efficacy supplements; 106 uncertain; 395 broader-class yes; 133 rest on recollection | `labels` |
| 7 | Publication outcomes judged without the registered primary outcomes | NCT01808638 "mixed" though its primaries are safety/PK | ≈163 rows | `sources`/`labels` |
| 8 | Target-engagement endpoints classed without knowing the drug | NCT02170025: sweat chloride for riociguat called target engagement | all 193 B1 labels | `labels` |
| 9 | Trials registered only outside ClinicalTrials.gov | pruxelutamide's China Phase 3s | — | out of scope (stated in Limitations) |

The NCT02205398 stop reason flagged in the outcome audit is already correct in the database.

## Status: fixed and rebuilt (2026-11-02)

Every fix above is in the code, and the database was rebuilt from a fresh ClinicalTrials.gov snapshot
(2026-11-02, 227,126 studies) through every stage of `make sources identity programs labels evidence`.
The evidence steps that read large raw releases ran on Modal (`scripts/modal_evidence.py`). The audited
cases now come out right:

| Case | Before | After |
|---|---|---|
| eneboparatide | Phase 2; CALYPSO missing | Phase 3 from 2023-06-07 (NCT05778071) |
| pegadricase | gout + purine metabolism disease ("failed") | one gout program, Phase 3 |
| sabizabulin | COVID trials under SARS; ARDS a separate program | one COVID-19 program, Phase 3 |
| ION363 / BIIB078 | ION363 linked to tadnersen sodium | ulefnersen (ALS, Phase 3) and tadnersen, each on its parent UNII |
| GenSci048 | "genakumab", no UNII | firsekibart |
| SARS strings | 16 strings, 124 trials from 2020 on | 1 string |
| Extraneal, Clenpiq | icodextrin + 4 electrolytes; sodium picosulfate anhydrous | icodextrin; picosulfate, magnesium oxide, citric acid |
| nedizantrep (AUDIT D76) | "CRC" mapped to colorectal carcinoma | chronic refractory cough, a symptom with no MONDO term |
| afuresertib (AUDIT D75) | 2012 ovarian Phase 1/2 attached to no disease | ovarian cancer program, entry 2012 |

### Bugs found during the rebuild

Each is fixed at its source, with a test:

- Condition mapper v3 took a disease from trial titles for strings that name none (biomarkers, drugs,
  qualifiers), and moved substance-cessation strings, diseases named with healthy volunteers and disease
  episodes off their disease. An adjudication of 101 changed strings found it; prompt v4 fixes all of these.
  The broader pass now reaches two levels of parents and never the MONDO root.
- Sibling intervention strings were grouped by any kept "code", including dose units ("MG") and short
  abbreviations, so 13,283 strings were sent for a second decision; only sponsor-code-shaped keys
  (letters and digits, at least three characters) group them now (1,611).
- An unregistered name was replaced by any kept code, so a vaccine became its study number ("208136");
  only a sponsor-code-shaped code replaces a drug's name, and vaccines keep theirs.
- UNII candidate truncation left a parent naming a salt outside the list (KeyError).
- Entity merges moved rows of a fixed list of tables and failed on stop_signal; they now move the rows of
  every table that references an entity, read from the catalog.
- Entity renames failed when a page of decision ids was all null (Postgres read the column as text).
- Entities nothing references were never removed; `drugs unii` now drops them.
- `make evidence` never ran `evidence_dates projectscore`, so Project Score evidence was left undated
  in a clean rebuild.
- `fda load` held its connection open through 25 minutes of OCR, and the server dropped it.
- The LLM runner waited indefinitely on batches the queue left untouched; a batch with no finished
  request after 45 minutes is now cancelled and sent directly (and one that finished meanwhile is collected).

### Accuracy after the rebuild

Fresh seeded audits (`python -m scripts.audit_samples`, seed 20261102) against primary sources,
counting correct and acceptable as agreement:

| Label | Audited | Agree | Wrong | Before |
|---|---|---|---|---|
| Condition → MONDO | 100 | 99 | 1 | 99 |
| Intervention → entities | 100 | 94 | 6 | 92 |
| FDA application → entities | 100 | 95 | 5 | 98 |
| Supplement label/review → approved uses (new) | 20 | 19 | 1 | — |
| Approval, yes/no strata | 71 | 71 | 0 | 71 of 71 |
| Approval, uncertain stratum | 12 | 9 | 3 | 9 of 14 |
| Primary endpoint from results papers | 30 | 30 | 0 | 29 of 30 |

### Remaining, measured

- Sponsor codes whose INN is recent stay unresolved when GSRS does not list the code (DW4902 is merigolix;
  HS-10365 is resencatinib), and reference-product codes in Korean bioequivalence trials stay opaque: about
  4 of the 6 wrong intervention strings. A code-to-INN source (ChEMBL synonyms) would close most of it.
- 22 entities, nearly all excipients and nutrients, sit on GSRS "unspecified form" grouping records, and
  dextrose is split across that record and anhydrous dextrose (4 of the 5 wrong FDA applications).
- A condition string naming several diseases sometimes maps to the first rather than a grouping.
- Several efficacy supplements approved weeks apart share one label, whose Recent Major Changes cannot
  separate them (1 of 20).
- Approval judgements left "uncertain" (12 of 21,628) are often settled by the rubric; they count as not
  approved, and the sensitivity table shows they move no rate.

## 1. Combination-product and genetic trials are never fetched

- **Where:** `pipeline/ctgov.py:31`. The fetch query keeps `AREA[InterventionType](DRUG OR BIOLOGICAL)`.
- **Cause:** CALYPSO's only intervention is typed `COMBINATION_PRODUCT`, so the trial never reaches
  the database. `pipeline/programs.py:28` accepts combination-product and genetic interventions, but
  only on trials that also have a drug or biological arm. AUDIT.md describes the snapshot as
  including both types, which it does not.
- **Fix:** add `COMBINATION_PRODUCT OR GENETIC` to the query.
- **Effect:** every downstream stage reruns. Many of these trials are device–drug combinations
  (prefilled pens, implants). The intervention resolver already drops non-drug interventions,
  but its non-drug rate should be checked on the new trials.

## 2. Drug → entity resolution

Code: `pipeline/drugs.py`:
- canonicalize prompt (42–48)
- exact-name linking (91–99, 145–146)
- UNII candidates (249–264)
- parent-substance rule (197)
- rename to the GSRS display name (296–302)
- same-substance merge (368, 432)

| Case | Cause | Fix |
| ---- | ----- | --- |
| ION363 → tadnersen sodium | The BIIB078 decision returned the code name `"ION363?"`. The key strips the `?`, and ION363 was linked by exact name with no model call. 26 entities carry `?` codes. | Before exact linking, drop returned code names that contain `?` or do not appear in the input. |
| TAK-418, tadnersen take the salt UNII | GSRS puts the sponsor code on the salt record. The free base is registered as "TAK-418 FREE BASE", which never matches exactly, so the parent is never a candidate and rule 197 cannot fire. | Expand UNII candidates through GSRS active-moiety relationships (or the "&lt;name&gt; free base/acid" records), then apply the parent rule. |
| Clenpiq "sodium picosulfate anhydrous", "calcium chloride anhydrous" | The model returned the right name; the UNII step picked the anhydrous record and renamed the entity to its display name. | Name entities by INN or the active-moiety record, never by the matched record's display name. |
| GenSci048 → "genakumab"; HPP737 unresolved | GSRS's firsekibart and prifemilast records lack the sponsor codes. The model invented an INN or kept the code. | Add a code → INN source (ChEMBL synonyms, WHO INN lists) as candidates. Reject an INN with no source record. |
| V116517 30 mg → oxycodone | A one-off model error; the other V116517 strings resolved correctly. Nothing checks strings that share a code against each other. | Pass sibling strings' decisions for a shared code. Flag disagreements for a second decision. |
| Meperizumab | The model kept the misspelling as the name while setting `biosimilar_of = mepolizumab`. 31 links have a name that differs from `biosimilar_of`. | For biosimilars, the entity name is `biosimilar_of`. |
| IO102-IO103 | Returned as one entity. The prompt has no rule for two codes joined by a hyphen. | Prompt rule: "CODE1-CODE2" naming two separately coded agents is a combination. |
| CKD-348(n) | Sibling strings resolved three different ways. | Covered by the sibling-consistency fix. |
| nab-paclitaxel | Its UNII is a formulation (specified-substance) record, and the merge compares only entities without a UNII. | Let the merge compare formulation UNIIs with their active moiety. |
| allo-APZ2-ACLF → allo-APZ2-CVU | Correctly merged as one cell product, but the merged entity took the name with the most links. | Name merged entities by the product's nonproprietary name. |

**Rerun:** `drugs canonicalize` → `fda link` → `drugs unii`, then `programs` onward.

## 3. FDA products link inactive components

- **Where:** `pipeline/fda.py:311–316` (ingredient prompt), `link` at 416–458.
- **Cause:** the prompt asks for "every active entity". Labels list dialysis and bowel-prep
  electrolytes as active, so they become entities and carry the product's approvals. Sodium chloride
  is linked to 193 applications; 60 link an electrolyte alongside a principal drug.
- **Fix:** add a component role (principal or electrolyte/vehicle) to the ingredient prompt and
  link only principals. The naming fix in item 2 removes the "anhydrous" names.
- **Rerun:** `fda link` → `drugs unii` → `approvals judge`.

## 4. Condition → disease mapping without trial context

- **Where:** `pipeline/indications.py:70–76, 93–98`.
- **Cause:** the mapper sees only the condition string. "SARS-CoV Infection" was mapped exactly to
  SARS. 16 strings map to SARS, covering 129 trials, 124 of which started after December 2019 and
  are COVID-19. Separately, NCT04388826 lists only "Respiratory Distress Syndrome, Adult";
  COVID-19 appears only in its title, which no program step reads.
- **Fix:**
  - Give the mapper each string's range of trial start years and two or three trial titles.
  - Add a prompt clause that SARS wording in trials from 2020 on means COVID-19.
  - Let `programs purposes` add the disease a trial's title names when the listed condition is
    only a complication of it.
- **Rerun:** `indications map`, then `programs` onward.

## 5. A broader-mapped condition starts its own program

- **Where:** `pipeline/indications.py:111–116, 166–176` (broader pass); `pipeline/programs.py:434–439, 549–552`.
- **Cause:** NCT02959918 lists "Gout Chronic" and "Hyperuricemia". MONDO's hyperuricemia term is
  obsolete, so "Hyperuricemia" was mapped to its parent, purine metabolism disease, which is not an
  ancestor of gout. Grouping an entity's diseases into indications only considers ancestor pairs
  (`programs.py:438`), so it never saw the pair, and `build` made two programs from one trial. One
  of them looks stopped, and that is how a program that went on to Phase 3 was recorded as failed.
  321 programs exist only because of a broader-mapped condition (286 at Phase 2+).
- **Fix:**
  - When the same trial has an exactly mapped disease, a broader-mapped condition attaches as
    `broader_condition` and does not seed a program.
  - Offer for grouping any two diseases that share one of the entity's trials, not only ancestor
    pairs.
- **Rerun:** `programs indications` → `programs build`, then `labels` and `evidence`.

## 6. Approval judgements

Code: `pipeline/approvals.py`:
- broader-class rule (31, 34)
- tumour-agnostic rule (34)
- date choice (35)
- date validator (77–81)

| Case | Cause | Fix |
| ---- | ----- | --- |
| rivaroxaban/PAD dated 2021-08-23, not 2018-10-11 | The 2018 efficacy supplement (NDA 202439 S-025) has no letter in Drugs@FDA, so it is never read (`fda.py:73–79`). The model knew the 2018 date, but the validator allows only listed events. 147 of 3,510 efficacy supplements since 2008 have no letter (133 for entities with programs). | Read the supplement's label or review when it has no letter. List every approved supplement date as an allowed answer. |
| dostarlimab/biliary "yes", /adrenal "uncertain" | The tumour-agnostic rule turns on whether the program's trials enrolled dMMR patients, but the prompt shows only condition strings (65). The model fell back on recollection. | Pass each program's trial titles and eligibility, or an extracted "biomarker required" field. |
| rituximab/liver lymphoma "uncertain"; fludarabine/immunoproliferative disorder "no" | The rules cover both cases; the model misapplied them, seeing only one level of MONDO parents. | Show the full ancestor chain and the approved use's histology. |
| plerixafor/B-cell CLL "yes" | No rule excludes supportive uses in a disease population (stem-cell mobilization in NHL patients is not treating NHL). | Add that rule. |

The prompt fixes change many judgements beyond the six audited:
- all 106 uncertain judgements (20 broader, 34 subtype, 49 none, 3 same);
- the 395 yes judgements reached through a broader class;
- the 133 yes-or-uncertain judgements that cite outside knowledge.

**Rerun:** `approvals judge`.

## 7. Publication outcomes judged without the registered primaries

- **Where:** the payload at `pipeline/outcomes.py:268–276`. The not-assessable rule (214–222) is
  already in the prompt.
- **Cause:** the payload carries the abstract but not the trial's registered primary outcomes, so
  the model cannot tell when they are descriptive safety or PK measures. ≈163 publication-derived
  met/mixed/not-met rows have a safety, PK or other primary.
- **Fix:** add the registered primary outcomes to the payload.
- **Rerun:** `outcomes classify`, then `stop_causes` and `attribution`.

## 8. Target-engagement endpoints classed blind to the drug

- **Where:** `pipeline/outcomes.py:303`. The prompt says "You are not told the drug", yet B1 (310)
  means the drug's own target or pathway.
- **Cause:** the model guessed the drug (a CFTR modulator, for a riociguat trial). None of the 193
  B1 labels can be trusted for the same reason.
- **Fix:** give the endpoint step the drug and its targets, or decide B1 against B2 in a second step
  that has them. The rest of the classification stays blind to the drug.
- **Rerun:** `outcomes endpoints`, then Section 3 and `attribution`.

## 9. Out of scope: trials registered only outside ClinicalTrials.gov

pruxelutamide's prostate cancer Phase 3s are on China's registry only. Its COVID-19 Phase 3s are on
ClinicalTrials.gov and are captured. The report's Limitations already cover registry coverage.

## Order of work

Fixes 1–5 sit upstream of every label, and any one of them forces a rebuild from `identity`
onward. So all code fixes land first, and the database is rebuilt once.

1. **Code and prompt changes, one PR per stage**, each with a dry run on the audited cases and a
   seeded sample. None writes to the database.
   - PR A, ingestion (fix 1).
   - PR B, entity resolution and FDA ingredients (fixes 2, 3).
   - PR C, disease mapping and program building (fixes 4, 5).
   - PR D, approvals (fix 6).
   - PR E, outcomes and endpoints (fixes 7, 8).
2. **One rebuild**, `make sources identity programs labels evidence`, announced to the other
   sessions first. It writes every shared table the report reads. Before starting, check which steps
   reuse earlier LLM decisions when input and prompt are unchanged; any step that does not
   re-decides every row.
3. **Re-audit** with fresh seeded samples for every label in the appendix audit table, plus the
   Section 3 case audit (`report.cases pending`). Add audit rows for the labels fixed here that
   were never audited: approval dates from letterless supplements, and B1 endpoints.
4. **Report:** `python -m report`, then reread every passage whose numbers moved. Two passages
   change regardless:
   - The appendix says remaining entity errors are "scattered rather than systematic". The salt
     and formulation findings in item 2 contradict that.
   - The Section 3 case paragraph lists the four outcome errors. Three of them (pegadricase,
     sabizabulin, eneboparatide) should be gone; pruxelutamide stays.

## Verification for each fix

| Fix | Check after the rebuild |
| --- | ----------------------- |
| 1 | NCT05778071 is in `preclin.ctgov_study` and marks eneboparatide's Phase 3 entry |
| 2 | Each audited drug string resolves to the auditor's entity; no linked code name contains `?`; the count of salt UNIIs with a parent drops to the legitimate salts |
| 3 | Extraneal links icodextrin only; no electrolyte is linked alongside a principal drug |
| 4 | No trial from 2020 on maps to MONDO:0005091 |
| 5 | pegadricase and sabizabulin each have one program for their gout and COVID-19 work; the 321-program pattern count falls to near zero |
| 6 | The six audited approvals match the auditor; rivaroxaban/PAD is dated 2018-10-11 |
| 7 | NCT01808638 is not assessable |
| 8 | NCT02170025 is B2; a B1 audit sample agrees |
