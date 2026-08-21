from __future__ import annotations

import html
from datetime import date

import streamlit as st

from data_kb import SPECIES_OPTIONS, load_disease_rows
from llm_assistant import configured_providers, provider_help_text
from vet_ai import analyze_case, build_case_summary, generate_ai_assessment


st.set_page_config(
    page_title="Jadoon Vet Clinic Assistant",
    layout="wide",
    initial_sidebar_state="collapsed",
)


SEXES = ["Unknown", "Male", "Female", "Neutered male", "Spayed female"]
URGENCY_COLORS = {
    "Emergency": "#b42318",
    "Urgent": "#b54708",
    "Routine": "#067647",
}


CSS = """
<style>
:root {
  --ink: #172026;
  --muted: #667085;
  --panel: #ffffff;
  --line: #d9e2e6;
  --teal: #0f766e;
  --teal-dark: #115e59;
  --blue: #2563eb;
  --amber: #d97706;
  --red: #b42318;
  --wash: #eef7f5;
}
.stApp {
  background:
    radial-gradient(circle at top left, rgba(15, 118, 110, .16), transparent 32rem),
    linear-gradient(180deg, #f7fbfa 0%, #eef4f2 48%, #f8fafc 100%);
  color: var(--ink);
}
.block-container {
  max-width: 1240px;
  padding-top: 2rem;
  padding-bottom: 3rem;
}
[data-testid="stHeader"] { background: transparent; }
.hero {
  border: 1px solid rgba(15, 118, 110, .18);
  background: linear-gradient(135deg, rgba(255,255,255,.96), rgba(232,246,243,.95));
  border-radius: 22px;
  padding: 30px 34px;
  box-shadow: 0 20px 60px rgba(20, 42, 54, .10);
  margin-bottom: 20px;
}
.kicker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--teal-dark);
  font-weight: 800;
  font-size: .82rem;
  letter-spacing: .08em;
  text-transform: uppercase;
}
.hero h1 {
  color: var(--ink);
  font-size: clamp(2.1rem, 5vw, 4.2rem);
  line-height: 1.02;
  margin: 12px 0 12px 0;
  letter-spacing: 0;
}
.hero p {
  color: #475467;
  max-width: 840px;
  font-size: 1.05rem;
  line-height: 1.62;
  margin: 0;
}
.hero-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 22px;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid var(--line);
  color: #344054;
  font-size: .9rem;
  font-weight: 700;
}
.section-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 26px 0 12px;
}
.section-icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #e4f5f2;
  border: 1px solid #b9e1da;
  color: var(--teal-dark);
}
.section-title h3 {
  margin: 0;
  font-size: 1.18rem;
  color: var(--ink);
}
.section-title p {
  margin: 2px 0 0;
  color: var(--muted);
  font-size: .92rem;
}
[data-testid="stForm"] {
  border: 1px solid rgba(15, 118, 110, .18);
  border-radius: 20px;
  padding: 12px 18px 24px;
  background: rgba(255,255,255,.90);
  box-shadow: 0 16px 50px rgba(20, 42, 54, .08);
}
.stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stTextArea textarea {
  border-radius: 12px !important;
  border-color: #c8d7dc !important;
  background-color: #ffffff !important;
}
.stTextArea textarea { min-height: 104px; }
.stButton button {
  border-radius: 12px;
  min-height: 48px;
  font-weight: 800;
  background: linear-gradient(135deg, var(--teal), #1d4ed8);
  border: none;
  color: #ffffff;
  box-shadow: 0 14px 28px rgba(15, 118, 110, .22);
}
.stButton button:hover {
  border: none;
  color: #ffffff;
  transform: translateY(-1px);
}
.alert-safe {
  border-left: 5px solid var(--teal);
  background: #ecfdf5;
  padding: 14px 16px;
  border-radius: 14px;
  color: #064e3b;
  margin: 12px 0 18px;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0 10px;
}
.metric-card, .result-card, .workflow-card {
  background: rgba(255,255,255,.96);
  border: 1px solid rgba(110, 134, 145, .22);
  border-radius: 18px;
  box-shadow: 0 12px 32px rgba(20, 42, 54, .08);
}
.metric-card { padding: 16px; }
.metric-label { color: var(--muted); font-size: .8rem; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; }
.metric-value { color: var(--ink); font-size: 1.45rem; font-weight: 900; margin-top: 4px; }
.result-card { padding: 18px 18px 14px; margin-bottom: 14px; }
.result-top { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
.result-card h4 { margin: 0; font-size: 1.12rem; color: var(--ink); }
.result-meta { color: var(--muted); font-size: .82rem; margin-top: 4px; }
.score-badge {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 7px 10px;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 900;
  font-size: .86rem;
}
.risk-badge {
  display: inline-block;
  margin: 8px 6px 0 0;
  padding: 5px 8px;
  border-radius: 999px;
  background: #fff7ed;
  color: #9a3412;
  border: 1px solid #fed7aa;
  font-size: .78rem;
  font-weight: 800;
}
.workflow-card { padding: 18px; margin-bottom: 14px; }
.workflow-card h4 { margin: 0 0 8px; color: var(--ink); }
.workflow-card ul { margin-top: 8px; padding-left: 1.2rem; }
.workflow-card li { margin-bottom: 6px; color: #344054; }
.urgency-chip {
  display: inline-flex;
  padding: 8px 12px;
  border-radius: 999px;
  color: white;
  font-weight: 900;
  margin: 4px 0 8px;
}
.small-note { color: var(--muted); font-size: .88rem; }
@media (max-width: 760px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; }
  .hero { padding: 22px 18px; border-radius: 18px; }
  .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .result-top { flex-direction: column; }
}
</style>
"""


ICON_PATHS = {
    "shield": "M12 3l7 3v5c0 5-3.2 8.5-7 10-3.8-1.5-7-5-7-10V6l7-3z",
    "animal": "M5 10c0-2 1.5-4 3.5-4S12 8 12 10s-1.5 4-3.5 4S5 12 5 10zm7 4c2.5 0 5 1.5 5 4v1H7v-1c0-2.5 2.5-4 5-4zm4-8l2-2m-2 2l2 2M8 6L6 4m2 2L6 8",
    "history": "M4 5h16M4 10h16M4 15h10M4 20h8",
    "clinical": "M12 4v16M4 12h16",
    "brain": "M8 8a4 4 0 118 0v8a4 4 0 11-8 0V8zM8 12h8",
    "report": "M7 3h7l3 3v15H7V3zm7 0v4h4M9 11h6M9 15h6M9 19h4",
}


def icon_svg(name: str) -> str:
    path = ICON_PATHS.get(name, ICON_PATHS["shield"])
    return (
        "<svg width='20' height='20' viewBox='0 0 24 24' fill='none' "
        "stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
        f"<path d='{path}'/></svg>"
    )


def section_title(icon: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="section-title">
          <div class="section-icon">{icon_svg(icon)}</div>
          <div><h3>{html.escape(title)}</h3><p>{html.escape(subtitle)}</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def render_header() -> None:
    rows = load_disease_rows()
    st.markdown(
        f"""
        <div class="hero">
          <div class="kicker">{icon_svg('shield')} Jadoon Vet Clinic</div>
          <h1>Vet Case Assistant</h1>
          <p>Clinical triage and decision support for veterinarians. Enter patient details, signs, history, and exam findings to generate differentials, red flags, diagnostics, and treatment principles for vet review.</p>
          <div class="hero-strip">
            <span class="pill">{icon_svg('animal')} {len(rows)} knowledge-base records</span>
            <span class="pill">{icon_svg('brain')} Open-source semantic matching</span>
            <span class="pill">{icon_svg('report')} Referral-ready summary</span>
          </div>
        </div>
        <div class="alert-safe"><strong>Clinical safety:</strong> Final diagnosis, prescriptions, dose calculation, and treatment decisions must be made by a licensed veterinarian after examination and local legal compliance.</div>
        """,
        unsafe_allow_html=True,
    )


def render_patient_form() -> dict:
    providers = configured_providers()
    with st.form("case_form"):
        section_title("animal", "Patient profile", "Core identity, production class, and reproductive status")
        patient_col, repro_col, history_col = st.columns([1.05, 1, 1])

        with patient_col:
            species = st.selectbox("Animal type", SPECIES_OPTIONS)
            animal_subtype = st.text_input("Further type / production class", placeholder="calf, dairy cow, broiler, layer")
            breed = st.text_input("Breed", placeholder="Labrador, Sahiwal, Beetal, Nili-Ravi")
            age = st.text_input("Age", placeholder="3 years, 8 months")

        with repro_col:
            sex = st.selectbox("Sex", SEXES)
            pregnancy_status = st.selectbox(
                "Pregnancy status",
                ["Not applicable / unknown", "Not pregnant", "Pregnant", "Recently gave birth", "Suspected pregnancy problem"],
            )
            lactation_status = st.selectbox("Lactation status", ["Unknown", "Not lactating", "Lactating", "Dry period"])
            weight = st.text_input("Weight", placeholder="18 kg")

        with history_col:
            body_condition = st.selectbox("Body condition", ["Unknown", "Thin", "Normal", "Overweight", "Obese"])
            vaccination = st.selectbox("Vaccination status", ["Unknown", "Up to date", "Incomplete", "Not vaccinated"])
            deworming = st.selectbox("Deworming / parasite control", ["Unknown", "Up to date", "Overdue", "Never done"])
            visit_date = st.date_input("Date", value=date.today())

        section_title("history", "History and exposure", "Duration, appetite, herd context, toxins, feed, trauma, contact risks")
        hist_col, exposure_col = st.columns([1, 1.25])
        with hist_col:
            duration = st.text_input("Duration", placeholder="2 days")
            appetite = st.selectbox("Appetite", ["Unknown", "Normal", "Reduced", "Not eating"])
            water = st.selectbox("Water intake", ["Unknown", "Normal", "Increased", "Reduced"])
            number_affected = st.text_input("Number of animals affected", placeholder="1 pet, 5 calves, whole flock")
        with exposure_col:
            exposure = st.text_area(
                "Exposure / history",
                placeholder="Ticks, new feed, toxins, trauma, travel, contact with sick animals...",
                height=130,
            )

        section_title("clinical", "Clinical signs", "Symptoms, vitals, stool/urine notes, exam findings, and owner description")
        signs_col, exam_col = st.columns([1.15, 1])
        with signs_col:
            symptoms = st.text_area(
                "Symptoms",
                placeholder="Vomiting, diarrhea, fever, cough, nasal discharge, lameness, lethargy...",
                height=132,
            )
            description = st.text_area(
                "Owner description (optional but recommended)",
                placeholder="Write the full story in plain English: what happened first, what changed, and what worries the owner most.",
                height=116,
            )
        with exam_col:
            temperature = st.text_input("Temperature", placeholder="103 F")
            heart_rate = st.text_input("Heart rate", placeholder="optional")
            respiratory_rate = st.text_input("Respiratory rate", placeholder="optional")
            stool = st.text_input("Stool / urine notes", placeholder="blood, straining, no urine, watery stool")
            exam_notes = st.text_area("Exam notes", placeholder="mucous membranes, dehydration, pain, swelling", height=104)

        section_title("brain", "Model settings", "Local matching first, optional free-tier LLM support when keys are configured")
        model_col, llm_col = st.columns([1, 1])
        with model_col:
            use_pretrained_model = st.toggle(
                "Use open-source pretrained semantic model",
                value=True,
                help="Uses sentence-transformers/all-MiniLM-L6-v2 when available. Falls back to keyword matching automatically.",
            )
        with llm_col:
            use_llm = st.toggle("Use optional external LLM assistant", value=False)
            llm_provider = st.selectbox("LLM provider", providers, help=provider_help_text())

        submitted = st.form_submit_button("Analyze case", type="primary", use_container_width=True)

    return {
        "submitted": submitted,
        "use_ai": use_llm,
        "llm_provider": llm_provider,
        "use_pretrained_model": use_pretrained_model,
        "species": species,
        "animal_subtype": animal_subtype,
        "breed": breed,
        "age": age,
        "sex": sex,
        "pregnancy_status": pregnancy_status,
        "lactation_status": lactation_status,
        "weight": weight,
        "body_condition": body_condition,
        "visit_date": str(visit_date),
        "duration": duration,
        "appetite": appetite,
        "water": water,
        "vaccination": vaccination,
        "deworming": deworming,
        "number_affected": number_affected,
        "exposure": exposure,
        "symptoms": symptoms,
        "description": description,
        "temperature": temperature,
        "heart_rate": heart_rate,
        "respiratory_rate": respiratory_rate,
        "stool": stool,
        "exam_notes": exam_notes,
    }


def list_html(items: list[str]) -> str:
    if not items:
        return "<p class='small-note'>Not provided.</p>"
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"


def render_metric_grid(result: dict) -> None:
    matches = result.get("matches", [])
    top = matches[0]["condition"] if matches else "No strong match"
    html_block = f"""
    <div class="metric-grid">
      <div class="metric-card"><div class="metric-label">Urgency</div><div class="metric-value">{html.escape(result['urgency'])}</div></div>
      <div class="metric-card"><div class="metric-label">Top differential</div><div class="metric-value">{html.escape(top)}</div></div>
      <div class="metric-card"><div class="metric-label">Matches</div><div class="metric-value">{len(matches)}</div></div>
      <div class="metric-card"><div class="metric-label">Red flags</div><div class="metric-value">{len(result.get('red_flags', []))}</div></div>
    </div>
    """
    st.markdown(html_block, unsafe_allow_html=True)


def render_match_card(match: dict) -> None:
    risks = "".join(f"<span class='risk-badge'>{html.escape(risk)}</span>" for risk in match.get("red_flags", []))
    meta = " | ".join(
        item
        for item in [
            match.get("record_id", ""),
            match.get("species", ""),
            match.get("category", ""),
            f"Emergency: {match.get('emergency')}" if match.get("emergency") else "",
        ]
        if item
    )
    card = f"""
    <div class="result-card">
      <div class="result-top">
        <div>
          <h4>{html.escape(match.get('condition', 'Unknown condition'))}</h4>
          <div class="result-meta">{html.escape(meta)}</div>
        </div>
        <div class="score-badge">{match.get('score', 0)}% match</div>
      </div>
      <p class="small-note">{html.escape(match.get('why', 'Matched from case text.'))}</p>
      {f"<p><strong>Possible cause:</strong> {html.escape(match.get('cause', ''))}</p>" if match.get('cause') else ""}
      {risks}
      {f"<p class='small-note'><strong>Clinical note:</strong> {html.escape(match.get('clinical_review_notes', ''))}</p>" if match.get('clinical_review_notes') else ""}
    </div>
    """
    st.markdown(card, unsafe_allow_html=True)


def render_workflow_card(title: str, items: list[str]) -> None:
    st.markdown(
        f"<div class='workflow-card'><h4>{html.escape(title)}</h4>{list_html(items)}</div>",
        unsafe_allow_html=True,
    )


def render_analysis(case: dict) -> None:
    if not case["symptoms"].strip() and not case["exam_notes"].strip() and not case["description"].strip():
        st.info("Enter symptoms, exam notes, or owner description to analyze the case.")
        return

    result = analyze_case(case)
    urgency_color = URGENCY_COLORS.get(result["urgency"], "#344054")

    st.markdown("---")
    st.markdown(
        f"<span class='urgency-chip' style='background:{urgency_color}'>Urgency: {html.escape(result['urgency'])}</span>",
        unsafe_allow_html=True,
    )
    st.caption(f"Matching method: {result.get('model_method', 'Not provided')}")

    render_metric_grid(result)

    if result["red_flags"]:
        st.error("Red flags detected: " + ", ".join(result["red_flags"]))
    else:
        st.success("No immediate red-flag phrase was detected from the entered notes.")

    match_col, plan_col = st.columns([1.08, 1])
    with match_col:
        section_title("report", "Differential list", "Ranked disease candidates from the knowledge base")
        if not result["matches"]:
            st.write("No strong match found. Add more signs, vitals, history, and exam findings.")
        for match in result["matches"]:
            render_match_card(match)

    with plan_col:
        section_title("shield", "Vet workflow", "Actions, tests, and treatment principles")
        render_workflow_card("Immediate actions", result["immediate_actions"])
        render_workflow_card("Recommended diagnostics", result["diagnostics"])
        render_workflow_card("Treatment principles", result["treatment_principles"])

    with st.expander("Case summary for record or referral"):
        st.code(build_case_summary(case, result), language="markdown")

    if case["use_ai"]:
        with st.spinner("Generating optional LLM assessment..."):
            ai_text = generate_ai_assessment(case, result)
        section_title("brain", "Optional LLM assessment", "External provider output for veterinarian review")
        st.write(ai_text)


def main() -> None:
    render_css()
    render_header()
    case = render_patient_form()
    if case["submitted"]:
        render_analysis(case)


if __name__ == "__main__":
    main()
