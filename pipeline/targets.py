"""Molecular targets of every entity with an industry-sponsored development program.

    python -m pipeline.targets resolve     # LLM: human protein targets (HGNC) -> preclin.moiety_target
    python -m pipeline.targets mechanism   # LLM: germline mechanism per (target, disease) -> preclin.gene_disease_mechanism
    python -m pipeline.targets mouse       # LLM: mouse model vs disease, per model -> preclin.mouse_model_relation

resolve: the LLM sees the entity's names, modality, the ChEMBL mechanism-of-action
records attached to any of its intervention names, and trial titles. Every
returned symbol must be an approved human protein symbol in public.targets.
Entities acting on pathogens, or without a defined molecular target, are
recorded as such and get no target rows; entities without an industry trial,
or whose decision failed, keep no target kind.

mechanism: for each primary target gene of an entity and each disease the entity
is developed for, where Open Targets has germline evidence (GWAS, gene burden,
ClinVar pathogenic, Orphanet, Gene2Phenotype, ClinGen, PanelApp, UniProt) for the
disease or a subtype, the LLM states, without being told any drug, whether
risk variants lower or raise the gene product's function, whether protective
variants are known, and when that was established. Open Targets' own direction
field follows variant consequence alone, so a few truncating ClinVar variants
make a gain-of-function disease gene such as PCSK9, MYH7 or TTR read as loss of
function.

mouse: for the same (target, disease) pairs, every mouse model Open Targets links
to the disease or a subtype (IMPC and MGI, matched by PhenoDigm) is shown with its
allele and the phenotypes that matched; the LLM, again without any drug, says
whether the model lowers or raises the gene's function and whether those
phenotypes resemble the disease or its opposite (a knockout with low LDL
cholesterol opposes hypercholesterolaemia). PhenoDigm scores phenotype
similarity without direction, so both kinds match.
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


MECHANISM_SYSTEM = """You state how germline variation in a human gene acts on a disease, from the human genetics literature. You are not told about any drug, and you answer from genetics alone.

- germline_link: established when inherited (germline) variants in this gene are shown to cause this disease or change its risk; somatic_only when the gene's link to the disease rests on somatic tumour mutations, fusions or mosaic variants (for example FLT3 or IDH1 in leukaemia), which do not count here; none otherwise. Evidence for a different disease does not count, however related (a coronary-disease variant says nothing about ulcerative colitis unless shown for ulcerative colitis).
- risk_mechanism: how the variants that cause the disease or raise its risk change the gene product's function. loss_of_function: null, hypomorphic, haploinsufficient or biallelic loss, or lower expression. gain_of_function: higher or constitutive activity, toxic gain (misfolding, aggregation), neomorphic activity, or higher expression. dominant_negative: a mutant product that interferes with the wild-type protein. mixed: variants acting in opposite directions on function both cause or raise risk of this disease. unknown: a genetic association is established but the direction of its effect on the gene's function is not (for example a GWAS locus without functional follow-up). none: no established germline link between this gene and this disease.
- protective: loss_of_function_protective when variants that lower the gene's function are established to protect against this disease (for example PCSK9 nonsense variants and coronary disease); gain_of_function_protective when variants that raise its function protect; none_known otherwise.
- established_year: the year of the first publication that showed the risk mechanism or the protective effect you report for this gene in this disease (the earlier of the two when both); a later paper that only confirmed it does not move the year, and a paper on another disease does not count. Null when risk_mechanism is unknown or none and no protective effect is known.
- confidence: high for replicated human genetic and functional evidence, medium for consistent but limited evidence, low otherwise.
- basis: one or two sentences naming the publication that sets established_year (first author and year) and its finding for this disease."""

MECHANISM_SCHEMA = {
    "type": "object",
    "properties": {
        "germline_link": {"type": "string", "enum": ["established", "somatic_only", "none"]},
        "risk_mechanism": {"type": "string", "enum": ["loss_of_function", "gain_of_function", "dominant_negative",
                                                       "mixed", "unknown", "none"]},
        "protective": {"type": "string", "enum": ["loss_of_function_protective", "gain_of_function_protective",
                                                   "none_known"]},
        "established_year": {"type": ["integer", "null"]},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "basis": {"type": "string"},
    },
    "required": ["germline_link", "risk_mechanism", "protective", "established_year", "confidence", "basis"],
    "additionalProperties": False,
}


def render_mechanism(p: dict) -> str:
    return (f"Gene: {p['symbol']} ({p['gene_name']})\nDisease: {p['disease']} ({p['mondo_id']})\n"
            f"Disease definition: {p['definition'] or 'none given'}")


def validate_mechanism(p: dict, out: dict) -> None:
    directed = out["risk_mechanism"] not in ("unknown", "none") or out["protective"] != "none_known"
    if directed and out["germline_link"] != "established":
        raise ValueError(f"a mechanism without an established germline link ({out['germline_link']})")
    year = out["established_year"]
    if directed and year is None:
        raise ValueError("a stated mechanism needs the year it was established")
    if year is not None and not 1900 <= year <= 2026:
        raise ValueError(f"established_year {year}")


MECHANISM_TASK = llm.Task(name="gene_disease_mechanism", prompt_version="v2", schema_version="v2",
                          system=MECHANISM_SYSTEM, schema=MECHANISM_SCHEMA, render=render_mechanism,
                          validate=validate_mechanism, subject_type="gene_disease", model="claude-opus-5-5",
                          effort="medium", max_tokens=4000)
GERMLINE_SOURCES = ["gwas_credible_sets", "gene_burden", "eva", "orphanet", "gene2phenotype", "clingen",
                    "genomics_england", "uniprot_variants", "uniprot_literature"]


def mechanism(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            WITH ev AS (
                SELECT DISTINCT e.target_ensembl, m.term
                FROM preclin.ot_evidence e JOIN preclin.ot_disease od USING (disease_id)
                CROSS JOIN LATERAL unnest(od.mondo_ids) AS m(term)
                WHERE e.datasource = ANY(%s)
                  AND (e.datasource <> 'eva'
                       OR e.detail->'clinicalSignificances' ?| array['pathogenic', 'likely pathogenic'])),
            covered AS (
                SELECT target_ensembl, term AS mondo_id FROM ev
                UNION
                SELECT ev.target_ensembl, a.ancestor_id FROM ev
                JOIN preclin.ontology_ancestor a ON a.ontology = 'MONDO' AND a.term_id = ev.term),
            pairs AS (
                SELECT DISTINCT t.ensembl_id, t.symbol, t.name, p.mondo_id
                FROM preclin.dev_program p JOIN preclin.moiety m USING (moiety_id)
                JOIN preclin.moiety_target mt USING (moiety_id) JOIN public.targets t ON t.id = mt.target_id
                WHERE mt.is_primary AND m.target_kind = 'human_protein' AND p.mondo_id IS NOT NULL)
            SELECT p.ensembl_id, p.symbol, p.name, p.mondo_id, o.label, o.definition
            FROM pairs p JOIN covered c ON c.target_ensembl = p.ensembl_id AND c.mondo_id = p.mondo_id
            JOIN preclin.ontology_term o ON o.ontology = 'MONDO' AND o.term_id = p.mondo_id
            ORDER BY p.ensembl_id, p.mondo_id""", (GERMLINE_SOURCES,))
        items = {f"{ens}|{mondo}": {"symbol": symbol, "gene_name": name or "", "mondo_id": mondo, "disease": label,
                                    "definition": (definition or "")[:500]}
                 for ens, symbol, name, mondo, label, definition in cur.fetchall()}
    run_id = llm.run(MECHANISM_TASK, items)
    rows = [(*key.split("|"), o["risk_mechanism"], o["protective"], o["established_year"], o["confidence"], did)
            for key, did, o in llm.decisions(run_id)]
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.gene_disease_mechanism")
        execute_values(cur, """INSERT INTO preclin.gene_disease_mechanism (ensembl_id, mondo_id, risk_mechanism,
                                 protective, established_year, confidence, llm_decision_id) VALUES %s""", rows)
        conn.commit()
    print(f"pairs={len(items)} classified={len(rows)}")


MOUSE_SYSTEM = """You compare mouse models with a human disease. You are told a gene, a disease and the mouse models of that gene (allele and the phenotypes that an automated matcher linked to the disease). You are not told about any drug.

For each model, by its number:
- perturbation: reduced_function for knockouts, knockdowns, hypomorphs, null or loss-of-function point mutants (including heterozygotes); increased_function for transgenic overexpression, constitutively active or gain-of-function mutants, and toxic mutant transgenes (for example mutant SOD1 or mutant APP overexpression); other when the effect on the gene's function cannot be told (humanised alleles, reporters, unknown chemically induced alleles).
- relation, judged against the disease's defining feature (bleeding for haemophilia, thrombosis for thrombophilia, seizures for epilepsy, leukaemic blasts for leukaemia, high LDL cholesterol for hypercholesterolaemia): mimics_disease when the phenotypes show that feature in the same direction (increased circulating cholesterol for hypercholesterolaemia, motor neuron degeneration for ALS); opposes_disease when they show its opposite or protection from it (decreased circulating cholesterol for hypercholesterolaemia, thrombosis for a bleeding disorder, resistance to diet-induced obesity for obesity); unrelated when they show neither, including lethality, growth defects and abnormalities of other systems."""

MOUSE_SCHEMA = {
    "type": "object",
    "properties": {"models": {"type": "array", "items": {
        "type": "object",
        "properties": {"index": {"type": "integer"},
                       "defining_feature": {"type": "string"},
                       "perturbation": {"type": "string", "enum": ["reduced_function", "increased_function", "other"]},
                       "relation": {"type": "string", "enum": ["mimics_disease", "opposes_disease", "unrelated"]}},
        "required": ["index", "defining_feature", "perturbation", "relation"], "additionalProperties": False}}},
    "required": ["models"],
    "additionalProperties": False,
}
MAX_MODELS = 12  # per (gene, disease), best PhenoDigm match first


def render_mouse(p: dict) -> str:
    models = "\n".join(f"{i}. allele {m['allele']} (background {m['background']}): {'; '.join(m['phenotypes'])}"
                       for i, m in enumerate(p["models"], 1))
    return (f"Gene: {p['symbol']} ({p['gene_name']})\nDisease: {p['disease']} ({p['mondo_id']})\n"
            f"Disease definition: {p['definition'] or 'none given'}\n\nMouse models:\n{models}")


def validate_mouse(p: dict, out: dict) -> None:
    if sorted(m["index"] for m in out["models"]) != list(range(1, len(p["models"]) + 1)):
        raise ValueError(f"models {[m['index'] for m in out['models']]} for {len(p['models'])} given")


MOUSE_TASK = llm.Task(name="mouse_model_relation", prompt_version="v2", schema_version="v2", system=MOUSE_SYSTEM,
                      schema=MOUSE_SCHEMA, render=render_mouse, validate=validate_mouse, subject_type="gene_disease",
                      model="claude-opus-5-5", effort="medium", max_tokens=6000)


def mouse(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            WITH ev AS (
                SELECT e.target_ensembl, m.term, e.detail->>'biologicalModelId' AS model_id,
                       e.detail->>'biologicalModelAllelicComposition' AS allele,
                       e.detail->>'biologicalModelGeneticBackground' AS background,
                       e.detail->'model_phenotypes' AS phenotypes, e.resource_score
                FROM preclin.ot_evidence e JOIN preclin.ot_disease od USING (disease_id)
                CROSS JOIN LATERAL unnest(od.mondo_ids) AS m(term)
                WHERE e.datasource = 'impc' AND e.detail ? 'biologicalModelId'),
            covered AS (
                SELECT ev.*, ev.term AS mondo_id FROM ev
                UNION ALL
                SELECT ev.*, a.ancestor_id FROM ev
                JOIN preclin.ontology_ancestor a ON a.ontology = 'MONDO' AND a.term_id = ev.term),
            pairs AS (
                SELECT DISTINCT t.ensembl_id, t.symbol, t.name, p.mondo_id
                FROM preclin.dev_program p JOIN preclin.moiety m USING (moiety_id)
                JOIN preclin.moiety_target mt USING (moiety_id) JOIN public.targets t ON t.id = mt.target_id
                WHERE mt.is_primary AND m.target_kind = 'human_protein' AND p.mondo_id IS NOT NULL),
            best AS (
                SELECT DISTINCT ON (c.target_ensembl, c.mondo_id, c.model_id) c.target_ensembl, c.mondo_id, c.model_id,
                       c.allele, c.background, c.phenotypes, c.resource_score
                FROM covered c JOIN pairs p ON p.ensembl_id = c.target_ensembl AND p.mondo_id = c.mondo_id
                ORDER BY c.target_ensembl, c.mondo_id, c.model_id, c.resource_score DESC NULLS LAST)
            SELECT b.target_ensembl, p.symbol, p.name, b.mondo_id, o.label, o.definition, b.model_id, b.allele,
                   b.background, b.phenotypes
            FROM best b JOIN pairs p ON p.ensembl_id = b.target_ensembl AND p.mondo_id = b.mondo_id
            JOIN preclin.ontology_term o ON o.ontology = 'MONDO' AND o.term_id = b.mondo_id
            ORDER BY b.target_ensembl, b.mondo_id, b.resource_score DESC NULLS LAST, b.model_id""")
        items: dict = {}
        for ens, symbol, name, mondo, label, definition, model_id, allele, background, phenotypes in cur.fetchall():
            item = items.setdefault(f"{ens}|{mondo}", {"symbol": symbol, "gene_name": name or "", "mondo_id": mondo,
                                                       "disease": label, "definition": (definition or "")[:500],
                                                       "models": []})
            if len(item["models"]) < MAX_MODELS:
                item["models"].append({"id": model_id, "allele": allele, "background": background or "unknown",
                                       "phenotypes": (phenotypes or [])[:8]})
    run_id = llm.run(MOUSE_TASK, items)
    rows = [(*key.split("|"), items[key]["models"][m["index"] - 1]["id"], m["perturbation"], m["relation"], did)
            for key, did, o in llm.decisions(run_id) for m in o["models"]]
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.mouse_model_relation")
        execute_values(cur, """INSERT INTO preclin.mouse_model_relation (ensembl_id, mondo_id, model_id, perturbation,
                                 relation, llm_decision_id) VALUES %s ON CONFLICT DO NOTHING""", rows, page_size=5000)
        conn.commit()
    print(f"pairs={len(items)} models={len(rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("resolve").set_defaults(fn=resolve)
    sub.add_parser("mechanism").set_defaults(fn=mechanism)
    sub.add_parser("mouse").set_defaults(fn=mouse)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
