"""analyses/model-system-atlas/indications.py: the stage, subtype and line read from a trial's condition rows.
Synthetic rows, no database."""
from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analyses", "model-system-atlas"))
import indications  # noqa: E402

NAMED = pd.DataFrame([{"mondo_id": "MONDO:G", "label": "glioblastoma"}, {"mondo_id": "MONDO:A", "label": "acute myeloid leukemia"},
                      {"mondo_id": "MONDO:B", "label": "breast cancer"}, {"mondo_id": "MONDO:H", "label": "HIV infectious disease"}])


def row(disease, name, stage=None, subset=None, line=None, classified=True, nct="NCT1", program=1):
    return {"program_id": program, "nct_id": nct, "phase": 2, "indication_id": 1, "display_name": name, "ind_mondo": disease,
            "canonical_disease": name if classified else None, "disease_stage": stage, "patient_subset": subset,
            "line_of_therapy": line, "disease": disease}


def classify(*rows):
    return indications.classify(pd.DataFrame(list(rows)), NAMED)


def test_a_stage_the_classifier_read_off_the_disease_name_is_not_a_stage():
    x = classify(row("MONDO:G", "Glioblastoma Multiforme", stage="advanced"),
                 row("MONDO:A", "Acute myeloid leukemia", stage="acute"),
                 row("MONDO:G", "Recurrent Glioblastoma", stage="relapsed"))
    assert list(x.indication) == ["general", "general", "relapsed"]
    assert list(x.basis) == ["name", "name", "classified"]


def test_unclassified_names_are_read_with_the_keyword_map_but_never_with_the_diseases_own_words():
    x = classify(row("MONDO:A", "Refractory Acute Myeloid Leukemia", classified=False),
                 row("MONDO:B", "Stage IV Breast Cancer AJCC v8", classified=False),
                 row("MONDO:B", "Triple-Negative Breast Carcinoma", classified=False))
    assert list(x.indication) == ["relapsed", "metastatic", "TNBC"]


def test_chronic_and_subtypes_that_restate_the_disease_fold_into_general():
    x = classify(row("MONDO:B", "Breast cancer", stage="chronic"), row("MONDO:H", "HIV-1 infection", subset="HIV-1"),
                 row("MONDO:B", "Breast cancer", subset="null"))
    assert list(x.indication) == ["general", "general", "general"]


def test_subtype_synonyms_share_one_label_and_the_commonest_spelling_wins():
    x = classify(row("MONDO:B", "a", subset="castrate-resistant"), row("MONDO:B", "b", subset="CRPC"),
                 row("MONDO:B", "c", subset="castration-resistant"), row("MONDO:B", "d", subset="castration-resistant"))
    assert x.indication.nunique() == 1 and x.indication.iloc[0] == "castration-resistant"


def test_relapsed_refractory_line_becomes_the_relapsed_stage():
    x = classify(row("MONDO:B", "Relapsed or refractory breast cancer", line="relapsed_refractory"))
    assert x.indication.iloc[0] == "relapsed" and pd.isna(x.line.iloc[0])
