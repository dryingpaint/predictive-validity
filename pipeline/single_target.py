"""Which diseases the target-based drugging paradigm solves (#197): definitions registered in #198, the pathway of
every atlas mechanism, and randomised trials of two pathways against one (#196).

    python -m pipeline.single_target indications  # LLM: shortlisted diseases each FDA label treats -> preclin.label_indication
    python -m pipeline.single_target pathways     # LLM: pathways of atlas and labelled mechanisms -> preclin.mechanism_pathway
    python -m pipeline.single_target regimens     # LLM: alone or with a partner, for each success on a stopped target
                                                  #   -> preclin.trial_regimen, preclin.stop_target_history
    python -m pipeline.single_target combos       # LLM + web: randomised trials of two pathways vs one
                                                  #   -> preclin.combination_trial

Each shortlisted disease gets two labels. How solved: by one drug (one molecule, up to three pathways), by stacking
drugs, or unsolved. Why one drug is not enough, where it is not: different patients need different targets, each
patient needs several, or the data can't tell. Counting needs pathways rather than targets (IL-17A and IL-17A/F
antibodies act through one pathway; an IL-17A/TNF bispecific through two). All rules are fixed here before any
response or regimen data is pulled.
"""
from __future__ import annotations

import argparse
import math
import re
import statistics
import uuid
from collections import Counter
from dataclasses import dataclass

import pandas as pd
from psycopg2.extras import execute_values

from pipeline import llm
from pipeline.outcomes import squash
from pipeline.target_history import History, stored
from report import frame
from report.section3 import CLOSE

# Disease areas left out of the labels and given their own sections (#200): their combinations exist mainly to stay
# ahead of tumour or pathogen evolution, not because the disease biology needs two targets
# (preclin.atlas_indication.area).
AREAS_APART = ("oncology", "infectious_disease")

# What counts as a combination when a later success on a target is read (#194). For the two-pathway evidence of #195
# and #196, a randomised add-on trial also counts: a drug on a new pathway added to a fixed background on another,
# against background alone, in the same patients.
COMBINATION = (
    "A combination is two active agents acting through different pathways given together as the tested regimen: a "
    "fixed-dose co-formulation, one molecule acting through two pathways (a bispecific antibody or a multi-receptor "
    "agonist), or a protocol-specified regimen pairing the drug with another investigational or newly paired agent. "
    "Background standard of care that every arm receives (methotrexate in rheumatoid arthritis, metformin in type 2 "
    "diabetes, stable conventional therapy) does not make a combination; a drug tested on top of it is tested alone."
)


@dataclass(frozen=True)
class Endpoint:
    disease: str
    endpoint: str  # the responder goal or the event the estimate is read on
    weeks: str     # the assessment window, or trial length for an event endpoint


# Diseases where several approved mechanisms are measured on the same responder endpoint (#195). A disease on either
# list stays only if #193 counts at least MIN_APPROVED_PATHWAYS distinct pathways with an FDA approval for it, any
# year. Asthma and multiple sclerosis are left out: their shared endpoints are rates (exacerbations, relapses), not
# responder shares.
SHORTLIST = {
    "MONDO:0005083": Endpoint("psoriasis", "PASI 90", "12-16"),
    "MONDO:0011849": Endpoint("psoriatic arthritis", "ACR50", "12-24"),
    "MONDO:0008383": Endpoint("rheumatoid arthritis", "ACR50", "12-24"),
    "MONDO:0005306": Endpoint("ankylosing spondylitis", "ASAS40", "12-16"),
    "MONDO:0005101": Endpoint("ulcerative colitis", "clinical remission (modified Mayo score)", "6-12"),
    "MONDO:0005011": Endpoint("Crohn disease", "clinical remission (CDAI < 150 or PRO2)", "6-12"),
    "MONDO:0004980": Endpoint("atopic eczema", "EASI-75", "12-16"),
    "MONDO:0006559": Endpoint("hidradenitis suppurativa", "HiSCR50", "12-16"),
    "MONDO:0011122": Endpoint("obesity", "weight loss of 15% or more", "52-72"),
    "MONDO:0005148": Endpoint("type 2 diabetes mellitus", "HbA1c below 7%", "24-52"),
    "MONDO:0005277": Endpoint("migraine", "50% or greater reduction in monthly migraine days", "12"),
    "MONDO:0021187": Endpoint("hyperlipidemia", "LDL cholesterol below 70 mg/dL", "12-24"),
    "MONDO:0001134": Endpoint("essential hypertension", "blood pressure below 130/80 mmHg", "8-12"),
}

# Diseases whose shared endpoint is an event, read as a hazard ratio against placebo or against background care.
EVENT_SHORTLIST = {
    "MONDO:0005252": Endpoint("heart failure", "cardiovascular death or heart failure hospitalisation", "trial length"),
    "MONDO:0005010": Endpoint("coronary artery disease", "major adverse cardiovascular events", "trial length"),
    "MONDO:0005300": Endpoint("chronic kidney disease", "kidney composite (sustained eGFR decline, kidney failure, "
                              "renal or cardiovascular death)", "trial length"),
    "MONDO:0004981": Endpoint("atrial fibrillation", "stroke or systemic embolism", "trial length"),
    "MONDO:0015924": Endpoint("pulmonary arterial hypertension", "clinical worsening or death", "trial length"),
}
MIN_APPROVED_PATHWAYS = 3

# Axis 1, how solved. Effects share one scale: for a responder endpoint the placebo-adjusted share of patients naive
# to advanced therapy reaching it, for an event endpoint the relative risk reduction (1 - HR). One drug is one molecule
# (approved, or positive in Phase 3) acting through at most MAX_PATHWAYS_ONE_DRUG pathways: bispecifics, trispecifics
# and multi-receptor agonists count, co-formulations of separate drugs do not. A stack is the best regimen of several
# drugs: for a responder endpoint its placebo-adjusted share, for an event endpoint stacked_rrr() of the add-on hazard
# ratios. The report also shows the labels at SOLVED_SENSITIVITY.
SOLVED_AT = 0.50
SOLVED_SENSITIVITY = (0.40, 0.60)
MAX_PATHWAYS_ONE_DRUG = 3
HOW_SOLVED = ("solved_by_one_drug", "solved_by_stacking", "unsolved")

# Axis 2, why one drug is not enough, asked of every disease one drug does not solve. Retained effect: pathway B's
# placebo-adjusted effect in patients who failed pathway A, over its effect in naive patients; its median over the
# disease's (A, B) pairs decides. Event endpoints have no retained effect, so they come out cant_tell.
RETAINED_DIFFERENT = 0.75
RETAINED_SEVERAL = 0.50
WHY_NOT_ONE_DRUG = ("different_patients", "several_targets", "cant_tell")

# Risk factor and the outcome disease it is treated to prevent: the drug that solves the risk factor is read across to
# the outcome's events, with trial length beside each estimate, since short trials in established disease understate
# what lifelong lowering does.
PAIRS = (
    ("MONDO:0021187", "MONDO:0005010"),  # hyperlipidemia -> coronary artery disease
    ("MONDO:0001134", "MONDO:0005010"),  # essential hypertension -> coronary artery disease
    ("MONDO:0011122", "MONDO:0005010"),  # obesity -> coronary artery disease
    ("MONDO:0005148", "MONDO:0005300"),  # type 2 diabetes -> chronic kidney disease
    ("MONDO:0005148", "MONDO:0005252"),  # type 2 diabetes -> heart failure
)


def stacked_rrr(add_on_hrs: list[float]) -> float:
    """Risk reduction of a stack of pathways, each hazard ratio measured against the background of those before it."""
    return 1 - math.prod(add_on_hrs)


def how_solved(one_drug: list[float], stack: float | None, solved_at: float = SOLVED_AT) -> str:
    """Axis 1. one_drug: the effect of each qualifying single drug; stack: the effect of the best multi-drug regimen."""
    if any(e >= solved_at for e in one_drug):
        return "solved_by_one_drug"
    if stack is not None and stack >= solved_at:
        return "solved_by_stacking"
    return "unsolved"


def why_not_one_drug(retained: list[float], combination_beats_single: bool) -> str:
    """Axis 2. retained: retained effect of each (failed pathway, next pathway) pair with an estimate.
    combination_beats_single: a randomised trial in the disease of two pathways against one (a combination, an add-on
    to a fixed background, or a multi-pathway drug head to head) met its efficacy primary endpoint, and the two-pathway
    arm was not stopped or abandoned for safety.

    Several targets needs both: a winning combination alone also arises when different patients respond to different
    drugs, and lost effect alone also arises because patients who failed a drug are harder to treat."""
    if not retained:
        return "cant_tell"
    kept = statistics.median(retained)
    if kept >= RETAINED_DIFFERENT:
        return "different_patients"
    if kept < RETAINED_SEVERAL and combination_beats_single:
        return "several_targets"
    return "cant_tell"


PATHWAY_SYSTEM = """You name the signalling pathways a drug mechanism acts through, so that mechanisms acting through the same pathway can be counted together.

A pathway is:
- a ligand or hormone with its receptors: IL-17 (IL-17A, IL-17F, IL-17RA, IL-17RC), TNF, GLP-1, CGRP, VEGF, PD-1/PD-L1;
- an intracellular cascade, when the target is a kinase or other component inside it: JAK-STAT (every JAK and TYK2 inhibitor), MAPK, PI3K-AKT-mTOR;
- for a drug that depletes or kills cells carrying a surface marker, the cell population it removes: B cells (CD20, CD19), plasma cells; for a tumour antigen, name the antigen;
- otherwise the target's own family or physiological system (SGLT, PCSK9-LDL receptor, acetylcholinesterase).

Rules:
- Upstream and downstream cytokines are separate pathways: IL-23 and IL-17 are two pathways.
- A drug whose targets lie in two pathways spans both: anti-IL12B (p40) acts through IL-12 and IL-23; a GIPR/GLP1R agonist through GIP and GLP-1; a GCGR/GLP1R agonist through glucagon and GLP-1; an IL-17A/TNF bispecific through IL-17 and TNF.
- Several targets inside one pathway stay one pathway: IL-17A/IL-17F antibodies act through IL-17; JAK1/JAK2 inhibitors through JAK-STAT.
- Ignore the direction of action: agonists and antagonists of a receptor act through the same pathway.
- Use short, conventional names written the same way each time: "IL-17", "IL-23", "TNF", "JAK-STAT", "GLP-1", "B cells".

kind:
- specific: one to three named pathways;
- broad: more than three, or a process rather than a pathway (multikinase inhibitors without a main target, cytotoxic chemotherapy, cell therapy without a defined antigen, general immunosuppression); pathways empty;
- no_target: no human target is given or the target is a pathogen; pathways empty.

You are given the mechanism (target genes and action), its display label, and some of its drugs with the diseases they were tested in."""

PATHWAY_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["specific", "broad", "no_target"]},
        "pathways": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
    "required": ["kind", "pathways", "reason"],
    "additionalProperties": False,
}


def validate_pathway(_payload: dict, out: dict) -> None:
    if (out["kind"] == "specific") != (1 <= len(out["pathways"]) <= 3):
        raise ValueError(f"kind {out['kind']} with {len(out['pathways'])} pathways")


def render_pathway(p: dict) -> str:
    return (f"Mechanism: {p['label']}\nTarget genes: {p['target_label']}\nAction: {p['action']}\n"
            f"Drugs (diseases tested): {'; '.join(p['drugs']) or 'none listed'}")


PATHWAY_TASK = llm.Task(name="mechanism_pathway", prompt_version="v1", schema_version="v1", system=PATHWAY_SYSTEM,
                        schema=PATHWAY_SCHEMA, render=render_pathway, subject_type="atlas_mechanism",
                        validate=validate_pathway, model="claude-opus-5-5", effort="low", max_tokens=2000)

MERGE_SYSTEM = """You are given pathway names that were assigned to drug mechanisms one mechanism at a time, with how many mechanisms carry each. The same pathway was sometimes written in different ways or at different levels of detail.

A pathway is a ligand or hormone with its receptors, an intracellular cascade, a cell population a depleting drug removes, or otherwise a target family. Map every name to the canonical pathway names it stands for:
- Spelling variants of one pathway share one canonical name, the shortest conventional form ("IL-17", "JAK-STAT", "GLP-1", "B cells").
- A receptor subtype or transporter of a transmitter or ligand belongs to that transmitter's pathway: "Serotonin 5-HT2A", "serotonin 5-HT1B/1D" and "Serotonin transporter" are "Serotonin"; "Dopamine D2" and "Dopamine transporter" are "Dopamine"; "PPAR-gamma" is "PPAR".
- An integrin keeps its own heterodimer, written one way ("α4β7 integrin"); a name covering two heterodimers maps to both.
- A name joining two pathways that are separate maps to both: "IL-4/IL-13" is "IL-4" and "IL-13"; "EGFR/HER2" is "EGFR" and "HER2". A name for one complex or one ligand-receptor pair stays one: "PD-1/PD-L1", "CDK4/6", "BAFF/APRIL", "Na+/K+-ATPase".
- Never merge different pathways, even closely related ones: IL-23 and IL-17, GLP-1 and GIP, IL-4 and IL-13, PD-1/PD-L1 and CTLA-4 stay apart.

Return every input name exactly once, with one or more canonical names."""

MERGE_SCHEMA = {
    "type": "object",
    "properties": {"names": {"type": "array", "items": {
        "type": "object",
        "properties": {"name": {"type": "string"},
                       "canonical": {"type": "array", "items": {"type": "string"}}},
        "required": ["name", "canonical"], "additionalProperties": False}}},
    "required": ["names"],
    "additionalProperties": False,
}


def validate_merge(payload: dict, out: dict) -> None:
    given = {n for n, _ in payload["names"]}
    got = [m["name"] for m in out["names"]]
    if set(got) != given or len(got) != len(given):
        raise ValueError(f"mapped {len(set(got) & given)} of {len(given)} names")
    if any(not m["canonical"] or not all(c.strip() for c in m["canonical"]) for m in out["names"]):
        raise ValueError("a name mapped to no canonical name")


def render_merge(p: dict) -> str:
    return "Pathway names (mechanisms carrying each):\n" + "\n".join(f"{n} ({c})" for n, c in p["names"])


MERGE_TASK = llm.Task(name="pathway_names", prompt_version="v2", schema_version="v2", system=MERGE_SYSTEM,
                      schema=MERGE_SCHEMA, render=render_merge, subject_type="pathway_name_set",
                      validate=validate_merge, model="claude-opus-5-5", effort="medium", max_tokens=64000)
PATHWAY_METHOD = "mechanism_pathway@v1+pathway_names@v2"


def mechanism_keys(cur) -> dict[int, tuple[str, str, str]]:
    """Entity -> (mechanism_key, target_label, action) for every entity with a current FDA label: its reviewed target
    and action where the atlas reviewed it, else its primary targets and their actions."""
    cur.execute("""SELECT DISTINCT m.moiety_id FROM preclin.fda_label l JOIN preclin.moiety m ON m.unii = ANY(l.unii)""")
    labelled = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT moiety_id, target_label, coalesce(action, '') FROM preclin.atlas_moiety_review "
                "WHERE moiety_id = ANY(%s)", (labelled,))
    out = {mid: (f"{target}|{action}", target, action) for mid, target, action in cur.fetchall()}
    cur.execute("""SELECT mt.moiety_id, string_agg(DISTINCT t.symbol, ';' ORDER BY t.symbol),
                          string_agg(DISTINCT mt.action, ';' ORDER BY mt.action)
                   FROM preclin.moiety_target mt JOIN public.targets t ON t.id = mt.target_id
                   WHERE mt.is_primary AND mt.moiety_id = ANY(%s) AND t.symbol IS NOT NULL GROUP BY 1""",
                ([m for m in labelled if m not in out],))
    out.update({mid: (f"{target}|{action}", target, action) for mid, target, action in cur.fetchall()})
    return out


def pathways(_args) -> None:
    """Name the pathways of every atlas mechanism and every labelled entity's mechanism, merge spelling variants into
    canonical names, store the table."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT mechanism_key, target_label, action, label FROM preclin.atlas_mechanism")
        mechanisms = {key: (target, action, label) for key, target, action, label in cur.fetchall()}
        cur.execute("""SELECT a.mechanism_key, m.name, string_agg(DISTINCT i.label, ', ')
                       FROM preclin.atlas_member a JOIN preclin.moiety m ON m.moiety_id = a.entity_id
                       JOIN preclin.atlas_indication i ON i.mondo_id = a.mondo_id
                       WHERE a.mechanism_key IS NOT NULL GROUP BY 1, 2 ORDER BY 1, 2""")
        drugs: dict[str, list[str]] = {}
        for key, name, diseases in cur.fetchall():
            drugs.setdefault(key, []).append(f"{name} ({diseases})")
        labelled = mechanism_keys(cur)
        cur.execute("SELECT moiety_id, name FROM preclin.moiety WHERE moiety_id = ANY(%s)", (list(labelled),))
        names = dict(cur.fetchall())
    for mid, (key, target, action) in sorted(labelled.items()):
        mechanisms.setdefault(key, (target, action, f"{target} {action}"))
        if key not in drugs or len(drugs[key]) < 5:
            drugs.setdefault(key, []).append(f"{names[mid]} (FDA-approved)")
    items = {key: {"label": label, "target_label": target, "action": action, "drugs": drugs.get(key, [])[:5]}
             for key, (target, action, label) in mechanisms.items()}
    named = {key: (decision_id, out) for key, decision_id, out in llm.decisions(llm.run(PATHWAY_TASK, items))}

    counts = Counter(p for _, out in named.values() for p in out["pathways"])
    merge_run = llm.run(MERGE_TASK, {"atlas": {"names": sorted(counts.items())}})
    [(_, merge_id, merged)] = llm.decisions(merge_run)
    canonical = {m["name"]: m["canonical"] for m in merged["names"]}

    rows = [(key, out["kind"], sorted({c for p in out["pathways"] for c in canonical[p]}), decision_id,
             merge_id if out["kind"] == "specific" else None)
            for key, (decision_id, out) in named.items()]
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, PATHWAY_METHOD, "Pathways of atlas and labelled mechanisms",
                          PATHWAY_SYSTEM + "\n\n" + MERGE_SYSTEM,
                          ["preclin.atlas_mechanism", "preclin.atlas_member", "preclin.atlas_moiety_review",
                           "preclin.moiety_target", "preclin.fda_label", "preclin.moiety"],
                          {"tasks": [PATHWAY_TASK.name, MERGE_TASK.name],
                           "prompt_versions": [PATHWAY_TASK.prompt_version, MERGE_TASK.prompt_version],
                           "model": PATHWAY_TASK.model, "merge_run": str(merge_run)})
        cur.execute("DELETE FROM preclin.mechanism_pathway")
        execute_values(cur, """INSERT INTO preclin.mechanism_pathway (mechanism_key, kind, pathways, llm_decision_id,
                                 merge_decision_id) VALUES %s""", rows, page_size=2000)
        conn.commit()
    print(f"mechanisms={len(rows)} kinds={dict(Counter(r[1] for r in rows))} "
          f"names={len(counts)} canonical={len({c for cs in canonical.values() for c in cs})}")


INDICATION_SYSTEM = """You read the Indications and Usage section of a US FDA drug label and say which diseases on a fixed list the label treats or prevents.

A disease counts when the label is indicated to treat it, to control its defining measure (blood pressure for hypertension, LDL cholesterol for hyperlipidemia, HbA1c for type 2 diabetes, weight for obesity), or, for a disease defined by events, to reduce those events: a drug indicated to reduce the risk of myocardial infarction, stroke or cardiovascular death in patients with coronary heart disease counts for coronary artery disease; one reducing stroke and systemic embolism in nonvalvular atrial fibrillation counts for atrial fibrillation; one reducing cardiovascular death or hospitalisation in heart failure counts for heart failure.

A disease does not count when the label mentions it only as a population restriction, a contraindication, a comorbidity of the treated patients, or a different disease that shares a word (ocular hypertension is not essential hypertension; pulmonary arterial hypertension is its own entry; acute migraine treatment counts for migraine). Return an empty list when none applies."""


def indication_schema(ids: list[str]) -> dict:
    return {"type": "object",
            "properties": {"diseases": {"type": "array", "items": {"type": "string", "enum": ids}},
                           "reason": {"type": "string"}},
            "required": ["diseases", "reason"], "additionalProperties": False}


SHORTLISTED = {**SHORTLIST, **EVENT_SHORTLIST}


def render_indication(p: dict) -> str:
    listed = "\n".join(f"{mid}: {e.disease}" for mid, e in SHORTLISTED.items())
    return f"Diseases:\n{listed}\n\nIndications and Usage:\n{p['text']}"


INDICATION_TASK = llm.Task(name="label_indication", prompt_version="v1", schema_version="v1", system=INDICATION_SYSTEM,
                           schema=indication_schema(list(SHORTLISTED)), render=render_indication,
                           subject_type="label_indications_text", model="claude-opus-5-5", effort="low",
                           max_tokens=1500)
INDICATION_METHOD = "label_indication@v1"


def indications(_args) -> None:
    """Which shortlisted diseases each current FDA label treats, decided once per distinct indications text."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT set_id, indications_text FROM preclin.fda_label WHERE indications_text IS NOT NULL")
        labels = cur.fetchall()
    by_text: dict[str, list[str]] = {}
    for set_id, text in labels:
        by_text.setdefault(llm.sha256_text(text), []).append(set_id)
    texts = {llm.sha256_text(text): text for _, text in labels}
    run_id = llm.run(INDICATION_TASK, {h: {"text": t} for h, t in texts.items()})
    rows = [(set_id, mid, decision_id) for h, decision_id, out in llm.decisions(run_id)
            for mid in sorted(set(out["diseases"])) for set_id in by_text[h]]
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, INDICATION_METHOD, "Shortlisted diseases an FDA label treats", INDICATION_SYSTEM,
                          ["preclin.fda_label"], {"task": INDICATION_TASK.name, "prompt_version": "v1",
                                                  "model": INDICATION_TASK.model, "run": str(run_id)})
        cur.execute("DELETE FROM preclin.label_indication")
        execute_values(cur, "INSERT INTO preclin.label_indication (set_id, mondo_id, llm_decision_id) VALUES %s",
                       rows, page_size=5000)
        conn.commit()
    print(f"labels={len(labels)} texts={len(texts)} rows={len(rows)} " + str(Counter(r[1] for r in rows)))

REGIMENS = ("monotherapy", "add_on_background", "combination")
ALONE = ("monotherapy", "add_on_background")
SUCCESS_FATES = ("worked_here", "worked_here_selected")
RECORD_CHARS = 12000  # of the summary and of the arm groups, each

REGIMEN_SYSTEM = f"""You read a clinical trial's registry record and decide how one drug, the drug of interest, was tested in it: alone or together with a partner drug.

{COMBINATION}

regimen:
- monotherapy: some experimental arm gives the drug of interest without any other active agent (placebo, vehicle or rescue medication do not count), whether against placebo, an active comparator or another dose;
- add_on_background: the drug of interest is added to background therapy that every arm receives, including the control arm (methotrexate, metformin, standard of care, stable conventional therapy, the same chemotherapy backbone in every arm), and no experimental arm pairs it with a further agent the control arm lacks;
- combination: every experimental arm that gives the drug of interest also gives another active agent on a different pathway that the control arm does not receive (or there is no control arm and the regimen is the pairing): a fixed-dose co-formulation, a protocol-specified pairing, or a drug added to a new partner.
When one arm gives the drug alone and another gives it with a partner, the regimen is monotherapy. Another drug acting through the same pathway as the drug of interest is not a partner. Hormone add-back therapy or an agent given to offset a side effect, when the control arm lacks it, is still a partner.

partner: for a combination, the paired agent or agents as the record names them; null otherwise. partner_moiety_id: for a combination, the entity id of the partner from the interventions list (the one newest to the regimen when there are several); null when the regimen is not combination or the partner has no entity id listed. Never give the drug of interest's own entity id.
quote: the record text (title, summary or arm group) that shows the regimen, copied exactly."""

REGIMEN_SCHEMA = {
    "type": "object",
    "properties": {
        "regimen": {"type": "string", "enum": list(REGIMENS)},
        "partner": {"type": ["string", "null"]},
        "partner_moiety_id": {"type": ["integer", "null"]},
        "quote": {"type": "string"},
    },
    "required": ["regimen", "partner", "partner_moiety_id", "quote"],
    "additionalProperties": False,
}


def render_regimen(p: dict) -> str:
    interventions = "\n".join(
        f"- {i['name']} ({i['type']}; arms: {', '.join(i['arms']) or 'not given'}; entities: "
        f"{', '.join(f'{n} [id {m}]' for m, n in i['entities']) or 'none'})" for i in p["interventions"])
    return (f"Drug of interest: {p['drug']} [id {p['moiety_id']}]\n\nTitle: {p['title']}\nOfficial title: "
            f"{p['official_title']}\n\nBrief summary:\n{p['summary']}\n\nArm groups:\n{p['arms']}\n\n"
            f"Interventions:\n{interventions}")


def validate_regimen(p: dict, out: dict) -> None:
    combination = out["regimen"] == "combination"
    if combination != bool(out["partner"] and out["partner"].strip()):
        raise ValueError(f"regimen {out['regimen']} with partner {out['partner']!r}")
    listed = {m for i in p["interventions"] for m, _ in i["entities"]} - {p["moiety_id"]}
    if out["partner_moiety_id"] is not None and (not combination or out["partner_moiety_id"] not in listed):
        raise ValueError(f"partner_moiety_id {out['partner_moiety_id']} with regimen {out['regimen']}")
    record = squash(" ".join([p["title"], p["official_title"], p["summary"], p["arms"]]))
    fragments = [f.strip() for f in re.split(r"\.\.\.|…", squash(out["quote"])) if f.strip()]
    if not fragments or any(f not in record for f in fragments):  # an ellipsis may join exact fragments
        raise ValueError(f"quote not in the record: {out['quote'][:120]}")


REGIMEN_TASK = llm.Task(name="trial_regimen", prompt_version="v1", schema_version="v1", system=REGIMEN_SYSTEM,
                        schema=REGIMEN_SCHEMA, render=render_regimen, validate=validate_regimen,
                        subject_type="trial_drug", model="claude-opus-5-5", effort="low", max_tokens=1500)
REGIMEN_METHOD = "trial_regimen@v1"
REGIMEN_DESCRIPTION = f"""Cohort: the stops of preclin.stop_target_history with target_fate {' or '.join(SUCCESS_FATES)}.
Their successes are those pipeline.target_history counts: another drug on the target (a partner there) approved for this
disease (MONDO Lin >= {CLOSE}) or with a Phase 2/3 trial there that met its primary endpoint (preclin.trial_outcome).
An approval is read through the met Phase 2/3 trials of the same program; an approval with none is a success of unknown
regimen. Each met trial is read for the drug that makes it a success (task {REGIMEN_TASK.name}
{REGIMEN_TASK.prompt_version}, model {REGIMEN_TASK.model}, effort {REGIMEN_TASK.effort}, no web): title, summary, arm
groups and interventions with the entities they resolve to, into monotherapy, add_on_background or combination under
the combination definition registered in #198, with the partner. success_regimen: alone when any success trial is
monotherapy or add_on_background; with_partner when every success is a combination trial; unknown otherwise (an approval
with no met trial). For with_partner, the met trials in the disease of each combination partner not approved for it are
read the same way, with the partner as the drug; partner_works_alone is true when every partner is approved in the
disease or tested alone in a met trial there, false when a resolved partner is neither, null when a partner did not
resolve to an entity."""


def success_regimen(regimens: list[str], unread_approvals: int) -> str:
    """How a target worked in a disease, from the regimens of its success trials and the number of its approvals with
    no met trial to read: alone if any success tested the drug alone, with_partner only if every one paired it."""
    if any(r in ALONE for r in regimens):
        return "alone"
    if regimens and not unread_approvals:
        return "with_partner"
    return "unknown"


def partner_works_alone(partners: list[int | None], works_alone: set[int]) -> bool | None:
    """Whether the partners of a with_partner success (one per combination trial, None when unresolved) all work on
    their own in the disease."""
    if any(p is not None and p not in works_alone for p in partners):
        return False
    if any(p is None for p in partners):
        return None
    return True


def met_trials() -> dict[tuple[int, str], set[str]]:
    """(entity, disease) -> its Phase 2/3 trials that met their primary endpoint, as pipeline.target_history counts
    them."""
    met = frame.query("""
        SELECT DISTINCT p.moiety_id, p.mondo_id, o.nct_id FROM preclin.trial_outcome o
        JOIN preclin.dev_program_trial dt USING (nct_id) JOIN preclin.dev_program p USING (program_id)
        WHERE dt.phase >= 2 AND p.mondo_id IS NOT NULL AND o.primary_endpoint = 'met'""")
    return met.groupby(["moiety_id", "mondo_id"]).nct_id.apply(set).to_dict()


def regimen_items(pairs: set[tuple[str, int]]) -> dict[str, dict]:
    """Payload per (trial, drug of interest), keyed nct_id|moiety_id."""
    ncts = sorted({n for n, _ in pairs})
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT nct_id, brief_title, official_title, brief_summary, arm_groups
                       FROM preclin.ctgov_study WHERE nct_id = ANY(%s)""", (ncts,))
        studies = {r[0]: r[1:] for r in cur.fetchall()}
        cur.execute("""SELECT sd.nct_id, d.display_name, sd.intervention_type, sd.arm_types,
                              coalesce(array_agg(m.moiety_id ORDER BY m.moiety_id) FILTER (WHERE m.moiety_id IS NOT NULL), '{}'),
                              coalesce(array_agg(m.name ORDER BY m.moiety_id) FILTER (WHERE m.moiety_id IS NOT NULL), '{}')
                       FROM preclin.ctgov_study_drug sd JOIN preclin.drug d USING (drug_id)
                       LEFT JOIN preclin.drug_moiety dm USING (drug_id) LEFT JOIN preclin.moiety m USING (moiety_id)
                       WHERE sd.nct_id = ANY(%s) GROUP BY 1, 2, 3, 4 ORDER BY 1, 2""", (ncts,))
        interventions: dict[str, list[dict]] = {}
        for nct, name, kind, arms, ids, names in cur.fetchall():
            interventions.setdefault(nct, []).append({"name": name, "type": kind, "arms": arms or [],
                                                      "entities": list(zip(ids, names))})
        cur.execute("SELECT moiety_id, name FROM preclin.moiety WHERE moiety_id = ANY(%s)",
                    (sorted({m for _, m in pairs}),))
        names = dict(cur.fetchall())
    items = {}
    for nct, m in sorted(pairs):
        title, official, summary, arms = studies[nct]
        arm_text = "\n".join(f"- {a.get('label', '')} ({a.get('type', 'type not given')}): {a.get('description', '')}"
                             f" Interventions: {', '.join(a.get('interventionNames', []))}" for a in arms or [])
        items[f"{nct}|{m}"] = {"moiety_id": m, "drug": names[m], "title": title or "", "official_title": official or "",
                               "summary": (summary or "")[:RECORD_CHARS],
                               "arms": arm_text[:RECORD_CHARS] or "(not registered)",
                               "interventions": interventions.get(nct, [])}
    return items


def read_regimens(pairs: set[tuple[str, int]]) -> tuple[uuid.UUID, dict[tuple[str, int], tuple[int, dict]]]:
    """Run the regimen task on (trial, drug) pairs: the run id and (trial, drug) -> (decision id, output). Every pair
    must validate; a rerun reuses the validated decisions and asks again for the rest."""
    run_id = llm.run(REGIMEN_TASK, regimen_items(pairs))
    read = {(k.split("|")[0], int(k.split("|")[1])): (i, o) for k, i, o in llm.decisions(run_id)}
    if missing := pairs - set(read):
        raise SystemExit(f"run {run_id}: {len(missing)} of {len(pairs)} decisions failed validation; rerun to retry")
    return run_id, read


def regimens(_args) -> None:
    """Read the regimen of every success behind a worked_here stop, and of its partners' trials in the disease when it
    needed a partner; store preclin.trial_regimen and the two regimen columns of preclin.stop_target_history."""
    d = stored()
    d = d[d.target_fate.isin(SUCCESS_FATES)]
    h = History()
    trials = met_trials()
    behind: dict[str, tuple[set[tuple[str, int]], int]] = {}  # stop -> (success trial, drug) pairs, unread approvals
    for r in d.itertuples():
        close = h.nb.terms(r.mondo_id, CLOSE)
        here = {(s.moiety_id, s.mondo_id, s.kind) for o in h.partners.get(r.moiety_id, ())
                for s in h.succ.get(o, ()) if s.mondo_id in close}
        pairs = {(n, m) for m, x, kind in here if kind == "met" for n in trials[(m, x)]}
        unread = sum(1 for m, x, kind in here if kind == "approved" and (m, x) not in trials)
        behind[r.key] = (pairs, unread)
    run_id, read = read_regimens({p for pairs, _ in behind.values() for p in pairs})

    regimen = {}
    for r in d.itertuples():
        pairs, unread = behind[r.key]
        regimen[r.key] = success_regimen([read[p][1]["regimen"] for p in pairs], unread)
    # partners of with_partner successes, and their met trials in the disease where they are not approved for it
    partners_of = {k: [read[p][1]["partner_moiety_id"] for p in behind[k][0]] for k, v in regimen.items()
                   if v == "with_partner"}
    asked: dict[str, tuple[set[int], set[tuple[str, int]]]] = {}  # stop -> (approved partners, partner trial pairs)
    for r in d[d.key.isin(set(partners_of))].itertuples():
        close = h.nb.terms(r.mondo_id, CLOSE)
        approved, pairs = set(), set()
        for p in {p for p in partners_of[r.key] if p is not None}:
            for s in h.succ.get(p, ()):
                if s.mondo_id in close and s.kind == "approved":
                    approved.add(p)
                elif s.mondo_id in close:
                    pairs |= {(n, p) for n in trials[(p, s.mondo_id)]}
        asked[r.key] = (approved, {q for q in pairs if q[1] not in approved})
    todo = {q for _, pairs in asked.values() for q in pairs} - set(read)
    partner_run, partner_read = read_regimens(todo) if todo else (None, {})
    read |= partner_read
    alone_partner = {k: partner_works_alone(partners_of[k], approved | {p for n, p in pairs
                                                                        if read[(n, p)][1]["regimen"] in ALONE})
                     for k, (approved, pairs) in asked.items()}

    rows = [(n, m, o["regimen"], o["partner"], o["partner_moiety_id"], o["quote"], i) for (n, m), (i, o) in read.items()]
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, REGIMEN_METHOD, "Alone or with a partner: the regimen of a success on a stopped target",
                          REGIMEN_DESCRIPTION,
                          ["preclin.stop_target_history", "preclin.trial_outcome", "preclin.dev_program_trial",
                           "preclin.dev_program_approval", "preclin.ctgov_study", "preclin.ctgov_study_drug",
                           "preclin.drug_moiety"],
                          {"task": REGIMEN_TASK.name, "prompt_version": REGIMEN_TASK.prompt_version,
                           "model": REGIMEN_TASK.model, "effort": REGIMEN_TASK.effort, "close": CLOSE,
                           "run": str(run_id), "partner_run": str(partner_run) if partner_run else None})
        cur.execute("DELETE FROM preclin.trial_regimen")
        execute_values(cur, """INSERT INTO preclin.trial_regimen (nct_id, moiety_id, regimen, partner, partner_moiety_id,
                                 quote, llm_decision_id) VALUES %s""", rows, page_size=5000)
        cur.execute("UPDATE preclin.stop_target_history SET success_regimen = NULL, partner_works_alone = NULL")
        execute_values(cur, """UPDATE preclin.stop_target_history h SET success_regimen = v.regimen,
                                 partner_works_alone = v.alone
                               FROM (VALUES %s) AS v(moiety_id, mondo_id, phase, regimen, alone)
                               WHERE (h.moiety_id, h.mondo_id, h.phase) = (v.moiety_id, v.mondo_id, v.phase)""",
                       [(int(k.split("|")[0]), k.split("|")[1], int(k.split("|")[2]), v, alone_partner.get(k))
                        for k, v in regimen.items()], template="(%s, %s, %s, %s, %s::boolean)")
        conn.commit()
    print(f"trials read={len(rows)} {dict(Counter(r[2] for r in rows))} run={run_id} partner_run={partner_run}")
    regimen_summary(None)


def regimen_summary(_args) -> None:
    """Counts by success regimen and partner, over every worked_here stop and those with a phase entry in the
    headline window, and across the #158 stops (worked_here with verdict target_not_causal)."""
    d = stored()
    print(f"engaged-without-benefit stops: {len(d)}, with a phase entry in the window: {int(d.headline.sum())}")
    d = d[d.target_fate.isin(SUCCESS_FATES)].copy()
    d["partner"] = d.partner_works_alone.map({True: "works alone", False: "not alone"})
    d["partner"] = d.partner.where(d.partner.notna(), d.success_regimen.eq("with_partner").map({True: "cannot tell",
                                                                                                False: "-"}))
    for name, g in (("all", d), ("phase entry in window", d[d.headline]),
                    ("#158: worked_here, target_not_causal", d[d.target_fate.eq("worked_here")
                                                               & d.verdict.eq("target_not_causal")]),
                    ("#158 in window", d[d.headline & d.target_fate.eq("worked_here")
                                         & d.verdict.eq("target_not_causal")])):
        print(f"\n{name}: {len(g)} stops")
        print(pd.crosstab([g.target_fate, g.success_regimen.fillna("(none)")], g.partner, margins=True).to_string())


# Randomised trials of two pathways against one (#196), the trial half of the several-targets rule
# (combination_beats_single). Known trials seed each disease's search; the model finds the rest.
SEED_TRIALS = {
    "MONDO:0005083": ["BE RADIANT, Reich 2021 (PMID 33891380): bimekizumab (IL-17A and IL-17F) vs secukinumab (IL-17A)"],
    "MONDO:0008383": ["Genovese 2004 (PMID 15146410): anakinra plus etanercept vs etanercept",
                      "Weinblatt 2007 (PMID 16935912): abatacept added to a TNF blocker vs the TNF blocker alone"],
    "MONDO:0011122": ["SURMOUNT-5: tirzepatide (GIP and GLP-1) vs semaglutide (GLP-1)"],
    "MONDO:0005148": ["SURPASS-2: tirzepatide vs semaglutide"],
    "MONDO:0005252": ["PARADIGM-HF: sacubitril/valsartan vs enalapril", "DAPA-HF: dapagliflozin added to background",
                      "EMPEROR-Reduced: empagliflozin added to background", "RALES: spironolactone added to background",
                      "EMPHASIS-HF: eplerenone added to background"],
    "MONDO:0005300": ["CREDENCE, DAPA-CKD, EMPA-KIDNEY: an SGLT2 inhibitor added to a renin-angiotensin blocker",
                      "FIDELIO-DKD: finerenone added to a renin-angiotensin blocker",
                      "VA NEPHRON-D and ALTITUDE: a second renin-angiotensin blocker added to the first"],
    "MONDO:0005010": ["IMPROVE-IT: ezetimibe added to simvastatin", "FOURIER and ODYSSEY OUTCOMES: a PCSK9 antibody "
                      "added to a statin", "COMPASS: rivaroxaban added to aspirin", "CANTOS: canakinumab added to "
                      "background"],
    "MONDO:0004981": ["ACTIVE A: clopidogrel added to aspirin"],
    "MONDO:0015924": ["AMBITION: ambrisentan plus tadalafil vs either alone", "GRIPHON: selexipag added to background",
                      "STELLAR: sotatercept added to background", "SERAPHIN: macitentan, most patients on background"],
}

COMBO_DESIGNS = ("combination", "add_on", "head_to_head_multi_pathway")
COMBO_RELATIONS = ("same_pathway", "parallel", "independent")
COMBO_RESULTS = ("met_primary", "missed_primary")
COMBO_LIMITS = ("none", "efficacy", "safety")
EFFECT_MEASURES = ("risk_difference", "hazard_ratio", "mean_difference", "other")


def combos_system(pathway_names: list[str]) -> str:
    return f"""You find randomised trials that test two pathways against one in one disease, and read each one.

Qualifying trials are randomised, Phase 2b or 3 or a large Phase 2, in the disease you are given, and compare an arm acting through two pathways with an arm acting through one of them:
- combination: two drugs on different pathways given together vs one of them alone (or vs one of them plus placebo);
- add_on: a drug on a new pathway added to a fixed background on another pathway vs the background alone (with placebo). For event diseases (heart failure, coronary artery disease, chronic kidney disease, atrial fibrillation, pulmonary arterial hypertension) these add-on outcome trials are the main evidence; the background may span several pathways;
- head_to_head_multi_pathway: one molecule acting through two pathways (a bispecific, a multi-receptor agonist) or a co-formulation vs a drug acting through only one of them.
Both arms' pathways must be specific. Conventional background with no specific pathway (methotrexate, azathioprine, 6-mercaptopurine, ciclosporin, corticosteroids, other general immunosuppressants or cytotoxics) is background care: a drug added to it, or combined with it, is tested alone, and the trial does not qualify (infliximab plus azathioprine vs infliximab; a biologic plus methotrexate vs methotrexate). A trial of a drug against placebo with no shared background pathway does not qualify, nor does a trial of two drugs on the same single pathway with no second pathway (two TNF blockers), nor a trial comparing two different single pathways head to head.

{COMBINATION}

relation, how the added pathway relates to the comparator's pathway:
- same_pathway: both arms act on one pathway; the two-pathway arm only blocks more of it (IL-17A vs IL-17A plus IL-17F; a second renin-angiotensin blocker on the first);
- parallel: different pathways converging on the same disease process (IL-17 and TNF in psoriasis; GIP and GLP-1 in obesity; a statin and ezetimibe lowering LDL; an SGLT2 inhibitor added to renin-angiotensin blockade for heart failure);
- independent: unrelated disease processes (an anti-inflammatory added to lipid lowering in coronary disease; an anticoagulant added to an antiplatelet).

result: met_primary when the two-pathway arm was statistically superior to the one-pathway arm on the trial's primary efficacy endpoint; otherwise missed_primary (including a non-inferiority primary with no superiority shown, and a trial stopped before its primary was read).
effect: the primary endpoint estimate of the two-pathway arm against the one-pathway arm: for a responder endpoint the difference in the share of patients responding in percentage points (risk_difference, e.g. 13.5 for 61.7% vs 48.2%); for an event endpoint the hazard ratio (hazard_ratio); a mean difference for a continuous primary; with the 95% confidence interval when reported, null otherwise. effect_text states it in words with the endpoint and time point.
limited_by: what held the two-pathway arm back: none (it won and was safe enough to use), efficacy (no or too small a gain), safety (more harm: serious infections, hyperkalaemia, kidney injury, bleeding). A trial that met its primary but whose regimen was dropped for harm is safety.
stopped_for_safety: true when the trial or its two-pathway arm was stopped early for harm, or the two-pathway regimen was abandoned or advised against because of harm seen in it (e.g. a regulator warning or a guideline recommending against the combination on safety grounds).

pathways: name each with the canonical names below, written exactly as listed, wherever one fits; only when none does, use a short conventional name. comparator_pathways: the pathways of the one-pathway arm only (for an add-on trial, the background's main pathways). added_pathway: the pathway the two-pathway arm adds (for same_pathway, the shared pathway itself). When a trial has two monotherapy arms (A plus B vs A vs B), compare against the monotherapy the primary analysis names, or else the first-listed, and list only that arm's pathway: AMBITION is comparator ["Endothelin"], added "NO-cGMP".

Canonical pathway names: {"; ".join(pathway_names)}

How to search: start with the seed trials given (find each one's publication and registration) and then search for further trials in the disease: trial registries (ClinicalTrials.gov), PubMed, journal pages, systematic reviews and network meta-analyses of combination or add-on therapy, regulatory reviews. Return up to 12 trials per disease: the largest and most cited, every head-to-head multi-pathway trial, and well-known negative or safety-stopped ones. Return none when the disease has none.

Judge only from pages you retrieved; never fill an NCT id, PMID or number from memory. For each trial give nct_id (NCT followed by 8 digits) and pmid (digits) of the primary results paper as shown on a page you retrieved, null if not found; leave out a trial for which you found neither. One entry per trial: a paper reporting two trials gives two entries, each with its own NCT id. sources: URLs from your own web_search results or web_fetch calls that show the trial's design and result, copied character for character as the tool returned them (never shortened, never a URL you did not see returned); a PubMed link counts only if a search returned it or you fetched it. quote: the sentence from a source that states the primary result."""


COMBO_SCHEMA = {
    "type": "object",
    "properties": {"trials": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "trial_name": {"type": "string"},
            "nct_id": {"type": ["string", "null"]},
            "pmid": {"type": ["string", "null"]},
            "year": {"type": ["integer", "null"]},
            "phase": {"type": "string"},
            "n_randomised": {"type": ["integer", "null"]},
            "two_pathway_arm": {"type": "string"},
            "one_pathway_arm": {"type": "string"},
            "comparator_pathways": {"type": "array", "items": {"type": "string"}},
            "added_pathway": {"type": "string"},
            "design": {"type": "string", "enum": list(COMBO_DESIGNS)},
            "relation": {"type": "string", "enum": list(COMBO_RELATIONS)},
            "primary_endpoint": {"type": "string"},
            "result": {"type": "string", "enum": list(COMBO_RESULTS)},
            "effect_measure": {"type": "string", "enum": list(EFFECT_MEASURES)},
            "effect": {"type": ["number", "null"]},
            "ci_low": {"type": ["number", "null"]},
            "ci_high": {"type": ["number", "null"]},
            "effect_text": {"type": "string"},
            "limited_by": {"type": "string", "enum": list(COMBO_LIMITS)},
            "stopped_for_safety": {"type": "boolean"},
            "sources": {"type": "array", "items": {"type": "string"}},
            "quote": {"type": "string"},
        },
        "required": ["trial_name", "nct_id", "pmid", "year", "phase", "n_randomised", "two_pathway_arm",
                     "one_pathway_arm", "comparator_pathways", "added_pathway", "design", "relation",
                     "primary_endpoint", "result", "effect_measure", "effect", "ci_low", "ci_high", "effect_text",
                     "limited_by", "stopped_for_safety", "sources", "quote"],
        "additionalProperties": False}}},
    "required": ["trials"],
    "additionalProperties": False,
}


def trial_key(t: dict) -> str:
    """The trial's key within a disease: its NCT id, else PMID:n."""
    return t["nct_id"] or f"PMID:{t['pmid']}"


def retrieved_source(source: str, retrieved: list[str]) -> str | None:
    """The retrieved URL a cited source stands for: the same URL, or one it is a truncation of (the model shortens
    long URLs); None when it stands for none."""
    cited = llm.norm_url(source)
    return next((u for u in retrieved if llm.norm_url(u) == cited), None) or next(
        (u for u in retrieved if len(cited) >= 30 and llm.norm_url(u).startswith(cited)), None)


def validate_combos(_payload: dict, out: dict) -> None:
    retrieved = out.get("retrieved_urls", [])
    if not retrieved:
        raise ValueError("no search returned anything, so no answer either way")
    keys = []
    for t in out["trials"]:
        name = t["trial_name"]
        if t["nct_id"] is not None and not re.fullmatch(r"NCT\d{8}", t["nct_id"]):
            raise ValueError(f"{name}: nct_id {t['nct_id']!r}")
        if t["pmid"] is not None and not re.fullmatch(r"\d{6,9}", t["pmid"]):
            raise ValueError(f"{name}: pmid {t['pmid']!r}")
        if not (t["nct_id"] or t["pmid"]):
            raise ValueError(f"{name}: neither an NCT id nor a PMID")
        if not t["sources"]:
            raise ValueError(f"{name}: no sources")
        unknown = [s for s in t["sources"] if retrieved_source(s, retrieved) is None]
        if unknown:
            raise ValueError(f"{name}: cites sources it did not retrieve: {unknown[:3]}")
        if not t["comparator_pathways"] or not t["added_pathway"].strip():
            raise ValueError(f"{name}: pathways missing")
        if (t["relation"] == "same_pathway") != (t["added_pathway"] in t["comparator_pathways"]):
            raise ValueError(f"{name}: relation {t['relation']} with added {t['added_pathway']} on "
                             f"{t['comparator_pathways']}")
        if t["effect_measure"] == "hazard_ratio" and t["effect"] is not None and t["effect"] <= 0:
            raise ValueError(f"{name}: hazard ratio {t['effect']}")
        if None not in (t["ci_low"], t["ci_high"]) and t["ci_low"] > t["ci_high"]:
            raise ValueError(f"{name}: confidence interval reversed")
        keys.append(trial_key(t))
    if len(keys) != len(set(keys)):
        raise ValueError(f"a trial listed twice: {sorted(k for k, n in Counter(keys).items() if n > 1)}")


def render_combos(p: dict) -> str:
    seeds = "\n".join(f"- {s}" for s in p["seeds"]) or "(none)"
    return (f"Disease: {p['disease']} ({p['mondo_id']})\nEndpoint it is measured on: {p['endpoint']}\n\n"
            f"Seed trials:\n{seeds}")


COMBO_TOOLS = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 25},
               {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 12}]
COMBO_METHOD = "combination_trial@v2"


def combos_task(pathway_names: list[str]) -> llm.Task:
    return llm.Task(name="combination_trial", prompt_version="v2", schema_version="v1",
                    system=combos_system(pathway_names), schema=COMBO_SCHEMA, render=render_combos,
                    subject_type="mondo_disease", validate=validate_combos, model="claude-opus-5-5",
                    effort="medium", max_tokens=32000, tools=COMBO_TOOLS)


def combination_beats_single(rows: list[dict]) -> bool:
    """Whether a disease's randomised trials (rows of preclin.combination_trial) show two pathways beating one: a
    trial whose two arms differ by a second pathway (not same_pathway) met its efficacy primary endpoint, and its
    two-pathway arm was not stopped or abandoned for safety."""
    return any(r["relation"] != "same_pathway" and r["result"] == "met_primary" and not r["stopped_for_safety"]
               for r in rows)


def combos(_args) -> None:
    """Find and read each shortlisted disease's randomised trials of two pathways against one; store the table."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT p FROM preclin.mechanism_pathway, unnest(pathways) p ORDER BY 1")
        names = [r[0] for r in cur.fetchall()]
    task = combos_task(names)
    items = {mondo: {"mondo_id": mondo, "disease": e.disease, "endpoint": e.endpoint,
                     "seeds": SEED_TRIALS.get(mondo, [])}
             for mondo, e in {**SHORTLIST, **EVENT_SHORTLIST}.items()}
    run_id = llm.run(task, items)
    decided = {mondo for mondo, _, _ in llm.decisions(run_id)}
    if decided != set(items):  # the table is replaced whole, so a disease without a decision would lose its rows
        raise SystemExit(f"no valid decision for {sorted(set(items) - decided)}; run again (decided ones are reused)")
    rows = [(mondo, trial_key(t), t["trial_name"], t["nct_id"], t["pmid"], t["year"], t["phase"],
             t["n_randomised"], t["two_pathway_arm"], t["one_pathway_arm"], t["comparator_pathways"],
             t["added_pathway"], t["design"], t["relation"], t["primary_endpoint"], t["result"],
             t["effect_measure"], t["effect"], t["ci_low"], t["ci_high"], t["effect_text"], t["limited_by"],
             t["stopped_for_safety"], sorted({retrieved_source(u, out["retrieved_urls"]) for u in t["sources"]}),
             t["quote"], decision_id)
            for mondo, decision_id, out in llm.decisions(run_id) for t in out["trials"]]
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, COMBO_METHOD, "Randomised trials of two pathways against one", task.system,
                          ["web search", "preclin.mechanism_pathway"],
                          {"task": task.name, "prompt_version": task.prompt_version, "model": task.model,
                           "run": str(run_id)})
        cur.execute("DELETE FROM preclin.combination_trial")
        execute_values(cur, """INSERT INTO preclin.combination_trial (mondo_id, trial_key, trial_name, nct_id, pmid,
                                 year, phase, n_randomised, two_pathway_arm, one_pathway_arm, comparator_pathways,
                                 added_pathway, design, relation, primary_endpoint, result, effect_measure, effect,
                                 ci_low, ci_high, effect_text, limited_by, stopped_for_safety, sources, quote,
                                 llm_decision_id) VALUES %s""", rows)
        conn.commit()
    by_disease: dict[str, list[dict]] = {}
    for r in rows:
        by_disease.setdefault(r[0], []).append({"relation": r[13], "result": r[15], "stopped_for_safety": r[22]})
    print(f"diseases={len(items)} trials={len(rows)} "
          f"relations={dict(Counter(r[13] for r in rows))} results={dict(Counter(r[15] for r in rows))}")
    for mondo, e in {**SHORTLIST, **EVENT_SHORTLIST}.items():
        trials = by_disease.get(mondo, [])
        print(f"  {e.disease}: trials={len(trials)} combination_beats_single={combination_beats_single(trials)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(required=True)
    for name, fn in (("indications", indications), ("pathways", pathways), ("regimens", regimens),
                     ("regimen-summary", regimen_summary), ("combos", combos)):
        sub.add_parser(name).set_defaults(fn=fn)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
