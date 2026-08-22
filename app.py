from __future__ import annotations

import html
from datetime import date

import streamlit as st

from data_kb import SPECIES_OPTIONS, load_disease_rows
from local_llm import generate_local_llm_assessment
from vet_ai import analyze_case, build_case_summary


st.set_page_config(
    page_title="Jadoon Vet Clinic Assistant",
    layout="wide",
    initial_sidebar_state="collapsed",
)


SEXES = ["Unknown", "Male", "Female", "Neutered male", "Spayed female"]
URGENCY_COLORS = {
    "Emergency": "#b91c1c",
    "Urgent": "#b45309",
    "Routine": "#047857",
}


CSS = """
<style>
:root {
  --page: #f2f6f7;
  --ink: #101828;
  --body: #26323f;
  --muted: #526170;
  --line: #c8d5dc;
  --panel: #ffffff;
  --panel-strong: #f8fbfc;
  --navy: #0b1f33;
  --navy-2: #143452;
  --teal: #047c72;
  --teal-2: #0f9f8e;
  --blue: #1d4ed8;
  --amber: #b45309;
  --red: #b91c1c;
}

.stApp {
  background: var(--page);
  color: var(--ink);
}

.block-container {
  max-width: 1240px;
  padding: 1.2rem 1.35rem 3rem;
}

[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { right: 1rem; }

h1, h2, h3, h4, h5, h6,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
label, .stSelectbox label, .stTextInput label, .stTextArea label {
  color: var(--ink) !important;
}

[data-testid="stCaptionContainer"], .small, .muted { color: var(--muted) !important; }

.app-shell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 14px 18px;
  margin-bottom: 18px;
  border: 1px solid #d7e2e7;
  border-radius: 18px;
  background: rgba(255,255,255,.92);
  box-shadow: 0 12px 30px rgba(16, 24, 40, .06);
}
.brand-mark {
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: var(--navy);
  color: #ffffff;
}
.brand-wrap { display: flex; align-items: center; gap: 12px; }
.brand-title { color: var(--ink); font-weight: 900; font-size: 1.05rem; line-height: 1.1; }
.brand-subtitle { color: var(--muted); font-size: .84rem; font-weight: 700; margin-top: 2px; }
.nav-pills { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }
.nav-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: 999px;
  background: #eef4f7;
  border: 1px solid #d2e0e6;
  color: var(--navy);
  font-weight: 900;
  font-size: .88rem;
}

.welcome-hero {
  min-height: 74vh;
  border-radius: 30px;
  overflow: hidden;
  background:
    linear-gradient(112deg, rgba(11,31,51,.98), rgba(12,73,76,.94)),
    radial-gradient(circle at 82% 18%, rgba(20, 184, 166, .45), transparent 20rem);
  color: white;
  box-shadow: 0 28px 80px rgba(11, 31, 51, .26);
  border: 1px solid rgba(255,255,255,.16);
  padding: clamp(28px, 6vw, 72px);
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(300px, .78fr);
  gap: clamp(22px, 4vw, 54px);
  align-items: center;
}
.welcome-copy h1 {
  color: #ffffff !important;
  font-size: clamp(3rem, 7vw, 6.8rem);
  line-height: .92;
  margin: 10px 0 16px;
  letter-spacing: 0;
}
.welcome-copy h2 {
  color: #b7f4ea !important;
  font-size: clamp(1.35rem, 3vw, 2.35rem);
  margin: 0 0 10px;
}
.welcome-copy p {
  color: #d8eef0 !important;
  font-size: 1.08rem;
  line-height: 1.7;
  max-width: 720px;
}
.kicker {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: #a7f3d0;
  font-weight: 900;
  letter-spacing: .11em;
  text-transform: uppercase;
  font-size: .88rem;
}
.hero-panel {
  background: rgba(255,255,255,.10);
  border: 1px solid rgba(255,255,255,.22);
  border-radius: 24px;
  padding: 22px;
  backdrop-filter: blur(10px);
}
.hero-stat {
  padding: 17px 0;
  border-bottom: 1px solid rgba(255,255,255,.16);
}
.hero-stat:last-child { border-bottom: none; }
.hero-stat strong { display: block; color: #ffffff; font-size: 1.7rem; }
.hero-stat span { color: #d8eef0; font-weight: 700; }

.screen-title {
  margin: 26px 0 18px;
}
.screen-title .eyebrow {
  color: var(--teal);
  font-size: .82rem;
  font-weight: 950;
  letter-spacing: .12em;
  text-transform: uppercase;
}
.screen-title h1 {
  font-size: clamp(2.1rem, 4vw, 4rem);
  line-height: 1;
  margin: 8px 0 8px;
  color: var(--ink) !important;
}
.screen-title p {
  max-width: 760px;
  color: var(--body) !important;
  font-size: 1.02rem;
  line-height: 1.65;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin: 18px 0 22px;
}
.feature-card, .panel, .result-card, .workflow-card, .metric-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 20px;
  box-shadow: 0 16px 42px rgba(16, 24, 40, .08);
}
.feature-card { padding: 22px; min-height: 190px; }
.feature-card h3 { margin: 14px 0 8px; font-size: 1.22rem; color: var(--ink) !important; }
.feature-card p { color: var(--body) !important; line-height: 1.58; margin: 0; }
.icon-box {
  width: 46px;
  height: 46px;
  border-radius: 15px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  background: linear-gradient(135deg, var(--teal), var(--blue));
}
.panel { padding: 20px 20px 24px; margin-bottom: 18px; }
.panel-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.panel-heading h3 { margin: 0; font-size: 1.18rem; color: var(--ink) !important; }
.panel-heading p { margin: 2px 0 0; color: var(--muted) !important; font-size: .94rem; }

[data-testid="stForm"] {
  border: none;
  background: transparent;
  padding: 0;
}
.stTextInput input, .stTextArea textarea,
.stSelectbox div[data-baseweb="select"] > div {
  background: #ffffff !important;
  border: 1px solid #aebfc8 !important;
  border-radius: 12px !important;
  color: var(--ink) !important;
  min-height: 45px;
}
.stTextArea textarea { min-height: 112px; }
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #667085 !important; opacity: 1; }
.stButton button {
  min-height: 48px;
  border-radius: 12px;
  border: 1px solid #0a5f58;
  background: linear-gradient(135deg, #075e59, #1d4ed8);
  color: #ffffff !important;
  font-weight: 950;
  box-shadow: 0 14px 30px rgba(29, 78, 216, .20);
}
.stButton button:hover { transform: translateY(-1px); border-color: #083f3b; color: #ffffff !important; }

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 16px 0 20px;
}
.metric-card { padding: 18px; }
.metric-label { color: var(--muted); font-size: .78rem; font-weight: 950; text-transform: uppercase; letter-spacing: .07em; }
.metric-value { color: var(--ink); font-size: 1.5rem; font-weight: 950; margin-top: 6px; line-height: 1.1; }
.result-card { padding: 18px; margin-bottom: 14px; }
.result-top { display: flex; justify-content: space-between; gap: 14px; align-items: flex-start; }
.result-card h4 { margin: 0; color: var(--ink) !important; font-size: 1.14rem; }
.result-meta { color: var(--muted); font-size: .84rem; margin-top: 5px; font-weight: 750; }
.result-card p { color: var(--body) !important; line-height: 1.55; }
.score-badge {
  flex: 0 0 auto;
  padding: 7px 10px;
  border-radius: 999px;
  background: #dbeafe;
  color: #1e3a8a;
  font-weight: 950;
}
.risk-badge {
  display: inline-block;
  margin: 6px 6px 0 0;
  padding: 6px 9px;
  border-radius: 999px;
  background: #fff7ed;
  color: #9a3412;
  border: 1px solid #fed7aa;
  font-weight: 900;
  font-size: .8rem;
}
.workflow-card { padding: 18px; margin-bottom: 14px; }
.workflow-card h4 { margin: 0 0 10px; color: var(--ink) !important; }
.workflow-card li { margin-bottom: 8px; color: var(--body) !important; }
.urgency-chip {
  display: inline-flex;
  padding: 10px 14px;
  border-radius: 999px;
  color: #ffffff;
  font-weight: 950;
  margin-bottom: 8px;
}
.safety-strip {
  border-left: 6px solid var(--teal);
  background: #e8f7f4;
  color: #063b35;
  padding: 15px 17px;
  border-radius: 14px;
  font-weight: 780;
  margin: 12px 0 20px;
}

@media (max-width: 900px) {
  .welcome-hero { grid-template-columns: 1fr; min-height: auto; }
  .card-grid { grid-template-columns: 1fr; }
  .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .app-shell { align-items: flex-start; flex-direction: column; }
  .nav-pills { justify-content: flex-start; }
}
@media (max-width: 560px) {
  .block-container { padding-left: .9rem; padding-right: .9rem; }
  .welcome-hero { padding: 28px 20px; border-radius: 22px; }
  .welcome-copy h1 { font-size: 3rem; }
  .metric-grid { grid-template-columns: 1fr; }
  .result-top { flex-direction: column; }
}
</style>
"""


ICON_PATHS = {
    "shield": "M12 3l7 3v5c0 5-3.2 8.5-7 10-3.8-1.5-7-5-7-10V6l7-3z",
    "home": "M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-9z",
    "case": "M7 3h10a2 2 0 0 1 2 2v16H5V5a2 2 0 0 1 2-2zm2 5h6M9 12h6M9 16h4",
    "brain": "M8 8a4 4 0 0 1 8 0v8a4 4 0 0 1-8 0V8zM8 12h8",
    "report": "M7 3h7l3 3v15H7V3zm7 0v4h4M9 12h6M9 16h6",
    "clinical": "M12 5v14M5 12h14",
    "history": "M4 6h16M4 12h16M4 18h10",
    "arrow": "M5 12h14M13 6l6 6-6 6",
}


def icon_svg(name: str, size: int = 22) -> str:
    path = ICON_PATHS.get(name, ICON_PATHS["shield"])
    return (
        f"<svg width='{size}' height='{size}' viewBox='0 0 24 24' fill='none' "
        "stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
        f"<path d='{path}'/></svg>"
    )


def set_page(page: str) -> None:
    st.session_state.page = page


def ensure_state() -> None:
    if "page" not in st.session_state:
        st.session_state.page = "welcome"
    if "last_case" not in st.session_state:
        st.session_state.last_case = None
    if "last_result" not in st.session_state:
        st.session_state.last_result = None


def render_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def render_topbar() -> None:
    st.markdown(
        f"""
        <div class="app-shell">
          <div class="brand-wrap">
            <div class="brand-mark">{icon_svg('shield')}</div>
            <div>
              <div class="brand-title">Jadoon Vet Clinic</div>
              <div class="brand-subtitle">Vet Doc Hammad Jadoon</div>
            </div>
          </div>
          <div class="nav-pills">
            <span class="nav-pill">{icon_svg('home', 17)} Home</span>
            <span class="nav-pill">{icon_svg('case', 17)} Case Intake</span>
            <span class="nav-pill">{icon_svg('report', 17)} Assessment</span>
            <span class="nav-pill">{icon_svg('history', 17)} History</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def screen_title(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="screen-title">
          <div class="eyebrow">{html.escape(eyebrow)}</div>
          <h1>{html.escape(title)}</h1>
          <p>{html.escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def panel_heading(icon: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="panel-heading">
          <div class="icon-box">{icon_svg(icon)}</div>
          <div><h3>{html.escape(title)}</h3><p>{html.escape(subtitle)}</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_welcome() -> None:
    rows = load_disease_rows()
    st.markdown(
        f"""
        <div class="welcome-hero">
          <div class="welcome-copy">
            <div class="kicker">{icon_svg('shield', 20)} Clinical Decision Support</div>
            <h1>Welcome to Jadoon Vet Clinic</h1>
            <h2>Vet Doc Hammad Jadoon</h2>
            <p>A modern veterinary case assistant for structured intake, red-flag triage, likely differentials, diagnostics, and treatment principles for licensed veterinarian review.</p>
          </div>
          <div class="hero-panel">
            <div class="hero-stat"><strong>{len(rows)}</strong><span>knowledge-base disease records</span></div>
            <div class="hero-stat"><strong>5</strong><span>focused screens including searchable history</span></div>
            <div class="hero-stat"><strong>Safe</strong><span>no final diagnosis or dose replacement</span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns([1, 3])
    with left:
        if st.button("Enter App", type="primary", use_container_width=True):
            set_page("home")
            st.rerun()


def render_home() -> None:
    render_topbar()
    rows = load_disease_rows()
    screen_title(
        "Home",
        "Clinical workflow, cleaned up.",
        "Use the assistant as a structured support tool: capture the case, identify urgent risks, compare disease candidates, and export a referral-ready summary.",
    )
    st.markdown(
        f"""
        <div class="card-grid">
          <div class="feature-card"><div class="icon-box">{icon_svg('case')}</div><h3>Structured Intake</h3><p>Animal type, breed, sex, pregnancy, lactation, vitals, exposure, symptoms, and owner description in one clean flow.</p></div>
          <div class="feature-card"><div class="icon-box">{icon_svg('brain')}</div><h3>Smart Matching</h3><p>Uses the vet CSV knowledge base with open-source semantic matching, then falls back to keyword matching if the model is unavailable.</p></div>
          <div class="feature-card"><div class="icon-box">{icon_svg('report')}</div><h3>Vet Assessment</h3><p>Ranks differentials, red flags, diagnostics, treatment principles, and a case summary for records or referral.</p></div>
        </div>
        <div class="safety-strip">Loaded {len(rows)} veterinarian-review-pending records. This app supports clinical workflow only; diagnosis, prescription, and dosing remain with the veterinarian.</div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("Start New Case", type="primary", use_container_width=True):
            set_page("case")
            st.rerun()
    with col2:
        if st.session_state.last_result and st.button("View Last Result", use_container_width=True):
            set_page("results")
            st.rerun()
    with col3:
        st.page_link("pages/Case_History.py", label="Open Case History")


def render_patient_form() -> None:
    render_topbar()
    screen_title(
        "Case Intake",
        "Capture the clinical picture clearly.",
        "Keep the form factual. More context improves matching: timeline, exposure, herd/flock pattern, vitals, and exam findings all matter.",
    )

    with st.form("case_form"):
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        panel_heading("case", "Patient profile", "Identity, production class, reproductive status, and preventive care.")
        patient_col, repro_col, care_col = st.columns([1.05, 1, 1])
        with patient_col:
            species = st.selectbox("Animal type", SPECIES_OPTIONS)
            animal_subtype = st.text_input("Further type / production class", placeholder="calf, dairy cow, broiler, layer")
            breed = st.text_input("Breed", placeholder="Labrador, Sahiwal, Beetal, Nili-Ravi")
            age = st.text_input("Age", placeholder="3 years, 8 months")
        with repro_col:
            sex = st.selectbox("Sex", SEXES)
            pregnancy_status = st.selectbox("Pregnancy status", ["Not applicable / unknown", "Not pregnant", "Pregnant", "Recently gave birth", "Suspected pregnancy problem"])
            lactation_status = st.selectbox("Lactation status", ["Unknown", "Not lactating", "Lactating", "Dry period"])
            weight = st.text_input("Weight", placeholder="18 kg")
        with care_col:
            body_condition = st.selectbox("Body condition", ["Unknown", "Thin", "Normal", "Overweight", "Obese"])
            vaccination = st.selectbox("Vaccination status", ["Unknown", "Up to date", "Incomplete", "Not vaccinated"])
            deworming = st.selectbox("Deworming / parasite control", ["Unknown", "Up to date", "Overdue", "Never done"])
            visit_date = st.date_input("Date", value=date.today())
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        panel_heading("history", "History and exposure", "Timeline, appetite, herd context, feed, toxins, trauma, and contact risks.")
        hist_col, exposure_col = st.columns([1, 1.25])
        with hist_col:
            duration = st.text_input("Duration", placeholder="2 days")
            appetite = st.selectbox("Appetite", ["Unknown", "Normal", "Reduced", "Not eating"])
            water = st.selectbox("Water intake", ["Unknown", "Normal", "Increased", "Reduced"])
            number_affected = st.text_input("Number of animals affected", placeholder="1 pet, 5 calves, whole flock")
        with exposure_col:
            exposure = st.text_area("Exposure / history", placeholder="Ticks, new feed, toxins, trauma, travel, contact with sick animals...", height=132)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        panel_heading("clinical", "Clinical signs", "Symptoms, vitals, stool/urine notes, exam findings, and owner description.")
        signs_col, exam_col = st.columns([1.15, 1])
        with signs_col:
            symptoms = st.text_area("Symptoms", placeholder="Vomiting, diarrhea, fever, cough, nasal discharge, lameness, lethargy...", height=136)
            description = st.text_area("Owner description (optional but recommended)", placeholder="Write the full story in plain English: what happened first, what changed, and what worries the owner most.", height=116)
        with exam_col:
            temperature = st.text_input("Temperature", placeholder="103 F")
            heart_rate = st.text_input("Heart rate", placeholder="optional")
            respiratory_rate = st.text_input("Respiratory rate", placeholder="optional")
            stool = st.text_input("Stool / urine notes", placeholder="blood, straining, no urine, watery stool")
            exam_notes = st.text_area("Exam notes", placeholder="mucous membranes, dehydration, pain, swelling", height=104)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        panel_heading("brain", "Prediction model", "No API key required. Uses open-source pretrained matching plus a local Hugging Face LLM assessment.")
        use_pretrained_model = st.toggle("Use open-source pretrained semantic model", value=True, help="Uses sentence-transformers/all-MiniLM-L6-v2 when available. Falls back automatically to keyword matching if the model cannot load.")
        st.markdown('</div>', unsafe_allow_html=True)

        submit_col, back_col, spacer = st.columns([1.2, 1, 2.8])
        with submit_col:
            submitted = st.form_submit_button("Analyze Case", type="primary", use_container_width=True)
        with back_col:
            back_home = st.form_submit_button("Back Home", use_container_width=True)

    if back_home:
        set_page("home")
        st.rerun()

    if submitted:
        case = {
            "submitted": True,
            "use_ai": True,
            "llm_provider": "Local no-key assessment",
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
        if not symptoms.strip() and not exam_notes.strip() and not description.strip():
            st.error("Enter symptoms, exam notes, or owner description before analyzing.")
            return
        with st.spinner("Analyzing case..."):
            result = analyze_case(case)
        st.session_state.last_case = case
        st.session_state.last_result = result
        set_page("results")
        st.rerun()


def list_html(items: list[str]) -> str:
    if not items:
        return "<p class='muted'>Not provided.</p>"
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"


def render_metric_grid(result: dict) -> None:
    matches = result.get("matches", [])
    top = matches[0]["condition"] if matches else "No strong match"
    st.markdown(
        f"""
        <div class="metric-grid">
          <div class="metric-card"><div class="metric-label">Urgency</div><div class="metric-value">{html.escape(result['urgency'])}</div></div>
          <div class="metric-card"><div class="metric-label">Top Differential</div><div class="metric-value">{html.escape(top)}</div></div>
          <div class="metric-card"><div class="metric-label">Matches</div><div class="metric-value">{len(matches)}</div></div>
          <div class="metric-card"><div class="metric-label">Red Flags</div><div class="metric-value">{len(result.get('red_flags', []))}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
    st.markdown(
        f"""
        <div class="result-card">
          <div class="result-top">
            <div>
              <h4>{html.escape(match.get('condition', 'Unknown condition'))}</h4>
              <div class="result-meta">{html.escape(meta)}</div>
            </div>
            <div class="score-badge">{match.get('score', 0)}% match</div>
          </div>
          <p>{html.escape(match.get('why', 'Matched from case text.'))}</p>
          {f"<p><strong>Possible cause:</strong> {html.escape(match.get('cause', ''))}</p>" if match.get('cause') else ""}
          {risks}
          {f"<p class='muted'><strong>Clinical note:</strong> {html.escape(match.get('clinical_review_notes', ''))}</p>" if match.get('clinical_review_notes') else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def workflow_card(title: str, items: list[str]) -> None:
    st.markdown(
        f"<div class='workflow-card'><h4>{html.escape(title)}</h4>{list_html(items)}</div>",
        unsafe_allow_html=True,
    )



def render_local_assessment_plan(result: dict) -> None:
    matches = result.get("matches", [])[:2]
    if not matches:
        workflow_card("Diagnosis and treatment plan", ["No confident local match was found. Add more history, vitals, exam findings, and diagnostics."])
        return

    primary = matches[0]
    secondary = matches[1] if len(matches) > 1 else None
    diagnosis_items = [
        f"Primary candidate: {primary.get('condition', 'Unknown')} ({primary.get('score', 0)}% match).",
    ]
    if secondary:
        diagnosis_items.append(f"Second candidate to rule out: {secondary.get('condition', 'Unknown')} ({secondary.get('score', 0)}% match).")
    diagnosis_items.append("Treat this as decision support for the veterinarian, not an automatic final diagnosis.")

    diagnostics = result.get("diagnostics", [])[:6]
    treatment = result.get("treatment_principles", [])[:6]
    safety = result.get("immediate_actions", [])[:5]

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    panel_heading("clinical", "Diagnosis and treatment plan", "Local no-key assessment from top 2 pretrained/knowledge-base matches.")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        workflow_card("Most likely diagnosis candidates", diagnosis_items)
        workflow_card("Diagnostics to confirm", diagnostics)
    with col_b:
        workflow_card("Treatment plan for vet review", treatment)
        workflow_card("Immediate safety actions", safety)
    st.markdown('</div>', unsafe_allow_html=True)


def render_llm_assessment(case: dict, result: dict) -> None:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    panel_heading("brain", "Local LLM assistant", "No API key or token. Runs a public Hugging Face model locally when available.")
    with st.spinner("Generating local LLM assessment..."):
        assessment, status = generate_local_llm_assessment(case, result)
    st.caption(status)
    st.markdown(assessment)
    st.markdown('</div>', unsafe_allow_html=True)

def render_results() -> None:
    render_topbar()
    case = st.session_state.last_case
    result = st.session_state.last_result
    if not case or not result:
        screen_title("Assessment", "No case analyzed yet.", "Start a new case to generate an assessment.")
        if st.button("Start New Case", type="primary"):
            set_page("case")
            st.rerun()
        return

    screen_title("Assessment", "Clinical assessment dashboard", "Review urgency, red flags, differential matches, diagnostics, and treatment principles before final veterinarian decision-making.")
    urgency_color = URGENCY_COLORS.get(result["urgency"], "#344054")
    st.markdown(f"<span class='urgency-chip' style='background:{urgency_color}'>Urgency: {html.escape(result['urgency'])}</span>", unsafe_allow_html=True)
    st.caption(f"Matching method: {result.get('model_method', 'Not provided')}")
    st.info(f"Case reference: {result.get('case_ref', 'Not saved')} | {result.get('storage_status', 'History status unavailable')}")
    render_metric_grid(result)

    if result["red_flags"]:
        st.error("Red flags detected: " + ", ".join(result["red_flags"]))
    else:
        st.success("No immediate red-flag phrase was detected from the entered notes.")

    render_local_assessment_plan(result)
    render_llm_assessment(case, result)

    left, right = st.columns([1.08, 1])
    with left:
        panel_heading("report", "Differential list", "Ranked disease candidates from the knowledge base.")
        for match in result.get("matches", []):
            render_match_card(match)
    with right:
        panel_heading("shield", "Vet workflow", "Actions, diagnostics, and treatment principles.")
        workflow_card("Immediate actions", result["immediate_actions"])
        workflow_card("Recommended diagnostics", result["diagnostics"])
        workflow_card("Treatment principles", result["treatment_principles"])

    with st.expander("Case summary for record or referral"):
        st.code(build_case_summary(case, result), language="markdown")


    nav1, nav2, nav3 = st.columns([1, 1, 2])
    with nav1:
        if st.button("New Case", type="primary", use_container_width=True):
            set_page("case")
            st.rerun()
    with nav2:
        if st.button("Home", use_container_width=True):
            set_page("home")
            st.rerun()
    with nav3:
        st.page_link("pages/Case_History.py", label="Open Case History")


def main() -> None:
    ensure_state()
    render_css()
    page = st.session_state.page
    if page == "welcome":
        render_welcome()
    elif page == "home":
        render_home()
    elif page == "case":
        render_patient_form()
    elif page == "results":
        render_results()
    else:
        set_page("welcome")
        st.rerun()


if __name__ == "__main__":
    main()





