"""Canonicalize every preclin.drug name to the molecular entities it contains.

    python -m pipeline.drugs canonicalize   # intervention names -> molecular entities
    python -m pipeline.drugs unii           # entity -> FDA UNII substance; merge entities that are the same
    python -m pipeline.drugs modality       # modality class of every entity with a development program

Trial intervention strings name the same molecule many ways ("Keytruda",
"pembrolizumab 200 mg", "Pembrolizumab Dose A", "MK-3475"), bundle placebo
with drug ("Tirzepatide-Placebo") and describe combinations. The LLM reads each
name with the trials it appears in and returns its active components under
their nonproprietary (INN/USAN) names, or sponsor code when no name exists.
Results go to preclin.moiety (one row per distinct active entity) and
preclin.drug_moiety (drug_id -> moiety_id, one row per active component).

An entity is then resolved to the FDA UNII substance it is (pipeline.unii
names: official, common, code and brand). Entities that resolve to the same
substance (a sponsor code and its later INN, say) are merged: the survivor
takes the substance's official name and keeps every other name as an alias, so
later runs map those names straight to it.
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict

from psycopg2.extras import execute_values

from pipeline import llm

SYSTEM = """You resolve clinical-trial intervention names to the molecular entities they contain.

For the intervention name given (with the trials it appears in for context), return:
- kind: drug (one active entity), combination (two or more active entities given together or co-formulated), placebo_or_vehicle (placebo, vehicle, sham, saline, standard-of-care-only label, diluent), vaccine, non_drug (device, procedure, radiation, behavioral, diet, diagnostic/imaging agent used only for diagnosis, supplement of no defined active entity), or unclear.
- components: every active entity, excluding placebo. For each give:
  name: the international nonproprietary name (INN) or USAN in lower case if one exists (e.g. "pembrolizumab", "semaglutide", "insulin glargine", "trastuzumab deruxtecan"); for an entity with no nonproprietary name, its sponsor code exactly as commonly written (e.g. "MK-1084"). Map brand names and sponsor codes to the nonproprietary name when you are confident they are the same entity (e.g. Keytruda and MK-3475 -> pembrolizumab). Strip doses, strengths, routes, formulations, salts and schedules (e.g. "metformin hydrochloride 500 mg XR" -> "metformin").
  code_names: sponsor codes for this entity mentioned in the input or that you are confident of.
  biosimilar_of: for a biosimilar or a proposed biosimilar, the reference product's nonproprietary name; otherwise null. Name a biosimilar by its core nonproprietary name without the four-letter suffix (e.g. "adalimumab").
  role: investigational if this entity is what the trial is developing in this arm; background if it is a partner/standard therapy given alongside.
- confidence: high, medium or low for the mapping as a whole.

Do not invent nonproprietary names: if you are not confident a code maps to an INN, keep the code."""

SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["drug", "combination", "placebo_or_vehicle", "vaccine",
                                             "non_drug", "unclear"]},
        "components": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "code_names": {"type": "array", "items": {"type": "string"}},
                "biosimilar_of": {"type": ["string", "null"]},
                "role": {"type": "string", "enum": ["investigational", "background"]},
            },
            "required": ["name", "code_names", "biosimilar_of", "role"],
            "additionalProperties": False}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["kind", "components", "confidence"],
    "additionalProperties": False,
}


def render(p: dict) -> str:
    trials = "\n".join(
        f"- {t['title']} (sponsor: {t['sponsor']}); interventions: "
        + "; ".join(f"{i.get('name')} [{i.get('type')}]: {(i.get('description') or '')[:160]}"
                    for i in t["interventions"][:8])
        for t in p["trials"])
    return (f"Intervention name: {p['name']}\nOther names recorded: {', '.join(p['synonyms']) or 'none'}\n"
            f"ChEMBL id recorded: {p['chembl_id'] or 'none'}\n\nTrials using it:\n{trials or '(none)'}")


TASK = llm.Task(name="drug_moiety", prompt_version="v1", schema_version="v1", system=SYSTEM,
                schema=SCHEMA, render=render, subject_type="drug", effort="medium", max_tokens=3000)


def moiety_key(name: str) -> str:
    """Identity key for a component name: case- and punctuation-insensitive."""
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def entity_keys(cur) -> dict[str, int]:
    """Every name key that identifies exactly one entity: its own key, a code
    name or an alias."""
    cur.execute("""SELECT k, min(moiety_id) FROM (
                     SELECT moiety_key AS k, moiety_id FROM preclin.moiety
                     UNION SELECT regexp_replace(lower(c), '[^a-z0-9]', '', 'g'), moiety_id
                     FROM preclin.moiety, unnest(code_names || aliases) c) x
                   WHERE k <> '' GROUP BY k HAVING count(DISTINCT moiety_id) = 1""")
    return dict(cur.fetchall())


def entity_ids(cur, names: dict[str, str]) -> dict[str, int]:
    """moiety_id for each name key: the entity it already identifies, else a
    new entity with that name."""
    known = entity_keys(cur)
    new = [(k, n) for k, n in names.items() if k not in known]
    if new:
        execute_values(cur, """INSERT INTO preclin.moiety (moiety_key, name) VALUES %s
                               ON CONFLICT (moiety_key) DO NOTHING""", new)
        cur.execute("SELECT moiety_key, moiety_id FROM preclin.moiety WHERE moiety_key = ANY(%s)",
                    ([k for k, _ in new],))
        known.update(cur.fetchall())
    return {k: known[k] for k in names}


def canonicalize(args) -> None:
    """Resolve intervention names. A name that is exactly an entity's
    nonproprietary name or sponsor code (ignoring case and punctuation) is
    linked directly; the rest go to the LLM. --scope industry limits the LLM
    to names from the legacy program tables or from industry-sponsored trials."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT drug_id, display_name, coalesce(synonyms, '{}'), chembl_id, normalized_name, "
                    "resolved_via FROM preclin.drug")
        drugs = cur.fetchall()
        exact_keys = entity_keys(cur)
        cur.execute("""SELECT DISTINCT sd.drug_id FROM preclin.ctgov_study_drug sd
                       JOIN preclin.ctgov_study s USING (nct_id) WHERE s.lead_sponsor_class = 'INDUSTRY'""")
        industry = {r[0] for r in cur.fetchall()}
        cur.execute("""SELECT DISTINCT d.subject_key::int FROM pv_evidence.llm_decision d
                       JOIN pv_evidence.llm_decision_run r USING (decision_run_id)
                       WHERE d.task = %s AND r.prompt_version = %s AND d.validation_status = 'validated'""",
                    (TASK.name, TASK.prompt_version))
        decided_before = {r[0] for r in cur.fetchall()}
    exact = {did: exact_keys[nk] for did, _, _, _, nk, _ in drugs
             if did not in decided_before and nk in exact_keys}
    in_scope = {did for did, *_, via in drugs
                if args.scope == "all" or via != "ctgov_snapshot" or did in industry}
    drugs = [d for d in drugs if d[0] in in_scope and d[0] not in exact]
    with llm.connect() as conn, conn.cursor() as cur:
        # Context: up to three trials per name, from the legacy program tables
        # when the name has programs there, otherwise from the CT.gov snapshot.
        cur.execute("""
            WITH t AS (
              SELECT p.drug_id, pt.nct_id,
                     row_number() OVER (PARTITION BY p.drug_id ORDER BY pt.nct_id) AS rn
              FROM preclin.program p JOIN preclin.program_trial pt USING (program_id)
              GROUP BY p.drug_id, pt.nct_id)
            SELECT t.drug_id, json_agg(json_build_object('title', tr.brief_title, 'sponsor', tr.sponsor_name,
                                                         'interventions', tr.interventions))
            FROM t JOIN public.trials tr ON tr.nct_id = t.nct_id
            WHERE t.rn <= 3 GROUP BY t.drug_id""")
        context = dict(cur.fetchall())
        cur.execute("""
            WITH s AS (
              SELECT drug_id, nct_id, row_number() OVER (PARTITION BY drug_id ORDER BY nct_id) AS rn
              FROM preclin.ctgov_study_drug)
            SELECT s.drug_id, json_agg(json_build_object('title', c.brief_title, 'sponsor', c.lead_sponsor,
                                                         'interventions', c.interventions))
            FROM s JOIN preclin.ctgov_study c USING (nct_id)
            WHERE s.rn <= 3 GROUP BY s.drug_id""")
        for drug_id, trials in cur.fetchall():
            context.setdefault(drug_id, trials)
        items = {str(did): {"name": name, "synonyms": list(syn)[:6], "chembl_id": chembl,
                            "trials": [{**t, "interventions": t["interventions"] or []}
                                       for t in context.get(did, [])]}
                 for did, name, syn, chembl, _, _ in drugs}
    run_id = llm.run(TASK, items, reuse_by="subject")

    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT subject_key, llm_decision_id, parsed_output FROM pv_evidence.llm_decision
                       WHERE decision_run_id = %s AND validation_status = 'validated'""", (str(run_id),))
        decided = cur.fetchall()
        moieties: dict[str, dict] = {}
        links = []
        kinds = []
        for drug_id, decision_id, out in decided:
            kinds.append((int(drug_id), out["kind"], decision_id))
            if out["kind"] not in ("drug", "combination", "vaccine"):
                continue
            for comp in out["components"]:
                key = moiety_key(comp["name"])
                if not key:
                    continue
                m = moieties.setdefault(key, {"name": comp["name"], "codes": set()})
                m["codes"].update(comp["code_names"])
                links.append((int(drug_id), key, comp["role"], comp["biosimilar_of"], decision_id))
        ids = entity_ids(cur, {k: m["name"] for k, m in moieties.items()})
        codes = {}
        for k, m in moieties.items():
            codes.setdefault(ids[k], set()).update(m["codes"])
        execute_values(cur, """UPDATE preclin.moiety m SET code_names = v.codes
            FROM (VALUES %s) AS v(moiety_id, codes) WHERE m.moiety_id = v.moiety_id""",
                       [(mid, sorted(c)) for mid, c in codes.items()], template="(%s, %s::text[])")
        cur.execute("DELETE FROM preclin.drug_moiety")
        execute_values(cur, """INSERT INTO preclin.drug_moiety
              (drug_id, moiety_id, role, biosimilar_of, llm_decision_id, method)
            VALUES %s ON CONFLICT (drug_id, moiety_id) DO NOTHING""",
                       [(did, ids[k], role, bio, dec, "llm") for did, k, role, bio, dec in links])
        if exact:
            execute_values(cur, """INSERT INTO preclin.drug_moiety (drug_id, moiety_id, role, method)
                VALUES %s ON CONFLICT (drug_id, moiety_id) DO NOTHING""",
                           [(did, mid, "investigational", "exact_name") for did, mid in exact.items()])
            execute_values(cur, """UPDATE preclin.drug d SET entity_kind = 'drug', moiety_decision_id = NULL
                FROM (VALUES %s) AS v(drug_id) WHERE d.drug_id = v.drug_id""", [(did,) for did in exact])
        execute_values(cur, """UPDATE preclin.drug d SET entity_kind = v.kind, moiety_decision_id = v.did
            FROM (VALUES %s) AS v(drug_id, kind, did) WHERE d.drug_id = v.drug_id""", kinds)
        conn.commit()
    print(f"llm items={len(items)} decided={len(decided)} exact-name links={len(exact)} "
          f"moieties={len(moieties)} links={len(links)}")


UNII_SYSTEM = """You decide which registered substance (FDA UNII) a drug entity from clinical trials is.

You get the entity's name, its code names and other names, the intervention strings that named it, some trials using it, and candidate substances from the FDA Global Substance Registration System: every substance with one of the entity's names among its registered names (exact match ignoring case and punctuation), shown with its display name, the names that matched and some other registered names.

Return the UNII of the candidate that is this same active entity, or null.
- A shared sponsor code or brand is not enough: the substance must fit the trials (sponsor, molecule type, mechanism, indication). Sponsors reuse code formats, and short codes collide.
- When candidates include a parent substance and its salts, hydrates, solvates, crystal forms or formulation esters, choose the parent active moiety (metformin, not metformin hydrochloride). Keep a conjugate, prodrug ester or radiolabelled form that is itself the entity's nonproprietary name (baloxavir marboxil, trastuzumab deruxtecan, lutetium Lu-177 dotatate).
- A biosimilar is the same substance as its reference product.
- null when no candidate is this entity, or when the entity is a combination or mixture that no single candidate represents."""

UNII_SCHEMA = {
    "type": "object",
    "properties": {"unii": {"type": ["string", "null"]},
                   "confidence": {"type": "string", "enum": ["high", "medium", "low"]}},
    "required": ["unii", "confidence"],
    "additionalProperties": False,
}
UNII_CANDIDATES = 15
UNII_NAMES = 12


def render_unii(p: dict) -> str:
    trials = "\n".join(f"- {t['title']} (sponsor: {t['sponsor']})" for t in p["trials"])
    cands = "\n".join(f"- UNII {c['unii']} | {c['display_name']} | {c['substance_type'] or '?'}"
                       f"{' | INN' if c['inn'] else ''} | matched: {'; '.join(c['matched'])} | "
                       f"other names: {'; '.join(c['names'])}" for c in p["candidates"])
    return (f"Entity: {p['name']}\nCode names: {', '.join(p['codes']) or 'none'}\n"
            f"Other names: {', '.join(p['aliases']) or 'none'}\n"
            f"Intervention strings naming it: {'; '.join(p['strings']) or 'none'}\n"
            f"Trials:\n{trials or '(none)'}\n\nCandidate substances:\n{cands}")


def validate_unii(p: dict, out: dict) -> None:
    if out["unii"] is not None and out["unii"] not in {c["unii"] for c in p["candidates"]}:
        raise ValueError(f"unii {out['unii']} is not a candidate")


UNII_TASK = llm.Task(name="moiety_unii", prompt_version="v1", schema_version="v1", system=UNII_SYSTEM,
                     schema=UNII_SCHEMA, render=render_unii, validate=validate_unii, subject_type="moiety",
                     model="claude-opus-5-5", effort="medium", max_tokens=1500)


def unii(_args) -> None:
    """Resolve every entity to its UNII substance, then merge entities that
    resolved to the same one into a single entity named by the substance's
    official name."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT m.moiety_id, m.name, m.code_names, m.aliases,
                   coalesce((SELECT array_agg(DISTINCT x) FROM preclin.drug_moiety dm JOIN preclin.drug d USING (drug_id),
                             unnest(array_append(coalesce(d.synonyms, '{}'), d.display_name)) x
                             WHERE dm.moiety_id = m.moiety_id), '{}'),
                   coalesce((SELECT array_agg(DISTINCT x) FROM preclin.fda_application_moiety am
                             JOIN preclin.fda_product p USING (appl_no), unnest(ARRAY[p.drug_name, p.active_ingredient]) x
                             WHERE am.moiety_id = m.moiety_id), '{}')
            FROM preclin.moiety m""")
        entities = cur.fetchall()
        keys = {}
        for mid, name, codes, aliases, strings, fda_names in entities:
            ordered = [name, *codes, *aliases, *fda_names, *strings]
            keys[mid] = list(dict.fromkeys(k for k in map(moiety_key, ordered) if k))
        cur.execute("""SELECT name_key, unii, name FROM preclin.unii_name WHERE name_key = ANY(%s)""",
                    (sorted({k for ks in keys.values() for k in ks}),))
        by_key = {}
        for key, u, name in cur.fetchall():
            by_key.setdefault(key, {}).setdefault(u, []).append(name)
        matched = {}
        for mid, ks in keys.items():
            cands = {}
            for k in ks:
                for u, names in by_key.get(k, {}).items():
                    cands.setdefault(u, []).extend(names)
            if cands:
                matched[mid] = dict(list(cands.items())[:UNII_CANDIDATES])
        uniis = sorted({u for c in matched.values() for u in c})
        cur.execute("""SELECT s.unii, s.display_name, s.substance_type, s.inn_id IS NOT NULL,
                              (SELECT array_agg(n.name ORDER BY array_position(ARRAY['of','cn','cd','bn'], n.name_type), n.name)
                               FROM preclin.unii_name n WHERE n.unii = s.unii AND n.name_type IN ('of','cn','cd','bn'))
                       FROM preclin.unii_substance s WHERE s.unii = ANY(%s)""", (uniis,))
        subs = {u: {"display_name": d, "substance_type": t, "inn": inn, "names": names or []}
                for u, d, t, inn, names in cur.fetchall()}
        cur.execute("""
            WITH s AS (SELECT dm.moiety_id, c.brief_title, c.lead_sponsor,
                              row_number() OVER (PARTITION BY dm.moiety_id ORDER BY c.start_date DESC NULLS LAST) rn
                       FROM preclin.drug_moiety dm JOIN preclin.ctgov_study_drug sd USING (drug_id)
                       JOIN preclin.ctgov_study c USING (nct_id)
                       WHERE dm.moiety_id = ANY(%s))
            SELECT moiety_id, json_agg(json_build_object('title', brief_title, 'sponsor', lead_sponsor))
            FROM s WHERE rn <= 3 GROUP BY moiety_id""", (list(matched),))
        trials = dict(cur.fetchall())
    items = {}
    for mid, name, codes, aliases, strings, fda_names in entities:
        if mid not in matched:
            continue
        items[str(mid)] = {
            "name": name, "codes": codes, "aliases": aliases,
            "strings": sorted(set(strings) | set(fda_names))[:10], "trials": trials.get(mid, []),
            "candidates": [{"unii": u, **{k: v for k, v in subs[u].items() if k != "names"},
                            "matched": sorted(set(m))[:4],
                            "names": [n for n in dict.fromkeys(subs[u]["names"]) if n not in m][:UNII_NAMES]}
                           for u, m in matched[mid].items()]}
    run_id = llm.run(UNII_TASK, items)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT subject_key::int, parsed_output->>'unii', llm_decision_id FROM pv_evidence.llm_decision
                       WHERE decision_run_id = %s AND validation_status = 'validated'
                         AND parsed_output->>'unii' IS NOT NULL""", (str(run_id),))
        chosen = {mid: (u, did) for mid, u, did in cur.fetchall()}
    merge(chosen)
    print(f"entities={len(entities)} with candidates={len(items)} resolved={len(chosen)}")
    same_entities()


def merge(chosen: dict[int, tuple[str, int]]) -> None:
    """Record each entity's UNII and merge entities that resolved to the same one,
    the survivor taking the substance's preferred (display) name."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT unii, display_name FROM preclin.unii_substance WHERE unii = ANY(%s)",
                    (sorted({u for u, _ in chosen.values()}),))
        preferred = {u: n.strip().lower() for u, n in cur.fetchall()}
    groups = defaultdict(list)
    for mid, (u, _) in chosen.items():
        groups[u].append(mid)
    merge_groups([(mids, preferred[u], u, {m: chosen[m][1] for m in mids}) for u, mids in groups.items()])


def merge_groups(groups: list[tuple[list[int], str | None, str | None, dict[int, int]]]) -> None:
    """Merge each group (members, preferred name, UNII, member -> UNII decision) into one
    entity: the member already named by the preferred name, else the one with a UNII
    and the most intervention names. Trial, FDA-application and target links move to
    the survivor; the merged entities' development programs are dropped for
    pipeline.programs build to rebuild. The survivor takes the preferred name
    unless another entity holds it, and keeps every other name as an alias."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT moiety_id, moiety_key, name, code_names, aliases, unii, unii_decision_id FROM preclin.moiety")
        ent = {r[0]: r[1:] for r in cur.fetchall()}
        cur.execute("""SELECT moiety_id, count(*) FROM preclin.drug_moiety GROUP BY 1""")
        n_links = dict(cur.fetchall())
        taken = {key: mid for mid, (key, *_) in ent.items()}
        mapping, renames, assigned = [], [], set()
        for mids, preferred, unii, dids in groups:
            mids = [m for m in mids if m in ent]
            if not mids:
                continue
            key = moiety_key(preferred) if preferred else None
            winner = next((m for m in mids if key and ent[m][0] == key), None) or \
                max(mids, key=lambda m: (ent[m][4] is not None, n_links.get(m, 0), -m))
            mapping += [(m, winner) for m in mids if m != winner]
            names = {ent[m][1] for m in mids} | {a for m in mids for a in ent[m][3]}
            codes = sorted({c for m in mids for c in ent[m][2]})
            name = preferred or ent[winner][1]
            key = key or ent[winner][0]
            if ent[winner][0] != key and (taken.get(key, winner) not in mids or key in assigned):
                name, key = ent[winner][1], ent[winner][0]  # another entity holds the preferred name
            assigned.add(key)
            renames.append((winner, key, name, codes, sorted(names - {name}), unii or ent[winner][4],
                            dids.get(winner) if unii else ent[winner][5]))
        cur.execute("CREATE TEMP TABLE merge_map (loser int PRIMARY KEY, winner int NOT NULL) ON COMMIT DROP")
        if mapping:
            execute_values(cur, "INSERT INTO merge_map VALUES %s", mapping)
        for table, cols in [("drug_moiety", "drug_id, role, biosimilar_of, llm_decision_id, method"),
                            ("fda_application_moiety", "appl_no, biosimilar_of, llm_decision_id"),
                            ("ctgov_study_moiety", None), ("moiety_target", None), ("program_indication", None)]:
            if cols is None:
                cur.execute("""SELECT string_agg(quote_ident(column_name), ', ') FROM information_schema.columns
                                WHERE table_schema = 'preclin' AND table_name = %s AND column_name <> 'moiety_id'""",
                            (table,))
                cols = cur.fetchone()[0]
            cur.execute(f"""INSERT INTO preclin.{table} (moiety_id, {cols})
                            SELECT mm.winner, {', '.join('t.' + c.strip() for c in cols.split(','))}
                            FROM preclin.{table} t JOIN merge_map mm ON mm.loser = t.moiety_id
                            ON CONFLICT DO NOTHING""")
            cur.execute(f"DELETE FROM preclin.{table} t USING merge_map mm WHERE t.moiety_id = mm.loser")
        cur.execute("DELETE FROM preclin.dev_program p USING merge_map mm WHERE p.moiety_id IN (mm.loser, mm.winner)")
        cur.execute("DELETE FROM preclin.moiety m USING merge_map mm WHERE m.moiety_id = mm.loser")
        execute_values(cur, """UPDATE preclin.moiety m SET moiety_key = v.key, name = v.name, code_names = v.codes,
                                 aliases = v.aliases, unii = v.unii, unii_decision_id = v.did
                               FROM (VALUES %s) AS v(moiety_id, key, name, codes, aliases, unii, did)
                               WHERE m.moiety_id = v.moiety_id""", renames,
                       template="(%s, %s, %s, %s::text[], %s::text[], %s, %s)")
        conn.commit()
    print(f"groups={len(groups)} entities merged away={len(mapping)}")


SAME_SYSTEM = """You decide which candidate entities are the same active entity as a given drug entity from clinical trials, so that they can be merged.

Same entity: the same molecule whatever its salt, hydrate, solvate, crystal form or unspecified stereochemistry (aclidinium and aclidinium bromide); the same biologic under a code name, a nonproprietary name or a descriptive name; the same vaccine or cell or gene therapy product from the same developer with the same antigens or components, valency, adjuvant and platform, however it is spelled.
Not the same: a different molecule from the same class or with a shared stem; a prodrug or a conjugate whose nonproprietary name differs from the parent's (tenofovir disoproxil vs tenofovir alafenamide; trastuzumab vs trastuzumab deruxtecan); a radiolabelled form vs the unlabelled ligand; a vaccine with another valency, strain composition, adjuvant or manufacturer; a combination product vs one of its components; a generic description that could cover several products ("influenza vaccine") vs a specific product.
Use the names, code names, sponsors and trial titles. When unsure, leave the candidate out."""

SAME_SCHEMA = {
    "type": "object",
    "properties": {"same": {"type": "array", "items": {"type": "integer"}}, "rationale": {"type": "string"}},
    "required": ["same", "rationale"],
    "additionalProperties": False,
}
SAME_CANDIDATES = 8
SAME_MIN_SIMILARITY = 0.5


def render_same(p: dict) -> str:
    def desc(e):
        return (f"{e['name']}" + (f" (also: {'; '.join(e['other_names'])})" if e["other_names"] else "")
                + (f" | sponsors: {', '.join(e['sponsors'])}" if e["sponsors"] else "")
                + (f" | trial: {e['trial']}" if e["trial"] else "") + (f" | UNII {e['unii']}" if e["unii"] else ""))
    cands = "\n".join(f"- {c['moiety_id']}: {desc(c)}" for c in p["candidates"])
    return f"Entity: {desc(p['entity'])}\n\nCandidates:\n{cands}"


def validate_same(p: dict, out: dict) -> None:
    extra = set(out["same"]) - {c["moiety_id"] for c in p["candidates"]}
    if extra:
        raise ValueError(f"not candidates: {sorted(extra)}")


SAME_TASK = llm.Task(name="moiety_same_entity", prompt_version="v1", schema_version="v1", system=SAME_SYSTEM,
                     schema=SAME_SCHEMA, render=render_same, validate=validate_same, subject_type="moiety",
                     model="claude-opus-5-5", effort="medium", max_tokens=1500)


def same_entities() -> None:
    """Merge entities that are the same active entity under names UNII does not
    connect (salt and parent registered separately, vaccines and other products
    without a UNII). Candidates are each entity's nearest names; an LLM decides;
    a pair merges when every decision that saw it agrees."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.neighbors import NearestNeighbors
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT m.moiety_id, m.name, m.code_names || m.aliases, m.unii,
                   coalesce((SELECT array_agg(DISTINCT c.lead_sponsor) FROM (
                       SELECT c.lead_sponsor FROM preclin.drug_moiety dm JOIN preclin.ctgov_study_drug sd USING (drug_id)
                       JOIN preclin.ctgov_study c USING (nct_id) WHERE dm.moiety_id = m.moiety_id LIMIT 3) c), '{}'),
                   (SELECT c.brief_title FROM preclin.drug_moiety dm JOIN preclin.ctgov_study_drug sd USING (drug_id)
                    JOIN preclin.ctgov_study c USING (nct_id) WHERE dm.moiety_id = m.moiety_id LIMIT 1)
            FROM preclin.moiety m
            WHERE EXISTS (SELECT 1 FROM preclin.drug_moiety dm WHERE dm.moiety_id = m.moiety_id)
               OR EXISTS (SELECT 1 FROM preclin.fda_application_moiety am WHERE am.moiety_id = m.moiety_id)""")
        ents = [{"moiety_id": mid, "name": name, "other_names": sorted(set(others))[:6], "unii": unii,
                 "sponsors": sorted(s for s in sponsors if s)[:3], "trial": trial}
                for mid, name, others, unii, sponsors, trial in cur.fetchall()]
    texts = [" ".join([e["name"], *e["other_names"]]).lower() for e in ents]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 4), sublinear_tf=True)
    X = vec.fit_transform(texts)
    dist, idx = NearestNeighbors(n_neighbors=SAME_CANDIDATES + 1, metric="cosine").fit(X).kneighbors(X)
    items = {}
    for i, e in enumerate(ents):
        cands = [ents[j] for d, j in zip(dist[i], idx[i]) if j != i and 1 - d >= SAME_MIN_SIMILARITY
                 and not (e["unii"] and ents[j]["unii"])]  # two resolved substances are already distinct
        if cands:
            items[str(e["moiety_id"])] = {"entity": e, "candidates": cands}
    run_id = llm.run(SAME_TASK, items)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT subject_key::int, parsed_output->'same' FROM pv_evidence.llm_decision
                       WHERE decision_run_id = %s AND validation_status = 'validated'""", (str(run_id),))
        said = {mid: set(same) for mid, same in cur.fetchall()}
    seen = {int(k): {c["moiety_id"] for c in it["candidates"]} for k, it in items.items()}
    parent = {}

    def find(x):
        while parent.get(x, x) != x:
            x = parent[x]
        return x
    for a, same in said.items():
        for b in same:
            if b in seen and a in seen[b] and a not in said.get(b, set()):
                continue  # b saw a and disagreed
            parent[find(a)] = find(b)
    groups = defaultdict(list)
    for m in {m for pair in parent.items() for m in pair}:
        groups[find(m)].append(m)
    merge_groups([(mids, None, None, {}) for mids in groups.values() if len(mids) > 1])
    print(f"same-entity checks={len(items)} groups={sum(len(g) > 1 for g in groups.values())}")


MODALITIES = ["small_molecule", "peptide", "protein", "monoclonal_antibody", "multispecific_antibody",
              "antibody_drug_conjugate", "radioligand", "sirna_rnai", "antisense_oligonucleotide",
              "other_oligonucleotide", "mrna", "gene_therapy", "car_t", "other_cell_therapy", "vaccine",
              "microbiome_or_live_biotherapeutic", "other"]

MODALITY_SYSTEM = """You classify a drug (molecular entity) into one modality, following the classes used by BIO's 2021 Clinical Development Success Rates report plus a few finer classes.

- small_molecule: synthetic or natural-product small molecules, including prodrugs and small-molecule radiosensitizers.
- peptide: peptides and peptide analogues up to about 40 amino acids, including GLP-1 analogues, cyclic peptides, peptide hormones and peptide-drug conjugates.
- protein: recombinant or purified proteins that are not antibodies: enzymes, hormones such as insulin, cytokines, fusion proteins (e.g. Fc-fusion), coagulation factors, plasma proteins, toxins.
- monoclonal_antibody: monospecific antibodies and antibody fragments (including nanobodies), unconjugated.
- multispecific_antibody: bispecific or multispecific antibodies and T-cell engagers.
- antibody_drug_conjugate: antibodies conjugated to a cytotoxic or other payload (not radionuclides).
- radioligand: small molecules, peptides or antibodies carrying a therapeutic radionuclide.
- sirna_rnai: siRNA and other RNA-interference agents.
- antisense_oligonucleotide: antisense oligonucleotides, including splice-switching ASOs and gapmers.
- other_oligonucleotide: aptamers, CpG and other oligonucleotides that are neither siRNA nor antisense.
- mrna: mRNA therapeutics other than vaccines.
- gene_therapy: viral or non-viral gene transfer and in vivo gene editing.
- car_t: chimeric antigen receptor T cells (autologous or allogeneic).
- other_cell_therapy: other cell therapies (TCR-T, TILs, NK, stem cells, ex vivo gene-modified HSCs).
- vaccine: prophylactic or therapeutic vaccines (any platform, including mRNA vaccines).
- microbiome_or_live_biotherapeutic: live bacteria, fecal microbiota, phages.
- other: anything else (e.g. herbal extracts, plasma, mixtures, devices with drug).
Use the name, code names and trial context. If you do not recognise a code-named entity, infer from the trial descriptions; say so with confidence low."""

MODALITY_SCHEMA = {
    "type": "object",
    "properties": {"modality": {"type": "string", "enum": MODALITIES},
                   "confidence": {"type": "string", "enum": ["high", "medium", "low"]}},
    "required": ["modality", "confidence"],
    "additionalProperties": False,
}


def render_modality(p: dict) -> str:
    return (f"Entity: {p['name']}\nCode names: {', '.join(p['codes']) or 'none'}\n"
            f"Intervention strings naming it: {'; '.join(p['strings'])}\n"
            f"FDA application types: {', '.join(p['fda']) or 'none'}\n"
            f"Trial titles: {' | '.join(p['titles'])}")


MODALITY_TASK = llm.Task(name="moiety_modality", prompt_version="v1", schema_version="v1",
                         system=MODALITY_SYSTEM, schema=MODALITY_SCHEMA, render=render_modality,
                         subject_type="moiety", model="claude-opus-5-5", effort="low", max_tokens=1000)


def modality(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT m.moiety_id, m.name, m.code_names,
                   (SELECT array_agg(DISTINCT d.display_name) FROM preclin.drug_moiety dm
                    JOIN preclin.drug d USING (drug_id) WHERE dm.moiety_id = m.moiety_id),
                   (SELECT array_agg(DISTINCT a.appl_type) FROM preclin.fda_application_moiety am
                    JOIN preclin.fda_application a USING (appl_no) WHERE am.moiety_id = m.moiety_id),
                   (SELECT array_agg(t.brief_title) FROM (
                      SELECT DISTINCT c.brief_title FROM preclin.ctgov_study_moiety sm
                      JOIN preclin.ctgov_study c USING (nct_id)
                      WHERE sm.moiety_id = m.moiety_id AND sm.role = 'investigational' LIMIT 3) t)
            FROM preclin.moiety m
            WHERE EXISTS (SELECT 1 FROM preclin.dev_program p WHERE p.moiety_id = m.moiety_id)""")
        items = {str(mid): {"name": name, "codes": codes or [], "strings": sorted(strings or [])[:8],
                            "fda": fda or [], "titles": titles or []}
                 for mid, name, codes, strings, fda, titles in cur.fetchall()}
    run_id = llm.run(MODALITY_TASK, items)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""UPDATE preclin.moiety m SET modality = d.parsed_output->>'modality',
                         modality_decision_id = d.llm_decision_id
                       FROM pv_evidence.llm_decision d
                       WHERE d.decision_run_id = %s AND d.validation_status = 'validated'
                         AND d.subject_key = m.moiety_id::text""", (str(run_id),))
        conn.commit()
    print(f"entities={len(items)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    canon = sub.add_parser("canonicalize")
    canon.add_argument("--scope", choices=["all", "industry"], default="all")
    canon.set_defaults(fn=canonicalize)
    sub.add_parser("unii").set_defaults(fn=unii)
    sub.add_parser("modality").set_defaults(fn=modality)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
