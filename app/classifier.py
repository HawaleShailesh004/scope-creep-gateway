import json

import os



import anthropic



_client: anthropic.Anthropic | None = None



SYSTEM = """You are a scope-detection classifier for a freelance project.

You are given (1) the agreed project brief and (2) a new message from the CLIENT.

Decide whether the message is requesting work that is OUTSIDE the agreed scope.



Rules:

- IN_SCOPE: clarifications, questions, feedback, or requests clearly covered by a deliverable.

- OUT_OF_SCOPE: a NEW deliverable, feature, or task not covered by the brief.

- AMBIGUOUS: plausibly new work but under-specified.

- REVISION: feedback on an existing deliverable (colors, copy tweaks, sizing) — set is_revision_request=true.

- Be conservative. A false "out of scope" accusation damages the freelancer's

  client relationship, so only mark OUT_OF_SCOPE when you are confident it is

  genuinely new work. When unsure, prefer AMBIGUOUS.



Size (for OUT_OF_SCOPE only):

- trivial: tiny tweak on unrelated item, or negligible effort ("make logo 2px bigger" when logo not in scope)

- small: minor add-on under ~1 hour ("tweak the footer link")

- significant: clear new feature ("add a blog section")

- major: large new subsystem ("build checkout flow")



Few-shot examples:

- "can you make the logo bigger" (logo is in scope) → IN_SCOPE, is_revision_request=true

- "can you also add a blog section" → OUT_OF_SCOPE, size=significant

- "what font did you use" → IN_SCOPE

- "while you're at it, maybe a dark mode?" → OUT_OF_SCOPE, size=major

- "can we tweak the colors" (colors in scope) → IN_SCOPE, is_revision_request=true

- "can you change the hero headline" (homepage in scope) → IN_SCOPE, is_revision_request=true

- "maybe move the contact form to the sidebar" → OUT_OF_SCOPE, size=small



Return ONLY strict JSON, no prose:

{"verdict": "IN_SCOPE|OUT_OF_SCOPE|AMBIGUOUS",

 "confidence": 0.0-1.0,

 "size": "trivial|small|significant|major",

 "estimated_value": 0,

 "estimated_hours": 0,

 "is_revision_request": false,

 "target_deliverable": "which deliverable for revisions, or null",

 "matched_deliverable": "which brief item it relates to, or null",

 "new_task_summary": "short label if out of scope, else null",

 "rationale": "one sentence"}"""



CLASSIFIER_MODEL = "claude-sonnet-4-6"

FLAG_THRESHOLD = 0.8





def _get_client() -> anthropic.Anthropic:

    global _client

    if _client is None:

        api_key = os.environ.get("ANTHROPIC_API_KEY")

        if not api_key:

            raise RuntimeError("ANTHROPIC_API_KEY must be set in .env")

        _client = anthropic.Anthropic(api_key=api_key)

    return _client





from services.message_text import truncate_for_classifier





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



    resp = _get_client().messages.create(

        model=CLASSIFIER_MODEL,

        max_tokens=500,

        temperature=0,

        system=SYSTEM,

        messages=[{"role": "user", "content": user}],

    )

    text = resp.content[0].text.strip()

    text = text.replace("```json", "").replace("```", "").strip()

    result = json.loads(text)

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

