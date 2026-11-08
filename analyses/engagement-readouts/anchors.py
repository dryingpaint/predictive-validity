"""Layer 2 bookkeeping: collapse the step 3 scope into readout families, cut the anchor-research batches, merge
the results into anchors.csv.

    .venv/bin/python analyses/engagement-readouts/anchors.py todo [--batch 7]   # families.csv, batches/anchor_todo_NN.csv
    .venv/bin/python analyses/engagement-readouts/anchors.py merge             # batches/anchor_done_NN.csv -> anchors.csv

A family is one (target, readout) pair the anchor question is asked of once. FAMILY maps canonical readout
names that mean the same measurement, or that the first-symbol naming rule filed under the wrong target, onto
one family; every other canonical name is its own family. Rows with no usable readout get no family.
"""
import argparse
import glob
import os
from datetime import date

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SCOPE = os.path.join(HERE, "step3_scope.csv")
FAMILIES = os.path.join(HERE, "families.csv")
ANCHORS = os.path.join(HERE, "anchors.csv")
BATCHES = os.path.join(HERE, "batches")
NO_FAMILY_KINDS = {"none", "exposure_only"}

FAMILY = {
    "AGTR1:renin_dependent_bp_lowering": "AGTR1:bp_lowering",
    "AR:psa50_response": "AR:psa",
    "ATP4A:acid_reflux": "ATP4A:gastric_ph",
    "AURKA:plasma_svegfr2": "KDR:plasma_svegfr2", "FLT1:plasma_svegfr2": "KDR:plasma_svegfr2",
    "FLT1:svegfr2_lowering": "KDR:plasma_svegfr2", "FGFR1:svegfr2_lowering": "KDR:plasma_svegfr2",
    "FGFR1:dce_mri_vascularity": "KDR:dce_mri",
    "AVPR1A:serum_sodium_osmolality": "AVPR2:aquaresis",
    "BACE1:csf_abeta_reduction": "BACE1:csf_abeta",
    "CD274:nk_cd8_expansion": "IL2RB:nk_cd8_expansion", "IL2RB:nk_cd8_activation": "IL2RB:nk_cd8_expansion",
    "CD274:ox40_cell_egress_ki67": "TNFRSF4:ox40_cell_egress",
    "CHRM3:salivary_secretion": "CHRM3:salivary_flow",
    "CSF1R:flt3_phosphorylation_inhibition": "FLT3:flt3_phosphorylation",
    "CSF3R:neutrophil_response": "CSF3R:neutrophil_count",
    "DGAT1:fasting_tg": "DGAT1:triglycerides", "DGAT1:postprandial_tg": "DGAT1:triglycerides",
    "FGFR1:adiponectin": "FGF21:adiponectin", "FGFR1:adiponectin_bhb": "FGF21:adiponectin",
    "FGFR1:hepatic_fat_fraction": "FGF21:hepatic_fat", "FGFR1:phosphate_fgf19": "FGFR1:serum_phosphate",
    "FGFR4:liver_fat_reduction": "FGF19:hepatic_fat", "FGFR4:serum_c4": "FGF19:serum_c4",
    "FGFR4:c4_bile_acid_fgf19": "FGFR4:c4_bile_acids",
    "GHSR:gh_cortisol_prolactin_rise": "GHSR:gh_release",
    "IFNAR1:innate_immune_biomarkers": "IFNAR1:isg_induction",
    "IL13:pd_biomarkers_unnamed": "IL13:periostin_ccl17", "IL13:serum_periostin_ccl13_ccl17": "IL13:periostin_ccl17",
    "IL13:serum_tarc_ccl17": "IL13:periostin_ccl17",
    "IL5RA:tissue_eosinophils": "IL5RA:eosinophil_depletion",
    "IL7R:tcell_cycling_cd4_cd8_expansion": "IL7R:tcell_expansion", "IL7R:lymphocyte_expansion": "IL7R:tcell_expansion",
    "INS:granzyme_b_cd4_expansion": "INS:antigen_specific_tcells", "INS:proinsulin_reactive_cd8": "INS:antigen_specific_tcells",
    "INSR:clamp_glucose_infusion_rate": "INSR:glucose_lowering", "INSR:fasting_plasma_glucose": "INSR:glucose_lowering",
    "JAK1:gut_pstat3": "JAK1:pstat", "JAK1:pstat_inhibition": "JAK1:pstat",
    "MAP2K1:perk_suppression": "MAP2K1:perk",
    "MAPK14:ex_vivo_lps_cytokine_inhibition": "MAPK14:lps_tnf_inhibition", "MAPK14:ex_vivo_lps_tnfa_inhibition": "MAPK14:lps_tnf_inhibition",
    "MAPK14:lps_sputum_tnfa": "MAPK14:lps_tnf_inhibition", "MAPK14:p_hsp27_inhibition": "MAPK14:phsp27",
    "MDM2:gdf15_induction": "MDM2:mic1_gdf15", "MDM2:mic1_induction": "MDM2:mic1_gdf15", "MDM2:serum_mic1": "MDM2:mic1_gdf15",
    "NPR1:plasma_urine_cgmp": "NPR1:cgmp", "NPR1:plasma_cgmp": "NPR1:cgmp",
    "PIK3CA:pakt_inhibition": "PIK3CA:platelet_pakt",
    "PPARA:plasma_adiponectin": "PPARG:adiponectin", "PPARG:plasma_adiponectin": "PPARG:adiponectin",
    "PPARD:muscle_fatty_acid_gene_upregulation": "PPARD:target_genes", "PPARD:target_gene_upregulation": "PPARD:target_genes",
    "S1PR1:lymphocyte_reduction": "S1PR1:lymphocyte_count", "S1PR1:peripheral_lymphocyte_count": "S1PR1:lymphocyte_count",
    "S1PR1:peripheral_lymphocytes": "S1PR1:lymphocyte_count",
    "SLC40A1:serum_iron_tsat": "SLC40A1:serum_iron",
    "TLR7:interferon_cytokine_induction": "TLR7:ifn_induction", "TLR7:ip10_induction": "TLR7:ifn_induction",
    "TLR7:skin_ifn_mx_induction": "TLR7:ifn_induction", "TLR7:skin_il6_mxa_induction": "TLR7:ifn_induction",
    "TLR9:blood_cytokine_induction": "TLR9:ifn_ip10_induction", "TLR9:interferon_response_induction": "TLR9:ifn_ip10_induction",
    "TLR9:ip10_monocyte_activation": "TLR9:ifn_ip10_induction", "TLR9:monocyte_activation_ip10": "TLR9:ifn_ip10_induction",
    "TLR9:serum_cxcl10": "TLR9:ifn_ip10_induction",
    "TNNC2:calf_muscle_performance": "TNNC2:muscle_performance",
}
OUT_COLS = ["family", "anchor", "anchor_year", "anchor_source", "anchor_quote", "anchor_detail", "other_movers",
            "specificity", "confidence", "note"]
ENUM = {"anchor": {"direct_assay", "genetics", "prior_drug", "pathway_only", "unknown"},
        "specificity": {"specific", "shared", "nonspecific", "unknown"},
        "confidence": {"high", "medium", "low"}}


def families() -> pd.DataFrame:
    s = pd.read_csv(SCOPE, dtype=str).fillna("")
    s["family"] = [("" if k in NO_FAMILY_KINDS or not c else FAMILY.get(c, c)) for c, k in zip(s.readout_canonical, s.readout_kind)]
    s.to_csv(SCOPE, index=False)
    f = s[s.family != ""]
    rows = []
    for fam, g in f.groupby("family"):
        best = g.loc[g.quote.str.len().idxmax()]
        rows.append({"family": fam, "target": fam.split(":")[0], "n_programs": len(g),
                     "readout_kind": g.readout_kind.mode().iloc[0],
                     "readouts": " | ".join(sorted(set(g.readout))[:4]),
                     "drugs": "; ".join(sorted(set(g.drug))[:4]),
                     "diseases": "; ".join(sorted(set(x for x in g.disease if x))[:4]),
                     "example_quote": best.quote, "example_drug": best.drug,
                     "members": ";".join(sorted(set(g.readout_canonical)))})
    out = pd.DataFrame(rows).sort_values(["target", "family"])
    out.to_csv(FAMILIES, index=False)
    return out


def todo(batch: int) -> None:
    fam = families()
    done = set(pd.read_csv(ANCHORS, dtype=str).family) if os.path.exists(ANCHORS) else set()
    q = fam[~fam.family.isin(done)].sample(frac=1, random_state=20261103)  # shuffle so no batch is one target
    os.makedirs(BATCHES, exist_ok=True)
    for f in glob.glob(os.path.join(BATCHES, "anchor_todo_*.csv")):
        os.remove(f)
    for i in range(0, len(q), batch):
        q.iloc[i:i + batch].to_csv(os.path.join(BATCHES, f"anchor_todo_{i // batch + 1:02d}.csv"), index=False)
    print(f"{len(fam)} families over {fam.target.nunique()} targets, {int(fam.n_programs.sum())} programs; "
          f"{len(done)} done, {len(q)} to research in {(len(q) + batch - 1) // batch} batches of {batch}")


def merge() -> None:
    fam = set(pd.read_csv(FAMILIES, dtype=str).family)
    old = pd.read_csv(ANCHORS, dtype=str).fillna("") if os.path.exists(ANCHORS) else pd.DataFrame(columns=OUT_COLS + ["researched_by", "researched_at"])
    new = []
    for f in sorted(glob.glob(os.path.join(BATCHES, "anchor_done_*.csv"))):
        d = pd.read_csv(f, dtype=str).fillna("")
        missing = [c for c in OUT_COLS if c not in d.columns]
        if missing:
            raise SystemExit(f"{f}: missing columns {missing}")
        bad = {c: sorted(set(d[c]) - v) for c, v in ENUM.items() if set(d[c]) - v}
        if bad:
            raise SystemExit(f"{f}: values outside the vocabulary {bad}")
        unknown = sorted(set(d.family) - fam)
        if unknown:
            raise SystemExit(f"{f}: families not in families.csv {unknown}")
        d = d[OUT_COLS].copy()
        d["researched_by"], d["researched_at"] = os.path.basename(f), date.today().isoformat()
        new.append(d)
    if not new:
        print("no anchor_done_*.csv batches")
        return
    merged = pd.concat([old] + new).drop_duplicates("family", keep="last")
    merged.to_csv(ANCHORS, index=False)
    print(f"anchors.csv: {len(old)} -> {len(merged)} families; anchor: {merged.anchor.value_counts().to_dict()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["todo", "merge"])
    ap.add_argument("--batch", type=int, default=7)
    a = ap.parse_args()
    {"todo": lambda: todo(a.batch), "merge": merge}[a.cmd]()
