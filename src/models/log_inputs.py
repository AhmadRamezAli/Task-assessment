"""Tool input contracts; Pydantic handles ordinary type and bounds checking."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)


class ToolInput(BaseModel):
    """Base contract that trims strings and rejects misspelled argument names.

    Example data: {}. Subclasses declare the arguments each tool accepts.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LogFilters(ToolInput):
    """Optional AND filters shared by search and aggregation.

    Example data: {"start_time": "2026-11-03T14:00:00Z",
                   "log_type": "payment", "level": "ERROR"}.
    AwareDatetime checks time syntax and timezone without a custom parser.
    """

    start_time: AwareDatetime | None = Field(
        default=None, description="Inclusive ISO 8601 time with Z or a UTC offset."
    )
    end_time: AwareDatetime | None = Field(
        default=None, description="Exclusive ISO 8601 time with Z or a UTC offset."
    )
    log_type: Literal["auth", "payment", "api", "database", "scheduler"] | None = Field(
        default=None, description="Log type, combined with other filters using AND."
    )
    level: Literal["INFO", "WARNING", "ERROR"] | None = Field(
        default=None, description="Severity, combined with other filters using AND."
    )
    service: str | None = Field(default=None, description="Exact service name.")
    request_id: str | None = Field(default=None, description="Exact request id.")
    message_contains: str | None = Field(
        default=None, description="Case-insensitive literal substring of the message."
    )

    @field_validator("log_type", "level", mode="before")
    @classmethod
    def normalize_category(cls, value: Any, info: ValidationInfo) -> Any:
        """Accept natural casing without changing the stored categories.

        Example: value="error", field_name="level" -> "ERROR".
        """
        if isinstance(value, str):
            value = value.strip()
            return value.upper() if info.field_name == "level" else value.lower()
        return value

    @model_validator(mode="after")
    def check_time_range(self) -> LogFilters:
        """Reject reversed or empty ranges after Pydantic has parsed the times.

        Example: start=15:00Z, end=14:00Z -> ValueError; a valid range returns self.
        """
        if self.start_time is not None and self.end_time is not None:
            if self.start_time >= self.end_time:
                raise ValueError("start_time must be earlier than end_time.")
        return self


class SearchLogsInput(LogFilters):
    """Search filters plus a bounded page of results.

    Example data: {"level": "ERROR", "limit": 10, "offset": 0}.
    """

    limit: int = Field(default=20, ge=1, le=50, description="Page size; maximum 50.")
    offset: int = Field(default=0, ge=0, description="Matching records to skip.")


class AggregateLogsInput(LogFilters):
    """Count all matching logs by category or fixed UTC time bucket.

    Example data: {"level": "ERROR", "group_by": "time", "bucket_minutes": 5}.
    """

    group_by: Literal["level", "log_type", "service", "host", "time"] = Field(
        default="level", description="Field to count by; time uses fixed UTC buckets."
    )
    bucket_minutes: int = Field(
        default=5, ge=1, le=1440, description="Bucket width when group_by is time."
    )


class LookupLogsInput(ToolInput):
    """Select a bounded set of full records by id.

    Example data: {"ids": ["LOG-0062", "LOG-0085"]}.
    """

    ids: list[str] = Field(
        min_length=1, max_length=50, description="Log ids; duplicate ids are removed."
    )


class LogContextInput(ToolInput):
    """Select the inclusive time window around an anchor record.

    Example data: {"log_id": "LOG-0062", "before_minutes": 5, "after_minutes": 5}.
    """

    log_id: str = Field(description="Anchor log id.")
    before_minutes: int = Field(default=5, ge=0, le=1440, description="Minutes before anchor.")
    after_minutes: int = Field(default=5, ge=0, le=1440, description="Minutes after anchor.")
    limit: int = Field(default=20, ge=1, le=50, description="Page size; maximum 50.")
    offset: int = Field(default=0, ge=0, description="Matching records to skip.")


class LogCatalogInput(ToolInput):
    """Choose whether the compact dataset catalog should include host names.

    Example data: {"include_hosts": true}; omitting it uses false.
    """

    include_hosts: bool = Field(default=False, description="Include host names.")
