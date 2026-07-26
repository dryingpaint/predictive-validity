#!/usr/bin/env python3
"""Dumbbell: real-time (date-pinned) vs present-day RS per structural dimension.
Reads data/structural_versioned_repull.csv, writes data/structural_versioned_repull.png."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

d = pd.read_csv(os.path.join(DATA, "structural_versioned_repull.csv"))
# headline panel: scale-comparable measures only (OT Era B, IMPC, DepMap)
d = d[~((d.source == "OpenTargets") & (d.era == "EraA"))].copy()
d = d.dropna(subset=["rs_realtime", "rs_present_self"])
label = {"ot_overall_max": "OT overall", "ot_genetic_max": "OT genetic",
         "ot_animal_model_max": "OT animal-model", "impc_n_phenotypes": "IMPC KO phenotypes",
         "depmap_pan_essential": "DepMap essentiality"}
d["lab"] = d.dimension.map(label) + "  (n=" + d.n_datable.astype(str) + ")"
d = d.sort_values("rs_present_self")

fig, ax = plt.subplots(figsize=(8.2, 4.2))
y = range(len(d))
ax.axvline(1.0, color="#999", lw=1, ls="--", zorder=0)
for yi, (_, r) in zip(y, d.iterrows()):
    ax.plot([r.rs_realtime, r.rs_present_self], [yi, yi], color="#c8c8c8", lw=3, zorder=1)
ax.scatter(d.rs_present_self, list(y), s=70, color="#3b6ea5", zorder=3,
           label="present-day snapshot (hindsight)")
ax.scatter(d.rs_realtime, list(y), s=70, color="#c0392b", zorder=3,
           label="real-time (evidence available at first-trial date)")
ax.set_yticks(list(y)); ax.set_yticklabels(d.lab, fontsize=9)
ax.set_xlabel("Relative Success  (P(approved|support) / P(approved|not));  1.0 = no association")
ax.set_title("Structural evidence: how much predictive signal is real-time vs hindsight",
             fontsize=11)
ax.legend(fontsize=8, loc="lower right", frameon=False)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
fig.tight_layout()
out = os.path.join(DATA, "structural_versioned_repull.png")
fig.savefig(out, dpi=150)
print("wrote", out)
