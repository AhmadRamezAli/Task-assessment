"""Deep Agents assembly for the Log Analysis Assistant.

The provided ``build_agent()`` creates a working Deep Agent with the
configured model and an in-memory checkpointer, so multi-turn
conversations keep their history per ``thread_id``.

TODO(candidate): extend this module to meet the requirements in README.md:
  * add at least one subagent and make delegation demonstrable
"""

from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver

from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from src.config import Settings, load_settings
from src.llm import get_chat_model
from src.middleware.compaction import create_compaction_middleware
from src.middleware.tool_limits import create_tool_limit_middleware
from src.tools import create_log_tools

SYSTEM_PROMPT = """\
You are a log analysis assistant for an e-commerce platform's operations team.
The log dataset covers 2026-11-03 (UTC) for these log types: auth, payment,
api, database and scheduler. Levels are INFO, WARNING and ERROR.

Answer questions about the logs accurately. Never invent log records: base
every finding on records you retrieved, and cite their ids (e.g. LOG-0042).
Copy log IDs and other identifiers character-for-character from the evidence.

Use the latest user request and its explicit scope to determine the current task.
A conversation summary describes older history at a cutoff and may contain an
outdated task. Use earlier answers and summaries for continuity; verify factual
claims against available tool results for the same scope, retrieving evidence
again when it is missing or insufficient. Correct earlier mistakes explicitly.

Use search_logs to retrieve evidence and get_logs_by_ids for full record details.
Search results are paginated: never treat a page as the complete matching dataset.
Use aggregate_logs for exact counts and distributions over all matching records.
Use get_log_context for the events surrounding a log, and distinguish observed
events from causal hypotheses. Use get_log_catalog to discover dataset coverage.
Search time ranges include their start and exclude their end; normalize to UTC.

Preserve each record's actual severity: never relabel WARNING as ERROR or treat
INFO as proof of a successful operation. Distinguish log-record counts from
request or operation counts. Sample log volume alone does not establish actual
production traffic or whether traffic is high without coverage and a baseline.
Use aggregate_logs for the requested grouping and bucket size; hourly counts
require group_by="time" and bucket_minutes=60. Never fill individual time buckets
with a daily average or invent a distribution that the tool did not return.

For ambiguous rankings such as "highest", "top" or "priority", clarify whether
the user means recency, frequency or operational impact. If the conversation
already establishes the criterion, state and apply it. For operational priority,
explain the impact-based criteria and cite supporting records, marking causal
interpretations as hypotheses. Chronological order alone does not establish
priority, and a proposed fix does not guarantee that other incidents will resolve.

If a tool reports invalid input, correct it or ask for clarification. If the
dataset is unavailable, explain that analysis cannot be completed from the logs.
"""


def build_agent(settings: Settings | None = None, checkpointer=None):
    """Create the log agent with history, automatic compaction and a tool budget.

    Example: build_agent(load_settings()) -> a compiled agent whose invocations
    share a conversation when config.configurable.thread_id is unchanged.
    """
    settings = settings or load_settings()
    model = get_chat_model(settings)
    backend = StateBackend()
    compaction = create_compaction_middleware(settings.compaction, model, backend)
    tool_limits = create_tool_limit_middleware(settings.tool_limits)
    agent = create_deep_agent(
        model=model,
        tools=create_log_tools(settings.log_file),
        system_prompt=SYSTEM_PROMPT,
        backend=backend,
        # The official instance replaces the built-in middleware by its name.
        middleware=[compaction, tool_limits],
        checkpointer=checkpointer or InMemorySaver(),
    )
    return agent.with_config({"metadata": {
        "evidence_output_file": str(settings.evidence.output_file),
    }})
