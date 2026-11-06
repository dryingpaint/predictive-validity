"""Draw each named indication's tile(s), its mechanism, from a hand-reviewed class table (decision 12).

    .venv/bin/python analyses/model-system-atlas/class_audit.py          # files only
    .venv/bin/python analyses/model-system-atlas/class_audit.py store    # and the database (migration 133)

Without `store` it only reads. Rebuilds the cohort lists.py uses (novel Phase 2 entrants 2008-2019 in the 71 named
indications, lists/named_indications.csv) on today's database and writes lists/named_contexts.csv,
one row per tracked tile, and under lists/class_audit/:

  class_members.csv     one row per (named indication, novel Phase 2 program): the database's
                        target, action, ChEMBL mechanism, modality, novelty, first FDA approval and
                        furthest phase, joined to the hand review in reviews.csv (verified target,
                        action, selectivity, modality group, first FDA approval, evidence) and a
                        disagrees_with_db flag;
  register.csv          every mechanism in every named indication, counted across modalities,
                        tracked when it has MIN_PROGRAMS programs (named_contexts.csv is the tracked rows);
  AUDIT.md              where the database disagrees with the review, and the rule's result.

reviews.csv is the hand-curated input, one row per moiety (same_entity_as folds a duplicate
moiety into the entity it repeats); a moiety absent from it falls back to the database's fields.

Rule (decision 12). The tile's unit is the mechanism, (verified target, verified action),
counted across modalities; modality only splits the dose and platform-safety sub-strips inside a
tile (`modality_groups` lists them). A non-selective or off-class member carries its own verified
target (e.g. "JAK (pan)"), so it falls into its own mechanism (a dual member whose verified target is
the mechanism's target, such as netarsudil, ROCK plus NET, stays in); a member with no molecular
target (lubricants, barriers, photosensitisers) or an undisclosed one forms none. Members
FDA-approved before their Phase 2 entry are dropped (not novel). Every mechanism of every
indication is registered; one with at least MIN_PROGRAMS distinct entities is tracked, a tile whose
model track record is drafted. Phase is never a criterion, so tracking does not depend on success.
"""
import importlib.util
import os
import sys
import uuid

import pandas as pd
from psycopg2.extras import execute_values

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
from pipeline import llm
from report import frame, section1

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "lists", "class_audit")
REVIEWS = os.path.join(OUT, "reviews.csv")
CONTEXTS = os.path.join(HERE, "lists", "named_contexts.csv")
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
ACTION_PHRASE = {**lists.ACTION_PHRASE, "corrector": "{t} correctors", "potentiator": "{t} potentiators",
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

def register(m: pd.DataFrame, named: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Every mechanism in every named indication (decision 12): one row per indication x mechanism,
    counted across modalities and tracked when it has MIN_PROGRAMS programs; and the members, each
    with its mechanism_key or the reason it is in none."""
    m = m.copy()
    unresolved = (m.db_target.isna() & m.chembl_mechanism.isna()).groupby(m.mondo_id_named).mean()
    m["c_target"] = m.verified_target.fillna(m.db_target)
    m["c_target"] = m.c_target.where(m.selectivity.ne("off-class"), m.c_target + " (off-class)")
    m["c_action"] = m.verified_action.fillna(m.db_action)
    m["c_group"] = m.modality_group.fillna(m.modality_group_db)
    m["excluded"] = None
    m.loc[m.c_target.isna(), "excluded"] = "no_target"
    m.loc[m.c_target.eq("unknown"), "excluded"] = "undisclosed"
    m.loc[m.selectivity.eq("no target"), "excluded"] = "no_target"
    m.loc[m.novel_verified.eq(False), "excluded"] = "not_novel"
    m["mechanism_key"] = (m.c_target + "|" + m.c_action.fillna("")).where(m.excluded.isna())
    n_ind = named.set_index("mondo_id").n
    reg = (m[m.mechanism_key.notna()]
           .groupby(["mondo_id_named", "mechanism_key", "c_target", "c_action"])
           .agg(n=("entity", "nunique"), furthest=("furthest_phase_reached", "max"),
                groups=("c_group", lambda x: ";".join(sorted(set(x.dropna())))),
                ex=("drug", lambda d: "; ".join(sorted(set(d))[:6])),
                sel=("selectivity", lambda x: "; ".join(sorted(set(x.dropna())))))
           .reset_index())
    reg["mechanism"] = [class_label(t, a) for t, a in zip(reg.c_target, reg.c_action)]
    reg["share"] = (reg.n / reg.mondo_id_named.map(n_ind)).round(3)
    reg["tracked"] = reg.n >= MIN_PROGRAMS
    reg["share_unresolved"] = reg.mondo_id_named.map(unresolved).round(2)
    reg = reg.merge(named[["mondo_id", "label", "area", "n"]].rename(columns={"mondo_id": "mondo_id_named", "n": "n_indication"}),
                    on="mondo_id_named")
    reg = reg.sort_values(["area", "label", "n", "mechanism"], ascending=[True, True, False, True])
    m["tracked"] = m.mechanism_key.map(reg.groupby("mechanism_key").tracked.any()).fillna(False) & \
        m.set_index(["mondo_id_named", "mechanism_key"]).index.isin(
            reg[reg.tracked].set_index(["mondo_id_named", "mechanism_key"]).index)
    return reg, m


def _nul(v):
    """None for a missing value, a plain Python scalar otherwise (psycopg2 does not adapt numpy types)."""
    if v is None or (not isinstance(v, (list, str)) and pd.isna(v)):
        return None
    return v.item() if hasattr(v, "item") else v


def store(m: pd.DataFrame, reg: pd.DataFrame, named: pd.DataFrame) -> str:
    """Replace the atlas build tables in one transaction (migration 133); returns the build id."""
    rv = pd.read_csv(REVIEWS, dtype={"verified_first_fda_approval": str, "novel_override": object})
    rv = rv[rv.moiety_id.notna()]
    placed = m[m.mechanism_key.notna()]
    mech = placed.drop_duplicates("mechanism_key")[["mechanism_key", "c_target", "c_action"]]
    build_id = str(uuid.uuid4())
    with llm.connect() as conn, conn.cursor() as cur:
        method = llm.record_method(
            cur, "atlas_class_register@v1", "Atlas class register",
            "Every mechanism (verified target, action; across modalities) of every named indication, from the "
            "novel Phase 2 entrants of 2008-2019 and a hand review of the entities; tracked when it has "
            "min_programs distinct entities (decision 12).",
            ["preclin.dev_program", "preclin.moiety_target", "preclin.chembl_mechanism",
             "analyses/model-system-atlas/lists/class_audit/reviews.csv"],
            {"window": [str(w) for w in lists.WINDOW], "phase": lists.PHASE, "min_programs": MIN_PROGRAMS})
        for t in ("atlas_member", "atlas_mechanism", "atlas_moiety_review", "atlas_indication"):
            cur.execute(f"DELETE FROM preclin.{t}")
        cur.execute("""INSERT INTO preclin.atlas_build (build_id, code_commit, snapshot, min_programs, n_members,
                                                        n_register, n_tracked, method_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (build_id, llm.git_commit(), frame.snapshot(), MIN_PROGRAMS, len(m), len(reg),
                     int(reg.tracked.sum()), method))
        execute_values(cur, """INSERT INTO preclin.atlas_indication (mondo_id, label, area, area_rank, n_programs,
                                                                     merged_from, build_id) VALUES %s""",
                       [(r.mondo_id, r.label, r.area, int(r.rank), int(r.n),
                         [x for x in str(r.merged_from).split(";") if x and x != "nan"], build_id)
                        for r in named.itertuples()])
        execute_values(cur, """INSERT INTO preclin.atlas_moiety_review (moiety_id, same_entity_as, target_label, action,
                                   selectivity, modality_group, first_fda_approval, novel_override, evidence, note,
                                   build_id) VALUES %s""",
                       [(int(r.moiety_id), _nul(r.same_entity_as) and int(r.same_entity_as), r.verified_target,
                         _nul(r.verified_action), _nul(r.selectivity), _nul(r.modality_group),
                         _nul(r.verified_first_fda_approval), {"True": True, "False": False}.get(str(r.novel_override)),
                         r.evidence, _nul(r.review_note), build_id) for r in rv.itertuples()])
        execute_values(cur, """INSERT INTO preclin.atlas_mechanism (mechanism_key, target_label, action, label, build_id)
                               VALUES %s""",
                       [(r.mechanism_key, r.c_target, r.c_action, class_label(r.c_target, r.c_action), build_id)
                        for r in mech.itertuples()])
        execute_values(cur, """INSERT INTO preclin.atlas_member (moiety_id, mondo_id, program_mondo_id, entity_id,
                                   mechanism_key, excluded, modality_group, entry_date, furthest_phase, reviewed,
                                   build_id) VALUES %s""",
                       [(int(r.moiety_id), r.mondo_id_named, r.program_mondo_id, int(r.entity), _nul(r.mechanism_key),
                         _nul(r.excluded), r.c_group, pd.Timestamp(r.entry).date(), _nul(r.furthest_phase_reached),
                         bool(r.reviewed), build_id) for r in m.itertuples()], page_size=2000)
        cur.execute("SELECT count(*), count(*) FILTER (WHERE tracked) FROM preclin.atlas_register")
        n_reg, n_tracked = cur.fetchone()
        if (n_reg, n_tracked) != (len(reg), int(reg.tracked.sum())):
            raise RuntimeError(f"register view gives {n_reg}/{n_tracked}, the draw {len(reg)}/{int(reg.tracked.sum())}")
        conn.commit()
    print(f"stored build {build_id}: {len(named)} indications, {len(rv)} reviews, {len(mech)} mechanisms, "
          f"{len(m)} members; register {n_reg}, tracked {n_tracked}")
    return build_id


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    ent, named, progs = cohort()
    m = reviewed(members(ent, named, progs))
    reg, m = register(m, named)
    cols = ["mondo_id_named", "indication", "area", "program_id", "program_mondo_id", "moiety_id", "drug", "code_names",
            "db_target", "db_action", "n_primary", "chembl_mechanism", "modality", "modality_group_db", "novel_flag",
            "first_approval_date", "entry_year", "approved_this_indication", "furthest_phase_reached",
            "mechanism_key", "excluded", "tracked", "same_entity_as",
            "verified_target", "verified_action", "selectivity", "modality_group", "verified_first_fda_approval",
            "novel_verified", "evidence", "disagrees_with_db", "db_issue", "review_note"]
    m[cols].rename(columns={"mondo_id_named": "mondo_id"}).to_csv(os.path.join(OUT, "class_members.csv"), index=False)
    out = reg.rename(columns={"mondo_id_named": "mondo_id", "n_indication": "n_programs", "n": "class_programs",
                              "mechanism": "class", "groups": "modality_groups", "sel": "selectivity_note",
                              "furthest": "furthest_phase", "ex": "example_entities", "share": "class_share"})
    keep = ["area", "mondo_id", "label", "n_programs", "mechanism_key", "class", "class_programs", "class_share",
            "modality_groups", "selectivity_note", "furthest_phase", "share_unresolved", "example_entities", "tracked"]
    out[keep].to_csv(os.path.join(OUT, "register.csv"), index=False)
    out[out.tracked][[k for k in keep if k != "tracked"]].to_csv(CONTEXTS, index=False)
    need = m[m.tracked & ~m.reviewed]
    t = out[out.tracked]
    print(f"{len(m)} member rows, {int(m.reviewed.sum())} reviewed, {int(m.disagrees_with_db.eq(True).sum())} disagree; "
          f"register {len(out)} indication x mechanism rows; tracked {len(t)} tiles in {t.mondo_id.nunique()} of "
          f"{len(named)} indications; "
          f"{need.moiety_id.nunique()} in-scope moieties unreviewed")
    if len(need):
        print(need[["indication", "moiety_id", "drug", "db_target", "db_action", "modality", "chembl_mechanism"]].to_string())
    if sys.argv[1:] == ["store"]:
        if len(need):
            raise SystemExit("not stored: in-scope entities are unreviewed")
        store(m, reg, named)

if __name__ == "__main__":
    main()
