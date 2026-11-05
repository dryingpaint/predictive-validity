-- Every entity merge (pipeline.drugs merge_groups), so a session holding an old moiety_id can follow it to the entity
-- that took its rows. Losers are deleted when merged, so the ids here carry no foreign keys.

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE preclin.moiety_merge (
    merge_id        bigserial PRIMARY KEY,
    loser_id        integer NOT NULL,
    loser_name      text NOT NULL,
    survivor_id     integer NOT NULL,
    cause           text NOT NULL CHECK (cause IN ('unii', 'same_entity', 'reversed')),
    llm_decision_id bigint REFERENCES pv_evidence.llm_decision (llm_decision_id),
    note            text,
    merged_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX moiety_merge_loser_idx ON preclin.moiety_merge (loser_id);
COMMENT ON TABLE preclin.moiety_merge IS
    'One row per entity merged into another (pipeline.drugs merge_groups), and per merge later undone (cause reversed). Ids are not foreign keys: a loser no longer exists, and a survivor may itself be merged later (follow its own row).';
COMMENT ON COLUMN preclin.moiety_merge.merge_id IS 'Row id, in the order merges were recorded.';
COMMENT ON COLUMN preclin.moiety_merge.loser_id IS 'The entity merged away: its rows moved to survivor_id and it was deleted. For cause reversed, the entity whose earlier merge was undone.';
COMMENT ON COLUMN preclin.moiety_merge.loser_name IS 'The merged-away entity''s name when merged.';
COMMENT ON COLUMN preclin.moiety_merge.survivor_id IS 'The entity that took the loser''s rows (for cause reversed, the entity it had been merged into).';
COMMENT ON COLUMN preclin.moiety_merge.cause IS 'unii: both resolved to the same FDA substance (pipeline.drugs unii); same_entity: the same-entity pass judged them one entity; reversed: a wrong merge undone by pipeline.drugs split, the loser''s strings now resolving to an entity of their own.';
COMMENT ON COLUMN preclin.moiety_merge.llm_decision_id IS 'The moiety_unii decision behind a unii merge or behind a reversed one; null for same_entity merges, which rest on several decisions.';
COMMENT ON COLUMN preclin.moiety_merge.note IS 'For backfilled rows and reversals, how the row was established (for a reversal, the entity id the strings went to).';
COMMENT ON COLUMN preclin.moiety_merge.merged_at IS 'When the merge (or reversal) was recorded; backfilled rows carry the time of the run that merged them.';
COMMIT;
