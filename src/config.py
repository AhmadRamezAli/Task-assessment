"""Configuration loading for the Log Analysis Assistant.

Settings come from ``config/settings.toml``; secrets come from ``.env``.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.models.compaction_settings import CompactionSettings
from src.models.evidence_settings import EvidenceSettings
from src.models.tool_limit_settings import ToolLimitSettings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "settings.toml"


@dataclass(frozen=True)
class ModelSettings:
    """Selected LLM settings. Do not change provider or model name."""

    provider: str
    name: str
    base_url: str
    reasoning_effort: str | None
    temperature: float
    max_tokens: int
    max_retries: int
    timeout_seconds: float
    requests_per_minute: int
    limits: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Settings:
    """All project settings."""

    model: ModelSettings
    log_file: Path
    raw: dict[str, Any]
    """The full parsed TOML document, for any sections you add yourself."""
    compaction: CompactionSettings = field(default_factory=CompactionSettings)
    tool_limits: ToolLimitSettings = field(default_factory=ToolLimitSettings)
    evidence: EvidenceSettings = field(default_factory=EvidenceSettings)


def load_settings(config_path: Path | str | None = None) -> Settings:
    """Load secrets and TOML model, data, compaction, limits and evidence settings.

    Example: load_settings() -> Settings with compaction.input_token_threshold=6000
    and compaction.keep_recent_tokens=1200 from the distributed configuration.
    """
    load_dotenv(PROJECT_ROOT / ".env")
    path = Path(config_path or os.getenv("LOG_ASSISTANT_CONFIG", DEFAULT_CONFIG_PATH))
    with path.open("rb") as fh:
        raw = tomllib.load(fh)

    m = raw["model"]
    model = ModelSettings(
        provider=m["provider"],
        name=m["name"],
        base_url=m["base_url"],
        reasoning_effort=m.get("reasoning_effort"),
        temperature=float(m.get("temperature", 0.0)),
        max_tokens=int(m.get("max_tokens", 1024)),
        max_retries=int(m.get("max_retries", 6)),
        timeout_seconds=float(m.get("timeout_seconds", 90)),
        requests_per_minute=int(m.get("requests_per_minute", 20)),
        limits=dict(m.get("limits", {})),
    )
    log_file = PROJECT_ROOT / raw.get("data", {}).get("log_file", "data/sample_logs.json")
    c = raw.get("compaction", {})
    compaction = CompactionSettings(
        input_token_threshold=int(c.get("input_token_threshold", 6000)),
        keep_recent_tokens=int(c.get("keep_recent_tokens", 1200)),
    )
    limits = raw.get("tool_limits", {})
    tool_limits = ToolLimitSettings(calls_per_turn=int(limits.get("calls_per_turn", 10)))
    e = raw.get("evidence", {})
    evidence = EvidenceSettings(
        output_file=PROJECT_ROOT / e.get("output_file", "evidence/conversations.txt"),
    )
    return Settings(
        model=model, log_file=log_file, raw=raw, compaction=compaction,
        tool_limits=tool_limits, evidence=evidence,
    )
