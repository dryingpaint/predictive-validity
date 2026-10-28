-- An approval that predates the first FDA approval letter the pipeline reads (pipeline.fda.LETTERS_FROM)
-- carries date_basis 'before_letters', so moving the start of the letters needs no schema change.

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.dev_program_approval DROP CONSTRAINT dev_program_approval_date_basis_check;
UPDATE preclin.dev_program_approval SET date_basis = 'before_letters' WHERE date_basis = 'before_2015';
ALTER TABLE preclin.dev_program_approval ADD CONSTRAINT dev_program_approval_date_basis_check
    CHECK (date_basis = ANY (ARRAY['dated', 'before_letters', 'undated', 'none']));
COMMENT ON COLUMN preclin.dev_program_approval.date_basis IS
    'dated: first_approval_date is the action date of the approval; before_letters: approved before the first approval letter read (pipeline.fda.LETTERS_FROM), date unknown; undated: approved, date unknown; none: not approved.';
COMMIT;
