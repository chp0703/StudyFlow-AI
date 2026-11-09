"""Nghiệm thu độc lập có thể thực thi. Thiếu cấu hình database là lỗi, không bỏ qua test."""
from dataclasses import replace
from datetime import datetime
import hashlib
import json
import unittest

from psycopg import sql

from harness import Call, Database, Fixture, canonical, uid


class RealDatabaseTransactions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        self.fixture = Fixture(self.db)

    def scalar(self, query, params=()):
        return self.db.admin.execute(query, params).fetchone()[0]

    def count(self, table, suffix="", params=()):
        query = sql.SQL("select count(*) from app_private.{} where user_id=%s ").format(sql.Identifier(table)) + sql.SQL(suffix)
        return self.scalar(query, (self.fixture.owner, *params))

    def revision(self):
        return self.scalar("select schedule_revision from app_private.user_profiles where user_id=%s", (self.fixture.owner,))

    def error(self, result, codes):
        # Database.invoke đã kiểm tra schema công khai riêng của từng thao tác.
        self.assertEqual("ERROR", result["outcome"], result)
        self.assertIsNone(result["data"])
        self.assertIn(result["error"]["code"], codes, result)

    def assert_promotion(self, candidate, call, revision):
        self.assertEqual(1, self.count("academic_tasks", "and candidate_id=%s", (candidate["candidate_id"],)))
        self.assertEqual(1, self.count("approval_actions", "and target_type='TASK_CANDIDATE' and target_id=%s", (candidate["candidate_id"],)))
        self.assertEqual(revision + 1, self.revision())
        self.assertEqual("COMPLETED", self.scalar("select state from app_private.pending_actions where user_id=%s and action_id=%s",
            (self.fixture.owner, call.reference["action_id"])))
        backlink = self.db.admin.execute("select c.confirmed_task_id,t.task_id from app_private.task_candidates c join app_private.academic_tasks t on t.candidate_id=c.candidate_id and t.user_id=c.user_id where c.user_id=%s and c.candidate_id=%s",
            (self.fixture.owner, candidate["candidate_id"])).fetchone()
        self.assertIsNotNone(backlink)
        self.assertEqual(backlink[0], backlink[1])

    def test_same_key_confirmation_race_and_lost_response_replay(self):
        candidate, call = self.fixture.candidate()
        revision = self.revision()
        first, second = self.db.race(self.fixture, [call, call])
        self.assertEqual(["COMMITTED", "COMMITTED"], [first["outcome"], second["outcome"]])
        self.assertEqual(first["data"], second["data"])
        self.assert_promotion(candidate, call, revision)
        self.assertEqual(1, self.count("idempotency_records", "and operation='confirm_task' and idempotency_key=%s", (call.key,)))
        # invoke mở kết nối mới và làm mới request_id/chứng thực.
        replay = self.db.invoke(self.fixture, call)
        self.assertEqual("COMMITTED", replay["outcome"])
        self.assertEqual(first["data"], replay["data"])
        self.assertNotEqual(first["request_id"], replay["request_id"])
        self.assert_promotion(candidate, call, revision)

    def test_distinct_key_confirmation_race_promotes_only_once(self):
        candidate, first_call = self.fixture.candidate()
        second_call = replace(first_call, key=self.fixture.key())
        revision = self.revision()
        results = self.db.race(self.fixture, [first_call, second_call])
        self.assertEqual(1, sum(result["outcome"] == "COMMITTED" for result in results), results)
        loser = next(result for result in results if result["outcome"] != "COMMITTED")
        self.error(loser, {"STALE_ENTITY_VERSION"})
        self.assert_promotion(candidate, first_call, revision)

    def planning_fixture(self):
        task = self.fixture.confirmed_task()
        self.fixture.availability()
        return task

    def test_competing_proposal_approvals_use_one_owner_lock_across_conversations(self):
        task = self.planning_fixture()
        proposal1, call1 = self.fixture.proposal(task)
        proposal2, call2 = self.fixture.proposal(task, offset=30)
        self.assertNotEqual(call1.conversation, call2.conversation)
        self.assertEqual(proposal1["base_schedule_revision"], proposal2["base_schedule_revision"])
        revision = self.revision()
        results = self.db.race(self.fixture, [call1, call2])
        self.assertEqual(1, sum(result["outcome"] == "COMMITTED" for result in results), results)
        winning_index = next(index for index, result in enumerate(results) if result["outcome"] == "COMMITTED")
        loser = results[1 - winning_index]
        self.error(loser, {"STALE_PROPOSAL", "STALE_PLAN_VERSION"})
        winner = results[winning_index]["data"]
        self.assertEqual(1, self.count("study_plans"))
        self.assertEqual(2, self.count("study_blocks"))
        self.assertEqual(1, self.count("approval_actions", "and target_type='PLAN_PROPOSAL'"))
        self.assertEqual(revision + 1, self.revision())
        current = self.scalar("select current_plan_id::text from app_private.user_profiles where user_id=%s", (self.fixture.owner,))
        self.assertEqual(winner["plan_id"], current)
        losing_proposal = [proposal1, proposal2][1 - winning_index]
        self.assertEqual("STALE", self.scalar("select status from app_private.plan_proposals where user_id=%s and proposal_id=%s",
            (self.fixture.owner, losing_proposal["proposal_id"])))
        replay = self.db.invoke(self.fixture, [call1, call2][winning_index])
        self.assertEqual("COMMITTED", replay["outcome"])
        self.assertEqual(winner, replay["data"])
        self.assertEqual(revision + 1, self.revision())

    def test_policy_revision_only_stale_persists_and_replays(self):
        task = self.planning_fixture()
        proposal, approval = self.fixture.proposal(task)
        pointer_before = self.scalar("select current_plan_id from app_private.user_profiles where user_id=%s", (self.fixture.owner,))
        self.fixture.policy_change()
        revision = self.revision()
        self.assertGreater(revision, proposal["base_schedule_revision"])
        self.assertEqual(pointer_before, self.scalar("select current_plan_id from app_private.user_profiles where user_id=%s", (self.fixture.owner,)))
        result = self.db.invoke(self.fixture, approval)
        self.error(result, {"STALE_PROPOSAL"})
        self.assertEqual(0, self.count("study_plans"))
        self.assertEqual(0, self.count("study_blocks"))
        self.assertEqual(0, self.count("approval_actions", "and target_type='PLAN_PROPOSAL'"))
        # Phiên xác thực mới phải thấy chuyển trạng thái STALE đã commit.
        view = self.db.invoke(self.fixture, Call("get_study_plan", {"view": "PROPOSAL", "version": None,
            "proposal_id": proposal["proposal_id"], "start_at": None, "end_at": None}, None, uid(), None))
        self.assertEqual("READ", view["outcome"])
        self.assertEqual("STALE", view["data"]["proposal"]["status"])
        replay = self.db.invoke(self.fixture, approval)
        self.error(replay, {"STALE_PROPOSAL"})
        self.assertEqual(result["error"], replay["error"])
        self.assertEqual(revision, self.revision())
        self.assertEqual(1, self.count("idempotency_records", "and operation='approve_study_plan' and idempotency_key=%s", (approval.key,)))

    def test_error_on_second_block_rolls_back_entire_approval_and_retry_works(self):
        task = self.planning_fixture()
        _, approval = self.fixture.proposal(task)
        before = self.db.snapshot(self.fixture.owner)
        function = "sol_fault_" + uid().replace("-", "")
        trigger = "sol_fault_" + uid().replace("-", "")
        # Hàm trigger tạm chỉ dùng cho test, không phải giao diện hỗ trợ của ứng dụng.
        # Nó được lệnh INSERT phê duyệt thật gọi bằng role của wrapper.
        self.db.admin.execute(sql.SQL("""create function pg_temp.{}() returns trigger language plpgsql
            set search_path='' as $fault$ begin
            if new.user_id={}::uuid and (select count(*) from app_private.study_blocks b
              where b.plan_id=new.plan_id and b.user_id=new.user_id)>=2 then
              raise exception using errcode='XX000',message='SOL_SECOND_BLOCK_FAULT';
            end if; return new; end $fault$""").format(sql.Identifier(function), sql.Literal(self.fixture.owner)))
        self.db.admin.execute(sql.SQL("create trigger {} after insert on app_private.study_blocks for each row execute function pg_temp.{}()").format(sql.Identifier(trigger), sql.Identifier(function)))
        try:
            result = self.db.invoke(self.fixture, approval)
            self.error(result, {"INTERNAL_ERROR"})
            self.assertNotIn("SOL_SECOND_BLOCK_FAULT", json.dumps(result))
            self.assertEqual(before, self.db.snapshot(self.fixture.owner),
                "plan, both blocks, pointer/revision, proposal, action, approval and idempotency must roll back together")
        finally:
            self.db.admin.execute(sql.SQL("drop trigger {} on app_private.study_blocks").format(sql.Identifier(trigger)))
            self.db.admin.execute(sql.SQL("drop function pg_temp.{}()").format(sql.Identifier(function)))
        self.db.success(self.fixture, approval, "COMMITTED")
        self.assertEqual(1, self.count("study_plans"))
        self.assertEqual(2, self.count("study_blocks"))

    def test_receipt_120_second_lease_reclaim_fences_old_worker(self):
        conversation, message, origin_key = uid(), uid(), self.fixture.key()
        fingerprint = hashlib.sha256(canonical({"text": "lease acceptance", "conversation_id": conversation}).encode()).hexdigest()
        claim_args = {"http_operation": "send_message", "idempotency_key": origin_key,
            "request_fingerprint": fingerprint, "conversation_id": conversation}
        claim = Call("claim_api_receipt", claim_args, conversation, message, self.fixture.key())
        first = self.db.success(self.fixture, claim, "COMMITTED")
        self.assertEqual(1, first["lease_version"])
        self.assertIsNotNone(first["message_id"])
        self.assertIsNotNone(first["action_id"])
        seconds = (datetime.fromisoformat(first["lease_until"].replace("Z", "+00:00")) -
            datetime.fromisoformat(first["created_at"].replace("Z", "+00:00"))).total_seconds()
        self.assertGreaterEqual(seconds, 119)
        self.assertLessEqual(seconds, 121)
        # Chỉ là fixture điều chỉnh đồng hồ vận hành; không chứng minh hết hạn theo thời gian thật.
        changed = self.db.admin.execute("update app_private.api_request_receipts set lease_until=clock_timestamp()-interval '1 second' where user_id=%s and http_operation=%s and idempotency_key=%s",
            (self.fixture.owner, "send_message", origin_key)).rowcount
        self.assertEqual(1, changed)
        print("LEASE_CLOCK_FIXTURE backdated only api_request_receipts.lease_until", flush=True)
        second = self.db.success(self.fixture, claim, "COMMITTED")
        self.assertEqual(first["lease_version"] + 1, second["lease_version"])
        self.assertEqual((first["message_id"], first["action_id"]), (second["message_id"], second["action_id"]))
        read = self.db.invoke(self.fixture, Call("search_tasks", {"query": None, "status_filter": [],
            "page_size": 50, "cursor": None}, None, uid(), None))
        self.assertEqual("READ", read["outcome"])
        reply = {"schema_version": "1.1", "request_id": read["request_id"], "state": "SUCCEEDED",
            "message": "Receipt acceptance complete", "action_reference": None,
            "questions": [], "result": read, "error": None}
        common = {"http_operation": "send_message", "idempotency_key": origin_key,
            "request_fingerprint": fingerprint, "expected_lease_version": first["lease_version"]}
        saved = self.db.snapshot(self.fixture.owner)
        for operation in ("renew_api_receipt", "release_api_receipt", "complete_api_receipt"):
            with self.subTest(old_worker_operation=operation):
                arguments = dict(common)
                if operation == "complete_api_receipt":
                    arguments.update(http_status=200, response=reply)
                result = self.db.invoke(self.fixture, Call(operation, arguments, conversation,
                    first["message_id"], self.fixture.key(), request_id=reply["request_id"] if operation == "complete_api_receipt" else None))
                self.error(result, {"STALE_ENTITY_VERSION", "IDEMPOTENCY_CONFLICT", "FORBIDDEN", "SERVICE_UNAVAILABLE"})
                self.assertEqual(saved, self.db.snapshot(self.fixture.owner), "old worker must not mutate reclaimed receipt")
        completed = self.db.success(self.fixture, Call("complete_api_receipt", {
            **common, "expected_lease_version": second["lease_version"], "http_status": 200, "response": reply},
            conversation, second["message_id"], self.fixture.key(), request_id=reply["request_id"]), "COMMITTED")
        self.assertEqual("COMPLETED", completed["state"])
        replay = self.db.success(self.fixture, claim, "COMMITTED")
        self.assertEqual("COMPLETED", replay["state"])
        self.assertEqual(reply, replay["response"])
        self.assertEqual(second["lease_version"], replay["lease_version"])
        self.assertEqual(0, self.revision())


if __name__ == "__main__":
    unittest.main(verbosity=2)
