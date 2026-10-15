# Operator Intake Agent

Pitch deck for the AMD Developer Hackathon ACT III, Evolus Business Agents track.
Plain-language slides. Speak one slide at a time.

---

## Title

**Operator Intake Agent**

The after-hours front desk for a local service business.

A homeowner messages at night. The agent takes the lead, qualifies it, and books the next open visit. The same facts stay in one shared record the whole way.

Built by madezmedia. Open model on AMD via vLLM. The business side lives in an Evolus workspace.

---

## The problem

Local service shops live on the phone. The office closes. The leads do not.

A homeowner whose AC dies at 9 p.m. will text or use the website. If nobody answers, they call the next company on the list. By morning the job is gone.

The shops that do pick up are often writing the same details twice: once in the chat, again on the calendar, again in whatever system the owner actually checks. Something gets dropped, or the customer gets asked for their phone number a second time.

---

## The solution

Operator Intake Agent runs that front desk as one short conversation.

1. **Intake.** The chat captures who they are, what is broken, and how to reach them.
2. **Qualify.** A few facts produce a plain 0–100 score. Name, phone, and the job are required. The default bar is 60.
3. **Book.** A qualified lead takes one open window on a mock calendar. A window cannot be booked twice.
4. **Follow-up.** Someone who is not ready gets a follow-up logged instead of a forced booking.

The demo stand-in is a Charlotte home-services shop (HVAC and plumbing). The same flow fits any shop that books visits.

---

## The model, on AMD

The track asks every team to bring its own model. This one is **Qwen2.5-7B-Instruct**, served with **vLLM on AMD ROCm** (MI300X, vLLM Quick Start image). The app talks to it over the OpenAI-compatible chat API, with tool calling turned on (`hermes` parser).

This repository’s container is the orchestrator. It does not ship a GPU. Judges do not need the GPU to try the product.

Stub mode is the default (`VLLM_STUB=true`). A small rule-based stand-in picks the same tools, so intake through booking runs with no credentials and no `.env`. Set `VLLM_STUB=false` and point `VLLM_ENDPOINT` at the AMD server for the live model. Setup is in [docs/VLLM_RUNBOOK.md](../VLLM_RUNBOOK.md).

**PLACEHOLDER — live AMD metrics.** Fill these in after the owner’s MI300X run. Do not invent them.

- Time to first token: PLACEHOLDER
- Tokens per second: PLACEHOLDER
- End-to-end turn time: PLACEHOLDER

---

## Evolus

The agent is wired to an Evolus workspace. The app drives Evolus. Evolus does not replace the model.

Three building blocks are in the code:

- **Knowledge library.** Price, service area, hours, and warranty questions go to the Evolus agent that sits on the library. The model is not allowed to guess a price.
- **Intake workflow.** A booked lead is handed to an Evolus workflow so the owner sees the summary in the workspace.
- **AI Tool.** When a follow-up tool name is configured, Evolus drafts the check-in message.

With no Evolus API key, those calls are skipped and written on the lead timeline. The booking still completes. That is the path in this stub demo. Turning the live workspace on is a separate owner step, with the real key only in a local `.env`.

---

## Shared memory

Every step reads and writes one lead record, plus a timeline and the conversation.

Intake stores the name. Qualify scores that same record. Booking repeats the visit details without asking for the phone number again. Follow-up sees why they did not book.

In this compose file the store is Redis. The production switch is the same calls with `MEMORY_BACKEND=acmi`.

The line to remember: each step is its own turn, and none of them re-asks a fact already on the lead.

---

## What judges can run in 60 seconds

No `.env`. No API key. No GPU.

```bash
docker compose up --build
curl -sS http://localhost:8000/health
```

`GET /health` returns 200 and `{"ok":true}`. Open http://localhost:8000 and send:

> Hi, my AC stopped blowing cold air

The agent answers and asks for a name and phone. That is a live process, the shared-memory store, and the chat widget, from one command.

`GET /healthz` adds non-secret status: stub on, Evolus not configured, memory on Redis. The same image runs the tests:

```bash
docker compose run --rm --no-deps --entrypoint pytest agent -q
```

The full booking, from that first line through a confirmed slot, is the script in [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

---

## Stub demo path

The video path is one lead, four messages, stub mode:

1. The AC is out.
2. Name, phone, ZIP, and “tomorrow.”
3. “Can you book me in?” The agent lists three open windows.
4. “The first one sounds good.” The agent confirms that window.

Then `GET /lead/{id}` shows the stored name, phone, score, and booking. `GET /lead/{id}/timeline` shows intake, qualification, booking, and an Evolus step marked skipped.

Exact lines, clicks, and the health check are in [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

---

## Roadmap

What is already true in the stub: container, health check, chat, qualify, book, shared memory, Evolus skipped cleanly when offline.

What the owner still does before this is a finished submission:

- Smoke the real `.env` against Evolus and the AMD vLLM server, and fill the metric placeholder above.
- Publish a public URL of this app in stub mode.
- Record the demo from the script, and render the cover from [COVER_BRIEF.md](COVER_BRIEF.md).
- Make the GitHub repo public when that is intended. This draft does not change visibility.

After the hackathon, the same loop can use the shop’s real calendar, the ACMI memory bridge, and the live Evolus workflow as the owner’s daily board.
