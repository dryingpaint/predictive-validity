"""Analysis frames for the report, read from the canonical program tables.

Every Section 1 and Section 2 number is computed from these frames; nothing
reads the legacy preclin.program / program_outcome / approval tables.
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


def connect():
    return psycopg2.connect(os.environ.get("DATABASE_URL_RO") or os.environ["DATABASE_URL"],
                            keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3)


def query(sql: str, params=None, attempts: int = 4) -> pd.DataFrame:
    """Run a read query, retrying when the connection drops."""
    for attempt in range(attempts):
        try:
            with connect() as conn, conn.cursor() as cur:
                cur.execute(sql, params)
                return pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])
        except psycopg2.OperationalError:
            if attempt == attempts - 1:
                raise
            time.sleep(15 * (attempt + 1))


def snapshot() -> date:
    return query("SELECT snapshot FROM preclin.dev_program_build ORDER BY built_at DESC LIMIT 1").iloc[0, 0]


def programs() -> pd.DataFrame:
    """One row per (entity, disease) program with entity and disease attributes
    and the FDA approval judgement for that disease."""
    return query("""
        SELECT p.program_id, p.moiety_id, m.name AS moiety, m.modality, m.target_kind,
               p.mondo_id, t.label AS disease, a.bio_area,
               p.first_start, p.highest_phase, p.n_trials, p.n_industry_trials, p.last_activity,
               p.n_active_trials, p.lead_sponsors,
               ap.approved, ap.first_approval_date, ap.date_basis, ap.relation,
               (SELECT min(s.status_date) FROM preclin.fda_application_moiety am
                JOIN preclin.fda_submission s ON s.appl_no = am.appl_no
                WHERE am.moiety_id = p.moiety_id AND s.submission_type = 'ORIG' AND s.status = 'AP'
                  AND am.biosimilar_of IS NULL) AS moiety_first_fda_approval
        FROM preclin.dev_program p
        JOIN preclin.moiety m USING (moiety_id)
        LEFT JOIN preclin.ontology_term t ON t.term_id = p.mondo_id
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
