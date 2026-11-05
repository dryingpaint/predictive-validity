"""Flat status x fact-field matrix over drafts/*.json + their checker verdicts.

    .venv/bin/python analyses/model-system-atlas/drafts/matrix.py

Writes drafts/matrix_entries.csv (one row per strip entry, draft and checked status side by
side) and drafts/matrix_cells.csv (one row per context x question, latest status), then prints
the summary tables used for the #76 write-up. Also writes drafts/matrix_models.csv, the per-model
record of decision 6: one row per context x question x model, where a model that failed stays failed
and `superseded_by` names the model that took the cell over. Read-only over drafts/; never touches contexts/.
"""
import csv
import glob
import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS = ["engagement", "dose", "efficacy", "safety"]
STATUSES = ["same", "other", "neg", "contra", "retro", "untested"]
FACTS = ["subjects", "comparison_stated", "product_in_model", "model_filed", "magnitude",
         "source_calls_it", "confidence", "registry_date", "epub_year", "print_year",
         "model_first_use_year", "population", "source_tier", "model_change", "patient_signal_reversed",
         "retrodiction"]


def load():
    rows = []
    for path in sorted(glob.glob(os.path.join(HERE, "*.json"))):
        if path.endswith(".check.json"):
            continue
        draft = json.load(open(path))
        cp = path[:-5] + ".check.json"
        check = json.load(open(cp)) if os.path.exists(cp) else None
        rows.append((os.path.basename(path)[:-5], draft, check))
    return rows


def index_base(check):
    """Checkers were told to number from 1; nine of them numbered from 0. Honour `index_base` if
    declared, else infer 0 when any entry carries index 0."""
    if check is None:
        return 1
    if check.get("index_base") is not None:
        return int(check["index_base"])
    return 0 if any(e.get("index") == 0 for e in check.get("entries", [])) else 1


def verdict_map(check):
    m = {}
    base = index_base(check)
    for e in (check or {}).get("entries", []):
        if e.get("index") is None:
            continue
        m[(e["cell"], int(e["index"]) - base + 1)] = e  # normalised to 1-based
    return m


def model_record(entries: list[dict]) -> list[dict]:
    """One row per context x question x model over the checked statuses, in strip order."""
    out = []
    by_cell = defaultdict(list)
    for r in entries:
        if not r["dropped"]:
            by_cell[(r["context"], r["question"])].append(r)
    for (cid, q), strip in by_cell.items():
        order = list(dict.fromkeys(r["model"] for r in strip))
        for k, m in enumerate(order):
            rs = [r for r in strip if r["model"] == m]
            sts = [r["status_checked"] for r in rs]
            out.append({
                "context": cid, "question": q, "model": m,
                "first_year": rs[0]["year_checked"], "last_year": rs[-1]["year_checked"],
                "statuses": ">".join(sts), "ever_contra": "contra" in sts,
                "record": "contra" if "contra" in sts and not any(r.get("patient_signal_reversed") for r in rs) else sts[-1],
                "superseded_by": order[k + 1] if k + 1 < len(order) else None,
            })
    return out


def main():
    rows = load()
    entries, cells = [], []
    for cid, d, c in rows:
        vm = verdict_map(c)
        for q in QUESTIONS:
            strip = d["cells"].get(q, [])
            latest_draft = latest_checked = None
            for i, e in enumerate(strip, start=1):
                v = vm.get((q, i), {})
                checked_status = e["status"]
                checked_year = e.get("year")
                dropped = False
                if v.get("verdict") == "corrected":
                    if str(v.get("proposed_status", "")).startswith("drop"):
                        dropped = True  # checker removed the entry; cell dated by the previous one
                    else:
                        checked_status = v.get("proposed_status") or checked_status
                        checked_year = v.get("proposed_year") or checked_year
                rec = {
                    "context": cid, "area": d.get("area"), "disease": d.get("disease"),
                    "mechanism": d.get("mechanism"), "question": q, "index": i,
                    "year": e.get("year"), "status_draft": e["status"],
                    "checked": c is not None, "verdict": v.get("verdict"),
                    "status_checked": "dropped" if dropped else checked_status,
                    "year_checked": checked_year, "dropped": dropped,
                    "quote_found": v.get("quote_found"), "source_resolves": v.get("source_resolves"),
                    "model": e.get("model_id") or e.get("model"), "srcLabel": e.get("srcLabel"), "src": e.get("src"),
                }
                for f in FACTS:
                    rec[f] = e.get(f)
                conf = str(e.get("confidence") or "").strip().lower()
                rec["confidence"] = next((k for k in ("high", "medium", "low") if conf.startswith(k)), None)
                rec["confidence_note"] = e.get("confidence") if rec["confidence"] != conf else None
                entries.append(rec)
                latest_draft = (e.get("year"), e["status"])
                if not dropped:
                    latest_checked = (checked_year, checked_status)
            cells.append({
                "context": cid, "area": d.get("area"), "disease": d.get("disease"),
                "mechanism": d.get("mechanism"), "question": q, "n_entries": len(strip),
                "checked": c is not None,
                "latest_year_draft": latest_draft[0] if latest_draft else None,
                "status_draft": latest_draft[1] if latest_draft else None,
                "latest_year_checked": latest_checked[0] if latest_checked else None,
                "status_checked": latest_checked[1] if latest_checked else None,
                "any_comparison_stated": any(e.get("comparison_stated") for e in strip),
                "latest_comparison_stated": strip[-1].get("comparison_stated") if strip else None,
                "latest_subjects": strip[-1].get("subjects") if strip else None,
                "latest_product_in_model": strip[-1].get("product_in_model") if strip else None,
                "latest_magnitude": strip[-1].get("magnitude") if strip else None,
                "overall": (c or {}).get("overall"),
            })
    models = model_record(entries)
    for name, data in (("matrix_entries.csv", entries), ("matrix_cells.csv", cells), ("matrix_models.csv", models)):
        with open(os.path.join(HERE, name), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader(); w.writerows(data)

    n_ctx = len(rows); n_chk = sum(1 for _, _, c in rows if c)
    print(f"contexts: {n_ctx} drafted, {n_chk} checked; entries: {len(entries)}; cells: {len(cells)}\n")

    def table(title, key, col="status_checked", pool=cells):
        groups = defaultdict(Counter)
        for r in pool:
            groups[key(r)][r[col] or "none"] += 1
        print(title)
        print("| " + " | ".join(["group"] + STATUSES + ["n"]) + " |")
        print("|" + "---|" * (len(STATUSES) + 2))
        for g in sorted(groups, key=lambda k: str(k)):
            cnt = groups[g]; n = sum(cnt.values())
            print("| " + " | ".join([str(g)] + [str(cnt.get(s, 0)) for s in STATUSES] + [str(n)]) + " |")
        print()

    chk = [r for r in cells if r["checked"]]
    table("Latest status by question (checked contexts, checker-corrected)", lambda r: r["question"], pool=chk)
    table("Latest status by question (checked contexts, drafter's call)", lambda r: r["question"], col="status_draft", pool=chk)
    table("Latest status by area (checked, corrected)", lambda r: r["area"], pool=chk)
    table("Latest status by comparison_stated on the latest entry (checked, corrected)",
          lambda r: f"stated={r['latest_comparison_stated']}", pool=chk)
    table("Latest status by subjects of the latest entry (checked, corrected)",
          lambda r: r["latest_subjects"], pool=chk)
    table("Latest status by product_in_model (checked, corrected)",
          lambda r: r["latest_product_in_model"], pool=chk)
    table("Latest status by magnitude bin (checked, corrected)", lambda r: r["latest_magnitude"], pool=chk)

    flips = Counter((r["status_draft"], r["status_checked"]) for r in chk if r["status_draft"] != r["status_checked"])
    print("Checker flips of the latest cell status (draft -> checked)")
    for (a, b), n in flips.most_common():
        print(f"  {a:9s} -> {b:9s} {n}")
    tot = len(chk); nflip = sum(flips.values())
    print(f"  {nflip}/{tot} cells flipped ({100*nflip/tot:.0f}%)\n")
    ev = Counter(r["verdict"] for r in entries if r["checked"])
    print("Entry-level verdicts:", dict(ev))
    print("Checker overall:", dict(Counter(r["overall"] for r in chk if r["question"] == "efficacy")))


if __name__ == "__main__":
    main()
