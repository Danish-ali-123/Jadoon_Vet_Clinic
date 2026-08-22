from __future__ import annotations

import csv
import math
import re
import socket
from functools import lru_cache
from pathlib import Path


DATA_PATH = Path(__file__).parent / "Raw Data" / "vet_doc_assistant_disease_kb_v1.csv"

SPECIES_OPTIONS = [
    "Cow",
    "Buffalo",
    "Cattle",
    "Dog",
    "Cat",
    "Goat",
    "Sheep",
    "Chicken",
    "Horse",
    "Camel",
    "Rabbit",
    "Other",
]

SPECIES_ALIASES = {
    "cow": "cattle",
    "buffalo": "cattle",
    "cattle": "cattle",
    "calf": "cattle",
    "bull": "cattle",
    "dog": "dog",
    "puppy": "dog",
    "cat": "cat",
    "kitten": "cat",
    "goat": "goat",
    "sheep": "sheep",
    "chicken": "poultry",
    "hen": "poultry",
    "poultry": "poultry",
    "horse": "horse",
    "camel": "camel",
    "rabbit": "rabbit",
}

DOSE_PATTERN = re.compile(
    r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml|iu|units?)\s*/?\s*(kg|lb|animal|day|dose)?\b",
    flags=re.IGNORECASE,
)


def canonical_species(value: str) -> str:
    return SPECIES_ALIASES.get(value.lower().strip(), value.lower().strip())


def split_pipe(value: str) -> list[str]:
    return [part.strip() for part in value.split("|") if part.strip()]


def row_species_values(value: str) -> set[str]:
    species = set()
    for item in re.split(r"[;/,]", value):
        canonical = canonical_species(item.strip())
        if canonical:
            species.add(canonical)
    return species


def sanitize_treatment(text: str) -> str:
    return DOSE_PATTERN.sub("[dose removed for vet validation]", text).strip()


def can_reach_huggingface() -> bool:
    try:
        with socket.create_connection(("huggingface.co", 443), timeout=2):
            return True
    except OSError:
        return False


def tokenize(text: str) -> set[str]:
    stop_words = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "by",
        "for",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in stop_words
    }


@lru_cache(maxsize=1)
def load_disease_rows() -> list[dict]:
    if not DATA_PATH.exists():
        return []

    with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    for row in rows:
        row["species_set"] = row_species_values(row.get("species", ""))
        row["sign_list"] = split_pipe(row.get("signs", ""))
        row["diagnosis_list"] = split_pipe(row.get("diagnosis", ""))
        row["red_flag_list"] = split_pipe(row.get("red_flags", ""))
        row["search_text"] = " ".join(
            [
                row.get("species", ""),
                row.get("category", ""),
                row.get("disease", ""),
                row.get("aliases", ""),
                row.get("cause", ""),
                row.get("signs", ""),
                row.get("diagnosis", ""),
                row.get("red_flags", ""),
            ]
        )
        row["tokens"] = tokenize(row["search_text"])
    return rows


def keyword_score(case_text: str, row: dict) -> float:
    case_tokens = tokenize(case_text)
    if not case_tokens or not row["tokens"]:
        return 0.0

    overlap = case_tokens & row["tokens"]
    if not overlap:
        return 0.0

    precision = len(overlap) / max(len(case_tokens), 1)
    recall = len(overlap) / max(len(row["tokens"]), 1)
    f_score = (2 * precision * recall) / max(precision + recall, 0.0001)
    sign_bonus = sum(1 for sign in row["sign_list"] if sign.lower() in case_text.lower()) * 0.05
    return min(1.0, f_score + sign_bonus)


@lru_cache(maxsize=1)
def semantic_resources():
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None

    rows = load_disease_rows()
    if not rows:
        return None

    try:
        model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2",
            local_files_only=not can_reach_huggingface(),
        )
        documents = [row["search_text"] for row in rows]
        embeddings = model.encode(documents, normalize_embeddings=True)
    except Exception:
        return None

    return model, embeddings


def semantic_scores(case_text: str) -> list[float] | None:
    resources = semantic_resources()
    if not resources:
        return None

    model, embeddings = resources
    query_embedding = model.encode([case_text], normalize_embeddings=True)[0]
    return [float(sum(a * b for a, b in zip(query_embedding, doc_embedding))) for doc_embedding in embeddings]


def species_score(input_species: str, row: dict) -> float:
    selected = canonical_species(input_species)
    row_species = row.get("species_set", set())
    if not selected or selected == "other":
        return 0.15
    if selected in row_species:
        return 0.2
    return -0.25


def build_case_text(case: dict) -> str:
    parts = [
        f"Species: {case.get('species', '')}",
        f"Animal subtype: {case.get('animal_subtype', '')}",
        f"Breed: {case.get('breed', '')}",
        f"Age: {case.get('age', '')}",
        f"Sex: {case.get('sex', '')}",
        f"Pregnancy status: {case.get('pregnancy_status', '')}",
        f"Lactation status: {case.get('lactation_status', '')}",
        f"Body condition: {case.get('body_condition', '')}",
        f"Vaccination: {case.get('vaccination', '')}",
        f"Deworming: {case.get('deworming', '')}",
        f"Duration: {case.get('duration', '')}",
        f"Appetite: {case.get('appetite', '')}",
        f"Water intake: {case.get('water', '')}",
        f"Temperature: {case.get('temperature', '')}",
        f"Heart rate: {case.get('heart_rate', '')}",
        f"Respiratory rate: {case.get('respiratory_rate', '')}",
        f"Number affected: {case.get('number_affected', '')}",
        f"Exposure history: {case.get('exposure', '')}",
        f"Symptoms: {case.get('symptoms', '')}",
        f"Stool or urine: {case.get('stool', '')}",
        f"Physical exam: {case.get('exam_notes', '')}",
        f"Owner description: {case.get('description', '')}",
    ]
    return ". ".join(part for part in parts if part.strip())


def match_diseases(case: dict, limit: int = 2) -> tuple[list[dict], str]:
    rows = load_disease_rows()
    case_text = build_case_text(case)
    semantic = semantic_scores(case_text) if case.get("use_pretrained_model") else None
    method = (
        "Pretrained semantic model + veterinary CSV knowledge base"
        if semantic
        else "Keyword matching + veterinary CSV knowledge base"
    )

    scored_rows = []
    for index, row in enumerate(rows):
        semantic_part = max(0.0, semantic[index]) if semantic else 0.0
        keyword_part = keyword_score(case_text, row)
        combined = (semantic_part * 0.65 + keyword_part * 0.35) if semantic else keyword_part
        combined += species_score(case.get("species", ""), row)
        if combined <= 0:
            continue
        scored_rows.append((combined, row, semantic_part, keyword_part))

    scored_rows.sort(key=lambda item: item[0], reverse=True)
    matches = []
    for combined, row, semantic_part, keyword_part in scored_rows[:limit]:
        score = max(1, min(100, math.floor(combined * 100)))
        matches.append(
            {
                "record_id": row.get("record_id", ""),
                "condition": row.get("disease", ""),
                "category": row.get("category", ""),
                "species": row.get("species", ""),
                "score": score,
                "why": "Matched against signs and case text from the veterinary CSV knowledge base.",
                "semantic_score": round(semantic_part, 3),
                "keyword_score": round(keyword_part, 3),
                "cause": row.get("cause", ""),
                "signs": row["sign_list"],
                "diagnostics": row["diagnosis_list"],
                "treatment_principles": [sanitize_treatment(row.get("treatment_raw", ""))],
                "prevention": row.get("prevention", ""),
                "red_flags": row["red_flag_list"],
                "zoonotic": row.get("zoonotic", ""),
                "emergency": row.get("emergency", ""),
                "clinical_review_status": row.get("clinical_review_status", ""),
                "clinical_review_notes": row.get("clinical_review_notes", ""),
                "source_type": row.get("source_type", ""),
            }
        )
    return matches, method

