from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google_sheets_store import append_record, is_google_sheets_configured, read_records


_HISTORY_LOCK = threading.Lock()
DEFAULT_HISTORY_PATH = Path(__file__).parent / "case_history.jsonl"


def history_path() -> Path:
    configured = os.getenv("CASE_HISTORY_PATH")
    if configured:
        return Path(configured)
    return DEFAULT_HISTORY_PATH


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_local_cases() -> list[dict[str, Any]]:
    path = history_path()
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def merge_records(primary: list[dict[str, Any]], secondary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for record in secondary + primary:
        ref = str(record.get("case_ref", ""))
        if ref:
            merged[ref] = record
    return list(merged.values())


def read_cases() -> list[dict[str, Any]]:
    local_records = read_local_cases()
    if not is_google_sheets_configured():
        return local_records

    sheet_records, _status = read_records()
    if not sheet_records:
        return local_records
    return merge_records(sheet_records, local_records)


def case_storage_source() -> str:
    if not is_google_sheets_configured():
        return f"Local JSONL only: {history_path()}"
    _records, status = read_records()
    return status


def list_cases(limit: int = 250) -> list[dict[str, Any]]:
    records = read_cases()
    records.sort(key=lambda item: item.get("saved_at", ""), reverse=True)
    return records[:limit]


def find_case(case_ref: str) -> dict[str, Any] | None:
    wanted = case_ref.strip().upper()
    for record in read_cases():
        if record.get("case_ref", "").upper() == wanted:
            return record
    return None


def next_case_ref(records: list[dict[str, Any]], saved_at: str) -> str:
    date_part = saved_at[:10].replace("-", "")
    prefix = f"JVC-{date_part}-"
    highest = 0
    for record in records:
        ref = str(record.get("case_ref", ""))
        if not ref.startswith(prefix):
            continue
        try:
            highest = max(highest, int(ref.rsplit("-", 1)[-1]))
        except ValueError:
            continue
    return f"{prefix}{highest + 1:04d}"


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "urgency": result.get("urgency"),
        "model_method": result.get("model_method"),
        "red_flags": result.get("red_flags", []),
        "matches": result.get("matches", [])[:2],
        "diagnostics": result.get("diagnostics", []),
        "treatment_principles": result.get("treatment_principles", []),
        "medication_support": result.get("medication_support", []),
        "immediate_actions": result.get("immediate_actions", []),
    }


def save_case(case: dict[str, Any], result: dict[str, Any]) -> dict[str, str]:
    path = history_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with _HISTORY_LOCK:
        records = read_cases()
        saved_at = utc_now()
        case_ref = next_case_ref(records, saved_at)
        stored_result = compact_result(result)
        stored_result["case_ref"] = case_ref
        stored_result["saved_at"] = saved_at
        top_match = stored_result.get("matches", [{}])[0] if stored_result.get("matches") else {}
        record = {
            "case_ref": case_ref,
            "saved_at": saved_at,
            "patient_label": f"{case.get('species', 'Unknown')} | {case.get('breed') or 'No breed'} | {case.get('visit_date') or saved_at[:10]}",
            "top_condition": top_match.get("condition", "No strong match"),
            "urgency": stored_result.get("urgency", "Unknown"),
            "case": case,
            "result": stored_result,
        }
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

        if is_google_sheets_configured():
            sheet_status = append_record(record)
            storage_status = f"Saved locally and Google Sheets: {sheet_status}"
        else:
            storage_status = "Saved to local case history; Google Sheets not configured"
    return {"case_ref": case_ref, "saved_at": saved_at, "storage_status": storage_status}