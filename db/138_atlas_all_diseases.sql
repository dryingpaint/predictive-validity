-- The atlas covers every disease with a Phase 2 entrant, not the top diseases of each area: restate the
-- comments that named the earlier list.

BEGIN;
SET LOCAL lock_timeout = '3s';

COMMENT ON TABLE preclin.atlas_indication IS
    'The diseases of the atlas (lists.py): every disease with a Phase 2 entrant of 2008-2019 under report.section1.phase_rows, after the MERGE and DROP cleaning rules. area_rank is the disease''s place in its area by programs.';
COMMENT ON COLUMN preclin.atlas_build.n_members IS 'Rows of atlas_member: novel Phase 2 entries of 2008-2019 in the atlas diseases.';
COMMENT ON TABLE preclin.atlas_member IS
    'One row per novel Phase 2 entry of 2008-2019 in an atlas disease, keyed by entity and disease since program ids change when programs are rebuilt: the mechanism it counts toward, or why it counts toward none.';
COMMENT ON COLUMN preclin.atlas_member.mondo_id IS 'The atlas disease (after lists.MERGE); program_mondo_id is the program''s own disease.';
COMMENT ON VIEW preclin.atlas_register IS
    'Every mechanism of every atlas disease, counted across modalities. tracked: at least atlas_build.min_programs distinct entities, so the tile''s model track record is drafted. Phase never decides tracking.';
COMMIT;
