"""The per-disease genetic-architecture profile of issue #147 (preclin.disease_polygenicity).

    python -m pipeline.polygenicity load-gbd     # pipeline/data/gbd_2023_prevalence_2021.csv -> preclin.gbd_prevalence
    python -m pipeline.polygenicity choose       # candidate diseases and their LDSC study -> preclin.disease_polygenicity
    python -m pipeline.polygenicity build        # every column: the runs, K, the score, Open Targets, O'Connor, Pan-UKB
    python -m pipeline.polygenicity counts       # scored diseases and entries against the candidates and the 531/2,275 base
    python -m pipeline.polygenicity check-unit   # every disease in today's unit has a row (exit 1 otherwise)
    python -m pipeline.polygenicity drugged      # drugged_large_effect (migration 172)
    python -m pipeline.polygenicity k-corrected  # the corrected-K sensitivity columns (migration 178); registered columns untouched

Candidates: non-oncology, non-infectious diseases with a US-developed Phase 2 entry in 2008-2019 (the unit of #147,
counted on the programme build of the day; a disease the unit gains later is added by rerunning choose, ldsc and
build). For each, the LDSC study (choose_study): among the Catalog studies of the disease and its MONDO
descendants, those with public harmonised summary statistics, parsed cases and controls, a European initial sample
(at least 90%), a genome-wide platform (200,000 SNPs or more, or unstated) and a single mapped trait; the disease
itself before a descendant; the largest effective sample size 4 / (1/cases + 1/controls). The status names the
first filter that emptied the set.

K, the population prevalence for the liability scale: the GBD cause the disease maps to by hand
(pipeline/data/gbd_cause_mondo.csv, exact or broader), rate per 100,000 over 100,000, when under 0.5; else the
Pan-UK Biobank European case fraction of an ICD-10 code from MONDO's cross-references, at least 100 cases; else none,
and the disease has no score. Two rules choose the Pan-UKB code. The registered profile (gate of 2026-11-25) used
k_for_registered: the disease's own codes and its MONDO descendants' in one pool, ranges unexpanded, each with its
three-character parent, the code with most cases; the review of 2026-11-25 found this takes a descendant's unrelated
code for 30 of the 64 scored diseases with a Pan-UKB K. The registered columns (k, k_source, k_code, k_via_parent,
h2_liab, score, ldsc_status) stand as built and are rebuilt by that rule. The corrected rule, k_for, takes the
disease's own codes first (ranges expanded), then their parents, then the descendants' codes, then theirs; it fills
the *_k_corrected columns of migration 178 for the corrected-K sensitivity (Melissa's decision of 2026-11-26).
Liability h2 = h2_obs * K^2 (1-K)^2 / (P (1-P) phi(t)^2), t = Phi^-1(1-K), P the study's case fraction (Lee et al.
2011).
An estimate exists when the run is ok on a genome-wide set of SNPs, h2_z = h2_obs / se >= 4 (Pan-UKB's
significant_z threshold) and 0 < h2_liab <= 1; the score is loci / h2_liab.

Secondary measures: distinct genes with GWAS evidence and with rare or Mendelian evidence in preclin.ot_evidence
(Open Targets 26.09, the targets we hold) for the disease, a subtype or a disease at Lin >= 0.8
(report.disease_match.Mondo, the evidence lines' rule), the GWAS count per 10,000 cases of the largest GWAS;
whether a Mendelian form exists (a gene from Orphanet, ClinGen, Genomics England or Gene2Phenotype by the same
match: Melissa's registered sensitivity 4); O'Connor 2019's log10 effective number of associated SNPs (Table 1,
pipeline/data/oconnor2019_me.csv); Pan-UKB's liability h2 and z for the ICD-10 code (a check on our LDSC).

GBD file: Global Burden of Disease Study 2023 (GBD 2023) Results, prevalence, global, both sexes, all ages, 2021,
exported from https://vizhub.healthdata.org/gbd-results/ by Melissa and received 2026-11-23 (pipeline/data/
gbd_citation.txt). IHME publishes it under the free-of-charge non-commercial user agreement.
"""
from __future__ import annotations

import argparse
import re
import hashlib
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd
from psycopg2.extras import execute_values
from scipy.stats import norm, spearmanr

from pipeline import llm
from pipeline.gwas_catalog import RELEASE, loci_catalog, read_associations, read_studies, trait_lookup
from pipeline.opentargets import CACHE, SOURCE_URL, curie
from pipeline.opentargets import RELEASE as OT_RELEASE
from report import frame, section3
from report.disease_match import Mondo, mondo_tables
from report.evidence_lines import us
from report.section3 import FAMILY
from report.windows import SECTION1

DATA = os.path.join(llm.REPO, "pipeline", "data")
GBD_FILE = os.path.join(DATA, "gbd_2023_prevalence_2021.csv")
GBD_CITATION = os.path.join(DATA, "gbd_citation.txt")
GBD_MAP = os.path.join(DATA, "gbd_cause_mondo.csv")
ME_FILE = os.path.join(DATA, "oconnor2019_me.csv")
PANUKB = os.path.join(llm.REPO, ".cache", "panukb")
EXCLUDED_AREAS = ("oncology", "infectious_disease")
BASE = {"diseases": 531, "entries": 2275}  # Melissa's unit of 2026-11-23, before the #185 rebuild
EUR_MIN = 0.9
MIN_PLATFORM_SNPS = 200_000
Z_MIN = 4.0
K_MAX = 0.5
MIN_UKB_CASES = 100
MENDELIAN_SOURCES = ("orphanet", "clingen", "genomics_england", "gene2phenotype")
STATUS_ORDER = ("no_study", "no_sumstats", "no_case_control", "not_european", "targeted_array")


def candidates() -> pd.DataFrame:
    """The unit's diseases on the current programme build: mondo_id, label, bio_area, entries."""
    progs, trials, snap = frame.programs(), frame.program_trials(), frame.snapshot()
    e = section3.entries(progs, trials, snap, SECTION1).merge(progs[["program_id", "mondo_id"]], on="program_id", how="left")
    p2 = us(e)
    p2 = p2[p2.phase.eq(2) & p2.mondo_id.notna() & ~p2.bio_area.isin(EXCLUDED_AREAS)]
    out = p2.groupby(["mondo_id", "bio_area"]).size().reset_index(name="entries")
    labels = frame.query("SELECT term_id, label FROM preclin.ontology_term WHERE ontology = 'MONDO'")
    out["label"] = out.mondo_id.map(dict(zip(labels.term_id, labels.label)))
    return out[["mondo_id", "label", "bio_area", "entries"]].sort_values("mondo_id").reset_index(drop=True)


def descendants_table(ancestors: dict) -> dict[str, set[str]]:
    d: dict[str, set[str]] = defaultdict(set)
    for term, anc in ancestors.items():
        for a in anc:
            d[a].add(term)
    return d


def members(mondo_id: str, descendants: dict[str, set[str]]) -> set[str]:
    return {mondo_id} | set(descendants.get(mondo_id, ()))


def n_eff(cases, controls) -> float:
    return 4 / (1 / float(cases) + 1 / float(controls))


def exome_studies(catalog: pd.DataFrame) -> set[str]:
    """Catalog studies whose genotyping technology is exome-wide (sequencing or array) without genome-wide sequencing:
    their summary statistics hold exome variants only, which no platform count reveals."""
    tech = catalog["GENOTYPING TECHNOLOGY"].fillna("").str.lower()
    return set(catalog["STUDY ACCESSION"][tech.str.contains("exome") & ~tech.str.contains("genome-wide sequencing")])


def excluded_runs(runs: pd.DataFrame) -> set[str]:
    """Studies whose run (gcst, n_snps, status) disqualifies them: fewer than MIN_PLATFORM_SNPS merged SNPs (a targeted
    array the Catalog lists as genome-wide), or no usable autosomal effect (an X-only study, a p-value-only file)."""
    few = pd.to_numeric(runs.n_snps, errors="coerce") < MIN_PLATFORM_SNPS
    return set(runs.gcst[few.fillna(False) | runs.status.eq("no_effect")])


def excluded_studies() -> set[str]:
    """Studies choose_study must skip: exome-wide by technology, or already run and disqualified (excluded_runs)."""
    return exome_studies(read_studies()) | excluded_runs(frame.query("SELECT gcst, n_snps, status FROM preclin.ldsc_run"))


def choose_study(studies: pd.DataFrame, mondo_id: str, members: set[str],
                 exclude: set[str] = frozenset()) -> tuple[str | None, str | None, str]:
    """(gcst, exact or descendant, status) for a disease; None and the reason when no study qualifies. Ties on
    effective sample size break on the accession, so a rerun chooses the same study."""
    s = studies[studies.mondo_ids.map(lambda m: bool(set(m) & members))]
    if s.empty:
        return None, None, "no_study"
    filters = (("no_sumstats", lambda x: x.sumstats_path.notna()),
               ("no_case_control", lambda x: x.cases.notna() & x.controls.notna()),
               ("not_european", lambda x: x.eur_share.notna() & (pd.to_numeric(x.eur_share) >= EUR_MIN)),
               ("targeted_array", lambda x: (x.platform_snps.isna()
                | (pd.to_numeric(x.platform_snps, errors="coerce") >= MIN_PLATFORM_SNPS)) & ~x.gcst.isin(exclude)),
               ("no_study", lambda x: x.mapped_trait_uris.map(len) == 1))
    for status, keep in filters:
        s = s[keep(s).fillna(False).astype(bool)]
        if s.empty:
            return None, None, status
    exact = s[s.mondo_ids.map(lambda m: mondo_id in m)]
    pool, level = (exact, "exact") if len(exact) else (s, "descendant")
    best = pool.assign(n_eff=[n_eff(c, k) for c, k in zip(pool.cases, pool.controls)]) \
               .sort_values(["n_eff", "gcst"], ascending=[False, True])
    return best.gcst.iloc[0], level, "ok"


def liability_h2(h2_obs: float, p: float, k: float) -> float:
    """Observed-scale h2 of a case-control GWAS with case fraction p to the liability scale at prevalence k."""
    t = norm.isf(k)
    return h2_obs * k ** 2 * (1 - k) ** 2 / (p * (1 - p) * norm.pdf(t) ** 2)


def gbd_k(mondo_id: str, gbd_map: dict, gbd: dict) -> float | None:
    """The GBD cause's rate as a prevalence when the disease maps exactly or to a broader cause and 0 < K < K_MAX."""
    relation, cause = gbd_map.get(mondo_id, ("none", None))
    if relation in ("exact", "broader") and cause in gbd:
        k = gbd[cause] / 1e5
        if 0 < k < K_MAX:
            return k
    return None


def k_for(mondo_id: str, gbd_map: dict, gbd: dict, icd_codes: set[str], panukb: pd.DataFrame,
          descendant_codes: set[str] = frozenset()) -> tuple[float | None, str, str | None, bool]:
    """The corrected rule (review of 2026-11-25; the *_k_corrected columns). (K, source, Pan-UKB code, via parent):
    the GBD prevalence (gbd_k); else the Pan-UKB European case fraction by tiers: the disease's own ICD-10 codes, their
    three-character parents, then its MONDO descendants' codes, then their parents; within a tier the code with most
    cases among those with at least MIN_UKB_CASES; else none. Via parent is true only for the second tier (the parent
    of one of the disease's own codes), never for a descendant's code (review of 2026-11-27)."""
    k = gbd_k(mondo_id, gbd_map, gbd)
    if k is not None:
        return k, "gbd", None, False
    own, desc = set(icd_codes), set(descendant_codes)
    for tier, via_parent in ((own, False), (with_parents(own) - own, True), (desc, False), (with_parents(desc) - desc, False)):
        rows = panukb[panukb.phenocode.isin(tier) & (panukb.n_cases_EUR >= MIN_UKB_CASES)]
        if not len(rows):
            continue
        r = rows.sort_values("n_cases_EUR", ascending=False).iloc[0]
        k = float(r.n_cases_EUR / (r.n_cases_EUR + r.n_controls_EUR))
        if 0 < k < K_MAX:
            return k, "panukb", str(r.phenocode), via_parent
    return None, "none", None, False


def k_for_registered(mondo_id: str, gbd_map: dict, gbd: dict, icd_codes: set[str], panukb: pd.DataFrame) \
        -> tuple[float | None, str, str | None, bool]:
    """The rule the registered profile was built with (gate of 2026-11-25), kept so a rebuild reproduces the registered
    columns: the GBD prevalence (gbd_k); else, over the disease's own ICD-10 codes and its MONDO descendants' in one
    pool, ranges unexpanded, each with its three-character parent, the Pan-UKB row with most cases, kept when it has
    MIN_UKB_CASES and 0 < K < K_MAX. Via parent here means only that the code is not one of the pooled codes. The review
    of 2026-11-25 found this takes a descendant's unrelated code for 30 of the 64 scored diseases with a Pan-UKB K;
    k_for is the corrected rule."""
    k = gbd_k(mondo_id, gbd_map, gbd)
    if k is not None:
        return k, "gbd", None, False
    rows = panukb[panukb.phenocode.isin(with_parents(icd_codes))]
    if len(rows):
        r = rows.sort_values("n_cases_EUR", ascending=False).iloc[0]
        k = float(r.n_cases_EUR / (r.n_cases_EUR + r.n_controls_EUR))
        if r.n_cases_EUR >= MIN_UKB_CASES and 0 < k < K_MAX:
            return k, "panukb", str(r.phenocode), str(r.phenocode) not in icd_codes
    return None, "none", None, False


def with_parents(codes: set[str]) -> set[str]:
    """The codes with the three-character parent of each."""
    return {c for code in codes for c in (code, code[:3])}


ICD9_RANGE = re.compile(r"^(\d{3})-(\d{3})$")
MIN_UKB_CASES_OVER_GBD = 1_000   # v3: a Pan-UKB code of the disease itself with this many cases is taken before GBD
CATEGORY_RANGE = 10              # v3: an own cross-reference spanning this many codes marks a chapter-level term
CATEGORY_DESCENDANTS = 30        # v3: more descendant codes than this marks one too


def expand_icd9(code: str) -> set[str]:
    """An ICD-9 cross-reference as the codes it names: a range like 401-405 lists every three-digit code in it; a
    single code (with or without a decimal part) stays as it is."""
    m = ICD9_RANGE.match(code)
    if not m:
        return {code}
    return {str(i) for i in range(int(m.group(1)), int(m.group(2)) + 1)}


def phecode_matches(icd9_codes: set[str], phecodes: set[str]) -> set[str]:
    """The Pan-UKB phecodes the ICD-9 codes reach: the exact string when it is a phecode, else its integer part
    (phecodes are numbered from ICD-9: 401.9 unspecified essential hypertension reaches 401 Hypertension)."""
    out = set()
    for c in icd9_codes:
        if c in phecodes:
            out.add(c)
        elif c.split(".")[0] in phecodes:
            out.add(c.split(".")[0])
    return out


def is_category(own_icd10_raw: set[str], own_icd9_raw: set[str], n_descendant_codes: int) -> bool:
    """A MONDO term that stands for a chapter rather than a disease (eye disorder, cardiovascular disorder, injury):
    an own cross-reference that is a range of CATEGORY_RANGE codes or more, or more than CATEGORY_DESCENDANTS
    descendant codes. Under v3 such a term gets no K rather than one member's."""
    spans = [len(expand_icd(c)) for c in own_icd10_raw] + [len(expand_icd9(c)) for c in own_icd9_raw]
    return any(s >= CATEGORY_RANGE for s in spans) or n_descendant_codes > CATEGORY_DESCENDANTS


def _best(panukb: pd.DataFrame, codes: set[str], floor: int = MIN_UKB_CASES):
    rows = panukb[panukb.phenocode.isin(codes) & (panukb.n_cases_EUR >= floor)]
    if not len(rows):
        return None
    r = rows.sort_values(["n_cases_EUR", "phenocode"], ascending=[False, True]).iloc[0]
    k = float(r.n_cases_EUR / (r.n_cases_EUR + r.n_controls_EUR))
    return (k, str(r.phenocode), int(r.n_cases_EUR)) if 0 < k < K_MAX else None


def k_for_v3(mondo_id: str, gbd_map: dict, gbd: dict, own_icd10: set[str], own_icd9: set[str], desc_icd10: set[str],
             desc_icd9: set[str], panukb: pd.DataFrame, phecodes: pd.DataFrame, category: bool = False) \
        -> tuple[float | None, str, str | None, bool]:
    """Rule v3 (announced on #147, 2026-11-27, after the independent code check; one row per disease in
    preclin.disease_polygenicity_k). (K, source, code, via parent). A category term gets none. Otherwise, in order:
    the disease's own three-character ICD-10 codes (ranges expanded) and the phecodes its own ICD-9 codes reach, as one
    pool; then the three-character parents of its own ICD-10 codes (via parent); a pick with MIN_UKB_CASES_OVER_GBD
    cases or more is taken, else the GBD prevalence when the disease maps to a cause, else the pick when it has
    MIN_UKB_CASES; then its MONDO descendants' codes, their parents and their phecodes as one pool; else none."""
    if category:
        return None, "none", None, False
    phe = set(phecodes.phenocode.astype(str))
    ukb_all = pd.concat([panukb, phecodes], ignore_index=True)
    own = _best(ukb_all, set(own_icd10) | phecode_matches(set(own_icd9), phe))
    via = False
    if own is None:
        own = _best(ukb_all, with_parents(set(own_icd10)) - set(own_icd10))
        via = own is not None
    if own is not None and own[2] >= MIN_UKB_CASES_OVER_GBD:
        return own[0], "panukb", own[1], via
    k = gbd_k(mondo_id, gbd_map, gbd)
    if k is not None:
        return k, "gbd", None, False
    if own is not None:
        return own[0], "panukb", own[1], via
    pooled = set(desc_icd10) | with_parents(set(desc_icd10)) | phecode_matches(set(desc_icd9), phe)
    d = _best(ukb_all, pooled)
    if d is not None:
        return d[0], "panukb", d[1], False
    return None, "none", None, False


def icd9_xrefs() -> pd.DataFrame:
    """MONDO's ICD-9 cross-references (term_id, code as written: 401, 401.9 or a range 401-405)."""
    return frame.query("""SELECT term_id, split_part(xref_id, ':', 2) AS code FROM preclin.ontology_xref
                          WHERE ontology = 'MONDO' AND xref_id LIKE 'ICD9:%%'""")


def panukb_phecodes() -> pd.DataFrame:
    """Pan-UKB's phecode phenotypes with European cases and controls (a sex-limited phecode counts within its sex)."""
    ph = pd.read_csv(os.path.join(PANUKB, "phenotype_manifest.tsv.bgz"), sep="\t", compression="gzip", low_memory=False)
    ph = ph[ph.trait_type.eq("phecode") & ph.n_cases_EUR.notna() & ph.n_controls_EUR.notna()]
    return ph[["phenocode", "n_cases_EUR", "n_controls_EUR"]].assign(phenocode=lambda x: x.phenocode.astype(str))


K_RULES = ("registered", "own_first", "v3")
K_CORRECTED_COLS = ("k_corrected", "k_corrected_source", "k_corrected_code", "k_corrected_via_parent",
                    "h2_liab_k_corrected", "score_k_corrected", "ldsc_status_k_corrected")
RUN_FIELDS = ("ldsc_status", "h2_obs", "h2_obs_se", "loci", "n_cases", "n_controls")


def corrected_k_fields(row: dict, n_snps, k: float | None) -> dict:
    """The K-dependent columns of the corrected-K sensitivity for one profiled disease (Melissa's decision of
    2026-11-26): the stored run (RUN_FIELDS of the registered profile) rescored under the corrected K through
    score_fields; a disease whose run gave no estimate keeps its registered status."""
    none = {"h2_liab_k_corrected": None, "score_k_corrected": None, "ldsc_status_k_corrected": row["ldsc_status"]}
    if row.get("h2_obs") is None or row.get("n_cases") is None or row.get("n_controls") is None:
        return none
    p = float(row["n_cases"]) / (float(row["n_cases"]) + float(row["n_controls"]))
    f = score_fields(float(row["h2_obs"]), float(row["h2_obs_se"]), n_snps, int(row["loci"]), p, k)
    return {"h2_liab_k_corrected": f["h2_liab"], "score_k_corrected": f["score"], "ldsc_status_k_corrected": f["ldsc_status"]}


def _none(v):
    """None for SQL NULL however pandas holds it (None, NaN); the value otherwise."""
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else v


def icd_xrefs() -> pd.DataFrame:
    """MONDO's ICD-10 cross-references (term_id, code with the dot removed; ranges as the source writes them)."""
    return frame.query("""SELECT term_id, replace(split_part(xref_id, ':', 2), '.', '') AS code FROM preclin.ontology_xref
                          WHERE ontology = 'MONDO' AND (xref_id LIKE 'ICD10CM:%%' OR xref_id LIKE 'ICD10WHO:%%')""")


def failed_status(run_status: str | None) -> str:
    """The profile status of a chosen study whose run gave no estimate: no_effect keeps its name."""
    return "no_effect" if run_status == "no_effect" else "run_failed"


def gene_counts(mondo_id: str, mondo, members: set[str], evidence: pd.DataFrame) -> tuple[int, int, bool]:
    """(GWAS genes, rare or Mendelian genes, Mendelian form) from evidence rows (target_ensembl, mondo_id,
    datasource) for the disease, its members or a disease at Lin >= 0.8."""
    close = {d for d in evidence.mondo_id.unique() if d not in members and mondo.matches(d, mondo_id)[1]}
    ev = evidence[evidence.mondo_id.isin(members | close)]
    family = ev.datasource.map(FAMILY)
    gwas = int(ev.target_ensembl[family == "gwas"].nunique())
    mendelian = int(ev.target_ensembl[family.isin(("burden", "mendelian"))].nunique())
    form = bool(ev.datasource.isin(MENDELIAN_SOURCES).any())
    return gwas, mendelian, form


def gbd_map() -> dict[str, tuple[str, int]]:
    """Disease -> (relation, GBD cause id): exact before broader, then the larger rate."""
    m = pd.read_csv(GBD_MAP, dtype=str).dropna(subset=["mondo_id"])
    m = m[m.relation.isin(["exact", "broader"])]
    rates = gbd_rates()
    m = m.assign(rank=m.relation.map({"exact": 0, "broader": 1}), rate=m.cause_id.astype(int).map(rates))
    m = m.sort_values(["mondo_id", "rank", "rate"], ascending=[True, True, False]).drop_duplicates("mondo_id")
    return {r.mondo_id: (r.relation, int(r.cause_id)) for r in m.itertuples()}


def gbd_rates() -> dict[int, float]:
    g = pd.read_csv(GBD_FILE)
    g = g[(g.measure_name == "Prevalence") & (g.metric_name == "Rate") & (g.year == 2021)]
    return dict(zip(g.cause_id.astype(int), g.val.astype(float)))


def panukb_manifest() -> pd.DataFrame:
    ph = pd.read_csv(os.path.join(PANUKB, "phenotype_manifest.tsv.bgz"), sep="\t", compression="gzip", low_memory=False)
    ph = ph[ph.trait_type.eq("icd10") & ph.n_cases_EUR.notna() & ph.n_controls_EUR.notna()]
    return ph[["phenocode", "n_cases_EUR", "n_controls_EUR"]].assign(phenocode=lambda x: x.phenocode.astype(str))


def panukb_h2() -> pd.DataFrame:
    h = pd.read_csv(os.path.join(PANUKB, "h2_manifest.tsv.bgz"), sep="\t", compression="gzip", low_memory=False)
    h = h[h.trait_type.eq("icd10") & h["pop"].eq("EUR") & h["qcflags.pass_all"].astype(str).str.lower().eq("true")]
    return pd.DataFrame({"phenocode": h.phenocode.astype(str), "h2_liab": h["estimates.final.h2_liability"],
                         "z": h["estimates.final.h2_z"]})


ICD_RANGE = re.compile(r"^([A-Z])(\d{2})-([A-Z])(\d{2})$")


def expand_icd(code: str) -> set[str]:
    """A cross-reference code as the codes it names: a range like I10-I16 lists every three-character code in it; a
    single code (three or four characters, the dot already removed) stays as it is."""
    m = ICD_RANGE.match(code)
    if not m or m.group(1) != m.group(3):
        return {code}
    return {f"{m.group(1)}{i:02d}" for i in range(int(m.group(2)), int(m.group(4)) + 1)}


def own_and_descendant_codes(mondo_id: str, members: set[str], xrefs: pd.DataFrame) -> tuple[set[str], set[str]]:
    """The disease's own ICD-10 codes and, kept apart, those of its MONDO descendants (ranges expanded)."""
    own = {c for code in xrefs[xrefs.term_id.eq(mondo_id)].code for c in expand_icd(code)}
    desc = {c for code in xrefs[xrefs.term_id.isin(members - {mondo_id})].code for c in expand_icd(code)} - own
    return own, desc


GENETIC_SOURCES = tuple(k for k, v in FAMILY.items() if v in ("gwas", "burden", "mendelian"))
ASSOCIATIONS = os.path.join(CACHE, "association_by_datasource_direct")   # the release's direct associations, every gene


def association_digest(path: str = ASSOCIATIONS) -> str:
    """SHA-256 over the sorted parquet files' digests: the association file's content, for its release row."""
    files = sorted(f for f in os.listdir(path) if f.endswith(".parquet"))
    return hashlib.sha256("".join(llm.sha256_file(os.path.join(path, f)) for f in files).encode()).hexdigest()


def register_associations(cur, path: str = ASSOCIATIONS) -> int:
    """The association file as a source release (preclin.evidence_source_release); returns its id."""
    n = sum(f.endswith(".parquet") for f in os.listdir(path))
    return llm.register_release(cur, "open_targets_platform_associations", OT_RELEASE,
                                f"{SOURCE_URL}/association_by_datasource_direct", association_digest(path),
                                {"files": n, "retrieved": "2026-11-24", "from": "ftp.ebi.ac.uk",
                                 "use": "gene counts and Mendelian form over every gene (#147, 2026-11-24 decision)"})


def evidence_frame(path: str = ASSOCIATIONS, diseases: pd.DataFrame | None = None) -> pd.DataFrame:
    """(target_ensembl, mondo_id, datasource) for every gene with a human-genetic association in the full Open
    Targets direct-association file (Melissa's 2026-11-24 ruling: all genes, not the held targets), the disease
    mapped to MONDO through preclin.ot_disease (or `diseases`: disease_id, mondo_id)."""
    import pyarrow.dataset as ds  # noqa: PLC0415
    t = ds.dataset(path, format="parquet").to_table(columns=["diseaseId", "targetId", "aggregationValue"],
                                                    filter=ds.field("aggregationValue").isin(list(GENETIC_SOURCES)))
    ev = t.to_pandas().rename(columns={"targetId": "target_ensembl", "aggregationValue": "datasource"})
    ev["disease_id"] = ev.diseaseId.map(curie)
    if diseases is None:
        diseases = frame.query("""SELECT d.disease_id, m.mondo AS mondo_id
                                  FROM preclin.ot_disease d, unnest(d.mondo_ids) AS m(mondo)""")
    ev = ev.merge(diseases, on="disease_id")
    return ev[["target_ensembl", "mondo_id", "datasource"]].drop_duplicates().reset_index(drop=True)


def load_gbd(_args) -> None:
    g = pd.read_csv(GBD_FILE)
    g = g[(g.measure_name == "Prevalence") & (g.metric_name == "Rate")]
    citation = open(GBD_CITATION).read().strip()
    with llm.connect() as conn, conn.cursor() as cur:
        rid = llm.register_release(cur, "gbd_prevalence", "GBD 2023, year 2021", "https://vizhub.healthdata.org/gbd-results/",
                                   llm.sha256_file(GBD_FILE), {"received": "2026-11-23", "from": "Melissa's export",
                                                              "terms": "IHME free-of-charge non-commercial user agreement",
                                                              "citation": citation, "causes": int(len(g))})
        cur.execute("DELETE FROM preclin.gbd_prevalence")
        execute_values(cur, "INSERT INTO preclin.gbd_prevalence (cause_id, cause_name, year, rate_per_100k, source_release_id) VALUES %s",
                       [(int(r.cause_id), r.cause_name, int(r.year), float(r.val), rid) for r in g.itertuples()])
        conn.commit()
    print(f"{len(g)} causes loaded")


def release_id(name: str) -> int:
    r = frame.query("SELECT source_release_id FROM preclin.evidence_source_release WHERE source_name = %s "
                    "ORDER BY retrieved_at DESC LIMIT 1", (name,))
    if r.empty:
        raise SystemExit(f"no release registered for {name}")
    return int(r.source_release_id.iloc[0])


def studies_frame() -> pd.DataFrame:
    return frame.query("""SELECT gcst, mondo_ids, mapped_trait_uris, sumstats_path, cases, controls, eur_share, platform_snps
                          FROM preclin.gwas_catalog_study WHERE mondo_ids <> '{}'""")


def choose(_args) -> None:
    cands = candidates()
    studies = studies_frame()
    desc = descendants_table(mondo_tables()[0])
    rid = release_id("gwas_catalog")
    exclude = excluded_studies()
    rows = []
    for c in cands.itertuples():
        gcst, level, status = choose_study(studies, c.mondo_id, members(c.mondo_id, desc), exclude)
        rows.append((c.mondo_id, c.label, c.bio_area, int(c.entries), gcst, level, status, [rid]))
    with llm.connect() as conn, conn.cursor() as cur:
        execute_values(cur, """INSERT INTO preclin.disease_polygenicity
                                   (mondo_id, label, bio_area, entries, gcst, trait_level, ldsc_status, source_release_ids)
                               VALUES %s ON CONFLICT (mondo_id) DO UPDATE SET label = EXCLUDED.label, bio_area = EXCLUDED.bio_area,
                                   entries = EXCLUDED.entries, gcst = EXCLUDED.gcst, trait_level = EXCLUDED.trait_level,
                                   ldsc_status = EXCLUDED.ldsc_status, built_at = now()""", rows)
        conn.commit()
    chosen = pd.Series([r[6] for r in rows]).value_counts()
    print(f"{len(rows)} candidate diseases; study chosen for {int(chosen.get('ok', 0))}; " +
          ", ".join(f"{k} {v}" for k, v in chosen.items()))


def score_fields(h2_obs: float, h2_obs_se: float, n_snps, loci: int, p: float, k: float | None) -> dict:
    """Status, liability-scale h2 and score of one LDSC run (p = case fraction of the study, k = population prevalence).
    h2_liab is kept for every run with a K, whatever the status, so the z >= 2 descriptive can use low_z diseases."""
    z = h2_obs / h2_obs_se if h2_obs_se and h2_obs_se > 0 else None
    h2l = liability_h2(h2_obs, p, k) if k is not None else None
    out = {"h2_z": z, "h2_liab": h2l, "score": None, "log10_score": None}
    if n_snps is None or not n_snps >= MIN_PLATFORM_SNPS:
        out["ldsc_status"] = "targeted_array"
    elif z is None or z < Z_MIN:
        out["ldsc_status"] = "low_z"
    elif k is None:
        out["ldsc_status"] = "no_k"
    elif not 0 < h2l <= 1:
        out["ldsc_status"] = "out_of_bounds"
    elif loci == 0:
        out["ldsc_status"] = "zero_loci"   # measurable heritability without a locus: the no-score group (2026-11-24 ruling)
    else:
        out["ldsc_status"] = "ok"
        out["score"] = loci / h2l
        out["log10_score"] = float(np.log10(out["score"]))
    return out


def build(_args) -> None:
    prof = frame.query("SELECT mondo_id, label, bio_area, entries, gcst, trait_level, ldsc_status FROM preclin.disease_polygenicity")
    runs = frame.query("SELECT gcst, status, n, n_snps, h2_obs, h2_obs_se, intercept, loci, concentration FROM preclin.ldsc_run")
    runs = runs.set_index("gcst")
    studies = frame.query("SELECT gcst, cases, controls, mondo_ids FROM preclin.gwas_catalog_study WHERE mondo_ids <> '{}'")
    studies = studies.set_index("gcst")
    xrefs = icd_xrefs()
    desc = descendants_table(mondo_tables()[0])
    mondo = Mondo()
    gmap, rates = gbd_map(), gbd_rates()
    ukb, ukb_h2 = panukb_manifest(), panukb_h2()
    me = pd.read_csv(ME_FILE, dtype=str).dropna(subset=["mondo_ids"])
    me_map = {m: float(r.log10_me) for r in me.itertuples() for m in r.mondo_ids.split(";")}
    evidence = evidence_frame()
    assoc, lookup = read_associations(), trait_lookup()
    with llm.connect() as conn, conn.cursor() as cur:
        assoc_release = register_associations(cur)
        conn.commit()
    releases = [release_id("gwas_catalog"), release_id("gbd_prevalence"), assoc_release]
    out = []
    for d in prof.itertuples():
        mem = members(d.mondo_id, desc)
        row = {"mondo_id": d.mondo_id, "ldsc_status": d.ldsc_status}
        row["gwas_studies"], row["gws_associations"], row["loci_catalog"] = loci_catalog(assoc, mem, lookup)
        own, desc_codes = own_and_descendant_codes(d.mondo_id, mem, xrefs)
        pooled = set(xrefs.code[xrefs.term_id.isin(mem)])
        k, source, code, via_parent = k_for_registered(d.mondo_id, gmap, rates, pooled, ukb)   # the registered columns
        row.update({"k": k, "k_source": source, "k_code": code, "k_via_parent": via_parent})
        k2, source2, code2, via2 = k_for(d.mondo_id, gmap, rates, own, ukb, desc_codes)        # the corrected-K sensitivity
        row.update({"k_corrected": k2, "k_corrected_source": source2, "k_corrected_code": code2, "k_corrected_via_parent": via2})
        n_snps_run = None
        gwas, mend, form = gene_counts(d.mondo_id, mondo, mem, evidence)
        row.update({"gwas_genes": gwas, "mendelian_genes": mend, "mendelian_form": form, "me_log10": me_map.get(d.mondo_id)})
        h = ukb_h2[ukb_h2.phenocode.isin(with_parents(own))]
        if not len(h):
            h = ukb_h2[ukb_h2.phenocode.isin(with_parents(desc_codes))]
        h = h.sort_values("z", ascending=False)
        row.update({"panukb_h2_liab": float(h.h2_liab.iloc[0]) if len(h) else None, "panukb_h2_z": float(h.z.iloc[0]) if len(h) else None})
        cases = None
        if d.gcst is not None and d.gcst in studies.index:
            cases, controls = int(studies.cases[d.gcst]), int(studies.controls[d.gcst])
            row.update({"n_cases": cases, "n_controls": controls, "n_eff": n_eff(cases, controls)})
            r = runs.loc[d.gcst] if d.gcst in runs.index else None
            if r is None or r.status != "ok":
                row["ldsc_status"] = failed_status(None if r is None else r.status)
            else:
                n_snps_run = r.n_snps
                row.update({"h2_obs": float(r.h2_obs), "h2_obs_se": float(r.h2_obs_se), "intercept": r.intercept,
                            "loci": int(r.loci), "concentration": r.concentration})
                row.update(score_fields(float(r.h2_obs), float(r.h2_obs_se), r.n_snps, int(r.loci), cases / (cases + controls), k))
        row.update(corrected_k_fields({c: row.get(c) for c in RUN_FIELDS}, n_snps_run, k2))
        if cases is None:
            own = studies[studies.mondo_ids.map(lambda m: bool(set(m) & mem))].cases.dropna()
            cases = int(own.max()) if len(own) else None
        row["gwas_genes_per_10k_cases"] = gwas / cases * 1e4 if cases else None
        row["source_release_ids"] = releases
        out.append(row)
    cols = ["gwas_studies", "gws_associations", "loci_catalog", "n_cases", "n_controls", "n_eff", "h2_obs", "h2_obs_se",
            "intercept", "h2_z", "k", "k_source", "h2_liab", "ldsc_status", "loci", "concentration", "score", "log10_score",
            "gwas_genes", "gwas_genes_per_10k_cases", "mendelian_genes", "mendelian_form", "me_log10", "panukb_h2_liab",
            "panukb_h2_z", "k_code", "k_via_parent", *K_CORRECTED_COLS, "source_release_ids"]
    with llm.connect() as conn, conn.cursor() as cur:
        for row in out:
            cur.execute(f"UPDATE preclin.disease_polygenicity SET {', '.join(f'{c} = %s' for c in cols)}, built_at = now() "
                        f"WHERE mondo_id = %s", [_py(row.get(c)) for c in cols] + [row["mondo_id"]])
        conn.commit()
    table = pd.DataFrame(out)
    print(table.ldsc_status.value_counts().to_string())
    both = table[table.h2_liab.notna() & table.panukb_h2_liab.notna()]
    if len(both) >= 3:
        rho, p = spearmanr(both.h2_liab, both.panukb_h2_liab)
        print(f"Pan-UKB check: Spearman {rho:.2f} (p {p:.3g}) over {len(both)} diseases with both estimates")
    print("K sources:", table.k_source.value_counts().to_dict())


def _py(v):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def counts(_args) -> None:
    t = frame.query("SELECT ldsc_status, entries FROM preclin.disease_polygenicity")
    ok = t[t.ldsc_status.eq("ok")]
    print(f"scored: {len(ok)} diseases, {int(ok.entries.sum())} entries, of {len(t)} candidate diseases with "
          f"{int(t.entries.sum())} entries on this build (Melissa's base: {BASE['diseases']} diseases, {BASE['entries']} entries)")
    print(t.groupby("ldsc_status").agg(diseases=("entries", "size"), entries=("entries", "sum")).to_string())


def check_unit(_args) -> None:
    cands = candidates()
    have = set(frame.query("SELECT mondo_id FROM preclin.disease_polygenicity").mondo_id)
    missing = cands[~cands.mondo_id.isin(have)]
    print(f"unit today: {len(cands)} diseases, {int(cands.entries.sum())} entries; profiled: {len(have)}")
    if len(missing):
        print("not profiled:", ", ".join(f"{r.mondo_id} ({r.label}, {r.entries})" for r in missing.itertuples()))
        sys.exit(1)


def drugged(_args) -> None:
    """Fill preclin.disease_polygenicity.drugged_large_effect (migration 172) for every profiled disease: a gene with
    rare-variant or Mendelian evidence for the disease is the primary target of a programme that entered Phase 2 or 3
    there or was approved for it. Reads the Open Targets direct-association download once; the report then needs
    only the table."""
    from report.polygenicity import drugged_large_effect  # noqa: PLC0415
    prof = frame.query("SELECT mondo_id FROM preclin.disease_polygenicity ORDER BY mondo_id")
    flags = drugged_large_effect(prof)
    with llm.connect() as conn, conn.cursor() as cur:
        for r in flags.itertuples():
            cur.execute("UPDATE preclin.disease_polygenicity SET drugged_large_effect = %s WHERE mondo_id = %s",
                        (bool(r.drugged_large_effect), r.mondo_id))
        conn.commit()
    print(f"drugged_large_effect: {int(flags.drugged_large_effect.sum())} of {len(flags)} diseases")


def k_corrected(_args) -> None:
    """Fill the corrected-K sensitivity columns (K_CORRECTED_COLS, migration 178) for every profiled disease from the
    stored runs under the corrected rule, leaving every registered column as it is (Melissa's decision of 2026-11-26)."""
    prof = frame.query(f"""SELECT mondo_id, gcst, k_source, k_code, {', '.join(RUN_FIELDS)}
                           FROM preclin.disease_polygenicity ORDER BY mondo_id""")
    n_snps = dict(frame.query("SELECT gcst, n_snps FROM preclin.ldsc_run").itertuples(index=False, name=None))
    xrefs, desc, gmap, rates, ukb = icd_xrefs(), descendants_table(mondo_tables()[0]), gbd_map(), gbd_rates(), panukb_manifest()
    rows = []
    for d in prof.itertuples():
        own, desc_codes = own_and_descendant_codes(d.mondo_id, members(d.mondo_id, desc), xrefs)
        k, source, code, via_parent = k_for(d.mondo_id, gmap, rates, own, ukb, desc_codes)
        f = corrected_k_fields({c: _none(getattr(d, c)) for c in RUN_FIELDS}, _none(n_snps.get(d.gcst)), k)
        rows.append({"k_corrected": k, "k_corrected_source": source, "k_corrected_code": code, "k_corrected_via_parent": via_parent,
                     **f, "mondo_id": d.mondo_id})
    with llm.connect() as conn, conn.cursor() as cur:
        cur.executemany(f"UPDATE preclin.disease_polygenicity SET {', '.join(f'{c} = %s' for c in K_CORRECTED_COLS)} WHERE mondo_id = %s",
                        [tuple(_py(r[c]) for c in K_CORRECTED_COLS) + (r["mondo_id"],) for r in rows])
        conn.commit()
    t = pd.DataFrame(rows).merge(prof[["mondo_id", "ldsc_status", "k_source", "k_code"]], on="mondo_id")
    print(t.ldsc_status_k_corrected.value_counts().to_string())
    ukb_scored = t.k_source.eq("panukb") & t.ldsc_status.eq("ok")
    changed = ukb_scored & (t.k_corrected_code.ne(t.k_code) | t.k_corrected_source.ne("panukb"))
    print(f"K code changed for {int(changed.sum())} of {int(ukb_scored.sum())} scored diseases with a Pan-UKB K; scored under the "
          f"corrected K: {int(t.ldsc_status_k_corrected.eq('ok').sum())} (registered {int(t.ldsc_status.eq('ok').sum())}); "
          f"via parent (corrected rule): {int(t.k_corrected_via_parent.fillna(False).astype(bool).sum())}")


def k_rules(_args) -> None:
    """Fill preclin.disease_polygenicity_k (migration 181): one row per profiled disease per rule. `registered` and
    `own_first` copy the profile's own columns; `v3` is k_for_v3 on the stored runs (announced on #147 2026-11-27).
    The profile's columns are not touched."""
    prof = frame.query(f"""SELECT mondo_id, gcst, k, k_source, k_code, k_via_parent, h2_liab, score, {', '.join(K_CORRECTED_COLS)},
                                  {', '.join(RUN_FIELDS)} FROM preclin.disease_polygenicity ORDER BY mondo_id""")
    n_snps = dict(frame.query("SELECT gcst, n_snps FROM preclin.ldsc_run").itertuples(index=False, name=None))
    x10, x9, desc = icd_xrefs(), icd9_xrefs(), descendants_table(mondo_tables()[0])
    gmap, rates, ukb, phe = gbd_map(), gbd_rates(), panukb_manifest(), panukb_phecodes()
    rows = []
    for d in prof.itertuples():
        mem = members(d.mondo_id, desc)
        own10, desc10 = own_and_descendant_codes(d.mondo_id, mem, x10)
        own9_raw = set(x9.code[x9.term_id.eq(d.mondo_id)])
        own9 = {c for code in own9_raw for c in expand_icd9(code)}
        desc9 = {c for code in x9.code[x9.term_id.isin(mem - {d.mondo_id})] for c in expand_icd9(code)} - own9
        cat = is_category(set(x10.code[x10.term_id.eq(d.mondo_id)]), own9_raw, len(desc10 | desc9))
        run = {c: _none(getattr(d, c)) for c in RUN_FIELDS}
        k, source, code, via = k_for_v3(d.mondo_id, gmap, rates, own10, own9, desc10, desc9, ukb, phe, category=cat)
        f = corrected_k_fields(run, _none(n_snps.get(d.gcst)), k)
        rows.append((d.mondo_id, "v3", k, source, code, via, f["h2_liab_k_corrected"], f["score_k_corrected"], f["ldsc_status_k_corrected"], cat))
        rows.append((d.mondo_id, "registered", _none(d.k), d.k_source, _none(d.k_code), _none(d.k_via_parent), _none(d.h2_liab), _none(d.score), d.ldsc_status, False))
        rows.append((d.mondo_id, "own_first", _none(d.k_corrected), d.k_corrected_source, _none(d.k_corrected_code), _none(d.k_corrected_via_parent),
                     _none(d.h2_liab_k_corrected), _none(d.score_k_corrected), d.ldsc_status_k_corrected, False))
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.disease_polygenicity_k")
        execute_values(cur, """INSERT INTO preclin.disease_polygenicity_k
                               (mondo_id, rule, k, k_source, k_code, k_via_parent, h2_liab, score, ldsc_status, category) VALUES %s""",
                       [tuple(_py(v) for v in r) for r in rows])
        conn.commit()
    t = pd.DataFrame(rows, columns=["mondo_id", "rule", "k", "k_source", "k_code", "k_via_parent", "h2_liab", "score", "ldsc_status", "category"])
    v3 = t[t.rule.eq("v3")].set_index("mondo_id")
    reg = t[t.rule.eq("registered")].set_index("mondo_id")
    print(v3.ldsc_status.value_counts().to_string())
    scored = reg.ldsc_status.eq("ok")
    print(f"v3: scored {int(v3.ldsc_status.eq('ok').sum())} (registered {int(scored.sum())}); category terms {int(v3.category.sum())} "
          f"({int((v3.category & scored).sum())} scored under the registered rule); K sources among the registered scored: "
          f"{v3.k_source[scored].value_counts().to_dict()}; code or source changed for "
          f"{int((scored & (v3.k_code.fillna('') != reg.k_code.fillna('')) | (scored & (v3.k_source != reg.k_source))).sum())} of {int(scored.sum())}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in (("load-gbd", load_gbd), ("choose", choose), ("build", build), ("counts", counts), ("check-unit", check_unit),
                     ("drugged", drugged), ("k-corrected", k_corrected), ("k-rules", k_rules)):
        sub.add_parser(name).set_defaults(fn=fn)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
