"""Routing. Offline: the model is stubbed, the filtering and fallback are real."""

import pytest

from intake_agent import agent as agent_mod
from intake_agent import router as router_mod
from intake_agent.adjudicator import Verdict
from intake_agent.agent import AdjudicationAgent
from intake_agent.store import MemoryStore
from intake_agent.template import Template


@pytest.fixture
def items():
    t = Template.load("community-nursing-v1")
    return [t[i] for i in ("M14", "M08", "M26")]


def stub_response(payload):
    class _Resp:
        text = payload
    class _Models:
        def generate_content(self, **_):
            return _Resp()
    class _Client:
        models = _Models()
    return _Client()


def test_only_the_named_items_come_back(items):
    got = router_mod.route(items, ["I fell twice."],
                           client=stub_response('{"item_ids": ["M14"]}'))
    assert [i.id for i in got] == ["M14"]


def test_the_router_cannot_invent_an_item(items):
    got = router_mod.route(items, ["something"],
                           client=stub_response('{"item_ids": ["M14", "M99"]}'))
    assert [i.id for i in got] == ["M14"]


def test_an_empty_route_is_a_normal_outcome(items):
    got = router_mod.route(items, ["Lovely weather today."],
                           client=stub_response('{"item_ids": []}'))
    assert got == []


def test_no_turns_means_no_call_and_no_items(items):
    class _Boom:
        @property
        def models(self):
            raise AssertionError("should not have called the model")
    assert router_mod.route(items, [], client=_Boom()) == []


def test_routing_failure_falls_open_to_every_item(items):
    # A routing outage must degrade to the old expensive behaviour, never to
    # silently skipping coverage — an unrouted item is an unasked question.
    class _Broken:
        @property
        def models(self):
            raise RuntimeError("503")
    got = router_mod.route(items, ["I fell twice."], client=_Broken())
    assert [i.id for i in got] == [i.id for i in items]


@pytest.mark.asyncio
async def test_the_pipeline_only_adjudicates_routed_items(monkeypatch):
    store = MemoryStore()
    session = store.create("community-nursing-v1", practitioner_id="p1")

    judged = []

    def fake_adjudicate(item, turns, *, model=None, client=None):
        judged.append(item.id)
        return Verdict("insufficient", "a couple of wobbles", ("count",),
                       "no count recorded", addressed=True)

    monkeypatch.setattr(agent_mod, "adjudicate", fake_adjudicate)
    monkeypatch.setattr(agent_mod, "route",
                        lambda items, turns, **kw: [i for i in items if i.id == "M14"])

    stage = AdjudicationAgent(name="adjudication", store=store)
    ctx = _ctx(session.session_id,
               [{"speaker": "interviewee", "text": "Oh, I've had a couple of wobbles."}])
    [e async for e in stage._run_async_impl(ctx)]

    # The bug this fixes: without routing, all 14 open items were judged against
    # a remark about falls and five of them kept the quote.
    assert judged == ["M14"]
    state = store.get(session.session_id)
    assert state.slots["M14"]["state"] == "partial"
    assert state.slots["M26"]["evidence"] == "", "mood must not hold a falls quote"
    assert state.slots["M08"]["state"] == "open"


class _FakeCtx:
    def __init__(self, state):
        self.session = type("S", (), {"state": state})()
        self.invocation_id = "inv-1"
        self.branch = None


def _ctx(session_id, turns):
    return _FakeCtx({"intake_session_id": session_id, "transcript": {"turns": turns}})
