from __future__ import annotations

import os
from functools import lru_cache


DEFAULT_LOCAL_LLM = "google/flan-t5-small"


@lru_cache(maxsize=1)
def load_local_llm():
    try:
        from transformers import pipeline
    except Exception as exc:
        return None, f"Transformers is not available: {exc}"

    model_name = os.getenv("LOCAL_LLM_MODEL", DEFAULT_LOCAL_LLM)
    try:
        generator = pipeline(
            "text2text-generation",
            model=model_name,
            tokenizer=model_name,
            max_new_tokens=360,
        )
        return generator, f"Local Hugging Face LLM loaded: {model_name}"
    except Exception as exc:
        return None, f"Local Hugging Face LLM could not load: {exc}"


def build_prompt(case: dict, result: dict) -> str:
    matches = result.get("matches", [])[:2]
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
You are a careful veterinary decision-support assistant. Do not claim certainty. Do not give drug dosages. Do not replace a veterinarian examination.

Patient:
Species: {case.get('species')}
Breed: {case.get('breed')}
Age: {case.get('age')}
Sex: {case.get('sex')}
Pregnancy status: {case.get('pregnancy_status')}
Lactation status: {case.get('lactation_status')}
Duration: {case.get('duration')}
Symptoms: {case.get('symptoms')}
Owner description: {case.get('description')}
Vitals/exam: temperature {case.get('temperature')}, stool/urine {case.get('stool')}, notes {case.get('exam_notes')}
Exposure/history: {case.get('exposure')}

Top 2 matched disease candidates:
{compact_matches}

Write a concise veterinary assistant assessment with these headings:
Most likely diagnosis
Why it matches
Second condition to rule out
Diagnostics to confirm
Treatment plan principles
Emergency warnings
Owner communication
""".strip()


def deterministic_assessment(case: dict, result: dict, status: str) -> str:
    matches = result.get("matches", [])[:2]
    if not matches:
        return f"Local LLM unavailable. {status}\n\nNo strong candidate was found. Add more history, symptoms, vitals, and exam findings."

    primary = matches[0]
    secondary = matches[1] if len(matches) > 1 else None
    diagnostics = result.get("diagnostics", [])[:5]
    treatment = result.get("treatment_principles", [])[:5]
    warnings = result.get("immediate_actions", [])[:4]

    lines = [
        f"Local LLM unavailable, so this structured local assessment was generated from the pretrained matcher and CSV knowledge base. {status}",
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
    lines.extend(["", "Emergency warnings"])
    lines.extend(f"- {item}" for item in warnings)
    lines.extend(["", "Owner communication", "- Explain that this is a suspected differential, not a final diagnosis, and confirmation requires veterinarian examination and appropriate tests."])
    return "\n".join(lines)


def generate_local_llm_assessment(case: dict, result: dict) -> tuple[str, str]:
    generator, status = load_local_llm()
    if generator is None:
        return deterministic_assessment(case, result, status), status

    prompt = build_prompt(case, result)
    try:
        output = generator(prompt, do_sample=False, truncation=True)
        text = output[0].get("generated_text", "").strip()
        if not text:
            return deterministic_assessment(case, result, "The local LLM returned an empty response."), status
        return text, status
    except Exception as exc:
        fallback_status = f"Local LLM generation failed: {exc}"
        return deterministic_assessment(case, result, fallback_status), fallback_status
