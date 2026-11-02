"""Every classification the analysis makes, one Google Sheet tab per kind, rebuilt from the database.

    python -m report.sheet

Tabs: diseases (condition string -> MONDO disease), drugs (intervention string -> molecular entities),
entities (UNII substance, modality, targets), programs (entity x disease: phase entries, approval,
disease area), trials (purpose, outcome, endpoint class) and stops (cause, subcause, detail), each row
carrying the id of the LLM decision behind it (pv_evidence.llm_decision). A README tab says what each
column means. All tabs come from one database snapshot.

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

TABS = {
    "diseases": ("One row per ClinicalTrials.gov condition string.", """
        SELECT i.display_name AS condition, count(si.nct_id) AS trials, i.indication_kind AS kind,
               i.mondo_id, i.mondo_label, i.mondo_match, i.mondo_decision_id AS decision_id
        FROM preclin.indication i LEFT JOIN preclin.ctgov_study_indication si USING (indication_id)
        GROUP BY i.indication_id ORDER BY trials DESC, condition"""),
    "drugs": ("One row per intervention string with the entities it resolves to.", """
        SELECT d.display_name AS intervention, d.entity_kind AS kind,
               string_agg(m.name, '; ' ORDER BY m.name) AS entities,
               string_agg(DISTINCT dm.role, '; ') AS roles,
               string_agg(DISTINCT dm.biosimilar_of, '; ') AS biosimilar_of,
               (SELECT count(*) FROM preclin.ctgov_study_drug sd WHERE sd.drug_id = d.drug_id) AS trials,
               d.moiety_decision_id AS decision_id
        FROM preclin.drug d LEFT JOIN preclin.drug_moiety dm USING (drug_id) LEFT JOIN preclin.moiety m USING (moiety_id)
        GROUP BY d.drug_id ORDER BY trials DESC, intervention"""),
    "entities": ("One row per molecular entity linked to an intervention or an FDA application.", """
        SELECT m.moiety_id AS entity_id, m.name AS entity, m.unii, s.display_name AS unii_substance,
               array_to_string(m.code_names, '; ') AS code_names, m.modality, m.target_kind,
               (SELECT string_agg(t.symbol || ' (' || mt.action || ')', '; ' ORDER BY t.symbol)
                FROM preclin.moiety_target mt JOIN public.targets t ON t.id = mt.target_id
                WHERE mt.moiety_id = m.moiety_id AND mt.is_primary) AS primary_targets,
               (SELECT count(*) FROM preclin.dev_program p WHERE p.moiety_id = m.moiety_id) AS programs,
               m.unii_decision_id, m.modality_decision_id, m.target_decision_id
        FROM preclin.moiety m LEFT JOIN preclin.unii_substance s USING (unii)
        WHERE EXISTS (SELECT 1 FROM preclin.drug_moiety dm WHERE dm.moiety_id = m.moiety_id)
           OR EXISTS (SELECT 1 FROM preclin.fda_application_moiety f WHERE f.moiety_id = m.moiety_id)
        ORDER BY programs DESC, entity"""),
    "programs": ("One row per development program: one entity developed for one disease.", """
        SELECT p.program_id, m.name AS entity, p.mondo_id, o.label AS disease, b.bio_area AS disease_area,
               p.ph1_start, p.ph2_start, p.ph3_start, p.highest_phase, p.n_trials, p.n_industry_trials,
               array_to_string(p.lead_sponsors, '; ') AS lead_sponsors, p.last_activity, p.n_active_trials,
               a.approved, a.first_approval_date, a.relation AS approval_relation, a.llm_decision_id AS approval_decision_id
        FROM preclin.dev_program p JOIN preclin.moiety m USING (moiety_id)
        LEFT JOIN preclin.ontology_term o ON o.term_id = p.mondo_id
        LEFT JOIN preclin.mondo_bio_area b ON b.mondo_id = p.mondo_id
        LEFT JOIN preclin.dev_program_approval a USING (program_id)
        ORDER BY entity, disease"""),
    "trials": ("One row per trial with a purpose, outcome or endpoint label.", """
        SELECT s.nct_id, s.brief_title, array_to_string(s.phases, ', ') AS phases, s.overall_status,
               s.lead_sponsor, s.start_date, tp.purpose, tp.title_disease,
               o.execution, o.stop_reason, o.primary_endpoint, o.safety_signal, o.efficacy_failure,
               e.purpose AS endpoint_purpose, e.endpoint_class,
               tp.llm_decision_id AS purpose_decision_id, o.llm_decision_id AS outcome_decision_id,
               e.llm_decision_id AS endpoint_decision_id
        FROM preclin.ctgov_study s
        LEFT JOIN preclin.trial_purpose tp USING (nct_id) LEFT JOIN preclin.trial_outcome o USING (nct_id)
        LEFT JOIN preclin.trial_endpoint e USING (nct_id)
        WHERE tp.nct_id IS NOT NULL OR o.nct_id IS NOT NULL OR e.nct_id IS NOT NULL
        ORDER BY s.start_date DESC NULLS LAST, s.nct_id"""),
    "stops": ("One row per program phase that stopped: why development did not go on.", """
        SELECT m.name AS entity, st.mondo_id, o.label AS disease, st.phase, st.registry_reason, st.cause,
               st.subcause, st.detail, st.traced, st.explanation, array_to_string(st.sources, ' ') AS sources
        FROM preclin.stop st JOIN preclin.moiety m USING (moiety_id)
        LEFT JOIN preclin.ontology_term o ON o.term_id = st.mondo_id
        ORDER BY entity, disease, st.phase"""),
}

COLUMNS = {  # README entries for columns whose meaning is not plain from the name
    "kind": "diseases: disease, symptom_or_sign, procedure_or_state, healthy_volunteers or other; "
            "drugs: drug, combination, vaccine, placebo_or_vehicle, non_drug or unclear",
    "mondo_match": "exact: the term names the condition; broader: the nearest containing term, as MONDO has none",
    "roles": "investigational (what the trial develops) or background (a partner or standard therapy)",
    "target_kind": "human_protein, pathogen, no_single_target or unknown",
    "primary_targets": "HGNC symbol (the drug's action on it)",
    "approved": "FDA approval of the entity for the disease, a subtype of it or a class containing it: yes, no or uncertain",
    "purpose": "trials: indication_development, early_development, product_support or other",
    "title_disease": "the disease the title says the trial treats when its listed conditions are complications of it",
    "primary_endpoint": "met, not_met, mixed, not_assessable or no_results",
    "endpoint_class": "B1 target engagement to B9 infection cure, O1-O3 oncology endpoints, or not_efficacy",
    "cause": "efficacy (with exposure), safety, sponsor_decision, operational, positive_not_advanced, unknown, "
             "not_stopped or not_a_program",
    "subcause": "the reason within the cause (for efficacy, whether the target was engaged)",
    "traced": "true where the cause comes from tracing beyond the registry (company releases, filings, news)",
    "decision_id": "pv_evidence.llm_decision row of the LLM call behind the label (also *_decision_id)",
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
            [f"Database snapshot read {date.today().isoformat()} by python -m report.sheet; rebuilt at each report publish."],
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
