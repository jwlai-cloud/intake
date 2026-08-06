"""Session state, owned by us and stored in Firestore (ADR-0004).

Two implementations behind one interface: `FirestoreStore` for the deployed
service and `MemoryStore` for tests and offline demos. The document shape is
identical, so the tests exercise the real schema.

Schema
------
    sessions/{session_id}
        template_id, practitioner_id, status, started_at, updated_at
        slots: { item_id: {state, value, evidence, missing[], reason,
                           resolved_at, source} }
        highlights: [ {id, item_id, title, quote, status} ]
        next_question: {item_id, prompt, why}
        followups: [ {item_id, outstanding, why, destination, drafted_at} ]
        processed_chunks: [seq, ...]
    practitioners/{practitioner_id}
        dismissed_categories, phrasing_notes, report_voice

Slots live in a map on the session document rather than a subcollection: the
whole coverage view then arrives in a single realtime snapshot and each chunk
is one atomic write. A template has tens of items, not thousands, so the 1MiB
document ceiling is not in play.

**No interviewee identity is stored in any of these** (ADR-0007). Sessions are
scoped to a job and a practitioner, never to a person.
"""

from __future__ import annotations

import copy
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .template import Template

log = logging.getLogger(__name__)

# Slot states. `partial` is the one the competition does not have: the item was
# discussed but the answer does not satisfy the guidance.
OPEN, PARTIAL, ANSWERED, DECLINED, ESCALATED = (
    "open", "partial", "answered", "declined", "escalated",
)
RESOLVED_STATES = {ANSWERED, DECLINED, ESCALATED}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _blank_slot() -> dict:
    return {"state": OPEN, "value": "", "evidence": "", "missing": [],
            "reason": "", "resolved_at": None, "source": ""}


@dataclass
class SessionState:
    session_id: str
    template_id: str
    practitioner_id: str
    status: str = "live"  # live | reported
    started_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    slots: dict[str, dict] = field(default_factory=dict)
    highlights: list[dict] = field(default_factory=list)
    next_question: dict | None = None
    followups: list[dict] = field(default_factory=list)
    processed_chunks: list[int] = field(default_factory=list)
    recent_turns: list[str] = field(default_factory=list)
    report: dict | None = None

    @property
    def template(self) -> Template:
        return Template.load(self.template_id)

    def sync_required(self) -> None:
        """Recompute the required set and open any newly triggered item.

        Called after every verdict: `depends_on` means required-ness is dynamic,
        so a chunk that answers M14 can bring M15 into scope mid-interview.
        """
        for item_id in self.template.required_ids(self.slots):
            self.slots.setdefault(item_id, _blank_slot())

    def outstanding_ids(self) -> list[str]:
        """Required items with no recorded resolution — what the gate holds on."""
        return [i for i in self.template.required_ids(self.slots)
                if self.slots.get(i, _blank_slot())["state"] not in RESOLVED_STATES]

    def gate_open(self) -> bool:
        """True when a report may be produced: nothing is silently blank."""
        return not self.outstanding_ids()

    def coverage(self) -> tuple[int, int]:
        required = self.template.required_ids(self.slots)
        resolved = [i for i in required
                    if self.slots.get(i, _blank_slot())["state"] in RESOLVED_STATES]
        return len(resolved), len(required)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "template_id": self.template_id,
            "practitioner_id": self.practitioner_id,
            "status": self.status,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "slots": copy.deepcopy(self.slots),
            "highlights": copy.deepcopy(self.highlights),
            "next_question": copy.deepcopy(self.next_question),
            "followups": copy.deepcopy(self.followups),
            "processed_chunks": list(self.processed_chunks),
            "recent_turns": list(self.recent_turns),
            "report": copy.deepcopy(self.report),
        }

    @staticmethod
    def from_dict(raw: dict) -> SessionState:
        return SessionState(**copy.deepcopy(raw))


class BaseStore:
    """Shared session mechanics. Subclasses only supply load and save."""

    def _load(self, session_id: str) -> SessionState:
        raise NotImplementedError

    def _save(self, state: SessionState) -> None:
        raise NotImplementedError

    def get(self, session_id: str) -> SessionState:
        return self._load(session_id)

    def create(self, template_id: str, practitioner_id: str) -> SessionState:
        Template.load(template_id)  # fail fast on an unknown template
        state = SessionState(
            session_id=uuid.uuid4().hex[:12],
            template_id=template_id,
            practitioner_id=practitioner_id,
        )
        state.sync_required()
        self._save(state)
        return state

    def claim_chunk(self, session_id: str, seq: int) -> bool:
        """Claim a chunk sequence number. False if it was already processed.

        The browser replays queued chunks after a network drop, so the same seq
        can legitimately arrive twice. Claiming makes reprocessing a no-op
        instead of a double-counted answer.
        """
        state = self._load(session_id)
        if seq in state.processed_chunks:
            return False
        state.processed_chunks.append(seq)
        state.updated_at = _now()
        self._save(state)
        return True

    def apply_verdict(self, session_id: str, item_id: str, verdict: str, *,
                      value: str, evidence: str, missing: list[str], reason: str,
                      source: str = "interview") -> SessionState:
        """Fold one adjudication result into the slot state."""
        state = self._load(session_id)
        slot = state.slots.setdefault(item_id, _blank_slot())

        if slot["state"] in RESOLVED_STATES:
            # A recorded resolution is never undone by later chatter about the
            # same topic. Only the practitioner reopens an item.
            return state

        slot.update(value=value, evidence=evidence, missing=list(missing),
                    reason=reason, source=source)
        if verdict == "sufficient":
            slot["state"] = ANSWERED
            slot["resolved_at"] = _now()
        elif verdict == "declined" and state.template[item_id].accepts_declined:
            slot["state"] = DECLINED
            slot["resolved_at"] = _now()
        else:
            # Includes a "declined" verdict on an item the template does not let
            # the interviewee decline — that stays open for the practitioner.
            slot["state"] = PARTIAL if (evidence or value) else OPEN

        state.sync_required()
        state.updated_at = _now()
        self._save(state)
        return state

    def resolve(self, session_id: str, item_id: str, resolution: str, *,
                reason: str, destination: str = "", value: str = "") -> SessionState:
        """Practitioner-driven resolution at the gate (ADR-0005)."""
        state = self._load(session_id)
        item = state.template[item_id]
        slot = state.slots.setdefault(item_id, _blank_slot())

        if resolution == ANSWERED:
            slot.update(state=ANSWERED, value=value, reason=reason,
                        resolved_at=_now(), source="practitioner")
        elif resolution == DECLINED:
            if not item.accepts_declined:
                raise ValueError(
                    f"{item_id} does not accept a declined resolution; "
                    "escalate it or record an answer"
                )
            slot.update(state=DECLINED, reason=reason, resolved_at=_now(),
                        source="practitioner")
        elif resolution == ESCALATED:
            slot.update(state=ESCALATED, reason=reason, resolved_at=_now(),
                        source="agent")
            state.followups.append({
                "item_id": item_id,
                "outstanding": item.prompt,
                "why": reason,
                "destination": destination or "Unassigned follow-up queue",
                "drafted_at": _now(),
            })
        else:
            raise ValueError(f"unknown resolution {resolution!r}")

        state.sync_required()
        state.updated_at = _now()
        self._save(state)
        return state

    def append_turns(self, session_id: str, turns: list[str],
                     cap: int = 12) -> SessionState:
        """Keep a bounded window of recent interviewee turns.

        An answer can arrive across two turns ("Three times." … "The last was in
        May on the stairs."), so adjudication needs a little history. The window
        is capped because ADR-0002's whole claim is that state stays bounded —
        an unbounded transcript in the prompt is the thing we are not doing.
        """
        state = self._load(session_id)
        state.recent_turns = (state.recent_turns + list(turns))[-cap:]
        state.updated_at = _now()
        self._save(state)
        return state

    def set_next_question(self, session_id: str, question: dict | None) -> None:
        state = self._load(session_id)
        state.next_question = question
        state.updated_at = _now()
        self._save(state)

    def add_highlights(self, session_id: str, highlights: list[dict]) -> None:
        state = self._load(session_id)
        seen = {h["quote"] for h in state.highlights}
        state.highlights.extend(h for h in highlights if h["quote"] not in seen)
        state.updated_at = _now()
        self._save(state)

    def set_highlight_status(self, session_id: str, highlight_id: str,
                             status: str) -> SessionState:
        state = self._load(session_id)
        for h in state.highlights:
            if h["id"] == highlight_id:
                h["status"] = status
        state.updated_at = _now()
        self._save(state)
        return state

    def set_report(self, session_id: str, report: dict) -> SessionState:
        state = self._load(session_id)
        state.report = report
        state.status = "reported"
        state.updated_at = _now()
        self._save(state)
        return state


class MemoryStore(BaseStore):
    """In-process store. Tests, local dev, and the demo when Firestore is absent."""

    def __init__(self) -> None:
        self._docs: dict[str, dict] = {}

    def _load(self, session_id: str) -> SessionState:
        try:
            return SessionState.from_dict(self._docs[session_id])
        except KeyError:
            raise KeyError(f"no session {session_id!r}") from None

    def _save(self, state: SessionState) -> None:
        self._docs[state.session_id] = state.to_dict()


class FirestoreStore(BaseStore):
    """Firestore-backed store. One document per session under `sessions/`."""

    def __init__(self, collection: str = "sessions", database: str | None = None) -> None:
        from google.cloud import firestore  # imported lazily: tests never need it

        self._db = firestore.Client(
            project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
            database=database or os.environ.get("FIRESTORE_DATABASE", "(default)"),
        )
        self._collection = collection

    def _doc(self, session_id: str):
        return self._db.collection(self._collection).document(session_id)

    def _load(self, session_id: str) -> SessionState:
        snap = self._doc(session_id).get()
        if not snap.exists:
            raise KeyError(f"no session {session_id!r}")
        return SessionState.from_dict(snap.to_dict())

    def _save(self, state: SessionState) -> None:
        self._doc(state.session_id).set(state.to_dict())

    def probe(self) -> None:
        """Round-trip a read so an unusable database fails at startup, not mid-visit.

        A bounded query rather than a named document: Firestore reserves ids
        matching `__…__`, so a probe document called `__probe__` is itself a
        400 and the probe fails for a reason that has nothing to do with the
        database being reachable.
        """
        list(self._db.collection(self._collection).limit(1).stream())


def default_store() -> BaseStore:
    """Firestore when it is actually usable, memory otherwise.

    The probe is a real round trip, not just a successful constructor. A
    Firestore client builds happily against a project whose default database is
    in Datastore Mode and only fails on the first write, which would take the
    demo down mid-interview instead of at startup. Falling back is loud.
    """
    if os.environ.get("INTAKE_STORE", "").lower() == "memory":
        return MemoryStore()
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        log.warning("no GOOGLE_CLOUD_PROJECT set — using in-memory session store")
        return MemoryStore()
    try:
        store = FirestoreStore()
        store.probe()
        return store
    except Exception as exc:
        log.warning("Firestore unavailable (%s) — falling back to the in-memory "
                    "session store. State will not survive a restart.", exc)
        return MemoryStore()
