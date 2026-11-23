"""Destination for actual question/answer evidence collected during normal use."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvidenceSettings:
    """Choose the destination for readable conversation-turn evidence.

    Example data: EvidenceSettings(output_file=Path("evidence/conversations.txt")).
    """

    output_file: Path = Path("evidence/conversations.txt")
