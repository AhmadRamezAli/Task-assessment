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
from copy import deepcopy
from pathlib import Path
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import LLMResult

from src.agent import build_agent
from src.config import PROJECT_ROOT, load_settings
from src.repositories.evidence_repository import append_turn_evidence
from src.utils.turn_report import render_token_report, summarize_token_usage


class _TurnRecorder(BaseCallbackHandler):
    """Capture model-visible messages and the usage needed for one turn's table.

    Example data: two requests contain context strings and usage counts such as
    {'role': 'agent', 'status': 'ok', 'usage': {'input_tokens': 300, ...}}.
    Run ids are used only in memory to match callbacks; no separate trace is saved.
    """

    run_inline = True

    def __init__(self):
        """Start an empty turn record; example: recorder.requests -> {}."""
        self.requests: dict[UUID, dict] = {}

    def on_chat_model_start(self, serialized, messages, *, run_id: UUID, metadata=None, **kwargs):
        """Capture and print the actual message input immediately before a request.

        Example: system + user + tool result -> readable messages in that order.
        Agent inputs are observed after middleware has prepared them, including
        compaction. This records messages, not tool schemas or the HTTP payload.
        """
        role = "summary" if (metadata or {}).get("lc_source") == "summarization" else "agent"
        context = (
            f"CONTEXT BEFORE REQUEST {len(self.requests) + 1} ({role})\n\n"
            + "\n\n".join(message.pretty_repr() for batch in messages for message in batch)
        )
        self.requests[run_id] = {
            "role": role, "status": "pending", "usage": None, "context": context,
        }
        print(f"\n=================\n{context}\n=================", flush=True)

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs):
        """Keep provider-reported usage for the table, without saving call details.

        Example: input=300, output=40 -> those counts appear in this request's row.
        """
        generation = response.generations[0][0] if response.generations and response.generations[0] else None
        message = getattr(generation, "message", None)
        self.requests[run_id].update(
            status="ok", usage=deepcopy(getattr(message, "usage_metadata", None)),
        )

    def on_llm_error(self, error, *, run_id: UUID, **kwargs):
        """Mark a failed request; example: a timeout -> error row with unknown usage."""
        self.requests[run_id]["status"] = "error"


def _text(message: AIMessage) -> str:
    """Extract printable text from an assistant message.

    Example: AIMessage(content="There are 19 errors") -> "There are 19 errors".
    """
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if isinstance(b, dict))


def _format_turn_evidence(record: dict) -> str:
    """Separate one question, request contexts, answer and token table for reading.

    Example: question='Count errors', answer='19' -> separate QUESTION and RESPONSE
    sections with model-input messages between them and a token table at the end.
    """
    sections = [
        "QUESTION\n" + record["question"],
        *(call["context"] for call in record["model_calls"]),
        "RESPONSE\n" + (record["answer"] if record["answer"] is not None
                         else "No answer completed."),
        "TOKEN USAGE\n" + render_token_report(record).strip(),
    ]
    separator = "================="
    return separator + "\n" + ("\n\n" + separator + "\n\n").join(sections) + "\n" + separator + "\n\n"


def run_turn(
    agent, thread_id: str, user_input: str, *,
    evidence_file: Path | None = None, display_answer: bool = False,
) -> str:
    """Show each model-input context, answer a turn, and save readable evidence.

    Example: run_turn(agent, "session-1", "Count errors") -> answer text, with a
    token table printed and one readable evidence block saved. CLI sets display_answer=True
    to print the answer before the table; callers can still use print(run_turn(...)).
    """
    metadata = (getattr(agent, "config", None) or {}).get("metadata", {})
    destination = Path(
        evidence_file if evidence_file is not None
        else metadata.get("evidence_output_file", PROJECT_ROOT / "evidence/conversations.txt")
    )
    if not destination.is_absolute():
        destination = PROJECT_ROOT / destination
    # Never append the new text format into an existing machine-readable JSONL file.
    if destination.suffix.lower() == ".jsonl":
        destination = destination.with_suffix(".txt")
    recorder = _TurnRecorder()
    record = {"question": user_input, "answer": None}
    config = {
        "configurable": {"thread_id": thread_id},
        "metadata": {"thread_id": thread_id},
        "recursion_limit": 60,
        "callbacks": [recorder],
    }
    try:
        result = agent.invoke({"messages": [{"role": "user", "content": user_input}]}, config=config)
        ai_messages = [message for message in result["messages"] if isinstance(message, AIMessage)]
        answer = _text(ai_messages[-1]) if ai_messages else ""
        record["answer"] = answer
        return answer
    except KeyboardInterrupt:
        record["answer"] = "Request interrupted; no answer completed."
        raise
    except Exception as error:
        record["answer"] = f"Request failed: {type(error).__name__}; no answer completed."
        raise
    finally:
        record["model_calls"] = list(recorder.requests.values())
        record["token_totals"] = summarize_token_usage(record["model_calls"])
        append_turn_evidence(destination, _format_turn_evidence(record))
        if display_answer:
            print(f"assistant> {record['answer']}")
        print(render_token_report(record))


def main(argv: list[str] | None = None) -> int:
    """Run the chat loop."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--script", type=Path, help="file with one user message per line")
    parser.add_argument("--thread-id", default=None, help="conversation thread id (default: random)")
    args = parser.parse_args(argv)

    settings = load_settings()
    agent = build_agent(settings)
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
            run_turn(agent, thread_id, prompt, evidence_file=settings.evidence.output_file, display_answer=True)
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
            run_turn(agent, thread_id, user_input, evidence_file=settings.evidence.output_file, display_answer=True)


if __name__ == "__main__":
    sys.exit(main())
