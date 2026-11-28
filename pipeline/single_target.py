"""Which diseases the target-based drugging paradigm solves (#197): definitions registered in #198, the pathway of
every atlas mechanism, and randomised trials of two pathways against one (#196).

    python -m pipeline.single_target pathways   # LLM: pathways each atlas mechanism acts through -> preclin.mechanism_pathway
    python -m pipeline.single_target combos     # LLM + web: randomised trials of two pathways vs one -> preclin.combination_trial

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
    sub.add_parser("pathways").set_defaults(fn=pathways)
    sub.add_parser("combos").set_defaults(fn=combos)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
