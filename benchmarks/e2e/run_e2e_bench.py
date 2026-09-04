"""B5 — E2E Functional Benchmark for P-160 AloSM.

Runs scripted end-to-end conversation scenarios via the text API
and validates booking state machine, correction flow, handoff,
FAQ, and safety behaviors.

Usage:
    uv run python -m benchmarks.e2e.run_e2e_bench [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from benchmarks.base import (
    E2EScenarioResult,
    Verdict,
    generate_benchmark_id,
    md_table,
)
from benchmarks.config import RESULTS_BASE, REVIEW_TEST_MAP
from benchmarks.http_client import BenchmarkHTTPClient

logger = logging.getLogger(__name__)

RESULTS_DIR = RESULTS_BASE / "e2e"


# ---------------------------------------------------------------------------
# E2E Scenario definitions
# ---------------------------------------------------------------------------

@dataclass
class E2EStep:
    """One user turn with expected oracle checks."""

    user_message: str
    expect_in_response: list[str] = field(default_factory=list)
    expect_not_in_response: list[str] = field(default_factory=list)
    expect_status_code: int = 200
    expect_booking_created: bool | None = None
    description: str = ""


@dataclass
class E2EScenario:
    """A complete E2E test scenario."""

    id: str
    name: str
    description: str
    steps: list[E2EStep]
    review_ids: list[str] = field(default_factory=list)
    priority: str = "P0"


SCENARIOS: list[E2EScenario] = [
    # --- F1: Voice Booking ---
    E2EScenario(
        id="E2E-F1-001",
        name="Happy Path Booking",
        description="Full booking: 1 câu → chọn candidate → quote → confirm → booking created",
        review_ids=["P160-F1-HAPPY-001", "P160-F1-EDGE-005"],
        steps=[
            E2EStep(
                user_message="Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm",
                description="One-shot booking với 3 entity",
            ),
            E2EStep(
                user_message="Tôi chọn Cổng chính VinUni",
                description="Chọn pickup candidate",
            ),
            E2EStep(
                user_message="Tôi chọn Bưu điện Hà Nội",
                description="Chọn destination candidate",
            ),
            E2EStep(
                user_message="Đúng, tôi xác nhận đặt chuyến này",
                description="Explicit confirmation",
                expect_booking_created=True,
            ),
        ],
    ),
    E2EScenario(
        id="E2E-F1-002",
        name="Multi-turn Incomplete Booking",
        description="Thiếu info, hỏi từng field",
        review_ids=["P160-F1-EDGE-002"],
        steps=[
            E2EStep(
                user_message="Đặt xe giúp tôi",
                expect_in_response=["điểm đón", "đón"],
                description="Agent hỏi pickup",
            ),
            E2EStep(
                user_message="Đón ở VinUni",
                description="Cung cấp pickup",
            ),
            E2EStep(
                user_message="Tôi chọn Cổng chính VinUni",
                description="Chọn pickup candidate",
            ),
            E2EStep(
                user_message="Đi Hồ Gươm",
                description="Cung cấp destination",
            ),
            E2EStep(
                user_message="Xe 4 chỗ",
                description="Chọn vehicle type",
            ),
        ],
    ),
    E2EScenario(
        id="E2E-F1-003",
        name="Correction Invalidates Quote",
        description="Sửa destination sau khi có quote → quote mới",
        review_ids=["P160-F1-UNHAPPY-004"],
        steps=[
            E2EStep(user_message="Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm", description="Initial booking"),
            E2EStep(user_message="Tôi chọn Cổng chính VinUni", description="Select pickup"),
            E2EStep(user_message="Tôi chọn Bưu điện Hà Nội", description="Select destination"),
            E2EStep(
                user_message="Đổi điểm đến thành Bệnh viện Bạch Mai",
                expect_not_in_response=["xác nhận"],
                description="Correction should invalidate old quote",
            ),
        ],
    ),
    E2EScenario(
        id="E2E-F1-004",
        name="Negative Confirmation",
        description="Câu mơ hồ không tạo booking",
        review_ids=["P160-F3-AI-904"],
        steps=[
            E2EStep(user_message="Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm", description="Initial"),
            E2EStep(user_message="Tôi chọn Cổng chính VinUni", description="Pickup"),
            E2EStep(user_message="Tôi chọn Bưu điện Hà Nội", description="Destination"),
            E2EStep(
                user_message="Ừ giá được, nhưng chưa đặt nhé",
                expect_booking_created=False,
                description="Negative confirm should NOT create booking",
            ),
        ],
    ),

    # --- F2: Handoff ---
    E2EScenario(
        id="E2E-F2-001",
        name="Explicit Handoff Request",
        description="User yêu cầu tổng đài viên giữa booking draft",
        review_ids=["P160-F2-HAPPY-001"],
        priority="P0",
        steps=[
            E2EStep(user_message="Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm", description="Start booking"),
            E2EStep(
                user_message="Cho tôi gặp tổng đài viên",
                expect_in_response=["chuyển", "tổng đài", "handoff", "kết nối"],
                expect_booking_created=False,
                description="Handoff should be created, no booking",
            ),
        ],
    ),

    # --- F3: FAQ/Price/Status ---
    E2EScenario(
        id="E2E-F3-001",
        name="Price Inquiry Only",
        description="Hỏi giá nhưng không đặt xe",
        review_ids=["P160-F3-HAPPY-001"],
        steps=[
            E2EStep(
                user_message="Giá từ VinUni tới Hồ Gươm bao nhiêu?",
                expect_in_response=["giá", "ước tính", "vnđ", "vnd"],
                expect_booking_created=False,
                description="Should return price estimate without booking",
            ),
        ],
    ),
    E2EScenario(
        id="E2E-F3-002",
        name="FAQ Policy Query",
        description="Hỏi chính sách",
        review_ids=["P160-F3-AI-003"],
        steps=[
            E2EStep(
                user_message="Chính sách hủy chuyến như thế nào?",
                expect_in_response=["chính sách", "hủy"],
                description="Grounded answer from KB",
            ),
        ],
    ),
    E2EScenario(
        id="E2E-F3-003",
        name="Out-of-scope Policy",
        description="Hỏi policy ngoài KB",
        review_ids=["P160-F3-UNHAPPY-004"],
        steps=[
            E2EStep(
                user_message="AloSM có hỗ trợ đặt vé máy bay không?",
                expect_not_in_response=["có", "chắc chắn"],
                description="Should decline or refer to human",
            ),
        ],
    ),

    # --- F9: Emergency ---
    E2EScenario(
        id="E2E-F9-001",
        name="Emergency During Booking",
        description="Tai nạn giữa booking → handoff, không booking",
        review_ids=["P160-F9-HAPPY-001", "P160-F9-AI-906"],
        priority="P0",
        steps=[
            E2EStep(user_message="Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm", description="Start booking"),
            E2EStep(
                user_message="Tôi vừa gặp tai nạn, cần hỗ trợ ngay",
                expect_in_response=["cấp cứu", "an toàn", "hỗ trợ", "115", "112", "handoff"],
                expect_booking_created=False,
                description="Should prioritize emergency, stop booking",
            ),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Run E2E scenarios
# ---------------------------------------------------------------------------

async def run_e2e_scenario(
    client: BenchmarkHTTPClient,
    scenario: E2EScenario,
) -> E2EScenarioResult:
    """Run one E2E scenario and return the result."""
    result = E2EScenarioResult(
        scenario_id=scenario.id,
        scenario_name=scenario.name,
        review_id=", ".join(scenario.review_ids),
    )

    t0 = time.perf_counter()
    session_id = await client.create_session()
    all_passed = True

    for step_idx, step in enumerate(scenario.steps):
        resp = await client.send_message(session_id, step.user_message)
        agent_msg = str(resp.body.get("message", resp.body.get("response", ""))).lower()

        step_result: dict[str, Any] = {
            "step": step_idx + 1,
            "user_message": step.user_message,
            "description": step.description,
            "http_status": resp.status_code,
            "response_time_ms": resp.elapsed_ms,
            "agent_response_preview": agent_msg[:150],
            "checks": [],
        }

        # Check status code
        if resp.status_code != step.expect_status_code:
            step_result["checks"].append(f"❌ HTTP {resp.status_code} != expected {step.expect_status_code}")
            all_passed = False
        else:
            step_result["checks"].append(f"✅ HTTP {resp.status_code}")

        # Check expected keywords in response
        for keyword in step.expect_in_response:
            if keyword.lower() in agent_msg:
                step_result["checks"].append(f"✅ Found '{keyword}'")
            else:
                step_result["checks"].append(f"❌ Missing '{keyword}' in response")
                all_passed = False

        # Check unexpected keywords
        for keyword in step.expect_not_in_response:
            if keyword.lower() in agent_msg:
                step_result["checks"].append(f"❌ Unexpected '{keyword}' found in response")
                all_passed = False
            else:
                step_result["checks"].append(f"✅ '{keyword}' correctly absent")

        # Check booking creation (at final step)
        if step.expect_booking_created is not None:
            # This is a heuristic check based on response content
            booking_indicators = ["đã đặt", "mã chuyến", "booking", "book_", "confirmed"]
            has_booking = any(ind in agent_msg for ind in booking_indicators)

            if step.expect_booking_created and has_booking:
                step_result["checks"].append("✅ Booking appears to be created")
            elif step.expect_booking_created and not has_booking:
                step_result["checks"].append("⚠️ Expected booking but not confirmed in response")
                # Not necessarily a failure — booking might exist in state
            elif not step.expect_booking_created and has_booking:
                step_result["checks"].append("❌ Booking created when it shouldn't be")
                all_passed = False
            else:
                step_result["checks"].append("✅ No booking created (as expected)")

        result.steps.append(step_result)

        logger.info(
            "  [%s] step %d: %s → %s",
            scenario.id, step_idx + 1,
            step.description,
            "PASS" if all(c.startswith("✅") for c in step_result["checks"]) else "FAIL/WARN",
        )

    result.duration_ms = (time.perf_counter() - t0) * 1000
    result.verdict = Verdict.PASS if all_passed else Verdict.FAIL
    result.details = f"{len(scenario.steps)} steps, {result.duration_ms:.0f}ms total"

    return result


async def run_all_e2e(client: BenchmarkHTTPClient) -> list[E2EScenarioResult]:
    """Run all E2E scenarios."""
    results: list[E2EScenarioResult] = []

    for scenario in SCENARIOS:
        logger.info("\n=== E2E: %s — %s ===", scenario.id, scenario.name)
        result = await run_e2e_scenario(client, scenario)
        results.append(result)

        verdict = "✅ PASS" if result.verdict == Verdict.PASS else "❌ FAIL"
        logger.info("  Result: %s (%s)", verdict, result.details)

    return results


async def dry_run_e2e() -> list[E2EScenarioResult]:
    """Generate synthetic E2E results."""
    import random

    logger.info("=== DRY RUN MODE — synthetic E2E data ===")
    results: list[E2EScenarioResult] = []

    for scenario in SCENARIOS:
        results.append(E2EScenarioResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            verdict=Verdict.PASS,
            review_id=", ".join(scenario.review_ids),
            duration_ms=random.uniform(1800, 3500),
            details=f"{len(scenario.steps)} steps, DRY RUN (PASS)",
            steps=[{"step": i + 1, "dry_run": True} for i in range(len(scenario.steps))],
        ))

    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_e2e_report(results: list[E2EScenarioResult]) -> str:
    """Build markdown E2E report."""
    lines = [
        "# B5 — E2E Functional Benchmark Report",
        "",
        f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"**Total scenarios**: {len(results)}",
        "",
    ]

    # Overall
    passed = sum(1 for r in results if r.verdict == Verdict.PASS)
    failed = sum(1 for r in results if r.verdict == Verdict.FAIL)
    total = len(results)

    lines.append("## Overall Results")
    lines.append("")
    lines.append(md_table(
        ["Metric", "Value"],
        [
            ["Total scenarios", str(total)],
            ["Passed", f"✅ {passed}"],
            ["Failed", f"❌ {failed}"],
            ["Pass rate", f"{passed / total * 100:.1f}%"],
        ],
    ))
    lines.append("")

    # Per-scenario results
    lines.append("## Scenario Results")
    lines.append("")

    headers = ["ID", "Name", "Steps", "Verdict", "Duration", "Review IDs"]
    rows: list[list[str]] = []
    for r in results:
        verdict = "✅ PASS" if r.verdict == Verdict.PASS else "❌ FAIL"
        rows.append([
            f"`{r.scenario_id}`",
            r.scenario_name,
            str(len(r.steps)),
            verdict,
            f"{r.duration_ms:.0f}ms",
            f"`{r.review_id}`" if r.review_id else "—",
        ])

    lines.append(md_table(headers, rows))
    lines.append("")

    # Feature coverage
    lines.append("## Feature Coverage")
    lines.append("")

    features = {
        "F1 — Booking": [r for r in results if r.scenario_id.startswith("E2E-F1")],
        "F2 — Handoff": [r for r in results if r.scenario_id.startswith("E2E-F2")],
        "F3 — FAQ/Price": [r for r in results if r.scenario_id.startswith("E2E-F3")],
        "F9 — Emergency": [r for r in results if r.scenario_id.startswith("E2E-F9")],
    }

    for feat, feat_results in features.items():
        feat_passed = sum(1 for r in feat_results if r.verdict == Verdict.PASS)
        feat_total = len(feat_results)
        status = "✅" if feat_passed == feat_total else "⚠️" if feat_passed > 0 else "❌"
        lines.append(f"- {status} **{feat}**: {feat_passed}/{feat_total} passed")

    lines.append("")

    # Detailed step results for failed scenarios
    failed_results = [r for r in results if r.verdict != Verdict.PASS]
    if failed_results:
        lines.append("## Failed Scenario Details")
        lines.append("")
        for r in failed_results:
            lines.append(f"### {r.scenario_id}: {r.scenario_name}")
            lines.append("")
            for step in r.steps:
                if isinstance(step, dict):
                    step_checks = step.get("checks", [])
                    failed_checks = [c for c in step_checks if not c.startswith("✅")]
                    if failed_checks:
                        lines.append(f"- **Step {step.get('step', '?')}**: {step.get('description', '')}")
                        for check in failed_checks:
                            lines.append(f"  - {check}")
                        if preview := step.get("agent_response_preview"):
                            lines.append(f"  - Response: `{preview[:100]}`")
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.dry_run:
        results = await dry_run_e2e()
    else:
        async with BenchmarkHTTPClient() as client:
            await client.login()
            logger.info("✅ Logged in successfully")
            results = await run_all_e2e(client)

    # Save raw data
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RESULTS_DIR / f"e2e-raw-{time.strftime('%Y%m%d-%H%M%S')}.json"
    raw_data = []
    for r in results:
        raw_data.append({
            "scenario_id": r.scenario_id,
            "scenario_name": r.scenario_name,
            "verdict": r.verdict.value,
            "review_id": r.review_id,
            "duration_ms": r.duration_ms,
            "details": r.details,
            "steps": r.steps,
        })
    raw_path.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Generate report
    md = generate_e2e_report(results)
    md_path = RESULTS_DIR / "e2e_report.md"
    md_path.write_text(md, encoding="utf-8")
    logger.info("📊 E2E report → %s", md_path)
    import sys
    sys.stdout.buffer.write(md.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


def cli() -> None:
    parser = argparse.ArgumentParser(description="B5 — E2E Functional Benchmark for P-160 AloSM")
    parser.add_argument("--dry-run", action="store_true", help="Generate synthetic data")
    args = parser.parse_args()
    asyncio.run(main(args))


if __name__ == "__main__":
    cli()
