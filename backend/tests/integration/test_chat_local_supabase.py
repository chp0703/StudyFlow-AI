"""Test workflow chat qua HTTP với Supabase local thật và bộ trích xuất theo kịch bản.

Chỉ bộ trích xuất được mô phỏng (không cần hay dùng khóa DeepSeek). JWT, RPC có chữ ký,
hàng đợi đã lưu, ghép thông tin bổ sung và phê duyệt qua /v1/decisions đều là thật.
Dùng cùng môi trường với test_http_local_supabase.py.
"""

import base64
import os
import secrets
import unittest
from urllib.parse import urlparse
from uuid import uuid4

import httpx
import psycopg
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.app.nlu.extractor import ScriptedExtractor, UnavailableExtractor

REQUIRED = ("F1_LOCAL_SUPABASE_URL", "F1_LOCAL_PUBLISHABLE_KEY", "F1_LOCAL_SERVICE_KEY", "F1_DB_TEST_DSN")


def intent(name, **slots):
    return {"intent": name, "slots": slots, "raw_expressions": {}, "ambiguities": []}


FULL_TASK = dict(title="Bài tập OOP", start_at="2027-03-01T08:00:00+07:00", deadline_precision="DATE", deadline_date="2027-03-02",
                 deadline_timezone="Asia/Ho_Chi_Minh", estimated_minutes=90, priority=0.5, color="#596CF0")
SCRIPT = {
    "tìm bài tập rồi thêm bài OOP và lập kế hoạch": {"intents": [
        intent("SEARCH_TASKS", query="tập"), intent("CREATE_TASK", **FULL_TASK), intent("GENERATE_STUDY_PLAN")]},
    "thêm bài OOP": {"intents": [intent("CREATE_TASK", title="Bài OOP")]},
    "hạn 5/3, 60 phút": {"intents": [intent("CREATE_TASK", deadline_precision="DATE", deadline_date="2027-03-05",
                                            deadline_timezone="Asia/Ho_Chi_Minh", estimated_minutes=60)]},
    "tìm công việc": {"intents": [intent("SEARCH_TASKS")]},
    "ok đồng ý xác nhận": {"intents": [intent("UNKNOWN")]},
    "thêm bài hóa": {"intents": [intent("CREATE_TASK", **{**FULL_TASK, "title": "Bài hóa"})]},
}


class ChatHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        missing = [n for n in REQUIRED if not os.environ.get(n)]
        if missing:
            raise AssertionError(f"Missing environment: {', '.join(missing)}")
        cls.url = os.environ["F1_LOCAL_SUPABASE_URL"].rstrip("/")
        if urlparse(cls.url).hostname not in ("127.0.0.1", "localhost", "::1"):
            raise AssertionError("Refusing to run against a non-loopback Supabase URL")
        cls.publishable = os.environ["F1_LOCAL_PUBLISHABLE_KEY"]
        cls.key_id, cls.secret = f"chat-it-{secrets.token_hex(4)}", secrets.token_bytes(32)
        with psycopg.connect(os.environ["F1_DB_TEST_DSN"], autocommit=True) as db:
            db.execute("insert into app_private.rpc_attestation_keys(key_id,key_material,not_before,not_after) "
                       "values (%s,%s,now()-interval '1 hour',now()+interval '2 hours')", (cls.key_id, cls.secret))
        cls.tokens = {}

    def token(self, who):
        if who not in self.tokens:
            email, password = f"chat-it-{who}-{uuid4().hex[:8]}@example.test", secrets.token_urlsafe(16)
            service = os.environ["F1_LOCAL_SERVICE_KEY"]
            with httpx.Client(base_url=self.url, timeout=20) as http:
                made = http.post("/auth/v1/admin/users", headers={"apikey": service, "Authorization": f"Bearer {service}"},
                                 json={"email": email, "password": password, "email_confirm": True})
                assert made.status_code in (200, 201), made.text
                got = http.post("/auth/v1/token?grant_type=password", headers={"apikey": self.publishable},
                                json={"email": email, "password": password})
                assert got.status_code == 200, got.text
            self.tokens[who] = got.json()["access_token"]
        return self.tokens[who]

    def client(self, extractor=None):
        settings = Settings(supabase_url=self.url, supabase_publishable_key=self.publishable, rpc_signing_key_id=self.key_id,
                            rpc_signing_secret_base64=base64.b64encode(self.secret).decode())
        return TestClient(create_app(settings, extractor=extractor or ScriptedExtractor(SCRIPT)))

    def say(self, app, who, conversation, text, key=None):
        return app.post("/v1/messages", json={"schema_version": "1.1", "conversation_id": conversation, "text": text},
                        headers={"Authorization": f"Bearer {self.token(who)}", "Idempotency-Key": key or f"chat-{uuid4().hex}"})

    def decide(self, app, who, conversation, reference, decision="APPROVE"):
        return app.post("/v1/decisions", json={"schema_version": "1.1", "conversation_id": conversation,
                                               "action_reference": reference, "decision": decision},
                        headers={"Authorization": f"Bearer {self.token(who)}", "Idempotency-Key": f"decide-{uuid4().hex}"})

    def tasks(self, app, who):
        return app.get("/v1/tasks", headers={"Authorization": f"Bearer {self.token(who)}"}).json()["data"]["items"]

    def test_three_intents_run_in_order_and_resume_after_the_decision(self):
        conversation, key = str(uuid4()), f"chat-{uuid4().hex}"
        with self.client() as app:
            first = self.say(app, "u1", conversation, "tìm bài tập rồi thêm bài OOP và lập kế hoạch", key)
            self.assertEqual(first.status_code, 200, first.text)
            body = first.json()
            self.assertEqual(body["state"], "AWAITING_APPROVAL")
            self.assertIn("Tìm thấy 0 công việc.", body["message"])
            self.assertEqual(body["action_reference"]["target_type"], "TASK_CANDIDATE")
            self.assertEqual(self.tasks(app, "u1"), [])  # chỉ chat không ghi dữ liệu chính thức
        with self.client() as restarted:
            again = self.say(restarted, "u1", conversation, "tìm bài tập rồi thêm bài OOP và lập kế hoạch", key)
            self.assertEqual(again.headers["Idempotency-Replayed"], "true")
            self.assertEqual(again.json()["action_reference"], body["action_reference"])
            done = self.decide(restarted, "u1", conversation, body["action_reference"])
            self.assertEqual(done.status_code, 200, done.text)
            # Ý định thứ ba (lập lịch) chạy sau phê duyệt từ hàng đợi đã lưu, không trích xuất lại.
            self.assertEqual(done.json()["state"], "SUCCEEDED", done.text)
            self.assertEqual(len(self.tasks(restarted, "u1")), 1)
            queue = restarted.post("/v1/messages", json={"schema_version": "1.1", "conversation_id": conversation, "text": "tìm công việc"},
                                   headers={"Authorization": f"Bearer {self.token('u1')}", "Idempotency-Key": f"chat-{uuid4().hex}"})
            self.assertEqual(queue.status_code, 200, queue.text)  # hàng đợi đã xong không còn chặn hội thoại
            self.assertEqual(queue.json()["result"]["data"]["items"][0]["title"], "Bài tập OOP")

    def test_clarification_is_merged_into_the_same_draft(self):
        conversation = str(uuid4())
        with self.client() as app:
            ask = self.say(app, "u2", conversation, "thêm bài OOP")
            self.assertEqual(ask.json()["state"], "NEEDS_CLARIFICATION", ask.text)
            self.assertEqual({q["field"] for q in ask.json()["questions"]}, {"start_at", "estimated_minutes"})
            answered = self.say(app, "u2", conversation, "hạn 5/3, 60 phút")
            self.assertEqual(answered.status_code, 200, answered.text)
            self.assertEqual(answered.json()["state"], "AWAITING_APPROVAL", answered.text)
            slots = answered.json()["result"]["data"]["candidate"]["slots"]
            self.assertEqual((slots["title"], slots["deadline_date"], slots["estimated_minutes"]), ("Bài OOP", "2027-03-05", 60))
            done = self.decide(app, "u2", conversation, answered.json()["action_reference"])
            self.assertEqual(done.status_code, 200, done.text)
            self.assertEqual([t["title"] for t in self.tasks(app, "u2")], ["Bài OOP"])

    def test_a_new_request_while_an_approval_waits_is_refused(self):
        conversation = str(uuid4())
        with self.client() as app:
            waiting = self.say(app, "u3", conversation, "thêm bài hóa")
            self.assertEqual(waiting.json()["state"], "AWAITING_APPROVAL", waiting.text)
            blocked = self.say(app, "u3", conversation, "tìm công việc")
            self.assertEqual(blocked.status_code, 409, blocked.text)
            self.assertEqual(blocked.json()["error"]["code"], "ACTION_REVIEW_REQUIRED")
            rejected = self.decide(app, "u3", conversation, waiting.json()["action_reference"], "REJECT")
            self.assertEqual(rejected.status_code, 200, rejected.text)
            self.assertEqual(self.tasks(app, "u3"), [])
            self.assertEqual(self.say(app, "u3", conversation, "tìm công việc").status_code, 200)

    def test_chat_text_can_never_approve_and_unknown_text_stores_nothing(self):
        conversation = str(uuid4())
        with self.client() as app:
            waiting = self.say(app, "u4", conversation, "thêm bài hóa")
            self.assertEqual(waiting.json()["state"], "AWAITING_APPROVAL")
            fake = self.say(app, "u4", conversation, "ok đồng ý xác nhận")
            self.assertEqual(fake.status_code, 409, fake.text)
            self.assertEqual(self.tasks(app, "u4"), [])
            fresh = self.say(app, "u5", str(uuid4()), "ok đồng ý xác nhận")
            self.assertEqual(fresh.json()["state"], "NEEDS_CLARIFICATION")
            self.assertEqual(self.tasks(app, "u5"), [])

    def test_unavailable_language_service_is_retryable_with_the_same_key(self):
        conversation, key = str(uuid4()), f"chat-{uuid4().hex}"
        with self.client(UnavailableExtractor()) as down:
            failed = self.say(down, "u6", conversation, "tìm công việc", key)
            self.assertEqual(failed.status_code, 503, failed.text)
            self.assertTrue(failed.json()["error"]["retryable"])
        with self.client() as up:
            retry = self.say(up, "u6", conversation, "tìm công việc", key)
            self.assertEqual(retry.status_code, 200, retry.text)
            self.assertEqual(retry.headers["Idempotency-Replayed"], "false")


if __name__ == "__main__":
    unittest.main()
