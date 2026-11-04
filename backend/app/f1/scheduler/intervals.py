from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from .models import Interval


def duration_minutes(interval: Interval) -> int:
    return int((interval.end_at - interval.start_at).total_seconds() // 60)


def overlaps(left: Interval, right: Interval) -> bool:
    """Half-open interval overlap: touching endpoints are not overlapping."""
    return left.start_at < right.end_at and right.start_at < left.end_at


def contains(container: Interval, value: Interval) -> bool:
    return container.start_at <= value.start_at and value.end_at <= container.end_at


def clip(interval: Interval, boundary: Interval) -> Interval | None:
    start_at = max(interval.start_at, boundary.start_at)
    end_at = min(interval.end_at, boundary.end_at)
    return Interval(start_at, end_at) if start_at < end_at else None


def merge_intervals(intervals: list[Interval] | tuple[Interval, ...]) -> list[Interval]:
    ordered = sorted(intervals, key=lambda item: (item.start_at, item.end_at))
    if not ordered:
        return []
    merged = [ordered[0]]
    for current in ordered[1:]:
        previous = merged[-1]
        if current.start_at <= previous.end_at:
            merged[-1] = Interval(previous.start_at, max(previous.end_at, current.end_at))
        else:
            merged.append(current)
    return merged


def subtract_interval(source: Interval, cut: Interval) -> list[Interval]:
    if not overlaps(source, cut):
        return [source]
    result: list[Interval] = []
    if source.start_at < cut.start_at:
        result.append(Interval(source.start_at, min(source.end_at, cut.start_at)))
    if cut.end_at < source.end_at:
        result.append(Interval(max(source.start_at, cut.end_at), source.end_at))
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
    amount = timedelta(minutes=minutes)
    return Interval(interval.start_at - amount, interval.end_at + amount)


def split_by_local_day(interval: Interval, timezone: str) -> list[Interval]:
    """Split an absolute interval at local-midnight boundaries."""
    tz = ZoneInfo(timezone)
    result: list[Interval] = []
    cursor = interval.start_at
    while cursor < interval.end_at:
        local_cursor = cursor.astimezone(tz)
        next_date = local_cursor.date() + timedelta(days=1)
        next_midnight = datetime.combine(next_date, time.min, tzinfo=tz)
        boundary = min(interval.end_at, next_midnight)
        if cursor < boundary:
            result.append(Interval(cursor, boundary))
        cursor = boundary
    return result


def is_single_local_day(interval: Interval, timezone: str) -> bool:
    tz = ZoneInfo(timezone)
    start = interval.start_at.astimezone(tz)
    end = interval.end_at.astimezone(tz)
    if start.date() == end.date():
        return True
    return end.time() == time.min and end.date() == start.date() + timedelta(days=1)

