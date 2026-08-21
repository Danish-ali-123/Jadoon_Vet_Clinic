from __future__ import annotations

from datetime import date

import streamlit as st

from data_kb import SPECIES_OPTIONS, load_disease_rows
from vet_ai import analyze_case, build_case_summary, generate_ai_assessment


st.set_page_config(
    page_title="Vet Case Assistant",
    page_icon=":medical_symbol:",
    layout="wide",
)


SEXES = ["Unknown", "Male", "Female", "Neutered male", "Spayed female"]
URGENCY_COLORS = {
    "Emergency": "#b91c1c",
    "Urgent": "#b45309",
    "Routine": "#047857",
}


def chip(text: str, color: str = "#374151") -> str:
    return (
        f"<span style='display:inline-block;background:{color};color:white;"
        "border-radius:999px;padding:0.2rem 0.55rem;margin:0.12rem;"
        "font-size:0.82rem;'>"
        f"{text}</span>"
    )


def render_header() -> None:
    st.title("Vet Case Assistant")
    st.caption(
        "A decision-support prototype for veterinarians. It suggests differentials, "
        "red flags, diagnostics, and treatment principles; it does not replace a vet's judgement."
    )
    st.warning(
        "Clinical safety: final diagnosis, prescriptions, dose calculation, and treatment decisions "
        "must be made by a licensed veterinarian after examination and local legal compliance."
    )
    rows = load_disease_rows()
    st.caption(f"Knowledge base loaded: {len(rows)} disease records from Raw Data.")


def render_patient_form() -> dict:
    with st.form("case_form"):
        st.subheader("Patient")
        patient_col, history_col = st.columns(2)

        with patient_col:
            species = st.selectbox("Animal type", SPECIES_OPTIONS)
            animal_subtype = st.text_input("Further type / production class", placeholder="e.g. calf, dairy cow, broiler, layer")
            breed = st.text_input("Breed", placeholder="e.g. Labrador, Sahiwal, Beetal, Nili-Ravi")
            age = st.text_input("Age", placeholder="e.g. 3 years, 8 months")
            sex = st.selectbox("Sex", SEXES)
            pregnancy_status = st.selectbox(
                "Pregnancy status",
                ["Not applicable / unknown", "Not pregnant", "Pregnant", "Recently gave birth", "Suspected pregnancy problem"],
            )
            lactation_status = st.selectbox("Lactation status", ["Unknown", "Not lactating", "Lactating", "Dry period"])
            weight = st.text_input("Weight", placeholder="e.g. 18 kg")
            body_condition = st.selectbox("Body condition", ["Unknown", "Thin", "Normal", "Overweight", "Obese"])
            visit_date = st.date_input("Date", value=date.today())

        with history_col:
            duration = st.text_input("Duration", placeholder="e.g. 2 days")
            appetite = st.selectbox("Appetite", ["Unknown", "Normal", "Reduced", "Not eating"])
            water = st.selectbox("Water intake", ["Unknown", "Normal", "Increased", "Reduced"])
            vaccination = st.selectbox("Vaccination status", ["Unknown", "Up to date", "Incomplete", "Not vaccinated"])
            deworming = st.selectbox("Deworming / parasite control", ["Unknown", "Up to date", "Overdue", "Never done"])
            number_affected = st.text_input("Number of animals affected", placeholder="e.g. 1 pet, 5 calves, whole flock")
            exposure = st.text_area(
                "Exposure / history",
                placeholder="Ticks, new feed, toxins, trauma, travel, contact with sick animals...",
                height=92,
            )

        st.subheader("Clinical signs")
        symptoms = st.text_area(
            "Symptoms",
            placeholder="Vomiting, diarrhea, fever, cough, nasal discharge, lameness, lethargy...",
            height=130,
        )
        description = st.text_area(
            "Owner description (optional but recommended)",
            placeholder="Write the full story in plain English: what happened first, what changed, and what worries the owner most.",
            height=110,
        )

        vital_col, exam_col = st.columns(2)
        with vital_col:
            temperature = st.text_input("Temperature", placeholder="e.g. 103 F")
            heart_rate = st.text_input("Heart rate", placeholder="optional")
            respiratory_rate = st.text_input("Respiratory rate", placeholder="optional")
        with exam_col:
            stool = st.text_input("Stool / urine notes", placeholder="blood, straining, no urine, watery stool...")
            exam_notes = st.text_area("Exam notes", placeholder="mucous membranes, dehydration, pain, swelling...", height=92)

        use_pretrained_model = st.toggle(
            "Use open-source pretrained semantic model",
            value=True,
            help="Uses sentence-transformers/all-MiniLM-L6-v2 when available. Falls back to keyword matching automatically.",
        )
        use_ai = st.toggle(
            "Use optional OpenAI assessment if OPENAI_API_KEY is configured",
            value=False,
            help="Not required. The app works with the open-source matcher and veterinary CSV knowledge base.",
        )
        submitted = st.form_submit_button("Analyze case", type="primary")

    return {
        "submitted": submitted,
        "use_ai": use_ai,
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


def render_analysis(case: dict) -> None:
    if not case["symptoms"].strip() and not case["exam_notes"].strip():
        st.info("Enter symptoms or exam notes to analyze the case.")
        return

    result = analyze_case(case)
    urgency = result["urgency"]
    urgency_color = URGENCY_COLORS.get(urgency, "#374151")

    st.divider()
    st.subheader("Assessment")
    st.markdown(chip(f"Urgency: {urgency}", urgency_color), unsafe_allow_html=True)
    st.caption(f"Matching method: {result.get('model_method', 'Not provided')}")

    if result["red_flags"]:
        st.error("Red flags detected: " + ", ".join(result["red_flags"]))
    else:
        st.success("No immediate red-flag phrase was detected from the entered notes.")

    match_col, plan_col = st.columns([1.05, 1])

    with match_col:
        st.markdown("#### Differential list")
        if not result["matches"]:
            st.write("No strong match found. Add more signs, vitals, history, and exam findings.")
        for match in result["matches"]:
            with st.container(border=True):
                st.markdown(f"**{match['condition']}**")
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
                if meta:
                    st.caption(meta)
                st.progress(match["score"] / 100, text=f"{match['score']}% pattern match")
                st.write(match["why"])
                if match.get("cause"):
                    st.write(f"Possible cause: {match['cause']}")
                if match["red_flags"]:
                    st.caption("Key risks: " + ", ".join(match["red_flags"]))
                if match.get("clinical_review_notes"):
                    st.caption("Clinical note: " + match["clinical_review_notes"])

    with plan_col:
        st.markdown("#### Vet workflow")
        st.markdown("**Immediate actions**")
        for item in result["immediate_actions"]:
            st.write(f"- {item}")

        st.markdown("**Recommended diagnostics**")
        for item in result["diagnostics"]:
            st.write(f"- {item}")

        st.markdown("**Treatment principles**")
        for item in result["treatment_principles"]:
            st.write(f"- {item}")

    with st.expander("Case summary for record or referral"):
        st.code(build_case_summary(case, result), language="markdown")

    if case["use_ai"]:
        with st.spinner("Generating optional AI assessment..."):
            ai_text = generate_ai_assessment(case, result)
        st.markdown("#### Optional AI assessment")
        st.write(ai_text)


def main() -> None:
    render_header()
    case = render_patient_form()
    if case["submitted"]:
        render_analysis(case)


if __name__ == "__main__":
    main()
