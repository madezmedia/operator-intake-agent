"""Agent loop: intake → qualify → book → follow-up, driven by model tool calls.

Every turn starts from the lead's shared memory, so nothing is ever re-asked.
The model does the talking and picks the tool; tools own the business rules.
"""
from __future__ import annotations

import json

from ..config import settings
from ..memory import store
from ..models import vllm
from . import tools

SYSTEM = (
    "You are the intake agent for {business}, a local home-services business.\n"
    "Goal: capture the lead, qualify them, book a visit, or log a follow-up.\n"
    "Rules:\n"
    "- Be warm, brief and plain-spoken. Ask ONE question at a time.\n"
    "- Whenever the lead shares a detail, call save_lead_details.\n"
    "- Never re-ask anything already in 'Known about this lead'.\n"
    "- For prices, hours, service area or warranty, call lookup_business_info. Never guess prices.\n"
    "- Once you have name, phone and service, call qualify_lead, then offer up to 3 slots.\n"
    "- Only call book_appointment with a slot_id the lead agreed to.\n"
    "- If they are not ready, call schedule_followup.\n"
)


def _context(lead: dict) -> str:
    known = {k: v for k, v in lead.items() if k not in ("evolus_execution",)}
    return (f"Known about this lead: {json.dumps(known)}\n"
            f"Current stage: {lead.get('stage', 'intake')} (intake → qualify → book → followup).")


async def handle_message(lead_id: str, user_text: str) -> str:
    lead = await store.get_lead(lead_id)
    if not lead:
        lead = await store.update_lead(lead_id, {"stage": "intake"})
        await store.log_event(lead_id, "intake", "new lead")
    history = await store.get_messages(lead_id)

    messages = [
        {"role": "system", "content": SYSTEM.format(business=settings.business_name)},
        {"role": "system", "content": _context(lead)},
        *history,
        {"role": "user", "content": user_text},
    ]
    await store.log_event(lead_id, "message", f"lead: {user_text[:120]}")

    reply = ""
    for _ in range(settings.max_tool_rounds):
        out = await vllm.chat_with_tools(messages, tools.TOOLS)
        if not out["tool_calls"]:
            reply = out["content"]
            break
        messages.append({
            "role": "assistant", "content": out["content"] or "",
            "tool_calls": [{"id": c["id"], "type": "function",
                            "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}}
                           for c in out["tool_calls"]],
        })
        for c in out["tool_calls"]:
            result = await tools.run(lead_id, c["name"], c["arguments"])
            await store.log_event(lead_id, "tool", f"{c['name']} -> {json.dumps(result)[:160]}")
            messages.append({"role": "tool", "tool_call_id": c["id"], "name": c["name"],
                             "content": json.dumps(result)})
        # Refresh the known-facts line so the next round sees what tools just saved.
        messages[1] = {"role": "system", "content": _context(await store.get_lead(lead_id))}

    if not reply:
        reply = "Thanks! Someone from our team will follow up shortly."

    await store.append_messages(lead_id, {"role": "user", "content": user_text},
                                {"role": "assistant", "content": reply})
    await store.log_event(lead_id, "message", f"agent: {reply[:120]}")
    return reply


async def qualify(lead_id: str) -> dict:
    """Kept for callers outside the chat loop."""
    return await tools.qualify_lead(lead_id)
