"""Configuration for the official conversation-compaction middleware."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CompactionSettings:
    """Separate the input trigger from the recent-history retention budget.

    Example data: CompactionSettings(input_token_threshold=6000,
                                     keep_recent_tokens=1200).
    Both budgets are estimates; system instructions and tools also use input.
    """

    input_token_threshold: int = 6000
    keep_recent_tokens: int = 1200

    def __post_init__(self) -> None:
        """Reject budgets that leave no room to summarize older history.

        Example: threshold=6000, keep=1200 -> valid; keep=6000 -> ValueError.
        """
        if not 0 < self.keep_recent_tokens < self.input_token_threshold:
            raise ValueError(
                "compaction.keep_recent_tokens must be positive and smaller than "
                "compaction.input_token_threshold."
            )
