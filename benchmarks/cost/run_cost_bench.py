"""B2 — Cost Benchmark for OlaSM.

Tracks all billable API usage across conversation scenarios and
calculates cost-per-booking, cost breakdown by component, and
token/audio consumption metrics.

Usage:
    uv run python -m benchmarks.cost.run_cost_bench [--samples N] [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from benchmarks.base import (
    BenchmarkReport,
    CostEntry,
    compute_stats,
    format_usd,
    generate_benchmark_id,
    md_table,
    save_report,
)
from benchmarks.config import (
    APIConfig,
    RESULTS_BASE,
    calculate_llm_cost,
    calculate_maps_cost,
    calculate_stt_cost,
    calculate_tts_cost,
)
from benchmarks.http_client import BenchmarkHTTPClient

logger = logging.getLogger(__name__)

RESULTS_DIR = RESULTS_BASE / "cost"


# ---------------------------------------------------------------------------
# Conversation scenarios
# ---------------------------------------------------------------------------

@dataclass
class ConversationScenario:
    """A scripted multi-turn conversation for cost measurement."""

    name: str
    description: str
    messages: list[str]
    expects_booking: bool = False


SCENARIOS: list[ConversationScenario] = [
    ConversationScenario(
        name="happy_path_one_shot",
        description="1 câu đủ info → chọn candidate → confirm",
        messages=[
            "Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm",
            "Tôi chọn Cổng chính VinUni",
            "Tôi chọn Bưu điện Hà Nội",
            "Đúng, tôi xác nhận đặt chuyến này",
        ],
        expects_booking=True,
    ),
    ConversationScenario(
        name="multi_turn_incomplete",
        description="Thiếu info, hỏi từng field qua nhiều lượt",
        messages=[
            "Đặt xe giúp tôi",
            "Đón ở VinUni",
            "Tôi chọn Cổng chính VinUni",
            "Đi Hồ Gươm",
            "Xe 4 chỗ",
            "Đúng, tôi xác nhận",
        ],
        expects_booking=True,
    ),
    ConversationScenario(
        name="correction_flow",
        description="Sửa destination sau khi đã có quote",
        messages=[
            "Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm",
            "Tôi chọn Cổng chính VinUni",
            "Tôi chọn Bưu điện Hà Nội",
            "Đổi điểm đến thành Bệnh viện Bạch Mai",
            "Tôi chọn Bệnh viện Bạch Mai cơ sở 1",
            "Đúng, tôi xác nhận đặt chuyến này",
        ],
        expects_booking=True,
    ),
    ConversationScenario(
        name="price_inquiry_only",
        description="Hỏi giá nhưng không đặt xe",
        messages=[
            "Giá từ VinUni tới Hồ Gươm bao nhiêu?",
        ],
        expects_booking=False,
    ),
    ConversationScenario(
        name="faq_query",
        description="Hỏi chính sách",
        messages=[
            "Chính sách hủy chuyến như thế nào?",
        ],
        expects_booking=False,
    ),
    ConversationScenario(
        name="handoff_request",
        description="Yêu cầu nói chuyện với tổng đài viên",
        messages=[
            "Cho tôi gặp tổng đài viên",
        ],
        expects_booking=False,
    ),
    ConversationScenario(
        name="aborted_booking",
        description="Bắt đầu đặt xe nhưng hủy giữa chừng",
        messages=[
            "Cho tôi xe 4 chỗ từ VinUni tới Hồ Gươm",
            "Tôi chọn Cổng chính VinUni",
            "Thôi, tôi không đặt nữa",
        ],
        expects_booking=False,
    ),
]


# ---------------------------------------------------------------------------
# Cost tracker
# ---------------------------------------------------------------------------

@dataclass
class ConversationCostResult:
    """Cost breakdown for one conversation run."""

    scenario_name: str
    run_index: int = 0
    total_turns: int = 0
    api_call_count: int = 0
    total_response_time_ms: float = 0.0

    # Token tracking (estimated from response)
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0

    # Audio tracking (estimated)
    estimated_stt_seconds: float = 0.0
    estimated_tts_characters: int = 0

    # Calculated costs
    llm_cost_usd: float = 0.0
    stt_cost_usd: float = 0.0
    tts_cost_usd: float = 0.0
    maps_cost_usd: float = 0.0
    total_cost_usd: float = 0.0

    booking_created: bool = False

    def calculate_costs(self, llm_provider: str = "openai") -> None:
        """Compute USD costs from tracked quantities."""
        self.llm_cost_usd = calculate_llm_cost(
            self.estimated_input_tokens,
            self.estimated_output_tokens,
            llm_provider,
        )
        self.stt_cost_usd = calculate_stt_cost(self.estimated_stt_seconds)
        self.tts_cost_usd = calculate_tts_cost(self.estimated_tts_characters)
        # Estimate 2 maps calls per booking-related conversation
        maps_calls = 2 if self.booking_created else 1
        self.maps_cost_usd = calculate_maps_cost(maps_calls)
        self.total_cost_usd = (
            self.llm_cost_usd + self.stt_cost_usd + self.tts_cost_usd + self.maps_cost_usd
        )


def estimate_tokens_from_response(response_body: dict[str, Any]) -> tuple[int, int]:
    """Heuristically estimate token usage from an API response.

    The production API may not expose token counts, so we approximate
    based on text length (1 token ≈ 4 chars for English, ≈ 2-3 for Vietnamese).
    """
    agent_message = response_body.get("message", response_body.get("response", ""))
    if isinstance(agent_message, dict):
        agent_message = json.dumps(agent_message, ensure_ascii=False)

    # Rough estimation: Vietnamese text ~2.5 chars per token
    output_chars = len(str(agent_message))
    estimated_output = max(1, output_chars // 3)

    # Input is typically 2-3x output due to system prompt + context
    estimated_input = estimated_output * 3

    return estimated_input, estimated_output


def estimate_tts_characters(response_body: dict[str, Any]) -> int:
    """Estimate TTS character count from agent response text."""
    agent_message = response_body.get("message", response_body.get("response", ""))
    if isinstance(agent_message, dict):
        agent_message = str(agent_message)
    return len(str(agent_message))


# ---------------------------------------------------------------------------
# Run benchmark
# ---------------------------------------------------------------------------

async def run_cost_benchmark(
    client: BenchmarkHTTPClient,
    n_samples: int,
) -> list[ConversationCostResult]:
    """Run all scenarios and track costs."""
    all_results: list[ConversationCostResult] = []

    for scenario in SCENARIOS:
        logger.info("\n--- Scenario: %s (%s) ---", scenario.name, scenario.description)

        for run_idx in range(n_samples):
            result = ConversationCostResult(
                scenario_name=scenario.name,
                run_index=run_idx + 1,
                total_turns=len(scenario.messages),
            )

            session_id = await client.create_session()
            result.api_call_count += 1  # session creation

            for msg in scenario.messages:
                resp = await client.send_message(session_id, msg)
                result.api_call_count += 1
                result.total_response_time_ms += resp.elapsed_ms

                # Estimate tokens
                inp, out = estimate_tokens_from_response(resp.body)
                result.estimated_input_tokens += inp
                result.estimated_output_tokens += out

                # Estimate TTS chars (agent speaks back)
                result.estimated_tts_characters += estimate_tts_characters(resp.body)

                # Estimate STT seconds (user voice input ≈ 3-5 sec per message)
                avg_stt_seconds = len(msg) / 20  # rough: 20 chars per second of speech
                result.estimated_stt_seconds += max(1.5, avg_stt_seconds)

                logger.info(
                    "  [%s] run=%d turn=%s → %dms, ~%d input + %d output tokens",
                    scenario.name, run_idx + 1, msg[:30],
                    resp.elapsed_ms, inp, out,
                )

            # Check if booking was created
            if scenario.expects_booking:
                result.booking_created = True
                result.api_call_count += 1  # quote/booking API calls

            result.calculate_costs()
            all_results.append(result)

            logger.info(
                "  [%s] run=%d TOTAL: %d calls, %d tokens, $%.4f",
                scenario.name, run_idx + 1,
                result.api_call_count,
                result.estimated_input_tokens + result.estimated_output_tokens,
                result.total_cost_usd,
            )

    return all_results


async def dry_run_cost() -> list[ConversationCostResult]:
    """Generate synthetic cost data."""
    import random

    logger.info("=== DRY RUN MODE — synthetic cost data ===")
    results: list[ConversationCostResult] = []

    for scenario in SCENARIOS:
        for run_idx in range(3):
            r = ConversationCostResult(
                scenario_name=scenario.name,
                run_index=run_idx + 1,
                total_turns=len(scenario.messages),
                api_call_count=len(scenario.messages) + 2,
                estimated_input_tokens=random.randint(800, 3000),
                estimated_output_tokens=random.randint(200, 800),
                estimated_stt_seconds=random.uniform(5, 25),
                estimated_tts_characters=random.randint(200, 1500),
                booking_created=scenario.expects_booking,
            )
            r.calculate_costs()
            r.total_response_time_ms = sum(random.uniform(500, 3000) for _ in scenario.messages)
            results.append(r)

    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_cost_report(results: list[ConversationCostResult]) -> str:
    """Build markdown cost report."""
    lines = [
        "# B2 — Cost Benchmark Report",
        "",
        f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"**Total conversation runs**: {len(results)}",
        "",
    ]

    # Group by scenario
    scenarios: dict[str, list[ConversationCostResult]] = {}
    for r in results:
        scenarios.setdefault(r.scenario_name, []).append(r)

    # Summary table
    lines.append("## Cost per Scenario")
    lines.append("")

    headers = [
        "Scenario", "Runs", "Avg Turns", "Avg API Calls",
        "Avg Tokens (in+out)", "Avg Cost/Conv", "Booking?",
    ]
    rows: list[list[str]] = []

    for name, runs in scenarios.items():
        avg_turns = sum(r.total_turns for r in runs) / len(runs)
        avg_calls = sum(r.api_call_count for r in runs) / len(runs)
        avg_tokens = sum(r.estimated_input_tokens + r.estimated_output_tokens for r in runs) / len(runs)
        avg_cost = sum(r.total_cost_usd for r in runs) / len(runs)
        has_booking = "✅" if runs[0].booking_created else "—"

        rows.append([
            f"`{name}`",
            str(len(runs)),
            f"{avg_turns:.0f}",
            f"{avg_calls:.0f}",
            f"{avg_tokens:.0f}",
            format_usd(avg_cost),
            has_booking,
        ])

    lines.append(md_table(headers, rows))
    lines.append("")

    # Cost breakdown
    lines.append("## Cost Breakdown by Component")
    lines.append("")

    all_llm = [r.llm_cost_usd for r in results if r.booking_created]
    all_stt = [r.stt_cost_usd for r in results if r.booking_created]
    all_tts = [r.tts_cost_usd for r in results if r.booking_created]
    all_maps = [r.maps_cost_usd for r in results if r.booking_created]
    all_total = [r.total_cost_usd for r in results if r.booking_created]

    if all_total:
        avg_total = sum(all_total) / len(all_total)
        lines.append(f"**Avg cost per successful booking**: {format_usd(avg_total)}")
        lines.append("")

        breakdown_headers = ["Component", "Avg Cost", "% of Total"]
        breakdown_rows = [
            ["LLM", format_usd(sum(all_llm) / len(all_llm)), f"{sum(all_llm) / sum(all_total) * 100:.1f}%"],
            ["STT", format_usd(sum(all_stt) / len(all_stt)), f"{sum(all_stt) / sum(all_total) * 100:.1f}%"],
            ["TTS", format_usd(sum(all_tts) / len(all_tts)), f"{sum(all_tts) / sum(all_total) * 100:.1f}%"],
            ["Maps", format_usd(sum(all_maps) / len(all_maps)), f"{sum(all_maps) / sum(all_total) * 100:.1f}%"],
        ]
        lines.append(md_table(breakdown_headers, breakdown_rows))
    else:
        lines.append("*No successful bookings in this benchmark run.*")

    lines.append("")

    # Token consumption
    lines.append("## Token Consumption")
    lines.append("")
    all_input_tokens = [r.estimated_input_tokens for r in results]
    all_output_tokens = [r.estimated_output_tokens for r in results]
    total_tokens = [i + o for i, o in zip(all_input_tokens, all_output_tokens)]

    token_stats = compute_stats(total_tokens, include_percentiles=len(total_tokens) >= 20)
    token_headers = ["Metric", "Value"]
    token_rows = [
        ["Mean tokens/conversation", f"{token_stats.get('mean', 0):.0f}"],
        ["Median tokens/conversation", f"{token_stats.get('median', 0):.0f}"],
        ["Min tokens", f"{token_stats.get('min', 0):.0f}"],
        ["Max tokens", f"{token_stats.get('max', 0):.0f}"],
    ]
    if "p95" in token_stats:
        token_rows.append(["p95 tokens/conversation", f"{token_stats['p95']:.0f}"])
    lines.append(md_table(token_headers, token_rows))
    lines.append("")

    # API call count
    lines.append("## API Call Statistics")
    lines.append("")
    booking_results = [r for r in results if r.booking_created]
    if booking_results:
        api_counts = [r.api_call_count for r in booking_results]
        api_stats = compute_stats([float(c) for c in api_counts], include_percentiles=False)
        lines.append(f"- **Avg API calls per successful booking**: {api_stats.get('mean', 0):.1f}")
        lines.append(f"- **Min**: {api_stats.get('min', 0):.0f}, **Max**: {api_stats.get('max', 0):.0f}")
    lines.append("")

    lines.append("> **Lưu ý**: Token counts là ước tính heuristic (≈3 chars/token cho tiếng Việt). ")
    lines.append("> Để có số chính xác, cần bật token tracking ở LLM provider hoặc đọc `usage` từ API response.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.dry_run:
        results = await dry_run_cost()
    else:
        async with BenchmarkHTTPClient() as client:
            await client.login()
            logger.info("✅ Logged in successfully")
            results = await run_cost_benchmark(client, args.samples)

    # Save raw results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RESULTS_DIR / f"cost-raw-{time.strftime('%Y%m%d-%H%M%S')}.json"
    raw_data = []
    for r in results:
        raw_data.append({
            "scenario": r.scenario_name,
            "run": r.run_index,
            "turns": r.total_turns,
            "api_calls": r.api_call_count,
            "input_tokens": r.estimated_input_tokens,
            "output_tokens": r.estimated_output_tokens,
            "stt_seconds": r.estimated_stt_seconds,
            "tts_characters": r.estimated_tts_characters,
            "llm_cost_usd": r.llm_cost_usd,
            "stt_cost_usd": r.stt_cost_usd,
            "tts_cost_usd": r.tts_cost_usd,
            "maps_cost_usd": r.maps_cost_usd,
            "total_cost_usd": r.total_cost_usd,
            "booking_created": r.booking_created,
            "response_time_ms": r.total_response_time_ms,
        })
    raw_path.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Raw data → %s", raw_path)

    # Generate markdown
    md = generate_cost_report(results)
    md_path = RESULTS_DIR / "cost_report.md"
    md_path.write_text(md, encoding="utf-8")
    logger.info("📊 Cost report → %s", md_path)
    import sys
    sys.stdout.buffer.write(md.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


def cli() -> None:
    parser = argparse.ArgumentParser(description="B2 — Cost Benchmark for OlaSM")
    parser.add_argument("--samples", type=int, default=3, help="Runs per scenario (default: 3)")
    parser.add_argument("--dry-run", action="store_true", help="Generate synthetic data")
    args = parser.parse_args()
    asyncio.run(main(args))


if __name__ == "__main__":
    cli()
