# vLLM on AMD Developer Cloud — runbook

Source: lablab.ai community tutorial "Host Your First LLM on AMD GPU"
(https://github.com/lablab-ai/community-content/blob/HEAD/tutorials/en/amd-developer-cloud-host-llm-vllm.mdx).
Zero to live endpoint in ~30 minutes.

## 1. Credits (5 min, do first)
- Join the **AMD AI Developer Program**: https://www.amd.com/en/developer/ai-dev-program.html
  → $100 credits ≈ 50 hours on one MI300X. (You started AMD account signup Oct 8 — confirm it's active.)
- Then sign up at **AMD Developer Cloud**: https://www.amd.com/en/developer/resources/cloud-access/amd-developer-cloud.html
  (DigitalOcean-powered dashboard, sign in with AMD account.)
- **Billing → add a card.** Required to unlock GPU droplet creation; credits burn first, card is only a safety net.

## 2. Create the GPU droplet (5 min)
GPU Droplets → Create GPU Droplet:
- **Region:** ATL1 (Atlanta) — best MI300X availability
- **Plan:** MI300X, 1 GPU — $1.99/hr, 192 GB VRAM, 20 vCPU, 240 GB RAM
- **Image:** vLLM Quick Start (pre-built vLLM + ROCm, zero setup)
- **SSH key:** paste your public key (`~/.ssh/id_ed25519.pub`)
- Create → 2–4 min to Active → copy the **public IP**.

## 3. Launch the model (10 min)
```bash
ssh root@<droplet-ip>
docker exec -it rocm /bin/bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3-32B \
  --host 0.0.0.0 --port 8000 \
  --dtype float16 \
  > /tmp/vllm.log 2>&1 &
tail -f /tmp/vllm.log   # wait for "Application startup complete"
```
Model pick: Qwen3-32B is a good hackathon middle ground — strong enough for real
agent reasoning, fits easily in 192 GB VRAM. Qwen2.5-1.5B loads in seconds if you
want a smoke test first. Llama needs a license accept on HF; Qwen doesn't.

## 4. Verify (2 min, from your laptop)
```bash
curl -s http://<droplet-ip>:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3-32B","messages":[{"role":"user","content":"Hello"}]}'
```
Port 8000 is publicly reachable (container port mapping bypasses UFW).

## 5. Plug into the project
```bash
# ~/workspace/goals/amd-hackathon-act-iii-evolus-business-agents-entry/project/.env
VLLM_ENDPOINT=http://<droplet-ip>:8000/v1
VLLM_MODEL=Qwen/Qwen3-32B
```

## Cost guard
$1.99/hr × ~6 days of hackathon ≈ under $300 if left running 24/7 — but you
won't. Destroy or power off the droplet when not actively building/demoing.
$100 credits cover ~50 hours; the Evolus credits are separate (platform only).
