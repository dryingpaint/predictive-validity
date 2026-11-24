-- FAERS counts are keyed by the openFDA search that produced them, and a drug whose UNIIs find no reports is searched
-- by its name. Comments only.

BEGIN;
COMMENT ON TABLE preclin.faers_year_count IS
    'FAERS reports by the year the FDA received them (openFDA drug/event, receivedate), for one search: every report (all), the reports naming a drug (drug), naming a reaction (reaction), or both (pair). A drug is searched by the UNIIs of its entity and their salts and forms (preclin.unii_parent); when they find no reports (a drug openFDA''s labels no longer list, such as a withdrawn one), by its name as a generic name or as the product name a report gives. Years with no reports have no row; a search with no reports at all has one row of year 0 and 0 reports.';
COMMENT ON COLUMN preclin.faers_year_count.subject_key IS 'The search: empty for all, the reaction for reaction, the openFDA search text for drug and pair.';
COMMIT;
