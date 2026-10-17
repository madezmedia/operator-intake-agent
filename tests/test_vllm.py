import json

import httpx

from src.config import settings
from src.models import vllm


def test_normalize_openai_tool_calls():
    msg = {"content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {
        "name": "save_lead_details", "arguments": json.dumps({"name": "Dana"})}}]}
    out = vllm.normalize(msg)
    assert out["tool_calls"] == [{"id": "c1", "name": "save_lead_details", "arguments": {"name": "Dana"}}]


def test_normalize_hermes_text_fallback():
    msg = {"content": 'Sure.\n<tool_call>\n{"name": "qualify_lead", "arguments": {}}\n</tool_call>'}
    out = vllm.normalize(msg)
    assert out["tool_calls"][0]["name"] == "qualify_lead"
    assert out["content"] == "Sure."


async def test_real_call_sends_tools(monkeypatch):
    seen = {}

    def handler(req: httpx.Request):
        seen.update(json.loads(req.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi", "tool_calls": []}}]})

    monkeypatch.setattr(settings, "vllm_stub", False)
    monkeypatch.setattr(vllm, "_transport", httpx.MockTransport(handler))
    out = await vllm.chat_with_tools([{"role": "user", "content": "hey"}], [{"type": "function"}])
    assert out == {"content": "hi", "tool_calls": []}
    assert seen["tool_choice"] == "auto" and seen["tools"] and seen["model"] == settings.vllm_model
