## Appendix

### Data

| Source | What it gives | Version |
| :---- | :---- | :---- |
| ClinicalTrials.gov API v2 | Every interventional drug or biological study: phases, status, dates, sponsor, arms, interventions, conditions, sites, why stopped, posted results | Snapshot {{section1.snapshot}} ({{section1.scale.ctgov_studies|int}} studies) |
| PubMed | Results papers linked to completed trials without posted results (registry RESULT/DERIVED references and the NCT secondary identifier) | Retrieved {{section1.snapshot}} |
| Drugs@FDA, FDA approval letters, openFDA labels | NDA/BLA applications, submissions and action dates; {{section1.scale.fda_approved_uses|int}} approved uses read from 2015–2026 approval letters; current Indications and Usage text | Retrieved October 2026 |
| CBER yearly approval pages, product pages and letters | {{section1.scale.cber_applications|int}} biologics applications (vaccines, blood products, cell and gene therapies) and their 2015–2025 approval actions, verified by an independent second enumeration | Retrieved October 2026 |
| FDA Global Substance Registration System | UNII substance identifiers and every registered name (official, common, code, brand) | 2026-08-04 |
| MONDO, EFO | Disease ontology and hierarchy | MONDO 2026-10-06, EFO 3.95 |
| Open Targets Platform | Target–disease associations by data source, with yearly score series | 26.09 |
| gnomAD | Loss-of-function constraint (LOEUF) | v4.1 |
| DepMap | Pan-essential genes from CRISPR (Chronos) screens | Release not recorded in the project database |

### How each label was made, and how good it is

Every judgement in the pipeline is an LLM call (Claude) that reads the source record and returns a structured answer, stored with its prompt, input, model and code version. Disease mapping, entity resolution, trial purpose and roles, approvals, stop reasons, trial outcomes, modality, disease area and targets were all made this way, not with keyword rules. For each high-stakes label, a seeded random sample was re-derived independently by agents working from the primary sources (registry records, PubMed, Drugs@FDA, DailyMed, CBER pages) before they saw the stored answer. Agreement counts answers judged correct or defensibly different under the same rules.

{{QUALITY_TABLE}}

Each error pattern these audits found was fixed in the pipeline and the affected labels re-derived, not patched by hand: diseases MONDO has no exact term for now map to their nearest broader term; development codes resolve to UNII substances, and the same substance under two names is merged; scanned FDA letters are read by OCR; labelling-only supplements no longer count as approvals; stop reasons stated only in a trial's summary are read; publication-based outcomes use only the abstracts given; and approval dates account for older applications of the same drug. The disease-mapping, entity and approval figures above come from fresh samples drawn after those fixes; before them, disease mapping agreed 94% of the time, entity resolution 95%, and 8 of 25 dated first approvals were wrong. Remaining entity errors are scattered (a development code resolved to the wrong substance, a salt chosen over its parent) rather than systematic. Programs whose approval is judged "uncertain" ({{section1.scale.approvals_uncertain|int}} of {{section1.scale.approval_judgements|int}} judgements) count as not approved; counting them as approved instead leaves every rate unchanged to the first decimal (sensitivity table). The approval audit's strata are those of the judgements it sampled; it was re-scored after the final rebuild against the auditors' own answers, and programs that are no longer development programs left the sample. The audit of the earlier draft, with every claim's verdict and every data issue, is in `AUDIT.md`.

### Limitations

* **Registry programs are not Biomedtracker programs.** BIO counts transitions that analysts record for programs companies disclose; this report counts programs from registered trials. Trials registered only outside ClinicalTrials.gov (ChiCTR, EU CTR, CTIS) are missing, so programs developed there look suspended. Restricting to programs with a US site removes most of the difference.
* **Suspension is inferred from inactivity.** A program counts as suspended when none of its trials has been active within {{section1.lag_months}} months. The rates move with that window (sensitivity table); BIO dates suspensions from company disclosures instead.
* **Recent entrants are mostly unresolved.** Programs that entered a phase in 2023–2025 are largely still running; the success rate counts only resolved programs, so it leans on early failures. Entries from 2015–2019 alone, with at least six years of follow-up, are shown as a sensitivity.
* **Outcome is FDA approval only.** Approvals elsewhere count as no approval.
* **Symptom and procedure indications without a MONDO term** (pain, cough, contraception; about 3% of trials) are grouped in each entity's disease-unspecified program, followed through Phase 2 but not to approval.
* **Most stopped programs give no reason.** Reasons come from the registry's why-stopped field, posted results and abstracts of results papers. Published results favour positive findings, and a missing reason is reported as such, not inferred.
* **The model declines some products.** Claude declines to classify some products derived from pathogens, toxins or live bacterial and viral vectors (botulinum and plague vaccines, oncolytic viruses, engineered bacteria) on every attempt: {{quality.refusals.moiety_targets|int}} entities have no resolved target and {{quality.refusals.moiety_modality|int}} no modality, so they fall out of Section 2 and the modality strata.
* **Evidence as of phase entry undercounts.** Open Targets leaves undated evidence out of its yearly series; a sensitivity uses the 2026 scores instead.
