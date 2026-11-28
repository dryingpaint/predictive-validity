# Independent check of every prevalence code (2026-11-27)

A fresh reviewer, on the corrected profile (migration 178, `k-corrected`), graded the prevalence code of each of the 114 scored diseases and the 16 without a K against the Pan-UKB descriptions and the GBD cause names, reading the manifest, the GBD file, the hand map and MONDO's cross-references directly. We verified the two structural claims (no I10 in Pan-UKB's ICD-10 list; a descendant's three-character code beating the parent of another's four-character code) against the manifest. The registered profile and the corrected-K sensitivity are unchanged by this file; the rule v3 it argues for is proposed on #147 and runs only on Melissa's yes.


Checked every one of the 114 scored diseases and the 16 `no_k` against the Pan-UKB manifest (`.cache/panukb/phenotype_manifest.tsv.bgz`, icd10 and phecode rows), `pipeline/data/gbd_2023_prevalence_2021.csv` + `gbd_cause_mondo.csv`, and `preclin.ontology_xref` (MONDO). Every chosen code's description and every K was recomputed from source; all 114 match the table. "UKB comparator" below = Pan-UKB phecode or icd10 K for the same disease, cases/(cases+controls), EUR.

## (a) Summary over the 114

| Source | correct | defensible | doubtful | wrong | K off >5x (any grade) |
|---|---|---|---|---|---|
| Pan-UKB (64) | 21 | 26 | 10 | 7 | 15 |
| GBD (50) | 34 | 12 | 2 | 2 | 16 |
| Total (114) | 55 | 38 | 12 | 9 | 31 |

Verdict: the code identity is right or defensible for 93/114, but 9 are wrong, and 31 carry a K that is off by more than 5x for the cohort the GWAS came from. The two drivers are structural (section d), not one-offs: Pan-UKB's icd10 manifest lacks I10 and 18 other common codes, and MONDO carries ICD-9 but no ICD-10 xrefs for many common diseases, so the rule falls through to a descendant's narrow code.

## (b) Wrong or doubtful (code identity), plus K-magnitude flags

Pan-UKB. K = chosen K; cmp = UKB comparator (phecode unless noted).

| mondo_id | label | chosen (desc) | K | verdict | why | right code |
|---|---|---|---|---|---|---|
| MONDO:0005044 | hypertensive disorder | I12 Hypertensive renal disease | 0.0038 | **wrong** | I10 is absent from the icd10 manifest; I12 is renal HTN only; 59x under | phecode 401 Hypertension, K=0.225 |
| MONDO:0007263 | cardiac rhythm disease | I46 Cardiac arrest | 0.0032 | **wrong** | tier-3 descendant code; AF (I48, 19,218 cases) sat in tier 4 | phecode 427 Cardiac dysrhythmias 0.075 (or I48 0.046) |
| MONDO:0005009 | congestive heart failure | I27 Other pulmonary heart diseases | 0.0029 | **wrong** | no own ICD-10 xref (has ICD9:428); descendant = pulmonary hypertension | I50 Heart failure 0.0177 / phecode 428 0.0178 |
| MONDO:0043579 | enteritis | K29 Gastritis and duodenitis | 0.084 | **wrong** | stomach, not intestine; K driven by gastritis | K52 non-infective gastroenteritis 0.042 / phecode 558 0.049 |
| MONDO:0021178 | injury | T23 Burn of wrist and hand | 0.00045 | **wrong** | category term; only burns/frostbite carry xrefs; union of S/T block is >0.1 | phecode 1009 Injury NOS 0.021, or exclude category terms |
| MONDO:0005388 | primary biliary cholangitis | K74 Fibrosis and cirrhosis of liver | 0.0027 | **wrong** | parent = cirrhosis of any cause; 3.5x over the exact phecode | phecode 571.6 PBC 0.00077 |
| MONDO:0011849 | psoriatic arthritis | L40 Psoriasis | 0.0068 | **wrong** | parent is psoriasis (3x PsA) | phecode 696.42 0.0022 or M07 0.0014 |
| MONDO:0020673 | arterial occlusion | I65 Precerebral artery occlusion | 0.0030 | doubtful | one narrow site for a generic term | phecode 444 arterial embolism/thrombosis 0.0027 or define the term |
| MONDO:0004995 | cardiovascular disorder | I25 Chronic IHD | 0.074 | doubtful | own xref I00-I99; single code, I10 missing; union >0.3 | category: exclude, or phecode 401 as the dominant member |
| MONDO:0024317 | chronic pain syndrome | M79 Other soft tissue disorders | 0.0097 | doubtful | fibromyalgia's parent; G89 does not exist in UK ICD-10; chronic pain ~0.2-0.4 | literature K; no UKB code |
| MONDO:0005362 | erectile dysfunction | F52 Sexual dysfunction, non-organic | 0.0008 | doubtful | psychogenic subset; ED in men >40 ~0.2-0.4 | phecode 605 ED 0.0036 (male denominator) or literature K |
| MONDO:0005328 | eye disorder | H26 Other cataract | 0.045 | doubtful | category; cataract alone (phecode 366) is 0.066 | category: exclude |
| MONDO:0005570 | hematologic disorder | D64 Other anaemias | 0.035 | doubtful | own xref D50-D89; single code; D50+D64+D69+D68 alone ~0.07 | category: exclude |
| MONDO:0013600 | insomnia | G47 Sleep disorders | 0.0156 | doubtful | G47 is 85% sleep apnoea; coded insomnia 0.0006; true ~0.1-0.3 | phecode 327.4 Insomnia 0.00057 (still 100x under); literature K |
| MONDO:0005093 | skin disorder | C44 Other malignant neoplasms of skin | 0.034 | doubtful | category; skin cancer as proxy for all skin disease | category: exclude |
| MONDO:0002118 | urinary system disorder | N17 Acute renal failure | 0.018 | doubtful | category; N39 (23,043 cases) sat in tier 4 | category: exclude, or phecode 599 0.037 |
| MONDO:0001343 | impaired renal function disease | N25 Impaired renal tubular function | 0.00025 | doubtful | MONDO's own xref, so "correct", but 105 cases = the floor; if the GWAS is renal impairment, 100x under | phecode 585 Renal failure 0.033 |

Pan-UKB, code correct/defensible but K implausible (hospital-coded, primary-care disease): allergic rhinitis J30 0.0035 (true ~0.2); rosacea L71 0.0010 (~0.05); dental caries K02 0.0087 (GBD caries of permanent teeth 0.28); essential tremor G25 0.0022 (~0.01-0.04); restless legs G25 0.0022 (~0.05-0.1); atopic conjunctivitis H10 0.0008; blepharitis H01 0.0018; dry eye H04 0.0064; CKD N18 0.018 (eGFR-defined ~0.1); HCM I42 0.0040 (phecode 425.11+425.12 = 0.0009, 4x over); Barrett K22 0.029 (~3x over).

GBD. cmp = UKB phecode K for the same disease.

| mondo_id | label | cause | K | verdict | why | right choice |
|---|---|---|---|---|---|---|
| MONDO:0005364 | Graves disease | Thyroid diseases (broader) | 0.053 | **wrong** | bucket is hypothyroidism/goitre; Graves phecode 242.1 = 0.0014 (38x) | phecode 242.1, or 242 thyrotoxicosis 0.0057 |
| MONDO:0004891 | hyperopia | Refraction disorders (broader) | 0.016 | **wrong** | GBD counts vision loss from uncorrected refractive error; hyperopia itself ~0.1-0.3 | literature K; no UKB code |
| MONDO:0006626 | diabetic neuropathy | Diabetes mellitus type 2 (broader) | 0.066 | doubtful | the parent disease, not the complication; coded DPN (250.6) 0.0013; true ~0.02-0.03 | literature K (~0.025) |
| MONDO:0001330 | presbyopia | Near vision loss (exact) | 0.069 | doubtful | GBD near vision loss = uncorrected presbyopia; presbyopia ~0.2+ all ages | literature K |
| MONDO:0005011 | Crohn disease | Crohn's disease | 0.00017 | correct, K 36x under | global vs UK: phecode 555.1 = 0.0060 | K50 0.0047 / 555.1 |
| MONDO:0005101 | ulcerative colitis | Ulcerative colitis | 0.00030 | correct, K 36x under | phecode 555.2 = 0.011 | K51 0.0086 / 555.2 |
| MONDO:0004646 | decubitus ulcer | Decubitus ulcer | 0.000076 | correct, K 46x under | point prevalence; L89 = 0.0035 | L89 |
| MONDO:0008171 | nephrolithiasis | Urolithiasis | 0.00051 | correct, K 35x under | point vs ever; phecode 594 = 0.018 | N20 0.013 / 594 |
| MONDO:0005041 | glaucoma | Glaucoma | 0.00083 | correct, K 18x under | GBD = vision loss due to glaucoma; H40 = 0.0147 | H40 / phecode 365 0.015 |
| MONDO:0005338 | open-angle glaucoma | Glaucoma (broader) | 0.00083 | defensible, K 4.5x under | phecode 365.1 = 0.0037 | 365.1 |
| MONDO:0005129 | cataract | Cataract | 0.0126 | correct, K 5x under | GBD = vision-impairing cataract; phecode 366 = 0.066 | 366 / H25+H26 |
| MONDO:0005081 | preeclampsia | Maternal hypertensive disorders | 0.00037 | defensible, K ~100x under | point prevalence over both sexes, all ages; lifetime in parous women 0.03-0.05 | phecode 642.1 0.0014 (women) or literature |
| MONDO:0005133 | endometriosis | Endometriosis | 0.0025 | correct, K 8x under | both-sex all-age denominator; phecode 615 = 0.020 (women) | 615 |
| MONDO:0010811 | benign prostatic hyperplasia | BPH | 0.014 | correct, K 5x under | both-sex denominator; phecode 600 = 0.077 (men) | 600 |
| MONDO:0004981 | atrial fibrillation | AF and flutter | 0.0071 | correct, K 6.7x under | global all-age vs cohort aged 40-70; phecode 427.2 = 0.048 | I48 / 427.2 |
| MONDO:0008383 | rheumatoid arthritis | RA | 0.0023 | correct, K 6.5x under | phecode 714.1 = 0.0147 | M06 / 714.1 |
| MONDO:0005147 | type 1 diabetes | T1D | 0.0010 | correct, K ~5x under | UK T1D ~0.4-0.5%; phecode 250.1 = 0.0081 | E10 0.0077 |
| MONDO:0006515 | acute pancreatitis | Pancreatitis (broader) | 0.00076 | defensible, K 7.5x under | point vs ever; phecode 577.1 = 0.0057 | K85 |
| MONDO:0001356 | iron deficiency anemia | Dietary iron deficiency | 0.179 | defensible, K 7x over | global burden; UK D50 / phecode 280 = 0.025 | D50 |
| MONDO:0011438 | acne | Acne vulgaris | 0.0065 | correct, K doubtful | all-age point prevalence of an adolescent disease; acne GWAS use self-report severe acne K ~0.1 | literature K |

Both-sex denominators also halve K for uterine fibroids (0.015 vs phecode 218.1 0.051 in women) and female infertility; MDD/anxiety/bipolar are point not lifetime prevalence (MDD 0.029 vs the 0.15 convention). Not graded wrong, but note for h2_liab.

## (c) `no_k` diseases: a usable code exists for all 16

MONDO has no ICD-10 xref for any of them but an ICD-9 xref for 11, and Pan-UKB phecodes are numbered from ICD-9, so the match is direct. phecode / icd10 alternatives (K, EUR):

| disease | MONDO ICD9 xref | phecode (K) | icd10 (K) |
|---|---|---|---|
| essential hypertension | 401, 401.9 | 401.1 Essential hypertension (0.224) | I10 absent from manifest |
| obesity disorder | 278.0 | 278.1 Obesity (0.038); note BMI>=30 GWAS use K~0.25 | E66 (0.038) |
| hemorrhoid | 455 | 455 Hemorrhoids (0.066) | I84 (0.063); K64 (0.0072) |
| ptosis | 374.3 | 374.3 Ptosis of eyelid (0.0055) | H02 (0.016, parent) |
| hypoglycemia | 251.1 | 251.1 Hypoglycemia (0.0033) | E16 (0.0031) |
| diabetic retinopathy | 362.0 | 250.7 Diabetic retinopathy (0.0042) | H36 (0.0041) |
| androgenetic alopecia | 704.09 | 704.1 Alopecia (0.00045) | L64 absent |
| intervertebral disk degeneration | 722.6 | 722 Intervertebral disc disorders (0.020) | M51 (0.022) |
| diastolic / systolic heart failure | 428.3 / 428.2 | 428 CHF (0.018, parent) | I50 (0.018) |
| dyspepsia | (ICD10CM K30 present) | 536 Disorders of function of stomach (0.0008) | K30 absent |
| abdominal aortic aneurysm | none | 442.11 AAA (0.0032) | I71 (0.0048) |
| venous thromboembolism | none | 451 (0.013) + 452 (0.0019); no union code | I26 0.011 + I80 0.011 + I82 0.0012 |
| hip fracture | none | 800.1 Fracture of neck of femur (0.0049) | S72 (0.0008) |
| bone fracture | none | 800/803/804/805/819 (0.02-0.03 each); category | S-block; category |
| spinal cord injury | none | 952 (0.00036) | S14 (0.00027) |

GBD offers nothing for these (no hypertension, obesity, AAA or fracture prevalence cause in the file).

## (d) Systematic problems and fixes

1. **Pan-UKB icd10 manifest (921 codes) is missing common 3-character codes**: of those probed, I10, G20, L20, N40, K30, L64, L97, N19, I64, I13, D53, D62, D70, K20, O13, S24, S34 are absent (and B50/D56/D57 have no EUR counts). Affects hypertensive disorder (wrong), essential hypertension, dyspepsia, androgenetic alopecia (no_k), cardiovascular disorder (I10 would be the top code). Fix: add a phecode tier. Match MONDO ICD9 xrefs to Pan-UKB `trait_type == "phecode"` by exact string, then by integer part (401.9 -> 401); prefer a phecode exact match over a 3-character ICD parent.
2. **MONDO ICD-10 xref coverage is thin** (2,205 ICD10CM vs 5,658 ICD9 xrefs), and the rule has no ancestor tier, so a disease with no own code drops to a descendant's narrow code: CHF (I27), cardiac rhythm disease (I46), enteritis (K29), injury (T23), skin disorder (C44), urinary system disorder (N17), arterial occlusion (I65), anemia (D50), kidney failure (N17), chronic ulcer of skin (L89). Fix: tier order own -> own parents -> ICD9-matched phecode -> nearest MONDO ancestor's codes (one level) -> descendants.
3. **Tier 3 beats tier 4 on an accident of MONDO's code length**: a descendant's 3-character code wins over the parent of another descendant's 4-character code. Cardiac rhythm disease: I46 (1,349) beat I48 (19,218, via I480); anemia: D50 (10,483) beat D64 (14,551, via D644); urinary system disorder: N17 (7,727) beat N39 (23,043, via N390). Fix: pool tiers 3 and 4.
4. **Category-level MONDO terms get a single member's K**: cardiovascular disorder, eye disorder, skin disorder, hematologic disorder, urinary system disorder, injury, bone fracture; range xrefs behave the same (I00-I99 -> I25; D50-D89 -> D64; M15-M19 -> M17 0.059 vs phecode 740 osteoarthrosis 0.086; E10-E14 -> E11 0.054 vs phecode 250 0.058, immaterial). Fix: when own codes are a range or the term has >20 descendant codes, use the phecode parent that is the union (401, 427, 285, 740, 250) or mark the disease category and exclude it from the liability conversion.
5. **Parent-code tier inflates rare subtypes** when the exact phecode exists: PBC (K74 3.5x), PsA (L40 3x), HCM (I42 4x), insomnia (G47 28x), essential tremor (G25 2.5x), Graves (GBD thyroid 38x). Fix: phecode exact match before 3-character parent (same as fix 1).
6. **GBD global, both-sex, all-age point prevalence is the wrong K for a European lifetime-diagnosis GWAS** for 16 of 50: IBD (36x), decubitus ulcer (46x), urolithiasis (35x), glaucoma (18x), cataract (5x), acute pancreatitis (7.5x), AF (6.7x), RA (6.5x), T1D (5x), preeclampsia (~100x), endometriosis (8x), BPH (5x), fibroids (3x), IDA (7x over), Graves (38x over), diabetic neuropathy. Fix: (i) take GBD only when no Pan-UKB code with >=1,000 cases exists for the same disease, or (ii) re-export GBD for the Western Europe / high-income location instead of Global, and (iii) use sex-specific denominators for sex-limited diseases (phecodes 600, 615, 218.1, 642.1, 605 already do).
7. **Hospital-coded ICD-10 K under-ascertains primary-care and self-report conditions by 10-100x**: allergic rhinitis, rosacea, ED, dental caries, essential tremor, RLS, insomnia, chronic pain, atopic conjunctivitis, blepharitis, dry eye, CKD, hearing loss (if ever coded). The GWAS for these are mostly self-report (23andMe/UKB questionnaire), so P and K disagree in kind. Fix: a small hand-curated literature K table for these (~15 entries), applied before Pan-UKB; otherwise report h2_liab for them as "coded-K, lower bound".
8. Minor: no K reached the 0.5 cap in either source (checked), so that gate never fired; `expand_icd` cannot expand a cross-letter range (none present in the 531).
