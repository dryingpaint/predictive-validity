"""Molecular targets of every entity with an industry-sponsored development program.

    python -m pipeline.targets resolve   # LLM: human protein targets (HGNC) -> preclin.moiety_target

The LLM sees the entity's names, modality, the ChEMBL mechanism-of-action
records attached to any of its intervention names, and trial titles. Every
returned symbol must be an approved human protein symbol in public.targets.
Entities acting on pathogens, or without a defined molecular target, are
recorded as such and get no target rows; entities without an industry trial,
or whose decision failed, keep no target kind.
"""
from __future__ import annotations

import argparse
from collections import defaultdict

from psycopg2.extras import execute_values

from pipeline import llm

SYSTEM = """You give the molecular target(s) through which a drug acts, as human gene symbols (HGNC).

- targets: the human proteins the drug binds or modulates to produce its therapeutic effect. Mark primary=true for the target(s) that define its mechanism (e.g. PCSK9 for evolocumab; the two arms of a bispecific; each receptor of a multi-receptor agonist such as GLP1R and GIPR for tirzepatide). Add secondary targets only when well established and pharmacologically relevant (e.g. multi-kinase inhibitors), with primary=false.
- For protein-replacement therapies and gene therapies, the target is the replaced or delivered gene product (e.g. F8 for factor VIII; SMN1 for onasemnogene). For CAR-T and other engineered cells, the antigen (e.g. CD19). For antisense/siRNA, the transcript's gene (e.g. TTR). For antibody-drug conjugates, the antigen. For radioligands, the binding target.
- action: inhibitor, antagonist, agonist, partial_agonist, inverse_agonist, activator, positive_modulator, negative_modulator, blocker, opener, degrader, binder_neutralizer (antibody neutralizing a ligand or blocking a receptor), depleter (cell-depleting antibody or cell therapy), replacement, gene_expression_reduction, gene_expression_increase, other.
- target_kind: human_protein when targets are listed; pathogen when the drug acts on a microbe or virus (antibiotics, antivirals, antifungals, antiparasitics, most vaccines); no_single_target for agents without a defined molecular target (e.g. nutritional products, many chemotherapy combinations given as one name, cell therapies without engineered specificity, plasma); unknown when you cannot tell (e.g. an unfamiliar code name with uninformative trial context).
Use the ChEMBL mechanism records when present; correct them only if clearly wrong. Never guess a target for an unrecognised code name."""

SCHEMA = {
    "type": "object",
    "properties": {
        "target_kind": {"type": "string", "enum": ["human_protein", "pathogen", "no_single_target", "unknown"]},
        "targets": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "action": {"type": "string", "enum": [
                    "inhibitor", "antagonist", "agonist", "partial_agonist", "inverse_agonist", "activator",
                    "positive_modulator", "negative_modulator", "blocker", "opener", "degrader",
                    "binder_neutralizer", "depleter", "replacement", "gene_expression_reduction",
                    "gene_expression_increase", "other"]},
                "primary": {"type": "boolean"},
            },
            "required": ["symbol", "action", "primary"], "additionalProperties": False}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["target_kind", "targets", "confidence"],
    "additionalProperties": False,
}


def render(p: dict) -> str:
    mech = "\n".join(f"- {m}" for m in p["chembl"]) or "(none)"
    return (f"Drug: {p['name']}\nCode names: {', '.join(p['codes']) or 'none'}\nModality: {p['modality'] or 'unknown'}\n"
            f"Intervention strings: {'; '.join(p['strings'])}\nChEMBL mechanism records:\n{mech}\n"
            f"Trial titles: {' | '.join(p['titles'])}")


HUMAN_SYMBOLS: set[str] = set()


def validate(p: dict, out: dict) -> None:
    bad = [t["symbol"] for t in out["targets"] if t["symbol"] not in HUMAN_SYMBOLS]
    if bad:
        raise ValueError(f"not human protein symbols: {bad}")
    if out["target_kind"] == "human_protein" and not out["targets"]:
        raise ValueError("human_protein without targets")


TASK = llm.Task(name="moiety_targets", prompt_version="v1", schema_version="v1", system=SYSTEM, schema=SCHEMA,
                render=render, validate=validate, subject_type="moiety", model="claude-opus-5-5",
                effort="medium", max_tokens=2000)


def resolve(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT symbol, id FROM public.targets WHERE ip_type = 'Protein'")
        symbol_id = dict(cur.fetchall())
        HUMAN_SYMBOLS.update(symbol_id)
        cur.execute("""
            SELECT dm.moiety_id, t.symbol || ': ' || coalesce(dt.mechanism, dt.role)
            FROM preclin.drug_moiety dm JOIN preclin.drug_target dt USING (drug_id)
            JOIN public.targets t ON t.id = dt.target_id
            WHERE dt.source = 'chembl_bulk'""")
        chembl = defaultdict(set)
        for mid, rec in cur.fetchall():
            chembl[mid].add(rec)
        cur.execute("""
            SELECT m.moiety_id, m.name, m.code_names, m.modality,
                   (SELECT array_agg(DISTINCT d.display_name) FROM preclin.drug_moiety dm
                    JOIN preclin.drug d USING (drug_id) WHERE dm.moiety_id = m.moiety_id),
                   (SELECT array_agg(t.brief_title ORDER BY t.latest DESC NULLS LAST, t.brief_title) FROM (
                      SELECT c.brief_title, max(c.start_date) AS latest FROM preclin.ctgov_study_moiety sm
                      JOIN preclin.ctgov_study c USING (nct_id)
                      WHERE sm.moiety_id = m.moiety_id AND sm.role = 'investigational' GROUP BY c.brief_title
                      ORDER BY latest DESC NULLS LAST, c.brief_title LIMIT 3) t)
            FROM preclin.moiety m
            WHERE EXISTS (SELECT 1 FROM preclin.dev_program p WHERE p.moiety_id = m.moiety_id
                          AND p.n_industry_trials > 0)""")
        items = {str(mid): {"name": name, "codes": codes or [], "modality": modality,
                            "strings": sorted(strings or [])[:8], "chembl": sorted(chembl[mid])[:12],
                            "titles": titles or []}
                 for mid, name, codes, modality, strings, titles in cur.fetchall()}
    run_id = llm.run(TASK, items)
    rows, kinds = [], []
    for mid, did, out in llm.decisions(run_id):
        kinds.append((int(mid), out["target_kind"], did))
        if out["target_kind"] == "human_protein":
            rows += [(int(mid), symbol_id[t["symbol"]], t["action"], t["primary"], did) for t in out["targets"]]
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.moiety_target")
        cur.execute("""UPDATE preclin.moiety SET target_kind = NULL, target_decision_id = NULL
                       WHERE target_kind IS NOT NULL OR target_decision_id IS NOT NULL""")
        execute_values(cur, """INSERT INTO preclin.moiety_target (moiety_id, target_id, action, is_primary, llm_decision_id)
                               VALUES %s ON CONFLICT DO NOTHING""", rows, page_size=5000)
        execute_values(cur, """UPDATE preclin.moiety m SET target_kind = v.kind, target_decision_id = v.did
                               FROM (VALUES %s) AS v(mid, kind, did) WHERE m.moiety_id = v.mid""", kinds)
        conn.commit()
    print(f"entities={len(items)} target rows={len(rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("resolve").set_defaults(fn=resolve)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
