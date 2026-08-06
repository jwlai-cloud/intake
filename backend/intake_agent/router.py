"""Which open items does this chunk actually bear on?

Without this, every open item is adjudicated against every chunk, and each one
independently decides whether a vague remark is relevant to it. A sentence about
falls is weakly relevant to mobility, to memory, to mood, to the reason for
referral — so the quote ends up attached to five items and the practitioner sees
"a couple of wobbles" quoted underneath *low mood*.

Routing first fixes that at the source and is cheaper: one small call replaces
N-minus-a-few large ones.

It is deliberately recall-biased. Missing an item costs a chunk's delay — the
item stays open and the next chunk sees it again through the rolling turn
window. Including one costs a single adjudication call that returns
`addressed: false`. Those are not symmetric, so when in doubt the router
includes.
"""

from __future__ import annotations

import json
import logging

from google import genai
from google.genai import types

from .adjudicator import DEFAULT_MODEL, get_client
from .template import Item

log = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """\
You route turns of an interview to the items of a form.

Given what the interviewee just said and a list of open form items, return the \
ids of the items these turns bear on — the ones where a person reading the \
turns would say "that is about this item", even if the answer given is vague, \
partial or evasive.

Include an item when the turns are on its topic at all, including a refusal to \
answer it or a deflection away from it. Do not include an item merely because \
its topic is adjacent: a remark about falls is not about continence, memory, \
mood or alcohol. If nothing bears on any item, return an empty list — that is \
a normal outcome for most chunks.

Judge only what the turns are about. Do not judge whether the answer is any \
good; something else does that."""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "item_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["item_ids"],
}


def route(items: list[Item], turns: list[str], *, model: str = DEFAULT_MODEL,
          client: genai.Client | None = None) -> list[Item]:
    """The subset of `items` these turns bear on.

    Fails open: any error returns every item, so a routing outage degrades to
    the old, more expensive behaviour rather than to silently skipping the
    interview's coverage.
    """
    if not items or not turns:
        return []

    listing = "\n".join(f"- {i.id}: {i.prompt}" for i in items)
    transcript = "\n".join(f"- {t}" for t in turns)
    prompt = (f"OPEN ITEMS:\n{listing}\n\n"
              f"INTERVIEWEE TURNS:\n{transcript}\n")

    try:
        resp = (client or get_client()).models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0,
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
            ),
        )
        wanted = set(json.loads(resp.text).get("item_ids", []))
    except Exception as exc:
        log.warning("routing failed (%s) — adjudicating every open item",
                    type(exc).__name__)
        return list(items)

    # The router may only select from what it was given; it cannot invent an id.
    return [i for i in items if i.id in wanted]
