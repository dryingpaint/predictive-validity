# Rule questions and missed comparisons from the v3 re-draft

Collected from each tile's checker verdict (`<slug>.check.json`). A rule question is a case the v3 rules did not decide; a missed comparison is evidence the checker found that the draft left out. Neither changed a stored status: those went through adjudication.

60 rule questions and 58 missed comparisons across the checked tiles.

## acute-myeloid-leukemia-flt3-inhibitors

Rule questions:

- LACEWING opened in 2016; the model paper that predicted the combination (Ueno 2019) was published in April 2019, before readout but after the trial started. Does a model published mid-trial count as 'the system the class relied on', and as prospective?
- When the same drug works as monotherapy (same) but fails in a combination regimen (contra), does 'one drug's contra beats another's same' make the whole efficacy cell contra, or is a combination a separate prediction?
- Dose table: in LACEWING, gilteritinib exposure was at target (troughs equal to monotherapy) and the regimen failed and was abandoned. Should dose get 'contra, derived_from: efficacy' even though the monotherapy dose worked?
- Safety: quizartinib entered humans around 2007 on a rat and monkey package whose QT prediction matched (public in 2023). Is a different tox species package the same model_id ('rat-dog-glp-tox'), or a model_change that could lift the gilteritinib contra?
- Can a single-arm trial's response-rate primary endpoint (quizartinib phase 2, 2018) score efficacy 'same', or only a randomised primary endpoint?

Missed comparisons:

- Efficacy, earlier 'same' in 2018: Cortes 2018 Lancet Oncol quizartinib single-arm phase 2 (doi:10.1016/S1470-2045(18)30240-7, epub 2018-05-31; NCT00989261), co-primary endpoints CRc and CR. The FDA Xospata review (Nov 2018, in bundle) also approved gilteritinib on ADMIRAL's co-primary CR/CRh. The strip's first 'same' should be 2018, not 2019.
- LACEWING sponsor release: Astellas 2020-12-21, 'did not meet endpoint of overall survival' (https://newsroom.astellas.com/2020-12-21-Astellas-Reports-XOSPATA-R-gilteritinib-in-Combination-with-Azacitidine-Did-Not-Meet-Endpoint-of-Overall-Survival-in-Newly-Diagnosed-FLT3-Mutation-Positive-Acute-Myeloid-Leukemia-Patients-Ineligible-for-Intensive-Induction-Chemotherapy); dates the contra to 2020.
- MORPHO (gilteritinib post-HCT maintenance, NCT02997202): missed primary RFS (HR 0.68, p=0.0518); Astellas topline release 2023-03-09; Levis JCO 2024 doi:10.1200/JCO.23.02474. Post-transplant maintenance was not modelled, so it is a patient_trials/untested note with no status change, but it is a Phase 3 failure the draft does not show.
- QuANTUM-R regulatory reading: FDA ODAC (May 2019) and a complete response letter (June 2019) questioned the robustness of the OS result; quizartinib was not approved in the US until 2023. The 2019 entry does not record this tier-2 view.
- Crenolanib (a class member) is absent: phase 3 NCT03250338 in relapsed/refractory FLT3-mutated AML was reportedly presented at ASH 2025 (benefit reported in NPM1/FLT3 co-mutated patients), and ARO-021 (NCT03258931) vs midostaurin is completed. Not verified here; the drafter should check primary-endpoint results. AKN-028 is also not mentioned.

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

## gastroesophageal-reflux-disease-atp4a-blockers

Rule questions:

- Efficacy: when the only published disease model (Kim 2019 rat GERD) was submitted after the phase 3 finished and after approval, and its run date is unpublished, is it prospective or `retrodiction: true` (retro rather than same)? The rules key on run date, which no source gives.
- Safety: if the class relied on an unpublished regulatory tox package and the only public animal safety study was run post-approval, should the cell stay `untested` on the unpublished package (model_first_use_year pre-clinic, unknown) or be built on the post-approval study as the draft does? And is that study then a retrodiction of the comparable-AE phase 3 data?
- Dose: does a model that states only an effective oral mg/kg (no exposure or occupancy target) count as stating a dose target, so that 'reached, drug worked' gives `same`, or does it stay `untested` as drafted?

Missed comparisons:

- No unreported failure found: Sebela press release 2025-04-23 (biospace.com/press-releases/sebela-pharmaceuticals-announces-positive-topline-results-from-phase-3-triumph-program-of-tegoprazan-in-gerd) reports all primary endpoints met in TRIUMpH EE and NERD; could be added to patient_trials (tier 5), no status change.
- Fexuprazan phase III EE head-to-head (Jeong 2024, J Clin Med, doi:10.3390/jcm13113262) is RETRACTED; correctly absent, worth a note so it is not re-added.
- Tegoprazan Korean NERD phase 3 and TRIUMpH NERD (GERD patients) are additional efficacy patient_trials; no status change.

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

## insomnia-hcrtr1-2-antagonists

Rule questions:

- Suvorexant next-day impairment was the harm behind the FDA dose cut, and the animal package never tested it. The drafter left it unscored under dose. Decision 16 puts an unpredicted harm in safety, so does model silence on next-day or residual sedation count as a harm the species could have shown (safety contra)? Or is it human-PK carryover (half-life), outside what the model could show?
- A dose cell mixes an efficacy-exposure target model (suvorexant C4h) with a decision 16 tolerability-margin model (daridorexant dog NOAEL). Should model_change: true be set when the cell was not contra, given the rule defines model_change only for turning a contra back?
- Dose entry 2: the effective-exposure target is published only in the FDA review that also holds the patient comparison, and Winrow 2011 is cited as model_src. Is this comparison_stated true (regulator states both sides) or false (a pairing)?

Missed comparisons:

- Vornorexant Phase 3 (Japan) met its primary sSL endpoint with no narcolepsy-related signs (Sleep 2025, PMID 41001841, https://pubmed.ncbi.nlm.nih.gov/41001841/): this agrees with the draft and changes no status. It could be added to efficacy patient_trials.
- Filorexant Phase 2 insomnia was positive at all doses (Connor 2016, doi:10.1093/ijnp/pyw022), and Merck dropped it without an insomnia failure. The draft names this only in a judgement, which is correct; no failure was missed.
- Lemborexant FDA multidiscipline review 2019 (Figure 1: lemborexant cataplexy in wild-type vs orexin-KO mice) is a separate member-drug safety model with a patient comparison. It agrees, so no status change, but it could be a dated safety entry.
- Fazamorexant Phase 3 (NCT05525637) is reported positive only on secondary aggregators. No failure was found for any member in a press release or SEC filing.

## interstitial-cystitis-anti-ngf-antibodies

Rule questions:

- Dose table row 'reached, failed, abandoned -> dose contra, derived_from efficacy' (and 'reached, worked -> same'): does it apply when no model ever stated an exposure target for any member drug? The draft keeps dose untested while efficacy goes same then contra; the rules do not say whether 'target reached' can be scored without a stated target.
- Engagement: can a model's functional readout (cystometric voiding frequency in CYP cystitis) count as a downstream PD readout when the human trial measured its counterpart (micturition frequency, unchanged in Evans 2011)? If yes, engagement would be contra 2011 at readout_tier downstream; the draft scored it as a symptom endpoint.
- Dating of efficacy entry 3: could not open the ClinicalTrials.gov history for NCT00999518 (API returned non-JSON). If the termination-for-interim-analysis text was public before Feb 2012, the year should be earlier; the rules do not say whether a registry termination reason without results counts as a public comparison.

Missed comparisons:

- Wang H et al. 2017, BMC Urol 17:2, doi:10.1186/s12894-016-0193-z (PMID 28056917, epub 2017-01-05): fulranumab 9 mg SC in IC/BPS (NCT01060254, n=31), primary endpoint LS mean difference -0.2 [-1.52, 1.10], not significant; no joint-related SAE. The draft says this trial ended 'with no results'; it belongs in efficacy entry 3's patient_trials (no status change: underpowered, already contra) and the note should be corrected.
- ASP6294 is a PEGylated Fab' (MAbs 2023, PMID 36458900, doi:10.1080/19420862.2022.2149055); the EU CTR record 2016-004138-12 (first posted 2020-02-08, women only, P=0.591, -0.2 [90% CI -0.84, 0.43]) confirms the draft's patient_trials quote and shows the female subgroup Nickel 2016 flagged was not confirmed prospectively.

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

## migraine-disorder-cgrp-receptor-antagonists

Rule questions:

- Retrodiction vs prospective on the same model: DILIsym retro-modeled MK-3207 (published 2020) in the same paper that reports the prospective ubrogepant match (2019 FDA, 2020 paper). Should the cell carry a separate retro entry for the MK-3207 member, or does the prospective same subsume it? Decision 10 does not say how a retro and a same of the same date and model order on the strip.
- Dose-table row 'reached, failed, a higher dose later worked': does the higher dose have to be shown superior to the predicted dose? For MK-3207, 200 mg alone was significant, but CIs overlapped from 10 mg up, and the same trial met its primary endpoint on a pooled dose-response trend. The table also implies efficacy contra-then-same, while the draft keeps efficacy same because the primary was met in the same trial. Which applies?
- Should a dose model built in human healthy volunteers (human CIDV calibrated on a non-member's phase 3 data) count as the same model_id/system as the rhesus CIDV used for engagement and efficacy, given that the brief scopes 'the model' to the preclinical system the class relied on?

Missed comparisons:

- Smith 2020 (doi 10.1093/toxsci/kfaa093, PMC8312697): 'DILIsym successfully modeled liver toxicity for telcagepant and MK-3207 at the dosing regimens used in clinical trials'. This is a 2020 retrodiction for member MK-3207. The draft mentions it only in a judgement, with no retro entry (see rule question).
- BI 44370 discontinuation: secondary reviews (e.g. PMC4392770) attribute it to liver toxicity and/or oral formulation difficulty. No primary source (press release or registry) was found. If confirmed, it is a second member liver signal for the safety cell. At minimum the safety note should mention it.
- Ubrogepant dose: Voss 2016 phase 2b (doi 10.1177/0333102416653233) found 1 and 10 mg ineffective and 25/50/100 mg effective. Moore 2020 gives human CIDV EC50 2.6 nM. If a CIDV-based ubrogepant dose prediction exists (e.g. the exposure-response paper 'Making Better Dose Decisions...'), it is a second member's dose comparison. The FDA ClinPharmR bundle has no CIDV dose rationale.

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

## non-small-cell-lung-carcinoma-egfr-inhibitors

Rule questions:

- The cell shows the BEST model's status. When a different member drug's own model (mobocertinib exon 20 Ba/F3/PDX; naquotinib xenografts) fails in its Phase 3, must that model get its own scored entries in the same cell, or only a note? The rules say 'one drug's contra beats another's same on the same model' but are silent on other models within one class.
- Population when the tile gives none and members span first-line sensitising, T790M-acquired and exon 20 insertion settings: one context (EGFR-mutant) or one per biomarker? The drafter's T790M-or-exon20 choice excludes FLAURA and SOLAR.
- EXCLAIM-2 / SOLAR failed against an active comparator while the drug's activity (ORR ~30%) matched the model's prediction of regression. Is failing to beat an active comparator, which no model tested, contra or untested ('conditions the model never tested')?
- Rociletinib: regulatory rejection because unconfirmed responses overstated ORR, with no failed pre-specified primary endpoint. Is that an efficacy contra, a partial same, or unscored?

Missed comparisons:

- Naquotinib (ASP8273, class member): Phase 3 SOLAR (NCT02588261, first-line EGFR-activating-mutation NSCLC vs erlotinib/gefitinib, primary PFS by IRR) terminated May 2017 on IDMC futility/benefit-risk; registry results posted 2019-02-12; Astellas press release May 2017 (e.g. fiercebiotech.com/biotech/astellas-scraps-nsclc-program-after-look-at-phase-3-data). Its own xenograft model (Hirano et al. 2015, Oncotarget; DOI not verified) predicted activity. This is outside the draft's stated population (T790M or exon 20) only because the draft narrowed it.
- Mobocertinib: an efficacy entry on its own exon 20 model (Gonzalvez 2021 Cancer Discov, Ba/F3/PDX) paired with EXCLAIM-2 (PMID 39879577, 2025; HR 1.04, crossed futility) is only noted in patient_trials, not scored; NCT04129502 has no posted results (completed 2026-09-22). Takeda withdrew the drug in 2023 (press release, tier 5).
- Osimertinib FLAURA (first-line sensitising EGFR, NEJM 2018, 10.1056/NEJMoa1713137) is the class's main efficacy datum for the same xenograft system (PC9 Ex19del models in Cross 2014) and is absent because the population excludes first line.
- Rociletinib: FDA ODAC April 2016 and complete response letter June 2016 after confirmed ORR fell to about 30% from the 59% reported earlier; hyperglycaemia in patients. Not scored; at minimum belongs in patient_trials or a note.
- Olmutinib: Boehringer Ingelheim returned rights in 2016 after fatal toxic epidermal necrolysis/SJS; a safety datum for another member on its own tox package, not recorded.

## ovarian-cancer-parp1-2-inhibitors

Rule questions:

- Safety: when an FDA review says animal findings were 'consistent with' the dose-limiting harms but explicitly notes a common patient harm the species could have shown (rucaparib ALT/AST, 74% incidence) was absent, is that same + partial or contra (silence contradicted)?
- Efficacy: does outcome_tested apply when the trial primary endpoint (PFS) is met but later OS shows detriment (ARIEL4) — i.e. is PFS a 'surrogate the model predicted' in oncology, and should an OS detriment ever move an efficacy cell?
- model_change: is it meaningful on an entry that follows a same (not contra) entry with a different model, or should lint reject model_change: true unless the previous entry is contra?

Missed comparisons:

- ARIEL4 (rucaparib vs chemotherapy, BRCA-mutant relapsed ovarian; NCT02855944, results posted 2022-02-11): primary invPFS met (Kristeleit, Lancet Oncol 2022), but final OS 19.4 vs 25.4 months (Lancet Oncol 2025, PIIS1470-2045(24)00674-0); FDA treatment indication voluntarily withdrawn June 2022. Status stays same on the primary endpoint, but efficacy should carry this as a patient_trials item / outcome_tested: negative.
- NOVA final OS (gBRCA HR ~0.85, not significant; non-gBRCA OS detriment) led to the 2022 restriction of niraparib 2L maintenance to gBRCA; relevant to outcome_tested, not to the PFS-based status.
- Stenoparib (2X-121, member) phase 2 NCT03878849 in platinum-resistant ovarian cancer, DRP-selected not BRCA-selected; sponsor press releases only (Allarity 2025), positive in tone, outside the BRCA/HRD population; no failure to add.

## rheumatoid-arthritis-btk-inhibitors

Rule questions:

- Safety silence and species capability: does a dog toxicology study that measured platelet aggregation as 'unremarkable' count as a model silent on a harm the species could have shown, when human BTK-inhibitor bleeding is mediated by GPVI platelet signalling whose BTK dependence differs across species (Tec compensation in rodents)? The rules do not say who decides species capability or on what evidence.
- Dose for a failed drug whose dose basis is unpublished (BMS-986142, poseltinib): the dose table assumes we know whether the model's exposure target was reached. When no source states the dose basis, is the dose entry untested (draft's implicit choice) or does efficacy contra still stand without the dose check (draft scores efficacy contra on BMS-986142 regardless)?

Missed comparisons:

- Safety, imported_from mantle cell lymphoma (acalabrutinib is a member): FDA NDA 210259 Multidiscipline Review (2017, https://www.accessdata.fda.gov/drugsatfda_docs/nda/2017/210259Orig1s000MultidisciplineR.pdf, in the source bundle) reports the 91-day dog study 'Platelet Aggregation: Unremarkable' and nonclinical platelet assays showing 'fewer effects than ibrutinib', while 39/124 (31.5%) of pivotal MCL patients had hemorrhage (1 major). A paired (comparison_stated false) on-target-harm entry, likely contra (model silent on bleeding) dated 2017 if the dog is judged able to show BTK-dependent platelet dysfunction; TAS5315 bleeding in RA (Takeuchi 2023) is the in-disease echo. See rule question.
- Efficacy patient_trials: NCT02387762 (acalabrutinib + MTX, Phase 2) registered primary endpoint was DAS28-CRP at week 4; registry results 2019-03-26 show 5.40 vs placebo 5.05 (no analysis posted). It is the earliest member primary-endpoint miss, not exploratory; same year as the cell's contra, so no status or year change.
- Efficacy/dose: spebrutinib NCT01975610 registered primary was ACR20 at week 4 (not met, 41.7% vs 21.7%, P=0.25, Schafer 2019 epub 2019-11-13) with median patient BTK occupancy 83%: a member that reached the model's occupancy target and missed its primary endpoint in 2019, independent of the BMS-986142 dose question.

## type-2-diabetes-mellitus-glp1r-agonists

Rule questions:

- Rule 5/12: when the only human null for an on-target class harm is a pooled cohort in which non-member drugs (here liraglutide) dominate, does it count for the member class at all, or only for the member share, and how is that share recorded?
- Rule 7: when the patient source (Kapitza, Jan 2015) predates the publication of the model source (Lau, Sept 2015) but the model was used prospectively before the clinic, is the paired entry dated to the later publication, or to the patient source with the model's use year as proxy?
- Safety silence: a single tier-5 liver-injury case in another indication (obesity), which the sponsor says sits at class-background rates. Is that a contradicted silence, or does it need a tier 1-4 patient source before it can be scored?

Missed comparisons:

- Dose (semaglutide, peptide): earlier patient PK source Kapitza 2015, J Clin Pharmacol, doi:10.1002/jcph.443 (PMID 25475122), and phase 2 dose-finding Nauck 2016 Diabetes Care doi:10.2337/dc15-0165 (epub 2015-09-10); either dates the semaglutide dose comparison to 2015 instead of the 2017 label.
- Safety (danuglipron, small molecule, imported_from obesity): Pfizer 2025-04-14 discontinuation after one case of possible drug-induced liver injury in an obesity dose-optimisation study (tier 5; e.g. https://www.cnbc.com/2025/04/14/pfizer-scraps-daily-weight-loss-pill-danuglipron.html). Pfizer says overall liver-enzyme rates matched approved GLP-1 RAs; scorable only if a tier 1-3 tox source states hepatic silence, otherwise untested at most.
- No missed efficacy failures found for other members: TTP273 phase 2 positive (vTv 2017, placebo-subtracted HbA1c -0.86/-0.71%), CJC-1134-PC phase 2 HbA1c fell vs placebo (NCT00638716/NCT00674466), efpeglenatide AMPLITUDE programme positive; LY2428757 discontinuation reason not found.

## ulcerative-colitis-s1pr1-agonists

Rule questions:

- Decision 16 and margin_stated: the etrasimod NOAEL studies were IND-enabling (pre-trial), but the multiple at MRHD (738x/446x) is stated only in the 2023 review, after the trial. Does a pre-trial filed NOAEL count as a margin 'stated before the trial'?
- Decision 16: the rat liver findings fell at >1000x MRHD, but patients at 2 mg had ALT elevations (label 5.3) that did not block dosing. Is that a misplaced-margin dose contra, a safety entry, or neither?
- Can a retro entry (safety 3, model_change true) follow a contra and be drawn as the cell's latest status, or does a contra stand until a prospective prediction holds?
- When the drafter's chosen model (S1P3-KO mouse, a design rationale in the literature) differs from the filed safety system (cynomolgus CV study), which one is 'the model the class relied on' for the safety cell, and do both get entries?
- Scott 2016 was received Aug 2015, after the TOUCHSTONE topline (Oct 2014 press release), but the mouse colitis experiments probably predate the trial. Is a model paper published after the patient result a retrodiction when the experiments were run earlier?

Missed comparisons:

- Safety, model_change same, 2020, comparison_stated true, tier 2, imported_from MS (MONDO:0005301), model_filed true: FDA ozanimod Summary Review 209899 (2020) says 'The applicant provided data from a cardiovascular safety study in cynomolgus monkeys that demonstrated dose-dependent cardiovascular effects of ozanimod. Heart rate decreased by 20%...' and 'Reduction in heart rate and increased blood pressure are seen in patients treated with ozanimod.' The filed system predicted the bradycardia that the S1P3-KO mouse missed.
- Safety, contra for etrasimod, 2023: dog CV safety pharmacology was silent (NOEL 350 mg/kg/day, FDA 216956 review) but patients' heart rate fell up to 19.4 bpm. The drafter mentions this only in a judgement. It is a different model (dog telemetry) and should be its own entry.
- Efficacy patient_trials: NCT02447302 (etrasimod OASIS) has no DOI; Sandborn 2020 Gastroenterology doi 10.1053/j.gastro.2019.10.035. No change to status.
- Searched for unreported UC failures of a member drug: none found. Ozanimod and etrasimod met their UC primary endpoints; mocravimod's UC phase 2 was terminated with no reason or results.
