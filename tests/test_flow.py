"""End-to-end intake → qualify → book with the stub model and Evolus offline."""
from src.agent import steps
from src.memory import store


async def test_full_intake_to_booking():
    lid = "t1"
    r1 = await steps.handle_message(lid, "Hi, my AC stopped blowing cold air")
    assert "name" in r1.lower() or "phone" in r1.lower()

    await steps.handle_message(lid, "I'm Dana Brooks, 704-555-0142, zip 28205, tomorrow if possible")
    lead = await store.get_lead(lid)
    assert lead["name"] == "Dana Brooks" and lead["phone"].endswith("0142") and lead["zip"] == "28205"
    assert "ac" in lead["service"].lower()

    r3 = await steps.handle_message(lid, "Can you book me in?")
    assert "slots" in r3.lower()
    assert (await store.get_lead(lid))["qualified"] is True

    r4 = await steps.handle_message(lid, "The first one sounds good")
    lead = await store.get_lead(lid)
    assert "booked" in r4.lower()
    assert lead["booking"]["slot_id"] and lead["stage"] == "followup"
    assert lead["evolus_status"] == "skipped"  # offline: no key configured

    kinds = [e["kind"] for e in await store.get_timeline(lid)]
    for k in ("intake", "qualification", "booking", "evolus", "tool"):
        assert k in kinds
    # Never re-asked: history carried forward
    assert len(await store.get_messages(lid)) == 8


async def test_unqualified_cannot_book():
    from src.agent import tools
    out = await tools.book_appointment("t2", "first")
    assert out["booked"] is False and "phone" in out["missing"]


async def test_slot_cannot_be_double_booked():
    from src.agent import tools, calendar
    for lid in ("a", "b"):
        await tools.save_lead_details(lid, name="X", phone="7045550100", service="leak",
                                      preferred_time="soon")
    slot = (await calendar.open_slots(limit=1))[0]["slot_id"]
    assert (await tools.book_appointment("a", slot))["booked"] is True
    second = await tools.book_appointment("b", slot)
    assert second["booked"] is False and second["open_slots"]
