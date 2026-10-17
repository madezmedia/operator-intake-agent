"""Evolus workspace integration: our app drives Evolus through its APIs.

Per https://evolus.ai/en/developers:
- Agent chat:   POST {openai_base}/chat/completions, Authorization: Bearer <key>,
                model "<applicationId>:<agentId>", conversation kept via X-Conversation-Id
- Workflows:    POST {api_base}/workflows/{id}/execute (multipart: input, parameters)
                -> 202 {executionId}; GET {api_base}/workflows/{id}/executions/{executionId}
                status Pending | Running | Completed | Failed
- AI Tools:     POST {api_base}/ai-tools/{tool}/run  {text, secondaryText, options}
- Libraries:    POST {api_base}/memories/{libraryId}/documents?language=en (multipart file)
REST auth: X-ApiKey + X-Application-Id. Keys live only in .env.

Without a key or application ID, every call returns {"offline": True} instead of
raising, so the demo still runs end to end.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

import httpx

from ..config import settings

log = logging.getLogger("evolus")

# Tests swap this for httpx.MockTransport.
_transport: httpx.AsyncBaseTransport | None = None

TERMINAL = {"completed", "failed"}


class EvolusError(RuntimeError):
    pass


def application_id() -> str:
    return settings.evolus_application_id or settings.evolus_workspace_id


def configured() -> bool:
    return bool(settings.evolus_api_key and application_id())


def _rest_headers() -> dict:
    return {"X-ApiKey": settings.evolus_api_key, "X-Application-Id": application_id()}


async def _send(method: str, url: str, headers: dict, **kw) -> httpx.Response:
    async with httpx.AsyncClient(timeout=settings.evolus_timeout, transport=_transport) as c:
        try:
            resp = await c.request(method, url, headers=headers, **kw)
        except httpx.HTTPError as e:
            raise EvolusError(f"{method} {url}: {e.__class__.__name__}") from e
    if resp.status_code == 402:
        raise EvolusError("Evolus credits exhausted (402)")
    if resp.status_code == 409:
        raise EvolusError("Workflow is switched off in the console (409)")
    if resp.status_code >= 400:
        # Never echo request headers; trimmed body text is safe to surface.
        raise EvolusError(f"{method} {url} -> {resp.status_code}: {resp.text[:300]}")
    return resp


def _json(resp: httpx.Response) -> dict:
    try:
        data = resp.json()
        return data if isinstance(data, dict) else {"data": data}
    except ValueError:
        return {"text": resp.text}


# ---------------------------------------------------------------- workflows

async def get_execution(workflow_id: str, execution_id: str) -> dict:
    resp = await _send("GET", f"{settings.evolus_api_base}/workflows/{workflow_id}/executions/{execution_id}",
                       _rest_headers())
    return _json(resp)


def _as_text(inputs: dict) -> str:
    return "\n".join(f"{k}: {v}" for k, v in inputs.items() if v not in (None, ""))


async def execute_workflow(workflow_id: str, inputs: dict, wait: bool = True) -> dict:
    """Run a workflow. `inputs` goes in as readable text (`input`) and as a flat JSON
    object (`parameters`). With wait=True, poll until Completed/Failed.

    Returns {"execution_id", "status", "output", "raw"} (status lower-cased).
    """
    if not configured() or not workflow_id:
        log.info("evolus offline: workflow %s not executed", workflow_id or "<unset>")
        return {"offline": True, "status": "skipped", "execution_id": None, "output": None}

    flat = {k: (v if isinstance(v, (str, int, float, bool)) or v is None else json.dumps(v))
            for k, v in inputs.items()}
    form = {"input": (None, _as_text(inputs)), "parameters": (None, json.dumps(flat))}
    resp = await _send("POST", f"{settings.evolus_api_base}/workflows/{workflow_id}/execute",
                       _rest_headers(), files=form)
    started = _json(resp)
    exec_id = started.get("executionId") or resp.headers.get("X-Workflow-Execution-Id")
    result = {"execution_id": exec_id, "status": "pending", "output": None, "raw": started}
    if not wait or not exec_id:
        return result

    deadline = time.monotonic() + settings.evolus_poll_timeout
    while time.monotonic() < deadline:
        await asyncio.sleep(settings.evolus_poll_seconds)
        cur = await get_execution(workflow_id, exec_id)
        status = str(cur.get("status", "")).lower()
        result.update(status=status or "unknown", output=cur.get("output") or cur.get("result"), raw=cur)
        if status in TERMINAL:
            return result
    result["status"] = "timeout"
    return result


# ---------------------------------------------------------------- agent chat

async def ask_agent(question: str, agent_id: str | None = None,
                    conversation_id: str | None = None) -> dict:
    """Ask the Evolus agent (answers from its knowledge library).

    Returns {"answer", "conversation_id"}; pass conversation_id back to continue.
    """
    agent_id = agent_id or settings.evolus_agent_id
    if not configured() or not agent_id:
        return {"offline": True, "answer": None}
    headers = {"Authorization": f"Bearer {settings.evolus_api_key}"}
    if conversation_id:
        headers["X-Conversation-Id"] = conversation_id
    resp = await _send("POST", f"{settings.evolus_openai_base}/chat/completions", headers,
                       json={"model": f"{application_id()}:{agent_id}",
                             "messages": [{"role": "user", "content": question}]})
    data = _json(resp)
    try:
        answer = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        answer = None
    return {"answer": answer, "conversation_id": resp.headers.get("X-Conversation-Id")}


# ---------------------------------------------------------------- AI Tools

async def run_ai_tool(tool: str, text: str, secondary_text: str = "",
                      options: dict | None = None) -> dict:
    """Run an Evolus AI Tool (e.g. "email", "summarize"). Returns {"output", "credits"}."""
    if not configured() or not tool:
        return {"offline": True, "output": None}
    body = {"text": text, "secondaryText": secondary_text, "options": options or {}}
    resp = await _send("POST", f"{settings.evolus_api_base}/ai-tools/{tool}/run",
                       _rest_headers(), json=body)
    data = _json(resp)
    return {"output": data.get("output"), "credits": data.get("creditsConsumed")}


# ---------------------------------------------------------------- knowledge library

async def upload_library_document(library_id: str, filename: str, content: bytes,
                                  language: str = "en") -> dict:
    """Add a document to a knowledge library (indexing runs in the background)."""
    if not configured() or not library_id:
        return {"offline": True}
    resp = await _send("POST", f"{settings.evolus_api_base}/memories/{library_id}/documents",
                       _rest_headers(), params={"language": language},
                       files={"file": (filename, content, "text/markdown")})
    return _json(resp)


async def list_library_documents(library_id: str) -> dict:
    resp = await _send("GET", f"{settings.evolus_api_base}/memories/{library_id}/documents",
                       _rest_headers())
    return _json(resp)


# ---------------------------------------------------------------- pipeline hook

async def push_lead_summary(lead_id: str, summary: dict) -> dict:
    """Hand the booked lead to the Evolus intake workflow (fire and record)."""
    return await execute_workflow(settings.evolus_intake_workflow_id,
                                  {"lead_id": lead_id, **summary}, wait=False)


def status() -> dict:
    """Non-secret integration status for /healthz."""
    return {
        "configured": configured(),
        "agent": bool(settings.evolus_agent_id),
        "intake_workflow": bool(settings.evolus_intake_workflow_id),
        "followup_tool": settings.evolus_followup_tool or None,
        "library": bool(settings.evolus_library_id),
    }
