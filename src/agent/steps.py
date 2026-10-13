"""Agent steps: intake → qualify → book → follow-up.

Each step reads the lead's shared memory first, so nothing is ever re-asked.
The model does the talking; these functions own the business logic.
"""
from ..memory import store
from ..models import vllm
from ..config import settings

SYSTEM = (
    "You are the intake agent for {business}, a local service business. "
    "Be warm, brief, and plain-spoken. Ask ONE question at a time. "
    "Never re-ask something the lead already told you — it's in the context."
)


async def handle_message(lead_id: str, user_text: str) -> str:
    lead = await store.get_lead(lead_id)
    stage = lead.get("stage", "intake")

    messages = [
        {"role": "system", "content": SYSTEM.format(business=settings.business_name)},
        {"role": "system", "content": f"Known about this lead so far: {lead}"},
        {"role": "system", "content": f"Current stage: {stage}. Stages: intake → qualify → book → followup."},
        {"role": "user", "content": user_text},
    ]
    reply = await vllm.chat(messages)

    await store.log_event(lead_id, "message", f"lead: {user_text[:120]}")
    await store.log_event(lead_id, "message", f"agent: {reply[:120]}")
    return reply


async def qualify(lead_id: str) -> dict:
    """Score the lead 0-100 based on shared context. Returns {score, qualified}."""
    lead = await store.get_lead(lead_id)
    verdict = await vllm.chat([
        {"role": "system", "content": "Score this service lead 0-100 for likelihood to book. Reply with just the number."},
        {"role": "user", "content": str(lead)},
    ])
    try:
        score = int("".join(c for c in verdict if c.isdigit()) or 0)
    except ValueError:
        score = 0
    qualified = score >= 60
    await store.update_lead(lead_id, {"score": score, "qualified": qualified,
                                      "stage": "book" if qualified else "followup"})
    await store.log_event(lead_id, "qualification", f"score={score} qualified={qualified}")
    return {"score": score, "qualified": qualified}
