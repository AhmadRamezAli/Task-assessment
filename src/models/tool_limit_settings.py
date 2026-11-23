"""Configuration for the main agent's per-invocation tool budget."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolLimitSettings:
    """Bound tool calls in one main-agent turn, without limiting the whole thread.

    Example data: ToolLimitSettings(calls_per_turn=10).
    """

    calls_per_turn: int = 10

    def __post_init__(self) -> None:
        """Reject negative budgets; zero intentionally disables tool execution.

        Example: calls_per_turn=10 -> valid; calls_per_turn=-1 -> ValueError.
        """
        if self.calls_per_turn < 0:
            raise ValueError("tool_limits.calls_per_turn cannot be negative.")
