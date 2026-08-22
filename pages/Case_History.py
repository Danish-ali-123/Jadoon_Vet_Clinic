from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import sys

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from case_store import case_storage_source, find_case, history_path, list_cases  # noqa: E402


st.set_page_config(
    page_title="Case History | Jadoon Vet Clinic",
    layout="wide",
    initial_sidebar_state="expanded",
)


CSS = """
<style>
.stApp { background: #f2f6f7; color: #101828; }
.block-container { max-width: 1180px; padding: 1.4rem 1.2rem 3rem; }
h1, h2, h3, p, li, label, [data-testid="stMarkdownContainer"] { color: #101828 !important; }
[data-testid="stCaptionContainer"] { color: #526170 !important; }
.history-hero {
  border-radius: 24px;
  background: linear-gradient(112deg, #0b1f33, #075e59);
  color: white;
  padding: clamp(24px, 5vw, 52px);
  margin-bottom: 22px;
  box-shadow: 0 24px 70px rgba(11, 31, 51, .22);
}
.history-hero h1 { color: #ffffff !important; font-size: clamp(2.4rem, 5vw, 4.7rem); margin: 0 0 10px; }
.history-hero p { color: #d8eef0 !important; max-width: 760px; font-size: 1.05rem; line-height: 1.65; }
.metric-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0;
}
.metric-card, .case-card {
  background: white;
  border: 1px solid #c8d5dc;
  border-radius: 18px;
  box-shadow: 0 16px 42px rgba(16, 24, 40, .08);
}
.metric-card { padding: 18px; }
.metric-label { color: #526170; font-size: .78rem; font-weight: 950; text-transform: uppercase; letter-spacing: .07em; }
.metric-value { color: #101828; font-size: 1.45rem; font-weight: 950; margin-top: 5px; }
.case-card { padding: 18px; margin: 14px 0; }
.case-card h3 { margin: 0; }
.case-meta { color: #526170; font-weight: 800; margin: 4px 0 12px; }
.badge {
  display: inline-block;
  padding: 6px 9px;
  border-radius: 999px;
  background: #dbeafe;
  color: #1e3a8a;
  font-weight: 900;
  margin: 3px 5px 3px 0;
}
.warning-strip {
  border-left: 6px solid #b45309;
  background: #fff7ed;
  color: #7c2d12;
  padding: 14px 16px;
  border-radius: 14px;
  font-weight: 780;
  margin: 12px 0 18px;
}
@media (max-width: 800px) { .metric-row { grid-template-columns: 1fr 1fr; } }
@media (max-width: 520px) { .metric-row { grid-template-columns: 1fr; } }
</style>
"""


def csv_export(records: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["case_ref", "saved_at", "patient_label", "species", "breed", "urgency", "top_condition"],
    )
    writer.writeheader()
    for record in records:
        case = record.get("case", {})
        writer.writerow(
            {
                "case_ref": record.get("case_ref", ""),
                "saved_at": record.get("saved_at", ""),
                "patient_label": record.get("patient_label", ""),
                "species": case.get("species", ""),
                "breed": case.get("breed", ""),
                "urgency": record.get("urgency", ""),
                "top_condition": record.get("top_condition", ""),
            }
        )
    return output.getvalue()


def match_query(record: dict, query: str) -> bool:
    if not query:
        return True
    case = record.get("case", {})
    haystack = " ".join(
        str(value)
        for value in [
            record.get("case_ref", ""),
            record.get("patient_label", ""),
            record.get("top_condition", ""),
            record.get("urgency", ""),
            record.get("saved_at", ""),
            case.get("species", ""),
            case.get("breed", ""),
            case.get("animal_subtype", ""),
            case.get("symptoms", ""),
        ]
    ).lower()
    return query.lower().strip() in haystack


def render_record(record: dict) -> None:
    case = record.get("case", {})
    result = record.get("result", {})
    matches = result.get("matches", [])
    ref = record.get("case_ref", "Unknown ref")
    st.markdown(
        f"""
        <div class="case-card">
          <h3>{ref}</h3>
          <div class="case-meta">{record.get('patient_label', 'Unknown patient')} | Saved {record.get('saved_at', 'Unknown time')}</div>
          <span class="badge">Urgency: {record.get('urgency', 'Unknown')}</span>
          <span class="badge">Top: {record.get('top_condition', 'No strong match')}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.subheader("Patient")
        st.write(
            {
                "Species": case.get("species"),
                "Breed": case.get("breed"),
                "Age": case.get("age"),
                "Sex": case.get("sex"),
                "Pregnancy": case.get("pregnancy_status"),
                "Visit date": case.get("visit_date"),
            }
        )
        st.subheader("Symptoms")
        st.write(case.get("symptoms") or "Not provided")
    with col_b:
        st.subheader("Top 2 Matches")
        for match in matches[:2]:
            st.write(f"{match.get('condition')} - {match.get('score')}% match")
        st.subheader("Diagnostics")
        st.write(result.get("diagnostics", []))

    with st.expander("Full stored case JSON"):
        st.json(record)
    st.download_button(
        "Download this case JSON",
        data=json.dumps(record, indent=2, ensure_ascii=False),
        file_name=f"{ref}.json",
        mime="application/json",
        use_container_width=True,
    )


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    records = list_cases(limit=500)
    latest = records[0] if records else {}
    emergencies = sum(1 for record in records if record.get("urgency") == "Emergency")

    st.markdown(
        """
        <div class="history-hero">
          <h1>Case History</h1>
          <p>Search saved Jadoon Vet Clinic cases by reference number, species, breed, condition, date, or symptoms.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="metric-row">
          <div class="metric-card"><div class="metric-label">Saved Cases</div><div class="metric-value">{len(records)}</div></div>
          <div class="metric-card"><div class="metric-label">Emergencies</div><div class="metric-value">{emergencies}</div></div>
          <div class="metric-card"><div class="metric-label">Latest Ref</div><div class="metric-value">{latest.get('case_ref', 'None')}</div></div>
          <div class="metric-card"><div class="metric-label">Storage</div><div class="metric-value">Cloud Ready</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='warning-strip'>Storage source: {case_storage_source()}. Local fallback file: {history_path()}. On free Streamlit Cloud local files can be lost after reboot/redeploy, so Google Sheets is recommended for persistent records.</div>",
        unsafe_allow_html=True,
    )

    query_col, ref_col = st.columns([1.3, 1])
    with query_col:
        query = st.text_input("Search history", placeholder="JVC-20260822-0001, cow, mastitis, emergency")
    with ref_col:
        direct_ref = st.text_input("Open exact reference", placeholder="JVC-YYYYMMDD-0001")

    if direct_ref.strip():
        record = find_case(direct_ref)
        if record:
            render_record(record)
        else:
            st.error("No case found for that reference number.")
        return

    filtered = [record for record in records if match_query(record, query)]
    export_col_a, export_col_b = st.columns([1, 1])
    with export_col_a:
        st.download_button(
            "Download history CSV",
            data=csv_export(filtered),
            file_name="jadoon_case_history.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with export_col_b:
        st.download_button(
            "Download history JSON",
            data=json.dumps(filtered, indent=2, ensure_ascii=False),
            file_name="jadoon_case_history.json",
            mime="application/json",
            use_container_width=True,
        )

    if not filtered:
        st.info("No saved cases found yet.")
        return

    options = [
        f"{record.get('case_ref')} | {record.get('patient_label')} | {record.get('top_condition')}"
        for record in filtered
    ]
    selected = st.selectbox("Select a saved case", options)
    selected_ref = selected.split("|", 1)[0].strip()
    selected_record = find_case(selected_ref)
    if selected_record:
        render_record(selected_record)


if __name__ == "__main__":
    main()

