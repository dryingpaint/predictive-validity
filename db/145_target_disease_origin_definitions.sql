-- The origin definitions follow the evidence chart's lines (the owner's one-list decision of 2026-11-20 on #146; the
-- crosswalk is pipeline.target_origin.CHART_LINE): cell_screen is a screen in human cells (the chart's crispr line);
-- earlier_drug_other_disease is an approval for an unrelated disease (the chart's approved_unrelated_only tier; an
-- approval for a related disease makes the pair validated_at_entry, which is not an origin); diseased_tissue covers
-- RNA and protein (the chart's expression line and #154's protein-in-tissue kind); observational_biomarker is a
-- measurement in blood, another fluid or imaging (#154's tracking kind); animal_model_pharmacology is non-genetic
-- (#154's second kind). Comment only; no data changes.

BEGIN;
SET LOCAL lock_timeout = '3s';
COMMENT ON COLUMN preclin.target_disease_origin.origin IS
    'human_genetics: germline variants link the target to the disease (GWAS, gene burden, Mendelian); tumour_genetics: the gene is recurrently mutated in the cancer; diseased_tissue: the gene''s RNA or protein level differs in diseased tissue; mouse_genetics: knocked-out or mutant mice show the disease; curated_pathway: a curated pathway shows a disease mutation disrupting the target; cell_screen: a gene-knockout screen in human cells; earlier_drug_other_disease: a drug on the target was approved for an unrelated disease; observational_biomarker: the target or its product in patients'' blood, another fluid or on imaging tracks the disease; human_cell_perturbation: perturbing the target in human cells or tissue changes a disease phenotype; animal_model_pharmacology: modulating the target by means other than genetics changes an animal model of the disease; clinical_observation: an effect seen in people, such as a side effect; phenotypic_screen: a molecule found without a target hypothesis came first; unclear: no source settles it. The last six exist only for labelled rows. Each kind is one line of the report''s evidence chart (pipeline.target_origin.CHART_LINE).';
COMMIT;
