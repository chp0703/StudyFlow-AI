"""Các ca nghiệm thu độc lập cho việc chuẩn hóa TimeWindow.

Giao diện đã thống nhất để tích hợp:
normalize_time_windows(windows, *, start_at, end_at) -> tuple[Interval, ...].
Đầu vào là các đối tượng JSON TimeWindow theo contract. Đầu ra là các khoảng có múi giờ UTC,
được sắp xếp, gộp và cắt theo phạm vi nửa mở yêu cầu. Đầu vào không hợp lệ,
bao gồm giờ DST địa phương mơ hồ/không tồn tại, sẽ gây ValueError.
"""

import importlib
import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from backend.app.f1.scheduler.models import Interval


def utc(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def metadata():
    return {
        "window_id": "00000000-0000-0000-0000-000000000064",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "version": 1, "archived_at": None,
        "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
    }


def once(start="2026-11-05T08:00:00+07:00", end="2026-11-05T10:00:00+07:00", **changes):
    window = {
        **metadata(),
        "kind": "AVAILABILITY", "label": None, "recurrence": "NONE",
        "timezone": "Asia/Ho_Chi_Minh", "start_at": start, "end_at": end,
        "weekday": None, "start_time": None, "end_time": None,
        "valid_from": None, "valid_until": None,
    }
    window.update(changes)
    return window


def weekly(**changes):
    window = {
        **metadata(),
        "kind": "AVAILABILITY", "label": None, "recurrence": "WEEKLY",
        "timezone": "Asia/Ho_Chi_Minh", "start_at": None, "end_at": None,
        "weekday": 4, "start_time": "08:00", "end_time": "10:00",
        "valid_from": "2026-11-05", "valid_until": None,
    }
    window.update(changes)
    return window


class TimeWindowNormalizationAcceptance(unittest.TestCase):
    def normalize(self, windows, start="2026-11-05T00:00:00Z", end="2026-11-06T00:00:00Z"):
        module = importlib.import_module("backend.app.f1.scheduler.normalization")
        result = module.normalize_time_windows(windows, start_at=utc(start), end_at=utc(end))
        self.assertIsInstance(result, tuple)
        for interval in result:
            self.assertIsInstance(interval, Interval)
            self.assertEqual(interval.start_at.utcoffset(), timezone.utc.utcoffset(None))
            self.assertEqual(interval.end_at.utcoffset(), timezone.utc.utcoffset(None))
        return result

    def test_none_converts_explicit_offset_to_expected_utc_instants(self):
        self.assertEqual(self.normalize([once()]), (
            Interval(utc("2026-11-05T01:00:00Z"), utc("2026-11-05T03:00:00Z")),
        ))

    def test_none_is_clipped_to_requested_horizon(self):
        self.assertEqual(self.normalize([once()], "2026-11-05T01:30:00Z", "2026-11-05T02:30:00Z"), (
            Interval(utc("2026-11-05T01:30:00Z"), utc("2026-11-05T02:30:00Z")),
        ))

    def test_half_open_boundaries_do_not_create_zero_length_intervals(self):
        self.assertEqual(self.normalize([once()], "2026-11-05T03:00:00Z", "2026-11-05T04:00:00Z"), ())

    def test_weekly_uses_iso_weekday_and_valid_until_is_exclusive(self):
        self.assertEqual(self.normalize(
            [weekly(valid_until="2026-11-12")],
            "2026-11-01T00:00:00Z", "2026-11-20T00:00:00Z",
        ), (Interval(utc("2026-11-05T01:00:00Z"), utc("2026-11-05T03:00:00Z")),))

    def test_weekly_honors_valid_from_and_expands_multiple_occurrences(self):
        self.assertEqual(self.normalize(
            [weekly(valid_from="2026-11-12")],
            "2026-11-01T00:00:00Z", "2026-11-20T00:00:00Z",
        ), (
            Interval(utc("2026-11-12T01:00:00Z"), utc("2026-11-12T03:00:00Z")),
            Interval(utc("2026-11-19T01:00:00Z"), utc("2026-11-19T03:00:00Z")),
        ))

    def test_weekly_end_24_is_next_local_midnight_including_previous_utc_day(self):
        self.assertEqual(self.normalize(
            [weekly(weekday=4, start_time="23:00", end_time="24:00")],
        ), (Interval(utc("2026-11-05T16:00:00Z"), utc("2026-11-05T17:00:00Z")),))

    def test_weekly_expansion_clips_both_edges_of_horizon(self):
        self.assertEqual(self.normalize(
            [weekly()], "2026-11-05T01:30:00Z", "2026-11-05T02:30:00Z",
        ), (Interval(utc("2026-11-05T01:30:00Z"), utc("2026-11-05T02:30:00Z")),))

    def test_overlapping_and_adjacent_windows_merge_in_chronological_order(self):
        windows = [
            once("2026-11-05T02:30:00Z", "2026-11-05T04:00:00Z"),
            once(),
            once("2026-11-05T04:00:00Z", "2026-11-05T05:00:00Z"),
        ]
        self.assertEqual(self.normalize(windows), (
            Interval(utc("2026-11-05T01:00:00Z"), utc("2026-11-05T05:00:00Z")),
        ))

    def test_iana_timezone_changes_utc_offset_across_dst(self):
        # 09:00 New York là 13:00Z ngày 25/10, thành 14:00Z sau khi lùi đồng hồ ngày 1/11.
        self.assertEqual(self.normalize(
            [weekly(timezone="America/New_York", weekday=7, start_time="09:00",
                    end_time="10:00", valid_from="2026-10-25", valid_until="2026-11-02")],
            "2026-10-25T00:00:00Z", "2026-11-02T00:00:00Z",
        ), (
            Interval(utc("2026-10-25T13:00:00Z"), utc("2026-10-25T14:00:00Z")),
            Interval(utc("2026-11-01T14:00:00Z"), utc("2026-11-01T15:00:00Z")),
        ))

    def test_ambiguous_fall_back_local_time_requires_clarification(self):
        # Cả hai fold đều tồn tại; tự chọn fold=0 sẽ tự suy diễn ý định người dùng.
        self.assertNotEqual(
            datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0).utcoffset(),
            datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=1).utcoffset(),
        )
        with self.assertRaises(ValueError):
            self.normalize([weekly(
                timezone="America/New_York", weekday=7, start_time="01:30", end_time="02:30",
                valid_from="2026-11-01", valid_until="2026-11-02",
            )], "2026-11-01T00:00:00Z", "2026-11-02T00:00:00Z")

    def test_nonexistent_spring_forward_local_time_requires_clarification(self):
        with self.assertRaises(ValueError):
            self.normalize([weekly(
                timezone="America/New_York", weekday=7, start_time="02:30", end_time="03:30",
                valid_from="2026-03-08", valid_until="2026-03-09",
            )], "2026-03-08T00:00:00Z", "2026-03-09T00:00:00Z")

    def test_invalid_none_windows_raise_value_error(self):
        invalid = {
            "zero duration": once(end="2026-11-05T08:00:00+07:00"),
            "negative duration": once(end="2026-11-05T07:00:00+07:00"),
            "naive instant": once(start="2026-11-05T08:00:00"),
            "second precision": once(start="2026-11-05T08:00:01+07:00"),
            "fraction precision": once(start="2026-11-05T08:00:00.000001+07:00"),
            "bad timezone": once(timezone="Not/A_Zone"),
            "union violation": once(weekday=4),
            "unknown recurrence": once(recurrence="DAILY"),
            "unknown field": once(trusted=True),
        }
        for label, window in invalid.items():
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.normalize([window])

    def test_invalid_weekly_windows_raise_value_error(self):
        invalid = {
            "24 start": weekly(start_time="24:00"),
            "25 end": weekly(end_time="25:00"),
            "noncanonical local time": weekly(start_time="8:00"),
            "zero duration": weekly(end_time="08:00"),
            "overnight unsupported": weekly(start_time="22:00", end_time="02:00"),
            "weekday zero": weekly(weekday=0),
            "weekday eight": weekly(weekday=8),
            "weekday bool": weekly(weekday=True),
            "equal validity dates": weekly(valid_until="2026-11-05"),
            "reversed validity": weekly(valid_until="2026-11-04"),
            "missing valid from": weekly(valid_from=None),
            "none field populated": weekly(start_at="2026-11-05T08:00:00+07:00"),
        }
        for label, window in invalid.items():
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.normalize([window])

    def test_empty_window_input_returns_empty_tuple(self):
        self.assertEqual(self.normalize([]), ())

    def test_archived_windows_are_ignored(self):
        self.assertEqual(self.normalize([
            once(archived_at="2026-11-04T12:00:00Z"),
            once("2026-11-05T04:00:00Z", "2026-11-05T05:00:00Z",
                 window_id="00000000-0000-0000-0000-000000000065"),
        ]), (Interval(utc("2026-11-05T04:00:00Z"), utc("2026-11-05T05:00:00Z")),))

    def test_mixed_availability_and_busy_sets_are_rejected(self):
        with self.assertRaises(ValueError):
            self.normalize([
                once(), once(kind="BUSY", window_id="00000000-0000-0000-0000-000000000065"),
            ])

    def test_busy_only_set_normalizes_independently(self):
        self.assertEqual(self.normalize([once(kind="BUSY")]), (
            Interval(utc("2026-11-05T01:00:00Z"), utc("2026-11-05T03:00:00Z")),
        ))

    def test_invalid_horizon_rejected_before_expansion(self):
        for start, end in (
            ("2026-11-05T02:00:00Z", "2026-11-05T02:00:00Z"),
            ("2026-11-05T03:00:00Z", "2026-11-05T02:00:00Z"),
            ("2026-11-05T01:00:00", "2026-11-05T02:00:00Z"),
        ):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                self.normalize([once()], start, end)


if __name__ == "__main__":
    unittest.main()
