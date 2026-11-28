"""Polygenicity (#147): the GWAS Catalog study table (pipeline.gwas_catalog)."""
import pandas as pd

from pipeline.gwas_catalog import eur_share, loci_catalog, parse_sample_size, study_frame

EFO_RA = "http://www.ebi.ac.uk/efo/EFO_0000685"


def test_cases_and_controls_sum_over_groups():
    assert parse_sample_size("2,080 European ancestry cases, 6,435 European ancestry controls") == (2080, 6435)
    assert parse_sample_size("25,662 British ancestry cases, 17,928 British ancestry controls, 1,000 Han Chinese "
                             "ancestry cases, 2,000 Han Chinese ancestry controls") == (26662, 19928)


def test_at_least_and_individuals_do_not_give_cases():
    assert parse_sample_size("at least 3,569 European ancestry cases, at least 19,085 European ancestry controls") == (3569, 19085)
    assert parse_sample_size("12,000 European ancestry individuals") == (None, None)   # Review Focus 1
    assert parse_sample_size(None) == (None, None)


def test_eur_share_is_initial_stage_european_over_total():
    a = pd.DataFrame({"STUDY ACCESSION": ["G1"] * 3, "STAGE": ["initial", "initial", "replication"],
                      "NUMBER OF INDIVIDUALS": [900, 100, 5000],
                      "BROAD ANCESTRAL CATEGORY": ["European", "East Asian", "European"]})
    assert eur_share(a, "G1") == 0.9
    assert eur_share(a, "G2") is None


class Lookup:
    def to_mondo(self, uri):
        return {EFO_RA: {"MONDO:0008383"}}.get(uri, set())


def test_loci_merge_within_500kb_and_mhc_as_one():
    assoc = pd.DataFrame({"STUDY ACCESSION": ["G1"] * 6, "MAPPED_TRAIT_URI": [EFO_RA] * 6,
                          "CHR_ID": ["1", "1", "1", "6", "6", "2"],
                          "CHR_POS": ["1000000", "1400000", "2000000", "26000000", "33000000", "x"],
                          "P-VALUE": ["1e-9", "1e-9", "1e-9", "1e-9", "1e-9", "1e-9"]})
    assert loci_catalog(assoc, {"MONDO:0008383"}, Lookup()) == (1, 5, 3)   # chr1 two loci; chr6 MHC one; "x" dropped


def test_loci_ignore_other_traits_and_weak_associations():
    assoc = pd.DataFrame({"STUDY ACCESSION": ["G1", "G2", "G3"], "MAPPED_TRAIT_URI": [EFO_RA, "http://x/EFO_1", EFO_RA],
                          "CHR_ID": ["1", "1", "3"], "CHR_POS": ["1000000", "9000000", "5000000"],
                          "P-VALUE": ["1e-9", "1e-9", "1e-6"]})
    assert loci_catalog(assoc, {"MONDO:0008383"}, Lookup()) == (2, 1, 1)   # G3 counts as a study, not an association


def test_study_frame_maps_every_uri_and_keeps_unmapped_as_empty():
    s = pd.DataFrame({"STUDY ACCESSION": ["G1", "G2"], "PUBMED ID": ["1", "2"], "DATE": ["2020-01-01", "2021-02-03"],
                      "DISEASE/TRAIT": ["RA", "Height"],
                      "MAPPED_TRAIT_URI": [f"{EFO_RA}, http://purl.obolibrary.org/obo/OBA_1", "http://x/EFO_2"],
                      "INITIAL SAMPLE SIZE": ["10 European ancestry cases, 20 European ancestry controls", "5 individuals"],
                      "ASSOCIATION COUNT": [3, 0], "SUMMARY STATS LOCATION": ["NA", "NA"]})
    a = pd.DataFrame({"STUDY ACCESSION": ["G1"], "STAGE": ["initial"], "NUMBER OF INDIVIDUALS": [30],
                      "BROAD ANCESTRAL CATEGORY": ["European"]})
    f = study_frame(s, a, Lookup(), {"G1": "./GCST1/harmonised/1-G1-EFO_0000685.h.tsv.gz"})
    assert list(f.mapped_trait_uris[0]) == [EFO_RA, "http://purl.obolibrary.org/obo/OBA_1"]
    assert f.mondo_ids[0] == ["MONDO:0008383"] and (f.cases[0], f.controls[0], f.eur_share[0]) == (10, 20, 1.0)
    assert f.sumstats_path[0] == "GCST1/harmonised/1-G1-EFO_0000685.h.tsv.gz"
    assert f.mondo_ids[1] == [] and pd.isna(f.cases[1]) and pd.isna(f.eur_share[1]) and f.sumstats_path[1] is None
    assert str(f.published[0]) == "2020-01-01"


def test_a_bare_comma_before_cases_is_not_a_number():
    assert parse_sample_size("500 cases, 600 controls, cases and controls of European ancestry") == (500, 600)


def test_platform_snps_reads_the_bracketed_count():
    from pipeline.gwas_catalog import platform_snps
    assert platform_snps("Illumina [~2,500,000] (imputed)") == 2_500_000
    assert platform_snps("Affymetrix, Illumina [130,000]") == 130_000
    assert platform_snps("Illumina [~ 10,500,000 (imputed)]; Affymetrix [550,000]") == 10_500_000
    assert platform_snps("NR") is None and platform_snps(None) is None


def test_reload_refuses_to_delete_ldsc_runs_without_force():
    """A Catalog reload deletes every LDSC run and the disease profile with it; on the shared database that is two
    days of runs and the registered profile, so it refuses unless forced."""
    import pytest
    from pipeline import gwas_catalog
    gwas_catalog.reload_allowed(0, force=False)
    gwas_catalog.reload_allowed(229, force=True)
    with pytest.raises(SystemExit):
        gwas_catalog.reload_allowed(229, force=False)
