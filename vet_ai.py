from __future__ import annotations

from collections import OrderedDict
from typing import Iterable

from case_store import save_case
from data_kb import match_diseases
from knowledge_base import CONDITION_RULES, DEFAULT_DIAGNOSTICS, DEFAULT_TREATMENT_PRINCIPLES
from medication_support import build_medication_support


GLOBAL_RED_FLAGS = {
    "difficulty breathing": "Respiratory distress",
    "respiratory distress": "Respiratory distress",
    "blue tongue": "Cyanosis",
    "collapse": "Collapse",
    "unconscious": "Unconscious",
    "seizure": "Seizures",
    "seizures": "Seizures",
    "bloated": "Bloat",
    "bloat": "Bloat",
    "unable to urinate": "Urinary obstruction",
    "not urinating": "Urinary obstruction",
    "severe bleeding": "Severe bleeding",
    "poison": "Possible toxin exposure",
    "toxin": "Possible toxin exposure",
    "dystocia": "Dystocia",
    "difficult birth": "Dystocia",
}


def normalize_text(*values: str) -> str:
    return " ".join(value.lower().strip() for value in values if value).replace("/", " ")


def unique(items: Iterable[str]) -> list[str]:
    return list(OrderedDict.fromkeys(item for item in items if item))


def score_rule(rule: dict, text: str, species: str) -> dict | None:
    if rule["species"] and species.lower() not in rule["species"]:
        return None

    matched_terms = []
    raw_score = 0
    for term, weight in rule["symptoms"].items():
        if term in text:
            matched_terms.append(term)
            raw_score += weight

    if not matched_terms:
        return None

    max_score = sum(rule["symptoms"].values())
    percentage = min(100, round((raw_score / max_score) * 100))
    return {
        "condition": rule["condition"],
        "score": percentage,
        "why": "Matched signs: " + ", ".join(matched_terms),
        "red_flags": rule.get("red_flags", []),
        "diagnostics": rule.get("diagnostics", []),
        "treatment_principles": rule.get("treatment_principles", []),
        "urgency": rule.get("urgency", "Routine"),
    }


def detect_temperature_flag(temperature: str) -> str | None:
    cleaned = temperature.lower().replace("f", "").replace("c", "").strip()
    try:
        value = float(cleaned)
    except ValueError:
        return None

    if value >= 104 or 40 <= value < 45:
        return "High fever"
    if 0 < value <= 99 or 30 <= value <= 37:
        return "Low temperature"
    return None


def detect_red_flags(case: dict, text: str) -> list[str]:
    flags = [label for phrase, label in GLOBAL_RED_FLAGS.items() if phrase in text]
    temp_flag = detect_temperature_flag(case.get("temperature", ""))
    if temp_flag:
        flags.append(temp_flag)
    return unique(flags)


def determine_urgency(matches: list[dict], red_flags: list[str]) -> str:
    if red_flags:
        return "Emergency"
    if any(match.get("urgency") == "Emergency" or match.get("emergency") == "Yes" for match in matches):
        return "Emergency"
    if any(match.get("urgency") == "Urgent" for match in matches):
        return "Urgent"
    return "Routine"


def analyze_case(case: dict) -> dict:
    text = normalize_text(
        case.get("species", ""),
        case.get("animal_subtype", ""),
        case.get("breed", ""),
        case.get("sex", ""),
        case.get("pregnancy_status", ""),
        case.get("lactation_status", ""),
        case.get("body_condition", ""),
        case.get("duration", ""),
        case.get("appetite", ""),
        case.get("water", ""),
        case.get("vaccination", ""),
        case.get("deworming", ""),
        case.get("number_affected", ""),
        case.get("exposure", ""),
        case.get("symptoms", ""),
        case.get("description", ""),
        case.get("temperature", ""),
        case.get("stool", ""),
        case.get("exam_notes", ""),
    )
    species = case.get("species", "")
    data_matches, model_method = match_diseases(case)

    rule_matches = []
    for rule in CONDITION_RULES:
        scored = score_rule(rule, text, species)
        if scored:
            rule_matches.append(scored)

    rule_matches = sorted(rule_matches, key=lambda item: item["score"], reverse=True)[:2]
    matches = data_matches[:2] if data_matches else rule_matches
    red_flags = detect_red_flags(case, text)

    diagnostics = []
    treatment_principles = []
    immediate_actions = []
    for match in matches:
        diagnostics.extend(match["diagnostics"])
        treatment_principles.extend(match["treatment_principles"])
        if match.get("urgency") in {"Emergency", "Urgent"} or match.get("emergency") == "Yes":
            immediate_actions.extend(match["red_flags"])

    if red_flags:
        immediate_actions.insert(0, "Stabilize patient and arrange immediate veterinary examination.")

    medication_support = build_medication_support(case, matches)

    result = {
        "urgency": determine_urgency(matches, red_flags),
        "model_method": model_method,
        "red_flags": red_flags,
        "matches": matches,
        "diagnostics": unique(diagnostics or DEFAULT_DIAGNOSTICS),
        "treatment_principles": unique(treatment_principles or DEFAULT_TREATMENT_PRINCIPLES),
        "medication_support": medication_support,
        "immediate_actions": unique(immediate_actions or ["Collect complete history, vitals, and physical exam findings."]),
    }
    try:
        storage_meta = save_case(case, result)
        result.update(storage_meta)
    except Exception as exc:
        result["case_ref"] = "Not saved"
        result["storage_status"] = f"Case history save failed: {exc}"
    return result


def build_case_summary(case: dict, result: dict) -> str:
    differentials = ", ".join(match["condition"] for match in result["matches"]) or "No strong match"
    return f"""# Vet Case Summary

Case reference: {result.get("case_ref", "Not saved")}
Saved at: {result.get("saved_at", "Not saved")}
Date: {case.get("visit_date")}
Species: {case.get("species")}
Further type: {case.get("animal_subtype") or "Not provided"}
Breed: {case.get("breed") or "Not provided"}
Age: {case.get("age") or "Not provided"}
Sex: {case.get("sex")}
Pregnancy status: {case.get("pregnancy_status") or "Not provided"}
Lactation status: {case.get("lactation_status") or "Not provided"}
Weight: {case.get("weight") or "Not provided"}
Body condition: {case.get("body_condition") or "Not provided"}

Symptoms:
{case.get("symptoms") or "Not provided"}

Owner description:
{case.get("description") or "Not provided"}

History/exposure:
{case.get("exposure") or "Not provided"}

Vitals/exam:
- Temperature: {case.get("temperature") or "Not provided"}
- Heart rate: {case.get("heart_rate") or "Not provided"}
- Respiratory rate: {case.get("respiratory_rate") or "Not provided"}
- Stool/urine: {case.get("stool") or "Not provided"}
- Notes: {case.get("exam_notes") or "Not provided"}

Urgency: {result["urgency"]}
Model method: {result.get("model_method", "Not provided")}
Red flags: {", ".join(result["red_flags"]) or "None detected"}
Differentials: {differentials}

Diagnostics:
{chr(10).join("- " + item for item in result["diagnostics"])}

Treatment principles:
{chr(10).join("- " + item for item in result["treatment_principles"])}

Medication support:
{chr(10).join("- " + support.get("condition", "Unknown") + ": " + "; ".join(option.get("class_or_category", "Vet-selected medication") for option in support.get("medication_options", [])) for support in result.get("medication_support", [])) or "- Vet medication protocol not available"}
"""


def generate_ai_assessment(case: dict, result: dict) -> str:
    return "This app uses the local no-key prediction engine."

