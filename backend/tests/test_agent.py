"""The ADK turn pipeline. Offline: the model is stubbed, the wiring is real."""

import json

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


def test_the_pipeline_emits_no_content_less_events(store):
    # `agents-cli eval generate` rejects any event without content, and ADK's
    # SequentialAgent emitted exactly one — which made behavioural evaluation
    # impossible. This pins the reason we orchestrate the stages ourselves.
    from google.adk.agents import SequentialAgent
    root = agent_mod.build_root_agent(store)
    assert not isinstance(root, SequentialAgent)
    assert isinstance(root, agent_mod.TurnPipeline)


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
    # Both quotes are verbatim, so this isolates the item-id filter from the
    # verbatim filter — otherwise a pass here could mean either rule fired.
    store.append_turns(session.session_id, ["nope", "three falls"])
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


# --- verbatim-quote detection (the observation step for ADR-0006) ------------

@pytest.mark.parametrize("quote, ok", [
    ("Three times since Christmas", True),
    ("three times SINCE christmas", True),        # case is not fabrication
    ("Three  times   since Christmas", True),     # nor is re-wrapped whitespace
    ("I don’t go out", True),                     # nor a curly apostrophe
    ("", True),                                   # nothing captured is fine
    ("   ", True),
    ("She has fallen three times", False),        # paraphrase
    ("Four times since Christmas", False),        # one word changed
])
def test_is_verbatim(quote, ok):
    turns = ["Three times since Christmas.", "I don't go out much."]
    assert agent_mod.is_verbatim(quote, turns) is ok


def test_is_verbatim_known_gap_quote_may_straddle_two_turns():
    """Known limitation, recorded rather than hidden.

    Turns are joined with a space before the substring test, so a "quote" that
    starts in one turn and ends in the next passes — a sentence nobody actually
    spoke as one. Checking each turn separately would fix it, but would also
    reject the legitimate case of an answer delivered across two turns, which
    the adjudicator explicitly combines. Left as-is deliberately; tighten only
    with evidence that the model does this.
    """
    assert agent_mod.is_verbatim("Christmas. I don't", ["Three times since Christmas.",
                                                       "I don't go out much."]) is True


# --- escalation drafting retries (ADR-0005's autonomous beat) ----------------

class _FlakyRunner:
    """Fails `fail_times` times, then yields a usable draft."""

    def __init__(self, fail_times, payload=None):
        self.fail_times, self.calls = fail_times, 0
        self.payload = payload if payload is not None else {
            "outstanding": "Home access not recorded.",
            "why": "Not recorded during the visit.",
            "destination": "Occupational therapy queue",
        }
        self.session_service = self

    async def create_session(self, **_):
        return type("S", (), {"id": "s"})()

    def run_async(self, **_):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

        async def gen():
            yield type("E", (), {"content": type("C", (), {"parts": [
                type("P", (), {"text": json.dumps(self.payload)})()]})()})()
        return gen()


def _escalator_with(store, runner):
    esc = agent_mod.Escalator.__new__(agent_mod.Escalator)
    esc.store, esc.runner = store, runner
    esc.RETRY_DELAYS = (0.0, 0.0)
    return esc


@pytest.mark.asyncio
async def test_escalation_retries_a_transient_failure(store, session):
    runner = _FlakyRunner(fail_times=2)
    state = await _escalator_with(store, runner).escalate(session.session_id, "M26")
    assert runner.calls == 3, "should have retried twice before succeeding"
    assert state.followups[-1]["destination"] == "Occupational therapy queue"


@pytest.mark.asyncio
async def test_escalation_files_anyway_when_every_attempt_fails(store, session):
    runner = _FlakyRunner(fail_times=99)
    state = await _escalator_with(store, runner).escalate(session.session_id, "M26")
    assert state.slots["M26"]["state"] == "escalated", "the item must still resolve"
    assert state.followups[-1]["destination"] == agent_mod.FALLBACK_DESTINATION


@pytest.mark.asyncio
async def test_escalation_substitutes_an_invented_queue(store, session):
    runner = _FlakyRunner(fail_times=0, payload={
        "outstanding": "x", "why": "y", "destination": "Cardiology triage desk"})
    state = await _escalator_with(store, runner).escalate(session.session_id, "M26")
    assert state.followups[-1]["destination"] == agent_mod.FALLBACK_DESTINATION, \
        "a queue outside the closed list must never be filed"


@pytest.mark.asyncio
async def test_escalation_does_not_retry_an_empty_but_successful_draft(store, session):
    runner = _FlakyRunner(fail_times=0, payload={})
    await _escalator_with(store, runner).escalate(session.session_id, "M26")
    assert runner.calls == 1, "the model answered; retrying costs money for nothing"


# --- non-verbatim quotes are now dropped, not just logged --------------------

@pytest.mark.asyncio
async def test_paraphrased_evidence_is_dropped_but_the_verdict_stands(
        store, session, monkeypatch):
    """Whether the guidance was satisfied is a separate question from whether
    the model copied the words. Keep the first, refuse to display the second."""
    monkeypatch.setattr(agent_mod, "adjudicate", lambda item, turns, **k: Verdict(
        "sufficient", "She has fallen three times.", (), "ok"))
    stage = AdjudicationAgent(name="adjudication", store=store)
    ctx = _ctx(session.session_id, [
        {"speaker": "interviewee", "text": "Three times since Christmas."}])
    [e async for e in stage._run_async_impl(ctx)]

    slot = store.get(session.session_id).slots["M14"]
    assert slot["state"] == "answered", "the verdict is unaffected"
    assert slot["evidence"] == "", "an unverifiable span must not render as a quote"
    assert slot["value"] == "", "nor leak into the report as the recorded answer"


@pytest.mark.asyncio
async def test_verbatim_evidence_is_kept(store, session, monkeypatch):
    monkeypatch.setattr(agent_mod, "adjudicate", lambda item, turns, **k: Verdict(
        "sufficient", "Three times since Christmas.", (), "ok"))
    stage = AdjudicationAgent(name="adjudication", store=store)
    ctx = _ctx(session.session_id, [
        {"speaker": "interviewee", "text": "Three times since Christmas."}])
    [e async for e in stage._run_async_impl(ctx)]
    assert store.get(session.session_id).slots["M14"]["evidence"] == \
        "Three times since Christmas."


def test_a_fabricated_highlight_quote_is_dropped(store, session):
    store.append_turns(session.session_id, ["Three times since Christmas."])
    runner = TurnRunner.__new__(TurnRunner)
    runner.store = store
    runner._record_coaching(session.session_id, {
        "next_question": {"item_id": "M14", "prompt": "?", "why": "?"},
        "highlights": [
            {"item_id": "M14", "title": "Falls", "quote": "Three times since Christmas."},
            {"item_id": "M14", "title": "Falls", "quote": "I fall over constantly."},
        ],
    })
    quotes = [h["quote"] for h in store.get(session.session_id).highlights]
    assert quotes == ["Three times since Christmas."], \
        "a highlight is its quote; an unverifiable one has nothing left to show"


# --- a lone tester must not see a dead screen --------------------------------

def test_the_transcriber_labels_a_lone_voice_as_the_interviewee():
    """Found by actually recording into the deployed app.

    One person testing alone is a single voice, and the transcriber labelled it
    `practitioner`. Adjudication only ever looks at `interviewee` turns, so
    every chunk was discarded, every turn finished in 0.1s having done nothing,
    and the screen sat inert — which reads as a broken product, and is exactly
    what a judge trying it alone would have seen.

    Fixed at the transcriber because that is the only stage that can hear how
    many people are in the room. The alternative — relaxing the filter in
    adjudication — would have broken the guarantee below.
    """
    instruction = agent_mod.make_transcriber().instruction
    assert "only ONE voice" in instruction
    assert "label every turn `interviewee`" in instruction
    assert "Use `practitioner` only when you can actually hear two" in instruction


@pytest.mark.asyncio
async def test_once_an_interviewee_is_heard_the_practitioner_stops_counting(
        store, session, monkeypatch):
    """The guarantee that matters: in a real two-person interview, the
    professional restating an answer must never close the item."""
    store.append_turns(session.session_id, ["Three times since Christmas."])
    called = []
    monkeypatch.setattr(agent_mod, "adjudicate",
                        lambda *a, **k: called.append(1) or Verdict("sufficient", "x", (), ""))
    stage = AdjudicationAgent(name="adjudication", store=store)
    ctx = _ctx(session.session_id, [
        {"speaker": "practitioner", "text": "So that's three falls, is that right?"}])
    [e async for e in stage._run_async_impl(ctx)]
    assert called == [], "the practitioner's own summary must not close an item"


@pytest.mark.asyncio
async def test_a_suggested_question_that_closes_an_item_is_remembered(
        store, session, monkeypatch):
    """The signal memory is built on, pinned against the bug that made it inert.

    An item is normally raised vaguely first (partial) and closed on the
    follow-up. The first version of this only learned when the slot went
    straight from `open` to `answered`, so in a week of real use it learned
    nothing at all.
    """
    store.count_interview("p1")
    store.set_next_question(session.session_id, {
        "item_id": "M14", "prompt": "How many times, and what happened the last one?",
        "why": "count"})
    store.apply_verdict(session.session_id, "M14", "insufficient", value="wobbles",
                        evidence="wobbles", missing=["number of falls"], reason="vague")

    monkeypatch.setattr(agent_mod, "adjudicate", lambda item, turns, **k: Verdict(
        "sufficient", "Three times since Christmas.", (), "ok")
        if item.id == "M14" else Verdict("insufficient", "", ("x",), "no"))
    stage = AdjudicationAgent(name="adjudication", store=store)
    ctx = _ctx(session.session_id,
               [{"speaker": "interviewee", "text": "Three times since Christmas."}])
    [e async for e in stage._run_async_impl(ctx)]

    learned = store.memory("p1").effective_phrasings.get("M14") or []
    assert learned == ["How many times, and what happened the last one?"], \
        "the wording that closed the item is what memory is for"
