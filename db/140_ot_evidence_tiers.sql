-- Each target, Open Targets disease and evidence source with the first year of each evidence tier, for the Phase 2
-- analysis (report.section3.evidence_index). It summarises preclin.ot_evidence, which changes only when Open Targets
-- evidence or its dates are reloaded: pipeline.opentargets.apply_dates refreshes it then, so a report build reads
-- the summary instead of scanning every evidence row. Undated evidence takes the year 9999 (section3.NEVER).
CREATE MATERIALIZED VIEW preclin.ot_evidence_tiers AS
WITH q75 AS (SELECT percentile_cont(0.75) WITHIN GROUP (ORDER BY resource_score) AS q
             FROM preclin.ot_evidence WHERE datasource = 'impc'),
     e AS (
    SELECT target_ensembl AS ens, disease_id, resource_score, confidence,
           direction_on_target AS dot, direction_on_trait AS dtr, (detail->>'log2FoldChangeValue')::float AS lfc,
           CASE WHEN datasource <> 'impc' THEN datasource
                WHEN preclin.ot_evidence_key(datasource, detail) IS NOT NULL THEN 'impc' ELSE 'mgi' END AS source,
           coalesce(evidence_year, 9999) AS y,
           datasource NOT IN ('eva', 'eva_somatic')
             OR detail->'clinicalSignificances' ?| array['pathogenic', 'likely pathogenic'] AS counts
    FROM preclin.ot_evidence
    WHERE (datasource NOT IN ('eva', 'eva_somatic')
           OR detail->'clinicalSignificances' ?| array['pathogenic', 'likely pathogenic', 'protective'])
      AND NOT (datasource = 'clingen' AND confidence IN ('Disputed', 'Refuted', 'Limited',
                                                           'No Known Disease Relationship'))
      AND NOT (datasource = 'impc' AND resource_score IS NULL))
SELECT ens, disease_id, source, min(y) FILTER (WHERE counts) AS y_any,
       min(y) FILTER (WHERE counts AND (
                            (source = 'gwas_credible_sets' AND resource_score >= 0.8)
                         OR (source = 'eva' AND confidence IN ('criteria provided, multiple submitters, no conflicts',
                                                               'reviewed by expert panel', 'practice guideline'))
                         OR (source = 'clingen' AND confidence IN ('Definitive', 'Strong'))
                         OR (source = 'gene2phenotype' AND confidence IN ('definitive', 'strong'))
                         OR (source = 'genomics_england' AND confidence = 'green')
                         OR (source IN ('impc', 'mgi') AND resource_score >= (SELECT q FROM q75)))) AS y_strong,
       min(y) FILTER (WHERE source = 'gwas_credible_sets' AND resource_score >= 0.5
                        AND resource_score < 0.8) AS y_mid,
       min(y) FILTER (WHERE source = 'gwas_credible_sets' AND resource_score < 0.5) AS y_weak,
       min(y) FILTER (WHERE dot = 'LoF' AND dtr = 'protect') AS y_lof_protect,
       min(y) FILTER (WHERE counts AND dot = 'LoF' AND dtr = 'risk') AS y_lof_risk,
       min(y) FILTER (WHERE counts AND dot = 'GoF' AND dtr = 'risk') AS y_gof_risk,
       min(y) FILTER (WHERE dot = 'GoF' AND dtr = 'protect') AS y_gof_protect,
       min(y) FILTER (WHERE lfc > 0) AS y_up
FROM e GROUP BY 1, 2, 3;

CREATE INDEX ot_evidence_tiers_ens ON preclin.ot_evidence_tiers (ens);

COMMENT ON MATERIALIZED VIEW preclin.ot_evidence_tiers IS
  'First year of each evidence tier per target, Open Targets disease and source; refreshed by pipeline.opentargets.apply_dates.';
