-- Polygenicity and failure (issue #147): the per-disease genetic-architecture profile and what it is built from.
-- preclin.gwas_catalog_study: one row per GWAS Catalog study (release 2026-11-19) with its traits mapped to MONDO,
-- its cases, controls and European share, and the path of its harmonised summary statistics when public.
-- preclin.ldsc_run: one row per study we ran LDSC on (observed-scale SNP heritability), with the independent
-- genome-wide significant loci after LD clumping (r2 < 0.1 within 1 Mb, extended MHC as one locus) and the share
-- of heritability carried by the ten strongest lead SNPs (Melissa's registered sensitivity 3).
-- preclin.gbd_prevalence: GBD 2023 prevalence by cause (global, both sexes, all ages, 2021), the population
-- prevalence for the liability scale.
-- preclin.disease_polygenicity: one row per candidate disease (non-oncology, non-infectious, with a US Phase 2
-- entry 2008-2019): the chosen study, K and its source, liability-scale h2, the score (loci per unit of h2),
-- and the secondary measures (gene counts, Mendelian form, O'Connor's Me, Pan-UKB h2). Tertiles are fixed in
-- report/polygenicity.py and in a dated #147 comment before any outcome is joined.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.gwas_catalog_study (
    gcst text PRIMARY KEY,
    pubmed_id text,
    published date,
    trait text,
    mapped_trait_uris text[] NOT NULL,
    mondo_ids text[] NOT NULL,
    initial_sample text,
    cases int,
    controls int,
    eur_share numeric,
    sumstats_path text,
    association_count int,
    source_release_id int NOT NULL REFERENCES preclin.evidence_source_release
);
COMMENT ON TABLE preclin.gwas_catalog_study IS
    'One GWAS Catalog study (release 2026-11-19): its mapped traits as MONDO ids, cases and controls parsed from the initial sample text, the European share of the initial sample, and the harmonised summary-statistics path when public.';
COMMENT ON COLUMN preclin.gwas_catalog_study.mondo_ids IS
    'MONDO ids of the mapped traits: through the Open Targets disease index, equivalent MONDO cross-references, or the id itself; empty when no trait maps.';
COMMENT ON COLUMN preclin.gwas_catalog_study.cases IS 'Cases summed over the ancestry groups of the initial sample; null when the text names no cases.';
COMMENT ON COLUMN preclin.gwas_catalog_study.eur_share IS 'Share of the initial sample in the Catalog''s European ancestry category; null when the ancestry file has no initial-stage row.';
COMMENT ON COLUMN preclin.gwas_catalog_study.sumstats_path IS 'Path under the Catalog summary-statistics FTP root of the harmonised file; null when none is public.';

CREATE TABLE preclin.ldsc_run (
    gcst text PRIMARY KEY REFERENCES preclin.gwas_catalog_study,
    status text NOT NULL CHECK (status IN ('ok', 'no_effect', 'fetch_failed', 'munge_failed', 'h2_failed', 'clump_failed')),
    n int,
    n_snps int,
    h2_obs numeric,
    h2_obs_se numeric,
    intercept numeric,
    ratio numeric,
    lambda_gc numeric,
    mean_chi2 numeric,
    n_index_snps int,
    loci int,
    concentration numeric,
    top10 jsonb,
    tool text NOT NULL,
    tool_version text NOT NULL,
    ld_reference text NOT NULL,
    run_at timestamptz NOT NULL DEFAULT now(),
    log text
);
COMMENT ON TABLE preclin.ldsc_run IS
    'One LDSC run per study: observed-scale SNP heritability on HapMap3 SNPs with the EUR LD scores, the lead SNPs after PLINK clumping of the genome-wide significant SNPs, and the heritability concentration.';
COMMENT ON COLUMN preclin.ldsc_run.status IS 'ok, or the first stage that failed: no_effect (no beta or odds ratio in the file), fetch_failed, munge_failed, h2_failed, clump_failed.';
COMMENT ON COLUMN preclin.ldsc_run.n IS 'Sample size given to munge_sumstats: cases plus controls.';
COMMENT ON COLUMN preclin.ldsc_run.loci IS 'Independent genome-wide significant loci: clumped lead SNPs at P <= 5e-8, r2 < 0.1 within 1 Mb, every lead SNP in chr6:25-34 Mb counted once.';
COMMENT ON COLUMN preclin.ldsc_run.concentration IS 'Share of observed-scale h2 carried by the ten lead SNPs with the largest z^2: sum of (z^2 - 1) / n over h2_obs.';
COMMENT ON COLUMN preclin.ldsc_run.top10 IS 'The lead SNPs behind concentration: rsid, chromosome, position, z^2, per-SNP h2.';

CREATE TABLE preclin.gbd_prevalence (
    cause_id int PRIMARY KEY,
    cause_name text NOT NULL,
    year int NOT NULL,
    rate_per_100k numeric NOT NULL,
    source_release_id int NOT NULL REFERENCES preclin.evidence_source_release
);
COMMENT ON TABLE preclin.gbd_prevalence IS
    'GBD 2023 prevalence rate per 100,000 by most-detailed cause, global, both sexes, all ages, year 2021 (IHME GBD Results tool export received from Melissa 2026-11-23; free-of-charge non-commercial terms).';

CREATE TABLE preclin.disease_polygenicity (
    mondo_id text PRIMARY KEY,
    label text,
    bio_area text,
    entries int,
    gwas_studies int,
    gws_associations int,
    loci_catalog int,
    gcst text REFERENCES preclin.gwas_catalog_study,
    trait_level text CHECK (trait_level IN ('exact', 'descendant')),
    n_cases int,
    n_controls int,
    n_eff numeric,
    h2_obs numeric,
    h2_obs_se numeric,
    intercept numeric,
    h2_z numeric,
    k numeric,
    k_source text CHECK (k_source IN ('gbd', 'panukb', 'none')),
    h2_liab numeric,
    ldsc_status text NOT NULL CHECK (ldsc_status IN ('ok', 'no_study', 'no_sumstats', 'not_european', 'no_case_control',
        'no_effect', 'run_failed', 'low_z', 'out_of_bounds', 'no_k', 'not_profiled')),
    loci int,
    concentration numeric,
    score numeric,
    log10_score numeric,
    gwas_genes int,
    gwas_genes_per_10k_cases numeric,
    mendelian_genes int,
    mendelian_form boolean,
    me_log10 numeric,
    panukb_h2_liab numeric,
    panukb_h2_z numeric,
    source_release_ids int[] NOT NULL,
    built_at timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE preclin.disease_polygenicity IS
    'The genetic-architecture profile of each candidate disease of #147: the study LDSC ran on, its heritability on the liability scale, the independent loci, the score (loci per unit of h2) and the secondary measures. Tertiles are fixed outside this table, in report/polygenicity.py.';
COMMENT ON COLUMN preclin.disease_polygenicity.trait_level IS 'exact when the study''s single mapped trait is the disease itself, descendant when it is a MONDO descendant.';
COMMENT ON COLUMN preclin.disease_polygenicity.k IS 'Population prevalence used for the liability scale: the GBD cause''s rate / 100,000, else the Pan-UKB European case fraction of the matching ICD-10 code.';
COMMENT ON COLUMN preclin.disease_polygenicity.ldsc_status IS 'ok when an estimate exists (h2_z >= 4, 0 < h2_liab <= 1); otherwise why not, the first reason in the order no_study, no_sumstats, not_european, no_case_control, no_effect, run_failed, low_z, out_of_bounds, no_k; not_profiled marks a disease the unit gained after the build.';
COMMENT ON COLUMN preclin.disease_polygenicity.score IS 'Independent loci per unit of liability-scale SNP heritability (loci / h2_liab), null unless ldsc_status is ok.';
COMMENT ON COLUMN preclin.disease_polygenicity.loci_catalog IS 'Descriptive only: genome-wide significant associations from every Catalog study of the disease and its MONDO descendants, any ancestry, merged within 500 kb.';
COMMENT ON COLUMN preclin.disease_polygenicity.gwas_genes IS 'Distinct genes with GWAS evidence (Open Targets credible sets) for the disease, a subtype or a disease at Lin >= 0.8, among the targets preclin.ot_evidence holds.';
COMMENT ON COLUMN preclin.disease_polygenicity.mendelian_form IS 'Melissa''s registered sensitivity 4: a gene with evidence from Orphanet, ClinGen, Genomics England or Gene2Phenotype through Open Targets for the disease, a subtype or a disease at Lin >= 0.8.';

COMMIT;
