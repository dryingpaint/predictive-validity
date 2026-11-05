"""Build the report: every analysis, then the figures, then REPORT.md, in one process.

    python -m report

Every query reads one snapshot of the database (report.frame.hold_snapshot), so the build is
consistent while other sessions write. The build fails when it read more than one snapshot (a
dropped link) or when a placeholder is left unfilled; everything else is written first.
"""
from __future__ import annotations

import sys
import time

from report import (attribution, evidence_analysis, figures, frame, methods, quality, render, section1, section2,
                    section3, stop_causes)

STEPS = [section1, section2, section3, evidence_analysis, attribution, stop_causes, methods, quality, figures, render]


def main() -> None:
    frame.hold_snapshot()
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
