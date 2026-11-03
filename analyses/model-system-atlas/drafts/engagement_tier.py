"""Small experiment: does the KIND of engagement evidence track later outcomes?

    .venv/bin/python analyses/model-system-atlas/drafts/engagement_tier.py

Tier of the human readout behind each engagement cell, assigned by hand from the entry's `model`,
`quote` and `note` (read after the run; no re-research):
  direct    = occupancy / free target / ex-vivo blockade of a stimulus in dosed humans
  proximal  = the product of the target itself (transgene protein, viral load, enzyme product, acid, cGMP)
  downstream = a biomarker or physiology further down the pathway
Writes engagement_tiers.csv and prints tier x efficacy / safety cross-tabs over the checked contexts.
"""
import csv
import os
from collections import Counter, defaultdict

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


def main():
    cells = [r for r in csv.DictReader(open(os.path.join(HERE, "matrix_cells.csv"))) if r["checked"] == "True"]
    ctx = defaultdict(dict)
    for r in cells:
        ctx[r["context"]][r["question"]] = r["status_checked"]
    matched = [c for c, q in ctx.items() if q.get("engagement") in ("same", "neg")]
    unknown = [c for c in matched if c not in TIER]
    if unknown:
        print("UNTIERED matched engagement cells:", unknown)
    rows = []
    for c, q in ctx.items():
        eng = q.get("engagement")
        tier = TIER.get(c) if eng in ("same", "neg") else ("contra" if eng == "contra" else "none")
        rows.append({"context": c, "engagement": eng, "tier": tier, "efficacy": q.get("efficacy"), "safety": q.get("safety"), "dose": q.get("dose")})
    with open(os.path.join(HERE, "engagement_tiers.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    def tri(s):
        return {"same": "matched", "neg": "matched", "other": "matched", "contra": "contradicted", "untested": "never compared"}.get(s, "no model")
    for outcome in ("efficacy", "safety"):
        print(f"\nEngagement evidence tier x {outcome} status (latest, checker-corrected)")
        print("| tier | n | matched | contradicted | never compared | no model |")
        print("|---|---|---|---|---|---|")
        for t in ("direct", "proximal", "downstream", "contra", "none"):
            g = [r for r in rows if r["tier"] == t]
            c = Counter(tri(r[outcome]) for r in g)
            n = len(g)
            def cell(k):
                return f"{c[k]} ({100*c[k]/n:.0f}%)" if n else "-"
            label = {"contra": "engagement contradicted", "none": "engagement never compared / no model"}.get(t, t)
            print(f"| {label} | {n} | {cell('matched')} | {cell('contradicted')} | {cell('never compared')} | {cell('no model')} |")
    # tested-only conditional: among contexts where efficacy WAS compared, share matched
    print("\nAmong contexts whose efficacy was compared (matched or contradicted): share matched, by engagement tier")
    for t in ("direct", "proximal", "downstream", "contra", "none"):
        g = [r for r in rows if r["tier"] == t and r["efficacy"] in ("same", "neg", "other", "contra")]
        m = sum(r["efficacy"] != "contra" for r in g)
        print(f"  {t:11s} {m}/{len(g)}" + (f" = {100*m/len(g):.0f}%" if g else ""))


if __name__ == "__main__":
    main()
