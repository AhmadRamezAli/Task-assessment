"""LangChain adapters only; data access and log operations live in separate layers.

``load_logs`` remains available here for the supplied setup checks.
"""

from pathlib import Path
from typing import Any, Callable

from langchain_core.tools import BaseTool, StructuredTool

from src.config import load_settings
from src.models.log_inputs import (
    AggregateLogsInput,
    LogCatalogInput,
    LogContextInput,
    LookupLogsInput,
    SearchLogsInput,
    ToolInput,
)
from src.repositories.log_repository import JsonLogRepository, load_logs
from src.services.log_service import LogService
from src.utils.tool_errors import format_validation_error


def _make_tool(
    name: str,
    description: str,
    schema: type[ToolInput],
    operation: Callable,
) -> BaseTool:
    """Adapt a service operation to LangChain with one schema validation pass.

    Example: name="search_logs", schema=SearchLogsInput, operation=service.search
    -> a StructuredTool whose invoke({"level": "ERROR"}) returns a result dict.
    """

    def invoke(**kwargs: Any) -> dict:
        """Pass already validated arguments to the operation and format data errors.

        Example (abridged): kwargs={"level": "ERROR"} ->
        {"status": "ok", "total_matches": 19, ...}; unreadable data ->
        {"status": "error", "error": {"code": "DATA_UNAVAILABLE", ...}}.
        """
        # StructuredTool validated and normalized these values before this call.
        # Constructing the model only supplies defaults; it does not validate again.
        query = schema.model_construct(**kwargs)
        try:
            return operation(query)
        except (OSError, UnicodeError, ValueError, KeyError, TypeError, OverflowError):
            return {
                "status": "error",
                "error": {
                    "code": "DATA_UNAVAILABLE",
                    "message": "The configured log dataset could not be read or is invalid.",
                },
            }

    return StructuredTool.from_function(
        func=invoke,
        name=name,
        description=description,
        args_schema=schema,
        handle_validation_error=format_validation_error,
    )


def create_log_tools(path: Path | str | None = None) -> list[BaseTool]:
    """Wire one configured repository and service to the five agent-facing tools.

    Example: create_log_tools("data/sample_logs.json") ->
    [search_logs, aggregate_logs, get_logs_by_ids, get_log_context, get_log_catalog].
    Each item is a BaseTool. The filesystem path is not exposed in its schema.
    """
    source = Path(path) if path is not None else load_settings().log_file
    service = LogService(JsonLogRepository(source))
    return [
        _make_tool(
            "search_logs",
            "Retrieve compact records using AND filters. Time ranges include start "
            "and exclude end. Results are chronological and paginated; total_matches "
            "counts all matches. Use next_offset for another page.",
            SearchLogsInput,
            service.search,
        ),
        _make_tool(
            "aggregate_logs",
            "Count ALL matching records using the same filters as search_logs. "
            "Group by severity, type, service, host or fixed UTC time buckets. "
            "sample_ids are examples, not the complete set counted.",
            AggregateLogsInput,
            service.aggregate,
        ),
        _make_tool(
            "get_logs_by_ids",
            "Retrieve full records for up to 50 ids in requested order. "
            "Use for details and evidence; unknown ids appear in missing_ids.",
            LookupLogsInput,
            service.lookup,
        ),
        _make_tool(
            "get_log_context",
            "Retrieve events across services around a log id, including both "
            "time endpoints. The anchor may be on another page. "
            "Temporal proximity alone does not prove causation.",
            LogContextInput,
            service.context,
        ),
        _make_tool(
            "get_log_catalog",
            "Describe the dataset's record count, UTC coverage, types, levels, "
            "services and optional hosts. Use to discover available values and dates.",
            LogCatalogInput,
            service.catalog,
        ),
    ]


search_logs, aggregate_logs, get_logs_by_ids, get_log_context, get_log_catalog = create_log_tools()
