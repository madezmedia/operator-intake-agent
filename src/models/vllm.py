"""OpenAI-compatible client for the vLLM endpoint on AMD."""
import httpx
from .config import settings


async def chat(messages: list[dict], temperature: float = 0.3) -> str:
    """Send a chat completion request to the vLLM server. Returns the reply text."""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{settings.vllm_endpoint}/chat/completions",
            headers={"Authorization": f"Bearer {settings.vllm_api_key}"},
            json={
                "model": settings.vllm_model,
                "messages": messages,
                "temperature": temperature,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
