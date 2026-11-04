## Appendix

### Data

| Source | What it gives | Version |
| :---- | :---- | :---- |
| ClinicalTrials.gov API v2 | Every interventional drug, biological, genetic or combination-product study: phases, status, dates, sponsor, arms, interventions, conditions, sites, why stopped, posted results | Snapshot {{section1.snapshot}} ({{section1.scale.ctgov_studies|int}} studies) |
| PubMed | Results papers linked to completed trials without posted results (registry RESULT/DERIVED references and the NCT secondary identifier) | Retrieved {{section1.snapshot}} |
| Drugs@FDA, FDA approval letters, openFDA labels | NDA/BLA applications, submissions and action dates; {{section1.scale.fda_approved_uses|int}} approved uses read from 2008–2026 approval letters; current Indications and Usage text | Retrieved October 2026 |
| CBER yearly approval pages, product pages and letters | {{section1.scale.cber_applications|int}} biologics applications (vaccines, blood products, cell and gene therapies) and their 2015–2025 approval actions, verified by an independent second enumeration | Retrieved October 2026 |
| FDA Global Substance Registration System | UNII substance identifiers and every registered name (official, common, code, brand) | 2026-08-04 |
| MONDO | Disease ontology and hierarchy | 2026-10-06 |
| Open Targets Platform | Target–disease associations by data source, with yearly score series | 26.09 |
| Open Targets Platform evidence | Every evidence row behind those associations for drug targets, with its date, direction of effect, confidence and source detail; mouse-model phenotypes | 26.09 |
| Mammalian Phenotype ontology | Mouse phenotype hierarchy (knockouts lethal before weaning) | Retrieved October 2026 |
| gnomAD | Loss-of-function constraint (LOEUF) | v4.1 |
| DepMap | Common-essential genes from CRISPR (Chronos) screens | Public 19Q4 to 24Q4, the last release of each year |
| HGNC | Approved human gene symbols with previous symbols and aliases | 2026-10-16 |
| ChEMBL | Drug mechanisms of action, as hints for target assignment | 37 |
| ChEMBL bioactivities | Potency, affinity and selectivity measurements of each entity's molecules, dated by the year of the paper, patent or dataset that reported them | 37 ({{section2.drug.release.n_activities|int}} measurements) |

Per-source detail (who compiles each source, what this analysis takes from it, raw response shape and a sample record) and the tables behind the main tab's figures are in the Appendix detail tab.

### How programs are counted

* **Trial:** a registered interventional study listing Early Phase 1 to Phase 3. A Phase 1/2 trial counts as Phase 2 and a Phase 2/3 trial as Phase 3. Withdrawn trials never enrolled and are left out.
* **Molecular entity:** the active substance, whatever its brand, sponsor code, dose or salt, resolved to its FDA UNII substance where one exists. Biosimilars fold into their reference entity.
* **Disease:** the MONDO term for the condition the trial treats, without line, stage, biomarker or age qualifiers.
* **Program:** one entity developed for one indication. An indication groups the entity's MONDO diseases the way a sponsor runs them as programs (prostate cancer with castration-resistant and metastatic prostate carcinoma; diffuse large B-cell and follicular lymphoma kept apart), decided by an LLM for each entity. An entity belongs to a program only in trials where it is the investigational agent, not a comparator or background therapy. Each industry trial's purpose is classified first: bioequivalence, formulation, food-effect, interaction and other product-support studies ({{section1.purpose.product_support|int}} trials) belong to no program; a first-in-human study or a basket across several diseases counts as Phase 1 only for the program the sponsor pursued next.
* **Phase entry and outcome:** a program enters a phase when its first industry-sponsored trial of that phase starts. It *advanced* when a later-phase trial in its disease started (any sponsor) or the FDA approved the entity for the disease. A trial that has not started, because it is still not yet recruiting or its record went silent before its estimated start date, marks neither entry nor advancement. A program is *suspended* when none of its trials, nor the trial that marked its Phase 1 entry, has been active within {{section1.lag_months}} months of the snapshot ({{section1.snapshot}}); otherwise it is still running and *censored*. Programs whose entity was already approved for the disease are lifecycle programs and are left out; an approval dated only as before 2008 (the first approval letters read) is placed at the entity's first FDA approval, the earliest it could have happened. As in BIO's report, a phase a program skipped (Phase 1 straight to Phase 3, or approval from Phase 2) counts as a success in that phase, each phase's success rate is advanced ÷ (advanced + suspended), and LOA is their product. *US-developed* programs are those with a US-sited industry trial in the phase; a cohort with fewer than ten entities resolved in a phase gets no LOA.
* **Approval:** FDA approval of the entity for the program's disease, a subtype or population of it, or a broader approved class that includes it, judged from the dated approval letters, original-approval dates and labels of every application of the entity (CDER and CBER).

### Phase transitions

![Share of Phase 1 entrants still in development at each phase, all programs and those developed in the US, against BIO 2011–2020](report/output/figures/phase_funnel.png)

### How LOA moves with each definition

{{SENSITIVITY_TABLE}}

### Change over time

{{SECTION1_TIME}}

### How each label was made, and how good it is

Every judgement in this analysis is an LLM call (Claude) that reads the source record and returns a structured answer, stored with its prompt, input, model and code version. Disease mapping, entity resolution, trial purpose and roles, approvals, stop reasons, trial outcomes, modality, disease area and targets were all made this way, not with keyword rules. For each high-stakes label, a seeded random sample was re-derived independently by agents working from the primary sources (registry records, PubMed, Drugs@FDA, DailyMed, CBER pages) before they saw the stored answer. Agreement counts answers judged correct or defensibly different under the same rules.

{{QUALITY_TABLE}}

Each error pattern these audits found was fixed at its source and the affected labels re-derived, not patched by hand. The latest round was a full rebuild: trials whose only interventions are combination products or genetic agents were added; each condition is mapped with its trials' titles and start years, so that it is read as its sponsors meant it (SARS wording in trials from 2020 on is COVID-19); a condition mapped only to a broader term no longer starts a program of its own; development codes resolve to the parent substance rather than a salt, hydrate or formulation; FDA products link only their principal active ingredients; efficacy supplements with no FDA letter are read from their label or review; approval judgements see each program's trial eligibility criteria and the disease's full ancestry; publication-based outcomes are judged against the registered primary outcomes; and endpoint classes are decided knowing the drug's targets. The figures above come from fresh samples drawn after that rebuild. The remaining entity errors are mostly development codes whose nonproprietary name is too recent for the FDA substance registry to list the code, and a few nutrients and excipients registered only as an unspecified form. Programs whose approval is judged "uncertain" ({{section1.scale.approvals_uncertain|int}} of {{section1.scale.approval_judgements|int}} judgements) count as not approved; counting them as approved instead moves no rate by more than a tenth of a percentage point (sensitivity table). The approval audit's strata are those of the judgements it sampled.

Three labels were also compared with the decisions their revised prompts replaced. Trial purposes and roles agree with the earlier decisions on {{quality.retest.trial_purpose|pct0}} and {{quality.retest.trial_moiety_role|pct0}} of trials, and disease mapping chose the same MONDO term for {{quality.retest.indication_mondo|pct0}} of conditions. ClinicalTrials.gov's own MeSH indexing is no substitute: its terms belong to a study rather than a condition, so only {{quality.mesh_crosswalk.attributable_share|pct0}} of condition strings can be given one, and where both routes name a disease, MeSH carried to MONDO agrees with the mapping for {{quality.mesh_crosswalk.same_share|pct0}} ({{quality.mesh_crosswalk.broader_share|pct0}} broader, {{quality.mesh_crosswalk.different_share|pct0}} another disease) and gives a disease to {{quality.mesh_crosswalk.non_disease|int}} conditions that are not diseases, such as healthy volunteers; a hand review of {{quality.mesh_crosswalk.review.sample|int}} disagreements favoured the mapping {{quality.mesh_crosswalk.review.llm|int}} times to MeSH's {{quality.mesh_crosswalk.review.mesh|int}}. Modality, disease area and targets were not audited. The Phase 2 endpoint classes were audited on a seeded sample of trials, and the mechanism and mouse-model labels were spot-checked (Phase 2 analysis).

{{APPENDIX_STOPS}}

{{APPENDIX_SECTION2}}

{{APPENDIX_SECTION3}}

{{APPENDIX_CATEGORIES}}

### Limitations

* **Registry programs are not Biomedtracker programs.** BIO counts transitions that analysts record for programs companies disclose; this report counts programs from registered trials. Trials registered only outside ClinicalTrials.gov (ChiCTR, EU CTR, CTIS) are missing, so programs developed there look suspended. Restricting to programs with a US site removes most of the difference.
* **Suspension is inferred from inactivity.** A program counts as suspended when none of its trials has been active within {{section1.lag_months}} months. The rates move with that window (sensitivity table); BIO dates suspensions from company disclosures instead.
* **Section 1 stops at 2019 entries.** Programs that entered a phase in 2020–2025 are largely still running, and the success rate counts only resolved programs, so the headline takes entries from 2008–2019, each with at least six years to resolve. Entries from 2015–2025 are shown as a sensitivity.
* **Older entrants are recorded less completely.** Phase 1 trials need not be registered, and registration grew more complete over the window. CBER approvals (vaccines, blood products, cell and gene therapies) are read from letters only from 2015, and earlier ones are dated from current labels.
* **Outcome is FDA approval only.** Approvals elsewhere count as no approval.
* **Symptom and procedure indications without a MONDO term** (pain, cough, contraception; about 3% of trials) are grouped in each entity's disease-unspecified program, followed through Phase 2 but not to approval.
* **Most stopped programs give no reason.** Reasons come from the registry's why-stopped field, posted results and abstracts of results papers. Published results favour positive findings, and a missing reason is reported as such, not inferred. A vague reason ("sponsor decision", "business reasons") may hide an efficacy or safety result. Where the registry gives no usable reason, the cause was traced from company releases, filings and news (appendix on stops); the efficacy share after tracing is an upper estimate, and safety is likely under-counted.
* **The model declines some products.** Claude declines to classify some products derived from pathogens, toxins or live bacterial and viral vectors (botulinum and plague vaccines, oncolytic viruses, engineered bacteria) on every attempt: {{quality.refusals.moiety_targets|int}} entities have no resolved target and {{quality.refusals.moiety_modality|int}} no modality, so they fall out of the evidence analysis and the modality strata.
* **Constraint is current; essentiality starts in 2019.** gnomAD v4.1 constraint comes from that release, not as of phase entry. The common-essential flag uses the last DepMap release of each year from 2019, when DepMap first published the list; programs that entered a phase before 2020 are never flagged, so the flag is a lower bound for them.
* **Evidence as of phase entry undercounts.** The yearly series count only dated evidence. Cancer Gene Census, Orphanet, UniProt, Reactome and PanelApp entries without a publication, and IMPC knockouts first released after 2024, have no date; a sensitivity uses the 2026 scores instead.
* **The Phase 2 analysis rests on labels made for it.** The trial endpoint class, the germline mechanism of each target in each disease and the orientation of each mouse model were classified by an LLM without the drug's name. The endpoint classifier was audited on {{section3.endpoint_audit.trials|int}} trials ({{section3.endpoint_audit.class_correct|int}} classes and {{section3.endpoint_audit.governing_index_correct|int}} governing outcomes right); the mechanism and mouse labels were spot-checked, and the errors found there led to a revised prompt rather than hand corrections.
* **Some evidence is dated approximately.** Open Targets dates ClinVar records by their latest review; here each record takes the year it was created, read off its accession number, so a variant first submitted as uncertain and reclassified pathogenic later counts from its first submission. IMPC knockouts take the year of the first IMPC data release with calls for the allele (none before 2015) and MGI models the year of their first paper. Open Targets dates every Project Score row 2024, from the re-analysis that now supplies it; here each target–cancer pair takes the year of the first Open Targets release that listed it ({{section2.project_score.n_2019|int}} pairs from 2019, {{section2.project_score.n_2024|int}} from 2024). Gene-burden results start in 2019, and GWAS on measurement traits cannot be matched to a disease, so these lines are undercounted in the Phase 2 analysis.
* **The Phase 2 analysis's post-hoc checks are exploratory.** The direction analyses and the three direction rules were added after the plan was committed, once their labels existed; their intervals are not corrected for the number of comparisons.
