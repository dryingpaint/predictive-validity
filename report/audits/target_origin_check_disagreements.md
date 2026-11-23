# Twenty labels the Sonnet checker rejected on the category and the Opus checker supported

**Status (2026-11-21, evening): superseded by check method v2** (`target_origin_run.md`, last section), which settles the
earlier-drug category from the Drugs@FDA approval index in code and sends the two checkers' other disagreements to
`target_origin_disputes.csv`, the live sheet. Of the twenty cases below: 4 stand on the index (SNAP25, SCN9A, PARP2,
AR: an approval for an unrelated disease before entry); 4 are unsupported on it (RAF1, INSR, NR3C1, HTR1B: the
approval is for a related disease, Lin 0.5 or more, so not the category as the one-list decision defines it); 2 are
disputed because the index holds no approval on the target (RHD, EGLN2); the 10 from the other kinds are category
rows on the sheet. The read asked for below is no longer needed; the file stays as the record of the sensitivity
study that led to v2.

Provenance: the Sonnet 5.5 verdicts are the stored check (prompt v3); the Opus 5.5 verdicts are the sensitivity run of 2026-11-21 (prompt version v4, same text), decision log only. Twenty drawn at random (seed 1), ten from earlier_drug_other_disease and ten from the other kinds, among the labels Sonnet rejected on the category alone and Opus supported. See `target_origin_run.md`, "Checker sensitivity".

Read the quote against the definition and say which checker is right. Both notes are the models' own.

## 1. SNAP25 x osteoarthritis (cutoff 2012), label **earlier_drug_other_disease**

- Quote: "We are studying the efficacy and safety of intra-articular injection of Botulinum Toxin Type A (IA-BoNT/A) into joints with arthritis pain."
- Sources: ['https://www.academia.edu:443/33639550/Intra-articular_Botulinum_Toxin_Type_A_A_new_approach_to_treat_arthritis_joint_pain', 'https://pubmed.ncbi.nlm.nih.gov/19351542/', 'https://pubmed.ncbi.nlm.nih.gov/20430328/']
- Sonnet (origin_follows no): The quote is in PMID 19351542 (2009), and all cited sources are dated 2009 or 2010, before the cutoff. But the passage describes intra-articular BoNT/A trials in arthritis joint pain and mouse arthritis pain models. That is not a drug approved for an unrelated disease, and it is closer to clinical observation or animal pharmacology, so earlier_drug_other_disease is not supported.
- Opus (origin_follows partly): The quote appears word for word in the abstract of PMID 19351542 (2009), whose title matches the academia.edu link (that page could not be fetched), and all cited sources date from 2009–2010. Botulinum toxin A, which cleaves SNAP25, was an existing approved drug repurposed into arthritis joints, so this fits earlier_drug_other_disease, but the sources also include osteoarthritis clinical trials and mouse arthritis pharmacology, which support neighbouring categories too.

## 2. SCN9A x myofascial pain syndrome (cutoff 2010), label **earlier_drug_other_disease**

- Quote: "TrP injection with 0.5% lidocaine is recommended"
- Sources: ['https://www.semanticscholar.org/paper/LIDOCAINE-INJECTION-VERSUS-DRY-NEEDLING-TO-TRIGGER-Hong/5a3e21ee08f3b68dcb2c2c7d1b3db943052f0c3e', 'https://www.researchgate.net/publication/24431095_A_randomized_controlled_study_comparing_a_lidocaine_patch_a_placebo_patch_and_anesthetic_injection_for_treatment_of_trigger_points_in_patients_with_myofascial_pain_syndrome_Evaluation_of_pain_and_soma']
- Sonnet (origin_follows no): The quote appears in the 1994 Hong abstract, and the other source is dated 2009, so both predate 2010. However, it only recommends lidocaine injection for myofascial trigger points, which is a treatment of the same disease. It does not show a drug on SCN9A approved for an unrelated disease, and neither source links SCN9A to the disease.
- Opus (origin_follows partly): The quote appears word for word in the abstract of Hong's 1994 paper in Am J Phys Med Rehabil, which I read through the journal and search copies, and both cited sources are dated before 2010 (1994 and 2009). The origin fits only partly: lidocaine was first approved as a non-selective local anaesthetic and antiarrhythmic rather than for an unrelated disease or for SCN9A specifically, and the passage reports its direct clinical use in myofascial pain, which also points to clinical_observation.

## 3. RAF1 x nasopharyngeal carcinoma (cutoff 2017), label **earlier_drug_other_disease**

- Quote: "To determine the efficacy and safety of single-agent sorafenib in patients with recurrent and/or metastatic squamous cell carcinoma of the head and neck (SCCHN) and nasopharyngeal carcinoma (NPC)."
- Sources: ['https://pubmed.ncbi.nlm.nih.gov/17704426/']
- Sonnet (origin_follows no): The quote is in the 2007 PubMed abstract, but it describes a phase II trial of sorafenib in NPC itself, not an earlier approval of a RAF1 drug for an unrelated disease, so it fits clinical trial evidence in the same disease and not earlier_drug_other_disease.
- Opus (origin_follows partly): The quote is the opening aim sentence of the 2007 PubMed abstract and reflects the pattern of testing sorafenib, a RAF inhibitor already approved for renal cancer, in NPC, but the record never names RAF1 or mentions the earlier approval, so that link comes from outside knowledge and the paired-biopsy biomarker data (lower pERK in tumour) also point toward clinical evidence.

## 4. PARP2 x urothelial carcinoma (cutoff 2018), label **earlier_drug_other_disease**

- Quote: "Therapeutic exploitation of DNA repair by inhibition of poly (adenosine diphosphate [ADP]) ribose polymerases (PARP), a family of enzymes involved in the repair of single-strand and in some cases double-strand breaks, has become a novel cancer treatment."
- Sources: ['https://acsjournals.onlinelibrary.wiley.com/doi/10.1002/cncr.30631']
- Sonnet (origin_follows no): The quote is the abstract of Rimar et al., Cancer 2017 (a review of PARP inhibitors in genitourinary cancers). It does not say that a drug on the target was approved for an unrelated disease, and it says nothing specific about PARP2 or urothelial carcinoma, so it does not support earlier_drug_other_disease.
- Opus (origin_follows partly): The Wiley page could not be fetched, but the quote appears as the opening of the abstract of Rimar et al. 2017 in Cancer ('The emerging role of homologous recombination repair and PARP inhibitors in genitourinary malignancies'), according to the Google Scholar and ResearchGate snippets. It only says that PARP inhibition is already a cancer treatment, without naming PARP2, an approved drug or another disease, and the review's reasoning rests on DNA-repair mutations in genitourinary tumours, so it supports earlier_drug_other_disease only partly and overlaps with tumour_genetics.

## 5. INSR x pregnancy disorder (cutoff 2010), label **earlier_drug_other_disease**

- Quote: "for deciding about insulin therapy in patients with gestational diabetes"
- Sources: ['https://pubmed.ncbi.nlm.nih.gov/8950733/']
- Sonnet (origin_follows no): The quote is in the 1996 abstract, but that paper is about using amniotic fluid insulin to decide on insulin therapy in gestational diabetes. It does not show an INSR drug approved for an unrelated disease, so it does not support earlier_drug_other_disease.
- Opus (origin_follows partly): The quote appears word for word in the 1996 abstract, which shows insulin, an INSR agonist, already in use for gestational diabetes; that fits a drug carried over from earlier diabetes use, but diabetes is closely related to the pregnancy disorder rather than unrelated, and the passage does not mention approval for another disease, so the category is only partly supported.

## 6. RHD x autoimmune thrombocytopenic purpura (cutoff 2008), label **earlier_drug_other_disease**

- Quote: "There is evidence that blockade of the reticuloendothelial system (RES) by sequestration of autologous red blood cells (RBC) leads to an elevation of platelet counts in immune thrombocytopenia."
- Sources: ['https://link.springer.com/article/10.1007/BF00320381']
- Sonnet (origin_follows no): The quote is the opening sentence of the 1984 Blut abstract, so the year is fine. But it describes treating ITP patients with anti-D, which is a clinical observation or treatment in the same disease, and not an earlier drug approved for an unrelated disease.
- Opus (origin_follows partly): The quote appears word for word as the first sentence of the 1984 Salama et al. Blut abstract, which is before the 2008 cutoff, but it gives a mechanistic rationale (RES blockade by sequestered RBCs, drawn from earlier IVIG observations) and never mentions that anti-D was already approved for Rh prophylaxis, so earlier_drug_other_disease rests on outside knowledge and the passage fits clinical_observation about as well.

## 7. NR3C1 x enteritis (cutoff 2009), label **earlier_drug_other_disease**

- Quote: "DOR has plans to further develop orBec® for the treatment of other gastrointestinal disorders characterized by severe inflammation such as radiation enteritis, Crohn's disease, IBS and ulcerative colitis."
- Sources: ['https://www.biospace.com/fda-advisory-panel-advises-against-dor-biopharma-inc-s-orbec-r-approval', 'https://www.biospace.com/dor-biopharma-inc-announces-fda-clearance-of-ind-for-dor201-in-radiation-enteritis', 'PMID:11254479']
- Sonnet (origin_follows no): The quote is on the 2006 BioSpace page and all sources are dated 2008 or earlier. But it only says DOR plans to develop orBec (oral beclomethasone, a glucocorticoid) for enteritis and other GI disorders. It does not show a drug on NR3C1 approved for an unrelated disease. It describes a development plan for the same class of drug, and the 2001 rat study points to animal_model_pharmacology instead.
- Opus (origin_follows partly): The quote appears word for word in the BioSpace orBec advisory-panel article, which is dated 10 May 2007 rather than the labeller's 2006; the 2008 IND notice and the 2001 PMID are also dated before the cutoff. The quote supports earlier_drug_other_disease only partly, because it states a plan to extend the glucocorticoid orBec (beclomethasone) to radiation enteritis but does not mention the drug's earlier approval for another disease, and the cited 2001 rat study (dexamethasone and the receptor blocker RU-486 changing toxin A enteritis) is an earlier animal_model_pharmacology origin.

## 8. EGLN2 x myelodysplastic syndrome (cutoff 2018), label **earlier_drug_other_disease**

- Quote: "Roxadustat is a hypoxia-inducible factor prolyl hydroxylase inhibitor (HIF-PHI) that promotes erythropoiesis through increasing endogenous erythropoietin, improving iron regulation, and reducing hepcidin."
- Sources: ['https://www.marketscreener.com/quote/stock/FIBROGEN-INC-18537026/news/FibroGen-Announces-China-FDA-Approval-of-CTA-to-Conduct-Pivotal-Phase-2-3-Clinical-Trial-of-Roxadust-24140303/']
- Sonnet (origin_follows no): The quote is in the March 2017 FibroGen press release, but it only describes roxadustat's mechanism in anemia of chronic kidney disease (CKD), where the drug was still in Phase 3 and not approved. The release announces a trial in MDS anemia, so it does not show an earlier approval for an unrelated disease.
- Opus (origin_follows partly): The quote appears word for word in FibroGen's 31 March 2017 press release on a China trial of roxadustat in MDS anemia, but roxadustat was only in Phase 3 for CKD anemia then and was not approved anywhere until late 2018; it was also being developed for anemia, a closely related use, so the earlier-drug-for-another-disease category is only partly supported.

## 9. HTR1B x cluster headache syndrome (cutoff 2019), label **earlier_drug_other_disease**

- Quote: "Its clinical efficacy on migraine and cluster headache had been already confirmed in about 100 western countries."
- Sources: ['PMID:11436516', 'PMID:17087122']
- Sonnet (origin_follows no): The quote is in the abstract of PMID:11436516 (2001), and both sources predate 2019. But it describes sumatriptan being effective in migraine and cluster headache, which is the same or a neighbouring headache indication. It does not show an earlier approval for an unrelated disease, so it fits clinical_observation or an on-target drug in the disease itself, not earlier_drug_other_disease.
- Opus (origin_follows partly): The quote appears word for word in the PMID:11436516 abstract and both sources predate 2019, but it says sumatriptan already worked for migraine and cluster headache together, and migraine is a closely related headache disorder rather than an unrelated disease, so it equally supports clinical_observation.

## 10. AR x chronic obstructive pulmonary disease (cutoff 2018), label **earlier_drug_other_disease**

- Quote: "Two hundred seventeen patients with COPD participated in a placebo-controlled, randomized trial investigating the physiologic effects of nutritional intervention alone (N) for 8 wk or combined with the anabolic steroid nandrolone decanoate (N+ A)."
- Sources: ['https://scholar.google.com/scholar_lookup?doi=10.1164%2Fajrccm.152.4.7551381&amp=&pmid=7551381']
- Sonnet (origin_follows no): I did not fetch the page. The quote matches my recollection of the abstract of Schols et al., AJRCCM 1995 (DOI 10.1164/ajrccm.152.4.7551381). It describes a nandrolone trial run directly in COPD patients, which is not a drug approved earlier for an unrelated disease, so it does not support earlier_drug_other_disease.
- Opus (origin_follows partly): The quote appears word for word in the abstract of Schols et al. 1995 (Am J Respir Crit Care Med), found through a Scholar copy, and the 1995 date is before the cutoff. But the passage only describes a trial in COPD patients of nandrolone decanoate, an anabolic steroid that acts on AR; it never says the drug was already approved for an unrelated disease, so 'earlier_drug_other_disease' depends on outside knowledge and the passage could also fit 'clinical_observation'.

## 11. GABRA4 x essential tremor (cutoff 2014), label **clinical_observation**

- Quote: "Although rarely prescribed to patients with essential tremor, alcohol (ethanol) markedly reduces tremor amplitude through action on a central component (20)."
- Sources: ['https://www.jci.org/articles/view/23625', 'PMID:21422964']
- Sonnet (origin_follows no): The quote is in the 2005 JCI paper on GABAA receptor α1 knockout mice, and both sources predate 2014. But it only says ethanol reduces tremor in essential tremor patients, and that isn't evidence linking GABRA4 to the disease. The 2011 paper found no association between GABRA4 variants and essential tremor risk.
- Opus (origin_follows partly): The quote appears word for word in the JCI 2005 paper (Kralic et al.), which reports tremor in mice lacking the GABA-A α1 subunit (GABRA1, not α4) and says ethanol relieves that tremor through non-GABAergic mechanisms; the paper never mentions α4, so the clinical observation that alcohol reduces tremor ties to GABRA4 only through the 2011 candidate-gene study, which found no GABRA4 association, and the mouse work points to the neighbouring mouse_genetics category.

## 12. THRA x hypothyroidism (cutoff 2019), label **clinical_observation**

- Quote: "In the late 1800s, treatment with thyroid extract caused dramatic improvement in patients with myxedema."
- Sources: ['https://www.researchgate.net/publication/49799842_The_discovery_of_thyroid_replacement_therapy_Part_2_The_critical_19th_century', 'PMID:28527577']
- Sonnet (origin_follows no): I did not fetch the ResearchGate page, and the shown PMID record (2017) does not contain the quote. Both sources are dated before 2019. Even if the quote is there, thyroid extract treating myxedema is a general observation about thyroid hormone replacement and does not show that THRA was first proposed as a target for hypothyroidism.
- Opus (origin_follows partly): ResearchGate wouldn't load, but the James Lind Library version of Slater's article (the 2011 JRSM paper was republished from it in three parts) describes Murray's 1891 thyroid-extract injections leaving a myxoedema patient 'dramatically better', so the quote is a fair paraphrase of a 2011 source; it supports a clinical observation for thyroid hormone in general, not THRA itself, and only the 2017 THRA-mutation review ties it to this target.

## 13. CHRM5 x motion sickness (cutoff 2014), label **clinical_observation**

- Quote: "The anticholinergic agents, such as scopolamine, when used for preventing motion sickness, present some disadvantages at the effective dose, especially the troublesome central inhibitory effect"
- Sources: ['http://www.chinaphar.com/article/view/3685/9939']
- Sonnet (origin_follows no): The cited chinaphar.com page and a search for the same source both failed with tool errors, so I could not read it. The quote describes side effects of scopolamine, which does not show that CHRM5 was first proposed as a target, so it does not clearly support clinical_observation for CHRM5.
- Opus (origin_follows partly): The quote appears word for word in the Discussion of Acta Pharmacol Sin 2005;26(5):527-532 (the 2016 date on the page is only when it went online); it describes how scopolamine, which blocks all muscarinic receptors, is used clinically for motion sickness and what side effects it has, so it backs a clinical observation in people but says nothing about M5 specifically, and the paper itself is rat receptor-binding and animal pharmacology work, which leans toward animal_model_pharmacology.

## 14. TYK2 x rheumatoid arthritis (cutoff 2012), label **curated_pathway**

- Quote: "Tyrosine kinase 2 (TYK2) is required for signaling of interleukin-23 (IL-23), which plays a key role in rheumatoid arthritis."
- Sources: ['PMID:21106455']
- Sonnet (origin_follows no): The quote is in the 2010 abstract of PMID:21106455, but it is a general statement that TYK2 is needed for IL-23 signaling. It does not cite a curated pathway showing a disease mutation disrupting TYK2, so it does not support curated_pathway.
- Opus (origin_follows partly): The quote appears word for word in the 2010 abstract, which is dated before the 2012 cutoff, but it only explains why TYK2 matters through IL-23 signalling biology; it does not show a curated pathway in which a disease mutation disrupts TYK2, so curated_pathway is only loosely supported.

## 15. IGLC1 x AL amyloidosis (cutoff 2013), label **diseased_tissue**

- Quote: "Immunoglobulin light chain amyloidosis (AL) is a plasma cell dyscrasia wherein monoclonal light chain proteins circulate at high levels and, due to misfolding and seeded aggregation events, accumulate as fibrillar deposits in visceral organs"
- Sources: ['https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0052686']
- Sonnet (origin_follows no): The quote is in the 2012 PLoS ONE paper, but it is only the general background sentence. The paper itself is about the 2A4 antibody binding AL amyloid deposits and imaging them in mice, which does not show that IGLC1 RNA or protein level differs in diseased tissue.
- Opus (origin_follows partly): I found the quote word for word in the Introduction of Wall et al., PLoS ONE (published 26 December 2012, so before the 2013 cutoff); it describes light-chain protein building up as deposits in organs, which supports diseased_tissue, but it also says the light chains circulate at high levels (observational_biomarker), it is a general background statement rather than evidence specific to IGLC1, and the paper's own work is anti-fibril antibody treatment of amyloidomas in mice (animal_model_pharmacology).

## 16. PDE4A x atopic eczema (cutoff 2010), label **observational_biomarker**

- Quote: "Several previous reports have suggested an increased activity of cAMP phosphodiesterases (PDEs) and a higher sensitivity of these enzymes toward PDE inhibitors in leukocytes of patients suffering from atopic dermatitis."
- Sources: ['PMID:9338548']
- Sonnet (origin_follows no): The quote is in the 1997 abstract, but it only cites earlier reports of raised PDE activity in leukocytes. The study itself found no real change in PDE activity in atopy, apart from higher PDE4A mRNA in atopic T cells, so it does not support an observational_biomarker origin for PDE4A.
- Opus (origin_follows partly): The quote appears word for word in the 1997 abstract, but it describes earlier reports of raised cAMP PDE activity in general, not PDE4A, in leukocytes from atopic dermatitis patients' blood; this fits observational_biomarker but also borders on diseased_tissue, and the study itself found no change in PDE activity, so the origin probably predates this paper.

## 17. FGFR4 x constipation disorder (cutoff 2015), label **human_genetics**

- Quote: "Genetic variation in FGFR4 was associated with AC t(½) in response to CDC (uncorrected P = .015)"
- Sources: ['PMID:20691689']
- Sonnet (origin_follows no): The quote is in the 2010 abstract, but it describes FGFR4 variants that modify how patients respond to chenodeoxycholate (a pharmacogenetic effect), not a germline link between FGFR4 and constipation risk, so it does not support human_genetics.
- Opus (origin_follows partly): The quote is in the 2010 abstract, but the FGFR4 germline variant was linked only to colonic transit after chenodeoxycholate treatment in a small candidate-gene pharmacogenetic analysis (uncorrected P = .015), not to the risk of having constipation, so it only partly supports human_genetics.

## 18. PDGFRA x epicondylitis (cutoff 2012), label **animal_model_pharmacology**

- Quote: "There have been several in vivo and in vitro studies regarding biologic augmentation of tendon healing."
- Sources: ['https://patents.google.com/patent/US20110245170A1/en']
- Sonnet (origin_follows no): The quote is in the patent, which was published 2011-10-06, but it is a generic background sentence about growth-factor studies of tendon healing. It shows no animal-model pharmacology on PDGFRA, so it does not support that origin.
- Opus (origin_follows partly): The cited Google Patents page for US20110245170A1 (published 2011-10-06, before the cutoff) could not be opened, so I checked the granted version, US8492335B2, which comes from the same application and contains the quote word for word; the quote is a general background line about tendon-healing studies that cites BMP-12 and other growth factors, so animal_model_pharmacology rests on the patent's own experiments (rhPDGF-BB injected into a rat collagenase Achilles tendon model, presented as a stand-in for lateral epicondylitis) rather than on the quote, and PDGF-BB mostly acts through PDGFRB, which makes the link to PDGFRA indirect.

## 19. GRIA4 x schizophrenia (cutoff 2016), label **animal_model_pharmacology**

- Quote: "Given the importance of glutamatergic mechanisms and the hippocampal formation in schizophrenia, these data suggest a potential substrate for neurotransmitter dysregulation in this illness, as well as a potential target for therapeutic intervention."
- Sources: ['PMID:9118313', 'PMID:12497607']
- Sonnet (origin_follows no): The quote is in the PMID:9118313 abstract (1996), and both sources predate 2016. However, it only shows that haloperidol and clozapine change GluR4 mRNA in rat hippocampus, which is not modulation of an animal disease model. The 2003 association study is human genetics, so the stated origin of animal_model_pharmacology is not supported.
- Opus (origin_follows partly): The quote appears word for word in the 1996 abstract, and both sources are dated before 2016. However, that study gave antipsychotics to normal rats and measured changes in AMPA and kainate subunit mRNAs, including GluR4. It did not modulate GRIA4 to change a schizophrenia model, so it fits animal_model_pharmacology only loosely, and the 2003 haplotype study points instead to human_genetics.

## 20. MTOR x brain cancer (cutoff 2014), label **tumour_genetics**

- Quote: "Because the phosphatidylinositol-3-kinase (PI3K) signaling pathway is activated in more than 88% of GBM, new drugs which target this pathway, such as the mTOR inhibitor Everolimus, are currently in clinical trials."
- Sources: ['PMID:21807103', 'PMID:22015553', 'PMID:20044633']
- Sonnet (origin_follows no): The quote is in the abstract of PMID:21807103 (2012) and all cited sources are dated before 2014, but it only says PI3K pathway activation in GBM and that everolimus is in trials, which is not recurrent gene mutation (tumour_genetics) and not an earlier approval for an unrelated disease.
- Opus (origin_follows partly): The quote appears word for word in the PMID:21807103 abstract, and all cited sources date from before 2014; it shows that the PI3K pathway is activated in most GBM, not that MTOR itself is recurrently mutated, so it supports tumour_genetics only indirectly, mainly with the PMID:22015553 review of genetic alterations, and its mention of the repurposed drug everolimus also points toward earlier_drug_other_disease.

