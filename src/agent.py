"""Deep Agents assembly for the Log Analysis Assistant.

The provided ``build_agent()`` creates a working Deep Agent with the
configured model and an in-memory checkpointer, so multi-turn
conversations keep their history per ``thread_id``.

TODO(candidate): extend this module to meet the requirements in README.md:
  * add at least one subagent and make delegation demonstrable
  * enable automatic session compaction at a configurable token threshold
"""

from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver

from deepagents import create_deep_agent
from src.config import Settings, load_settings
from src.llm import get_chat_model
from src.tools import create_log_tools

SYSTEM_PROMPT = """\
You are a log analysis assistant for an e-commerce platform's operations team.
The log dataset covers 2026-11-03 (UTC) for these log types: auth, payment,
api, database and scheduler. Levels are INFO, WARNING and ERROR.

Answer questions about the logs accurately. Never invent log records: base
every finding on records you retrieved, and cite their ids (e.g. LOG-0042).

Use search_logs to retrieve evidence and get_logs_by_ids for full record details.
Search results are paginated: never treat a page as the complete matching dataset.
Use aggregate_logs for exact counts and distributions over all matching records.
Use get_log_context for the events surrounding a log, and distinguish observed
events from causal hypotheses. Use get_log_catalog to discover dataset coverage.
Search time ranges include their start and exclude their end; normalize to UTC.
If a tool reports invalid input, correct it or ask for clarification. If the
dataset is unavailable, explain that analysis cannot be completed from the logs.
"""


def build_agent(settings: Settings | None = None, checkpointer=None):
    """Create the Deep Agent."""
    settings = settings or load_settings()
    model = get_chat_model(settings)
    return create_deep_agent(
        model=model,
        tools=create_log_tools(settings.log_file),
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer or InMemorySaver(),
    )
