"""Resolve preclin.drug intervention names to the molecular entities they contain.

    python -m pipeline.drugs canonicalize   # intervention names -> molecular entities
    python -m pipeline.drugs unii           # entity -> FDA UNII substance; merge entities that are the same
    python -m pipeline.drugs codes          # keep each sponsor code only on the entity it belongs to
    python -m pipeline.drugs modality       # modality class of every entity with a development program

Trial intervention strings name the same molecule many ways ("Keytruda",
"pembrolizumab 200 mg", "Pembrolizumab Dose A", "MK-3475"), bundle placebo
with drug ("Tirzepatide-Placebo") and describe combinations. A name with no
earlier LLM decision that exactly matches the name, code name or alias of an
entity resolved to a UNII substance (ignoring case and punctuation) is linked to
that entity directly. The LLM reads every other in-scope name with up to three
of its CT.gov snapshot trials and returns its active components under their
nonproprietary (INN/USAN) names, or sponsor code when no name exists. A
returned code name is kept only when the input mentions it; a nonproprietary
name that neither the input nor a registered UNII name carries gives way to the
component's sponsor code; a biosimilar takes its reference product's name.
Names that carry the same sponsor code and resolve it differently are decided
again, each shown how the others resolved. Results go to preclin.moiety (one row
per distinct active entity) and preclin.drug_moiety (drug_id -> moiety_id, one
row per active component).

An entity is then resolved to the FDA UNII substance it is (pipeline.unii
names: official, common, code and brand), choosing among the substances
registered under one of its names, those with a registered name containing one
of its sponsor codes as a word, and the parents of salts and hydrates among them
(preclin.unii_parent). Entities that resolve to the same substance (a sponsor
code and its later INN, say) are merged: the survivor takes the substance's
nonproprietary name (INN or USAN) when it has one and keeps every other name as
an alias, so later runs map those names straight to it. A same-entity pass then
merges entities UNII does not connect (salt and parent registered separately, a
formulation substance and its active moiety, vaccines and other products without
a UNII) when every LLM decision that saw the pair agrees, naming the merged
entity by the product's nonproprietary name.

An entity's code names are the sponsor codes its intervention strings wrote, so a code a trial
wrote next to another drug ("Canakinumab (AIN457)", AIN457 being secukinumab) lands on the wrong
entity. The codes pass reviews every code that more than one entity carries, or that the FDA
substance registry assigns to a substance other than the entity's own (or a salt, parent or
sibling form of it): an LLM reads the registry entries, each holder's names and substance, and
the intervention strings that wrote the code; a second model checks every removal, and a code leaves an
entity only when both say it names another entity.
"""
from __future__ import annotations

import argparse
import os
import re
from collections import Counter, defaultdict

from psycopg2.extras import execute_values

from pipeline import llm

SYSTEM = """You resolve clinical-trial intervention names to the molecular entities they contain.

For the intervention name given (with the trials it appears in for context), return:
- kind: drug (one active entity), combination (two or more active entities given together or co-formulated), placebo_or_vehicle (placebo, vehicle, sham, saline, standard-of-care-only label, diluent), vaccine, non_drug (device, procedure, radiation, behavioral, diet, diagnostic/imaging agent used only for diagnosis, supplement of no defined active entity), or unclear.
- components: every active entity, excluding placebo. For each give:
  name: the international nonproprietary name (INN) or USAN in lower case if one exists (e.g. "pembrolizumab", "semaglutide", "insulin glargine", "trastuzumab deruxtecan"); for an entity with no nonproprietary name, its sponsor code exactly as commonly written (e.g. "MK-1084"). Map brand names and sponsor codes to the nonproprietary name when you are confident they are the same entity (e.g. Keytruda and MK-3475 -> pembrolizumab). Strip doses, strengths, routes, formulations, salts and schedules (e.g. "metformin hydrochloride 500 mg XR" -> "metformin").
  code_names: sponsor codes for this entity exactly as the input writes them; codes the input does not mention are dropped.
  biosimilar_of: for a biosimilar or a proposed biosimilar, the reference product's nonproprietary name; otherwise null. A biosimilar is named by its reference product's core nonproprietary name without the four-letter suffix (e.g. "adalimumab"), however the input spells or transliterates it.
  role: investigational if this entity is what the trial is developing in this arm; background if it is a partner/standard therapy given alongside.
- confidence: high, medium or low for the mapping as a whole.

Sponsor codes joined by a hyphen or slash, each naming a separately coded agent ("IO102-IO103"), are a combination of those agents, one component each, unless the joined form is itself one product's code.

Do not invent nonproprietary names: if you are not confident a code maps to an INN, keep the code. A nonproprietary name that no registered substance carries is replaced by the code.

Other intervention strings that carry the same sponsor code may be listed with how each was resolved. Resolve this string consistently with them when it names the same product; when they disagree among themselves, decide from the trials which resolution is right."""

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
    siblings = "\n".join(f"- {s['name']}: {s['kind']}; {', '.join(s['components']) or 'no components'}"
                         for s in p.get("siblings", []))
    return (f"Intervention name: {p['name']}\nOther names recorded: {', '.join(p['synonyms']) or 'none'}\n"
            f"ChEMBL id recorded: {p['chembl_id'] or 'none'}\n\nTrials using it:\n{trials or '(none)'}"
            + (f"\n\nOther strings carrying the same sponsor code, as resolved:\n{siblings}" if siblings else ""))


TASK = llm.Task(name="drug_moiety", prompt_version="v2", schema_version="v1", system=SYSTEM,
                schema=SCHEMA, render=render, subject_type="drug", effort="medium", max_tokens=3000)
SIBLINGS = 8  # sibling strings shown to a second decision
CODE_MIN = 3  # shortest sponsor-code key that groups sibling strings


def moiety_key(name: str) -> str:
    """Identity key for a component name: case- and punctuation-insensitive."""
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def word_keys(text: str, n: int = 4) -> set[str]:
    """Keys of every run of up to n consecutive words of text, splitting at anything but letters and
    digits: the keys a code written "MK-3475", "MK 3475" or "MK3475" can take."""
    words = [w for w in re.split(r"[^a-z0-9]+", text.lower()) if w]
    return {"".join(words[i:j]) for i in range(len(words)) for j in range(i + 1, min(i + n, len(words)) + 1)}


def components(out: dict, text: str, registered: set[str]) -> list[dict]:
    """The active components a decision records, given the rendered input it read (text) and the
    keys of registered UNII names among its component names. A code name is kept when it has no
    question mark and the input mentions it. A biosimilar is named by its reference product. A
    drug's nonproprietary name that neither the input nor a registered UNII name carries is
    replaced by the component's first kept code shaped like a sponsor code (a vaccine keeps its
    descriptive name, and a study number is no code)."""
    if out["kind"] not in ("drug", "combination", "vaccine"):
        return []
    seen, words = moiety_key(text), word_keys(text)
    comps = []
    for c in out["components"]:
        codes = [x for x in c["code_names"] if "?" not in x and moiety_key(x) in words]
        name = c["biosimilar_of"] or c["name"]
        sponsor_codes = [x for x in codes if is_code(moiety_key(x))]
        if (sponsor_codes and out["kind"] != "vaccine" and moiety_key(name) not in seen
                and moiety_key(name) not in registered):
            name = sponsor_codes[0]
        if moiety_key(name):
            comps.append({"name": name, "codes": codes, "role": c["role"], "biosimilar_of": c["biosimilar_of"]})
    return comps


def disagreements(names: dict[str, str], resolved: dict[str, tuple[str, list[dict]]]) -> dict[str, list[str]]:
    """Strings to decide again (subject key -> sibling keys to show), given each string's name and
    its decided kind and components. Siblings are strings with components or an unclear kind whose
    names carry, as words, the same sponsor code a decision kept. When they do not all resolve to
    the entity they most often give that code, the strings without it are decided again if the
    rest are a majority, else all are. Only keys shaped like a sponsor code (letters and digits, at
    least CODE_MIN characters) define siblings: a dose unit or an abbreviation that a decision kept
    as a code ("MG", "HIB") would otherwise group unrelated strings."""
    codes = {k for _, comps in resolved.values() for c in comps for k in map(moiety_key, c["codes"])
             if is_code(k) and len(k) >= CODE_MIN}
    members = defaultdict(list)
    for k, (kind, comps) in resolved.items():
        if comps or kind == "unclear":
            for code in word_keys(names[k]) & codes:
                members[code].append(k)
    flagged = defaultdict(list)
    for code, ks in members.items():
        votes = Counter(moiety_key(c["name"]) for k in ks for c in resolved[k][1]
                        if code == moiety_key(c["name"]) or code in map(moiety_key, c["codes"]))
        if len(ks) < 2 or not votes:
            continue
        top = votes.most_common(1)[0][0]
        agree = [k for k in ks if top in {moiety_key(c["name"]) for c in resolved[k][1]}]
        if len(agree) == len(ks):
            continue
        for k in ([k for k in ks if k not in agree] if 2 * len(agree) > len(ks) else ks):
            flagged[k] += [s for s in agree + ks if s != k]
    return {k: list(dict.fromkeys(sibs))[:SIBLINGS] for k, sibs in flagged.items()}


def entity_keys(cur, resolved: bool = False) -> dict[str, int]:
    """Every name key that identifies exactly one entity (with resolved, one resolved to a UNII
    substance): its own key, a code name without a question mark or an alias."""
    cur.execute("""SELECT k, min(moiety_id) FROM (
                     SELECT moiety_key AS k, moiety_id FROM preclin.moiety WHERE unii IS NOT NULL OR NOT %(r)s
                     UNION SELECT regexp_replace(lower(c), '[^a-z0-9]', '', 'g'), moiety_id
                     FROM preclin.moiety, unnest(code_names || aliases) c
                     WHERE (unii IS NOT NULL OR NOT %(r)s) AND strpos(c, '?') = 0) x
                   WHERE k <> '' GROUP BY k HAVING count(DISTINCT moiety_id) = 1""", {"r": resolved})
    return dict(cur.fetchall())


def registered_keys(keys: set[str]) -> set[str]:
    """The keys among these that name a registered UNII substance."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT name_key FROM preclin.unii_name WHERE name_key = ANY(%s)", (sorted(keys),))
        return {k for k, in cur.fetchall()}


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


def decide(items: dict[str, dict], reuse_by: str = "input") -> dict[str, tuple[int, str, list[dict]]]:
    """subject key -> (decision id, kind, recorded components) for every validated decision."""
    decided = llm.decisions(llm.run(TASK, items, reuse_by=reuse_by))
    registered = registered_keys({moiety_key(c["biosimilar_of"] or c["name"]) for _, _, out in decided
                                  for c in out["components"]})
    return {k: (did, out["kind"], components(out, render(items[k]), registered)) for k, did, out in decided}


def canonicalize(_args) -> None:
    """Resolve intervention names. A name with no earlier validated decision
    that is exactly the name, code name or alias of an entity resolved to a UNII
    substance (ignoring case and punctuation) is linked directly. The LLM reads
    the other names that are not from the CT.gov snapshot registration
    (resolved_via <> 'ctgov_snapshot') or that appear in an industry-sponsored
    snapshot trial, each with up to three of its CT.gov snapshot trials. Names
    whose shared sponsor code the decisions resolve differently are decided
    again with the other names' resolutions (disagreements)."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT drug_id, display_name, coalesce(synonyms, '{}'), chembl_id, normalized_name, "
                    "resolved_via FROM preclin.drug")
        drugs = cur.fetchall()
        exact_keys = entity_keys(cur, resolved=True)
        cur.execute("""SELECT DISTINCT sd.drug_id FROM preclin.ctgov_study_drug sd
                       JOIN preclin.ctgov_study s USING (nct_id) WHERE s.lead_sponsor_class = 'INDUSTRY'""")
        industry = {r[0] for r in cur.fetchall()}
        cur.execute("""SELECT DISTINCT d.subject_key::int FROM pv_evidence.llm_decision d
                       JOIN pv_evidence.llm_decision_run r USING (decision_run_id)
                       WHERE d.task = %s AND r.prompt_version = %s AND d.validation_status = 'validated'""",
                    (TASK.name, TASK.prompt_version))
        decided_before = {r[0] for r in cur.fetchall()}
        cur.execute("""
            WITH s AS (
              SELECT drug_id, nct_id, row_number() OVER (PARTITION BY drug_id ORDER BY nct_id) AS rn
              FROM preclin.ctgov_study_drug)
            SELECT s.drug_id, json_agg(json_build_object('title', c.brief_title, 'sponsor', c.lead_sponsor,
                                                         'interventions', c.interventions) ORDER BY s.rn)
            FROM s JOIN preclin.ctgov_study c USING (nct_id)
            WHERE s.rn <= 3 GROUP BY s.drug_id""")
        context = dict(cur.fetchall())
    exact = {did: exact_keys[nk] for did, _, _, _, nk, _ in drugs
             if did not in decided_before and nk in exact_keys}
    in_scope = {did for did, *_, via in drugs if via != "ctgov_snapshot" or did in industry}
    items = {str(did): {"name": name, "synonyms": list(syn)[:6], "chembl_id": chembl,
                        "trials": [{**t, "interventions": t["interventions"] or []}
                                   for t in context.get(did, [])]}
             for did, name, syn, chembl, _, _ in drugs if did in in_scope and did not in exact}
    decided = decide(items, reuse_by="subject")
    again = disagreements({k: items[k]["name"] for k in decided}, {k: (kind, comps) for k, (_, kind, comps)
                                                                   in decided.items()})
    if again:
        decided |= decide({k: {**items[k], "siblings": [{"name": items[s]["name"], "kind": decided[s][1],
                                                         "components": [c["name"] for c in decided[s][2]]}
                                                        for s in sibs]}
                           for k, sibs in again.items()})
    with llm.connect() as conn, conn.cursor() as cur:
        moieties: dict[str, dict] = {}
        links = []
        kinds = []
        for drug_id, (decision_id, kind, comps) in decided.items():
            kinds.append((int(drug_id), kind, decision_id))
            for comp in comps:
                key = moiety_key(comp["name"])
                m = moieties.setdefault(key, {"name": comp["name"], "codes": set()})
                m["codes"].update(comp["codes"])
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
                       [(did, ids[k], role, bio, dec, "llm") for did, k, role, bio, dec in links]
                       + [(did, mid, "investigational", None, None, "exact_name") for did, mid in exact.items()])
        execute_values(cur, """UPDATE preclin.drug d SET entity_kind = v.kind, moiety_decision_id = v.did
            FROM (VALUES %s) AS v(drug_id, kind, did) WHERE d.drug_id = v.drug_id""",
                       kinds + [(did, "drug", None) for did in exact], template="(%s, %s, %s::bigint)")
        conn.commit()
    print(f"llm items={len(items)} decided={len(decided)} decided again={len(again)} "
          f"exact-name links={len(exact)} moieties={len(moieties)} links={len(links)}")


UNII_SYSTEM = """You decide which registered substance (FDA UNII) a drug entity from clinical trials is.

You get the entity's name, its code names and other names, the intervention strings that named it, some trials using it, and candidate substances from the FDA Global Substance Registration System, each shown with its display name, the names that matched and some other registered names: every substance with one of the entity's names among its registered names (exact match ignoring case and punctuation); every substance with a registered name that contains one of the entity's sponsor codes as a word ("TAK-418 FREE BASE", or an antibody's descriptive name naming its development code); and the parent substance of any candidate that is a salt, hydrate or solvate of it (marked "parent substance of").

Return the UNII of the candidate that is this same active entity, or null.
- A shared sponsor code or brand is not enough: the substance must fit the trials (sponsor, molecule type, mechanism, indication). Sponsors reuse code formats, and short codes collide.
- When candidates include a parent substance and its salts, hydrates, solvates, crystal forms or formulation esters, choose the parent active moiety (metformin, not metformin hydrochloride), also when the sponsor code is registered only on the salt (choose "TAK-418 FREE BASE" over "TAK-418", the hydrochloride). Keep a conjugate, prodrug ester or radiolabelled form that is itself the entity's nonproprietary name (baloxavir marboxil, trastuzumab deruxtecan, lutetium Lu-177 dotatate).
- A formulation substance (type specifiedSubstance, e.g. nab-paclitaxel) is chosen only when no candidate is its active moiety; when the active moiety is a candidate, choose it (paclitaxel).
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
CODE_WORD_MAX = 5  # a sponsor code found as a word in more substances' names than this offers none of them


def render_unii(p: dict) -> str:
    trials = "\n".join(f"- {t['title']} (sponsor: {t['sponsor']})" for t in p["trials"])
    cands = "\n".join(f"- UNII {c['unii']} | {c['display_name']} | {c['substance_type'] or '?'}"
                       f"{' | INN' if c['inn'] else ''} | "
                       + (f"matched: {'; '.join(c['matched'])} | " if c["matched"] else "")
                       + (f"parent substance of: {'; '.join(c['parent_of'])} | " if c["parent_of"] else "")
                       + f"other names: {'; '.join(c['names'])}" for c in p["candidates"])
    return (f"Entity: {p['name']}\nCode names: {', '.join(p['codes']) or 'none'}\n"
            f"Other names: {', '.join(p['aliases']) or 'none'}\n"
            f"Intervention strings naming it: {'; '.join(p['strings']) or 'none'}\n"
            f"Trials:\n{trials or '(none)'}\n\nCandidate substances:\n{cands}")


def validate_unii(p: dict, out: dict) -> None:
    if out["unii"] is not None and out["unii"] not in {c["unii"] for c in p["candidates"]}:
        raise ValueError(f"unii {out['unii']} is not a candidate")


UNII_TASK = llm.Task(name="moiety_unii", prompt_version="v2", schema_version="v1", system=UNII_SYSTEM,
                     schema=UNII_SCHEMA, render=render_unii, validate=validate_unii, subject_type="moiety",
                     model="claude-opus-5-5", effort="medium", max_tokens=1500)


def is_code(key: str) -> bool:
    """Whether a name key has the shape of a sponsor code: letters and digits."""
    return bool(re.search(r"[a-z]", key) and re.search(r"[0-9]", key))


def candidate_uniis(found: list[tuple[str, list[str]]], parents: dict[str, list[str]]) -> dict[str, dict]:
    """The candidate substances of one entity, at most UNII_CANDIDATES: each substance found by
    name (UNII, matched names) in order, followed by its parents; a parent found by name too is
    marked as one. Returns UNII -> {"matched": names, "parent_of": child UNIIs among the candidates}."""
    cands: dict[str, dict] = {}
    for u, names in found:
        for v in [u, *parents.get(u, [])]:
            c = cands.setdefault(v, {"matched": [], "parent_of": []})
            if v == u:
                c["matched"] += names
            elif u not in c["parent_of"]:
                c["parent_of"].append(u)
    kept = dict(list(cands.items())[:UNII_CANDIDATES])
    return {v: {**c, "parent_of": [u for u in c["parent_of"] if u in kept]} for v, c in kept.items()}


def nonproprietary_name(display: str, names: list[str]) -> str | None:
    """The name an entity resolved to a substance takes, from its display name and registered
    names: the display name when it is a registered INN or USAN, else the INN, else None (the
    entity keeps its own name)."""
    def tagged(tag):
        return [re.sub(r"\s*\[[^\]]*\]\s*$", "", n).strip().lower() for n in names
                if n.rstrip().upper().endswith(f"[{tag}]")]
    if moiety_key(display) in {moiety_key(n) for n in tagged("INN") + tagged("USAN")}:
        return display.strip().lower()
    return min(tagged("INN"), default=None)


def unii_items(cur, entities: list[tuple], parents: dict[str, list[str]]) -> dict[str, dict]:
    """moiety_unii payloads of the entities (moiety_id, name, code names, aliases, intervention
    strings, FDA names) that have candidate substances, given each salt's parent UNIIs."""
    keys, code_keys = {}, {}
    for mid, name, codes, aliases, strings, fda_names in entities:
        ordered = [name, *codes, *aliases, *fda_names, *strings]
        keys[mid] = list(dict.fromkeys(k for k in map(moiety_key, ordered) if k))
        code_keys[mid] = [k for k in dict.fromkeys(map(moiety_key, [name, *codes, *aliases])) if is_code(k)]
    cur.execute("""SELECT name_key, unii, name FROM preclin.unii_name WHERE name_key = ANY(%s)""",
                (sorted({k for ks in keys.values() for k in ks}),))
    by_key = {}
    for key, u, name in cur.fetchall():
        by_key.setdefault(key, {}).setdefault(u, []).append(name)
    # Registered names (other than systematic ones) that contain a sponsor code as a word.
    cur.execute("""SELECT DISTINCT k.key, n.unii, n.name FROM preclin.unii_name n
                   CROSS JOIN LATERAL regexp_split_to_table(n.name, '[\\s,;()\\[\\]]+') w
                   JOIN unnest(%s::text[]) k(key) ON regexp_replace(lower(w), '[^a-z0-9]', '', 'g') = k.key
                   WHERE n.name_type <> 'sys' AND n.name_key <> k.key""",
                (sorted({k for ks in code_keys.values() for k in ks}),))
    by_code = {}
    for key, u, name in cur.fetchall():
        by_code.setdefault(key, {}).setdefault(u, []).append(name[:160])
    by_code = {k: v for k, v in by_code.items() if len(v) <= CODE_WORD_MAX}
    matched = {}
    for mid, ks in keys.items():
        found = [hit for k in ks for hit in by_key.get(k, {}).items()]
        found += [hit for k in code_keys[mid] for hit in by_code.get(k, {}).items()]
        if found:
            matched[mid] = candidate_uniis(found, parents)
    uniis = sorted({u for c in matched.values() for u in c})
    cur.execute("""SELECT s.unii, s.display_name, s.substance_type, s.inn_id IS NOT NULL,
                          (SELECT array_agg(n.name ORDER BY array_position(ARRAY['of','cn','cd','bn'], n.name_type), n.name)
                           FROM preclin.unii_name n WHERE n.unii = s.unii AND n.name_type IN ('of','cn','cd','bn'))
                   FROM preclin.unii_substance s WHERE s.unii = ANY(%s)""", (uniis,))
    subs = {u: {"display_name": d, "substance_type": t, "inn": inn, "names": names or []}
            for u, d, t, inn, names in cur.fetchall()}
    cur.execute("""
        WITH s AS (SELECT dm.moiety_id, c.brief_title, c.lead_sponsor,
                          row_number() OVER (PARTITION BY dm.moiety_id
                                             ORDER BY c.start_date DESC NULLS LAST, c.nct_id) rn
                   FROM preclin.drug_moiety dm JOIN preclin.ctgov_study_drug sd USING (drug_id)
                   JOIN preclin.ctgov_study c USING (nct_id)
                   WHERE dm.moiety_id = ANY(%s))
        SELECT moiety_id, json_agg(json_build_object('title', brief_title, 'sponsor', lead_sponsor) ORDER BY rn)
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
                            "matched": sorted(set(c["matched"]))[:4],
                            "parent_of": [f"UNII {p} ({subs[p]['display_name']})" for p in c["parent_of"]],
                            "names": [n for n in dict.fromkeys(subs[u]["names"])
                                      if n not in c["matched"]][:UNII_NAMES]}
                           for u, c in matched[mid].items()]}
    return items


def unii(_args) -> None:
    """Resolve every entity to its UNII substance, merge entities that
    resolved to the same one into a single entity named by the substance's
    nonproprietary name (nonproprietary_name), run the same-entity pass
    (same_entities), and drop the entities nothing references (drop_unreferenced)."""
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
        cur.execute("SELECT unii, array_agg(parent_unii ORDER BY parent_unii) FROM preclin.unii_parent GROUP BY 1")
        items = unii_items(cur, entities, dict(cur.fetchall()))
    run_id = llm.run(UNII_TASK, items)
    chosen = {int(k): (out["unii"], did) for k, did, out in llm.decisions(run_id) if out["unii"] is not None}
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT s.unii, s.display_name, coalesce(array_agg(n.name) FILTER (WHERE n.name IS NOT NULL), '{}')
                       FROM preclin.unii_substance s
                       LEFT JOIN preclin.unii_name n ON n.unii = s.unii AND n.name ~ '\\[(INN|USAN)\\]\\s*$'
                       WHERE s.unii = ANY(%s) GROUP BY 1, 2""", (sorted({u for u, _ in chosen.values()}),))
        preferred = {u: nonproprietary_name(display, names) for u, display, names in cur.fetchall()}
    groups = defaultdict(list)
    for mid, (u, _) in chosen.items():
        groups[u].append(mid)
    merge_groups([(mids, preferred[u], u, {m: chosen[m][1] for m in mids}) for u, mids in groups.items()])
    print(f"entities={len(entities)} with candidates={len(items)} resolved={len(chosen)}")
    same_entities()
    drop_unreferenced()


def drop_unreferenced() -> None:
    """Delete the entities no table references any longer: names a later canonicalize resolves
    elsewhere leave their old entity behind."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT c.conrelid::regclass::text FROM pg_constraint c
                       WHERE c.contype = 'f' AND c.confrelid = 'preclin.moiety'::regclass""")
        unreferenced = " AND ".join(f"NOT EXISTS (SELECT 1 FROM {t} r WHERE r.moiety_id = m.moiety_id)"
                                    for t, in cur.fetchall())
        cur.execute(f"DELETE FROM preclin.moiety m WHERE {unreferenced}")
        print(f"unreferenced entities dropped={cur.rowcount}")
        conn.commit()


def merge_groups(groups: list[tuple[list[int], str | None, str | None, dict[int, int]]]) -> None:
    """Merge each group (members, preferred name, UNII, member -> UNII decision) into one
    entity: the member already named by the preferred name, else the one with a UNII
    that is not a formulation substance, a UNII, and the most intervention names,
    in that order. Rows of every table that references an entity (intervention
    names, trials, FDA applications, targets, development indications, stops,
    literature searches, ChEMBL parents) move to the survivor, keeping the
    survivor's own on a conflict; the development programs of
    the merged entities and of the survivor are deleted for pipeline.programs build
    to rebuild. The survivor takes the preferred name unless another entity holds
    it, and keeps every other name as an alias."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT m.moiety_id, m.moiety_key, m.name, m.code_names, m.aliases, m.unii, m.unii_decision_id,
                              coalesce(s.substance_type LIKE 'specifiedSubstance%', false)
                       FROM preclin.moiety m LEFT JOIN preclin.unii_substance s USING (unii)""")
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
                max(mids, key=lambda m: (ent[m][4] is not None and not ent[m][6], ent[m][4] is not None,
                                         n_links.get(m, 0), -m))
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
        execute_values(cur, "INSERT INTO merge_map VALUES %s", mapping)
        cur.execute("""SELECT DISTINCT c.conrelid::regclass::text FROM pg_constraint c
                       WHERE c.contype = 'f' AND c.confrelid = 'preclin.moiety'::regclass
                         AND c.conrelid <> 'preclin.dev_program'::regclass""")
        for table in sorted(t.removeprefix("preclin.") for t, in cur.fetchall()):
            cur.execute("""SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position),
                                  string_agg('t.' || quote_ident(column_name), ', ' ORDER BY ordinal_position)
                           FROM information_schema.columns
                           WHERE table_schema = 'preclin' AND table_name = %s AND column_name <> 'moiety_id'""",
                        (table,))
            cols, t_cols = cur.fetchone()
            cur.execute(f"""INSERT INTO preclin.{table} (moiety_id, {cols})
                            SELECT mm.winner, {t_cols}
                            FROM preclin.{table} t JOIN merge_map mm ON mm.loser = t.moiety_id
                            ON CONFLICT DO NOTHING""")
            cur.execute(f"DELETE FROM preclin.{table} t USING merge_map mm WHERE t.moiety_id = mm.loser")
        cur.execute("DELETE FROM preclin.dev_program p USING merge_map mm WHERE p.moiety_id IN (mm.loser, mm.winner)")
        cur.execute("DELETE FROM preclin.moiety m USING merge_map mm WHERE m.moiety_id = mm.loser")
        execute_values(cur, """UPDATE preclin.moiety m SET moiety_key = v.key, name = v.name, code_names = v.codes,
                                 aliases = v.aliases, unii = v.unii, unii_decision_id = v.did
                               FROM (VALUES %s) AS v(moiety_id, key, name, codes, aliases, unii, did)
                               WHERE m.moiety_id = v.moiety_id""", renames,
                       template="(%s, %s, %s, %s::text[], %s::text[], %s, %s::bigint)")
        conn.commit()
    print(f"groups={len(groups)} entities merged away={len(mapping)}")


SAME_SYSTEM = """You decide which candidate entities are the same active entity as a given drug entity from clinical trials, so that they can be merged.

Same entity: the same molecule whatever its salt, hydrate, solvate, crystal form or unspecified stereochemistry (aclidinium and aclidinium bromide); a formulation of a molecule and the molecule itself (nab-paclitaxel and paclitaxel; a UNII marked "formulation" is a formulation substance); the same biologic under a code name, a nonproprietary name or a descriptive name; the same vaccine or cell or gene therapy product from the same developer with the same antigens or components, valency, adjuvant and platform, however it is spelled or whatever indication its code suffix names.
Not the same: a different molecule from the same class or with a shared stem; a prodrug or a conjugate whose nonproprietary name differs from the parent's (tenofovir disoproxil vs tenofovir alafenamide; trastuzumab vs trastuzumab deruxtecan); a radiolabelled form vs the unlabelled ligand; a vaccine with another valency, strain composition, adjuvant or manufacturer; a combination product vs one of its components; a generic description that could cover several products ("influenza vaccine") vs a specific product.
Use the names, code names, sponsors and trial titles. When unsure, leave the candidate out.

name: when you list any candidate, the name the merged entity takes: its nonproprietary name (INN or USAN) if it has one; otherwise the product's code or descriptive name common to all of them, without an indication, dose, formulation or cohort suffix (allo-APZ2, not allo-APZ2-CVU). An empty string when you list none."""

SAME_SCHEMA = {
    "type": "object",
    "properties": {"same": {"type": "array", "items": {"type": "integer"}}, "name": {"type": "string"},
                   "rationale": {"type": "string"}},
    "required": ["same", "name", "rationale"],
    "additionalProperties": False,
}
SAME_CANDIDATES = 8
SAME_MIN_SIMILARITY = 0.5


def render_same(p: dict) -> str:
    def desc(e):
        return (f"{e['name']}" + (f" (also: {'; '.join(e['other_names'])})" if e["other_names"] else "")
                + (f" | sponsors: {', '.join(e['sponsors'])}" if e["sponsors"] else "")
                + (f" | trial: {e['trial']}" if e["trial"] else "")
                + (f" | UNII {e['unii']}" + (" (formulation)" if e["formulation"] else "") if e["unii"] else ""))
    cands = "\n".join(f"- {c['moiety_id']}: {desc(c)}" for c in p["candidates"])
    return f"Entity: {desc(p['entity'])}\n\nCandidates:\n{cands}"


def validate_same(p: dict, out: dict) -> None:
    extra = set(out["same"]) - {c["moiety_id"] for c in p["candidates"]}
    if extra:
        raise ValueError(f"not candidates: {sorted(extra)}")


SAME_TASK = llm.Task(name="moiety_same_entity", prompt_version="v2", schema_version="v2", system=SAME_SYSTEM,
                     schema=SAME_SCHEMA, render=render_same, validate=validate_same, subject_type="moiety",
                     model="claude-opus-5-5", effort="medium", max_tokens=1500)


def same_entities() -> None:
    """Merge entities that are the same active entity under names UNII does not
    connect (salt and parent registered separately, a formulation substance and
    its active moiety, vaccines and other products without a UNII). Candidates
    are each entity's nearest names, leaving out pairs of two substances that
    are not formulations; an LLM decides; a pair merges when every decision that
    saw it agrees. A merged entity none of whose members holds such a substance
    takes the name its decisions most often give it."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.neighbors import NearestNeighbors
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT m.moiety_id, m.name, m.code_names || m.aliases, m.unii,
                   coalesce((SELECT s.substance_type LIKE 'specifiedSubstance%' FROM preclin.unii_substance s
                             WHERE s.unii = m.unii), false),
                   coalesce((SELECT array_agg(DISTINCT c.lead_sponsor) FROM (
                       SELECT c.lead_sponsor FROM preclin.drug_moiety dm JOIN preclin.ctgov_study_drug sd USING (drug_id)
                       JOIN preclin.ctgov_study c USING (nct_id) WHERE dm.moiety_id = m.moiety_id
                       ORDER BY c.start_date DESC NULLS LAST, c.nct_id LIMIT 3) c), '{}'),
                   (SELECT c.brief_title FROM preclin.drug_moiety dm JOIN preclin.ctgov_study_drug sd USING (drug_id)
                    JOIN preclin.ctgov_study c USING (nct_id) WHERE dm.moiety_id = m.moiety_id
                    ORDER BY c.start_date DESC NULLS LAST, c.nct_id LIMIT 1)
            FROM preclin.moiety m
            WHERE EXISTS (SELECT 1 FROM preclin.drug_moiety dm WHERE dm.moiety_id = m.moiety_id)
               OR EXISTS (SELECT 1 FROM preclin.fda_application_moiety am WHERE am.moiety_id = m.moiety_id)""")
        ents = [{"moiety_id": mid, "name": name, "other_names": sorted(set(others))[:6], "unii": unii,
                 "formulation": formulation, "sponsors": sorted(s for s in sponsors if s)[:3], "trial": trial}
                for mid, name, others, unii, formulation, sponsors, trial in cur.fetchall()]
    substance = {e["moiety_id"] for e in ents if e["unii"] and not e["formulation"]}
    texts = [" ".join([e["name"], *e["other_names"]]).lower() for e in ents]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 4), sublinear_tf=True)
    X = vec.fit_transform(texts)
    dist, idx = NearestNeighbors(n_neighbors=SAME_CANDIDATES + 1, metric="cosine").fit(X).kneighbors(X)
    items = {}
    for i, e in enumerate(ents):
        cands = [ents[j] for d, j in zip(dist[i], idx[i]) if j != i and 1 - d >= SAME_MIN_SIMILARITY
                 and not {e["moiety_id"], ents[j]["moiety_id"]} <= substance]  # two substances are distinct
        if cands:
            items[str(e["moiety_id"])] = {"entity": e, "candidates": cands}
    decided = llm.decisions(llm.run(SAME_TASK, items))
    said = {int(k): set(out["same"]) for k, _, out in decided}
    named = {int(k): out["name"].strip() for k, _, out in decided if out["same"] and out["name"].strip()}
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
    merges = []
    for mids in groups.values():
        votes = Counter(named[m] for m in sorted(mids) if m in named)
        if len(mids) > 1:
            merges.append((mids, None if substance & set(mids) or not votes else votes.most_common(1)[0][0], None, {}))
    merge_groups(merges)
    print(f"same-entity checks={len(items)} groups={sum(len(g) > 1 for g in groups.values())}")


CODES_SYSTEM = """You decide which drug entities a sponsor code belongs to.

A code (a sponsor's development code such as "AIN457" or "MK-3475", or a short label written beside a drug in a trial) has been recorded on one or more drug entities from clinical-trial intervention strings. You get the code; the substances the FDA substance registry lists under that name; and each entity carrying it, with its other names, its registered substance, and the intervention strings and trials that wrote the code.

For each entity, decide whether the code is that entity's own:
- the_entity_itself: the code is this entity's development or product code.
- a_form_of_the_entity: the code names a salt, ester, formulation, conjugate or labelled form of this entity, or a precursor code of the same product.
- combination_containing_it: the code names a combination product or regimen that contains this entity (each component keeps the code).
- sponsor_reused_code: another product carries the same code in the registry, but this entity's own trials use the code for this entity (sponsors reuse short codes).
- code_of_another_entity: the code names a different product; this entity carries it only because an intervention string paired them (a typo, a combination listed drug by drug, a partner drug in the same arm).
- unclear: the evidence does not settle it.

owns is false only for code_of_another_entity; every other reason keeps the code."""

CODES_SCHEMA = {
    "type": "object",
    "properties": {
        "holders": {"type": "array", "items": {"type": "object", "properties": {
            "moiety_id": {"type": "integer"}, "owns": {"type": "boolean"},
            "reason": {"type": "string", "enum": ["the_entity_itself", "a_form_of_the_entity", "combination_containing_it",
                                                  "sponsor_reused_code", "code_of_another_entity", "unclear"]}},
            "required": ["moiety_id", "owns", "reason"], "additionalProperties": False}},
        "rationale": {"type": "string"},
    },
    "required": ["holders", "rationale"],
    "additionalProperties": False,
}
CODE_STRINGS = 4  # intervention strings shown per holder
CODE_REGISTERED = 5  # registry substances shown per code
CODES_AUDIT = "report/audits/code_names_fix.json"


def render_codes(p: dict) -> str:
    reg = "\n".join(f"- {r['display_name']} ({r['type']}; registered as \"{r['as']}\")" for r in p["registry"]) or "- none"
    hold = []
    for h in p["holders"]:
        strings = "\n".join(f"    - \"{s['string']}\" in {s['nct']} ({s['sponsor']}): {s['title']}" for s in h["strings"])
        hold.append(f"- {h['moiety_id']}: {h['name']}" + (f" (also: {'; '.join(h['other_names'])})" if h["other_names"] else "")
                    + f" | registered substance: {h['substance'] or 'none'}"
                    + (f"\n  intervention strings that wrote the code:\n{strings}" if strings else ""))
    return f"Code: {p['code']}\n\nFDA substance registry entries under this name:\n{reg}\n\nEntities carrying it:\n" + "\n".join(hold)


def validate_codes(p: dict, out: dict) -> None:
    ids = [h["moiety_id"] for h in out["holders"]]
    if sorted(ids) != sorted(h["moiety_id"] for h in p["holders"]):
        raise ValueError(f"holders {sorted(ids)} are not the entities given")
    if any(h["owns"] != (h["reason"] != "code_of_another_entity") for h in out["holders"]):
        raise ValueError("owns must be false exactly for code_of_another_entity")


CODES_TASK = llm.Task(name="moiety_code_owner", prompt_version="v1", schema_version="v1", system=CODES_SYSTEM,
                      schema=CODES_SCHEMA, render=render_codes, validate=validate_codes, subject_type="code",
                      model="claude-opus-5-5", effort="medium", max_tokens=2000)
# A code leaves an entity only when a second model, reading the same evidence, agrees it is another entity's.
CODES_CHECK_TASK = llm.Task(name="moiety_code_owner_check", prompt_version="v1", schema_version="v1",
                            system=CODES_SYSTEM, schema=CODES_SCHEMA, render=render_codes, validate=validate_codes,
                            subject_type="code", model="claude-sonnet-5", effort="medium", max_tokens=2000)


def related_substances(a: str | None, b: str, parents: dict[str, set[str]]) -> bool:
    """Whether substance b is a, its parent, its salt or form, or a sibling form sharing a parent."""
    if a is None:
        return False
    pa, pb = parents.get(a, set()), parents.get(b, set())
    return a == b or b in pa or a in pb or bool(pa & pb)


def review_keys(holders: dict[str, set[int]], unii_of: dict[int, str | None], registered: dict[str, set[str]],
                parents: dict[str, set[str]]) -> set[str]:
    """Code keys to review: carried by more than one entity, or registered to a substance that is not the
    holder's own (or a related form of it), including a holder with no substance of its own."""
    return {k for k, ms in holders.items()
            if len(ms) > 1 or any(not any(related_substances(unii_of.get(m), u, parents) for u in registered.get(k, ()))
                                  for m in ms if registered.get(k))}


def agreed_verdicts(first: dict[str, dict[int, bool]], second: dict[str, dict[int, bool]]) -> dict[str, dict[int, bool]]:
    """An entity does not own a code only when both decisions say so; a code the second model did not decide stays."""
    return {k: {m: owns or second.get(k, {}).get(m, True) for m, owns in vs.items()} for k, vs in first.items()}


def owned_codes(codes: dict[int, list[str]], keys: dict[int, str], verdicts: dict[str, dict[int, bool]]) -> dict[int, list[str]]:
    """Each entity's codes without those a verdict says it does not own; an entity keeps a code that is its own name."""
    return {m: [c for c in cs if verdicts.get(moiety_key(c), {}).get(m, True) or moiety_key(c) == keys[m]]
            for m, cs in codes.items()}


def codes(args) -> None:
    """Keep each code name only on the entities it belongs to (CODES_TASK over review_keys, each removal confirmed by
    CODES_CHECK_TASK); with --dry-run,
    write the audit (CODES_AUDIT), with the intervention strings routed to an entity that does not own the code
    they name, and leave moiety as is."""
    import json
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT m.moiety_id, m.moiety_key, m.name, m.code_names, m.aliases, m.unii,
                              s.display_name || ' (' || coalesce(s.substance_type, '?') || ')'
                       FROM preclin.moiety m LEFT JOIN preclin.unii_substance s USING (unii)""")
        ents = {r[0]: r[1:] for r in cur.fetchall()}
        cur.execute("SELECT unii, array_agg(parent_unii) FROM preclin.unii_parent GROUP BY 1")
        parents = {u: set(ps) for u, ps in cur.fetchall()}
        holders = defaultdict(set)
        for m, (_, _, cs, *_) in ents.items():
            for c in cs:
                if moiety_key(c):
                    holders[moiety_key(c)].add(m)
        cur.execute("""SELECT n.name_key, n.unii, n.name, n.name_type, s.display_name, s.substance_type
                       FROM preclin.unii_name n JOIN preclin.unii_substance s USING (unii) WHERE n.name_key = ANY(%s)""",
                    (sorted(holders),))
        registry = defaultdict(dict)
        for k, u, name, ntype, display, stype in cur.fetchall():
            registry[k].setdefault(u, {"display_name": display, "type": stype or "?", "as": f"{name} [{ntype}]"})
        keys = review_keys(holders, {m: e[4] for m, e in ents.items()}, {k: set(r) for k, r in registry.items()}, parents)
        mids = sorted({m for k in keys for m in holders[k]})
        cur.execute("""SELECT dm.moiety_id, d.display_name, coalesce(d.synonyms, '{}'), sd.nct_id, c.lead_sponsor,
                              c.brief_title
                       FROM preclin.drug_moiety dm JOIN preclin.drug d USING (drug_id)
                       JOIN LATERAL (SELECT nct_id FROM preclin.ctgov_study_drug x WHERE x.drug_id = d.drug_id
                                     ORDER BY nct_id LIMIT 1) sd ON true
                       JOIN preclin.ctgov_study c USING (nct_id) WHERE dm.moiety_id = ANY(%s)""", (mids,))
        strings = defaultdict(list)
        for m, display, synonyms, nct, sponsor, title in cur.fetchall():
            for text in [display, *synonyms]:  # the intervention name, then the names its registration lists
                strings[m].append({"string": display if text == display else f"{display} [listed as: {text}]",
                                   "words": word_keys(text), "nct": nct, "sponsor": sponsor or "?", "title": title or ""})
    items = {}
    for k in sorted(keys):
        hs = sorted(holders[k])
        written = sorted({c for m in hs for c in ents[m][2] if moiety_key(c) == k})
        items[k] = {"code": " / ".join(written),
                    "registry": sorted(registry.get(k, {}).values(), key=lambda r: r["display_name"])[:CODE_REGISTERED],
                    "holders": [{"moiety_id": m, "name": ents[m][1], "other_names": sorted(set(ents[m][3]))[:6],
                                 "substance": ents[m][5],
                                 "strings": [{x: s[x] for x in ("string", "nct", "sponsor", "title")}
                                             for s in strings[m] if k in s["words"]][:CODE_STRINGS]} for m in hs]}
    decided = llm.decisions(llm.run(CODES_TASK, items))
    first = {k: {h["moiety_id"]: h["owns"] for h in out["holders"]} for k, _, out in decided}
    reasons = Counter(h["reason"] for _, _, out in decided for h in out["holders"])
    disputed = {k: items[k] for k, v in first.items() if not all(v.values())}
    second = {k: {h["moiety_id"]: h["owns"] for h in out["holders"]}
              for k, _, out in llm.decisions(llm.run(CODES_CHECK_TASK, disputed))}
    verdicts = agreed_verdicts(first, second)
    dropped = sum(not v for k, vs in first.items() for v in vs.values()) - sum(not v for vs in verdicts.values()
                                                                             for v in vs.values())
    new = owned_codes({m: list(e[2]) for m, e in ents.items()}, {m: e[0] for m, e in ents.items()}, verdicts)
    removed = [(m, c) for m, e in ents.items() for c in e[2] if c not in new[m]]
    print(f"codes reviewed={len(items)} holder verdicts={sum(reasons.values())} by reason={dict(reasons)} "
          f"second-model checks={len(disputed)} removals the check did not confirm={dropped} "
          f"codes removed={len(removed)} from entities={len({m for m, _ in removed})}")
    if args.dry_run:
        out = {"reviewed_codes": len(items), "verdicts_by_reason": dict(reasons), "second_model_checks": len(disputed),
               "removals_not_confirmed": dropped, "removed": len(removed),
               "entities_changed": len({m for m, _ in removed}),
               "removed_pairs": [{"moiety_id": m, "entity": ents[m][1], "code": c,
                                  "owner": [ents[o][1] for o, v in verdicts[moiety_key(c)].items() if v],
                                  "strings_routed_here": sorted({x["string"] for x in strings[m]
                                                                 if moiety_key(c) in x["words"]})[:CODE_STRINGS]}
                                 for m, c in sorted(removed)]}
        with open(os.path.join(llm.REPO, CODES_AUDIT), "w") as f:
            json.dump(out, f, indent=1)
        return
    with llm.connect() as conn, conn.cursor() as cur:
        execute_values(cur, """UPDATE preclin.moiety m SET code_names = v.codes
            FROM (VALUES %s) AS v(moiety_id, codes) WHERE m.moiety_id = v.moiety_id""",
                       [(m, new[m]) for m in sorted({m for m, _ in removed})], template="(%s, %s::text[])")
        conn.commit()


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
                   (SELECT array_agg(t.brief_title ORDER BY t.latest DESC NULLS LAST, t.brief_title) FROM (
                      SELECT c.brief_title, max(c.start_date) AS latest FROM preclin.ctgov_study_moiety sm
                      JOIN preclin.ctgov_study c USING (nct_id)
                      WHERE sm.moiety_id = m.moiety_id AND sm.role = 'investigational' GROUP BY c.brief_title
                      ORDER BY latest DESC NULLS LAST, c.brief_title LIMIT 3) t)
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
    sub.add_parser("canonicalize").set_defaults(fn=canonicalize)
    sub.add_parser("unii").set_defaults(fn=unii)
    sub.add_parser("modality").set_defaults(fn=modality)
    p = sub.add_parser("codes")
    p.add_argument("--dry-run", action="store_true", help="write the audit and leave preclin.moiety as is")
    p.set_defaults(fn=codes)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
