"""Log operations over a repository, without LangChain registration code."""

from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from src.models.log_inputs import (
    AggregateLogsInput,
    LogCatalogInput,
    LogContextInput,
    LogFilters,
    LookupLogsInput,
    SearchLogsInput,
)
from src.repositories.log_repository import JsonLogRepository
from src.utils.log_results import applied_filters, paginate_logs
from src.utils.time_utils import format_utc, parse_timestamp


class LogService:
    """Coordinate filtering, statistics, lookup, context and catalog operations.

    Example data: LogService(JsonLogRepository(Path("data/sample_logs.json"))).
    Its state is only the repository; it does not store conversation history.
    """

    def __init__(self, repository: JsonLogRepository):
        """Keep the injected data source for every operation.

        Example: repository=JsonLogRepository(Path("data/sample_logs.json"))
        -> a LogService bound to that source, without reading it yet.
        """
        self.repository = repository

    def filtered(self, query: LogFilters) -> list[dict]:
        """Apply all supplied filters using AND and a half-open time range.

        Example (abridged): LogFilters(level="ERROR") ->
        [{"id": "LOG-0011", "level": "ERROR", ...}, ...].
        """
        text = query.message_contains.casefold() if query.message_contains else None
        exact_filters = {
            "log_type": query.log_type,
            "level": query.level,
            "service": query.service,
            "request_id": query.request_id,
        }
        matches = []
        for record in self.repository.load():
            timestamp = parse_timestamp(record["timestamp"])
            if query.start_time is not None and timestamp < query.start_time:
                continue
            if query.end_time is not None and timestamp >= query.end_time:
                continue
            if any(
                value is not None and record.get(key) != value
                for key, value in exact_filters.items()
            ):
                continue
            if text is not None and text not in record["message"].casefold():
                continue
            matches.append(record)
        return matches

    def search(self, query: SearchLogsInput) -> dict:
        """Return a compact page while reporting the complete matching count.

        Example (abridged): SearchLogsInput(level="ERROR", limit=1) ->
        {"total_matches": 19, "returned_count": 1, "next_offset": 1, ...}.
        """
        return {
            **paginate_logs(self.filtered(query), query.limit, query.offset),
            "filters": applied_filters(query),
        }

    def aggregate(self, query: AggregateLogsInput) -> dict:
        """Count every match and attach up to three example ids per group.

        Example (abridged): AggregateLogsInput(group_by="level") ->
        {"total_matches": 121, "groups": [{"value": "INFO", "count": 79, ...}, ...]}.
        """
        records = self.filtered(query)
        counts: Counter[str] = Counter()
        examples: dict[str, list[str]] = {}
        for record in records:
            if query.group_by == "time":
                seconds = query.bucket_minutes * 60
                bucket = datetime.fromtimestamp(
                    parse_timestamp(record["timestamp"]).timestamp() // seconds * seconds,
                    timezone.utc,
                )
                value = format_utc(bucket)
            else:
                value = record[query.group_by]
            counts[value] += 1
            ids = examples.setdefault(value, [])
            if len(ids) < 3:
                ids.append(record["id"])
        values = (
            sorted(counts) if query.group_by == "time"
            else sorted(counts, key=lambda value: (-counts[value], value))
        )
        return {
            "status": "ok",
            "filters": applied_filters(query),
            "total_matches": len(records),
            "group_by": query.group_by,
            "bucket_minutes": query.bucket_minutes if query.group_by == "time" else None,
            "groups": [
                {"value": value, "count": counts[value], "sample_ids": examples[value]}
                for value in values
            ],
        }

    def lookup(self, query: LookupLogsInput) -> dict:
        """Copy full records in requested order and report unknown ids separately.

        Example (abridged): LookupLogsInput(ids=["LOG-0062", "missing"]) ->
        {"returned_count": 1, "records": [{"id": "LOG-0062", ...}],
         "missing_ids": ["missing"], ...}.
        """
        by_id = {record["id"]: record for record in self.repository.load()}
        ids = list(dict.fromkeys(query.ids))
        records = [deepcopy(by_id[log_id]) for log_id in ids if log_id in by_id]
        return {
            "status": "ok",
            "returned_count": len(records),
            "records": records,
            "missing_ids": [log_id for log_id in ids if log_id not in by_id],
        }

    def context(self, query: LogContextInput) -> dict:
        """Page through all services within an inclusive window around a record.

        Example (abridged): LogContextInput(log_id="LOG-0062") ->
        {"anchor_found": true, "anchor_id": "LOG-0062", "total_matches": 8, ...}.
        """
        records = self.repository.load()
        anchor = next((record for record in records if record["id"] == query.log_id), None)
        if anchor is None:
            return {
                **paginate_logs([], query.limit, query.offset),
                "anchor_id": query.log_id,
                "anchor_found": False,
                "window": None,
            }
        timestamp = parse_timestamp(anchor["timestamp"])
        start = timestamp - timedelta(minutes=query.before_minutes)
        end = timestamp + timedelta(minutes=query.after_minutes)
        matches = [
            record for record in records
            if start <= parse_timestamp(record["timestamp"]) <= end
        ]
        return {
            **paginate_logs(matches, query.limit, query.offset),
            "anchor_id": query.log_id,
            "anchor_found": True,
            "window": {
                "start_time": format_utc(start),
                "end_time": format_utc(end),
                "end_inclusive": True,
            },
        }

    def catalog(self, query: LogCatalogInput) -> dict:
        """Describe actual record coverage and the values available for filtering.

        Example (abridged): LogCatalogInput() ->
        {"record_count": 121, "timezone": "UTC", "log_types": ["api", ...], ...}.
        """
        records = self.repository.load()
        result = {
            "status": "ok",
            "record_count": len(records),
            "timezone": "UTC",
            "earliest_timestamp": (
                format_utc(parse_timestamp(records[0]["timestamp"])) if records else None
            ),
            "latest_timestamp": (
                format_utc(parse_timestamp(records[-1]["timestamp"])) if records else None
            ),
            "log_types": sorted({record["log_type"] for record in records}),
            "levels": sorted({record["level"] for record in records}),
            "services": sorted({record["service"] for record in records}),
        }
        if query.include_hosts:
            result["hosts"] = sorted({record["host"] for record in records})
        return result
