import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from backend.app.orchestrator.actions import ActionProcessor
from backend.app.orchestrator.chat import ChatProcessor, action_id_for
from backend.app.orchestrator.workflow_shared import Terminal

CONV = "00300000-0000-4000-8000-000000000002"
MSG = "00300000-0000-4000-8000-000000000003"
MAT_A = "00300000-0000-4000-8000-0000000000a1"
MAT_B = "00300000-0000-4000-8000-0000000000b2"
CTX = SimpleNamespace(request_id="req-1", user_id="00300000-0000-4000-8000-000000000001")
NOW = datetime(2026, 11, 24, 9, tzinfo=timezone.utc)


def material(material_id, filename, status="READY", course_label=None):
    return {"material_id": material_id, "filename": filename, "status": status, "course_label": course_label}


def intent(kind, **slots):
    return {"intent": kind, "slots": slots, "raw_expressions": {}, "ambiguities": []}


class FakeProc:
    """Replaces only the database/F2 boundary used by ChatProcessor."""

    def __init__(self, materials=None, active=None):
        self.materials, self.active = materials or [], active
        self.steps, self.drafts, self.recs = [], [], []
        self.questions_ops = SimpleNamespace(generate_drafts=self._drafts)
        self.recommendations_ops = SimpleNamespace(create=self._rec)

    def step(self, ctx, operation, arguments, **kwargs):
        self.steps.append((operation, arguments))
        if operation == "list_learning_materials":
            return {"data": {"materials": self.materials, "has_more": False}}
        raise AssertionError(operation)

    def workflow_context(self, ctx, conversation, action_id, key, tolerate_absent):
        return {"active_action": self.active, "selected_action": None}

    def _reply(self, receipt):
        ref = {"action_id": receipt["action_id"], "action_version": 1, "target_type": "PENDING_ACTION",
               "target_id": receipt["action_id"], "target_version": 1}
        return 200, {"state": "AWAITING_APPROVAL", "message": "ok", "action_reference": ref}

    def _drafts(self, ctx, receipt, key, body):
        self.drafts.append((receipt, key, body))
        return self._reply(receipt)

    def _rec(self, ctx, receipt, key, body, record_message=True):
        self.recs.append((receipt, key, body, record_message))
        return self._reply(receipt)


def chat_for(proc):
    return ChatProcessor(proc, None, clock=lambda: NOW)


def cont(index=0, intents=None):
    return {"conversation_id": CONV, "source_message_id": MSG, "cursor": index, "version": 1,
            "origin_idempotency_key": "k" * 16, "extraction": {"intents": intents or []},
            "completed_steps": [], "depends_on": [[]], "awaiting_reference": None}


KEY = "orchestrator-test-key-0001"


class RevisionPlanTests(unittest.TestCase):
    def test_revision_without_a_plan_gets_one_appended(self):
        out = ChatProcessor.with_revision_plan({"intents": [intent("PROPOSE_REVISION", topic="x")]})
        self.assertEqual([i["intent"] for i in out["intents"]], ["PROPOSE_REVISION", "GENERATE_STUDY_PLAN"])

    def test_existing_later_plan_or_no_revision_is_untouched(self):
        with_plan = {"intents": [intent("PROPOSE_REVISION", topic="x"), intent("GENERATE_STUDY_PLAN")]}
        self.assertIs(ChatProcessor.with_revision_plan(with_plan), with_plan)
        plain = {"intents": [intent("CREATE_QUIZ", topic="x")]}
        self.assertIs(ChatProcessor.with_revision_plan(plain), plain)

    def test_a_plan_before_the_revision_does_not_count(self):
        out = ChatProcessor.with_revision_plan({"intents": [intent("GENERATE_STUDY_PLAN"), intent("PROPOSE_REVISION", topic="x")]})
        self.assertEqual(out["intents"][-1]["intent"], "GENERATE_STUDY_PLAN")
        self.assertEqual(len(out["intents"]), 3)

    def test_the_revision_is_a_write_the_plan_waits_for(self):
        deps = ChatProcessor.dependencies({"intents": [intent("PROPOSE_REVISION"), intent("GENERATE_STUDY_PLAN")]})
        self.assertEqual(deps, [[], [0]])


class PickMaterialTests(unittest.TestCase):
    def pick(self, materials, name=None):
        return chat_for(FakeProc(materials)).pick_material(CTX, name)["material_id"]

    def test_the_only_ready_material_is_chosen(self):
        self.assertEqual(self.pick([material(MAT_A, "so.pdf"), material(MAT_B, "x.pdf", "INDEXING")]), MAT_A)

    def test_name_selects_among_several_case_insensitively(self):
        both = [material(MAT_A, "Giai-tich.pdf"), material(MAT_B, "dai-so.pdf")]
        self.assertEqual(self.pick(both, "DAI-SO"), MAT_B)

    def test_a_named_material_that_does_not_match_is_an_error_not_a_fallback(self):
        with self.assertRaises(Terminal) as raised:
            self.pick([material(MAT_A, "history.pdf")], "algebra.pdf")
        self.assertEqual(raised.exception.error["code"], "ENTITY_NOT_FOUND")
        self.assertIn("algebra.pdf", raised.exception.error["message"])

    def test_ambiguous_or_missing_material_is_a_clear_error(self):
        both = [material(MAT_A, "a.pdf"), material(MAT_B, "b.pdf")]
        with self.assertRaises(Terminal) as many:
            self.pick(both)
        self.assertIn("a.pdf", many.exception.error["message"])
        with self.assertRaises(Terminal) as none:
            self.pick([material(MAT_A, "a.pdf", "FAILED")])
        self.assertEqual(none.exception.error["code"], "ENTITY_NOT_FOUND")


class WriteLearningTests(unittest.TestCase):
    def run_step(self, proc, item):
        return chat_for(proc).write_learning(CTX, KEY, cont(), 0, item)

    def test_quiz_calls_generation_with_defaults_and_a_per_step_action_id(self):
        proc = FakeProc([material(MAT_A, "so.pdf")])
        outcome, ref = self.run_step(proc, intent("CREATE_QUIZ", topic=" Số chẵn "))
        self.assertIsNone(outcome)
        receipt, _, body = proc.drafts[0]
        self.assertEqual(receipt["action_id"], action_id_for(MSG, 0))
        self.assertEqual((body["topic"], body["count"], body["question_type"], body["material_id"]),
                         ("Tài liệu học tập", 5, "MCQ", MAT_A))
        self.assertEqual(ref["action_id"], action_id_for(MSG, 0))

    def test_f2_gets_the_materials_own_topic_not_the_spoken_one(self):
        proc = FakeProc([material(MAT_A, "so.pdf", course_label="Toán rời rạc")])
        self.run_step(proc, intent("CREATE_QUIZ", topic="số chẵn"))
        self.assertEqual(proc.drafts[0][2]["topic"], "Toán rời rạc")

    def test_revision_defaults_and_does_not_rerecord_the_chat_message(self):
        proc = FakeProc([material(MAT_A, "so.pdf")])
        _, ref = self.run_step(proc, intent("PROPOSE_REVISION", topic="Số chẵn"))
        _, _, body, record_message = proc.recs[0]
        self.assertEqual((body["suggested_minutes"], body["priority"], record_message), (30, 0.5, False))
        self.assertEqual(ref["target_type"], "PENDING_ACTION")

    def test_priority_one_is_sent_as_integer_one(self):
        proc = FakeProc([material(MAT_A, "so.pdf")])
        self.run_step(proc, intent("PROPOSE_REVISION", topic="x", priority=1.0, suggested_minutes=45))
        self.assertIs(type(proc.recs[0][2]["priority"]), int)

    def test_missing_topic_and_invalid_slots_fail_the_step_without_calling_f2(self):
        proc = FakeProc([material(MAT_A, "so.pdf")])
        for item in (intent("CREATE_QUIZ"), intent("CREATE_QUIZ", topic="x", count=99),
                     intent("PROPOSE_REVISION", topic="x", suggested_minutes=5)):
            with self.subTest(item=item):
                outcome, ref = self.run_step(proc, item)
                self.assertIsNone(ref)
                self.assertEqual((outcome["disposition"], outcome["error"]["code"]), ("FAILED", "INVALID_PARAMETER"))
        self.assertEqual((proc.drafts, proc.recs), ([], []))

    def test_another_pending_action_blocks_the_step(self):
        proc = FakeProc([material(MAT_A, "so.pdf")], active={"pending_action": {"action_id": "someone-else"}})
        outcome, ref = self.run_step(proc, intent("CREATE_QUIZ", topic="x"))
        self.assertEqual(outcome["error"]["code"], "ACTION_REVIEW_REQUIRED")
        self.assertEqual(proc.drafts, [])

    def test_retry_reuses_the_action_created_by_this_step(self):
        mine = action_id_for(MSG, 0)
        active = {"pending_action": {"action_id": mine, "version": 1}, "candidate": None, "proposal": None}
        proc = FakeProc([material(MAT_A, "so.pdf")], active=active)
        outcome, ref = self.run_step(proc, intent("CREATE_QUIZ", topic="x"))
        self.assertIsNone(outcome)
        self.assertEqual(ref["action_id"], mine)
        self.assertEqual(proc.drafts, [])

    def test_summarize_is_reported_as_unsupported_in_chat(self):
        outcome, ref = chat_for(FakeProc()).run_step(CTX, KEY, cont(intents=[intent("SUMMARIZE_LEARNING")]), 0)
        self.assertIsNone(ref)
        self.assertEqual((outcome["disposition"], outcome["error"]["code"]), ("FAILED", "UNSUPPORTED_OPERATION"))


class ResumeTests(unittest.TestCase):
    """The recommendation step stays open (WAIT) on the task draft it created; other decisions ADVANCE."""

    def setUp(self):
        self.calls = []
        queue = {**cont(0, [intent("PROPOSE_REVISION")]), "awaiting_reference": {"action_id": "rec-action"}, "receipt": 1}
        proc = SimpleNamespace(step=self.step, workflow_context=self.workflow_context, queue=queue)
        self.chat = chat_for(proc)
        self.queue = queue

    def step(self, ctx, operation, arguments, **kwargs):
        self.calls.append((operation, arguments))
        if operation == "get_workflow_continuation":
            return {"data": {"continuation": self.queue}}
        if operation == "checkpoint_workflow_continuation":
            return {"data": {**self.queue, "version": 2,
                             "awaiting_reference": arguments["action_reference"], "completed_steps": []}}
        raise AssertionError(operation)

    def workflow_context(self, ctx, conversation, action_id, key, tolerate_absent):
        raise RuntimeError("compose reached")

    def test_approved_recommendation_waits_on_the_new_task_draft(self):
        new = {"data": {"pending_action": {"action_id": "task-action", "version": 1, "state": "AWAITING_CLARIFICATION"},
                        "candidate": {"candidate_id": "cand-1", "version": 3}}}
        receipt = {"request_fingerprint": "f", "lease_version": 1}
        with self.assertRaisesRegex(RuntimeError, "compose reached"):
            self.chat.resume(CTX, receipt, KEY, CONV, {"action_id": "rec-action"}, "decide_revision_recommendation", new, False)
        op, args = self.calls[-1]
        self.assertEqual((op, args["transition"]), ("checkpoint_workflow_continuation", "WAIT"))
        self.assertEqual((args["action_reference"]["target_type"], args["action_reference"]["target_id"]),
                         ("TASK_CANDIDATE", "cand-1"))

    def test_rejected_recommendation_advances_with_a_rejected_outcome(self):
        receipt = {"request_fingerprint": "f", "lease_version": 1}
        self.queue["extraction"]["intents"] = [intent("PROPOSE_REVISION")]
        try:
            self.chat.resume(CTX, receipt, KEY, CONV, {"action_id": "rec-action"}, "decide_revision_recommendation", None, True)
        except RuntimeError:
            pass
        args = [a for op, a in self.calls if op == "checkpoint_workflow_continuation"][0]
        self.assertEqual((args["transition"], args["outcome"]["disposition"]), ("ADVANCE", "REJECTED"))

    def test_foreign_action_is_not_part_of_the_queue(self):
        out = self.chat.resume(CTX, {"request_fingerprint": "f", "lease_version": 1}, KEY, CONV,
                               {"action_id": "other"}, "verify_question_drafts", {}, False)
        self.assertIsNone(out)


class CrossFeatureDecisionTests(unittest.TestCase):
    def test_decision_reply_is_returned_when_no_queue_is_waiting(self):
        proc = ActionProcessor.__new__(ActionProcessor)
        proc.chat = SimpleNamespace(resume=lambda *a, **k: None)
        body = {"conversation_id": CONV, "action_reference": {"action_id": "a"}, "decision": "APPROVE"}
        done = (200, {"result": {"outcome": "COMMITTED"}, "state": "SUCCEEDED"})
        self.assertEqual(proc.resume_cross_feature(CTX, {}, KEY, body, "verify_question_drafts", done), done)

    def test_queue_reply_replaces_the_decision_reply(self):
        proc = ActionProcessor.__new__(ActionProcessor)
        seen = {}
        proc.chat = SimpleNamespace(resume=lambda *a: seen.update(args=a) or {"state": "AWAITING_APPROVAL"})
        body = {"conversation_id": CONV, "action_reference": {"action_id": "a"}, "decision": "REJECT"}
        status, payload = proc.resume_cross_feature(CTX, {}, KEY, body, "verify_question_drafts", (200, {"result": None}))
        self.assertEqual(payload["state"], "AWAITING_APPROVAL")
        self.assertIs(seen["args"][7], True)  # rejected flag


class AnswerRecommendationDraftTests(unittest.TestCase):
    """A follow-up message completes the task draft a revision recommendation created, through review_pending_action."""

    def test_answer_goes_through_the_review_path_not_a_reprepare(self):
        from backend.app.nlu.extractor import ScriptedExtractor

        slots = {"title": "Ôn tập: Số chẵn", "estimated_minutes": 30, "priority": 0.5, "color": "#596CF0"}
        last = {"kind": "ACTION_PRESENTATION", "revision_recommendation": {"recommendation_id": "r"}}
        action = {"pending_action": {"action_id": "a-1", "version": 3, "state": "AWAITING_CLARIFICATION",
                                     "missing_fields": ["start_at"]},
                  "candidate": {"candidate_id": "c-1", "version": 2, "slots": slots, "field_sources": {}},
                  "last_presentation": {"presentation": last}}
        calls = []

        def step(ctx, operation, arguments, **kwargs):
            calls.append((operation, arguments))
            return {"data": {"stored": True}}

        proc = SimpleNamespace(
            step=step, normalize_slots=ActionProcessor.normalize_slots, questions=ActionProcessor.questions,
            validate_task_slots=ActionProcessor.validate_task_slots, clock=lambda: NOW,
            workflow_context=lambda *a, **k: {"selected_action": action},
            candidate_review_reply=lambda ctx, stored: (200, {"state": "AWAITING_APPROVAL", "stored": stored}))
        given = {"intents": [{"intent": "CREATE_TASK", "slots": {"start_at": "2026-11-25T08:00:00+07:00"},
                              "raw_expressions": {}, "ambiguities": []}]}
        chat = ChatProcessor(proc, ScriptedExtractor({"8h sáng mai": given}), clock=lambda: NOW)
        queue = {**cont(0, [intent("PROPOSE_REVISION")]), "awaiting_reference": {"action_id": "a-1"}}
        receipt = {"message_id": MSG, "request_fingerprint": "f", "lease_version": 1}

        status, payload = chat.answer_open_queue(CTX, receipt, KEY, CONV, "8h sáng mai", queue)

        self.assertEqual((status, payload["state"]), (200, "AWAITING_APPROVAL"))
        self.assertEqual([op for op, _ in calls], ["review_pending_action"])
        args = calls[0][1]
        self.assertEqual((args["action_id"], args["expected_action_version"], args["expected_candidate_version"]),
                         ("a-1", 3, 2))
        self.assertEqual(args["candidate_patch"]["start_at"], "2026-11-25T01:00:00.000000Z")
        self.assertEqual(args["candidate_patch"]["title"], "Ôn tập: Số chẵn")


if __name__ == "__main__":
    unittest.main()
