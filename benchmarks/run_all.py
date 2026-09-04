"""Run all benchmarks and generate unified dashboard.

Usage:
    uv run python -m benchmarks.run_all [--dry-run] [--samples N]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


BENCHMARK_MODULES = [
    ("B1 — Latency",    "benchmarks.latency.run_latency_bench"),
    ("B2 — Cost",       "benchmarks.cost.run_cost_bench"),
    ("B3 — Stability",  "benchmarks.stability.run_stability_bench"),
    ("B4 — AI Accuracy","benchmarks.ai_accuracy.run_accuracy_bench"),
    ("B5 — E2E",        "benchmarks.e2e.run_e2e_bench"),
]


def run_module(module: str, extra_args: list[str]) -> int:
    """Run a benchmark module as a subprocess."""
    cmd = [sys.executable, "-m", module] + extra_args
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(Path(__file__).resolve().parents[1]))
    return result.returncode


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Run all P-160 benchmarks")
    parser.add_argument("--dry-run", action="store_true", help="Synthetic data mode")
    parser.add_argument("--samples", type=int, default=10, help="Samples per benchmark")
    parser.add_argument("--skip", nargs="*", default=[], help="Module names to skip (e.g. B1 B2)")
    args = parser.parse_args()

    extra = []
    if args.dry_run:
        extra.append("--dry-run")
    if args.samples:
        extra.extend(["--samples", str(args.samples)])

    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    results: dict[str, str] = {}

    for name, module in BENCHMARK_MODULES:
        short = name.split("—")[0].strip()
        if short in args.skip:
            logger.info("Skipping %s", name)
            results[name] = "SKIPPED"
            continue

        logger.info("\n{'=' * 60}")
        logger.info("Running %s", name)
        logger.info("{'=' * 60}\n")

        # Latency and cost accept --samples; accuracy and e2e don't
        module_args = list(extra)
        if "accuracy" in module or "e2e" in module:
            module_args = ["--dry-run"] if args.dry_run else []

        rc = run_module(module, module_args)
        results[name] = "[PASS]" if rc == 0 else f"[FAIL EXIT {rc}]"

    # Generate unified dashboard
    logger.info("\n{'=' * 60}")
    logger.info("Generating Dashboard")
    logger.info("{'=' * 60}\n")

    rc = run_module("benchmarks.report_generator", [])
    results["Dashboard"] = "[PASS]" if rc == 0 else f"[FAIL EXIT {rc}]"

    # Generate visual charts
    logger.info("\n{'=' * 60}")
    logger.info("Generating Visual Charts")
    logger.info("{'=' * 60}\n")
    try:
        rc_charts = run_module("benchmarks.chart_generator", [])
        results["Visual Charts"] = "[PASS]" if rc_charts == 0 else f"[WARN EXIT {rc_charts}]"
    except Exception as e:
        logger.warning("Could not generate charts: %s", e)

    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK SUITE SUMMARY")
    print("=" * 60)
    for name, status in results.items():
        print(f"  {name:30s} {status}")
    print("=" * 60)


if __name__ == "__main__":
    main()
