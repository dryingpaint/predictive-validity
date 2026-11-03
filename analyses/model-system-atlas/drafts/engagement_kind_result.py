"""Does the KIND of engagement evidence track what happened to the class? Joins the atlas's engagement
tiers (engagement_tier.py -> engagement_tiers.csv) to the DB's Phase 2 and Phase 3 advancement of each
context's drug class (engagement_outcomes.py -> context_outcomes.csv). No DB access here.

    .venv/bin/python analyses/model-system-atlas/drafts/engagement_kind_result.py

Writes engagement_experiment.csv (the join, one row per context) and engagement_kind_result.md (tables).
Rates are over resolved programs only (advanced + suspended; censored excluded), Wilson 95% intervals,
two-sided Fisher exact tests. The within-atlas arm (efficacy cell by tier) is a consistency check: the
same drafters read the trial results.
"""
import math
import os

import pandas as pd
from scipy.stats import fisher_exact

HERE = os.path.dirname(os.path.abspath(__file__))
TIERS = ["direct", "proximal", "downstream", "contra", "none"]
# matrix_cells.csv keys the four pilot contexts by their short draft ids; context_outcomes.csv by manifest id
ALIAS = {"hema-fviii-gt": "hemophilia-a--f8-replacement-gene-therapy",
         "ipf-il13": "idiopathic-pulmonary-fibrosis--anti-il13-antibodies",
         "nsclc-egfr": "non-small-cell-lung-carcinoma--egfr-inhibitors",
         "scz-pde10a": "schizophrenia--pde10a-inhibitors"}
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


def main():
    tiers = pd.read_csv(os.path.join(HERE, "engagement_tiers.csv"))
    tiers["context"] = tiers.context.replace(ALIAS)
    outc = pd.read_csv(os.path.join(HERE, "context_outcomes.csv"))
    d = outc.merge(tiers, on="context", how="inner")
    missing = sorted(set(outc.context) - set(tiers.context)) + sorted(set(tiers.context) - set(outc.context))
    d.to_csv(os.path.join(HERE, "engagement_experiment.csv"), index=False)

    lines = ["# Engagement evidence kind vs class outcome", "",
             f"_{len(d)} contexts joined (unjoined: {missing or 'none'}). Rates over resolved programs; Wilson 95% CI._", ""]

    def table(ph, title):
        lines.extend([f"## {title}", "", "| engagement readout | contexts | programs resolved | advanced | rate (95% CI) |",
                      "|---|---|---|---|---|"])
        agg = {}
        for t in TIERS:
            g = d[d.tier == t]
            a, s = int(g[f"{ph}_advanced"].sum()), int(g[f"{ph}_suspended"].sum())
            agg[t] = (a, s)
            lines.append(f"| {LABEL[t]} | {len(g)} | {a + s} | {a} | {pct(a, a + s)} ({ci(a, a + s)}) |")
        lines.append("")

        def pool(ts):
            return sum(agg[t][0] for t in ts), sum(agg[t][1] for t in ts)
        da, ds = pool(["direct"]); ia, is_ = pool(["proximal", "downstream"])
        ma, ms = pool(["direct", "proximal", "downstream"]); na, ns = pool(["none"])
        pa, ps = pool(["proximal"]); wa, ws = pool(["downstream"])
        p1, p2 = da / (da + ds), ia / (ia + is_)
        se = math.sqrt(p1 * (1 - p1) / (da + ds) + p2 * (1 - p2) / (ia + is_))
        lines.extend([
            f"- direct vs inferred (product + downstream): {pct(da, da + ds)} vs {pct(ia, ia + is_)}, difference "
            f"{100 * (p1 - p2):+.0f} points ({100 * (p1 - p2 - 1.96 * se):+.0f} to {100 * (p1 - p2 + 1.96 * se):+.0f}), "
            f"Fisher p = {fisher_exact([[da, ds], [ia, is_]])[1]:.2f}",
            f"- product vs downstream: Fisher p = {fisher_exact([[pa, ps], [wa, ws]])[1]:.2f}",
            f"- any matched engagement vs none: {pct(ma, ma + ms)} vs {pct(na, na + ns)}, "
            f"Fisher p = {fisher_exact([[ma, ms], [na, ns]])[1]:.3f} (survivorship: not a test of the evidence)", ""])

    table("ph2", "Phase 2 entrants 2008–2019 of the context's class: advanced to Phase 3")
    table("ph3", "Phase 3 entrants of the context's class: advanced")

    lines.extend(["## Within the atlas: efficacy cell by engagement readout (contexts whose efficacy was compared)", "",
                  "| engagement readout | efficacy compared | efficacy matched |", "|---|---|---|"])
    for t in TIERS:
        g = d[(d.tier == t) & d.efficacy.isin(["same", "neg", "other", "contra"])]
        m = int((g.efficacy != "contra").sum())
        lines.append(f"| {LABEL[t]} | {len(g)} | {m} ({pct(m, len(g))}) |")
    lines.extend(["", "_Same drafters read the trial results, so this arm is a consistency check, not evidence._", ""])
    open(os.path.join(HERE, "engagement_kind_result.md"), "w").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
