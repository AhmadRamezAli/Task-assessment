"""Verify your environment: API key, model access and tool calling.

Run:  python -m src.check_setup

Uses 2 small requests (well under 1,000 tokens in total).
"""

from __future__ import annotations

import sys

from langchain_core.tools import tool

from src.config import load_settings
from src.llm import get_chat_model
from src.tools import load_logs


@tool
def get_server_time(timezone: str) -> str:
    """Return the current server time for the given IANA timezone name."""
    return f"2026-11-03T12:00:00 ({timezone})"


def main() -> int:
    """Run the setup checks."""
    settings = load_settings()
    print(f"Provider: {settings.model.provider}   Model: {settings.model.name}")
    print(f"Proxy: {settings.model.base_url}")

    records = load_logs()
    print(f"[PASS] dataset loaded: {len(records)} records from {settings.log_file.name}")

    try:
        model = get_chat_model(settings)
        reply = model.invoke("Reply with exactly the word: READY")
        if reply.text.strip().casefold() != "ready":
            print("[FAIL] model invocation: expected READY")
            return 1
        print("[PASS] model invocation: READY")

        ai = model.bind_tools([get_server_time]).invoke(
            "What time is it on the server in Europe/Berlin? Use the tool."
        )
        call = next((item for item in ai.tool_calls if item["name"] == "get_server_time"), None)
        if call is None:
            print("[FAIL] tool calling: the model did not call get_server_time")
            return 1
        print(f"[PASS] tool calling: {call['name']}({call['args']})")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {type(exc).__name__}: {exc}")
        return 1

    print("\nSetup OK - you are ready to start.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
