# Rule questions and missed comparisons from the v3 re-draft

Collected from each tile's checker verdict (`<slug>.check.json`). A rule question is a case the v3 rules did not decide; a missed comparison is evidence the checker found that the draft left out. Neither changed a stored status: those went through adjudication.

185 rule questions and 183 missed comparisons across the checked tiles.

## acute-myeloid-leukemia-flt3-inhibitors

Rule questions:

- LACEWING opened in 2016; the model paper that predicted the combination (Ueno 2019) was published in April 2019, before readout but after the trial started. Does a model published mid-trial count as 'the system the class relied on', and as prospective?
- When the same drug works as monotherapy (same) but fails in a combination regimen (contra), does 'one drug's contra beats another's same' make the whole efficacy cell contra, or is a combination a separate prediction?
- Dose table: in LACEWING, gilteritinib exposure was at target (troughs equal to monotherapy) and the regimen failed and was abandoned. Should dose get 'contra, derived_from: efficacy' even though the monotherapy dose worked?
- Safety: quizartinib entered humans around 2007 on a rat and monkey package whose QT prediction matched (public in 2023). Is a different tox species package the same model_id ('rat-dog-glp-tox'), or a model_change that could lift the gilteritinib contra?
- Can a single-arm trial's response-rate primary endpoint (quizartinib phase 2, 2018) score efficacy 'same', or only a randomised primary endpoint?
- A patient-level resistance-genotype prediction (which kinase-domain mutations emerge at relapse) is filed under efficacy with endpoint_role 'primary', but relapse genotype is not any trial's primary endpoint. Does decision 4's primary-endpoint rule apply to prediction_level 'patient' tracks, or do they need their own endpoint_role value?

Missed comparisons:

- Efficacy, earlier 'same' in 2018: Cortes 2018 Lancet Oncol quizartinib single-arm phase 2 (doi:10.1016/S1470-2045(18)30240-7, epub 2018-05-31; NCT00989261), co-primary endpoints CRc and CR. The FDA Xospata review (Nov 2018, in bundle) also approved gilteritinib on ADMIRAL's co-primary CR/CRh. The strip's first 'same' should be 2018, not 2019.
- LACEWING sponsor release: Astellas 2020-12-21, 'did not meet endpoint of overall survival' (https://newsroom.astellas.com/2020-12-21-Astellas-Reports-XOSPATA-R-gilteritinib-in-Combination-with-Azacitidine-Did-Not-Meet-Endpoint-of-Overall-Survival-in-Newly-Diagnosed-FLT3-Mutation-Positive-Acute-Myeloid-Leukemia-Patients-Ineligible-for-Intensive-Induction-Chemotherapy); dates the contra to 2020.
- MORPHO (gilteritinib post-HCT maintenance, NCT02997202): missed primary RFS (HR 0.68, p=0.0518); Astellas topline release 2023-03-09; Levis JCO 2024 doi:10.1200/JCO.23.02474. Post-transplant maintenance was not modelled, so it is a patient_trials/untested note with no status change, but it is a Phase 3 failure the draft does not show.
- QuANTUM-R regulatory reading: FDA ODAC (May 2019) and a complete response letter (June 2019) questioned the robustness of the OS result; quizartinib was not approved in the US until 2023. The 2019 entry does not record this tier-2 view.
- Crenolanib (a class member) is absent: phase 3 NCT03250338 in relapsed/refractory FLT3-mutated AML was reportedly presented at ASH 2025 (benefit reported in NPM1/FLT3 co-mutated patients), and ARO-021 (NCT03258931) vs midostaurin is completed. Not verified here; the drafter should check primary-endpoint results. AKN-028 is also not mentioned.
- Gilteritinib in-vitro activity against FLT3-TKD (Ba/F3 D835Y), the basis for enrolling and labelling FLT3-TKD patients, has no patient-level track. The FDA Xospata multidisciplinary review (NDA 211349, 2018, in bundle) reports CR/CRh 0/18 in TKD vs 35/161 in ITD in the pooled interim analysis and issued PMR-3 (>=30 TKD patients) and PMC-1 (in-vitro sensitivity of other non-ITD mutations). Candidate 2018 patient-level untested/contra entry; ADMIRAL's later TKD subgroup should be checked before scoring.

## allergic-rhinitis-allergen-immunotherapy

Rule questions:

- For model_kind human_challenge the engagement readout (chamber symptom score) is the dosed-patient readout itself; the rules do not say whether engagement is scored same, left untested, or the cell emptied for a human-challenge track.
- A year-only correction with the status unchanged (engagement 2: 2017 -> 2013) does not enter the adjudication queue, which keys on status_draft != status_checked; the brief gives proposed_year but no path for it.
- When a tier-5 press release makes a comparison public first (2017) and a tier-3 registry results record for the same trial is posted later (2018-06-15), rule 2 says the higher tier sets the status but not whether the entry keeps the press-release year or the registry posting date.
- gp-ASIT+ BTT009 met its primary at p=.041 but with a 15.5% effect below the sponsor's pre-specified 20% clinical-relevance bar, and the confirmatory trial then missed: is the first trial same + source_calls_it partial, or does a pre-specified effect-size bar on the primary govern the status?
- Safety rule 'a harm the species could have shown': a 219-subject human-challenge trial was silent on anaphylaxis that appeared once in 1084 programme subjects; does the test turn on species or on the model's power to show a rare harm?
- Dating a drafter-made retrodiction pairing (rBet v 1 mouse, efficacy 7): rule 7 keys on 'the earliest admissible source that makes the comparison', but no source makes a drafter pairing; is the year the model paper's (2013, both sides public via a tier-5 PR) or the tier-1 patient record's (2015)?
- Should the opening untested entry of a post-hoc model (efficacy 6, Tourdot 2013) carry retrodiction: true, since the model was built after the clinic knew the answer, even though that entry makes no comparison?

Missed comparisons:

- gp-ASIT+ conjunctival provocation test (CPT) track, human_challenge, absent from the draft (its judgement says 'no model system compared'): Phase IIb dose-finding scored on CPT, 170 ug chosen, Mosges 2017 doi:10.1111/all.13358 (epub 2017-12-22, PMID 29150857); Phase III BTT009 NCT02560948 (2016 season) CSMS -15.5% peak p=.041 and CPT reactivity reduced p<.001 in dosed patients, Mosges 2018 doi:10.1111/all.13433 (epub 2018-06-21, PMID 29512827); confirmatory Phase III ABT-gpASIT011 NCT03724240 (first posted 2018-10-30, 2019 season) missed primary: CSMS 0.15 vs 0.30 target, p=0.05, ASIT biotech 2019-12-20 (https://firstwordpharma.com/story/4919807, tier 5, model_src 10.1111/all.13358). Engagement same 2018, dose 170 ug reached then failed, efficacy same/partial 2018 then contra 2019 (not 2018 as the draft says).
- NCT02150343 (HDM-SPIRE field Phase 2b, n=715): results posted on ClinicalTrials.gov 2018-06-15, a tier-3 record of the trial the draft calls 'never published' and 'press release is the only record'; primary CS wk 50-52 1.69/1.51/1.40 (active) vs 1.56 (placebo). Under evidence rule 2 it sets the status for dose 3, efficacy 2, safety 3 (still contra/contra/same) and trial_unreported becomes false.
- Circassia PRNewswire 2013-09-12 (https://www.prnewswire.com/news-releases/circassias-short-course-house-dust-mite-allergy-treatment-achieves-significant-long-term-symptom-reduction-223419011.html): HDM-SPIRE chamber Phase II, 172 subjects, four doses over 12 weeks, symptoms improved vs placebo one year after start (p=0.02), 'All treatment regimens were well tolerated'. Earliest public member-drug chamber comparison (engagement year 2013) and the HDM-SPIRE model-side safety statement.
- Health Canada Regulatory Decision Summary RDS00632 for Itulatek (https://dhpp.hpfb-dgpsa.ca/review-documents/resource/RDS00632, approval April 2020): tier-2 record stating authorization rested on four trials including 'a Phase II dose-finding EEC trial'; sets model_filed true for the birch-tablet entries; reports 35.69% TCS reduction, one anaphylaxis at 8 SQ-Bet.
- Not found / not searched: Europe PMC returns no primary animal-model paper for the SPIRE peptides (reviews only), so no missed animal track for the peptide members; DP/MG/14-1 and Salsola kali pollen extract were not pursued beyond one Europe PMC query (no model found); no mouse-model search was run for rBet v 1.
- Stallergenes press release 2009-09-16, BioSpace copy (https://www.biospace.com/stallergenes-s-a-immunotherapy-tablet-containing-recombinant-allergen-rbet-v-1-of-birch-pollen-positive-results-for-a-phase-iib-iii-trial): VO59.08 Phase IIb/III, 2009 season, 483 patients, 12.5/25/50 ug rBet v 1 tablets all significantly reduced AASS vs placebo. Tier-5 patient record predating Tourdot 2013 (received 2012-09-04); dates the rBet v 1 mouse retrodiction (efficacy 7 year 2013) and is the earliest patient source for the patient-blood-dc-pbmc track as well. No further model-system search was run on the models pass.

## alzheimer-disease-anti-app-antibodies

Rule questions:

- Engagement: when the model's main PD readout (brain protofibrils) was never measured in patients, may the cell be scored on a secondary readout that the model said would NOT move (plaque), where the patient readout moved more than the model predicted? Or is it untested?
- Dose: when no member's model stated a human exposure target, does 'reached, failed, abandoned' still give dose contra derived_from efficacy, or is dose untested because there was no target to compare?
- Safety and best model: rule 6 makes one drug's contra override another's same within one model. Ponezumab's Tg2576/2H6 model matched (2017) and lecanemab's mAb158 model missed ARIA (2023). These are different models of one class, so which status does the cell show after 2023?
- Safety: ARIA-E (edema) cannot be seen with histology in mice. Does a mouse study that reported only microhemorrhage count as silent on ARIA-E (not a miss), leaving only excess ARIA-H in Clarity AD to score?
- Efficacy: Study 201 favoured drug in direction (64% probability of a 25% effect) but missed its Bayesian gate. Against a model predicting benefit, is that a primary-endpoint miss (contra) or a directional match?

Missed comparisons:

- safety, lecanemab, contra (model_id tg-arcswe-mab158, plus Tg2576 with mAb158), year 2023. FDA SumR, BLA 761269 (sources/761269/761269Orig1s000SumR.txt, line 346): 'In studies specifically conducted with mAb158 to microhemorrhage in Tg2576 and APPArcSwe transgenic mice, no mAb158-related microhemorrhage was seen.' PharmR studies AD-TR-009 (3 months) and the 4-month Tg2576 study are consistent. Patients: Clarity AD (van Dyck 2022, doi 10.1056/NEJMoa2212948) had ARIA-E 12.6% (abstract) and excess ARIA-H in the full text; Study 201 had ARIA-E 10% vs 1% in the Jan 2023 label (ARIA-H 6% vs 5%, no excess). The model-side numbers were first public in the Jan 2023 FDA review. Under rule 6 this contra likely sets the safety cell's latest status.
- efficacy, lecanemab (only if the protofibril model is scored as predicting benefit): Study 201 missed its 12-month Bayesian ADCOMS primary (64% vs the 80% bar; Eisai release Dec 2017; Swanson 2021, doi 10.1186/s13195-021-00813-8), before Clarity AD met its primary in 2022.

## alzheimer-disease-bace1-inhibitors

Rule questions:

- Can a dose 'contra derived_from efficacy' be paired across sibling drugs when the model that set the exposure target (Lilly dogs, LY2886721) never set the failed drug's dose? Atabecestat doses came from its own human CSF PK/PD. And when the failed trial (EARLY) was stopped for toxicity while the efficacy readout was interim, which dose-table row applies?
- Does a later safety prediction made from a non-model heuristic (low daily dose lowers idiosyncratic DILI risk, LY3202626) count as model_change and let the safety cell turn back, or is it out of scope because it is not a model system?
- The opening year for unpublished preclinical work is proxied to a member's Phase 2 start (2012). Should it be the first-in-human date (LY2886721 Phase 1, about 2011) instead?
- Efficacy 4 (A673T genetics vs atabecestat): A673T lowers beta-cleavage of APP only, while drug BACE1 inhibition also blocks other substrates (e.g. SEZ6), the likely cause of cognitive worsening. Is that a 'condition the model never tested' (#35/#72 -> untested) when no trial source attributes it so? Kept contra.

Missed comparisons:

- Willis 2022 (doi:10.3233/ADR-210037, PMC8842743): LY3202626 was 'predicted to have reduced risk' of hepatotoxicity because of its low dose. NAVIGATE-AD (NCT02791191) showed 'no evidence of hepatotoxicity'. This is a later safety prediction that held, on a dose-load heuristic rather than an animal model, so it is probably not model_change; see rule questions.
- J&J's May 2018 atabecestat discontinuation for liver enzymes (tier 5): no atabecestat nonclinical tox source was found either way. Safety stays contra from LY2886721, but the drafter should say that atabecestat's tox prediction was searched for.
- Elenbecestat (Eisai/Biogen) Sept 2019 MISSION AD stop press release: already covered by the NCT02956486 registry record, which is the higher tier, so no status change.

## asthma-ptgdr2-antagonists

Rule questions:

- Dose 'reached and enough': a member reached target exposure and in the same year met a biomarker primary (Gonem 2016, sputum eosinophils) but missed an FEV1 primary (Erpenbeck 2016b). Does 'drug worked' in the dose table follow any positive primary, or the efficacy cell's status, which was already contra from 2013 on another drug?
- Safety: a member showed a patient harm that animals could show (GB001 hepatotoxicity) but no preclinical toxicology was ever published or filed. Is that untested, or 'silence contradicted' (contra) at low confidence?
- Efficacy: the rodent model was run on QAV680, but AZD1981 (the drug that failed) could not be tested in rodent cells (Schmidt 2013) and relied on guinea pig. Is a sibling-drug model admissible for a member that could not have been run in it?

Missed comparisons:

- Efficacy: ARRY-502 (member) phase 2 met its pre-bronchodilator FEV1 primary, +3.9% vs placebo at 200 mg BID, P=0.02, announced July 2013 (Array BioPharma FY2013 10-K, https://www.sec.gov/Archives/edgar/data/1100412/000110041213000025/arraybiopharma6301310k.htm; tier 5, trial_unreported true). This 'same' precedes AZD1981's 2013-09-10 contra; the cell still ends 2013 contra.
- Efficacy/dose dating: Novartis press releases of October 2019 (ZEAL-1/2 missed FEV1 primary) and 2019-12-16 (LUSTER missed, development stopped), https://www.novartis.com/news/media-releases/novartis-provides-update-luster-phase-iii-studies-patients-uncontrolled-gina-45-asthma. ZEAL-1 (NCT03215758, results 2020-02-12) is also absent from patient_trials.
- Efficacy patient_trials: ADC3680B (PTR-36, Pulmagen/Teijin) positive phase II on morning PEF in mild-moderate asthma (press release, e.g. https://www.biospace.com/positive-phase-ii-in-eosinophilic-asthma-for-b-pulmagen-b-teijin-pharma). Date and whether mPEF was the primary are not verified.
- Engagement: ARRY-502 reduced Th2 mediators in patients (ERS 2014 abstract, https://publications.ersnet.org/content/erj/44/suppl58/4836). Conference abstract only, not read; possible downstream entry.
- Efficacy, human-allergen-challenge-lar track: OC000459 (timapiprant) reduced the LAR AUC 25.4% (95% CI 5.1-45.6%) (Singh 2013 Eur Respir J, PMID 22496329, epub 2012-04-10; NCT01056692, started 2006-02) and its own trials met pre-BD FEV1 primaries (Barnes 2012 Clin Exp Allergy, 28-day, NCT01057927; Pettipher 2014 Allergy, PMID 24866478: 25 mg QD P=0.028). A product_in_model 'same' entry dated 2012 precedes the AZD1981 contra.
- Efficacy, human-allergen-challenge-lar track: setipiprant's own proof-of-concept FEV1 trial in partly controlled asthma (NCT01225315, 2010-11 to 2012-02) has no posted results; a same-drug pairing for the challenge model, trial_unreported.

## atopic-eczema-pde4-inhibitors

Rule questions:

- When several class members went in on different efficacy models (crisaborole: TPA ear edema; LEO 29102: mouse allergic contact dermatitis, failed primary; difamilast: chronic contact dermatitis), must the cell record every model's track as its own entries, or only the best model's? The rule 'one drug's contra beats another drug's same on the same model' does not say what happens across models within one cell.
- Decision 16 margin_stated: the minipig NOAEL (5% ointment, above the 2% clinical strength) was filed under the IND before Phase 3, but the AUC-based margin (about 1x) was first stated in the 2016 NDA review using patient PK. Does a pre-trial NOAEL at a higher strength count as a stated margin, or does the margin need to be expressed in exposure before the trial?
- Does a sponsor's own optimistic reading in a tier-1 paper (Felding 2014: 'clinically relevant efficacy') hold the status until the registry posts a failed primary (2019), per rule 7 (what was known at the date)?
- An ex-vivo explant measuring free drug and tissue cAMP (Eirefelt 2020) is a PK/engagement readout; should its comparison with a failed efficacy primary be scored in the efficacy cell (as drafted, contra) or in the dose/engagement cells?

Missed comparisons:

- LEO 29102 (member): Phase 2 NCT01037881 primary endpoint (EASI change) not significant vs vehicle for any dose (p=0.27, 0.83, 0.08, 0.16), results posted 2019-10-14. Model = mouse topical allergic contact dermatitis (Felding 2014, doi:10.1021/jm500378a, which called the efficacy 'clinically relevant'). This is a contra for a second model_id (mouse-acd) dated 2019, currently buried in patient_trials with no status. It does not lower the crisaborole model's cell under the best-model rule, but it should be recorded.
- DRM02 (member): Dermira 10-K filed March 2015 (sec.gov/Archives/edgar/data/1557883/000104746915002713/a2223853z10-k.htm): 'Initial efficacy data in proof-of-concept clinical trials indicated that DRM02 gel was not more effective than vehicle-only gel'. Tier 5 failure (NCT01993420, no posted results). Its model side was not found, so it scores untested or is set aside, but the note should say it failed rather than 'stopped'.
- Difamilast (member): its FDA multidiscipline review (NDA 219474) names a mouse chronic contact dermatitis model; the Japanese Phase 2/3 primary IGA endpoints were met. A same entry for a separate model_id; the cell status does not change.
- LEO 39652 (topical PDE4 soft drug, LEO): Phase 2 in mild-moderate AD NCT02219633 (2014-07 to 2015-01, no posted results); Eirefelt 2020 (doi:10.1007/s11095-020-02962-1) states its 'lack of clinical efficacy' in AD patients. Not listed as a class member; the explant track's retro reproduction of its failure has no entry.
- Difamilast psychological-stress idiopathic dermatitis mouse model: JID 2022 abstract 576 (jidonline.org/article/S0022-202X(22)01026-0), run after Japanese approval; a further retro track if conference abstracts are admissible.

## breast-cancer-cdk4-6-inhibitors

Rule questions:

- Does a negative adjuvant (early-disease) trial count against a model that only predicted antiproliferative sensitivity in advanced-disease cell lines? Under the brief it is either untested (a condition the model never tested) or contra (one drug's contra beats another's same, even though abemaciclib in monarchE and ribociclib in NATALEE succeeded). The context population ('HR-positive, HER2-negative') does not exclude early disease.
- model_kind has no in_vitro value; the draft uses ex_vivo for an established cell-line panel. Should in_vitro be added, or should ex_vivo be reserved for patient-derived material?
- Efficacy/dose parallel track rodent-brain-penetration-abema: does a rat intracranial glioblastoma survival model count as testing breast-cancer brain metastasis response, or is the breast brain-met trial a condition the model never tested (untested)?
- Safety track dog-cv-telemetry (palbociclib): when an FDA review duplicates text across a pre-FIH study and a later study run after patient QT data were public, which date governs retrodiction?

Missed comparisons:

- Efficacy: PALLAS (palbociclib + adjuvant endocrine therapy, HR+/HER2- early breast cancer) failed its primary iDFS endpoint. Pfizer press release 2020-05-29 (tier 5); Mayer et al. Lancet Oncol 2021, doi:10.1016/S1470-2045(20)30642-2 (PMID 33460574, epub 2021-01-15); NCT02513394 results 2022-04-13. Candidate contra for the cell-line model unless the adjuvant setting counts as a condition the model never tested (see rule question).
- Efficacy: PENELOPE-B (palbociclib, residual high-risk HR+/HER2- early breast cancer) negative for iDFS. Loibl et al. J Clin Oncol 2021, doi:10.1200/JCO.20.03639 (PMID 33793299); NCT01864746 results 2023-12-12.
- Safety: ribociclib dog telemetry predicted QTc prolongation at patient-level exposure, 'consistent with QTc prolongation observed clinically' (FDA 209092 Multidiscipline review, 2017; comparison stated). A same for the class that the draft omits; status unchanged, because abemaciclib's contra outranks it. Not checked: whether ribociclib animal studies were silent on its labelled hepatobiliary toxicity (a possible second contra).

## breast-cancer-pan-her-inhibitors

Rule questions:

- The tile gives no population; the drafter set 'HER2-positive', which turns the sapitinib trials (MINT: no HER2 criterion in the registry, 'hormone-sensitive' in the abstract; THYME: HER2-low) into sibling-population comparisons that decision 12 transfers for safety only. Who fixes the population when the tile has none, and may one context carry a patient-level HER2-low prediction beside a HER2-positive class-level track?
- Does a single-arm phase 2 whose primary endpoint (PFS) has no prespecified bar count as 'the primary endpoint responded as predicted' (Park 2018, poziotinib, PFS 4.04 months, authors call it meaningful activity), so that it dates the track's first same? The draft excluded the phase 1 (Ma 2017, ORR 50 %) because its primary was MTD, which the rules support; the single-arm phase 2 case is undecided.
- Decision 16: does a model source published after the trial began but before the comparison was public (Li 2017, 2017-01-21; the pyrotinib phase 1 ran 2013-2016 and was published 2017-05-12) count as a margin 'stated before the trial'? The checker brief flags margin_stated with no pre-trial model statement; the drafter brief dates by what was public at the entry's date.
- When a model source asserts 'sufficient safety windows in animals' but its animal data are unreadable, is the assertion scored as silence (safety contra when the harm appears) or as a stated margin that held (dose same, safety same)? The draft scores it both ways at once (dose 3 margin_stated true; safety 3 silence contradicted).
- A patient-level prediction tested by the model only in other tissues (Hickinson 2010: HER2-non-overexpressing LoVo, FaDu, PC-9; the breast model was HER2-amplified) and paired with a breast HER2-low trial: is that 'a condition the model never tested' (untested) or a tested class-level prediction (contra)?
- Models track (er-pos-tamres-mcf7-xenograft, efficacy #6): a stated post-hoc comparison (decision 10 retro) whose patient arm is a sibling population of the context (MINT, HR+ HER2-non-amplified, in a HER2-positive tile). Does decision 12's safety-only transfer override decision 10, making it untested, as efficacy #3 was adjudicated, or does a patient-level track carry its own population so retro stands?

Missed comparisons:

- Morrison 2014, BCRT 10.1007/s10549-014-2878-x (epub 2014-02-20): ER+/HER2-negative MCF7 tamoxifen-resistant xenografts, AZD8931 + tamoxifen/fulvestrant delayed growth. This, not Hickinson 2010's panel, is the model behind MINT (AZD8931 + anastrozole, endocrine-naive). No track; paired with NCT01151215 results (2014-05-08, PFS HR 1.37/1.16) it is contra, prospective (published before the result).
- THYME, NCT00900627 (tier 3, results posted 2014-09-29): phase II PFS, AZD8931 + weekly paclitaxel vs paclitaxel in 'advanced breast cancer with low HER2 expression', HR 1.08 (95 % CI 0.76-1.52, p = 0.679); ORR OR 2.02 (p = 0.026). The direct HER2-low test of Hickinson 2010's pitch; the draft lists it with no result or quote. No peer-reviewed publication found on Europe PMC.
- Kim 2018, Cancer Res Treat 10.4143/crt.2017.303 (epub 2017-08-29): poziotinib phase 1, MTD 24 mg/day intermittent and 18 mg/day continuous, DLT grade 3 diarrhoea; 5 of 7 partial responses were HER2-amplified breast cancer. The poziotinib arm of track B has no dose entry and no PD readout; this is the source for both.
- Tjulandin 2014, Invest New Drugs 10.1007/s10637-013-9963-6 (epub 2013-04-16): AZD8931 phase 1 (NCT00637039), MTD 240 mg bid, DLTs grade 3 rash and grade 3-4 diarrhoea, exposure proportional to 160 mg. Track A's dose and safety cells cite no human PK or tolerability source.
- Hickinson 2010 full text (read): xenograft panel is BT474c (HER2-amplified breast), Calu-3, LoVo, FaDu, PC-9. The draft's track-A model description should say the breast model was HER2-amplified and the HER2-non-overexpressing models were non-breast.
- No patient-derived organoid or PDX comparison for any member in breast cancer was found (Europe PMC: pyrotinib + organoid/patient-derived + breast; the only PDX-style hit, 10.1002/ctm2.148, is gastric). No regulator document for pyrotinib is public (NMPA conditional approval 2018 on the Ma 2019 phase 2); nothing to add.

## cystic-fibrosis-cftr-correctors

Rule questions:

- Decision 16 / checker brief: does a tox margin first published in the NDA review (after Phase 3) count as 'stated before the trial' when the studies themselves were in the IND before Phase 3 (model_filed true)?
- Decision 16 says a harm the model predicted with a misplaced margin is counted in dose, but its dose contra row is for a target never reached. Where does a predicted-organ, misplaced-margin harm go when patients reached target and the harm was not dose-limiting (vanzacaftor liver)? Safety contra, safety same, or dose contra?
- #70 for fixed-dose combinations whose components are all class members or the shared backbone (Trikafta, Alyftrek): can a label harm attributed to the combination anchor a contra for the corrector's tox model?
- Same drug, two combinations, opposite engagement results on the same model (GLPG2737: FALCON null, PELICAN positive). Decision 6 says one drug's contra beats another drug's same; it does not say how one drug's mixed record is resolved.

Missed comparisons:

- Elexacaftor tox (NDA 212273 MultidisciplineR p.43): rat target organs stomach/testes, no liver; dog only hepatocellular hypertrophy (non-adverse). Trikafta 2019 label 5.1 'Elevated transaminases have been observed in patients with CF treated with TRIKAFTA', later liver failure. Candidate safety entry for model elexacaftor-rat-dog-tox, subject to the same #70 attribution question as safety 2.
- Lumacaftor liver: Orkambi 2015 label 5.2/6.1, 'Three patients who received ORKAMBI had liver-related serious adverse reactions ... compared to none in the placebo group', rats and dogs silent on liver (PharmR l.435). Weak because transaminase rates were similar to placebo; the draft should at least note it in safety 1.
- Galicaftor HBE model side exists (Wang 2018 J Med Chem, doi 10.1021/acs.jmedchem.7b01339) for the NCT04853368 FEV1 miss (cohort 2 vs placebo 0.9, p=0.402, verified on CT.gov). The draft says no model prediction was found; the judgement should cite this paper and say why it is not scored (combination with non-member correctors).
- PELICAN (NCT03474042, GLPG2737 on Orkambi, sweat chloride primary met, no posted results) is a same-drug match on the same HBE model; it belongs in the engagement judgement (it is mentioned) but could be its own dated tier-5 entry before the 2019 contra.
- Patient nasal epithelial cell cultures (HNE): Pranke 2017 Sci Rep, doi 10.1038/s41598-017-07504-1 (PMID 28785019), 'Correction of CFTR function in nasal epithelial cells ... predicts improvement of respiratory function by CFTR modulators' (lumacaftor/ivacaftor); later Thorax 2026 doi 10.1136/thorax-2025-223153 on sequential modulators. No parallel track in the draft.

## cystic-fibrosis-cftr-potentiators

Rule questions:

- One trial, two genotype arms predicted by the same assay: icenticaftor met the LCI2.5 primary in class III/IV but showed 'no significant efficacy' in F508del homozygotes although the model potentiated F508del CFTR (Grand 2021). Is the track same with source_calls_it partial, contra (a wrong prediction beats a right one on the same track), or untested for that arm because the model tested recombinant F508del potentiation, not F508del epithelia as monotherapy?
- Does a label whose section 12.1 (HBE) and section 14 (sweat chloride, ppFEV1) carry the two sides in separate sections count as comparison_stated and set the year under rule 6, or only a document that puts them side by side? The draft dates efficacy 4 by the 2024 label and engagement 4 by the 2025 paper for the same trial.
- A model prediction of 'greater activity' than the comparator regimens (HBE Ussing) answered by a non-inferiority primary endpoint with superiority only on a secondary (sweat chloride): is that same direction_only or source_calls_it over_predicted? Rules define over_predicted only as a source call.
- A prospective, member-drug, patient-level comparison known only from a consortium press release (CHOICES) whose model side is an unpublished organoid study: with no tier 1-3 model_src available, is the entry inadmissible, untested with the release noted, or tier 5 with model_src_tier null?
- Tracks whose model_first_use_year precedes their first entry (FRT 2012, organoids 2016) pass lint; should the opening untested entry be mandatory per track rather than per cell?

Missed comparisons:

- Prospective organoid-guided patient-level track with member drug dirocaftor: HIT-CF CHOICES, NCT06468527 (acronym CHOICES; sponsor Kors van der Ent; phase 2b placebo-controlled crossover; 41 adults selected from the HIT-CF Organoid Study; primary ppFEV1; completed 2025-06-26; no results posted). Results reported only in HIT-CF/CF Europe press material (https://www.cf-europe.eu/hit-cf-choices-cftr-modulator-trial/: lung function changes from -12% to +22% ppFEV1 'along with matching improvements in sweat chloride') and FirstWord (https://firstwordpharma.com/story/6326317: 'clinical effect proportional to in-vitro' organoid response). Tier 5 patient side, trial_unreported true; the model side (HIT-CF organoid screen) needs a tier 1-3 source not located within budget. The draft's judgement cites the wrong NCT: NCT03500263 is Proteostasis's own safety study, not CHOICES. This prospective entry on cf-intestinal-organoid-fis would precede the Kroes 2026 retrodiction.
- GLPG1837 on the HBE track before SAPHIRA1: Gees et al. 2018, Front Pharmacol, doi 10.3389/fphar.2018.01221 (open access, 2018-10-26): 'The observed activities in YFP halide assays translated well to primary cells derived from CF lungs when measured using Trans-epithelial clamp circuit (TECC).' Patient-derived primary airway cells with a member drug, so cf-hbe-ussing carries a GLPG1837 prediction (engagement, paired with Davies 2019) that the draft places only on the recombinant-assay track; it also settles the draft's open question that Van der Plas 2018 was a recombinant YFP assay.
- Checked and not missing: navocaftor (NCT03969888 results 2023-06-28; monotherapy ppFEV1 -2.2 vs -2.2 placebo, sweat chloride -8.9 vs -2.1 confirmed) has no admissible model source on Europe PMC; ORIGIN-1 organoid-guided N-of-1 trial (doi 10.1186/s13063-026-09789-y) tests ETI only, outside the member list.

## gastroesophageal-reflux-disease-atp4a-blockers

Rule questions:

- Efficacy: when the only published disease model (Kim 2019 rat GERD) was submitted after the phase 3 finished and after approval, and its run date is unpublished, is it prospective or `retrodiction: true` (retro rather than same)? The rules key on run date, which no source gives.
- Safety: if the class relied on an unpublished regulatory tox package and the only public animal safety study was run post-approval, should the cell stay `untested` on the unpublished package (model_first_use_year pre-clinic, unknown) or be built on the post-approval study as the draft does? And is that study then a retrodiction of the comparable-AE phase 3 data?
- Dose: does a model that states only an effective oral mg/kg (no exposure or occupancy target) count as stating a dose target, so that 'reached, drug worked' gives `same`, or does it stay `untested` as drafted?

Missed comparisons:

- No unreported failure found: Sebela press release 2025-04-23 (biospace.com/press-releases/sebela-pharmaceuticals-announces-positive-topline-results-from-phase-3-triumph-program-of-tegoprazan-in-gerd) reports all primary endpoints met in TRIUMpH EE and NERD; could be added to patient_trials (tier 5), no status change.
- Fexuprazan phase III EE head-to-head (Jeong 2024, J Clin Med, doi:10.3390/jcm13113262) is RETRACTED; correctly absent, worth a note so it is not re-added.
- Tegoprazan Korean NERD phase 3 and TRIUMpH NERD (GERD patients) are additional efficacy patient_trials; no status change.
- Zastaprazan (JP-1366; Korean approval 2024 for erosive oesophagitis) is a Korean P-CAB the tile does not list; its only model found is a GERD-patient popPK model (doi:10.1002/psp4.13228, 2024) that describes exposure, not acid or healing, so no track needed unless zastaprazan is added to the class.

## hemophilia-a-f8-replacement-gene-therapy

Rule questions:

- Where is a durability failure scored when every primary endpoint and PoC gate was met? Valoctocogene lost ~50% FVIII from year 1 to 2 and giroctocogene fell 42.6% to 25.4%, yet ABR stayed down; decision 4 (efficacy = primary endpoint) cannot hold the dog-track miss, and engagement asks only whether the readout moved. Efficacy #4 turns on this.
- Does the checker-brief bar 'result attributed to conditions the model never tested' extend to a mechanism the species cannot mount — capsid-directed T-cell hepatitis in tolerant hFVIII-transgenic mice or in macaques? If yes, efficacy #7 (BAX 888) and safety #2 (ALT rise) become untested; if no, both contra stand.
- Decision 5: is a model harm that the sponsor and regulator attribute to xenogeneic immunogenicity (monkey anti-drug antibodies, acquired hemophilia, one death on efanesoctocog alfa) a 'predicted harm that never came' (contra, opposite) or not a stated human prediction (same)? Safety #4 turns on this; untested seems wrong either way.
- Is a secondary FVIII-activity endpoint in a phase 1/2 gene-therapy dose-escalation trial whose registry primary is adverse events only (NCT03370172, NCT03003533) a 'pre-specified proof-of-concept gate' by default, or must the sponsor name it as the decision point in a source?
- Decision 16: does a mouse toxicology margin of 1.09x (mortality at 6.53e13 vg/kg against a 6e13 vg/kg clinical dose) count as a stated margin that held (dose #2, margin_stated true)?
- A platform harm (AAV capsid hepatotoxicity with ALT rise) was already shown in hemophilia B AAV2 patients (Manno 2006) and missed by dogs and macaques before any F8 member was dosed: does `other` (same platform) open the gene-therapy safety strip in 2006, or is cross-class evidence set aside under decision 13 and the strip opens at 2017 as drafted?
- Does a retrodiction track need an opening untested entry (engagement #4, same source and year as the retro entry), and if so should it carry retrodiction: true when lint only allows retro/contra on retrodiction entries?
- Is a 3-patient terminated descriptive study reporting registry counts only on a secondary outcome (NCT03520712, 1/3 FVIII >=5 IU/dL at week 26) a patient result for an engagement `same` (engagement #7), given decision 10's 'a non-significant trend in a terminated trial is not a patient result'?

Missed comparisons:

- Mouse unfolded-protein-response / ER-stress prediction for high FVIII expression (Lange 2016, doi:10.1038/mtm.2016.64, PMID 27738645: transient UPR activation at >200% FVIII after AAV in hemophilia A mice) versus patient biopsies in Fong 2022 (doi:10.1038/s41591-022-01751-0: 'no endoplasmic reticulum stress was detected in hepatocytes expressing hFVIII-SQ protein') — a safety comparison on the mouse track that the draft never scores (decision 5 contra/opposite, or same if only BioMarin's own mice are the track).
- Dog on-target safety prediction: no long-term FVIII inhibitor after liver gene transfer (Sabatino 2011, doi:10.1038/mt.2010.240: 'no long-term immune response to FVIII was observed in any of the dogs (1/9 dogs had a transient inhibitor)'; also Finn 2010, doi:10.1182/blood-2010-06-288001) versus no FVIII inhibitors in GENEr8-1 (Roctavian SBRA, https://www.fda.gov/media/170455/download) — a pooled on-target safety entry on the dog track; the drafter noted it as 'uncompared in print' but v3 rule 1 allows the pairing.
- Dog genotoxicity prediction: clonal expansion of AAV-transduced hepatocytes in 5/6 dogs at 10 years (Nguyen 2021, doi:10.1038/s41587-020-0741-7, PMID 33199875) versus NHP integration analysis showing no clonal expansion (Roctavian SBRA nonclinical section) and no hepatic tumours reported in patients to date — the dog track has no safety entry at all.
- Post-clinic nonhuman-primate models of AAV-FVIII expression loss (IL-15 blockade + rapamycin rescue of 'multifactorial loss of factor VIII'), pointed to by the review doi:10.1177/20406207251406537 (Ther Adv Hematol, 2026) — a candidate retrodiction track (decision 10, status retro) that the draft does not carry; primary paper not resolved within budget.
- Peboctocogene camaparvovec (BAY 2599023 / DTX201, Bayer/Ultragenyx, AAVhu37; WHO INN proposed list 124) is a tile member with no entry and no model named; its phase 1/2 (NCT03588299) and preclinical model were not searched by the drafter.
- Regulator action on the durability miss: FDA Complete Response Letter for valoctocogene, August 2020, requesting two-year GENEr8-1 data (BioMarin press release, tier 5), and BioMarin's 2025 withdrawal of Roctavian from the US market (https://www.bleeding.org/news/biomarin-pulls-roctavian-hemophilia-a-gene-therapy-from-us-market) — neither changes a status but both belong in the efficacy note.
- Member-drug program stops with no model comparison, worth a note: Pfizer ceased giroctocogene development despite AFFINE meeting its primary endpoint (Sangamo press release, https://investor.sangamo.com/news-releases/news-release-details/sangamo-therapeutics-regain-full-rights-hemophilia-gene-therapy); Roche withdrew the SPK-8011 phase 3 (https://www.fiercebiotech.com/biotech/roche-mothballs-another-hemophilia-gene-therapy-under-spark-it-plans-debut-new-hematologic) and discontinued SPK-8016.
- Kistner 2024 (doi:10.1038/s41434-023-00423-z, PMID 37833563, epub 2023-10-13): cynomolgus macaques given AAVrh10-hFVIII under prophylactic prednisolone, rapamycin or combinations (Ultragenyx/Penn); prednisolone alone raised hFVIII but 'this was not sustained upon taper'. The drafter set it aside as a sibling capsid asking a regimen question, but decision 8 allows proxies (product_in_model: false) and the dose cell scores regimen predictions, with GENEr8-3 prophylactic corticosteroids (NCT04323098, results 2024-04-04) as the patient test; candidate dose/engagement track, retro if motivated by the GENEr8-1 steroid data.

## hemophilia-b-f9-replacement-gene-therapy

Rule questions:

- Best-model rule vs class members on different models: when one member (BAX 335, mouse model) is contradicted and another (fidanacogene, dog model) matches in the same cell and same year range, the cell shows only the dog's same. Should a different member's contra on a different model of the same kind (AAV8 FIX-Padua, liver) be shown?
- Two dog systems for fidanacogene: Crudele 2015 AAV8-cFIX-Padua (cited by George 2017) vs the AAVRh74var-cFIX-R338L surrogate FDA reviewed. Are these one model_id (same species, transgene, route) or two, and which is 'the model the class relied on' for dose?
- Year of a pairing whose patient side was public first by press release (Dec 2022) and model side only in the SBRA (Apr 2024): rule 6 does not say whether the year is the later of the two dates.

Missed comparisons:

- DTX101 (AAVrh10-hFIX, a class member): Phase 1/2 101HEMB01 missed its primary endpoint (peak FIX >=20 IU/dL at week 6; median 7 and 10 IU/dL) and the program was dropped (Dimension press release Nov 2017; Blood Adv 2025, PMID 40197980, PMC12197983). The paper names no preclinical model; if Dimension's NHP/mouse data predicted >=20%, efficacy and gene-therapy dose take a contra (2017, tier 5 then tier 1). Not entered in the draft at all, not even in patient_trials.
- AskBio009/BAX 335 (Konkle 2021, PMID 33067633): FIX not sustained beyond 5-11 weeks in 7 of 8 patients; first public in Baxalta 2015-2016 releases and ASH abstracts. Only mentioned in judgement/patient_trials; a dated engagement/dose entry against its own preclinical model (Monahan 2015 mice/NHP) would show the miss even if the best-model rule leaves the cell at same.
- verbrinacogene setparvovec (FLT180a, Chowdary 2022 NEJM 10.1056/NEJMoa2119913): needed glucocorticoids +/- tacrolimus, one AV-fistula thrombosis at FIX 260%; development paused 2022 (Freeline). Its preclinical (NHP) model was not read by the drafter or by me.
- AAV5-hFIX (AMT-060, Miesbach 2018 Blood 10.1182/blood-2017-09-804419): FIX 4.4-6.9 IU/dL; no comparison with its NHP predictions was looked for (dose cell, gene therapy).
- Fidanacogene predecessor (AAVRh74var-hFIX-Padua) GLP toxicology in healthy mice: 6 test-article-related unscheduled deaths (brain/skin pathology, read as exacerbated tissue/vascular injury in animals with endogenous FIX) at doses 2-10x below the human dose; no such harm in patients. Safety track absent from the draft (FDA SBRA Beqvez, https://www.fda.gov/media/178688/download, nonclinical section).

## hepatitis-c-virus-infection-hcv-ns3-4a-protease-inhibitors

Rule questions:

- Dose table 'reached, drug worked': does a phase 1 viral-load response count as 'worked', so the entry is dated at phase 1, or must the efficacy primary endpoint have read out first? Also, can a dose entry be 'same' when the source never reports exposure against the model's numeric target (EC99)?
- Q80K: the replicon fold change was measured on baseline clinical isolates at the same time as the phase 3 trials. Is this a prospective model prediction or a retrodiction (retro)?
- Hepatotoxicity seen only under a drug interaction (sovaprevir with atazanavir/r in healthy volunteers; paritaprevir with ethinyl estradiol): no rule says whether a DDI-driven harm the animals were never dosed under counts as the model's silence being contradicted or as untested.
- Models check: a routine preclinical model (HCV chimpanzee monotherapy) whose run date is unstated and whose first record (2010) post-dates a public patient result (AASLD 2008), but which was not motivated by it. Rule 10 requires both 'post-dates' and 'motivated by'; scored retro here on the record date.

Missed comparisons:

- Efficacy: vaniprevir phase II (Manns 2012 Hepatology, doi:10.1002/hep.25743, epub 2012-07-17): primary endpoint RVR 68.8-83.3% vs 5.6% placebo (P<0.001). An earlier member 'same' (paired with vaniprevir replicon data), so the efficacy cell turns 'same' in 2012, not 2013.
- Dose: glecaprevir 6-month rat NOAEL gives a 70x exposure margin at 300 mg (209394 PharmR: 'This provides an exposure margin of 70X'), which held in patients. This is a margin_stated 'same' (2017) and could carry the dose cell if dose entry 2 is not accepted.
- Safety (no status change expected): FDA clinical hold on sovaprevir, June 2013, for grade 3-4 ALT elevations in a healthy-volunteer DDI study with atazanavir/ritonavir (Achillion 10-K, https://www.sec.gov/Archives/edgar/data/1070336/000119312514089075/d645073d10k.htm; https://www.fiercepharma.com/regulatory/fda-slaps-a-clinical-hold-on-achillion-hep-c-drug). The harm came from conditions the model never tested, so 'untested'; the draft's judgement should mention it.

## hiv-infectious-disease-hiv-integrase-insti-inhibitors

Rule questions:

- When the first public patient signal is a tier 1 letter with no abstract (Zash 2018) and a tier 2 regulator communication exists but could not be retrieved, should the contra be dated to the first public signal (2018) or the first quotable source (2019)?
- For dose 'reached, drug worked', is the entry dated when both halves are public (HV PK reaching target 2009 + first efficacy 2011) via pairing, or does it need a source that states trough vs target and response together (FDA review 2013)?
- Class-wide harms not tested against tox packages (INSTI weight gain, DTG creatinine/OCT2, neuropsychiatric AEs): does rodent silence on weight gain count as a miss the species could have shown?

Missed comparisons:

- Min 2010 AAC 10.1128/AAC.00842-09 (epub 2009-11-02): 'C(tau) with a 50-mg dose was 1.6 microg/ml, approximately 25-fold higher than the protein-adjusted 90% inhibitory concentration (0.064 microg/ml)': healthy-volunteer dose comparison the draft omits; moves dose dating earlier.
- Zash et al. AIDS 2025, 10.1097/QAD.0000000000004326: earliest peer-reviewed report of the Tsepamo NTD signal attenuating (0.10% vs 0.11%).
- Zash 2018 NEJM letter 10.1056/NEJMc1807653 (epub 2018-07-24) and the May 2018 FDA/EMA safety communications: first public NTD signal, a year before the scored entry.
- Zebrafish embryo DTG developmental-toxicity model (Cabrera et al. AIDS 2019, 10.1097/QAD.0000000000002289; Cabrera 2026 DMM 10.1242/dmm.052632): folate-receptor antagonism and NTD-type defects set against the Tsepamo signal; no track.
- Second mouse NTD model, SWV/Fnn and other strains dosed with DTG (Tukeman et al. AIDS 2024, 10.1097/QAD.0000000000003639; Gelineau-van Waes 2023 Front Cell Dev Biol 10.3389/fcell.2023.1175917): DTG-induced NTDs, folate-responsive; a separate model system from the C57BL/6J therapeutic-dose track.

## hiv-infectious-disease-hiv-maturation-gag-inhibitors

Rule questions:

- readout_tier for on-treatment resistance selection at the drug's binding site (A364V at CA/SP1): 'direct', 'proximal', or not an engagement readout at all when the model's own PD readout (viral replication = viral load, listed as proximal) is available earlier?
- Safety 'contra' for a predicted animal harm absent in patients: what minimum sample size and duration makes 'never appeared' a comparison rather than 'untested' (here 14 on-drug paired gastric biopsies at 24 weeks, planned Week-96 biopsies never done), and does an animal finding with no public exposure margin count as a stated prediction of harm at clinical exposure (decision 16 interaction)?
- Dose table: when the exposure target was reached and the Week-24 primary was met but the regimen was abandoned for emergent NRTI-backbone resistance and GI intolerability (GSK3532795 Phase 2b, NCT02415595), does the 'reached, failed, abandoned' row apply, or does dose stay 'same' because efficacy is judged on the primary endpoint only?
- Does a cross-species ADME/PK projection (bioavailability, metabolite profile, excretion route) compared with human PK count as a model-system track, or is only the exposure-target model (serum-shifted EC90) scored under dose?
- Patient-level prediction on an existing track (baseline Gag V362I/V370A predicted and observed reduced response): does it require its own entry with prediction_level 'patient', or is one entry per status change per track regardless of prediction_level?
- May a track that only a non-member first-generation drug (bevirimat) ever used in vivo (SCID-hu Thy/Liv mice) appear as an 'untested' track opened by proxy, or does a track need at least one member run in it to exist?

Missed comparisons:

- Humanized mouse efficacy model, no track: HIV-1-infected SCID-hu Thy/Liv mice, oral bevirimat cut viral RNA >2 log10 at plasma concentrations 'achievable in humans' with dose-dependent CA-SP1 cleavage inhibition in thymocytes and in-vivo confirmation of the SP1/A1V resistance phenotype (Stoddart 2007, PLoS One, doi 10.1371/journal.pone.0001251, PMID 18043758; cited as ref 52 in Nowicka-Sans 2016). No member was reported in it, so it is a separate track opening 'untested' (proxy, product_in_model false), and the draft's claim that no animal efficacy model exists must be withdrawn.
- Chronic animal toxicology as the track's species: Johnson 2018 (doi 10.1002/prp2.408) names 6-month rat and 9-month dog studies for GSK2838232 and an FDA clinical hold (Studies 200912/200207 terminated; resumed as Study 204953) that the draft's safety track does not record; not a new track but a dated event on mi-nonclinical-tox.
- Candidate, pending rule question 4: cross-species ADME/PK prediction compared with human PK for GSK2838232 (oral bioavailability 6-40% across species, preclinical metabolite profile 'qualitatively similar' to human plasma, negligible renal excretion predicted and used to skip urine collection), Johnson 2018 doi 10.1002/prp2.408; the GSK3640254 discovery paper (Regueiro-Ren 2022, J Med Chem, doi 10.1021/acs.jmedchem.2c00879, abstract only) describes the preclinical PK profile that preceded the Phase 1 (Pene Dumitrescu 2020, doi 10.1002/prp2.671).

## hyperlipidemia-cetp-inhibitors

Rule questions:

- Decision 16 margin_stated: does a margin count as 'stated before the trial' when the model data were generated pre-IND but first published (Cao 2011) after the human MAD that tested it was run, and before that MAD was published (2014)?
- The same rat BP / exposure-multiple datum scores both dose (margin_stated same) and safety (same). 'Count the harm once' covers a harm that occurred; is double scoring allowed when no harm occurred?
- Best-model rule vs member-specific dose models: should a different model's dose miss for another member (rocacetrapib PK/PD allometry, Choi 2019) appear as its own entry, and is a model published after phase 1 data a retrodiction even if it set the FIH dose?

Missed comparisons:

- Lilly press release 2015-10-12 announcing discontinuation of evacetrapib after ACCELERATE futility (tier 5, investor.lilly.com; page returned 403, not opened) dates the outcome failure to 2015, earlier than the NEJM 2017 / registry 2018 dates in patient_trials.
- Rocacetrapib (CKD-519): Choi 2019 (https://doi.org/10.3390/pharmaceutics11070336, abstract) animal allometric PK/PD model predicted a 25 mg efficacious dose with a 'huge difference' from observed phase 1 bioavailability; published after phase 1 (Kim 2016, https://doi.org/10.2147/DDDT.S120387), so likely retrodiction/contra on a different model of a member drug. Drafter noted it in judgement but scored nothing; best-model rule keeps cell same.
- Teramoto 2014 (PMID 24786356, Europe PMC abstract) gives patient CETP-activity engagement data in April 2014, ahead of Suico (June 2014).
- DRL-17822 patient_trials quote is a paraphrase of the NCT01388816 results table, not a verbatim sentence; numbers (3.2/84.2/122.1/160.6%) verified.
- Prospective pairing for the human-genetics track: Brown 1989 (https://doi.org/10.1038/342448a0) / Inazu 1990 (https://doi.org/10.1056/NEJM199011013231803) CETP deficiency raises HDL-C, confirmed in patients by de Grooth 2002 JTT-705/dalcetrapib phase 2 (https://doi.org/10.1161/01.CIR.0000015857.31889.7B): first class-level same, 2002.

## insomnia-hcrtr1-2-antagonists

Rule questions:

- Suvorexant next-day impairment was the harm behind the FDA dose cut, and the animal package never tested it. The drafter left it unscored under dose. Decision 16 puts an unpredicted harm in safety, so does model silence on next-day or residual sedation count as a harm the species could have shown (safety contra)? Or is it human-PK carryover (half-life), outside what the model could show?
- A dose cell mixes an efficacy-exposure target model (suvorexant C4h) with a decision 16 tolerability-margin model (daridorexant dog NOAEL). Should model_change: true be set when the cell was not contra, given the rule defines model_change only for turning a contra back?
- Dose entry 2: the effective-exposure target is published only in the FDA review that also holds the patient comparison, and Winrow 2011 is cited as model_src. Is this comparison_stated true (regulator states both sides) or false (a pairing)?
- Safety 5-6: the lemborexant mouse cataplexy study (W-20140712, mid-2014) ran when suvorexant's cataplexy-like events in patients were already known (2013 AdCom, 2014 label). At prediction_level class, is a member's model run after a sibling's patient result a retrodiction, or prospective because its own drug's patients were untested?

Missed comparisons:

- Vornorexant Phase 3 (Japan) met its primary sSL endpoint with no narcolepsy-related signs (Sleep 2025, PMID 41001841, https://pubmed.ncbi.nlm.nih.gov/41001841/): this agrees with the draft and changes no status. It could be added to efficacy patient_trials.
- Filorexant Phase 2 insomnia was positive at all doses (Connor 2016, doi:10.1093/ijnp/pyw022), and Merck dropped it without an insomnia failure. The draft names this only in a judgement, which is correct; no failure was missed.
- Lemborexant FDA multidiscipline review 2019 (Figure 1: lemborexant cataplexy in wild-type vs orexin-KO mice) is a separate member-drug safety model with a patient comparison. It agrees, so no status change, but it could be a dated safety entry.
- Fazamorexant Phase 3 (NCT05525637) is reported positive only on secondary aggregators. No failure was found for any member in a press release or SEC filing.
- Lemborexant's and daridorexant's own nonclinical abuse-liability studies vs their human abuse potential trials (FDA 212028 multidiscipline review 2019: 'Nonclinical findings were less suggestive of abuse liability'; daridorexant NDA 214985 review 2022, HAP vs zolpidem): further entries in the rhesus-rat-abuse-liability-battery track, both C-IV.

## interstitial-cystitis-anti-ngf-antibodies

Rule questions:

- Dose table row 'reached, failed, abandoned -> dose contra, derived_from efficacy' (and 'reached, worked -> same'): does it apply when no model ever stated an exposure target for any member drug? The draft keeps dose untested while efficacy goes same then contra; the rules do not say whether 'target reached' can be scored without a stated target.
- Engagement: can a model's functional readout (cystometric voiding frequency in CYP cystitis) count as a downstream PD readout when the human trial measured its counterpart (micturition frequency, unchanged in Evans 2011)? If yes, engagement would be contra 2011 at readout_tier downstream; the draft scored it as a symptom endpoint.
- Dating of efficacy entry 3: could not open the ClinicalTrials.gov history for NCT00999518 (API returned non-JSON). If the termination-for-interim-analysis text was public before Feb 2012, the year should be earlier; the rules do not say whether a registry termination reason without results counts as a public comparison.

Missed comparisons:

- Wang H et al. 2017, BMC Urol 17:2, doi:10.1186/s12894-016-0193-z (PMID 28056917, epub 2017-01-05): fulranumab 9 mg SC in IC/BPS (NCT01060254, n=31), primary endpoint LS mean difference -0.2 [-1.52, 1.10], not significant; no joint-related SAE. The draft says this trial ended 'with no results'; it belongs in efficacy entry 3's patient_trials (no status change: underpowered, already contra) and the note should be corrected.
- ASP6294 is a PEGylated Fab' (MAbs 2023, PMID 36458900, doi:10.1080/19420862.2022.2149055); the EU CTR record 2016-004138-12 (first posted 2020-02-08, women only, P=0.591, -0.2 [90% CI -0.84, 0.43]) confirms the draft's patient_trials quote and shows the female subgroup Nickel 2016 flagged was not confirmed prospectively.

## metabolic-dysfunction-associated-steatohepatitis-fgf21-analogue-fgfr1c-klb-agonists

Rule questions:

- Is a congress abstract (Hepatology 2016;64 Suppl 1:749A, no DOI/PMID), reached only through a trial paper's citing sentence, an admissible model side? Rule 2 lists no such tier. If not, the nash-fibrosis-mouse track has no model source and the class's fibrosis endpoint (FALCON 1/2 failed, HARMONY and ENLIVEN met) has no track at all.
- When the model stated no exposure target or tolerability margin, does the dose table's 'reached, drug worked' / 'reached, failed' row still apply (as the draft does for dose 2, 4 and 6), or is dose 'untested' because there was no prediction to reach?
- One stated comparison that half matches (triglycerides, adiponectin) and half contradicts (glucose, insulin, weight) on the model's own readouts, with the source framing it as a contrast: v3 says partial -> same + source_calls_it partial. Confirm that is intended when the quoted sentence states the contradiction.
- A member-drug toxicology study run before but published after the human result (pegbelfermin 1-year monkey bone, 2021 vs BMD known 2018-2019): retro or same? Decision 10 keys on when the model was 'built or run', which a publication date does not show.
- Non-member drugs of the same mechanism (PF-05231023, LY2405319) carry tier-1 monkey-to-human comparisons including a BP/heart-rate harm. Are they set aside entirely, or does safety's 'other' (same platform) admit them?
- Dating across comparison kinds on one track: can a pairing (comparison_stated false, Kaufman 2020) set the year of a track's 'same' earlier than a later stated comparison (Rosenstock 2023), or does the stated one govern the date?
- Independent human-genetic model (Frayling 2018) published after a sponsor-internal, unpublished patient result (Amgen AKR-001 MAD NCT01856881, 2013-2015, no results posted; published Kaufman 2020): decision 10 needs 'post-dates and is motivated by', so scored same, not retro. Confirm that unpublished sponsor data do not make a later independent model a retrodiction.

Missed comparisons:

- Member-drug monkey bone model with a stated margin: pegbelfermin 1-year skeletally-mature cynomolgus study (Toxicol Appl Pharmacol 2021, doi 10.1016/j.taap.2021.115673, PMID 34364948) at 0.7-2.2x human AUC (20 mg QW) found no bone effects and states 'low potential for negative effects on bone quality in adult humans'. A second bone track (margin_stated true); retro vs same depends on when the study was run (rule question 4).
- Member-drug rat BP/sympathetic model: efruxifermin 4/26-week Sprague Dawley tox (Br J Pharmacol 2022, doi 10.1111/bph.15725, PMID 34773249) states 'absence of an increase in sympathetic tone in rats mirrors the unchanged salivary cortisol and systemic blood pressure following efruxifermin treatment in humans' (Kaufman 2020 PK-PD). Stated comparison, published after the human data: retro. Rats also ate more, matching the increased-appetite AE.
- Human-genetic model on blood pressure: Kaufman 2020 (doi 10.1016/j.xcrm.2020.100057) compares the absence of a BP effect of efruxifermin with FGF21 loss-of-function variant carriers having higher BP (its ref 28); model_kind human_genetic, no track.
- Monkey-track safety silence: tremor (Kaufman 2020: product-related withdrawals for tremor at 140 mg QW efruxifermin) and GI AEs (diarrhoea/nausea, the class's commonest harm) are harms a cynomolgus monkey could show; Stanislaus 2017 / Rosenstock 2023 say nothing. No safety entry exists on the obese-diabetic-cyno-monkey track; the pegbelfermin 1-year monkey paper (clinical observations, food intake) could settle whether monkeys predicted GI effects.
- Later mouse bone model that reversed Wei 2012: Kaufman 2020 ref 27, a DIO-mouse rhFGF21 study finding no bone loss (likely Li et al., J Bone Miner Res 2017, Amgen); a separate track or a retrodiction on the bone question, absent from the draft.
- Pegozafermin phase 1b/2a in NASH patients (Loomba, Lancet Gastroenterol Hepatol 2022, doi 10.1016/s2468-1253(22)00347-8, NCT04048135, epub 2022-12-12): MASH-patient adiponectin/liver-fat PD for the monkey track one year before ENLIVEN; dates the subjects=patients engagement datum earlier than the healthy-volunteer SAD.
- Non-member FGF21 analogues with tier-1 stated monkey-to-human comparisons: PF-05231023 (Talukdar 2016, doi 10.1016/j.cmet.2016.02.001; raised BP/heart rate in one human study) and LY2405319 (Gaich 2013, doi 10.1016/j.cmet.2013.08.005). Outside the member list, so not scored; see rule question 5.
- Could not verify: no phase 3 topline for SYNCHRONY Histology (efruxifermin) or ENLIGHTEN-Fibrosis (pegozafermin; 89bio guides 1H 2027) was found by web search as of 2026-11-05; no BMS press release on pegbelfermin discontinuation was checked beyond the registry (no phase 3 registered).

## metabolic-dysfunction-associated-steatohepatitis-nr1h4-agonists

Rule questions:

- Safety, model-side disclaimer: when the model paper itself says its readout cannot predict the human effect (Hernandez on STAM cholesterol, after OCA's FLINT LDL rise was known), is the later patient opposite result contra or untested? Decision 4 covers trials disclaimed as efficacy tests (#57) but not model papers disclaiming their own readout.
- Safety, askable silence on pruritus: every member had dose-limiting pruritus (tropifexor, EDP-305 50.9%, cilofexor, vonafexor). Mice can show scratching, but no member's rodent studies measured it. Is 'measurable in the model species at the time' satisfied by the behaviour being measurable, or does it require an FXR-itch mouse readout to have existed? If the former, safety should carry a contra on pruritus.
- Dose tie without a stated exposure target: cilofexor efficacy is contra at 30 mg (rat effective dose 10-30 mg/kg, no human exposure mapping). Does row 3 ('reached, failed, abandoned' -> dose contra derived_from efficacy) apply when the model never stated a target, or does dose stay untested as drafted?
- Is a conference abstract with a DOI in a journal supplement (Reiberger 2016) an admissible tier-1 model-side source for dating and for model_first_use_year?

Missed comparisons:

- Cilofexor rat model first public as Reiberger et al. 2016 Z Gastroenterol abstract 'The non-steroidal FXR agonists PX20606 and GS-9674 improve liver fibrosis and portal hypertension in rodent models...' (doi:10.1055/s-0036-1583977); sets model_first_use_year and rules out retrodiction for efficacy entry 2.
- EDP-305 ARGON-2 (NCT04378010, histology phase 2b) stopped after the 12-week interim; Enanta press release 2021-10-04 (businesswire.com/news/home/20211004005192) calls it a strategic decision to prioritize combinations, not safety. Tier 5; belongs in patient_trials, changes no status (development stop is not 'failed', decision 4).
- Cilofexor phase 2 in non-cirrhotic NASH (NCT02854605, results 2019-01-29; Patel 2020 doi:10.1002/hep.31205): primary endpoint safety only; liver-fat fall was secondary. Could be a patient_trials row; does not change status.
- PXB humanized-mouse track, tropifexor healthy volunteers: Papazyan 2018 (doi:10.1194/jlr.M081935) cites Badman 2016 LJN452 first-in-human abstract (Hepatology 64:16A) as reportedly lipid-neutral over <=2 weeks; the mouse LDL rise contradicts that known HV result (retrodiction, contra 2018) before FLIGHT-FXR's patient LDL rise.
- PXB track, cilofexor in NASH patients: Patel 2020 phase 2 (doi:10.1002/hep.31205, NCT02854605, 24 weeks) reportedly no LDL/HDL change vs placebo; would give a patient-population contra in 2020 on top of the HV contra (full text paywalled; registry results posted 2019-01-29 could confirm lipid tables).

## migraine-disorder-anti-calca-calcb-cgrp-ligand-antibodies

Rule questions:

- Pediatric-population miss: fremanezumab failed its primary endpoint in pediatric chronic migraine (NCT04464707, 2025) after matching in adults. Under 'patients of the context's disease only' and 'one drug's contra still beats another drug's same', does a pediatric placebo-controlled miss flip an Unselected (adult-derived) efficacy track to contra, or is age a population split the context does not cover?
- Efficacy cell on a PD-only system: when the only prospective preclinical system is a target-engagement model (evoked vasodilation) whose authors nonetheless made an explicit efficacy prediction (Zeller 2008), does efficacy score same on that track, or is the cell the empty list because no disease model was relied on? The draft's context note says 'not on a disease model' yet populates the cell.
- readout_tier for in-vivo blockade of an evoked stimulus (capsaicin-induced dermal blood flow): the rule lists ex-vivo blockade of a stimulus as direct; in-vivo physiology (blood flow) could be downstream. Undecided.
- magnitude for a predicted-null harm that then appeared: 'opposite' is defined for a predicted harm that never appeared; the reverse case (null predicted, hypertension reported) has no stated value.
- Dating a class-wide pharmacovigilance harm: a tier-1 prospective cohort pooling a sibling-class drug (erenumab) with a member (fremanezumab) showed BP rising in 2022; does a pooled cohort where the member is the minority arm set the member's comparison date, or only the member-specific label (2025)?
- margin_stated on a PD-model track: the tolerability margin comes from the FDA-filed monkey tox NOAEL (a separate study on the same species), not from the CIDBF PK/PD model that is the track's model_id. Does a tox NOAEL count as 'the model stated the margin' for decision 16?
- Christensen 2019 runs two paradigms (mouse GTN-provoked allodynia; selectively bred rat spontaneous trigeminal allodynia) with one result under one model_id rodent-gtn-sta-pain. Decision 8 tracks each system; does one paper/one result justify one track, or should it be split?

Missed comparisons:

- Fremanezumab pediatric chronic migraine Phase 3 NCT04464707 (6-17 y): primary endpoint NOT met, LS mean difference -0.1 MMD (95% CI -1.48 to 1.22), p=0.8484, placebo -3.7 vs fremanezumab -3.8; CT.gov results posted 2025-12-19 (tier 3); AAN 2026 abstract Hershey et al. (index.mirasmart.com/AAN2026/PDFfiles/AAN2026-001129.html) states 'no significant difference was observed between treatment groups in the CM study (-3.8 vs -3.7; p=0.8484)'. A member-drug primary-endpoint miss in the context disease with no entry on the efficacy track; companion EM study NCT04458857 was positive (-2.5 vs -1.4, p=0.0210; label s031 adds pediatric EM). Whether it scores contra is rule question 1.
- Human ex-vivo artery model: Ohlsson et al. 2018, 'Fremanezumab blocks CGRP induced dilatation in human cerebral, middle meningeal and abdominal arteries', J Headache Pain, doi 10.1186/s10194-018-0905-8 (PMID 30109438, 2018-08-14): model_kind ex_vivo, product_in_model true, retrodiction after Phase 3; no track in the draft.
- Mouse CGRP-evoked light-aversion / spontaneous-pain models blocked by ALD405 (eptinezumab's murine sibling, Alder): Mason et al. 2017 J Neurosci doi 10.1523/JNEUROSCI.2967-16.2016 (PMID 28053042) and Rea et al. 2018 Pain doi 10.1097/j.pain.0000000000001337 (PMID 29994995): retrodiction track, product_in_model false; no track in the draft.
- Rodent GTN / migraine-like pain models with ALD405 and olcegepant: Christensen et al. 2019 Cephalalgia doi 10.1177/0333102419861726 (PMID 31288556, 2019-07-09): retrodiction, product_in_model false; no track in the draft.
- Rat post-concussion headache model (Bree & Levy, Cephalalgia, doi 10.1177/0333102416681571, epub 2016-12-07) is filed in the 761089 PharmR as a paradigm distinct from the MOH model; the draft folds it into rat-headache-behaviour without an entry or source of its own. Acceptable as one track, but the PharmR citation should be recorded.
- For the record, not scoring: CHALLENGE-MIG NCT05127486 (galcanezumab vs rimegepant, Lilly 2024 release) missed superiority on >=50% responder, an active-comparator endpoint no model predicted; galcanezumab chronic cluster headache and fremanezumab ENFORCE cluster headache (futility, 2018-2019) are another disease (MONDO cluster headache), outside this context.

## migraine-disorder-cgrp-receptor-antagonists

Rule questions:

- Retrodiction vs prospective on the same model: DILIsym retro-modeled MK-3207 (published 2020) in the same paper that reports the prospective ubrogepant match (2019 FDA, 2020 paper). Should the cell carry a separate retro entry for the MK-3207 member, or does the prospective same subsume it? Decision 10 does not say how a retro and a same of the same date and model order on the strip.
- Dose-table row 'reached, failed, a higher dose later worked': does the higher dose have to be shown superior to the predicted dose? For MK-3207, 200 mg alone was significant, but CIs overlapped from 10 mg up, and the same trial met its primary endpoint on a pooled dose-response trend. The table also implies efficacy contra-then-same, while the draft keeps efficacy same because the primary was met in the same trial. Which applies?
- Should a dose model built in human healthy volunteers (human CIDV calibrated on a non-member's phase 3 data) count as the same model_id/system as the rhesus CIDV used for engagement and efficacy, given that the brief scopes 'the model' to the preclinical system the class relied on?
- MK-3207 GLP toxicology: Monroe 2020 reads three species as silent on liver, but a 1-month dog study showed slight periportal vacuolation and <4X ALT/AST at 17X, attributed to body-weight loss. Is that a sponsor-dismissed animal signal that patients confirmed (same, #23) or askable silence contradicted (contra)? The paper's own reading is silence.

Missed comparisons:

- Smith 2020 (doi 10.1093/toxsci/kfaa093, PMC8312697): 'DILIsym successfully modeled liver toxicity for telcagepant and MK-3207 at the dosing regimens used in clinical trials'. This is a 2020 retrodiction for member MK-3207. The draft mentions it only in a judgement, with no retro entry (see rule question).
- BI 44370 discontinuation: secondary reviews (e.g. PMC4392770) attribute it to liver toxicity and/or oral formulation difficulty. No primary source (press release or registry) was found. If confirmed, it is a second member liver signal for the safety cell. At minimum the safety note should mention it.
- Ubrogepant dose: Voss 2016 phase 2b (doi 10.1177/0333102416653233) found 1 and 10 mg ineffective and 25/50/100 mg effective. Moore 2020 gives human CIDV EC50 2.6 nM. If a CIDV-based ubrogepant dose prediction exists (e.g. the exposure-response paper 'Making Better Dose Decisions...'), it is a second member's dose comparison. The FDA ClinPharmR bundle has no CIDV dose rationale.
- MK-3207 GLP toxicology, 2020 contra on model_id mk3207-glp-tox: Monroe 2020 (doi 10.1093/toxsci/kfaa088, PMC7553701, Table 1 and text) states MK-3207 'was dosed for 9 months in NHP at ... exposures exceeding 4-fold', rat and mouse 6-month margins 'exceeded 30-fold and 14-fold', 'No liver safety signals of concern were noted', and concludes such molecules 'present no evidence of liver safety concerns in 3 species of conventional animal toxicology studies ... and still provoke liver signals' in the clinic (phase 2 ALT>3x ULN 42% at >500 mg, Hy's law case). Comparison stated (comparison_stated true, tier 1); prospective model (run before the clinical signal), so contra, year 2020. Caveat: a 1-month dog study at 17X showed slight periportal vacuolation with <4X ALT/AST, attributed to excessive body-weight loss (see rule question).

## non-small-cell-lung-carcinoma-anti-igf1r-antibodies

Rule questions:

- Efficacy pairing across partner drugs: the A549 model tested h7C10 + vinorelbine or + anti-EGFR antibody 225; the trials ran R1507 + erlotinib (TKI), cixutumumab + pemetrexed/cisplatin and + carboplatin/paclitaxel/bevacizumab. Does 'conditions the model never tested' cover a different combination partner of the same mechanism (EGFR blockade, cytotoxic chemo), or only population/biomarker conditions? Ramalingam attributes the failure to lack of a predictive biomarker, which the unselected A549 model also lacked, so I kept contra.
- Opening (untested) entries at model_first_use_year: may they cite a later patient-side source (dose and safety cells cite 2012 and 2016 papers in 2005 entries), or must the opening entry cite the model source dated to that year?
- When two prospective models of member drugs disagree before the trial (h7C10/A549 predicting near-complete inhibition; R1507 22-line panel predicting low unselected sensitivity), which is 'the best model in the context' for scoring the R1507 trial?
- Safety contra whose patient harm is documented for the same drug only in another indication (TED) while NSCLC trials of a different member (cixutumumab) show the same on-target harm: imported_from the TED id, or a direct NSCLC comparison via the pooled on-target rule?

Missed comparisons:

- safety: contra entry, model = cynomolgus monkey repeat-dose toxicology of R1507/teprotumumab (Roche reports Jul-Aug 2005, up to 39 weeks; product_in_model true), source FDA BLA 761143 Pharmacology/Toxicology review (http://www.accessdata.fda.gov/drugsatfda_docs/nda/2021/761143Orig1s000PharmR.pdf, tier 2, comparison_stated true). Quote (11.4): 'the monkey model predicted the clinical reduced weight gain/weight loss and decreased serum ALP, but not the clinical infusion reactions, exacerbation of inflammatory bowel disease, or hyperglycemia.' Executive summary: 'The monkey toxicology studies did not predict these effects.' Patient harm is in TED patients, so imported_from the thyroid eye disease MONDO id; hyperglycemia is on-target (IGF1R/IR) and also seen with cixutumumab in NSCLC (Novello 2017 9.4% vs 1.2%; E3508). Year = review posting (approval Jan 2020; file under nda/2021). Monkeys can show hyperglycemia, so this is a scored miss, not silence a species could not show.
- efficacy (candidate competing model): Gong et al. 2009 PLoS One, doi:10.1371/journal.pone.0007273 (PMID 19806209), a member-drug (R1507) NSCLC model: in 22 NSCLC lines only 5 were moderately sensitive, linked to high total IGF-1R, i.e. it predicted little benefit in unselected NSCLC. Published Oct 2009, before the Ramalingam result (Oct 2011). Not the model the draft scored; recorded so the adjudicator can decide whether it, not A549/h7C10, is the 'best model' for the R1507 trial.
- No press release, SEC filing or EMA document found reporting an additional member-drug NSCLC failure; figitumumab's NSCLC phase 3 failures are outside the member list (figitumumab is not a member) and correctly absent.
- efficacy (parallel track r1507-nsclc-cell-line-panel): likely 2011 contra, patient side Habben et al. J Clin Oncol 29:15_suppl 7584 (doi:10.1200/jco.2011.29.15_suppl.7584, NO21160 R1507+erlotinib): search-engine text of the abstract reads 'No significant impact on treatment was observed when the PFS rates of patient subgroups defined by other biomarkers, including IGF1R level, were compared'; abstract body 403 on ascopubs and absent from Europe PMC/Crossref, so it needs a verbatim read before entry.

## non-small-cell-lung-carcinoma-egfr-inhibitors

Rule questions:

- The cell shows the BEST model's status. When a different member drug's own model (mobocertinib exon 20 Ba/F3/PDX; naquotinib xenografts) fails in its Phase 3, must that model get its own scored entries in the same cell, or only a note? The rules say 'one drug's contra beats another's same on the same model' but are silent on other models within one class.
- Population when the tile gives none and members span first-line sensitising, T790M-acquired and exon 20 insertion settings: one context (EGFR-mutant) or one per biomarker? The drafter's T790M-or-exon20 choice excludes FLAURA and SOLAR.
- EXCLAIM-2 / SOLAR failed against an active comparator while the drug's activity (ORR ~30%) matched the model's prediction of regression. Is failing to beat an active comparator, which no model tested, contra or untested ('conditions the model never tested')?
- Rociletinib: regulatory rejection because unconfirmed responses overstated ORR, with no failed pre-specified primary endpoint. Is that an efficacy contra, a partial same, or unscored?
- Brain-metastasis pairing: a parenchymal brain-metastasis mouse model paired with a leptomeningeal-only trial at twice the label dose (BLOOM). Is LM disease 'a condition the model never tested' (untested) or the same CNS-activity question (same)?
- Organoid studies whose enrolment keeps only patients with response evaluations 'consistent with' the organoid test: is a selection-filtered cohort admissible as same, or should it score at most low-confidence same / untested?

Missed comparisons:

- Naquotinib (ASP8273, class member): Phase 3 SOLAR (NCT02588261, first-line EGFR-activating-mutation NSCLC vs erlotinib/gefitinib, primary PFS by IRR) terminated May 2017 on IDMC futility/benefit-risk; registry results posted 2019-02-12; Astellas press release May 2017 (e.g. fiercebiotech.com/biotech/astellas-scraps-nsclc-program-after-look-at-phase-3-data). Its own xenograft model (Hirano et al. 2015, Oncotarget; DOI not verified) predicted activity. This is outside the draft's stated population (T790M or exon 20) only because the draft narrowed it.
- Mobocertinib: an efficacy entry on its own exon 20 model (Gonzalvez 2021 Cancer Discov, Ba/F3/PDX) paired with EXCLAIM-2 (PMID 39879577, 2025; HR 1.04, crossed futility) is only noted in patient_trials, not scored; NCT04129502 has no posted results (completed 2026-09-22). Takeda withdrew the drug in 2023 (press release, tier 5).
- Osimertinib FLAURA (first-line sensitising EGFR, NEJM 2018, 10.1056/NEJMoa1713137) is the class's main efficacy datum for the same xenograft system (PC9 Ex19del models in Cross 2014) and is absent because the population excludes first line.
- Rociletinib: FDA ODAC April 2016 and complete response letter June 2016 after confirmed ORR fell to about 30% from the 59% reported earlier; hyperglycaemia in patients. Not scored; at minimum belongs in patient_trials or a note.
- Olmutinib: Boehringer Ingelheim returned rights in 2016 after fatal toxic epidermal necrolysis/SJS; a safety datum for another member on its own tox package, not recorded.
- Brain-metastasis model track: AURA3 CNS analysis (Wu et al., J Clin Oncol 2018, osimertinib vs platinum-pemetrexed in T790M NSCLC with CNS metastases; CNS ORR 70% vs 31%; DOI 10.1200/JCO.2018.77.9363 not verified here) is the randomised CNS comparison for the PC9 brain-metastasis model; secondary/subgroup endpoint, so at most a note unless marked poc_gate.
- Brain-metastasis dose track: BLOOM osimertinib LM cohort first reported at ASCO 2016 (Yang et al., JCO 34:15_suppl 9002), before Ballard 2016 epub; meeting abstract, not an admissible tier, recorded for dating only.
- Organoid track: Hu et al. 2021 Nat Commun (PMID 33972544, doi 10.1038/s41467-021-22676-1) compared lung-cancer-organoid TKI responses with patient outcomes, but for gefitinib/afatinib (outside this tile's third-gen/exon 20 class); not a track here, noted so the organoid system is not mistaken as first compared in 2023 across EGFR TKIs.

## open-angle-glaucoma-rock-inhibitors

Rule questions:

- ROCKET-1 (Study 301) failed its primary endpoint, which was non-inferiority of mean IOP to timolol, although IOP fell significantly. The model predicted IOP lowering with no comparator margin. Does an active-comparator NI primary that fails while the absolute endpoint responds count as an efficacy 'contra', or is it untested for the model? The draft kept it as a status-neutral patient_trial.
- Decision 16 margin_stated: the 2017 PharmR states NOAEL margins of 8x/2x for the chronic studies but a corneal-haze NOEL margin of 1. Is margin_stated judged on the NOAEL or on the most sensitive finding? Neither margin was shown to be public before Phase 2. Status 'same' holds either way.
- When the system relied on is an IOP-lowering model in normotensive animals, should a failed sibling-member drug with model data only in a conference abstract (ATS907 ARVO 2011) be admissible on the model side (tier 1 needs DOI/PMID)?
- efficacy 4: an undirected genotype hypothesis ('may influence response') meets an underpowered null (aOR 1.31, CI 0.42-4.10). Is that a failed prediction (contra) or no patient result (untested)? The rules decide neither undirected predictions nor underpowered nulls outside terminated trials.

Missed comparisons:

- ATS907 had public model data: Hsu & Kengatharan, ARVO 2011, 'Safety and Efficacy of a Novel Topical Rho Kinase Inhibitor ATS907 in Normotensive Cynomolgus Monkeys' (https://iovs.arvojournals.org/article.aspx?articleid=2360870): single-dose IOP -3.7/-4.65 mmHg vs -2.43 latanoprost, plus a rabbit abstract. The draft's note says 'no public model data' for ATS907; this is wrong. The Phase 2 failure (NCT01520116 status unknown, NCT01668524 no results) is known only from the Wang & Chang 2014 review, so it is not scorable without a tier 1-5 patient source. If one is found, ATS907 would be a contra on a normotensive-monkey IOP model.
- DE-104 Phase 2 trials NCT00650338, NCT00657579, NCT00656240, NCT00868894 are registered with no posted results. The discontinuation for a missed primary endpoint (late 2010) appears only in the review; no Santen tier 5 document was found in budget, and no DE-104 model data was found.
- Ripasudil (K-115, Kowa; approved Japan 2014) is a ROCK inhibitor for POAG/OHT with its own rabbit/monkey IOP models (e.g. Isobe 2014, Curr Eye Res) and Japanese patient trials (Tanihara 2013, Am J Ophthalmol); no track if it is in the class. Not verified in budget.
- AR-12286 (Aerie's earlier ROCK inhibitor) had monkey IOP data and a Phase 2 patient trial (Williams 2011, Am J Ophthalmol) before netarsudil; a member drug's own model with no track. Not verified in budget.

## osteoarthritis-ntrk1-inhibitors

Rule questions:

- Dose, decision 4: when the trial paper itself states after the failure that plasma levels were 'well above the IC50 reported in pre-clinical models' (total drug), the dose was chosen on a toxicity ceiling with the pre-clinical dosing data 'on file', and the unbound trough (111 nM) fell below the in-vitro IC50 (155 nM), is this case 3 (reached, failed, abandoned: contra derived_from efficacy) or the post-hoc PK/PD clause (untested, source_calls_it scaling)? Which exposure measure, total or unbound, peak or trough, counts as 'reached'?
- Class boundary, decision 12: GZ389988's own sponsor reports similar IC50s for TrkA, TrkB, TrkC and CSF1R (0.89/0.38/0.5/1.3 nM) and the editorial raises CSF1R as a contributor to its analgesia, yet the tile lists it as an NTRK1 inhibitor. Does a member stay in the class when its own sources describe it as pan-Trk/CSF1R, and is its injection-site joint inflammation an on-target harm (pooled) or a formulation harm?
- Human genetic models, decision 8/4: Watt 2019 puts human NTRK1 loss-of-function (insensitivity to pain) beside the failed ASP7962 trial and attributes the gap to the completeness and duration of blockade. Is a lifelong complete loss-of-function ever an admissible model of a 4-week partial inhibitor, and if so is this pairing untested (conditions the genotype never tested) or contra?
- Track identity, decision 8: Flannery's rat IA biocompatibility study used naive rat knees, while the efficacy model is rat MIA knee OA. Is a naive-joint tolerability study the same system as the rat MIA track for safety (one species, one route, one compound programme), or its own model_id?
- Human genetic models, decision 4 symmetry (models check): if ASP7962's failure cannot contradict the CIPA genotype / TrkA-null tracks because a partial 4-week inhibitor never produced the genotype's condition (proposed untested), can GZ389988A's met 4-week primary confirm them? Krupka cites the genotype only in its intro (ref 25), a bare-citation (b) pairing; by the same logic that pairing should also be untested, which leaves both genetic tracks untested throughout.
- Track identity, decision 8 (models check): the Flannery 2015 rat IA biocompatibility statement is now the model side of two contra entries, rat-mia-knee-oa safety index 2 (adjudicated) and rat-naive-knee-ia-tolerability safety index 5 (this check). Naive-knee tolerability is a different experiment from MIA knee OA, so the new track is the better home and the rat-MIA safety contra should revert to untested; whichever is chosen, the comparison must be counted once.

Missed comparisons:

- Flannery CR et al. 2015, 'Efficacy of a novel, locally delivered TrkA inhibitor in preclinical models of OA and joint pain', Osteoarthritis Cartilage 23(Suppl 2):A45-A46, DOI 10.1016/j.joca.2015.02.100 (OARSI abstract, April 2015): GZ389988's own rat MIA single-IA-injection model, rat PGPS flare model and rat IA biocompatibility study. Cited by Krupka 2019 (ref 28: 'In rat models of OA and joint pain, GZ389988 showed a significant relief of local knee pain'), so the GZ389988A efficacy pairing is comparison_stated with product_in_model true (same, subordinate to ASP7962 contra on the same track), and the rat biocompatibility silence on joint inflammation is the model side of the safety contra proposed above. The draft said this abstract could not be located.
- Human NTRK1 loss-of-function (HSAN IV / congenital insensitivity to pain) as a human_genetic track: Watt 2019 (DOI 10.1016/j.joca.2019.05.029, full text) sets it beside the failed trial: 'Individuals with mutations of the TrkA receptor, either in humans or in pre-clinical models, have insensitivity to pain, suggesting that TrkA is a valid analgesic target', then attributes the gap to the degree and duration of blockade. No track in the draft; likely untested (conditions the genotype never tested) rather than contra; see rule question 3.
- NGF-receptor knockout mouse (Watt 2019 ref 7): cited in the same discussion as pre-clinical evidence against the 'more complete blockade needed' explanation; a mouse genetic model placed beside the patient result with no track.
- GZ389988 first-in-human study NCT02424942 (Genzyme/Sanofi, Phase 1, 28 knee-OA patients, ascending single IA doses, April 2015 to July 2016): secondary endpoints were plasma and synovial-fluid PK and WOMAC pain over 12 weeks; no results posted, no publication found. This, not NCT02845271, was the escalation study; it is the only patient-side PK source for the IA member and should be recorded on the dose/engagement cells as unreported.
- ASP7962 Phase 1 healthy-volunteer studies NCT01981928 and NCT02136316 (Watt 2019 full text: single doses up to 240 mg, favourable safety; 100 mg BID was the highest dose with safety data when Phase 2 started): healthy-volunteer PK counts for the dose cell under v3; no results posted, no publication, so no status change, but the draft does not cite them.
- Not searched for budget: Astellas, Sanofi and Purdue discontinuation notices (tier 5) for ASP7962, GZ389988A and VM902A; none would change a status since the tier 1 trial papers and the registry termination record already set them.

## ovarian-cancer-parp1-2-inhibitors

Rule questions:

- Safety: when an FDA review says animal findings were 'consistent with' the dose-limiting harms but explicitly notes a common patient harm the species could have shown (rucaparib ALT/AST, 74% incidence) was absent, is that same + partial or contra (silence contradicted)?
- Efficacy: does outcome_tested apply when the trial primary endpoint (PFS) is met but later OS shows detriment (ARIEL4) — i.e. is PFS a 'surrogate the model predicted' in oncology, and should an OS detriment ever move an efficacy cell?
- model_change: is it meaningful on an entry that follows a same (not contra) entry with a different model, or should lint reject model_change: true unless the previous entry is contra?

Missed comparisons:

- ARIEL4 (rucaparib vs chemotherapy, BRCA-mutant relapsed ovarian; NCT02855944, results posted 2022-02-11): primary invPFS met (Kristeleit, Lancet Oncol 2022), but final OS 19.4 vs 25.4 months (Lancet Oncol 2025, PIIS1470-2045(24)00674-0); FDA treatment indication voluntarily withdrawn June 2022. Status stays same on the primary endpoint, but efficacy should carry this as a patient_trials item / outcome_tested: negative.
- NOVA final OS (gBRCA HR ~0.85, not significant; non-gBRCA OS detriment) led to the 2022 restriction of niraparib 2L maintenance to gBRCA; relevant to outcome_tested, not to the PFS-based status.
- Stenoparib (2X-121, member) phase 2 NCT03878849 in platinum-resistant ovarian cancer, DRP-selected not BRCA-selected; sponsor press releases only (Allarity 2025), positive in tone, outside the BRCA/HRD population; no failure to add.

## paroxysmal-nocturnal-hemoglobinuria-anti-c5-antibodies

Rule questions:

- Dose: the monkey-based paper claimed a recycling antibody needs 'a much lower trough' than the ~99 µg/mL a conventional antibody needs, yet patients needed ~100 µg/mL. The regimen still worked. Is a wrong qualitative exposure claim with a working regimen 'same' with magnitude opposite or unquantified, or 'contra' (target too low)? Decision 16 and the dose table do not cover this case.
- Efficacy for a follow-on member (ravulizumab) rested on non-inferiority to a non-member (eculizumab) plus an engagement assay. Does that count as an efficacy model, or as 'no disease model relied on' (empty list)? It is close to the cross-indication case but sits in the same indication.
- model_change: is it meant only for turning a cell back after a contra, or also for any switch of model between entries? The draft uses it for both, and lint does not check it.
- Safety cell with two distinct harms (meningococcal infection; DTDC hypersensitivity), each predicted by a different model: should these be separate entries scored independently, or one entry per change of best-model status as now?

Missed comparisons:

- Pozelimab + cemdisiran (ACCESS-1, NCT05133531; Regeneron press release and Lancet 2026) was positive against ravulizumab in PNH. The combination includes an siRNA, so it is optional in patient_trials and does not change status. Source: https://pmlive.com/pharma_news/regeneron-shares-positive-late-stage-results-for-poze-cemdi-in-rare-blood-disorder-pnh/
- Tesidolumab: Novartis stopped development in favour of iptacopan, a strategic choice and not an efficacy failure. Worth a note so it is not read as a failure. Source: NCT02534909 / Novartis trial results.
- Pozelimab's FDA review in the bundle (BLA 761339) is for CHAPLE disease, not PNH. It cannot serve as a PNH source, and the draft correctly does not use it.
- COMMODORE 1 C5-polymorphism cohort (FDA crovalimab integrated review 2024, BLA 761388): one subject 'discontinued the study treatment on or after 24 weeks of treatment due to lack of efficacy'. It is a later patient result for the c5-r885h-variant-hemolysis-assay track and has no entry of its own. The cohort's genotype-level hemolysis data should be sought before it is scored.

## plasma-cell-myeloma-tnfrsf17-directed-depleters

Rule questions:

- Safety: when the model showed the harm but its own report called it non-adverse (Blenrep corneal necrosis 'considered non-adverse') and patients had severe keratopathy, is that a predicted harm that held (same, direction_only) or a stated 'no adverse finding' contradicted (contra)? Rules decide neither.
- Efficacy: a confirmatory phase 3 vs an active comparator that misses (DREAMM-3) while single-agent activity is reproduced: is the comparator 'a condition the model never tested' (untested) or a primary-endpoint miss (contra)? The rule list names untested only when the trial source attributes the result to untested conditions; GSK attributed it to nothing.
- Engagement: may a phase 1 whose primary endpoint is safety supply the engagement entry when its readout (marrow plasma-cell clearance) is effectively the efficacy readout of the xenograft?
- Class-level post-marketing harms (CAR-T T-cell malignancy boxed warning) shared with CD19 products: score in this context or import?
- Efficacy index 4 (ide-cel response by tumour BCMA level): a patient-selection prediction scored on a phase 1 subgroup of a secondary end point (ORR; primary was safety) with endpoint_role null. Should such patient-level selection entries require endpoint_role poc_gate, or are they exempt from the secondary-endpoint rule?
- Dating when the patient result (ASH 2017 abstract) is public before the model's first publication (Friedman 2018) but the model data were filed pre-trial: may the opening untested entry be dated earlier than its publication to keep the strip ordered?

Missed comparisons:

- DREAMM-3 primary PFS miss (HR 1.03) was public 2022-11-07 via GSK press release / SEC 6-K (https://www.sec.gov/Archives/edgar/data/1131399/000165495422014760/a4558f.htm); patient_trials cites only the 2026 final analysis DOI with a title as its quote and should cite the 2022 record, the first public date.
- Ide-cel insertional-oncogenesis prediction: Abecma SBRA states integration-site analysis 'does not preferentially integrate in or near genes of concern for oncogenic transformation' and an IL-2-independent growth assay 'showed no signs of uncontrolled cellular proliferation' (ex_vivo model). FDA required a class boxed warning for T-cell malignancies, including CAR+ cases, on BCMA- and CD19-directed CAR-T incl. Abecma (Jan-Apr 2024; https://www.onclive.com/view/fda-requires-boxed-warning-for-risk-of-t-cell-malignancies-with-approved-car-t-cell-therapies). A candidate cell-therapy safety entry (contra or untested, depending on whether any ide-cel case was CAR+); not verified at product level here.

## prostate-cancer-ar-antagonists

Rule questions:

- Safety: when the filed animal toxicity (dog convulsions at a Cmax at or near the human Cmax) predicts a harm at clinical exposure and patients show it at 0.2%, is that 'same' in direction, or does the magnitude need to be recorded as over_predicted?
- Rule 6 opener: when the model's first use (2010 dog study) became public only in the same document that carries the comparison (2018 FDA review), is an untested opener at model_first_use_year still required? The draft skipped it and lint did not flag it.
- Population mismatch for a member drug on its own model: if a castration-resistant (NHA-naive) xenograft is paired with a post-abiraterone phase 3 failure (proxalutamide), is the cell untested under 'conditions the model never tested', or contra?
- Patient-level parallel tracks (efficacy 6): when the model predicts a resistance mutation and the patient datum is an exploratory cfDNA finding in progressing patients (not a trial endpoint, no carrier vs non-carrier comparison), does it count as an admissible 'primary' efficacy comparison, or should it be untested?

Missed comparisons:

- Proxalutamide (pruxelutamide, a class member) has an in-vivo model: Zhou 2020 Eur J Cancer, doi:10.1016/j.ejca.2020.04.013 (PMID 32460179), 'The efficacy of GT0918 was investigated in a castration-resistant xenograft model' plus phase 1 (PSA>=50% in 2/16). The draft's claim that its preclinical work is cell lines only is wrong. Kintor announced (Sept 2020 IDMC; tier 5, e.g. Kintor 2020 interim results, en.kintor.com.cn/news/131.html) that the 2L+ mCRPC phase 3 missed interim rPFS. It needs its own model_id entry in efficacy: probably untested (model never tested post-abiraterone/docetaxel disease), otherwise contra. The trial population was not verified.
- Darolutamide's own model (castration-resistant VCaP xenograft; FDA review NDA 212099, lines ~1364-1378) is only mentioned in a judgement. As a different system, it should get its own model_id entries (efficacy vs ARADES NCT01317641 / ARAMIS; safety, where mouse brain:plasma was low and ARAMIS seizures were 0.2% in both arms).
- Rezvilutamide (SHR3680): CHART phase 3 in high-volume mHSPC was positive, but no published in-vivo model was found, so no entry is needed. TRC-253 (JNJ-63576253): preclinical xenografts in Branch 2021 MCT (doi:10.1158/1535-7163.MCT-20-0510); the phase 1/2a primary endpoint was DLT, so it is unscored, as the draft says.
- Enzalutamide's own F876L resistance models: Korpal 2013 Cancer Discov (doi:10.1158/2159-8290.CD-13-0142, PMID 23842682; resistant LNCaP-derived lines) and Balbas 2013 eLife (doi:10.7554/eLife.00499; mutagenesis screen) predicted F876L resistance; Azad 2015 Clin Cancer Res (doi:10.1158/1078-0432.CCR-14-2666) reported F876L in cfDNA of an enzalutamide-progressing patient and AR aberrations predicting lower PSA response. They could join the arn509-resistant-cell-lines-f876l track (product_in_model per drug) if enzalutamide is a member.

## psoriasis-anti-il17a-antibodies

Rule questions:

- Dose, decision 16: the 9-month cynomolgus NOAEL existed in the IND before Phase 3, but the only public statement of the margin is the 2015 FDA review, written after the trials. Does 'a model source stated the margin before the trial' mean the sponsor's filed data (model_filed: true) or a public source dated before the trial?
- Safety, IBD: Puel 2011 says IL-17A/F are 'otherwise largely redundant', which predicts no other harm, but the label warns of new or worse Crohn's disease and UC (0.1%/0.2% vs 0%). The rules don't say whether a small human genetic cohort 'could have shown' a harm this rare. If it could, the silence contradicts the label (contra); if not, it is no miss. The drafter took the second reading and did not score it.
- Efficacy, magnitude: when the model's claim is relative potency (izokibep 30-fold more effective per mg/kg than ixekizumab) and patients needed the same mg dose, should magnitude be scored on dose (off_by_>5x) rather than left direction_only on PASI 90?

Missed comparisons:

- No failure found for any member (ixekizumab, izokibep, netakimab, vunakizumab) in psoriasis. Positive patient trials not listed in patient_trials (they would change no status): vunakizumab Phase III (e.g. PMID 42952621, doi 10.3389/fimmu.2026.1894231) and netakimab Phase III PLANETA (citation not retrieved in budget). No press-release or SEC search was run for izokibep's later program; any failures I know of are outside psoriasis (not verified here).

## psoriasis-rorc-inverse-agonists

Rule questions:

- When the topical drug fails the engagement readout in the same biopsied field, does the efficacy cell become untested (target not reached, decision 4 row 1) even though the engagement model, not a PK model, set the target? The dose table is written for exposure. The draft scored engagement and efficacy both contra, so one failure counted twice.
- Engagement entry 3: the 'model' (human whole-blood ex vivo IL-17 assay) and the human readout (the same assay on dosed subjects' blood) are the same measurement. Does a human ex-vivo assay whose own readout is repeated in dosed humans count as a model prediction that can turn back a contra, or is it close to tautological?

Missed comparisons:

- Engagement, VTP-43742: a peer-reviewed healthy-volunteer PK/PD paper ('Safety, tolerability, pharmacokinetics and pharmacodynamics of VTP-43742, a RORγt inhibitor, in normal healthy volunteers', ResearchGate 366800762, c. 2022-23) is a tier-1 source for the whole-blood IL-17 readout; it does not predate the 2021 registry date, so it adds no status change. Not opened.
- Efficacy patient_trials: NCT03835481 (BI 730357 long-term extension) TERMINATED 'Due to company decision', results posted 2022-11-18. This was a program stop, not an efficacy failure under decision 4 ('Failed' ≠ development stopped).
- Safety: NCT03339999 registry gives whyStopped 'safety reason' (verified). The draft says so, but no source says what the safety signal was.

## rheumatoid-arthritis-btk-inhibitors

Rule questions:

- Safety silence and species capability: does a dog toxicology study that measured platelet aggregation as 'unremarkable' count as a model silent on a harm the species could have shown, when human BTK-inhibitor bleeding is mediated by GPVI platelet signalling whose BTK dependence differs across species (Tec compensation in rodents)? The rules do not say who decides species capability or on what evidence.
- Dose for a failed drug whose dose basis is unpublished (BMS-986142, poseltinib): the dose table assumes we know whether the model's exposure target was reached. When no source states the dose basis, is the dose entry untested (draft's implicit choice) or does efficacy contra still stand without the dose check (draft scores efficacy contra on BMS-986142 regardless)?

Missed comparisons:

- Safety, imported_from mantle cell lymphoma (acalabrutinib is a member): FDA NDA 210259 Multidiscipline Review (2017, https://www.accessdata.fda.gov/drugsatfda_docs/nda/2017/210259Orig1s000MultidisciplineR.pdf, in the source bundle) reports the 91-day dog study 'Platelet Aggregation: Unremarkable' and nonclinical platelet assays showing 'fewer effects than ibrutinib', while 39/124 (31.5%) of pivotal MCL patients had hemorrhage (1 major). A paired (comparison_stated false) on-target-harm entry, likely contra (model silent on bleeding) dated 2017 if the dog is judged able to show BTK-dependent platelet dysfunction; TAS5315 bleeding in RA (Takeuchi 2023) is the in-disease echo. See rule question.
- Efficacy patient_trials: NCT02387762 (acalabrutinib + MTX, Phase 2) registered primary endpoint was DAS28-CRP at week 4; registry results 2019-03-26 show 5.40 vs placebo 5.05 (no analysis posted). It is the earliest member primary-endpoint miss, not exploratory; same year as the cell's contra, so no status or year change.
- Efficacy/dose: spebrutinib NCT01975610 registered primary was ACR20 at week 4 (not met, 41.7% vs 21.7%, P=0.25, Schafer 2019 epub 2019-11-13) with median patient BTK occupancy 83%: a member that reached the model's occupancy target and missed its primary endpoint in 2019, independent of the BMS-986142 dose question.

## rheumatoid-arthritis-syk-inhibitors

Rule questions:

- What tier is a peer-reviewed-society meeting abstract with no DOI or PMID (ACR 2014, Arthritis Rheumatol suppl)? Decision 2 tier 1 needs a DOI/PMID; tier 5 is never allowed for the model side, yet here the ONLY model source for MK-8457 (rat AIA/CIA, 69% PK-PD target) is such an abstract. The whole rat track rests on it.
- Decision 16: does a sponsor's healthy-volunteer MAD tolerability statement (200 mg BID x10 d) count as a 'stated margin', given it is clinical data, not a model? If yes, MK-8457's 24-week serious infections at 100 mg BID are toxicity at the effective exposure (dose contra, blocked_by toxicity) rather than a safety miss; the 'counted once' clause points to safety because nothing predicted infection, but then margin_stated=true on a dose same entry is contradictory.
- A trade-press report of a sponsor's exchange disclosure (Korea Biomedical Review quoting Oscotec) is not a press release or SEC filing: admissible as tier 5? And when a tier-3 registry record of the same trial later posts (2024-07-31), does the entry keep the tier-5 src and 2021 year (decision 7, earliest public date) or move to the registry src, 2024 and trial_unreported=false?
- A development model published only after the trial failed (Cho 2023, received 2022-09, trial topline 2021-01), with no public pre-trial record and no mention of the trial: prospective (retrodiction=false) or retrodiction? Status is contra either way, but the mark differs.
- Does the safety cell accept a healthy-volunteer comparison (lanraplenib cynomolgus bleeding time vs Phase 1 humans, Clarke 2018)? Decision 3 names engagement and dose only.
- A member drug whose only published model is another indication's (lanraplenib, NZB/W lupus) and whose RA trial failed: decision 12 says cross-indication transfers only for safety, so the failure has no efficacy track and is invisible on the tile. Should a class failure with no published model be surfaced some other way than inside another drug's patient_trials?

Missed comparisons:

- Engagement entry on the cynomolgus-bleeding-time-lanraplenib track: Clarke 2018 (10.1016/j.thromres.2018.08.012) reports ex vivo GPVI-stimulated platelet aggregation inhibited in both GS-9876-dosed monkeys and humans, a direct readout in healthy volunteers; the draft uses the paper only for safety.
- Lanraplenib RA Phase 2 conference record: Kivitz et al., ACR 2018 abstract 2518 (https://acrabstracts.org/abstract/gs-9876-a-novel-highly-selective-syk-inhibitor-in-patients-with-active-rheumatoid-arthritis-safety-tolerability-and-efficacy-results-of-a-phase-2-study/), 'Clinical efficacy of GS-9876 in RA was not observed'; also reports patient PK comparable to HV and ex vivo whole-blood PD differences vs placebo. No published arthritis model to score it on (Blomgren 2020 ACS Med Chem Lett abstract and BMC Rheumatol 2021 name only NZB/W lupus; Blomgren full text paywalled, not checked), so no status change unless its full text carries an arthritis model.
- Sponsor-side record for the cevidoplenib RA miss: Oscotec's own 2021-01-07 disclosure (KRX/DART filing) was not located; the draft's tier-5 source is a trade-press report of it. The ITP PRNewswire release (2023) is another indication and not relevant.
- Not missing but noted: entospletinib in K/BxN (Kaposztas 2023, 10.3389/fimmu.2023.1279155) is a non-member sibling; correctly left unscored.

## schizophrenia-pde10a-inhibitors

Rule questions:

- Does a peer-reviewed congress abstract with a DOI (journal supplement poster) count as tier 1 for dating, or only as 'data not shown' with low confidence? It decides whether efficacy contra here is 2012 or 2016.
- When a cell's first sourced entry (2014) comes after model_first_use_year (2008), should the opening untested entry be backdated to model_first_use_year with an earlier source, or does lint accept the gap?
- A conclusion that a model 'refutes the hypothesis' in a trial paper that names the preclinical rationale: is that comparison_stated true, or a pairing under evidence rule 1?
- The TAK-063 healthy-volunteer ketamine challenge (run 2013-14) was prospective for TAK-063 but run after a class member (PF-02545920) had failed in patients (2012), while prediction_level is 'class'. Is a class-level model run after another member's failure a retrodiction? Here status is contra either way.

Missed comparisons:

- DeMartinis et al. 2012, 'Results of a phase 2A proof-of-concept trial with a PDE10A inhibitor in the treatment of acute exacerbation of schizophrenia', SIRS Poster #212, Schizophrenia Research (April 2012), doi 10.1016/s0920-9964(12)70783-1: PF-02545920 monotherapy not superior to placebo. This dates efficacy contra to 2012, and reportedly says PK suggested striatal engagement like that in the preclinical models (possibly dose contra 2012 as well). I saw only the title/Crossref record and a search snippet.
- OMS824 (member): Omeros suspended its PDE10 trials in Oct 2015 after a rat high-dose toxicology finding (Omeros press release 2015, https://www.prnewswire.com/news-releases/omeros-provides-update-on-pde10-inhibitor-program-322137646.html; 10-K FY2015). This is not a patient comparison, so it does not score, but the draft does not mention it.
- Lu AF11167 NCT03793712 (stopped for futility, completion 2020-08-20, no results posted): the draft lists it with registry_date null. A Lundbeck disclosure could date it, but it does not change the status.
- Roche RG7203 (PDE10A inhibitor) reward-processing fMRI/MID model in healthy volunteers, then tested in chronic schizophrenia patients where reward-processing improvement was absent: Schizophr Bull 2018 suppl abstract S43, https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5888501/ (search snippet only; also summarised in Frontiers Neurosci 2020, doi 10.3389/fnins.2020.600178). A human-model parallel track for the efficacy (negative symptoms) question, likely contra; RG7203 membership in the class needs confirming.

## type-2-diabetes-mellitus-gck-activators

Rule questions:

- Dose: does a semi-mechanistic model fitted to the drug's own patient MAD data (LY2599506 GIG model) count as a 'model' with model_change: true that can turn a contra cell back to same? It is a human-to-human extrapolation, not a preclinical system, and its trials stopped before efficacy was fully shown.
- Safety: when a model's only public sources are pharmacology papers (no tox review, no NDA), is their silence on a harm the species can show (rodent triglycerides) enough to score contra when patients show it?
- Efficacy: can a human-genetic rationale for a hepatoselective drug (TTP399) count as the model for later, non-hepatoselective members (dorzagliatin), or is it a separate model_id limited to the drugs designed from it?
- Dating: TTP399 Phase 2 results were presented in 2016 (ADA), before Vella 2019. Does a conference abstract or press release set the entry year under rule 6?
- Model-informed drug development papers (Liu 2017 sinogliatin PK/PD) published after the first-in-patient data, claiming a learn-research-confirm projection: without a dated pre-trial record of the projection, does the default fall to retro (checker) or to the paper's framing (drafter)?
- Two-arm drug-target MR (GCK vs GCKR proxies) under one model_id: when one arm reproduces the class harm and the other contradicts it, which arm is the class proxy? Safety 7 scores the GCK arm contra on dorzagliatin's TG rise.

Missed comparisons:

- safety 2011: MK-0941 raised triglycerides (and hypoglycaemia) in patients (Meininger 2011, doi 10.2337/dc11-1200), while the rodent model of record (Eiki 2011) was silent on lipids that rodents can show (De Ceuninck 2013). Arguably contra (silence contradicted), which would keep later rodent-model safety entries from flipping to same.
- dose 2011: MK-0941 dose reached and the Week-14 primary met (Meininger 2011): the 'reached, drug worked' row gives dose same in 2011 before the AZD1656 contra.
- efficacy patient_trials: PF-04991532 (hepatoselective member) met the 12-week HbA1c primary in NCT01336738 (450 and 750 mg vs placebo, p=0.0017 and 0.0003; results posted 2013-08-06) and NCT01338870 (results 2013-04-23). No status change.
- efficacy patient_trials: PF-04937319 (nerigliatin) met the 12-week HbA1c primary at 100 mg (-0.45 to -0.47%) in two studies, Amin 2015 doi 10.1111/dom.12474. No status change.
- safety: LY2599506 Phase 2s (NCT01024244, NCT01029795) were terminated for 'nonclinical safety findings'. The model flagged a harm before patients showed it, and nobody compared it in patients, so it is not scored but is worth a note.
- safety: Baker 2014 (doi 10.1111/bph.12504) is a rodent model that showed no triglyceride rise, against the patient hyperlipidaemia signal. It is a second rodent result that conflicts with De Ceuninck.

## type-2-diabetes-mellitus-glp1r-agonists

Rule questions:

- Rule 5/12: when the only human null for an on-target class harm is a pooled cohort in which non-member drugs (here liraglutide) dominate, does it count for the member class at all, or only for the member share, and how is that share recorded?
- Rule 7: when the patient source (Kapitza, Jan 2015) predates the publication of the model source (Lau, Sept 2015) but the model was used prospectively before the clinic, is the paired entry dated to the later publication, or to the patient source with the model's use year as proxy?
- Safety silence: a single tier-5 liver-injury case in another indication (obesity), which the sponsor says sits at class-background rates. Is that a contradicted silence, or does it need a tier 1-4 patient source before it can be scored?
- Ala316Thr genetics (safety 5/6): the analysis was done before, but first published after, the SUSTAIN-6 topline press release (2016-04-28). Decision 10 requires post-dating AND being motivated by the patient result; does first-public date alone make it retro? Scored same here.

Missed comparisons:

- Dose (semaglutide, peptide): earlier patient PK source Kapitza 2015, J Clin Pharmacol, doi:10.1002/jcph.443 (PMID 25475122), and phase 2 dose-finding Nauck 2016 Diabetes Care doi:10.2337/dc15-0165 (epub 2015-09-10); either dates the semaglutide dose comparison to 2015 instead of the 2017 label.
- Safety (danuglipron, small molecule, imported_from obesity): Pfizer 2025-04-14 discontinuation after one case of possible drug-induced liver injury in an obesity dose-optimisation study (tier 5; e.g. https://www.cnbc.com/2025/04/14/pfizer-scraps-daily-weight-loss-pill-danuglipron.html). Pfizer says overall liver-enzyme rates matched approved GLP-1 RAs; scorable only if a tier 1-3 tox source states hepatic silence, otherwise untested at most.
- No missed efficacy failures found for other members: TTP273 phase 2 positive (vTv 2017, placebo-subtracted HbA1c -0.86/-0.71%), CJC-1134-PC phase 2 HbA1c fell vs placebo (NCT00638716/NCT00674466), efpeglenatide AMPLITUDE programme positive; LY2428757 discontinuation reason not found.
- Safety (semaglutide): SUSTAIN-6 headline press release 2016-04-28 (https://www.globenewswire.com/news-release/2016/4/28/1600310/0/en/semaglutide-significantly-reduces-the-risk-of-major-adverse-cardiovascular-events-in-the-sustain-6-trial.html) predates Scott 2016 publication (2016-06-01); the safety 6 confidence_note should record it.

## type-2-diabetes-mellitus-slc5a2-inhibitors

Rule questions:

- Track granularity: does a family of rodent hyperglycaemia models (90%-pancreatectomized SD rat, ZDF rat, db/db mouse) count as one model_id, as the draft's t2dm-rodent-diabetic does, or is each strain its own track?
- Decision 16 timing and ownership: a 5-7x margin first stated in the 2013 NDA pharmacology review (2-year carcinogenicity completed during phase 3), while FDA identified no chronic-tox NOAEL (hyperostosis and Leydig tumours below 1x MRHD): does it satisfy 'the model stated the effective exposure was tolerated' for margin_stated true? And which track owns a dose entry whose efficacy exposure comes from the ZDF rat and whose margin comes from SD-rat toxicology?
- Human-genetic retrodiction in a general population (UK Biobank Mendelian randomization, mostly non-diabetic) set against T2DM trials: does 'patients of the context's disease only' bind the model side, or only the patient side?
- Cross-member pairing on one track: may a prediction the model made for member A (canagliflozin rat Leydig tumours) be scored against member B's patients (bexagliflozin) when member B's own run of the same model made no such prediction?
- A model that names the right organ with the wrong direction (rat bone accretion and hypercalciuria; human BMD loss and fractures, found by the bone monitoring the rat prompted): contra with magnitude opposite, as drafted, or same with source_calls_it partial? And may a 14-carrier human LoF phenotype ('glucosuria without hypoglycemia') be paired against trial hypoglycaemia rates as a same?
- Decision 10 'known': does a patient result count as known from the sponsor's run (canagliflozin FIH NCT01177150 completed 2007-04) or from publication (Sha 2011-07)? The Sglt2-null engagement pairing is prospective only on the latter; and does a non-member's public UGE result (dapagliflozin, 2009) make a 2011 knockout a class retrodiction?
- Safety partial agreement across sources: Ly 2011 named four harms; infection and volume depletion held, weight loss stands in for malnutrition, mortality did not. Decision 11 'partial' is written for one source's readouts; is a drafter-assigned partial admissible when the label never cites the model, or does the mortality miss make it contra?
- Dose 'same' dating: when healthy-volunteer PK is reached years before efficacy is shown (ertugliflozin 2011 vs 2017), is the entry dated at the PK or at the first primary-endpoint success?

Missed comparisons:

- Canagliflozin in DBA/2J diabetic and control male mice (10 weeks, microCT): increased bone resorption and trabecular loss, the human direction, published after the 2013 FDA reviews had noted BMD loss and fractures and before Bilezikian/Watts. A retrodiction (retro) on a new mouse-bone track, not the SD-rat 2-year tox system. Thrailkill et al., Bone 2016;82:101-107, doi 10.1016/j.bone.2015.07.025, PMID 26211996, epub 2015-07-23.
- Sglt2-knockout mouse (HFD and db/db backgrounds): prevented hyperglycaemia and preserved beta-cell function, a prospective 2011 genetic-animal model of the mechanism with no drug; no track in the draft. Jurczak et al., Diabetes 2011;60:890-898, doi 10.2337/db10-1328, PMID 21357472.
- Ertugliflozin, a listed member, has no entry in any cell. The combined FDA pharmacology review (NDA 209803/209805/209806, 2017) exists at https://www.accessdata.fda.gov/drugsatfda_docs/nda/2017/209803,209805,209806Orig1s000PharmR.pdf (the bundle's single-NDA URLs 404) and, per its indexed text, reports glucosuria and kidney alterations in rats and dogs at clinical exposure; FDA rate-limited this session so it was not read. Its label (bundle 209803s000lbl.txt) carries 5.5 Lower Limb Amputation at approval.
- Tofogliflozin, a listed member: its own rodent model paper (db/db mice and diabetic rats) could strengthen the rodent track and date a second prospective member before 2023. Suzuki et al., J Pharmacol Exp Ther 2012, doi 10.1124/jpet.112.191593, PMID 22410641.
- Canagliflozin lower-limb amputation: FDA boxed warning 2017 from CANVAS, removed 2020-08-26 (https://www.fda.gov/drugs/drug-safety-and-availability/fda-removes-boxed-warning-about-risk-leg-and-foot-amputations-diabetes-medicine-canagliflozin). An unpredicted harm absent from the safety narrative; no species could show it, so no status change, but the 2013 safety note should carry it beside DKA.
- Rat euglycaemic-ketoacidosis retrodiction (dehydration plus insulinopenia with an SGLT2 inhibitor in healthy and T2DM rats), Perry et al., Nat Commun 2019, doi 10.1038/s41467-019-08466-w. Run with dapagliflozin, which is not on this tile's member list, so it does not score here; flag for the T1DM tile or a class-level note.
- Enavogliflozin, a listed member: no rodent-efficacy source found by Europe PMC title search (only a PK/tissue-distribution paper, PMID 35745783); the Korean approval dossier was not searched. Not verified.
- Sha 2011 phase 1 registry: NCT01177150 (canagliflozin first-in-human, healthy men; start 2006-11, primary completion 2007-04, first posted 2010-08-06, no results) fills the null registry_date on engagement 4 (checker, CT.gov API v2).
- Ertugliflozin human ADME paper (DMD 2013, Miao et al., doi 10.1124/dmd.112.049551) reportedly gives oral clearance within 1.5-fold of the allometric prediction: a within_2x magnitude for dose 4 instead of null. Seen only in a search snippet; not verified.
- Vallon et al. 2011 JASN Sglt2-/- mouse (PMID 20616166, doi 10.1681/asn.2010030246, epub 2010-07-08, print 2011-01): the same Slc5a2-null system, public six months before Ly 2011 (print 2011-01-01) and Jurczak 2011; the slc5a2-null-mouse opener and model_first_use_year should move to 2010 (Europe PMC, checked).

## ulcerative-colitis-s1pr1-agonists

Rule questions:

- Decision 16 and margin_stated: the etrasimod NOAEL studies were IND-enabling (pre-trial), but the multiple at MRHD (738x/446x) is stated only in the 2023 review, after the trial. Does a pre-trial filed NOAEL count as a margin 'stated before the trial'?
- Decision 16: the rat liver findings fell at >1000x MRHD, but patients at 2 mg had ALT elevations (label 5.3) that did not block dosing. Is that a misplaced-margin dose contra, a safety entry, or neither?
- Can a retro entry (safety 3, model_change true) follow a contra and be drawn as the cell's latest status, or does a contra stand until a prospective prediction holds?
- When the drafter's chosen model (S1P3-KO mouse, a design rationale in the literature) differs from the filed safety system (cynomolgus CV study), which one is 'the model the class relied on' for the safety cell, and do both get entries?
- Scott 2016 was received Aug 2015, after the TOUCHSTONE topline (Oct 2014 press release), but the mouse colitis experiments probably predate the trial. Is a model paper published after the patient result a retrodiction when the experiments were run earlier?
- Prediction_level class: ozanimod's monkey CV study (c.2012) and etrasimod's hERG/tox ran before their own patients but after fingolimod's class bradycardia was known (2006+). Is a filed product-specific study run after the class result a retrodiction at prediction_level class? Scored here as prospective (same) because it was not motivated by the patient result.

Missed comparisons:

- Safety, model_change same, 2020, comparison_stated true, tier 2, imported_from MS (MONDO:0005301), model_filed true: FDA ozanimod Summary Review 209899 (2020) says 'The applicant provided data from a cardiovascular safety study in cynomolgus monkeys that demonstrated dose-dependent cardiovascular effects of ozanimod. Heart rate decreased by 20%...' and 'Reduction in heart rate and increased blood pressure are seen in patients treated with ozanimod.' The filed system predicted the bradycardia that the S1P3-KO mouse missed.
- Safety, contra for etrasimod, 2023: dog CV safety pharmacology was silent (NOEL 350 mg/kg/day, FDA 216956 review) but patients' heart rate fell up to 19.4 bpm. The drafter mentions this only in a judgement. It is a different model (dog telemetry) and should be its own entry.
- Efficacy patient_trials: NCT02447302 (etrasimod OASIS) has no DOI; Sandborn 2020 Gastroenterology doi 10.1053/j.gastro.2019.10.035. No change to status.
- Searched for unreported UC failures of a member drug: none found. Ozanimod and etrasimod met their UC primary endpoints; mocravimod's UC phase 2 was terminated with no reason or results.
- Safety, parallel track for the dog-silence gap: conscious guinea-pig telemetry (ponesimod, product_in_model false, non-member proxy) reproduced S1P1 first-dose HR fall and AV delay that rats and dogs did not; Bolli et al. 2013 PLoS One doi 10.1371/journal.pone.0074285 (PMID 24069292), compared with healthy-volunteer ponesimod data. No UC-patient comparison found, so at most an untested/retro note.
