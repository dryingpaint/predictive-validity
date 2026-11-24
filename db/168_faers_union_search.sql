-- A drug's FAERS search is the union of its UNIIs and its name: a salt missing from preclin.unii_parent, or a drug
-- openFDA's labels no longer list, is found by name. Comments only.

BEGIN;
COMMENT ON TABLE preclin.faers_year_count IS
    'FAERS reports by the year the FDA received them (openFDA drug/event, receivedate), for one search: every report (all), the reports naming a drug (drug), naming a reaction (reaction), or both (pair). A report names a drug when it gives one of the UNIIs of its entity and their salts and forms (preclin.unii_parent), or the drug''s name as a generic name or as the product name. Years with no reports have no row; a search with no reports at all has one row of year 0 and 0 reports. Only the searches the current pairs use are kept.';
COMMIT;
