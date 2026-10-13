"""OpenAI-compatible client for the open model served by vLLM on AMD.

Tool calling: start vLLM with
    --enable-auto-tool-choice --tool-call-parser hermes
(Qwen2.5 uses the Hermes format). If the server was started without the parser,
Qwen still emits <tool_call>{...}</tool_call> in the text; we parse that as a fallback.

VLLM_STUB=true swaps in a small rule-based fake model so the full tool loop runs
with no GPU. It is for smoke tests only, not the demo.
"""
from __future__ import annotations

import json
import re
import uuid

import httpx

from ..config import settings

_transport: httpx.AsyncBaseTransport | None = None  # tests swap in MockTransport

_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)


async def _complete(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=settings.vllm_timeout, transport=_transport) as c:
        resp = await c.post(
            f"{settings.vllm_endpoint}/chat/completions",
            headers={"Authorization": f"Bearer {settings.vllm_api_key}"},
            json={"model": settings.vllm_model, **payload},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]


async def chat(messages: list[dict], temperature: float = 0.3) -> str:
    """Plain completion. Returns the reply text."""
    if settings.vllm_stub:
        return "[stub] Thanks! What's the best phone number to reach you, and what day works?"
    msg = await _complete({"messages": messages, "temperature": temperature})
    return msg.get("content") or ""


async def chat_with_tools(messages: list[dict], tools: list[dict],
                          temperature: float = 0.2) -> dict:
    """Completion with tools. Returns {"content": str, "tool_calls": [...]} where each
    tool call is {"id", "name", "arguments": dict}."""
    if settings.vllm_stub:
        return _stub_model(messages)
    msg = await _complete({"messages": messages, "tools": tools,
                           "tool_choice": "auto", "temperature": temperature})
    return normalize(msg)


def normalize(msg: dict) -> dict:
    """Turn a raw assistant message into {"content", "tool_calls"} (hermes fallback included)."""
    content = msg.get("content") or ""
    calls = []
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function", {})
        calls.append({"id": tc.get("id") or _id(), "name": fn.get("name", ""),
                      "arguments": _args(fn.get("arguments"))})
    if not calls and "<tool_call>" in content:
        for raw in _TOOL_CALL_RE.findall(content):
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            calls.append({"id": _id(), "name": obj.get("name", ""),
                          "arguments": _args(obj.get("arguments"))})
        content = _TOOL_CALL_RE.sub("", content).strip()
    return {"content": content, "tool_calls": calls}


def _args(a) -> dict:
    if isinstance(a, dict):
        return a
    if not a:
        return {}
    try:
        v = json.loads(a)
        return v if isinstance(v, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _id() -> str:
    return "call_" + uuid.uuid4().hex[:12]


# ------------------------------------------------------------------ stub model

_PHONE = re.compile(r"(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_NAME = re.compile(r"\b(?:[Ii]['’]?m|[Mm]y name is|[Tt]his is)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)")
_ZIP = re.compile(r"\b\d{5}\b")
_SERVICES = ["ac", "a/c", "air conditioning", "heat", "furnace", "plumb", "leak", "drain",
             "water heater", "lawn", "landscap", "roof", "electric", "hvac"]
_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "tomorrow", "today"]


def _stub_model(messages: list[dict]) -> dict:
    """Deterministic fake: one tool round per user turn, then a short reply."""
    last = messages[-1]
    if last.get("role") == "tool":
        return {"content": _stub_reply_after_tools(messages), "tool_calls": []}

    text = last.get("content", "")
    low = text.lower()
    calls = []
    details = {}
    if m := _NAME.search(text):
        details["name"] = m.group(1)
    if m := _PHONE.search(text):
        details["phone"] = m.group(0)
    if m := _EMAIL.search(text):
        details["email"] = m.group(0)
    if m := _ZIP.search(text):
        if not _PHONE.search(text) or m.group(0) not in _PHONE.search(text).group(0):
            details["zip"] = m.group(0)
    for s in _SERVICES:
        if s in low:
            details["service"] = text[:80]
            break
    if any(d in low for d in _DAYS) or "asap" in low:
        details["preferred_time"] = next((d for d in _DAYS if d in low), "asap")
    if details:
        calls.append({"id": _id(), "name": "save_lead_details", "arguments": details})
    if "?" in text and any(w in low for w in ["price", "cost", "how much", "hours", "warranty", "area"]):
        calls.append({"id": _id(), "name": "lookup_business_info", "arguments": {"question": text}})
    if any(w in low for w in ["first one", "the first", "sounds good", "that works"]):
        calls.append({"id": _id(), "name": "book_appointment", "arguments": {"slot_id": "first"}})
    elif any(w in low for w in ["book", "schedule", "appointment"]):
        calls.append({"id": _id(), "name": "qualify_lead", "arguments": {}})
    return {"content": "", "tool_calls": calls} if calls else {
        "content": "[stub] Thanks! What do you need help with, and what's your name and best phone number?",
        "tool_calls": []}


def _stub_reply_after_tools(messages: list[dict]) -> str:
    tool_msgs = []
    for m in reversed(messages):
        if m.get("role") != "tool":
            break
        tool_msgs.append(m)
    results = {}
    for m in tool_msgs:
        try:
            results[m.get("name")] = json.loads(m.get("content") or "{}")
        except json.JSONDecodeError:
            results[m.get("name")] = {}
    if "book_appointment" in results:
        b = results["book_appointment"]
        return f"[stub] You're booked for {b.get('slot_label', 'that time')}. We'll text a reminder."
    if "qualify_lead" in results:
        q = results["qualify_lead"]
        if q.get("qualified"):
            return "[stub] Great, you're all set to book. Open slots: " + ", ".join(
                s["label"] for s in q.get("open_slots", [])[:3])
        missing = q.get("missing") or []
        return "[stub] Almost there. Could you share your " + " and ".join(missing[:2]) + "?"
    if "lookup_business_info" in results:
        ans = results["lookup_business_info"].get("answer")
        return f"[stub] {ans}" if ans else "[stub] Good question, I'll have the team confirm that."
    missing = results.get("save_lead_details", {}).get("missing") or []
    if missing:
        return "[stub] Got it, thanks. What's your " + " and ".join(missing[:2]) + "?"
    return "[stub] Got it. Want me to book you in?"
