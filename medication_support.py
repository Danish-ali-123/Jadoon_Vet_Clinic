from __future__ import annotations

import re
from typing import Any


DRUG_CLASS_PATTERNS = [
    (r"\bpenicillin\b", "Penicillin beta-lactam antibiotic", "Antibiotic", "Penicillin"),
    (r"\bstreptomycin\b", "Aminoglycoside antibiotic", "Antibiotic", "Streptomycin"),
    (r"\bsulfadiazine\b|\bsulfa\b|\bsulfonamide\b", "Sulfonamide antibiotic", "Antibiotic", "Sulfadiazine / sulfonamide"),
    (r"\boxytetracycline\b|\btetracycline\b", "Tetracycline antibiotic", "Antibiotic", "Oxytetracycline / tetracycline"),
    (r"\bceftiofur\b|\bcephalosporin\b", "Cephalosporin antibiotic", "Antibiotic", "Ceftiofur / cephalosporin"),
    (r"\benrofloxacin\b|\bfluoroquinolone\b", "Fluoroquinolone antibiotic", "Antibiotic", "Enrofloxacin / fluoroquinolone"),
    (r"\bmetronidazole\b", "Nitroimidazole antimicrobial", "Antimicrobial", "Metronidazole"),
    (r"\bivermectin\b|\bdeworm\b|\banthelmintic\b", "Antiparasitic / anthelmintic", "Antiparasitic", "Ivermectin / dewormer"),
    (r"\banti-inflammatory\b|\bnsaid\b|\bmeloxicam\b|\bflunixin\b|\bketoprofen\b", "NSAID / anti-inflammatory", "Supportive medication", "Anti-inflammatory therapy"),
    (r"\bantipyretic\b", "Antipyretic fever control", "Supportive medication", "Antipyretic"),
    (r"\bfluid\b|\bfluids\b", "Fluid therapy", "Supportive care", "Fluids"),
    (r"\bantitoxin\b", "Antitoxin / biologic", "Biologic support", "Antitoxin"),
    (r"\bintramammary\b", "Intramammary therapy", "Local udder therapy", "Intramammary antibiotic product"),
]


def infer_medication_items(text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for pattern, med_class, med_type, example in DRUG_CLASS_PATTERNS:
        if not re.search(pattern, text, flags=re.IGNORECASE):
            continue
        key = f"{med_class}:{example}"
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "medication_type": med_type,
                "class_or_category": med_class,
                "example_from_knowledge_base": example,
                "dose_status": "Exact drug, dose, route, interval, and duration must be selected and confirmed by the veterinarian.",
            }
        )
    return items


def general_safety_notes(case: dict[str, Any], match: dict[str, Any]) -> list[str]:
    species = str(case.get("species", "")).lower()
    notes = [
        "Do not auto-prescribe. Confirm diagnosis, weight, hydration, pregnancy/lactation, organ status, and contraindications first.",
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
        treatment_text = " ".join(match.get("treatment_principles", []))
        inferred = infer_medication_items(treatment_text)
        if not inferred and treatment_text:
            inferred = [
                {
                    "medication_type": "Condition-specific treatment",
                    "class_or_category": "Veterinarian-selected medication/supportive care",
                    "example_from_knowledge_base": treatment_text,
                    "dose_status": "Exact drug, dose, route, interval, and duration must be selected and confirmed by the veterinarian.",
                }
            ]
        support.append(
            {
                "condition": match.get("condition", "Unknown condition"),
                "score": match.get("score", 0),
                "medication_options": inferred,
                "safety_notes": general_safety_notes(case, match),
                "vet_protocol_needed": "Add a vet-approved medication protocol sheet if exact clinic-specific doses should be displayed.",
            }
        )
    return support