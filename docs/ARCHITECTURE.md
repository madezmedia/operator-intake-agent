# Architecture — Operator Intake Agent

## The one business process

A local service business (HVAC, plumbing, landscaping — the demo uses a generic
"Charlotte home services" stand-in) loses after-hours leads. This agent owns the
full intake flow:

```
visitor message
      │
      ▼
┌─────────────┐
│   INTAKE    │  chat widget → capture name, service, contact
└──────┬──────┘
       │  shared memory: lead profile created
       ▼
┌─────────────┐
│   QUALIFY   │  2–3 questions → score 0–100 → qualified?
└──┬──────┬───┘
   │ yes  │ no
   ▼      ▼
┌──────┐ ┌──────────┐
│ BOOK │ │ FOLLOW-UP│  booking → calendar slot + confirmation
└──┬───┘ │          │  follow-up → timed check-in messages
   │     └──────────┘
   ▼
Evolus workspace ← lead summary + booking pushed here
```

## Why the shared memory layer is the point

Each step is a separate agent call, but all of them read/write the **same lead
context** (ACMI profile/signals/timeline semantics; Redis in dev). The demo's
money moment: the booking step references details from intake without re-asking.

This is the same pattern Michael runs in production across his multi-agent
fleet — the hackathon version is one business process, ruthlessly scoped.

## Model

Open model served via vLLM on AMD (OpenAI-compatible `/v1/chat/completions`).
Model choice is a config value (`VLLM_MODEL`), not code — swap freely.

## Evolus

The agent runs inside an Evolus workspace (50k credits from the hackathon).
Lead summaries and bookings are pushed to the workspace so the business owner
sees every lead in one place. See `docs/EVOLUS_NOTES.md` for the API surface
(filled in after kickoff).
