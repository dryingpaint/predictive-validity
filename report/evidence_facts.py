"""Evidence facts on their subject: the rows of preclin.evidence_subject_fact (migration 152).

Each row is one dated fact about a gene, a gene and a disease, a cell line or a drug, with its source and the key of
the source rows behind it. Every evidence line of report.evidence_lines and report.section3 is scored from these rows
(a program's answer is a lookup for its targets and its disease as of the year before entry); nothing in the report
reads the evidence source tables directly. The precedent facts (approvals, failed trials, safety stops) come from the
program, trial and stop tables the cohorts are built from.
"""
from __future__ import annotations

import pandas as pd

from report import frame


@frame.held_once
def facts(fact_key: str) -> pd.DataFrame:
    """Every fact of one kind (preclin.evidence_subject_fact.fact_key): its subject, answer, the year it became known
    (null when undated), further attributes, source and source-row key."""
    return frame.query("""SELECT ensembl_id, mondo_id, disease_id, moiety_id, value, value_num, known_year, detail,
                                 source, record_key
                          FROM preclin.evidence_subject_fact WHERE fact_key = %s""", (fact_key,))


def detail(f: pd.DataFrame, key: str) -> pd.Series:
    """One attribute of each fact's detail."""
    return f.detail.map(lambda x: x.get(key))


def common_essentials() -> dict[int, set[str]]:
    """DepMap common-essential genes (Ensembl ids) by the year of the release that listed them."""
    f = facts("common_essential")
    return {int(y): set(g.ensembl_id) for y, g in f.groupby("known_year")}


def drug_assays() -> pd.DataFrame:
    """ChEMBL potency measurements of each entity's molecules (every form of each parent matches to it), one row per
    activity: the target's genes and type, the measurement, whether the assay was functional and in cells, and the
    year of the document that reported it."""
    f = facts("measurement")
    return pd.DataFrame({"moiety_id": f.moiety_id, "activity_id": f.record_key.astype(int),
                         **{k: detail(f, k) for k in ("target_chembl_id", "symbols", "target_type")},
                         "standard_type": f.value, "pchembl": f.value_num,
                         **{k: detail(f, k) for k in ("functional", "cell_based")}, "year": f.known_year})
