"""Groq proxy integration (provided - do not change provider or model).

Use ``get_chat_model()`` everywhere your implementation needs a chat model.
"""

from __future__ import annotations

import os

from dotenv import dotenv_values
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_groq import ChatGroq

from src.config import PROJECT_ROOT, Settings, load_settings


def get_chat_model(settings: Settings | None = None) -> ChatGroq:
    """Return the configured Groq model through the assessment proxy."""
    settings = settings or load_settings()
    m = settings.model
    if m.provider != "groq":
        raise ValueError(f"Unsupported provider {m.provider!r}; this assessment uses 'groq'.")
    key = os.getenv("GROQ_PROXY_API_KEY")
    if not key:
        credential_file = PROJECT_ROOT / "config" / "assessment.env"
        key = dotenv_values(credential_file, interpolate=False).get("GROQ_PROXY_API_KEY")
    if not key:
        raise RuntimeError("No proxy key found. Use the distributed ZIP or set GROQ_PROXY_API_KEY.")

    rate_limiter = InMemoryRateLimiter(
        requests_per_second=m.requests_per_minute / 60,
        check_every_n_seconds=0.1,
        max_bucket_size=1,
    )
    return ChatGroq(
        model=m.name,
        api_key=key,
        # The Groq SDK appends /openai/v1 to its base URL.
        base_url=m.base_url.rstrip("/").removesuffix("/openai/v1"),
        reasoning_effort=m.reasoning_effort,
        temperature=m.temperature,
        max_tokens=m.max_tokens,
        max_retries=m.max_retries,
        timeout=m.timeout_seconds,
        rate_limiter=rate_limiter,
    )
