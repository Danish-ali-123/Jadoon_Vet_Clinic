from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]
DEFAULT_WORKSHEET = "Cases"
SHEET_COLUMNS = [
    "case_ref",
    "saved_at",
    "patient_label",
    "species",
    "breed",
    "urgency",
    "top_condition",
    "case_json",
    "result_json",
    "record_json",
]


def streamlit_secret(name: str, default: Any = None) -> Any:
    try:
        import streamlit as st

        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return default


def sheet_id() -> str | None:
    return os.getenv("GOOGLE_SHEET_ID") or streamlit_secret("GOOGLE_SHEET_ID")


def worksheet_name() -> str:
    return os.getenv("GOOGLE_SHEET_WORKSHEET") or streamlit_secret("GOOGLE_SHEET_WORKSHEET", DEFAULT_WORKSHEET)


def service_account_info() -> dict[str, Any] | None:
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or streamlit_secret("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw:
        if isinstance(raw, str):
            return json.loads(raw)
        if isinstance(raw, dict):
            return dict(raw)

    nested = streamlit_secret("google_service_account")
    if nested:
        return dict(nested)
    return None


def is_google_sheets_configured() -> bool:
    return bool(sheet_id() and service_account_info())


@lru_cache(maxsize=1)
def worksheet_client():
    sid = sheet_id()
    info = service_account_info()
    if not sid or not info:
        return None, "Google Sheets is not configured."

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        credentials = Credentials.from_service_account_info(info, scopes=SCOPES)
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(sid)
        title = worksheet_name()
        try:
            worksheet = spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(SHEET_COLUMNS))
        ensure_header(worksheet)
        return worksheet, "Google Sheets connected."
    except Exception as exc:
        return None, f"Google Sheets connection failed: {exc}"


def ensure_header(worksheet: Any) -> None:
    values = worksheet.row_values(1)
    if values[: len(SHEET_COLUMNS)] != SHEET_COLUMNS:
        worksheet.update("A1", [SHEET_COLUMNS])


def record_to_row(record: dict[str, Any]) -> list[str]:
    case = record.get("case", {})
    result = record.get("result", {})
    return [
        str(record.get("case_ref", "")),
        str(record.get("saved_at", "")),
        str(record.get("patient_label", "")),
        str(case.get("species", "")),
        str(case.get("breed", "")),
        str(record.get("urgency", "")),
        str(record.get("top_condition", "")),
        json.dumps(case, ensure_ascii=False),
        json.dumps(result, ensure_ascii=False),
        json.dumps(record, ensure_ascii=False),
    ]


def append_record(record: dict[str, Any]) -> str:
    worksheet, status = worksheet_client()
    if worksheet is None:
        return status
    worksheet.append_row(record_to_row(record), value_input_option="RAW")
    return "Saved to Google Sheets"


def read_records() -> tuple[list[dict[str, Any]], str]:
    worksheet, status = worksheet_client()
    if worksheet is None:
        return [], status

    try:
        rows = worksheet.get_all_records()
    except Exception as exc:
        return [], f"Google Sheets read failed: {exc}"

    records: list[dict[str, Any]] = []
    for row in rows:
        raw = row.get("record_json")
        if raw:
            try:
                records.append(json.loads(raw))
                continue
            except json.JSONDecodeError:
                pass
        try:
            case = json.loads(row.get("case_json") or "{}")
        except json.JSONDecodeError:
            case = {}
        try:
            result = json.loads(row.get("result_json") or "{}")
        except json.JSONDecodeError:
            result = {}
        records.append(
            {
                "case_ref": row.get("case_ref", ""),
                "saved_at": row.get("saved_at", ""),
                "patient_label": row.get("patient_label", ""),
                "top_condition": row.get("top_condition", ""),
                "urgency": row.get("urgency", ""),
                "case": case,
                "result": result,
            }
        )
    return records, "Loaded from Google Sheets"