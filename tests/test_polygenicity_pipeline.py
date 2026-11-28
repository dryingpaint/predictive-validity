"""Polygenicity (#147): the disease-profile pipeline (pipeline.polygenicity) and its tables."""
import pytest

from pipeline import llm


@pytest.mark.db
def test_migration_156_tables_exist():
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT table_name FROM information_schema.tables WHERE table_schema = 'preclin'
                       AND table_name IN ('gwas_catalog_study', 'ldsc_run', 'gbd_prevalence', 'disease_polygenicity')""")
        assert {r[0] for r in cur.fetchall()} == {"gwas_catalog_study", "ldsc_run", "gbd_prevalence",
                                                   "disease_polygenicity"}


import numpy as np
import pandas as pd

from pipeline.polygenicity import choose_study, gene_counts, k_for, liability_h2


def test_liability_conversion_matches_the_standard_formula():
    assert abs(liability_h2(0.05, 0.5, 0.01) - 0.0276) < 5e-4    # K^2(1-K)^2 / (P(1-P) phi(t)^2), t = Phi^-1(1-K)


def studies(rows):
    return pd.DataFrame(rows, columns=["gcst", "mondo_ids", "mapped_trait_uris", "sumstats_path", "cases", "controls",
                                       "eur_share", "platform_snps"], dtype=object)


def test_choose_largest_european_exact_single_trait_study():
    s = studies([("G1", ["M1"], ["u1"], "p", 1000, 1000, 1.0, 2_500_000), ("G2", ["M1"], ["u1"], "p", 5000, 5000, 1.0, 2_500_000),
                 ("G3", ["M1"], ["u1"], "p", 9000, 9000, 0.5, 2_500_000),
                 ("G4", ["M1", "M9"], ["u1", "u2"], "p", 9000, 9000, 1.0, 2_500_000)])
    assert choose_study(s, "M1", {"M1", "M2"}) == ("G2", "exact", "ok")   # G3 not European, G4 two traits (Review Focus 3)


def test_descendant_fallback_and_statuses():
    s = studies([("G5", ["M2"], ["u2"], "p", 100, 100, 1.0, 2_500_000)])
    assert choose_study(s, "M1", {"M1", "M2"}) == ("G5", "descendant", "ok")
    assert choose_study(s.assign(sumstats_path=None), "M1", {"M1", "M2"}) == (None, None, "no_sumstats")
    assert choose_study(s.assign(cases=None), "M1", {"M1", "M2"}) == (None, None, "no_case_control")
    assert choose_study(s.assign(eur_share=0.8), "M1", {"M1", "M2"}) == (None, None, "not_european")
    assert choose_study(s.assign(platform_snps=130_000), "M1", {"M1", "M2"}) == (None, None, "targeted_array")
    assert choose_study(s.assign(platform_snps=None), "M1", {"M1", "M2"}) == ("G5", "descendant", "ok")  # unknown platform kept
    assert choose_study(s, "M7", {"M7"}) == (None, None, "no_study")


def test_k_prefers_gbd_then_panukb_then_none():   # Review Focus 4
    gbd_map = {"M1": ("exact", 627), "M2": ("none", None), "M3": ("exact", 1)}
    gbd = {627: 226.6, 1: 60000.0}
    ukb = pd.DataFrame({"phenocode": ["M06", "L40"], "n_cases_EUR": [5000, 50], "n_controls_EUR": [415000, 420000]})
    assert k_for("M1", gbd_map, gbd, {"M06"}, ukb) == (0.002266, "gbd", None, False)
    assert k_for("M2", gbd_map, gbd, {"M06"}, ukb) == (5000 / 420000, "panukb", "M06", False)
    assert k_for("M2", gbd_map, gbd, {"M060"}, ukb) == (5000 / 420000, "panukb", "M06", True)   # through the parent code
    assert k_for("M2", gbd_map, gbd, {"L40"}, ukb) == (None, "none", None, False)        # fewer than 100 cases
    assert k_for("M3", gbd_map, gbd, set(), ukb) == (None, "none", None, False)          # K >= 0.5


class StubMondo:
    def __init__(self, close):
        self.close = close

    def matches(self, evidence, program):
        c = (evidence, program) in self.close
        return c or evidence == program, c


def test_gene_counts_use_members_and_lin_neighbours_and_family():
    ev = pd.DataFrame({"target_ensembl": ["g1", "g2", "g2", "g3", "g4"], "mondo_id": ["M1", "M2", "M1", "M8", "M9"],
                       "datasource": ["gwas_credible_sets", "gwas_credible_sets", "orphanet", "clingen", "gene_burden"]})
    gwas, mend, form = gene_counts("M1", StubMondo({("M8", "M1")}), {"M1", "M2"}, ev)
    assert (gwas, mend, form) == (2, 2, True)      # g3 via Lin neighbour M8; M9 unrelated


def test_score_fields_keep_h2_liab_for_low_z_and_score_only_when_ok():
    from pipeline.polygenicity import score_fields
    low = score_fields(h2_obs=0.10, h2_obs_se=0.05, n_snps=1_000_000, loci=3, p=0.5, k=0.01)
    assert low["ldsc_status"] == "low_z" and low["h2_liab"] is not None and low["score"] is None
    ok = score_fields(h2_obs=0.20, h2_obs_se=0.02, n_snps=1_000_000, loci=10, p=0.5, k=0.01)
    assert ok["ldsc_status"] == "ok" and ok["score"] == pytest.approx(10 / ok["h2_liab"])
    assert ok["log10_score"] == pytest.approx(np.log10(ok["score"]))
    none = score_fields(h2_obs=0.20, h2_obs_se=0.02, n_snps=1_000_000, loci=0, p=0.5, k=0.01)
    assert none["ldsc_status"] == "zero_loci" and none["score"] is None and none["log10_score"] is None
    assert none["h2_liab"] == pytest.approx(ok["h2_liab"])   # the no-score group keeps its heritability
    assert score_fields(0.20, 0.02, 50_000, 10, 0.5, 0.01)["ldsc_status"] == "targeted_array"
    nok = score_fields(0.20, 0.02, 1_000_000, 10, 0.5, None)
    assert nok["ldsc_status"] == "no_k" and nok["h2_liab"] is None
    assert score_fields(0.90, 0.02, 1_000_000, 10, 0.5, 0.2)["ldsc_status"] == "out_of_bounds"


def test_choose_study_skips_excluded_studies_and_breaks_ties_on_accession():
    from pipeline.polygenicity import exome_studies
    s = studies([("G1", ["M1"], ["u1"], "p", 1000, 1000, 1.0, 2_500_000), ("G2", ["M1"], ["u1"], "p", 5000, 5000, 1.0, 2_500_000),
                 ("G0", ["M1"], ["u1"], "p", 5000, 5000, 1.0, 2_500_000)])
    assert choose_study(s, "M1", {"M1"}) == ("G0", "exact", "ok")                      # G0 and G2 tie on n_eff: the accession decides
    assert choose_study(s, "M1", {"M1"}, exclude={"G0", "G2"}) == ("G1", "exact", "ok")
    assert choose_study(s, "M1", {"M1"}, exclude={"G0", "G1", "G2"}) == (None, None, "targeted_array")
    cat = pd.DataFrame({"STUDY ACCESSION": ["G1", "G2", "G3", "G4"],
                        "GENOTYPING TECHNOLOGY": ["Genome-wide genotyping array", "Genome-wide genotyping array, Exome-wide sequencing",
                                                  "Genome-wide sequencing, Exome-wide sequencing", "Exome genotyping array"]})
    assert exome_studies(cat) == {"G2", "G4"}


def test_panukb_k_is_bounded_and_failed_runs_keep_their_reason():
    from pipeline.polygenicity import failed_status
    ukb = pd.DataFrame({"phenocode": ["X1"], "n_cases_EUR": [600], "n_controls_EUR": [400]})
    assert k_for("M1", {}, {}, {"X1"}, ukb) == (None, "none", None, False)
    assert failed_status("no_effect") == "no_effect" and failed_status("fetch_failed") == "run_failed" and failed_status(None) == "run_failed"


def test_evidence_frame_reads_every_gene_of_the_full_association_file(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from pipeline.polygenicity import evidence_frame
    pq.write_table(pa.table({"diseaseId": ["EFO_1", "EFO_1", "EFO_2", "EFO_3"], "targetId": ["g1", "g2", "g2", "g9"],
                             "aggregationValue": ["gwas_credible_sets", "orphanet", "gwas_credible_sets", "chembl"]}),
                   tmp_path / "part-0.parquet")
    diseases = pd.DataFrame({"disease_id": ["EFO:1", "EFO:2", "EFO:3"], "mondo_id": ["M1", "M2", "M3"]})
    ev = evidence_frame(str(tmp_path), diseases)
    assert set(ev.columns) == {"target_ensembl", "mondo_id", "datasource"}
    assert sorted(map(tuple, ev.values.tolist())) == [("g1", "M1", "gwas_credible_sets"), ("g2", "M1", "orphanet"),
                                                      ("g2", "M2", "gwas_credible_sets")]   # chembl is not a genetic source


def test_association_digest_is_deterministic_and_sensitive_to_the_files(tmp_path):
    from pipeline.polygenicity import association_digest
    (tmp_path / "part-0.parquet").write_bytes(b"a")
    (tmp_path / "part-1.parquet").write_bytes(b"b")
    d1 = association_digest(str(tmp_path))
    assert d1 == association_digest(str(tmp_path)) and len(d1) == 64
    (tmp_path / "part-1.parquet").write_bytes(b"c")
    assert association_digest(str(tmp_path)) != d1


def test_panukb_h2_keeps_european_icd10_rows_that_pass_qc(tmp_path, monkeypatch):
    """The real h2 manifest names the ancestry column `pop` (and pandas has a .pop method, so it is read by key)."""
    import gzip
    from pipeline import polygenicity
    rows = ["trait_type\tphenocode\tpop\tqcflags.pass_all\testimates.final.h2_liability\testimates.final.h2_z",
            "icd10\tM06\tEUR\tTrue\t0.12\t6.5",
            "icd10\tM06\tAFR\tTrue\t0.30\t1.2",
            "icd10\tL40\tEUR\tFalse\t0.20\t2.0",
            "phecode\t714\tEUR\tTrue\t0.15\t7.0"]
    with gzip.open(tmp_path / "h2_manifest.tsv.bgz", "wt") as f:
        f.write("\n".join(rows) + "\n")
    monkeypatch.setattr(polygenicity, "PANUKB", str(tmp_path))
    h = polygenicity.panukb_h2()
    assert h.values.tolist() == [["M06", 0.12, 6.5]]


def test_excluded_runs_skips_studies_with_too_few_merged_snps_or_no_usable_effect():
    """A run that merged fewer than MIN_PLATFORM_SNPS SNPs (a targeted array the Catalog lists as genome-wide) or that
    found no usable autosomal effect (an X-only study, a p-value-only file) excludes its study so the next one is chosen."""
    from pipeline import polygenicity
    runs = pd.DataFrame({"gcst": ["GCST003044", "GCST90444373", "GCST90027158", "GCST000001"],
                         "n_snps": [48_002, None, 1_168_849, None],
                         "status": ["ok", "no_effect", "ok", "fetch_failed"]})
    assert polygenicity.excluded_runs(runs) == {"GCST003044", "GCST90444373"}


def test_expand_icd_range_lists_every_three_character_code():
    from pipeline import polygenicity
    assert polygenicity.expand_icd("I10-I16") == {"I10", "I11", "I12", "I13", "I14", "I15", "I16"}
    assert polygenicity.expand_icd("K50") == {"K50"} and polygenicity.expand_icd("E109") == {"E109"}
    assert len(polygenicity.expand_icd("D50-D89")) == 40


def test_own_and_descendant_codes_keep_the_diseases_own_codes_apart():
    from pipeline import polygenicity
    xrefs = pd.DataFrame({"term_id": ["M", "M", "C"], "code": ["I10-I16", "I15", "H40"]})
    own, desc = polygenicity.own_and_descendant_codes("M", {"M", "C"}, xrefs)
    assert own == {"I10", "I11", "I12", "I13", "I14", "I15", "I16"} and desc == {"H40"}


def test_k_for_prefers_the_diseases_own_icd_code_over_a_descendants_code_with_more_cases():
    """Review of 2026-11-25: hypertensive disorder took K from glaucoma's H40, a descendant's code with more Pan-UKB
    cases, because its own codes were a range the cross-reference parser did not expand. Own codes come first."""
    from pipeline import polygenicity
    ukb = pd.DataFrame({"phenocode": ["I10", "H40"], "n_cases_EUR": [20_000, 50_000], "n_controls_EUR": [380_000, 350_000]})
    k, source, code, via_parent = polygenicity.k_for("M", {}, {}, {"I10"}, ukb, descendant_codes={"H40"})
    assert (source, code, via_parent) == ("panukb", "I10", False) and abs(k - 0.05) < 1e-9
    k, source, code, via_parent = polygenicity.k_for("M", {}, {}, set(), ukb, descendant_codes={"H40"})
    assert (source, code, via_parent) == ("panukb", "H40", False)   # a descendant's code is not "through the parent" (review of 2026-11-27)
    k, source, code, via_parent = polygenicity.k_for("M", {}, {}, {"I109"}, ukb, descendant_codes={"H40"})
    assert (code, via_parent) == ("I10", True)


def test_k_for_registered_reproduces_the_rule_the_profile_was_built_with():
    """The registered profile (gate of 2026-11-25) took the Pan-UKB code with most cases among the disease's own codes,
    its descendants' codes and their three-character parents, in one pool, ranges unexpanded, and applied the 100-case
    floor to that one row. It stands as fixed, so a rebuild reproduces it beside the corrected rule."""
    from pipeline import polygenicity
    ukb = pd.DataFrame({"phenocode": ["I10", "H40", "E78"], "n_cases_EUR": [20_000, 50_000, 50],
                        "n_controls_EUR": [380_000, 350_000, 400_000]})
    # the own range stays a string no phenocode matches; the descendant's H40 has more cases than the range's parent I10
    assert polygenicity.k_for_registered("M", {}, {}, {"I10-I16", "H40"}, ukb) == (50_000 / 400_000, "panukb", "H40", False)
    assert polygenicity.k_for_registered("M", {}, {}, {"E78"}, ukb) == (None, "none", None, False)   # top row under the floor
    assert polygenicity.k_for_registered("M", {}, {}, {"I109"}, ukb) == (20_000 / 400_000, "panukb", "I10", True)
    assert polygenicity.k_for_registered("M", {"M": ("exact", 1)}, {1: 500.0}, {"H40"}, ukb) == (0.005, "gbd", None, False)


def test_corrected_k_fields_rescore_the_stored_run_under_the_corrected_prevalence():
    """The corrected-K sensitivity (Melissa's decision of 2026-11-26): the K-dependent columns recomputed from the
    stored run under the own-code-first K, the registered columns untouched; a disease whose run gave no estimate
    keeps its status; one that had no K and gains one is scored."""
    from pipeline import polygenicity
    row = {"ldsc_status": "ok", "h2_obs": 0.05, "h2_obs_se": 0.005, "loci": 10, "n_cases": 10_000, "n_controls": 90_000}
    out = polygenicity.corrected_k_fields(row, n_snps=1_100_000, k=0.01)
    assert out["ldsc_status_k_corrected"] == "ok"
    assert abs(out["h2_liab_k_corrected"] - polygenicity.liability_h2(0.05, 0.1, 0.01)) < 1e-12
    assert abs(out["score_k_corrected"] - 10 / out["h2_liab_k_corrected"]) < 1e-9
    assert polygenicity.corrected_k_fields({**row, "ldsc_status": "no_k"}, n_snps=1_100_000, k=None) == \
        {"h2_liab_k_corrected": None, "score_k_corrected": None, "ldsc_status_k_corrected": "no_k"}
    assert polygenicity.corrected_k_fields({**row, "ldsc_status": "no_k"}, n_snps=1_100_000, k=0.01)["ldsc_status_k_corrected"] == "ok"
    none = {"ldsc_status": "no_study", "h2_obs": None, "h2_obs_se": None, "loci": None, "n_cases": None, "n_controls": None}
    assert polygenicity.corrected_k_fields(none, n_snps=None, k=0.01) == \
        {"h2_liab_k_corrected": None, "score_k_corrected": None, "ldsc_status_k_corrected": "no_study"}


def test_expand_icd9_ranges_and_phecode_matching():
    """Rule v3 (2026-11-27): MONDO's ICD-9 cross-references reach Pan-UKB's phecodes, which are numbered from ICD-9:
    the exact string when it is a phecode, else its integer part."""
    from pipeline import polygenicity
    assert polygenicity.expand_icd9("401-405") == {"401", "402", "403", "404", "405"}
    assert polygenicity.expand_icd9("571.6") == {"571.6"} and polygenicity.expand_icd9("428") == {"428"}
    phecodes = {"401", "401.1", "571.6", "242", "242.1", "696"}
    assert polygenicity.phecode_matches({"401.9"}, phecodes) == {"401"}
    assert polygenicity.phecode_matches({"571.6"}, phecodes) == {"571.6"}
    assert polygenicity.phecode_matches({"242.0", "696.0", "999.9"}, phecodes) == {"242", "696"}


def test_is_category_term():
    """A MONDO term that stands for a chapter (eye disorder, cardiovascular disorder) gets no K under v3 rather than one
    member's: its own cross-reference is a range of ten or more codes, or it has more than thirty descendant codes."""
    from pipeline import polygenicity
    assert polygenicity.is_category({"I00-I99"}, set(), 175) is True
    assert polygenicity.is_category(set(), {"800-999"}, 9) is True
    assert polygenicity.is_category(set(), set(), 241) is True
    assert polygenicity.is_category({"I10-I16"}, {"401-405"}, 12) is False
    assert polygenicity.is_category({"K743"}, {"571.6"}, 0) is False


def test_k_for_v3_takes_own_code_or_phecode_then_gbd_then_pooled_descendants():
    from pipeline import polygenicity
    ukb = pd.DataFrame({"phenocode": ["I12", "I48", "I46", "K74", "L40"], "n_cases_EUR": [1_608, 19_218, 1_349, 1_145, 2_868],
                        "n_controls_EUR": [418_923, 401_313, 419_182, 419_386, 417_663]})
    phe = pd.DataFrame({"phenocode": ["401", "571.6", "427"], "n_cases_EUR": [94_311, 314, 31_341], "n_controls_EUR": [325_488, 408_402, 384_657]})
    own10 = {f"I{i}" for i in range(10, 17)}
    # hypertensive disorder: I10 is not in the ICD-10 manifest; the own phecode 401 (through ICD-9 401-405) beats own I12
    k, source, code, via = polygenicity.k_for_v3("H", {}, {}, own10, {"401", "402", "403", "404", "405"}, set(), set(), ukb, phe)
    assert (source, code, via) == ("panukb", "401", False) and abs(k - 94_311 / (94_311 + 325_488)) < 1e-12
    # PBC: own K74.3 is four characters, so K74 is only a parent; the exact phecode 571.6 (314 cases) comes first
    assert polygenicity.k_for_v3("P", {}, {}, {"K743"}, {"571.6"}, set(), set(), ukb, phe)[2] == "571.6"
    # GBD beats a Pan-UKB pick under 1,000 cases; a pick of 1,000 or more beats GBD
    assert polygenicity.k_for_v3("G", {"G": ("exact", 1)}, {1: 500.0}, set(), {"571.6"}, set(), set(), ukb, phe) == (0.005, "gbd", None, False)
    assert polygenicity.k_for_v3("G", {"G": ("exact", 1)}, {1: 500.0}, {"K74"}, set(), set(), set(), ukb, phe)[1:3] == ("panukb", "K74")
    # cardiac rhythm disease: no own code, no GBD; the descendants' codes and their parents are one pool, so I48 beats I46
    assert polygenicity.k_for_v3("C", {}, {}, set(), set(), {"I46", "I480"}, set(), ukb, phe)[2] == "I48"
    # a parent of an own four-character code is "via parent"; a category term gets nothing
    assert polygenicity.k_for_v3("S", {}, {}, {"L405"}, set(), set(), set(), ukb, phe)[2:] == ("L40", True)
    assert polygenicity.k_for_v3("X", {}, {}, set(), set(), {"I46"}, set(), ukb, phe, category=True) == (None, "none", None, False)
