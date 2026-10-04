"""Configuration and pricing tables for OlaSM benchmarks.

All pricing is approximate and should be updated to match actual provider
contracts before running cost benchmarks.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks"
RESULTS_BASE = BENCHMARKS_DIR / "results"


# ---------------------------------------------------------------------------
# API / Provider config — read from environment
# ---------------------------------------------------------------------------

@dataclass
class APIConfig:
    """Connection details pulled from environment variables."""

    # Backend
    base_url: str = ""
    staging_url: str = ""

    # Auth
    demo_phone: str = "0901234567"
    demo_password: str = "Password123!"

    # LLM
    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: str = ""

    # STT
    stt_provider: str = ""
    stt_model: str = ""

    # TTS
    tts_provider: str = ""
    tts_model: str = ""
    tts_voice: str = ""

    # LiveKit
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    @classmethod
    def from_env(cls) -> "APIConfig":
        """Build config from current environment (or .env file)."""
        return cls(
            base_url=os.getenv("VITE_API_URL", "http://localhost:8000"),
            staging_url=os.getenv("STAGING_URL", "https://staging.alosm.nairyuuu.site"),
            llm_base_url=os.getenv("AGENT_LLM_BASE_URL", ""),
            llm_model=os.getenv("AGENT_LLM_MODEL", ""),
            llm_api_key=os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", ""),
            stt_provider=os.getenv("LIVEKIT_STT_PROVIDER", "deepgram"),
            stt_model=os.getenv("LIVEKIT_STT_MODEL", "nova-2"),
            tts_provider=os.getenv("LIVEKIT_TTS_PROVIDER", "openai"),
            tts_model=os.getenv("LIVEKIT_TTS_MODEL", ""),
            tts_voice=os.getenv("LIVEKIT_TTS_VOICE", ""),
            livekit_url=os.getenv("LIVEKIT_URL", ""),
            livekit_api_key=os.getenv("LIVEKIT_API_KEY", ""),
            livekit_api_secret=os.getenv("LIVEKIT_API_SECRET", ""),
        )


# ---------------------------------------------------------------------------
# Pricing table  (approximate — update per actual provider contracts)
# ---------------------------------------------------------------------------

@dataclass
class PricingEntry:
    provider: str
    service: str
    unit: str
    price_per_unit_usd: float
    notes: str = ""


# fmt: off
DEFAULT_PRICING: list[PricingEntry] = [
    # LLM
    PricingEntry("openai",       "llm_input",   "1M_tokens",   2.50,   "GPT-4o input"),
    PricingEntry("openai",       "llm_output",  "1M_tokens",  10.00,   "GPT-4o output"),
    PricingEntry("openrouter",   "llm_input",   "1M_tokens",   2.50,   "Via OpenRouter, model-dependent"),
    PricingEntry("openrouter",   "llm_output",  "1M_tokens",  10.00,   "Via OpenRouter, model-dependent"),

    # STT
    PricingEntry("deepgram",     "stt",         "minute",      0.0059, "Nova-2 Vietnamese"),
    PricingEntry("openai",       "stt",         "minute",      0.006,  "Whisper"),
    PricingEntry("google",       "stt",         "minute",      0.006,  "Chirp"),

    # TTS
    PricingEntry("openai",       "tts",         "1M_chars",   15.00,   "tts-1"),
    PricingEntry("elevenlabs",   "tts",         "1M_chars",   30.00,   "Turbo v2"),

    # Maps / Geocoding
    PricingEntry("google_maps",  "geocoding",   "1K_requests", 5.00,   "Geocoding API"),
    PricingEntry("google_maps",  "directions",  "1K_requests", 5.00,   "Directions API"),
    PricingEntry("google_maps",  "distance",    "1K_requests", 5.00,   "Distance Matrix API"),

    # LiveKit (usage-based, approximate)
    PricingEntry("livekit",      "room",        "minute",      0.004,  "Audio room per participant-minute"),
]
# fmt: on


def get_price(provider: str, service: str) -> float:
    """Look up price-per-unit for a provider/service combo."""
    for entry in DEFAULT_PRICING:
        if entry.provider == provider and entry.service == service:
            return entry.price_per_unit_usd
    return 0.0


def calculate_llm_cost(
    input_tokens: int,
    output_tokens: int,
    provider: str = "openai",
) -> float:
    """Return total LLM cost in USD."""
    input_price = get_price(provider, "llm_input")   # per 1M tokens
    output_price = get_price(provider, "llm_output")  # per 1M tokens
    return (input_tokens / 1_000_000 * input_price) + (output_tokens / 1_000_000 * output_price)


def calculate_stt_cost(
    duration_seconds: float,
    provider: str = "deepgram",
) -> float:
    """Return total STT cost in USD."""
    price_per_min = get_price(provider, "stt")
    return (duration_seconds / 60) * price_per_min


def calculate_tts_cost(
    character_count: int,
    provider: str = "openai",
) -> float:
    """Return total TTS cost in USD."""
    price_per_1m = get_price(provider, "tts")
    return (character_count / 1_000_000) * price_per_1m


def calculate_maps_cost(
    request_count: int,
    service: str = "geocoding",
) -> float:
    """Return total Maps API cost in USD."""
    price_per_1k = get_price("google_maps", service)
    return (request_count / 1000) * price_per_1k


# ---------------------------------------------------------------------------
# Latency targets (from latency-remediation-plan.md)
# ---------------------------------------------------------------------------

@dataclass
class LatencyTarget:
    metric: str
    p50_ms: float
    p95_ms: float
    description: str = ""


LATENCY_TARGETS: list[LatencyTarget] = [
    LatencyTarget("stt_latency",              800,  1500, "End-of-speech → transcript final"),
    LatencyTarget("llm_ttft",                 500,  1200, "Prompt → first token"),
    LatencyTarget("llm_total",                800,  1500, "Prompt → complete response"),
    LatencyTarget("tts_ttfb",                 600,  1200, "Text → first audio byte"),
    LatencyTarget("tool_execution",           200,   500, "Single tool call"),
    LatencyTarget("e2e_voice_no_tool",       1800,  3500, "End-of-speech → audio (no tool)"),
    LatencyTarget("e2e_voice_with_tool",     3000,  5500, "End-of-speech → audio (with tool)"),
    LatencyTarget("backend_api",              100,   300, "REST endpoint response"),
    LatencyTarget("place_search",             300,   800, "Place query → candidates"),
]


def get_target(metric: str) -> LatencyTarget | None:
    for t in LATENCY_TARGETS:
        if t.metric == metric:
            return t
    return None


# ---------------------------------------------------------------------------
# Review test catalog mapping
# ---------------------------------------------------------------------------

REVIEW_TEST_MAP: dict[str, dict[str, str]] = {
    "P160-F1-HAPPY-001": {"status": "PASS",    "desc": "One-shot booking, entity normalized"},
    "P160-F1-EDGE-002":  {"status": "PASS",    "desc": "Incomplete booking multi-turn"},
    "P160-F1-AI-003":    {"status": "PASS",    "desc": "Ambiguous place disambiguation"},
    "P160-F1-UNHAPPY-004": {"status": "PASS",  "desc": "Correction invalidates quote"},
    "P160-F1-EDGE-005":  {"status": "PASS",    "desc": "Explicit confirm + idempotency"},
    "P160-F1-UNHAPPY-006": {"status": "PASS",  "desc": "Microphone fallback to UI text"},
    "P160-F1-AI-007":    {"status": "BLOCKED", "desc": "Low-confidence ASR hardware lab"},
    "P160-F1-EDGE-008":  {"status": "PASS",    "desc": "Reconnect before confirm restored"},
    "P160-F1-AI-009":    {"status": "PASS",    "desc": "Barge-in correction handling"},
    "P160-F1-AI-010":    {"status": "BLOCKED", "desc": "Extreme accent/noise lab testing"},
    "P160-F1-AI-901":    {"status": "PASS",    "desc": "Address context auto-inferred"},
    "P160-F1-AI-902":    {"status": "PASS",    "desc": "Code-switch entity extraction"},
    "P160-F1-AI-903":    {"status": "PASS",    "desc": "Mid-flow correction retention"},
    "P160-F2-HAPPY-001": {"status": "PASS",    "desc": "Explicit handoff"},
    "P160-F2-UNHAPPY-002": {"status": "PASS",  "desc": "Repeated ASR fallback to agent"},
    "P160-F2-EDGE-003":  {"status": "BLOCKED", "desc": "Operator takeover concurrency lock"},
    "P160-F2-SEC-004":   {"status": "PASS",    "desc": "Handoff privacy masking"},
    "P160-F3-HAPPY-001": {"status": "PASS",    "desc": "Price-only query handled"},
    "P160-F3-HAPPY-002": {"status": "PASS",    "desc": "Trip status lookup"},
    "P160-F3-AI-003":    {"status": "PASS",    "desc": "Policy grounding with citation"},
    "P160-F3-UNHAPPY-004": {"status": "PASS",  "desc": "Missing policy, refers to human"},
    "P160-F3-AI-904":    {"status": "PASS",    "desc": "Negative confirmation"},
    "P160-F3-AI-905":    {"status": "PASS",    "desc": "Duplicate confirmation"},
    "P160-F9-HAPPY-001": {"status": "PASS",    "desc": "Emergency interrupts booking"},
    "P160-F9-UNHAPPY-002": {"status": "PASS",  "desc": "Emergency without GPS fallback"},
    "P160-F9-READINESS-003": {"status": "PASS","desc": "Full incident AC confirmed"},
    "P160-F9-AI-906":    {"status": "PASS",    "desc": "Emergency disambiguation immediate"},
    "P160-XFLOW-001":    {"status": "PASS",    "desc": "Correction-to-handoff flow"},
}
