from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


PROTOCOL_PATH = Path(__file__).parent / "Raw Data" / "vet_medication_protocols_template.csv"
DRUG_CLASS_PATTERNS = [
    (r"\bpenicillin\b", "Penicillin", "Penicillin beta-lactam antibiotic", "Antibiotic"),
    (r"\bstreptomycin\b", "Streptomycin", "Aminoglycoside antibiotic", "Antibiotic"),
    (r"\bsulfadiazine\b|\bsulfa\b|\bsulfonamide\b", "Sulfadiazine / sulfonamide", "Sulfonamide antibiotic", "Antibiotic"),
    (r"\boxytetracycline\b|\btetracycline\b", "Oxytetracycline / tetracycline", "Tetracycline antibiotic", "Antibiotic"),
    (r"\bceftiofur\b|\bcephalosporin\b", "Ceftiofur / cephalosporin", "Cephalosporin antibiotic", "Antibiotic"),
    (r"\benrofloxacin\b|\bfluoroquinolone\b", "Enrofloxacin / fluoroquinolone", "Fluoroquinolone antibiotic", "Antibiotic"),
    (r"\bmetronidazole\b", "Metronidazole", "Nitroimidazole antimicrobial", "Antimicrobial"),
    (r"\bantibiotic\b|\bantibiotics\b", "Culture-guided antibiotic", "Veterinarian-selected antimicrobial class", "Antibiotic"),
    (r"\bivermectin\b|\bdeworm\b|\banthelmintic\b", "Ivermectin / dewormer", "Antiparasitic / anthelmintic", "Antiparasitic"),
    (r"\banti-inflammatory\b|\bnsaid\b|\bmeloxicam\b|\bflunixin\b|\bketoprofen\b", "Anti-inflammatory therapy", "NSAID / anti-inflammatory", "Supportive medication"),
    (r"\bantipyretic\b", "Antipyretic", "Antipyretic fever control", "Supportive medication"),
    (r"\bfluid\b|\bfluids\b", "Fluids", "Fluid therapy", "Supportive care"),
    (r"\bantitoxin\b", "Antitoxin", "Antitoxin / biologic", "Biologic support"),
    (r"\bintramammary\b", "Intramammary antibiotic product", "Intramammary therapy", "Local udder therapy"),
]


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().strip())


@lru_cache(maxsize=1)
def load_protocol_rows() -> list[dict[str, str]]:
    if not PROTOCOL_PATH.exists():
        return []
    with PROTOCOL_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def protocol_matches(case: dict[str, Any], condition: str) -> list[dict[str, str]]:
    rows = load_protocol_rows()
    species = normalize(str(case.get("species", "")))
    condition_norm = normalize(condition)
    matches: list[dict[str, str]] = []
    for row in rows:
        row_condition = normalize(row.get("condition", ""))
        row_species = normalize(row.get("species", ""))
        if row_condition and row_condition not in condition_norm and condition_norm not in row_condition:
            continue
        if row_species and species and row_species not in {species, "any", "all"}:
            continue
        matches.append(row)
    return matches


def row_to_option(row: dict[str, str]) -> dict[str, str]:
    review_status = row.get("review_status") or "Vet protocol"
    return {
        "medication_name": row.get("medicine_name") or "Vet-approved medicine",
        "medication_type": row.get("medicine_type") or "Medication",
        "class_or_category": row.get("antibiotic_class") or row.get("class_or_category") or "Vet-selected class",
        "example_from_knowledge_base": row.get("medicine_name") or "Vet protocol medicine",
        "dosage_limit": row.get("dosage_limit") or "Vet must calculate from weight and product label/protocol.",
        "route": row.get("route") or "Vet to confirm",
        "frequency": row.get("frequency") or "Vet to confirm",
        "duration": row.get("duration") or "Vet to confirm",
        "withdrawal_period": row.get("withdrawal_period") or "Vet to confirm for food animals",
        "dose_status": f"{review_status}: veterinarian must confirm exact dose, route, interval, duration, and withdrawal rules before use.",
    }


def inferred_option(name: str, med_class: str, med_type: str) -> dict[str, str]:
    return {
        "medication_name": name,
        "medication_type": med_type,
        "class_or_category": med_class,
        "example_from_knowledge_base": name,
        "dosage_limit": "Exact dose limit requires veterinarian weight-based calculation and local product label/protocol.",
        "route": "Vet to confirm",
        "frequency": "Vet to confirm",
        "duration": "Vet to confirm",
        "withdrawal_period": "Vet to confirm for milk/meat/egg-producing animals",
        "dose_status": "Recommendation only: veterinarian must decide exact drug, dose, route, interval, and duration.",
    }


def infer_medication_items(text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for pattern, name, med_class, med_type in DRUG_CLASS_PATTERNS:
        if not re.search(pattern, text, flags=re.IGNORECASE):
            continue
        key = f"{name}:{med_class}"
        if key in seen:
            continue
        seen.add(key)
        items.append(inferred_option(name, med_class, med_type))
    return items


def general_safety_notes(case: dict[str, Any], match: dict[str, Any]) -> list[str]:
    species = str(case.get("species", "")).lower()
    notes = [
        "Recommendation only - the veterinarian must make the final prescribing decision.",
        "Confirm diagnosis, accurate weight, hydration, pregnancy/lactation, organ status, allergies, and contraindications first.",
        "Use culture/sensitivity where bacterial infection is suspected and the case is not immediately life-threatening.",
    ]
    if species in {"cow", "cattle", "buffalo", "goat", "sheep", "camel", "chicken"}:
        notes.append("Food-animal treatment must follow local label rules and milk/meat/egg withdrawal periods.")
    if match.get("emergency") == "Yes":
        notes.append("Emergency cases require immediate veterinarian examination and stabilization before routine medication planning.")
    if str(case.get("pregnancy_status", "")).lower().startswith("pregnant"):
        notes.append("Pregnancy status can change drug choice; avoid unsafe medications unless vet confirms benefit outweighs risk.")
    return notes


def build_medication_support(case: dict[str, Any], matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    support: list[dict[str, Any]] = []
    for match in matches[:2]:
        condition = match.get("condition", "Unknown condition")
        protocol_options = [row_to_option(row) for row in protocol_matches(case, condition)]
        treatment_text = " ".join(match.get("treatment_principles", []))
        inferred = infer_medication_items(treatment_text)
        if not protocol_options and not inferred and treatment_text:
            inferred = [
                inferred_option(
                    treatment_text,
                    "Veterinarian-selected medication/supportive care",
                    "Condition-specific treatment",
                )
            ]
        support.append(
            {
                "condition": condition,
                "score": match.get("score", 0),
                "recommendation_notice": "Recommendation only - the veterinarian must make the final decision.",
                "medication_options": protocol_options or inferred,
                "safety_notes": general_safety_notes(case, match),
                "vet_protocol_needed": "Exact dose/duration display requires a vet-approved row in Raw Data/vet_medication_protocols_template.csv or Google Sheets protocol storage.",
            }
        )
    return support