"""Section 3: which evidence translates to the clinic (plan: report/translation_plan.md).

    python -m report.section3

Cohort C2: programs on a human protein target entering Phase 2 from 2015-01-01
to 2020-10-20; outcome S4 = advanced (own Phase 3 start, or FDA approval for the
disease) within four years of entry. C1 and C3 are the same for Phase 1 and
Phase 3. Evidence comes from Open Targets evidence rows (preclin.ot_evidence),
each dated, frozen at the year before entry, and matched to the program's
disease on MONDO: G3 is the same term, a subtype, or Lin >= 0.8; G2 a disease at
Lin 0.5-0.8; G1 germline evidence only for unrelated diseases. Risk ratios come
from modified Poisson models clustered by primary-target set and adjusted for
disease area, modality, entity novelty, entry period and target precedent.
Trials T: industry randomised Phase 2/3 trials since 2010 whose governing primary
is an efficacy endpoint (preclin.trial_endpoint) with a readable primary result
(preclin.trial_outcome); outcome NOT MET (mixed counts as not met).
"""
from __future__ import annotations

import json
import os
import warnings
from collections import defaultdict
from datetime import date

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.discrete.conditional_models import ConditionalLogit

from report import frame
from report.disease_match import Mondo
from report.section1 import SEED, failure_modes, phase_rows

OUT = os.path.join(frame.REPO, "report", "output", "section3")
CASE_AUDIT = os.path.join(frame.REPO, "report", "audits", "section3_cases.json")
BIOLOGY_CODES = ("F2", "F3", "F4", "F5")  # failures that test the evidence's biological claim
WINDOW = (date(2015, 1, 1), date(2020, 10, 20))  # four years of follow-up before the 24-month inactivity cutoff
HORIZON_YEARS = 4.0
TRIALS_FROM = date(2010, 1, 1)
FDAAA_START = date(2017, 1, 18)
N_BOOT = 1000
N_PERMUTATIONS = 200
MIN_TARGETS = 15  # distinct exposed target sets below which no risk ratio is fitted
DISCOVERY_SHARE = 0.6
CLOSE, RELATED = 0.8, 0.5  # Lin similarity at which evidence counts for the disease (G3) or a related one (G2)
HEREDITARY = "MONDO:0003847"
PREWEANING_LETHAL = "MP:0010770"
NEVER = 9999  # year given to evidence with no date: it counts only when evidence is not frozen
ABSENT = 10**6  # year of a tier or direction that a target-disease pair does not have
IMPC_ALLELE = "[(](EUCOMM|KOMP|IMPC|EUCOMMTools|NCOM)[)]"  # alleles made by the high-throughput knockout consortia

FAMILY = {"gwas_credible_sets": "gwas", "gene_burden": "burden", "eva": "mendelian", "orphanet": "mendelian",
          "gene2phenotype": "mendelian", "clingen": "mendelian", "genomics_england": "mendelian",
          "uniprot_variants": "mendelian", "uniprot_literature": "mendelian", "cancer_gene_census": "somatic",
          "intogen": "somatic", "eva_somatic": "somatic", "expression_atlas": "expression", "reactome": "reactome",
          "crispr": "crispr", "crispr_screen": "crispr", "impc": "impc", "mgi": "mgi"}
GERMLINE = ("gwas", "burden", "mendelian")
FAMILIES = ("gwas", "burden", "mendelian", "somatic", "impc", "mgi", "expression", "reactome", "crispr")
TIERS = ("any", "strong", "mid", "weak", "lof_protect", "lof_risk", "gof_risk", "gof_protect", "up", "down")
DECREASE = {"inhibitor", "antagonist", "blocker", "negative_modulator", "inverse_agonist", "degrader",
            "binder_neutralizer", "gene_expression_reduction"}
INCREASE = {"agonist", "partial_agonist", "activator", "positive_modulator", "opener", "replacement",
            "gene_expression_increase"}
PROXIMITY = {"B1_target_engagement": "proximal", "B2_exploratory_biomarker": "proximal",
             "B3_regulatory_surrogate": "proximal", "B4_objective_physiological": "intermediate",
             "B5_clinician_scale": "intermediate", "B6_patient_reported": "intermediate",
             "B7_disease_events": "distal", "B8_hard_outcome": "distal"}
TREND = {"proximal": 0, "intermediate": 1, "distal": 2}
EFFICACY = ("efficacy: stated", "efficacy: primary endpoint not met")
LABELS = {
    "g3": "Human germline genetics for the disease (G3)", "g2": "Germline genetics, related disease only (G2)",
    "g1": "Germline genetics, unrelated diseases only (G1)",
    "gwas": "GWAS, any locus-to-gene", "gwas_strong": "GWAS, locus-to-gene >= 0.8",
    "gwas_mid": "GWAS, best locus-to-gene 0.5-0.8", "gwas_weak": "GWAS, best locus-to-gene < 0.5",
    "burden": "Gene burden (exome)", "burden_strong": "Gene burden, p < 2.5e-6",
    "mendelian": "Mendelian / ClinVar pathogenic", "mendelian_strong": "Mendelian, top-tier curation",
    "somatic": "Somatic driver, any", "somatic_concordant": "Somatic driver, concordant with drug action",
    "impc": "Mouse knockout (IMPC pipeline)", "impc_strong": "IMPC knockout, top-quartile phenotype match",
    "mgi": "Mouse model (literature, MGI)", "mgi_strong": "Literature mouse model, top-quartile match",
    "expression": "Differential expression in disease", "expression_strong": "Differential expression, |log2FC| >= 1",
    "reactome": "Pathway (Reactome)", "crispr": "CRISPR screen", "precedent": "Approved drug on the target (any disease)",
    "b1": "Approved drug on the target for a related disease", "liability": "Target liability (any)",
    "pan_essential": "Pan-essential (DepMap)", "constrained": "LoF-intolerant (LOEUF < 0.35)",
    "ko_lethal": "Mouse knockout lethal before weaning",
}
# Burden and expression strength tiers are left out: Open Targets exports only burden results at p < 2.5e-6
# and expression changes of |log2FC| >= 1.1, so each tier equals its family.
MAP_FEATURES = ["g3", "gwas", "gwas_strong", "gwas_mid", "gwas_weak", "burden", "mendelian",
                "mendelian_strong", "somatic", "somatic_concordant", "impc", "mgi", "mgi_strong", "expression",
                "reactome", "crispr", "b1", "precedent", "liability", "pan_essential", "constrained", "ko_lethal"]


def evidence_index() -> tuple[dict, dict]:
    """gene -> family -> MONDO term -> first year of each tier in TIERS; and gene -> first
    year of germline evidence for any trait, including measurement traits with no MONDO
    term. Strength tiers: GWAS locus-to-gene >= 0.8 (0.5-0.8 mid, < 0.5 weak); burden
    p < 2.5e-6; ClinVar pathogenic with multiple submitters or expert review, ClinGen or
    Gene2Phenotype definitive or strong, PanelApp green; mouse PhenoDigm score in the top
    quartile; expression |log2FC| >= 1. ClinVar 'protective' records inform direction only.
    Mouse models from the IMPC consortia carry no date of their own in Open Targets (none,
    or the gene's first literature year), so they count only when evidence is not frozen."""
    q75 = float(frame.query("""SELECT percentile_cont(0.75) WITHIN GROUP (ORDER BY resource_score) AS q
                               FROM preclin.ot_evidence WHERE datasource = 'impc'""").q.iloc[0])
    g = frame.query("""
        WITH e AS (
            SELECT target_ensembl AS ens, disease_id, resource_score, confidence,
                   direction_on_target AS dot, direction_on_trait AS dtr, (detail->>'log2FoldChangeValue')::float AS lfc,
                   CASE WHEN datasource <> 'impc' THEN datasource
                        WHEN detail->>'biologicalModelAllelicComposition' ~ %s THEN 'impc' ELSE 'mgi' END AS source,
                   CASE WHEN datasource = 'impc' AND detail->>'biologicalModelAllelicComposition' ~ %s THEN 9999
                        ELSE coalesce(evidence_year, 9999) END AS y,
                   datasource NOT IN ('eva', 'eva_somatic')
                     OR detail->'clinicalSignificances' ?| array['pathogenic', 'likely pathogenic'] AS counts
            FROM preclin.ot_evidence
            WHERE (datasource NOT IN ('eva', 'eva_somatic')
                   OR detail->'clinicalSignificances' ?| array['pathogenic', 'likely pathogenic', 'protective'])
              AND NOT (datasource = 'clingen' AND confidence IN ('Disputed', 'Refuted', 'Limited',
                                                                   'No Known Disease Relationship'))
              AND NOT (datasource = 'impc' AND resource_score IS NULL))
        SELECT ens, disease_id, source, min(y) FILTER (WHERE counts) AS y_any,
               min(y) FILTER (WHERE counts AND (
                                    (source = 'gwas_credible_sets' AND resource_score >= 0.8)
                                 OR (source = 'gene_burden' AND resource_score < 2.5e-6)
                                 OR (source = 'eva' AND confidence IN ('criteria provided, multiple submitters, no conflicts',
                                                                       'reviewed by expert panel', 'practice guideline'))
                                 OR (source = 'clingen' AND confidence IN ('Definitive', 'Strong'))
                                 OR (source = 'gene2phenotype' AND confidence IN ('definitive', 'strong'))
                                 OR (source = 'genomics_england' AND confidence = 'green')
                                 OR (source IN ('impc', 'mgi') AND resource_score >= %s)
                                 OR (source = 'expression_atlas' AND abs(lfc) >= 1))) AS y_strong,
               min(y) FILTER (WHERE source = 'gwas_credible_sets' AND resource_score >= 0.5
                                AND resource_score < 0.8) AS y_mid,
               min(y) FILTER (WHERE source = 'gwas_credible_sets' AND resource_score < 0.5) AS y_weak,
               min(y) FILTER (WHERE dot = 'LoF' AND dtr = 'protect') AS y_lof_protect,
               min(y) FILTER (WHERE counts AND dot = 'LoF' AND dtr = 'risk') AS y_lof_risk,
               min(y) FILTER (WHERE counts AND dot = 'GoF' AND dtr = 'risk') AS y_gof_risk,
               min(y) FILTER (WHERE dot = 'GoF' AND dtr = 'protect') AS y_gof_protect,
               min(y) FILTER (WHERE lfc > 0) AS y_up,
               min(y) FILTER (WHERE lfc < 0) AS y_down
        FROM e GROUP BY 1, 2, 3""", (IMPC_ALLELE, IMPC_ALLELE, q75))
    g["family"] = g.source.map(FAMILY)
    germline_first = g[g.family.isin(GERMLINE)].groupby("ens").y_any.min().dropna().astype(int).to_dict()
    mondo = frame.query("SELECT disease_id, mondo_ids FROM preclin.ot_disease WHERE cardinality(mondo_ids) > 0")
    g = g.merge(mondo, on="disease_id").explode("mondo_ids").rename(columns={"mondo_ids": "mondo"})
    cols = [f"y_{t}" for t in TIERS]
    g[cols] = g[cols].fillna(ABSENT).astype(int)
    g = g.groupby(["ens", "family", "mondo"], as_index=False)[cols].min()
    idx: dict = defaultdict(dict)
    for (ens, fam), sub in g.groupby(["ens", "family"]):
        idx[ens][fam] = dict(zip(sub.mondo, sub[cols].itertuples(index=False, name=None)))
    return idx, germline_first


class Neighbourhood:
    """MONDO terms whose evidence counts for a program disease at a Lin threshold: the
    disease, its subtypes, and every term at least that similar to it."""

    def __init__(self, mondo: Mondo):
        self.mondo = mondo
        self.desc = defaultdict(set)
        for t, ancs in mondo.ancestors.items():
            for a in ancs:
                self.desc[a].add(t)
        self.cache: dict = {}

    def terms(self, d: str, threshold: float) -> frozenset:
        key = (d, threshold)
        if key not in self.cache:
            m = self.mondo
            out = {d} | self.desc[d]
            # The most informative common ancestor c of d and any term b with Lin(b, d) >= t has
            # IC(c) >= t / 2 * IC(d), and b descends from c, so only those ancestors are swept.
            floor = threshold / 2 * m.ic.get(d, 0.0)
            for c in m.ancestors[d] | {d}:
                if m.ic.get(c, 0.0) >= floor:
                    out |= {b for b in self.desc[c] | {c} if b not in out and m.lin(b, d) >= threshold}
            self.cache[key] = frozenset(out)
        return self.cache[key]


def hits(terms: dict, allowed: frozenset) -> list[tuple]:
    """Year tuples of the evidence terms in `allowed`."""
    if len(terms) < len(allowed):
        return [ys for t, ys in terms.items() if t in allowed]
    return [terms[t] for t in allowed if t in terms]


class Evidence:
    """Evidence features of a program (its entity's primary targets x its disease) as of a cutoff year."""

    def __init__(self, progs: pd.DataFrame):
        self.mondo = Mondo()
        self.nb = Neighbourhood(self.mondo)
        self.idx, self.germline_first = evidence_index()
        t = frame.query("""
            SELECT mt.moiety_id, t.symbol, t.ensembl_id AS ens, mt.action, t.target_class
            FROM preclin.moiety_target mt JOIN public.targets t ON t.id = mt.target_id
            JOIN preclin.moiety m USING (moiety_id)
            WHERE mt.is_primary AND m.target_kind = 'human_protein' AND t.ensembl_id IS NOT NULL""")
        t["sign"] = np.where(t.action.isin(DECREASE), "decrease", np.where(
            t.action.isin(INCREASE), "increase", np.where(t.action == "depleter", "address", "ambiguous")))
        self.ent = t.groupby("moiety_id").agg(
            target=("symbol", lambda s: "+".join(sorted(set(s)))), genes=("ens", lambda s: sorted(set(s))),
            classes=("target_class", lambda s: sorted(set(s.fillna("Unclassified")))),
            sign=("sign", lambda s: s.iloc[0] if s.nunique() == 1 else "ambiguous"))
        self.liab = {
            "pan_essential": set(frame.query("""SELECT t.ensembl_id FROM public.gene_essentiality_summary e
                                                JOIN public.targets t ON t.id = e.target_id
                                                WHERE e.pan_essential""").ensembl_id),
            "constrained": set(frame.query("""SELECT t.ensembl_id FROM public.gene_constraint g
                                              JOIN public.targets t ON t.id = g.target_id
                                              GROUP BY 1 HAVING min(g.loeuf) < 0.35""").ensembl_id),
            "ko_lethal": set(frame.query("""
                SELECT DISTINCT target_ensembl FROM preclin.ot_mouse_phenotype
                WHERE phenotype_id = %s OR phenotype_id IN (SELECT term_id FROM preclin.ontology_ancestor
                                                            WHERE ontology = 'MP' AND ancestor_id = %s)""",
                (PREWEANING_LETHAL, PREWEANING_LETHAL)).target_ensembl),
        }
        self.mechanism = {(e, m): (risk, prot, ry, py) for e, m, risk, prot, ry, py in frame.query(
            """SELECT ensembl_id, mondo_id, risk_mechanism, protective, risk_year, protective_year
               FROM preclin.gene_disease_mechanism""").itertuples(index=False)}
        self.mouse = defaultdict(list)
        for e, m, pert, rel, year in frame.query("""
                SELECT r.ensembl_id, r.mondo_id, r.perturbation, r.relation,
                       min(CASE WHEN e.detail->>'biologicalModelAllelicComposition' ~ %s THEN NULL
                                ELSE e.evidence_year END) AS year
                FROM preclin.mouse_model_relation r JOIN preclin.ot_evidence e
                  ON e.target_ensembl = r.ensembl_id AND e.datasource = 'impc'
                 AND e.detail->>'biologicalModelId' = r.model_id
                GROUP BY r.ensembl_id, r.mondo_id, r.model_id, r.perturbation, r.relation""",
                (IMPC_ALLELE,)).itertuples(index=False):
            self.mouse[(e, m)].append((pert, rel, int(year) if pd.notna(year) else NEVER))
        self.disease = progs.set_index("program_id").mondo_id
        # Approvals on each gene: each entity's first FDA approval (any disease), and its
        # approved diseases, dated as in section1.phase_rows.
        p = progs[progs.moiety_id.isin(self.ent.index)]
        self.first_approval: dict = {}
        self.approved: dict = defaultdict(list)
        for r in p.itertuples(index=False):
            genes = self.ent.at[r.moiety_id, "genes"]
            first = pd.Timestamp(r.moiety_first_fda_approval) if pd.notna(r.moiety_first_fda_approval) else None
            if first is not None:
                for gene in genes:
                    self.first_approval[gene] = min(self.first_approval.get(gene, pd.Timestamp.max), first)
            if r.approved == "yes" and isinstance(r.mondo_id, str):
                when = (pd.Timestamp(r.first_approval_date) if r.date_basis == "dated" and pd.notna(r.first_approval_date)
                        else min(first, pd.Timestamp("2014-12-31")) if first is not None else pd.Timestamp("2014-12-31"))
                for gene in genes:
                    self.approved[gene].append((r.mondo_id, when))
                    self.first_approval[gene] = min(self.first_approval.get(gene, pd.Timestamp.max), when)

    def levels(self, moiety_id: str, d: str, cut: int) -> tuple[float, float, float]:
        """(G3, G2, G1) indicators of germline evidence dated by `cut`: for the disease, for a
        related disease only, for unrelated diseases only."""
        genes = self.ent.at[moiety_id, "genes"]

        def within(allowed: frozenset) -> bool:
            return any(ys[0] <= cut for g in genes for f in GERMLINE
                       for ys in hits(self.idx.get(g, {}).get(f, {}), allowed))
        if within(self.nb.terms(d, CLOSE)):
            return 1.0, 0.0, 0.0
        if within(self.nb.terms(d, RELATED)):
            return 0.0, 1.0, 0.0
        return 0.0, 0.0, float(min(self.germline_first.get(g, ABSENT) for g in genes) <= cut)

    def program(self, moiety_id: str, d: str, entry: pd.Timestamp, cut: int) -> dict:
        e = self.ent.loc[moiety_id]
        close, related = self.nb.terms(d, CLOSE), self.nb.terms(d, RELATED)
        first = defaultdict(lambda: [ABSENT] * len(TIERS))  # family -> first year of each tier, matched to d
        rel = ABSENT
        for gene in e.genes:
            for f, terms in self.idx.get(gene, {}).items():
                for ys in hits(terms, close):
                    acc = first[f]
                    for i, y in enumerate(ys):
                        acc[i] = min(acc[i], y)
                if f in GERMLINE:
                    rel = min([rel, *(ys[0] for ys in hits(terms, related))])

        def on(f: str, tier: str) -> bool:
            return f in first and first[f][TIERS.index(tier)] <= cut

        g3 = any(on(f, "any") for f in GERMLINE)
        g2 = not g3 and rel <= cut
        g1 = not g3 and not g2 and min(self.germline_first.get(g, ABSENT) for g in e.genes) <= cut
        dec, inc = e.sign == "decrease", e.sign == "increase"
        germ = {k: any(on(f, k) for f in GERMLINE) for k in ("lof_protect", "lof_risk", "gof_risk", "gof_protect")}
        conc = (dec and (germ["lof_protect"] or germ["gof_risk"])) or (inc and (germ["lof_risk"] or germ["gof_protect"]))
        disc = (dec and (germ["lof_risk"] or germ["gof_protect"])) or (inc and (germ["lof_protect"] or germ["gof_risk"]))
        direction = ("none" if not g3 else "not_applicable" if not (dec or inc) else "mixed" if conc and disc
                     else "concordant" if conc else "discordant" if disc else "undirected")
        liab = {k: float(any(g in s for g in e.genes)) for k, s in self.liab.items()}
        labelled = [m for m in (self.mechanism.get((g, d)) for g in e.genes) if m]
        risks = {risk for risk, _, ry, _ in labelled if pd.notna(ry) and ry <= cut}
        prots = {prot for _, prot, _, py in labelled if pd.notna(py) and py <= cut}
        mconc = ((dec and ("gain_of_function" in risks or "loss_of_function_protective" in prots))
                 or (inc and ("loss_of_function" in risks or "gain_of_function_protective" in prots)))
        mdisc = ((dec and ("loss_of_function" in risks or "gain_of_function_protective" in prots))
                 or (inc and ("gain_of_function" in risks or "loss_of_function_protective" in prots)))
        models = [(pert, rel) for g in e.genes for pert, rel, y in self.mouse.get((g, d), ()) if y <= cut]
        like = {(p, r) for p, r in models if p != "other" and r != "unrelated"}
        # A model that lowers the gene's function and resembles the disease argues for raising it, and so on.
        favour = {("reduced_function", "mimics_disease"): "increase", ("increased_function", "opposes_disease"): "increase",
                  ("reduced_function", "opposes_disease"): "decrease", ("increased_function", "mimics_disease"): "decrease"}
        wants = {favour[x] for x in like}
        return {
            "target": e.target, "sign": e.sign, "classes": e.classes,
            "mouse_any": float(bool(models)), "mouse_oriented": float(bool(like)),
            "mouse_direction": ("none" if not like else "not_applicable" if not (dec or inc) else "mixed" if len(wants) > 1
                                else "concordant" if e.sign in wants else "discordant"),
            "mouse_ko_mimics": float(("reduced_function", "mimics_disease") in like),
            "mouse_ko_opposes": float(("reduced_function", "opposes_disease") in like),
            "g3": float(g3), "g2": float(g2), "g1": float(g1), "g_level": 3 if g3 else 2 if g2 else 1 if g1 else 0,
            "direction": direction, "burden_lof_protect": float(on("burden", "lof_protect")),
            "mechanism": ("none" if not g3 else "not_applicable" if not (dec or inc) else "unlabelled" if not labelled
                          else "mixed" if mconc and mdisc else "concordant" if mconc else "discordant" if mdisc
                          else "undirected"),
            "lof_protective": float("loss_of_function_protective" in prots),
            **{f: float(on(f, "any")) for f in FAMILIES},
            **{f"{f}_strong": float(on(f, "strong")) for f in FAMILIES},
            "gwas_mid": float(on("gwas", "mid") and not on("gwas", "strong")),
            "gwas_weak": float(on("gwas", "weak") and not on("gwas", "mid") and not on("gwas", "strong")),
            "somatic_mixed": float(on("somatic", "any") and on("somatic", "gof_risk") and on("somatic", "lof_risk")
                                   and (dec or inc)),
            "somatic_concordant": float(on("somatic", "any") and ((dec and on("somatic", "gof_risk"))
                                                                  or (inc and on("somatic", "lof_risk")))),
            "expression_up": float(on("expression", "up")), "expression_down": float(on("expression", "down")),
            **liab, "liability": float(any(liab.values())),
            "precedent": float(any(self.first_approval.get(g, pd.Timestamp.max) < entry for g in e.genes)),
            "b1": float(any(m in related and when < entry for g in e.genes for m, when in self.approved.get(g, ()))),
        }

    def features(self, rows: pd.DataFrame, freeze: bool = True) -> pd.DataFrame:
        """Features per (program, phase) row with a target and a disease; frozen at entry - 1, or all
        evidence known today when freeze is False."""
        out = []
        for r in rows.itertuples(index=False):
            d = self.disease.get(r.program_id)
            if r.moiety_id not in self.ent.index or not isinstance(d, str):
                continue
            cut = pd.Timestamp(r.entry).year - 1 if freeze else NEVER
            out.append({"program_id": r.program_id, "phase": r.phase,
                        **self.program(r.moiety_id, d, pd.Timestamp(r.entry), cut)})
        return pd.DataFrame(out)


TODAY = ["g3", "g2", "g1", *FAMILIES, *(f"{f}_strong" for f in FAMILIES), "gwas_mid", "gwas_weak",
         "somatic_concordant"]


def cohorts(progs: pd.DataFrame, trials: pd.DataFrame, snap: date, ev: Evidence) -> pd.DataFrame:
    """C1-C3 program rows with S4, regime and frozen evidence; *_today columns hold evidence known today."""
    rows = phase_rows(progs, trials, snap, window=WINDOW)
    rows = rows[~rows.credited].copy()
    rows["s4"] = ((rows.event == "advanced") & (rows.years <= HORIZON_YEARS)).astype(float)
    rows["era"] = pd.cut(rows.entry_year, [2014, 2016, 2018, 2020], labels=["2015-16", "2017-18", "2019-20"]).astype(str)
    d = rows.merge(ev.features(rows), on=["program_id", "phase"])
    today = ev.features(rows, freeze=False)
    d = d.merge(today[["program_id", "phase", *TODAY]].rename(columns={k: f"{k}_today" for k in TODAY}),
                on=["program_id", "phase"])
    d["mondo_id"] = d.program_id.map(ev.disease)
    d["hereditary"] = d.mondo_id.map(lambda m: HEREDITARY in ev.mondo.ancestors.get(m, ()))
    d["regime"] = np.where(d.bio_area.eq("oncology"), "ONC",
                           np.where(d.hereditary & (d.mendelian > 0), "DD", "COM"))
    return d


COVARS = ("bio_area", "modality", "era", "novel", "precedent")
TRIAL_COVARS = ("bio_area", "modality", "era", "phase3", "novel", "precedent")


def design(d: pd.DataFrame, exposure: list[str], covars: tuple[str, ...]) -> pd.DataFrame:
    X = pd.DataFrame({c: d[c].astype(float) for c in exposure}, index=d.index)
    for c in (c for c in covars if c not in exposure):
        if d[c].dtype == bool or pd.api.types.is_numeric_dtype(d[c]):
            X[c] = d[c].astype(float)
            continue
        counts = d[c].value_counts()
        common = counts[counts >= 30].index  # the most common level is the reference; rare levels pool together
        for lev in common[1:]:
            X[f"{c}={lev}"] = (d[c] == lev).astype(float)
        X[f"{c}=other"] = (~d[c].isin(common)).astype(float)
    X = X.loc[:, (X.std() > 0) | X.columns.isin(exposure)]
    return sm.add_constant(X, has_constant="add")


def poisson(d: pd.DataFrame, outcome: str, exposure: list[str], covars: tuple[str, ...] = COVARS):
    """Modified Poisson fit (log link, robust errors clustered by primary-target set)."""
    X = design(d, exposure, covars)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return sm.GLM(d[outcome].astype(float), X, family=sm.families.Poisson()).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(d.target, sort=True)[0]})


def coef(fit, name: str, ratio: str = "rr") -> dict:
    if name not in fit.params or not np.isfinite(fit.bse[name]):
        return {}
    b, se = fit.params[name], fit.bse[name]
    return {ratio: float(np.exp(b)), "lo": float(np.exp(b - 1.96 * se)), "hi": float(np.exp(b + 1.96 * se)),
            "p": float(fit.pvalues[name])}


def describe(d: pd.DataFrame, outcome: str, col: str) -> dict:
    w, wo, succ = d[d[col] > 0], d[d[col] <= 0], d[d[outcome] > 0]
    return {"n": int(len(w)), "n_targets": int(w.target.nunique()), "n_cohort": int(len(d)),
            "ppv": float(w[outcome].mean()) if len(w) else None,
            "rate_without": float(wo[outcome].mean()) if len(wo) else None,
            "coverage": float((succ[col] > 0).mean()) if len(succ) else None}


def estimate(d: pd.DataFrame, outcome: str, col: str, covars: tuple[str, ...] = COVARS) -> dict:
    """Description plus the adjusted risk ratio of one binary exposure."""
    desc = describe(d, outcome, col)
    if desc["n_targets"] < MIN_TARGETS or desc["n"] == desc["n_cohort"] or not d[outcome].any():
        return {"feature": col, **desc}
    return {"feature": col, **desc, **coef(poisson(d, outcome, [col], covars), col)}


def adjusted(d: pd.DataFrame, outcome: str, exposure: list[str], covars: tuple[str, ...] = COVARS) -> dict:
    """Risk ratio of the first exposure from a model holding all of them, when it has enough exposed targets."""
    if d.loc[d[exposure[0]] > 0, "target"].nunique() < MIN_TARGETS:
        return {}
    return coef(poisson(d, outcome, exposure, covars), exposure[0])


def levels_vs_g0(d: pd.DataFrame, suffix: str = "") -> dict:
    """G3, G2 and G1 each against G0 (no germline evidence), from one model holding all three;
    a level's description counts only its programs and G0's."""
    cols = [f"g{k}{suffix}" for k in (3, 2, 1)]
    g0 = (d[cols] <= 0).all(axis=1)
    present = [c for c in cols if (d[c] > 0).any()]
    fit = poisson(d, "s4", present) if present else None
    out = {}
    succ = d[d.s4 > 0]
    for c in cols:
        sub = d[(d[c] > 0) | g0]
        desc = {**describe(sub, "s4", c), "coverage": float((succ[c] > 0).mean()) if len(succ) else None}
        out[c] = {"feature": c, **desc, **(coef(fit, c) if fit is not None and desc["n_targets"] >= MIN_TARGETS else {})}
    return out


def within_target(d: pd.DataFrame, outcome: str, col: str) -> dict:
    """Conditional logit with target strata, among targets whose programs differ on `col` and on outcome."""
    keep = d.groupby("target").filter(lambda g: g[col].nunique() > 1 and g[outcome].nunique() > 1)
    out = {"informative_targets": int(keep.target.nunique()), "programs": int(len(keep))}
    if out["informative_targets"] < MIN_TARGETS:
        return out
    X = keep[[col]].astype(float).assign(era_late=(keep.entry_year >= 2018).astype(float))
    fit = ConditionalLogit(keep[outcome].astype(float), X, groups=pd.factorize(keep.target)[0]).fit(disp=False)
    return {**out, **coef(fit, col, "or")}


def holm(p: dict[str, float | None]) -> dict[str, float]:
    order = sorted((v, k) for k, v in p.items() if v is not None and np.isfinite(v))
    adj, running = {}, 0.0
    for i, (v, k) in enumerate(order):
        running = max(running, min(1.0, v * (len(order) - i)))
        adj[k] = running
    return adj


def cause_outcomes(d: pd.DataFrame) -> pd.DataFrame:
    """Cause-specific failure indicators from the stopping reason of each suspended program."""
    r = d.reason.fillna("")
    ops = "enrollment, operational or regulatory"
    return d.assign(f_efficacy=r.isin(EFFICACY).astype(float), f_safety=r.eq("safety").astype(float),
                    f_business=r.eq("business or strategic (explicit)").astype(float),
                    f_unspecified=r.eq("sponsor decision, unspecified").astype(float),
                    f_bizops=r.isin(["business or strategic (explicit)", ops]).astype(float),
                    f_pkops=r.isin(["PK, dose or formulation", ops]).astype(float))


def stacked_ratio(d: pd.DataFrame, a: str, b: str, exposure: str, covars: tuple[str, ...]) -> dict:
    """Ratio of the exposure's adjusted risk ratio for outcome b to its adjusted risk ratio for
    outcome a, from one model on the two outcomes stacked, every term interacted with the
    outcome (so each outcome keeps its own covariate effects) and errors clustered by target."""
    s = pd.concat([d.assign(y=d[a]), d.assign(y=d[b])], ignore_index=True)
    second = np.repeat([0.0, 1.0], len(d))
    X = design(s, [exposure], covars)
    X = pd.concat([X, X.mul(second, axis=0).add_suffix(":second")], axis=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = sm.GLM(s.y.astype(float), X, family=sm.families.Poisson()).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(s.target, sort=True)[0]})
    return {"rr_" + a: coef(fit, exposure), "ratio_" + b + "_vs_" + a: coef(fit, f"{exposure}:second")}


def trial_frame(progs: pd.DataFrame, trials: pd.DataFrame, ev: Evidence) -> pd.DataFrame:
    """One row per randomised industry Phase 2/3 efficacy trial with a readable primary result,
    with the G3 status (as of the year before its start) of the programs it tests."""
    t = frame.query("""
        SELECT s.nct_id, s.start_date, s.primary_completion_date, s.has_results,
               'United States' = ANY(coalesce(s.countries, '{}')) AS us_site,
               e.endpoint_class, e.measurement_type, e.scale, o.primary_endpoint,
               CASE d.task WHEN 'trial_outcome_from_publication' THEN 'publication' ELSE 'registry' END AS results_source
        FROM preclin.ctgov_study s
        JOIN preclin.trial_endpoint e USING (nct_id)
        JOIN preclin.trial_outcome o USING (nct_id)
        JOIN pv_evidence.llm_decision d ON d.llm_decision_id = o.llm_decision_id
        WHERE s.lead_sponsor_class = 'INDUSTRY' AND s.allocation = 'RANDOMIZED' AND e.purpose = 'efficacy'
          AND o.primary_endpoint IN ('met', 'not_met', 'mixed') AND s.start_date >= %s""", (TRIALS_FROM,))
    links = trials[(trials.attach == "disease") & trials.phase.isin([2, 3])][["program_id", "nct_id", "phase"]]
    links = links.merge(t[["nct_id", "start_date"]], on="nct_id")
    p = progs.set_index("program_id")
    rows = []
    for r in links.itertuples(index=False):
        mid, d = p.at[r.program_id, "moiety_id"], p.at[r.program_id, "mondo_id"]
        if mid not in ev.ent.index or not isinstance(d, str):
            continue
        first, start = p.at[r.program_id, "moiety_first_fda_approval"], pd.Timestamp(r.start_date)
        rows.append({"nct_id": r.nct_id, "phase": r.phase, "target": ev.ent.at[mid, "target"],
                     "g3": ev.levels(mid, d, start.year - 1)[0],
                     "bio_area": p.at[r.program_id, "bio_area"] or "unmapped",
                     "modality": p.at[r.program_id, "modality"] or "unknown",
                     "novel": pd.isna(first) or pd.Timestamp(first) > start,
                     "precedent": any(ev.first_approval.get(g, pd.Timestamp.max) < start
                                      for g in ev.ent.at[mid, "genes"])})
    x = pd.DataFrame(rows).sort_values(["nct_id", "g3"], ascending=[True, False]).groupby("nct_id").agg(
        phase=("phase", "max"), target=("target", lambda s: "|".join(sorted(set(s)))), g3=("g3", "max"),
        bio_area=("bio_area", "first"), modality=("modality", "first"), novel=("novel", "all"),
        precedent=("precedent", "any")).reset_index()
    x = x.merge(t, on="nct_id")
    x["not_met"] = x.primary_endpoint.isin(["not_met", "mixed"]).astype(float)
    x["not_met_strict"] = x.primary_endpoint.eq("not_met").astype(float)
    x["proximity"] = x.endpoint_class.map(PROXIMITY)
    x["phase3"] = (x.phase == 3).astype(float)
    x["era"] = pd.cut(pd.to_datetime(x.start_date).dt.year, [2009, 2014, 2018, 2026],
                      labels=["2010-14", "2015-18", "2019+"]).astype(str)
    x["fdaaa"] = (x.results_source.eq("registry") & x.us_site
                  & (pd.to_datetime(x.primary_completion_date) >= pd.Timestamp(FDAAA_START)))
    return x


def proximity_test(x: pd.DataFrame, outcome: str = "not_met") -> dict:
    """H4: whether G3's effect on NOT MET changes across proximal, intermediate and distal endpoints."""
    x = x[x.proximity.notna() & x.bio_area.ne("oncology")].copy()
    x["trend"] = x.proximity.map(TREND).astype(float)
    x["g3_trend"] = x.g3 * x.trend
    for lev in ("intermediate", "distal"):
        x[f"prox_{lev}"] = (x.proximity == lev).astype(float)
    fit = poisson(x, outcome, ["g3", "g3_trend", "prox_intermediate", "prox_distal"], TRIAL_COVARS)
    return {"n": int(len(x)), "n_g3": int(x.g3.sum()), "g3_at_proximal": coef(fit, "g3"),
            "interaction_per_step": coef(fit, "g3_trend"),
            "by_proximity": {lev: estimate(x[x.proximity == lev], outcome, "g3", TRIAL_COVARS) for lev in TREND}}


def program_endpoint(trials: pd.DataFrame, c2: pd.DataFrame) -> pd.Series:
    """Endpoint class of each Phase 2 program's first randomised industry Phase 2 efficacy trial
    that started within a year of entry and before the program advanced (a later trial would
    let the outcome choose the stratum)."""
    e = frame.query("""SELECT e.nct_id, e.endpoint_class, s.start_date FROM preclin.trial_endpoint e
                       JOIN preclin.ctgov_study s USING (nct_id)
                       WHERE e.purpose = 'efficacy' AND s.allocation = 'RANDOMIZED'
                         AND s.lead_sponsor_class = 'INDUSTRY'""")
    own = trials[(trials.phase == 2) & trials.attach.eq("disease")][["program_id", "nct_id"]].merge(e, on="nct_id")
    own = own.merge(c2[["program_id", "entry", "event", "years"]], on="program_id")
    start, entry = pd.to_datetime(own.start_date), pd.to_datetime(own.entry)
    advanced = entry + pd.to_timedelta(own.years * 365.25, unit="D")
    own = own[(start <= entry + pd.Timedelta(days=365)) & (own.event.ne("advanced") | (start < advanced))]
    return own.sort_values(["program_id", "start_date", "nct_id"]).drop_duplicates("program_id") \
              .set_index("program_id").endpoint_class


def stratum(c) -> str | None:
    if not isinstance(c, str):
        return None
    return PROXIMITY.get(c) or ("oncology" if c.startswith("O") else "infection" if c.startswith("B9") else None)


def bootstrap_rr(d: pd.DataFrame, col: str, outcome: str, rng: np.random.Generator) -> tuple[float, np.ndarray]:
    """Crude risk ratio and its target-cluster bootstrap draws."""
    x = d[col] > 0
    g = pd.DataFrame({"n_exp": x, "s_exp": d[outcome] * x, "n_un": ~x, "s_un": d[outcome] * ~x}).astype(float) \
          .groupby(d.target).sum().to_numpy()
    n_exp, s_exp, n_un, s_un = g.sum(axis=0)
    rr = (s_exp / n_exp) / (s_un / n_un) if n_exp and s_un else np.nan
    w = rng.multinomial(len(g), np.full(len(g), 1 / len(g)), size=N_BOOT)
    s = w @ g
    with np.errstate(divide="ignore", invalid="ignore"):
        draws = (s[:, 1] / s[:, 0]) / (s[:, 3] / s[:, 2])
    return float(rr), draws


def crude_rr(d: pd.DataFrame, col: str, outcome: str = "s4") -> float:
    x = d[col] > 0
    a, b = d.loc[x, outcome].mean(), d.loc[~x, outcome].mean()
    return float(a / b) if b else np.nan


def influence(d: pd.DataFrame, col: str, outcome: str = "s4") -> list[tuple[str, float]]:
    """Crude risk ratio without each exposed target, the most influential (largest drop) first."""
    out = [(t, crude_rr(d[d.target != t], col, outcome)) for t in d.loc[d[col] > 0, "target"].unique()]
    return sorted(out, key=lambda kv: kv[1])


RULES = {  # key: (label, rule, regime, in the committed plan)
    "M1": ("Protective loss-of-function burden + drug that decreases function",
           lambda d: (d.burden_lof_protect > 0) & d.sign.eq("decrease"), "all", True),
    "M2": ("Mendelian evidence + drug that increases function or replaces the gene",
           lambda d: d.sign.eq("increase"), "DD", True),
    "M3": ("Mendelian evidence extrapolated to a common disease", lambda d: d.mendelian > 0, "COM", True),
    "M4": ("GWAS, locus-to-gene >= 0.8 for the indication", lambda d: d.gwas_strong > 0, "all", True),
    "M5": ("GWAS and rare-variant evidence for the same disease",
           lambda d: (d.gwas > 0) & ((d.burden > 0) | (d.mendelian > 0)), "all", True),
    "M6": ("Concordant somatic driver + drug that decreases function",
           lambda d: (d.somatic_concordant > 0) & d.sign.eq("decrease"), "ONC", True),
    "M7": ("IMPC knockout phenotype matching the disease, top quartile", lambda d: d.impc_strong > 0, "all", True),
    "M8": ("Literature-curated mouse model of the disease", lambda d: d.mgi > 0, "all", True),
    "M9": ("Expression up in disease + drug that decreases function",
           lambda d: (d.expression_up > 0) & d.sign.eq("decrease"), "all", True),
    "M10": ("Reactome pathway evidence", lambda d: d.reactome > 0, "all", True),
    "M11": ("Target liability + drug that decreases function",
            lambda d: (d.liability > 0) & d.sign.eq("decrease"), "all", True),
    "B1": ("Approved drug on the target for a disease within Lin 0.5", lambda d: d.b1 > 0, "all", True),
    "P1": ("Protective loss of function established + drug that decreases function",
           lambda d: (d.lof_protective > 0) & d.sign.eq("decrease"), "all", False),
    "P2": ("Germline mechanism concordant with drug action", lambda d: d.mechanism.eq("concordant"), "all", False),
    "P3": ("Mouse model direction concordant with drug action",
           lambda d: d.mouse_direction.eq("concordant"), "all", False),
}
CASES_RANDOM = 4  # successes and failures drawn per rule
CASES_EFFICACY = 6  # programs stopped for efficacy after a missed randomised trial, drawn per rule


def rules(c2: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rule screen on a 60/40 split of target sets: a rule is predictive when its discovery
    risk ratio has a 90% bootstrap lower bound above 1.3, its confirmation risk ratio is at
    least 1.2 with a one-sided 95% lower bound above 1, and the full-sample risk ratio stays
    at least 1.2 without its most influential target. Risk ratios here are crude, within
    the rule's regime; the adjusted one is reported beside them."""
    targets = np.array(sorted(c2.target.unique()))
    discovery = set(targets[rng.random(len(targets)) < DISCOVERY_SHARE])
    out, exposed = [], []
    for key, (label, rule, regime, registered) in RULES.items():
        d = c2 if regime == "all" else c2[c2.regime == regime]
        d = d.assign(rule=rule(d).astype(float))
        row = {"rule": key, "label": label, "regime": regime, "registered": registered,
               **describe(d, "s4", "rule"), "crude_rr": crude_rr(d, "rule")}
        if row["n_targets"] >= MIN_TARGETS and row["n"] < len(d):
            row.update({f"adj_{k}": v for k, v in coef(poisson(d, "s4", ["rule"]), "rule").items()})
        for split, part in (("discovery", d[d.target.isin(discovery)]), ("confirmation", d[~d.target.isin(discovery)])):
            if part.loc[part.rule > 0, "target"].nunique() < 5:
                continue
            rr, draws = bootstrap_rr(part, "rule", "s4", rng)
            row.update({f"{split}_rr": rr, f"{split}_lo90": float(np.nanpercentile(draws, 5)),
                        f"{split}_hi90": float(np.nanpercentile(draws, 95)), f"{split}_n": int((part.rule > 0).sum()),
                        f"{split}_targets": int(part.loc[part.rule > 0, "target"].nunique())})
        infl = influence(d, "rule") if (d.rule > 0).any() else []
        row["most_influential"] = infl[0][0] if infl else None
        row["rr_without_most_influential"] = infl[0][1] if infl else None
        row["predictive"] = bool(row.get("discovery_lo90", 0) > 1.3 and row.get("confirmation_rr", 0) >= 1.2
                                 and row.get("confirmation_lo90", 0) > 1
                                 and (row["rr_without_most_influential"] or 0) >= 1.2)
        out.append(row)
        exposed.append(d[d.rule > 0].assign(rule_key=key, influential=d.target.isin([t for t, _ in infl[:3]])))
    return pd.DataFrame(out), pd.concat(exposed, ignore_index=True)


def pick_cases(rule_table: pd.DataFrame, exposed: pd.DataFrame, missed: set[str],
               rng: np.random.Generator) -> pd.DataFrame:
    """Cases for each rule that is predictive, or whose adjusted risk ratio excludes 1 (marked
    as short of the bar): four successes and four suspended programs at random, up to two
    programs of each of the three most influential targets, and up to CASES_EFFICACY of the
    programs that stopped for efficacy after a randomised trial missed its primary endpoint
    (`missed`); n_missed records how many there were. The plan asks for every such program;
    the cap keeps verification to a size agents can check against primary sources."""
    out = []
    for r in rule_table[rule_table.predictive | (rule_table.adj_lo > 1)].itertuples():
        e = exposed[exposed.rule_key == r.rule]
        succ, fail = e[e.s4 > 0], e[(e.s4 == 0) & (e.event == "suspended")]
        stopped = e[e.reason.isin(EFFICACY) & e.reason_nct.isin(missed)]
        out.append(pd.concat([
            succ.iloc[rng.permutation(len(succ))[:CASES_RANDOM]].assign(why="random success"),
            fail.iloc[rng.permutation(len(fail))[:CASES_RANDOM]].assign(why="random failure"),
            e[e.influential].sort_values(["target", "s4", "program_id"], ascending=[True, False, True])
             .groupby("target").head(2).assign(why="influential target"),
            stopped.iloc[rng.permutation(len(stopped))[:CASES_EFFICACY]].assign(why="primary endpoint missed"),
        ]).drop_duplicates("program_id").assign(status="predictive" if r.predictive else "short of the bar",
                                                n_missed=len(stopped)))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def permutation_null(com: pd.DataFrame, ev: Evidence, rng: np.random.Generator) -> dict:
    """H1's G3 risk ratio (G3, G2 and G1 against G0 in COM) with each program's disease swapped
    for another COM program's in the same area, against the unshuffled estimate."""
    levels = ["g3", "g2", "g1"]
    observed = coef(poisson(com, "s4", levels), "g3")["rr"]
    years = (com.entry_year - 1).to_numpy()
    rrs = []
    for _ in range(N_PERMUTATIONS):
        shuffled = com.groupby("bio_area").mondo_id.transform(lambda s: rng.permutation(s.to_numpy()))
        x = com.copy()
        x[levels] = [ev.levels(m, d, y) for m, d, y in zip(com.moiety_id, shuffled, years)]
        rrs.append(coef(poisson(x, "s4", levels), "g3").get("rr", np.nan) if x.g3.any() else np.nan)
    ok = np.array(rrs)[np.isfinite(rrs)]
    return {"observed": observed, "null_median": float(np.median(ok)), "null_95": float(np.percentile(ok, 95)),
            "p_one_sided": float((np.sum(ok >= observed) + 1) / (len(ok) + 1)), "n_permutations": int(len(ok))}


def case_audit(cases: pd.DataFrame) -> dict:
    """Agreement of the agent-verified case studies (report/audits/section3_cases.json) with the
    pipeline: outcome within four years, the evidence claim and its date, and the failure codes.
    The audit must cover exactly the cases picked."""
    a = pd.DataFrame(json.load(open(CASE_AUDIT)))
    picked = {f"{r}:{int(p)}" for r, p in zip(cases.rule_key, cases.program_id)}
    if set(a.case_id) != picked:
        raise ValueError(f"case audit covers {len(set(a.case_id) & picked)} of {len(picked)} picked cases")
    prog = a.drop_duplicates("program_id")
    failed = prog[prog.advanced_within_4y == "no"]
    return {"cases": int(len(a)), "programs": int(len(prog)),
            "outcome_correct": int((prog.pipeline_correct == "yes").sum()),
            "outcome_wrong": int((prog.pipeline_correct == "no").sum()),
            "claim_supported": int(a.claim_supported.eq("yes").sum()),
            "claim_partial": int(a.claim_supported.eq("partial").sum()),
            "claim_not_supported": int(a.claim_supported.eq("no").sum()),
            "predates_entry": int(a.predates_entry.eq("yes").sum()),
            "failed_programs": int(len(failed)),
            "failure_codes": failed.failure_code.value_counts().to_dict(),
            "biology_failures": int(failed.failure_code.isin(BIOLOGY_CODES).sum()),
            "by_rule": {r: {"cases": int(len(g)), "advanced": int((g.advanced_within_4y == "yes").sum()),
                            "claim_supported": int(g.claim_supported.isin(["yes", "partial"]).sum()),
                            "biology_failures": int(g.failure_code.isin(BIOLOGY_CODES).sum())}
                        for r, g in a.groupby("rule")}}


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return float(o) if np.isfinite(o) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def summary(g: pd.DataFrame) -> dict:
    return {"programs": int(len(g)), "targets": int(g.target.nunique()), "s4": float(g.s4.mean())}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(SEED)
    snap = frame.snapshot()
    progs, trials, outcomes = frame.programs(), frame.program_trials(), frame.trial_outcomes()
    ev = Evidence(progs)
    d = cohorts(progs, trials, snap, ev)
    rows_all = phase_rows(progs, trials, snap, window=WINDOW)
    fm = failure_modes(rows_all, progs, trials, outcomes)
    d = cause_outcomes(d.merge(fm[["program_id", "phase", "reason", "nct_id"]].rename(columns={"nct_id": "reason_nct"}),
                               on=["program_id", "phase"], how="left"))
    d["endpoint_class"] = d.program_id.map(program_endpoint(trials, d[d.phase == 2])).where(d.phase == 2)
    d["endpoint_stratum"] = d.endpoint_class.map(stratum)
    c1, c2, c3 = (d[d.phase == p] for p in (1, 2, 3))
    com, onc = c2[c2.regime == "COM"], c2[c2.regime == "ONC"]
    # Programs outside the cohorts: no disease (healthy-volunteer, basket or symptom trials only) or
    # no resolved human protein target. Their exposures are undefined; they advance less often.
    out_ = rows_all[~rows_all.credited].assign(
        s4=lambda r: ((r.event == "advanced") & (r.years <= HORIZON_YEARS)).astype(float),
        why=lambda r: np.where(r.program_id.map(ev.disease).isna(), "no_disease",
                               np.where(~r.moiety_id.isin(ev.ent.index), "no_protein_target", "kept")))
    excluded = {f"C{p}": {w: {"programs": int(len(g)), "s4": float(g.s4.mean())}
                          for w, g in out_[out_.phase == p].groupby("why")} for p in (1, 2, 3)}
    n: dict = {"window": [str(w) for w in WINDOW], "horizon_years": HORIZON_YEARS, "excluded": excluded,
               "cohorts": {f"C{p}": {"all": summary(d[d.phase == p]),
                                     **{r: summary(g) for r, g in d[d.phase == p].groupby("regime")}}
                           for p in (1, 2, 3)}}

    fit = poisson(com, "s4", ["g3", "g2", "g1"])
    n["h1"] = {"g3": coef(fit, "g3"), "g2": coef(fit, "g2"), "g1": coef(fit, "g1"),
               "levels": {int(k): summary(g) for k, g in com.groupby("g_level")}}
    n["h2"] = within_target(c2, "s4", "g3")
    dirn = c2[c2.direction.isin(["discordant", "undirected", "concordant"])]
    dirn = dirn.assign(trend=dirn.direction.map({"discordant": 0, "undirected": 1, "concordant": 2}).astype(float))
    n["h3"] = {"trend": coef(poisson(dirn, "s4", ["trend"]), "trend"),
               "levels": {k: summary(g) for k, g in c2.groupby("direction")}}

    tf = trial_frame(progs, trials, ev)
    n["h4"] = {"fdaaa": proximity_test(tf[tf.fdaaa]), "all_readable": proximity_test(tf),
               "fdaaa_mixed_as_met": proximity_test(tf[tf.fdaaa], "not_met_strict"),
               "all_readable_mixed_as_met": proximity_test(tf, "not_met_strict")}
    by_class = []
    for cls, g in tf.groupby("endpoint_class"):
        for scope, part in (("all", g), ("fdaaa", g[g.fdaaa])):
            r = estimate(part, "not_met", "g3", TRIAL_COVARS)
            by_class.append({"endpoint_class": cls, "scope": scope, "not_met": float(part.not_met.mean()),
                             **{k: v for k, v in r.items() if k != "feature"}})
    pd.DataFrame(by_class).to_csv(os.path.join(OUT, "endpoint_classes.csv"), index=False)
    n["endpoints"] = {f"{r['endpoint_class']}_{r['scope']}": r for r in by_class}
    n["trials"] = {"n": int(len(tf)), "fdaaa": int(tf.fdaaa.sum()), "g3": int(tf.g3.sum()),
                   "not_met": float(tf.not_met.mean())}
    n["twin"] = {s: {**summary(g), **estimate(g, "s4", "g3")} for s, g in c2.groupby("endpoint_stratum")}

    c23, covp = pd.concat([c2, c3]), (*COVARS, "phase")
    n["h5"] = stacked_ratio(c23, "f_efficacy", "f_bizops", "g3", covp)
    nononc = d[d.bio_area.ne("oncology")]  # Phases 1-3: Phase 1 is where safety stops a program
    n["h6"] = {"safety": estimate(nononc, "f_safety", "liability", covp),
               "efficacy": estimate(nononc, "f_efficacy", "liability", covp),
               **stacked_ratio(nononc, "f_efficacy", "f_safety", "liability", covp)}
    # H6 claims both that liability raises safety failure and that it does so more than efficacy
    # failure: the intersection-union test takes the larger p.
    n["h6"]["p"] = max(n["h6"]["safety"].get("p", 1.0), n["h6"]["ratio_f_safety_vs_f_efficacy"].get("p", 1.0))
    n["h7"] = estimate(onc, "s4", "somatic_concordant")
    n["holm"] = holm({"H1": n["h1"]["g3"].get("p"), "H2": n["h2"].get("p"), "H3": n["h3"]["trend"].get("p"),
                      "H4": n["h4"]["fdaaa"]["interaction_per_step"].get("p"),
                      "H5": n["h5"]["ratio_f_bizops_vs_f_efficacy"].get("p"),
                      "H6": n["h6"]["p"], "H7": n["h7"].get("p")})
    n["h7_without_mixed"] = estimate(onc.assign(x=((onc.somatic_concordant > 0) & (onc.somatic_mixed == 0))
                                                .astype(float)), "s4", "x")

    emap = []
    for scope, g in (("C2", c2), ("C2 COM", com), ("C2 ONC", onc), ("C1", c1), ("C3", c3)):
        for f in MAP_FEATURES:  # each against programs without it; the G levels against G0 are in h1 and levels
            r = estimate(g, "s4", f)
            if f"{f}_today" in g:
                t = estimate(g, "s4", f"{f}_today")
                r.update({"today_n": t["n"], "today_rr": t.get("rr"), "today_lo": t.get("lo"), "today_hi": t.get("hi")})
            emap.append({"scope": scope, "label": LABELS.get(f, f), **r})
    pd.DataFrame(emap).to_csv(os.path.join(OUT, "evidence_map.csv"), index=False)
    n["map"] = {r["scope"].replace(" ", "_"): {} for r in emap}
    for r in emap:
        n["map"][r["scope"].replace(" ", "_")][r["feature"]] = r
    n["beyond_precedent"] = {scope: {"adjusted_for_b1": adjusted(g, "s4", ["g3", "b1"]),
                                     "novel_targets": estimate(g[g.precedent == 0], "s4", "g3"),
                                     "without_b1": estimate(g[g.b1 == 0], "s4", "g3")}
                             for scope, g in (("C2", c2), ("COM", com), ("ONC", onc))}
    n["levels"] = {scope: {"frozen": levels_vs_g0(g), "today": levels_vs_g0(g, "_today")}
                   for scope, g in (("C1", c1), ("C2", c2), ("COM", com), ("ONC", onc), ("C3", c3))}
    n["by_area"] = {a: estimate(g, "s4", "g3") for a, g in c2.groupby("bio_area")}
    n["by_sign"] = {s: estimate(g, "s4", "g3") for s, g in c2.groupby("sign")}
    n["by_modality"] = {m: estimate(g, "s4", "g3") for m, g in c2.groupby("modality")}
    n["controls"] = {
        "phase1_g3": levels_vs_g0(c1[c1.regime == "COM"])["g3"],
        "phase3_g3": levels_vs_g0(c3[c3.regime == "COM"])["g3"],
        **{f"{o}_failure_g3": estimate(c23, f"f_{o}", "g3", covp)
           for o in ("efficacy", "safety", "business", "unspecified", "pkops")},
    }

    infl = sorted(((t, coef(poisson(com[com.target != t], "s4", ["g3", "g2", "g1"]), "g3").get("rr", np.nan))
                   for t in com.loc[com.g3 > 0, "target"].unique()), key=lambda kv: kv[1])
    classes = pd.Series([c for cs in com.classes for c in cs]).value_counts().index[:5]
    n["influence"] = {
        "most_influential": infl[0][0], "rr_without": infl[0][1], "rr_range": [infl[0][1], infl[-1][1]],
        "without_class": {c.replace(" ", "_"): coef(poisson(com[~com.classes.map(lambda cs: c in cs)], "s4",
                                                            ["g3", "g2", "g1"]), "g3") for c in classes}}
    n["permutation"] = permutation_null(com, ev, rng)

    # Not in the plan: direction of effect from the drug-blind mechanism and mouse-model labels
    def versus(g: pd.DataFrame, col: str, level: str, ref: str) -> dict:
        sub = g[g[col].isin([level, ref])]
        return estimate(sub.assign(x=(sub[col] == level).astype(float)), "s4", "x")
    mech = c2[c2.mechanism.isin(["discordant", "undirected", "concordant"])]
    mech = mech.assign(trend=mech.mechanism.map({"discordant": 0, "undirected": 1, "concordant": 2}).astype(float))
    n["mechanism"] = {"levels": {k: summary(g) for k, g in c2.groupby("mechanism")},
                      "levels_com": {k: summary(g) for k, g in com.groupby("mechanism")},
                      "trend": coef(poisson(mech, "s4", ["trend"]), "trend"),
                      "vs_no_g3": {k: versus(c2, "mechanism", k, "none") for k in ("concordant", "undirected", "discordant")},
                      "lof_protective_decrease": estimate(c2.assign(x=((c2.lof_protective > 0) & c2.sign.eq("decrease"))
                                                                  .astype(float)), "s4", "x")}
    # Gene2Phenotype records an absent gene product (SO:0002317) for loss-of-function mechanisms and
    # an increased gene product level (SO:0002315) for gain of function: an external check on the labels.
    g2p = frame.query("""
        WITH g2p AS (SELECT DISTINCT e.target_ensembl, m.term, e.variant_consequence FROM preclin.ot_evidence e
                     JOIN preclin.ot_disease od USING (disease_id) CROSS JOIN LATERAL unnest(od.mondo_ids) m(term)
                     WHERE e.datasource = 'gene2phenotype' AND e.variant_consequence IN ('SO_0002317', 'SO_0002315'))
        SELECT g2p.variant_consequence, g.risk_mechanism, count(*) AS n FROM g2p
        JOIN preclin.gene_disease_mechanism g ON g.ensembl_id = g2p.target_ensembl AND g.mondo_id = g2p.term
        GROUP BY 1, 2""")
    n["mechanism"]["g2p"] = {"absent_product": int(g2p[g2p.variant_consequence == "SO_0002317"].n.sum()),
                             "absent_product_lof": int(g2p[(g2p.variant_consequence == "SO_0002317")
                                                           & g2p.risk_mechanism.eq("loss_of_function")].n.sum()),
                             "absent_product_gof": int(g2p[(g2p.variant_consequence == "SO_0002317")
                                                           & g2p.risk_mechanism.eq("gain_of_function")].n.sum()),
                             "increased_product": int(g2p[g2p.variant_consequence == "SO_0002315"].n.sum()),
                             "increased_product_gof": int(g2p[(g2p.variant_consequence == "SO_0002315")
                                                              & g2p.risk_mechanism.eq("gain_of_function")].n.sum())}
    n["mouse"] = {"levels": {k: summary(g) for k, g in c2.groupby("mouse_direction")},
                  "vs_none": {k: versus(c2, "mouse_direction", k, "none") for k in ("concordant", "discordant", "mixed")},
                  "ko_mimics": estimate(c2, "s4", "mouse_ko_mimics"), "ko_opposes": estimate(c2, "s4", "mouse_ko_opposes"),
                  "concordant_beyond_g3": adjusted(c2.assign(x=c2.mouse_direction.eq("concordant").astype(float)),
                                                   "s4", ["x", "g3"]),
                  "c3": {k: versus(c3, "mouse_direction", k, "none") for k in ("concordant", "discordant")}}
    succ = c2[c2.s4 > 0]
    evidence = succ[["g3", "somatic", "mgi", "impc", "expression", "reactome", "crispr"]].max(axis=1) > 0
    n["coverage"] = {"successes": int(len(succ)), "with_g3": float((succ.g3 > 0).mean()),
                     "with_any_evidence": float(evidence.mean()), "with_b1": float((succ.b1 > 0).mean()),
                     "neither": float((~evidence & (succ.b1 == 0)).mean())}

    # The split and the case draws get their own generators, so they do not move with the analyses above.
    rule_table, exposed = rules(c2, np.random.default_rng(SEED))
    rule_table.to_csv(os.path.join(OUT, "rules.csv"), index=False)
    n["rules"] = {r["rule"]: r for r in rule_table.to_dict("records")}
    missed = set(frame.query("""SELECT o.nct_id FROM preclin.trial_outcome o JOIN preclin.ctgov_study s USING (nct_id)
                                 WHERE o.primary_endpoint IN ('not_met', 'mixed')
                                   AND s.allocation = 'RANDOMIZED'""").nct_id)
    cases = pick_cases(rule_table, exposed, missed, np.random.default_rng(SEED + 1))
    names = frame.query("SELECT moiety_id, name FROM preclin.moiety").set_index("moiety_id").name
    labels = frame.query("SELECT term_id, label FROM preclin.ontology_term WHERE ontology = 'MONDO'") \
                  .set_index("term_id").label
    cases = cases.assign(entity=cases.moiety_id.map(names), disease=cases.mondo_id.map(labels),
                         registered=cases.rule_key.map({k: v[3] for k, v in RULES.items()}))
    cases[["rule_key", "registered", "status", "why", "n_missed", "program_id", "entity", "target", "sign", "disease", "mondo_id",
           "entry", "event", "years", "s4", "reason", "reason_nct", "g3", "gwas", "gwas_strong", "mendelian",
           "somatic_concordant", "mgi", "reactome", "b1", "mechanism", "mouse_direction"]] \
        .to_csv(os.path.join(OUT, "cases.csv"), index=False)
    if os.path.exists(CASE_AUDIT):
        n["case_audit"] = case_audit(cases)
    d.drop(columns=["classes"]).to_csv(os.path.join(OUT, "programs.csv"), index=False)
    tf.to_csv(os.path.join(OUT, "trials.csv"), index=False)
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(jsonable(n), f, indent=1)


if __name__ == "__main__":
    main()
