"""Every date window the report's cohorts use. Each analysis names its window here; no
cohort takes a default.

A phase window bounds the date a program entered the phase (its first industry trial of the
phase started); a trial window bounds trial start dates.
"""
from __future__ import annotations

from datetime import date

# Section 1 headline: entries from 2008 (US registration mandatory from late 2007) through
# 2019, so every entry has at least six years to the 2026-10-20 snapshot.
SECTION1 = (date(2008, 1, 1), date(2019, 12, 31))
SECTION1_PERIODS = [(date(2008, 1, 1), date(2011, 12, 31)), (date(2012, 1, 1), date(2015, 12, 31)),
                    (date(2016, 1, 1), date(2019, 12, 31))]
# Entries through 2025, many of them still running at the snapshot: a Section 1 sensitivity, the
# Section 2 relative-success cohort and the stop tracing (pipeline.stops).
RECENT = (date(2015, 1, 1), date(2025, 12, 31))
# Section 2 prediction: Phase 1 entries with ten years to reach approval before the snapshot.
SECTION2_PREDICT = (date(2008, 1, 1), date(2016, 10, 20))
# Section 3: Phase 2 entries with four years of follow-up before the 24-month inactivity cutoff.
SECTION3 = (date(2015, 1, 1), date(2020, 10, 20))
# Section 3 trial analyses: trials started from here have outcome and endpoint labels.
SECTION3_TRIALS_FROM = date(2010, 1, 1)
