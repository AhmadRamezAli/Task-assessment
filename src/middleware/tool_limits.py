"""Configure the framework's tool-call limiter."""

from langchain.agents.middleware import ToolCallLimitMiddleware

from src.models.tool_limit_settings import ToolLimitSettings


def create_tool_limit_middleware(settings: ToolLimitSettings) -> ToolCallLimitMiddleware:
    """Stop a main-agent invocation when its next tool batch would exceed the budget.

    Example: settings.calls_per_turn=10 -> an official middleware with run_limit=10.
    The native 'end' behavior supplies tool responses and a final limit message,
    including when a parallel batch contains both allowed and excessive calls.
    """
    return ToolCallLimitMiddleware(
        run_limit=settings.calls_per_turn,
        thread_limit=None,
        exit_behavior="end",
    )
