"""Build the report: every analysis, then the figures, then REPORT.md, in one process.

    python -m report

Every query reads one snapshot of the database (report.frame.hold_snapshot), so the build is
consistent while other sessions write. The build fails when it read more than one snapshot (a
dropped link) or when a placeholder is left unfilled; everything else is written first.
"""
from __future__ import annotations

import sys
import time

from report import (attribution, disease_match, evidence_analysis, figures, frame, methods, quality, render, section1,
                    section2, section3, stop_causes)

# quality reads only the database and audit files, so it runs first with the other large reads
STEPS = [quality, section1, section2, section3, evidence_analysis, attribution, stop_causes, methods, figures, render]


def load_tables() -> None:
    """Read the large tables the steps share while the held snapshot is young: a query against a snapshot held
    for minutes, while other sessions write, runs several times slower than the same query on a fresh one."""
    for load in (frame.programs, frame.program_trials, frame.trial_outcomes, frame.drug_assays,
                 frame.common_essentials, disease_match.mondo_tables, section2.target_tables, section3.evidence_index):
        load()


def main() -> None:
    frame.hold_snapshot()
    start = time.monotonic()
    load_tables()
    print(f"[report] load_tables {time.monotonic() - start:.0f}s", flush=True)
    problems = []
    for step in STEPS:
        start = time.monotonic()
        step.main()
        print(f"[report] {step.__name__} {time.monotonic() - start:.0f}s", flush=True)
    if frame.snapshots_read > 1:
        problems.append(f"the build read {frame.snapshots_read} database snapshots (the link dropped); run it again")
    for p in problems:
        print(f"[report] {p}", file=sys.stderr)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
