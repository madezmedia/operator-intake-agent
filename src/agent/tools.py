"""Tools the model can call. Each tool reads/writes the lead's shared memory first.

The model decides WHEN to call; these functions own the business rules
(scoring, slot rules, what goes to Evolus).
"""
from __future__ import annotations

import logging

from ..config import settings
from ..evolus import client as evolus
from ..memory import store
from . import calendar

log = logging.getLogger("tools")

REQUIRED = ("name", "phone", "service")
LEAD_FIELDS = ("name", "phone", "email", "service", "zip", "address", "preferred_time", "urgency", "notes")


def _fn(name: str, description: str, properties: dict | None = None, required: list | None = None) -> dict:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties or {}, "required": required or []},
    }}


TOOLS = [
    _fn("save_lead_details",
        "Save any detail the lead just shared (name, phone, service needed, etc). "
        "Call this every time the lead gives new information.",
        {
            "name": {"type": "string"},
            "phone": {"type": "string"},
            "email": {"type": "string"},
            "service": {"type": "string", "description": "What they need done, in their words"},
            "zip": {"type": "string"},
            "address": {"type": "string"},
            "preferred_time": {"type": "string", "description": "When they want the visit"},
            "urgency": {"type": "string", "enum": ["emergency", "this_week", "flexible"]},
            "notes": {"type": "string"},
        }),
    _fn("lookup_business_info",
        "Answer a question about the business (prices, service area, hours, warranty) "
        "from the company knowledge library. Never guess prices.",
        {"question": {"type": "string"}}, ["question"]),
    _fn("qualify_lead",
        "Score the lead once you know their name, phone and service. Returns whether they "
        "can book and, if so, open appointment slots."),
    _fn("check_availability", "List open appointment slots, optionally for one day.",
        {"day": {"type": "string", "description": "e.g. 'Tuesday' or '2026-10-20'"}}),
    _fn("book_appointment", "Book a slot the lead agreed to. Only after qualify_lead says qualified.",
        {"slot_id": {"type": "string", "description": "slot_id from qualify_lead/check_availability"}},
        ["slot_id"]),
    _fn("schedule_followup",
        "Log a follow-up for a lead who isn't ready to book (or isn't qualified yet).",
        {"when": {"type": "string"}, "reason": {"type": "string"}}, ["reason"]),
]


def _missing(lead: dict) -> list[str]:
    return [f for f in REQUIRED if not lead.get(f)]


def score(lead: dict) -> int:
    """Deterministic, explainable 0-100 score (judges can read it)."""
    pts = {"phone": 25, "service": 25, "name": 15, "preferred_time": 15, "zip": 10, "address": 10}
    s = sum(v for k, v in pts.items() if lead.get(k))
    if lead.get("urgency") == "emergency":
        s += 10
    if lead.get("email"):
        s += 5
    return min(s, 100)


async def save_lead_details(lead_id: str, **fields) -> dict:
    patch = {k: str(v).strip() for k, v in fields.items() if k in LEAD_FIELDS and v not in (None, "")}
    lead = await store.update_lead(lead_id, patch)
    if patch:
        await store.log_event(lead_id, "intake", "saved " + ", ".join(sorted(patch)))
    return {"saved": sorted(patch), "missing": _missing(lead)}


async def lookup_business_info(lead_id: str, question: str = "") -> dict:
    lead = await store.get_lead(lead_id)
    try:
        res = await evolus.ask_agent(question, conversation_id=lead.get("evolus_conversation"))
        if res.get("conversation_id"):
            await store.update_lead(lead_id, {"evolus_conversation": res["conversation_id"]})
    except evolus.EvolusError as e:
        log.warning("knowledge lookup failed: %s", e)
        res = {"answer": None, "error": "knowledge library unavailable"}
    await store.log_event(lead_id, "knowledge", f"q: {question[:100]}")
    if res.get("offline"):
        return {"answer": None, "note": "Knowledge library not connected; offer to have the team confirm."}
    return {"answer": res.get("answer"), "error": res.get("error")}


async def qualify_lead(lead_id: str) -> dict:
    lead = await store.get_lead(lead_id)
    missing = _missing(lead)
    s = score(lead)
    qualified = not missing and s >= settings.qualify_threshold
    stage = "book" if qualified else ("intake" if missing else "followup")
    await store.update_lead(lead_id, {"score": s, "qualified": qualified, "stage": stage})
    await store.log_event(lead_id, "qualification", f"score={s} qualified={qualified}")
    out = {"score": s, "qualified": qualified, "missing": missing}
    if qualified:
        out["open_slots"] = await calendar.open_slots(lead.get("preferred_time"), limit=3)
    return out


async def check_availability(lead_id: str, day: str | None = None) -> dict:
    return {"open_slots": await calendar.open_slots(day)}


async def book_appointment(lead_id: str, slot_id: str = "first") -> dict:
    lead = await store.get_lead(lead_id)
    if not lead.get("qualified"):
        q = await qualify_lead(lead_id)
        if not q["qualified"]:
            return {"booked": False, "reason": "not qualified yet", "missing": q["missing"]}
    slot = await calendar.book(slot_id, lead_id)
    if not slot:
        return {"booked": False, "reason": "slot unavailable",
                "open_slots": await calendar.open_slots(limit=3)}
    lead = await store.update_lead(lead_id, {"stage": "followup", "booking": slot})
    await store.log_event(lead_id, "booking", f"booked {slot['label']}")

    # Hand the booked lead to the Evolus intake workflow (pipeline + owner visibility).
    summary = {k: lead.get(k) for k in LEAD_FIELDS if lead.get(k)}
    summary.update(score=lead.get("score"), slot=slot["label"], slot_id=slot["slot_id"])
    try:
        run = await evolus.push_lead_summary(lead_id, summary)
        await store.update_lead(lead_id, {"evolus_execution": run.get("execution_id"),
                                          "evolus_status": run.get("status")})
        await store.log_event(lead_id, "evolus", f"workflow {run.get('status')}")
    except evolus.EvolusError as e:
        log.warning("evolus push failed: %s", e)
        await store.log_event(lead_id, "evolus", "workflow push failed (will retry)")
    return {"booked": True, "slot_id": slot["slot_id"], "slot_label": slot["label"]}


async def schedule_followup(lead_id: str, reason: str = "", when: str = "tomorrow") -> dict:
    lead = await store.get_lead(lead_id)
    draft = None
    if settings.evolus_followup_tool:
        brief = (f"Write a short, friendly follow-up text from {settings.business_name} to "
                 f"{lead.get('name', 'the customer')} about their {lead.get('service', 'service request')}. "
                 f"Reason: {reason}. Send: {when}.")
        try:
            res = await evolus.run_ai_tool(settings.evolus_followup_tool, brief)
            draft = res.get("output")
        except evolus.EvolusError as e:
            log.warning("follow-up tool failed: %s", e)
    fu = {"when": when, "reason": reason, "draft": draft}
    await store.update_lead(lead_id, {"stage": "followup", "followup": fu})
    await store.log_event(lead_id, "followup", f"{when}: {reason[:100]}")
    return {"scheduled": True, "when": when}


REGISTRY = {
    "save_lead_details": save_lead_details,
    "lookup_business_info": lookup_business_info,
    "qualify_lead": qualify_lead,
    "check_availability": check_availability,
    "book_appointment": book_appointment,
    "schedule_followup": schedule_followup,
}


async def run(lead_id: str, name: str, args: dict) -> dict:
    fn = REGISTRY.get(name)
    if not fn:
        return {"error": f"unknown tool {name}"}
    try:
        return await fn(lead_id, **(args or {}))
    except TypeError as e:  # model sent an unexpected argument
        return {"error": f"bad arguments for {name}: {e}"}
