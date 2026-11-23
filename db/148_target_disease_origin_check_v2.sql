-- Check method v2 of the origin labels (#146 note of 2026-11-21: facts in code, judgment by agreement). A graded
-- label on which the two checkers disagree, or whose earlier-drug approval the dated Drugs@FDA index cannot confirm,
-- is stored disputed (origin unclear) until a human read from the disputes sheet settles it. check_fields records
-- each field's answer (quote, year, category: yes, no, unverified, disputed), the approval fact (unrelated, related,
-- none, or null for other origins), both checkers' decision ids and the human verdicts applied. No data changes.

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.target_disease_origin DROP CONSTRAINT target_disease_origin_check_outcome_check;
ALTER TABLE preclin.target_disease_origin ADD CONSTRAINT target_disease_origin_check_outcome_check
    CHECK (check_outcome = ANY (ARRAY['supported'::text, 'unsupported'::text, 'unverified'::text,
                                     'disputed'::text, 'not_checked'::text]));
ALTER TABLE preclin.target_disease_origin ADD COLUMN check_fields jsonb;
COMMENT ON COLUMN preclin.target_disease_origin.check_outcome IS
    'supported: every field holds; unsupported: a field is no; unverified: a field could not be verified; disputed: the two checkers disagree on a field, or the earlier-drug approval is not in the dated index, and no human verdict has settled it; not_checked: the label was (re)written and not yet checked. A row that is not supported holds origin unclear, grade none; the label as read stays in llm_decision_id''s decision. Method pipeline.target_origin.CHECK_METHOD.';
COMMENT ON COLUMN preclin.target_disease_origin.check_fields IS
    'The check''s record for the row: quote, year, category (yes, no, unverified, disputed), fact (unrelated, related, none; null unless the label is earlier_drug_other_disease), decisions (model -> llm_decision_id of each checker''s answer), human (field -> verdict applied from the disputes sheet). Null until checked.';
COMMIT;
