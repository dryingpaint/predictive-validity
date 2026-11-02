"""Every classification the analysis makes, one Google Sheet tab per kind, rebuilt from the database.

    python -m report.sheet

Tabs: diseases (condition string -> MONDO disease), drugs (intervention string -> molecular entities),
entities (UNII substance, modality, targets), programs (entity x disease: phase entries, approval,
disease area), trials (purpose, outcome, endpoint class) and stops (cause, subcause, detail). A README tab
says what each column means. All tabs come from one database snapshot. The sheet is for readers outside
the codebase: headers are plain English and nothing names a table, schema or module.

The sheet (SHEET_ID) belongs to the report's owner and is shared with the service account SERVICE_ACCOUNT
as an editor. The writer impersonates that account with the caller's application-default credentials,
so no key exists; the caller needs roles/iam.serviceAccountTokenCreator on it.
"""
from __future__ import annotations

from datetime import date

import google.auth
import pandas as pd
from google.auth import impersonated_credentials
from google.auth.transport.requests import AuthorizedSession

from report import frame

SHEET_ID = "1_--uUMY_ZQcGkUZw1rDUMgl4MAS44k5348GPZrY4q0I"
PROJECT = "capable-500218"  # the Google Cloud project holding the service account and the API quota
SERVICE_ACCOUNT = f"pv-sheets-writer@{PROJECT}.iam.gserviceaccount.com"
API = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
ROWS_PER_WRITE = 20000

TABS = {  # column aliases are the sheet's headers, written for readers rather than for the schema
    "diseases": ("One row per ClinicalTrials.gov condition string.", """
        SELECT i.display_name AS "Condition", count(si.nct_id) AS "Trials", i.indication_kind AS "Kind",
               i.mondo_id AS "MONDO ID", i.mondo_label AS "MONDO disease", i.mondo_match AS "Match"
        FROM preclin.indication i LEFT JOIN preclin.ctgov_study_indication si USING (indication_id)
        GROUP BY i.indication_id ORDER BY 2 DESC, 1"""),
    "drugs": ("One row per intervention string with the entities it resolves to.", """
        SELECT d.display_name AS "Intervention", d.entity_kind AS "Kind",
               string_agg(m.name, '; ' ORDER BY m.name) AS "Entities",
               string_agg(DISTINCT dm.role, '; ') AS "Roles",
               string_agg(DISTINCT dm.biosimilar_of, '; ') AS "Biosimilar of",
               (SELECT count(*) FROM preclin.ctgov_study_drug sd WHERE sd.drug_id = d.drug_id) AS "Trials"
        FROM preclin.drug d LEFT JOIN preclin.drug_moiety dm USING (drug_id) LEFT JOIN preclin.moiety m USING (moiety_id)
        GROUP BY d.drug_id ORDER BY 6 DESC, 1"""),
    "entities": ("One row per molecular entity linked to an intervention or an FDA application.", """
        SELECT m.name AS "Entity", m.unii AS "UNII", s.display_name AS "UNII substance",
               array_to_string(m.code_names, '; ') AS "Code names", m.modality AS "Modality",
               m.target_kind AS "Target kind",
               (SELECT string_agg(t.symbol || ' (' || mt.action || ')', '; ' ORDER BY t.symbol)
                FROM preclin.moiety_target mt JOIN public.targets t ON t.id = mt.target_id
                WHERE mt.moiety_id = m.moiety_id AND mt.is_primary) AS "Primary targets",
               (SELECT count(*) FROM preclin.dev_program p WHERE p.moiety_id = m.moiety_id) AS "Programs"
        FROM preclin.moiety m LEFT JOIN preclin.unii_substance s USING (unii)
        WHERE EXISTS (SELECT 1 FROM preclin.drug_moiety dm WHERE dm.moiety_id = m.moiety_id)
           OR EXISTS (SELECT 1 FROM preclin.fda_application_moiety f WHERE f.moiety_id = m.moiety_id)
        ORDER BY 8 DESC, 1"""),
    "programs": ("One row per development program: one entity developed for one disease.", """
        SELECT m.name AS "Entity", p.mondo_id AS "MONDO ID", o.label AS "Disease", b.bio_area AS "Disease area",
               p.ph1_start AS "Phase 1 start", p.ph2_start AS "Phase 2 start", p.ph3_start AS "Phase 3 start",
               p.highest_phase AS "Highest phase", p.n_trials AS "Trials", p.n_industry_trials AS "Industry trials",
               array_to_string(p.lead_sponsors, '; ') AS "Lead sponsors", p.last_activity AS "Last activity",
               p.n_active_trials AS "Active trials", a.approved AS "Approved",
               a.first_approval_date AS "First approval", a.relation AS "Approved for"
        FROM preclin.dev_program p JOIN preclin.moiety m USING (moiety_id)
        LEFT JOIN preclin.ontology_term o ON o.term_id = p.mondo_id
        LEFT JOIN preclin.mondo_bio_area b ON b.mondo_id = p.mondo_id
        LEFT JOIN preclin.dev_program_approval a USING (program_id)
        ORDER BY 1, 3"""),
    "trials": ("One row per trial with a purpose, outcome or endpoint label.", """
        SELECT s.nct_id AS "NCT ID", s.brief_title AS "Title", array_to_string(s.phases, ', ') AS "Phases",
               s.overall_status AS "Status", s.lead_sponsor AS "Lead sponsor", s.start_date AS "Start",
               tp.purpose AS "Purpose", tp.title_disease AS "Disease in title",
               o.execution AS "Execution", o.stop_reason AS "Stop reason", o.primary_endpoint AS "Primary endpoint",
               o.safety_signal AS "Safety signal", o.efficacy_failure AS "Efficacy failure",
               e.purpose AS "Endpoint purpose", e.endpoint_class AS "Endpoint class"
        FROM preclin.ctgov_study s
        LEFT JOIN preclin.trial_purpose tp USING (nct_id) LEFT JOIN preclin.trial_outcome o USING (nct_id)
        LEFT JOIN preclin.trial_endpoint e USING (nct_id)
        WHERE tp.nct_id IS NOT NULL OR o.nct_id IS NOT NULL OR e.nct_id IS NOT NULL
        ORDER BY s.start_date DESC NULLS LAST, s.nct_id"""),
    "stops": ("One row per program phase that stopped: why development did not go on.", """
        SELECT m.name AS "Entity", st.mondo_id AS "MONDO ID", o.label AS "Disease", st.phase AS "Phase",
               st.registry_reason AS "Registry reason", st.cause AS "Cause", st.subcause AS "Subcause",
               st.detail AS "Detail", st.traced AS "Traced", st.explanation AS "Explanation",
               array_to_string(st.sources, ' ') AS "Sources"
        FROM preclin.stop st JOIN preclin.moiety m USING (moiety_id)
        LEFT JOIN preclin.ontology_term o ON o.term_id = st.mondo_id
        ORDER BY 1, 3, 4"""),
}

COLUMNS = {  # README entries for columns whose meaning is not plain from the header
    "Kind": "diseases: disease, symptom_or_sign, procedure_or_state, healthy_volunteers or other; "
            "drugs: drug, combination, vaccine, placebo_or_vehicle, non_drug or unclear",
    "Match": "exact: the term names the condition; broader: the nearest containing term, as MONDO has none",
    "Roles": "investigational (what the trial develops) or background (a partner or standard therapy)",
    "UNII": "the FDA Global Substance Registration System's unique ingredient identifier",
    "Target kind": "human_protein, pathogen, no_single_target or unknown",
    "Primary targets": "HGNC symbol (the drug's action on it)",
    "Approved": "FDA approval of the entity for the disease, a subtype of it or a class containing it: yes, no or uncertain",
    "Approved for": "whether the approval is for the disease itself, a subtype of it or a class containing it",
    "Purpose": "indication_development, early_development, product_support or other",
    "Disease in title": "the disease the title says the trial treats when its listed conditions are complications of it",
    "Primary endpoint": "met, not_met, mixed, not_assessable or no_results",
    "Endpoint class": "B1 target engagement to B9 infection cure, O1-O3 oncology endpoints, or not_efficacy",
    "Cause": "efficacy (with exposure), safety, sponsor_decision, operational, positive_not_advanced, unknown, "
             "not_stopped or not_a_program",
    "Subcause": "the reason within the cause (for efficacy, whether the target was engaged)",
    "Traced": "true where the cause comes from tracing beyond the registry (company releases, filings, news)",
}


def cell(v):
    """A JSON value the Sheets API accepts: dates as ISO text, missing values empty."""
    if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT:
        return ""
    if isinstance(v, (date, pd.Timestamp)):
        return v.isoformat()[:10]
    if hasattr(v, "item"):  # numpy scalars
        return v.item()
    return v


def readme(tabs: dict[str, pd.DataFrame]) -> list[list]:
    rows = [["Predictive validity: every classification, one tab per kind"],
            [f"Data as of {date.today().isoformat()}; refreshed with each report update. Every label was made by "
             "an LLM reading the source record."],
            [], ["tab", "rows", "what one row is"]]
    rows += [[name, len(df), TABS[name][0]] for name, df in tabs.items()]
    rows += [[], ["column", "meaning"]] + [[k, v] for k, v in COLUMNS.items()]
    return rows


def session() -> AuthorizedSession:
    source, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"],
                                    quota_project_id=PROJECT)
    creds = impersonated_credentials.Credentials(source_credentials=source, target_principal=SERVICE_ACCOUNT,
                                                 target_scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return AuthorizedSession(creds)


def write(s: AuthorizedSession, tabs: dict[str, list[list]]) -> None:
    """Replace each tab's contents, creating missing tabs and dropping tabs no longer written."""
    meta = s.get(API, params={"fields": "sheets.properties"}).json()["sheets"]
    existing = {t["properties"]["title"]: t["properties"]["sheetId"] for t in meta}
    requests = [{"addSheet": {"properties": {"title": name}}} for name in tabs if name not in existing]
    if requests:
        s.post(f"{API}:batchUpdate", json={"requests": requests}).raise_for_status()
        meta = s.get(API, params={"fields": "sheets.properties"}).json()["sheets"]
        existing = {t["properties"]["title"]: t["properties"]["sheetId"] for t in meta}
    stale = [{"deleteSheet": {"sheetId": sid}} for name, sid in existing.items() if name not in tabs]
    if stale:
        s.post(f"{API}:batchUpdate", json={"requests": stale}).raise_for_status()
    for name, rows in tabs.items():
        width = max(len(r) for r in rows)
        sid = existing[name]
        s.post(f"{API}:batchUpdate", json={"requests": [
            {"updateCells": {"range": {"sheetId": sid}, "fields": "userEnteredValue"}},
            {"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {
                "rowCount": len(rows) + 1, "columnCount": width, "frozenRowCount": 0 if name == "README" else 1}},
                "fields": "gridProperties(rowCount,columnCount,frozenRowCount)"}},
            {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1},
                            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                            "fields": "userEnteredFormat.textFormat.bold"}}]}).raise_for_status()
        for start in range(0, len(rows), ROWS_PER_WRITE):
            chunk = rows[start:start + ROWS_PER_WRITE]
            s.put(f"{API}/values/'{name}'!A{start + 1}", params={"valueInputOption": "RAW"},
                  json={"values": chunk}).raise_for_status()
        print(f"{name}: {len(rows) - 1} rows", flush=True)


def main() -> None:
    frame.hold_snapshot()
    tabs = {name: frame.query(sql) for name, (_, sql) in TABS.items()}
    values = {"README": readme(tabs)}
    values |= {name: [list(df.columns)] + [[cell(v) for v in row] for row in df.itertuples(index=False)]
               for name, df in tabs.items()}
    write(session(), values)
    print(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")


if __name__ == "__main__":
    main()
