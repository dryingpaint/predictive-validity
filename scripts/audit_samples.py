"""Seeded samples of the stored labels for an independent audit, one JSON file per label.

    python -m scripts.audit_samples <out_dir> [--seed 20261102]

Each file lists the sampled items with what the auditor needs to re-derive the label from primary
sources and the label as stored. Agents judge each item (correct, acceptable or wrong, with the right
answer when wrong) and their verdicts go to report/audits/, which report.quality reads:
label_audit_post_fix.json (conditions, intervention strings, FDA applications, supplement documents),
approval_audit.json (program approvals by stratum), publication_outcome_audit.json and
endpoint_audit.json.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

from report import frame

APPROVAL_STRATA = {"yes_dated": 25, "yes_before_letters": 15, "no_entity_appr": 31, "uncertain": 14}
ENDPOINT_PER_CLASS = 3  # each endpoint class, 4 for B3-B6, as in the first audit
ENDPOINT_LARGE = ("B3_regulatory_surrogate", "B4_objective_physiological", "B5_clinician_rated", "B6_patient_reported")


def pick(df: pd.DataFrame, n: int, rng: np.random.Generator) -> pd.DataFrame:
    return df.iloc[rng.choice(len(df), size=min(n, len(df)), replace=False)] if len(df) else df


def samples(rng: np.random.Generator) -> dict[str, pd.DataFrame]:
    q = frame.query
    out = {}
    conditions = q("""SELECT i.indication_id, i.display_name AS condition, i.indication_kind, i.mondo_id, i.mondo_label,
                             i.mondo_match, i.mondo_decision_id,
                             (SELECT json_agg(x) FROM (SELECT s.nct_id, s.brief_title, s.start_date FROM preclin.ctgov_study_indication si
                               JOIN preclin.ctgov_study s USING (nct_id) WHERE si.indication_id = i.indication_id
                               ORDER BY s.start_date DESC NULLS LAST LIMIT 3) x) AS trials
                      FROM preclin.indication i
                      WHERE EXISTS (SELECT 1 FROM preclin.ctgov_study_indication si JOIN preclin.ctgov_study s USING (nct_id)
                                    WHERE si.indication_id = i.indication_id AND s.lead_sponsor_class = 'INDUSTRY')""")
    out["indication_mondo"] = pick(conditions, 100, rng)
    strings = q("""SELECT d.drug_id, d.display_name AS intervention, d.entity_kind,
                          (SELECT json_agg(json_build_object('entity', m.name, 'unii', m.unii, 'role', dm.role,
                                                             'biosimilar_of', dm.biosimilar_of))
                           FROM preclin.drug_moiety dm JOIN preclin.moiety m USING (moiety_id) WHERE dm.drug_id = d.drug_id) AS stored,
                          (SELECT json_agg(x) FROM (SELECT s.nct_id, s.brief_title, s.lead_sponsor FROM preclin.ctgov_study_drug sd
                            JOIN preclin.ctgov_study s USING (nct_id) WHERE sd.drug_id = d.drug_id LIMIT 3) x) AS trials
                   FROM preclin.drug d
                   WHERE EXISTS (SELECT 1 FROM preclin.ctgov_study_drug sd JOIN preclin.ctgov_study s USING (nct_id)
                                 WHERE sd.drug_id = d.drug_id AND s.lead_sponsor_class = 'INDUSTRY')""")
    out["drug_moiety"] = pick(strings, 100, rng)
    apps = q("""SELECT a.appl_no, a.appl_type, a.sponsor_name,
                       (SELECT string_agg(DISTINCT p.drug_name || ': ' || p.active_ingredient, ' | ') FROM preclin.fda_product p
                        WHERE p.appl_no = a.appl_no) AS products,
                       (SELECT json_agg(json_build_object('entity', m.name, 'unii', m.unii))
                        FROM preclin.fda_application_moiety f JOIN preclin.moiety m USING (moiety_id) WHERE f.appl_no = a.appl_no) AS stored
                FROM preclin.fda_application a WHERE EXISTS (SELECT 1 FROM preclin.fda_application_moiety f WHERE f.appl_no = a.appl_no)""")
    out["fda_application_moiety"] = pick(apps, 100, rng)
    docs = q("""SELECT sl.appl_no, sl.submission_type, sl.submission_no, sl.doc_type, sl.url, sl.doc_date,
                       (SELECT json_agg(json_build_object('disease', u.disease, 'as_written', u.indication_as_written,
                                                          'change', u.change_type) ORDER BY u.ordinal)
                        FROM preclin.fda_approved_use u WHERE u.letter_sha256 = sl.letter_sha256) AS stored
                FROM preclin.fda_submission_letter sl WHERE sl.doc_type <> 'letter' AND sl.letter_sha256 IS NOT NULL""")
    out["fda_supplement_document_approved_uses"] = pick(docs, 20, rng)
    progs = q("""SELECT p.program_id, m.name AS entity, m.unii, p.mondo_id, o.label AS disease, a.approved AS own_approved,
                        a.first_approval_date AS own_first_approval, a.date_basis, a.relation, a.evidence
                 FROM preclin.dev_program p JOIN preclin.moiety m USING (moiety_id) JOIN preclin.dev_program_approval a USING (program_id)
                 LEFT JOIN preclin.ontology_term o ON o.term_id = p.mondo_id""")
    strata = {"yes_dated": progs[(progs.own_approved == "yes") & (progs.date_basis == "dated")],
              "yes_before_letters": progs[(progs.own_approved == "yes") & (progs.date_basis == "before_letters")],
              "no_entity_appr": progs[(progs.own_approved == "no") & progs.unii.isin(
                  progs.loc[progs.own_approved == "yes", "unii"].dropna())],
              "uncertain": progs[progs.own_approved == "uncertain"]}
    out["approval"] = pd.concat([pick(df, APPROVAL_STRATA[s], rng).assign(stratum=s) for s, df in strata.items()])
    pubs = q("""SELECT o.nct_id, o.primary_endpoint AS own_primary_endpoint, o.safety_signal AS own_safety_signal,
                       o.efficacy_failure AS own_efficacy_failure, s.primary_outcomes,
                       (SELECT string_agg(tp.pmid::text, ', ') FROM preclin.trial_publication tp WHERE tp.nct_id = o.nct_id) AS pmids
                FROM preclin.trial_outcome o JOIN preclin.ctgov_study s USING (nct_id)
                JOIN pv_evidence.llm_decision d ON d.llm_decision_id = o.llm_decision_id
                WHERE d.task = 'trial_outcome_from_publication'""")
    out["publication_outcome"] = pick(pubs, 30, rng)
    ends = q("""SELECT e.nct_id, e.endpoint_class AS stored_class, e.governing_index, e.purpose, s.primary_outcomes,
                       s.conditions
                FROM preclin.trial_endpoint e JOIN preclin.ctgov_study s USING (nct_id)""")
    out["endpoint"] = pd.concat([pick(g, 4 if c in ENDPOINT_LARGE else ENDPOINT_PER_CLASS, rng)
                                 for c, g in ends.groupby("stored_class")])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out_dir")
    parser.add_argument("--seed", type=int, default=20261102)
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    frame.hold_snapshot()
    for name, df in samples(np.random.default_rng(args.seed)).items():
        path = os.path.join(args.out_dir, f"{name}.json")
        with open(path, "w") as f:
            json.dump(json.loads(df.to_json(orient="records", date_format="iso")), f, indent=1)
        print(f"{name}: {len(df)} -> {path}")


if __name__ == "__main__":
    main()
