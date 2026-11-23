"""Build the report: every analysis, then the figures, then REPORT.md, in one process.

    python -m report                     # every step
    python -m report evidence_analysis   # that step and every step that uses it, in build order

Every query reads one snapshot of the database (report.frame.hold_snapshot), so the build is
consistent while other sessions write. The build fails when it read more than one snapshot (a
dropped link) or when a placeholder is left unfilled; everything else is written first.

Each step that writes report/output/<step>/ copies it to CACHE when it finishes. A build of named steps
reads the other steps' outputs from report/output/, seeding any that are missing from CACHE, so a fresh
worktree can redraw a figure or rerun one analysis without the full build. Seeded outputs come from the
last build of that step on this machine, on whatever commit and database snapshot it ran; the build
prints both.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

from report import (attribution, disease_match, evidence_analysis, evidence_facts, failure_modes, figures, frame,
                    methods, quality, render, section1, section2, section3, stop_causes, target_origin)

# quality reads only the database and audit files, so it runs first with the other large reads
STEPS = [quality, section1, section2, section3, evidence_analysis, attribution, stop_causes, failure_modes, target_origin,
         methods, figures, render]
# step -> the steps whose outputs it reads or whose code it imports: it reruns whenever one of them does
USES = {
    quality: (), section1: (), section2: (section1,), section3: (section1,),
    evidence_analysis: (section1, section2, section3, stop_causes), attribution: (section1, section3),
    stop_causes: (section3,), failure_modes: (evidence_analysis, stop_causes, section3),
    target_origin: (evidence_analysis, stop_causes, section3, failure_modes), methods: (stop_causes, attribution),
    figures: (section1, section2, section3, evidence_analysis, attribution, stop_causes, target_origin, render),
    render: (quality, section1, section2, section3, evidence_analysis, attribution, stop_causes, failure_modes,
             target_origin),
}
QUERIES_DATABASE = (quality, section1, section2, section3, evidence_analysis, attribution, stop_causes, failure_modes,
                    target_origin)
OUTPUT = os.path.join(frame.REPO, "report", "output")
CACHE = os.path.expanduser("~/.cache/predictive-validity/report-output")
MANIFEST = "_build.json"  # in each cached step directory: when, on which commit and snapshot it was built


def name(step) -> str:
    return step.__name__.rsplit(".", 1)[-1]


def selected(names: list[str]) -> list:
    """The named steps and every step that uses one of them, directly or through another, in build order; every
    step when no name is given."""
    by_name = {name(s): s for s in STEPS}
    if unknown := [n for n in names if n not in by_name]:
        raise SystemExit(f"unknown step {', '.join(unknown)}; steps: {', '.join(by_name)}")
    run = {by_name[n] for n in names} or set(STEPS)
    while grown := {s for s in STEPS if s not in run and run & set(USES[s])}:
        run |= grown
    return [s for s in STEPS if s in run]


def seed(run: list) -> None:
    """Copy from CACHE the outputs of every step not run whose report/output/<step>/ is missing."""
    for step in (s for s in QUERIES_DATABASE if s not in run):
        here, cached = os.path.join(OUTPUT, name(step)), os.path.join(CACHE, name(step))
        if os.path.isdir(here):
            continue
        if not os.path.isdir(cached):
            raise SystemExit(f"no outputs of {name(step)} here or in {CACHE}: run it too, or the full build")
        shutil.copytree(cached, here)
        m = json.load(open(os.path.join(cached, MANIFEST)))
        print(f"[report] {name(step)} seeded from the cache: built {m['built_at']} on {m['commit']} ({m['branch']}), "
              f"snapshot {m['snapshot']}", flush=True)


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", frame.REPO, *args], capture_output=True, text=True).stdout.strip()


def cache(step) -> None:
    """Replace the step's cached outputs with the ones it just wrote."""
    here = os.path.join(OUTPUT, name(step))
    if not os.path.isdir(here):
        return
    tmp = os.path.join(CACHE, f".{name(step)}.{os.getpid()}")
    shutil.copytree(here, tmp)
    with open(os.path.join(tmp, MANIFEST), "w") as f:
        json.dump({"built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "commit": git("rev-parse", "--short", "HEAD") + ("+dirty" if git("status", "--porcelain") else ""),
                   "branch": git("rev-parse", "--abbrev-ref", "HEAD"), "snapshot": str(frame.snapshot())}, f)
    shutil.rmtree(os.path.join(CACHE, name(step)), ignore_errors=True)
    os.replace(tmp, os.path.join(CACHE, name(step)))


def load_tables() -> None:
    """Read the large tables the steps share while the held snapshot is young: a query against a snapshot held
    for minutes, while other sessions write, runs several times slower than the same query on a fresh one."""
    for load in (frame.programs, frame.program_trials, frame.trial_outcomes, evidence_facts.load_all,
                 disease_match.mondo_tables, section3.evidence_index):
        load()


def main() -> None:
    run = selected(sys.argv[1:])
    os.makedirs(CACHE, exist_ok=True)
    seed(run)
    if any(s in QUERIES_DATABASE for s in run):
        frame.hold_snapshot()
        start = time.monotonic()
        load_tables()
        print(f"[report] load_tables {time.monotonic() - start:.0f}s", flush=True)
    problems = []
    for step in run:
        start = time.monotonic()
        step.main()
        if step in QUERIES_DATABASE:
            cache(step)
        print(f"[report] {step.__name__} {time.monotonic() - start:.0f}s", flush=True)
    if frame.snapshots_read > 1:
        problems.append(f"the build read {frame.snapshots_read} database snapshots (the link dropped); run it again")
    for p in problems:
        print(f"[report] {p}", file=sys.stderr)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
