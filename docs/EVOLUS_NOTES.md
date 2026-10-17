# Evolus notes

## Platform
- Evolus = AI agent platform for business processes (built by Codedesign, Italy). Agents, sub-agents, workflows, document extractors, knowledge libraries (RAG), AI Tools, MCP connectors, chat widget, webhooks.
- Console: https://app.evolus.ai (sign-in required)
- Track spec: https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii
- Partnership announcement: https://www.linkedin.com/posts/andreabelloni_activity-7512888700691931136-d9wK

## Event workspace (DONE 2026-10-12 ~1:20 PM ET)
- Workspace "MYAIAMDROCmPV3_1_2" claimed via the event link https://app.evolus.ai/join/AMDACT3 (published on evolus.ai/en/hackathon at kickoff — no code, link only).
- Free: 50,000 credits, 60 req/min, no card, valid to 2026-11-15 23:59 Italian time.
- Space ID (X-Application-Id header): 465362ae-e872-4da6-9a3c-81e1c73e00aa.
- API keys page: https://app.evolus.ai/company/api-keys — key "act3-intake-agent" CREATED 2026-10-12 ~4:55 PM ET with Full access (workflows, agents, AI tools, knowledge libraries, MCP server). Key fingerprint: evo_W3pt… (full value shown once at creation, not retained — rotate/create a fresh key when wiring the app and drop it into local .env, never commit).

## Track requirements (5 hard requirements)
1. Build in the free Evolus event workspace (event code at kickoff).
2. **Bring your own model:** main agent must use an open model served on AMD infra via your own vLLM endpoint on AMD Developer Cloud. (LinkedIn: "every team brings its own model" — vLLM on AMD Developer Cloud, Fireworks AI, or any OpenAI-compatible provider.)
3. **Use ≥2 Evolus building blocks** (workflows, document extractors, AI Tools, knowledge libraries, MCP connectors, sub-agents, chat widget).
4. **Drive Evolus from your app via APIs** — Evolus team verifies compliance by reviewing workspace config + usage stats.
5. Containerized app, public GitHub repo, runnable README, no committed keys.

## Integration surfaces
- REST API: workflows (`POST /api/v1/workflows/{id}/execute`), extractors, AI Tools, libraries; agent chat via `ask` / streaming `ask-stream`.
- OpenAI-compatible `/v1/chat/completions` for agent chat.
- MCP server for coding agents building on Evolus.

## Plan for Operator Intake Agent (≥2 blocks)
- Block 1: **chat widget** (lead intake on the demo site)
- Block 2: **workflow** (intake → qualify → book → follow-up pipeline, triggered by API)
- Our app calls Evolus APIs; vLLM endpoint is the model's brain; shared memory (ACMI) keeps context across steps.

## App wiring (`src/evolus/client.py`), per https://evolus.ai/en/developers
| What | Call | Used by |
|---|---|---|
| REST auth | `X-ApiKey` + `X-Application-Id` | workflows, AI Tools, libraries |
| Agent chat | `POST https://api.evolus.ai/v1/chat/completions`, `Authorization: Bearer <key>`, model `<applicationId>:<agentId>`, `X-Conversation-Id` kept per lead | `lookup_business_info` (knowledge library answers) |
| Workflow run | `POST /api/v1/workflows/{id}/execute`, multipart `input` (text) + `parameters` (flat JSON) → 202 `executionId` | `book_appointment` hands the booked lead to the intake workflow |
| Workflow status | `GET /api/v1/workflows/{id}/executions/{executionId}`: Pending, Running, Completed, Failed | `execute_workflow(wait=True)` |
| AI Tool | `POST /api/v1/ai-tools/{tool}/run` `{text, secondaryText, options}` (tool `email`) | `schedule_followup` drafts the follow-up text |
| Library upload | `POST /api/v1/memories/{libraryId}/documents?language=en`, multipart `file` | `python -m scripts.seed_library` uploads `docs/knowledge/*.md` |

Errors: 402 = credits exhausted, 409 = workflow switched off. Without `EVOLUS_API_KEY` the app runs offline: calls are skipped, logged on the lead timeline, and the chat flow still completes. An Evolus outage never blocks a booking.

## IDs to record here (after step 2)
- Agent ID (knowledge library agent):
- Chat widget ID:
- Knowledge library ID (EVOLUS_LIBRARY_ID):
- Intake workflow ID:
- Follow-up AI Tool: built-in `email` tool (no ID needed)

## Open questions
- API key issuance flow (check in-console after kickoff).
- Whether 50k credits cover inference or platform only (model is BYO on AMD anyway).
- Public quickstart: https://evolus.ai/en/developers. Full interactive reference is inside the console.
