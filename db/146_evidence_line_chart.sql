-- The evidence chart's grouping in the evidence-line registry: each line's area and whether it heads the area or is
-- one of its mutually exclusive tiers, and the lines only the chart uses, so the stored dataset holds every row the
-- chart draws.

BEGIN;
SET LOCAL lock_timeout = '3s';

ALTER TABLE preclin.evidence_line
    ADD COLUMN area text,
    ADD COLUMN area_level text CHECK (area_level IN ('area', 'tier')),
    ADD COLUMN area_position integer,
    ADD CONSTRAINT evidence_line_area_complete
        CHECK ((area IS NULL) = (area_level IS NULL) AND (area IS NULL) = (area_position IS NULL));
ALTER TABLE preclin.evidence_line DROP CONSTRAINT evidence_line_level_check;
ALTER TABLE preclin.evidence_line ADD CONSTRAINT evidence_line_level_check
    CHECK (level IN ('category', 'subcategory', 'descriptive', 'adjustment', 'measurement', 'chart'));

COMMENT ON TABLE preclin.evidence_line IS
    'Registry of evidence lines (report.evidence_lines.CATEGORIES and AREAS): efficacy categories grouped by the experimental system that produced the evidence, then safety risk and clinical precedent, the biomarker-selection adjustment, two raw measurements, and the lines only the evidence chart uses. A line the chart draws also carries its area.';
COMMENT ON COLUMN preclin.evidence_line.level IS
    'category (exposed when any non-descriptive subcategory is), subcategory, descriptive (shown but not part of its category), adjustment, measurement (a raw value behind a line), or chart (a line only the evidence chart uses, filed under the category its evidence comes from).';
COMMENT ON COLUMN preclin.evidence_line.area IS
    'The evidence chart''s area the line is drawn in (report.evidence_lines.AREAS); null for a line the chart does not draw.';
COMMENT ON COLUMN preclin.evidence_line.area_level IS
    'area (the area''s heading row) or tier (one of the area''s mutually exclusive groups below it).';
COMMENT ON COLUMN preclin.evidence_line.area_position IS 'The line''s order in the evidence chart, top to bottom.';

COMMIT;
