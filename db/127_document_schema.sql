-- Document every table and column of preclin, public and pv_evidence that had no comment, and rewrite the
-- comments that named tables no longer there. Comments state what a row is, which step writes it, and for each
-- column its meaning, values and what null means; columns from an earlier import that no step writes or reads
-- say so. Tables still being built elsewhere (literature, cell dependency) are documented by their own
-- migrations. Also: an index for reading the long-form evidence values by line, and the evidence store's input
-- fingerprint (report.evidence_lines check).

BEGIN;
SET LOCAL lock_timeout = '3s';

ALTER TABLE preclin.evidence_line_build ADD COLUMN inputs jsonb NOT NULL DEFAULT '{}';
COMMENT ON COLUMN preclin.evidence_line_build.inputs IS
    'Fingerprint of the inputs the store read beyond the programs build (report.evidence_lines.input_fingerprint): the programs snapshot, rows and latest llm_decision_id of each LLM label table, the latest source release of the ChEMBL potencies and computed properties, and the rows of preclin.cell_dependency once it exists. python -m report.evidence_lines check compares it with the inputs now; empty for stores made before it was recorded.';

CREATE INDEX IF NOT EXISTS evidence_entry_line_line_idx ON preclin.evidence_entry_line (line_key);

-- preclin.analysis_method
COMMENT ON COLUMN preclin.analysis_method.parameters IS 'The method''s parameters as run (cohort bounds, seeds, sample sizes, thresholds), as the step recorded them.';
COMMENT ON COLUMN preclin.analysis_method.inputs IS 'Tables and other sources the method reads, e.g. preclin.dev_program or "web search".';
COMMENT ON COLUMN preclin.analysis_method.version IS 'Version part of method_id (v1, v2, ...); a changed procedure is recorded under a new version.';
COMMENT ON COLUMN preclin.analysis_method.name IS 'Plain-English name of the method.';
COMMENT ON COLUMN preclin.analysis_method.recorded_at IS 'When the step recorded the method.';
COMMENT ON COLUMN preclin.analysis_method.code_commit IS 'Git commit of the code that ran the method.';

-- preclin.chembl_activity
COMMENT ON COLUMN preclin.chembl_activity.activity_id IS 'ChEMBL activity id.';
COMMENT ON COLUMN preclin.chembl_activity.bao_label IS 'Label of bao_format: cell-based format, single protein format, assay format, ...';
COMMENT ON COLUMN preclin.chembl_activity.target_chembl_id IS 'The ChEMBL target measured (preclin.chembl_target).';
COMMENT ON COLUMN preclin.chembl_activity.parent_chembl_id IS 'ChEMBL parent molecule of molecule_chembl_id; preclin.chembl_moiety maps it to an entity.';
COMMENT ON COLUMN preclin.chembl_activity.source_release_id IS 'ChEMBL release the row was read from (preclin.evidence_source_release).';
COMMENT ON COLUMN preclin.chembl_activity.assay_chembl_id IS 'ChEMBL assay the activity belongs to.';
COMMENT ON COLUMN preclin.chembl_activity.document_chembl_id IS 'Document reporting the activity (preclin.chembl_document), which dates it.';

-- preclin.chembl_document
COMMENT ON COLUMN preclin.chembl_document.journal IS 'Journal abbreviation as ChEMBL gives it; empty or null for patents and deposited datasets.';
COMMENT ON COLUMN preclin.chembl_document.document_chembl_id IS 'ChEMBL document id.';
COMMENT ON COLUMN preclin.chembl_document.source_release_id IS 'ChEMBL release the row was read from (preclin.evidence_source_release).';

-- preclin.chembl_mechanism
COMMENT ON TABLE preclin.chembl_mechanism IS
    'Every drug mechanism of action record in the ChEMBL release, with the human genes of its target (python -m pipeline.chembl load). pipeline.targets shows these records to the LLM that assigns each entity''s targets.';
COMMENT ON COLUMN preclin.chembl_mechanism.mec_id IS 'ChEMBL mechanism record id.';
COMMENT ON COLUMN preclin.chembl_mechanism.molecule_chembl_id IS 'Molecule the mechanism is recorded for.';
COMMENT ON COLUMN preclin.chembl_mechanism.parent_chembl_id IS 'Parent molecule of molecule_chembl_id (the molecule itself when it is a parent).';
COMMENT ON COLUMN preclin.chembl_mechanism.target_chembl_id IS 'ChEMBL target the mechanism acts on; null when ChEMBL names none.';
COMMENT ON COLUMN preclin.chembl_mechanism.target_name IS 'ChEMBL preferred name of target_chembl_id; null when there is no target.';
COMMENT ON COLUMN preclin.chembl_mechanism.action_type IS 'ChEMBL action type: INHIBITOR, ANTAGONIST, AGONIST, BINDING AGENT, BLOCKER, MODULATOR, ...; null when there is no target.';
COMMENT ON COLUMN preclin.chembl_mechanism.mechanism_of_action IS 'ChEMBL''s description of the mechanism, e.g. Glucocorticoid receptor agonist.';
COMMENT ON COLUMN preclin.chembl_mechanism.symbols IS 'HGNC approved symbols of the target''s human UniProt components (several for a complex); empty for a non-human or unmapped target.';
COMMENT ON COLUMN preclin.chembl_mechanism.source_release_id IS 'ChEMBL release the row was read from (preclin.evidence_source_release).';

-- preclin.chembl_moiety
COMMENT ON COLUMN preclin.chembl_moiety.moiety_id IS 'Molecular entity (preclin.moiety).';
COMMENT ON COLUMN preclin.chembl_moiety.parent_chembl_id IS 'ChEMBL parent molecule matched to the entity.';
COMMENT ON COLUMN preclin.chembl_moiety.source_release_id IS 'ChEMBL release the match was made against (preclin.evidence_source_release).';

-- preclin.chembl_molecule
COMMENT ON TABLE preclin.chembl_molecule IS
    'ChEMBL molecule -> parent molecule for every ChEMBL id preclin.drug carries (python -m pipeline.chembl load); salts and other forms map to their parent.';
COMMENT ON COLUMN preclin.chembl_molecule.molecule_chembl_id IS 'ChEMBL molecule id.';
COMMENT ON COLUMN preclin.chembl_molecule.parent_chembl_id IS 'Its parent molecule (the molecule itself when it is a parent).';
COMMENT ON COLUMN preclin.chembl_molecule.source_release_id IS 'ChEMBL release the row was read from (preclin.evidence_source_release).';

-- preclin.chembl_target
COMMENT ON COLUMN preclin.chembl_target.organism IS 'Organism of the target: always Homo sapiens, since only human targets are kept.';
COMMENT ON COLUMN preclin.chembl_target.pref_name IS 'ChEMBL preferred target name.';
COMMENT ON COLUMN preclin.chembl_target.target_chembl_id IS 'ChEMBL target id.';
COMMENT ON COLUMN preclin.chembl_target.source_release_id IS 'ChEMBL release the row was read from (preclin.evidence_source_release).';

-- preclin.clinvar_accession_calibration
COMMENT ON COLUMN preclin.clinvar_accession_calibration.rcv_number IS 'Numeric part of the sampled ClinVar RCV accession.';
COMMENT ON COLUMN preclin.clinvar_accession_calibration.created IS 'Date the RCV record was first submitted to ClinVar.';
COMMENT ON COLUMN preclin.clinvar_accession_calibration.source_release_id IS 'The calibration run (preclin.evidence_source_release, clinvar_record_creation_calibration).';

-- preclin.ctgov_result_summary
COMMENT ON TABLE preclin.ctgov_result_summary IS
    'Primary-outcome results posted on ClinicalTrials.gov, one row per trial with a results section, condensed to text for the LLM steps (python -m pipeline.outcomes results).';
COMMENT ON COLUMN preclin.ctgov_result_summary.nct_id IS 'The trial (preclin.ctgov_study).';
COMMENT ON COLUMN preclin.ctgov_result_summary.summary IS 'Each primary outcome measure with its time frame, parameter type, unit and per-group values (with the number analysed), as text.';
COMMENT ON COLUMN preclin.ctgov_result_summary.analyses IS 'Statistical analyses posted for the primary measures (groups, p-value, parameter, confidence interval), as a JSON array.';
COMMENT ON COLUMN preclin.ctgov_result_summary.n_analyses IS 'Number of posted statistical analyses of the primary measures.';

-- preclin.ctgov_study
COMMENT ON TABLE preclin.ctgov_study IS
    'One row per interventional ClinicalTrials.gov study with a drug, biological, genetic or combination-product intervention, any sponsor and date, from the API v2 snapshot (python -m pipeline.ctgov fetch, load). Coded fields keep the registry''s own values.';
COMMENT ON COLUMN preclin.ctgov_study.nct_id IS 'NCT id.';
COMMENT ON COLUMN preclin.ctgov_study.brief_title IS 'Brief title.';
COMMENT ON COLUMN preclin.ctgov_study.official_title IS 'Official title; null when the registry gives none.';
COMMENT ON COLUMN preclin.ctgov_study.overall_status IS 'Recruitment status at the snapshot: COMPLETED, RECRUITING, TERMINATED, ACTIVE_NOT_RECRUITING, NOT_YET_RECRUITING, WITHDRAWN, SUSPENDED, ENROLLING_BY_INVITATION or UNKNOWN.';
COMMENT ON COLUMN preclin.ctgov_study.why_stopped IS 'Free-text reason the registry gives for stopping; null when none.';
COMMENT ON COLUMN preclin.ctgov_study.phases IS 'Phases listed: EARLY_PHASE1, PHASE1, PHASE2, PHASE3, PHASE4 or NA (a Phase 1/2 trial lists two).';
COMMENT ON COLUMN preclin.ctgov_study.start_date IS 'Start date; a month-only date is the 1st. A started study with no registered start date gets the earliest of its first submission and completion dates (start_date_type UPPER_BOUND).';
COMMENT ON COLUMN preclin.ctgov_study.start_date_type IS 'ACTUAL, ESTIMATED, UPPER_BOUND (set by the loader, see start_date), or null when the registry gives no type.';
COMMENT ON COLUMN preclin.ctgov_study.primary_completion_date IS 'Primary completion date; a month-only date is the 1st.';
COMMENT ON COLUMN preclin.ctgov_study.primary_completion_date_type IS 'ACTUAL or ESTIMATED; null when not given.';
COMMENT ON COLUMN preclin.ctgov_study.completion_date IS 'Study completion date; a month-only date is the 1st.';
COMMENT ON COLUMN preclin.ctgov_study.completion_date_type IS 'ACTUAL or ESTIMATED; null when not given.';
COMMENT ON COLUMN preclin.ctgov_study.first_posted IS 'Date the record was first posted.';
COMMENT ON COLUMN preclin.ctgov_study.last_update_posted IS 'Date of the last posted update.';
COMMENT ON COLUMN preclin.ctgov_study.results_first_posted IS 'Date results were first posted; null when none are.';
COMMENT ON COLUMN preclin.ctgov_study.has_results IS 'Results are posted on ClinicalTrials.gov.';
COMMENT ON COLUMN preclin.ctgov_study.lead_sponsor IS 'Lead sponsor name.';
COMMENT ON COLUMN preclin.ctgov_study.lead_sponsor_class IS 'Lead sponsor class: INDUSTRY, OTHER, NIH, OTHER_GOV, NETWORK, FED, INDIV or UNKNOWN. INDUSTRY marks an industry trial throughout the analysis.';
COMMENT ON COLUMN preclin.ctgov_study.collaborators IS 'Collaborators as a JSON array of {name, class}.';
COMMENT ON COLUMN preclin.ctgov_study.enrollment IS 'Enrollment count as the registry gives it (actual or anticipated); null when not given.';
COMMENT ON COLUMN preclin.ctgov_study.allocation IS 'RANDOMIZED, NON_RANDOMIZED or NA (single group); null when not given.';
COMMENT ON COLUMN preclin.ctgov_study.intervention_model IS 'PARALLEL, SINGLE_GROUP, CROSSOVER, SEQUENTIAL or FACTORIAL; null when not given.';
COMMENT ON COLUMN preclin.ctgov_study.masking IS 'NONE, SINGLE, DOUBLE, TRIPLE or QUADRUPLE; null when not given.';
COMMENT ON COLUMN preclin.ctgov_study.primary_purpose IS 'TREATMENT, PREVENTION, BASIC_SCIENCE, DIAGNOSTIC, SUPPORTIVE_CARE, SCREENING, HEALTH_SERVICES_RESEARCH, OTHER, ...; null when not given.';
COMMENT ON COLUMN preclin.ctgov_study.healthy_volunteers IS 'The registry says healthy volunteers are accepted; null when not stated.';
COMMENT ON COLUMN preclin.ctgov_study.conditions IS 'Conditions as listed in the record.';
COMMENT ON COLUMN preclin.ctgov_study.keywords IS 'Keywords as listed in the record.';
COMMENT ON COLUMN preclin.ctgov_study.interventions IS 'Interventions as a JSON array of {name, type, description, otherNames, armGroupLabels}.';
COMMENT ON COLUMN preclin.ctgov_study.arm_groups IS 'Arm groups as a JSON array of {label, type, description, interventionNames}.';
COMMENT ON COLUMN preclin.ctgov_study.references_ IS 'References as a JSON array of {pmid, type, citation}; type RESULT or DERIVED marks a results paper.';
COMMENT ON COLUMN preclin.ctgov_study.countries IS 'Distinct countries of the study''s locations; empty when none are listed.';
COMMENT ON COLUMN preclin.ctgov_study.brief_summary IS 'Brief summary text.';
COMMENT ON COLUMN preclin.ctgov_study.primary_outcomes IS 'Primary outcome measures as a JSON array of {measure, timeFrame, description}.';
COMMENT ON COLUMN preclin.ctgov_study.source_release_id IS 'The snapshot (preclin.evidence_source_release, clinicaltrials_gov_api_v2).';

-- preclin.ctgov_study_drug
COMMENT ON TABLE preclin.ctgov_study_drug IS
    'Drug, biological, genetic and combination-product interventions of each in-scope trial (Early Phase 1 to Phase 3), one row per (trial, intervention name) (python -m pipeline.programs register).';
COMMENT ON COLUMN preclin.ctgov_study_drug.nct_id IS 'The trial (preclin.ctgov_study).';
COMMENT ON COLUMN preclin.ctgov_study_drug.drug_id IS 'The intervention name (preclin.drug).';
COMMENT ON COLUMN preclin.ctgov_study_drug.intervention_type IS 'DRUG, BIOLOGICAL, COMBINATION_PRODUCT or GENETIC, as registered.';
COMMENT ON COLUMN preclin.ctgov_study_drug.arm_types IS 'Types of the arms the intervention is given in (EXPERIMENTAL, PLACEBO_COMPARATOR, ...); UNKNOWN for an arm the record does not type.';
COMMENT ON COLUMN preclin.ctgov_study_drug.other_names IS 'Up to ten other names the record gives for the intervention.';

-- preclin.ctgov_study_indication
COMMENT ON TABLE preclin.ctgov_study_indication IS
    'Conditions of each in-scope trial (Early Phase 1 to Phase 3), one row per (trial, condition string) (python -m pipeline.programs register).';
COMMENT ON COLUMN preclin.ctgov_study_indication.nct_id IS 'The trial (preclin.ctgov_study).';
COMMENT ON COLUMN preclin.ctgov_study_indication.indication_id IS 'The condition string (preclin.indication).';

-- preclin.ctgov_study_moiety
COMMENT ON TABLE preclin.ctgov_study_moiety IS
    'Role of each molecular entity in each trial (python -m pipeline.programs roles): one row per (trial, entity).';
COMMENT ON COLUMN preclin.ctgov_study_moiety.nct_id IS 'The trial (preclin.ctgov_study).';
COMMENT ON COLUMN preclin.ctgov_study_moiety.moiety_id IS 'The entity (preclin.moiety).';
COMMENT ON COLUMN preclin.ctgov_study_moiety.role IS 'investigational (what the trial develops or tests), background (given in every arm, or a partner, premedication or probe drug) or comparator (the active or placebo control).';
COMMENT ON COLUMN preclin.ctgov_study_moiety.method IS 'arm_types (one entity in the trial, or a non-industry trial: comparator when it appears only in comparator arms, else investigational) or llm (task trial_moiety_role).';
COMMENT ON COLUMN preclin.ctgov_study_moiety.llm_decision_id IS 'The trial_moiety_role decision; null for method arm_types.';

-- preclin.depmap_common_essential
COMMENT ON COLUMN preclin.depmap_common_essential.entrez_id IS 'Entrez gene id as DepMap lists it.';
COMMENT ON COLUMN preclin.depmap_common_essential.symbol IS 'Gene symbol as DepMap lists it.';
COMMENT ON COLUMN preclin.depmap_common_essential.source_release_id IS 'The DepMap release (preclin.evidence_source_release, depmap_common_essentials).';

-- preclin.dev_program
COMMENT ON TABLE preclin.dev_program IS
    'One row per development program: a molecular entity tested in one indication (the MONDO disease representing a group of the entity''s diseases, preclin.program_indication), or the entity''s disease-unspecified program (mondo_id null), assembled from its investigational trials in Early Phase 1 to Phase 3, any sponsor (python -m pipeline.programs build). Each build replaces the table and reassigns program_id, so stable keys are (moiety_id, mondo_id).';
COMMENT ON COLUMN preclin.dev_program.program_id IS 'Row id; reassigned by every build.';
COMMENT ON COLUMN preclin.dev_program.moiety_id IS 'The entity (preclin.moiety).';
COMMENT ON COLUMN preclin.dev_program.mondo_id IS 'The indication''s representative MONDO disease; null for the disease-unspecified program (trials of symptoms, procedures, healthy volunteers or no condition).';
COMMENT ON COLUMN preclin.dev_program.ph1_start IS 'Start of the program''s earliest attached Phase 1 trial (Early Phase 1 counts as 1); null when none.';
COMMENT ON COLUMN preclin.dev_program.ph2_start IS 'Start of the earliest attached Phase 2 trial that can mark phase entry (dev_program_trial.starts_phase; Phase 1/2 counts as 2); null when none.';
COMMENT ON COLUMN preclin.dev_program.ph3_start IS 'Start of the earliest attached Phase 3 trial that can mark phase entry (dev_program_trial.starts_phase); null when none.';
COMMENT ON COLUMN preclin.dev_program.first_start IS 'Start of the program''s earliest attached trial.';
COMMENT ON COLUMN preclin.dev_program.highest_phase IS 'Highest phase among attached trials: 1, 2 or 3 (a trial''s phase is the highest it lists).';
COMMENT ON COLUMN preclin.dev_program.n_trials IS 'Attached trials, any sponsor.';
COMMENT ON COLUMN preclin.dev_program.n_industry_trials IS 'Attached trials with an industry lead sponsor.';
COMMENT ON COLUMN preclin.dev_program.first_industry_start IS 'Start of the earliest attached industry trial; null when there is none.';
COMMENT ON COLUMN preclin.dev_program.lead_sponsors IS 'Up to five industry lead sponsors of attached trials, most frequent first.';
COMMENT ON COLUMN preclin.dev_program.last_activity IS 'Latest end (completion, else primary completion, else start) of an attached trial, or the snapshot date while one is active; never after the snapshot date.';
COMMENT ON COLUMN preclin.dev_program.n_active_trials IS 'Attached trials recruiting, active not recruiting, enrolling by invitation or not yet recruiting at the snapshot.';
COMMENT ON COLUMN preclin.dev_program.build_id IS 'The build that wrote the row (preclin.dev_program_build).';

-- preclin.dev_program_approval
COMMENT ON TABLE preclin.dev_program_approval IS
    'FDA approval of each development program''s disease, judged by an LLM for every program whose entity has an FDA application (python -m pipeline.approvals judge, task program_fda_approval). A program whose entity has no application is not approved and has no row.';
COMMENT ON COLUMN preclin.dev_program_approval.program_id IS 'The program (preclin.dev_program).';
COMMENT ON COLUMN preclin.dev_program_approval.approved IS 'yes, no or uncertain (counted as not approved).';
COMMENT ON COLUMN preclin.dev_program_approval.first_approval_date IS 'Action date of the first approval for the disease when date_basis is dated; null otherwise.';
COMMENT ON COLUMN preclin.dev_program_approval.relation IS 'How the approved use relates to the program disease: same_disease, subtype_or_subpopulation (the approved use is narrower), broader (the approved use covers a broader disease including it) or none.';
COMMENT ON COLUMN preclin.dev_program_approval.evidence IS 'Short verbatim quote from the approval event, label or trial that supports the answer.';
COMMENT ON COLUMN preclin.dev_program_approval.llm_decision_id IS 'The program_fda_approval decision.';

-- preclin.dev_program_build
COMMENT ON TABLE preclin.dev_program_build IS
    'Each run of python -m pipeline.programs build, one row per build of preclin.dev_program.';
COMMENT ON COLUMN preclin.dev_program_build.build_id IS 'Build id; preclin.dev_program.build_id references it.';
COMMENT ON COLUMN preclin.dev_program_build.built_at IS 'When the build ran.';
COMMENT ON COLUMN preclin.dev_program_build.code_commit IS 'Git commit of the code that ran the build.';
COMMENT ON COLUMN preclin.dev_program_build.snapshot IS 'ClinicalTrials.gov snapshot the build read (source_version of its clinicaltrials_gov_api_v2 release).';
COMMENT ON COLUMN preclin.dev_program_build.parameters IS 'Build rules and counts: phases in scope, active statuses, how shared trials mark entry, n_programs, n_links.';

-- preclin.dev_program_trial
COMMENT ON TABLE preclin.dev_program_trial IS
    'Trials attached to each development program (python -m pipeline.programs build), one row per (program, trial).';
COMMENT ON COLUMN preclin.dev_program_trial.program_id IS 'The program (preclin.dev_program).';
COMMENT ON COLUMN preclin.dev_program_trial.nct_id IS 'The trial (preclin.ctgov_study).';
COMMENT ON COLUMN preclin.dev_program_trial.phase IS 'The trial''s phase: the highest it lists, with Early Phase 1 as 1 and Phase 1/2 as 2.';
COMMENT ON COLUMN preclin.dev_program_trial.attach IS 'How the trial attaches: disease (it lists the program''s disease or one grouped into it), broader_condition (it lists a broader term, or a condition mapped only to a broader term, that contains the program''s disease), basket (a multi-indication trial shared by the programs of the diseases it lists), no_disease (healthy volunteers or no condition, shared by the entity''s programs) or non_disease_condition (only symptoms, procedures or other conditions without a MONDO term; it attaches to the disease-unspecified program).';
COMMENT ON COLUMN preclin.dev_program_trial.marks_entry IS 'Whether the trial can mark this program''s phase entry: always for a trial of its own disease; for a shared trial, only for programs whose own first trial had started by then or that began next after it.';

-- preclin.drug
COMMENT ON TABLE preclin.drug IS
    'Distinct intervention names from in-scope ClinicalTrials.gov trials, one row per name keyed by its lower-case alphanumerics, registered by python -m pipeline.programs register and resolved to molecular entities by python -m pipeline.drugs canonicalize (preclin.drug_moiety). Rows from an earlier import have other resolved_via values, and many columns are from that import and no longer written or read.';
COMMENT ON COLUMN preclin.drug.drug_id IS 'Row id; preclin.ctgov_study_drug and preclin.drug_moiety reference it.';
COMMENT ON COLUMN preclin.drug.normalized_name IS 'Lower-case alphanumerics of the name: the key trial interventions are matched on.';
COMMENT ON COLUMN preclin.drug.display_name IS 'Most frequent spelling of the name in the trials.';
COMMENT ON COLUMN preclin.drug.synonyms IS 'Up to ten other names the trials give for the intervention.';
COMMENT ON COLUMN preclin.drug.entity_kind IS 'What the name is (task drug_moiety): drug, combination, placebo_or_vehicle, vaccine, non_drug or unclear; null when the name has not been resolved.';
COMMENT ON COLUMN preclin.drug.moiety_decision_id IS 'The drug_moiety decision that resolved the name; null when it was linked by exact name or has not been resolved.';
COMMENT ON COLUMN preclin.drug.chembl_id IS 'ChEMBL molecule id, from the earlier import; python -m pipeline.chembl load reads it to find each drug''s ChEMBL molecules.';
COMMENT ON COLUMN preclin.drug.created_at IS 'When the row was created.';
COMMENT ON COLUMN preclin.drug.updated_at IS 'When the row was last updated.';
COMMENT ON COLUMN preclin.drug.primary_action_type IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.drugbank_id IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.modality IS 'From an earlier import; no current pipeline step writes or reads it. The entity''s modality is preclin.moiety.modality.';
COMMENT ON COLUMN preclin.drug.modality_subtype IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.mechanism IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.route_of_admin IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.is_placebo IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.is_combination IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.is_biosimilar IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.resolved_confidence IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.resolved_at IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.notes IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.chembl_max_phase IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.chembl_lookup_at IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.chembl_resolved_via IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.primary_target_chembl IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.mechanism_of_action IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.n_mechanisms IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.chembl_mechanism_fetched_at IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.bioactivity_pchembl_median IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.bioactivity_n_targets_1um IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.bioactivity_n_records IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.bioactivity_fetched_at IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.drug.resolved_via IS 'Where the row came from: ctgov_snapshot (python -m pipeline.programs register); unresolved, chembl_bulk, llm_sonnet, llm_sonnet_verified, llm_haiku and public_therapy mark rows from the earlier import.';
COMMENT ON COLUMN preclin.drug.is_globally_approved IS 'From an earlier import; no current pipeline step writes or reads it.';

-- preclin.drug_moiety
COMMENT ON TABLE preclin.drug_moiety IS
    'Molecular entities each intervention name contains (python -m pipeline.drugs canonicalize), one row per (name, entity).';
COMMENT ON COLUMN preclin.drug_moiety.drug_id IS 'The intervention name (preclin.drug).';
COMMENT ON COLUMN preclin.drug_moiety.moiety_id IS 'The entity (preclin.moiety).';
COMMENT ON COLUMN preclin.drug_moiety.role IS 'investigational (what the trial develops in that arm) or background (a partner or standard therapy named with it).';
COMMENT ON COLUMN preclin.drug_moiety.method IS 'llm (task drug_moiety) or exact_name (the name equals a name, code or alias of an entity already resolved to a UNII substance).';
COMMENT ON COLUMN preclin.drug_moiety.llm_decision_id IS 'The drug_moiety decision; null for method exact_name.';
COMMENT ON COLUMN preclin.drug_moiety.biosimilar_of IS 'Reference product''s name when the name is a biosimilar of it; null otherwise.';

-- preclin.evidence_entry
COMMENT ON COLUMN preclin.evidence_entry.moiety_id IS 'The entity (preclin.moiety).';
COMMENT ON COLUMN preclin.evidence_entry.phase IS 'Phase entered: 1, 2 or 3.';
COMMENT ON COLUMN preclin.evidence_entry.entry_date IS 'Date the program entered the phase: start of its first industry trial of the phase (report.section1.phase_rows).';
COMMENT ON COLUMN preclin.evidence_entry.entry_year IS 'Year of entry_date.';
COMMENT ON COLUMN preclin.evidence_entry.modality IS 'The entity''s modality (preclin.moiety.modality).';
COMMENT ON COLUMN preclin.evidence_entry.bio_area IS 'BIO disease area of the program disease (preclin.mondo_bio_area); unmapped when the disease has none or the program is disease-unspecified.';
COMMENT ON COLUMN preclin.evidence_entry.build_id IS 'The store that wrote the row (preclin.evidence_line_build).';

-- preclin.evidence_entry_line
COMMENT ON COLUMN preclin.evidence_entry_line.moiety_id IS 'The entry''s entity.';
COMMENT ON COLUMN preclin.evidence_entry_line.mondo_id IS 'The entry''s program disease; empty for a disease-unspecified program.';
COMMENT ON COLUMN preclin.evidence_entry_line.phase IS 'The entry''s phase.';
COMMENT ON COLUMN preclin.evidence_entry_line.line_key IS 'The line (preclin.evidence_line).';

-- preclin.evidence_known_year
COMMENT ON COLUMN preclin.evidence_known_year.datasource IS 'Open Targets datasource of the item.';
COMMENT ON COLUMN preclin.evidence_known_year.key IS 'The item: its preclin.ot_evidence_key (ClinVar RCV accession, IMPC allele, study accession or cohort), or "target disease" for Project Score.';
COMMENT ON COLUMN preclin.evidence_known_year.year IS 'Year the item became public.';
COMMENT ON COLUMN preclin.evidence_known_year.source_release_id IS 'The dating source read (preclin.evidence_source_release).';

-- preclin.evidence_line
COMMENT ON COLUMN preclin.evidence_line.category IS 'Category key: human_genetics, tumour_genetics, diseased_tissue, animal, cell, molecule, early_human, safety_risk, precedent or adjustment.';
COMMENT ON COLUMN preclin.evidence_line.label IS 'Plain-English label as the report shows it.';
COMMENT ON COLUMN preclin.evidence_line.build_id IS 'The store that wrote the row (preclin.evidence_line_build).';

-- preclin.evidence_line_build
COMMENT ON COLUMN preclin.evidence_line_build.build_id IS 'Store id; the other evidence-line tables reference it.';
COMMENT ON COLUMN preclin.evidence_line_build.built_at IS 'When the dataset was stored.';
COMMENT ON COLUMN preclin.evidence_line_build.code_commit IS 'Git commit of the code that built it.';
COMMENT ON COLUMN preclin.evidence_line_build.snapshot IS 'Programs snapshot the dataset was built from (preclin.dev_program_build.snapshot).';
COMMENT ON COLUMN preclin.evidence_line_build.n_entries IS 'Entries stored.';

-- preclin.evidence_source_release
COMMENT ON TABLE preclin.evidence_source_release IS
    'Every source release a loader read, one row per (source, version, content hash), registered by each loader through pipeline.llm.register_release. Loaded rows reference it by source_release_id.';
COMMENT ON COLUMN preclin.evidence_source_release.source_release_id IS 'Release id.';
COMMENT ON COLUMN preclin.evidence_source_release.source_name IS 'Source, e.g. clinicaltrials_gov_api_v2, fda_drugsfda, open_targets_platform, chembl_mechanism, depmap_common_essentials.';
COMMENT ON COLUMN preclin.evidence_source_release.source_version IS 'The source''s own version or snapshot date.';
COMMENT ON COLUMN preclin.evidence_source_release.source_url IS 'Where it was downloaded from.';
COMMENT ON COLUMN preclin.evidence_source_release.content_sha256 IS 'SHA-256 of the content read (how it is computed is in metadata where it is not one file).';
COMMENT ON COLUMN preclin.evidence_source_release.retrieved_at IS 'When it was read.';
COMMENT ON COLUMN preclin.evidence_source_release.metadata IS 'Source-specific facts: counts, file names, filters, how content_sha256 was computed.';

-- preclin.fda_application
COMMENT ON COLUMN preclin.fda_application.appl_no IS 'FDA application number (six digits).';
COMMENT ON COLUMN preclin.fda_application.appl_type IS 'NDA or BLA.';
COMMENT ON COLUMN preclin.fda_application.center IS 'CDER (from Drugs@FDA) or CBER (licensed biologics read from CBER approval letters).';
COMMENT ON COLUMN preclin.fda_application.sponsor_name IS 'Sponsor as FDA records it.';
COMMENT ON COLUMN preclin.fda_application.source_release_id IS 'The release read (preclin.evidence_source_release).';

-- preclin.fda_application_moiety
COMMENT ON TABLE preclin.fda_application_moiety IS
    'Molecular entities each FDA application contains as principal active ingredients (python -m pipeline.fda link), one row per (application, entity).';
COMMENT ON COLUMN preclin.fda_application_moiety.appl_no IS 'The application (preclin.fda_application).';
COMMENT ON COLUMN preclin.fda_application_moiety.moiety_id IS 'The entity (preclin.moiety).';
COMMENT ON COLUMN preclin.fda_application_moiety.biosimilar_of IS 'Reference product''s name when the application is a biosimilar of it; null otherwise.';
COMMENT ON COLUMN preclin.fda_application_moiety.llm_decision_id IS 'The decision linking them: task fda_application_moiety; fda_application_trial_entity for an application none of whose entities appears in a trial, matched to the trial entity that is the same product; or, for entities linked by web search, task trial_entity_fda_application.';

-- preclin.fda_approved_use
COMMENT ON COLUMN preclin.fda_approved_use.approved_use_id IS 'Row id.';
COMMENT ON COLUMN preclin.fda_approved_use.letter_sha256 IS 'The action document the use was read from (preclin.fda_letter).';
COMMENT ON COLUMN preclin.fda_approved_use.ordinal IS 'Position of the use among those its document states, from 0.';
COMMENT ON COLUMN preclin.fda_approved_use.disease IS 'Disease or condition in plain standard terms, without population qualifiers.';
COMMENT ON COLUMN preclin.fda_approved_use.indication_as_written IS 'The approved indication as the document writes it.';
COMMENT ON COLUMN preclin.fda_approved_use.qualifiers IS 'Population restrictions stated: age group, line of therapy, prior treatment, biomarker, stage, combination partner, setting.';
COMMENT ON COLUMN preclin.fda_approved_use.change_type IS 'original_approval, new_indication, new_population, new_regimen, conversion_to_full (accelerated approval converted to regular), efficacy_labeling (efficacy data added without a new population) or other.';
COMMENT ON COLUMN preclin.fda_approved_use.accelerated_approval IS 'The use was granted accelerated approval.';
COMMENT ON COLUMN preclin.fda_approved_use.llm_decision_id IS 'The decision: task fda_letter_approved_uses, or fda_supplement_document_approved_uses for an efficacy supplement read from its label or review.';

-- preclin.fda_label
COMMENT ON TABLE preclin.fda_label IS
    'openFDA drug labels (structured product labels) carrying an NDA or BLA number, one row per label set (python -m pipeline.fda load).';
COMMENT ON COLUMN preclin.fda_label.set_id IS 'SPL set id, stable across versions of the label.';
COMMENT ON COLUMN preclin.fda_label.spl_id IS 'SPL id of the version loaded.';
COMMENT ON COLUMN preclin.fda_label.effective_date IS 'Effective date of the version loaded.';
COMMENT ON COLUMN preclin.fda_label.application_numbers IS 'NDA/BLA numbers the label is filed under, e.g. NDA020898.';
COMMENT ON COLUMN preclin.fda_label.brand_names IS 'Brand names (openFDA).';
COMMENT ON COLUMN preclin.fda_label.generic_names IS 'Generic names (openFDA).';
COMMENT ON COLUMN preclin.fda_label.substance_names IS 'Substance names (openFDA).';
COMMENT ON COLUMN preclin.fda_label.unii IS 'UNII codes of the label''s substances (openFDA).';
COMMENT ON COLUMN preclin.fda_label.indications_text IS 'Indications and Usage section text; null when the label has none.';
COMMENT ON COLUMN preclin.fda_label.source_release_id IS 'The openFDA export read (preclin.evidence_source_release, openfda_drug_label).';

-- preclin.fda_letter
COMMENT ON TABLE preclin.fda_letter IS
    'Text of each FDA action document read: approval letters, and the label or review PDF of an efficacy supplement with no letter, keyed by the PDF''s SHA-256 (python -m pipeline.fda load); scanned PDFs are OCRed.';
COMMENT ON COLUMN preclin.fda_letter.letter_sha256 IS 'SHA-256 of the PDF.';
COMMENT ON COLUMN preclin.fda_letter.letter_text IS 'Text extracted from the PDF.';
COMMENT ON COLUMN preclin.fda_letter.n_bytes IS 'PDF size in bytes.';

-- preclin.fda_product
COMMENT ON TABLE preclin.fda_product IS
    'Products of each NDA/BLA application, one row per (application, product number): Drugs@FDA Products.txt for CDER, and CBER products from python -m pipeline.fda load-cber.';
COMMENT ON COLUMN preclin.fda_product.appl_no IS 'The application (preclin.fda_application).';
COMMENT ON COLUMN preclin.fda_product.product_no IS 'Product number within the application.';
COMMENT ON COLUMN preclin.fda_product.drug_name IS 'Product (brand) name.';
COMMENT ON COLUMN preclin.fda_product.active_ingredient IS 'Active ingredients as FDA lists them, separated by semicolons.';
COMMENT ON COLUMN preclin.fda_product.form IS 'Dosage form and route, e.g. TABLET;ORAL; null for CBER products.';
COMMENT ON COLUMN preclin.fda_product.strength IS 'Strength as FDA lists it; null for CBER products.';

-- preclin.fda_submission
COMMENT ON TABLE preclin.fda_submission IS
    'Submissions of each NDA/BLA application (Drugs@FDA Submissions.txt; CBER approvals from python -m pipeline.fda load-cber), one row per (application, submission type, number).';
COMMENT ON COLUMN preclin.fda_submission.appl_no IS 'The application (preclin.fda_application).';
COMMENT ON COLUMN preclin.fda_submission.submission_type IS 'ORIG (original application) or SUPPL (supplement).';
COMMENT ON COLUMN preclin.fda_submission.submission_no IS 'Submission number within the application.';
COMMENT ON COLUMN preclin.fda_submission.submission_class IS 'Drugs@FDA submission class: EFFICACY, LABELING, MANUF (CMC), REMS, TYPE 1 to TYPE 10 for originals, ...';
COMMENT ON COLUMN preclin.fda_submission.status IS 'AP (approved) or TA (tentative approval).';
COMMENT ON COLUMN preclin.fda_submission.status_date IS 'Date of the status.';
COMMENT ON COLUMN preclin.fda_submission.review_priority IS 'STANDARD, PRIORITY, UNKNOWN, N/A, 901 REQUIRED or 901 ORDER as Drugs@FDA gives it; null when not given.';

-- preclin.fda_submission_letter
COMMENT ON TABLE preclin.fda_submission_letter IS
    'Action documents of each approved original or efficacy supplement from 2008 on (Drugs@FDA ApplicationDocs, CBER pages), one row per (submission, document URL) (python -m pipeline.fda fetch, load).';
COMMENT ON COLUMN preclin.fda_submission_letter.appl_no IS 'The application.';
COMMENT ON COLUMN preclin.fda_submission_letter.submission_type IS 'ORIG or SUPPL.';
COMMENT ON COLUMN preclin.fda_submission_letter.submission_no IS 'Submission number within the application.';
COMMENT ON COLUMN preclin.fda_submission_letter.url IS 'Document URL.';
COMMENT ON COLUMN preclin.fda_submission_letter.doc_date IS 'Document date as Drugs@FDA gives it.';
COMMENT ON COLUMN preclin.fda_submission_letter.letter_sha256 IS 'The fetched document (preclin.fda_letter); null when the fetch failed.';
COMMENT ON COLUMN preclin.fda_submission_letter.fetch_error IS '404 or no_letter_pdf when the document could not be read; null otherwise.';

-- preclin.gene_disease_mechanism
COMMENT ON COLUMN preclin.gene_disease_mechanism.ensembl_id IS 'The target gene (Ensembl id).';
COMMENT ON COLUMN preclin.gene_disease_mechanism.mondo_id IS 'The program disease.';
COMMENT ON COLUMN preclin.gene_disease_mechanism.risk_mechanism IS 'How risk-raising variants change the gene''s function: loss_of_function, gain_of_function, dominant_negative, mixed, unknown (association without a known direction) or none (no established germline link).';
COMMENT ON COLUMN preclin.gene_disease_mechanism.protective IS 'loss_of_function_protective, gain_of_function_protective or none_known.';
COMMENT ON COLUMN preclin.gene_disease_mechanism.confidence IS 'high (replicated genetic and functional evidence), medium or low.';
COMMENT ON COLUMN preclin.gene_disease_mechanism.llm_decision_id IS 'The gene_disease_mechanism decision.';

-- preclin.hgnc_gene
COMMENT ON TABLE preclin.hgnc_gene IS
    'HGNC approved human genes, from the complete set (python -m pipeline.hgnc load).';
COMMENT ON COLUMN preclin.hgnc_gene.hgnc_id IS 'HGNC id, e.g. HGNC:5.';
COMMENT ON COLUMN preclin.hgnc_gene.symbol IS 'Approved symbol.';
COMMENT ON COLUMN preclin.hgnc_gene.name IS 'Approved name.';
COMMENT ON COLUMN preclin.hgnc_gene.locus_group IS 'protein-coding gene, pseudogene, non-coding RNA or other.';
COMMENT ON COLUMN preclin.hgnc_gene.entrez_id IS 'NCBI Entrez gene id; null when HGNC gives none.';
COMMENT ON COLUMN preclin.hgnc_gene.ensembl_id IS 'Ensembl gene id; null when HGNC gives none.';
COMMENT ON COLUMN preclin.hgnc_gene.uniprot_ids IS 'UniProt accessions of the gene''s proteins; empty when none.';
COMMENT ON COLUMN preclin.hgnc_gene.prev_symbols IS 'Previous approved symbols.';
COMMENT ON COLUMN preclin.hgnc_gene.alias_symbols IS 'Alias symbols.';
COMMENT ON COLUMN preclin.hgnc_gene.source_release_id IS 'The HGNC download read (preclin.evidence_source_release).';

-- preclin.indication
COMMENT ON TABLE preclin.indication IS
    'Distinct condition strings from in-scope ClinicalTrials.gov trials, one row per string keyed by its lower-case alphanumerics, registered by python -m pipeline.programs register and mapped to MONDO by python -m pipeline.indications map. Several columns are from an earlier import and no longer written or read.';
COMMENT ON COLUMN preclin.indication.indication_id IS 'Row id; preclin.ctgov_study_indication references it.';
COMMENT ON COLUMN preclin.indication.normalized_name IS 'Lower-case alphanumerics of the condition: the key trial conditions are matched on.';
COMMENT ON COLUMN preclin.indication.display_name IS 'Most frequent spelling of the condition in the trials.';
COMMENT ON COLUMN preclin.indication.ct_gov_conditions IS 'Every spelling of the condition in the trials.';
COMMENT ON COLUMN preclin.indication.mondo_label IS 'Label of mondo_id; null when unmapped.';
COMMENT ON COLUMN preclin.indication.mondo_match IS 'exact (the term is the condition''s core disease) or broader (only a broader term fits); null when unmapped.';
COMMENT ON COLUMN preclin.indication.mondo_decision_id IS 'The decision that mapped it (task indication_mondo, or indication_mondo_broader for a broader match).';
COMMENT ON COLUMN preclin.indication.indication_kind IS 'disease, symptom_or_sign, procedure_or_state, healthy_volunteers or other (a trial acronym or a drug given as the condition).';
COMMENT ON COLUMN preclin.indication.created_at IS 'When the row was created.';
COMMENT ON COLUMN preclin.indication.updated_at IS 'When the row was last updated.';
COMMENT ON COLUMN preclin.indication.canonical_classified_at IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.indication.age_group IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.indication.line_of_therapy IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.indication.patient_subset IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.indication.disease_stage IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.indication.canonical_disease IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.indication.notes IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.indication.therapeutic_area IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN preclin.indication.efo_id IS 'From an earlier import; no current pipeline step writes or reads it.';

-- preclin.moiety
COMMENT ON TABLE preclin.moiety IS
    'One row per molecular entity (distinct active substance) that trial intervention names resolve to (python -m pipeline.drugs canonicalize, unii, modality); python -m pipeline.targets resolve sets target_kind.';
COMMENT ON COLUMN preclin.moiety.moiety_id IS 'Entity id.';
COMMENT ON COLUMN preclin.moiety.moiety_key IS 'Lower-case alphanumerics of name; unique.';
COMMENT ON COLUMN preclin.moiety.name IS 'Nonproprietary name (INN or USAN), else the sponsor code.';
COMMENT ON COLUMN preclin.moiety.aliases IS 'Other names of entities merged into this one because they are the same UNII substance.';
COMMENT ON COLUMN preclin.moiety.code_names IS 'Sponsor codes the trial intervention names gave for the entity, as written. They come from registry text, so a code a record misattributes to the drug can appear here.';
COMMENT ON COLUMN preclin.moiety.unii IS 'The FDA UNII substance the entity is (preclin.unii_substance); null when none was resolved.';
COMMENT ON COLUMN preclin.moiety.unii_decision_id IS 'The moiety_unii decision; null when unii is.';
COMMENT ON COLUMN preclin.moiety.modality IS 'Modality (task moiety_modality): small_molecule, monoclonal_antibody, protein, peptide, vaccine, antibody_drug_conjugate, multispecific_antibody, gene_therapy, other_cell_therapy, ...; null for entities not judged (those without a development program).';
COMMENT ON COLUMN preclin.moiety.modality_decision_id IS 'The moiety_modality decision; null when modality is.';
COMMENT ON COLUMN preclin.moiety.target_kind IS 'human_protein, pathogen, no_single_target or unknown (task moiety_targets); null for entities not judged (those without an industry development program).';
COMMENT ON COLUMN preclin.moiety.target_decision_id IS 'The moiety_targets decision; null when target_kind is.';

-- preclin.moiety_property
COMMENT ON COLUMN preclin.moiety_property.moiety_id IS 'The entity (preclin.moiety).';
COMMENT ON COLUMN preclin.moiety_property.source_release_id IS 'The pull the values came from (preclin.evidence_source_release).';

-- preclin.moiety_publication
COMMENT ON COLUMN preclin.moiety_publication.moiety_id IS 'The entity (preclin.moiety).';
COMMENT ON COLUMN preclin.moiety_publication.pmid IS 'The article (public.publications).';
COMMENT ON COLUMN preclin.moiety_publication.query_kind IS 'pharmacology (the entity''s human pharmacology) or disease (the entity in one program disease).';
COMMENT ON COLUMN preclin.moiety_publication.retrieved_at IS 'When the search returned it.';

-- preclin.moiety_target
COMMENT ON TABLE preclin.moiety_target IS
    'Molecular targets of each entity with an industry development program (python -m pipeline.targets resolve, task moiety_targets), one row per (entity, target).';
COMMENT ON COLUMN preclin.moiety_target.moiety_id IS 'The entity (preclin.moiety).';
COMMENT ON COLUMN preclin.moiety_target.target_id IS 'The human protein target (public.targets).';
COMMENT ON COLUMN preclin.moiety_target.action IS 'What the drug does to the target: inhibitor, antagonist, agonist, partial_agonist, inverse_agonist, activator, positive_modulator, negative_modulator, blocker, opener, degrader, binder_neutralizer, depleter, replacement, gene_expression_reduction, gene_expression_increase or other.';
COMMENT ON COLUMN preclin.moiety_target.is_primary IS 'The target the drug is meant to work through; others are secondary.';
COMMENT ON COLUMN preclin.moiety_target.llm_decision_id IS 'The moiety_targets decision.';

-- preclin.mondo_bio_area
COMMENT ON TABLE preclin.mondo_bio_area IS
    'Disease area of every program disease, in the areas of BIO''s 2021 Clinical Development Success Rates report (python -m pipeline.indications areas, task mondo_bio_area).';
COMMENT ON COLUMN preclin.mondo_bio_area.mondo_id IS 'The program disease.';
COMMENT ON COLUMN preclin.mondo_bio_area.bio_area IS 'allergy, autoimmune, cardiovascular, endocrine, gastroenterology, hematology, infectious_disease, metabolic, neurology, oncology, ophthalmology, psychiatry, respiratory, urology or other.';
COMMENT ON COLUMN preclin.mondo_bio_area.llm_decision_id IS 'The mondo_bio_area decision.';

-- preclin.mouse_model_relation
COMMENT ON TABLE preclin.mouse_model_relation IS
    'Whether each mouse model of a primary target that matched a program disease mimics or opposes the disease (python -m pipeline.targets mouse, task mouse_model_relation), one row per (gene, disease, model).';
COMMENT ON COLUMN preclin.mouse_model_relation.ensembl_id IS 'The target gene (Ensembl id).';
COMMENT ON COLUMN preclin.mouse_model_relation.mondo_id IS 'The program disease.';
COMMENT ON COLUMN preclin.mouse_model_relation.model_id IS 'The mouse model (MGI id).';
COMMENT ON COLUMN preclin.mouse_model_relation.perturbation IS 'reduced_function (knockout, knockdown, hypomorph, loss-of-function mutant), increased_function (overexpression, activating or toxic mutant) or other.';
COMMENT ON COLUMN preclin.mouse_model_relation.relation IS 'mimics_disease, opposes_disease or unrelated, judged against the disease''s defining feature.';
COMMENT ON COLUMN preclin.mouse_model_relation.llm_decision_id IS 'The mouse_model_relation decision.';

-- preclin.ontology_ancestor
COMMENT ON TABLE preclin.ontology_ancestor IS
    'Transitive is_a closure of MONDO and Mammalian Phenotype terms (python -m pipeline.ontology load), one row per (term, ancestor), the term itself excluded.';
COMMENT ON COLUMN preclin.ontology_ancestor.ontology IS 'MONDO or MP.';
COMMENT ON COLUMN preclin.ontology_ancestor.term_id IS 'The term.';
COMMENT ON COLUMN preclin.ontology_ancestor.ancestor_id IS 'One of its ancestors.';
COMMENT ON COLUMN preclin.ontology_ancestor.distance IS 'Shortest is_a path from the term to the ancestor (1 = parent).';

-- preclin.ontology_is_a
COMMENT ON TABLE preclin.ontology_is_a IS
    'Direct is_a edges of MONDO and Mammalian Phenotype terms (python -m pipeline.ontology load).';
COMMENT ON COLUMN preclin.ontology_is_a.ontology IS 'MONDO or MP.';
COMMENT ON COLUMN preclin.ontology_is_a.child_id IS 'The child term.';
COMMENT ON COLUMN preclin.ontology_is_a.parent_id IS 'Its parent term.';

-- preclin.ontology_term
COMMENT ON TABLE preclin.ontology_term IS
    'MONDO and Mammalian Phenotype terms from the pinned OBO releases (python -m pipeline.ontology load).';
COMMENT ON COLUMN preclin.ontology_term.term_id IS 'Term id (CURIE, e.g. MONDO:0005148).';
COMMENT ON COLUMN preclin.ontology_term.ontology IS 'MONDO or MP.';
COMMENT ON COLUMN preclin.ontology_term.label IS 'Term label.';
COMMENT ON COLUMN preclin.ontology_term.definition IS 'Term definition; null when the release gives none.';
COMMENT ON COLUMN preclin.ontology_term.synonyms IS 'Exact synonyms.';
COMMENT ON COLUMN preclin.ontology_term.is_obsolete IS 'The term is obsolete in the release.';
COMMENT ON COLUMN preclin.ontology_term.replaced_by IS 'Term an obsolete term is replaced by; null otherwise.';
COMMENT ON COLUMN preclin.ontology_term.source_release_id IS 'The OBO release read (preclin.evidence_source_release).';

-- preclin.ontology_xref
COMMENT ON TABLE preclin.ontology_xref IS
    'Cross-references of MONDO and Mammalian Phenotype terms to other vocabularies (python -m pipeline.ontology load).';
COMMENT ON COLUMN preclin.ontology_xref.ontology IS 'MONDO or MP.';
COMMENT ON COLUMN preclin.ontology_xref.term_id IS 'The term.';
COMMENT ON COLUMN preclin.ontology_xref.xref_id IS 'The cross-referenced id (CURIE, e.g. DOID:4, ICD9:799.9).';
COMMENT ON COLUMN preclin.ontology_xref.equivalent IS 'MONDO declares the two equivalent (source MONDO:equivalentTo); false for other cross-references.';

-- preclin.ot_association
COMMENT ON TABLE preclin.ot_association IS
    'Open Targets direct target-disease association scores by datasource, for the targets of entities with an industry development program (python -m pipeline.opentargets load), with yearly score series rebuilt from the dated evidence (python -m pipeline.opentargets evidence, dates).';
COMMENT ON COLUMN preclin.ot_association.target_ensembl IS 'The target gene (Ensembl id).';
COMMENT ON COLUMN preclin.ot_association.disease_id IS 'Open Targets disease id (preclin.ot_disease).';
COMMENT ON COLUMN preclin.ot_association.datasource IS 'Open Targets datasource: impc, gwas_credible_sets, eva, expression_atlas, cancer_gene_census, ...';
COMMENT ON COLUMN preclin.ot_association.datatype IS 'Open Targets datatype of the datasource: genetic, somatic, animal_model, rna_expression, affected_pathway or functional_screen.';
COMMENT ON COLUMN preclin.ot_association.score IS 'Association score in the release (0 to 1).';
COMMENT ON COLUMN preclin.ot_association.evidence_count IS 'Evidence items behind the association in the release.';
COMMENT ON COLUMN preclin.ot_association.first_year IS 'First year of series_years, when dated evidence first gave a score; null when the association has no dated evidence.';
COMMENT ON COLUMN preclin.ot_association.series_scores IS 'Association score at each year of series_years.';
COMMENT ON COLUMN preclin.ot_association.source_release_id IS 'The Open Targets release read (preclin.evidence_source_release).';

-- preclin.ot_disease
COMMENT ON TABLE preclin.ot_disease IS
    'Open Targets diseases with the MONDO terms each maps to (python -m pipeline.opentargets load).';
COMMENT ON COLUMN preclin.ot_disease.disease_id IS 'Open Targets disease id (CURIE).';
COMMENT ON COLUMN preclin.ot_disease.name IS 'Disease name.';
COMMENT ON COLUMN preclin.ot_disease.mondo_ids IS 'MONDO terms the disease is, or that MONDO declares equivalent to it; empty when none.';
COMMENT ON COLUMN preclin.ot_disease.therapeutic_areas IS 'Open Targets therapeutic area ids.';
COMMENT ON COLUMN preclin.ot_disease.source_release_id IS 'The Open Targets release read (preclin.evidence_source_release).';

-- preclin.ot_evidence
COMMENT ON TABLE preclin.ot_evidence IS
    'Open Targets evidence items behind the loaded associations, one row per item, each dated by when it became known (python -m pipeline.opentargets evidence, dates).';
COMMENT ON COLUMN preclin.ot_evidence.evidence_id IS 'Open Targets evidence id.';
COMMENT ON COLUMN preclin.ot_evidence.target_ensembl IS 'The target gene (Ensembl id).';
COMMENT ON COLUMN preclin.ot_evidence.disease_id IS 'Open Targets disease id (preclin.ot_disease).';
COMMENT ON COLUMN preclin.ot_evidence.datasource IS 'Open Targets datasource of the item.';
COMMENT ON COLUMN preclin.ot_evidence.score IS 'Open Targets evidence score (0 to 1).';
COMMENT ON COLUMN preclin.ot_evidence.resource_score IS 'The datasource''s own score (Open Targets resourceScore): locus-to-gene for gwas_credible_sets, PhenoDigm for impc, ...; null where the source gives none.';
COMMENT ON COLUMN preclin.ot_evidence.direction_on_target IS 'LoF or GoF: the variant''s effect on the gene; null when not given.';
COMMENT ON COLUMN preclin.ot_evidence.direction_on_trait IS 'risk or protect: the variant''s effect on the trait; null when not given.';
COMMENT ON COLUMN preclin.ot_evidence.confidence IS 'The source''s confidence: ClinVar review status for eva, ClinGen classification, PanelApp rating, Gene2Phenotype confidence, ...; null when not given.';
COMMENT ON COLUMN preclin.ot_evidence.allelic_requirements IS 'Inheritance (e.g. Autosomal dominant inheritance); null when not given.';
COMMENT ON COLUMN preclin.ot_evidence.variant_consequence IS 'Sequence Ontology id of the variant''s functional consequence; null when not given.';
COMMENT ON COLUMN preclin.ot_evidence.detail IS 'Datasource-specific fields as JSON: study id, log2 fold change, clinical significances, matched model phenotypes, number of supporting papers (n_literature).';
COMMENT ON COLUMN preclin.ot_evidence.source_release_id IS 'The Open Targets release read (preclin.evidence_source_release).';

-- preclin.ot_mouse_phenotype
COMMENT ON TABLE preclin.ot_mouse_phenotype IS
    'Mouse mutant phenotypes of each target (Open Targets mouse phenotypes, python -m pipeline.opentargets evidence), one row per (human target, MP phenotype); the models of all mouse orthologs are pooled.';
COMMENT ON COLUMN preclin.ot_mouse_phenotype.target_ensembl IS 'The target gene (Ensembl id).';
COMMENT ON COLUMN preclin.ot_mouse_phenotype.phenotype_id IS 'Mammalian Phenotype term.';
COMMENT ON COLUMN preclin.ot_mouse_phenotype.phenotype_label IS 'Its label.';
COMMENT ON COLUMN preclin.ot_mouse_phenotype.class_ids IS 'Top-level MP classes the phenotype falls under.';
COMMENT ON COLUMN preclin.ot_mouse_phenotype.models IS 'Allelic compositions of the mouse models showing it.';
COMMENT ON COLUMN preclin.ot_mouse_phenotype.source_release_id IS 'The Open Targets release read (preclin.evidence_source_release).';

-- preclin.program_indication
COMMENT ON TABLE preclin.program_indication IS
    'Grouping of each entity''s diseases into development indications (python -m pipeline.programs indications, task entity_indication_groups), one row per (entity, disease) for entities with related or co-listed diseases; ungrouped diseases are their own indication.';
COMMENT ON COLUMN preclin.program_indication.moiety_id IS 'The entity (preclin.moiety).';
COMMENT ON COLUMN preclin.program_indication.mondo_id IS 'A disease the entity was tested in.';
COMMENT ON COLUMN preclin.program_indication.indication_mondo IS 'The disease representing its indication group; it becomes preclin.dev_program.mondo_id.';
COMMENT ON COLUMN preclin.program_indication.llm_decision_id IS 'The entity_indication_groups decision.';

-- preclin.pubmed_search
COMMENT ON COLUMN preclin.pubmed_search.moiety_id IS 'The entity searched.';
COMMENT ON COLUMN preclin.pubmed_search.mondo_id IS 'The program disease searched; empty for a pharmacology search.';
COMMENT ON COLUMN preclin.pubmed_search.query_kind IS 'pharmacology or disease.';
COMMENT ON COLUMN preclin.pubmed_search.query IS 'The exact PubMed query.';
COMMENT ON COLUMN preclin.pubmed_search.n_hits IS 'Number of PubMed results.';
COMMENT ON COLUMN preclin.pubmed_search.searched_at IS 'When the search ran.';

-- preclin.schema_migration
COMMENT ON COLUMN preclin.schema_migration.migration_number IS 'Number of the migration file.';
COMMENT ON COLUMN preclin.schema_migration.migration_name IS 'Its name, the part of the file name after the number.';
COMMENT ON COLUMN preclin.schema_migration.filename IS 'The migration file.';
COMMENT ON COLUMN preclin.schema_migration.migration_kind IS 'sql or python.';
COMMENT ON COLUMN preclin.schema_migration.file_sha256 IS 'SHA-256 of the file as applied; a changed file is a drift error.';
COMMENT ON COLUMN preclin.schema_migration.git_commit IS 'Git commit the migration was applied from.';
COMMENT ON COLUMN preclin.schema_migration.applied_by IS 'Database role that applied it.';
COMMENT ON COLUMN preclin.schema_migration.applied_at IS 'When it was applied.';
COMMENT ON COLUMN preclin.schema_migration.details IS 'Runner details as JSON (runner, bootstrap, reason for a baseline row).';

-- preclin.stop
COMMENT ON COLUMN preclin.stop.moiety_id IS 'The stopped program''s entity (preclin.moiety).';
COMMENT ON COLUMN preclin.stop.mondo_id IS 'The stopped program''s disease; empty for a disease-unspecified program.';
COMMENT ON COLUMN preclin.stop.phase IS 'Phase the program stopped in: 1, 2 or 3.';
COMMENT ON COLUMN preclin.stop.method_id IS 'The method that produced the row (preclin.analysis_method).';

-- preclin.stop_continuation
COMMENT ON COLUMN preclin.stop_continuation.moiety_id IS 'The stopped program''s entity (preclin.moiety).';
COMMENT ON COLUMN preclin.stop_continuation.mondo_id IS 'The stopped program''s disease; empty for a disease-unspecified program.';
COMMENT ON COLUMN preclin.stop_continuation.phase IS 'Phase the program stopped in: 1, 2 or 3.';
COMMENT ON COLUMN preclin.stop_continuation.method_id IS 'The method that produced the row (preclin.analysis_method).';
COMMENT ON COLUMN preclin.stop_continuation.explanation IS 'What the sources show development went on to, in plain words.';
COMMENT ON COLUMN preclin.stop_continuation.sources IS 'URLs and NCT ids the decision cites; each was retrieved during the decision.';

-- preclin.stop_signal
COMMENT ON COLUMN preclin.stop_signal.moiety_id IS 'The stopped program''s entity (preclin.moiety).';
COMMENT ON COLUMN preclin.stop_signal.mondo_id IS 'The stopped program''s disease; empty for a disease-unspecified program.';
COMMENT ON COLUMN preclin.stop_signal.phase IS 'Phase the program stopped in: 1, 2 or 3.';
COMMENT ON COLUMN preclin.stop_signal.method_id IS 'The method that produced the row (preclin.analysis_method).';

-- preclin.trial_biomarker_selection
COMMENT ON COLUMN preclin.trial_biomarker_selection.nct_id IS 'The trial (preclin.ctgov_study).';
COMMENT ON COLUMN preclin.trial_biomarker_selection.llm_decision_id IS 'The trial_biomarker_selection decision.';

-- preclin.trial_endpoint
COMMENT ON TABLE preclin.trial_endpoint IS
    'Kind of each Phase 2/3 trial''s governing primary endpoint (python -m pipeline.outcomes endpoints, task trial_endpoint).';
COMMENT ON COLUMN preclin.trial_endpoint.nct_id IS 'The trial (preclin.ctgov_study).';
COMMENT ON COLUMN preclin.trial_endpoint.governing_index IS 'Which listed primary outcome governs, from 1: the only one, the first in a stated hierarchy, the one the trial is powered on, else the first efficacy measure.';
COMMENT ON COLUMN preclin.trial_endpoint.purpose IS 'efficacy, safety_tolerability, pk_pd_dose or other.';
COMMENT ON COLUMN preclin.trial_endpoint.endpoint_class IS 'For efficacy: B1_target_engagement, B2_exploratory_biomarker, B3_regulatory_surrogate, B4_objective_physiological, B5_clinician_scale, B6_patient_reported, B7_disease_events, B8_hard_outcome, B9_infection_cure, O1_tumor_response, O2_progression_free or O3_overall_survival; not_efficacy otherwise.';
COMMENT ON COLUMN preclin.trial_endpoint.measurement_type IS 'lab, imaging, clinician_rated, patient_reported, performance, event or other.';
COMMENT ON COLUMN preclin.trial_endpoint.scale IS 'continuous, responder, time_to_event, count_rate or other.';
COMMENT ON COLUMN preclin.trial_endpoint.llm_decision_id IS 'The trial_endpoint decision.';

-- preclin.trial_outcome
COMMENT ON TABLE preclin.trial_outcome IS
    'What happened in each trial: execution, stated stop reason, primary-endpoint result and safety signal (python -m pipeline.outcomes classify: task trial_outcome from the registry record, or trial_outcome_from_publication from a results paper).';
COMMENT ON COLUMN preclin.trial_outcome.nct_id IS 'The trial (preclin.ctgov_study).';
COMMENT ON COLUMN preclin.trial_outcome.execution IS 'completed, stopped_early (terminated or suspended after enrolling) or withdrawn_before_enrollment.';
COMMENT ON COLUMN preclin.trial_outcome.stop_reason IS 'The sponsor''s stated reason, by meaning: efficacy_futility, safety_tolerability, pk_pd_or_formulation, business_portfolio, sponsor_decision_unspecified, competitive_landscape, enrollment_feasibility, operational_or_site, regulatory, manufacturing_supply, covid19, replaced_by_new_protocol, objectives_met_or_early_success, other or not_stated; not_applicable when completed.';
COMMENT ON COLUMN preclin.trial_outcome.secondary_reasons IS 'Other stated reasons, same vocabulary; empty when none.';
COMMENT ON COLUMN preclin.trial_outcome.primary_endpoint IS 'met, not_met, mixed, not_assessable (results posted but the primary analysis is missing or uninterpretable) or no_results.';
COMMENT ON COLUMN preclin.trial_outcome.safety_signal IS 'notable (a safety problem shown in the record), none_evident or unknown.';
COMMENT ON COLUMN preclin.trial_outcome.efficacy_failure IS 'The record shows the drug failed to show efficacy (an efficacy_futility stop, or a not_met primary in a trial designed to test efficacy).';
COMMENT ON COLUMN preclin.trial_outcome.evidence IS 'What the answer rests on, quoted or summarised from the record.';
COMMENT ON COLUMN preclin.trial_outcome.llm_decision_id IS 'The decision (task trial_outcome or trial_outcome_from_publication).';

-- preclin.trial_phase_role
COMMENT ON COLUMN preclin.trial_phase_role.nct_id IS 'The trial (preclin.ctgov_study).';
COMMENT ON COLUMN preclin.trial_phase_role.extension IS 'The trial enrolls only people from earlier trials of the drug (open-label extension, rollover, long-term continuation).';
COMMENT ON COLUMN preclin.trial_phase_role.main_period_moieties IS 'Entities (preclin.moiety) the trial''s main period tests.';
COMMENT ON COLUMN preclin.trial_phase_role.llm_decision_id IS 'The trial_phase_role decision.';

-- preclin.trial_publication
COMMENT ON TABLE preclin.trial_publication IS
    'Results papers linked to completed industry Phase 2/3 trials that posted no results (python -m pipeline.outcomes publications), one row per (trial, paper).';
COMMENT ON COLUMN preclin.trial_publication.nct_id IS 'The trial (preclin.ctgov_study).';
COMMENT ON COLUMN preclin.trial_publication.pmid IS 'The paper (public.publications).';
COMMENT ON COLUMN preclin.trial_publication.link_source IS 'ctgov_reference (the record lists it as a RESULT or DERIVED reference) or pubmed_secondary_id (PubMed indexes the NCT id as a secondary identifier).';

-- preclin.trial_purpose
COMMENT ON TABLE preclin.trial_purpose IS
    'What each in-scope industry trial with an investigational entity contributes to development (python -m pipeline.programs purposes, task trial_purpose); pipeline.programs build reads it to decide which programs a trial counts for.';
COMMENT ON COLUMN preclin.trial_purpose.nct_id IS 'The trial (preclin.ctgov_study).';
COMMENT ON COLUMN preclin.trial_purpose.purpose IS 'What the trial contributes: indication_development, multi_indication (basket, umbrella or several indications), early_development (first-in-human or early clinical pharmacology), product_support (bioequivalence, formulation, interaction, labelling work on a marketed drug) or other.';
COMMENT ON COLUMN preclin.trial_purpose.development_conditions IS 'For indication_development and multi_indication, the listed conditions the trial develops the drug for, as listed; empty otherwise.';
COMMENT ON COLUMN preclin.trial_purpose.llm_decision_id IS 'The trial_purpose decision.';

-- preclin.unii_name
COMMENT ON TABLE preclin.unii_name IS
    'Every registered name of each FDA UNII substance (GSRS public UNII list, python -m pipeline.unii load).';
COMMENT ON COLUMN preclin.unii_name.unii IS 'The substance (preclin.unii_substance).';
COMMENT ON COLUMN preclin.unii_name.name IS 'The name as registered, with any bracketed source tag.';
COMMENT ON COLUMN preclin.unii_name.name_type IS 'GSRS name type: of (official), cn (common), cd (code), sys (systematic), bn (brand) or mn (rare).';
COMMENT ON COLUMN preclin.unii_name.name_key IS 'Lower-case alphanumerics of the name without bracketed tags, as entity names are keyed.';

-- preclin.unii_parent
COMMENT ON COLUMN preclin.unii_parent.unii IS 'The salt, hydrate or solvate.';
COMMENT ON COLUMN preclin.unii_parent.parent_unii IS 'The parent substance it contains.';

-- preclin.unii_substance
COMMENT ON TABLE preclin.unii_substance IS
    'FDA UNII substances from the GSRS public records pinned to a release (python -m pipeline.unii load).';
COMMENT ON COLUMN preclin.unii_substance.unii IS 'UNII code.';
COMMENT ON COLUMN preclin.unii_substance.display_name IS 'GSRS display name.';
COMMENT ON COLUMN preclin.unii_substance.substance_type IS 'chemical, protein, nucleicAcid, polymer, mixture, structurallyDiverse or specifiedSubstanceG1.';
COMMENT ON COLUMN preclin.unii_substance.ingredient_type IS 'INGREDIENT SUBSTANCE, IONIC MOIETY, SPECIFIED SUBSTANCE, UNSPECIFIED INGREDIENT or MOLECULAR FRAGMENT.';
COMMENT ON COLUMN preclin.unii_substance.inn_id IS 'WHO INN id; null when none.';
COMMENT ON COLUMN preclin.unii_substance.usan_id IS 'USAN id; null when none.';
COMMENT ON COLUMN preclin.unii_substance.rxcui IS 'RxNorm concept id; null when none.';
COMMENT ON COLUMN preclin.unii_substance.pubchem_cid IS 'PubChem compound id; null when none. preclin.moiety_property reads properties by it.';
COMMENT ON COLUMN preclin.unii_substance.inchikey IS 'Standard InChIKey of the structure; null for substances without a defined structure.';
COMMENT ON COLUMN preclin.unii_substance.source_release_id IS 'The GSRS release read (preclin.evidence_source_release).';

-- public.gene_constraint
COMMENT ON TABLE public.gene_constraint IS
    'gnomAD v4.1 gene constraint per target, from an earlier import with no loader in this repository; Sections 2 and 3 read loeuf.';
COMMENT ON COLUMN public.gene_constraint.target_id IS 'The target (public.targets).';
COMMENT ON COLUMN public.gene_constraint.source IS 'Release: gnomad_v4.1.';
COMMENT ON COLUMN public.gene_constraint.loeuf IS 'Loss-of-function observed/expected upper bound (LOEUF); lower is more constrained. Null when gnomAD gives none.';
COMMENT ON COLUMN public.gene_constraint.oe_lof_upper IS 'Same value as loeuf, as gnomAD names it.';
COMMENT ON COLUMN public.gene_constraint.pli IS 'Probability of loss-of-function intolerance (pLI).';
COMMENT ON COLUMN public.gene_constraint.mis_z IS 'Missense constraint z-score.';
COMMENT ON COLUMN public.gene_constraint.syn_z IS 'Synonymous z-score.';
COMMENT ON COLUMN public.gene_constraint.oe_mis_upper IS 'Missense observed/expected upper bound.';
COMMENT ON COLUMN public.gene_constraint.constraint_flags IS 'gnomAD constraint flags as a JSON list in text (e.g. ["no_exp_lof"]); [] when none.';

-- public.publications
COMMENT ON TABLE public.publications IS
    'PubMed articles the pipeline fetched (python -m pipeline.outcomes publications, pipeline.attribution literature, pipeline.literature), one row per PMID.';
COMMENT ON COLUMN public.publications.id IS 'Row id.';
COMMENT ON COLUMN public.publications.pmid IS 'PubMed id.';
COMMENT ON COLUMN public.publications.title IS 'Article title.';
COMMENT ON COLUMN public.publications.authors IS 'First author and "et al." when there are more.';
COMMENT ON COLUMN public.publications.journal IS 'Journal ISO abbreviation, else its title.';
COMMENT ON COLUMN public.publications.year IS 'Publication year (PubDate); null when PubMed gives none.';
COMMENT ON COLUMN public.publications.doi IS 'DOI; null when PubMed gives none.';
COMMENT ON COLUMN public.publications.abstract IS 'Abstract text; null when the article has none.';
COMMENT ON COLUMN public.publications.fetched_at IS 'When the article was fetched.';

-- public.targets
COMMENT ON TABLE public.targets IS
    'Gene and target catalogue from an earlier import, with no loader in this repository. pipeline.targets assigns entity targets among its human proteins (ip_type Protein), and the evidence joins on ensembl_id.';
COMMENT ON COLUMN public.targets.id IS 'Target id; preclin.moiety_target references it.';
COMMENT ON COLUMN public.targets.symbol IS 'Gene symbol (or the catalogue''s symbol for a pathogen or RNA target).';
COMMENT ON COLUMN public.targets.name IS 'Name; null when the catalogue gives none.';
COMMENT ON COLUMN public.targets.ip_type IS 'Protein, Genomic, RNA or Pathogen.';
COMMENT ON COLUMN public.targets.ensembl_id IS 'Ensembl gene id of a human gene; null for pathogen and some RNA targets.';
COMMENT ON COLUMN public.targets.target_class IS 'Class: Enzyme, Kinase, GPCR, Ion Channel, Transporter, Transcription Factor, RNA, Other Protein, ...; the evidence analyses group targets by it.';
COMMENT ON COLUMN public.targets.uniprot_id IS 'Empty in this import.';
COMMENT ON COLUMN public.targets.family IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN public.targets.tdl IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN public.targets.location IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN public.targets.description IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN public.targets.tractability_sm IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN public.targets.tractability_ab IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN public.targets.tractability_protac IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN public.targets.rna_type IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN public.targets.pathogen_type IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN public.targets.pathogen_species IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN public.targets.intervention_type IS 'From an earlier import; no current pipeline step writes or reads it.';
COMMENT ON COLUMN public.targets.created_at IS 'When the row was created.';
COMMENT ON COLUMN public.targets.updated_at IS 'When the row was last updated.';

-- pv_evidence.llm_decision
COMMENT ON TABLE pv_evidence.llm_decision IS
    'Every LLM decision the pipeline made (pipeline.llm.run), one row per (run, subject): the input, raw and parsed output, validation and usage. Label tables reference it by llm_decision_id.';
COMMENT ON COLUMN pv_evidence.llm_decision.llm_decision_id IS 'Decision id.';
COMMENT ON COLUMN pv_evidence.llm_decision.decision_run_id IS 'The run (pv_evidence.llm_decision_run).';
COMMENT ON COLUMN pv_evidence.llm_decision.task IS 'The task, e.g. trial_outcome, indication_mondo, drug_moiety.';
COMMENT ON COLUMN pv_evidence.llm_decision.subject_type IS 'What the decision is about: trial, moiety, indication, drug, program_phase, fda_application, ...';
COMMENT ON COLUMN pv_evidence.llm_decision.subject_key IS 'The subject''s key (an NCT id, entity id, ...).';
COMMENT ON COLUMN pv_evidence.llm_decision.input_payload IS 'The input sent, as JSON.';
COMMENT ON COLUMN pv_evidence.llm_decision.input_sha256 IS 'SHA-256 of the canonical input; a later run reuses a validated decision with the same hash.';
COMMENT ON COLUMN pv_evidence.llm_decision.raw_response IS 'The model''s raw text response.';
COMMENT ON COLUMN pv_evidence.llm_decision.parsed_output IS 'The response parsed as JSON; an {error} object when it could not be parsed or validated.';
COMMENT ON COLUMN pv_evidence.llm_decision.output_sha256 IS 'SHA-256 of raw_response.';
COMMENT ON COLUMN pv_evidence.llm_decision.canonical_decision IS 'The decision as stored for use (currently equal to parsed_output).';
COMMENT ON COLUMN pv_evidence.llm_decision.decision_sha256 IS 'SHA-256 of canonical_decision.';
COMMENT ON COLUMN pv_evidence.llm_decision.prior_decision_id IS 'The earlier decision this row reuses; null for a new decision.';
COMMENT ON COLUMN pv_evidence.llm_decision.change_status IS 'unchanged (copied from prior_decision_id) or not_compared (a new decision).';
COMMENT ON COLUMN pv_evidence.llm_decision.provider_request_id IS 'The provider''s request id.';
COMMENT ON COLUMN pv_evidence.llm_decision.model_parameters IS 'Model, effort and max_tokens the decision was made with.';
COMMENT ON COLUMN pv_evidence.llm_decision.usage IS 'Token usage as the provider reported it.';
COMMENT ON COLUMN pv_evidence.llm_decision.validation_status IS 'validated or invalid; only validated decisions are used.';
COMMENT ON COLUMN pv_evidence.llm_decision.validation_detail IS 'Validation errors as a JSON array; empty when validated.';
COMMENT ON COLUMN pv_evidence.llm_decision.created_at IS 'When the row was written.';

-- pv_evidence.llm_decision_run
COMMENT ON TABLE pv_evidence.llm_decision_run IS
    'Each run of an LLM task: model, prompt and schema versions, code commit, parameters (the system prompt and output schema with their hashes) and status.';
COMMENT ON COLUMN pv_evidence.llm_decision_run.decision_run_id IS 'Run id.';
COMMENT ON COLUMN pv_evidence.llm_decision_run.task IS 'The task.';
COMMENT ON COLUMN pv_evidence.llm_decision_run.provider IS 'anthropic; openai, openrouter or agent for runs of earlier tooling.';
COMMENT ON COLUMN pv_evidence.llm_decision_run.model IS 'Model id.';
COMMENT ON COLUMN pv_evidence.llm_decision_run.model_snapshot IS 'Provider''s model snapshot when it gives one; null otherwise.';
COMMENT ON COLUMN pv_evidence.llm_decision_run.prompt_version IS 'Prompt version; a decision is reused only under the same prompt and schema versions.';
COMMENT ON COLUMN pv_evidence.llm_decision_run.output_schema_version IS 'Output schema version.';
COMMENT ON COLUMN pv_evidence.llm_decision_run.code_commit IS 'Git commit of the code that ran it.';
COMMENT ON COLUMN pv_evidence.llm_decision_run.parameters IS 'System prompt, output schema and their SHA-256s, effort, max_tokens, item count, reuse mode; errors for failed runs.';
COMMENT ON COLUMN pv_evidence.llm_decision_run.status IS 'running, completed or failed.';
COMMENT ON COLUMN pv_evidence.llm_decision_run.started_at IS 'When the run started.';
COMMENT ON COLUMN pv_evidence.llm_decision_run.completed_at IS 'When it finished; null while running or when it stopped without finishing.';
COMMENT ON COLUMN pv_evidence.llm_decision_run.compare_to_run_id IS 'An earlier run this one was compared with, from earlier tooling; null otherwise.';
COMMENT ON COLUMN pv_evidence.llm_decision_run.created_at IS 'When the row was written.';

COMMIT;
