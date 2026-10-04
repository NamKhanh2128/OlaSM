"""Aggregate report generator for OlaSM benchmark suite.

Reads individual benchmark results and produces a unified markdown
dashboard suitable for Demo Day presentation.

Usage:
    uv run python -m benchmarks.report_generator
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from benchmarks.base import md_table, target_check
from benchmarks.config import RESULTS_BASE, REVIEW_TEST_MAP

logger = logging.getLogger(__name__)


def _load_report_md(path: Path) -> str:
    """Read a markdown report file, returning empty string if missing."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _count_lines_starting(report: str, prefix: str) -> int:
    """Count table rows starting with a specific prefix."""
    return sum(1 for line in report.splitlines() if line.strip().startswith(prefix))


def generate_dashboard() -> str:
    """Build the master benchmark dashboard."""
    lines = [
        "# 📊 OlaSM — Benchmark Dashboard",
        "",
        f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "",
        "---",
        "",
    ]

    # --- Executive Summary ---
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("Benchmark suite đo lường 5 khía cạnh của sản phẩm OlaSM theo yêu cầu review:")
    lines.append("")

    summary_items = [
        ("B1 — Latency", "Đo độ trễ từng component và E2E", "benchmarks/results/latency/latency_report.md"),
        ("B2 — Cost", "Chi phí per booking, token consumption", "benchmarks/results/cost/cost_report.md"),
        ("B3 — Stability", "Error rate, recovery, idempotency", "benchmarks/results/stability/stability_report.md"),
        ("B4 — AI Accuracy", "Entity extraction, intent, safety", "benchmarks/results/ai_accuracy/accuracy_report.md"),
        ("B5 — E2E Functional", "Happy path, correction, handoff, FAQ, emergency", "benchmarks/results/e2e/e2e_report.md"),
    ]

    headers = ["Module", "Đo gì", "Report"]
    rows = []
    for name, desc, path in summary_items:
        full_path = RESULTS_BASE.parent.parent / path
        exists = "✅" if full_path.exists() else "⏳ Chưa chạy"
        rows.append([f"**{name}**", desc, exists])

    lines.append(md_table(headers, rows))
    lines.append("")

    # --- Include individual reports ---
    lines.append("---")
    lines.append("")

    report_files = [
        ("B1 — Latency", RESULTS_BASE / "latency" / "latency_report.md"),
        ("B2 — Cost", RESULTS_BASE / "cost" / "cost_report.md"),
        ("B3 — Stability", RESULTS_BASE / "stability" / "stability_report.md"),
        ("B4 — AI Accuracy", RESULTS_BASE / "ai_accuracy" / "accuracy_report.md"),
        ("B5 — E2E Functional", RESULTS_BASE / "e2e" / "e2e_report.md"),
    ]

    for title, report_path in report_files:
        content = _load_report_md(report_path)
        if content:
            # Embed the report content, adjusting heading levels
            adjusted = content.replace("# B", "## B")  # Demote top heading
            lines.append(adjusted)
            lines.append("")
            lines.append("---")
            lines.append("")
        else:
            lines.append(f"## {title}")
            lines.append("")
            lines.append(f"> ⏳ Benchmark chưa được chạy. Chạy module tương ứng để tạo report.")
            lines.append("")
            lines.append("---")
            lines.append("")

    # --- OlaSM Review Regression Map ---
    lines.append("## Mapping với OlaSM Review Test Catalog")

    lines.append("")
    lines.append("Bảng so sánh kết quả benchmark với verdict cuối cùng từ review:")
    lines.append("")

    reg_headers = ["Review ID", "Mô tả", "Review Status", "Benchmark Relevance"]
    reg_rows: list[list[str]] = []

    for review_id, info in sorted(REVIEW_TEST_MAP.items()):
        status = info["status"]
        desc = info["desc"]
        status_icon = {
            "PASS": "✅",
            "FAIL": "❌",
            "BLOCKED": "⚫",
            "NOT_RUN": "⚪",
        }.get(status, "❓")

        # Determine which benchmark covers this
        coverage = []
        if "entity" in desc.lower() or "extraction" in desc.lower() or "code-switch" in desc.lower():
            coverage.append("B4")
        if "booking" in desc.lower() or "correction" in desc.lower():
            coverage.append("B5")
        if "handoff" in desc.lower() or "operator" in desc.lower():
            coverage.append("B5")
        if "emergency" in desc.lower() or "safety" in desc.lower():
            coverage.append("B4, B5")
        if "policy" in desc.lower() or "faq" in desc.lower() or "grounding" in desc.lower():
            coverage.append("B4")
        if "idempotency" in desc.lower() or "confirm" in desc.lower():
            coverage.append("B3, B5")
        if "recovery" in desc.lower() or "reconnect" in desc.lower():
            coverage.append("B3")
        if "asr" in desc.lower() or "accent" in desc.lower() or "barge" in desc.lower():
            coverage.append("B1 (cần audio)")
        if "mic" in desc.lower():
            coverage.append("B5 (UI)")

        reg_rows.append([
            f"`{review_id}`",
            desc,
            f"{status_icon} {status}",
            ", ".join(coverage) if coverage else "—",
        ])

    lines.append(md_table(reg_headers, reg_rows))
    lines.append("")

    # --- Demo Day Metrics Summary ---
    lines.append("## Demo Day Presentation Metrics")
    lines.append("")
    lines.append("Các chỉ số cần trình bày tại Demo Day (10 phút):")
    lines.append("")
    lines.append("### 1. Painpoints đã giải quyết")
    lines.append("- Voice booking: Đặt xe bằng giọng nói cho người lớn tuổi/bận tay")
    lines.append("- Multi-turn context: Giữ context qua nhiều lượt hội thoại")
    lines.append("- Safety: Phát hiện emergency và handoff tổng đài viên")
    lines.append("")
    lines.append("### 2. Độ tin cậy (từ B3 & B4)")
    lines.append("- Error rate: `<target>` → xem B3 report")
    lines.append("- AI accuracy: `<target>` → xem B4 report")
    lines.append("- Session recovery rate: `<target>` → xem B3 report")
    lines.append("- Booking idempotency: `<target>` → xem B3 report")
    lines.append("")
    lines.append("### 3. Performance (từ B1 & B2)")
    lines.append("- E2E latency p50/p95: `<value>` → xem B1 report")
    lines.append("- Cost per booking: `<value>` → xem B2 report")
    lines.append("- Tokens per conversation: `<value>` → xem B2 report")
    lines.append("")
    lines.append("### 4. Hướng phát triển")
    lines.append("- Hoàn thiện one-shot entity extraction (hiện FAIL)")
    lines.append("- Code-switch handling (hiện FAIL)")
    lines.append("- Operator UI cho handoff flow (hiện BLOCKED)")
    lines.append("- Audio injection test cho ASR accent/noise (hiện BLOCKED)")
    lines.append("- Production deployment với monitoring")
    lines.append("")

    lines.append("> **Lưu ý**: Thay `<target>` và `<value>` bằng số thực tế sau khi chạy benchmark.")

    return "\n".join(lines)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    dashboard = generate_dashboard()

    output_dir = RESULTS_BASE / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "benchmark_summary.md"
    output_path.write_text(dashboard, encoding="utf-8")

    logger.info("📊 Dashboard → %s", output_path)
    import sys
    preview = dashboard[:2000] + "\n\n... (truncated, see full file)"
    sys.stdout.buffer.write(preview.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
