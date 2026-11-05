"""Every date window the report's cohorts use. Each analysis names its window here; no
cohort takes a default.

A phase window bounds the date a program entered the phase (its first industry trial of the
phase started); a trial window bounds trial start dates.
"""
from __future__ import annotations

from datetime import date

# The report's one window: entries from 2008 (US registration mandatory from late 2007) through
# 2019, so every entry has at least six years to the 2026-10-20 snapshot. Section 1, Section 2's
# relative success and models, and Section 3 (whose four-year outcome resolves by 2023) all use it.
SECTION1 = (date(2008, 1, 1), date(2019, 12, 31))
SECTION1_PERIODS = [(date(2008, 1, 1), date(2011, 12, 31)), (date(2012, 1, 1), date(2015, 12, 31)),
                    (date(2016, 1, 1), date(2019, 12, 31))]
# Entries through 2025, many of them still running at the snapshot: a Section 1 sensitivity and the
# comparison window of the stop causes and efficacy failures.
RECENT = (date(2015, 1, 1), date(2025, 12, 31))
# Stops traced and labelled (pipeline.stops): every Phase 1-3 entry from 2008 through 2025, so the
# Section 1 headline window and RECENT both lie inside it.
TRACING = (date(2008, 1, 1), date(2025, 12, 31))
# Section 2 prediction: Phase 1 entries with ten years to reach approval before the snapshot, the one
# analysis outside SECTION1, since a six-year horizon on SECTION1 halves the approvals it learns from
# (that version is reported as a check).
SECTION2_PREDICT = (date(2008, 1, 1), date(2016, 10, 20))
