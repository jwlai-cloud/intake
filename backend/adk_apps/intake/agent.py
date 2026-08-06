"""ADK entrypoint for the interview turn pipeline.

The service builds its pipeline through `build_root_agent(store)` because the
store is injected. ADK's own tooling — `adk api_server`, `adk web`,
`agents-cli eval generate` — discovers a module-level `root_agent` instead, so
this module provides one.

It exists for two reasons beyond tidiness:

1. **Behavioural evaluation.** `eval/run_eval.py` scores the adjudicator's
   judgement, one item at a time. It says nothing about whether the *pipeline*
   behaves: whether the coach obeys ADR-0006, whether its next question targets
   something genuinely open. Those are trajectory properties, and ADK's eval
   harness is built for them. See `tests/eval/`.
2. **`adk web`.** The turn pipeline becomes inspectable in ADK's dev UI without
   running the whole service.

The store here is in-memory on purpose: eval must not write to the interview
database, and each eval case is meant to be isolated anyway.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from intake_agent.agent import (
    AdjudicationAgent,
    TurnPipeline,
    make_coach,
    make_transcriber,
)
from intake_agent.store import MemoryStore

log = logging.getLogger(__name__)

EVAL_TEMPLATE_ID = "community-nursing-v1"

_store = MemoryStore()


class SelfOpeningTurnPipeline(TurnPipeline):
    """Opens an Intake session for the invocation if the caller did not.

    The service always sets `intake_session_id` before running a turn. ADK
    tooling does not, and the adjudication stage would fail on the missing key.

    The documented way to initialise state is a `before_agent_callback`, and
    that was the first implementation — but ADK emits an event for the state
    delta a callback produces, and that event carries no content.
    `agents-cli eval generate` rejects any content-less event outright, so the
    callback silently made the pipeline un-evaluable. Setting the key here, in
    an override that yields nothing extra, keeps every emitted event a real one.
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if not ctx.session.state.get("intake_session_id"):
            session = _store.create(EVAL_TEMPLATE_ID, practitioner_id="eval")
            ctx.session.state["intake_session_id"] = session.session_id
            ctx.session.state.setdefault("coach_brief", "")
            log.info("opened intake session %s for ADK invocation", session.session_id)

        async for event in super()._run_async_impl(ctx):
            yield event


# The stages are constructed here rather than reused from `build_root_agent`:
# an ADK agent may have exactly one parent, so handing an already-parented stage
# to a second pipeline raises "already has a parent agent".
root_agent = SelfOpeningTurnPipeline(
    name="intake_turn",
    description="Transcribe one chunk, adjudicate every open item, coach the next question.",
    sub_agents=[
        make_transcriber(),
        AdjudicationAgent(name="adjudication", store=_store),
        make_coach(),
    ],
)


def store() -> MemoryStore:
    """The in-memory store these invocations write to. Used by eval assertions."""
    return _store
