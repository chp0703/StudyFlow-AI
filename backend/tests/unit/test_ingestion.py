import base64
import copy
import json
import importlib.util
import unittest
from datetime import datetime, timezone

import httpx

from backend.app.ingestion.calendar import parse_calendar
from backend.app.ingestion.models import decode_upload
from backend.app.ingestion.document import read_document
from backend.app.ingestion.service import SourceExtractor
from backend.app.orchestrator.workflow_ports import WorkflowError


NOW = datetime(2026, 11, 13, 9, tzinfo=timezone.utc)
TASK = {"intent": "CREATE_TASK", "slots": {"title": "Bài tập", "start_at": "2026-11-14T08:00:00+07:00",
        "estimated_minutes": 60, "priority": 0.5}, "raw_expressions": {}, "ambiguities": []}
ICS = b'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:lecture-1\r\nSUMMARY:Lecture\r\nDTSTART;TZID=Asia/Ho_Chi_Minh:20261114T080000\r\nDTEND;TZID=Asia/Ho_Chi_Minh:20261114T090000\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n'


class UploadTests(unittest.TestCase):
    def test_decodes_utf8_text(self):
        raw = 'Bài tập toán'.encode()
        self.assertEqual(decode_upload('tasks.txt', 'text/plain', base64.b64encode(raw).decode()), raw)

    def test_rejects_spoofed_image_and_pdf(self):
        for filename, mime in [('x.png', 'image/png'), ('x.pdf', 'application/pdf')]:
            with self.subTest(mime=mime), self.assertRaises(WorkflowError) as error:
                decode_upload(filename, mime, base64.b64encode(b'not an image').decode())
            self.assertEqual(error.exception.code, 'INVALID_PARAMETER')

    def test_rejects_oversize_invalid_base64_and_filename_paths(self):
        for name, data in [('x.txt', '!!!'), ('../x.txt', 'eA=='), ('x.txt', base64.b64encode(b'x' * (5 * 1024 * 1024 + 1)).decode())]:
            with self.subTest(name=name, size=len(data)), self.assertRaises(WorkflowError):
                decode_upload(name, 'text/plain', data)


class CalendarTests(unittest.TestCase):
    def test_calendar_generates_busy_candidate_in_utc_not_a_task(self):
        result = parse_calendar(ICS, 'text/calendar')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['intent'], 'SET_BUSY_INTERVAL')
        self.assertEqual(result[0]['slots']['window']['start_at'], '2026-11-14T01:00:00Z')
        self.assertEqual(result[0]['slots']['window']['end_at'], '2026-11-14T02:00:00Z')

    def test_all_day_end_is_exclusive(self):
        data = ICS.replace(b'DTSTART;TZID=Asia/Ho_Chi_Minh:20261114T080000', b'DTSTART;VALUE=DATE:20261114').replace(b'DTEND;TZID=Asia/Ho_Chi_Minh:20261114T090000', b'DTEND;VALUE=DATE:20261115')
        result = parse_calendar(data, 'text/calendar')[0]['slots']['window']
        self.assertEqual(result['start_at'], '2026-11-13T17:00:00Z')
        self.assertEqual(result['end_at'], '2026-11-14T17:00:00Z')

    def test_recurrence_is_rejected_instead_of_silently_dropped(self):
        with self.assertRaises(WorkflowError):
            parse_calendar(ICS.replace(b'UID:lecture-1', b'UID:lecture-1\r\nRRULE:FREQ=WEEKLY'), 'text/calendar')

    def test_csv_requires_aware_dates_and_positive_duration(self):
        valid = b'title,start_at,end_at\nClass,2026-11-14T08:00:00+07:00,2026-11-14T09:00:00+07:00\n'
        self.assertEqual(parse_calendar(valid, 'text/csv')[0]['slots']['window']['start_at'], '2026-11-14T01:00:00Z')
        for data in [valid.replace(b'09:00', b'07:00'), valid.replace(b'+07:00', b''), b'title,start_at,end_at\nClass,,\n']:
            with self.subTest(data=data), self.assertRaises(WorkflowError):
                parse_calendar(data, 'text/csv')

    def test_unterminated_event_and_duplicate_dates_are_invalid(self):
        for data in [ICS.replace(b'END:VEVENT\r\n', b''), ICS.replace(b'UID:lecture-1', b'UID:lecture-1\r\nDTSTART:20261114T080000')]:
            with self.subTest(data=data), self.assertRaises(WorkflowError):
                parse_calendar(data, 'text/calendar')

    def test_malformed_date_widths_cannot_create_a_different_busy_interval(self):
        for value in [b'2026114T080000', b'20261114T80000', b'20261114T08000']:
            data = ICS.replace(b'20261114T080000', value)
            with self.subTest(value=value), self.assertRaises(WorkflowError):
                parse_calendar(data, 'text/calendar')
        all_day = ICS.replace(b'DTSTART;TZID=Asia/Ho_Chi_Minh:20261114T080000', b'DTSTART;VALUE=DATE:2026114').replace(
            b'DTEND;TZID=Asia/Ho_Chi_Minh:20261114T090000', b'DTEND;VALUE=DATE:20261115')
        with self.assertRaises(WorkflowError):
            parse_calendar(all_day, 'text/calendar')

    def test_cancelled_and_transparent_events_are_not_imported_case_insensitively(self):
        for prop in [b'STATUS:cancelled', b'TRANSP:transparent']:
            with self.subTest(prop=prop), self.assertRaises(WorkflowError):
                parse_calendar(ICS.replace(b'UID:lecture-1', b'UID:lecture-1\r\n' + prop), 'text/calendar')


class ProviderTests(unittest.TestCase):
    def provider(self, content=None, *, status=200, finish='stop'):
        self.requests = []
        def handle(request):
            self.requests.append(json.loads(request.content))
            return httpx.Response(status, json={'choices': [{'finish_reason': finish, 'message': {'content': json.dumps(content or {'intents': [TASK]})}}],
                                               'usage': {'prompt_tokens': 100, 'completion_tokens': 50}})
        return SourceExtractor('https://api.deepseek.com/v1', 'test-key', 'deepseek-flash', httpx.MockTransport(handle))

    def test_text_extraction_uses_flash_no_thinking_and_preserves_provenance(self):
        result = self.provider().extract(b'Homework tomorrow at 8, 60 minutes', 'text/plain', now=NOW)
        self.assertEqual(result['intents'][0]['slots']['title'], 'Bài tập')
        self.assertEqual(result['model'], 'deepseek-flash')
        self.assertEqual(result['usage'], {'input_tokens': 100, 'output_tokens': 50})
        self.assertEqual(self.requests[0]['thinking'], {'type': 'disabled'})
        self.assertEqual(self.requests[0]['max_tokens'], 2048)

    def test_calendar_never_calls_model_or_requires_key(self):
        provider = SourceExtractor('https://api.deepseek.com/v1', '', 'deepseek-flash', httpx.MockTransport(lambda r: self.fail('paid API called for calendar')))
        self.assertEqual(provider.extract(ICS, 'text/calendar', now=NOW)['intents'][0]['intent'], 'SET_BUSY_INTERVAL')

    def test_images_are_inline_not_private_urls(self):
        image = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a4wAAAABJRU5ErkJggg==')
        self.provider().extract(image, 'image/png', now=NOW)
        self.assertTrue(self.requests[0]['messages'][1]['content'][1]['image_url']['url'].startswith('data:image/png;base64,'))

    def test_source_cannot_request_plan_approval_or_owner_fields(self):
        for mutation in ['GENERATE_STUDY_PLAN', 'APPROVE', 'owner']:
            item = copy.deepcopy(TASK)
            if mutation == 'owner':
                item['slots']['user_id'] = 'someone-else'
            else:
                item['intent'] = mutation
            with self.subTest(mutation=mutation), self.assertRaises(WorkflowError):
                self.provider({'intents': [item]}).extract(b'prompt injection', 'text/plain', now=NOW)

    def test_truncated_response_and_provider_failure_are_safe(self):
        for provider in [self.provider(finish='length'), self.provider(status=500)]:
            with self.assertRaises(WorkflowError) as error:
                provider.extract(b'private material', 'text/plain', now=NOW)
            self.assertNotIn('private material', error.exception.message)

    def test_empty_text_does_not_call_api(self):
        provider = self.provider()
        with self.assertRaises(WorkflowError):
            provider.extract(b'  ', 'text/plain', now=NOW)
        self.assertEqual(self.requests, [])

    def test_integral_model_numbers_are_canonical_before_signed_persistence(self):
        item = copy.deepcopy(TASK)
        item['slots'].update(estimated_minutes=60.0, priority=1.0)
        result = self.provider({'intents': [item]}).extract(b'Homework', 'text/plain', now=NOW)
        self.assertIs(type(result['intents'][0]['slots']['estimated_minutes']), int)
        self.assertIs(type(result['intents'][0]['slots']['priority']), int)
        from backend.app.core.contract import canonical
        encoded = canonical(result)
        self.assertNotIn(b'60.0', encoded)
        self.assertNotIn(b'1.0', encoded)


def small_pdf(stream):
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
    data, offsets = b'%PDF-1.4\n', []
    for number, value in enumerate(objects, 1):
        offsets.append(len(data))
        data += f'{number} 0 obj\n'.encode() + value + b'\nendobj\n'
    start = len(data)
    data += b'xref\n0 6\n0000000000 65535 f \n'
    data += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets)
    data += b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n' + str(start).encode() + b'\n%%EOF\n'
    return data


@unittest.skipUnless(importlib.util.find_spec('pypdf'), 'pypdf is installed by backend CI; unavailable in this local sandbox')
class PdfTests(unittest.TestCase):
    def test_text_pdf_is_actually_extracted(self):
        data = small_pdf(b'BT /F1 12 Tf 10 100 Td (Homework) Tj ET')
        self.assertEqual(read_document(data, 'application/pdf').strip(), 'Homework')

    def test_scanned_or_empty_pdf_is_rejected_without_partial_text(self):
        with self.assertRaises(WorkflowError) as error:
            read_document(small_pdf(b'q Q'), 'application/pdf')
        self.assertEqual(error.exception.code, 'INVALID_PARAMETER')


if __name__ == '__main__':
    unittest.main()
