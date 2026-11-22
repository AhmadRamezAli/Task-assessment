"""Command-line chat for the Log Analysis Assistant.

Interactive:        python -m src.main
Scripted session:   python -m src.main --script prompts.txt

A scripted session sends each non-empty line of the file as one user turn,
all in the same conversation thread. Lines starting with '#' are ignored.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

from langchain_core.messages import AIMessage

from src.agent import build_agent


def _text(message: AIMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if isinstance(b, dict))


def run_turn(agent, thread_id: str, user_input: str) -> str:
    """Send one user message and return the assistant's final reply."""
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 60}
    before = len(agent.get_state(config).values.get("messages", []))
    result = agent.invoke({"messages": [{"role": "user", "content": user_input}]}, config=config)
    new_messages = result["messages"][before:]
    ai_calls = [m for m in new_messages if isinstance(m, AIMessage)]
    input_tokens = [(m.usage_metadata or {}).get("input_tokens") for m in ai_calls]
    print(f"   [turn stats] model calls: {len(ai_calls)}, input tokens per call: {input_tokens}")
    return _text(ai_calls[-1]) if ai_calls else ""


def main(argv: list[str] | None = None) -> int:
    """Run the chat loop."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--script", type=Path, help="file with one user message per line")
    parser.add_argument("--thread-id", default=None, help="conversation thread id (default: random)")
    args = parser.parse_args(argv)

    agent = build_agent()
    thread_id = args.thread_id or f"session-{uuid.uuid4().hex[:8]}"
    print(f"Log Analysis Assistant - thread {thread_id}")

    if args.script:
        prompts = [
            line.strip()
            for line in args.script.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        for i, prompt in enumerate(prompts, start=1):
            print(f"\n[{i}/{len(prompts)}] you> {prompt}")
            print(f"assistant> {run_turn(agent, thread_id, prompt)}")
        return 0

    print("Type 'exit' to quit.")
    while True:
        try:
            user_input = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if user_input.lower() in {"exit", "quit"}:
            return 0
        if user_input:
            print(f"assistant> {run_turn(agent, thread_id, user_input)}")


if __name__ == "__main__":
    sys.exit(main())
