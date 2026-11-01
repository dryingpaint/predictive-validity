import numpy as np
import pandas as pd

from report.section3 import evidence_types


def programs(n: int = 600, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    flag = lambda p: (rng.random(n) < p).astype(float)
    d = pd.DataFrame({
        "target": [f"T{i % 150}" for i in range(n)], "bio_area": rng.choice(["oncology", "neurology"], n),
        "modality": rng.choice(["small_molecule", "antibody"], n), "era": rng.choice(["2015-16", "2017-18"], n),
        "novel": flag(0.5), "precedent": flag(0.3), "g3": flag(0.3), "mgi": flag(0.3), "impc": flag(0.05),
        "somatic": flag(0.3), "crispr": flag(0.01), "expression": flag(0.3), "reactome": flag(0.2),
        "liability": flag(0.4), "b1": flag(0.3), "gwas_strong": flag(0.1), "mendelian": flag(0.2), "gwas": flag(0.2),
        "burden": flag(0.05), "lof_protective": flag(0.05), "mgi_strong": flag(0.1), "impc_strong": flag(0.02),
        "somatic_concordant": flag(0.2), "expression_up": flag(0.2),
        "sign": rng.choice(["decrease", "increase"], n), "mechanism": rng.choice(["concordant", "undirected"], n),
        "mouse_direction": rng.choice(["concordant", "none"], n)})
    d["regime"] = np.where(d.bio_area.eq("oncology"), "ONC", "COM")
    d["s4"] = (rng.random(n) < 0.15 + 0.15 * d.g3).astype(float)
    return d


def test_each_refinement_is_compared_only_within_its_kind():
    d = programs()
    _, refined = evidence_types(d)
    germline = refined.set_index("refinement").loc["gwas_strong"]
    assert germline.n_cohort == int((d.g3 > 0).sum())
    animal = refined.set_index("refinement").loc["animal_direction"]
    assert animal.n_cohort == int(((d.mgi > 0) | (d.impc > 0)).sum())


def test_benchmark_is_outside_the_holm_family():
    types, _ = evidence_types(programs())
    t = types.set_index("type")
    assert pd.isna(t.loc["benchmark", "holm_p"])
    assert t.loc["germline", "holm_p"] >= t.loc["germline", "p"]
