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

Runs with no keys: `VLLM_STUB=true` uses a rule-based fake model and Evolus calls are skipped when `EVOLUS_API_KEY` is empty. `GET /healthz` shows which integrations are live (never the keys).

Endpoints: `GET /` chat widget · `POST /chat {lead_id, message}` · `GET /lead/{id}` shared-memory profile · `GET /lead/{id}/timeline` every step the agent took.

## Seed the knowledge library

```bash
# with EVOLUS_API_KEY, EVOLUS_APPLICATION_ID, EVOLUS_LIBRARY_ID in .env
python -m scripts.seed_library        # uploads docs/knowledge/*.md
python -m scripts.seed_library --list # indexing status
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q   # in-process Redis, no network, no keys
```

## How the agent decides

The open model (Qwen2.5-7B-Instruct on AMD via vLLM, Hermes tool parser) picks a tool each turn; the tools own the business rules:

| Tool | Does | Evolus |
|---|---|---|
| `save_lead_details` | writes facts to shared memory | — |
| `lookup_business_info` | answers price/area/hours questions | agent chat over the knowledge library |
| `qualify_lead` | deterministic 0–100 score, returns open slots | — |
| `check_availability` / `book_appointment` | mock calendar, no double-booking | runs the intake workflow with the lead summary |
| `schedule_followup` | logs a follow-up for leads not ready to book | `email` AI Tool drafts the message |

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
