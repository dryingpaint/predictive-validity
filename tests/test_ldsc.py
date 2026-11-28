"""Polygenicity (#147): LDSC heritability, clumping and heritability concentration per study (pipeline.ldsc)."""
import numpy as np
import pandas as pd

from pipeline.ldsc import concentration, loci, munge_input, parse_clumped, parse_h2_log


def test_munge_input_uses_beta_then_log_odds_ratio_and_hapmap_columns():
    h = pd.DataFrame({"hm_rsid": ["rs1", "rs2", "rs3"], "hm_effect_allele": ["A", "C", "G"],
                      "hm_other_allele": ["G", "T", "A"], "hm_beta": [0.1, np.nan, np.nan],
                      "hm_odds_ratio": [np.nan, 1.5, np.nan], "p_value": [1e-3, 1e-9, 0.5]})
    m = munge_input(h)
    assert list(m.columns) == ["SNP", "A1", "A2", "BETA", "P"] and len(m) == 2
    assert abs(m.BETA.iloc[1] - np.log(1.5)) < 1e-9


def test_munge_input_is_none_without_any_effect():   # Review Focus 2
    h = pd.DataFrame({"hm_rsid": ["rs1"], "hm_effect_allele": ["A"], "hm_other_allele": ["G"], "hm_beta": [np.nan],
                      "hm_odds_ratio": [np.nan], "p_value": [0.1]})
    assert munge_input(h) is None


LOG = """After merging with regression SNP LD, 1150000 SNPs remain.
Total Observed scale h2: 0.1234 (0.0123)
Lambda GC: 1.0912
Mean Chi^2: 1.1402
Intercept: 1.0123 (0.0089)
Ratio: 0.0877 (0.0634)
"""


def test_parse_h2_log():
    assert parse_h2_log(LOG) == {"h2_obs": 0.1234, "h2_obs_se": 0.0123, "intercept": 1.0123, "ratio": 0.0877,
                                 "lambda_gc": 1.0912, "mean_chi2": 1.1402, "n_snps": 1150000}


def test_parse_h2_log_with_a_ratio_note():
    text = LOG.replace("Ratio: 0.0877 (0.0634)", "Ratio < 0 (usually indicates GC correction).")
    assert parse_h2_log(text)["ratio"] is None and parse_h2_log(text)["h2_obs"] == 0.1234


CLUMPED = """ CHR    F         SNP         BP        P    TOTAL   NSIG    S05    S01   S001  S0001    SP2
   1    1      rs10    1000000  1.0e-12       10      0      0      0      0     10 rs11(1),rs12(1)
   6    1      rs60   26000000  1.0e-20       50      0      0      0      0     50 NONE
   6    1      rs61   33000000  1.0e-09        3      0      0      0      0      3 NONE

"""


def test_parse_clumped_and_mhc_counts_once():
    c = parse_clumped(CLUMPED)
    assert list(c.SNP) == ["rs10", "rs60", "rs61"] and list(c.CHR) == [1, 6, 6] and loci(c) == 2
    assert loci(parse_clumped("")) == 0


def test_concentration_is_top10_per_snp_h2_over_observed_h2():
    z2 = pd.Series([101.0, 51.0, 26.0])   # (z^2 - 1)/N = 0.1, 0.05, 0.025 -> 0.175 over 0.5
    share, top = concentration(z2, 1000, 0.5)
    assert abs(share - 0.35) < 1e-9 and len(top) == 3
    assert concentration(z2, 1000, 0.0) == (None, [])
    share12, top12 = concentration(pd.Series([11.0] * 12), 1000, 1.0)
    assert len(top12) == 10 and abs(share12 - 0.1) < 1e-9


def test_munge_input_accepts_the_plain_harmonised_columns():
    """Newer harmonised files (GWAS-SSF) have rsid, effect_allele, beta... without the hm_ prefix."""
    h = pd.DataFrame({"rsid": ["rs1", "rs2"], "effect_allele": ["A", "C"], "other_allele": ["G", "T"],
                      "beta": [0.1, np.nan], "odds_ratio": [np.nan, 2.0], "p_value": [1e-3, 1e-9]})
    m = munge_input(h)
    assert list(m.SNP) == ["rs1", "rs2"] and abs(m.BETA.iloc[1] - np.log(2.0)) < 1e-9


def test_munge_input_without_an_effect_column_is_none():
    h = pd.DataFrame({"rsid": ["rs1"], "effect_allele": ["A"], "other_allele": ["G"], "p_value": [1e-3]})
    assert munge_input(h) is None


def test_read_sumstats_keeps_the_column_map_across_chunks(tmp_path, monkeypatch):   # the second chunk reused m
    import gzip
    from pipeline import ldsc
    rows = ["hm_rsid\thm_effect_allele\thm_other_allele\thm_beta\tp_value"]
    rows += [f"rs{i}\tA\tG\t0.0{i}\t0.{i}" for i in range(1, 8)]
    path = tmp_path / "x.h.tsv.gz"
    with gzip.open(path, "wt") as f:
        f.write("\n".join(rows) + "\n")
    monkeypatch.setattr(ldsc, "CHUNK", 2)
    out = ldsc.read_sumstats(str(path), {"rs1", "rs3", "rs6", "rs7"})
    assert sorted(out.SNP) == ["rs1", "rs3", "rs6", "rs7"]
    monkeypatch.setattr(ldsc, "CHUNK", 3)   # a first chunk with no kept SNP
    out = ldsc.read_sumstats(str(path), {"rs5", "rs7"})
    assert sorted(out.SNP) == ["rs5", "rs7"]


def test_munge_input_reads_an_OR_column_and_floors_tiny_p():   # GCST007228; p below 1e-308 became 0 and was dropped
    h = pd.DataFrame({"rsid": ["rs1", "rs2"], "effect_allele": ["A", "C"], "other_allele": ["G", "T"],
                      "OR": ["2.0", "0.5"], "p_value": ["1e-350", "0.5"]})
    out = munge_input(h)
    assert list(out.SNP) == ["rs1", "rs2"] and out.BETA.iloc[0] == np.log(2.0)
    assert out.P.iloc[0] == 1e-300 and out.P.iloc[1] == 0.5


def test_concentration_collapses_the_mhc_to_its_strongest_snp():
    from pipeline.ldsc import MHC
    index = pd.DataFrame({"SNP": ["a", "b", "c", "d"], "CHR": [MHC[0], MHC[0], MHC[0], 1], "BP": [26_000_000, 27_000_000, 30_000_000, 100]})
    z2 = pd.Series({"a": 50.0, "b": 80.0, "c": 60.0, "d": 40.0})
    share, top = concentration(z2, 1000, 0.1, index)
    assert [r["snp"] for r in top] == ["b", "d"] and share == ((80 - 1) / 1000 + (40 - 1) / 1000) / 0.1


def test_extra_loci_adds_significant_snps_the_panel_lacks_when_they_are_distant():
    from pipeline.ldsc import extra_loci
    index = pd.DataFrame({"SNP": ["i1"], "CHR": [1], "BP": [1_000_000], "P": [1e-10]})
    missing = pd.DataFrame({"SNP": ["m1", "m2", "m3", "m4"], "CHR": [1, 1, 1, 2], "BP": [1_500_000, 3_000_000, 3_200_000, 100],
                            "P": [1e-9, 1e-12, 1e-9, 1e-8 / 2]})
    added = extra_loci(missing, index)
    assert list(added.SNP) == ["m2", "m4"]   # m1 within 1 Mb of i1, m3 within 1 Mb of m2


def test_trim_log_keeps_the_head_and_the_tail():
    from pipeline.ldsc import trim_log
    text = "H" * 100 + "M" * 100 + "T" * 100
    out = trim_log(text, head=50, tail=50)
    assert out.startswith("H" * 50) and out.endswith("T" * 50) and "..." in out and trim_log("short") == "short"
