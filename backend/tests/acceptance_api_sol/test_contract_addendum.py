"""Independent acceptance for the user-approved A/B/C/D contract 1.0.1.

These are static contract tests, not database/authentication evidence. They use
the real shared JSON Schema and the existing approved pure semantic checker.
No substitute schema, queue implementation or test-local semantic oracle exists.
"""

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from contracts.check_contract import validate_instance


ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "contracts"
FIXTURES = Path(__file__).parent / "fixtures"
CONVERSATION = "00000000-0000-4000-8000-000000000003"
SOURCE = "00000000-0000-4000-8000-000000000004"
NEW_HELPERS = {
    "ensure_user_context": (False, True, "User"),
    "list_time_windows": (True, False, "TimeWindowListData"),
    "get_workflow_context": (True, False, "WorkflowContextData"),
    "get_workflow_continuation": (True, False, None),
    "initialize_workflow_continuation": (False, True, "WorkflowContinuationRecord"),
    "checkpoint_workflow_continuation": (False, True, "WorkflowContinuationRecord"),
}
OLD_HELPERS = {
    "get_scheduling_context", "persist_plan_proposal", "prepare_pending_action",
    "review_pending_action", "update_candidate_draft", "cancel_pending_action",
    "record_source_message", "claim_api_receipt", "complete_api_receipt",
    "lookup_operation_result", "renew_api_receipt", "release_api_receipt",
}
PUBLIC_OPERATIONS = {
    "create_task_candidate", "confirm_task", "search_tasks", "set_availability",
    "set_busy_interval", "set_scheduling_preferences", "generate_study_plan",
    "get_study_plan", "approve_study_plan", "reject_study_plan",
}
PUBLIC_ENDPOINTS = {
    ("post", "/v1/messages"), ("post", "/v1/actions"),
    ("post", "/v1/actions/{action_id}/review"), ("post", "/v1/decisions"),
    ("get", "/v1/tasks"), ("get", "/v1/time-windows"),
    ("get", "/v1/preferences"), ("get", "/v1/plans"),
}
RECORD_KEYS = {
    "user_id", "conversation_id", "source_message_id", "origin_http_operation",
    "origin_idempotency_key", "origin_request_fingerprint", "version", "extraction",
    "extraction_digest", "depends_on", "cursor", "awaiting_reference",
    "completed_steps", "created_at", "updated_at",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ApprovedAddendumAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = read(CONTRACTS / "schemas/f1.schema.json")
        cls.defs = cls.schema["$defs"]
        cls.service = read(CONTRACTS / "service-contract.json")
        cls.data = read(CONTRACTS / "data-contract.json")
        cls.api = read(CONTRACTS / "openapi.yaml")
        cls.internal = {entry["rpc"]: entry for entry in cls.service["internal_interfaces"]}

    def definition(self, name):
        self.assertTrue(name in self.defs, f"Approved 1.0.1 definition not implemented: {name}")
        return self.defs[name]

    def helper(self, name):
        self.assertTrue(name in self.internal, f"Approved internal helper not implemented: {name}")
        return self.internal[name]

    def errors(self, name, value, *, semantic=True):
        self.definition(name)
        return validate_instance(self.defs, name, value, semantic=semantic)

    def valid(self, name, value):
        self.assertEqual(self.errors(name, value), [], f"{name}: expected approved valid payload")

    def invalid(self, name, value, *, semantic=True):
        self.assertTrue(self.errors(name, value, semantic=semantic), f"{name}: invalid payload was accepted")

    def arguments(self):
        record = read(FIXTURES / "continuation_valid.json")
        binding = read(FIXTURES / "checkpoint_wait_valid.json")["receipt_binding"]
        return {
            "ensure_user_context": {},
            "list_time_windows": {"kind": None, "include_archived": False, "page_size": 50, "cursor": None},
            "get_workflow_context": {"conversation_id": CONVERSATION, "action_id": None, "message_id": None},
            "get_workflow_continuation": {"conversation_id": CONVERSATION, "source_message_id": None},
            "initialize_workflow_continuation": {
                "conversation_id": CONVERSATION, "source_message_id": SOURCE,
                "extraction": record["extraction"], "depends_on": record["depends_on"],
                "receipt_binding": binding,
            },
            "checkpoint_workflow_continuation": read(FIXTURES / "checkpoint_wait_valid.json"),
        }

    def rpc(self, name):
        request = read(CONTRACTS / "examples/valid/rpc-read-no-conversation.json")
        request.update(contract_version="1.0.1", operation=name, arguments=self.arguments()[name])
        if name in {"initialize_workflow_continuation", "checkpoint_workflow_continuation"}:
            request["execution_context"]["conversation_id"] = CONVERSATION
            request["execution_context"]["idempotency_key"] = "sol-addendum-0001"
        if NEW_HELPERS[name][1]:
            # Deliberately shape-only signature, never sent to a live service.
            request["attestation"] = {"key_id": "sol-shape-only", "payload": "shape-only", "signature": "0" * 64}
        return request

    def test_package_version_advances_without_logical_schema_change(self):
        self.assertEqual(self.service["contract_version"], "1.0.1")
        self.assertEqual(self.data["contract_version"], "1.0.1")
        self.assertEqual(self.api["info"]["version"], "1.0.1")
        self.assertEqual(self.service["schema_version"], "1.1")
        self.assertEqual(self.data["schema_version"], "1.1")
        self.assertEqual(self.schema["$id"], "urn:studyflow:f1:1.1:integration:1.0.1")

    def test_exact_six_internal_additions_and_security_flags(self):
        self.assertEqual(set(self.internal), OLD_HELPERS | set(NEW_HELPERS))
        self.assertEqual(len(self.service["internal_interfaces"]), 18, "Duplicate or missing internal routine")
        for name, (read_only, signed, data_schema) in NEW_HELPERS.items():
            with self.subTest(rpc=name):
                entry = self.helper(name)
                self.assertIs(entry["read_only"], read_only)
                self.assertIs(entry["attestation_required"], signed)
                self.assertIs(entry["llm_callable"], False)
                self.assertEqual(entry["result_schema"], f"{name}InternalResult")
                self.definition(entry["arguments_schema"])
                self.definition(entry["result_schema"])
                if data_schema:
                    self.assertEqual(entry["data_schema"], data_schema)

    def test_public_routes_operations_and_business_entities_do_not_expand(self):
        actual_endpoints = {(method, path) for path, operations in self.api["paths"].items()
                            for method in operations if method in {"get", "post", "put", "patch", "delete", "options", "head"}}
        self.assertEqual(actual_endpoints, PUBLIC_ENDPOINTS)
        self.assertEqual({entry["operation"] for entry in self.service["operations"]}, PUBLIC_OPERATIONS)
        self.assertEqual(len(self.service["operations"]), 10)
        self.assertEqual(set(self.defs["Operation"]["enum"]), PUBLIC_OPERATIONS)
        self.assertEqual(len(self.data["entities"]), 10)
        command_operations = {branch["properties"]["operation"]["const"] for branch in self.defs["ValidatedCommand"]["oneOf"]}
        self.assertEqual(command_operations, PUBLIC_OPERATIONS)
        action_operations = {branch["properties"]["operation"]["const"] for branch in self.defs["ActionRequest"]["oneOf"]}
        self.assertEqual(action_operations, {"create_task_candidate", "set_availability", "set_busy_interval", "set_scheduling_preferences", "generate_study_plan"})

    def test_continuation_is_infrastructure_with_exact_mapping(self):
        entries = [entry for entry in self.data["infrastructure_records"] if entry["schema"] == "WorkflowContinuationRecord"]
        self.assertEqual(len(entries), 1, "Continuation infrastructure mapping not implemented")
        entry = entries[0]
        self.assertEqual(entry["table"], "app_private.workflow_continuations")
        self.assertEqual(entry["primary_key"], ["user_id", "source_message_id"])
        columns = {column["name"]: column for column in entry["columns"]}
        self.assertEqual(set(columns), RECORD_KEYS)
        for name in RECORD_KEYS:
            self.assertIs(columns[name]["nullable"], name == "awaiting_reference", name)
        for name in ("version", "cursor"):
            self.assertEqual(columns[name]["postgres_type"], "bigint")
        for name in ("extraction", "depends_on", "awaiting_reference", "completed_steps"):
            self.assertEqual(columns[name]["postgres_type"], "jsonb")

    def test_all_helper_argument_keys_are_required_and_objects_closed(self):
        for name, payload in self.arguments().items():
            with self.subTest(rpc=name):
                schema_name = self.helper(name)["arguments_schema"]
                self.valid(schema_name, payload)
                self.invalid(schema_name, {**payload, "user_id": SOURCE}, semantic=False)
                for key in payload:
                    incomplete = copy.deepcopy(payload)
                    del incomplete[key]
                    self.invalid(schema_name, incomplete, semantic=False)

    def test_continuation_record_is_closed_and_fully_required(self):
        record = read(FIXTURES / "continuation_valid.json")
        self.assertEqual(set(record), RECORD_KEYS)
        self.valid("WorkflowContinuationRecord", record)
        self.invalid("WorkflowContinuationRecord", {**record, "approved": True}, semantic=False)
        for key in RECORD_KEYS:
            with self.subTest(missing=key):
                incomplete = copy.deepcopy(record)
                del incomplete[key]
                self.invalid("WorkflowContinuationRecord", incomplete, semantic=False)

    def test_workflow_context_closed_required_shape(self):
        value = {"conversation_id": CONVERSATION, "active_action": None, "selected_action": None,
                 "source_message": None, "read_at": "2026-11-05T03:00:00Z"}
        self.valid("WorkflowContextData", value)
        self.invalid("WorkflowContextData", {**value, "conversation_history": []}, semantic=False)
        for key in value:
            incomplete = dict(value)
            del incomplete[key]
            self.invalid("WorkflowContextData", incomplete, semantic=False)

    def test_receipt_binding_rejects_missing_fence_and_caller_fields(self):
        binding = read(FIXTURES / "checkpoint_wait_valid.json")["receipt_binding"]
        self.valid("ActiveApiReceiptBinding", binding)
        for changes in ({"expected_lease_version": 0}, {"expected_lease_version": True},
                        {"request_fingerprint": "bad"}, {"idempotency_key": "short"},
                        {"http_operation": "confirm_task"}, {"principal": {"user_id": SOURCE}}):
            with self.subTest(changes=changes):
                self.invalid("ActiveApiReceiptBinding", {**binding, **changes}, semantic=False)
        incomplete = dict(binding)
        del incomplete["expected_lease_version"]
        self.invalid("ActiveApiReceiptBinding", incomplete, semantic=False)

    def test_wait_and_advance_are_distinct_closed_unions(self):
        name = self.helper("checkpoint_workflow_continuation")["arguments_schema"]
        wait = read(FIXTURES / "checkpoint_wait_valid.json")
        advance = read(FIXTURES / "checkpoint_advance_valid.json")
        self.valid(name, wait)
        self.valid(name, advance)
        self.invalid(name, read(FIXTURES / "checkpoint_wait_invalid_outcome.json"), semantic=False)
        for invalid in ({**wait, "action_reference": None}, {**advance, "outcome": None},
                        {**advance, "transition": "EXECUTE"}, {**wait, "expected_cursor": -1},
                        {**wait, "expected_version": 0}):
            self.invalid(name, invalid, semantic=False)

    def test_advance_outcome_index_matches_checkpoint_cursor(self):
        name = self.helper("checkpoint_workflow_continuation")["arguments_schema"]
        invalid = read(FIXTURES / "checkpoint_advance_valid.json")
        invalid["outcome"]["intent_index"] = 1
        self.invalid(name, invalid)

    def test_continuation_cursor_and_completed_prefix_are_consistent(self):
        self.invalid("WorkflowContinuationRecord", read(FIXTURES / "continuation_invalid_cursor.json"))
        record = read(FIXTURES / "continuation_valid.json")
        for cursor in (1, 2):
            with self.subTest(cursor=cursor):
                self.invalid("WorkflowContinuationRecord", {**record, "cursor": cursor})
        outcome = read(FIXTURES / "checkpoint_advance_valid.json")["outcome"]
        record.update(cursor=1, completed_steps=[outcome])
        self.valid("WorkflowContinuationRecord", record)
        record["completed_steps"][0]["intent_index"] = 1
        self.invalid("WorkflowContinuationRecord", record)

    def test_dependencies_only_reference_distinct_earlier_intents(self):
        for depends_on in ([[]], [[1], []], [[0], [0]], [[], [1]], [[], [0, 0]], [[], [-1]]):
            with self.subTest(depends_on=depends_on):
                record = read(FIXTURES / "continuation_valid.json")
                record["depends_on"] = depends_on
                self.invalid("WorkflowContinuationRecord", record)
                arguments = self.arguments()["initialize_workflow_continuation"]
                arguments["depends_on"] = depends_on
                self.invalid(self.helper("initialize_workflow_continuation")["arguments_schema"], arguments)

    def test_initializer_restricts_origin_receipt_operation(self):
        name = self.helper("initialize_workflow_continuation")["arguments_schema"]
        for operation in ("review_action", "submit_decision"):
            payload = self.arguments()["initialize_workflow_continuation"]
            payload["receipt_binding"]["http_operation"] = operation
            self.invalid(name, payload)

    def test_helpers_have_exact_declared_result_data_and_outcomes(self):
        record = read(FIXTURES / "continuation_valid.json")
        profile = read(CONTRACTS / "examples/valid/User.json")
        values = {
            "ensure_user_context": profile,
            "list_time_windows": {"items": [], "next_cursor": None},
            "get_workflow_context": {"conversation_id": CONVERSATION, "active_action": None, "selected_action": None, "source_message": None, "read_at": "2026-11-05T03:00:00Z"},
            "get_workflow_continuation": {"continuation": record},
            "initialize_workflow_continuation": record,
            "checkpoint_workflow_continuation": record,
        }
        for name, data in values.items():
            with self.subTest(rpc=name):
                schema_name = self.helper(name)["result_schema"]
                outcome = "READ" if NEW_HELPERS[name][0] else "COMMITTED"
                result = {"schema_version": "1.1", "request_id": "sol-addendum", "outcome": outcome,
                          "data": data, "error": None, "warnings": []}
                self.valid(schema_name, result)
                self.invalid(schema_name, {**result, "outcome": "COMMITTED" if outcome == "READ" else "READ"}, semantic=False)
                self.invalid(schema_name, {**result, "data": {"unapproved": True}}, semantic=False)
        empty = {"schema_version": "1.1", "request_id": "sol-addendum", "outcome": "READ",
                 "data": {"continuation": None}, "error": None, "warnings": []}
        self.valid(self.helper("get_workflow_continuation")["result_schema"], empty)

    def test_all_helper_envelopes_use_101_and_signed_writers(self):
        for name, (read_only, signed, _) in NEW_HELPERS.items():
            with self.subTest(rpc=name):
                envelope = self.rpc(name)
                self.valid("RpcRequest", envelope)
                self.invalid("RpcRequest", {**envelope, "contract_version": "1.0.0"}, semantic=False)
                if signed:
                    self.invalid("RpcRequest", {**envelope, "attestation": None}, semantic=False)
                else:
                    bad = copy.deepcopy(envelope)
                    bad["attestation"] = {"key_id": "fake", "payload": "shape", "signature": "0" * 64}
                    self.invalid("RpcRequest", bad, semantic=False)
                    bad = copy.deepcopy(envelope)
                    bad["execution_context"]["idempotency_key"] = "sol-addendum-0001"
                    self.invalid("RpcRequest", bad, semantic=False)
        # First GET bootstrap is a signed helper with no invented domain key.
        self.assertIsNone(self.rpc("ensure_user_context")["execution_context"]["idempotency_key"])

    def test_shared_bundle_is_valid_json_schema(self):
        Draft202012Validator.check_schema(self.schema)


if __name__ == "__main__":
    unittest.main()
