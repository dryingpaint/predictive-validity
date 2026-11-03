"""Layer 1 bookkeeping: which labelled programs still need their engagement readout extracted, batches for
the extractor, the merge back, and the vocabulary.

    .venv/bin/python analyses/engagement-readouts/extract.py todo [--batch 80]   # batches/todo_NN.csv
    .venv/bin/python analyses/engagement-readouts/extract.py merge               # batches/done_NN.csv -> readouts.csv
    .venv/bin/python analyses/engagement-readouts/extract.py vocab               # vocabulary.csv + counts
    .venv/bin/python analyses/engagement-readouts/extract.py scope               # step3_scope.csv

Rows are keyed by content_sha (pull.py), so a re-pull after the labels change re-queues only the rows
whose rationale changed. Verdicts with no human data are never queued.
"""
import argparse
import glob
import os
import re
from datetime import date

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = os.path.join(HERE, "labels.csv")
READOUTS = os.path.join(HERE, "readouts.csv")
BATCHES = os.path.join(HERE, "batches")
VOCAB = os.path.join(HERE, "vocabulary.csv")
QUEUED = ("adequate", "inferred_adequate", "inadequate")
INPUT_COLS = ["content_sha", "key", "drug", "modality", "targets", "actions", "mondo_id", "disease", "phase",
              "primary_code", "exposure", "engagement", "pathway", "engagement_in_disease",
              "engagement_before_index", "rationale", "sources"]
OUT_COLS = ["content_sha", "key", "readout", "readout_kind", "matrix", "subjects", "inference_basis",
            "specific_to_target", "readout_canonical", "quote", "note"]
ENUM = {"readout_kind": {"occupancy", "target_product", "downstream_marker", "clinical_response", "exposure_only", "none"},
        "matrix": {"blood", "tissue", "imaging", "physiology", "csf", "urine", "other", ""},
        "subjects": {"patients_this_disease", "patients_other_disease", "healthy_volunteers", "mixed", "unknown"},
        "inference_basis": {"measured", "other_disease", "class", "none"},
        "specific_to_target": {"yes", "no", "unsure"}}


def canonical(name: str) -> str:
    """`<TARGET>:<readout>` with the target part reduced to [A-Z0-9_-] and the readout part to [a-z0-9_]."""
    if not name or ":" not in name:
        return name
    target, readout = name.split(":", 1)
    target = re.sub(r"[^A-Z0-9_-]", "", target.upper())
    readout = re.sub(r"[^a-z0-9_]", "_", readout.lower()).strip("_")
    return f"{target}:{readout}"


GREEK = str.maketrans({"α": "a", "β": "b", "γ": "g", "δ": "d", "κ": "k", "µ": "u", "μ": "u", "ω": "w", "σ": "s", "τ": "t"})


def _norm(t: str) -> str:
    """Lower-case alphanumerics with citations and Greek letters normalised, so a quote the extractor typed with
    'IFN-b' or 'ug/ml' still matches the rationale's 'IFN-β' or 'µg/ml'."""
    t = re.sub(r"\((?:PMID|NCT|doi)[^)]*\)?", "", t.translate(GREEK))
    t = re.sub(r"(?i)\b(alpha|beta|gamma|delta|kappa)\b", lambda m: m.group(1)[0].lower(), t)
    t = re.sub(r"(?i)(?<=[A-Za-z0-9-])(alpha|beta|gamma|delta|kappa)(?=\d|\b)", lambda m: m.group(1)[0].lower(), t)
    t = re.sub(r"[^a-z0-9]+", " ", t.lower())
    return t.strip()


def quote_in(quote: str, rationale: str) -> bool:
    """Every fragment of the quote (split on an ellipsis) with four or more words occurs in the rationale, both
    normalised to lower-case alphanumerics with citations removed. A quote lifted from another row fails."""
    r = _norm(rationale)
    frags = [f for f in re.split(r"\.\.\.|…", quote) if len(f.split()) >= 4]
    return all(_norm(f) in r for f in frags) if frags else True


def cache() -> pd.DataFrame:
    if os.path.exists(READOUTS):
        return pd.read_csv(READOUTS, dtype=str).fillna("")
    return pd.DataFrame(columns=OUT_COLS + ["extracted_by", "extracted_at"])


def todo(batch: int) -> None:
    labels = pd.read_csv(LABELS, dtype=str).fillna("")
    done = set(cache().content_sha)
    q = labels[labels.engagement.isin(QUEUED) & ~labels.content_sha.isin(done)]
    os.makedirs(BATCHES, exist_ok=True)
    for f in glob.glob(os.path.join(BATCHES, "todo_*.csv")):
        os.remove(f)
    vocab = sorted(set(cache().readout_canonical) - {""})
    with open(os.path.join(BATCHES, "vocabulary.txt"), "w") as f:
        f.write("\n".join(vocab))  # the names the extractor should reuse
    for i in range(0, len(q), batch):
        q.iloc[i:i + batch][INPUT_COLS].to_csv(os.path.join(BATCHES, f"todo_{i // batch + 1:02d}.csv"), index=False)
    print(f"{len(labels)} labelled, {int(labels.engagement.isin(QUEUED).sum())} queueable, {len(done)} cached, "
          f"{len(q)} to extract in {(len(q) + batch - 1) // batch} batches; vocabulary {len(vocab)} names")


def merge() -> None:
    labels = pd.read_csv(LABELS, dtype=str).fillna("").set_index("content_sha")
    old = cache()
    new = []
    for f in sorted(glob.glob(os.path.join(BATCHES, "done_*.csv"))):
        d = pd.read_csv(f, dtype=str).fillna("")
        missing = [c for c in OUT_COLS if c not in d.columns]
        if missing:
            raise SystemExit(f"{f}: missing columns {missing}")
        bad = {c: sorted(set(d[c]) - v) for c, v in ENUM.items() if set(d[c]) - v}
        if bad:
            raise SystemExit(f"{f}: values outside the vocabulary {bad}")
        unknown = d[~d.content_sha.isin(labels.index)]
        if len(unknown):
            raise SystemExit(f"{f}: {len(unknown)} rows whose content_sha is not in labels.csv")
        todo_f = f.replace("done_", "todo_")
        if os.path.exists(todo_f):
            want = pd.read_csv(todo_f, dtype=str, usecols=["content_sha"]).content_sha.tolist()
            if d.content_sha.tolist() != want:
                raise SystemExit(f"{f}: content_sha sequence differs from {os.path.basename(todo_f)}")
        bad_quotes = [sha for sha, q in zip(d.content_sha, d.quote) if q and not quote_in(q, labels.rationale.get(sha, ""))]
        if bad_quotes:
            print(f"{os.path.basename(f)}: {len(bad_quotes)} quotes not found in their own rationale: {bad_quotes[:3]}")
        d = d[OUT_COLS].copy()
        d["readout_canonical"] = d.readout_canonical.map(canonical)
        d["extracted_by"], d["extracted_at"] = os.path.basename(f), date.today().isoformat()
        new.append(d)
    if not new:
        print("no done_*.csv batches")
        return
    merged = pd.concat([old] + new).drop_duplicates("content_sha", keep="last")
    merged.to_csv(READOUTS, index=False)
    print(f"readouts.csv: {len(old)} -> {len(merged)} rows")


def vocab() -> None:
    """One kind per canonical readout name, across all rows: vocabulary.csv carries the majority kind, a conflict
    flag where batches disagreed, and a kind_final column for hand decisions that survive re-runs. The
    crosstabs use kind_final where set, else the majority."""
    r = cache()
    if r.empty:
        print("readouts.csv is empty")
        return
    labels = pd.read_csv(LABELS, dtype=str).fillna("")
    d = r.merge(labels[["content_sha", "engagement", "primary_code", "targets", "drug"]], on="content_sha", how="left")
    hand = {}
    if os.path.exists(VOCAB):
        v0 = pd.read_csv(VOCAB, dtype=str).fillna("")
        hand = dict(zip(v0.readout_canonical, v0.kind_final))
    rows = []
    for name, g in d[d.readout_canonical != ""].groupby("readout_canonical"):
        kinds = g.readout_kind.value_counts()
        spec = g.specific_to_target.value_counts()
        rows.append({"readout_canonical": name, "n": len(g),
                     "kinds": ";".join(f"{k}:{n}" for k, n in kinds.items()),
                     "kind_majority": kinds.index[0], "kind_final": hand.get(name, ""),
                     "conflict": len(kinds) > 1, "specific_majority": spec.index[0],
                     "example_readout": g.readout.iloc[0], "drugs": ";".join(sorted(set(g.drug))[:6])})
    v = pd.DataFrame(rows).sort_values(["conflict", "n"], ascending=[False, False])
    v.to_csv(VOCAB, index=False)
    eff = {x.readout_canonical: (x.kind_final or x.kind_majority) for x in v.itertuples()}
    d["kind"] = [eff.get(c, k) for c, k in zip(d.readout_canonical, d.readout_kind)]
    print(f"vocabulary.csv: {len(v)} canonical names, {int(v.conflict.sum())} with conflicting kinds, "
          f"{int((v.kind_final != '').sum())} set by hand")
    print("\nkind x engagement verdict (vocabulary-harmonised)\n", pd.crosstab(d.kind, d.engagement, margins=True))
    print("\ninference_basis x engagement verdict\n", pd.crosstab(d.inference_basis, d.engagement, margins=True))
    print("\nspecific_to_target among measured:", d[d.inference_basis == "measured"].specific_to_target.value_counts().to_dict())
    print(f"\ntop 25 canonical names:\n{v.sort_values('n', ascending=False).head(25)[['readout_canonical', 'n', 'kind_majority', 'conflict']].to_string(index=False)}")


def scope() -> None:
    """Step 3 scope: the measured-engaged programs whose readout does not by itself show the target was hit
    (a downstream marker, a non-specific or unsure target product, no readout), written to step3_scope.csv
    with their canonical names, so the anchor research starts from a file."""
    r = cache()
    labels = pd.read_csv(LABELS, dtype=str).fillna("")
    d = r.merge(labels[["content_sha", "key", "drug", "targets", "disease", "engagement", "primary_code",
                        "engagement_in_disease", "engagement_before_index"]], on=["content_sha", "key"])
    a = d[d.engagement == "adequate"]
    needs = a[(a.readout_kind == "downstream_marker")
              | ((a.readout_kind == "target_product") & (a.specific_to_target != "yes"))
              | ((a.readout_kind == "occupancy") & (a.specific_to_target == "no"))
              | a.readout_kind.isin(["none", "exposure_only", "clinical_response"])]
    needs = needs.sort_values(["targets", "readout_canonical"])
    needs.to_csv(os.path.join(HERE, "step3_scope.csv"), index=False)
    fam = needs[needs.readout_canonical != ""].readout_canonical
    print(f"step3_scope.csv: {len(needs)} of {len(a)} measured-engaged programs need an anchor; "
          f"{fam.nunique()} canonical names over {needs.targets.str.split(';').str[0].replace('', 'no target').nunique()} first targets; "
          f"{int((needs.targets == '').sum())} without a DB target")
    print(needs.readout_kind.value_counts().to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["todo", "merge", "vocab", "scope"])
    ap.add_argument("--batch", type=int, default=80)
    a = ap.parse_args()
    {"todo": lambda: todo(a.batch), "merge": merge, "vocab": vocab, "scope": scope}[a.cmd]()
