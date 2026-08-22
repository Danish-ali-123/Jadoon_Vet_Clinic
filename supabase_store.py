from __future__ import annotations

import os
from typing import Any


DEFAULT_TABLE = "cases"
TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}


def _read_streamlit_secret(path: list[str]) -> str:
    try:
        import streamlit as st

        value: Any = st.secrets
        for part in path:
            if not hasattr(value, "get"):
                return ""
            value = value.get(part)
            if value is None:
                return ""
        return str(value).strip()
    except Exception:
        return ""


def _setting(name: str, nested_name: str | None = None) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value

    try:
        import streamlit as st

        value = str(st.secrets.get(name, "")).strip()
        if value:
            return value
    except Exception:
        pass

    if nested_name:
        return _read_streamlit_secret(["connections", "supabase", nested_name])
    return ""


def _enabled(name: str, nested_name: str | None = None) -> bool:
    return _setting(name, nested_name).lower() in TRUE_VALUES


def supabase_settings() -> tuple[str, str, str]:
    url = _setting("SUPABASE_URL", "SUPABASE_URL")
    key = _setting("SUPABASE_KEY", "SUPABASE_KEY") or _setting("SUPABASE_ANON_KEY", "SUPABASE_ANON_KEY")
    table = _setting("SUPABASE_TABLE", "SUPABASE_TABLE") or DEFAULT_TABLE
    return url, key, table


def supabase_sync_enabled() -> bool:
    return _enabled("SUPABASE_CASE_SYNC_ENABLED", "SUPABASE_CASE_SYNC_ENABLED")


def supabase_full_case_enabled() -> bool:
    return _enabled("SUPABASE_STORE_FULL_CASE", "SUPABASE_STORE_FULL_CASE")


def is_supabase_configured() -> bool:
    url, key, _table = supabase_settings()
    return bool(url and key and supabase_sync_enabled())


def supabase_status() -> str:
    url, _key, table = supabase_settings()
    if not url or not _key:
        return "Supabase not configured"
    if not supabase_sync_enabled():
        return "Supabase connected but case sync is disabled"
    host = url.replace("https://", "").replace("http://", "").split("/", 1)[0]
    return f"Supabase table `{table}` at {host}"


def _client():
    url, key, _table = supabase_settings()
    if not url or not key:
        raise RuntimeError("Supabase secrets are missing")
    if not supabase_sync_enabled():
        raise RuntimeError("SUPABASE_CASE_SYNC_ENABLED is not true")
    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError("Supabase package is not installed. Add `supabase` to requirements.txt.") from exc
    return create_client(url, key)


def _summary_payload(record: dict[str, Any]) -> dict[str, Any]:
    case = record.get("case", {}) or {}
    result = record.get("result", {}) or {}
    matches = result.get("matches", []) or []
    top_condition = record.get("top_condition") or (matches[0].get("condition") if matches else "")
    symptoms = str(case.get("symptoms") or "")
    description = str(case.get("description") or "")
    exam_notes = str(case.get("exam_notes") or "")
    symptom_blob = "\n\n".join(part for part in [symptoms, description, exam_notes] if part)

    return {
        "case_ref": record.get("case_ref", ""),
        "saved_at": record.get("saved_at"),
        "patient_label": record.get("patient_label", ""),
        "animal_type": case.get("species", ""),
        "species": case.get("species", ""),
        "breed": case.get("breed", ""),
        "age": str(case.get("age", "")),
        "sex": case.get("sex", ""),
        "symptoms": symptom_blob,
        "urgency": record.get("urgency", ""),
        "top_condition": top_condition or "",
    }


def _full_payload(record: dict[str, Any]) -> dict[str, Any]:
    payload = _summary_payload(record)
    payload.update(
        {
            "case_json": record.get("case", {}) or {},
            "result_json": record.get("result", {}) or {},
            "record_json": record,
        }
    )
    return payload


def _fallback_payload(record: dict[str, Any]) -> dict[str, Any]:
    payload = _summary_payload(record)
    return {
        "animal_type": payload["animal_type"],
        "species": payload["species"],
        "age": payload["age"],
        "sex": payload["sex"],
        "symptoms": payload["symptoms"],
    }


def append_supabase_record(record: dict[str, Any]) -> str:
    client = _client()
    _url, _key, table = supabase_settings()
    payload = _full_payload(record) if supabase_full_case_enabled() else _summary_payload(record)
    try:
        client.table(table).insert(payload).execute()
        mode = "full case" if supabase_full_case_enabled() else "summary case"
        return f"Supabase saved {mode}"
    except Exception as primary_error:
        try:
            client.table(table).insert(_fallback_payload(record)).execute()
            return f"Supabase saved basic case only; add full schema for searchable refs. Insert error: {primary_error}"
        except Exception as fallback_error:
            return f"Supabase save failed: {fallback_error}"


def _row_to_record(row: dict[str, Any]) -> dict[str, Any]:
    if isinstance(row.get("record_json"), dict):
        return row["record_json"]

    case = row.get("case_json") if isinstance(row.get("case_json"), dict) else {}
    result = row.get("result_json") if isinstance(row.get("result_json"), dict) else {}
    if not case:
        case = {
            "species": row.get("species") or row.get("animal_type", ""),
            "breed": row.get("breed", ""),
            "age": row.get("age", ""),
            "sex": row.get("sex", ""),
            "symptoms": row.get("symptoms", ""),
        }

    return {
        "case_ref": row.get("case_ref") or row.get("id") or "",
        "saved_at": row.get("saved_at") or row.get("created_at") or "",
        "patient_label": row.get("patient_label") or f"{case.get('species', 'Unknown')} | {case.get('breed') or 'No breed'}",
        "top_condition": row.get("top_condition", ""),
        "urgency": row.get("urgency", ""),
        "case": case,
        "result": result,
    }


def read_supabase_records(limit: int = 500) -> tuple[list[dict[str, Any]], str]:
    if not is_supabase_configured():
        return [], supabase_status()

    client = _client()
    _url, _key, table = supabase_settings()
    try:
        response = client.table(table).select("*").order("saved_at", desc=True).limit(limit).execute()
        rows = response.data or []
        return [_row_to_record(row) for row in rows], f"Supabase: loaded {len(rows)} cases"
    except Exception as exc:
        return [], f"Supabase read failed: {exc}"
