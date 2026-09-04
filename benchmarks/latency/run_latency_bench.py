"""B1 — Latency Benchmark for P-160 AloSM.

Measures per-component and end-to-end latency across the voice pipeline:
  • STT  (via API or mock)
  • LLM  (Agent text turn)
  • TTS  (via API or mock)
  • Tool execution (place_search, get_quote, create_booking)
  • Backend REST API endpoints
  • E2E text conversation turn

Usage:
    uv run python -m benchmarks.latency.run_latency_bench [--samples N] [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

from benchmarks.base import (
    BenchmarkReport,
    TimingResult,
    compute_stats,
    format_ms,
    generate_benchmark_id,
    md_table,
    save_report,
    target_check,
)
from benchmarks.config import APIConfig, LatencyTarget, get_target, RESULTS_BASE
from benchmarks.http_client import BenchmarkHTTPClient

logger = logging.getLogger(__name__)

RESULTS_DIR = RESULTS_BASE / "latency"

# ---------------------------------------------------------------------------
# Sample data for benchmarks
# ---------------------------------------------------------------------------

SAMPLE_MESSAGES: list[dict[str, str]] = [
    {"text": "Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm", "label": "one_shot_booking"},
    {"text": "Đặt xe giúp tôi", "label": "incomplete_booking"},
    {"text": "Đón tôi ở Vincom", "label": "ambiguous_place"},
    {"text": "Giá từ VinUni tới Hồ Gươm bao nhiêu?", "label": "price_inquiry"},
    {"text": "Trạng thái chuyến xe của tôi?", "label": "trip_status"},
    {"text": "Chính sách hủy chuyến như thế nào?", "label": "faq_policy"},
    {"text": "Cho tôi gặp tổng đài viên", "label": "handoff_request"},
    {"text": "Đổi điểm đến thành Bệnh viện Bạch Mai", "label": "correction"},
    {"text": "Tôi vừa gặp tai nạn, cần hỗ trợ ngay", "label": "emergency"},
    {"text": "Tôi chọn Cổng chính VinUni", "label": "candidate_select"},
]

API_ENDPOINTS: list[dict[str, str]] = [
    {"method": "GET", "path": "/api/v1/health",   "label": "health_check"},
    {"method": "GET", "path": "/api/v1/bookings",  "label": "list_bookings"},
    {"method": "GET", "path": "/api/v1/trips",     "label": "list_trips"},
]


# ---------------------------------------------------------------------------
# Benchmark functions
# ---------------------------------------------------------------------------

async def bench_backend_api(
    client: BenchmarkHTTPClient,
    n_samples: int,
) -> list[BenchmarkReport]:
    """Measure latency of REST API endpoints."""
    reports: list[BenchmarkReport] = []

    for endpoint in API_ENDPOINTS:
        timings: list[float] = []
        for i in range(n_samples):
            resp = await client.timed_get(endpoint["path"])
            timings.append(resp.elapsed_ms)
            logger.info(
                "  API %s %s [%d/%d] → %dms (HTTP %d)",
                endpoint["method"], endpoint["path"],
                i + 1, n_samples,
                resp.elapsed_ms, resp.status_code,
            )

        stats = compute_stats(timings)
        report = BenchmarkReport(
            benchmark_id=generate_benchmark_id("latency-api"),
            category="latency",
            component=f"backend_api_{endpoint['label']}",
            sample_count=len(timings),
            results=stats,
            raw_values=timings,
            metadata={"endpoint": endpoint["path"], "method": endpoint["method"]},
        )
        reports.append(report)

    return reports


async def bench_text_turn(
    client: BenchmarkHTTPClient,
    n_samples: int,
) -> list[BenchmarkReport]:
    """Measure E2E latency of a text conversation turn via the messages API."""
    reports: list[BenchmarkReport] = []

    for msg_data in SAMPLE_MESSAGES[:min(n_samples, len(SAMPLE_MESSAGES))]:
        timings: list[float] = []
        # Create a fresh session for each message type
        session_id = await client.create_session()

        for i in range(max(1, n_samples // len(SAMPLE_MESSAGES))):
            resp = await client.send_message(session_id, msg_data["text"])
            timings.append(resp.elapsed_ms)
            logger.info(
                "  TEXT TURN [%s] [%d] → %dms (HTTP %d)",
                msg_data["label"], i + 1,
                resp.elapsed_ms, resp.status_code,
            )

        stats = compute_stats(timings)
        report = BenchmarkReport(
            benchmark_id=generate_benchmark_id(f"latency-turn-{msg_data['label']}"),
            category="latency",
            component=f"text_turn_{msg_data['label']}",
            sample_count=len(timings),
            results=stats,
            raw_values=timings,
            metadata={"message": msg_data["text"], "label": msg_data["label"]},
        )
        reports.append(report)

    return reports


async def bench_conversation_flow(
    client: BenchmarkHTTPClient,
    n_samples: int,
) -> list[BenchmarkReport]:
    """Measure a full happy-path booking conversation (multi-turn)."""
    conversation_steps = [
        "Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm",
        "Tôi chọn Cổng chính VinUni",
        "Tôi chọn Bưu điện Hà Nội",
        "Đúng, tôi xác nhận đặt chuyến này",
    ]

    flow_timings: list[float] = []
    step_timings: dict[int, list[float]] = {i: [] for i in range(len(conversation_steps))}

    for run in range(n_samples):
        session_id = await client.create_session()
        flow_start = time.perf_counter()

        for step_idx, step_msg in enumerate(conversation_steps):
            resp = await client.send_message(session_id, step_msg)
            step_timings[step_idx].append(resp.elapsed_ms)
            logger.info(
                "  FLOW run=%d step=%d → %dms (HTTP %d)",
                run + 1, step_idx + 1, resp.elapsed_ms, resp.status_code,
            )

        flow_elapsed = (time.perf_counter() - flow_start) * 1000
        flow_timings.append(flow_elapsed)
        logger.info("  FLOW run=%d total → %dms", run + 1, flow_elapsed)

    reports: list[BenchmarkReport] = []

    # Per-step reports
    for step_idx, step_msg in enumerate(conversation_steps):
        stats = compute_stats(step_timings[step_idx])
        reports.append(BenchmarkReport(
            benchmark_id=generate_benchmark_id(f"latency-flow-step{step_idx + 1}"),
            category="latency",
            component=f"booking_flow_step_{step_idx + 1}",
            sample_count=len(step_timings[step_idx]),
            results=stats,
            raw_values=step_timings[step_idx],
            metadata={"step": step_idx + 1, "message": step_msg},
        ))

    # Total flow report
    flow_stats = compute_stats(flow_timings)
    reports.append(BenchmarkReport(
        benchmark_id=generate_benchmark_id("latency-flow-total"),
        category="latency",
        component="booking_flow_total",
        sample_count=len(flow_timings),
        results=flow_stats,
        raw_values=flow_timings,
        metadata={"steps": len(conversation_steps)},
    ))

    return reports


# ---------------------------------------------------------------------------
# Dry-run mode (no API calls)
# ---------------------------------------------------------------------------

async def dry_run() -> list[BenchmarkReport]:
    """Generate synthetic benchmark data for testing the pipeline."""
    import random

    logger.info("=== DRY RUN MODE — synthetic data ===")
    reports: list[BenchmarkReport] = []

    for component in ["stt", "llm_ttft", "llm_total", "tts_ttfb", "backend_api", "text_turn"]:
        # Generate plausible random latencies
        base = {"stt": 500, "llm_ttft": 400, "llm_total": 700, "tts_ttfb": 350, "backend_api": 50, "text_turn": 1500}
        values = [base.get(component, 500) + random.gauss(0, base.get(component, 500) * 0.3) for _ in range(30)]
        values = [max(10, v) for v in values]  # floor at 10ms

        stats = compute_stats(values)
        reports.append(BenchmarkReport(
            benchmark_id=generate_benchmark_id(f"latency-{component}"),
            category="latency",
            component=component,
            sample_count=len(values),
            results=stats,
            raw_values=values,
            metadata={"mode": "dry_run"},
        ))

    return reports


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_latency_report(reports: list[BenchmarkReport]) -> str:
    """Build a markdown summary of latency benchmark results."""
    lines = [
        "# B1 — Latency Benchmark Report",
        "",
        f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"**Total components tested**: {len(reports)}",
        "",
        "## Summary",
        "",
    ]

    headers = ["Component", "Samples", "Min", "Mean", "Median", "Max", "p50", "p95", "Target p95", "Status"]
    rows: list[list[str]] = []

    for r in reports:
        s = r.results
        target = get_target(r.component)
        p95 = s.get("p95", s.get("max", 0))
        target_p95 = target.p95_ms if target else "—"
        status = ""
        if target and p95:
            status = target_check(p95, target.p95_ms)

        rows.append([
            f"`{r.component}`",
            str(int(s.get("count", r.sample_count))),
            format_ms(s.get("min", 0)),
            format_ms(s.get("mean", 0)),
            format_ms(s.get("median", 0)),
            format_ms(s.get("max", 0)),
            format_ms(s["p50"]) if "p50" in s else "—",
            format_ms(p95) if "p95" in s else "—",
            format_ms(target_p95) if isinstance(target_p95, (int, float)) else "—",
            status or "—",
        ])

    lines.append(md_table(headers, rows))
    lines.append("")

    # Note about sample size
    low_sample = [r for r in reports if r.sample_count < 20]
    if low_sample:
        lines.append("> ⚠️ **Lưu ý**: Các component sau có < 20 samples, chỉ ghi min/max/mean (không tính p95 theo hướng dẫn mentor):")
        for r in low_sample:
            lines.append(f">   - `{r.component}` ({r.sample_count} samples)")
        lines.append("")

    lines.append("## Raw data")
    lines.append("")
    lines.append("Chi tiết từng lần đo nằm trong JSON files tại `benchmarks/results/latency/`.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.dry_run:
        reports = await dry_run()
    else:
        async with BenchmarkHTTPClient() as client:
            await client.login()
            logger.info("✅ Logged in successfully")

            all_reports: list[BenchmarkReport] = []

            logger.info("\n=== Backend API Latency ===")
            api_reports = await bench_backend_api(client, args.samples)
            all_reports.extend(api_reports)

            logger.info("\n=== Text Turn Latency ===")
            turn_reports = await bench_text_turn(client, args.samples)
            all_reports.extend(turn_reports)

            logger.info("\n=== Booking Flow Latency ===")
            flow_reports = await bench_conversation_flow(client, min(args.samples, 5))
            all_reports.extend(flow_reports)

            reports = all_reports

    # Save individual reports
    for report in reports:
        path = save_report(report, RESULTS_DIR)
        logger.info("  Saved → %s", path)

    # Generate markdown summary
    md = generate_latency_report(reports)
    md_path = RESULTS_DIR / "latency_report.md"
    md_path.write_text(md, encoding="utf-8")
    logger.info("\n📊 Latency report → %s", md_path)
    sys.stdout.buffer.write(md.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


def cli() -> None:
    parser = argparse.ArgumentParser(description="B1 — Latency Benchmark for P-160 AloSM")
    parser.add_argument("--samples", type=int, default=10, help="Number of samples per component (default: 10)")
    parser.add_argument("--dry-run", action="store_true", help="Generate synthetic data without API calls")
    args = parser.parse_args()
    asyncio.run(main(args))


if __name__ == "__main__":
    cli()
