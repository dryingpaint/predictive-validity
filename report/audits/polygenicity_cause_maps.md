# Cause-to-MONDO maps: GBD 2021 prevalence causes and WHO GHE 2021 DALY causes

Built 2026-11-23 for issue #147. Inputs: 299 GBD causes (IHME-GBD_2023_DATA-3ed44f89-1.csv), 214 WHO GHE causes
(who_ghe_2021_global_dalys.csv), burden.py MAP (85 rows), 594 P2 diseases minus 63 infectious = 531 candidates, MONDO from
preclin.ontology_term / ontology_ancestor / ontology_xref (read-only; 36,055 terms, 3,921 obsolete). Builder and the local
MONDO extracts sit in `cm_work/` next to this file (`build_maps.py` holds every decision as data; `lib.py` the MONDO helpers).

## Counts

| table | rows | causes | causes with a disease | none rows | candidates exact | candidates broader | candidates unmatched |
|---|---|---|---|---|---|---|---|
| GBD (`gbd_cause_mondo.csv`) | 386 | 299 | 197 | 102 | 48 | 87 | 396 |
| WHO (`who_ghe_cause_mondo.csv`) | 328 | 214 | 136 | 78 | 32 | 80 | 419 |

Validation (run in code at the end of `build_maps.py` and again from the written CSVs): headers exact; every one of the 299
and 214 causes present; every mondo_id resolves to a live MONDO term; no candidate under two causes in either table; a
`none` row never shares its cause with another row.

## burden.py agreement

MAP has 23 exact, 11 broader, 13 shared, 38 none diseases (37 exact/broader cause pairs, 13 shared pairs). Checked in
code: all 37 exact/broader pairs are present with the same code, mondo_id and relation; all 13 shared pairs are recorded as
`broader` under the cause the other disease holds; none of the 38 `none` diseases appears anywhere in the WHO table.
Consequences carried through: psoriasis, atopic eczema, acne and the other skin candidates get no WHO cause (Skin diseases
is an aggregate); endometriosis, PCOS and dysmenorrhea get none (Gynecological diseases is an aggregate); GERD, IBS and the
other K20-K92 leftovers get none (Other digestive); DME and the diabetic retinopathies get none (Other vision loss).

## Method

1. Exact label or synonym match of each cause name against live MONDO terms.
2. ICD-10: the candidates' `icd10` column and MONDO `ICD10CM`/`ICD10WHO` xrefs, against the cause code ranges. For WHO the
   code ranges are verified against Annex Table A of the WHO GHE 2021 DALY methods paper
   (ghe2021_daly_methods.pdf, text in `cm_work/who_ghe_methods.txt`). The GBD 2021 nonfatal ICD map on GHDx needs a
   login and could not be fetched; GBD-specific inclusions rest on the published GBD case definitions and are flagged below
   where they carry a decision.
3. MONDO ancestor relation to decide `broader` (child in parent); where MONDO does not nest a pair that ICD or the cause
   definition clearly does (coronary artery disease in I20-I25, FSGS in the glomerulonephritis bucket, Kennedy disease in
   G12), the note says so.
4. Every written id was printed with its MONDO label and read (`cm_work/build_log.txt`).

Rules applied: residual "Other ..." causes never match; aggregates ("Total ...", group rows, injuries) get `none`; a
disease split across several causes (osteoarthritis, dental caries, CKD, cirrhosis, diabetes mellitus, depressive disorder,
stroke in GBD) is left unmatched rather than forced under one part, and the parts are named in the notes so downstream code
can sum them if it wants to. Candidates are recorded in GBD under the narrowest cause that truly contains them.

## GBD: the 15 unmatched candidates with the most entries

| mondo_id | label | entries | why |
|---|---|---|---|
| MONDO:0006733 | dry eye syndrome | 40 | only the Other sense organ diseases residual |
| MONDO:0009061 | cystic fibrosis | 29 | no cause in the 299 (sits in Other chronic respiratory, not in the extract) |
| MONDO:0007915 | systemic lupus erythematosus | 28 | M32 is in Other musculoskeletal disorders (residual) |
| MONDO:0021187 | hyperlipidemia | 19 | risk factor, not a cause |
| MONDO:0004728 | diabetic macular edema | 18 | GBD models it as vision loss from diabetic retinopathy, a diabetes sequela; owner put it in Other vision loss for WHO |
| MONDO:0011122 | obesity disorder | 17 | risk factor (high BMI), not a cause |
| MONDO:0006559 | hidradenitis suppurativa | 17 | Other skin and subcutaneous diseases (residual) |
| MONDO:0005252 | heart failure | 17 | GBD impairment, not a cause; no single cause contains it |
| MONDO:0010679 | Duchenne muscular dystrophy | 16 | Other neurological disorders (residual) |
| MONDO:0005178 | osteoarthritis | 15 | split across hip 1014, knee 1015, hand 1016, other 1017; sum them |
| MONDO:0005052 | irritable bowel syndrome | 13 | Other digestive diseases (residual) |
| MONDO:0010602 | hemophilia A | 13 | Other endocrine, metabolic, blood and immune (residual) |
| MONDO:0004605 | chronic ulcer of skin | 13 | Other skin (residual); its child decubitus ulcer is the separate cause 665 |
| MONDO:0041052 | postherpetic neuralgia | 13 | sequela of herpes zoster; the varicella and zoster cause (342) models acute infection |
| MONDO:0010030 | Sjogren syndrome | 12 | Other musculoskeletal (residual) |

Also unmatched and worth knowing: epilepsy (8; see least-sure 1), CKD (8; split across 591, 592, 593, 997, 998),
diabetes mellitus (3; 975 + 976), cirrhosis of liver (3; 522-525 + 971), depressive disorder (9; 568 + 569), stroke
disorder (9; 495-497), dental caries (3; 681 + 682), psoriatic arthritis (6; see least-sure list), pulmonary hypertension
(4; GBD PAH is group 1 only), interstitial cystitis (6), nicotine dependence (3; tobacco is a risk factor).

## WHO: the 15 unmatched candidates with the most entries

| mondo_id | label | entries | why |
|---|---|---|---|
| MONDO:0004980 | atopic eczema | 48 | Skin diseases aggregate (burden.py none) |
| MONDO:0005083 | psoriasis | 43 | Skin diseases aggregate (burden.py none) |
| MONDO:0006733 | dry eye syndrome | 40 | Other sense organ disorders (residual; burden.py none) |
| MONDO:0009061 | cystic fibrosis | 29 | Other respiratory diseases (residual; burden.py none) |
| MONDO:0007915 | systemic lupus erythematosus | 28 | Other musculoskeletal (residual; burden.py none) |
| MONDO:0011438 | acne | 28 | Skin diseases aggregate |
| MONDO:0021187 | hyperlipidemia | 19 | risk factor (burden.py none) |
| MONDO:0800504 | idiopathic pulmonary fibrosis | 18 | J84 is in Other respiratory diseases (residual) |
| MONDO:0004728 | diabetic macular edema | 18 | Other vision loss (burden.py none) |
| MONDO:0005252 | heart failure | 17 | I50 is in Other circulatory diseases (residual) |
| MONDO:0011122 | obesity disorder | 17 | risk factor |
| MONDO:0006559 | hidradenitis suppurativa | 17 | Skin diseases aggregate |
| MONDO:0010679 | Duchenne muscular dystrophy | 16 | Other neurological (residual; burden.py none) |
| MONDO:0004976 | amyotrophic lateral sclerosis | 16 | G12.2 is in Other neurological conditions (residual) |
| MONDO:0005052 | irritable bowel syndrome | 13 | K58.0 sits in Inflammatory bowel disease and K58.9 in Other digestive; overlap only |

Also: hearing loss disorder (2) and sensorineural hearing loss (3) are unmatched because Other hearing loss (1080) is a
residual row by name (see least-sure 3); CKD (8) because Other chronic kidney disease (1273) is residual and Kidney
diseases (1270) is a group row; PAH (12), AF (7), PAD (10) because they sit in Other circulatory; uterine fibroids and
PCOS because D25 is in Other neoplasms and E28.2 in Other endocrine.

## The ten mappings I was least sure of

1. **epilepsy MONDO:0005027, GBD: unmatched.** GBD's only epilepsy cause is Idiopathic epilepsy (545), which excludes
   secondary epilepsy (attributed to stroke, injury, infection). Alternative: record 545 as `exact` for epilepsy; the WHO
   table does record Epilepsy (970, G40-G41) as exact. Candidates placed as broader under 545 (photosensitive, Dravet, DEE9)
   rest on GBD counting genetic epilepsies as idiopathic; Lennox-Gastaut, infantile spasms and focal epilepsy were left out
   because much of each is structural.
2. **diabetic neuropathy MONDO:0006626: GBD 976 broader, WHO 800 broader.** GBD models it as a sequela of diabetes type 1
   and type 2, so the type-2 placement mirrors the task's diabetic kidney disease convention; WHO's Diabetes mellitus
   includes E10.4-E14.4. Alternative: unmatched in both, as was done for diabetic retinopathy and DME (following burden.py's
   Other vision loss call for DME).
3. **hearing loss disorder MONDO:0005365: GBD 674 exact, WHO 1080 none.** GBD's "Age-related and other hearing loss" is
   H90-H91 and the only hearing-loss cause; WHO's "Other hearing loss" is the same H90-H91 but starts with "Other", so the
   residual rule left it out. Alternative: WHO 1080 exact (and sensorineural hearing loss broader), which is what the ICD
   range says.
4. **ankylosing spondylitis MONDO:0005306: WHO 1380 broader.** The WHO GHE annex codes M45 to Back and neck pain
   (M45-M48, M50-M54). Clinically it belongs with the other spondyloarthritides in Other musculoskeletal. Alternative:
   unmatched. Spondyloarthropathy itself was left out (spans M45-M46 and M02/M07).
5. **presbyopia MONDO:0001330: GBD 1000 Near vision loss exact.** The cause is vision impairment from uncorrected
   presbyopia, so it understates total presbyopia. Alternative: unmatched (the relation vocabulary has no "narrower").
   The same caveat applies to refractive error under 999.
6. **achondroplasia, osteogenesis imperfecta, hereditary multiple osteochondromas (GBD 649 broader) and Alagille
   syndrome (GBD 651 broader).** Placed by ICD block (Q65-Q79, Q38-Q45); GBD's modelled prevalence for these causes is
   dominated by structural limb, hip, foot and gut anomalies. Alternative: unmatched.
7. **primary sclerosing cholangitis MONDO:0013433: GBD 534 and WHO 1246 broader.** K83.01 sits inside K80-K83, but both
   causes are mostly gallstone disease. Alternative: unmatched, as PBC is (its K74.3 sits in cirrhosis residuals).
8. **lupus nephritis, IgA nephropathy, FSGS, primary FSGS, membranous nephropathy, C3 glomerulopathy: GBD 592 "CKD due
   to glomerulonephritis" broader.** Honest only insofar as persistent proteinuria is CKD by the KDIGO definition GBD uses;
   nephrotic syndrome was left out because it also arises from diabetic kidney disease. GBD's attribution of lupus nephritis
   (N08.5*) to the glomerulonephritis rather than the "other" bucket could not be verified. Alternative: unmatched.
9. **macular degeneration MONDO:0003004: WHO 1060 exact alongside AMD exact.** H35.3 is all macular degeneration; AMD is
   nearly all of it and burden.py records AMD as exact, so both are exact. Alternative: drop MONDO:0003004 (GBD 672 is
   age-related only, so it is unmatched there).
10. **endocrine exophthalmos (thyroid eye disease) MONDO:0001509: GBD 1032 Thyroid diseases broader.** Coded through its
    Graves disease dagger code E05.0; MONDO files it as an orbital disease. Alternative: unmatched (it is unmatched in WHO,
    where E05 sits in Other endocrine).

Runners-up: psoriatic arthritis left unmatched in GBD although L40.5 is inside L40 (alternative 655 broader); MASLD under
WHO 1234 broader on the same cirrhosis-attribution basis as burden.py's MASH entry (alternative unmatched, since
non-cirrhotic MASLD is K76.0 in Other digestive); malignant skin melanoma recorded as MONDO:0005105 melanoma to match
burden.py rather than MONDO:0005012 cutaneous melanoma (C43); OCD and PTSD under GBD Anxiety disorders rest on the GBD case
definition (verified for WHO: F40-F44); retinopathy of prematurity under GBD 381 rests on GBD listing it as a preterm-birth
sequela (not recorded for WHO, where H35.1 is Other vision loss); coronary microvascular disorder under ischaemic heart
disease rests on ICD-10-CM I20.81/I21.B; interstitial cystitis left unmatched although N30.1 is inside the GBD UTI code
range.

## Files

- `/private/tmp/claude-503/-Users-stephengoldstein-Library-Mobile-Documents-com-apple-CloudDocs-Capable/9e5fd4bb-064f-4793-af2a-572f0ae49f8a/scratchpad/gbd_cause_mondo.csv`
- `/private/tmp/claude-503/-Users-stephengoldstein-Library-Mobile-Documents-com-apple-CloudDocs-Capable/9e5fd4bb-064f-4793-af2a-572f0ae49f8a/scratchpad/who_ghe_cause_mondo.csv`
- `/private/tmp/claude-503/-Users-stephengoldstein-Library-Mobile-Documents-com-apple-CloudDocs-Capable/9e5fd4bb-064f-4793-af2a-572f0ae49f8a/scratchpad/cause_maps_notes.md` (this file)
- builder, MONDO extracts (~40 MB, delete when done) and logs: `.../scratchpad/cm_work/`
