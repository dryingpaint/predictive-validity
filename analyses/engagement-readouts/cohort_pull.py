"""The report's efficacy-stop cohort with each stop's phase-entry date, for the step 4 join (anchor year vs the
index trial). Read-only; the cohort is pipeline.stops.stops + cohort, the report's own definition.

    .venv/bin/python analyses/engagement-readouts/cohort_pull.py

Writes cohort.csv: key, phase, entry (phase entry date), reason, origin.
"""
import os
import sys

from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
load_dotenv(os.path.join(ROOT, ".env"))
from pipeline import stops  # noqa: E402


def main():
    modes, rows, progs, trials = stops.stops()
    c = stops.cohort(modes)[["key", "phase", "entry", "reason", "origin"]].sort_values("key")
    c.to_csv(os.path.join(HERE, "cohort.csv"), index=False)
    print(f"{len(c)} efficacy/exposure stops in the report cohort; phases {c.phase.value_counts().to_dict()}; "
          f"entry {c.entry.min()} .. {c.entry.max()}")


if __name__ == "__main__":
    main()
