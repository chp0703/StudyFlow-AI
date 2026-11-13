from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime, time, timedelta, timezone
import re
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .intervals import clip, is_single_local_day, merge_intervals
from .models import PRODUCT_TIMEZONE, Interval


_RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$"
)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_START_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
_END_TIME_RE = re.compile(r"^(?:(?:[01]\d|2[0-3]):[0-5]\d|24:00)$")

_WINDOW_KEYS = frozenset({
    "window_id",
    "user_id",
    "version",
    "kind",
    "label",
    "recurrence",
    "timezone",
    "start_at",
    "end_at",
    "weekday",
    "start_time",
    "end_time",
    "valid_from",
    "valid_until",
    "archived_at",
    "created_at",
    "updated_at",
})


def _is_aware_datetime(value: object) -> bool:
    return (
        isinstance(value, datetime)
        and value.tzinfo is not None
        and value.utcoffset() is not None
    )


def _is_minute_aligned(value: datetime) -> bool:
    return value.second == 0 and value.microsecond == 0


def _parse_uuid(value: object, field_name: str) -> UUID:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a UUID string")
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid UUID") from exc


def _parse_rfc3339(value: object, field_name: str, *, minute_aligned: bool) -> datetime:
    if not isinstance(value, str) or not _RFC3339_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a valid RFC 3339 timestamp with offset")
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field_name} is not a valid calendar timestamp") from exc
    if not _is_aware_datetime(parsed):
        raise ValueError(f"{field_name} must include a timezone offset")
    if minute_aligned and not _is_minute_aligned(parsed):
        raise ValueError(f"{field_name} must be minute-aligned")
    return parsed


def _parse_date(value: object, field_name: str) -> date:
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a canonical YYYY-MM-DD date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} is not a valid calendar date") from exc


def _parse_timezone(value: object) -> ZoneInfo:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timezone must be a non-empty IANA timezone name")
    try:
        tz = ZoneInfo(value)
    except (ZoneInfoNotFoundError, KeyError, ValueError) as exc:
        raise ValueError(f"Invalid IANA timezone: {value}") from exc
    if value != PRODUCT_TIMEZONE:
        raise ValueError(f"timezone must be {PRODUCT_TIMEZONE}: {value}")
    return tz


def _resolve_strict_local_datetime(local_date: date, local_time: time, tz: ZoneInfo) -> datetime:
    naive = datetime.combine(local_date, local_time)
    dt0 = naive.replace(tzinfo=tz, fold=0)
    dt1 = naive.replace(tzinfo=tz, fold=1)
    if dt0.utcoffset() != dt1.utcoffset():
        raise ValueError(
            f"Local time {naive.isoformat()} in {tz.key} is ambiguous or nonexistent across DST"
        )
    roundtrip = dt0.astimezone(timezone.utc).astimezone(tz)
    if roundtrip.replace(tzinfo=None) != naive:
        raise ValueError(
            f"Local time {naive.isoformat()} in {tz.key} does not exist due to a DST transition"
        )
    return dt0.astimezone(timezone.utc)


def _validate_common_fields(window: Mapping[str, object]) -> tuple[str, str, ZoneInfo, bool]:
    if not isinstance(window, Mapping):
        raise ValueError("Each time window must be a mapping")
    keys = set(window.keys())
    if keys != _WINDOW_KEYS:
        unknown = sorted(keys - _WINDOW_KEYS)
        missing = sorted(_WINDOW_KEYS - keys)
        if unknown:
            raise ValueError(f"Unknown TimeWindow fields: {', '.join(unknown)}")
        raise ValueError(f"Missing required TimeWindow fields: {', '.join(missing)}")

    _parse_uuid(window["window_id"], "window_id")
    _parse_uuid(window["user_id"], "user_id")

    version = window["version"]
    if type(version) is not int or not (1 <= version <= 9007199254740991):
        raise ValueError("version must be a positive safe integer")

    kind = window["kind"]
    if kind not in ("AVAILABILITY", "BUSY"):
        raise ValueError("kind must be AVAILABILITY or BUSY")

    label = window["label"]
    if label is not None and (not isinstance(label, str) or not label.strip()):
        raise ValueError("label must be null or a non-blank string")

    recurrence = window["recurrence"]
    if recurrence not in ("NONE", "WEEKLY"):
        raise ValueError("recurrence must be NONE or WEEKLY")

    tz = _parse_timezone(window["timezone"])

    archived_at = window["archived_at"]
    if archived_at is not None:
        _parse_rfc3339(archived_at, "archived_at", minute_aligned=False)
    _parse_rfc3339(window["created_at"], "created_at", minute_aligned=False)
    _parse_rfc3339(window["updated_at"], "updated_at", minute_aligned=False)

    return str(kind), str(recurrence), tz, archived_at is not None


def _normalize_none_window(
    window: Mapping[str, object],
    tz: ZoneInfo,
    horizon: Interval,
) -> list[Interval]:
    for weekly_field in ("weekday", "start_time", "end_time", "valid_from", "valid_until"):
        if window[weekly_field] is not None:
            raise ValueError(f"{weekly_field} must be null when recurrence is NONE")

    start_dt = _parse_rfc3339(window["start_at"], "start_at", minute_aligned=True)
    end_dt = _parse_rfc3339(window["end_at"], "end_at", minute_aligned=True)
    start_utc = start_dt.astimezone(timezone.utc)
    end_utc = end_dt.astimezone(timezone.utc)
    if start_utc >= end_utc:
        raise ValueError("NONE window end_at must be strictly after start_at")

    raw_interval = Interval(start_utc, end_utc)
    if not is_single_local_day(raw_interval, tz.key):
        raise ValueError("NONE window must stay within a single local day or end at next midnight")

    clipped = clip(raw_interval, horizon)
    return [clipped] if clipped is not None else []


def _normalize_weekly_window(
    window: Mapping[str, object],
    tz: ZoneInfo,
    horizon: Interval,
) -> list[Interval]:
    if window["start_at"] is not None or window["end_at"] is not None:
        raise ValueError("start_at and end_at must be null when recurrence is WEEKLY")

    weekday = window["weekday"]
    if type(weekday) is not int or not (1 <= weekday <= 7):
        raise ValueError("weekday must be an integer between 1 (Monday) and 7 (Sunday)")

    start_time_raw = window["start_time"]
    end_time_raw = window["end_time"]
    if not isinstance(start_time_raw, str) or not _START_TIME_RE.fullmatch(start_time_raw):
        raise ValueError("start_time must be in canonical HH:MM format (00:00..23:59)")
    if not isinstance(end_time_raw, str) or not _END_TIME_RE.fullmatch(end_time_raw):
        raise ValueError("end_time must be in canonical HH:MM format (00:00..23:59) or 24:00")

    start_hour, start_minute = int(start_time_raw[:2]), int(start_time_raw[3:5])
    start_total_minutes = start_hour * 60 + start_minute
    if end_time_raw == "24:00":
        end_total_minutes = 24 * 60
        end_day_offset = 1
        end_local_time = time.min
    else:
        end_hour, end_minute = int(end_time_raw[:2]), int(end_time_raw[3:5])
        end_total_minutes = end_hour * 60 + end_minute
        end_day_offset = 0
        end_local_time = time(end_hour, end_minute)

    if end_total_minutes <= start_total_minutes:
        raise ValueError("WEEKLY window end_time must be strictly after start_time in the same local day")

    start_local_time = time(start_hour, start_minute)
    valid_from = _parse_date(window["valid_from"], "valid_from")
    valid_until_raw = window["valid_until"]
    valid_until: date | None = None
    if valid_until_raw is not None:
        valid_until = _parse_date(valid_until_raw, "valid_until")
        if valid_until <= valid_from:
            raise ValueError("valid_until must be strictly after valid_from")

    horizon_local_start = horizon.start_at.astimezone(tz)
    horizon_local_end = horizon.end_at.astimezone(tz)
    first_date = max(valid_from, horizon_local_start.date())
    last_horizon_date = (
        horizon_local_end.date()
        if horizon_local_end.time() == time.min
        else horizon_local_end.date() + timedelta(days=1)
    )
    end_exclusive = min(valid_until, last_horizon_date) if valid_until is not None else last_horizon_date

    days_ahead = (weekday - first_date.isoweekday()) % 7
    current_date = first_date + timedelta(days=days_ahead)

    expanded: list[Interval] = []
    while current_date < end_exclusive:
        occ_start = _resolve_strict_local_datetime(current_date, start_local_time, tz)
        occ_end = _resolve_strict_local_datetime(
            current_date + timedelta(days=end_day_offset),
            end_local_time,
            tz,
        )
        if occ_start >= occ_end:
            raise ValueError("Expanded WEEKLY occurrence has non-positive duration")
        clipped = clip(Interval(occ_start, occ_end), horizon)
        if clipped is not None:
            expanded.append(clipped)
        current_date += timedelta(days=7)

    return expanded


def normalize_time_windows(
    windows: Iterable[Mapping[str, object]],
    *,
    start_at: datetime,
    end_at: datetime,
) -> tuple[Interval, ...]:
    """Mở rộng và kiểm tra các đối tượng JSON TimeWindow theo contract trong phạm vi thời gian hữu hạn."""
    if not _is_aware_datetime(start_at) or not _is_aware_datetime(end_at):
        raise ValueError("Horizon start_at and end_at must be timezone-aware datetimes")
    if not _is_minute_aligned(start_at) or not _is_minute_aligned(end_at):
        raise ValueError("Horizon start_at and end_at must be minute-aligned")

    horizon_start = start_at.astimezone(timezone.utc)
    horizon_end = end_at.astimezone(timezone.utc)
    if horizon_start >= horizon_end:
        raise ValueError("Horizon end_at must be strictly after start_at")

    if isinstance(windows, (str, bytes, Mapping)) or not isinstance(windows, Iterable):
        raise ValueError("windows must be an iterable of TimeWindow dictionaries")

    horizon = Interval(horizon_start, horizon_end)
    seen_kinds: set[str] = set()
    collected: list[Interval] = []

    for window in windows:
        kind, recurrence, tz, is_archived = _validate_common_fields(window)
        if is_archived:
            continue

        seen_kinds.add(kind)
        if len(seen_kinds) > 1:
            raise ValueError("Cannot mix AVAILABILITY and BUSY windows in a single normalization call")

        if recurrence == "NONE":
            intervals = _normalize_none_window(window, tz, horizon)
        else:
            intervals = _normalize_weekly_window(window, tz, horizon)

        collected.extend(intervals)

    return tuple(merge_intervals(collected))
