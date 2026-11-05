import numpy as np
import pandas as pd

from report.section2 import AREA_LINES, by_area


def synthetic_rows(seed: int = 0) -> pd.DataFrame:
    """Programs in two disease areas: genetics multiplies the chance of advancing from
    Phase 2 in oncology and does nothing in psychiatry."""
    rng = np.random.default_rng(seed)
    rows = []
    for area, effect in (("oncology", 3.0), ("psychiatry", 1.0)):
        for i in range(1200):
            genetic = i % 3 == 0
            target = f"{area[:3].upper()}{i % 300}"
            for phase in (1, 2, 3):
                p = min(0.9, 0.2 * (effect if genetic and phase == 2 else 1.0)) if phase == 2 else 0.6
                rows.append({"program_id": f"{area}-{i}", "phase": phase, "target": target, "bio_area": area,
                             "modality": "small_molecule", "novel": int(i % 2), "entry_year": 2008 + i % 12,
                             "event": "advanced" if rng.random() < p else "suspended",
                             **{f: 0.0 for f in AREA_LINES}, "genetic_any": float(genetic)})
    return pd.DataFrame(rows)


def test_by_area_finds_the_area_where_genetics_predicts():
    rs, tests, loo = by_area(synthetic_rows())
    gen = rs[rs.feature == "genetic_any"].set_index("group")
    assert gen.at["oncology", "rs"] > 2 and abs(gen.at["neuroscience", "rs"] - 1) < 0.4
    assert set(rs.group) == {"oncology", "neuroscience"}
    assert tests.set_index("feature").at["genetic_any", "p"] < 0.01
    assert set(loo.left_out) >= {"oncology", "neuroscience"}
