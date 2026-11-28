"""The limits of single-target drugs (#197): definitions registered in #198, and the pathway of every atlas mechanism.

    python -m pipeline.single_target pathways   # LLM: pathways each atlas mechanism acts through -> preclin.mechanism_pathway

When one mechanism doesn't fully treat a disease, either different patients need different targets, one pathway is not
blocked fully enough, or each patient needs several targets hit. Telling these apart needs pathways rather than
targets (IL-17A and IL-17A/F antibodies act through one pathway; an IL-17A/TNF bispecific through two), one
definition of a combination, a fixed set of diseases with a shared endpoint, and fixed rules for labelling each
disease. All of them are here, fixed before any response or regimen data is pulled.
"""
from __future__ import annotations

import argparse
import statistics
from collections import Counter
from dataclasses import dataclass

from psycopg2.extras import execute_values

from pipeline import llm

# Disease areas reported apart from the rest: their combinations exist mainly to overcome resistance (tumour or
# pathogen evolution), not because the disease biology needs two targets (preclin.atlas_indication.area).
AREAS_APART = ("oncology", "infectious_disease")

# What counts as a combination when a later success on a target is read (#194) and when trials are collected (#196).
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
    endpoint: str  # a responder endpoint: the share of patients reaching it
    weeks: str     # the assessment window the estimate is read at


# Diseases where several approved mechanisms are measured on the same responder endpoint (#195). A disease stays on
# the list only if #193 counts at least MIN_APPROVED_PATHWAYS distinct pathways with an FDA approval for it, any
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
}
MIN_APPROVED_PATHWAYS = 3

# A pathway gets most patients to goal when its share reaching the endpoint is at least SOLVED_RESPONSE and its
# placebo-adjusted difference at least SOLVED_DELTA, in patients naive to advanced therapy.
SOLVED_RESPONSE = 0.50
SOLVED_DELTA = 0.40
# Retained effect: pathway B's placebo-adjusted effect in patients who failed pathway A, over its placebo-adjusted
# effect in naive patients. Its median over the disease's (A, B) pairs decides between the two partial labels.
RETAINED_DIFFERENT = 0.75
RETAINED_SEVERAL = 0.50

LABELS = ("single_target_enough", "different_patients", "several_targets_needed", "cant_tell")


@dataclass(frozen=True)
class Response:
    pathways: frozenset[str]  # one pathway, or two or more for a combination or a drug spanning them
    response: float           # share reaching the endpoint, 0-1
    delta: float              # placebo-adjusted difference, 0-1


def disease_label(naive: list[Response], retained: list[float], combination_beats_single: bool) -> str:
    """The registered label of one shortlisted disease.

    naive: the best estimate per mechanism in patients naive to advanced therapy, biomarker-selected trials left out.
    retained: retained effect of each (failed pathway, next pathway) pair with an estimate.
    combination_beats_single: a randomised trial in the disease of two pathways against one of them alone met its
    efficacy primary endpoint, and the two-pathway arm was not stopped or abandoned for safety.

    Single target enough needs a single-pathway mechanism to reach goal; a disease that only a two-pathway drug gets
    to goal is read by the crossover rules like any other. A combination beating one drug is not enough alone for
    several targets needed, since different patients responding to different drugs also produces it."""
    if len({r.pathways for r in naive}) < 2:
        return "cant_tell"
    if any(len(r.pathways) == 1 and r.response >= SOLVED_RESPONSE and r.delta >= SOLVED_DELTA for r in naive):
        return "single_target_enough"
    if not retained:
        return "cant_tell"
    kept = statistics.median(retained)
    if kept >= RETAINED_DIFFERENT:
        return "different_patients"
    if kept < RETAINED_SEVERAL and combination_beats_single:
        return "several_targets_needed"
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

MERGE_SYSTEM = """You are given pathway names that were assigned to drug mechanisms one mechanism at a time, with how many mechanisms carry each. The same pathway was sometimes written in different ways ("IL-17", "IL17", "interleukin-17 pathway"; "JAK-STAT", "JAK/STAT signalling").

Map every name to one canonical name. Names that mean the same pathway get the same canonical name: use the shortest conventional form among them ("IL-17", "JAK-STAT", "GLP-1", "B cells"). Never merge different pathways, even closely related ones: IL-23 and IL-17 stay apart, GLP-1 and GIP stay apart, IL-4 and IL-13 stay apart, PD-1/PD-L1 and CTLA-4 stay apart. Return every input name exactly once."""

MERGE_SCHEMA = {
    "type": "object",
    "properties": {"names": {"type": "array", "items": {
        "type": "object",
        "properties": {"name": {"type": "string"}, "canonical": {"type": "string"}},
        "required": ["name", "canonical"], "additionalProperties": False}}},
    "required": ["names"],
    "additionalProperties": False,
}


def validate_merge(payload: dict, out: dict) -> None:
    given = {n for n, _ in payload["names"]}
    got = [m["name"] for m in out["names"]]
    if set(got) != given or len(got) != len(given):
        raise ValueError(f"mapped {len(set(got) & given)} of {len(given)} names")


def render_merge(p: dict) -> str:
    return "Pathway names (mechanisms carrying each):\n" + "\n".join(f"{n} ({c})" for n, c in p["names"])


MERGE_TASK = llm.Task(name="pathway_names", prompt_version="v1", schema_version="v1", system=MERGE_SYSTEM,
                      schema=MERGE_SCHEMA, render=render_merge, subject_type="pathway_name_set",
                      validate=validate_merge, model="claude-opus-5-5", effort="medium", max_tokens=64000)
PATHWAY_METHOD = "mechanism_pathway@v1"


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

    rows = [(key, out["kind"], sorted({canonical[p] for p in out["pathways"]}), decision_id,
             merge_id if out["kind"] == "specific" else None)
            for key, (decision_id, out) in named.items()]
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, PATHWAY_METHOD, "Pathways of atlas mechanisms", PATHWAY_SYSTEM + "\n\n" + MERGE_SYSTEM,
                          ["preclin.atlas_mechanism", "preclin.atlas_member", "preclin.moiety"],
                          {"tasks": [PATHWAY_TASK.name, MERGE_TASK.name], "prompt_version": PATHWAY_TASK.prompt_version,
                           "model": PATHWAY_TASK.model, "merge_run": str(merge_run)})
        cur.execute("DELETE FROM preclin.mechanism_pathway")
        execute_values(cur, """INSERT INTO preclin.mechanism_pathway (mechanism_key, kind, pathways, llm_decision_id,
                                 merge_decision_id) VALUES %s""", rows, page_size=2000)
        conn.commit()
    print(f"mechanisms={len(rows)} kinds={dict(Counter(r[1] for r in rows))} "
          f"names={len(counts)} canonical={len(set(canonical.values()))}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(required=True)
    sub.add_parser("pathways").set_defaults(fn=pathways)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
