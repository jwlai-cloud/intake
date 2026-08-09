"""HTTP surface for the agent service. Runs on Cloud Run.

The browser posts audio chunks here and reads session state back. Firestore is
the durable store; when a Firestore realtime listener is wired up the client can
stop polling, but every endpoint returns the full session so the UI works either
way.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import tracing

# BEFORE importing .agent, which imports ADK. OpenTelemetry resolves a tracer at
# the moment get_tracer is called, and google.adk.telemetry does that at import
# time — so a provider installed afterwards is silently ignored and every span
# goes to the no-op default. Ordering is the whole fix.
_tracing = tracing.setup()

from . import report as report_builder  # noqa: E402
from .agent import Escalator, TurnRunner  # noqa: E402
from .store import BaseStore, FirestoreStore, MemoryStore, default_store  # noqa: E402
from .template import Template, TemplateError  # noqa: E402

# uvicorn configures its own loggers, so ours default to WARNING and every
# log.info in the package is silently dropped — which is why the pipeline's
# audit lines never reached Cloud Logging.
logging.basicConfig(
    level=os.environ.get("INTAKE_LOG_LEVEL", "INFO"),
    format="%(levelname)s %(name)s | %(message)s",
)
log = logging.getLogger(__name__)

# 20-second Opus chunks are well under a megabyte; anything much larger is a
# mistake or an attack, and decoding it first would be the expensive part.
MAX_AUDIO_BYTES = 8 * 1024 * 1024

def _adk_version() -> str:
    try:
        import importlib.metadata as md
        return md.version("google-adk")
    except Exception:
        return "unknown"


app = FastAPI(title="Intake", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get(
        "INTAKE_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

log.info("Intake starting · ADK %s · model %s via Vertex AI · project %s · "
         "Firestore %s · tracing=%s",
         _adk_version(), os.environ.get("GEMINI_MODEL", "gemini-3.6-flash"),
         os.environ.get("GOOGLE_CLOUD_PROJECT", "(unset)"),
         os.environ.get("FIRESTORE_DATABASE", "(default)"), _tracing)

_store: BaseStore = default_store()
_runner = TurnRunner(_store)
_escalator = Escalator(_store)


def require_api_key(x_intake_key: str | None = Header(default=None)) -> None:
    """Shared-secret gate.

    Every endpoint below spends money on Vertex AI, so an open deployment is an
    open wallet. If INTAKE_API_KEY is unset the service runs ungated for local
    development — set it in Cloud Run.

    Compared in constant time: a plain `!=` on a secret leaks its prefix to a
    patient attacker through response timing.

    This is a stopgap for the contest. Firebase Auth ID tokens replace it —
    see ADR-0012.
    """
    expected = os.environ.get("INTAKE_API_KEY")
    if not expected:
        # Fail closed. An empty secret version, or a deploy that drops
        # --set-secrets, would otherwise mount cleanly and publish an
        # unauthenticated, unrated, Vertex-spending endpoint to the internet —
        # with /health still cheerfully reporting ok. Local work opts out
        # explicitly instead.
        if os.environ.get("INTAKE_ALLOW_UNGATED") == "1":
            return
        raise HTTPException(status_code=503,
                            detail="service is not configured with an API key")
    if not x_intake_key or not secrets.compare_digest(x_intake_key, expected):
        raise HTTPException(status_code=401, detail="bad or missing X-Intake-Key")
    _rate_limit(x_intake_key)


# Requests per minute per key. One interview turn is ~18 Vertex calls, and a
# practitioner speaking produces a chunk every 18 seconds — so a real session
# needs about 4/min. 20 leaves generous headroom while capping what a leaked
# code is worth: the ceiling is the bill, not the traffic.
RATE_LIMIT_PER_MINUTE = int(os.environ.get("INTAKE_RATE_LIMIT_PER_MINUTE", "20"))
_hits: dict[str, deque[float]] = defaultdict(deque)
_hits_lock = threading.Lock()


def _rate_limit(key: str) -> None:
    """Per-key sliding window, in process.

    ponytail: in-memory, so the real limit is per Cloud Run instance and the
    service is capped at 2. Good enough while the key count is one. Move to a
    Firestore counter keyed on the Firebase uid when there are real users.
    """
    now = time.monotonic()
    bucket = _hits[hashlib.sha256(key.encode()).hexdigest()]
    with _hits_lock:
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail=f"rate limit: {RATE_LIMIT_PER_MINUTE} requests per minute",
            )
        bucket.append(now)


def get_session(session_id: str):
    try:
        return _store.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"no session {session_id}") from None


# --- payloads ----------------------------------------------------------------


class NewSession(BaseModel):
    template_id: str
    practitioner_id: str = Field(min_length=1, max_length=64)


class Chunk(BaseModel):
    # Bounds are enforced by Pydantic before the handler runs, so an oversized
    # body is rejected without ever being base64-decoded. The MAX_AUDIO_BYTES
    # check further down only fires after decode has already allocated the
    # buffer, which is too late to protect memory.
    #
    # `text` matters more than it looks: it is fed verbatim into every model
    # call in the turn — transcriber, router, N adjudicators, coach — so an
    # unbounded string here is the largest denial-of-wallet lever in the
    # service. A chunk of speech is a couple of hundred characters.
    seq: int = Field(ge=0)
    audio_b64: str | None = Field(default=None, max_length=4 * MAX_AUDIO_BYTES // 3 + 4)
    mime_type: str = Field(default="audio/webm", max_length=64)
    text: str | None = Field(default=None, max_length=4000)


class Resolution(BaseModel):
    item_id: str = Field(max_length=64)
    resolution: str = Field(max_length=32)  # answered | declined | escalated
    reason: str = Field(default="", max_length=2000)
    destination: str = Field(default="", max_length=200)
    value: str = Field(default="", max_length=4000)


class HighlightUpdate(BaseModel):
    status: str  # confirmed | dismissed


# --- routes ------------------------------------------------------------------


@app.get("/health")
def health(response: Response) -> dict:
    """Not /healthz — Cloud Run's frontend reserves that path and answers it
    itself, so the request never reaches the container.

    Fails when the session store silently degraded. `default_store()` runs at
    import, so a Firestore blip during a cold start pinned that instance to
    in-memory storage for its whole life while still reporting ok — sessions on
    it vanish on restart, and at --max-instances=2 that is up to half the
    traffic. Reporting it as unhealthy lets Cloud Run replace the instance
    instead of leaving it quietly losing interviews.

    `INTAKE_STORE=memory` stays an explicit, healthy opt-out: choosing memory is
    not the same as falling back to it.
    """
    chose_memory = os.environ.get("INTAKE_STORE", "").lower() == "memory"
    degraded = (type(_store).__name__ == "MemoryStore"
                and not chose_memory
                and bool(os.environ.get("GOOGLE_CLOUD_PROJECT")))
    if degraded:
        response.status_code = 503
    return {"ok": not degraded, "store": type(_store).__name__,
            "tracing_configured": _tracing,
            **({"detail": "session store degraded to memory"} if degraded else {})}


@app.get("/templates")
def list_templates() -> dict:
    out = []
    for tid in Template.available():
        t = Template.load(tid)
        out.append({"template_id": t.template_id, "title": t.title,
                    "subtitle": t.subtitle, "required": len(t.required_ids({}))})
    return {"templates": out}


@app.get("/templates/{template_id}")
def get_template(template_id: str) -> dict:
    try:
        t = Template.load(template_id)
    except TemplateError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return {
        "template_id": t.template_id, "title": t.title, "subtitle": t.subtitle,
        "items": [
            {"id": i.id, "prompt": i.prompt, "section_title": i.section_title,
             "high_risk": i.high_risk, "accepts_declined": i.accepts_declined,
             "guidance_ref": i.guidance_ref}
            for i in t.items.values()
        ],
    }


@app.post("/sessions", dependencies=[Depends(require_api_key)])
def create_session(body: NewSession) -> dict:
    try:
        state = _store.create(body.template_id, body.practitioner_id)
    except TemplateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return _view(state)


@app.get("/sessions/{session_id}", dependencies=[Depends(require_api_key)])
def read_session(session_id: str) -> dict:
    return _view(get_session(session_id))


@app.post("/sessions/{session_id}/chunks", dependencies=[Depends(require_api_key)])
async def post_chunk(session_id: str, body: Chunk) -> dict:
    get_session(session_id)

    if not _store.claim_chunk(session_id, body.seq):
        # A replayed chunk after a network drop. Already folded in; returning the
        # current state keeps the client's retry loop simple and side-effect free.
        return _view(_store.get(session_id)) | {"replayed": True}

    audio = None
    if body.audio_b64:
        try:
            audio = base64.b64decode(body.audio_b64, validate=True)
        except Exception:
            raise HTTPException(status_code=400, detail="audio_b64 is not base64") from None
        if len(audio) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413, detail="chunk too large")
    if audio is None and not body.text:
        raise HTTPException(status_code=400, detail="need audio_b64 or text")

    try:
        state = await _runner.run_turn(session_id, audio=audio,
                                       mime_type=body.mime_type, text=body.text)
    except Exception as exc:
        # Never lose the session over one bad chunk. The client keeps recording
        # and the next chunk retries the same open items.
        # Type only, never str(exc). A Vertex 400 echoes the offending request,
        # and the adjudicator's request body is verbatim interviewee speech —
        # so logging the message writes transcript into Cloud Logging, which
        # outlives the session document and sits outside every promise
        # ADR-0007 makes about where interview content lives. The same text
        # returned to the client would also disclose project and model.
        log.error("chunk %s failed for session %s (%s)",
                  body.seq, session_id, type(exc).__name__)
        return _view(_store.get(session_id)) | {
            "degraded": True,
            "error": "turn failed; the next chunk retries the same open items",
        }

    return _view(state)


@app.post("/sessions/{session_id}/resolve", dependencies=[Depends(require_api_key)])
async def resolve_item(session_id: str, body: Resolution) -> dict:
    get_session(session_id)
    try:
        if body.resolution == "escalated" and not body.reason:
            # No reason supplied means the agent drafts the follow-up itself.
            try:
                state = await _escalator.escalate(session_id, body.item_id)
            except Exception as exc:
                # The drafting is a nicety; filing the follow-up is the promise.
                # When the model is unavailable — a spend cap, a quota, an
                # outage — the item must still be resolved and routed, or the
                # gate holds the report hostage over a feature that failed.
                log.error("escalation drafting failed for %s (%s)",
                          body.item_id, type(exc).__name__)
                state = _store.resolve(
                    session_id, body.item_id, "escalated",
                    reason="Not recorded during the visit. Follow-up drafted "
                           "by hand — automatic drafting was unavailable.",
                    destination="Unassigned follow-up queue")
                return _view(state) | {"degraded": True}
        else:
            state = _store.resolve(session_id, body.item_id, body.resolution,
                                   reason=body.reason, destination=body.destination,
                                   value=body.value)
    except TemplateError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return _view(state)


@app.post("/sessions/{session_id}/highlights/{highlight_id}",
          dependencies=[Depends(require_api_key)])
def update_highlight(session_id: str, highlight_id: str, body: HighlightUpdate) -> dict:
    get_session(session_id)
    if body.status not in {"confirmed", "dismissed"}:
        raise HTTPException(status_code=400, detail="status must be confirmed or dismissed")
    return _view(_store.set_highlight_status(session_id, highlight_id, body.status))


@app.post("/sessions/{session_id}/report", dependencies=[Depends(require_api_key)])
def generate_report(session_id: str) -> dict:
    state = get_session(session_id)
    if not state.gate_open():
        # The gate is the product's promise. It is a router, not a wall: the
        # response says exactly what is outstanding so the UI can offer the
        # three resolutions.
        raise HTTPException(status_code=409, detail={
            "error": "unresolved required items",
            "outstanding": [
                {"item_id": i,
                 "prompt": state.template[i].prompt,
                 "accepts_declined": state.template[i].accepts_declined,
                 "missing": state.slots.get(i, {}).get("missing", []),
                 "evidence": state.slots.get(i, {}).get("evidence", "")}
                for i in state.outstanding_ids()
            ],
        })
    return _view(_store.set_report(session_id, report_builder.build(state)))


# --- view --------------------------------------------------------------------


def _view(state) -> dict:
    """One shape for the client, whatever endpoint it came from."""
    template = state.template
    resolved, required = state.coverage()
    return {
        "session_id": state.session_id,
        "template_id": state.template_id,
        "title": template.title,
        "subtitle": template.subtitle,
        "status": state.status,
        "coverage": {"resolved": resolved, "required": required},
        "gate_open": state.gate_open(),
        "outstanding": state.outstanding_ids(),
        "next_question": state.next_question,
        "highlights": state.highlights,
        "followups": state.followups,
        "report": state.report,
        "items": [
            {
                "id": item.id,
                "prompt": item.prompt,
                "section_title": item.section_title,
                "high_risk": item.high_risk,
                "accepts_declined": item.accepts_declined,
                **state.slots[item.id],
            }
            for item in template.ordered(template.required_ids(state.slots))
        ],
    }


def configure_for_tests(store: BaseStore) -> None:
    """Point the module at a store the test owns. Not used in production."""
    global _store, _runner, _escalator
    _store = store
    _runner = TurnRunner(store)
    _escalator = Escalator(store)


__all__ = ["app", "configure_for_tests", "FirestoreStore", "MemoryStore"]
