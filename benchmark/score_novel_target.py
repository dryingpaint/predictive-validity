"""Score novel (not-yet-clinical) target x indication hypotheses.

Every scorer in this repo evaluates T-I pairs that are ALREADY in the cohort
(>=1 Phase 1+ program). This tool answers a different, earlier question: "if
we started a drug program against this gene, for this indication, today, how
would the model rate it?" -- i.e. genuine out-of-cohort extrapolation for
preclinical target scoping.

WHY THIS EXISTS AND ISN'T JUST "CALL THE EXISTING SCORER":

1. Target-level vs T-I-level evidence. `preclin.v_target_evidence_wide` (what
   every scorer in scorers_ml.py consumes) is TARGET-level: "best genetic /
   animal-model evidence found for this gene against ANY disease." That's
   fine for the existing cohort (every row already has a real, matched
   indication from an actual drug program). It is WRONG for a novel
   hypothesis: naively plugging a new gene's target-level row in silently
   credits genetics from a disease you are not actually pursuing. This tool
   re-derives Category A (genetics) and Category D (animal) evidence scoped
   to the SPECIFIC indication_id being scored, by name-matching against
   public.target_evidence / mendelian_associations / gwas_associations /
   clingen_validity, and leaves those features NaN (missing, median-imputed
   by the trained pipeline) when no disease-specific row exists at all --
   which, empirically, is most of them for genuinely novel hypotheses. That
   null IS the finding; do not "fix" it by falling back to the target-level
   aggregate.

2. nelson_tier LEAKAGE. Do not set nelson_tier for a novel, uncurated target.
   Empirically (2026-08-10, Phase 1+ strict cohort, n=13,639): 97%+ of T-I
   pairs have nelson_tier=NULL at the cohort base rate (~3%), but the tiny
   minority with ANY tier assigned at all -- T0 included, nominally "no
   genetic evidence" -- sits at ~90-100% approval. Nelson-tier annotations
   come from a curated case series built around ALREADY-KNOWN drugs, so
   "has a tier assigned" is a proxy for "this is a famous/successful
   program," not a real evidence signal. Assigning ANY tier to a novel
   target (even out of an instinct to be "conservative" with T0) puts it in
   that ultra-high-success curated bucket by pure selection artifact and
   the model will return ~0.99 for everything. `score()` below refuses to
   accept a nelson_tier override without an explicit, loud acknowledgment.

Usage:
    python3 benchmark/score_novel_target.py --csv path/to/pairs.csv --out results.json
    python3 benchmark/score_novel_target.py --gene SIK3 --indication "Idiopathic Hypersomnia" \\
        --area other

CSV columns: symbol,indication,therapeutic_area,aliases,note
  aliases: pipe-separated extra disease-name search terms (for indications
  with no single matching Open Targets disease, e.g. "Sleep Disorders" ->
  "Narcolepsy|Insomnia|Obstructive sleep apnea"). Optional.
"""
import argparse
import csv
import json
import os
import sys

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
_ml = import_module("scorers_ml")
_ens = import_module("scorers_ensemble")

DB_URL = os.environ["DATABASE_URL"]

THERAPEUTIC_AREAS = set(_ml.THERAPEUTIC_AREAS)

# Same cohort as analyses/final_benchmark.py's headline logreg_final_v1 run --
# Phase 1+, strict per-indication outcome, no phase filter beyond "entered
# clinic at all." Using the full cohort (not CV) because we are extrapolating
# to brand-new points, not estimating held-out performance.
PHASE1_SQL = """
    SELECT s.target_id, s.indication_id,
      s.strict_approved_this_ti AS y_strict,
      s.first_trial_date, s.max_phase_reached,
      s.n_programs, s.n_sponsors,
      i.therapeutic_area, tw.*,
      (SELECT value_text FROM preclin.evidence_score
        WHERE subject_type='target_indication' AND subject_id = s.target_id
          AND subject_id2 = s.indication_id AND dimension = 'nelson_tier'
        LIMIT 1) AS nelson_tier
    FROM preclin.v_target_indication_strict_outcome s
    JOIN public.targets t ON t.id = s.target_id
    JOIN preclin.indication i ON i.indication_id = s.indication_id
    JOIN preclin.v_target_evidence_wide tw ON tw.target_id = s.target_id
    WHERE s.max_phase_reached >= 1
      AND (t.pathogen_type IS NULL OR t.pathogen_type = '')
      AND s.outcomes_broad_all NOT SIMILAR TO 'in_dev%%'
"""

TI_NUMERIC_OVERRIDE = [
    "ot_genetic_max", "ot_somatic_score_max", "ot_rna_expression_max",
    "ot_l2g_score_max", "ot_animal_model_max",
]
TI_BOOL_OVERRIDE = ["ot_is_mendelian_any"]
TI_COUNT_OVERRIDE = ["mendelian_n", "mendelian_n_dominant", "mendelian_n_recessive",
                     "gwas_n_sig", "clingen_n_strong"]


class NovelTargetScorer:
    """Fit once on the full Phase 1+ cohort, score many novel T-I pairs."""

    def __init__(self, conn=None):
        self.conn = conn or psycopg2.connect(DB_URL)
        self._fit()

    def _fit(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(PHASE1_SQL)
            rows = cur.fetchall()
        X = np.stack([_ml.row_to_feature_vector(r) for r in rows])
        y = np.array([1 if r["y_strict"] else 0 for r in rows], dtype=np.int64)
        self.X_log = _ens.log_transform_features(X, _ml.FEATURE_NAMES)
        self.y = y
        self.n_cohort = len(rows)
        self.base_rate = float(y.mean())
        self.model = _ens.make_logreg_l2()  # == logreg_final_v1's base model
        self.model.fit(self.X_log, y)
        self.cohort_p = self.model.predict_proba(self.X_log)[:, 1]

    # -- resolution -------------------------------------------------------

    def resolve_target(self, symbol):
        """Best target_id for a gene symbol. public.targets has duplicate
        stub rows for some symbols (no tdl/tractability populated) alongside
        the real annotated row -- prefer the richer one."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, symbol, tdl, tractability_sm, tractability_ab
                FROM public.targets WHERE symbol = %s
                ORDER BY (tdl IS NOT NULL) DESC,
                         (tractability_sm OR tractability_ab) DESC,
                         id ASC
            """, (symbol,))
            rows = cur.fetchall()
        if not rows:
            return None, []
        return rows[0]["id"], rows

    def resolve_diseases(self, indication_name, aliases=None):
        """Disease_id(s) in public.diseases matching indication_name or any
        alias. Tries exact (case-insensitive) match per term first; falls
        back to substring match. Returns (disease_ids, matched_rows,
        match_quality) where match_quality in {'exact','fuzzy','none'}."""
        terms = [indication_name] + list(aliases or [])
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name FROM public.diseases WHERE name ILIKE ANY(%s)",
                        (terms,))
            exact = cur.fetchall()
            if exact:
                return [r["id"] for r in exact], exact, "exact"
            like_terms = [f"%{t}%" for t in terms]
            cur.execute("SELECT id, name FROM public.diseases WHERE name ILIKE ANY(%s)",
                        (like_terms,))
            fuzzy = cur.fetchall()
            if fuzzy:
                return [r["id"] for r in fuzzy], fuzzy, "fuzzy"
        return [], [], "none"

    # -- feature construction ----------------------------------------------

    def _target_level_row(self, target_id):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM preclin.v_target_evidence_wide WHERE target_id = %s",
                        (target_id,))
            return cur.fetchone()

    def _ti_scoped_override(self, target_id, disease_ids):
        out = {k: np.nan for k in TI_NUMERIC_OVERRIDE}
        out.update({k: np.nan for k in TI_BOOL_OVERRIDE})
        out.update({k: 0 for k in TI_COUNT_OVERRIDE})
        if not disease_ids:
            return out, []

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT d.name, te.genetic_score, te.somatic_score, te.rna_expression_score,
                       te.l2g_score, te.animal_model_score, te.is_mendelian
                FROM public.target_evidence te JOIN public.diseases d ON d.id = te.disease_id
                WHERE te.target_id = %s AND te.disease_id = ANY(%s)
            """, (target_id, disease_ids))
            te_rows = cur.fetchall()

        matched_names = [r["name"] for r in te_rows]
        if te_rows:
            def best(col):
                vals = [r[col] for r in te_rows if r[col] is not None]
                return max(vals) if vals else np.nan
            out["ot_genetic_max"] = best("genetic_score")
            out["ot_somatic_score_max"] = best("somatic_score")
            out["ot_rna_expression_max"] = best("rna_expression_score")
            out["ot_l2g_score_max"] = best("l2g_score")
            out["ot_animal_model_max"] = best("animal_model_score")
            out["ot_is_mendelian_any"] = any(r["is_mendelian"] for r in te_rows)

            match_terms = [f"%{n}%" for n in matched_names]
            with self.conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM public.mendelian_associations "
                            "WHERE target_id=%s AND phenotype_name ILIKE ANY(%s)",
                            (target_id, match_terms))
                out["mendelian_n"] = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM public.gwas_associations "
                            "WHERE target_id=%s AND trait ILIKE ANY(%s)",
                            (target_id, match_terms))
                out["gwas_n_sig"] = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM public.clingen_validity "
                            "WHERE target_id=%s AND disease_name ILIKE ANY(%s) "
                            "AND classification IN ('Definitive','Strong')",
                            (target_id, match_terms))
                out["clingen_n_strong"] = cur.fetchone()[0]
        return out, matched_names

    # -- public API ----------------------------------------------------------

    def score(self, symbol, indication, therapeutic_area, aliases=None,
              nelson_tier=None, i_acknowledge_the_nelson_tier_leakage_risk=False):
        if therapeutic_area not in THERAPEUTIC_AREAS:
            raise ValueError(f"therapeutic_area must be one of {sorted(THERAPEUTIC_AREAS)}, "
                              f"got {therapeutic_area!r}")
        if nelson_tier is not None and not i_acknowledge_the_nelson_tier_leakage_risk:
            raise ValueError(
                "Refusing to set nelson_tier without "
                "i_acknowledge_the_nelson_tier_leakage_risk=True. Read the LEAKAGE "
                "warning in this module's docstring first -- assigning ANY tier to an "
                "uncurated target (T0 included) will push p(approval) towards ~0.99 "
                "as a pure selection artifact, not a real signal."
            )

        warnings = []
        target_id, target_candidates = self.resolve_target(symbol)
        if target_id is None:
            return {"symbol": symbol, "indication": indication, "error":
                     f"no target found in public.targets for symbol={symbol!r}"}

        disease_ids, disease_rows, match_quality = self.resolve_diseases(indication, aliases)
        if match_quality == "none":
            warnings.append(f"no Open Targets disease matched {indication!r} "
                             f"(or aliases {aliases!r}) -- Category A/D fully null")
        elif match_quality == "fuzzy":
            warnings.append(f"only fuzzy disease-name matches found: "
                             f"{[r['name'] for r in disease_rows]} -- verify relevance")

        wide = self._target_level_row(target_id)
        if wide is None:
            return {"symbol": symbol, "indication": indication, "error":
                     f"no v_target_evidence_wide row for target_id={target_id}"}

        ti_override, matched_disease_names = self._ti_scoped_override(target_id, disease_ids)
        if disease_ids and not matched_disease_names:
            warnings.append(f"disease(s) matched by name ({[r['name'] for r in disease_rows]}) "
                             f"but target has NO target_evidence row for any of them -- "
                             f"Category A/D fully null for this specific pair")

        row = dict(wide)
        row["therapeutic_area"] = therapeutic_area
        row["nelson_tier"] = nelson_tier
        row.update(ti_override)

        x = _ml.row_to_feature_vector(row).reshape(1, -1)
        x_log = _ens.log_transform_features(x, _ml.FEATURE_NAMES)
        p = float(self.model.predict_proba(x_log)[0, 1])
        pctile = float((self.cohort_p < p).mean() * 100)

        return {
            "symbol": symbol, "target_id": target_id, "indication": indication,
            "therapeutic_area": therapeutic_area,
            "matched_diseases": matched_disease_names,
            "disease_match_quality": match_quality,
            "p_approval": p, "cohort_percentile": pctile,
            "cohort_base_rate": self.base_rate, "n_cohort": self.n_cohort,
            "warnings": warnings,
        }


def _read_csv(path):
    pairs = []
    with open(path) as f:
        for row in csv.DictReader(f):
            aliases = [a.strip() for a in row.get("aliases", "").split("|") if a.strip()]
            pairs.append({
                "symbol": row["symbol"].strip(),
                "indication": row["indication"].strip(),
                "therapeutic_area": row["therapeutic_area"].strip(),
                "aliases": aliases,
                "note": row.get("note", "").strip(),
            })
    return pairs


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", help="CSV of symbol,indication,therapeutic_area,aliases,note")
    ap.add_argument("--gene", help="single-pair mode: gene symbol")
    ap.add_argument("--indication", help="single-pair mode: indication name")
    ap.add_argument("--area", choices=sorted(THERAPEUTIC_AREAS),
                     help="single-pair mode: therapeutic area")
    ap.add_argument("--aliases", default="", help="single-pair mode: pipe-separated aliases")
    ap.add_argument("--out", help="write JSON results here")
    args = ap.parse_args()

    if args.csv:
        pairs = _read_csv(args.csv)
    elif args.gene and args.indication and args.area:
        pairs = [{"symbol": args.gene, "indication": args.indication,
                  "therapeutic_area": args.area,
                  "aliases": [a for a in args.aliases.split("|") if a],
                  "note": ""}]
    else:
        ap.error("provide --csv, or --gene/--indication/--area for single-pair mode")

    scorer = NovelTargetScorer()
    print(f"Trained on Phase 1+ strict cohort: n={scorer.n_cohort}, "
          f"base_rate={scorer.base_rate:.4f}\n")

    results = []
    for pair in pairs:
        r = scorer.score(pair["symbol"], pair["indication"], pair["therapeutic_area"],
                          aliases=pair.get("aliases"))
        r["note"] = pair.get("note", "")
        results.append(r)

    print(f"{'Symbol':10} {'Indication':24} {'Matched disease(s)':28} {'p(approval)':>11} {'%ile':>6}")
    print("-" * 90)
    for r in results:
        if "error" in r:
            print(f"{r['symbol']:10} {r['indication']:24} ERROR: {r['error']}")
            continue
        md = ", ".join(r["matched_diseases"]) or "(none)"
        print(f"{r['symbol']:10} {r['indication']:24} {md[:28]:28} "
              f"{r['p_approval']:11.4f} {r['cohort_percentile']:5.1f}%")
        for w in r["warnings"]:
            print(f"    ! {w}")

    if args.out:
        with open(args.out, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
