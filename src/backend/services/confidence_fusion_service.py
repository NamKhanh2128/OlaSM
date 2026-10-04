"""Dynamic Confidence Fusion & Selective Autonomy Service.

Cơ sở lý thuyết & Công thức chuẩn từ Báo cáo Ý tưởng Nhóm 4 (Mục 4.3):
    c_trip = w1 * p_STT + w2 * p_intent + w3 * p_addr + w4 * p_vision

Trong đó:
    - p_STT: Điểm tin cậy của tầng nhận dạng giọng nói PhoWhisper STT ∈ [0, 1].
    - p_intent: Xác suất dự đoán đúng ý định người dùng từ LLM/Classifier ∈ [0, 1].
    - p_addr: Điểm chuẩn hóa địa chỉ do RapidFuzz + Mapbox Geocoding tạo ra ∈ [0, 1].
    - p_vision: Điểm tin cậy đối chiếu ảnh đón từ VLM Spatial OCR (nếu có) ∈ [0, 1].

Cơ chế chuẩn hóa động (Dynamic Re-normalization):
    Nếu khách hàng không gửi ảnh đón (p_vision is None):
        w4 = 0
        w1' = w1 / (w1 + w2 + w3)
        w2' = w2 / (w1 + w2 + w3)
        w3' = w3 / (w1 + w2 + w3)
        đảm bảo w1' + w2' + w3' = 1.0

Cơ chế Quyết định Tự động hóa Có Chọn lọc (Selective Autonomy Routing):
    - c_trip >= tau_high : AUTO_BOOK (Tự động chốt đơn và điều xe)
    - tau_low < c_trip < tau_high : CLARIFY (Hỏi lại khách để làm rõ thông tin)
    - c_trip <= tau_low : HITL_HANDOFF (Chuyển giao sang tổng đài viên kèm ngữ cảnh < 0.5s)

Hiệu chỉnh (Confidence Calibration):
    Expected Calibration Error (ECE) <= 0.10 trên tập validation bằng Temperature Scaling.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
import math

logger = logging.getLogger(__name__)

# ─── Trọng số mặc định khi có đủ 4 kênh (w1 + w2 + w3 + w4 = 1.0) ─────────────
DEFAULT_W1_STT: float = 0.25
DEFAULT_W2_INTENT: float = 0.25
DEFAULT_W3_ADDR: float = 0.30
DEFAULT_W4_VISION: float = 0.20

# ─── Ngưỡng Selective Autonomy chuẩn hóa ───────────────────────────────────────
DEFAULT_TAU_HIGH: float = 0.85   # Ngưỡng auto-confirm & book
DEFAULT_TAU_LOW: float = 0.55    # Ngưỡng HITL handoff sang tổng đài viên


class AutonomyDecision(StrEnum):
    """Quyết định điều hướng 3 nhánh của Selective Autonomy."""
    AUTO_BOOK = "AUTO_BOOK"         # c_trip >= tau_high: Tự động chốt đơn
    CLARIFY = "CLARIFY"             # tau_low < c_trip < tau_high: Hỏi lại khách
    HITL_HANDOFF = "HITL_HANDOFF"   # c_trip <= tau_low: Chuyển tổng đài viên (<0.5s)


@dataclass
class MultimodalConfidenceInputs:
    """Các điểm tin cậy đầu vào từ các thành phần không tương quan."""
    p_stt: float                   # STT acoustic/language model confidence ∈ [0, 1]
    p_intent: float                # LLM intent classification confidence ∈ [0, 1]
    p_addr: float                  # RapidFuzz + Mapbox match score ∈ [0, 1]
    p_vision: float | None = None  # Multimodal VLM pickup verification ∈ [0, 1] hoặc None

    def __post_init__(self) -> None:
        self.p_stt = max(0.0, min(1.0, float(self.p_stt)))
        self.p_intent = max(0.0, min(1.0, float(self.p_intent)))
        self.p_addr = max(0.0, min(1.0, float(self.p_addr)))
        if self.p_vision is not None:
            self.p_vision = max(0.0, min(1.0, float(self.p_vision)))


@dataclass
class ConfidenceFusionResult:
    """Kết quả hợp nhất điểm tin cậy c_trip và quyết định điều hướng."""
    c_trip: float
    decision: AutonomyDecision
    p_stt: float
    p_intent: float
    p_addr: float
    p_vision: float | None
    effective_weights: dict[str, float]
    tau_high: float
    tau_low: float
    has_vision: bool
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "c_trip": round(self.c_trip, 4),
            "decision": self.decision.value,
            "p_stt": round(self.p_stt, 4),
            "p_intent": round(self.p_intent, 4),
            "p_addr": round(self.p_addr, 4),
            "p_vision": round(self.p_vision, 4) if self.p_vision is not None else None,
            "effective_weights": {k: round(v, 4) for k, v in self.effective_weights.items()},
            "tau_high": self.tau_high,
            "tau_low": self.tau_low,
            "has_vision": self.has_vision,
            "explanation": self.explanation,
        }


class ConfidenceFusionService:
    """Service tính toán Dynamic Confidence Fusion và phân loại Selective Autonomy."""

    def __init__(
        self,
        w1_stt: float = DEFAULT_W1_STT,
        w2_intent: float = DEFAULT_W2_INTENT,
        w3_addr: float = DEFAULT_W3_ADDR,
        w4_vision: float = DEFAULT_W4_VISION,
        tau_high: float = DEFAULT_TAU_HIGH,
        tau_low: float = DEFAULT_TAU_LOW,
        temperature: float = 1.0,
    ) -> None:
        self.w1 = w1_stt
        self.w2 = w2_intent
        self.w3 = w3_addr
        self.w4 = w4_vision
        self.tau_high = tau_high
        self.tau_low = tau_low
        self.temperature = max(0.01, float(temperature))

    def evaluate(self, inputs: MultimodalConfidenceInputs) -> ConfidenceFusionResult:
        """Tính c_trip có chuẩn hóa động và phân nhánh Selective Autonomy.

        Công thức:
            c_trip = w1*p_STT + w2*p_intent + w3*p_addr + w4*p_vision
        """
        has_vision = inputs.p_vision is not None

        if has_vision:
            # Đủ 4 kênh: chuẩn hóa trực tiếp
            total_w = self.w1 + self.w2 + self.w3 + self.w4
            w1_eff = self.w1 / total_w
            w2_eff = self.w2 / total_w
            w3_eff = self.w3 / total_w
            w4_eff = self.w4 / total_w

            c_trip_raw = (
                w1_eff * inputs.p_stt
                + w2_eff * inputs.p_intent
                + w3_eff * inputs.p_addr
                + w4_eff * inputs.p_vision  # type: ignore[operator]
            )
            weights_dict = {
                "w1_stt": w1_eff,
                "w2_intent": w2_eff,
                "w3_addr": w3_eff,
                "w4_vision": w4_eff,
            }
        else:
            # Khách không gửi ảnh: w4 = 0, tái chuẩn hóa w1 + w2 + w3 = 1.0 (Dòng 84)
            total_w = self.w1 + self.w2 + self.w3
            w1_eff = self.w1 / total_w
            w2_eff = self.w2 / total_w
            w3_eff = self.w3 / total_w

            c_trip_raw = (
                w1_eff * inputs.p_stt
                + w2_eff * inputs.p_intent
                + w3_eff * inputs.p_addr
            )
            weights_dict = {
                "w1_stt": w1_eff,
                "w2_intent": w2_eff,
                "w3_addr": w3_eff,
                "w4_vision": 0.0,
            }

        # Temperature Scaling Calibration (nếu temperature != 1.0)
        c_trip = self._apply_temperature_scaling(c_trip_raw, self.temperature)
        c_trip = max(0.0, min(1.0, c_trip))

        # Selective Autonomy 3-tier routing
        if c_trip >= self.tau_high:
            decision = AutonomyDecision.AUTO_BOOK
            explanation = (
                f"Độ tin cậy chuyến đi rất cao ({c_trip:.2f} >= {self.tau_high}): "
                "Đủ điều kiện tự động xác nhận và chốt đơn xe (Auto-book)."
            )
        elif c_trip > self.tau_low:
            decision = AutonomyDecision.CLARIFY
            explanation = (
                f"Độ tin cậy chuyến đi ở mức trung bình ({self.tau_low} < {c_trip:.2f} < {self.tau_high}): "
                "Cần hỏi lại khách bằng giọng nói để làm rõ thông tin chưa chắc chắn."
            )
        else:
            decision = AutonomyDecision.HITL_HANDOFF
            explanation = (
                f"Độ tin cậy chuyến đi thấp ({c_trip:.2f} <= {self.tau_low}): "
                "Cần chuyển giao mượt mà sang tổng đài viên người thật (HITL Handoff < 0.5s)."
            )

        logger.info(
            "confidence_fusion evaluated: c_trip=%.4f decision=%s has_vision=%s",
            c_trip,
            decision.value,
            has_vision,
        )

        return ConfidenceFusionResult(
            c_trip=round(c_trip, 4),
            decision=decision,
            p_stt=inputs.p_stt,
            p_intent=inputs.p_intent,
            p_addr=inputs.p_addr,
            p_vision=inputs.p_vision,
            effective_weights=weights_dict,
            tau_high=self.tau_high,
            tau_low=self.tau_low,
            has_vision=has_vision,
            explanation=explanation,
        )

    @staticmethod
    def _apply_temperature_scaling(p: float, temperature: float) -> float:
        """Áp dụng Temperature Scaling hiệu chỉnh xác suất."""
        if math.isclose(temperature, 1.0, rel_tol=1e-5):
            return p
        # Tránh vô cực khi p gần 0 hoặc 1
        eps = 1e-6
        p_clamped = max(eps, min(1.0 - eps, p))
        logit = math.log(p_clamped / (1.0 - p_clamped))
        scaled_logit = logit / temperature
        return 1.0 / (1.0 + math.exp(-scaled_logit))

    @staticmethod
    def compute_ece(
        confidences: list[float],
        ground_truth: list[int],
        num_bins: int = 10,
    ) -> float:
        """Tính Expected Calibration Error (ECE) theo công thức chuẩn.

        ECE = sum_m (|B_m| / N) * |acc(B_m) - conf(B_m)|
        Mục tiêu KPI (Báo cáo Dòng 129-131): ECE <= 0.10
        """
        if not confidences or len(confidences) != len(ground_truth):
            return 0.0

        n = len(confidences)
        bin_size = 1.0 / num_bins
        ece = 0.0

        for b in range(num_bins):
            bin_lower = b * bin_size
            bin_upper = (b + 1) * bin_size

            # Lấy các điểm thuộc bin
            bin_indices = [
                i for i, c in enumerate(confidences)
                if bin_lower <= c < bin_upper or (b == num_bins - 1 and c == bin_upper)
            ]

            if not bin_indices:
                continue

            bin_conf = sum(confidences[i] for i in bin_indices) / len(bin_indices)
            bin_acc = sum(ground_truth[i] for i in bin_indices) / len(bin_indices)
            bin_weight = len(bin_indices) / n

            ece += bin_weight * abs(bin_acc - bin_conf)

        return round(ece, 4)
