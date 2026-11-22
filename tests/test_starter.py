"""Offline checks for the provided starter project (no API calls)."""

from datetime import datetime

from src.config import load_settings
from src.tools import load_logs

REQUIRED_FIELDS = {"id", "timestamp", "log_type", "level", "service", "host", "message"}


def test_settings_load():
    settings = load_settings()
    assert settings.model.provider == "groq"
    assert settings.model.name == "openai/gpt-oss-20b"
    assert settings.model.base_url.endswith(".workers.dev/openai/v1")
    assert settings.log_file.exists()


def test_dataset_shape():
    records = load_logs()
    assert len(records) > 100
    for rec in records:
        assert REQUIRED_FIELDS <= rec.keys()
        assert rec["level"] in {"INFO", "WARNING", "ERROR"}
        datetime.fromisoformat(rec["timestamp"].replace("Z", "+00:00"))


def test_agent_builds(monkeypatch):
    monkeypatch.setenv("GROQ_PROXY_API_KEY", "offline-test-key")
    from src.agent import build_agent
    from src.llm import get_chat_model

    settings = load_settings()
    model = get_chat_model(settings)
    assert model.model_name == settings.model.name
    assert model.groq_api_base == settings.model.base_url.removesuffix("/openai/v1")
    assert build_agent(settings) is not None
