"""Audit the drug-class assignment behind the named contexts (lists/named_contexts.csv, PR #81).

    .venv/bin/python analyses/model-system-atlas/class_audit.py

Read-only. Rebuilds the cohort lists.py uses (novel Phase 2 entrants 2008-2019 in the 71 named
indications) on today's database and writes, under lists/class_audit/:

  class_members.csv     one row per (named indication, novel Phase 2 program): the database's
                        target, action, ChEMBL mechanism, modality, novelty, first FDA approval and
                        furthest phase, joined to the hand review in reviews.csv (verified target,
                        action, selectivity, modality group, first FDA approval, evidence) and a
                        disagrees_with_db flag;
  current_on_db.csv     lists.classes() re-run on today's database (the committed
                        named_contexts.csv was drawn from an earlier build);
  proposed_contexts.csv the proposed rule (below) applied to the reviewed members.

reviews.csv is the hand-curated input, one row per moiety (same_entity_as folds a duplicate
moiety into the entity it repeats); a moiety absent from it falls back to the database's fields.

Proposed rule (decision 12). The tile's unit is the mechanism, (verified target, verified action),
counted across modalities; modality only splits the dose and platform-safety sub-strips inside a
tile (`modality_groups` lists them). A non-selective or off-class member carries its own verified
target (e.g. "JAK (pan)"), so it falls into its own mechanism (a dual member whose verified target is
the mechanism's target, such as netarsudil, ROCK plus NET, stays in); a member with no molecular
target (lubricants, barriers, photosensitisers) or an undisclosed one forms none. Members
FDA-approved before their Phase 2 entry are dropped (not novel). The indication's mechanism is the
one with the most distinct entities, at least MIN_PROGRAMS; phase is never a criterion, so the
choice does not depend on success. Mechanisms tied on count each get a tile; with none qualifying
the indication is blank.
"""
import importlib.util
import os
import sys

import pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
from report import frame, section1  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "lists", "class_audit")
REVIEWS = os.path.join(OUT, "reviews.csv")
MIN_PROGRAMS = 3

_spec = importlib.util.spec_from_file_location("atlas_lists", os.path.join(HERE, "lists.py"))
lists = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lists)

MODALITY_GROUP = {
    "small_molecule": "small molecule", "monoclonal_antibody": "antibody", "multispecific_antibody": "antibody",
    "antibody_drug_conjugate": "ADC", "car_t": "cell therapy", "other_cell_therapy": "cell therapy",
    "gene_therapy": "gene therapy", "sirna_rnai": "oligo", "antisense_oligonucleotide": "oligo",
    "other_oligonucleotide": "oligo", "peptide": "peptide", "protein": "protein",
}


def cohort() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Phase 2 entries in the window as lists.main() draws them, the named indications, and the programs frame."""
    snap = frame.snapshot()
    progs, trials = frame.programs(), frame.program_trials()
    rows = section1.phase_rows(progs, trials, snap, window=lists.WINDOW)
    ent = rows[(rows.phase == lists.PHASE) & ~rows.credited][
        ["program_id", "moiety_id", "bio_area", "novel", "modality", "entry", "entry_year"]].copy()
    ent["mondo_id"] = ent.program_id.map(progs.set_index("program_id").mondo_id)
    ent = ent[ent.mondo_id.notna()]
    ent["disease"] = ent.mondo_id.map(lambda m: lists.MERGE.get(m, m))
    ent = ent[~ent.disease.isin(lists.DROP)]
    named = pd.read_csv(os.path.join(HERE, "lists", "named_indications.csv"))
    return ent, named, progs


def members(ent: pd.DataFrame, named: pd.DataFrame, progs: pd.DataFrame) -> pd.DataFrame:
    """One row per novel program in a named indication, with the database's view of its class."""
    mt = frame.query("""SELECT mt.moiety_id, string_agg(t.symbol, ';' ORDER BY t.symbol) AS db_target,
                               string_agg(mt.action, ';' ORDER BY t.symbol) AS db_action, count(*) AS n_primary
                        FROM preclin.moiety_target mt JOIN public.targets t ON t.id = mt.target_id
                        WHERE mt.is_primary GROUP BY mt.moiety_id""")
    mt["db_action"] = mt.db_action.map(lambda a: a if len(set(a.split(";"))) > 1 else a.split(";")[0])
    mech = frame.query("""SELECT x.moiety_id, string_agg(DISTINCT cm.mechanism_of_action, ' | ') AS chembl_mechanism
                          FROM preclin.chembl_moiety x JOIN preclin.chembl_mechanism cm
                            ON cm.parent_chembl_id = x.parent_chembl_id
                          WHERE cm.mechanism_of_action IS NOT NULL GROUP BY x.moiety_id""")
    moiety = frame.query("SELECT moiety_id, name AS drug, code_names FROM preclin.moiety")
    dp = frame.query("SELECT program_id, highest_phase FROM preclin.dev_program")
    p = progs.set_index("program_id")
    e = ent[ent.novel & ent.disease.isin(named.mondo_id)].copy()
    e = e.merge(named[["mondo_id", "label", "area"]].rename(columns={"mondo_id": "disease", "label": "indication"}),
                on="disease").merge(moiety, on="moiety_id", how="left").merge(mt, on="moiety_id", how="left") \
         .merge(mech, on="moiety_id", how="left").merge(dp, on="program_id", how="left")
    e["first_approval_date"] = e.program_id.map(p.moiety_first_fda_approval)
    e["approved_this_indication"] = e.program_id.map(p.approved)
    e["furthest_phase_reached"] = e.highest_phase.where(e.approved_this_indication.ne("yes"), 4)
    e["modality_group_db"] = e.modality.map(MODALITY_GROUP).fillna("other")
    e["novel_flag"] = e.novel
    e["code_names"] = e.code_names.map(lambda c: "; ".join(c) if isinstance(c, list) else "")
    e = e.rename(columns={"disease": "mondo_id_named", "mondo_id": "program_mondo_id"})
    return e.sort_values(["area", "indication", "db_target", "drug"], na_position="last")


ACTIVATING = {"agonist", "partial_agonist", "positive_modulator", "activator", "opener", "corrector", "potentiator",
              "amplifier", "replacement", "gene_expression_increase"}
ALIAS = {  # family words in verified-target labels -> gene symbols, for comparing with the database's targets
    "VEGFR": {"KDR", "FLT1", "FLT4"}, "FGFR": {"FGFR1", "FGFR2", "FGFR3", "FGFR4"}, "FGFR1C": {"FGFR1"},
    "PDGFR": {"PDGFRA", "PDGFRB"}, "HER": {"EGFR", "ERBB2", "ERBB4"}, "AURK": {"AURKA", "AURKB"},
    "TAM": {"AXL", "MERTK", "TYRO3"}, "ABL": {"ABL1"}, "PIM": {"PIM1", "PIM2", "PIM3"},
    "JAK": {"JAK1", "JAK2", "JAK3", "TYK2"}, "PI3K": {"PIK3CA", "PIK3CB", "PIK3CD", "PIK3CG"},
    "HDAC": {"HDAC1", "HDAC2", "HDAC3", "HDAC6", "HDAC8"}, "CDK4/6": {"CDK4", "CDK6"}, "PARP1/2": {"PARP1", "PARP2"},
    "MAP2K1/2": {"MAP2K1", "MAP2K2"}, "HCRTR1/2": {"HCRTR1", "HCRTR2"}, "CGRP": {"CALCRL", "RAMP1"},
    "ROCK": {"ROCK1", "ROCK2"}, "PDE4": {"PDE4A", "PDE4B", "PDE4C", "PDE4D"}, "SGLT1/2": {"SLC5A1", "SLC5A2"},
    "SLC6A2/3/4": {"SLC6A2", "SLC6A3", "SLC6A4"}, "NMDA": {"GRIN1", "GRIN2A", "GRIN2B", "GRIN2C", "GRIN2D"},
    "NTRK": {"NTRK1", "NTRK2", "NTRK3"}, "TUBULIN": {"TUBB", "TUBA1A"}, "AMYR": {"CALCR", "RAMP3"}, "TEC": {"TEC", "BTK", "ITK", "BMX", "TXK"},
}
NOT_GENES = {"HIV", "HCV", "HBV", "RNA", "RT", "NAP", "CAM", "MABA", "NRTI", "NNRTI", "NRTTI", "INSTI", "HA", "RAS", "RBD",
             "PSA", "SOD", "RASP", "IKACH", "SERT", "PD", "LT", "HBSAG", "BNAB", "ENV", "GAG"}
ACTION_PHRASE = {**lists.ACTION_PHRASE, "inverse_agonist": "{t} inverse agonists", "corrector": "{t} correctors", "potentiator": "{t} potentiators",
                 "amplifier": "{t} amplifiers", "tolerance_induction": "{t}", "other": "{t}"}


def symbols(label: str) -> set[str]:
    """Gene symbols a verified-target label names, through ALIAS for family words."""
    out: set[str] = set()
    for key, genes in ALIAS.items():
        if "/" in key and key in label:
            out |= genes
            label = label.replace(key, " ")
    for tok in label.replace("/", " ").replace("(", " ").replace(")", " ").replace("-", " ").split():
        t = tok.upper()
        if t in ALIAS:
            out |= ALIAS[t]
        elif tok.isalnum() and tok.isupper() and len(tok) > 1 and tok not in NOT_GENES:
            out.add(tok)
    return out


def db_issue(r) -> str:
    """How the database's class for one reviewed member differs from the review ('' when it agrees)."""
    if not r.reviewed or r.verified_target == "unknown":
        return ""
    issues = []
    db = set(str(r.db_target).split(";")) if pd.notna(r.db_target) else set()
    if not db:
        issues.append("target_missing")
    elif r.selectivity == "off-class" or not (symbols(r.verified_target) & db):
        issues.append("target_wrong")
    elif r.selectivity in ("pan", "dual") and len(db) == 1:
        issues.append("selectivity_understated")
    if db and pd.notna(r.verified_action) and pd.notna(r.db_action) and ";" not in str(r.db_action) \
            and (r.verified_action in ACTIVATING) != (r.db_action in ACTIVATING) and r.verified_action != "other":
        issues.append("action_wrong")
    if pd.isna(r.modality) or r.modality == "unknown":
        issues.append("modality_missing")
    elif r.modality_group != r.modality_group_db:
        issues.append("modality_wrong")
    if r.novel_verified is False:
        issues.append("not_novel")
    if (str(r.verified_first_fda_approval)[:10] if pd.notna(r.verified_first_fda_approval) else "") \
            != (str(r.first_approval_date)[:10] if pd.notna(r.first_approval_date) else ""):
        issues.append("fda_date_wrong")
    return ";".join(issues)


def reviewed(m: pd.DataFrame) -> pd.DataFrame:
    """Join the hand review (reviews.csv); a moiety not reviewed keeps the database's fields."""
    rv = pd.read_csv(REVIEWS, dtype={"verified_first_fda_approval": str, "novel_override": object}).drop(columns="drug")
    m = m.merge(rv, on="moiety_id", how="left")
    m["reviewed"] = m.verified_target.notna()
    m["entity"] = m.same_entity_as.fillna(m.moiety_id).astype(int)
    fda = pd.to_datetime(m.verified_first_fda_approval, errors="coerce")
    entry = pd.to_datetime(m.entry)
    novel = pd.Series(fda.isna() | (fda > entry), dtype=object)
    override = m.novel_override.map({"False": False, "True": True, False: False, True: True})
    m["novel_verified"] = override.where(override.notna(), novel).where(m.reviewed, None)
    m["db_issue"] = m.apply(db_issue, axis=1)
    wrong = m.db_issue.str.contains("target_wrong|action_wrong|modality_wrong|not_novel")
    m["disagrees_with_db"] = pd.Series(wrong, dtype=object).where(m.reviewed & m.verified_target.ne("unknown"), None)
    return m


def class_label(target: str, action: str) -> str:
    return ACTION_PHRASE.get(action, "{t} " + str(action)).format(t=target)

def ranked_classes(g: pd.DataFrame) -> pd.DataFrame:
    """Mechanisms of one indication's members, counted across modalities, by program count. Phase is
    reported, never ranked on, so the choice does not depend on whether a mechanism succeeded."""
    return (g.groupby(["c_target", "c_action"])
            .agg(furthest=("furthest_phase_reached", "max"), n=("entity", "nunique"),
                 groups=("c_group", lambda x: ";".join(sorted(set(x.dropna())))),
                 ex=("drug", lambda d: "; ".join(sorted(set(d))[:6])),
                 sel=("selectivity", lambda s: "; ".join(sorted(set(s.dropna())))))
            .reset_index().sort_values(["n", "c_target"], ascending=[False, True]))

def proposed(m: pd.DataFrame, named: pd.DataFrame, current: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The proposed rule over reviewed members (database fields where a member is unreviewed), and the
    members with the mechanism each is counted in. Mechanisms tied on program count each get a tile."""
    m = m.copy()
    m["c_target"] = m.verified_target.fillna(m.db_target)
    m["c_target"] = m.c_target.where(m.selectivity.ne("off-class"), m.c_target + " (off-class)")
    m["c_action"] = m.verified_action.fillna(m.db_action)
    m["c_group"] = m.modality_group.fillna(m.modality_group_db)
    m = m[m.novel_verified.ne(False) & m.c_target.notna() & m.c_target.ne("unknown") & m.selectivity.ne("no target")]
    cur = current.set_index("mondo_id")
    out, chosen = [], []
    for r in named.itertuples():
        g = m[m.mondo_id_named == r.mondo_id]
        ranked = ranked_classes(g)
        ok = ranked[ranked.n >= MIN_PROGRAMS]
        base = {"area": r.area, "mondo_id": r.mondo_id, "label": r.label, "n_programs": int(r.n),
                "share_unresolved": cur.at[r.mondo_id, "share_unresolved"]}
        if not len(ok):
            top = ranked.iloc[0] if len(ranked) else None
            out.append({**base, "class": "no qualifying class", "class_programs": 0, "class_share": 0.0,
                        "class_basis": "proposed_rule", "example_entities": "", "modality_groups": "",
                        "selectivity_note": "", "furthest_phase": None, "tile": 1, "runner_up": "",
                        "reason": f"no mechanism reaches {MIN_PROGRAMS} programs"
                                  + (f"; largest is {class_label(top.c_target, top.c_action)} ({top.n})" if top is not None else "")})
            continue
        winners = ok[ok.n == ok.n.iloc[0]]
        rest = ok[ok.n < ok.n.iloc[0]]
        nxt = rest.iloc[0] if len(rest) else None
        for tile, w in enumerate(winners.itertuples(), 1):
            chosen.append(g[(g.c_target == w.c_target) & (g.c_action == w.c_action)].assign(proposed_rank=1))
            out.append({**base, "class": class_label(w.c_target, w.c_action), "class_programs": int(w.n),
                        "class_share": round(w.n / r.n, 3), "class_basis": "proposed_rule", "example_entities": w.ex,
                        "modality_groups": w.groups, "selectivity_note": w.sel, "furthest_phase": int(w.furthest),
                        "tile": tile,
                        "runner_up": f"{class_label(nxt.c_target, nxt.c_action)} ({nxt.n})" if nxt is not None else "",
                        "reason": f"tied with {len(winners) - 1} other mechanism(s) on {int(w.n)} programs; each gets a tile"
                                  if len(winners) > 1 else ""})
        if nxt is not None:
            chosen.append(g[(g.c_target == nxt.c_target) & (g.c_action == nxt.c_action)].assign(proposed_rank=2))
    return pd.DataFrame(out), pd.concat(chosen)

def current_members(m: pd.DataFrame) -> pd.Series:
    """Whether each member counts toward its indication's class in the committed named_contexts.csv."""
    committed = pd.read_csv(os.path.join(HERE, "lists", "named_contexts.csv")).set_index("mondo_id")["class"]
    want = m.mondo_id_named.map(committed)
    in_class = pd.Series(False, index=m.index)
    for i, r in m.iterrows():
        if pd.notna(r.db_target):
            actions = str(r.db_action).split(";")
            for k, t in enumerate(str(r.db_target).split(";")):
                a = actions[k] if len(actions) > 1 else actions[0]
                in_class[i] |= lists.ACTION_PHRASE.get(a, "{t} " + a).format(t=t) == want[i]
        elif pd.notna(r.chembl_mechanism):
            in_class[i] = r.chembl_mechanism.split(" | ")[0] == want[i]
    return in_class


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    ent, named, progs = cohort()
    current = lists.classes(ent, named)
    current.to_csv(os.path.join(OUT, "current_on_db.csv"), index=False)
    m = reviewed(members(ent, named, progs))
    m["in_current_class"] = current_members(m)
    prop, chosen = proposed(m, named, current)
    rank = chosen.set_index("program_id").proposed_rank
    m["proposed_class_rank"] = m.program_id.map(rank)
    cols = ["mondo_id_named", "indication", "area", "program_id", "program_mondo_id", "moiety_id", "drug", "code_names",
            "db_target", "db_action", "n_primary", "chembl_mechanism", "modality", "modality_group_db", "novel_flag",
            "first_approval_date", "entry_year", "approved_this_indication", "furthest_phase_reached",
            "in_current_class", "proposed_class_rank", "same_entity_as",
            "verified_target", "verified_action", "selectivity", "modality_group", "verified_first_fda_approval",
            "novel_verified", "evidence", "disagrees_with_db", "db_issue", "review_note"]
    m[cols].rename(columns={"mondo_id_named": "mondo_id"}).to_csv(os.path.join(OUT, "class_members.csv"), index=False)
    committed = pd.read_csv(os.path.join(HERE, "lists", "named_contexts.csv")).set_index("mondo_id")
    prop["current_class"] = prop.mondo_id.map(committed["class"])
    prop["changed_from_current"] = prop["class"] != prop.current_class
    prop[list(pd.read_csv(os.path.join(HERE, "lists", "named_contexts.csv"), nrows=0).columns) + ["class_share", "tile", "modality_groups", "selectivity_note",
                                                   "furthest_phase", "changed_from_current", "reason", "runner_up", "current_class"]] \
        .to_csv(os.path.join(OUT, "proposed_contexts.csv"), index=False)
    need = m[(m.in_current_class | m.proposed_class_rank.notna()) & ~m.reviewed]
    print(f"{len(m)} member rows, {int(m.reviewed.sum())} reviewed, {int(m.disagrees_with_db.eq(True).sum())} disagree; "
          f"{len(prop)} tiles over {prop.mondo_id.nunique()} indications, {int(prop['class'].eq('no qualifying class').sum())} blank; "
          f"{int(prop.changed_from_current.sum())} tiles differ from named_contexts.csv; "
          f"{need.moiety_id.nunique()} in-scope moieties unreviewed")
    if len(need):
        print(need[["indication", "moiety_id", "drug", "db_target", "db_action", "modality", "chembl_mechanism"]].to_string())


if __name__ == "__main__":
    main()
