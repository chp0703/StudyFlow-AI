"""Test HTTP đầu cuối với Supabase local thật (GoTrue, PostgREST, Postgres).

Không mock: dùng access token ES256, JWKS, ranh giới RPC có chữ ký và RLS thật.
Biến môi trường bắt buộc (chỉ loopback; không dùng dự án cloud):
  F1_LOCAL_SUPABASE_URL      ví dụ http://127.0.0.1:54321
  F1_LOCAL_PUBLISHABLE_KEY   khóa publishable/anon local
  F1_LOCAL_SERVICE_KEY       khóa service-role/secret local để tạo hai người dùng test
  F1_DB_TEST_DSN             postgresql://postgres:postgres@127.0.0.1:54322/postgres để đăng ký khóa HMAC
"""

import base64
import os
from datetime import datetime, timedelta, timezone
import secrets
import unittest
from urllib.parse import urlparse
from uuid import uuid4

import httpx
import psycopg
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.main import create_app

REQUIRED = ("F1_LOCAL_SUPABASE_URL", "F1_LOCAL_PUBLISHABLE_KEY", "F1_LOCAL_SERVICE_KEY", "F1_DB_TEST_DSN")


class LocalSupabaseHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        missing = [name for name in REQUIRED if not os.environ.get(name)]
        if missing:
            raise AssertionError(f"Missing environment: {', '.join(missing)}")
        cls.url = os.environ["F1_LOCAL_SUPABASE_URL"].rstrip("/")
        if urlparse(cls.url).hostname not in ("127.0.0.1", "localhost", "::1"):
            raise AssertionError("Refusing to run against a non-loopback Supabase URL")
        cls.publishable = os.environ["F1_LOCAL_PUBLISHABLE_KEY"]
        cls.key_id = f"http-it-{secrets.token_hex(4)}"
        cls.secret = secrets.token_bytes(32)
        with psycopg.connect(os.environ["F1_DB_TEST_DSN"], autocommit=True) as db:
            db.execute("insert into app_private.rpc_attestation_keys(key_id,key_material,not_before,not_after) "
                       "values (%s,%s,now()-interval '1 hour',now()+interval '2 hours')", (cls.key_id, cls.secret))
        cls.users = {name: cls.sign_in(name) for name in ("a", "b", "c", "d")}

    @classmethod
    def sign_in(cls, name):
        email, password = f"http-it-{name}-{uuid4().hex[:8]}@example.test", secrets.token_urlsafe(16)
        service = os.environ["F1_LOCAL_SERVICE_KEY"]
        with httpx.Client(base_url=cls.url, timeout=20) as http:
            made = http.post("/auth/v1/admin/users", headers={"apikey": service, "Authorization": f"Bearer {service}"},
                             json={"email": email, "password": password, "email_confirm": True})
            assert made.status_code in (200, 201), made.text
            token = http.post("/auth/v1/token?grant_type=password", headers={"apikey": cls.publishable},
                              json={"email": email, "password": password})
            assert token.status_code == 200, token.text
        return token.json()["access_token"], made.json()["id"]

    def client(self):
        settings = Settings(
            supabase_url=self.url, supabase_publishable_key=self.publishable, rpc_signing_key_id=self.key_id,
            rpc_signing_secret_base64=base64.b64encode(self.secret).decode(), cors_origins=["http://localhost:5173"])
        return TestClient(create_app(settings))

    def auth(self, who, **extra):
        return {"Authorization": f"Bearer {self.users[who][0]}", **extra}

    def post(self, client, path, body, who="a", key=None):
        return client.post(path, json=body, headers=self.auth(who, **{"Idempotency-Key": key or f"it-{uuid4().hex}"}))

    @staticmethod
    def task_body(conversation, title="Ôn giải tích"):
        return {"schema_version": "1.1", "conversation_id": conversation, "operation": "create_task_candidate",
                "arguments": {"slots": {"title": title, "description": "Chương 1", "start_at": "2026-01-01T08:00:00+07:00",
                                        "available_from_at": "2026-01-01T08:00:00+07:00", "deadline_at": None, "deadline_precision": "DATE",
                                        "deadline_date": "2027-03-01", "deadline_timezone": "Asia/Ho_Chi_Minh",
                                        "estimated_minutes": 90, "priority": 1, "color": "#596CF0"}}}

    def test_candidate_decision_read_survives_retry_and_restart(self):
        conversation, key = str(uuid4()), f"it-prepare-{uuid4().hex}"
        with self.client() as app:
            first = self.post(app, "/v1/actions", self.task_body(conversation), key=key)
            self.assertEqual(first.status_code, 200, first.text)
            body = first.json()
            self.assertEqual(body["state"], "AWAITING_APPROVAL")
            self.assertEqual(first.headers["Idempotency-Replayed"], "false")
            reference = body["action_reference"]
            self.assertEqual(reference["target_type"], "TASK_CANDIDATE")
        with self.client() as restarted:  # ứng dụng mới khởi tạo: chỉ database còn nhớ lần gọi đầu
            again = self.post(restarted, "/v1/actions", self.task_body(conversation), key=key)
            self.assertEqual(again.status_code, 200, again.text)
            self.assertEqual(again.headers["Idempotency-Replayed"], "true")
            self.assertEqual(again.json()["action_reference"], reference)
            self.assertNotEqual(again.json()["request_id"], body["request_id"])
            conflict = self.post(restarted, "/v1/actions", self.task_body(conversation, "Khác"), key=key)
            self.assertEqual(conflict.status_code, 409)
            self.assertEqual(conflict.json()["error"]["code"], "IDEMPOTENCY_CONFLICT")

            # Người dùng khác không thể quyết định thao tác này.
            foreign = self.post(restarted, "/v1/decisions", {"schema_version": "1.1", "conversation_id": conversation,
                                                              "action_reference": reference, "decision": "APPROVE"}, who="b")
            self.assertEqual(foreign.status_code, 404, foreign.text)

            decide = {"schema_version": "1.1", "conversation_id": conversation, "action_reference": reference, "decision": "APPROVE"}
            dkey = f"it-decide-{uuid4().hex}"
            done = self.post(restarted, "/v1/decisions", decide, key=dkey)
            self.assertEqual(done.status_code, 200, done.text)
            self.assertEqual(done.json()["state"], "SUCCEEDED")
            self.assertEqual(done.json()["result"]["outcome"], "COMMITTED")
            task_id = done.json()["result"]["data"]["task_id"]
            replay = self.post(restarted, "/v1/decisions", decide, key=dkey)
            self.assertEqual(replay.headers["Idempotency-Replayed"], "true")
            self.assertEqual(replay.json()["result"]["data"]["task_id"], task_id)

            # Quyết định thứ hai với khóa mới thấy thao tác đã xong: không tạo task thứ hai.
            late = self.post(restarted, "/v1/decisions", decide)
            self.assertEqual(late.status_code, 409, late.text)

            mine = restarted.get("/v1/tasks", headers=self.auth("a")).json()
            self.assertEqual([t["task_id"] for t in mine["data"]["items"]], [task_id])
            self.assertEqual(mine["data"]["items"][0]["deadline_at"], "2027-03-01T17:00:00.000000Z")
            self.assertEqual(restarted.get("/v1/tasks", headers=self.auth("b")).json()["data"]["items"], [])

    def test_incomplete_form_asks_questions_and_stores_nothing(self):
        conversation = str(uuid4())
        body = self.task_body(conversation)
        body["arguments"]["slots"].update(title=None, estimated_minutes=None)
        with self.client() as app:
            response = self.post(app, "/v1/actions", body, who="b")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["state"], "NEEDS_CLARIFICATION")
        self.assertEqual({q["field"] for q in response.json()["questions"]}, {"title", "estimated_minutes"})

    def test_reject_cancels_without_saving(self):
        conversation = str(uuid4())
        with self.client() as app:
            prepared = self.post(app, "/v1/actions", self.task_body(conversation, "Sẽ bị hủy"), who="b").json()
            rejected = self.post(app, "/v1/decisions", {"schema_version": "1.1", "conversation_id": conversation,
                                                        "action_reference": prepared["action_reference"], "decision": "REJECT"}, who="b")
            self.assertEqual(rejected.status_code, 200, rejected.text)
            self.assertEqual(rejected.json()["result"]["data"]["pending_action"]["state"], "CANCELLED")
            titles = [t["title"] for t in app.get("/v1/tasks", headers=self.auth("b")).json()["data"]["items"]]
            self.assertNotIn("Sẽ bị hủy", titles)

    def test_preferences_change_needs_a_decision_then_shows_in_the_read(self):
        conversation = str(uuid4())
        with self.client() as app:
            before = app.get("/v1/preferences", headers=self.auth("b")).json()["data"]
            command = {"schema_version": "1.1", "conversation_id": conversation, "operation": "set_scheduling_preferences",
                       "arguments": {"policy_patch": {"break_minutes": 20}, "expected_schedule_revision": before["schedule_revision"]}}
            prepared = self.post(app, "/v1/actions", command, who="b").json()
            self.assertEqual(prepared["result"]["data"]["effective_policy"]["break_minutes"], 20)
            self.assertEqual(app.get("/v1/preferences", headers=self.auth("b")).json()["data"], before)
            done = self.post(app, "/v1/decisions", {"schema_version": "1.1", "conversation_id": conversation,
                                                    "action_reference": prepared["action_reference"], "decision": "APPROVE"}, who="b")
            self.assertEqual(done.status_code, 200, done.text)
            after = app.get("/v1/preferences", headers=self.auth("b")).json()["data"]
            self.assertEqual(after["scheduling_policy"]["break_minutes"], 20)
            self.assertEqual(after["schedule_revision"], before["schedule_revision"] + 1)


    def approve(self, app, body, who):
        prepared = self.post(app, "/v1/actions", body, who=who)
        self.assertEqual(prepared.status_code, 200, prepared.text)
        self.assertEqual(prepared.json()["state"], "AWAITING_APPROVAL", prepared.text)
        done = self.post(app, "/v1/decisions", {"schema_version": "1.1", "conversation_id": body["conversation_id"],
                                                "action_reference": prepared.json()["action_reference"], "decision": "APPROVE"}, who=who)
        self.assertEqual(done.status_code, 200, done.text)
        return done.json()

    def test_generate_review_approve_plan_end_to_end(self):
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        scope = {"start_at": tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "end_at": (tomorrow + timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "selection_mode": "ALL_ELIGIBLE", "task_ids": []}
        generate = lambda: {"schema_version": "1.1", "conversation_id": str(uuid4()), "operation": "generate_study_plan",
                            "arguments": {"generation_scope": scope, "policy_overrides": {}}}
        weekly = {"kind": "AVAILABILITY", "label": "Giờ học", "recurrence": "WEEKLY", "timezone": "Asia/Ho_Chi_Minh",
                  "start_at": None, "end_at": None, "weekday": (tomorrow + timedelta(days=1)).isoweekday(),
                  "start_time": "09:00", "end_time": "24:00", "valid_from": datetime.now(timezone.utc).date().isoformat(),
                  "valid_until": None}
        with self.client() as app:
            self.approve(app, self.task_body(str(uuid4()), "Ôn lập kế hoạch"), "c")
            self.approve(app, {"schema_version": "1.1", "conversation_id": str(uuid4()), "operation": "set_availability",
                               "arguments": {"change_type": "ADD", "window_id": None, "expected_window_version": None,
                                             "window": weekly}}, "c")
            prepared = self.post(app, "/v1/actions", generate(), who="c")
            self.assertEqual(prepared.status_code, 200, prepared.text)
            reply = prepared.json()
            self.assertEqual(reply["state"], "AWAITING_APPROVAL", prepared.text)
            self.assertEqual(reply["action_reference"]["target_type"], "PLAN_PROPOSAL")
            proposal = reply["result"]["data"]["proposal"]
            blocks = proposal["payload"]["study_blocks"]
            confirmation = reply["result"]["data"]["schedule_confirmation"]
            self.assertEqual(confirmation, proposal["payload"]["schedule_confirmation"])
            self.assertEqual(
                (confirmation["proposal_id"], confirmation["proposal_version"],
                 confirmation["base_schedule_revision"]),
                (proposal["proposal_id"], proposal["version"], proposal["base_schedule_revision"]),
            )
            self.assertEqual(
                (reply["action_reference"]["target_id"], reply["action_reference"]["target_version"]),
                (confirmation["proposal_id"], confirmation["proposal_version"]),
            )
            self.assertEqual(confirmation["added"], confirmation["entries"])
            self.assertEqual(confirmation["changed"], [])
            self.assertEqual(confirmation["removed"], [])
            self.assertEqual(confirmation["unscheduled_work"], [])
            for entry in confirmation["entries"]:
                self.assertEqual(entry["task_name"], "Ôn lập kế hoạch")
                self.assertEqual(entry["color"], "#596CF0")
                self.assertGreater(entry["duration_minutes"], 0)
                self.assertEqual(
                    entry["duration_minutes"],
                    int((datetime.fromisoformat(entry["end_at"]) -
                         datetime.fromisoformat(entry["start_at"])).total_seconds() // 60),
                )
            self.assertEqual(proposal["payload"]["coverage"], "FULL")
            self.assertEqual(sum((datetime.fromisoformat(b["end_at"]) - datetime.fromisoformat(b["start_at"])).seconds // 60
                                 for b in blocks), 90)
            self.assertEqual(app.get("/v1/plans", params={"view": "CURRENT"}, headers=self.auth("c")).json()["data"]["plan"], None)
            shown = app.get("/v1/plans", params={"view": "PROPOSAL", "proposal_id": proposal["proposal_id"]}, headers=self.auth("c"))
            self.assertEqual(shown.json()["data"]["proposal"]["status"], "PROPOSED")

            before = app.get("/v1/preferences", headers=self.auth("c")).json()["data"]["schedule_revision"]
            conversation = reply["result"]["data"]["pending_action"]["conversation_id"]
            done = self.post(app, "/v1/decisions", {"schema_version": "1.1", "conversation_id": conversation,
                                                    "action_reference": reply["action_reference"], "decision": "APPROVE"}, who="c")
            self.assertEqual(done.status_code, 200, done.text)
            self.assertEqual(done.json()["result"]["data"]["version"], 1)
            current = app.get("/v1/plans", headers=self.auth("c")).json()["data"]
            self.assertEqual({b["block_id"] for b in current["study_blocks"]}, {b["block_id"] for b in blocks})
            self.assertEqual(app.get("/v1/preferences", headers=self.auth("c")).json()["data"]["schedule_revision"], before + 1)

            # Mọi việc đã có lịch: lần sinh lịch thứ hai không có thay đổi để đề xuất.
            again = self.post(app, "/v1/actions", generate(), who="c")
            self.assertEqual(again.status_code, 200, again.text)
            self.assertEqual(again.json()["state"], "SUCCEEDED")
            self.assertEqual(again.json()["result"]["data"]["coverage"], "NO_CHANGE")


    def test_a_stale_plan_proposal_can_still_be_rejected_and_frees_the_conversation(self):
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        scope = {"start_at": tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "end_at": (tomorrow + timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "selection_mode": "ALL_ELIGIBLE", "task_ids": []}
        weekly = {"kind": "AVAILABILITY", "label": "Giờ học", "recurrence": "WEEKLY", "timezone": "Asia/Ho_Chi_Minh",
                  "start_at": None, "end_at": None, "weekday": (tomorrow + timedelta(days=1)).isoweekday(),
                  "start_time": "09:00", "end_time": "24:00", "valid_from": datetime.now(timezone.utc).date().isoformat(),
                  "valid_until": None}
        conversation = str(uuid4())
        with self.client() as app:
            self.approve(app, self.task_body(str(uuid4()), "Việc thứ nhất"), "d")
            self.approve(app, {"schema_version": "1.1", "conversation_id": str(uuid4()), "operation": "set_availability",
                               "arguments": {"change_type": "ADD", "window_id": None, "expected_window_version": None, "window": weekly}}, "d")
            prepared = self.post(app, "/v1/actions", {"schema_version": "1.1", "conversation_id": conversation, "operation": "generate_study_plan",
                                                      "arguments": {"generation_scope": scope, "policy_overrides": {}}}, who="d")
            self.assertEqual(prepared.json()["state"], "AWAITING_APPROVAL", prepared.text)
            reference = prepared.json()["action_reference"]
            self.approve(app, self.task_body(str(uuid4()), "Việc thứ hai"), "d")  # moves the schedule revision on
            decision = {"schema_version": "1.1", "conversation_id": conversation, "action_reference": reference}
            stale = self.post(app, "/v1/decisions", {**decision, "decision": "APPROVE"}, who="d")
            self.assertEqual((stale.status_code, stale.json()["error"]["code"]), (409, "STALE_PROPOSAL"), stale.text)
            rejected = self.post(app, "/v1/decisions", {**decision, "decision": "REJECT"}, who="d")
            self.assertEqual(rejected.status_code, 200, rejected.text)
            self.assertEqual(rejected.json()["result"]["data"]["pending_action"]["state"], "CANCELLED")
            again = self.post(app, "/v1/actions", {"schema_version": "1.1", "conversation_id": conversation, "operation": "generate_study_plan",
                                                   "arguments": {"generation_scope": scope, "policy_overrides": {}}}, who="d")
            self.assertEqual(again.json()["state"], "AWAITING_APPROVAL", again.text)  # the conversation is free again

    def test_tampered_or_foreign_token_is_rejected_before_the_database(self):
        with self.client() as app:
            token = self.users["a"][0]
            bad = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
            response = app.get("/v1/tasks", headers={"Authorization": f"Bearer {bad}"})
            self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
