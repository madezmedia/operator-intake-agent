"""Shared config loaded from environment."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    vllm_endpoint: str = "http://localhost:8000/v1"
    vllm_model: str = "open-model"
    vllm_api_key: str = "not-needed"
    vllm_stub: bool = False  # true = canned replies, no model call (smoke tests only)

    evolus_api_key: str = ""
    evolus_workspace_id: str = ""
    evolus_intake_workflow_id: str = ""

    memory_backend: str = "redis"  # redis | acmi
    redis_url: str = "redis://redis:6379/0"

    app_host: str = "0.0.0.0"
    app_port: int = 8000

    business_name: str = "Your Business Name"
    business_timezone: str = "America/New_York"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
