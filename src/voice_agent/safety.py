"""Versioned safety policy and fast classifier for high-risk voice turns."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_SAFETY_POLICY_PATH = PROJECT_ROOT / "data" / "safety" / "emergency_policy.yaml"
STATIC_SAFETY_POLICY_PATH = PROJECT_ROOT / "config" / "safety" / "emergency_policy.yaml"
DEFAULT_SAFETY_POLICY_PATH = (
    DATA_SAFETY_POLICY_PATH if DATA_SAFETY_POLICY_PATH.is_file() else STATIC_SAFETY_POLICY_PATH
)


class EmergencySafetyRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: Literal["EMERGENCY"]
    risk_level: Literal["CRITICAL"]
    priority: int = Field(ge=1, le=100)
    severity: Literal["CRITICAL"]
    queue: str = Field(min_length=1)
    requires_immediate_transfer: bool
    signals: list[str] = Field(min_length=1)
    guidance: str = Field(min_length=1)


class SafetyPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"]
    policy_version: str = Field(min_length=1)
    status: Literal["APPROVED"]
    emergency: EmergencySafetyRule


@lru_cache(maxsize=4)
def load_safety_policy(path: str | Path = DEFAULT_SAFETY_POLICY_PATH) -> SafetyPolicy:
    policy_path = Path(path)
    if not policy_path.is_file():
        raise RuntimeError(f"safety policy not found: {policy_path}")
    try:
        raw = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        return SafetyPolicy.model_validate(raw)
    except Exception as exc:
        raise RuntimeError(f"invalid safety policy {policy_path}: {exc}") from exc


def normalize_user_text(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    without_marks = "".join(char for char in folded if not unicodedata.combining(char))
    return " ".join(without_marks.replace("đ", "d").split())


@dataclass(frozen=True)
class SafetyAssessment:
    reason_code: str
    priority: int
    severity: str
    queue: str
    requires_immediate_transfer: bool

    @property
    def is_emergency(self) -> bool:
        return self.reason_code == "EMERGENCY"


class SafetyClassifier:
    """Small, cached policy adapter used before the LiveKit LLM turn."""

    def __init__(self, policy: SafetyPolicy | None = None) -> None:
        self.policy = policy or load_safety_policy()
        self._signals = tuple(
            normalized
            for signal in self.policy.emergency.signals
            if (normalized := normalize_user_text(signal))
        )
        if not self._signals:
            raise ValueError("safety policy must define at least one non-empty signal")

    def assess(self, text: str) -> SafetyAssessment:
        normalized = normalize_user_text(text)
        rule = self.policy.emergency
        if any(signal in normalized for signal in self._signals):
            return SafetyAssessment(
                reason_code=rule.reason_code,
                priority=rule.priority,
                severity=rule.severity,
                queue=rule.queue,
                requires_immediate_transfer=rule.requires_immediate_transfer,
            )
        return SafetyAssessment(
            reason_code="USER_REQUEST",
            priority=60,
            severity="NORMAL",
            queue="GENERAL_OPERATOR",
            requires_immediate_transfer=False,
        )

    def emergency_guidance(self) -> str:
        return self.policy.emergency.guidance


@lru_cache(maxsize=1)
def get_default_safety_classifier() -> SafetyClassifier:
    return SafetyClassifier()


def assess_user_safety(text: str, classifier: SafetyClassifier | None = None) -> SafetyAssessment:
    return (classifier or get_default_safety_classifier()).assess(text)


def emergency_guidance(classifier: SafetyClassifier | None = None) -> str:
    return (classifier or get_default_safety_classifier()).emergency_guidance()
