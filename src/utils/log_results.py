"""Format compact result pages and the filters reported with them."""

from copy import deepcopy
from datetime import datetime

from src.models.log_inputs import LogFilters
from src.utils.time_utils import format_utc

COMPACT_FIELDS = (
    "id", "timestamp", "log_type", "level", "service", "message", "request_id"
)


def applied_filters(query: LogFilters) -> dict:
    """Return only supplied filters, with times serialized in UTC.

    Example: LogFilters(level="ERROR") -> {"level": "ERROR"}.
    """
    values = query.model_dump(include=set(LogFilters.model_fields), exclude_none=True)
    return {
        key: format_utc(value) if isinstance(value, datetime) else value
        for key, value in values.items()
    }


def paginate_logs(records: list[dict], limit: int, offset: int) -> dict:
    """Copy one compact page and retain the full match count.

    Example (abridged): records=[{"id": "A"}, {"id": "B"}], limit=1, offset=0
    -> {"records": [{"id": "A"}], "total_matches": 2, "next_offset": 1, ...}.
    Copies prevent callers from mutating cached source records.
    """
    selected = records[offset : offset + limit]
    next_offset = offset + len(selected)
    has_more = next_offset < len(records)
    return {
        "status": "ok",
        "total_matches": len(records),
        "returned_count": len(selected),
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
        "next_offset": next_offset if has_more else None,
        "records": [
            {key: deepcopy(record[key]) for key in COMPACT_FIELDS if key in record}
            for record in selected
        ],
    }
