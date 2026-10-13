"""Evolus workspace integration: our app drives Evolus through its APIs.

Surfaces used (track requirement 4):
- Workflows:   POST {api_base}/workflows/{id}/execute, then poll the execution status
- Agent chat:  OpenAI-compatible POST {openai_base}/chat/completions with
               model "<applicationId>:<agentId>" (default), or REST ask
- AI Tools:    POST {api_base}{evolus_ai_tool_path}

Auth: X-ApiKey + X-Application-Id headers. Keys live only in .env.

When the key or application ID is missing, every call returns an offline result
marked {"offline": True} instead of raising, so the demo still runs end to end.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from ..config import settings

log = logging.getLogger("evolus")

# Tests swap this for httpx.MockTransport.
_transport: httpx.AsyncBaseTransport | None = None

TERMINAL = {"completed", "succeeded", "success", "failed", "error", "cancelled", "canceled", "timeout"}


class EvolusError(RuntimeError):
    pass


def application_id() -> str:
    return settings.evolus_application_id or settings.evolus_workspace_id


def configured() -> bool:
    return bool(settings.evolus_api_key and application_id())


def _headers() -> dict:
    return {
        "X-ApiKey": settings.evolus_api_key,
        "X-Application-Id": application_id(),
        "Content-Type": "application/json",
    }


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=settings.evolus_timeout, transport=_transport)


async def _request(method: str, url: str, **kw) -> dict:
    async with _client() as c:
        try:
            resp = await c.request(method, url, headers=_headers(), **kw)
        except httpx.HTTPError as e:
            raise EvolusError(f"{method} {url}: {e.__class__.__name__}") from e
    if resp.status_code >= 400:
        # Never echo request headers; body text is safe to surface (trimmed).
        raise EvolusError(f"{method} {url} -> {resp.status_code}: {resp.text[:300]}")
    try:
        return resp.json()
    except ValueError:
        return {"text": resp.text}


def _pick(d: dict, *keys: str, default: Any = None) -> Any:
    """Read the first present key, also looking one level into 'data'."""
    for src in (d, d.get("data") if isinstance(d.get("data"), dict) else {}):
        for k in keys:
            if k in src and src[k] is not None:
                return src[k]
    return default


# ---------------------------------------------------------------- workflows

async def get_execution(execution_id: str) -> dict:
    path = settings.evolus_execution_status_path.format(execution_id=execution_id)
    return await _request("GET", settings.evolus_api_base + path)


async def execute_workflow(workflow_id: str, inputs: dict, wait: bool = True) -> dict:
    """Run a workflow. With wait=True, poll until it reaches a terminal status.

    Returns {"execution_id", "status", "output", "raw"}.
    """
    if not configured() or not workflow_id:
        log.info("evolus offline: workflow %s not executed", workflow_id or "<unset>")
        return {"offline": True, "status": "skipped", "execution_id": None, "output": None}

    started = await _request(
        "POST",
        f"{settings.evolus_api_base}/workflows/{workflow_id}/execute",
        json={"input": inputs, "text": _as_text(inputs)},
    )
    exec_id = _pick(started, "executionId", "execution_id", "id")
    status = str(_pick(started, "status", "state", default="")).lower()
    result = {"execution_id": exec_id, "status": status or "started",
              "output": _pick(started, "output", "result", "outputs"), "raw": started}

    if not wait or not exec_id or status in TERMINAL:
        return result

    deadline = time.monotonic() + settings.evolus_poll_timeout
    while time.monotonic() < deadline:
        await asyncio.sleep(settings.evolus_poll_seconds)
        cur = await get_execution(exec_id)
        status = str(_pick(cur, "status", "state", default="")).lower()
        result.update(status=status, output=_pick(cur, "output", "result", "outputs"), raw=cur)
        if status in TERMINAL:
            return result
    result["status"] = "timeout"
    return result


def _as_text(inputs: dict) -> str:
    return "\n".join(f"{k}: {v}" for k, v in inputs.items() if v not in (None, ""))


# ---------------------------------------------------------------- agent chat

async def ask_agent(question: str, agent_id: str | None = None,
                    history: list[dict] | None = None) -> dict:
    """Ask the Evolus agent (backed by the knowledge library). Returns {"answer", ...}."""
    agent_id = agent_id or settings.evolus_agent_id
    if not configured() or not agent_id:
        return {"offline": True, "answer": None}

    if settings.evolus_agent_chat_mode == "rest":
        path = settings.evolus_agent_ask_path.format(agent_id=agent_id)
        data = await _request("POST", settings.evolus_api_base + path,
                              json={"message": question, "question": question})
        answer = _pick(data, "answer", "response", "message", "text", "content")
        return {"answer": answer, "raw": data}

    messages = list(history or []) + [{"role": "user", "content": question}]
    data = await _request(
        "POST",
        f"{settings.evolus_openai_base}/chat/completions",
        json={"model": f"{application_id()}:{agent_id}", "messages": messages},
    )
    try:
        answer = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        answer = _pick(data, "answer", "content", "text")
    return {"answer": answer, "raw": data}


# ---------------------------------------------------------------- AI Tools

async def run_ai_tool(tool_id: str, inputs: dict) -> dict:
    if not configured() or not tool_id:
        return {"offline": True, "output": None}
    path = settings.evolus_ai_tool_path.format(tool_id=tool_id)
    data = await _request("POST", settings.evolus_api_base + path, json={"input": inputs})
    return {"output": _pick(data, "output", "result", "text", default=data), "raw": data}


# ---------------------------------------------------------------- pipeline hook

async def push_lead_summary(lead_id: str, summary: dict) -> dict:
    """Hand the qualified, booked lead to the Evolus intake workflow (fire and record)."""
    return await execute_workflow(settings.evolus_intake_workflow_id,
                                  {"lead_id": lead_id, **summary}, wait=False)


def status() -> dict:
    """Non-secret integration status for /healthz."""
    return {
        "configured": configured(),
        "agent": bool(settings.evolus_agent_id),
        "intake_workflow": bool(settings.evolus_intake_workflow_id),
        "followup_tool": bool(settings.evolus_followup_tool_id),
        "agent_chat_mode": settings.evolus_agent_chat_mode,
    }
