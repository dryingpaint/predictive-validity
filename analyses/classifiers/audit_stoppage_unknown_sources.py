"""Freeze and summarize the source-retrieval backlog for stoppage rescoring."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Iterable


TARGET_SCIENTIFIC_OUTCOMES = {"not_efficacy_evaluable", "unknown"}


def read_jsonl(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: {exc}") from exc


def enrolled_or_unknown(registry: dict) -> bool:
    enrollment = (registry.get("enrollment") or {}).get("count")
    return enrollment is None or int(enrollment) > 0


def freeze(args: argparse.Namespace) -> None:
    results = {row["nct_id"]: row for row in read_jsonl(args.results)}
    records: list[dict] = []
    for dossier in read_jsonl(args.dossiers):
        nct_id = dossier["nct_id"]
        result = results.get(nct_id)
        if result is None:
            raise ValueError(f"Missing rescore result for {nct_id}")
        registry = dossier["registry"]
        if result["termination_driver"] != "unknown":
            continue
        if result["scientific_outcome"] not in TARGET_SCIENTIFIC_OUTCOMES:
            continue
        if registry.get("has_results") or dossier.get("publications"):
            continue
        if not enrolled_or_unknown(registry):
            continue

        enrollment = (registry.get("enrollment") or {}).get("count")
        records.append({
            "nct_id": nct_id,
            "scientific_outcome": result["scientific_outcome"],
            "study_execution": result["study_execution"],
            "termination_driver": result["termination_driver"],
            "confidence": result["confidence"],
            "overall_status": registry.get("overall_status"),
            "why_stopped": registry.get("why_stopped"),
            "phases": registry.get("phases") or [],
            "enrollment": enrollment,
            "enrollment_type": (registry.get("enrollment") or {}).get("type"),
            "lead_sponsor": (registry.get("lead_sponsor") or {}).get("name"),
            "conditions": registry.get("conditions") or [],
            "intervention_names": [
                item.get("name") for item in registry.get("interventions") or []
                if item.get("name")
            ],
            "title": registry.get("title") or registry.get("brief_title"),
            "registry_source_document_id": dossier["source_inputs"][0]["source_document_id"],
            "original_dossier_sha256": dossier["dossier_sha256"],
        })

    records.sort(key=lambda row: row["nct_id"])
    if args.expected_count is not None and len(records) != args.expected_count:
        raise ValueError(f"Expected {args.expected_count} rows, found {len(records)}")
    if len({row["nct_id"] for row in records}) != len(records):
        raise ValueError("Duplicate NCT ids in frozen backlog")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    args.ids_out.parent.mkdir(parents=True, exist_ok=True)
    args.ids_out.write_text("".join(f"{row['nct_id']}\n" for row in records), encoding="utf-8")

    by_outcome = Counter(row["scientific_outcome"] for row in records)
    by_phase = Counter(
        phase for row in records for phase in (row["phases"] or ["NO_PHASE"])
    )
    summary = {
        "cohort_count": len(records),
        "unique_nct_ids": len({row["nct_id"] for row in records}),
        "selection": {
            "termination_driver": "unknown",
            "scientific_outcome": sorted(TARGET_SCIENTIFIC_OUTCOMES),
            "registry_has_results": False,
            "linked_publication_count": 0,
            "enrollment": "greater than zero or missing",
        },
        "scientific_outcome_counts": dict(sorted(by_outcome.items())),
        "phase_counts": dict(sorted(by_phase.items())),
        "inputs": {
            "dossiers": str(args.dossiers),
            "results": str(args.results),
        },
    }
    summary_path = args.out.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dossiers", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ids-out", type=Path, required=True)
    parser.add_argument("--expected-count", type=int)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> None:
    freeze(parse_args(argv))


if __name__ == "__main__":
    main()
