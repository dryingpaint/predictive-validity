"""Build the report: every analysis, then the figures, then REPORT.md, in one process.

    python -m report

Every query reads one snapshot of the database (report.frame.hold_snapshot), so the build is
consistent while other sessions write. The build fails when it read more than one snapshot (a
dropped link), when a placeholder is left unfilled, or when Section 3 picked cases its audit does
not cover (`python -m report.cases pending`); everything else is written first.
"""
from __future__ import annotations

import json
import os
import sys
import time

from report import (attribution, figures, frame, methods, quality, render, section1, section2, section3,
                    stop_causes)

STEPS = [section1, section2, section3, attribution, stop_causes, methods, quality, figures, render]


def main() -> None:
    frame.hold_snapshot()
    problems = []
    for step in STEPS:
        start = time.monotonic()
        step.main()
        print(f"[report] {step.__name__} {time.monotonic() - start:.0f}s", flush=True)
    if frame.snapshots_read > 1:
        problems.append(f"the build read {frame.snapshots_read} database snapshots (the link dropped); run it again")
    pending = json.load(open(os.path.join(section3.OUT, "numbers.json")))["case_audit"]["pending"]
    if pending:
        problems.append(f"{len(pending)} Section 3 cases need verification (python -m report.cases pending)")
    for p in problems:
        print(f"[report] {p}", file=sys.stderr)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
