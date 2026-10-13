"""Shared memory layer: every agent step reads/writes the same lead context.

Dev backend: Redis. Production: ACMI/LogMem bridge (same profile/signal/timeline
semantics — swap MEMORY_BACKEND=acmi and point at the bridge).
"""
import json
import redis.asyncio as redis
from .config import settings

_client: redis.Redis | None = None


def _client_or_raise() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def get_lead(lead_id: str) -> dict:
    """Read the full shared context for a lead."""
    raw = await _client_or_raise().get(f"lead:{lead_id}")
    return json.loads(raw) if raw else {}


async def update_lead(lead_id: str, patch: dict) -> dict:
    """Merge new facts into the lead's shared context. Returns the full context."""
    lead = await get_lead(lead_id)
    lead.update(patch)
    await _client_or_raise().set(f"lead:{lead_id}", json.dumps(lead))
    return lead


async def log_event(lead_id: str, kind: str, text: str) -> None:
    """Append a timeline event for a lead (intake, qualification, booking, follow-up)."""
    await _client_or_raise().rpush(f"lead:{lead_id}:timeline", json.dumps({"kind": kind, "text": text}))
