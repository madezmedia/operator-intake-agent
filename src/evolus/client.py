"""Evolus workspace integration.

Drives the Evolus event workspace from our app via the Evolus REST API:
- workflows: POST /api/v1/workflows/{id}/execute (text + files in, status out)
- agent chat: ask / ask-stream
- OpenAI-compatible /v1/chat/completions also available

API key is issued in the workspace dashboard after redeeming the event code.
"""
import httpx
from ..config import settings

BASE = "https://app.evolus.ai/api/v1"


def configured() -> bool:
    return bool(settings.evolus_api_key and settings.evolus_workspace_id)


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.evolus_api_key}"}


async def execute_workflow(workflow_id: str, payload: dict) -> dict:
    """Trigger an Evolus workflow; returns the execution result."""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{BASE}/workflows/{workflow_id}/execute",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


async def ask_agent(agent_id: str, message: str, stream: bool = False) -> dict:
    """Chat with an Evolus agent (ask or ask-stream)."""
    endpoint = "ask-stream" if stream else "ask"
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{BASE}/agents/{agent_id}/{endpoint}",
            headers=_headers(),
            json={"message": message, "workspace_id": settings.evolus_workspace_id},
        )
        resp.raise_for_status()
        return resp.json()


async def push_lead_summary(lead_id: str, summary: dict) -> None:
    """Push the qualified lead + booking into the Evolus workspace.

    Implemented once the intake workflow exists in the workspace:
    set EVOLUS_INTAKE_WORKFLOW_ID and call execute_workflow().
    """
    if not configured():
        return
    workflow_id = getattr(settings, "evolus_intake_workflow_id", "")
    if not workflow_id:
        raise RuntimeError("Set EVOLUS_INTAKE_WORKFLOW_ID from the workspace dashboard")
    await execute_workflow(workflow_id, {"lead_id": lead_id, **summary})
