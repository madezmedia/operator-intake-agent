# Operator Intake Agent

An AI agent that runs a local service business's lead intake end to end: captures the inquiry in chat, qualifies the lead, books the job on the calendar, and follows up. The agent lives in an Evolus workspace. The model is an open model served with vLLM on AMD ROCm. Every step reads and writes the same shared memory.

Built for the **AMD Developer Hackathon ACT III — Evolus Business Agents track** (lablab.ai, Oct 12–17, 2026).

## Stub quickstart

One command. No credentials, no `.env`, no GPU:

```bash
docker compose up --build
```

Then open http://localhost:8000. Liveness is `GET /health` (200, `{"ok": true}`). `GET /healthz` adds non-secret integration status.

Stub mode is the default (`VLLM_STUB=true`, alias `USE_STUB` when `VLLM_STUB` is unset). The process uses a rule-based stand-in for the model and skips Evolus while the Evolus credential is empty. Redis in this compose file is the shared memory store.

Run the test suite in that same image (no network):

```bash
docker compose run --rm --no-deps --entrypoint pytest agent -q
```

On the host, the same suite is:

```bash
pip install -r requirements-dev.txt
pytest -q
```

## What the agent does

1. **Intake** — the chat widget captures the lead (name, service, contact).
2. **Qualify** — a few follow-up questions, then a deterministic 0–100 score.
3. **Book** — a qualified lead takes one mock-calendar slot. A slot cannot be booked twice.
4. **Follow-up** — a lead who is not ready gets a follow-up logged, and Evolus can draft the message when configured.

Every step reads and writes the same lead record, so the agent does not ask again for a fact it already stored.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness, 200 |
| GET | `/healthz` | Liveness plus stub / Evolus / memory status. Never returns credentials. |
| GET | `/` | Chat widget |
| POST | `/chat` | Body `{"lead_id", "message"}` |
| GET | `/lead/{id}` | Shared-memory profile |
| GET | `/lead/{id}/timeline` | Steps the agent took |

## Configuration

Values come from the environment or a local `.env` (gitignored). `.env.example` has placeholders only. The code defaults below are what you get when a variable is unset. `VLLM_STUB` wins over `USE_STUB` when both are set.

| Variable | Code default | Role |
|---|---|---|
| `VLLM_ENDPOINT` | `http://localhost:8000/v1` | OpenAI-compatible base URL of the vLLM server |
| `VLLM_MODEL` | `Qwen/Qwen2.5-7B-Instruct` | Model name sent to vLLM |
| `VLLM_API_KEY` | `not-needed` | Bearer token for a vLLM server started with `--api-key`. Blank in `.env.example`. |
| `VLLM_STUB` | `true` | Rule-based model, no outbound model call. Set `false` for the live AMD server. |
| `USE_STUB` | unset | Alias of `VLLM_STUB`, used only when `VLLM_STUB` is unset |
| `VLLM_TIMEOUT` | `60` | HTTP timeout, seconds |
| `EVOLUS_API_KEY` | empty | Blank stays offline. Real value belongs in `.env` only. |
| `EVOLUS_APPLICATION_ID` | empty | Space id, sent as `X-Application-Id` |
| `EVOLUS_WORKSPACE_ID` | empty | Legacy stand-in, used only when the application id is empty |
| `EVOLUS_AGENT_ID` | empty | Knowledge-library agent |
| `EVOLUS_INTAKE_WORKFLOW_ID` | empty | Workflow that receives a booked lead |
| `EVOLUS_FOLLOWUP_TOOL` | empty | AI Tool name. Empty skips the draft. The built-in tool is `email`. |
| `EVOLUS_LIBRARY_ID` | empty | Knowledge library for `scripts/seed_library.py` |
| `EVOLUS_API_BASE` | `https://api.evolus.ai/api/v1` | Evolus REST base |
| `EVOLUS_OPENAI_BASE` | `https://api.evolus.ai/v1` | Evolus OpenAI-compatible agent chat |
| `EVOLUS_TIMEOUT` | `60` | HTTP timeout, seconds |
| `EVOLUS_POLL_SECONDS` | `2` | Workflow status poll interval |
| `EVOLUS_POLL_TIMEOUT` | `90` | Stop waiting for a workflow after this many seconds |
| `MEMORY_BACKEND` | `redis` | `redis` in this compose file, `acmi` for the production bridge |
| `REDIS_URL` | `redis://redis:6379/0` | Compose service name is `redis` |
| `APP_HOST` | `0.0.0.0` | Bind address |
| `APP_PORT` | `8000` | Bind port |
| `BUSINESS_NAME` | `Your Business Name` | Name used in the system prompt |
| `BUSINESS_TIMEZONE` | `America/New_York` | Timezone for mock calendar slots |
| `QUALIFY_THRESHOLD` | `60` | Score at or above this, with required fields present, can book |
| `MAX_TOOL_ROUNDS` | `5` | Tool-call loop cap per chat turn |

## Architecture

```
chat widget (GET /)
        │
        ▼
FastAPI  ──►  agent loop (src/agent/steps.py)
                 │  tool choice
                 ▼
              vLLM on AMD ROCm     (stubbed in this default compose)
                 │
                 ▼
              tools (src/agent/tools.py)
                 │
     ┌───────────┼────────────┐
     ▼           ▼            ▼
 shared memory   mock calendar   Evolus
 Redis / ACMI    no double-book  workflow, knowledge library, AI Tool
```

The model picks a tool. The tools own the business rules: what gets stored, the qualify score, which slot can be booked, and what is handed to Evolus. With no Evolus credential the Evolus calls are skipped and recorded on the lead timeline, and the booking still completes.

Shared memory is one lead record plus a timeline and the conversation. Intake, qualify, book, and follow-up all use it. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

| Tool | Does | Evolus |
|---|---|---|
| `save_lead_details` | writes facts to shared memory | — |
| `lookup_business_info` | price, area, hours, warranty | agent chat over the knowledge library |
| `qualify_lead` | deterministic 0–100 score, returns open slots | — |
| `check_availability` / `book_appointment` | mock calendar, no double-booking | runs the intake workflow with the lead summary |
| `schedule_followup` | logs a follow-up when the lead is not ready to book | AI Tool drafts the message when `EVOLUS_FOLLOWUP_TOOL` is set |

## AMD ROCm and vLLM

The track requires the model to run on AMD hardware. This repository's container is the CPU orchestrator: it does not ship a GPU runtime. The model server is vLLM on an AMD ROCm image (MI300X, vLLM Quick Start), started with tool calling:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 --port 8000 \
  --dtype float16 \
  --enable-auto-tool-choice --tool-call-parser hermes \
  --api-key "$VLLM_API_KEY"
```

Point `VLLM_ENDPOINT` at that server and set `VLLM_STUB=false` for the live demo. Setup steps are in [docs/VLLM_RUNBOOK.md](docs/VLLM_RUNBOOK.md). The app still parses a Hermes `<tool_call>` block from the text if the server was started without the parser flags.

Live endpoint numbers (time to first token, tokens/sec, end-to-end turn time): **placeholder — fill in after the MI300X run. Do not invent these.**

## Seed the knowledge library

This step needs a real Evolus credential and library id in `.env`. It is not part of the stub quickstart.

```bash
python -m scripts.seed_library        # uploads docs/knowledge/*.md
python -m scripts.seed_library --list # indexing status
```

## Project layout

- `src/agent/` — intake, qualification, booking, follow-up
- `src/memory/` — shared memory (Redis now, ACMI bridge behind the same calls)
- `src/models/` — vLLM OpenAI-compatible client and the stub model
- `src/evolus/` — Evolus REST and agent-chat client
- `docs/` — architecture, Evolus notes, vLLM runbook, demo script

## License

MIT. See [LICENSE](LICENSE).

## Submission checklist

- [x] Containerized (`Dockerfile` + `docker-compose.yml`), stub path runs with no credentials
- [x] README quickstart matches `docker compose up --build`
- [ ] Live smoke with the owner's real `.env` (Evolus + AMD vLLM)
- [ ] Public hosted URL of this app in stub mode
- [ ] Demo video (one scripted lead, intake through a booked appointment)
- [ ] Pitch deck
- [ ] Cover image
