"""Bounded calendar parsing. Unsupported recurrence is rejected, never guessed."""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..core import contract
from .models import MAX_CANDIDATES, MAX_TEXT, decode_text, invalid

VN = ZoneInfo('Asia/Ho_Chi_Minh')


def _stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def _candidate(title: str, start: datetime, end: datetime) -> dict:
    if not title.strip() or len(title) > 500 or end <= start:
        raise invalid('Sự kiện cần tên và giờ kết thúc sau giờ bắt đầu.')
    window = {'kind': 'BUSY', 'label': title, 'recurrence': 'NONE', 'timezone': 'Asia/Ho_Chi_Minh',
              'start_at': _stamp(start), 'end_at': _stamp(end), 'weekday': None,
              'start_time': None, 'end_time': None, 'valid_from': None, 'valid_until': None}
    args = {'change_type': 'ADD', 'window_id': None, 'expected_window_version': None, 'window': window}
    if not contract.is_valid('set_busy_intervalArguments', args):
        raise invalid('Khoảng bận không hợp lệ.')
    return {'intent': 'SET_BUSY_INTERVAL', 'slots': {'change_type': 'ADD', 'window': window},
            'raw_expressions': {}, 'ambiguities': []}


def _ical_time(prop: tuple[dict, str]) -> tuple[datetime, bool]:
    params, value = prop
    is_date = params.get('VALUE') == 'DATE'
    try:
        if is_date:
            if params.get('TZID'):
                raise ValueError()
            return datetime.strptime(value, '%Y%m%d').replace(tzinfo=VN), True
        if params.get('VALUE', 'DATE-TIME') != 'DATE-TIME':
            raise ValueError()
        if value.endswith('Z'):
            if params.get('TZID'):
                raise ValueError()
            return datetime.strptime(value, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc), False
        tz = ZoneInfo(params.get('TZID', 'Asia/Ho_Chi_Minh'))
        result = datetime.strptime(value, '%Y%m%dT%H%M%S').replace(tzinfo=tz)
        # Reject nonexistent/ambiguous DST instants rather than choosing an offset.
        if result.utcoffset() != result.replace(fold=1).utcoffset() or result.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) != result.replace(tzinfo=None):
            raise ValueError()
        return result, False
    except (ValueError, ZoneInfoNotFoundError):
        raise invalid('Ngày giờ hoặc múi giờ iCalendar không hợp lệ.') from None


def _ics(text: str) -> list[dict]:
    lines = re.sub(r'\r?\n[ \t]', '', text).splitlines()
    stack, event, events, uids = [], None, [], set()
    for line in lines:
        if not line.strip():
            continue
        if ':' not in line:
            raise invalid('Dòng iCalendar không hợp lệ.')
        key, value = line.split(':', 1)
        if key in ('BEGIN', 'END'):
            if key == 'BEGIN':
                if not stack and (value != 'VCALENDAR' or events):
                    raise invalid()
                if value == 'VEVENT':
                    if stack != ['VCALENDAR']:
                        raise invalid()
                    event = {}
                stack.append(value)
            else:
                if not stack or stack[-1] != value:
                    raise invalid()
                if value == 'VEVENT':
                    if event is None or not {'DTSTART', 'SUMMARY', 'UID'} <= event.keys():
                        raise invalid('Sự kiện thiếu UID, tên hoặc ngày bắt đầu.')
                    if any(k in event for k in ('RRULE', 'RDATE', 'EXDATE', 'EXRULE', 'RECURRENCE-ID', 'DURATION')):
                        raise invalid('Chưa hỗ trợ quy tắc lặp hoặc DURATION; hãy xuất từng sự kiện có DTEND.')
                    uid = event['UID'][1]
                    if not uid or uid in uids:
                        raise invalid('UID sự kiện bị trùng hoặc rỗng.')
                    uids.add(uid)
                    if event.get('STATUS', ({}, ''))[1] == 'CANCELLED' or event.get('TRANSP', ({}, ''))[1] == 'TRANSPARENT':
                        raise invalid('Lịch chứa sự kiện đã hủy hoặc không đánh dấu bận; hãy loại chúng trước khi nhập.')
                    start, all_day = _ical_time(event['DTSTART'])
                    if 'DTEND' in event:
                        end, end_date = _ical_time(event['DTEND'])
                        if end_date != all_day:
                            raise invalid('DTSTART và DTEND phải cùng loại ngày/giờ.')
                    elif all_day:
                        end = start + timedelta(days=1)
                    else:
                        raise invalid('Sự kiện có giờ cần DTEND rõ ràng.')
                    title = re.sub(r'\\([nN,;\\])', lambda m: '\n' if m[1].lower() == 'n' else m[1], event['SUMMARY'][1])
                    events.append(_candidate(title, start, end))
                    if len(events) > MAX_CANDIDATES:
                        raise invalid('Mỗi nguồn chỉ hỗ trợ tối đa 20 sự kiện.')
                    event = None
                stack.pop()
            continue
        if stack and stack[-1] == 'VEVENT':
            parts = key.split(';')
            prop = parts[0].upper()
            if prop in event:
                raise invalid('Thuộc tính sự kiện bị lặp.')
            params = {}
            for item in parts[1:]:
                if '=' not in item:
                    raise invalid()
                name, val = item.split('=', 1)
                if name.upper() in params:
                    raise invalid()
                params[name.upper()] = val.strip('"')
            event[prop] = params, value
    if stack or not events:
        raise invalid('Lịch chưa đóng đúng cấu trúc hoặc không có sự kiện.')
    return events


def parse_calendar(content: bytes, mime_type: str) -> list[dict]:
    text = decode_text(content)
    if len(text) > MAX_TEXT:
        raise invalid('Nội dung lịch vượt giới hạn 24.000 ký tự.')
    if mime_type == 'text/calendar':
        return _ics(text)
    if mime_type != 'text/csv':
        raise invalid()
    try:
        reader = csv.DictReader(io.StringIO(text), strict=True)
        if reader.fieldnames != ['title', 'start_at', 'end_at']:
            raise ValueError()
        events = []
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError()
            start, end = (datetime.fromisoformat(row[k].replace('Z', '+00:00')) for k in ('start_at', 'end_at'))
            if start.tzinfo is None or end.tzinfo is None:
                raise ValueError()
            events.append(_candidate(row['title'], start, end))
            if len(events) > MAX_CANDIDATES:
                raise ValueError()
        if not events:
            raise ValueError()
        return events
    except (ValueError, csv.Error):
        raise invalid('CSV cần title,start_at,end_at; tối đa 20 dòng, ngày giờ phải kèm múi giờ.') from None
