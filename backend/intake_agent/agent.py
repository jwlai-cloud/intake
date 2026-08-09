"""The ADK agent that runs one interview turn.

One audio chunk in, one bounded turn of work out. The pipeline is a custom
`BaseAgent` (`TurnPipeline`, below) running three stages in order:

    transcribe → adjudicate (custom BaseAgent, fans out) → coach

Only the middle stage is ours rather than an LLM call, and it is the one that
matters: it adjudicates every open item independently and folds the verdicts
into Firestore. Scoping adjudication per item is what stops a wrong verdict on
one item from corrupting another, and it is why the coach stage can be given a
short, factual brief instead of the whole transcript.

**The slot state is the state, not the transcript** (ADR-0002). Each turn sends
the model only the open items and the new audio, so context is bounded and a
three-hour interview costs the same per chunk as a ten-minute one.

Verified against google-adk 2.6.2: custom agents subclass `BaseAgent` and
override `_run_async_impl`; there is no `BaseNode`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .adjudicator import DEFAULT_MODEL, adjudicate
from .router import route
from .store import ANSWERED, BaseStore, SessionState

log = logging.getLogger(__name__)

APP_NAME = "intake"

# --- stage 1: transcription --------------------------------------------------

TRANSCRIBE_SCHEMA = {
    "type": "object",
    "properties": {
        "turns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "speaker": {"type": "string", "enum": ["practitioner", "interviewee"]},
                    "text": {"type": "string"},
                },
                "required": ["speaker", "text"],
            },
        }
    },
    "required": ["turns"],
}

def make_transcriber(model: str = DEFAULT_MODEL) -> LlmAgent:
    """A fresh instance per pipeline: an ADK agent may only have one parent."""
    return LlmAgent(
        name="transcriber",
        model=model,
        description="Transcribes one audio chunk into speaker-attributed turns.",
        instruction=(
            "Transcribe the audio verbatim into turns. Label each turn "
            "`practitioner` (the professional asking the questions) or "
            "`interviewee` (the person answering). Transcribe what was said, "
            "including hedges and false starts — do not tidy the speech up, "
            "because whether an answer was vague is exactly what is being judged "
            "downstream. Never invent a turn. If the audio contains no speech, "
            "return an empty list."
        ),
        output_schema=TRANSCRIBE_SCHEMA,
        output_key="transcript",
        )

# --- stage 3: coaching -------------------------------------------------------

COACH_SCHEMA = {
    "type": "object",
    "properties": {
        "next_question": {
            "type": "object",
            "properties": {
                "item_id": {"type": "string"},
                "prompt": {"type": "string"},
                "why": {"type": "string"},
            },
            "required": ["item_id", "prompt", "why"],
        },
        "highlights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                    "title": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["item_id", "title", "quote"],
            },
        },
    },
    "required": ["next_question", "highlights"],
}

def make_coach(model: str = DEFAULT_MODEL) -> LlmAgent:
    return LlmAgent(
        name="coach",
        model=model,
        description="Proposes the next question to ask and highlights worth keeping.",
        instruction=(
            "You are the practitioner's second chair. You are given a BRIEF listing "
            "the items that still lack a recorded answer, what each one is missing, "
            "and the verbatim quotes captured in the last chunk.\n\n"
            "Produce:\n"
            "1. `next_question` — the single question the practitioner should ask "
            "next, phrased naturally enough to say out loud, targeting the highest "
            "item in the brief. `why` states which element of the guidance it "
            "closes, in one short clause.\n"
            "2. `highlights` — quotes from this chunk worth surfacing, each with the "
            "item it bears on. Quote verbatim. Empty list if nothing is worth "
            "surfacing. `title` must be a plain noun phrase naming the topic and "
            "nothing more — \"Falls\", \"Alcohol intake\", \"Medication adherence\". "
            "It is a label, not a finding: never characterise the answer, the "
            "person, or what the quote implies. \"Formal decline to answer\" and "
            "\"Reluctant about alcohol\" are both wrong; \"Alcohol intake\" is "
            "right.\n\n"
            "Hard rules. You ask questions; you never write answers. Never suggest "
            "what the interviewee might have meant, never propose wording for an "
            "item, and never state a professional judgement about the person. For "
            "an item the brief marks HIGH RISK, ask the question and stop — offer "
            "nothing else about it. Do not invent a quote: every quote must appear "
            "verbatim in the brief.\n\n"
            "BRIEF:\n{coach_brief}"
        ),
        output_schema=COACH_SCHEMA,
        output_key="coaching",
        )


# --- stage 2: adjudication (the product) -------------------------------------


class AdjudicationAgent(BaseAgent):
    """Adjudicates every open required item against the new turns, in parallel.

    Not an LlmAgent: the judgement is one constrained call per item, and one
    item's verdict must never be able to influence another's. Fanning out keeps
    the per-item contract and keeps the turn's latency at roughly one call
    rather than N.
    """

    store: Any = None
    model: str = DEFAULT_MODEL

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        session_id = state["intake_session_id"]
        transcript = state.get("transcript") or {}
        if isinstance(transcript, str):  # a model that ignored the schema
            transcript = _loads(transcript)

        turns = [t["text"] for t in transcript.get("turns", [])
                 if t.get("speaker") == "interviewee" and t.get("text", "").strip()]

        session = self.store.get(session_id)
        open_items = [session.template[i] for i in session.outstanding_ids()]
        relevant_ids: list[str] = []
        updated: list[str] = []

        # Deliberately explicit. These lines are the audit trail for what the
        # agent did, and they are also what proves — in Cloud Logging, from the
        # deployed service — that this is an ADK pipeline calling Gemini on
        # Vertex AI, rather than a claim in a README.
        #
        # Item ids, verdicts and timings only. Never transcript text: a Vertex
        # error once echoed interviewee speech into these logs, and Cloud
        # Logging outlives the session document (ADR-0007).
        turn_t0 = time.monotonic()
        log.info("ADK turn · session %s · stage=adjudication · %d open items · "
                 "model=%s via Vertex AI",
                 session_id[:8], len(open_items), self.model)

        if turns and open_items:
            session = self.store.append_turns(session_id, turns)
            heard = session.recent_turns

            # Route before adjudicating: one small call decides which items this
            # chunk is even about, so a remark about falls is not judged against
            # continence and cannot leave its quote there.
            route_t0 = time.monotonic()
            relevant = await asyncio.to_thread(
                route, open_items, turns, model=self.model)
            relevant_ids = [i.id for i in relevant]
            log.info("  route      · 1 Gemini call (%s) · %.1fs · "
                     "%d of %d items in play: %s",
                     self.model, time.monotonic() - route_t0,
                     len(relevant), len(open_items), relevant_ids)

            adj_t0 = time.monotonic()
            verdicts = await asyncio.gather(*[
                asyncio.to_thread(adjudicate, item, heard, model=self.model)
                for item in relevant
            ], return_exceptions=True)
            log.info("  adjudicate · %d Gemini call%s (%s)%s · %.1fs",
                     len(relevant), "" if len(relevant) == 1 else "s", self.model,
                     " in parallel" if len(relevant) > 1 else "",
                     time.monotonic() - adj_t0)

            for item, verdict in zip(relevant, verdicts):
                if isinstance(verdict, Exception):
                    # One item failing must not lose the whole chunk. The item
                    # simply stays open and the next chunk retries it.
                    log.warning("adjudication failed for %s (%s)",
                                item.id, type(verdict).__name__)
                    continue
                if not verdict.addressed:
                    continue  # this chunk said nothing about the item
                after = self.store.apply_verdict(
                    session_id, item.id, verdict.verdict,
                    value=verdict.evidence, evidence=verdict.evidence,
                    missing=list(verdict.missing), reason=verdict.reason,
                )
                state_now = after.slots[item.id]["state"]
                updated.append(f"{item.id}={state_now}")
                log.info("             %s · %s → %s", item.id,
                         verdict.verdict, state_now)

        session = self.store.get(session_id)
        brief = build_coach_brief(session, turns)
        resolved, required = session.coverage()

        # The event carries content as well as the state delta. An event with
        # only a state_delta is invisible to anything reading the trace — ADK's
        # eval tooling rejects it outright as "missing content", and it does not
        # show up in `adk web` either. The text is the audit line for this turn.
        summary = (
            f"Adjudicated {len(relevant_ids)} of {len(open_items)} open items "
            f"against {len(turns)} interviewee turn(s). "
            f"Coverage {resolved}/{required}."
            + (f" Updated: {', '.join(updated)}." if updated else " No item changed state.")
        )

        log.info("ADK turn · session %s · done in %.1fs · coverage %d/%d · %s",
                 session_id[:8], time.monotonic() - turn_t0, resolved, required,
                 ", ".join(updated) or "no item changed state")

        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            branch=ctx.branch,
            content=types.Content(role="model",
                                  parts=[types.Part.from_text(text=summary)]),
            actions=EventActions(state_delta={
                "coach_brief": brief,
                "heard_turns": turns,
            }),
        )


def build_coach_brief(session: SessionState, turns: list[str]) -> str:
    """A short factual brief. Never the transcript — that is the point of ADR-0002."""
    lines = []
    resolved, total = session.coverage()
    lines.append(f"Coverage: {resolved} of {total} required items resolved.")

    lines.append("\nItems still without a recorded answer, most nearly complete first:")
    outstanding = session.outstanding_ids()
    ordered = sorted(
        outstanding,
        key=lambda i: (session.slots.get(i, {}).get("state") != "partial", i),
    )
    for item_id in ordered:
        item = session.template[item_id]
        slot = session.slots.get(item_id, {})
        risk = " [HIGH RISK — ask the question and offer nothing else]" if item.high_risk else ""
        lines.append(f"- {item.id}: {item.prompt}{risk}")
        lines.append(f"    guidance: {item.guidance}")
        if slot.get("missing"):
            lines.append(f"    still missing: {'; '.join(slot['missing'])}")
        if slot.get("evidence"):
            lines.append(f"    heard so far: \"{slot['evidence']}\"")

    if not outstanding:
        lines.append("- none. Every required item has a recorded resolution.")

    lines.append("\nVerbatim interviewee turns from this chunk:")
    lines.extend(f'- "{t}"' for t in turns) if turns else lines.append("- (none)")
    return "\n".join(lines)


def _loads(raw: str) -> dict:
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {}


# --- the pipeline ------------------------------------------------------------


class TurnPipeline(BaseAgent):
    """Runs the three stages in order, forwarding each stage's events.

    This was a `SequentialAgent`. It is hand-rolled because both of ADK's own
    orchestration primitives emit events that ADK's own eval CLI rejects.

    `agents-cli eval generate` raises on any event lacking `author` or
    `content`, and it parses the whole SSE stream in one comprehension — so the
    first such event fails the entire eval case. `SequentialAgent` emits a
    container event carrying only `actions`. The graph `Workflow` emits
    `Event(output=...)` with no `content` for node-to-node data passing, and so
    fails identically (measured — see ADR-0013).

    A custom `BaseAgent` is not deprecated in 2.6.2 and is the only one of the
    three where every emitted event is one we deliberately wrote. Sequential
    composition is a four-line loop, so owning it costs nothing.

    ADR-0008 claimed the graph migration was blocked because `Workflow` cannot
    take an `LlmAgent` as a sub-agent. That was a misreading of the deprecation
    warning, which says the reverse; ADR-0013 corrects it.
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        for stage in self.sub_agents:
            async for event in stage.run_async(ctx):
                yield event


def build_root_agent(store: BaseStore, model: str = DEFAULT_MODEL) -> TurnPipeline:
    return TurnPipeline(
        name="intake_turn",
        description="Transcribe one chunk, adjudicate every open item, coach the next question.",
        sub_agents=[
            make_transcriber(model),
            AdjudicationAgent(name="adjudication", store=store, model=model),
            make_coach(model),
        ],
    )


class TurnRunner:
    """Runs one chunk through the pipeline and returns the updated session.

    ADK's session service holds only the scratch state of a single turn.
    Durable state is ours, in Firestore (ADR-0004), so a Cloud Run instance
    recycling mid-interview costs nothing.
    """

    def __init__(self, store: BaseStore, model: str = DEFAULT_MODEL) -> None:
        self.store = store
        self.runner = Runner(
            app_name=APP_NAME,
            agent=build_root_agent(store, model),
            session_service=InMemorySessionService(),
        )

    async def run_turn(self, session_id: str, *, audio: bytes | None = None,
                       mime_type: str = "audio/webm",
                       text: str | None = None) -> SessionState:
        session = self.store.get(session_id)

        if audio is not None:
            part = types.Part.from_bytes(data=audio, mime_type=mime_type)
        elif text is not None:
            # Text path: used by the eval harness, tests, and the demo's typed
            # fallback when a venue's microphone is not usable.
            part = types.Part.from_text(text=text)
        else:
            raise ValueError("run_turn needs audio or text")

        adk_session = await self.runner.session_service.create_session(
            app_name=APP_NAME,
            user_id=session.practitioner_id,
            state={"intake_session_id": session_id, "coach_brief": ""},
        )

        coaching = None
        async for event in self.runner.run_async(
            user_id=session.practitioner_id,
            session_id=adk_session.id,
            new_message=types.Content(role="user", parts=[part]),
        ):
            if event.author == "coach" and event.content and event.content.parts:
                coaching = _loads(event.content.parts[0].text or "")

        if coaching:
            self._record_coaching(session_id, coaching)
        return self.store.get(session_id)

    def _record_coaching(self, session_id: str, coaching: dict) -> None:
        session = self.store.get(session_id)
        nq = coaching.get("next_question") or None
        if nq and nq.get("item_id") in session.slots:
            self.store.set_next_question(session_id, nq)

        highlights = []
        for n, h in enumerate(coaching.get("highlights") or []):
            if h.get("item_id") not in session.template.items:
                continue  # the coach may not invent items
            highlights.append({
                # Not count-based: add_highlights dedupes on quote, so the
                # count after a batch is not len(before) + n, and a later batch
                # could mint an id that already exists. set_highlight_status
                # updates every match, so one confirm would confirm two.
                "id": uuid.uuid4().hex[:8],
                "item_id": h["item_id"],
                "title": h.get("title", ""),
                "quote": h.get("quote", ""),
                "status": "proposed",
            })
        if highlights:
            self.store.add_highlights(session_id, highlights)


# --- escalation: the autonomous execution beat (ADR-0005) --------------------

ESCALATION_SCHEMA = {
    "type": "object",
    "properties": {
        "outstanding": {"type": "string"},
        "why": {"type": "string"},
        "destination": {"type": "string"},
    },
    "required": ["outstanding", "why", "destination"],
}

def make_escalation_agent(model: str = DEFAULT_MODEL) -> LlmAgent:
    return LlmAgent(
        name="escalation",
        model=model,
        description="Drafts the follow-up action for an item that could not be closed.",
        instruction=(
            "An item on a mandated form could not be resolved during the interview. "
            "Draft the follow-up action that will be filed.\n\n"
            "`outstanding` states, in one sentence, precisely what is still not "
            "recorded — in terms of the form's own guidance. `why` states why it "
            "could not be closed, drawing only on what the BRIEF says; if the brief "
            "does not say, write 'not recorded during the visit'. `destination` "
            "names the queue or role it should go to, chosen from the DESTINATIONS "
            "list only.\n\n"
            "Never speculate about the person and never propose the answer itself. "
            "You are writing an administrative action, not a clinical or "
            "professional opinion.\n\nBRIEF:\n{escalation_brief}"
        ),
        output_schema=ESCALATION_SCHEMA,
        output_key="escalation",
        )


def escalation_brief(session: SessionState, item_id: str,
                     destinations: list[str]) -> str:
    item = session.template[item_id]
    slot = session.slots.get(item_id, {})
    return (
        f"ITEM {item.id}: {item.prompt}\n"
        f"GUIDANCE: {item.guidance}\n"
        f"STATE: {slot.get('state', 'open')}\n"
        f"RECORDED SO FAR: {slot.get('evidence') or '(nothing)'}\n"
        f"STILL MISSING: {'; '.join(slot.get('missing') or []) or '(everything)'}\n"
        f"DESTINATIONS: {', '.join(destinations)}\n"
    )


class Escalator:
    """Drafts and files a follow-up action for an unresolved item."""

    DESTINATIONS = [
        "District nursing team inbox",
        "Referring GP practice",
        "Occupational therapy queue",
        "Safeguarding lead",
        "Claims handler queue",
        "Surveyor scheduling queue",
    ]

    def __init__(self, store: BaseStore, model: str = DEFAULT_MODEL) -> None:
        self.store = store
        self.runner = Runner(
            app_name=APP_NAME,
            agent=make_escalation_agent(model),
            session_service=InMemorySessionService(),
        )

    async def escalate(self, session_id: str, item_id: str) -> SessionState:
        session = self.store.get(session_id)
        brief = escalation_brief(session, item_id, self.DESTINATIONS)

        adk_session = await self.runner.session_service.create_session(
            app_name=APP_NAME,
            user_id=session.practitioner_id,
            state={"escalation_brief": brief},
        )
        drafted = {}
        async for event in self.runner.run_async(
            user_id=session.practitioner_id,
            session_id=adk_session.id,
            new_message=types.Content(
                role="user", parts=[types.Part.from_text(text="Draft the follow-up.")]
            ),
        ):
            if event.content and event.content.parts:
                drafted = _loads(event.content.parts[0].text or "") or drafted

        destination = drafted.get("destination", "")
        if destination not in self.DESTINATIONS:
            destination = "Unassigned follow-up queue"

        return self.store.resolve(
            session_id, item_id, "escalated",
            reason=drafted.get("why") or "Not recorded during the visit.",
            destination=destination,
        )


def is_high_risk_answered_by_agent(session: SessionState, item_id: str) -> bool:
    """True if a high-risk item was closed by the agent rather than a human.

    Nothing should ever make this true — high-risk items are the practitioner's
    to write (ADR-0006) — so it exists to be asserted against.
    """
    slot = session.slots.get(item_id, {})
    return (session.template[item_id].high_risk
            and slot.get("state") == ANSWERED
            and slot.get("source") != "practitioner")


ROOT_AGENT_MODEL = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
