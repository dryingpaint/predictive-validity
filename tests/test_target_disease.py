from pipeline.target_disease import provisional_origin
from report.section3 import ABSENT


def test_the_earliest_evidence_before_entry_is_the_origin_and_the_next_distinct_one_secondary():
    assert provisional_origin({"expression": 2004, "gwas": 2010}, ABSENT, 2012) == \
        ("diseased_tissue", 2004, "human_genetics")


def test_evidence_from_the_year_of_entry_or_later_does_not_count():
    assert provisional_origin({"gwas": 2012, "mgi": 2015}, ABSENT, 2012) == ("unclear", None, None)


def test_an_approval_for_another_disease_is_an_origin_of_its_own():
    assert provisional_origin({"mgi": 2006}, 1998, 2010) == ("earlier_drug_other_disease", 1998, "mouse_genetics")


def test_within_one_year_genetics_comes_first_and_one_origin_appears_once():
    assert provisional_origin({"gwas": 2005, "mendelian": 2005, "impc": 2005}, ABSENT, 2009) == \
        ("human_genetics", 2005, "mouse_genetics")
