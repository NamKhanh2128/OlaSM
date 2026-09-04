"""B3 — Stability Benchmark for P-160 AloSM.

Measures error rates, timeout rates, session recovery, idempotency,
and concurrent session handling.

Usage:
    uv run python -m benchmarks.stability.run_stability_bench [--samples N] [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from benchmarks.base import (
    BenchmarkReport,
    StabilityEvent,
    compute_stats,
    generate_benchmark_id,
    md_table,
    save_report,
    target_check,
)
from benchmarks.config import RESULTS_BASE
from benchmarks.http_client import BenchmarkHTTPClient

logger = logging.getLogger(__name__)

RESULTS_DIR = RESULTS_BASE / "stability"


# ---------------------------------------------------------------------------
# Stability test helpers
# ---------------------------------------------------------------------------

def classify_error(resp_body: dict[str, Any], status_code: int, elapsed_ms: float) -> str:
    """Classify the error type from an API response."""
    if status_code == 0:
        return "network_error"
    if status_code == 408 or elapsed_ms > 25000:
        return "timeout"
    if status_code == 429:
        return "rate_limited"
    if status_code >= 500:
        return "backend_500"
    if status_code >= 400:
        return "client_error"
    # Check for application-level issues
    error_msg = str(resp_body.get("error", "") or resp_body.get("detail", ""))
    if "timeout" in error_msg.lower():
        return "llm_timeout"
    if "stt" in error_msg.lower() or "transcri" in error_msg.lower():
        return "stt_no_final"
    if "tts" in error_msg.lower():
        return "tts_error"
    return ""


# ---------------------------------------------------------------------------
# Test 1: Error rate across N conversations
# ---------------------------------------------------------------------------

async def test_error_rate(
    client: BenchmarkHTTPClient,
    n_samples: int,
) -> list[StabilityEvent]:
    """Send N conversation turns and track success/error/timeout."""
    events: list[StabilityEvent] = []
    test_messages = [
        "Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm",
        "Giá từ VinUni tới Hồ Gươm bao nhiêu?",
        "Chính sách hủy chuyến như thế nào?",
        "Trạng thái chuyến xe của tôi?",
        "Cho tôi gặp tổng đài viên",
    ]

    for i in range(n_samples):
        msg = test_messages[i % len(test_messages)]
        request_id = str(uuid.uuid4())[:8]

        try:
            session_id = await client.create_session()
            resp = await client.send_message(session_id, msg)

            error_type = classify_error(resp.body, resp.status_code, resp.elapsed_ms)
            is_success = resp.status_code == 200 and not error_type

            event = StabilityEvent(
                request_id=request_id,
                scenario=f"turn_{i + 1}",
                timestamp_iso=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                success=is_success,
                error_type=error_type,
                response_time_ms=resp.elapsed_ms,
                details=f"HTTP {resp.status_code}, msg='{msg[:40]}'",
            )
        except Exception as exc:
            event = StabilityEvent(
                request_id=request_id,
                scenario=f"turn_{i + 1}",
                timestamp_iso=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                success=False,
                error_type="exception",
                details=str(exc)[:200],
            )

        events.append(event)
        status = "✅" if event.success else f"❌ {event.error_type}"
        logger.info("  [%d/%d] %s → %s (%dms)", i + 1, n_samples, msg[:30], status, event.response_time_ms)

    return events


# ---------------------------------------------------------------------------
# Test 2: Session recovery after disconnect
# ---------------------------------------------------------------------------

async def test_session_recovery(
    client: BenchmarkHTTPClient,
    n_samples: int,
) -> list[dict[str, Any]]:
    """Simulate disconnect/reconnect by creating session, sending message,
    then accessing session state again.
    """
    results: list[dict[str, Any]] = []

    for i in range(n_samples):
        session_id = await client.create_session()

        # Step 1: Send initial message
        resp1 = await client.send_message(session_id, "Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm")
        initial_success = resp1.status_code == 200

        # Step 2: Simulate "reconnect" — send another message to same session
        resp2 = await client.send_message(session_id, "Tôi chọn Cổng chính VinUni")
        resume_success = resp2.status_code == 200

        # Check context preservation: agent should not ask for pickup again
        agent_msg = str(resp2.body.get("message", resp2.body.get("response", ""))).lower()
        context_preserved = "điểm đón" not in agent_msg and "pickup" not in agent_msg

        result = {
            "run": i + 1,
            "session_id": session_id,
            "initial_success": initial_success,
            "resume_success": resume_success,
            "context_preserved": context_preserved,
            "recovered": initial_success and resume_success and context_preserved,
        }
        results.append(result)

        status = "✅ recovered" if result["recovered"] else "❌ failed"
        logger.info("  Recovery [%d/%d] → %s (context=%s)", i + 1, n_samples, status, context_preserved)

    return results


# ---------------------------------------------------------------------------
# Test 3: Booking idempotency
# ---------------------------------------------------------------------------

async def test_idempotency(
    client: BenchmarkHTTPClient,
    n_samples: int,
) -> list[dict[str, Any]]:
    """Double-submit confirmation and verify only 1 booking created."""
    results: list[dict[str, Any]] = []

    for i in range(n_samples):
        session_id = await client.create_session()

        # Build up booking state
        await client.send_message(session_id, "Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm")
        await client.send_message(session_id, "Tôi chọn Cổng chính VinUni")
        await client.send_message(session_id, "Tôi chọn Bưu điện Hà Nội")

        # Get booking count before
        bookings_before = await client.get_bookings()
        count_before = len(bookings_before.body.get("bookings", bookings_before.body.get("data", [])))

        # Double submit confirmation
        resp1 = await client.send_message(session_id, "Đúng, tôi xác nhận đặt chuyến này")
        resp2 = await client.send_message(session_id, "Đúng, tôi xác nhận đặt chuyến này")

        # Get booking count after
        bookings_after = await client.get_bookings()
        count_after = len(bookings_after.body.get("bookings", bookings_after.body.get("data", [])))

        new_bookings = count_after - count_before
        is_idempotent = new_bookings <= 1  # Should be exactly 0 or 1

        result = {
            "run": i + 1,
            "session_id": session_id,
            "bookings_before": count_before,
            "bookings_after": count_after,
            "new_bookings": new_bookings,
            "is_idempotent": is_idempotent,
        }
        results.append(result)

        status = "✅ idempotent" if is_idempotent else f"❌ {new_bookings} bookings created"
        logger.info("  Idempotency [%d/%d] → %s (before=%d, after=%d)", i + 1, n_samples, status, count_before, count_after)

    return results


# ---------------------------------------------------------------------------
# Test 4: Concurrent sessions
# ---------------------------------------------------------------------------

async def test_concurrent_sessions(
    client: BenchmarkHTTPClient,
    concurrency: int,
) -> dict[str, Any]:
    """Run N sessions concurrently and check for errors/conflicts."""

    async def single_session(idx: int) -> dict[str, Any]:
        try:
            session_id = await client.create_session()
            resp = await client.send_message(session_id, f"Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm")
            return {
                "session_idx": idx,
                "session_id": session_id,
                "success": resp.status_code == 200,
                "elapsed_ms": resp.elapsed_ms,
                "error": resp.error or "",
            }
        except Exception as exc:
            return {
                "session_idx": idx,
                "success": False,
                "error": str(exc)[:200],
                "elapsed_ms": 0,
            }

    logger.info("  Running %d concurrent sessions...", concurrency)
    tasks = [single_session(i) for i in range(concurrency)]
    results = await asyncio.gather(*tasks)

    succeeded = sum(1 for r in results if r["success"])
    failed = concurrency - succeeded
    latencies = [r["elapsed_ms"] for r in results if r["success"]]

    return {
        "concurrency": concurrency,
        "succeeded": succeeded,
        "failed": failed,
        "success_rate": succeeded / concurrency * 100 if concurrency > 0 else 0,
        "latency_stats": compute_stats(latencies, include_percentiles=False) if latencies else {},
        "details": list(results),
    }


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------

async def dry_run_stability() -> dict[str, Any]:
    """Generate synthetic stability data."""
    import random

    logger.info("=== DRY RUN MODE — synthetic stability data ===")

    events = []
    for i in range(30):
        events.append(StabilityEvent(
            request_id=f"dry-{i}",
            scenario=f"turn_{i}",
            success=True,
            error_type="",
            response_time_ms=random.uniform(400, 1600),
        ))

    recovery = [{"run": i, "recovered": True} for i in range(10)]
    idempotency = [{"run": i, "is_idempotent": True, "new_bookings": 1} for i in range(5)]
    concurrent = {
        "concurrency": 5,
        "succeeded": 5,
        "failed": 0,
        "success_rate": 100,
    }

    return {
        "error_events": events,
        "recovery": recovery,
        "idempotency": idempotency,
        "concurrent": concurrent,
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_stability_report(
    error_events: list[StabilityEvent],
    recovery_results: list[dict[str, Any]],
    idempotency_results: list[dict[str, Any]],
    concurrent_result: dict[str, Any],
) -> str:
    """Build markdown stability report."""
    lines = [
        "# B3 — Stability Benchmark Report",
        "",
        f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "",
    ]

    # Error rate
    total = len(error_events)
    errors = sum(1 for e in error_events if not e.success)
    timeouts = sum(1 for e in error_events if e.error_type in ("timeout", "llm_timeout"))
    error_rate = errors / total * 100 if total > 0 else 0
    timeout_rate = timeouts / total * 100 if total > 0 else 0

    lines.append("## 1. Error Rate")
    lines.append("")
    lines.append(md_table(
        ["Metric", "Value", "Target", "Status"],
        [
            ["Total requests", str(total), "—", "—"],
            ["Successful", str(total - errors), "—", "—"],
            ["Errors", str(errors), "—", "—"],
            ["Error rate", f"{error_rate:.1f}%", "< 5%", target_check(error_rate, 5)],
            ["Timeout rate", f"{timeout_rate:.1f}%", "< 2%", target_check(timeout_rate, 2)],
        ],
    ))
    lines.append("")

    # Error breakdown
    error_types: dict[str, int] = {}
    for e in error_events:
        if e.error_type:
            error_types[e.error_type] = error_types.get(e.error_type, 0) + 1

    if error_types:
        lines.append("### Error Breakdown")
        lines.append("")
        lines.append(md_table(
            ["Error Type", "Count", "% of Total"],
            [[t, str(c), f"{c / total * 100:.1f}%"] for t, c in sorted(error_types.items(), key=lambda x: -x[1])],
        ))
        lines.append("")

    # Response time stats
    resp_times = [e.response_time_ms for e in error_events if e.response_time_ms > 0]
    if resp_times:
        rt_stats = compute_stats(resp_times)
        lines.append("### Response Time Distribution")
        lines.append("")
        lines.append(md_table(
            ["Metric", "Value"],
            [
                ["Mean", f"{rt_stats.get('mean', 0):.0f}ms"],
                ["Median", f"{rt_stats.get('median', 0):.0f}ms"],
                ["Min", f"{rt_stats.get('min', 0):.0f}ms"],
                ["Max", f"{rt_stats.get('max', 0):.0f}ms"],
            ] + ([["p95", f"{rt_stats['p95']:.0f}ms"]] if "p95" in rt_stats else []),
        ))
        lines.append("")

    # Session recovery
    lines.append("## 2. Session Recovery")
    lines.append("")
    if recovery_results:
        recovered = sum(1 for r in recovery_results if r["recovered"])
        total_r = len(recovery_results)
        rate = recovered / total_r * 100 if total_r > 0 else 0
        lines.append(md_table(
            ["Metric", "Value", "Target", "Status"],
            [
                ["Total attempts", str(total_r), "—", "—"],
                ["Recovered", str(recovered), "—", "—"],
                ["Recovery rate", f"{rate:.1f}%", "> 95%", target_check(rate, 95, lower_is_better=False)],
            ],
        ))
    lines.append("")

    # Idempotency
    lines.append("## 3. Booking Idempotency")
    lines.append("")
    if idempotency_results:
        idempotent = sum(1 for r in idempotency_results if r["is_idempotent"])
        total_i = len(idempotency_results)
        rate_i = idempotent / total_i * 100 if total_i > 0 else 0
        lines.append(md_table(
            ["Metric", "Value", "Target", "Status"],
            [
                ["Total tests", str(total_i), "—", "—"],
                ["Idempotent", str(idempotent), "—", "—"],
                ["Rate", f"{rate_i:.1f}%", "100%", target_check(100 - rate_i, 0)],
            ],
        ))
    lines.append("")

    # Concurrent sessions
    lines.append("## 4. Concurrent Sessions")
    lines.append("")
    if concurrent_result:
        lines.append(md_table(
            ["Metric", "Value"],
            [
                ["Concurrency level", str(concurrent_result.get("concurrency", 0))],
                ["Succeeded", str(concurrent_result.get("succeeded", 0))],
                ["Failed", str(concurrent_result.get("failed", 0))],
                ["Success rate", f"{concurrent_result.get('success_rate', 0):.1f}%"],
            ],
        ))
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.dry_run:
        data = await dry_run_stability()
        error_events = data["error_events"]
        recovery = data["recovery"]
        idempotency = data["idempotency"]
        concurrent = data["concurrent"]
    else:
        async with BenchmarkHTTPClient() as client:
            await client.login()
            logger.info("✅ Logged in successfully")

            logger.info("\n=== Error Rate Test ===")
            error_events = await test_error_rate(client, args.samples)

            logger.info("\n=== Session Recovery Test ===")
            recovery = await test_session_recovery(client, min(args.samples, 5))

            logger.info("\n=== Idempotency Test ===")
            idempotency = await test_idempotency(client, min(args.samples, 3))

            logger.info("\n=== Concurrent Sessions Test ===")
            concurrent = await test_concurrent_sessions(client, args.concurrency)

    # Save raw data
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RESULTS_DIR / f"stability-raw-{time.strftime('%Y%m%d-%H%M%S')}.json"
    raw_data = {
        "error_events": [asdict(e) for e in error_events] if isinstance(error_events[0], StabilityEvent) else error_events,
        "recovery": recovery,
        "idempotency": idempotency,
        "concurrent": concurrent,
    }
    raw_path.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    # Generate report
    md = generate_stability_report(error_events, recovery, idempotency, concurrent)
    md_path = RESULTS_DIR / "stability_report.md"
    md_path.write_text(md, encoding="utf-8")
    logger.info("📊 Stability report → %s", md_path)
    import sys
    sys.stdout.buffer.write(md.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


def cli() -> None:
    parser = argparse.ArgumentParser(description="B3 — Stability Benchmark for P-160 AloSM")
    parser.add_argument("--samples", type=int, default=20, help="Number of error-rate samples (default: 20)")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrent session count (default: 5)")
    parser.add_argument("--dry-run", action="store_true", help="Generate synthetic data")
    args = parser.parse_args()
    asyncio.run(main(args))


if __name__ == "__main__":
    cli()
