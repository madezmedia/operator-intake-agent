import json

import httpx
import pytest

from src.config import settings
from src.evolus import client as evolus


@pytest.fixture
def online(monkeypatch):
    monkeypatch.setattr(settings, "evolus_api_key", "test-key")
    monkeypatch.setattr(settings, "evolus_application_id", "app-123")
    monkeypatch.setattr(settings, "evolus_agent_id", "agent-9")


def use(monkeypatch, handler):
    monkeypatch.setattr(evolus, "_transport", httpx.MockTransport(handler))


async def test_offline_without_key():
    assert (await evolus.execute_workflow("wf", {"a": 1}))["offline"] is True
    assert (await evolus.ask_agent("hours?"))["offline"] is True


async def test_workflow_execute_then_poll(monkeypatch, online):
    calls = []

    def handler(req: httpx.Request):
        calls.append((req.method, req.url.path))
        assert req.headers["X-ApiKey"] == "test-key"
        assert req.headers["X-Application-Id"] == "app-123"
        if req.method == "POST":
            body = json.loads(req.content)
            assert body["input"]["lead_id"] == "L1"
            return httpx.Response(200, json={"executionId": "ex1", "status": "running"})
        n = sum(1 for m, _ in calls if m == "GET")
        return httpx.Response(200, json={"status": "completed" if n >= 2 else "running",
                                         "output": {"ok": True}})

    use(monkeypatch, handler)
    res = await evolus.execute_workflow("wf1", {"lead_id": "L1"})
    assert res["status"] == "completed" and res["output"] == {"ok": True}
    assert calls[0] == ("POST", "/api/v1/workflows/wf1/execute")
    assert calls[1] == ("GET", "/api/v1/workflows/executions/ex1")


async def test_agent_chat_openai_mode(monkeypatch, online):
    def handler(req: httpx.Request):
        body = json.loads(req.content)
        assert req.url.path == "/v1/chat/completions"
        assert body["model"] == "app-123:agent-9"
        return httpx.Response(200, json={"choices": [{"message": {"content": "We serve Charlotte."}}]})

    use(monkeypatch, handler)
    assert (await evolus.ask_agent("area?"))["answer"] == "We serve Charlotte."


async def test_http_error_is_wrapped_without_key(monkeypatch, online):
    use(monkeypatch, lambda req: httpx.Response(401, text="bad key"))
    with pytest.raises(evolus.EvolusError) as e:
        await evolus.ask_agent("x")
    assert "401" in str(e.value) and "test-key" not in str(e.value)


async def test_booking_survives_evolus_outage(monkeypatch, online):
    from src.agent import tools
    monkeypatch.setattr(settings, "evolus_intake_workflow_id", "wf1")
    use(monkeypatch, lambda req: httpx.Response(503, text="down"))
    await tools.save_lead_details("L9", name="Sam", phone="7045550199", service="leak",
                                  preferred_time="Tue")
    out = await tools.book_appointment("L9", "first")
    assert out["booked"] is True
