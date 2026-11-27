#!/usr/bin/env python3
"""Load, Throughput (RPS), CCU Ramp & Breaking-Point Benchmark for StudyFlow AI F1.

Measures 4 realistic tiers strictly against loopback local stack (FastAPI + Local Supabase)
and in-process deterministic scheduler:
  - Tier A: Read Path Step-Load (GET /v1/tasks, /v1/plans?view=CURRENT, /v1/time-windows)
  - Tier B: Write & Decision Commit Step-Load (POST /v1/actions -> POST /v1/decisions)
  - Tier C: Live Chat NLU Concurrency Ramp (POST /v1/messages with real DeepSeek API)
  - Tier D: Deterministic Scheduler Scale Stress (5 -> 200 tasks, 14-day horizon)

Refuses non-loopback URLs or forbidden cloud project refs.
"""

from __future__ import annotations

import argparse
import asyncio
import ctypes
import json
import math
import os
import pathlib
import secrets
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import httpx

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.f1.scheduler.evaluation import evaluate_context
from backend.app.f1.scheduler.models import (
    AcademicTask,
    GenerationScope,
    Interval,
    Priority,
    SchedulingContext,
    SchedulingPolicy,
    SelectionMode,
)

FORBIDDEN_PROJECT_REF = "phomrutsdhdgejlskwcb"
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def assert_safe_local_url(url: str, label: str) -> None:
    if FORBIDDEN_PROJECT_REF in url:
        raise SystemExit(f"[BLOCKED] Refusing to run against forbidden cloud project in {label}: {url}")
    host = (urlparse(url).hostname or "").lower()
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit(f"[BLOCKED] {label} must target loopback (127.0.0.1/localhost), got: {url}")


def load_env_file(path: pathlib.Path | None) -> dict[str, str]:
    values: dict[str, str] = {}
    if path is None or not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def discover_supabase_local_env() -> dict[str, str]:
    try:
        proc = subprocess.run(
            ["supabase", "status", "-o", "env"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if proc.returncode != 0:
            return {}
        out: dict[str, str] = {}
        for raw in proc.stdout.splitlines():
            line = raw.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
        return out
    except Exception:
        return {}


def get_host_metadata() -> dict[str, Any]:
    logical_cpus = os.cpu_count() or 0
    total_ram_gb = None
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):  # type: ignore[attr-defined]
            total_ram_gb = round(stat.ullTotalPhys / (1024 ** 3), 2)
    except Exception:
        total_ram_gb = None
    git_sha = "unknown"
    try:
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            git_sha = proc.stdout.strip()
    except Exception:
        pass
    return {
        "git_sha": git_sha,
        "logical_cpus": logical_cpus,
        "total_ram_gb": total_ram_gb,
        "topology": "1 Uvicorn worker + Local Supabase Docker on Windows loopback",
    }


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
    return round(ordered[idx], 2)


def summarize_latencies(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "max_ms": 0.0}
    return {
        "mean_ms": round(sum(values) / len(values), 2),
        "p50_ms": percentile(values, 0.50),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
        "max_ms": round(max(values), 2),
    }


async def create_user_pool(
    supa_http: httpx.AsyncClient, pub_key: str, svc_key: str, count: int
) -> list[str]:
    sem = asyncio.Semaphore(10)

    async def make_one(idx: int) -> str:
        async with sem:
            email = f"f1-load-{idx}-{uuid4().hex[:8]}@example.test"
            password = secrets.token_urlsafe(16)
            r1 = await supa_http.post(
                "/auth/v1/admin/users",
                headers={"apikey": svc_key, "Authorization": f"Bearer {svc_key}"},
                json={"email": email, "password": password, "email_confirm": True},
            )
            if r1.status_code not in (200, 201):
                raise RuntimeError(f"Admin user creation failed: {r1.status_code} {r1.text[:200]}")
            r2 = await supa_http.post(
                "/auth/v1/token?grant_type=password",
                headers={"apikey": pub_key},
                json={"email": email, "password": password},
            )
            if r2.status_code != 200:
                raise RuntimeError(f"Token grant failed: {r2.status_code} {r2.text[:200]}")
            return r2.json()["access_token"]

    return await asyncio.gather(*(make_one(i) for i in range(count)))


async def seed_user_planner_data(
    api_http: httpx.AsyncClient, token: str, now_vn: datetime
) -> None:
    conv = str(uuid4())
    hdrs_base = {"Authorization": f"Bearer {token}"}

    async def act_and_approve(operation: str, arguments: dict) -> None:
        r_act = await api_http.post(
            "/v1/actions",
            headers={**hdrs_base, "Idempotency-Key": f"load-seed-act-{uuid4().hex}"},
            json={
                "schema_version": "1.1",
                "conversation_id": conv,
                "operation": operation,
                "arguments": arguments,
            },
        )
        if r_act.status_code != 200:
            raise RuntimeError(f"Seed action {operation} failed: {r_act.status_code} {r_act.text[:200]}")
        ref = r_act.json()["action_reference"]
        r_dec = await api_http.post(
            "/v1/decisions",
            headers={**hdrs_base, "Idempotency-Key": f"load-seed-dec-{uuid4().hex}"},
            json={
                "schema_version": "1.1",
                "conversation_id": conv,
                "action_reference": ref,
                "decision": "APPROVE",
            },
        )
        if r_dec.status_code != 200:
            raise RuntimeError(f"Seed decision {operation} failed: {r_dec.status_code} {r_dec.text[:200]}")

    t1_start = (now_vn + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    t1_end = (now_vn + timedelta(days=1)).replace(hour=23, minute=59, second=0, microsecond=0)
    t2_start = (now_vn + timedelta(days=2)).replace(hour=14, minute=0, second=0, microsecond=0)
    t2_end = (now_vn + timedelta(days=2)).replace(hour=23, minute=59, second=0, microsecond=0)
    busy_s = (now_vn + timedelta(days=1)).replace(hour=13, minute=0, second=0, microsecond=0)
    busy_e = (now_vn + timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)

    await act_and_approve("create_task_candidate", {
        "slots": {
            "title": "Ôn Giải tích 1",
            "start_at": t1_start.isoformat(),
            "estimated_minutes": 60,
            "priority": 1,
            "deadline_timezone": "Asia/Ho_Chi_Minh",
            "deadline_precision": "DATETIME",
            "deadline_at": t1_end.isoformat(),
        }
    })
    await act_and_approve("create_task_candidate", {
        "slots": {
            "title": "Làm bài tập Cấu trúc dữ liệu",
            "start_at": t2_start.isoformat(),
            "estimated_minutes": 90,
            "priority": 0.5,
            "deadline_timezone": "Asia/Ho_Chi_Minh",
            "deadline_precision": "DATETIME",
            "deadline_at": t2_end.isoformat(),
        }
    })
    await act_and_approve("set_busy_interval", {
        "change_type": "ADD",
        "window_id": None,
        "expected_window_version": None,
        "window": {
            "kind": "BUSY",
            "label": "Học trên lớp",
            "recurrence": "NONE",
            "timezone": "Asia/Ho_Chi_Minh",
            "start_at": busy_s.isoformat(),
            "end_at": busy_e.isoformat(),
            "weekday": None,
            "start_time": None,
            "end_time": None,
            "valid_from": None,
            "valid_until": None,
        },
    })
    scope_s = (now_vn + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
    scope_e = (now_vn + timedelta(days=3)).replace(hour=22, minute=0, second=0, microsecond=0)
    await act_and_approve("generate_study_plan", {
        "generation_scope": {
            "start_at": scope_s.isoformat(),
            "end_at": scope_e.isoformat(),
            "selection_mode": "ALL_ELIGIBLE",
            "task_ids": [],
        },
        "policy_overrides": {},
    })


async def run_tier_a_read_load(
    api_http: httpx.AsyncClient,
    read_tokens: list[str],
    ccu_steps: list[int],
    duration_s: float,
) -> dict[str, Any]:
    print("\n--- Tier A: Read Path Step-Load (/v1/tasks, /v1/plans?view=CURRENT, /v1/time-windows) ---")
    paths = [
        ("/v1/tasks", None),
        ("/v1/plans", {"view": "CURRENT"}),
        ("/v1/time-windows", None),
    ]
    results: list[dict[str, Any]] = []
    peak_rps = 0.0
    breaking_point: dict[str, Any] | None = None

    # Warmup 1 step so connections are open
    await api_http.get("/v1/tasks", headers={"Authorization": f"Bearer {read_tokens[0]}"})

    for ccu in ccu_steps:
        latencies: list[float] = []
        statuses: Counter[str] = Counter()
        stop_at = time.perf_counter() + duration_s

        async def worker(wid: int) -> None:
            tok = read_tokens[wid % len(read_tokens)]
            hdr = {"Authorization": f"Bearer {tok}"}
            i = wid
            while time.perf_counter() < stop_at:
                path, params = paths[i % len(paths)]
                i += 1
                t0 = time.perf_counter()
                try:
                    resp = await api_http.get(path, headers=hdr, params=params)
                    ms = (time.perf_counter() - t0) * 1000.0
                    latencies.append(ms)
                    statuses[str(resp.status_code)] += 1
                except httpx.TimeoutException:
                    latencies.append((time.perf_counter() - t0) * 1000.0)
                    statuses["timeout"] += 1
                except Exception as exc:
                    latencies.append((time.perf_counter() - t0) * 1000.0)
                    statuses[f"err:{type(exc).__name__}"] += 1

        t_wall0 = time.perf_counter()
        await asyncio.gather(*(worker(w) for w in range(ccu)))
        wall_s = max(0.001, time.perf_counter() - t_wall0)

        total = sum(statuses.values())
        ok_2xx = sum(v for k, v in statuses.items() if k.startswith("2"))
        err_cnt = total - ok_2xx
        err_pct = round((err_cnt / total * 100.0) if total else 100.0, 2)
        rps = round(ok_2xx / wall_s, 2)
        stats = summarize_latencies(latencies)
        peak_rps = max(peak_rps, rps)

        reasons: list[str] = []
        if err_pct > 1.0:
            reasons.append(f"error_rate={err_pct}% > 1%")
        if stats["p95_ms"] > 1000.0:
            reasons.append(f"P95={stats['p95_ms']}ms > 1000ms (Read SLO)")
        if ccu >= 20 and peak_rps > 0 and rps < peak_rps * 0.90:
            reasons.append(f"RPS dropped >10% from peak ({rps} vs peak {peak_rps})")

        if breaking_point is None and reasons:
            breaking_point = {"ccu": ccu, "rps_at_break": rps, "p95_ms": stats["p95_ms"], "error_rate_pct": err_pct, "reasons": reasons}

        step = {
            "ccu": ccu,
            "duration_s": round(wall_s, 2),
            "total_requests": total,
            "success_2xx": ok_2xx,
            "error_rate_pct": err_pct,
            "rps": rps,
            "status_counts": dict(statuses),
            **stats,
        }
        results.append(step)
        print(f"CCU={ccu:>3} | req={total:>5} | 2xx={ok_2xx:>5} | err={err_pct:>5.2f}% | RPS={rps:>7.2f} | P50={stats['p50_ms']:>7.1f}ms | P95={stats['p95_ms']:>7.1f}ms | P99={stats['p99_ms']:>7.1f}ms")

        if err_pct >= 25.0 or stats["p95_ms"] > 5000.0:
            print(f"[Tier A stop early at CCU={ccu}: threshold exceeded]")
            break

    return {
        "steps": results,
        "peak_rps": peak_rps,
        "breaking_point": breaking_point,
    }


async def run_tier_b_write_load(
    api_http: httpx.AsyncClient,
    write_tokens: list[str],
    now_vn: datetime,
    ccu_steps: list[int],
    duration_s: float,
) -> dict[str, Any]:
    print("\n--- Tier B: Write & Decision Commit Step-Load (/v1/actions -> /v1/decisions) ---")
    start_iso = (now_vn + timedelta(days=3)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat()
    end_iso = (now_vn + timedelta(days=3)).replace(hour=23, minute=59, second=0, microsecond=0).isoformat()

    results: list[dict[str, Any]] = []
    peak_tx_rps = 0.0
    breaking_point: dict[str, Any] | None = None

    for ccu in ccu_steps:
        act_lat: list[float] = []
        dec_lat: list[float] = []
        tx_lat: list[float] = []
        statuses: Counter[str] = Counter()
        tx_ok = 0
        tx_total = 0
        stop_at = time.perf_counter() + duration_s

        async def worker(wid: int) -> None:
            nonlocal tx_ok, tx_total
            tok = write_tokens[wid % len(write_tokens)]
            hdr_base = {"Authorization": f"Bearer {tok}"}
            while time.perf_counter() < stop_at:
                conv = str(uuid4())
                t_tx0 = time.perf_counter()
                tx_total += 1
                try:
                    t0 = time.perf_counter()
                    r_act = await api_http.post(
                        "/v1/actions",
                        headers={**hdr_base, "Idempotency-Key": f"load-act-{uuid4().hex}"},
                        json={
                            "schema_version": "1.1",
                            "conversation_id": conv,
                            "operation": "create_task_candidate",
                            "arguments": {
                                "slots": {
                                    "title": f"Load Task W{wid}",
                                    "start_at": start_iso,
                                    "estimated_minutes": 45,
                                    "priority": 0.5,
                                    "deadline_timezone": "Asia/Ho_Chi_Minh",
                                    "deadline_precision": "DATETIME",
                                    "deadline_at": end_iso,
                                }
                            },
                        },
                    )
                    act_lat.append((time.perf_counter() - t0) * 1000.0)
                    statuses[f"act:{r_act.status_code}"] += 1
                    if r_act.status_code != 200:
                        tx_lat.append((time.perf_counter() - t_tx0) * 1000.0)
                        continue
                    ref = r_act.json().get("action_reference")
                    if not ref:
                        statuses["act:no_ref"] += 1
                        tx_lat.append((time.perf_counter() - t_tx0) * 1000.0)
                        continue

                    t1 = time.perf_counter()
                    r_dec = await api_http.post(
                        "/v1/decisions",
                        headers={**hdr_base, "Idempotency-Key": f"load-dec-{uuid4().hex}"},
                        json={
                            "schema_version": "1.1",
                            "conversation_id": conv,
                            "action_reference": ref,
                            "decision": "APPROVE",
                        },
                    )
                    dec_lat.append((time.perf_counter() - t1) * 1000.0)
                    statuses[f"dec:{r_dec.status_code}"] += 1
                    tx_lat.append((time.perf_counter() - t_tx0) * 1000.0)
                    if r_dec.status_code == 200:
                        tx_ok += 1
                except httpx.TimeoutException:
                    tx_lat.append((time.perf_counter() - t_tx0) * 1000.0)
                    statuses["tx:timeout"] += 1
                except Exception as exc:
                    tx_lat.append((time.perf_counter() - t_tx0) * 1000.0)
                    statuses[f"tx:{type(exc).__name__}"] += 1

        t_wall0 = time.perf_counter()
        await asyncio.gather(*(worker(w) for w in range(ccu)))
        wall_s = max(0.001, time.perf_counter() - t_wall0)

        err_cnt = tx_total - tx_ok
        err_pct = round((err_cnt / tx_total * 100.0) if tx_total else 100.0, 2)
        tx_rps = round(tx_ok / wall_s, 2)
        http_rps = round((statuses.get("act:200", 0) + statuses.get("dec:200", 0)) / wall_s, 2)
        dec_stats = summarize_latencies(dec_lat)
        act_stats = summarize_latencies(act_lat)
        tx_stats = summarize_latencies(tx_lat)
        peak_tx_rps = max(peak_tx_rps, tx_rps)

        reasons: list[str] = []
        if err_pct > 1.0:
            reasons.append(f"error_rate={err_pct}% > 1%")
        if dec_stats["p95_ms"] > 1500.0:
            reasons.append(f"Decisions P95={dec_stats['p95_ms']}ms > 1500ms (Decision SLO)")
        if ccu >= 10 and peak_tx_rps > 0 and tx_rps < peak_tx_rps * 0.90:
            reasons.append(f"TX RPS dropped >10% from peak ({tx_rps} vs peak {peak_tx_rps})")

        if breaking_point is None and reasons:
            breaking_point = {
                "ccu": ccu,
                "tx_rps_at_break": tx_rps,
                "http_rps_at_break": http_rps,
                "decisions_p95_ms": dec_stats["p95_ms"],
                "error_rate_pct": err_pct,
                "reasons": reasons,
            }

        step = {
            "ccu": ccu,
            "duration_s": round(wall_s, 2),
            "tx_total": tx_total,
            "tx_ok": tx_ok,
            "error_rate_pct": err_pct,
            "tx_rps": tx_rps,
            "http_rps": http_rps,
            "actions": act_stats,
            "decisions": dec_stats,
            "tx_total_latency": tx_stats,
            "status_counts": dict(statuses),
        }
        results.append(step)
        print(
            f"CCU={ccu:>3} | tx={tx_ok:>4}/{tx_total:<4} | err={err_pct:>5.2f}% | "
            f"TX_RPS={tx_rps:>6.2f} (HTTP {http_rps:>6.2f}) | "
            f"Act_P95={act_stats['p95_ms']:>6.1f}ms | Dec_P50={dec_stats['p50_ms']:>6.1f}ms | Dec_P95={dec_stats['p95_ms']:>6.1f}ms"
        )

        if err_pct >= 25.0 or dec_stats["p95_ms"] > 6000.0:
            print(f"[Tier B stop early at CCU={ccu}: threshold exceeded]")
            break

    return {
        "steps": results,
        "peak_tx_rps": peak_tx_rps,
        "breaking_point": breaking_point,
    }


async def run_tier_c_chat_ramp(
    api_http: httpx.AsyncClient,
    chat_tokens: list[str],
    ccu_steps: list[int],
) -> dict[str, Any]:
    print("\n--- Tier C: Live Chat NLU Concurrency Ramp (POST /v1/messages + real DeepSeek) ---")
    prompts = [
        "Ngày mai tôi muốn ôn Giải tích lúc 9h sáng trong 60 phút, ưu tiên cao.",
        "Thứ Sáu 14h học Vật lý 90 phút.",
        "Mai 19h30 học Tiếng Anh 60 phút, ưu tiên vừa.",
        "Sáng mai 8h ôn Xác suất thống kê 45 phút.",
    ]
    results: list[dict[str, Any]] = []
    peak_rps = 0.0
    breaking_point: dict[str, Any] | None = None

    for ccu in ccu_steps:
        latencies: list[float] = []
        statuses: Counter[str] = Counter()

        async def send_one(wid: int) -> None:
            tok = chat_tokens[wid % len(chat_tokens)]
            conv = str(uuid4())
            prompt = prompts[wid % len(prompts)]
            t0 = time.perf_counter()
            try:
                resp = await api_http.post(
                    "/v1/messages",
                    headers={
                        "Authorization": f"Bearer {tok}",
                        "Idempotency-Key": f"load-chat-{uuid4().hex}",
                    },
                    json={"schema_version": "1.1", "conversation_id": conv, "text": prompt},
                    timeout=35.0,
                )
                ms = (time.perf_counter() - t0) * 1000.0
                latencies.append(ms)
                statuses[str(resp.status_code)] += 1
            except httpx.TimeoutException:
                latencies.append((time.perf_counter() - t0) * 1000.0)
                statuses["timeout"] += 1
            except Exception as exc:
                latencies.append((time.perf_counter() - t0) * 1000.0)
                statuses[f"err:{type(exc).__name__}"] += 1

        t_wall0 = time.perf_counter()
        await asyncio.gather(*(send_one(w) for w in range(ccu)))
        wall_s = max(0.001, time.perf_counter() - t_wall0)

        total = sum(statuses.values())
        ok_200 = statuses.get("200", 0)
        err_cnt = total - ok_200
        err_pct = round((err_cnt / total * 100.0) if total else 100.0, 2)
        rps = round(ok_200 / wall_s, 2)
        stats = summarize_latencies(latencies)
        peak_rps = max(peak_rps, rps)

        reasons: list[str] = []
        if err_pct > 1.0:
            reasons.append(f"error_rate={err_pct}% > 1% ({dict(statuses)})")
        if stats["p95_ms"] > 6000.0:
            reasons.append(f"P95={stats['p95_ms']}ms > 6000ms (Chat SLO)")

        if breaking_point is None and reasons:
            breaking_point = {
                "ccu": ccu,
                "rps_at_break": rps,
                "p95_ms": stats["p95_ms"],
                "error_rate_pct": err_pct,
                "reasons": reasons,
                "status_counts": dict(statuses),
            }

        step = {
            "ccu": ccu,
            "wall_s": round(wall_s, 2),
            "total_requests": total,
            "success_200": ok_200,
            "error_rate_pct": err_pct,
            "rps": rps,
            "status_counts": dict(statuses),
            **stats,
        }
        results.append(step)
        print(
            f"CCU={ccu:>2} | wall={wall_s:>5.2f}s | 200={ok_200:>2}/{total:<2} | err={err_pct:>5.1f}% | "
            f"RPS={rps:>5.2f} | P50={stats['p50_ms']:>7.1f}ms | P95={stats['p95_ms']:>7.1f}ms | Max={stats['max_ms']:>7.1f}ms | {dict(statuses)}"
        )

        if err_pct >= 20.0:
            print(f"[Tier C stop early at CCU={ccu}: upstream/error rate >= 20%]")
            break
        await asyncio.sleep(1.0)

    return {
        "steps": results,
        "peak_rps": peak_rps,
        "breaking_point": breaking_point,
    }


def run_tier_d_scheduler_scale(task_counts: list[int], repetitions: int = 30) -> list[dict[str, Any]]:
    print("\n--- Tier D: Deterministic Scheduler Scale Stress (14-day horizon) ---")
    uid = UUID(int=99)
    base_day = datetime(2026, 11, 28, 0, 0, tzinfo=VN_TZ)
    avail = tuple(
        Interval(
            (base_day + timedelta(days=d)).replace(hour=6),
            (base_day + timedelta(days=d)).replace(hour=22),
        )
        for d in range(14)
    )
    busy = tuple(
        Interval(
            (base_day + timedelta(days=d)).replace(hour=12),
            (base_day + timedelta(days=d)).replace(hour=13),
        )
        for d in range(14)
    )
    policy = SchedulingPolicy(min_block_minutes=25, max_block_minutes=90, allow_short_final_block=True, max_daily_minutes=360, break_minutes=10)

    out: list[dict[str, Any]] = []
    for n in task_counts:
        tasks = tuple(
            AcademicTask(
                task_id=UUID(int=1000 + i),
                user_id=uid,
                title=f"Scale Task {i}",
                deadline_at=(base_day + timedelta(days=(i % 13) + 1)).replace(hour=22),
                estimated_minutes=60 + (i % 3) * 30,
                remaining_minutes=60 + (i % 3) * 30,
                priority=[Priority.LOW, Priority.NORMAL, Priority.HIGH][i % 3],
            )
            for i in range(n)
        )
        selected = tuple(t.task_id for t in tasks)
        ctx = SchedulingContext(
            now=base_day.replace(hour=5),
            timezone="Asia/Ho_Chi_Minh",
            generation_scope=GenerationScope(
                base_day.replace(hour=6),
                (base_day + timedelta(days=14)).replace(hour=22),
                SelectionMode.SELECTED_TASKS,
                selected,
            ),
            selected_task_ids=selected,
            tasks=tasks,
            available_intervals=avail,
            busy_intervals=busy,
            retained_blocks=(),
            policy=policy,
        )
        res, met = evaluate_context(ctx, repetitions=repetitions, warmup_repetitions=2)
        plans_per_sec = round(1000.0 / max(1e-6, met.mean_latency_ms), 1)
        row = {
            "task_count": n,
            "repetitions": repetitions,
            "coverage": res.coverage.value,
            "hard_constraint_violations": met.hard_constraint_violations,
            "deterministic": met.deterministic,
            "generated_block_count": met.generated_block_count,
            "scheduled_ratio": round(met.scheduled_ratio, 4),
            "mean_ms": round(met.mean_latency_ms, 3),
            "p50_ms": round(met.latency_p50_ms, 3),
            "p95_ms": round(met.latency_p95_ms, 3),
            "p99_ms": round(met.latency_p99_ms, 3),
            "plans_per_sec": plans_per_sec,
        }
        out.append(row)
        print(
            f"Tasks={n:>3} | blocks={met.generated_block_count:>3} | cov={res.coverage.value:<7} | "
            f"viol={met.hard_constraint_violations} | det={met.deterministic} | "
            f"P50={row['p50_ms']:>6.3f}ms | P95={row['p95_ms']:>6.3f}ms | P99={row['p99_ms']:>6.3f}ms | {plans_per_sec:>7.1f} plans/s"
        )
    return out


def render_markdown(payload: dict[str, Any]) -> str:
    host = payload["host"]
    ta = payload["tier_a_reads"]
    tb = payload["tier_b_writes"]
    tc = payload["tier_c_chat"]
    td = payload["tier_d_scheduler"]

    lines = [
        f"# Báo cáo Kiểm thử Tải, CCU, RPS & Điểm gãy F1 ({payload['timestamp']})",
        "",
        f"- **Commit:** `{host['git_sha']}`",
        f"- **Phần cứng & Topology:** `{host['logical_cpus']} logical CPUs · {host['total_ram_gb']} GB RAM · {host['topology']}`",
        f"- **Cấu hình mục tiêu:** Backend `{payload['api_url']}` · Local Supabase `{payload['supabase_url']}`",
        "",
        "## Tier A — Read Path (`GET /v1/tasks`, `/v1/plans?view=CURRENT`, `/v1/time-windows`)",
        f"- **Peak RPS:** `{ta['peak_rps']} req/s` · **Breaking Point:** `{ta['breaking_point']}`",
        "",
        "| CCU | Thời lượng (s) | Tổng req | 2xx | Lỗi (%) | RPS (req/s) | P50 (ms) | P95 (ms) | P99 (ms) | Max (ms) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in ta["steps"]:
        lines.append(
            f"| {s['ccu']} | {s['duration_s']} | {s['total_requests']} | {s['success_2xx']} | {s['error_rate_pct']}% | **{s['rps']}** | {s['p50_ms']} | {s['p95_ms']} | {s['p99_ms']} | {s['max_ms']} |"
        )

    lines.extend([
        "",
        "## Tier B — Write & Transactional Commit (`POST /v1/actions` -> `POST /v1/decisions`)",
        f"- **Peak TX RPS:** `{tb['peak_tx_rps']} tx/s` · **Breaking Point:** `{tb['breaking_point']}`",
        "",
        "| CCU | Thời lượng (s) | TX OK/Tổng | Lỗi (%) | TX RPS | HTTP RPS | Actions P95 (ms) | Decisions P50 (ms) | Decisions P95 (ms) | Decisions P99 (ms) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])
    for s in tb["steps"]:
        lines.append(
            f"| {s['ccu']} | {s['duration_s']} | {s['tx_ok']}/{s['tx_total']} | {s['error_rate_pct']}% | **{s['tx_rps']}** | {s['http_rps']} | {s['actions']['p95_ms']} | {s['decisions']['p50_ms']} | {s['decisions']['p95_ms']} | {s['decisions']['p99_ms']} |"
        )

    lines.extend([
        "",
        "## Tier C — Live Chat NLU Concurrency (`POST /v1/messages` + DeepSeek)",
        f"- **Peak RPS:** `{tc['peak_rps']} req/s` · **Breaking Point:** `{tc['breaking_point']}`",
        "",
        "| CCU | Wall (s) | 200 OK | Lỗi (%) | RPS (req/s) | P50 (ms) | P95 (ms) | Max (ms) | Chi tiết mã HTTP |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for s in tc["steps"]:
        lines.append(
            f"| {s['ccu']} | {s['wall_s']} | {s['success_200']}/{s['total_requests']} | {s['error_rate_pct']}% | **{s['rps']}** | {s['p50_ms']} | {s['p95_ms']} | {s['max_ms']} | `{s['status_counts']}` |"
        )

    lines.extend([
        "",
        "## Tier D — Deterministic Scheduler Scale Stress (14 ngày, 30 lượt/mốc)",
        "",
        "| Số Task | Số Block sinh | Coverage | Vi phạm cứng | Tất định | Mean (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Thông lượng (plans/s) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])
    for s in td:
        lines.append(
            f"| {s['task_count']} | {s['generated_block_count']} | {s['coverage']} | {s['hard_constraint_violations']} | {s['deterministic']} | {s['mean_ms']} | {s['p50_ms']} | {s['p95_ms']} | {s['p99_ms']} | **{s['plans_per_sec']}** |"
        )
    return "\n".join(lines) + "\n"


async def async_main(args: argparse.Namespace) -> int:
    assert_safe_local_url(args.api_url, "--api-url")
    assert_safe_local_url(args.supabase_url, "--supabase-url")

    env_path = args.env_file
    if env_path is None:
        for candidate in (ROOT / ".env.local", ROOT / ".env", ROOT / "backend" / ".env"):
            if candidate.exists():
                env_path = candidate
                break
    env = load_env_file(env_path)
    supa_cli = discover_supabase_local_env()

    pub_key = (
        env.get("SUPABASE_PUBLISHABLE_KEY")
        or os.environ.get("SUPABASE_PUBLISHABLE_KEY")
        or supa_cli.get("PUBLISHABLE_KEY")
        or supa_cli.get("ANON_KEY")
        or ""
    )
    svc_key = (
        env.get("SUPABASE_SERVICE_KEY")
        or env.get("F1_LOCAL_SERVICE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("F1_LOCAL_SERVICE_KEY")
        or supa_cli.get("SECRET_KEY")
        or supa_cli.get("SERVICE_ROLE_KEY")
        or ""
    )
    if not pub_key or not svc_key:
        raise SystemExit("[BLOCKED] Missing SUPABASE_PUBLISHABLE_KEY / SUPABASE_SERVICE_KEY")

    limits = httpx.Limits(max_connections=250, max_keepalive_connections=80, keepalive_expiry=60.0)
    api_http = httpx.AsyncClient(base_url=args.api_url.rstrip("/"), timeout=httpx.Timeout(40.0), limits=limits)
    supa_http = httpx.AsyncClient(base_url=args.supabase_url.rstrip("/"), timeout=httpx.Timeout(20.0), limits=limits)

    try:
        ping = await api_http.get("/v1/tasks")
        if ping.status_code not in (200, 401):
            raise SystemExit(f"[BLOCKED] Unexpected backend response HTTP {ping.status_code}")

        now_vn = datetime.now(VN_TZ)
        print("Creating 50 real local Supabase test users and seeding Tier A dataset (20 users)...")
        tokens = await create_user_pool(supa_http, pub_key, svc_key, 50)
        for i in range(20):
            await seed_user_planner_data(api_http, tokens[i], now_vn)
        print("User pool & seed complete.")

        tier_a = await run_tier_a_read_load(api_http, tokens[:20], [1, 5, 10, 20, 40, 60, 80, 100], args.step_seconds)
        tier_b = await run_tier_b_write_load(api_http, tokens, now_vn, [1, 5, 10, 20, 30, 50], max(8.0, args.step_seconds))
        tier_c = await run_tier_c_chat_ramp(api_http, tokens[:20], [1, 3, 5, 10, 15, 20])
        tier_d = run_tier_d_scheduler_scale([5, 20, 50, 100, 200], repetitions=30)

        ts = datetime.now(VN_TZ).strftime("%Y%m%d_%H%M%S")
        payload = {
            "timestamp": ts,
            "api_url": args.api_url,
            "supabase_url": args.supabase_url,
            "host": get_host_metadata(),
            "tier_a_reads": tier_a,
            "tier_b_writes": tier_b,
            "tier_c_chat": tier_c,
            "tier_d_scheduler": tier_d,
        }
        out_dir = args.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / f"f1_load_test_{ts}.json"
        md_path = out_dir / f"f1_load_test_{ts}.md"
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(render_markdown(payload), encoding="utf-8")
        print(f"\nSaved JSON: {json_path}")
        print(f"Saved MD  : {md_path}")
        return 0
    finally:
        await api_http.aclose()
        await supa_http.aclose()


def main() -> int:
    parser = argparse.ArgumentParser(description="StudyFlow AI F1 Load, CCU, RPS & Breaking-Point Benchmark")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--supabase-url", default="http://127.0.0.1:54321")
    parser.add_argument("--env-file", type=pathlib.Path, default=None)
    parser.add_argument("--step-seconds", type=float, default=8.0)
    parser.add_argument("--output-dir", type=pathlib.Path, default=ROOT / "logs" / "f1-qa-reports")
    args = parser.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
