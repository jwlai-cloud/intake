"""HTTP surface for the agent service. Runs on Cloud Run.

The browser posts audio chunks here and reads session state back. Firestore is
the durable store; when a Firestore realtime listener is wired up the client can
stop polling, but every endpoint returns the full session so the UI works either
way.
"""

from __future__ import annotations

import base64
import logging
import os

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import report as report_builder
from .agent import Escalator, TurnRunner
from .store import BaseStore, FirestoreStore, MemoryStore, default_store
from .template import Template, TemplateError

log = logging.getLogger(__name__)

# 20-second Opus chunks are well under a megabyte; anything much larger is a
# mistake or an attack, and decoding it first would be the expensive part.
MAX_AUDIO_BYTES = 8 * 1024 * 1024

app = FastAPI(title="Intake", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get(
        "INTAKE_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_store: BaseStore = default_store()
_runner = TurnRunner(_store)
_escalator = Escalator(_store)


def require_api_key(x_intake_key: str | None = Header(default=None)) -> None:
    """Shared-secret gate.

    Every endpoint below spends money on Vertex AI, so an open deployment is an
    open wallet. If INTAKE_API_KEY is unset the service runs ungated for local
    development — set it in Cloud Run.
    """
    expected = os.environ.get("INTAKE_API_KEY")
    if expected and x_intake_key != expected:
        raise HTTPException(status_code=401, detail="bad or missing X-Intake-Key")


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
    seq: int = Field(ge=0)
    audio_b64: str | None = None
    mime_type: str = "audio/webm"
    text: str | None = None  # typed fallback; also what the tests drive


class Resolution(BaseModel):
    item_id: str
    resolution: str  # answered | declined | escalated
    reason: str = ""
    destination: str = ""
    value: str = ""


class HighlightUpdate(BaseModel):
    status: str  # confirmed | dismissed


# --- routes ------------------------------------------------------------------


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "store": type(_store).__name__}


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
        log.exception("chunk %s failed for session %s", body.seq, session_id)
        return _view(_store.get(session_id)) | {"degraded": True, "error": str(exc)[:200]}

    return _view(state)


@app.post("/sessions/{session_id}/resolve", dependencies=[Depends(require_api_key)])
async def resolve_item(session_id: str, body: Resolution) -> dict:
    get_session(session_id)
    try:
        if body.resolution == "escalated" and not body.reason:
            # No reason supplied means the agent drafts the follow-up itself.
            state = await _escalator.escalate(session_id, body.item_id)
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
