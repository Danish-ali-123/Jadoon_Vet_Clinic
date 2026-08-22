from __future__ import annotations

import os
from functools import lru_cache


DEFAULT_LOCAL_LLM = "HuggingFaceTB/SmolLM2-135M-Instruct"
PUBLIC_MODEL_NOTE = "Local AI assistant active. No API key or token is required."


@lru_cache(maxsize=1)
def load_local_llm():
    try:
        from transformers import pipeline
    except Exception:
        return None, PUBLIC_MODEL_NOTE

    model_name = os.getenv("LOCAL_LLM_MODEL", DEFAULT_LOCAL_LLM)
    try:
        generator = pipeline(
            "text-generation",
            model=model_name,
            tokenizer=model_name,
            max_new_tokens=420,
            return_full_text=False,
        )
        return generator, f"Local Hugging Face LLM active: {model_name}"
    except Exception:
        return None, PUBLIC_MODEL_NOTE


def build_prompt(case: dict, result: dict) -> str:
    matches = result.get("matches", [])[:2]
    medication_support = result.get("medication_support", [])[:2]
    compact_matches = []
    for match in matches:
        compact_matches.append(
            {
                "condition": match.get("condition"),
                "score": match.get("score"),
                "cause": match.get("cause"),
                "red_flags": match.get("red_flags"),
                "diagnostics": match.get("diagnostics"),
                "treatment_principles": match.get("treatment_principles"),
                "clinical_note": match.get("clinical_review_notes"),
            }
        )

    return f"""
You are a veterinary clinical decision-support assistant for a licensed veterinarian.
Write concise, practical English.
First line must say: Recommendation only - the veterinarian must make the final decision.
Do not claim certainty. Do not replace examination, diagnostics, local prescribing rules, or food-animal withdrawal rules.

Patient:
Species: {case.get('species')}
Breed: {case.get('breed')}
Age: {case.get('age')}
Sex: {case.get('sex')}
Pregnancy status: {case.get('pregnancy_status')}
Lactation status: {case.get('lactation_status')}
Weight: {case.get('weight')}
Duration: {case.get('duration')}
Symptoms: {case.get('symptoms')}
Owner description: {case.get('description')}
Vitals/exam: temperature {case.get('temperature')}, stool/urine {case.get('stool')}, notes {case.get('exam_notes')}
Exposure/history: {case.get('exposure')}

Top 2 matched disease candidates:
{compact_matches}

Medication support available to the veterinarian:
{medication_support}

Return these headings:
Recommendation only
Most likely diagnosis
Why it matches
Second condition to rule out
Diagnostics to confirm
Treatment plan principles
Medication recommendation for vet review
Emergency warnings
Owner communication
""".strip()


def deterministic_assessment(case: dict, result: dict, _status: str = "") -> str:
    matches = result.get("matches", [])[:2]
    if not matches:
        return "\n".join(
            [
                "Recommendation only - the veterinarian must make the final decision.",
                "",
                "Most likely diagnosis",
                "- No strong candidate was found from the current notes.",
                "",
                "Next step",
                "- Add more history, symptoms, vitals, physical exam findings, and diagnostic results.",
            ]
        )

    primary = matches[0]
    secondary = matches[1] if len(matches) > 1 else None
    diagnostics = result.get("diagnostics", [])[:5]
    treatment = result.get("treatment_principles", [])[:5]
    warnings = result.get("immediate_actions", [])[:4]
    medication_support = result.get("medication_support", [])[:2]

    lines = [
        "Recommendation only - the veterinarian must make the final decision.",
        "",
        "Most likely diagnosis",
        f"- {primary.get('condition')} ({primary.get('score')}% match)",
        "",
        "Why it matches",
        f"- {primary.get('why', 'Matched from case text and clinical signs.')}",
    ]
    if primary.get("cause"):
        lines.append(f"- Possible cause: {primary.get('cause')}")
    if secondary:
        lines.extend(["", "Second condition to rule out", f"- {secondary.get('condition')} ({secondary.get('score')}% match)"])
    lines.extend(["", "Diagnostics to confirm"])
    lines.extend(f"- {item}" for item in diagnostics)
    lines.extend(["", "Treatment plan principles"])
    lines.extend(f"- {item}" for item in treatment)
    lines.extend(["", "Medication recommendation for vet review"])
    if medication_support:
        for support in medication_support:
            condition = support.get("condition", "Unknown condition")
            options = support.get("medication_options", [])
            if not options:
                lines.append(f"- {condition}: veterinarian-selected medication/supportive care after exam and diagnostics.")
            for option in options:
                lines.append(
                    f"- {condition}: {option.get('example_from_knowledge_base', 'Vet-selected medicine')} | {option.get('class_or_category', 'Vet-selected class')} | {option.get('medication_type', 'Medication')} | {option.get('dose_status', 'Vet must confirm dose, route, interval, and duration.')}"
                )
    else:
        lines.append("- Vet should select medication after exam, diagnostics, weight check, contraindication review, and local label rules.")
    lines.extend(["", "Emergency warnings"])
    lines.extend(f"- {item}" for item in warnings)
    lines.extend(["", "Owner communication", "- Explain that this is a suspected differential and medication plan for veterinarian review, not an automatic final prescription."])
    return "\n".join(lines)


def is_usable_generated_text(text: str) -> bool:
    lowered = text.lower().strip()
    if len(lowered) < 120:
        return False
    bad_fragments = [
        "guidelines",
        "what is the most likely diagnosis",
        "patient's symptoms?",
        "unknown task",
        "could not load",
        "traceback",
    ]
    if any(fragment in lowered for fragment in bad_fragments):
        return False
    required = ["most likely", "diagnostics", "treatment", "medication"]
    return sum(1 for term in required if term in lowered) >= 3


def clean_generated_text(text: str) -> str:
    text = text.strip()
    marker = "Recommendation only"
    if marker in text:
        text = text[text.find(marker) :]
    if not text.startswith(marker):
        text = "Recommendation only - the veterinarian must make the final decision.\n\n" + text
    return text


def generate_local_llm_assessment(case: dict, result: dict) -> tuple[str, str]:
    generator, status = load_local_llm()
    if generator is None:
        return deterministic_assessment(case, result, status), status

    prompt = build_prompt(case, result)
    try:
        output = generator(prompt, do_sample=False, truncation=True)
        text = output[0].get("generated_text", "").strip()
        if not text or len(text) < 40:
            return deterministic_assessment(case, result, status), status
        return clean_generated_text(text), status
    except Exception:
        return deterministic_assessment(case, result, status), status