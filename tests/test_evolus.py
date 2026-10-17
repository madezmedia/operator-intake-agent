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
    assert (await evolus.run_ai_tool("email", "x"))["offline"] is True


async def test_workflow_execute_multipart_then_poll(monkeypatch, online):
    calls = []

    def handler(req: httpx.Request):
        calls.append((req.method, req.url.path))
        assert req.headers["X-ApiKey"] == "test-key"
        assert req.headers["X-Application-Id"] == "app-123"
        if req.method == "POST":
            assert req.headers["content-type"].startswith("multipart/form-data")
            body = req.content.decode()
            assert 'name="input"' in body and "lead_id: L1" in body
            assert 'name="parameters"' in body and '"lead_id": "L1"' in body
            return httpx.Response(202, json={"executionId": "ex1", "jobId": "j1"})
        n = sum(1 for m, _ in calls if m == "GET")
        return httpx.Response(200, json={"status": "Completed" if n >= 2 else "Running",
                                         "output": {"ok": True}})

    use(monkeypatch, handler)
    res = await evolus.execute_workflow("wf1", {"lead_id": "L1", "booking": {"slot": "x"}})
    assert res["status"] == "completed" and res["output"] == {"ok": True}
    assert calls[0] == ("POST", "/api/v1/workflows/wf1/execute")
    assert calls[1] == ("GET", "/api/v1/workflows/wf1/executions/ex1")


async def test_execution_id_from_header(monkeypatch, online):
    use(monkeypatch, lambda req: httpx.Response(202, json={}, headers={"X-Workflow-Execution-Id": "ex9"}))
    res = await evolus.execute_workflow("wf1", {"a": 1}, wait=False)
    assert res["execution_id"] == "ex9" and res["status"] == "pending"


async def test_agent_chat_bearer_and_conversation(monkeypatch, online):
    def handler(req: httpx.Request):
        body = json.loads(req.content)
        assert req.url.path == "/v1/chat/completions"
        assert req.headers["Authorization"] == "Bearer test-key"
        assert req.headers.get("X-Conversation-Id") == "conv-1"
        assert body["model"] == "app-123:agent-9"
        return httpx.Response(200, headers={"X-Conversation-Id": "conv-1"},
                              json={"choices": [{"message": {"content": "We serve Charlotte."}}]})

    use(monkeypatch, handler)
    res = await evolus.ask_agent("area?", conversation_id="conv-1")
    assert res == {"answer": "We serve Charlotte.", "conversation_id": "conv-1"}


async def test_ai_tool_run(monkeypatch, online):
    def handler(req: httpx.Request):
        assert req.url.path == "/api/v1/ai-tools/email/run"
        assert json.loads(req.content)["text"] == "brief"
        return httpx.Response(200, json={"tool": "email", "output": "Hi Dana", "creditsConsumed": 3})

    use(monkeypatch, handler)
    assert await evolus.run_ai_tool("email", "brief") == {"output": "Hi Dana", "credits": 3}


async def test_library_upload(monkeypatch, online):
    def handler(req: httpx.Request):
        assert req.url.path == "/api/v1/memories/lib1/documents"
        assert req.url.params["language"] == "en"
        assert 'filename="faq.md"' in req.content.decode()
        return httpx.Response(201, json={"id": "doc1"})

    use(monkeypatch, handler)
    assert (await evolus.upload_library_document("lib1", "faq.md", b"# FAQ"))["id"] == "doc1"


@pytest.mark.parametrize("code,msg", [(401, "401"), (402, "credits"), (409, "switched off")])
async def test_errors_wrapped_without_key(monkeypatch, online, code, msg):
    use(monkeypatch, lambda req: httpx.Response(code, text="nope"))
    with pytest.raises(evolus.EvolusError) as e:
        await evolus.execute_workflow("wf1", {"a": 1})
    assert msg in str(e.value) and "test-key" not in str(e.value)


async def test_booking_survives_evolus_outage(monkeypatch, online):
    from src.agent import tools
    monkeypatch.setattr(settings, "evolus_intake_workflow_id", "wf1")
    use(monkeypatch, lambda req: httpx.Response(503, text="down"))
    await tools.save_lead_details("L9", name="Sam", phone="7045550199", service="leak",
                                  preferred_time="Tue")
    out = await tools.book_appointment("L9", "first")
    assert out["booked"] is True
