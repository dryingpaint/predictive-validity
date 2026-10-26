-- Schema of the database as of migration 92 (db/migrate.py SCHEMA_THROUGH): every table, function
-- and comment in preclin, public and pv_evidence. Earlier migrations are squashed into this file;
-- their rows stay in preclin.schema_migration. `python db/migrate.py init` creates it in an empty
-- database. Generated with
--   pg_dump --schema-only --no-owner --no-privileges -n preclin -n public -n pv_evidence
-- after migration 92, without pg_dump's psql-only \restrict lines.

--
-- PostgreSQL database dump
--


-- Dumped from database version 17.11 (11592b3)
-- Dumped by pg_dump version 18.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: preclin; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA preclin;


--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS public;


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: pv_evidence; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA pv_evidence;


--
-- Name: harmonic_series(integer[], double precision[]); Type: FUNCTION; Schema: preclin; Owner: -
--

CREATE FUNCTION preclin.harmonic_series(ys integer[], ss double precision[], OUT years smallint[], OUT scores real[]) RETURNS record
    LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE
    AS $$
DECLARE
    norm CONSTANT double precision := 1.6439345666815615;
    known double precision[] := '{}';
    total double precision;
    n integer := cardinality(ys);
BEGIN
    years := '{}';
    scores := '{}';
    FOR i IN 1 .. n LOOP
        known := known || ss[i];
        IF i = n OR ys[i + 1] <> ys[i] THEN
            known := ARRAY(SELECT unnest(known) ORDER BY 1 DESC);
            total := 0;
            FOR j IN 1 .. least(cardinality(known), 1000) LOOP
                total := total + known[j] / (j * j);
            END LOOP;
            years := years || ys[i]::smallint;
            scores := scores || (total / norm)::real;
        END IF;
    END LOOP;
END
$$;


--
-- Name: ot_evidence_key(text, jsonb); Type: FUNCTION; Schema: preclin; Owner: -
--

CREATE FUNCTION preclin.ot_evidence_key(datasource text, detail jsonb) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    AS $$
    SELECT CASE
        WHEN datasource IN ('eva', 'eva_somatic', 'expression_atlas', 'crispr_screen') THEN detail->>'studyId'
        WHEN datasource = 'intogen' THEN detail->>'cohortShortName'
        WHEN datasource = 'impc' THEN (  -- an allele may carry a note after it ("hom early")
            SELECT split_part(trim(a), ' ', 1)
            FROM unnest(string_to_array(detail->>'biologicalModelAllelicComposition', '/')) AS a
            WHERE a ~ '[(](EUCOMM|KOMP|IMPC|EUCOMMTools|NCOM)[)]' LIMIT 1)
    END
$$;


--
-- Name: reject_schema_migration_mutation(); Type: FUNCTION; Schema: preclin; Owner: -
--

CREATE FUNCTION preclin.reject_schema_migration_mutation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  RAISE EXCEPTION
    'preclin.schema_migration is append-only; migration % cannot be modified by %',
    OLD.migration_number, lower(TG_OP);
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: chembl_mechanism; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.chembl_mechanism (
    mec_id integer NOT NULL,
    molecule_chembl_id text NOT NULL,
    parent_chembl_id text NOT NULL,
    target_chembl_id text,
    target_name text,
    action_type text,
    mechanism_of_action text,
    symbols text[] NOT NULL,
    source_release_id bigint NOT NULL
);


--
-- Name: chembl_molecule; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.chembl_molecule (
    molecule_chembl_id text NOT NULL,
    parent_chembl_id text NOT NULL,
    source_release_id bigint NOT NULL
);


--
-- Name: clinvar_accession_calibration; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.clinvar_accession_calibration (
    rcv_number bigint NOT NULL,
    created date NOT NULL,
    source_release_id bigint NOT NULL
);


--
-- Name: TABLE clinvar_accession_calibration; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON TABLE preclin.clinvar_accession_calibration IS 'ClinVar RCV records sampled across the accession range with the date of their first submission; accessions are issued in order of creation, so these date every record (pipeline.evidence_dates clinvar)';


--
-- Name: ctgov_result_summary; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.ctgov_result_summary (
    nct_id text NOT NULL,
    summary text NOT NULL,
    n_analyses integer NOT NULL,
    analyses jsonb NOT NULL
);


--
-- Name: ctgov_study; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.ctgov_study (
    nct_id text NOT NULL,
    brief_title text,
    official_title text,
    overall_status text,
    why_stopped text,
    phases text[] NOT NULL,
    start_date date,
    start_date_type text,
    primary_completion_date date,
    primary_completion_date_type text,
    completion_date date,
    completion_date_type text,
    first_posted date,
    last_update_posted date,
    results_first_posted date,
    has_results boolean NOT NULL,
    lead_sponsor text,
    lead_sponsor_class text,
    collaborators jsonb NOT NULL,
    enrollment integer,
    allocation text,
    intervention_model text,
    masking text,
    primary_purpose text,
    healthy_volunteers boolean,
    conditions text[] NOT NULL,
    keywords text[] NOT NULL,
    interventions jsonb NOT NULL,
    arm_groups jsonb NOT NULL,
    references_ jsonb NOT NULL,
    source_release_id bigint NOT NULL,
    countries text[],
    brief_summary text,
    primary_outcomes jsonb,
    CONSTRAINT ctgov_study_nct_id_check CHECK ((nct_id ~ '^NCT[0-9]{8}$'::text))
);


--
-- Name: ctgov_study_drug; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.ctgov_study_drug (
    nct_id text NOT NULL,
    drug_id integer NOT NULL,
    intervention_type text NOT NULL,
    arm_types text[] NOT NULL,
    other_names text[] NOT NULL
);


--
-- Name: ctgov_study_indication; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.ctgov_study_indication (
    nct_id text NOT NULL,
    indication_id integer NOT NULL
);


--
-- Name: ctgov_study_moiety; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.ctgov_study_moiety (
    nct_id text NOT NULL,
    moiety_id integer NOT NULL,
    role text NOT NULL,
    method text NOT NULL,
    llm_decision_id bigint,
    CONSTRAINT ctgov_study_moiety_method_check CHECK ((method = ANY (ARRAY['arm_types'::text, 'llm'::text]))),
    CONSTRAINT ctgov_study_moiety_role_check CHECK ((role = ANY (ARRAY['investigational'::text, 'background'::text, 'comparator'::text])))
);


--
-- Name: depmap_common_essential; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.depmap_common_essential (
    entrez_id integer NOT NULL,
    symbol text NOT NULL,
    source_release_id bigint NOT NULL
);


--
-- Name: dev_program; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.dev_program (
    program_id integer NOT NULL,
    moiety_id integer NOT NULL,
    mondo_id text,
    ph1_start date,
    ph2_start date,
    ph3_start date,
    first_start date NOT NULL,
    highest_phase integer NOT NULL,
    n_trials integer NOT NULL,
    n_industry_trials integer NOT NULL,
    first_industry_start date,
    lead_sponsors text[] NOT NULL,
    last_activity date NOT NULL,
    n_active_trials integer NOT NULL,
    build_id uuid NOT NULL,
    CONSTRAINT dev_program_highest_phase_check CHECK (((highest_phase >= 1) AND (highest_phase <= 3)))
);


--
-- Name: dev_program_approval; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.dev_program_approval (
    program_id integer NOT NULL,
    approved text NOT NULL,
    first_approval_date date,
    date_basis text NOT NULL,
    relation text NOT NULL,
    evidence text NOT NULL,
    llm_decision_id bigint NOT NULL,
    CONSTRAINT dev_program_approval_approved_check CHECK ((approved = ANY (ARRAY['yes'::text, 'no'::text, 'uncertain'::text]))),
    CONSTRAINT dev_program_approval_date_basis_check CHECK ((date_basis = ANY (ARRAY['dated'::text, 'before_2015'::text, 'undated'::text, 'none'::text])))
);


--
-- Name: dev_program_build; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.dev_program_build (
    build_id uuid NOT NULL,
    built_at timestamp with time zone DEFAULT now() NOT NULL,
    code_commit text,
    snapshot date NOT NULL,
    parameters jsonb NOT NULL
);


--
-- Name: dev_program_program_id_seq; Type: SEQUENCE; Schema: preclin; Owner: -
--

CREATE SEQUENCE preclin.dev_program_program_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dev_program_program_id_seq; Type: SEQUENCE OWNED BY; Schema: preclin; Owner: -
--

ALTER SEQUENCE preclin.dev_program_program_id_seq OWNED BY preclin.dev_program.program_id;


--
-- Name: dev_program_trial; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.dev_program_trial (
    program_id integer NOT NULL,
    nct_id text NOT NULL,
    phase integer NOT NULL,
    attach text NOT NULL,
    marks_entry boolean DEFAULT true NOT NULL,
    starts_phase boolean DEFAULT true NOT NULL,
    CONSTRAINT dev_program_trial_attach_check CHECK ((attach = ANY (ARRAY['disease'::text, 'broader_condition'::text, 'no_disease'::text, 'non_disease_condition'::text, 'basket'::text]))),
    CONSTRAINT dev_program_trial_phase_check CHECK (((phase >= 1) AND (phase <= 3)))
);


--
-- Name: COLUMN dev_program_trial.starts_phase; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON COLUMN preclin.dev_program_trial.starts_phase IS 'Whether the trial can mark the program''s entry into, or advancement to, its phase: false for an extension study, or when the program''s entity enters the trial only after its main period (preclin.trial_phase_role)';


--
-- Name: drug; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.drug (
    drug_id integer NOT NULL,
    normalized_name text NOT NULL,
    display_name text NOT NULL,
    chembl_id text,
    drugbank_id text,
    modality text,
    modality_subtype text,
    mechanism text,
    route_of_admin text,
    is_placebo boolean DEFAULT false NOT NULL,
    is_combination boolean DEFAULT false NOT NULL,
    is_biosimilar boolean DEFAULT false NOT NULL,
    synonyms text[],
    resolved_via text,
    resolved_confidence text,
    resolved_at timestamp with time zone,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    chembl_max_phase integer,
    chembl_lookup_at timestamp with time zone,
    is_globally_approved boolean,
    chembl_resolved_via text,
    primary_action_type text,
    primary_target_chembl text,
    mechanism_of_action text,
    n_mechanisms integer,
    chembl_mechanism_fetched_at timestamp with time zone,
    bioactivity_pchembl_median numeric(4,2),
    bioactivity_n_targets_1um integer,
    bioactivity_n_records integer,
    bioactivity_fetched_at timestamp with time zone,
    entity_kind text,
    moiety_decision_id bigint,
    CONSTRAINT drug_entity_kind_check CHECK ((entity_kind = ANY (ARRAY['drug'::text, 'combination'::text, 'placebo_or_vehicle'::text, 'vaccine'::text, 'non_drug'::text, 'unclear'::text])))
);


--
-- Name: TABLE drug; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON TABLE preclin.drug IS 'Canonical drug identity. Superset of public.therapies (~11k) with all CT.gov trial-only drugs added.';


--
-- Name: COLUMN drug.resolved_via; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON COLUMN preclin.drug.resolved_via IS 'Provenance of drug→target mapping. Critical for selection-bias analysis.';


--
-- Name: COLUMN drug.is_globally_approved; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON COLUMN preclin.drug.is_globally_approved IS 'TRUE iff drug is in preclin.approval (narrow FDA CDER/CBER 2015-2025) OR chembl_max_phase=4 (broad any-regulator any-indication). One source of truth for "did this drug ever approve anywhere". Rebuild via db/11_consolidated_approval.sql after refreshing chembl_max_phase.';


--
-- Name: drug_drug_id_seq; Type: SEQUENCE; Schema: preclin; Owner: -
--

CREATE SEQUENCE preclin.drug_drug_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: drug_drug_id_seq; Type: SEQUENCE OWNED BY; Schema: preclin; Owner: -
--

ALTER SEQUENCE preclin.drug_drug_id_seq OWNED BY preclin.drug.drug_id;


--
-- Name: drug_moiety; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.drug_moiety (
    drug_id integer NOT NULL,
    moiety_id integer NOT NULL,
    role text NOT NULL,
    biosimilar_of text,
    llm_decision_id bigint,
    method text DEFAULT 'llm'::text NOT NULL,
    CONSTRAINT drug_moiety_method_check CHECK ((method = ANY (ARRAY['llm'::text, 'exact_name'::text]))),
    CONSTRAINT drug_moiety_method_decision CHECK (((method = 'llm'::text) = (llm_decision_id IS NOT NULL))),
    CONSTRAINT drug_moiety_role_check CHECK ((role = ANY (ARRAY['investigational'::text, 'background'::text])))
);


--
-- Name: evidence_known_year; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.evidence_known_year (
    datasource text NOT NULL,
    key text NOT NULL,
    year integer NOT NULL,
    basis text NOT NULL,
    source_release_id bigint NOT NULL
);


--
-- Name: TABLE evidence_known_year; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON TABLE preclin.evidence_known_year IS 'Year an evidence item became public, by preclin.ot_evidence_key (ClinVar RCV accession, IMPC allele, study accession or cohort), from the source''s own release history (pipeline.evidence_dates)';


--
-- Name: COLUMN evidence_known_year.basis; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON COLUMN preclin.evidence_known_year.basis IS 'How the year was found: clinvar_accession (creation year of the RCV record, calibrated from its accession number), clinvar_evaluated (record from ClinVar''s 2013 launch import, dated by its earlier evaluation), impc_release (first IMPC data release with phenotype calls for the allele), geo_public or arrayexpress_public (public date of the experiment), intogen_cohort_year (year in the cohort name), publication (the screen''s paper)';


--
-- Name: evidence_source_release; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.evidence_source_release (
    source_release_id bigint NOT NULL,
    source_name text NOT NULL,
    source_version text NOT NULL,
    source_url text NOT NULL,
    content_sha256 text NOT NULL,
    retrieved_at timestamp with time zone DEFAULT now() NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT evidence_source_release_content_sha256_check CHECK ((content_sha256 ~ '^[0-9a-f]{64}$'::text))
);


--
-- Name: evidence_source_release_source_release_id_seq; Type: SEQUENCE; Schema: preclin; Owner: -
--

CREATE SEQUENCE preclin.evidence_source_release_source_release_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: evidence_source_release_source_release_id_seq; Type: SEQUENCE OWNED BY; Schema: preclin; Owner: -
--

ALTER SEQUENCE preclin.evidence_source_release_source_release_id_seq OWNED BY preclin.evidence_source_release.source_release_id;


--
-- Name: fda_application; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.fda_application (
    appl_no text NOT NULL,
    appl_type text NOT NULL,
    center text NOT NULL,
    sponsor_name text,
    source_release_id bigint NOT NULL,
    CONSTRAINT fda_application_appl_type_check CHECK ((appl_type = ANY (ARRAY['NDA'::text, 'BLA'::text]))),
    CONSTRAINT fda_application_center_check CHECK ((center = ANY (ARRAY['CDER'::text, 'CBER'::text])))
);


--
-- Name: TABLE fda_application; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON TABLE preclin.fda_application IS 'NDA/BLA applications from Drugs@FDA (CDER) and CBER licensed biologics. Loaded by pipeline.fda.';


--
-- Name: fda_application_moiety; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.fda_application_moiety (
    appl_no text NOT NULL,
    moiety_id integer NOT NULL,
    biosimilar_of text,
    llm_decision_id bigint NOT NULL
);


--
-- Name: fda_approved_use; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.fda_approved_use (
    approved_use_id bigint NOT NULL,
    letter_sha256 text NOT NULL,
    ordinal integer NOT NULL,
    disease text NOT NULL,
    indication_as_written text NOT NULL,
    qualifiers text[] NOT NULL,
    change_type text NOT NULL,
    accelerated_approval boolean NOT NULL,
    llm_decision_id bigint NOT NULL,
    CONSTRAINT fda_approved_use_change_type_check CHECK ((change_type = ANY (ARRAY['original_approval'::text, 'new_indication'::text, 'new_population'::text, 'new_regimen'::text, 'conversion_to_full'::text, 'efficacy_labeling'::text, 'other'::text])))
);


--
-- Name: TABLE fda_approved_use; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON TABLE preclin.fda_approved_use IS 'Approved uses stated in FDA approval letters (one row per disease/population per letter), extracted by the referenced pv_evidence.llm_decision. Holds the rows of one extraction run; reloading replaces them. Approval dates come from preclin.fda_submission via fda_submission_letter.';


--
-- Name: fda_approved_use_approved_use_id_seq; Type: SEQUENCE; Schema: preclin; Owner: -
--

CREATE SEQUENCE preclin.fda_approved_use_approved_use_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: fda_approved_use_approved_use_id_seq; Type: SEQUENCE OWNED BY; Schema: preclin; Owner: -
--

ALTER SEQUENCE preclin.fda_approved_use_approved_use_id_seq OWNED BY preclin.fda_approved_use.approved_use_id;


--
-- Name: fda_label; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.fda_label (
    set_id text NOT NULL,
    spl_id text NOT NULL,
    effective_date date,
    application_numbers text[] NOT NULL,
    brand_names text[] NOT NULL,
    generic_names text[] NOT NULL,
    substance_names text[] NOT NULL,
    unii text[] NOT NULL,
    indications_text text,
    source_release_id bigint NOT NULL
);


--
-- Name: fda_letter; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.fda_letter (
    letter_sha256 text NOT NULL,
    letter_text text NOT NULL,
    n_bytes integer NOT NULL,
    CONSTRAINT fda_letter_letter_sha256_check CHECK ((letter_sha256 ~ '^[0-9a-f]{64}$'::text))
);


--
-- Name: fda_product; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.fda_product (
    appl_no text NOT NULL,
    product_no text NOT NULL,
    drug_name text NOT NULL,
    active_ingredient text NOT NULL,
    form text,
    strength text
);


--
-- Name: fda_submission; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.fda_submission (
    appl_no text NOT NULL,
    submission_type text NOT NULL,
    submission_no text NOT NULL,
    submission_class text,
    status text NOT NULL,
    status_date date,
    review_priority text,
    CONSTRAINT fda_submission_submission_type_check CHECK ((submission_type = ANY (ARRAY['ORIG'::text, 'SUPPL'::text])))
);


--
-- Name: fda_submission_letter; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.fda_submission_letter (
    appl_no text NOT NULL,
    submission_type text NOT NULL,
    submission_no text NOT NULL,
    url text NOT NULL,
    doc_date date,
    letter_sha256 text,
    fetch_error text
);


--
-- Name: gene_disease_mechanism; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.gene_disease_mechanism (
    ensembl_id text NOT NULL,
    mondo_id text NOT NULL,
    risk_mechanism text NOT NULL,
    protective text NOT NULL,
    confidence text NOT NULL,
    llm_decision_id bigint NOT NULL,
    risk_year integer,
    protective_year integer
);


--
-- Name: TABLE gene_disease_mechanism; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON TABLE preclin.gene_disease_mechanism IS 'How germline variation in a primary drug target acts on a program disease (pipeline.targets mechanism, drug-blind LLM)';


--
-- Name: COLUMN gene_disease_mechanism.risk_year; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON COLUMN preclin.gene_disease_mechanism.risk_year IS 'Year the risk mechanism was first shown for this gene in this disease; null when risk_mechanism is unknown or none';


--
-- Name: COLUMN gene_disease_mechanism.protective_year; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON COLUMN preclin.gene_disease_mechanism.protective_year IS 'Year the protective effect was first shown for this gene in this disease; null when protective is none_known';


--
-- Name: hgnc_gene; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.hgnc_gene (
    hgnc_id text NOT NULL,
    symbol text NOT NULL,
    name text NOT NULL,
    locus_group text NOT NULL,
    entrez_id integer,
    ensembl_id text,
    uniprot_ids text[] NOT NULL,
    prev_symbols text[] NOT NULL,
    alias_symbols text[] NOT NULL,
    source_release_id bigint NOT NULL
);


--
-- Name: indication; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.indication (
    indication_id integer NOT NULL,
    normalized_name text NOT NULL,
    display_name text NOT NULL,
    mondo_id text,
    efo_id text,
    therapeutic_area text,
    ct_gov_conditions text[],
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    canonical_disease text,
    disease_stage text,
    patient_subset text,
    line_of_therapy text,
    age_group text,
    canonical_classified_at timestamp with time zone,
    mondo_label text,
    indication_kind text,
    mondo_decision_id bigint,
    mondo_match text,
    CONSTRAINT indication_indication_kind_check CHECK ((indication_kind = ANY (ARRAY['disease'::text, 'symptom_or_sign'::text, 'procedure_or_state'::text, 'healthy_volunteers'::text, 'other'::text]))),
    CONSTRAINT indication_mondo_match_check CHECK ((mondo_match = ANY (ARRAY['exact'::text, 'broader'::text])))
);


--
-- Name: TABLE indication; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON TABLE preclin.indication IS 'Canonical indications derived from CT.gov conditions + FDA labels. Superset of public.diseases (~167 curated).';


--
-- Name: COLUMN indication.mondo_id; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON COLUMN preclin.indication.mondo_id IS 'MONDO term for the core disease (no line/stage/biomarker/age qualifiers); set by pipeline.indications from OLS4 candidates.';


--
-- Name: indication_indication_id_seq; Type: SEQUENCE; Schema: preclin; Owner: -
--

CREATE SEQUENCE preclin.indication_indication_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: indication_indication_id_seq; Type: SEQUENCE OWNED BY; Schema: preclin; Owner: -
--

ALTER SEQUENCE preclin.indication_indication_id_seq OWNED BY preclin.indication.indication_id;


--
-- Name: moiety; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.moiety (
    moiety_id integer NOT NULL,
    moiety_key text NOT NULL,
    name text NOT NULL,
    code_names text[] DEFAULT '{}'::text[] NOT NULL,
    modality text,
    modality_decision_id bigint,
    target_kind text,
    target_decision_id bigint,
    unii text,
    unii_decision_id bigint,
    aliases text[] DEFAULT '{}'::text[] NOT NULL,
    CONSTRAINT moiety_moiety_key_check CHECK ((moiety_key ~ '^[a-z0-9]+$'::text)),
    CONSTRAINT moiety_target_kind_check CHECK ((target_kind = ANY (ARRAY['human_protein'::text, 'pathogen'::text, 'no_single_target'::text, 'unknown'::text])))
);


--
-- Name: moiety_moiety_id_seq; Type: SEQUENCE; Schema: preclin; Owner: -
--

CREATE SEQUENCE preclin.moiety_moiety_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: moiety_moiety_id_seq; Type: SEQUENCE OWNED BY; Schema: preclin; Owner: -
--

ALTER SEQUENCE preclin.moiety_moiety_id_seq OWNED BY preclin.moiety.moiety_id;


--
-- Name: moiety_target; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.moiety_target (
    moiety_id integer NOT NULL,
    target_id integer NOT NULL,
    action text NOT NULL,
    is_primary boolean NOT NULL,
    llm_decision_id bigint NOT NULL
);


--
-- Name: mondo_bio_area; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.mondo_bio_area (
    mondo_id text NOT NULL,
    bio_area text NOT NULL,
    llm_decision_id bigint NOT NULL
);


--
-- Name: mouse_model_relation; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.mouse_model_relation (
    ensembl_id text NOT NULL,
    mondo_id text NOT NULL,
    model_id text NOT NULL,
    perturbation text NOT NULL,
    relation text NOT NULL,
    llm_decision_id bigint NOT NULL
);


--
-- Name: ontology_ancestor; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.ontology_ancestor (
    ontology text NOT NULL,
    term_id text NOT NULL,
    ancestor_id text NOT NULL,
    distance integer NOT NULL,
    CONSTRAINT ontology_ancestor_distance_check CHECK ((distance > 0))
);


--
-- Name: ontology_is_a; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.ontology_is_a (
    ontology text NOT NULL,
    child_id text NOT NULL,
    parent_id text NOT NULL
);


--
-- Name: ontology_term; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.ontology_term (
    term_id text NOT NULL,
    ontology text NOT NULL,
    label text NOT NULL,
    definition text,
    synonyms text[] DEFAULT '{}'::text[] NOT NULL,
    is_obsolete boolean NOT NULL,
    source_release_id bigint NOT NULL,
    replaced_by text
);


--
-- Name: ontology_xref; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.ontology_xref (
    ontology text NOT NULL,
    term_id text NOT NULL,
    xref_id text NOT NULL,
    equivalent boolean DEFAULT false NOT NULL
);


--
-- Name: ot_association; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.ot_association (
    target_ensembl text NOT NULL,
    disease_id text NOT NULL,
    datasource text NOT NULL,
    datatype text NOT NULL,
    score double precision NOT NULL,
    evidence_count integer,
    first_year smallint,
    series_years smallint[] NOT NULL,
    series_scores real[] NOT NULL,
    source_release_id bigint NOT NULL
);


--
-- Name: COLUMN ot_association.series_years; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON COLUMN preclin.ot_association.series_years IS 'Years at which the association score changed, rebuilt from the dated rows of preclin.ot_evidence (preclin.harmonic_series); undated rows count only in the release score';


--
-- Name: ot_disease; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.ot_disease (
    disease_id text NOT NULL,
    name text NOT NULL,
    mondo_ids text[] NOT NULL,
    therapeutic_areas text[] NOT NULL,
    source_release_id bigint NOT NULL
);


--
-- Name: ot_evidence; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.ot_evidence (
    evidence_id text NOT NULL,
    target_ensembl text NOT NULL,
    disease_id text NOT NULL,
    datasource text NOT NULL,
    score double precision,
    resource_score double precision,
    evidence_year integer,
    direction_on_target text,
    direction_on_trait text,
    confidence text,
    allelic_requirements text[],
    variant_consequence text,
    detail jsonb NOT NULL,
    source_release_id bigint NOT NULL,
    year_basis text,
    source_year integer
);


--
-- Name: COLUMN ot_evidence.evidence_year; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON COLUMN preclin.ot_evidence.evidence_year IS 'Year the evidence became known: the year preclin.evidence_known_year holds for its key where there is one, else source_year';


--
-- Name: COLUMN ot_evidence.year_basis; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON COLUMN preclin.ot_evidence.year_basis IS 'open_targets (evidence_year is source_year) or the basis of its preclin.evidence_known_year row; null when the row is undated';


--
-- Name: COLUMN ot_evidence.source_year; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON COLUMN preclin.ot_evidence.source_year IS 'Year of the row''s own publication, evidence or release date in Open Targets';


--
-- Name: ot_mouse_phenotype; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.ot_mouse_phenotype (
    target_ensembl text NOT NULL,
    phenotype_id text NOT NULL,
    phenotype_label text NOT NULL,
    class_ids text[] NOT NULL,
    models text[] NOT NULL,
    source_release_id bigint NOT NULL
);


--
-- Name: program_indication; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.program_indication (
    moiety_id integer NOT NULL,
    mondo_id text NOT NULL,
    indication_mondo text NOT NULL,
    llm_decision_id bigint NOT NULL
);


--
-- Name: schema_migration; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.schema_migration (
    migration_number integer NOT NULL,
    migration_name text NOT NULL,
    filename text NOT NULL,
    file_sha256 text NOT NULL,
    migration_kind text NOT NULL,
    execution_mode text NOT NULL,
    applied_at timestamp with time zone DEFAULT now() NOT NULL,
    applied_by text DEFAULT CURRENT_USER NOT NULL,
    git_commit text,
    details jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT schema_migration_execution_mode_check CHECK ((execution_mode = ANY (ARRAY['applied'::text, 'baseline'::text]))),
    CONSTRAINT schema_migration_file_sha256_check CHECK ((file_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT schema_migration_git_commit_check CHECK (((git_commit IS NULL) OR (git_commit ~ '^[0-9a-f]{40}$'::text))),
    CONSTRAINT schema_migration_migration_kind_check CHECK ((migration_kind = ANY (ARRAY['sql'::text, 'python'::text]))),
    CONSTRAINT schema_migration_migration_number_check CHECK ((migration_number > 0))
);


--
-- Name: TABLE schema_migration; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON TABLE preclin.schema_migration IS 'Append-only ledger of numbered migration files with their exact SHA-256; baseline rows explicitly identify migrations applied before this ledger existed.';


--
-- Name: COLUMN schema_migration.execution_mode; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON COLUMN preclin.schema_migration.execution_mode IS 'applied = executed by db/migrate.py; baseline = already applied before ledger introduction and explicitly acknowledged.';


--
-- Name: trial_endpoint; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.trial_endpoint (
    nct_id text NOT NULL,
    purpose text NOT NULL,
    endpoint_class text NOT NULL,
    governing_index integer NOT NULL,
    measurement_type text NOT NULL,
    scale text NOT NULL,
    llm_decision_id bigint NOT NULL
);


--
-- Name: trial_outcome; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.trial_outcome (
    nct_id text NOT NULL,
    execution text NOT NULL,
    stop_reason text NOT NULL,
    secondary_reasons text[] NOT NULL,
    primary_endpoint text NOT NULL,
    safety_signal text NOT NULL,
    efficacy_failure boolean NOT NULL,
    evidence text NOT NULL,
    llm_decision_id bigint NOT NULL
);


--
-- Name: trial_phase_role; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.trial_phase_role (
    nct_id text NOT NULL,
    extension boolean NOT NULL,
    main_period_moieties integer[] NOT NULL,
    llm_decision_id bigint NOT NULL
);


--
-- Name: TABLE trial_phase_role; Type: COMMENT; Schema: preclin; Owner: -
--

COMMENT ON TABLE preclin.trial_phase_role IS 'Phase-start candidates judged by an LLM (pipeline.programs build): whether the trial is an extension of earlier trials, and which of its investigational entities its main period tests';


--
-- Name: trial_publication; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.trial_publication (
    nct_id text NOT NULL,
    pmid text NOT NULL,
    link_source text NOT NULL,
    CONSTRAINT trial_publication_link_source_check CHECK ((link_source = ANY (ARRAY['ctgov_reference'::text, 'pubmed_secondary_id'::text])))
);


--
-- Name: trial_purpose; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.trial_purpose (
    nct_id text NOT NULL,
    purpose text NOT NULL,
    development_conditions text[] NOT NULL,
    llm_decision_id bigint NOT NULL,
    CONSTRAINT trial_purpose_purpose_check CHECK ((purpose = ANY (ARRAY['indication_development'::text, 'multi_indication'::text, 'early_development'::text, 'product_support'::text, 'other'::text])))
);


--
-- Name: unii_name; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.unii_name (
    unii text NOT NULL,
    name text NOT NULL,
    name_type text NOT NULL,
    name_key text NOT NULL,
    CONSTRAINT unii_name_name_type_check CHECK ((name_type = ANY (ARRAY['of'::text, 'cn'::text, 'cd'::text, 'sys'::text, 'bn'::text, 'mn'::text])))
);


--
-- Name: unii_substance; Type: TABLE; Schema: preclin; Owner: -
--

CREATE TABLE preclin.unii_substance (
    unii text NOT NULL,
    display_name text NOT NULL,
    substance_type text,
    ingredient_type text,
    inn_id text,
    usan_id text,
    rxcui text,
    pubchem_cid text,
    inchikey text,
    source_release_id bigint NOT NULL
);


--
-- Name: gene_constraint; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gene_constraint (
    target_id integer NOT NULL,
    pli double precision,
    loeuf double precision,
    oe_lof_upper double precision,
    oe_mis_upper double precision,
    mis_z double precision,
    syn_z double precision,
    constraint_flags text,
    source text DEFAULT 'gnomad_v4.1'::text NOT NULL
);


--
-- Name: publications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.publications (
    id integer NOT NULL,
    pmid text NOT NULL,
    title text,
    authors text,
    journal text,
    year integer,
    doi text,
    fetched_at timestamp with time zone DEFAULT now(),
    abstract text
);


--
-- Name: publications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.publications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: publications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.publications_id_seq OWNED BY public.publications.id;


--
-- Name: targets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.targets (
    id integer NOT NULL,
    symbol text NOT NULL,
    name text,
    ip_type text NOT NULL,
    ensembl_id text,
    tdl text,
    family text,
    location text,
    description text,
    tractability_sm boolean DEFAULT false,
    tractability_ab boolean DEFAULT false,
    tractability_protac boolean DEFAULT false,
    rna_type text,
    pathogen_type text,
    pathogen_species text,
    intervention_type text,
    target_class text,
    uniprot_id text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT targets_intervention_type_check CHECK ((intervention_type = ANY (ARRAY['correction'::text, 'addition'::text, 'silencing'::text]))),
    CONSTRAINT targets_location_check CHECK ((location = ANY (ARRAY['intracellular'::text, 'membrane'::text, 'secreted'::text, 'unknown'::text]))),
    CONSTRAINT targets_pathogen_type_check CHECK ((pathogen_type = ANY (ARRAY['viral'::text, 'bacterial'::text, 'parasitic'::text, 'fungal'::text]))),
    CONSTRAINT targets_tdl_check CHECK ((tdl = ANY (ARRAY['Tclin'::text, 'Tchem'::text, 'Tbio'::text, 'Tdark'::text])))
);


--
-- Name: targets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.targets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: targets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.targets_id_seq OWNED BY public.targets.id;


--
-- Name: llm_decision; Type: TABLE; Schema: pv_evidence; Owner: -
--

CREATE TABLE pv_evidence.llm_decision (
    llm_decision_id bigint NOT NULL,
    decision_run_id uuid NOT NULL,
    task text NOT NULL,
    subject_type text NOT NULL,
    subject_key text NOT NULL,
    input_sha256 text NOT NULL,
    raw_response text NOT NULL,
    parsed_output jsonb NOT NULL,
    output_sha256 text NOT NULL,
    canonical_decision jsonb NOT NULL,
    decision_sha256 text NOT NULL,
    prior_decision_id bigint,
    change_status text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    input_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    provider_request_id text,
    model_parameters jsonb DEFAULT '{}'::jsonb NOT NULL,
    usage jsonb DEFAULT '{}'::jsonb NOT NULL,
    validation_status text DEFAULT 'validated'::text NOT NULL,
    validation_detail jsonb DEFAULT '[]'::jsonb NOT NULL,
    CONSTRAINT llm_decision_change_status_check CHECK ((change_status = ANY (ARRAY['not_compared'::text, 'added'::text, 'changed'::text, 'unchanged'::text]))),
    CONSTRAINT llm_decision_decision_sha256_check CHECK ((decision_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT llm_decision_input_sha256_check CHECK ((input_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT llm_decision_output_sha256_check CHECK ((output_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT llm_decision_validation_status_check CHECK ((validation_status = ANY (ARRAY['validated'::text, 'invalid'::text])))
);


--
-- Name: llm_decision_llm_decision_id_seq; Type: SEQUENCE; Schema: pv_evidence; Owner: -
--

CREATE SEQUENCE pv_evidence.llm_decision_llm_decision_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: llm_decision_llm_decision_id_seq; Type: SEQUENCE OWNED BY; Schema: pv_evidence; Owner: -
--

ALTER SEQUENCE pv_evidence.llm_decision_llm_decision_id_seq OWNED BY pv_evidence.llm_decision.llm_decision_id;


--
-- Name: llm_decision_run; Type: TABLE; Schema: pv_evidence; Owner: -
--

CREATE TABLE pv_evidence.llm_decision_run (
    decision_run_id uuid NOT NULL,
    task text NOT NULL,
    provider text NOT NULL,
    model text NOT NULL,
    model_snapshot text,
    prompt_version text NOT NULL,
    output_schema_version text NOT NULL,
    code_commit text,
    parameters jsonb DEFAULT '{}'::jsonb NOT NULL,
    status text NOT NULL,
    started_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    compare_to_run_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT llm_decision_run_code_commit_check CHECK (((code_commit IS NULL) OR (code_commit ~ '^[0-9a-f]{40}$'::text))),
    CONSTRAINT llm_decision_run_status_check CHECK ((status = ANY (ARRAY['running'::text, 'completed'::text, 'failed'::text])))
);


--
-- Name: dev_program program_id; Type: DEFAULT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.dev_program ALTER COLUMN program_id SET DEFAULT nextval('preclin.dev_program_program_id_seq'::regclass);


--
-- Name: drug drug_id; Type: DEFAULT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.drug ALTER COLUMN drug_id SET DEFAULT nextval('preclin.drug_drug_id_seq'::regclass);


--
-- Name: evidence_source_release source_release_id; Type: DEFAULT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.evidence_source_release ALTER COLUMN source_release_id SET DEFAULT nextval('preclin.evidence_source_release_source_release_id_seq'::regclass);


--
-- Name: fda_approved_use approved_use_id; Type: DEFAULT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_approved_use ALTER COLUMN approved_use_id SET DEFAULT nextval('preclin.fda_approved_use_approved_use_id_seq'::regclass);


--
-- Name: indication indication_id; Type: DEFAULT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.indication ALTER COLUMN indication_id SET DEFAULT nextval('preclin.indication_indication_id_seq'::regclass);


--
-- Name: moiety moiety_id; Type: DEFAULT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.moiety ALTER COLUMN moiety_id SET DEFAULT nextval('preclin.moiety_moiety_id_seq'::regclass);


--
-- Name: publications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publications ALTER COLUMN id SET DEFAULT nextval('public.publications_id_seq'::regclass);


--
-- Name: targets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.targets ALTER COLUMN id SET DEFAULT nextval('public.targets_id_seq'::regclass);


--
-- Name: llm_decision llm_decision_id; Type: DEFAULT; Schema: pv_evidence; Owner: -
--

ALTER TABLE ONLY pv_evidence.llm_decision ALTER COLUMN llm_decision_id SET DEFAULT nextval('pv_evidence.llm_decision_llm_decision_id_seq'::regclass);


--
-- Name: chembl_mechanism chembl_mechanism_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.chembl_mechanism
    ADD CONSTRAINT chembl_mechanism_pkey PRIMARY KEY (mec_id);


--
-- Name: chembl_molecule chembl_molecule_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.chembl_molecule
    ADD CONSTRAINT chembl_molecule_pkey PRIMARY KEY (molecule_chembl_id);


--
-- Name: clinvar_accession_calibration clinvar_accession_calibration_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.clinvar_accession_calibration
    ADD CONSTRAINT clinvar_accession_calibration_pkey PRIMARY KEY (rcv_number);


--
-- Name: ctgov_result_summary ctgov_result_summary_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ctgov_result_summary
    ADD CONSTRAINT ctgov_result_summary_pkey PRIMARY KEY (nct_id);


--
-- Name: ctgov_study_drug ctgov_study_drug_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ctgov_study_drug
    ADD CONSTRAINT ctgov_study_drug_pkey PRIMARY KEY (nct_id, drug_id);


--
-- Name: ctgov_study_indication ctgov_study_indication_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ctgov_study_indication
    ADD CONSTRAINT ctgov_study_indication_pkey PRIMARY KEY (nct_id, indication_id);


--
-- Name: ctgov_study_moiety ctgov_study_moiety_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ctgov_study_moiety
    ADD CONSTRAINT ctgov_study_moiety_pkey PRIMARY KEY (nct_id, moiety_id);


--
-- Name: ctgov_study ctgov_study_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ctgov_study
    ADD CONSTRAINT ctgov_study_pkey PRIMARY KEY (nct_id);


--
-- Name: depmap_common_essential depmap_common_essential_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.depmap_common_essential
    ADD CONSTRAINT depmap_common_essential_pkey PRIMARY KEY (entrez_id);


--
-- Name: dev_program_approval dev_program_approval_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.dev_program_approval
    ADD CONSTRAINT dev_program_approval_pkey PRIMARY KEY (program_id);


--
-- Name: dev_program_build dev_program_build_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.dev_program_build
    ADD CONSTRAINT dev_program_build_pkey PRIMARY KEY (build_id);


--
-- Name: dev_program dev_program_moiety_id_mondo_id_key; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.dev_program
    ADD CONSTRAINT dev_program_moiety_id_mondo_id_key UNIQUE NULLS NOT DISTINCT (moiety_id, mondo_id);


--
-- Name: dev_program dev_program_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.dev_program
    ADD CONSTRAINT dev_program_pkey PRIMARY KEY (program_id);


--
-- Name: dev_program_trial dev_program_trial_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.dev_program_trial
    ADD CONSTRAINT dev_program_trial_pkey PRIMARY KEY (program_id, nct_id);


--
-- Name: drug_moiety drug_moiety_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.drug_moiety
    ADD CONSTRAINT drug_moiety_pkey PRIMARY KEY (drug_id, moiety_id);


--
-- Name: drug drug_normalized_name_key; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.drug
    ADD CONSTRAINT drug_normalized_name_key UNIQUE (normalized_name);


--
-- Name: drug drug_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.drug
    ADD CONSTRAINT drug_pkey PRIMARY KEY (drug_id);


--
-- Name: evidence_known_year evidence_known_year_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.evidence_known_year
    ADD CONSTRAINT evidence_known_year_pkey PRIMARY KEY (datasource, key);


--
-- Name: evidence_source_release evidence_source_release_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.evidence_source_release
    ADD CONSTRAINT evidence_source_release_pkey PRIMARY KEY (source_release_id);


--
-- Name: evidence_source_release evidence_source_release_source_name_source_version_content__key; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.evidence_source_release
    ADD CONSTRAINT evidence_source_release_source_name_source_version_content__key UNIQUE (source_name, source_version, content_sha256);


--
-- Name: fda_application_moiety fda_application_moiety_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_application_moiety
    ADD CONSTRAINT fda_application_moiety_pkey PRIMARY KEY (appl_no, moiety_id);


--
-- Name: fda_application fda_application_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_application
    ADD CONSTRAINT fda_application_pkey PRIMARY KEY (appl_no);


--
-- Name: fda_approved_use fda_approved_use_letter_sha256_ordinal_key; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_approved_use
    ADD CONSTRAINT fda_approved_use_letter_sha256_ordinal_key UNIQUE (letter_sha256, ordinal);


--
-- Name: fda_approved_use fda_approved_use_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_approved_use
    ADD CONSTRAINT fda_approved_use_pkey PRIMARY KEY (approved_use_id);


--
-- Name: fda_label fda_label_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_label
    ADD CONSTRAINT fda_label_pkey PRIMARY KEY (set_id);


--
-- Name: fda_letter fda_letter_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_letter
    ADD CONSTRAINT fda_letter_pkey PRIMARY KEY (letter_sha256);


--
-- Name: fda_product fda_product_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_product
    ADD CONSTRAINT fda_product_pkey PRIMARY KEY (appl_no, product_no);


--
-- Name: fda_submission_letter fda_submission_letter_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_submission_letter
    ADD CONSTRAINT fda_submission_letter_pkey PRIMARY KEY (appl_no, submission_type, submission_no, url);


--
-- Name: fda_submission fda_submission_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_submission
    ADD CONSTRAINT fda_submission_pkey PRIMARY KEY (appl_no, submission_type, submission_no);


--
-- Name: gene_disease_mechanism gene_disease_mechanism_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.gene_disease_mechanism
    ADD CONSTRAINT gene_disease_mechanism_pkey PRIMARY KEY (ensembl_id, mondo_id);


--
-- Name: hgnc_gene hgnc_gene_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.hgnc_gene
    ADD CONSTRAINT hgnc_gene_pkey PRIMARY KEY (hgnc_id);


--
-- Name: hgnc_gene hgnc_gene_symbol_key; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.hgnc_gene
    ADD CONSTRAINT hgnc_gene_symbol_key UNIQUE (symbol);


--
-- Name: indication indication_normalized_name_key; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.indication
    ADD CONSTRAINT indication_normalized_name_key UNIQUE (normalized_name);


--
-- Name: indication indication_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.indication
    ADD CONSTRAINT indication_pkey PRIMARY KEY (indication_id);


--
-- Name: moiety moiety_moiety_key_key; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.moiety
    ADD CONSTRAINT moiety_moiety_key_key UNIQUE (moiety_key);


--
-- Name: moiety moiety_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.moiety
    ADD CONSTRAINT moiety_pkey PRIMARY KEY (moiety_id);


--
-- Name: moiety_target moiety_target_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.moiety_target
    ADD CONSTRAINT moiety_target_pkey PRIMARY KEY (moiety_id, target_id);


--
-- Name: mondo_bio_area mondo_bio_area_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.mondo_bio_area
    ADD CONSTRAINT mondo_bio_area_pkey PRIMARY KEY (mondo_id);


--
-- Name: mouse_model_relation mouse_model_relation_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.mouse_model_relation
    ADD CONSTRAINT mouse_model_relation_pkey PRIMARY KEY (ensembl_id, mondo_id, model_id);


--
-- Name: ontology_ancestor ontology_ancestor_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ontology_ancestor
    ADD CONSTRAINT ontology_ancestor_pkey PRIMARY KEY (term_id, ancestor_id);


--
-- Name: ontology_is_a ontology_is_a_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ontology_is_a
    ADD CONSTRAINT ontology_is_a_pkey PRIMARY KEY (child_id, parent_id);


--
-- Name: ontology_term ontology_term_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ontology_term
    ADD CONSTRAINT ontology_term_pkey PRIMARY KEY (term_id);


--
-- Name: ontology_xref ontology_xref_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ontology_xref
    ADD CONSTRAINT ontology_xref_pkey PRIMARY KEY (term_id, xref_id);


--
-- Name: ot_association ot_association_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ot_association
    ADD CONSTRAINT ot_association_pkey PRIMARY KEY (target_ensembl, disease_id, datasource);


--
-- Name: ot_disease ot_disease_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ot_disease
    ADD CONSTRAINT ot_disease_pkey PRIMARY KEY (disease_id);


--
-- Name: ot_evidence ot_evidence_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ot_evidence
    ADD CONSTRAINT ot_evidence_pkey PRIMARY KEY (evidence_id);


--
-- Name: ot_mouse_phenotype ot_mouse_phenotype_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ot_mouse_phenotype
    ADD CONSTRAINT ot_mouse_phenotype_pkey PRIMARY KEY (target_ensembl, phenotype_id);


--
-- Name: program_indication program_indication_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.program_indication
    ADD CONSTRAINT program_indication_pkey PRIMARY KEY (moiety_id, mondo_id);


--
-- Name: schema_migration schema_migration_filename_key; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.schema_migration
    ADD CONSTRAINT schema_migration_filename_key UNIQUE (filename);


--
-- Name: schema_migration schema_migration_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.schema_migration
    ADD CONSTRAINT schema_migration_pkey PRIMARY KEY (migration_number);


--
-- Name: trial_endpoint trial_endpoint_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.trial_endpoint
    ADD CONSTRAINT trial_endpoint_pkey PRIMARY KEY (nct_id);


--
-- Name: trial_outcome trial_outcome_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.trial_outcome
    ADD CONSTRAINT trial_outcome_pkey PRIMARY KEY (nct_id);


--
-- Name: trial_phase_role trial_phase_role_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.trial_phase_role
    ADD CONSTRAINT trial_phase_role_pkey PRIMARY KEY (nct_id);


--
-- Name: trial_publication trial_publication_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.trial_publication
    ADD CONSTRAINT trial_publication_pkey PRIMARY KEY (nct_id, pmid, link_source);


--
-- Name: trial_purpose trial_purpose_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.trial_purpose
    ADD CONSTRAINT trial_purpose_pkey PRIMARY KEY (nct_id);


--
-- Name: unii_name unii_name_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.unii_name
    ADD CONSTRAINT unii_name_pkey PRIMARY KEY (unii, name, name_type);


--
-- Name: unii_substance unii_substance_pkey; Type: CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.unii_substance
    ADD CONSTRAINT unii_substance_pkey PRIMARY KEY (unii);


--
-- Name: gene_constraint gene_constraint_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gene_constraint
    ADD CONSTRAINT gene_constraint_pkey PRIMARY KEY (target_id);


--
-- Name: publications publications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publications
    ADD CONSTRAINT publications_pkey PRIMARY KEY (id);


--
-- Name: publications publications_pmid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publications
    ADD CONSTRAINT publications_pmid_key UNIQUE (pmid);


--
-- Name: targets targets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.targets
    ADD CONSTRAINT targets_pkey PRIMARY KEY (id);


--
-- Name: targets targets_symbol_ip_type_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.targets
    ADD CONSTRAINT targets_symbol_ip_type_key UNIQUE (symbol, ip_type);


--
-- Name: llm_decision llm_decision_decision_run_id_task_subject_type_subject_key_key; Type: CONSTRAINT; Schema: pv_evidence; Owner: -
--

ALTER TABLE ONLY pv_evidence.llm_decision
    ADD CONSTRAINT llm_decision_decision_run_id_task_subject_type_subject_key_key UNIQUE (decision_run_id, task, subject_type, subject_key);


--
-- Name: llm_decision llm_decision_pkey; Type: CONSTRAINT; Schema: pv_evidence; Owner: -
--

ALTER TABLE ONLY pv_evidence.llm_decision
    ADD CONSTRAINT llm_decision_pkey PRIMARY KEY (llm_decision_id);


--
-- Name: llm_decision_run llm_decision_run_pkey; Type: CONSTRAINT; Schema: pv_evidence; Owner: -
--

ALTER TABLE ONLY pv_evidence.llm_decision_run
    ADD CONSTRAINT llm_decision_run_pkey PRIMARY KEY (decision_run_id);


--
-- Name: chembl_mechanism_parent_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX chembl_mechanism_parent_idx ON preclin.chembl_mechanism USING btree (parent_chembl_id);


--
-- Name: ctgov_study_drug_drug_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX ctgov_study_drug_drug_idx ON preclin.ctgov_study_drug USING btree (drug_id);


--
-- Name: ctgov_study_indication_ind_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX ctgov_study_indication_ind_idx ON preclin.ctgov_study_indication USING btree (indication_id);


--
-- Name: ctgov_study_moiety_moiety_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX ctgov_study_moiety_moiety_idx ON preclin.ctgov_study_moiety USING btree (moiety_id, role);


--
-- Name: ctgov_study_start_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX ctgov_study_start_idx ON preclin.ctgov_study USING btree (start_date);


--
-- Name: ctgov_study_status_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX ctgov_study_status_idx ON preclin.ctgov_study USING btree (overall_status);


--
-- Name: dev_program_mondo_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX dev_program_mondo_idx ON preclin.dev_program USING btree (mondo_id);


--
-- Name: dev_program_trial_nct_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX dev_program_trial_nct_idx ON preclin.dev_program_trial USING btree (nct_id);


--
-- Name: drug_moiety_moiety_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX drug_moiety_moiety_idx ON preclin.drug_moiety USING btree (moiety_id);


--
-- Name: fda_application_moiety_moiety_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX fda_application_moiety_moiety_idx ON preclin.fda_application_moiety USING btree (moiety_id);


--
-- Name: fda_label_appl_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX fda_label_appl_idx ON preclin.fda_label USING gin (application_numbers);


--
-- Name: fda_submission_class_date_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX fda_submission_class_date_idx ON preclin.fda_submission USING btree (submission_class, status_date);


--
-- Name: hgnc_gene_entrez_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX hgnc_gene_entrez_idx ON preclin.hgnc_gene USING btree (entrez_id);


--
-- Name: idx_drug_chembl; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX idx_drug_chembl ON preclin.drug USING btree (chembl_id);


--
-- Name: idx_drug_globally_approved; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX idx_drug_globally_approved ON preclin.drug USING btree (is_globally_approved);


--
-- Name: idx_drug_resolved_via; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX idx_drug_resolved_via ON preclin.drug USING btree (resolved_via);


--
-- Name: idx_ind_area; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX idx_ind_area ON preclin.indication USING btree (therapeutic_area);


--
-- Name: idx_ind_mondo; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX idx_ind_mondo ON preclin.indication USING btree (mondo_id);


--
-- Name: moiety_target_target_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX moiety_target_target_idx ON preclin.moiety_target USING btree (target_id);


--
-- Name: ontology_ancestor_anc_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX ontology_ancestor_anc_idx ON preclin.ontology_ancestor USING btree (ancestor_id);


--
-- Name: ontology_xref_xref_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX ontology_xref_xref_idx ON preclin.ontology_xref USING btree (xref_id);


--
-- Name: ot_association_disease_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX ot_association_disease_idx ON preclin.ot_association USING btree (disease_id);


--
-- Name: ot_evidence_target_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX ot_evidence_target_idx ON preclin.ot_evidence USING btree (target_ensembl, datasource);


--
-- Name: unii_name_key_idx; Type: INDEX; Schema: preclin; Owner: -
--

CREATE INDEX unii_name_key_idx ON preclin.unii_name USING btree (name_key);


--
-- Name: idx_constraint_loeuf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_constraint_loeuf ON public.gene_constraint USING btree (loeuf);


--
-- Name: idx_constraint_pli; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_constraint_pli ON public.gene_constraint USING btree (pli);


--
-- Name: idx_targets_class; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_targets_class ON public.targets USING btree (target_class);


--
-- Name: idx_targets_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_targets_location ON public.targets USING btree (location) WHERE (ip_type = 'Protein'::text);


--
-- Name: idx_targets_pathogen; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_targets_pathogen ON public.targets USING btree (pathogen_type) WHERE (ip_type = 'Pathogen'::text);


--
-- Name: pv_llm_decision_run_task_idx; Type: INDEX; Schema: pv_evidence; Owner: -
--

CREATE INDEX pv_llm_decision_run_task_idx ON pv_evidence.llm_decision_run USING btree (task, started_at DESC);


--
-- Name: pv_llm_decision_subject_idx; Type: INDEX; Schema: pv_evidence; Owner: -
--

CREATE INDEX pv_llm_decision_subject_idx ON pv_evidence.llm_decision USING btree (task, subject_type, subject_key, created_at DESC);


--
-- Name: schema_migration trg_schema_migration_append_only; Type: TRIGGER; Schema: preclin; Owner: -
--

CREATE TRIGGER trg_schema_migration_append_only BEFORE DELETE OR UPDATE ON preclin.schema_migration FOR EACH ROW EXECUTE FUNCTION preclin.reject_schema_migration_mutation();


--
-- Name: chembl_mechanism chembl_mechanism_source_release_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.chembl_mechanism
    ADD CONSTRAINT chembl_mechanism_source_release_id_fkey FOREIGN KEY (source_release_id) REFERENCES preclin.evidence_source_release(source_release_id);


--
-- Name: chembl_molecule chembl_molecule_source_release_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.chembl_molecule
    ADD CONSTRAINT chembl_molecule_source_release_id_fkey FOREIGN KEY (source_release_id) REFERENCES preclin.evidence_source_release(source_release_id);


--
-- Name: clinvar_accession_calibration clinvar_accession_calibration_source_release_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.clinvar_accession_calibration
    ADD CONSTRAINT clinvar_accession_calibration_source_release_id_fkey FOREIGN KEY (source_release_id) REFERENCES preclin.evidence_source_release(source_release_id);


--
-- Name: ctgov_result_summary ctgov_result_summary_nct_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ctgov_result_summary
    ADD CONSTRAINT ctgov_result_summary_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES preclin.ctgov_study(nct_id);


--
-- Name: ctgov_study_drug ctgov_study_drug_drug_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ctgov_study_drug
    ADD CONSTRAINT ctgov_study_drug_drug_id_fkey FOREIGN KEY (drug_id) REFERENCES preclin.drug(drug_id);


--
-- Name: ctgov_study_drug ctgov_study_drug_nct_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ctgov_study_drug
    ADD CONSTRAINT ctgov_study_drug_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES preclin.ctgov_study(nct_id);


--
-- Name: ctgov_study_indication ctgov_study_indication_indication_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ctgov_study_indication
    ADD CONSTRAINT ctgov_study_indication_indication_id_fkey FOREIGN KEY (indication_id) REFERENCES preclin.indication(indication_id);


--
-- Name: ctgov_study_indication ctgov_study_indication_nct_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ctgov_study_indication
    ADD CONSTRAINT ctgov_study_indication_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES preclin.ctgov_study(nct_id);


--
-- Name: ctgov_study_moiety ctgov_study_moiety_llm_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ctgov_study_moiety
    ADD CONSTRAINT ctgov_study_moiety_llm_decision_id_fkey FOREIGN KEY (llm_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: ctgov_study_moiety ctgov_study_moiety_moiety_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ctgov_study_moiety
    ADD CONSTRAINT ctgov_study_moiety_moiety_id_fkey FOREIGN KEY (moiety_id) REFERENCES preclin.moiety(moiety_id);


--
-- Name: ctgov_study_moiety ctgov_study_moiety_nct_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ctgov_study_moiety
    ADD CONSTRAINT ctgov_study_moiety_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES preclin.ctgov_study(nct_id);


--
-- Name: ctgov_study ctgov_study_source_release_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ctgov_study
    ADD CONSTRAINT ctgov_study_source_release_id_fkey FOREIGN KEY (source_release_id) REFERENCES preclin.evidence_source_release(source_release_id);


--
-- Name: depmap_common_essential depmap_common_essential_source_release_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.depmap_common_essential
    ADD CONSTRAINT depmap_common_essential_source_release_id_fkey FOREIGN KEY (source_release_id) REFERENCES preclin.evidence_source_release(source_release_id);


--
-- Name: dev_program_approval dev_program_approval_llm_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.dev_program_approval
    ADD CONSTRAINT dev_program_approval_llm_decision_id_fkey FOREIGN KEY (llm_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: dev_program_approval dev_program_approval_program_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.dev_program_approval
    ADD CONSTRAINT dev_program_approval_program_id_fkey FOREIGN KEY (program_id) REFERENCES preclin.dev_program(program_id) ON DELETE CASCADE;


--
-- Name: dev_program dev_program_build_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.dev_program
    ADD CONSTRAINT dev_program_build_id_fkey FOREIGN KEY (build_id) REFERENCES preclin.dev_program_build(build_id);


--
-- Name: dev_program dev_program_moiety_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.dev_program
    ADD CONSTRAINT dev_program_moiety_id_fkey FOREIGN KEY (moiety_id) REFERENCES preclin.moiety(moiety_id);


--
-- Name: dev_program_trial dev_program_trial_nct_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.dev_program_trial
    ADD CONSTRAINT dev_program_trial_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES preclin.ctgov_study(nct_id);


--
-- Name: dev_program_trial dev_program_trial_program_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.dev_program_trial
    ADD CONSTRAINT dev_program_trial_program_id_fkey FOREIGN KEY (program_id) REFERENCES preclin.dev_program(program_id) ON DELETE CASCADE;


--
-- Name: drug drug_moiety_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.drug
    ADD CONSTRAINT drug_moiety_decision_id_fkey FOREIGN KEY (moiety_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: drug_moiety drug_moiety_drug_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.drug_moiety
    ADD CONSTRAINT drug_moiety_drug_id_fkey FOREIGN KEY (drug_id) REFERENCES preclin.drug(drug_id);


--
-- Name: drug_moiety drug_moiety_llm_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.drug_moiety
    ADD CONSTRAINT drug_moiety_llm_decision_id_fkey FOREIGN KEY (llm_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: drug_moiety drug_moiety_moiety_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.drug_moiety
    ADD CONSTRAINT drug_moiety_moiety_id_fkey FOREIGN KEY (moiety_id) REFERENCES preclin.moiety(moiety_id);


--
-- Name: evidence_known_year evidence_known_year_source_release_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.evidence_known_year
    ADD CONSTRAINT evidence_known_year_source_release_id_fkey FOREIGN KEY (source_release_id) REFERENCES preclin.evidence_source_release(source_release_id);


--
-- Name: fda_application_moiety fda_application_moiety_appl_no_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_application_moiety
    ADD CONSTRAINT fda_application_moiety_appl_no_fkey FOREIGN KEY (appl_no) REFERENCES preclin.fda_application(appl_no);


--
-- Name: fda_application_moiety fda_application_moiety_llm_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_application_moiety
    ADD CONSTRAINT fda_application_moiety_llm_decision_id_fkey FOREIGN KEY (llm_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: fda_application_moiety fda_application_moiety_moiety_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_application_moiety
    ADD CONSTRAINT fda_application_moiety_moiety_id_fkey FOREIGN KEY (moiety_id) REFERENCES preclin.moiety(moiety_id);


--
-- Name: fda_application fda_application_source_release_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_application
    ADD CONSTRAINT fda_application_source_release_id_fkey FOREIGN KEY (source_release_id) REFERENCES preclin.evidence_source_release(source_release_id);


--
-- Name: fda_approved_use fda_approved_use_letter_sha256_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_approved_use
    ADD CONSTRAINT fda_approved_use_letter_sha256_fkey FOREIGN KEY (letter_sha256) REFERENCES preclin.fda_letter(letter_sha256);


--
-- Name: fda_approved_use fda_approved_use_llm_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_approved_use
    ADD CONSTRAINT fda_approved_use_llm_decision_id_fkey FOREIGN KEY (llm_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: fda_label fda_label_source_release_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_label
    ADD CONSTRAINT fda_label_source_release_id_fkey FOREIGN KEY (source_release_id) REFERENCES preclin.evidence_source_release(source_release_id);


--
-- Name: fda_product fda_product_appl_no_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_product
    ADD CONSTRAINT fda_product_appl_no_fkey FOREIGN KEY (appl_no) REFERENCES preclin.fda_application(appl_no);


--
-- Name: fda_submission fda_submission_appl_no_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_submission
    ADD CONSTRAINT fda_submission_appl_no_fkey FOREIGN KEY (appl_no) REFERENCES preclin.fda_application(appl_no);


--
-- Name: fda_submission_letter fda_submission_letter_appl_no_submission_type_submission_n_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_submission_letter
    ADD CONSTRAINT fda_submission_letter_appl_no_submission_type_submission_n_fkey FOREIGN KEY (appl_no, submission_type, submission_no) REFERENCES preclin.fda_submission(appl_no, submission_type, submission_no);


--
-- Name: fda_submission_letter fda_submission_letter_letter_sha256_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.fda_submission_letter
    ADD CONSTRAINT fda_submission_letter_letter_sha256_fkey FOREIGN KEY (letter_sha256) REFERENCES preclin.fda_letter(letter_sha256);


--
-- Name: gene_disease_mechanism gene_disease_mechanism_llm_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.gene_disease_mechanism
    ADD CONSTRAINT gene_disease_mechanism_llm_decision_id_fkey FOREIGN KEY (llm_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: hgnc_gene hgnc_gene_source_release_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.hgnc_gene
    ADD CONSTRAINT hgnc_gene_source_release_id_fkey FOREIGN KEY (source_release_id) REFERENCES preclin.evidence_source_release(source_release_id);


--
-- Name: indication indication_mondo_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.indication
    ADD CONSTRAINT indication_mondo_decision_id_fkey FOREIGN KEY (mondo_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: moiety moiety_modality_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.moiety
    ADD CONSTRAINT moiety_modality_decision_id_fkey FOREIGN KEY (modality_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: moiety moiety_target_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.moiety
    ADD CONSTRAINT moiety_target_decision_id_fkey FOREIGN KEY (target_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: moiety_target moiety_target_llm_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.moiety_target
    ADD CONSTRAINT moiety_target_llm_decision_id_fkey FOREIGN KEY (llm_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: moiety_target moiety_target_moiety_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.moiety_target
    ADD CONSTRAINT moiety_target_moiety_id_fkey FOREIGN KEY (moiety_id) REFERENCES preclin.moiety(moiety_id);


--
-- Name: moiety_target moiety_target_target_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.moiety_target
    ADD CONSTRAINT moiety_target_target_id_fkey FOREIGN KEY (target_id) REFERENCES public.targets(id);


--
-- Name: moiety moiety_unii_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.moiety
    ADD CONSTRAINT moiety_unii_decision_id_fkey FOREIGN KEY (unii_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: moiety moiety_unii_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.moiety
    ADD CONSTRAINT moiety_unii_fkey FOREIGN KEY (unii) REFERENCES preclin.unii_substance(unii);


--
-- Name: mondo_bio_area mondo_bio_area_llm_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.mondo_bio_area
    ADD CONSTRAINT mondo_bio_area_llm_decision_id_fkey FOREIGN KEY (llm_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: mouse_model_relation mouse_model_relation_llm_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.mouse_model_relation
    ADD CONSTRAINT mouse_model_relation_llm_decision_id_fkey FOREIGN KEY (llm_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: ontology_term ontology_term_source_release_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ontology_term
    ADD CONSTRAINT ontology_term_source_release_id_fkey FOREIGN KEY (source_release_id) REFERENCES preclin.evidence_source_release(source_release_id);


--
-- Name: ot_association ot_association_source_release_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ot_association
    ADD CONSTRAINT ot_association_source_release_id_fkey FOREIGN KEY (source_release_id) REFERENCES preclin.evidence_source_release(source_release_id);


--
-- Name: ot_disease ot_disease_source_release_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ot_disease
    ADD CONSTRAINT ot_disease_source_release_id_fkey FOREIGN KEY (source_release_id) REFERENCES preclin.evidence_source_release(source_release_id);


--
-- Name: ot_evidence ot_evidence_source_release_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ot_evidence
    ADD CONSTRAINT ot_evidence_source_release_id_fkey FOREIGN KEY (source_release_id) REFERENCES preclin.evidence_source_release(source_release_id);


--
-- Name: ot_mouse_phenotype ot_mouse_phenotype_source_release_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.ot_mouse_phenotype
    ADD CONSTRAINT ot_mouse_phenotype_source_release_id_fkey FOREIGN KEY (source_release_id) REFERENCES preclin.evidence_source_release(source_release_id);


--
-- Name: program_indication program_indication_llm_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.program_indication
    ADD CONSTRAINT program_indication_llm_decision_id_fkey FOREIGN KEY (llm_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: program_indication program_indication_moiety_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.program_indication
    ADD CONSTRAINT program_indication_moiety_id_fkey FOREIGN KEY (moiety_id) REFERENCES preclin.moiety(moiety_id);


--
-- Name: trial_endpoint trial_endpoint_llm_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.trial_endpoint
    ADD CONSTRAINT trial_endpoint_llm_decision_id_fkey FOREIGN KEY (llm_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: trial_endpoint trial_endpoint_nct_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.trial_endpoint
    ADD CONSTRAINT trial_endpoint_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES preclin.ctgov_study(nct_id);


--
-- Name: trial_outcome trial_outcome_llm_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.trial_outcome
    ADD CONSTRAINT trial_outcome_llm_decision_id_fkey FOREIGN KEY (llm_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: trial_outcome trial_outcome_nct_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.trial_outcome
    ADD CONSTRAINT trial_outcome_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES preclin.ctgov_study(nct_id);


--
-- Name: trial_phase_role trial_phase_role_llm_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.trial_phase_role
    ADD CONSTRAINT trial_phase_role_llm_decision_id_fkey FOREIGN KEY (llm_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: trial_phase_role trial_phase_role_nct_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.trial_phase_role
    ADD CONSTRAINT trial_phase_role_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES preclin.ctgov_study(nct_id);


--
-- Name: trial_publication trial_publication_nct_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.trial_publication
    ADD CONSTRAINT trial_publication_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES preclin.ctgov_study(nct_id);


--
-- Name: trial_publication trial_publication_pmid_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.trial_publication
    ADD CONSTRAINT trial_publication_pmid_fkey FOREIGN KEY (pmid) REFERENCES public.publications(pmid);


--
-- Name: trial_purpose trial_purpose_llm_decision_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.trial_purpose
    ADD CONSTRAINT trial_purpose_llm_decision_id_fkey FOREIGN KEY (llm_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: trial_purpose trial_purpose_nct_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.trial_purpose
    ADD CONSTRAINT trial_purpose_nct_id_fkey FOREIGN KEY (nct_id) REFERENCES preclin.ctgov_study(nct_id);


--
-- Name: unii_name unii_name_unii_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.unii_name
    ADD CONSTRAINT unii_name_unii_fkey FOREIGN KEY (unii) REFERENCES preclin.unii_substance(unii);


--
-- Name: unii_substance unii_substance_source_release_id_fkey; Type: FK CONSTRAINT; Schema: preclin; Owner: -
--

ALTER TABLE ONLY preclin.unii_substance
    ADD CONSTRAINT unii_substance_source_release_id_fkey FOREIGN KEY (source_release_id) REFERENCES preclin.evidence_source_release(source_release_id);


--
-- Name: gene_constraint gene_constraint_target_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gene_constraint
    ADD CONSTRAINT gene_constraint_target_id_fkey FOREIGN KEY (target_id) REFERENCES public.targets(id) ON DELETE CASCADE;


--
-- Name: llm_decision llm_decision_decision_run_id_fkey; Type: FK CONSTRAINT; Schema: pv_evidence; Owner: -
--

ALTER TABLE ONLY pv_evidence.llm_decision
    ADD CONSTRAINT llm_decision_decision_run_id_fkey FOREIGN KEY (decision_run_id) REFERENCES pv_evidence.llm_decision_run(decision_run_id);


--
-- Name: llm_decision llm_decision_prior_decision_id_fkey; Type: FK CONSTRAINT; Schema: pv_evidence; Owner: -
--

ALTER TABLE ONLY pv_evidence.llm_decision
    ADD CONSTRAINT llm_decision_prior_decision_id_fkey FOREIGN KEY (prior_decision_id) REFERENCES pv_evidence.llm_decision(llm_decision_id);


--
-- Name: llm_decision_run llm_decision_run_compare_to_run_id_fkey; Type: FK CONSTRAINT; Schema: pv_evidence; Owner: -
--

ALTER TABLE ONLY pv_evidence.llm_decision_run
    ADD CONSTRAINT llm_decision_run_compare_to_run_id_fkey FOREIGN KEY (compare_to_run_id) REFERENCES pv_evidence.llm_decision_run(decision_run_id);


--
-- PostgreSQL database dump complete
--


