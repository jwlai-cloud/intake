"""The HTTP surface, including the gate. No model calls: the turn is stubbed."""

import pytest
from fastapi.testclient import TestClient

from intake_agent import main
from intake_agent.store import MemoryStore


@pytest.fixture
def client(monkeypatch):
    # The service fails closed when INTAKE_API_KEY is unset, so the ungated
    # path has to be asked for explicitly — that is the point of the flag.
    monkeypatch.setenv("INTAKE_ALLOW_UNGATED", "1")
    store = MemoryStore()
    main.configure_for_tests(store)
    monkeypatch.setattr(main, "_store", store)
    return TestClient(main.app), store


def new_session(c):
    r = c.post("/sessions", json={"template_id": "community-nursing-v1",
                                  "practitioner_id": "p1"})
    assert r.status_code == 200
    return r.json()


def test_both_templates_are_offered_without_a_code_path_each(client):
    c, _ = client
    ids = {t["template_id"] for t in c.get("/templates").json()["templates"]}
    assert ids == {"community-nursing-v1", "loss-adjusting-v1"}


def test_session_starts_with_every_required_item_open(client):
    c, _ = client
    s = new_session(c)
    assert s["coverage"] == {"resolved": 0, "required": len(s["outstanding"])}
    assert s["gate_open"] is False
    assert all(i["state"] == "open" for i in s["items"])


def test_report_is_refused_while_anything_is_outstanding(client):
    c, _ = client
    s = new_session(c)
    r = c.post(f"/sessions/{s['session_id']}/report")
    assert r.status_code == 409
    detail = r.json()["detail"]
    # A router, not a wall: the refusal carries what is missing and whether a
    # decline is even permitted for it.
    assert detail["outstanding"][0]["item_id"]
    assert "accepts_declined" in detail["outstanding"][0]


def test_the_three_resolutions_each_close_an_item(client):
    c, store = client
    s = new_session(c)
    sid = s["session_id"]

    c.post(f"/sessions/{sid}/resolve", json={
        "item_id": "M14", "resolution": "answered",
        "value": "Three falls, the last in May on the stairs.", "reason": "written by nurse"})
    c.post(f"/sessions/{sid}/resolve", json={
        "item_id": "M24", "resolution": "declined", "reason": "Prefers not to say"})
    c.post(f"/sessions/{sid}/resolve", json={
        "item_id": "M20", "resolution": "escalated", "reason": "Ran out of time",
        "destination": "District nursing team inbox"})

    state = store.get(sid)
    assert state.slots["M14"]["state"] == "answered"
    assert state.slots["M24"]["state"] == "declined"
    assert state.slots["M20"]["state"] == "escalated"
    assert state.followups[0]["destination"] == "District nursing team inbox"


def test_declining_an_item_the_template_forbids_is_a_conflict_not_a_crash(client):
    c, _ = client
    s = new_session(c)
    r = c.post(f"/sessions/{s['session_id']}/resolve",
               json={"item_id": "M14", "resolution": "declined", "reason": "skip"})
    assert r.status_code == 409
    assert "M14" in r.json()["detail"]


def test_report_is_produced_once_nothing_is_silently_blank(client):
    c, store = client
    s = new_session(c)
    sid = s["session_id"]
    for item_id in s["outstanding"]:
        c.post(f"/sessions/{sid}/resolve", json={
            "item_id": item_id, "resolution": "escalated",
            "reason": "Visit ended before this could be covered",
            "destination": "District nursing team inbox"})

    r = c.post(f"/sessions/{sid}/report")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "reported"
    assert body["report"]["sections"], "report has content"
    assert body["report"]["unresolved"] == []
    assert len(body["report"]["followups"]) == len(s["outstanding"])


def test_report_never_leaves_an_item_blank(client):
    c, _ = client
    s = new_session(c)
    sid = s["session_id"]
    for item_id in s["outstanding"]:
        c.post(f"/sessions/{sid}/resolve", json={
            "item_id": item_id, "resolution": "escalated", "reason": "no time",
            "destination": "District nursing team inbox"})
    report = c.post(f"/sessions/{sid}/report").json()["report"]
    for section in report["sections"]:
        for entry in section["entries"]:
            assert entry["text"].strip(), f"{entry['item_id']} rendered blank"


def test_a_replayed_chunk_is_not_processed_twice(client, monkeypatch):
    c, store = client
    s = new_session(c)
    sid = s["session_id"]

    calls = []

    async def fake_turn(session_id, **kw):
        calls.append(kw)
        return store.get(session_id)

    monkeypatch.setattr(main._runner, "run_turn", fake_turn)

    first = c.post(f"/sessions/{sid}/chunks", json={"seq": 1, "text": "hello"})
    second = c.post(f"/sessions/{sid}/chunks", json={"seq": 1, "text": "hello"})

    assert first.status_code == 200 and second.status_code == 200
    assert second.json().get("replayed") is True
    assert len(calls) == 1


def test_a_failing_chunk_degrades_and_keeps_the_session(client, monkeypatch):
    c, _ = client
    s = new_session(c)

    async def boom(session_id, **kw):
        raise RuntimeError("503 Vertex unavailable")

    monkeypatch.setattr(main._runner, "run_turn", boom)
    r = c.post(f"/sessions/{s['session_id']}/chunks", json={"seq": 1, "text": "hi"})
    assert r.status_code == 200
    assert r.json()["degraded"] is True
    assert r.json()["session_id"] == s["session_id"]


def test_oversized_audio_is_rejected_before_it_is_decoded(client):
    import base64
    c, _ = client
    s = new_session(c)
    payload = base64.b64encode(b"x" * (main.MAX_AUDIO_BYTES + 1)).decode()
    r = c.post(f"/sessions/{s['session_id']}/chunks",
               json={"seq": 1, "audio_b64": payload})
    assert r.status_code == 413


def test_the_api_key_gate_closes_when_a_key_is_configured(client, monkeypatch):
    c, _ = client
    monkeypatch.setenv("INTAKE_API_KEY", "s3cret")
    unauth = c.post("/sessions", json={"template_id": "community-nursing-v1",
                                       "practitioner_id": "p1"})
    assert unauth.status_code == 401
    ok = c.post("/sessions", json={"template_id": "community-nursing-v1",
                                   "practitioner_id": "p1"},
                headers={"X-Intake-Key": "s3cret"})
    assert ok.status_code == 200


def test_a_leaked_key_is_still_rate_limited(client, monkeypatch):
    # The access code is typed rather than shipped in the bundle, but a code
    # that leaks anyway must not be worth much: the ceiling on abuse is the
    # Vertex bill, not the request count.
    c, _ = client
    monkeypatch.setenv("INTAKE_API_KEY", "s3cret")
    monkeypatch.setattr(main, "RATE_LIMIT_PER_MINUTE", 3)
    main._hits.clear()

    headers = {"X-Intake-Key": "s3cret"}
    body = {"template_id": "community-nursing-v1", "practitioner_id": "p1"}
    codes = [c.post("/sessions", json=body, headers=headers).status_code
             for _ in range(5)]
    assert codes[:3] == [200, 200, 200]
    assert codes[3:] == [429, 429]


def test_a_wrong_key_costs_nothing_and_does_not_burn_the_real_budget(client, monkeypatch):
    # A 401 does no model work, so an anonymous flood is cheap. Importantly it
    # must not consume the legitimate key's allowance either.
    c, _ = client
    monkeypatch.setenv("INTAKE_API_KEY", "s3cret")
    monkeypatch.setattr(main, "RATE_LIMIT_PER_MINUTE", 2)
    main._hits.clear()

    body = {"template_id": "community-nursing-v1", "practitioner_id": "p1"}
    for _ in range(10):
        assert c.post("/sessions", json=body,
                      headers={"X-Intake-Key": "wrong"}).status_code == 401
    assert c.post("/sessions", json=body,
                  headers={"X-Intake-Key": "s3cret"}).status_code == 200


def test_the_service_refuses_to_serve_ungated_by_accident(client, monkeypatch):
    # An empty secret version, or a deploy that drops --set-secrets, must not
    # quietly publish a Vertex-spending endpoint. Only the explicit local flag
    # opens it.
    c, _ = client
    monkeypatch.delenv("INTAKE_API_KEY", raising=False)
    monkeypatch.delenv("INTAKE_ALLOW_UNGATED", raising=False)
    body = {"template_id": "community-nursing-v1", "practitioner_id": "p1"}
    assert c.post("/sessions", json=body).status_code == 503

    monkeypatch.setenv("INTAKE_API_KEY", "")   # empty secret payload
    assert c.post("/sessions", json=body).status_code == 503


def test_an_oversized_text_chunk_is_rejected_before_any_model_call(client):
    # `text` is fed verbatim into every model call in the turn, so an unbounded
    # string here is the biggest denial-of-wallet lever in the service.
    c, _ = client
    s = new_session(c)
    r = c.post(f"/sessions/{s['session_id']}/chunks",
               json={"seq": 1, "text": "a" * 5000})
    assert r.status_code == 422


def test_a_traversing_template_id_cannot_probe_the_filesystem(client):
    c, _ = client
    for probe in ("../../../../etc/passwd", "../../pyproject", "..%2f..%2fetc"):
        r = c.post("/sessions", json={"template_id": probe, "practitioner_id": "p1"})
        assert r.status_code == 400, probe
        assert "/" not in r.json()["detail"].split("(have:")[0].replace(probe, "")


def test_unknown_session_is_a_404(client):
    c, _ = client
    assert c.get("/sessions/nope").status_code == 404


def test_the_loss_adjusting_template_runs_the_same_endpoints(client):
    # The decoupling test at the HTTP layer: no branch anywhere on template_id.
    c, _ = client
    s = c.post("/sessions", json={"template_id": "loss-adjusting-v1",
                                  "practitioner_id": "p1"}).json()
    sid = s["session_id"]
    for item_id in s["outstanding"]:
        c.post(f"/sessions/{sid}/resolve", json={
            "item_id": item_id, "resolution": "escalated", "reason": "site visit ended",
            "destination": "Claims handler queue"})
    assert c.post(f"/sessions/{sid}/report").status_code == 200


def test_escalation_still_files_when_the_model_is_unavailable(client, monkeypatch):
    """A spend cap, a quota, or an outage must not hold the report hostage.

    Drafting the follow-up text is the nicety. Filing it, with a destination, is
    the promise the gate makes — so the item resolves either way, flagged
    degraded so nobody mistakes the fallback wording for the agent's.
    """
    c, store = client
    s = new_session(c)
    sid = s["session_id"]

    async def unavailable(session_id, item_id):
        raise RuntimeError("403 Spend cap breached for project")

    monkeypatch.setattr(main._escalator, "escalate", unavailable)

    r = c.post(f"/sessions/{sid}/resolve",
               json={"item_id": "M20", "resolution": "escalated"})
    assert r.status_code == 200
    assert r.json()["degraded"] is True

    state = store.get(sid)
    assert state.slots["M20"]["state"] == "escalated"
    assert state.followups[0]["item_id"] == "M20"
    assert state.followups[0]["destination"], "a follow-up with no destination is a gap"
