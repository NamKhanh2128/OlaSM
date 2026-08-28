"""Offline concurrent load test for the deterministic Core Agent workflows.

This intentionally does not start FastAPI and does not call OpenAI, LiveKit,
Google, Maps, Redis, Supabase, or any other network provider.  It reuses the
same scripted workflow/evaluation seam used by ``eval_cases`` and runs each
case in a separate worker process so the legacy in-memory SessionService state
cannot leak between concurrent scenarios.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import multiprocessing
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from eval_cases.run_agent_workflow_evals import CASE_DEFINITIONS, CaseDefinition, execute_case  # noqa: E402

DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts" / "load-test" / "offline-load.json"


def percentile(values: list[float], quantile: float) -> float:
    """Return a linearly interpolated percentile for a non-empty sample."""

    if not values:
        raise ValueError("percentile requires at least one value")
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between 0 and 1")
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _definition_by_slug(slug: str) -> CaseDefinition:
    for definition in CASE_DEFINITIONS:
        if definition.slug == slug:
            return definition
    raise ValueError(f"unknown scenario: {slug}")


def build_plan(scenario: str, iterations: int) -> list[str]:
    """Build a deterministic round-robin scenario plan."""

    if iterations < 1:
        raise ValueError("iterations must be at least 1")
    if scenario == "all":
        slugs = [definition.slug for definition in CASE_DEFINITIONS]
    else:
        _definition_by_slug(scenario)
        slugs = [scenario]
    return [slugs[index % len(slugs)] for index in range(iterations)]


def _run_case(slug: str) -> dict[str, Any]:
    """Run one case in a spawned process and return only safe load-test data."""

    definition = _definition_by_slug(slug)
    started = time.perf_counter()
    try:
        result = asyncio.run(execute_case(definition))
        return {
            "scenario": slug,
            "status": result.get("status", "error"),
            "case_duration_ms": float(result.get("duration_ms", 0.0)),
            "worker_error": None,
            "observed_ms": (time.perf_counter() - started) * 1000,
        }
    except Exception as exc:  # pragma: no cover - defensive process boundary
        return {
            "scenario": slug,
            "status": "error",
            "case_duration_ms": 0.0,
            "worker_error": f"{type(exc).__name__}: {exc}",
            "observed_ms": (time.perf_counter() - started) * 1000,
        }


def _summary(results: list[dict[str, Any]], *, iterations: int, concurrency: int, scenario: str) -> dict[str, Any]:
    durations = [float(result["observed_ms"]) for result in results]
    passed = sum(result["status"] == "passed" for result in results)
    failed = sum(result["status"] == "failed" for result in results)
    errors = sum(result["status"] == "error" for result in results)
    return {
        "iterations": iterations,
        "concurrency": concurrency,
        "scenario": scenario,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "success_rate": round(passed / iterations, 6),
        "error_rate": round((failed + errors) / iterations, 6),
        "latency_ms": {
            "p50": round(percentile(durations, 0.50), 3),
            "p95": round(percentile(durations, 0.95), 3),
            "p99": round(percentile(durations, 0.99), 3),
            "max": round(max(durations), 3),
        },
        "status_counts": {
            "passed": passed,
            "failed": failed,
            "error": errors,
        },
    }


def run_load_test(*, scenario: str, iterations: int, concurrency: int) -> dict[str, Any]:
    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")
    plan = build_plan(scenario, iterations)
    results: list[dict[str, Any]] = []
    process_context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=concurrency, mp_context=process_context) as executor:
        futures = [executor.submit(_run_case, slug) for slug in plan]
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda result: (str(result["scenario"]), float(result["observed_ms"])))
    summary = _summary(results, iterations=iterations, concurrency=concurrency, scenario=scenario)
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "offline_deterministic_agent_workflow_load",
        "python": platform.python_version(),
        "summary": summary,
        "results": results,
        "network_calls": False,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run concurrent offline Agent workflow load tests.")
    parser.add_argument(
        "--scenario",
        choices=["all", *(definition.slug for definition in CASE_DEFINITIONS)],
        default="all",
        help="Scenario to repeat; 'all' rotates through every deterministic case.",
    )
    parser.add_argument("--iterations", type=int, default=100, help="Total workflow executions.")
    parser.add_argument("--concurrency", type=int, default=4, help="Concurrent worker processes.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="JSON artifact path.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    artifact = run_load_test(
        scenario=args.scenario,
        iterations=args.iterations,
        concurrency=args.concurrency,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact["summary"], ensure_ascii=False, indent=2))
    print(f"artifact={args.output}")
    return 0 if artifact["summary"]["errors"] == 0 and artifact["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
