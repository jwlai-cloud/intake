"""Session state. Firestore owns it, not ADK (ADR-0004), so this is our schema."""

import pytest

from intake_agent.store import MemoryStore, SessionState


@pytest.fixture
def store():
    return MemoryStore()


def test_new_session_opens_every_unconditional_required_item(store):
    s = store.create("community-nursing-v1", practitioner_id="p1")
    assert s.status == "live"
    assert s.slots["M14"]["state"] == "open"
    assert "M15" not in s.slots, "conditional item is not open until its parent answers"


def test_no_interviewee_identity_field_exists_anywhere(store):
    # ADR-0007 is a design guarantee, not a policy note. If someone adds a
    # client-name field this test is what stops it.
    s = store.create("community-nursing-v1", practitioner_id="p1")
    blob = repr(s.to_dict()).lower()
    for banned in ("client_name", "patient", "subject_name", "dob", "nhs"):
        assert banned not in blob


def test_recording_an_answer_moves_the_slot_and_keeps_the_evidence(store):
    s = store.create("community-nursing-v1", practitioner_id="p1")
    store.apply_verdict(s.session_id, "M14", "sufficient",
                        value="Three falls, the last in May on the stairs.",
                        evidence="the last in May on the stairs", missing=[],
                        reason="count and circumstances recorded")
    s = store.get(s.session_id)
    assert s.slots["M14"]["state"] == "answered"
    assert s.slots["M14"]["evidence"] == "the last in May on the stairs"


def test_an_insufficient_verdict_is_partial_not_answered(store):
    # The entire product. "Mentioned" must never read as "resolved".
    s = store.create("community-nursing-v1", practitioner_id="p1")
    store.apply_verdict(s.session_id, "M14", "insufficient",
                        value="A couple of wobbles.", evidence="a couple of wobbles",
                        missing=["number of falls"], reason="no count recorded")
    s = store.get(s.session_id)
    assert s.slots["M14"]["state"] == "partial"
    assert s.slots["M14"]["missing"] == ["number of falls"]
    assert "M14" in s.outstanding_ids()


def test_an_answered_slot_is_never_reopened_by_a_later_chunk(store):
    # Later small talk about falls must not undo a recorded answer.
    s = store.create("community-nursing-v1", practitioner_id="p1")
    store.apply_verdict(s.session_id, "M14", "sufficient", value="Three, last in May.",
                        evidence="Three, last in May.", missing=[], reason="ok")
    store.apply_verdict(s.session_id, "M14", "insufficient", value="mm, a few",
                        evidence="a few", missing=["count"], reason="vague")
    assert store.get(s.session_id).slots["M14"]["state"] == "answered"


def test_answering_a_parent_opens_its_conditional_child(store):
    s = store.create("community-nursing-v1", practitioner_id="p1")
    store.apply_verdict(s.session_id, "M14", "sufficient",
                        value="Three falls, the last in May.",
                        evidence="Three falls", missing=[], reason="ok")
    s = store.get(s.session_id)
    assert s.slots["M15"]["state"] == "open"


def test_declining_only_counts_where_the_template_allows_it(store):
    s = store.create("community-nursing-v1", practitioner_id="p1")
    store.resolve(s.session_id, "M24", "declined", reason="Prefers not to say")
    assert store.get(s.session_id).slots["M24"]["state"] == "declined"

    with pytest.raises(ValueError, match="M14"):
        store.resolve(s.session_id, "M14", "declined", reason="skip it")


def test_escalation_files_a_followup_and_resolves_the_slot(store):
    s = store.create("community-nursing-v1", practitioner_id="p1")
    store.resolve(s.session_id, "M20", "escalated",
                  reason="No answer recorded before the visit ended",
                  destination="District nursing team inbox")
    s = store.get(s.session_id)
    assert s.slots["M20"]["state"] == "escalated"
    assert s.followups[0]["item_id"] == "M20"
    assert s.followups[0]["destination"] == "District nursing team inbox"


def test_the_gate_holds_until_every_required_item_is_resolved(store):
    s = store.create("community-nursing-v1", practitioner_id="p1")
    assert not s.gate_open()
    for item_id in list(s.outstanding_ids()):
        store.resolve(s.session_id, item_id, "escalated", reason="ran out of time",
                      destination="Team inbox")
    assert store.get(s.session_id).gate_open()


def test_chunk_replay_is_idempotent(store):
    # Network-drop reconciliation replays chunks in order; a replayed chunk must
    # not be processed twice.
    s = store.create("community-nursing-v1", practitioner_id="p1")
    assert store.claim_chunk(s.session_id, 1) is True
    assert store.claim_chunk(s.session_id, 1) is False
    assert store.claim_chunk(s.session_id, 2) is True


def test_state_round_trips_through_its_serialised_form(store):
    s = store.create("community-nursing-v1", practitioner_id="p1")
    store.apply_verdict(s.session_id, "M14", "insufficient", value="a couple",
                        evidence="a couple", missing=["count"], reason="vague")
    restored = SessionState.from_dict(store.get(s.session_id).to_dict())
    assert restored.slots["M14"]["state"] == "partial"
    assert restored.outstanding_ids() == store.get(s.session_id).outstanding_ids()
