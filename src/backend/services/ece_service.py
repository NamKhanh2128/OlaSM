"""ECE Calibration & Reliability Evaluation Service.

Cơ sở lý thuyết & Tiêu chuẩn KPI theo Báo cáo Đề án Nhóm 4 (Mục 4.3):
- Expected Calibration Error (ECE) đánh giá độ tin cậy của xác suất dự báo c_trip:
    ECE = sum_{m=1}^M (|B_m| / N) * |acc(B_m) - conf(B_m)|
- Maximum Calibration Error (MCE) đánh giá sai lệch tồi tệ nhất giữa các bin:
    MCE = max_{m=1}^M |acc(B_m) - conf(B_m)|
- Temperature Scaling:
    p_calibrated = sigma(logit / T*)
    T* được tối ưu hóa trên tập kiểm chuẩn (Validation Set) để triệt tiêu overconfidence.
- Tiêu chuẩn nghiệm thu: ECE <= 0.10.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class CalibrationBin:
    """Chi tiết một bin xác suất phục vụ vẽ biểu đồ tin cậy (Reliability Diagram)."""
    bin_index: int
    lower_bound: float
    upper_bound: float
    sample_count: int
    mean_confidence: float
    accuracy: float
    calibration_gap: float  # |accuracy - mean_confidence|


@dataclass
class CalibrationReport:
    """Báo cáo chi tiết độ hiệu chuẩn xác suất toàn diện."""
    num_samples: int
    num_bins: int
    ece: float
    mce: float
    is_calibrated: bool  # True nếu ECE <= 0.10
    temperature: float
    bins: list[CalibrationBin] = field(default_factory=list)

    def summary(self) -> str:
        status = "ĐẠT CHUẨN (PASS)" if self.is_calibrated else "CẦN HIỆU CHỈNH (FAIL)"
        return (
            f"Calibration Report: N={self.num_samples}, ECE={self.ece:.4f}, MCE={self.mce:.4f}, "
            f"Temperature={self.temperature:.2f} -> {status}"
        )


class ECEService:
    """Dịch vụ đo lường và tối ưu hóa độ hiệu chuẩn xác suất (ECE)."""

    def __init__(self, target_ece_threshold: float = 0.10, default_bins: int = 10) -> None:
        self.target_ece_threshold = target_ece_threshold
        self.default_bins = default_bins

    def evaluate(
        self,
        confidences: list[float],
        ground_truth: list[int],
        num_bins: int | None = None,
        temperature: float = 1.0,
    ) -> CalibrationReport:
        """Đo lường chi tiết ECE, MCE và cấu trúc các bin xác suất."""
        if not confidences or len(confidences) != len(ground_truth):
            return CalibrationReport(
                num_samples=0,
                num_bins=num_bins or self.default_bins,
                ece=0.0,
                mce=0.0,
                is_calibrated=True,
                temperature=temperature,
            )

        n_bins = num_bins or self.default_bins
        n = len(confidences)

        # Hiệu chỉnh bằng temperature nếu khác 1.0
        calibrated_confs: list[float] = []
        for c in confidences:
            if math.isclose(temperature, 1.0, rel_tol=1e-5):
                calibrated_confs.append(max(0.0, min(1.0, c)))
            else:
                eps = 1e-6
                c_clamped = max(eps, min(1.0 - eps, c))
                logit = math.log(c_clamped / (1.0 - c_clamped))
                scaled = 1.0 / (1.0 + math.exp(-logit / temperature))
                calibrated_confs.append(max(0.0, min(1.0, scaled)))

        bin_size = 1.0 / n_bins
        bins: list[CalibrationBin] = []
        ece = 0.0
        mce = 0.0

        for b in range(n_bins):
            lower = b * bin_size
            upper = (b + 1) * bin_size

            # Tập mẫu thuộc bin
            indices = [
                i for i, c in enumerate(calibrated_confs)
                if lower <= c < upper or (b == n_bins - 1 and c == upper)
            ]

            count = len(indices)
            if count == 0:
                bins.append(
                    CalibrationBin(
                        bin_index=b,
                        lower_bound=round(lower, 2),
                        upper_bound=round(upper, 2),
                        sample_count=0,
                        mean_confidence=0.0,
                        accuracy=0.0,
                        calibration_gap=0.0,
                    )
                )
                continue

            mean_conf = sum(calibrated_confs[i] for i in indices) / count
            acc = sum(ground_truth[i] for i in indices) / count
            gap = abs(acc - mean_conf)

            weight = count / n
            ece += weight * gap
            if gap > mce:
                mce = gap

            bins.append(
                CalibrationBin(
                    bin_index=b,
                    lower_bound=round(lower, 2),
                    upper_bound=round(upper, 2),
                    sample_count=count,
                    mean_confidence=round(mean_conf, 4),
                    accuracy=round(acc, 4),
                    calibration_gap=round(gap, 4),
                )
            )

        ece_rounded = round(ece, 4)
        mce_rounded = round(mce, 4)
        is_pass = ece_rounded <= self.target_ece_threshold

        return CalibrationReport(
            num_samples=n,
            num_bins=n_bins,
            ece=ece_rounded,
            mce=mce_rounded,
            is_calibrated=is_pass,
            temperature=temperature,
            bins=bins,
        )

    def find_optimal_temperature(
        self,
        confidences: list[float],
        ground_truth: list[int],
        search_range: tuple[float, float] = (0.5, 3.0),
        steps: int = 50,
    ) -> float:
        """Tìm giá trị T* tối ưu hóa bằng grid search để giảm thiểu ECE."""
        best_t = 1.0
        best_ece = float("inf")

        step_size = (search_range[1] - search_range[0]) / steps
        for step in range(steps + 1):
            t = search_range[0] + step * step_size
            report = self.evaluate(confidences, ground_truth, temperature=t)
            if report.ece < best_ece:
                best_ece = report.ece
                best_t = t

        logger.info("ece_service.optimal_temperature_found t=%.3f min_ece=%.4f", best_t, best_ece)
        return round(best_t, 3)
