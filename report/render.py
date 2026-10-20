"""Render REPORT.md from REPORT.template.md and the generated outputs.

    python -m report.render

Tables are built from report/output/section*/ CSVs; inline numbers use
{{key}} placeholders resolved against report/output/numbers.json (written by
report.section1, report.section2 and report.quality). Narrative blocks live
in report/narrative/*.md with the same placeholders.
"""
from __future__ import annotations

import json
import os
import re

import numpy as np
import pandas as pd

from report import frame

OUT = os.path.join(frame.REPO, "report", "output")
NARRATIVE = os.path.join(frame.REPO, "report", "narrative")
BIO_TRANSITIONS = {1: 52.0, 2: 28.9, 3: 52.4}
BIO = {"bio.loa": "7.9%", "bio.loa_novel": "6.8%", "bio.ph1": "52.0%", "bio.ph2": "28.9%", "bio.ph3": "52.4%"}


def pct(x, digits=1):
    return "–" if pd.isna(x) else f"{100 * x:.{digits}f}%"


def ci(lo, hi, digits=1):
    return "" if pd.isna(lo) else f" ({100 * lo:.{digits}f}–{100 * hi:.{digits}f})"


def table(df: pd.DataFrame) -> str:
    head = "| " + " | ".join(df.columns) + " |\n| " + " | ".join(":----" for _ in df.columns) + " |\n"
    return head + "\n".join("| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False))


def transitions_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section1", "loa_overall.csv")).set_index("label")
    cohorts = {"all programs": "All programs", "programs with a US site in the phase": "Developed in the US"}
    rows = []
    for ph, label in [(1, "Phase 1 → Phase 2"), (2, "Phase 2 → Phase 3"), (3, "Phase 3 → Approval")]:
        row = [label]
        for key in cohorts:
            o = df.loc[key]
            n = int(o[f"ph{ph}_n_advanced"] + o[f"ph{ph}_n_suspended"])
            row.append(f"{pct(o[f'ph{ph}_rate'])}{ci(o[f'ph{ph}_lo'], o[f'ph{ph}_hi'])}, n={n:,}")
        rows.append(row + [f"{BIO_TRANSITIONS[ph]:.1f}%"])
    rows.append(["**Phase 1 → Approval (LOA)**"]
                + [f"**{pct(df.at[k, 'loa'])}**{ci(df.at[k, 'loa_lo'], df.at[k, 'loa_hi'])}" for k in cohorts]
                + ["**7.9%** (novel drugs 6.8%)"])
    return table(pd.DataFrame(rows, columns=["Transition", *[f"{v} (95% CI)" for v in cohorts.values()],
                                             "BIO 2011–2020"]))


def sensitivity_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section1", "loa_overall.csv"))
    df = df.assign(**{"Cohort or definition": df.label.str.capitalize(),
                      "Ph1→2": df.ph1_rate.map(pct), "Ph2→3": df.ph2_rate.map(pct), "Ph3→approval": df.ph3_rate.map(pct),
                      "LOA (95% CI)": [f"{pct(r.loa)}{ci(r.loa_lo, r.loa_hi)}" for r in df.itertuples()]})
    return table(df.iloc[:, -5:])


def stratum_table(csv: str, label: str) -> str:
    df = pd.read_csv(os.path.join(OUT, "section1", csv))
    df = df.assign(**{label: df.label.str.replace("_", " ").str.capitalize(),
                      "LOA (95% CI)": [f"{pct(r.loa)}{ci(r.loa_lo, r.loa_hi)}" for r in df.itertuples()],
                      "Entities": df.n_entities.map("{:,}".format)})
    return table(df[[label, "LOA (95% CI)", "Entities"]])


def failure_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section1", "failure_modes_by_phase.csv")).set_index("reason")
    share = df.div(df.sum(axis=0), axis=1)
    out = pd.DataFrame({f"Phase {c}": [f"{pct(share.at[r, c], 0)} ({int(df.at[r, c]):,})" for r in df.index]
                        for c in df.columns}, index=df.index).reset_index().rename(columns={"reason": "Reason"})
    return table(out)


def rs_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section2", "relative_success.csv")).sort_values("rs", ascending=False)
    df = df.assign(**{"Evidence (for the program's disease, as of phase entry)": df.label,
                      "Programs with it": df.n_with.map("{:,}".format),
                      "LOA with / without": [f"{pct(a)} / {pct(b)}" for a, b in zip(df.loa_with, df.loa_without)],
                      "Relative success (95% CI)": [f"{r:.2f} ({lo:.2f}–{hi:.2f})"
                                                    for r, lo, hi in zip(df.rs, df.rs_lo, df.rs_hi)]})
    return table(df.iloc[:, -4:])


def prediction_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section2", "prediction_metrics.csv"))
    df = df.assign(**{"Validation": df.split.str.replace("_", " "), "Features": df.features,
                      "AUC (95% CI)": [f"{a:.3f} ({lo:.3f}–{hi:.3f})" for a, lo, hi in zip(df.auc, df.auc_lo, df.auc_hi)],
                      "PR-AUC (base rate)": [f"{a:.3f} ({b:.3f})" for a, b in zip(df.pr_auc, df.base_rate)],
                      "Programs (approved)": [f"{n:,} ({p:,})" for n, p in zip(df.n, df.n_positive)]})
    return table(df.iloc[:, -5:])


def dose_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section2", "genetic_dose_response.csv"))
    band = {"none": "None", "low": "Lower third", "middle": "Middle third", "high": "Upper third"}
    df = df.assign(**{"Human genetic support (Open Targets score, as of phase entry)": [
                          band[b] + ("" if b == "none" else f" ({lo:.2f}–{hi:.2f})" if np.isfinite(hi) else f" (> {lo:.2f})")
                          for b, lo, hi in zip(df.band, df.score_from, df.score_to)],
                      "Programs": df.n_programs.map("{:,}".format), "Targets": df.n_targets.map("{:,}".format),
                      "LOA (95% CI)": [f"{pct(r.loa)}{ci(r.loa_lo, r.loa_hi)}" for r in df.itertuples()]})
    return table(df.iloc[:, -4:])


def joint_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section2", "joint_rr_by_phase.csv"))
    labels = pd.read_csv(os.path.join(OUT, "section2", "relative_success.csv")).set_index("feature").label
    df["cell"] = [f"{r:.2f} ({lo:.2f}–{hi:.2f})" for r, lo, hi in zip(df.rr, df.rr_lo, df.rr_hi)]
    wide = df.pivot(index="feature", columns="phase", values="cell").fillna("–")
    wide.columns = [f"Phase {c} → next" for c in wide.columns]
    wide.insert(0, "Evidence", [labels.get(f, f) for f in wide.index])
    return table(wide.reset_index(drop=True))


def ablation_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section2", "prediction_ablation.csv")).sort_values("auc_drop", ascending=False)
    df = df.assign(**{"Evidence removed": df.label,
                      "AUC change (95% CI)": [f"{-d:+.3f} ({-hi:+.3f} to {-lo:+.3f})"
                                              for d, lo, hi in zip(df.auc_drop, df.drop_lo, df.drop_hi)]})
    return table(df.iloc[:, -2:])


TABLES = {"TRANSITIONS_TABLE": transitions_table, "SENSITIVITY_TABLE": sensitivity_table, "AREA_TABLE": lambda: stratum_table("loa_by_area.csv", "Disease area"),
          "MODALITY_TABLE": lambda: stratum_table("loa_by_modality.csv", "Modality"),
          "FAILURE_TABLE": failure_table, "RS_TABLE": rs_table, "PREDICTION_TABLE": prediction_table,
          "DOSE_TABLE": dose_table, "JOINT_TABLE": joint_table, "ABLATION_TABLE": ablation_table}


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def fill(text: str, numbers: dict) -> str:
    def sub(m):
        key, _, fmt = m.group(1).partition("|")
        if key in TABLES:
            return TABLES[key]()
        if key.isupper():  # narrative block
            path = os.path.join(NARRATIVE, key.lower() + ".md")
            return fill(open(path).read(), numbers) if os.path.exists(path) else m.group(0)
        v = numbers[key]
        if fmt == "pct":
            return pct(v)
        if fmt == "pct0":
            return pct(v, 0)
        if fmt == "int":
            return f"{int(v):,}"
        if fmt == "x2":
            return f"{v:.2f}"
        return str(v)
    return re.sub(r"\{\{([A-Za-z0-9_.|+-]+)\}\}", sub, text)


def main() -> None:
    numbers = dict(BIO)
    for section in ("section1", "section2", "quality"):
        path = os.path.join(OUT, section, "numbers.json")
        if os.path.exists(path):
            numbers.update(flatten(json.load(open(path)), section + "."))
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(numbers, f, indent=1, default=float, sort_keys=True)
    template = open(os.path.join(frame.REPO, "report", "REPORT.template.md")).read()
    with open(os.path.join(frame.REPO, "REPORT.md"), "w") as f:
        f.write(fill(template, numbers))
    print(f"REPORT.md written; {len(numbers)} numbers")


if __name__ == "__main__":
    main()
