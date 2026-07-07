import json
import os

from groq import Groq

from services.classifier_prompts import PROMPT_VERSIONS
from services.message_text import truncate_for_classifier

_client: Groq | None = None

SYSTEM = PROMPT_VERSIONS["v3"]
CLASSIFIER_MODEL = "llama-3.3-70b-versatile"
FLAG_THRESHOLD = 0.8


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY must be set in .env")
        _client = Groq(api_key=api_key)
    return _client


def _parse_classifier_json(text: str) -> dict:
    text = text.strip().replace("```json", "").replace("```", "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Classifier returned no JSON: {text[:160]}")
    return json.loads(text[start : end + 1])


def classify(
    brief_markdown: str,
    deliverables: list[str],
    client_message: str,
    exclusions: list[str] | None = None,
) -> dict:
    client_message = truncate_for_classifier(client_message)
    exclusion_block = ""
    if exclusions:
        exclusion_block = (
            "\n\nEXPLICITLY OUT OF SCOPE (noted at kickoff — high confidence if matched):\n"
            + "\n".join("- " + e for e in exclusions)
        )

    user = f"""PROJECT BRIEF:

{brief_markdown}

DELIVERABLES (in scope):

{chr(10).join("- " + d for d in deliverables)}
{exclusion_block}

NEW CLIENT MESSAGE:

"{client_message}"

Classify it. If the message clearly matches an exclusion, prefer OUT_OF_SCOPE with high confidence."""

    resp = _get_client().chat.completions.create(
        model=CLASSIFIER_MODEL,
        max_tokens=500,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
    )

    text = resp.choices[0].message.content or ""
    result = _parse_classifier_json(text)
    result.setdefault("size", "significant")
    result.setdefault("estimated_value", 0)
    result.setdefault("estimated_hours", 0)
    result.setdefault("is_revision_request", False)
    return result


def should_flag(result: dict, threshold: float = FLAG_THRESHOLD) -> bool:
    return (
        result.get("verdict") == "OUT_OF_SCOPE"
        and float(result.get("confidence", 0)) >= threshold
    )
