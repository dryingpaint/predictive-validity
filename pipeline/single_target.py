"""Which diseases the target-based drugging paradigm solves (#197): definitions registered in #198, the pathway of
every atlas mechanism, and randomised trials of two pathways against one (#196).

    python -m pipeline.single_target indications  # LLM: shortlisted diseases each FDA label treats -> preclin.label_indication
    python -m pipeline.single_target pathways     # LLM: pathways of atlas and labelled mechanisms -> preclin.mechanism_pathway
    python -m pipeline.single_target regimens     # LLM: alone or with a partner, for each success on a stopped target
                                                  #   -> preclin.trial_regimen, preclin.stop_target_history
    python -m pipeline.single_target combos       # LLM + web: randomised trials of two pathways vs one
                                                  #   -> preclin.combination_trial
    python -m pipeline.single_target responses    # LLM + web: published responder shares, crossover, event hazard
                                                  #   ratios, risk factor -> outcome -> preclin.mechanism_response

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
# The diseases #193 confirmed under that rule, the ones the labels are computed for: hidradenitis suppurativa has two
# approved pathways (TNF, IL-17). report.single_target checks this against the rule on the current labels.
DROPPED = ("MONDO:0006559",)
CONFIRMED = {mondo: e for mondo, e in SHORTLIST.items() if mondo not in DROPPED}
EVENTS_CONFIRMED = {mondo: e for mondo, e in EVENT_SHORTLIST.items() if mondo not in DROPPED}

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


# Published estimates behind the labels (#195), one decision per confirmed disease and question, or per risk factor ->
# outcome pair. A pair's decision is shown the risk factor's response estimates, so pairs run after the rest.
MEASURES = ("share", "hazard_ratio", "odds_ratio")
POPULATIONS = ("naive", "prior_failure", "on_background", "lifelong_genetic")
SOURCE_KINDS = ("nma", "pooled_trials", "trial", "mendelian_randomisation")

QUESTION_TEXT = {
    "response": """Question: response. For every drug approved (US or EU) for the disease, and for drugs positive in Phase 3 for it, give its placebo-adjusted share reaching the endpoint in the window, in patients naive to advanced therapy (no prior biologic or targeted synthetic drug; for a metabolic or cardiovascular disease, patients on no drug of a specific pathway beyond the background care named below). Where a network meta-analysis pools a class, one row for the class is enough; give separate rows for molecules the source separates when they differ materially. Add every multi-drug regimen (two or more separate drugs on specific pathways, started together) tested against placebo or against background care alone on this endpoint, one_drug false; the best one matters most. A drug added to a background drug on a specific pathway, against that background alone, is population on_background with the background in background_pathways. population is naive or on_background.""",
    "crossover": """Question: crossover. For every (failed pathway A -> pathway B) comparison you can find, give two rows sharing one pair_key: B's placebo-adjusted share in patients who failed or were intolerant of A (an inadequate-responder trial such as TNF-IR in rheumatoid arthritis, psoriatic arthritis, ankylosing spondylitis, ulcerative colitis or Crohn disease, a prior-biologic subgroup of a placebo-controlled trial, or a network meta-analysis of the prior-failure population), population prior_failure with failed_pathway A; and B's placebo-adjusted share in naive patients from the same source family (the same network meta-analysis, the same programme's naive trial, or the naive subgroup of the same trial), population naive, on the same endpoint and time point, so that the ratio is like for like. The registered endpoint is preferred; when the source family reports the prior-failure result only on another responder endpoint (ACR20, clinical response), use that endpoint for both rows. Each row gives B's pathways in pathways. Search (trial registries, PubMed, reviews of resistant or refractory disease) before concluding; return no rows only when your searches found no such comparison.""",
    "events": """Question: events. measure hazard_ratio throughout, on the registered event endpoint (or the closest composite the trial reports, named in endpoint). (a) For every drug approved or Phase 3-positive for the disease with a placebo-controlled outcome trial, its hazard ratio against placebo; population naive when the trial had no background on a specific pathway, otherwise on_background with those pathways in background_pathways (a drug added to background care is still that one drug's effect against placebo). (b) The disease's best stack: a sequence of pathways where position 1 was tested against placebo, and each later position was added to a background that included the pathways of the positions before it, against that background with placebo; mark those rows with stack_position 1, 2, 3, ... Prefer the stack modern guidelines recommend. Use the randomised add-on trials listed in the message where they fit, with their published hazard ratios on this endpoint. trial_weeks is the median follow-up in weeks.""",
    "pair": """Question: pair. The risk factor's own response estimates are listed in the message. (a) Take the drug (or class) with the largest one-drug placebo-adjusted share there: the drug that best solves the risk factor. Give its hazard ratio on the outcome disease's event endpoint from its placebo-controlled outcome trial, with trial_weeks and in per_unit the risk-factor change the trial achieved. When that drug has no placebo-controlled outcome trial on the endpoint, give the drug of the same pathway closest to it that has one and say so in derivation; when the pathway has none, give the outcome trial of the next-best drug on the risk-factor list. (b) Any Mendelian randomisation estimate of lifelong genetically lower risk factor (or of variants in the solving drug's target gene) on the outcome: population lifelong_genetic, source_kind mendelian_randomisation, measure odds_ratio (or hazard_ratio when the study reports one), per_unit the change it is scaled to, trial_weeks null; regimen names the genetic exposure, drugs is empty, and pathways is the target gene's pathway or empty for variants across the genome. Give the largest or most cited, at most three.""",
}


def responses_system(pathway_names: list[str]) -> str:
    return f"""You collect published effect estimates of drugs and drug regimens in one disease, for a study of which diseases one drug can solve. The user message names the disease, its registered endpoint and window, and the question to answer.

One drug is one molecule acting through at most 3 pathways: bispecifics, trispecifics and multi-receptor agonists (tirzepatide) count as one drug; co-formulations of separate drugs and regimens of several drugs do not (one_drug false). A pooled class of such molecules is one_drug true. A pathway is a ligand or hormone with its receptors, an intracellular cascade, a cell population a depleting drug removes, or otherwise the target's family.

Background care that every arm receives and that is not a drug of a specific pathway does not count as a drug: methotrexate and other conventional DMARDs, corticosteroids, aminosalicylates, thiopurines, topical therapy, stable conventional therapy, lifestyle advice, and metformin in type 2 diabetes. A drug tested on top of such background against placebo on the same background is tested alone (population naive). Any other background drug (a statin, a renin-angiotensin blocker, an SGLT2 inhibitor, a TNF blocker) is a background pathway.

Sources, in order of preference: the most recent network meta-analysis that covers the drug and reports the endpoint on the estimate's own scale (for a share, the absolute share per arm or the risk difference against placebo; for an event, the hazard ratio); else pooled placebo-controlled Phase 3 trials (a pooled analysis, or the programme's Phase 3 trials pooled by patient numbers); else the largest placebo-controlled Phase 3 trial (trial). Leave out trials that enrolled only biomarker-selected patients. Systemic drugs only for a disease that also has topical treatments: leave out creams, ointments and other topical forms. Use the registered endpoint in the registered window; when no source reports it, use the closest responder threshold or time point and name it exactly in endpoint.

Every estimate:
- regimen: the drug, class or regimen as the source names it; drugs: the generic names of its active drugs in lower case (every member for a class); pathways: its pathways, written exactly as in the canonical list below (choose the closest canonical name; never invent one).
- measure share: placebo-adjusted percentage points of patients reaching the endpoint, active share minus placebo share (e.g. 66.3 for 70.9% vs 4.6%), both shares as the source reports them. Never convert a risk ratio or odds ratio into a share: a ratio against a small placebo share is unstable and an assumed placebo rate is not data. When a network meta-analysis reports only ratios, use pooled Phase 3 shares (or the largest Phase 3 trial) instead. ci_low and ci_high only when the source reports the interval of the difference in percentage points, null otherwise.
- measure hazard_ratio: against placebo (or against the background with placebo), with its 95% CI.
- trial_weeks: the week the share was assessed, or the outcome trial's median follow-up in weeks.
- source_kind, source_name (first author, year, trial or review name), pmid of that source as shown on a page you retrieved (null if not found).
- quote: text copied from a retrieved source that states the numbers used; derivation: the arithmetic from those numbers to estimate (or "as reported").
- sources: URLs from your own web_search results or web_fetch calls that show the numbers, copied character for character as the tool returned them; a PubMed link counts only if a search returned it or you fetched it.

Judge only from pages you retrieved; never fill a number, PMID or URL from memory. Leave out an estimate you could not find on a retrieved page. Fields that do not apply to the question are null (failed_pathway, stack_position, pair_key, per_unit) or empty (background_pathways). Return at most 30 estimates.

Canonical pathway names: {"; ".join(pathway_names)}"""


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"estimates": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "regimen": {"type": "string"},
            "drugs": {"type": "array", "items": {"type": "string"}},
            "pathways": {"type": "array", "items": {"type": "string"}},
            "one_drug": {"type": "boolean"},
            "endpoint": {"type": "string"},
            "measure": {"type": "string", "enum": list(MEASURES)},
            "population": {"type": "string", "enum": list(POPULATIONS)},
            "failed_pathway": {"type": ["string", "null"]},
            "background_pathways": {"type": "array", "items": {"type": "string"}},
            "stack_position": {"type": ["integer", "null"]},
            "pair_key": {"type": ["string", "null"]},
            "estimate": {"type": "number"},
            "ci_low": {"type": ["number", "null"]},
            "ci_high": {"type": ["number", "null"]},
            "trial_weeks": {"type": ["number", "null"]},
            "per_unit": {"type": ["string", "null"]},
            "source_kind": {"type": "string", "enum": list(SOURCE_KINDS)},
            "source_name": {"type": "string"},
            "pmid": {"type": ["string", "null"]},
            "sources": {"type": "array", "items": {"type": "string"}},
            "quote": {"type": "string"},
            "derivation": {"type": "string"},
        },
        "required": ["regimen", "drugs", "pathways", "one_drug", "endpoint", "measure", "population",
                     "failed_pathway", "background_pathways", "stack_position", "pair_key", "estimate", "ci_low",
                     "ci_high", "trial_weeks", "per_unit", "source_kind", "source_name", "pmid", "sources",
                     "quote", "derivation"],
        "additionalProperties": False}}},
    "required": ["estimates"],
    "additionalProperties": False,
}

# What each question may return: (measures, populations)
QUESTION_ROWS = {
    "response": ({"share"}, {"naive", "on_background"}),
    "crossover": ({"share"}, {"naive", "prior_failure"}),
    "events": ({"hazard_ratio"}, {"naive", "on_background"}),
    "pair": ({"hazard_ratio", "odds_ratio"}, {"naive", "on_background", "lifelong_genetic"}),
}


def canonical_pathway(name: str, names: dict[str, str]) -> str | None:
    """The canonical spelling of a pathway name (names: lower case -> canonical), None when it is not canonical."""
    return names.get(name.strip().lower())


def check_estimates(question: str, out: dict, names: dict[str, str]) -> None:
    """Raise when a decision's estimates break the question's rules: sources not retrieved, a pathway not canonical,
    a measure or population the question does not take, a crossover comparison that is not one prior-failure and one
    naive row on one endpoint, or a stack whose positions are not 1..n."""
    retrieved = out.get("retrieved_urls", [])
    if not retrieved:
        raise ValueError("no search returned anything, so no answer either way")
    measures, populations = QUESTION_ROWS[question]
    for e in out["estimates"]:
        name = e["regimen"]
        if not e["sources"] or any(retrieved_source(s, retrieved) is None for s in e["sources"]):
            raise ValueError(f"{name}: no sources, or cites sources it did not retrieve")
        if e["pmid"] is not None and not re.fullmatch(r"\d{6,9}", e["pmid"]):
            raise ValueError(f"{name}: pmid {e['pmid']!r}")
        if (not e["drugs"] or not e["pathways"]) and e["population"] != "lifelong_genetic":
            raise ValueError(f"{name}: no drugs or no pathways")
        unknown = [p for p in e["pathways"] + e["background_pathways"] if canonical_pathway(p, names) is None]
        if unknown:
            raise ValueError(f"{name}: pathways not in the canonical list: {unknown}")
        if e["one_drug"] and len(e["pathways"]) > MAX_PATHWAYS_ONE_DRUG:
            raise ValueError(f"{name}: one drug on {len(e['pathways'])} pathways")
        if e["measure"] not in measures or e["population"] not in populations:
            raise ValueError(f"{name}: {e['measure']} / {e['population']} in question {question}")
        if (e["population"] == "prior_failure") != bool(e["failed_pathway"]):
            raise ValueError(f"{name}: population {e['population']} with failed_pathway {e['failed_pathway']!r}")
        if (e["population"] == "lifelong_genetic") != (e["source_kind"] == "mendelian_randomisation"):
            raise ValueError(f"{name}: population {e['population']} from a {e['source_kind']}")
        if e["measure"] == "share" and not -100 <= e["estimate"] <= 100:
            raise ValueError(f"{name}: share {e['estimate']}")
        if e["measure"] != "share" and e["estimate"] <= 0:
            raise ValueError(f"{name}: ratio {e['estimate']}")
        if None not in (e["ci_low"], e["ci_high"]) and e["ci_low"] > e["ci_high"]:
            raise ValueError(f"{name}: confidence interval reversed")
        if e["trial_weeks"] is not None and e["trial_weeks"] <= 0:
            raise ValueError(f"{name}: trial_weeks {e['trial_weeks']}")
        if question == "crossover" and not e["pair_key"]:  # other questions' pair_key is ignored (response_rows)
            raise ValueError(f"{name}: crossover estimate without a pair_key")
        if e["stack_position"] is not None and question != "events":
            raise ValueError(f"{name}: stack_position in question {question}")
    if question == "crossover":
        pairs: dict[str, list[dict]] = {}
        for e in out["estimates"]:
            pairs.setdefault(e["pair_key"], []).append(e)
        for key, rows in pairs.items():
            if sorted(r["population"] for r in rows) != ["naive", "prior_failure"]:
                raise ValueError(f"comparison {key}: {[r['population'] for r in rows]}")
            if len({squash(r["endpoint"]).lower() for r in rows}) != 1:
                raise ValueError(f"comparison {key}: two endpoints")
    positions = sorted(e["stack_position"] for e in out["estimates"] if e["stack_position"] is not None)
    if positions != list(range(1, len(positions) + 1)):
        raise ValueError(f"stack positions {positions}")


def render_responses(p: dict) -> str:
    if p["question"] == "pair":
        listed = "\n".join(f"- {s}" for s in p["risk_estimates"]) or "(none stored)"
        return (f"Risk factor: {p['risk_factor']} ({p['risk_mondo_id']}); its endpoint: {p['risk_endpoint']}\n"
                f"Outcome disease: {p['disease']} ({p['mondo_id']}); event endpoint: {p['endpoint']}\n\n"
                f"Risk factor response estimates (one drug, placebo-adjusted share):\n{listed}\n\n"
                f"{QUESTION_TEXT['pair']}")
    labelled = "\n".join(f"- {d}" for d in p["labelled"]) or "(none listed)"
    text = (f"Disease: {p['disease']} ({p['mondo_id']})\nRegistered endpoint: {p['endpoint']}\n"
            f"Window: {p['weeks']}{' weeks' if p['question'] != 'events' else ''}\n\n"
            f"Drugs with a current FDA label for the disease (their pathways), a starting list, not a limit:\n"
            f"{labelled}\n\n{QUESTION_TEXT[p['question']]}")
    if p["question"] == "events":
        trials = "\n".join(f"- {t}" for t in p["add_on_trials"]) or "(none)"
        text += f"\n\nRandomised add-on and combination trials found for the disease:\n{trials}"
    return text


RESPONSE_TOOLS = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 30},
                  {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 15}]
RESPONSE_METHOD = "mechanism_response@v2+response_subgroup@v1"


def responses_task(pathway_names: list[str]) -> llm.Task:
    names = {n.lower(): n for n in pathway_names}
    return llm.Task(name="mechanism_response", prompt_version="v2", schema_version="v1",
                    system=responses_system(pathway_names), schema=RESPONSE_SCHEMA, render=render_responses,
                    subject_type="disease_question",
                    validate=lambda p, out: check_estimates(p["question"], out, names),
                    model="claude-opus-5-5", effort="medium", max_tokens=48000, tools=RESPONSE_TOOLS)


def drug_mechanisms(cur) -> dict[str, set[str]]:
    """Lower-case entity name or alias -> its mechanism keys (atlas membership, and the labelled entity's mechanism)."""
    cur.execute("SELECT DISTINCT entity_id, mechanism_key FROM preclin.atlas_member WHERE mechanism_key IS NOT NULL")
    by_entity: dict[int, set[str]] = {}
    for entity, key in cur.fetchall():
        by_entity.setdefault(entity, set()).add(key)
    for mid, (key, _, _) in mechanism_keys(cur).items():
        by_entity.setdefault(mid, set()).add(key)
    cur.execute("SELECT moiety_id, name, aliases FROM preclin.moiety WHERE moiety_id = ANY(%s)", (list(by_entity),))
    out: dict[str, set[str]] = {}
    for mid, name, aliases in cur.fetchall():
        for n in [name, *(aliases or [])]:
            out.setdefault(n.strip().lower(), set()).update(by_entity[mid])
    return out


def labelled_drugs(cur) -> dict[str, list[str]]:
    """Disease -> 'drug (pathways)' for every entity with a current FDA label indicated for it."""
    keys = mechanism_keys(cur)
    cur.execute("SELECT mechanism_key, pathways FROM preclin.mechanism_pathway")
    pathways = dict(cur.fetchall())
    cur.execute("""SELECT DISTINCT li.mondo_id, m.moiety_id, m.name FROM preclin.label_indication li
                   JOIN preclin.fda_label l USING (set_id) JOIN preclin.moiety m ON m.unii = ANY(l.unii)
                   ORDER BY 1, 3""")
    out: dict[str, list[str]] = {}
    for mondo, mid, name in cur.fetchall():
        ps = pathways.get(keys.get(mid, ("",))[0]) or []
        out.setdefault(mondo, []).append(f"{name} ({', '.join(ps) or 'pathway not resolved'})")
    return out


def add_on_trials(cur) -> dict[str, list[str]]:
    """Disease -> one line per preclin.combination_trial row, for the events question."""
    cur.execute("""SELECT mondo_id, trial_name, two_pathway_arm, one_pathway_arm, added_pathway, comparator_pathways,
                          primary_endpoint, effect_measure, effect, ci_low, ci_high, result
                   FROM preclin.combination_trial ORDER BY 1, 2""")
    out: dict[str, list[str]] = {}
    for mondo, name, two, one, added, base, endpoint, measure, effect, lo, hi, result in cur.fetchall():
        ci = f" ({lo}-{hi})" if lo is not None and hi is not None else ""
        out.setdefault(mondo, []).append(
            f"{name}: {two} vs {one}; adds {added} to {', '.join(base)}; primary {endpoint}; "
            f"{measure} {effect if effect is not None else 'not given'}{ci}; {result}")
    return out


def risk_estimates(rows: list[dict]) -> list[str]:
    """One line per one-drug naive response estimate of a risk factor, largest first."""
    best = sorted((e for e in rows if e["one_drug"] and e["population"] == "naive"), key=lambda e: -e["estimate"])
    return [f"{e['regimen']} ({', '.join(e['pathways'])}): {e['estimate']:g} points, {e['endpoint']} "
            f"[{e['source_name']}]" for e in best]


def response_rows(question: str, mondo: str, risk_mondo: str | None, decision_id: int, out: dict,
                  names: dict[str, str], mechanisms: dict[str, set[str]],
                  subgroup: dict[tuple[int, int], tuple[bool, int]]) -> list[tuple]:
    """Table rows of one decision: pathway names in their canonical spelling, drugs resolved to mechanism keys, and
    whether each estimate comes from a subgroup."""
    def canon(ps: list[str]) -> list[str]:
        return sorted({names[p.strip().lower()] for p in ps})

    return [(mondo, question, risk_mondo, e["regimen"], [d.strip().lower() for d in e["drugs"]],
             canon(e["pathways"]), sorted({k for d in e["drugs"] for k in mechanisms.get(d.strip().lower(), ())}),
             e["one_drug"], e["endpoint"], e["measure"], e["population"], e["failed_pathway"],
             canon(e["background_pathways"]), e["stack_position"], e["pair_key"] if question == "crossover" else None,
             e["estimate"], e["ci_low"],
             e["ci_high"], e["trial_weeks"], e["per_unit"], e["source_kind"], e["source_name"], e["pmid"],
             sorted({retrieved_source(u, out["retrieved_urls"]) for u in e["sources"]}), e["quote"],
             e["derivation"], decision_id, *subgroup[(decision_id, i)])
            for i, e in enumerate(out["estimates"])]


SUBGROUP_SYSTEM = """You read one published effect estimate recorded for a study of drug response and say whether it comes from a subgroup.

The study takes estimates from a network meta-analysis, pooled trials or a whole trial. An estimate is a subgroup estimate when it is restricted to a subset of the source's randomised or analysed population defined by a patient characteristic: a baseline-therapy subgroup (patients already on an SGLT2 inhibitor), a disease-type or severity subgroup, a region, age or biomarker subgroup, or any post hoc stratum.

One restriction does not count: prior advanced therapy, when the estimate's population is the one the study asks for. An estimate in advanced-therapy-naive (biologic-naive, TNF-naive) patients with population naive, or in patients who failed a named pathway with population prior_failure, is not a subgroup estimate, whether the source reports it as a stratum of a trial or as its own trial. A trial whose whole population is restricted by design (a trial enrolling only patients with HFpEF and obesity, or only ACE-inhibitor-intolerant patients) is a whole trial, not a subgroup. A secondary endpoint or a post hoc endpoint analysed in the whole trial is not a subgroup either."""

SUBGROUP_SCHEMA = {"type": "object", "properties": {"subgroup": {"type": "boolean"}, "reason": {"type": "string"}},
                   "required": ["subgroup", "reason"], "additionalProperties": False}


def render_subgroup(p: dict) -> str:
    return (f"Disease: {p['disease']}\nEstimate population: {p['population']}"
            f"{' (failed ' + p['failed_pathway'] + ')' if p['failed_pathway'] else ''}\nRegimen: {p['regimen']}\n"
            f"Endpoint: {p['endpoint']}\nSource: {p['source_name']} ({p['source_kind']})\nQuote: {p['quote']}\n"
            f"Derivation: {p['derivation']}")


SUBGROUP_TASK = llm.Task(name="response_subgroup", prompt_version="v1", schema_version="v1", system=SUBGROUP_SYSTEM,
                         schema=SUBGROUP_SCHEMA, render=render_subgroup, subject_type="mechanism_response_estimate",
                         model="claude-opus-5-5", effort="low", max_tokens=1500)


def subgroups(decisions: dict[str, tuple[int, dict]], disease: dict[str, str]) -> dict[tuple[int, int], tuple[bool, int]]:
    """(decision id, estimate index) -> (subgroup, decision id of the subgroup call) for every estimate."""
    items = {f"{decision_id}|{i}": {"disease": disease[key], **{k: e[k] for k in (
                 "population", "failed_pathway", "regimen", "endpoint", "source_name", "source_kind", "quote",
                 "derivation")}}
             for key, (decision_id, out) in decisions.items() for i, e in enumerate(out["estimates"])}
    run_id = llm.run(SUBGROUP_TASK, items)
    read = {tuple(map(int, k.split("|"))): (o["subgroup"], i) for k, i, o in llm.decisions(run_id)}
    if missing := len(items) - len(read):
        raise SystemExit(f"run {run_id}: {missing} subgroup decisions failed validation; run again")
    return read


def responses(_args) -> None:
    """Collect the published estimates behind the labels for every confirmed disease and risk factor -> outcome pair;
    store the table."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT p FROM preclin.mechanism_pathway, unnest(pathways) p ORDER BY 1")
        pathway_names = [r[0] for r in cur.fetchall()]
        labelled = labelled_drugs(cur)
        trials = add_on_trials(cur)
        mechanisms = drug_mechanisms(cur)
    names = {n.lower(): n for n in pathway_names}
    task = responses_task(pathway_names)

    def item(question: str, mondo: str, e: Endpoint) -> dict:
        return {"question": question, "mondo_id": mondo, "disease": e.disease, "endpoint": e.endpoint,
                "weeks": e.weeks, "labelled": labelled.get(mondo, []),
                **({"add_on_trials": trials.get(mondo, [])} if question == "events" else {})}

    items = {f"{mondo}|{q}": item(q, mondo, e) for mondo, e in CONFIRMED.items() for q in ("response", "crossover")}
    items |= {f"{mondo}|events": item("events", mondo, e) for mondo, e in EVENTS_CONFIRMED.items()}
    run_id = llm.run(task, items)
    decided = {key: (decision_id, out) for key, decision_id, out in llm.decisions(run_id)}
    if missing := set(items) - set(decided):  # the table is replaced whole
        raise SystemExit(f"no valid decision for {sorted(missing)}; run again (decided ones are reused)")

    pair_items = {f"{risk}>{outcome}|pair": {
        "question": "pair", "mondo_id": outcome, "disease": EVENTS_CONFIRMED[outcome].disease,
        "endpoint": EVENTS_CONFIRMED[outcome].endpoint, "risk_mondo_id": risk, "risk_factor": CONFIRMED[risk].disease,
        "risk_endpoint": CONFIRMED[risk].endpoint,
        "risk_estimates": risk_estimates(decided[f"{risk}|response"][1]["estimates"])} for risk, outcome in PAIRS}
    pair_run = llm.run(task, pair_items)
    paired = {key: (decision_id, out) for key, decision_id, out in llm.decisions(pair_run)}
    if missing := set(pair_items) - set(paired):
        raise SystemExit(f"no valid decision for {sorted(missing)}; run again (decided ones are reused)")

    every = {**items, **pair_items}
    flagged = subgroups({**decided, **paired}, {key: p["disease"] for key, p in every.items()})
    rows = [r for key, (decision_id, out) in {**decided, **paired}.items()
            for r in response_rows(every[key]["question"], every[key]["mondo_id"], every[key].get("risk_mondo_id"),
                                   decision_id, out, names, mechanisms, flagged)]
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, RESPONSE_METHOD, "Published estimates behind the single-drug labels", task.system,
                          ["web search", "preclin.mechanism_pathway", "preclin.label_indication",
                           "preclin.combination_trial", "preclin.atlas_member", "preclin.moiety"],
                          {"task": task.name, "prompt_version": task.prompt_version, "model": task.model,
                           "effort": task.effort, "questions": QUESTION_TEXT, "run": str(run_id),
                           "pair_run": str(pair_run), "subgroup_task": SUBGROUP_TASK.name,
                           "subgroup_prompt": SUBGROUP_SYSTEM})
        cur.execute("DELETE FROM preclin.mechanism_response")
        execute_values(cur, """INSERT INTO preclin.mechanism_response (mondo_id, question, risk_factor_mondo_id,
                                 regimen, drugs, pathways, mechanism_keys, one_drug, endpoint, measure, population,
                                 failed_pathway, background_pathways, stack_position, pair_key, estimate, ci_low,
                                 ci_high, trial_weeks, per_unit, source_kind, source_name, pmid, sources, quote,
                                 derivation, llm_decision_id, subgroup, subgroup_decision_id) VALUES %s""", rows)
        conn.commit()
    print(f"run={run_id} pair_run={pair_run} rows={len(rows)} by question={dict(Counter(r[1] for r in rows))} "
          f"with mechanism keys={sum(bool(r[6]) for r in rows)} subgroup={sum(r[-2] for r in rows)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(required=True)
    for name, fn in (("indications", indications), ("pathways", pathways), ("regimens", regimens),
                     ("regimen-summary", regimen_summary), ("combos", combos), ("responses", responses)):
        sub.add_parser(name).set_defaults(fn=fn)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
