"""Which diseases the target-based drugging paradigm solves (#197): definitions registered in #198, and the pathway of
every atlas mechanism.

    python -m pipeline.single_target pathways   # LLM: pathways each atlas mechanism acts through -> preclin.mechanism_pathway

Each shortlisted disease gets two labels. How solved: by one drug (one molecule, up to three pathways), by stacking
drugs, or unsolved. Why one drug is not enough, where it is not: different patients need different targets, each
patient needs several, or the data can't tell. Counting needs pathways rather than targets (IL-17A and IL-17A/F
antibodies act through one pathway; an IL-17A/TNF bispecific through two). All rules are fixed here before any
response or regimen data is pulled.
"""
from __future__ import annotations

import argparse
import math
import statistics
from collections import Counter
from dataclasses import dataclass

from psycopg2.extras import execute_values

from pipeline import llm

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


def pathways(_args) -> None:
    """Name the pathways of every atlas mechanism, merge spelling variants into canonical names, store the table."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT mechanism_key, target_label, action, label FROM preclin.atlas_mechanism")
        mechanisms = cur.fetchall()
        cur.execute("""SELECT a.mechanism_key, m.name, string_agg(DISTINCT i.label, ', ')
                       FROM preclin.atlas_member a JOIN preclin.moiety m ON m.moiety_id = a.entity_id
                       JOIN preclin.atlas_indication i ON i.mondo_id = a.mondo_id
                       WHERE a.mechanism_key IS NOT NULL GROUP BY 1, 2 ORDER BY 1, 2""")
        drugs: dict[str, list[str]] = {}
        for key, name, diseases in cur.fetchall():
            drugs.setdefault(key, []).append(f"{name} ({diseases})")
    items = {key: {"label": label, "target_label": target, "action": action, "drugs": drugs.get(key, [])[:5]}
             for key, target, action, label in mechanisms}
    named = {key: (decision_id, out) for key, decision_id, out in llm.decisions(llm.run(PATHWAY_TASK, items))}

    counts = Counter(p for _, out in named.values() for p in out["pathways"])
    merge_run = llm.run(MERGE_TASK, {"atlas": {"names": sorted(counts.items())}})
    [(_, merge_id, merged)] = llm.decisions(merge_run)
    canonical = {m["name"]: m["canonical"] for m in merged["names"]}

    rows = [(key, out["kind"], sorted({c for p in out["pathways"] for c in canonical[p]}), decision_id,
             merge_id if out["kind"] == "specific" else None)
            for key, (decision_id, out) in named.items()]
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, PATHWAY_METHOD, "Pathways of atlas mechanisms", PATHWAY_SYSTEM + "\n\n" + MERGE_SYSTEM,
                          ["preclin.atlas_mechanism", "preclin.atlas_member", "preclin.moiety"],
                          {"tasks": [PATHWAY_TASK.name, MERGE_TASK.name], "prompt_versions": [PATHWAY_TASK.prompt_version, MERGE_TASK.prompt_version],
                           "model": PATHWAY_TASK.model, "merge_run": str(merge_run)})
        cur.execute("DELETE FROM preclin.mechanism_pathway")
        execute_values(cur, """INSERT INTO preclin.mechanism_pathway (mechanism_key, kind, pathways, llm_decision_id,
                                 merge_decision_id) VALUES %s""", rows, page_size=2000)
        conn.commit()
    print(f"mechanisms={len(rows)} kinds={dict(Counter(r[1] for r in rows))} "
          f"names={len(counts)} canonical={len({c for cs in canonical.values() for c in cs})}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(required=True)
    sub.add_parser("pathways").set_defaults(fn=pathways)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
