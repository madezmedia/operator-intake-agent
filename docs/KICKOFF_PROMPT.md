# Kickoff prompt — Operator Intake Agent (paste into Claude Code)

You are building the submission for the **AMD Developer Hackathon ACT III — Evolus Business Agents track** (build window Oct 12–17, submissions close Oct 18 11:00 AM ET).

## Mission
Ship a working **Operator Intake Agent**: an AI agent that runs a local service business's lead intake end to end — captures the inquiry in chat, qualifies the lead, books the job on the calendar, logs a follow-up — inside an Evolus workspace, powered by an open model served on AMD, with a shared memory layer across steps. Ruthless scope: ONE business process, ONE demo.

## Track requirements (all five are hard gates)
1. Build in the free Evolus event workspace — already claimed: "MYAIAMDROCmPV3_1_2", Space ID `465362ae-e872-4da6-9a3c-81e1c73e00aa` (this is the `X-Application-Id` header value).
2. Main agent runs on YOUR OWN open model served on AMD via your own vLLM endpoint. Model: Qwen2.5-7B-Instruct, served with `--tool-call-parser hermes` (tool calling is required for agents). Endpoint must be AMD infrastructure — start on the existing DigitalOcean MI300X vLLM droplet, cut over to AMD Developer Cloud once credits clear (2–3 business-day approval; application already in flight).
3. Use at least two Evolus building blocks. We use three: **chat widget** (intake), **workflow** (intake → qualify → book → follow-up pipeline), **knowledge library** (company FAQ/pricing docs for RAG answers).
4. Drive Evolus from OUR app through its APIs. REST API at `https://api.evolus.ai/api/v1` with `X-ApiKey` + `X-Application-Id` headers; agent chat also via the OpenAI-compatible endpoint at `https://api.evolus.ai/v1` with model `<applicationId>:<agentId>`. Evolus verifies compliance by reviewing workspace config + usage stats.
5. Containerized app, public GitHub repo, runnable README, never commit API keys.

## What already exists
- Full scaffold in `project/`: `src/agent/` (intake/qualify/book/follow-up steps), `src/memory/` (shared memory layer), `src/models/` (vLLM OpenAI-compatible client), `src/evolus/` (workspace client), `src/main.py`, `src/config.py`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `requirements.txt`.
- Docs: `docs/ARCHITECTURE.md`, `docs/DEMO_SCRIPT.md`, `docs/EVOLUS_NOTES.md` (workspace details, API key status), `docs/VLLM_RUNBOOK.md` (step-by-step MI300X droplet setup).
- Evolus workspace claimed; an "act3-intake-agent" API key with Full access exists — create a FRESH key when wiring the app and drop it into local `.env` (never commit).

## Hard rules
- Public naming is **ACMI**, never LogMem (standing rule — the rename hasn't landed in code yet).
- No API keys, tokens, or secrets in the repo. `.env` only.
- ACMI is the shared memory layer between workflow steps: the agent never re-asks what it already knows. Keep the ACMI adapter interface in `src/memory/store.py`; a local in-memory implementation is acceptable for the demo as long as the protocol interface is real.
- Demo is ONE scripted lead: first chat message → qualified → appointment booked. The `docs/DEMO_SCRIPT.md` is the source of truth for the video.

## Build order
1. `cp .env.example .env`, fill in the vLLM endpoint and a fresh Evolus API key; `docker compose up --build` runs clean with stubs.
2. In the Evolus workspace: create the agent, the chat widget, the knowledge library (seed with 2–3 sample FAQ docs), and the intake→qualify→book→follow-up workflow. Record every workflow ID and agent ID in `docs/EVOLUS_NOTES.md`.
3. Wire `src/evolus/client.py` to the real REST endpoints (workflow execute + execution status polling, agent chat, AI Tools). Wire `src/models/vllm.py` to the real vLLM endpoint and confirm tool calling works.
4. End-to-end: run the demo script against the live stack, fix what breaks.
5. Harden the README so `docker compose up` is truly runnable by a judge.

## What is OUT of scope
CRM sync, multi-channel (no email/Teams), payments, auth beyond the demo, real calendar OAuth (a mock calendar with a real API surface is acceptable for the demo). Do not gold-plate.

## Submission checklist (all due before Oct 17 EOD ET)
- [ ] Working prototype: chat → qualify → book → follow-up against the live Evolus workspace
- [ ] Containerized: `Dockerfile` + `docker-compose.yml`
- [ ] Public GitHub repo with runnable README
- [ ] Demo video (scripted lead, intake to booked appointment)
- [ ] Pitch deck
- [ ] Cover image

Start with step 1 and report back what's green and what's blocked.
