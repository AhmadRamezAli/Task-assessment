"""JSON access and caching, independent of LangChain and query behavior."""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from src.config import load_settings
from src.utils.time_utils import parse_timestamp


@lru_cache(maxsize=4)
def load_logs(path: Path | str | None = None) -> tuple[dict, ...]:
    """Read a static JSON array and cache records in chronological/id order.

    Example (abridged): load_logs("data/sample_logs.json") ->
    ({"id": "LOG-0001", "timestamp": "2026-11-03T00:00:20Z", ...}, ...).
    File/JSON errors propagate to the tool boundary for a structured response.
    The supplied dataset is trusted; there is no per-field validation pass.
    """
    source = Path(path) if path is not None else load_settings().log_file
    with source.open(encoding="utf-8") as stream:
        records = json.load(stream)
    if not isinstance(records, list):
        raise ValueError("The log dataset must be a JSON array.")
    return tuple(sorted(
        records, key=lambda record: (parse_timestamp(record["timestamp"]), record["id"])
    ))


@dataclass(frozen=True)
class JsonLogRepository:
    """Bind data access to one configured file; loading stays lazy and cached.

    Example data: JsonLogRepository(path=Path("data/sample_logs.json")).
    """

    path: Path

    def load(self) -> tuple[dict, ...]:
        """Return the cached records belonging to this repository.

        Example (abridged): repository.load() -> ({"id": "LOG-0001", ...}, ...).
        """
        return load_logs(self.path.resolve())
