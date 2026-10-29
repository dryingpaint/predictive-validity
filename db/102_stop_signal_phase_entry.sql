-- The phase entry date of each stopped program, so reports can show the stop causes for any window of entries
-- inside the one traced (pipeline.stops.TRACING_WINDOW).

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.stop_signal ADD COLUMN IF NOT EXISTS phase_entry date;
COMMENT ON COLUMN preclin.stop_signal.phase_entry IS 'Date the program entered the phase it stopped in (report.section1.phase_rows).';
COMMIT;
