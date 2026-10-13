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

## Open questions
- API key issuance flow (check in-console after kickoff).
- Whether 50k credits cover inference or platform only (model is BYO on AMD anyway).
- No public docs site found — API details from in-console docs / kickoff materials.
