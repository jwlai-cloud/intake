"""Answer-level adjudication — the whole product.

Given one required template item, its human-authored guidance, and the
transcript turns spoken since the item came into scope, decide whether the
item actually received a *substantive answer* — not whether it was mentioned.

The agent never authors domain content (ADR-0006). It returns a verdict, the
verbatim transcript span it relied on, and a list of the guidance elements
still missing. It never invents an answer.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass

from google import genai
from google.genai import types

from .template import Item

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

SYSTEM_INSTRUCTION = """\
You adjudicate whether a required item on a mandated professional form has \
received a substantive answer. You are the second chair to a practitioner \
running a structured interview. You do not conduct the interview and you \
never write domain content.

You are given:
- ITEM: the form item, including its id and prompt.
- GUIDANCE: the human-authored rule for what counts as a sufficient answer to \
this item. This rule is authoritative. It overrides your own intuition about \
what a good answer looks like.
- TRANSCRIPT: the interviewee's turns, in order, spoken since the item came \
into scope.

Return exactly one verdict:

- "sufficient" — every element the GUIDANCE requires is present in the \
transcript. Elements may arrive across several turns; combine them.
- "insufficient" — the item was mentioned, deflected, hedged, partially \
answered, or answered with a vague quantifier where GUIDANCE demands \
specifics. A topic being discussed is not an answer.
- "declined" — the interviewee explicitly refuses to answer, or explicitly \
says they do not know and cannot find out. Only use this for a clear refusal \
or a clear unable-to-answer, not for evasiveness or a change of subject.

Rules:

1. Default to "insufficient". Return "sufficient" only when you can point at \
the words that satisfy each required element. If you are weighing it up, it \
is insufficient.
2. Never infer, extrapolate or fill a gap. "I fell" does not imply a count. \
"I take my tablets" does not imply which tablets. An approximation offered \
where GUIDANCE requires a specific ("a few", "some", "now and then", "a \
couple") is insufficient.
3. A refusal or deflection by the practitioner's own suggestion does not \
count as the interviewee's answer. Only the interviewee's words answer the \
item.
4. `evidence` must be a verbatim substring of the transcript — copy it, do \
not paraphrase. If nothing in the transcript bears on the item, use an empty \
string.
5. `missing` lists, in the GUIDANCE's own terms, the elements not yet \
recorded. Empty when the verdict is "sufficient". This is a description of \
what is absent, never a suggested answer.
6. `reason` is one short sentence for the practitioner, phrased about the \
record, not the person: "no count recorded", not "the client seems confused".
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["sufficient", "insufficient", "declined"],
        },
        "evidence": {
            "type": "string",
            "description": "Verbatim transcript span relied on; empty if none.",
        },
        "missing": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Guidance elements not yet recorded.",
        },
        "reason": {"type": "string"},
    },
    "required": ["verdict", "evidence", "missing", "reason"],
}


@dataclass(frozen=True)
class Verdict:
    verdict: str  # sufficient | insufficient | declined
    evidence: str
    missing: tuple[str, ...]
    reason: str


_client: genai.Client | None = None
_client_lock = threading.Lock()


def get_client() -> genai.Client:
    """The process-wide Vertex AI client (ADR: Vertex, not AI Studio).

    Built under a lock rather than with `lru_cache`: the cache is not atomic, so
    concurrent adjudication threads each construct a Client, and the duplicate
    that loses the race is garbage collected — closing the shared HTTP transport
    out from under every in-flight request. The symptom is a burst of
    "Cannot send a request, as the client has been closed".
    """
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = genai.Client(
                    vertexai=True,
                    project=os.environ["GOOGLE_CLOUD_PROJECT"],
                    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
                )
    return _client


def _prompt(item: Item, turns: list[str]) -> str:
    transcript = "\n".join(f"- {t}" for t in turns)
    return (
        f"ITEM {item.id}: {item.prompt}\n"
        f"answer_type: {item.answer_type}\n"
        f"accepts_declined: {item.accepts_declined}\n\n"
        f"GUIDANCE:\n{item.guidance}\n\n"
        f"TRANSCRIPT (interviewee turns, in order):\n{transcript}\n"
    )


def adjudicate(
    item: Item,
    turns: list[str],
    *,
    model: str = DEFAULT_MODEL,
    client: genai.Client | None = None,
) -> Verdict:
    """Adjudicate one template item against the turns heard so far."""
    resp = (client or get_client()).models.generate_content(
        model=model,
        contents=_prompt(item, turns),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0,
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
        ),
    )
    data = json.loads(resp.text)
    return Verdict(
        verdict=data["verdict"],
        evidence=data.get("evidence", ""),
        missing=tuple(data.get("missing", ())),
        reason=data.get("reason", ""),
    )
