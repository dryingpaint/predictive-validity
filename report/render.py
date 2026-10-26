"""Render REPORT.md from REPORT.template.md and the generated outputs.

    python -m report.render

Tables are built from report/output/section*/ CSVs; inline numbers use
{{key}} placeholders resolved against report/output/numbers.json (written by
report.section1, report.section2, report.section3, report.attribution and report.quality). Narrative blocks live
in report/narrative/*.md with the same placeholders.
"""
from __future__ import annotations

import json
import os
import re

import numpy as np
import pandas as pd

from report import bio, frame
from report.section3 import CASE_AUDIT

OUT = os.path.join(frame.REPO, "report", "output")
NARRATIVE = os.path.join(frame.REPO, "report", "narrative")
BIO = {"bio.loa": f"{bio.LOA}%", "bio.loa_novel": f"{bio.LOA_NOVEL}%",
       **{f"bio.ph{ph}": f"{v}%" for ph, v in bio.TRANSITIONS.items()},
       **{f"bio.{k}": f"{v}%" for k, v in {**bio.AREA_LOA, **bio.MODALITY_LOA}.items()}}


def pct(x, digits=1):
    return "–" if pd.isna(x) else f"{100 * x:.{digits}f}%"


FORMATS = {"": str, "pct": pct, "pct0": lambda v: pct(v, 0), "int": lambda v: f"{int(v):,}",
           "x2": "{:.2f}".format, "x3": "{:.3f}".format}
BAND_NAMES = {"none": "None", "low": "Lower third", "middle": "Middle third", "high": "Upper third"}


def ci(lo, hi, digits=1):
    return "" if pd.isna(lo) else f" ({100 * lo:.{digits}f}–{100 * hi:.{digits}f})"


def table(df: pd.DataFrame) -> str:
    head = "| " + " | ".join(df.columns) + " |\n| " + " | ".join(":----" for _ in df.columns) + " |\n"
    return head + "\n".join("| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False))


def transitions_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section1", "loa_overall.csv")).set_index("label")
    cohorts = {"all programs": "All programs", "programs with a US-sited industry trial in the phase": "Developed in the US"}
    rows = []
    for ph, label in [(1, "Phase 1 → Phase 2"), (2, "Phase 2 → Phase 3"), (3, "Phase 3 → Approval")]:
        row = [label]
        for key in cohorts:
            o = df.loc[key]
            n = int(o[f"ph{ph}_n_advanced"] + o[f"ph{ph}_n_suspended"])
            row.append(f"{pct(o[f'ph{ph}_rate'])}{ci(o[f'ph{ph}_lo'], o[f'ph{ph}_hi'])}, n={n:,}")
        rows.append(row + [f"{bio.TRANSITIONS[ph]:.1f}%"])
    rows.append(["**Phase 1 → Approval (LOA)**"]
                + [f"**{pct(df.at[k, 'loa'])}**{ci(df.at[k, 'loa_lo'], df.at[k, 'loa_hi'])}" for k in cohorts]
                + [f"**{bio.LOA}%** (novel drugs {bio.LOA_NOVEL}%)"])
    return table(pd.DataFrame(rows, columns=["Transition", *[f"{v} (95% CI)" for v in cohorts.values()],
                                             "BIO 2011–2020"]))


def sensitivity_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section1", "loa_overall.csv"))
    df = df.assign(**{"Cohort or definition": df.label.map(sentence_case),
                      "Ph1→2": df.ph1_rate.map(pct), "Ph2→3": df.ph2_rate.map(pct), "Ph3→approval": df.ph3_rate.map(pct),
                      "LOA (95% CI)": [f"{pct(r.loa)}{ci(r.loa_lo, r.loa_hi)}" for r in df.itertuples()]})
    return table(df.iloc[:, -5:])


STRATUM_NAMES = {"sirna_rnai": "siRNA / RNAi", "car_t": "CAR-T", "mrna": "mRNA (non-vaccine)",
                 "antibody_drug_conjugate": "Antibody–drug conjugate", "other_cell_therapy": "Other cell therapy",
                 "microbiome_or_live_biotherapeutic": "Microbiome or live biotherapeutic",
                 "infectious_disease": "Infectious disease"}


def stratum_name(key: str) -> str:
    return STRATUM_NAMES.get(key, key.replace("_", " ").capitalize())


def sentence_case(text: str) -> str:
    return text[:1].upper() + text[1:]


def stratum_table(csv: str, label: str, ref: dict) -> str:
    df = pd.read_csv(os.path.join(OUT, "section1", csv)).dropna(subset=["loa"])
    df = df.assign(**{label: df.label.map(stratum_name),
                      "All programs, LOA (95% CI)": [f"{pct(r.loa)}{ci(r.loa_lo, r.loa_hi)}" for r in df.itertuples()],
                      "Entities": df.n_entities.map("{:,}".format),
                      "Developed in the US, LOA (95% CI)": [
                          f"{pct(r.us_loa)}{ci(r.us_loa_lo, r.us_loa_hi)}" if pd.notna(getattr(r, "us_loa", np.nan)) else "–"
                          for r in df.itertuples()],
                      "BIO 2011–2020": [f"{ref[k]:.1f}%" if k in ref else "–" for k in df.label]})
    return table(df[[label, "All programs, LOA (95% CI)", "Entities", "Developed in the US, LOA (95% CI)",
                     "BIO 2011–2020"]])


def failure_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section1", "failure_modes_by_phase.csv")).set_index("reason")
    share = df.div(df.sum(axis=0), axis=1)
    out = pd.DataFrame({f"Phase {c}": [f"{pct(share.at[r, c], 0)} ({int(df.at[r, c]):,})" for r in df.index]
                        for c in df.columns}, index=df.index).reset_index().rename(columns={"reason": "Reason"})
    return table(out)


ATTRIBUTION_GROUPS = {"not_engaged": "Not engaged: exposure or engagement inadequate, or another drug on the target worked (F1)",
                      "engaged_no_benefit": "Engaged, no benefit: target or mechanism wrong for the disease as tested (F2–F4)",
                      "trial_design": "Trial design, population or endpoint, mechanism not in question (F7)",
                      "toxicity": "Toxicity offset or ended efficacy (F5, F6)",
                      "not_a_failure": "Recorded as efficacy, but the sources show otherwise: endpoint met, non-inferiority margin, business stop (F8, F9)",
                      "indeterminate": "Indeterminate: no human engagement evidence either way (U)"}


def attribution_table() -> str:
    n = json.load(open(os.path.join(OUT, "attribution", "numbers.json")))
    cols = {"Phase 2": n["by_phase"]["2"], "Phase 3": n["by_phase"]["3"], "Phase 2 and 3": n["phase23"],
            "Outside oncology": n["outside_oncology"]}
    rows = [[label] + [f"{pct(c['groups'][g]['share'], 0)} ({int(c['groups'][g]['n']):,})" for c in cols.values()]
            for g, label in ATTRIBUTION_GROUPS.items()]
    rows.append(["**Not engaged, of failures whose mechanism was tested**"]
                + [f"**{pct(c['testable']['not_engaged_share'], 0)}**{ci(c['testable']['lo'], c['testable']['hi'], 0)}"
                   for c in cols.values()])
    rows.append(["Programs (entities)"] + [f"{c['programs']:,} ({c['entities']:,})" for c in cols.values()])
    return table(pd.DataFrame(rows, columns=["What the evidence shows"] + list(cols)))


def attribution_sensitivity_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "attribution", "sensitivity.csv"))
    out = pd.DataFrame({"Variant": df.variant.map(sentence_case), "Programs": df.programs.map("{:,}".format),
                        "Mechanism tested": df.testable.map("{:,}".format),
                        "Not engaged, of tested (95% CI)": [pct(v, 0) + ci(lo, hi, 0) for v, lo, hi
                                                            in zip(df.not_engaged_of_testable, df.lo, df.hi)],
                        "Indeterminate": df.indeterminate.map(lambda v: pct(v, 0))})
    return table(out)


def rs_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section2", "relative_success.csv")).dropna(subset=["rs"]).sort_values("rs", ascending=False)
    df = df.assign(**{"Evidence line": df.label,
                      "Programs with it": df.n_with.map("{:,}".format),
                      "LOA with / without": [f"{pct(a)} / {pct(b)}" for a, b in zip(df.loa_with, df.loa_without)],
                      "Relative success (95% CI)": [f"{r:.2f} ({lo:.2f}–{hi:.2f})"
                                                    for r, lo, hi in zip(df.rs, df.rs_lo, df.rs_hi)]})
    return table(df.iloc[:, -4:])


def prediction_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section2", "prediction_metrics.csv"))
    splits = {"grouped_cv": "Held-out target sets", "temporal": "Temporal (2013–2016)"}
    features = {"covariates": "Area, modality, novelty, year", "covariates+evidence": "… plus all evidence lines",
                "evidence": "Evidence lines only"}
    df = df.assign(**{"Validation": df.split.map(splits), "Features": df.features.map(features),
                      "AUC (95% CI)": [f"{a:.3f} ({lo:.3f}–{hi:.3f})" for a, lo, hi in zip(df.auc, df.auc_lo, df.auc_hi)],
                      "PR-AUC (base rate)": [f"{a:.3f} ({b:.3f})" for a, b in zip(df.pr_auc, df.base_rate)],
                      "Programs (approved)": [f"{n:,} ({p:,})" for n, p in zip(df.n, df.n_positive)]})
    return table(df.iloc[:, -5:])


def dose_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section2", "genetic_dose_response.csv"))
    df = df.assign(**{"Human genetic support (Open Targets score, as of phase entry)": [
                          BAND_NAMES[b] + ("" if b == "none" else f" (> {lo:.2f} to {hi:.2f})" if np.isfinite(hi) else f" (> {lo:.2f})")
                          for b, lo, hi in zip(df.band, df.score_from, df.score_to)],
                      "Programs": df.n_programs.map("{:,}".format), "Targets": df.n_targets.map("{:,}".format),
                      "LOA (95% CI)": [f"{pct(r.loa)}{ci(r.loa_lo, r.loa_hi)}" for r in df.itertuples()]})
    return table(df.iloc[:, -4:])


def joint_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section2", "joint_rr_by_phase.csv"))
    rs = pd.read_csv(os.path.join(OUT, "section2", "relative_success.csv"))
    labels, order = rs.set_index("feature").label, {f: i for i, f in enumerate(rs.feature)}
    df["cell"] = [f"{r:.2f} ({lo:.2f}–{hi:.2f})" for r, lo, hi in zip(df.rr, df.rr_lo, df.rr_hi)]
    wide = df.pivot(index="feature", columns="phase", values="cell").fillna("–")
    wide = wide.loc[sorted(wide.index, key=lambda f: order.get(f, 99))]
    wide.columns = [f"Phase {c} → next" for c in wide.columns]
    wide.insert(0, "Evidence", [labels.get(f, f) for f in wide.index])
    return table(wide.reset_index(drop=True))


def ablation_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section2", "prediction_ablation.csv")).sort_values("auc_drop", ascending=False)
    df = df.assign(**{"Evidence removed": df.label,
                      "AUC change (95% CI)": [f"{-d:+.3f} ({-hi:+.3f} to {-lo:+.3f})"
                                              for d, lo, hi in zip(df.auc_drop, df.drop_lo, df.drop_hi)]})
    return table(df.iloc[:, -2:])


QUALITY_ROWS = [
    ("label_audit", "indication_mondo", "Condition → MONDO disease"),
    ("label_audit", "drug_moiety", "Intervention name → molecular entities"),
    ("label_audit", "fda_application_moiety", "FDA application → molecular entities"),
    ("label_audit", "fda_letter_approved_uses", "Approval letter → approved uses"),
    ("outcome_audit", "stop_reason", "Trial stop reason"),
    ("outcome_audit", "primary_endpoint", "Primary endpoint met / not met (posted results)"),
    ("publication_audit", "primary_endpoint", "Primary endpoint met / not met (results papers)"),
    ("approval_audit", "yes_dated.approved", "Approval (sampled as approved, dated 2015 or later)"),
    ("approval_audit", "yes_dated.date", "Approval date (sampled as approved, dated 2015 or later)"),
    ("approval_audit", "yes_pre2015.approved", "Approval (sampled as approved before 2015)"),
    ("approval_audit", "no_entity_appr.approved", "Approval (sampled as not approved, Phase 2+ programs)"),
    ("approval_audit", "uncertain.approved", "Approval (sampled as uncertain)"),
]


def quality_table() -> str:
    q = json.load(open(os.path.join(OUT, "quality", "numbers.json")))
    rows = []
    for group, key, label in QUALITY_ROWS:
        r = q.get(group, {}).get(key)
        if r:
            rows.append([label, f"{r['n']:,}", f"{pct(r['accuracy'], 0)} ({pct(r['lo'], 0)}–{pct(r['hi'], 0)})",
                         str(r["wrong"])])
    return table(pd.DataFrame(rows, columns=["Label", "Audited", "Agreement (95% CI)", "Wrong"]))


def rr_ci(r, ratio="rr") -> str:
    """'1.23 (1.01–1.50)' from a dict or row with the ratio, lo and hi; '–' when not estimated."""
    v = r.get(ratio)
    return "–" if v is None or pd.isna(v) else f"{v:.2f} ({r.get('lo'):.2f}–{r.get('hi'):.2f})"


def p_value(p) -> str:
    return "–" if p is None or pd.isna(p) else "< 0.001" if p < 0.001 else f"{p:.3f}"


def s3_hypotheses_table() -> str:
    n = json.load(open(os.path.join(OUT, "section3", "numbers.json")))
    h4 = n["h4"]["fdaaa"]["interaction_per_step"]
    rows = [
        ("H1", "Outside oncology: genetics for the disease (G3) vs no germline genetics (G0), advancing within 4 years "
               "of Phase 2", "risk ratio", rr_ci(n["h1"]["g3"]), n["h1"]["g3"].get("p")),
        ("H2", "Same target, different diseases: G3 vs not (conditional logit)", "odds ratio", rr_ci(n["h2"], "or"),
         n["h2"].get("p")),
        ("H3", "Direction of genetic effect vs drug action (Open Targets direction fields): discordant < undirected < "
               "concordant", "risk ratio per step", rr_ci(n["h3"]["trend"]), n["h3"]["trend"].get("p")),
        ("H4", "Trials outside oncology: change in G3's effect on NOT MET per step from proximal to distal endpoints "
               "(registry-posted results, FDAAA era)", "ratio of risk ratios", rr_ci(h4), h4.get("p")),
        ("H5", "G3 lowers efficacy failure more than business or operational failure (Phase 2 and 3)",
         "ratio of risk ratios", rr_ci(n["h5"]["ratio_f_bizops_vs_f_efficacy"]),
         n["h5"]["ratio_f_bizops_vs_f_efficacy"].get("p")),
        ("H6", "Outside oncology, target liability raises safety failure, and more than efficacy failure (Phases "
               "1–3; intersection-union test)", "risk ratio, safety failure", rr_ci(n["h6"]["safety"]), n["h6"]["p"]),
        ("H7", "Oncology: a somatic driver whose direction matches the drug, advancing within 4 years of Phase 2",
         "risk ratio", rr_ci(n["h7"]), n["h7"].get("p")),
    ]
    out = [[h, text, measure, est, p_value(p), p_value(n["holm"].get(h)),
            "supported" if n["holm"].get(h, 1) < 0.05 else "not supported"] for h, text, measure, est, p in rows]
    return table(pd.DataFrame(out, columns=["", "Hypothesis", "Measure", "Estimate (95% CI)", "p", "Holm p", "Result"]))


# Evidence-map rows shown in the table and the figure: section3.MAP_FEATURES without the families no program had
# before entry (burden, IMPC, CRISPR) and the union of the three liability rows.
S3_MAP_ROWS = ["g3", "gwas", "gwas_strong", "gwas_mid", "gwas_weak", "mendelian", "mendelian_strong",
               "somatic", "somatic_concordant", "mgi", "mgi_strong", "expression", "reactome", "b1", "precedent",
               "pan_essential", "constrained", "ko_lethal"]


def s3_map_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section3", "evidence_map.csv"))
    c2, com, onc = (df[df.scope == s].set_index("feature") for s in ("C2", "C2 COM", "C2 ONC"))
    rows = []
    for f in S3_MAP_ROWS:
        r = c2.loc[f]
        rows.append([r.label, f"{int(r.n):,} ({int(r.n_targets):,})", f"{pct(r.ppv, 0)} / {pct(r.rate_without, 0)}",
                     pct(r.coverage, 0), rr_ci(r), rr_ci(com.loc[f]), rr_ci(onc.loc[f])])
    return table(pd.DataFrame(rows, columns=["Evidence for the program's disease, before entry", "Programs (targets)",
                                             "Advanced: with / without", "Share of all that advanced",
                                             "Risk ratio vs programs without it, all (95% CI)", "Non-oncology",
                                             "Oncology"]))


S3_ENDPOINTS = {"B1_target_engagement": "Target engagement", "B2_exploratory_biomarker": "Exploratory biomarker",
                "B3_regulatory_surrogate": "Regulatory surrogate (LDL-C, HbA1c, viral load…)",
                "B4_objective_physiological": "Objective physiology (6MWD, visual acuity, weight…)",
                "B5_clinician_scale": "Clinician-rated scale or responder index",
                "B6_patient_reported": "Patient-reported outcome",
                "B7_disease_events": "Disease events (relapses, exacerbations…)",
                "B8_hard_outcome": "Hard outcome (death, MI, stroke…)", "O1_tumor_response": "Tumour response",
                "O2_progression_free": "Progression-free survival", "O3_overall_survival": "Overall survival"}


def s3_endpoint_table() -> str:
    df = pd.read_csv(os.path.join(OUT, "section3", "endpoint_classes.csv"))
    a, f = (df[df.scope == s].set_index("endpoint_class") for s in ("all", "fdaaa"))
    rows = []
    for c, name in S3_ENDPOINTS.items():
        if c not in a.index:
            continue
        r = a.loc[c]
        rows.append([name, f"{int(r.n_cohort):,}", pct(r.not_met, 0), f"{int(r.n):,}",
                     f"{pct(r.ppv, 0)} / {pct(r.rate_without, 0)}", rr_ci(r),
                     rr_ci(f.loc[c]) if c in f.index else "–"])
    return table(pd.DataFrame(rows, columns=["Class of the governing primary endpoint", "Trials", "Not met",
                                             "Trials with G3", "Not met: with G3 / without", "Risk ratio of NOT MET, "
                                             "all readable (95% CI)", "Registry-posted, FDAAA era"]))


def s3_rules() -> pd.DataFrame:
    return pd.read_csv(os.path.join(OUT, "section3", "rules.csv")).set_index("rule", drop=False)


def rule_name(r) -> str:
    """'M3 Mendelian evidence …', with * for a rule added after the plan."""
    return f"{r.rule}{'' if r.registered else '*'} {r.label}"


def s3_rules_table() -> str:
    regime = {"all": "All", "COM": "Non-oncology", "ONC": "Oncology", "DD": "Hereditary"}
    rows = []
    for r in s3_rules().itertuples():
        def split(name):
            v = getattr(r, f"{name}_rr")
            if pd.isna(v) or v == 0:
                return "–" if pd.isna(v) else "none advanced"
            return f"{v:.2f} ({getattr(r, f'{name}_lo90'):.2f}–{getattr(r, f'{name}_hi90'):.2f})"
        rows.append([f"{r.rule}{'' if r.registered else '*'}", r.label, regime[r.regime],
                     f"{int(r.n):,} ({int(r.n_targets):,})", pct(r.ppv, 0) if r.n else "–",
                     pct(r.coverage, 0), "–" if pd.isna(r.adj_rr) else f"{r.adj_rr:.2f} ({r.adj_lo:.2f}–{r.adj_hi:.2f})",
                     split("discovery"), split("confirmation"),
                     "**predictive**" if r.predictive else ("not testable" if r.n == 0 else "no")])
    return table(pd.DataFrame(rows, columns=["Rule", "Applied at Phase 2 entry", "Regime", "Programs (targets)",
                                             "Advanced", "Share of all that advanced", "Adjusted RR (95% CI)",
                                             "Discovery RR (90%)", "Held-out RR (90%)", "Meets the bar"]))


CODE_NAMES = {"F1": "F1 exposure", "F2": "F2 biology did not translate", "F3": "F3 wrong population",
              "F4": "F4 surrogate gap", "F5": "F5 on-target toxicity", "F6": "F6 off-target toxicity",
              "F7": "F7 trial design", "F8": "F8 commercial", "unknown": "unknown"}
SOURCE_CHARS = 160  # length of the evidence source shown in a case card


def failure_label(advanced: str, code: str, short: bool = False) -> str:
    if advanced == "yes":
        return "–"
    if code == "not_a_failure":
        return "still progressing"
    return code if short else CODE_NAMES[code]


def s3_case_audit() -> pd.DataFrame:
    return pd.DataFrame(json.load(open(CASE_AUDIT)))


def s3_cases_table() -> str:
    a, rules = s3_case_audit(), s3_rules()
    rows = []
    for rule, g in a.groupby("rule", sort=False):
        failed = g[g.advanced_within_4y == "no"]
        codes = pd.Series([failure_label("no", c, short=True) for c in failed.failure_code]).value_counts()
        rows.append([rule_name(rules.loc[rule]), f"{len(g)}", f"{(g.advanced_within_4y == 'yes').sum()}",
                     f"{g.claim_supported.isin(['yes', 'partial']).sum()} ({(g.claim_supported == 'partial').sum()} "
                     f"partly)", f"{(g.predates_entry == 'yes').sum()}",
                     ", ".join(f"{c}: {k}" for c, k in codes.items()) or "–"])
    return table(pd.DataFrame(rows, columns=["Rule", "Cases", "Advanced within 4 years (verified)",
                                             "Evidence claim verified", "Evidence published before entry",
                                             "Why the others stopped (codes)"]))


def shorten(text: str, limit: int) -> str:
    """`text` cut at the last word boundary before `limit` characters, with an ellipsis."""
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def s3_case_cards() -> str:
    rows = []
    for r in s3_case_audit().itertuples():
        source = shorten(r.evidence_source or "", SOURCE_CHARS) + (f" ({r.evidence_year})" if r.evidence_year else "")
        outcome = {"yes": "advanced", "no": "did not advance"}.get(r.advanced_within_4y, "unclear")
        rows.append([f"{r.rule}", f"{r.entity} ({', '.join(r.targets)})", r.disease, r.phase2_entry,
                     f"{r.claim_supported}; {source}",
                     outcome + ("" if r.pipeline_correct == "yes" else " (pipeline wrong)"),
                     failure_label(r.advanced_within_4y, r.failure_code)])
    return table(pd.DataFrame(rows, columns=["Rule", "Drug (target, action)", "Disease", "Phase 2 entry",
                                             "Evidence claim: verdict; earliest source", "Outcome (verified)",
                                             "Failure"]))


TABLES = {"TRANSITIONS_TABLE": transitions_table, "SENSITIVITY_TABLE": sensitivity_table,
          "AREA_TABLE": lambda: stratum_table("loa_by_area.csv", "Disease area", bio.AREA_LOA),
          "MODALITY_TABLE": lambda: stratum_table("loa_by_modality.csv", "Modality", bio.MODALITY_LOA),
          "FAILURE_TABLE": failure_table, "RS_TABLE": rs_table, "PREDICTION_TABLE": prediction_table,
          "DOSE_TABLE": dose_table, "JOINT_TABLE": joint_table, "ABLATION_TABLE": ablation_table,
          "QUALITY_TABLE": quality_table, "S3_HYPOTHESES_TABLE": s3_hypotheses_table, "S3_MAP_TABLE": s3_map_table,
          "S3_ENDPOINT_TABLE": s3_endpoint_table, "S3_RULES_TABLE": s3_rules_table, "S3_CASES_TABLE": s3_cases_table,
          "S3_CASE_CARDS": s3_case_cards, "ATTRIBUTION_TABLE": attribution_table,
          "ATTRIBUTION_SENSITIVITY_TABLE": attribution_sensitivity_table}


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
            return fill(open(os.path.join(NARRATIVE, key.lower() + ".md")).read(), numbers)
        return FORMATS[fmt](numbers[key])
    return re.sub(r"\{\{([A-Za-z0-9_.|+-]+)\}\}", sub, text)


def main() -> None:
    numbers = dict(BIO)
    for section in ("section1", "section2", "section3", "attribution", "quality"):
        numbers.update(flatten(json.load(open(os.path.join(OUT, section, "numbers.json"))), section + "."))
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(numbers, f, indent=1, default=float, sort_keys=True)
    template = open(os.path.join(frame.REPO, "report", "REPORT.template.md")).read()
    with open(os.path.join(frame.REPO, "REPORT.md"), "w") as f:
        f.write(fill(template, numbers))
    print(f"REPORT.md written; {len(numbers)} numbers")


if __name__ == "__main__":
    main()
