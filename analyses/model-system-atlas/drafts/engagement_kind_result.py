"""Does the KIND of engagement evidence track what happened to the class? Grades the human readout behind
each context's engagement cell and joins it to the DB's Phase 2 and Phase 3 advancement of the context's
drug class (context_outcomes.csv, from engagement_outcomes.py). No DB access here.

    .venv/bin/python analyses/model-system-atlas/drafts/engagement_kind_result.py

Reads matrix_cells.csv and context_outcomes.csv; writes engagement_experiment.csv (one row per context) and
prints the tables recorded in ENGAGEMENT_KIND_RESULT.md. Rates are over resolved programs (advanced +
suspended; censored excluded), Wilson 95% intervals, two-sided Fisher exact tests. The within-atlas arm
(efficacy cell by tier) is a consistency check: the same drafters read the trial results.

Tier of the readout, assigned by hand from each entry's `model`, `quote` and `note` after the run, one per
context:
  direct     = occupancy / free target / ex-vivo blockade of a stimulus in dosed humans
  proximal   = the product of the target itself (transgene protein, viral load, enzyme product, acid, cGMP)
  downstream = a biomarker or physiology further down the pathway
"""
import math
import os

import pandas as pd
from scipy.stats import fisher_exact

HERE = os.path.dirname(os.path.abspath(__file__))

TIER = {
    # direct
    "acute-myeloid-leukemia--flt3-inhibitors": "direct",
    "allergic-rhinitis--ptgdr2-antagonists": "direct",
    "asthma--ptgdr2-antagonists": "direct",
    "rheumatoid-arthritis--btk-inhibitors": "direct",
    "malignant-pancreatic-neoplasm--map2k1-inhibitors": "direct",
    "ovarian-cancer--parp1-inhibitors": "direct",
    "paroxysmal-nocturnal-hemoglobinuria--anti-c5-antibodies": "direct",
    "coronary-artery-disorder--p2ry12-antagonists": "direct",
    "alzheimer-disease--anti-mapt-antibodies": "direct",
    "hypertriglyceridemia--apoc3-antisense-sirna": "direct",
    "hyperlipidemia--cetp-inhibitors": "direct",
    "migraine-disorder--calcrl-antagonists": "direct",
    "hypertensive-disorder--agtr1-antagonists": "direct",
    "breast-cancer--erbb2-inhibitors": "direct",
    "melanoma--braf-inhibitors": "direct",
    # proximal
    "hema-fviii-gt": "proximal",
    "hemophilia-b--f9-replacement-gene-therapy": "proximal",
    "sickle-cell-disease--hbb-replacement-gene-therapy": "proximal",
    "chronic-hepatitis-b-virus-infection--core-antigen-inhibitor": "proximal",
    "hepatitis-c-virus-infection--hepatitis-c-virus-serine-protea": "proximal",
    "hiv-infectious-disease--human-immunodeficiency-virus-type-1-": "proximal",
    "gastroesophageal-reflux-disease--atp4a-blockers": "proximal",
    "heart-failure--npr1-agonists": "proximal",
    "irritable-bowel-syndrome--tph1-inhibitors": "proximal",
    "type-2-diabetes-mellitus--glp1r-agonists": "proximal",
    "influenza--hemagglutinin-inhibitor": "proximal",
    # downstream
    "cystic-fibrosis--cftr-positive-modulators": "downstream",
    "chronic-obstructive-pulmonary-disease--chrm3-antagonists": "downstream",
    "primary-biliary-cholangitis--nr1h4-agonists": "downstream",
    "secondary-hyperparathyroidism--casr-positive-modulators": "downstream",
    "type-1-diabetes-mellitus--slc5a2-inhibitors": "downstream",
    "ulcerative-colitis--s1pr1-agonists": "downstream",
    "ipf-il13": "downstream",
    "eosinophilic-esophagitis--anti-il13-antibodies": "downstream",
    "psoriasis--anti-il17a-antibodies": "downstream",
    "insomnia--hcrtr2-antagonists": "downstream",
    "major-depressive-disorder--grin2b-antagonists": "downstream",
    "attention-deficit-hyperactivity-disorder--slc6a2-inhibitors": "downstream",
    "obesity-disorder--glp1r-agonists": "downstream",
    "prostate-cancer--ar-antagonists": "downstream",
    "plasma-cell-myeloma--tnfrsf17-directed-depleters": "downstream",
    "follicular-lymphoma--cd19-directed-depleters": "downstream",
    "age-related-macular-degeneration--anti-vegfa-antibodies": "downstream",
    "nsclc-egfr": "downstream",
}
# the four pilot contexts are keyed by short draft ids in matrix_cells.csv and by manifest id in context_outcomes.csv
ALIAS = {"hema-fviii-gt": "hemophilia-a--f8-replacement-gene-therapy",
         "ipf-il13": "idiopathic-pulmonary-fibrosis--anti-il13-antibodies",
         "nsclc-egfr": "non-small-cell-lung-carcinoma--egfr-inhibitors",
         "scz-pde10a": "schizophrenia--pde10a-inhibitors"}
TIERS = ["direct", "proximal", "downstream", "contra", "none"]
LABEL = {"direct": "target itself (occupancy, free target, ex-vivo blockade)",
         "proximal": "target's product (transgene protein, viral load, acid, cGMP)",
         "downstream": "downstream biomarker or physiology",
         "contra": "engagement contradicted", "none": "no engagement comparison"}


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


def pct(k, n):
    return f"{100 * k / n:.0f}%" if n else "–"


def ci(k, n):
    lo, hi = wilson(k, n)
    return f"{100 * lo:.0f}–{100 * hi:.0f}%" if n else "–"


def tiers_from_matrix():
    cells = pd.read_csv(os.path.join(HERE, "matrix_cells.csv"))
    cells = cells[cells.checked.astype(str) == "True"]
    status = cells.pivot(index="context", columns="question", values="status_checked")
    untiered = [c for c, s in status.engagement.items() if s in ("same", "neg") and c not in TIER]
    if untiered:
        raise SystemExit(f"matched engagement cells without a tier: {untiered}")
    return pd.DataFrame({
        "context": [ALIAS.get(c, c) for c in status.index],
        "engagement": status.engagement.values,
        "tier": [TIER[c] if s in ("same", "neg") else ("contra" if s == "contra" else "none")
                 for c, s in status.engagement.items()],
        "efficacy": status.efficacy.values, "safety": status.safety.values, "dose": status.dose.values,
    })


def main():
    tiers = tiers_from_matrix()
    outc = pd.read_csv(os.path.join(HERE, "context_outcomes.csv"))
    d = outc.merge(tiers, on="context", how="inner")
    missing = sorted(set(outc.context) ^ set(tiers.context))
    d.to_csv(os.path.join(HERE, "engagement_experiment.csv"), index=False)
    print(f"{len(d)} contexts joined" + (f" (unjoined: {missing})" if missing else ""))

    def table(ph, title):
        print(f"\n## {title}\n")
        print("| engagement readout | contexts | programs resolved | advanced | rate (95% CI) |\n|---|---|---|---|---|")
        agg = {}
        for t in TIERS:
            g = d[d.tier == t]
            a, s = int(g[f"{ph}_advanced"].sum()), int(g[f"{ph}_suspended"].sum())
            agg[t] = (a, s)
            print(f"| {LABEL[t]} | {len(g)} | {a + s} | {a} | {pct(a, a + s)} ({ci(a, a + s)}) |")

        def pool(ts):
            return sum(agg[t][0] for t in ts), sum(agg[t][1] for t in ts)
        da, ds = pool(["direct"]); ia, is_ = pool(["proximal", "downstream"])
        ma, ms = pool(["direct", "proximal", "downstream"]); na, ns = pool(["none"])
        pa, ps = pool(["proximal"]); wa, ws = pool(["downstream"])
        p1, p2 = da / (da + ds), ia / (ia + is_)
        se = math.sqrt(p1 * (1 - p1) / (da + ds) + p2 * (1 - p2) / (ia + is_))
        print(f"\n- direct vs inferred (product + downstream): {pct(da, da + ds)} vs {pct(ia, ia + is_)}, difference "
              f"{100 * (p1 - p2):+.0f} points ({100 * (p1 - p2 - 1.96 * se):+.0f} to {100 * (p1 - p2 + 1.96 * se):+.0f}), "
              f"Fisher p = {fisher_exact([[da, ds], [ia, is_]])[1]:.2f}")
        print(f"- product vs downstream: Fisher p = {fisher_exact([[pa, ps], [wa, ws]])[1]:.2f}")
        print(f"- any matched engagement vs none: {pct(ma, ma + ms)} vs {pct(na, na + ns)}, "
              f"Fisher p = {fisher_exact([[ma, ms], [na, ns]])[1]:.3f} (survivorship; not a test of the evidence)")

    table("ph2", "Phase 2 entrants 2008–2019 of the context's class: advanced to Phase 3")
    table("ph3", "Phase 3 entrants of the context's class: advanced")

    print("\n## Within the atlas: efficacy cell by engagement readout (contexts whose efficacy was compared)\n")
    print("| engagement readout | efficacy compared | efficacy matched |\n|---|---|---|")
    for t in TIERS:
        g = d[(d.tier == t) & d.efficacy.isin(["same", "neg", "other", "contra"])]
        m = int((g.efficacy != "contra").sum())
        print(f"| {LABEL[t]} | {len(g)} | {m} ({pct(m, len(g))}) |")


if __name__ == "__main__":
    main()
