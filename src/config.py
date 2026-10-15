"""Shared config loaded from environment. No secrets have defaults here."""
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Model: open model on AMD via vLLM (OpenAI-compatible) ---
    vllm_endpoint: str = "http://localhost:8000/v1"
    vllm_model: str = "Qwen/Qwen2.5-7B-Instruct"
    vllm_api_key: str = "not-needed"
    # Stub is the default so `docker compose up` and a public URL need no credentials.
    # VLLM_STUB wins when both are set. USE_STUB is the alias used when VLLM_STUB is absent.
    vllm_stub: bool = Field(
        default=True,
        validation_alias=AliasChoices("VLLM_STUB", "USE_STUB"),
    )
    vllm_timeout: float = 60.0

    # --- Evolus workspace (REST + OpenAI-compatible agent chat) ---
    evolus_api_key: str = ""
    evolus_application_id: str = ""  # Space ID, sent as X-Application-Id
    evolus_workspace_id: str = ""    # legacy name; used if application_id is empty
    evolus_agent_id: str = ""        # knowledge-library agent (FAQ / pricing answers)
    evolus_intake_workflow_id: str = ""
    evolus_followup_tool: str = ""  # AI Tool name, e.g. "email" (drafts follow-ups; uses credits)
    evolus_library_id: str = ""      # knowledge library, for scripts/seed_library.py
    evolus_api_base: str = "https://api.evolus.ai/api/v1"
    evolus_openai_base: str = "https://api.evolus.ai/v1"
    evolus_timeout: float = 60.0
    evolus_poll_seconds: float = 2.0
    evolus_poll_timeout: float = 90.0

    # --- Shared memory ---
    memory_backend: str = "redis"  # redis | acmi
    redis_url: str = "redis://redis:6379/0"

    # --- App ---
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    business_name: str = "Your Business Name"
    business_timezone: str = "America/New_York"
    qualify_threshold: int = 60
    max_tool_rounds: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
