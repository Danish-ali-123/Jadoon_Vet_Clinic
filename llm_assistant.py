from __future__ import annotations

import os
from typing import Any

import requests


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"


def configured_providers() -> list[str]:
    providers = ["Rule-based only"]
    if os.getenv("GROQ_API_KEY"):
        providers.append("Groq free tier")
    if os.getenv("HF_TOKEN"):
        providers.append("Hugging Face free tier")
    return providers


def provider_help_text() -> str:
    missing = []
    if not os.getenv("GROQ_API_KEY"):
        missing.append("GROQ_API_KEY")
    if not os.getenv("HF_TOKEN"):
        missing.append("HF_TOKEN")
    if not missing:
        return "External LLM providers are configured."
    return "Optional LLMs need Streamlit secrets: " + ", ".join(missing)


def build_messages(case: dict, result: dict) -> list[dict[str, str]]:
    compact_matches = [
        {
            "condition": match.get("condition"),
            "score": match.get("score"),
            "cause": match.get("cause"),
            "red_flags": match.get("red_flags"),
            "diagnostics": match.get("diagnostics"),
            "treatment": match.get("treatment_principles"),
            "clinical_note": match.get("clinical_review_notes"),
        }
        for match in result.get("matches", [])[:5]
    ]
    system = """
You assist a licensed veterinarian as a decision-support tool.
Never claim a final diagnosis.
Never give drug dosages.
Never replace a physical exam, local regulations, or veterinarian judgment.
For food animals, mention withdrawal-period and local regulatory review when medicines are considered.
Prefer concise, practical reasoning and separate emergency warnings from routine advice.
"""
    user = f"""
Case input:
{case}

Knowledge-base matches:
{compact_matches}

Return these sections:
1. Most likely differentials
2. Reasoning
3. Emergency concerns
4. Diagnostics to confirm
5. Treatment principles for veterinarian review
6. Owner-friendly explanation
"""
    return [{"role": "system", "content": system.strip()}, {"role": "user", "content": user.strip()}]


def parse_chat_response(payload: dict[str, Any]) -> str:
    try:
        return payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        return f"LLM response could not be parsed: {payload}"


def call_groq(case: dict, result: dict) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "GROQ_API_KEY is not configured in Streamlit secrets."

    model = os.getenv("GROQ_MODEL", "groq/compound-mini")
    response = requests.post(
        GROQ_API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": build_messages(case, result),
            "temperature": 0.2,
            "max_completion_tokens": 900,
            "citation_options": "enabled",
        },
        timeout=45,
    )
    if response.status_code >= 400:
        return f"Groq request failed ({response.status_code}): {response.text[:800]}"
    return parse_chat_response(response.json())


def call_huggingface(case: dict, result: dict) -> str:
    token = os.getenv("HF_TOKEN")
    if not token:
        return "HF_TOKEN is not configured in Streamlit secrets."

    model = os.getenv("HF_MODEL", "deepseek-ai/DeepSeek-R1:fastest")
    response = requests.post(
        HF_API_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": build_messages(case, result),
            "temperature": 0.2,
            "max_tokens": 900,
        },
        timeout=60,
    )
    if response.status_code >= 400:
        return f"Hugging Face request failed ({response.status_code}): {response.text[:800]}"
    return parse_chat_response(response.json())


def generate_llm_assessment(case: dict, result: dict, provider: str) -> str:
    if provider == "Groq free tier":
        return call_groq(case, result)
    if provider == "Hugging Face free tier":
        return call_huggingface(case, result)
    return "No external LLM selected. The assessment above used the local veterinary knowledge base."
