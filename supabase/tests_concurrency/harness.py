"""Real local PostgreSQL fixtures; no runtime adapters or mocked DB responses."""
from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
import os
from pathlib import Path
import queue
import secrets
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.check_contract import validate_instance  # noqa: E402

VERSION = "1.0.1"
UTC = timezone.utc


def uid():
    return str(uuid4())


def stamp(value=None):
    return (value or datetime.now(UTC)).isoformat().replace("+00:00", "Z")


def canonical(value):
    """Independent signer; the SQL implementation is never used to sign."""
    def check(item):
        if item is None or type(item) in (str, bool):
            return
        if type(item) is int and abs(item) <= 9007199254740991:
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                check(child)
            return
        raise ValueError("canonical signing accepts JSON-safe integers, never floats")
    check(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def local_dsn():
    raw = os.environ.get("F1_DB_TEST_DSN")
    if not raw:
        raise RuntimeError("F1_DB_TEST_DSN is required; use an ephemeral local Supabase PostgreSQL DSN. No tests were executed.")
    options = conninfo_to_dict(raw)
    host = options.get("host", "")
    if options.get("service") or host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("F1_DB_TEST_DSN must explicitly select one localhost/127.0.0.1/::1 host; service files, sockets and remote/multi-host DSNs are rejected")
    if options.get("hostaddr") not in (None, "127.0.0.1", "::1"):
        raise RuntimeError("F1_DB_TEST_DSN hostaddr must also be loopback")
    # Explicit hostaddr prevents environment overrides and DNS forwarding.
    return make_conninfo(raw, hostaddr="::1" if host == "::1" else "127.0.0.1", connect_timeout=5)


@dataclass(frozen=True)
class Call:
    operation: str
    arguments: dict
    conversation: str | None
    message: str
    key: str | None
    approval: dict | None = None
    reference: dict | None = None
    request_id: str | None = None


class Database:
    def __init__(self):
        self.dsn = local_dsn()
        self.schema = json.loads((ROOT / "contracts/schemas/f1.schema.json").read_text(encoding="utf-8"))
        registry = json.loads((ROOT / "contracts/service-contract.json").read_text(encoding="utf-8"))
        if registry["contract_version"] != VERSION:
            raise RuntimeError("WP0 approved contract 1.0.1 must be synchronized before concurrency acceptance; refusing an older contract")
        self.defs = self.schema["$defs"]
        self.registry = {row["rpc"]: row for row in registry["operations"] if row.get("rpc")}
        self.registry.update({row["rpc"]: row for row in registry["internal_interfaces"]})
        self.admin = psycopg.connect(self.dsn, autocommit=True)
        self.key_id = "sol-concurrency-" + uid()
        self.secret = secrets.token_bytes(32)
        self.admin.execute("insert into app_private.rpc_attestation_keys(key_id,key_material,not_before,not_after) values (%s,%s,clock_timestamp()-interval '1 minute',clock_timestamp()+interval '2 hours')", (self.key_id, self.secret))

    def close(self):
        self.admin.close()

    def validate(self, name, value, *, semantic=True):
        errors = validate_instance(self.defs, name, value, semantic=semantic)
        if errors:
            raise AssertionError(f"{name} contract failure: {errors[:4]}")

    def envelope(self, fixture, call):
        row = self.registry[call.operation]
        now = datetime.now(UTC)
        request_id = call.request_id or uid()
        request = {
            "contract_version": VERSION, "schema_version": "1.1", "request_id": request_id,
            "operation": call.operation, "arguments": copy.deepcopy(call.arguments),
            "execution_context": {
                "trusted_context": {"request_id": request_id, "message_id": call.message,
                    "principal": {"user_id": fixture.owner}, "received_at": stamp(now),
                    "timezone": fixture.profile.get("timezone", "Asia/Ho_Chi_Minh"),
                    "locale": fixture.profile.get("locale", "vi-VN")},
                "conversation_id": call.conversation, "idempotency_key": call.key,
                "approval_action": call.approval, "action_reference": call.reference},
        }
        if not row["read_only"]:
            payload = {"v": 1, "key_id": self.key_id, "user_id": fixture.owner,
                "rpc": call.operation, "request_id": request_id,
                "request_digest": hashlib.sha256(canonical(request).encode()).hexdigest(),
                "issued_at": stamp(now), "expires_at": stamp(now + timedelta(seconds=60))}
            encoded = base64.urlsafe_b64encode(canonical(payload).encode()).decode().rstrip("=")
            request["attestation"] = {"key_id": self.key_id, "payload": encoded,
                "signature": hmac.new(self.secret, encoded.encode("ascii"), hashlib.sha256).hexdigest()}
        else:
            request["attestation"] = None
        self.validate("RpcRequest", request, semantic=False)
        return request

    def invoke(self, fixture, call, connection=None):
        own_connection = connection is None
        connection = connection or psycopg.connect(self.dsn)
        try:
            with connection.transaction():
                connection.execute("set local role authenticated")
                connection.execute("set local lock_timeout='10s'")
                connection.execute("set local statement_timeout='20s'")
                connection.execute("select set_config('request.jwt.claims',%s,true),set_config('request.jwt.claim.sub',%s,true)",
                    (json.dumps({"sub": fixture.owner, "role": "authenticated"}), fixture.owner))
                # Construct and HMAC-sign immediately before SQL, after any start barrier.
                request = self.envelope(fixture, call)
                result = connection.execute(sql.SQL("select app_api.{}(%s)").format(sql.Identifier(call.operation)), (Jsonb(request),)).fetchone()[0]
                self.validate(self.registry[call.operation]["result_schema"], result)
                if result["request_id"] != request["request_id"]:
                    raise AssertionError("RPC must return the current request_id, including replay")
                return result
        finally:
            if own_connection:
                connection.close()

    def success(self, fixture, call, outcome):
        result = self.invoke(fixture, call)
        if result["outcome"] != outcome:
            raise AssertionError(f"{call.operation}: expected {outcome}, got {result}")
        return result["data"]

    def race(self, fixture, calls):
        """Both requests must demonstrably queue behind the owner's row lock."""
        if len(calls) != 2:
            raise ValueError("race requires exactly two independent request sessions")
        pids = queue.Queue()
        barrier = threading.Barrier(3)

        def worker(call):
            with psycopg.connect(self.dsn) as connection:
                pids.put(connection.info.backend_pid)
                barrier.wait(timeout=8)
                return self.invoke(fixture, call, connection)

        with psycopg.connect(self.dsn) as holder, ThreadPoolExecutor(max_workers=2) as pool:
            holder.execute("select user_id from app_private.user_profiles where user_id=%s for update", (fixture.owner,))
            holder_pid = holder.info.backend_pid
            futures = [pool.submit(worker, call) for call in calls]
            observations = []
            try:
                worker_pids = [pids.get(timeout=5), pids.get(timeout=5)]
                barrier.wait(timeout=8)
                until = time.monotonic() + 6
                while time.monotonic() < until:
                    graph = {pid: self.admin.execute("select pg_blocking_pids(%s)", (pid,)).fetchone()[0]
                        for pid in worker_pids}

                    def reaches_holder(pid, seen=None):
                        if pid == holder_pid:
                            return True
                        seen = (seen or set()) | {pid}
                        return any(reaches_holder(parent, seen) for parent in graph.get(pid, []) if parent not in seen)

                    if all(reaches_holder(pid) for pid in worker_pids):
                        observations = graph
                        break
                    if any(future.done() for future in futures):
                        break
                    time.sleep(0.025)  # Poll cadence; the lock graph is the evidence.
                if not observations:
                    raise AssertionError(f"both authenticated sessions did not queue on owner row lock: {graph}")
                print("OWNER_LOCK_BARRIER", json.dumps({"holder": holder_pid, "workers": worker_pids, "blocking": observations}), flush=True)
            finally:
                # Release before joining workers, including all failure paths.
                holder.rollback()
            return [future.result(timeout=25) for future in futures]

    def snapshot(self, owner):
        tables = self.admin.execute("select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace join pg_attribute a on a.attrelid=c.oid where n.nspname='app_private' and c.relkind in ('r','p') and a.attname='user_id' and not a.attisdropped order by c.relname").fetchall()
        return {table: self.admin.execute(sql.SQL("select coalesce(jsonb_agg(v order by v::text),'[]'::jsonb) from (select to_jsonb(t) v from app_private.{} t where user_id=%s) x").format(sql.Identifier(table)), (owner,)).fetchone()[0] for (table,) in tables}


class Fixture:
    """Synthetic backend caller; every business setup write uses approved RPCs."""
    def __init__(self, db):
        self.db = db
        self.owner = uid()
        self.profile = {}
        self.start = (datetime.now(UTC) + timedelta(days=2)).replace(hour=6, minute=0, second=0, microsecond=0)
        db.admin.execute("insert into auth.users(id) values (%s)", (self.owner,))
        self.profile = db.success(self, Call("ensure_user_context", {}, None, uid(), None), "COMMITTED")

    def key(self):
        return "sol-concurrency-" + uid()

    def source(self, text="Synthetic independent acceptance"):
        conversation, message = uid(), uid()
        args = {"message": {"message_id": message, "user_id": self.owner,
            "conversation_id": conversation, "source": "UI", "role": "USER",
            "text": text, "received_at": stamp()}}
        self.db.success(self, Call("record_source_message", args, conversation, message, self.key()), "COMMITTED")
        return conversation, message

    def profile_now(self):
        self.profile = self.db.success(self, Call("ensure_user_context", {}, None, uid(), None), "COMMITTED")
        return self.profile

    def prepare(self, operation, arguments, *, intent, target_type, target=None,
                candidate=None, proposal=None, policy=None, source=None):
        conversation, message = source or self.source()
        action = uid()
        target_id = target[0] if target else action
        target_version = target[1] if target else 1
        pending = {"action_id": action, "user_id": self.owner, "conversation_id": conversation,
            "version": 1, "intent": intent,
            "state": "AWAITING_APPROVAL" if proposal else "AWAITING_CONFIRMATION",
            "requires_review": False, "candidate_id": candidate["candidate_id"] if candidate else None,
            "proposal_id": proposal["proposal_id"] if proposal else None,
            "draft_arguments": {"slots": candidate["slots"]} if candidate else copy.deepcopy(arguments),
            "missing_fields": [], "ambiguities": [], "depends_on_action_id": None,
            "created_at": stamp(), "updated_at": stamp()}
        presentation = {"kind": "ACTION_PRESENTATION", "pending_action": pending,
            "candidate": candidate, "proposal": proposal, "normalized_command": {
                "schema_version": "1.1", "operation": operation, "arguments": arguments},
            "effective_policy": policy}
        stored = self.db.success(self, Call("prepare_pending_action", {"presentation": presentation,
            "expected_action_version": None}, conversation, message, self.key()), "COMMITTED")
        reference = {"action_id": stored["pending_action"]["action_id"],
            "action_version": stored["pending_action"]["version"], "target_type": target_type,
            "target_id": target_id, "target_version": target_version}
        approval = {"approval_action_id": uid(), "user_id": self.owner, "target_type": target_type,
            "target_id": target_id, "target_version": target_version, "decision": "APPROVE",
            "source": "UI", "source_message_id": None, "created_at": stamp()}
        return Call(operation, arguments, conversation, message, self.key(), approval, reference)

    def candidate(self, minutes=120):
        source = self.source("Create a 120 minute task")
        slots = {"title": "Independent concurrency task 🧠", "description": None,
            "course_label": None, "available_from_at": None,
            "deadline_at": stamp(self.start + timedelta(days=2)), "deadline_precision": "DATETIME",
            "deadline_date": None, "deadline_timezone": "UTC", "estimated_minutes": minutes,
            "priority": "NORMAL"}
        candidate = self.db.success(self, Call("create_task_candidate", {"slots": slots}, *source, self.key()), "DRAFTED")
        arguments = {"candidate_id": candidate["candidate_id"], "expected_candidate_version": candidate["version"]}
        call = self.prepare("confirm_task", arguments, intent="CREATE_TASK", target_type="TASK_CANDIDATE",
            target=(candidate["candidate_id"], candidate["version"]), candidate=candidate, source=source)
        return candidate, call

    def confirmed_task(self):
        _, call = self.candidate()
        return self.db.success(self, call, "COMMITTED")

    def availability(self):
        args = {"change_type": "ADD", "window_id": None, "expected_window_version": None,
            "window": {"kind": "AVAILABILITY", "label": "Acceptance availability", "recurrence": "NONE",
                "timezone": "UTC", "start_at": stamp(self.start), "end_at": stamp(self.start + timedelta(hours=6)),
                "weekday": None, "start_time": None, "end_time": None, "valid_from": None, "valid_until": None}}
        call = self.prepare("set_availability", args, intent="SET_AVAILABILITY", target_type="PENDING_ACTION")
        return self.db.success(self, call, "COMMITTED")

    def policy_change(self):
        profile = self.profile_now()
        policy = {**profile["scheduling_policy"], "break_minutes": profile["scheduling_policy"]["break_minutes"] + 1}
        args = {"policy_patch": {"break_minutes": policy["break_minutes"]},
            "expected_schedule_revision": profile["schedule_revision"]}
        call = self.prepare("set_scheduling_preferences", args, intent="SET_SCHEDULING_PREFERENCES",
            target_type="PENDING_ACTION", policy=policy)
        return self.db.success(self, call, "COMMITTED")

    def proposal(self, task, offset=0):
        source = self.source("Generate and present a complete study plan")
        scope = {"start_at": stamp(self.start), "end_at": stamp(self.start + timedelta(hours=6)),
            "selection_mode": "SELECTED_TASKS", "task_ids": [task["task_id"]]}
        snapshot = self.db.success(self, Call("get_scheduling_context", {"generation_scope": scope},
            None, uid(), None), "READ")
        base = snapshot["base_plan"]["plan"]
        if base is not None:
            raise AssertionError("minimal concurrency proposal fixture expects no current plan")
        blocks = [{"block_id": uid(), "user_id": self.owner, "task_id": task["task_id"],
            "start_at": stamp(self.start + timedelta(minutes=offset + index * 70)),
            "end_at": stamp(self.start + timedelta(minutes=offset + index * 70 + 60)),
            "is_locked": False} for index in range(2)]
        proposal = {"proposal_id": uid(), "user_id": self.owner, "version": 1, "status": "PROPOSED",
            "base_plan_id": None, "base_plan_version": None, "base_schedule_revision": snapshot["schedule_revision"],
            "generation_scope": scope, "payload": {"study_blocks": blocks, "task_summaries": [{
                "task_id": task["task_id"], "remaining_minutes": 120, "retained_future_minutes": 0,
                "newly_scheduled_minutes": 120, "unallocated_minutes": 0, "reason_codes": []}],
                "coverage": "FULL", "warnings": [], "plan_diff": {"added": [b["block_id"] for b in blocks],
                    "moved": [], "removed": [], "unchanged": []}},
            "algorithm_version": "sol-known-valid-fixture-v1", "policy_snapshot": snapshot["user"]["scheduling_policy"],
            "generated_at": stamp(), "committed_plan_id": None, "created_at": stamp(), "updated_at": stamp()}
        self.db.validate("PlanProposal", proposal)
        stored = self.db.success(self, Call("persist_plan_proposal", {"command_arguments": {
            "generation_scope": scope, "policy_overrides": {}}, "proposal": proposal}, *source, self.key()), "PROPOSED")
        args = {"proposal_id": stored["proposal_id"], "expected_proposal_version": stored["version"], "expected_plan_version": None}
        approval = self.prepare("approve_study_plan", args, intent="GENERATE_STUDY_PLAN", target_type="PLAN_PROPOSAL",
            target=(stored["proposal_id"], stored["version"]), proposal=stored,
            policy=stored["policy_snapshot"], source=source)
        return stored, approval
