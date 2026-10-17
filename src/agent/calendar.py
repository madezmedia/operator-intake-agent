"""Mock calendar for the demo (real calendar OAuth is out of scope).

Slots: next 5 business days at 9:00, 11:00, 13:00, 15:00 in the business timezone.
Bookings are stored in shared memory so two leads can never take the same slot.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..config import settings
from ..memory import store

HOURS = (9, 11, 13, 15)


def _slots(now: datetime | None = None, days: int = 5) -> list[dict]:
    tz = ZoneInfo(settings.business_timezone)
    now = now or datetime.now(tz)
    out, d = [], now.date()
    while len({s["date"] for s in out}) < days:
        d += timedelta(days=1)
        if d.weekday() >= 5:
            continue
        for h in HOURS:
            start = datetime(d.year, d.month, d.day, h, tzinfo=tz)
            out.append({
                "slot_id": start.strftime("%Y-%m-%dT%H:%M"),
                "date": d.isoformat(),
                "label": start.strftime("%a %b %-d, %-I:%M %p"),
            })
    return out


async def open_slots(day: str | None = None, limit: int = 6) -> list[dict]:
    taken = await store.booked_slots()
    slots = [s for s in _slots() if s["slot_id"] not in taken]
    if day:
        key = day.strip().lower()[:3]
        slots = [s for s in slots if s["label"].lower().startswith(key) or s["date"] == day] or slots
    return slots[:limit]


async def book(slot_id: str, lead_id: str) -> dict | None:
    """Claim a slot. slot_id may be 'first' (first open slot). None if unavailable."""
    if slot_id in ("first", "", None):
        opts = await open_slots(limit=1)
        if not opts:
            return None
        slot_id = opts[0]["slot_id"]
    match = next((s for s in _slots() if s["slot_id"] == slot_id), None)
    if not match or not await store.claim_slot(slot_id, lead_id):
        return None
    return match
