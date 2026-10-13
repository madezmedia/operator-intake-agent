# Operator Intake Agent

An AI agent that runs a local service business's lead intake end to end: captures the inquiry (chat), qualifies the lead, books the job on the calendar, and follows up — all inside an Evolus workspace, powered by an open model served on AMD, with a shared memory layer across every step.

Built for the **AMD Developer Hackathon ACT III — Evolus Business Agents track** (Oct 12–17, 2026).

## How it works

One business process, four steps, one shared memory:

1. **Intake** — a chat-first web widget captures the lead (name, service needed, contact).
2. **Qualify** — the agent asks 2–3 smart follow-up questions and scores the lead.
3. **Book** — qualified leads get a calendar slot, confirmed back in chat.
4. **Follow-up** — no-shows and cold leads get automatic follow-up messages.

Every step reads and writes to the same shared memory (ACMI protocol), so context survives handoffs — the agent never re-asks what it already knows.

## Quickstart

```bash
cp .env.example .env   # fill in VLLM_ENDPOINT, EVOLUS_API_KEY, etc.
docker compose up --build
# open http://localhost:8000
```

## Architecture

```
chat widget (web) ──▶ agent orchestrator ──▶ vLLM (open model on AMD)
                              │
                    shared memory (ACMI)
                              │
                    tools: calendar, follow-up, Evolus workspace
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

## Project layout

- `src/agent/` — intake, qualification, booking, follow-up steps
- `src/memory/` — shared memory layer (ACMI client)
- `src/models/` — vLLM OpenAI-compatible client
- `src/evolus/` — Evolus workspace integration
- `docs/` — architecture, Evolus notes, demo script

## Submission checklist

- [ ] Working prototype (chat → qualify → book → follow-up)
- [ ] Containerized (`Dockerfile` + `docker-compose.yml`)
- [ ] Public GitHub repo with this README runnable
- [ ] Demo video (one scripted lead, intake to booked appointment)
- [ ] Pitch deck
- [ ] Cover image
