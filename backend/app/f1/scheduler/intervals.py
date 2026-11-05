from __future__ import annotations

from datetime import datetime, time, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from .models import Interval


def to_utc(value: datetime) -> datetime:
    """Convert an aware datetime to its exact UTC instant (respecting PEP 495 fold)."""
    return value.astimezone(dt_timezone.utc)


def _preserve_tz(utc_value: datetime, reference: datetime) -> datetime:
    if reference.tzinfo is None or reference.tzinfo is dt_timezone.utc:
        return utc_value
    return utc_value.astimezone(reference.tzinfo)


def add_minutes(value: datetime, minutes: int) -> datetime:
    """Add elapsed UTC minutes to an aware datetime while preserving its timezone."""
    utc_result = to_utc(value) + timedelta(minutes=minutes)
    return _preserve_tz(utc_result, value)


def ceil_to_minute(value: datetime) -> datetime:
    """Round an aware datetime upward to the next UTC minute boundary."""
    utc_value = to_utc(value)
    if utc_value.second == 0 and utc_value.microsecond == 0:
        return _preserve_tz(utc_value, value)
    rounded_utc = utc_value.replace(second=0, microsecond=0) + timedelta(minutes=1)
    return _preserve_tz(rounded_utc, value)


def min_instant(left: datetime, right: datetime) -> datetime:
    return left if to_utc(left) <= to_utc(right) else right


def max_instant(left: datetime, right: datetime) -> datetime:
    return left if to_utc(left) >= to_utc(right) else right


def duration_minutes(interval: Interval) -> int:
    return int((to_utc(interval.end_at) - to_utc(interval.start_at)).total_seconds() // 60)


def overlaps(left: Interval, right: Interval) -> bool:
    """Half-open interval overlap: touching endpoints are not overlapping."""
    return to_utc(left.start_at) < to_utc(right.end_at) and to_utc(right.start_at) < to_utc(left.end_at)


def contains(container: Interval, value: Interval) -> bool:
    return to_utc(container.start_at) <= to_utc(value.start_at) and to_utc(value.end_at) <= to_utc(container.end_at)


def clip(interval: Interval, boundary: Interval) -> Interval | None:
    start_utc = to_utc(max_instant(interval.start_at, boundary.start_at))
    end_utc = to_utc(min_instant(interval.end_at, boundary.end_at))
    if start_utc >= end_utc:
        return None
    return Interval(
        _preserve_tz(start_utc, interval.start_at),
        _preserve_tz(end_utc, interval.end_at),
    )


def merge_intervals(intervals: list[Interval] | tuple[Interval, ...]) -> list[Interval]:
    ordered = sorted(intervals, key=lambda item: (to_utc(item.start_at), to_utc(item.end_at)))
    if not ordered:
        return []
    merged = [ordered[0]]
    for current in ordered[1:]:
        previous = merged[-1]
        if to_utc(current.start_at) <= to_utc(previous.end_at):
            end_utc = to_utc(max_instant(previous.end_at, current.end_at))
            merged[-1] = Interval(previous.start_at, _preserve_tz(end_utc, previous.end_at))
        else:
            merged.append(current)
    return merged


def subtract_interval(source: Interval, cut: Interval) -> list[Interval]:
    if not overlaps(source, cut):
        return [source]
    result: list[Interval] = []
    if to_utc(source.start_at) < to_utc(cut.start_at):
        end_utc = to_utc(min_instant(source.end_at, cut.start_at))
        result.append(Interval(source.start_at, _preserve_tz(end_utc, source.end_at)))
    if to_utc(cut.end_at) < to_utc(source.end_at):
        start_utc = to_utc(max_instant(source.start_at, cut.end_at))
        result.append(Interval(_preserve_tz(start_utc, source.start_at), source.end_at))
    return result


def subtract_intervals(
    sources: list[Interval] | tuple[Interval, ...],
    cuts: list[Interval] | tuple[Interval, ...],
) -> list[Interval]:
    result = merge_intervals(sources)
    for cut in merge_intervals(cuts):
        updated: list[Interval] = []
        for source in result:
            updated.extend(subtract_interval(source, cut))
        result = updated
    return result


def pad(interval: Interval, minutes: int) -> Interval:
    return Interval(add_minutes(interval.start_at, -minutes), add_minutes(interval.end_at, minutes))


def split_by_local_day(interval: Interval, timezone: str) -> list[Interval]:
    """Split an absolute interval at local-midnight boundaries."""
    tz = ZoneInfo(timezone)
    result: list[Interval] = []
    cursor = interval.start_at
    while to_utc(cursor) < to_utc(interval.end_at):
        local_cursor = to_utc(cursor).astimezone(tz)
        next_date = local_cursor.date() + timedelta(days=1)
        next_midnight = _preserve_tz(
            to_utc(datetime.combine(next_date, time.min, tzinfo=tz)),
            interval.start_at,
        )
        boundary = min_instant(interval.end_at, next_midnight)
        if to_utc(cursor) < to_utc(boundary):
            result.append(Interval(cursor, boundary))
        cursor = boundary
    return result


def is_single_local_day(interval: Interval, timezone: str) -> bool:
    if to_utc(interval.start_at) >= to_utc(interval.end_at):
        return False
    tz = ZoneInfo(timezone)
    start = to_utc(interval.start_at).astimezone(tz)
    end = to_utc(interval.end_at).astimezone(tz)
    if start.date() == end.date():
        return True
    return end.time() == time.min and end.date() == start.date() + timedelta(days=1)

