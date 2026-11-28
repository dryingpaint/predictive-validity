-- Polygenicity (#147): the drugged large-effect gene flag stored with the profile, so the report reads it from the
-- table instead of the Open Targets direct-association download (filled by `python -m pipeline.polygenicity drugged`).
ALTER TABLE preclin.disease_polygenicity ADD COLUMN drugged_large_effect boolean;
COMMENT ON COLUMN preclin.disease_polygenicity.drugged_large_effect IS
    'a gene with rare-variant or Mendelian evidence for the disease (the mendelian_genes match) is the primary target of a programme that entered Phase 2 or 3 in the disease or was approved for it; pipeline.polygenicity drugged';
