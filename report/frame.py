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
QUERY_ATTEMPTS = 8  # with waits of 30 s more each time: rides out about 18 minutes of a dropping link


def query(sql: str, params=None) -> pd.DataFrame:
    """Run a read query, retrying on a fresh connection when the link drops. A dropped link surfaces
    as OperationalError, or as InterfaceError once psycopg2 finds the connection closed."""
    for attempt in range(QUERY_ATTEMPTS):
        conn = None
        try:
            conn = psycopg2.connect(os.environ.get("DATABASE_URL_RO") or os.environ["DATABASE_URL"],
                                    keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3)
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            if attempt == QUERY_ATTEMPTS - 1:
                raise
            time.sleep(30 * (attempt + 1))
        finally:
            if conn is not None and not conn.closed:
                conn.close()


PAGES = 24  # a large frame is read in parts, so a dropped link costs one part, not the frame


def query_paged(sql: str, key: str, params: dict | None = None) -> pd.DataFrame:
    """`sql` read in PAGES parts split by a hash of its output column `key`, each its own retried
    query; named %(...)s parameters of `sql` go in `params`."""
    part = f"SELECT * FROM ({sql}) q WHERE mod(abs(hashtext(({key})::text)), %(pages)s) = %(page)s"
    return pd.concat([query(part, {**(params or {}), "pages": PAGES, "page": page}) for page in range(PAGES)],
                     ignore_index=True)


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
    return query_paged("""
        SELECT dt.program_id, dt.nct_id, dt.phase, dt.attach, dt.marks_entry, dt.starts_phase,
               s.lead_sponsor_class = 'INDUSTRY' AS industry,
               s.overall_status, s.start_date, s.start_date_type, s.last_update_posted,
               s.primary_completion_date, s.completion_date,
               'United States' = ANY(coalesce(s.countries, '{}')) AS us_site, s.has_results
        FROM preclin.dev_program_trial dt JOIN preclin.ctgov_study s USING (nct_id)""", "program_id")


def trial_outcomes() -> pd.DataFrame:
    """Classified trial outcomes; results_source says whether the endpoint was
    judged from registry-posted results or from a results paper's abstract."""
    return query_paged("""
        SELECT o.*, CASE d.task WHEN 'trial_outcome_from_publication' THEN 'publication'
                                ELSE 'registry' END AS results_source
        FROM preclin.trial_outcome o JOIN pv_evidence.llm_decision d USING (llm_decision_id)""", "llm_decision_id")
