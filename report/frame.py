"""Analysis frames for the report, read from the canonical program tables.

Every Section 1 and Section 2 number is computed from these frames.
"""
from __future__ import annotations

import os
import time
from datetime import date

import pandas as pd
import psycopg2
from dotenv import load_dotenv

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(REPO, ".env"))

WINDOW = (date(2015, 1, 1), date(2025, 12, 31))
ACTIVE = ("RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING")
QUERY_ATTEMPTS = 4


def query(sql: str, params=None) -> pd.DataFrame:
    """Run a read query, retrying when the connection drops."""
    for attempt in range(QUERY_ATTEMPTS):
        try:
            with (psycopg2.connect(os.environ.get("DATABASE_URL_RO") or os.environ["DATABASE_URL"],
                                   keepalives=1, keepalives_idle=30, keepalives_interval=10,
                                   keepalives_count=3) as conn,
                  conn.cursor() as cur):
                cur.execute(sql, params)
                return pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])
        except psycopg2.OperationalError:
            if attempt == QUERY_ATTEMPTS - 1:
                raise
            time.sleep(15 * (attempt + 1))


def snapshot() -> date:
    return query("SELECT snapshot FROM preclin.dev_program_build ORDER BY built_at DESC LIMIT 1").iloc[0, 0]


def programs() -> pd.DataFrame:
    """One row per (entity, disease) program with the attributes the phase cohorts
    use and the FDA approval judgement for that disease."""
    return query("""
        SELECT p.program_id, p.moiety_id, m.modality, p.mondo_id, a.bio_area,
               ap.approved, ap.first_approval_date, ap.date_basis,
               (SELECT min(s.status_date) FROM preclin.fda_application_moiety am
                JOIN preclin.fda_submission s ON s.appl_no = am.appl_no
                WHERE am.moiety_id = p.moiety_id AND s.submission_type = 'ORIG' AND s.status = 'AP'
                  AND am.biosimilar_of IS NULL) AS moiety_first_fda_approval
        FROM preclin.dev_program p
        JOIN preclin.moiety m USING (moiety_id)
        LEFT JOIN preclin.mondo_bio_area a ON a.mondo_id = p.mondo_id
        LEFT JOIN preclin.dev_program_approval ap USING (program_id)""")


def program_trials() -> pd.DataFrame:
    """Every trial attached to a program, with its sponsor class, status and dates."""
    return query("""
        SELECT dt.program_id, dt.nct_id, dt.phase, dt.attach, dt.marks_entry,
               s.lead_sponsor_class = 'INDUSTRY' AS industry,
               s.overall_status, s.start_date, s.primary_completion_date, s.completion_date,
               'United States' = ANY(coalesce(s.countries, '{}')) AS us_site, s.has_results
        FROM preclin.dev_program_trial dt JOIN preclin.ctgov_study s USING (nct_id)""")


def trial_outcomes() -> pd.DataFrame:
    """Classified trial outcomes; results_source says whether the endpoint was
    judged from registry-posted results or from a results paper's abstract."""
    return query("""
        SELECT o.*, CASE d.task WHEN 'trial_outcome_from_publication' THEN 'publication'
                                ELSE 'registry' END AS results_source
        FROM preclin.trial_outcome o JOIN pv_evidence.llm_decision d USING (llm_decision_id)""")
