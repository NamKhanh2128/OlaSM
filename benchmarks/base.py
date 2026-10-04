"""Base classes and utilities for OlaSM benchmark suite.

Provides TimingResult, CostEntry, statistical helpers, and report
formatting shared by all benchmark modules.
"""

from __future__ import annotations

import json
import math
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def percentile(data: list[float], pct: int) -> float:
    """Return the *pct*-th percentile of *data* using interpolation."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * pct / 100
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)


def compute_stats(values: list[float], *, include_percentiles: bool = True) -> dict[str, float]:
    """Compute min/max/mean/median and optional p50/p95/p99.

    Percentiles are only reported when *include_percentiles* is ``True``
    **and** there are at least 20 samples (per mentor guidance).
    """
    if not values:
        return {}
    stats: dict[str, float] = {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
    }
    if include_percentiles and len(values) >= 20:
        stats["p50"] = percentile(values, 50)
        stats["p95"] = percentile(values, 95)
        stats["p99"] = percentile(values, 99)
    return stats


# ---------------------------------------------------------------------------
# Core data classes
# ---------------------------------------------------------------------------

class BenchmarkCategory(str, Enum):
    LATENCY = "latency"
    COST = "cost"
    STABILITY = "stability"
    AI_ACCURACY = "ai_accuracy"
    E2E = "e2e"
    SCALABILITY = "scalability"


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    FLAKY = "FLAKY"
    BLOCKED = "BLOCKED"
    NOT_RUN = "NOT_RUN"


@dataclass
class TimingResult:
    """A single latency measurement."""

    label: str
    start_epoch: float = 0.0
    end_epoch: float = 0.0
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def start(self) -> "TimingResult":
        self.start_epoch = time.perf_counter()
        return self

    def stop(self) -> "TimingResult":
        self.end_epoch = time.perf_counter()
        self.duration_ms = (self.end_epoch - self.start_epoch) * 1000
        return self


@dataclass
class CostEntry:
    """One billable usage record."""

    provider: str
    service: str  # "llm", "stt", "tts", "maps"
    unit: str  # "tokens", "seconds", "characters", "requests"
    quantity: float = 0.0
    unit_price_usd: float = 0.0
    total_cost_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def calculate(self) -> "CostEntry":
        self.total_cost_usd = self.quantity * self.unit_price_usd
        return self


@dataclass
class AccuracyCase:
    """A single accuracy evaluation case with expected vs actual."""

    case_id: str
    category: str
    input_text: str
    expected: dict[str, Any] = field(default_factory=dict)
    actual: dict[str, Any] = field(default_factory=dict)
    is_correct: bool = False
    details: str = ""
    review_id: str = ""  # Maps to P160-F1-HAPPY-001 etc.


@dataclass
class StabilityEvent:
    """One request/response cycle for stability tracking."""

    request_id: str
    scenario: str
    timestamp_iso: str = ""
    success: bool = False
    error_type: str = ""  # stt_no_final, llm_timeout, tts_error, backend_500
    response_time_ms: float = 0.0
    details: str = ""


@dataclass
class E2EScenarioResult:
    """Result of one end-to-end scenario run."""

    scenario_id: str
    scenario_name: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    verdict: Verdict = Verdict.NOT_RUN
    review_id: str = ""
    duration_ms: float = 0.0
    details: str = ""


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkReport:
    """Top-level benchmark report aggregating all modules."""

    benchmark_id: str = ""
    generated_at: str = ""
    category: str = ""
    component: str = ""
    provider: str = ""
    model: str = ""
    sample_count: int = 0
    results: dict[str, Any] = field(default_factory=dict)
    raw_values: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)


def generate_benchmark_id(category: str) -> str:
    """Generate a timestamped benchmark ID."""
    now = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    return f"{category}-{now}"


def save_report(report: BenchmarkReport, output_dir: Path) -> Path:
    """Write a benchmark report to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{report.benchmark_id}.json"
    path = output_dir / filename
    path.write_text(report.to_json(), encoding="utf-8")
    return path


def load_report(path: Path) -> BenchmarkReport:
    """Load a benchmark report from JSON."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return BenchmarkReport(**data)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_ms(value: float) -> str:
    """Human-readable millisecond value."""
    if value < 1000:
        return f"{value:.0f}ms"
    return f"{value / 1000:.2f}s"


def format_usd(value: float) -> str:
    """Human-readable USD value."""
    if value < 0.01:
        return f"${value:.4f}"
    return f"${value:.2f}"


def target_check(actual: float, target: float, *, lower_is_better: bool = True) -> str:
    """Return ✅ or ❌ comparing actual to target."""
    if lower_is_better:
        return "✅" if actual <= target else "❌"
    return "✅" if actual >= target else "❌"


# ---------------------------------------------------------------------------
# Markdown table builder
# ---------------------------------------------------------------------------

def md_table(headers: list[str], rows: list[list[str]]) -> str:
    """Build a simple markdown table."""
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)
