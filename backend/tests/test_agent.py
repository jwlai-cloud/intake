"""The ADK turn pipeline. Offline: the model is stubbed, the wiring is real."""

import pytest

from intake_agent import agent as agent_mod
from intake_agent.adjudicator import Verdict
from intake_agent.agent import AdjudicationAgent, TurnRunner, build_coach_brief
from intake_agent.store import MemoryStore


@pytest.fixture
def store():
    return MemoryStore()


@pytest.fixture
def session(store):
    return store.create("community-nursing-v1", practitioner_id="p1")


def test_pipeline_is_transcribe_adjudicate_coach(store):
    root = agent_mod.build_root_agent(store)
    assert [a.name for a in root.sub_agents] == ["transcriber", "adjudication", "coach"]


def test_coach_is_never_given_a_field_it_could_put_an_answer_in():
    # ADR-0006 enforced structurally, not by asking nicely: the coach's output
    # schema has no answer field, so it cannot emit one however it is prompted.
    props = agent_mod.COACH_SCHEMA["properties"]
    assert set(props) == {"next_question", "highlights"}
    assert set(props["next_question"]["properties"]) == {"item_id", "prompt", "why"}


def test_brief_marks_high_risk_items_and_omits_the_transcript(session):
    brief = build_coach_brief(session, ["I've had a couple of wobbles."])
    assert "M14" in brief
    assert "HIGH RISK" in brief
    # The brief carries the open items and this chunk's quotes — never a running
    # transcript. That bound is ADR-0002's entire claim.
    assert brief.count("\n") < 200


def test_brief_puts_partly_answered_items_before_untouched_ones(store, session):
    store.apply_verdict(session.session_id, "M14", "insufficient",
                        value="a couple of wobbles", evidence="a couple of wobbles",
                        missing=["number of falls"], reason="no count")
    brief = build_coach_brief(store.get(session.session_id), [])
    lines = [l for l in brief.splitlines() if l.startswith("- M")]
    assert lines[0].startswith("- M14"), "the nearly-complete item should be next"


def test_brief_reports_full_coverage_without_inventing_an_item(store, session):
    for item_id in list(session.outstanding_ids()):
        store.resolve(session.session_id, item_id, "escalated", reason="time",
                      destination="Team inbox")
    brief = build_coach_brief(store.get(session.session_id), [])
    assert "none. Every required item" in brief


@pytest.mark.asyncio
async def test_adjudication_stage_folds_verdicts_into_the_store(store, session, monkeypatch):
    calls = []

    def fake_adjudicate(item, turns, *, model=None, client=None):
        calls.append((item.id, tuple(turns)))
        if item.id == "M14":
            return Verdict("sufficient", "Three falls, the last in May.", (), "ok")
        return Verdict("insufficient", "", ("everything",), "no answer recorded")

    monkeypatch.setattr(agent_mod, "adjudicate", fake_adjudicate)

    stage = AdjudicationAgent(name="adjudication", store=store)
    ctx = _ctx(session.session_id, [
        {"speaker": "practitioner", "text": "Any falls?"},
        {"speaker": "interviewee", "text": "Three falls, the last in May."},
    ])

    events = [e async for e in stage._run_async_impl(ctx)]

    assert store.get(session.session_id).slots["M14"]["state"] == "answered"
    assert events[0].actions.state_delta["coach_brief"]
    # Every open item is judged, each against the same turns, independently.
    assert len(calls) == len(session.outstanding_ids())
    assert all(t == ("Three falls, the last in May.",) for _, t in calls)


@pytest.mark.asyncio
async def test_practitioner_turns_are_not_treated_as_answers(store, session, monkeypatch):
    called = []
    monkeypatch.setattr(agent_mod, "adjudicate",
                        lambda *a, **k: called.append(1) or Verdict("sufficient", "x", (), ""))

    stage = AdjudicationAgent(name="adjudication", store=store)
    ctx = _ctx(session.session_id, [
        {"speaker": "practitioner", "text": "So that's three falls, the last in May?"},
    ])
    [e async for e in stage._run_async_impl(ctx)]

    assert called == [], "the practitioner's own summary must not close an item"
    assert store.get(session.session_id).slots["M14"]["state"] == "open"


@pytest.mark.asyncio
async def test_one_item_failing_does_not_lose_the_chunk(store, session, monkeypatch):
    def flaky(item, turns, *, model=None, client=None):
        if item.id == "M14":
            raise RuntimeError("503 model overloaded")
        return Verdict("sufficient", "recorded", (), "ok")

    monkeypatch.setattr(agent_mod, "adjudicate", flaky)
    stage = AdjudicationAgent(name="adjudication", store=store)
    ctx = _ctx(session.session_id,
               [{"speaker": "interviewee", "text": "Here is an answer."}])
    [e async for e in stage._run_async_impl(ctx)]

    s = store.get(session.session_id)
    assert s.slots["M14"]["state"] == "open", "failed item stays open and retries"
    assert s.slots["M06"]["state"] == "answered", "its neighbours still land"


def test_coaching_cannot_introduce_an_item_the_template_does_not_have(store, session):
    runner = TurnRunner.__new__(TurnRunner)  # no ADK Runner needed for this
    runner.store = store
    runner._record_coaching(session.session_id, {
        "next_question": {"item_id": "M99", "prompt": "?", "why": "?"},
        "highlights": [{"item_id": "M99", "title": "made up", "quote": "nope"},
                       {"item_id": "M14", "title": "real", "quote": "three falls"}],
    })
    s = store.get(session.session_id)
    assert s.next_question is None, "a question about a non-existent item is dropped"
    assert [h["item_id"] for h in s.highlights] == ["M14"]


def test_high_risk_answered_by_agent_is_detectable(store, session):
    store.apply_verdict(session.session_id, "M14", "sufficient", value="v",
                        evidence="v", missing=[], reason="", source="interview")
    s = store.get(session.session_id)
    assert agent_mod.is_high_risk_answered_by_agent(s, "M14") is True

    store.resolve(session.session_id, "M10", "answered", reason="written by nurse",
                  value="Red area at the sacrum.")
    assert agent_mod.is_high_risk_answered_by_agent(
        store.get(session.session_id), "M10") is False


# --- helpers -----------------------------------------------------------------


class _FakeSession:
    def __init__(self, state):
        self.state = state


class _FakeCtx:
    def __init__(self, state):
        self.session = _FakeSession(state)
        self.invocation_id = "inv-1"
        self.branch = None


def _ctx(session_id, turns):
    return _FakeCtx({"intake_session_id": session_id, "transcript": {"turns": turns}})
