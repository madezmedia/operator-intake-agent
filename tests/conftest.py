import fakeredis
import pytest

from src.config import settings
from src.memory import store


@pytest.fixture(autouse=True)
def fake_env(monkeypatch):
    """Isolated settings + in-process Redis for every test. No network, no keys."""
    monkeypatch.setattr(store, "_client", fakeredis.FakeAsyncRedis(decode_responses=True))
    monkeypatch.setattr(settings, "vllm_stub", True)
    monkeypatch.setattr(settings, "evolus_api_key", "")
    monkeypatch.setattr(settings, "evolus_application_id", "")
    monkeypatch.setattr(settings, "evolus_workspace_id", "")
    monkeypatch.setattr(settings, "evolus_poll_seconds", 0)
    yield
