# Independent check of rule v3's prevalence codes (2026-11-28)

The same fresh-reviewer check as `polygenicity_k_code_check.md`, run on the 114 diseases scored under rule v3 (migration 181, `k-rules`) the night it was built. Verdict: v3 fixes 11 of the earlier 21 flagged diseases and most GBD magnitude problems, but grades worse overall (23 wrong, 13 doubtful) because its ICD-9-to-phecode matching by number is not a mapping and its most-cases rule prefers the broadest code; it also drops glaucoma, hypertensive disorder and cardiomyopathy as chapter terms. v3 is reported in the appendix as run and is not recommended; the fixes it argues for (the published ICD-to-phecode maps, specificity before case count, parents pooled from the start, no ICD-9 range expansion, an own exact code overriding the category rule, descendants' own codes only, a literature-K table) are proposed on #147 and run only on a ruling there.


All 124 rows of `k_v3_for_review.csv` were re-derived with the pipeline's own functions (`k_for_v3`, `is_category`, `phecode_matches`, read-only) and every chosen code, description, case count and K was checked against the Pan-UKB manifest, MONDO xrefs (`preclin.ontology_xref`) and the GBD file. All 124 reproduce exactly. Grading conventions as in `k_codes_review.md`: a parent bucket >=3x off the disease's own code (when that code has >=1,000 cases or is the only exact code) is wrong; 2-3x or an under-coded exact (<1,000) is doubtful; <2x defensible. K flag = >5x off a European lifetime-diagnosis GWAS K.

Caveat: the `k_code` ("registered") columns in this CSV differ from the earlier report for 8 terms (hypertensive disorder H40, cardiomyopathy/cardiovascular/eye/hematologic E78, urinary N81, injury T20, ED N48). Not graded; the earlier report's registered codes were used for (c).

## (a) Summary over the 114 scored under v3

| Source | correct | defensible | doubtful | wrong | K off >5x (any grade) |
|---|---|---|---|---|---|
| Pan-UKB (107) | 47 | 25 | 12 | 23 | 25 |
| GBD (7) | 5 | 1 | 1 | 0 | 0 |
| Total (114) | 52 | 26 | 13 | 23 | 25 |

Verdict: v3 fixed 5 of the earlier 9 wrong and 6 of the 12 doubtful, and repaired most of the GBD K-magnitude problems (IBD, cataract, AF, RA, T1D, endometriosis, BPH, fibroids, IDA, Graves), but it introduced 19 new wrong or doubtful codes, so code identity is worse than before (36 vs 21 flagged). The cause is one design choice: ICD-9 -> phecode by integer part (and exact string) is not a mapping, phecode numbers only loosely follow ICD-9, and "most cases wins" then picks the broadest bucket in the pool.

## (b) Wrong or doubtful under v3

| mondo_id | label | chosen (desc) | K | verdict | why | right code (K) |
|---|---|---|---|---|---|---|
| MONDO:0001106 | kidney failure | 586 Other disorders of kidney and ureters | 0.0107 | **wrong** | ICD-9 586 = renal failure NOS; phecode 586 is a different bucket | 585 Renal failure (0.033) |
| MONDO:0002203 | constipation disorder | 564 Functional digestive disorders | 0.106 | **wrong** | grab-bag (IBS 7k, "personal history" 20k); 3.0x over own K59 (14,578 cases) which lost on case count | K59 (0.035) |
| MONDO:0004976 | ALS | 335 Multiple sclerosis | 0.0038 | **wrong** | ICD-9 335.20 -> integer 335 = MS; no ALS phecode in Pan-UKB | G12 (0.00083, 350 cases) or literature 0.0025 |
| MONDO:0005002 | COPD | 495 Asthma | 0.076 | **wrong** | ICD-9 range 490-496 expanded into the pool; asthma out-counts 496 | 496 Chronic airway obstruction (0.036) |
| MONDO:0005130 | celiac disease | 579 Other symptoms involving abdomen | 0.0088 | **wrong** | ICD-9 579.0 -> 579; phecode 579 is symptoms | 557.1 Celiac disease (0.0066) or K90 |
| MONDO:0000728 | ptosis (new) | 374 Other disorders of eyelids | 0.0163 | **wrong** | 374.3 Ptosis (2,257 cases) was in the pool and lost on cases; 3.0x | 374.3 (0.0055) |
| MONDO:0005266 | diabetic retinopathy (new) | 362 Other retinal disorders | 0.0161 | **wrong** | AMD-dominated bucket; 3.8x over 250.7 (1,709 cases) | 250.7 Diabetic retinopathy (0.0042) |
| MONDO:0005296 | sleep apnea syndrome | 780 Hypothermia/Chills | 0.0006 | **wrong** | ICD-9 780.57 -> 780; own G47.3 is 4-char so G47 never pooled; K flag | 327.3 Sleep apnea (0.0134) or G47 |
| MONDO:0005469 | orthostatic hypotension | 458 Hypotension | 0.0208 | **wrong** | 4.0x over 458.1 (2,032 cases) | 458.1 Orthostatic hypotension (0.0051) |
| MONDO:0006031 | chronic rhinosinusitis | 473 Diseases of the larynx and vocal cords | 0.0076 | **wrong** | ICD-9 473 = chronic sinusitis; phecode 473 = larynx | 475 Chronic sinusitis (0.0075) or J32 |
| MONDO:0007263 | cardiac rhythm disease | 427.9 Palpitations | 0.0119 | **wrong** | exact-string collision: ICD-9 427.9 dysrhythmia NOS vs phecode 427.9 palpitations | 427 Cardiac dysrhythmias (0.075) |
| MONDO:0007915 | SLE | 710 Osteomyelitis and bone infections | 0.0021 | **wrong** | ICD-9 710.0 -> 710 = osteomyelitis; own M32 lost on cases | M32 (0.00098) or 695.42 |
| MONDO:0008171 | nephrolithiasis | 592 Cystitis and urethritis | 0.0098 | **wrong** | ICD-9 592 calculus -> phecode 592 cystitis | 594 Urinary calculus (0.018) or N20 (0.013) |
| MONDO:0008364 | Raynaud disease | 443 Peripheral vascular disease | 0.0122 | **wrong** | 3.3x over 443.1 (1,510 cases) | 443.1 Raynaud's (0.0037) |
| MONDO:0011438 | acne | 706 Diseases of sebaceous glands | 0.0234 | **wrong** | 9,745 of 9,834 cases are 706.2 sebaceous cyst; no acne phecode, L70 absent | GBD 0.0065 (registered) or literature |
| MONDO:0011786 | allergic rhinitis | 477 Epistaxis or throat hemorrhage | 0.0074 | **wrong** | ICD-9 477 -> phecode 477 epistaxis | 476 Allergic rhinitis (0.0038) / J30; K flag (true ~0.2) |
| MONDO:0011849 | psoriatic arthritis | 696 Psoriasis and related disorders | 0.0073 | **wrong** | still the psoriasis bucket; 3.3x over 696.42 (887 cases) | 696.42 (0.0022) |
| MONDO:0013209 | MASLD | 571.8 Liver abscess and sequelae of chronic liver disease | 0.0034 | **wrong** | ICD-9 571.8 (NAFLD) != phecode 571.8 (abscess, portal HTN) | 571.5 (0.0059) or GBD 0.155; K flag |
| MONDO:0013600 | insomnia | 780 Hypothermia/Chills | 0.0006 | **wrong** | ICD-9 780.52 -> 780; G47.0 4-char never pooled | 327.4 (0.00057) or literature 0.1-0.3; K flag |
| MONDO:0013662 | Barrett esophagus | 530 Diseases of esophagus | 0.104 | **wrong** | GERD-dominated bucket; 3.6x over own K22 (12,256 cases) | K22 (0.029) |
| MONDO:0021124 | female infertility | 628 Ovarian cyst (F) | 0.0265 | **wrong** | ICD-9 628 infertility -> phecode 628 ovarian cyst; N97 has 989 cases (11 short of 1,000) | 626.8 Infertility, female (0.0073, F) or N97 |
| MONDO:0021178 | injury | T23 Burn of wrist and hand | 0.00045 | **wrong** | category term, 9 descendant codes so the category rule misses it | exclude, or 1009 Injury NOS (0.021) |
| MONDO:0043579 | enteritis | 535 Gastritis and duodenitis | 0.086 | **wrong** | descendant tier pools parents of descendants (duodenitis -> 535) | 558 Noninfectious gastroenteritis (0.049) or K52 |
| MONDO:0001330 | presbyopia | 367 Disorders of refraction | 0.0089 | doubtful | myopia-dominated bucket, presbyopia not coded; K flag (true >=0.2) | literature K |
| MONDO:0001343 | impaired renal function disease | 588 Impaired renal function | 0.0003 | doubtful | exact ICD-9 category but 120 cases; K flag if GWAS = renal impairment | 585 (0.033) or define term |
| MONDO:0002009 | major depressive disorder | 296 Mood disorders | 0.0049 | doubtful | hospital bucket incl. bipolar; 7.6x under F32, 30x under 0.15 convention; K flag; registered GBD 0.029 was better | F32 (0.037) or literature 0.15 |
| MONDO:0004891 | hyperopia | 367 Disorders of refraction | 0.0089 | doubtful | bucket; 367.8 Hypermetropia (345 cases, 0.00083) exists but numbering differs; K flag | literature K |
| MONDO:0005045 | hypertrophic cardiomyopathy | 425 Cardiomyopathy | 0.0040 | doubtful | 4.4x over 425.11+425.12 (0.0009), which are under-coded; K ~2x true 0.002 | 425.11+425.12 or literature 0.002 |
| MONDO:0005081 | preeclampsia | 642 Hypertension in pregnancy (F) | 0.0053 | doubtful | 3.8x over 642.1 (319 cases); K flag (lifetime in parous women 0.03-0.05) | 642.1 or literature |
| MONDO:0005338 | open-angle glaucoma | 365 Glaucoma | 0.0151 | doubtful | 4.1x over 365.1 (1,498 cases, in the pool, lost on cases); unspecified glaucoma is mostly POAG | 365.1 (0.0037) |
| MONDO:0005339 | androgenetic alopecia (new) | 704 Diseases of hair and hair follicles | 0.0140 | doubtful | bucket; 704.1 Alopecia 187 cases; K flag (AGA ~0.3+ in men) | literature K |
| MONDO:0005362 | erectile dysfunction | F52 Sexual dysfunction, non-organic | 0.0008 | doubtful | psychogenic subset; 605 ED (603 males, 0.0036) and N48 (2,448) ignored; K flag | 605 (males) or literature |
| MONDO:0005391 | restless legs syndrome | 333 Extrapyramidal and movement disorders | 0.0032 | doubtful | no RLS phecode; bucket; K flag (0.05-0.1) | literature K |
| MONDO:0005642 | atopic conjunctivitis | 372 Disorders of conjunctiva | 0.0023 | doubtful | 2.8x over H10; K flag (0.1-0.2) | literature K |
| MONDO:0020673 | arterial occlusion | 433 Cerebrovascular disease | 0.027 | doubtful | generic term scored on the cerebrovascular bucket (via descendants) | define the term |
| MONDO:0006626 | diabetic neuropathy (GBD) | T2D (broader) | 0.066 | doubtful | unchanged; 250.6 (517 cases, 0.0013) lost to the 1,000 rule | 250.6 or literature 0.025 |

Code correct/defensible but K off >5x: essential tremor 333.1 (0.00085), blepharitis H01 (0.0018), Alzheimer 290.1 (0.0048 vs ~0.05), periodontitis 523 (0.005 vs 0.1-0.4), dental caries 521 (0.009), **migraine G43 (0.0085; registered GBD 0.144 was right, 17x worse)**, **hearing loss 389 (0.014; GBD 0.205, 14x worse)**, rosacea 695.3, dry eye 375, obesity 278 (0.038 vs BMI>=30 GWAS 0.25), headache disorder 339 (0.023 vs ~0.5), chronic pain 338 (0.0022).

Defensible picks worth noting (parent bucket <2x, exact available): decubitus 707 over L89/707.1 (1.9x); AF 427 over 427.2/I48 (1.6x); CKD 585 over 585.3 (1.8x); bipolar 296 over F31 (1.8x); Alzheimer 290.1 over G30 (2.4x); Graves 242 over 242.1 (4.1x, accepted in the earlier report); osteoarthritis M17 (largest of M15-M19; union 740 = 0.086); stroke 433; GERD 530; OSA 327; PE 415; acute pancreatitis 577; periodontitis 523.

## (c) The earlier 21, before and after

| disease | before | v3 | status |
|---|---|---|---|
| hypertensive disorder | I12 wrong | dropped (category) | removed, not fixed: phecode 401 (94k cases) was available |
| cardiac rhythm disease | I46 wrong | 427.9 Palpitations | still wrong |
| congestive heart failure | I27 wrong | 428 | fixed |
| enteritis | K29 wrong | 535 Gastritis | still wrong (same bucket) |
| injury | T23 wrong | T23 | still wrong |
| primary biliary cholangitis | K74 wrong | 571.6 | fixed |
| psoriatic arthritis | L40 wrong | 696 | still wrong (same bucket) |
| Graves disease | GBD thyroid wrong | 242 Thyrotoxicosis | fixed (defensible) |
| hyperopia | GBD refraction wrong | 367 | doubtful, K flag remains |
| arterial occlusion | I65 doubtful | 433 | still doubtful |
| cardiovascular disorder | I25 doubtful | dropped | fixed |
| chronic pain syndrome | M79 doubtful | 338 Pain | defensible, K flag remains |
| erectile dysfunction | F52 doubtful | F52 | unchanged |
| eye disorder | H26 doubtful | dropped | fixed |
| hematologic disorder | D64 doubtful | dropped | fixed |
| insomnia | G47 doubtful | 780 Hypothermia/Chills | worse: now wrong |
| skin disorder | C44 doubtful | dropped | fixed |
| urinary system disorder | N17 doubtful | dropped | fixed |
| impaired renal function | N25 doubtful | 588 | unchanged |
| diabetic neuropathy | GBD T2D doubtful | GBD T2D | unchanged |
| presbyopia | GBD doubtful | 367 | still doubtful, K flag |

Fixed 11, unchanged 8, worse 1, removed 1. GBD K-magnitude flags fixed by the switch: Crohn, UC, decubitus, cataract, OAG, endometriosis, BPH, AF, RA, T1D, acute pancreatitis, IDA, fibroids. Made worse by the switch: migraine, hearing loss, MDD, MASLD, periodontitis, acne, nephrolithiasis.

New wrong/doubtful introduced by v3 (19): kidney failure, constipation, ALS, COPD, celiac, ptosis, diabetic retinopathy, sleep apnea, orthostatic hypotension, chronic rhinosinusitis, SLE, nephrolithiasis, Raynaud, acne, allergic rhinitis, MASLD, Barrett, female infertility, MDD; plus AGA (doubtful), and three wrong category drops below.

## (d) The 10 out and the 10 in

Out (category): right to drop 7: urinary system disorder (772 members), cardiovascular disorder (I00-I99), skin disorder, eye disorder, hematologic disorder (D50-D89), mineral metabolism disease (chapter E83; knife-edge at 31 descendant codes vs 30), anemia (class; 285 Other anemias 0.037 if wanted). Wrong to drop 3: **glaucoma** (37 subtype codes tripped the rule; 365/H40, 6,199 cases, 0.015), **hypertensive disorder** (401, 94,311 cases, 0.225, the best-powered K in the set), **cardiomyopathy** (53 genetic-subtype codes; 425/I42, 0.004).

In: essential hypertension 401 correct; hemorrhoid 455 correct; obesity 278 correct (K flag vs BMI GWAS 0.25); intervertebral disc degeneration 722.6 correct; hypoglycemia 251 defensible (= 251.1); diastolic and systolic heart failure 428 defensible (no HFpEF/HFrEF code); androgenetic alopecia 704 doubtful; ptosis 374 wrong (374.3); diabetic retinopathy 362 wrong (250.7).

## (e) Systematic problems and fixes

1. **Integer-part (and exact-string) ICD-9 -> phecode matching is not a mapping.** 13 of 114 land on an unrelated phecode: 780 (x2), 710, 477, 592, 473, 335, 495, 579, 586, 628, 571.8, 427.9. Fix: load the PheWAS catalog maps (`phecode_map_v1_2_icd9.csv`, `Phecode_map_v1_2_icd10_beta.csv`) and map MONDO's ICD-9 and ICD-10 xrefs through them; drop `phecode_matches`. If no map file, require the manifest description to share a token with the MONDO label before accepting a phecode.
2. **"Most cases wins" picks the broadest bucket.** 12 picks are a parent over an exact code that was in the same pool: 374/374.3, 362/250.7, 458/458.1, 443/443.1, 696/696.42, 530/K22, 564/K59, 365/365.1, 425/425.11, 707/L89, 427/427.2, 296/F31. Fix: rank candidates by specificity first (exact phecode = own 3-char ICD-10 > parent/integer phecode), cases second; take the most specific with >=1,000 cases.
3. **First pool uses raw own ICD-10 codes.** 4-character own codes (G473, G470, K900, H010, L405, I730, H401, J330) are absent from the 3-character manifest, so the 3-char parent never competes and the parent tier runs only when the pool is empty: sleep apnea, insomnia, celiac, Barrett, PsA, Raynaud. Fix: pool `with_parents(own_icd10)` from the start (`_best(ukb_all, with_parents(own_icd10) | phecode_matches(...))`).
4. **ICD-9 ranges are expanded into the phecode pool** (490-496 -> asthma for COPD; 410-414, 401-405, 390-459 likewise). Fix: never expand an ICD-9 range into candidates; treat any own range (ICD-9 or ICD-10) as the category signal it is, and keep only explicit codes (496).
5. **Category rule fires on subtype-rich diseases and misses real categories.** >30 descendant codes drops glaucoma, hypertensive disorder, cardiomyopathy; injury (9 codes), enteritis and arterial occlusion pass. Fix: a term with an exact own phecode or 3-char ICD-10 code at >=1,000 cases is a disease regardless of descendant count; category = own range xref >=10 codes, or no own code and >30 descendant codes; hand-list injury.
6. **Descendant tier pools parents of descendants**, pulling in sibling diseases (enteritis -> 535 gastritis; glaucoma's pool led with 743 osteoporosis; cardiomyopathy's with E78). Fix: descendants' own codes and mapped phecodes only, no parents.
7. **The 1,000-case switch from GBD to hospital codes undercounts primary-care diseases** (migraine 17x, hearing loss 14x, MDD 6x under the registered GBD K; MASLD 46x). Fix: keep the earlier report's hand-curated literature-K table (~15 entries) ahead of both sources; otherwise, when an exact GBD cause exists and exceeds the Pan-UKB K by >5x, keep GBD and label the UKB value "coded, lower bound".
8. Minor: N97 female infertility sits at 989 cases, 11 under the 1,000 threshold; sex-limited phecodes (600, 218, 642, 628, 626.8) are handled correctly within sex; no K reached the 0.5 cap.
