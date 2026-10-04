"""Offer Profile Service — Tính toán và cache behavioral profile của user.

Chạy async sau mỗi chuyến hoàn thành; không block booking flow.

Hai scorer chính:
- ChurnRisk  ∈ [0, 1]: 1.0 = nguy cơ churn cao nhất
- PriceSensitivity ∈ [0, 1]: 1.0 = rất nhạy cảm về giá
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

# Cập nhật định kỳ từ analytics pipeline (VND)
_MARKET_AVG_FARE_VND: int = 45_000


@dataclass
class UserOfferProfile:
    """Snapshot behavioral profile dùng cho OfferEngine.

    Được populate từ DB (bảng user_offer_profiles) hoặc tính fresh từ booking
    history khi profile chưa tồn tại.
    """

    user_id: str

    # ── Frequency / Recency ─────────────────────────────────────────────────
    total_rides: int = 0
    rides_last_30d: int = 0
    rides_last_7d: int = 0
    avg_monthly_rides: float = 0.0
    days_since_last_ride: int | None = None

    # ── Price sensitivity raw signals ───────────────────────────────────────
    avg_fare_accepted: int | None = None        # VND
    promo_usage_count: int = 0
    promo_usage_rate: float = 0.0              # promo_bookings / total_bookings
    cancel_on_high_fare: int = 0               # cancels when fare > P75
    downgrade_count: int = 0                   # times chose cheaper vehicle

    # ── Churn signals ───────────────────────────────────────────────────────
    peak_cancel_count: int = 0                 # cancels during peak hours
    peak_booking_count: int = 0                # attempts during peak hours
    consecutive_no_ride_days: int = 0

    # ── Behavioral clusters ─────────────────────────────────────────────────
    frequent_zones: list[str] = field(default_factory=list)     # ["cau_giay"]
    preferred_hours: list[int] = field(default_factory=list)    # [7, 8, 17, 18]
    preferred_vehicles: list[str] = field(default_factory=list) # ["CAR_4"]
    historical_routes: list[str] = field(default_factory=list)  # route_hash (last 50)
    loyalty_tier: str = "BRONZE"               # BRONZE/SILVER/GOLD/PLATINUM

    # ── Computed scores (populated by OfferProfileService.refresh_scores) ───
    churn_risk_score: float = 0.0
    price_sensitivity: float = 0.0
    last_scored_at: datetime | None = None


class OfferProfileService:
    """Tính và cập nhật behavioral profile cho mỗi user.

    Usage:
        svc = OfferProfileService()
        profile = UserOfferProfile(user_id="usr_abc", rides_last_30d=0, ...)
        profile = svc.refresh_scores(profile)
        # profile.churn_risk_score, profile.price_sensitivity đã được cập nhật
    """

    # ── Public API ───────────────────────────────────────────────────────────

    def refresh_scores(self, profile: UserOfferProfile) -> UserOfferProfile:
        """Cập nhật churn_risk_score và price_sensitivity vào profile object.

        Trả về cùng object đã mutate (convenience); caller không cần reassign.
        """
        profile.churn_risk_score = self.compute_churn_risk(profile)
        profile.price_sensitivity = self.compute_price_sensitivity(profile)
        profile.last_scored_at = datetime.now(UTC)
        logger.debug(
            "offer_profile.scored user=%s churn=%.4f price_sens=%.4f",
            profile.user_id,
            profile.churn_risk_score,
            profile.price_sensitivity,
        )
        return profile

    def compute_churn_risk(self, p: UserOfferProfile) -> float:
        """ChurnRisk ∈ [0, 1] — 1.0 là nguy cơ churn cao nhất.

        Signals:
          - Recency         (0.40): thời gian kể từ chuyến cuối
          - Frequency drop  (0.30): so sánh rides_last_30d vs avg_monthly_rides
          - Peak cancel rate(0.20): tỷ lệ hủy trong khung giờ cao điểm
          - Consecutive     (0.10): số ngày liên tiếp không đặt xe
        """
        # Recency: càng lâu không đi → score càng cao
        recency = min((p.days_since_last_ride or 30) / 30.0, 1.0)

        # Frequency drop: avg=0 → trung tính 0.5 để tránh sai số cho user mới
        if p.avg_monthly_rides > 0:
            freq_drop = max(0.0, 1.0 - p.rides_last_30d / p.avg_monthly_rides)
        else:
            freq_drop = 0.5

        # Peak-hour cancel rate
        if p.peak_booking_count > 0:
            peak_cancel_rate = min(p.peak_cancel_count / p.peak_booking_count, 1.0)
        else:
            peak_cancel_rate = 0.0

        # Consecutive no-ride days (cap ở 14 ngày = 1.0)
        consec = min(p.consecutive_no_ride_days / 14.0, 1.0)

        score = (
            0.40 * recency
            + 0.30 * freq_drop
            + 0.20 * peak_cancel_rate
            + 0.10 * consec
        )
        return round(min(max(score, 0.0), 1.0), 4)

    def compute_price_sensitivity(self, p: UserOfferProfile) -> float:
        """PriceSensitivity ∈ [0, 1] — 1.0 là rất nhạy cảm về giá.

        Signals:
          - Avg fare vs market  (0.35): chấp nhận giá thấp hơn market → sensitivity cao
          - Promo usage rate    (0.30): tần suất dùng mã giảm giá
          - Cancel on high fare (0.20): tỷ lệ hủy khi giá cao hơn P75
          - Downgrade rate      (0.15): tần suất chọn xe rẻ hơn gợi ý
        """
        # Avg fare vs market: fare thấp hơn market → nhạy cảm cao hơn
        if p.avg_fare_accepted and _MARKET_AVG_FARE_VND > 0:
            fare_ratio = p.avg_fare_accepted / _MARKET_AVG_FARE_VND
            # fare_ratio in [0, 2]: 0.5 means pays 50% of market → very price-sensitive
            normalized_fare = max(0.0, 1.0 - min(fare_ratio, 2.0) / 2.0)
        else:
            normalized_fare = 0.5  # Unknown → neutral

        promo = min(p.promo_usage_rate, 1.0)
        cancel_rate = min(
            p.cancel_on_high_fare / max(p.total_rides, 1), 1.0
        )
        downgrade = min(p.downgrade_count / max(p.total_rides, 1), 1.0)

        score = (
            0.35 * normalized_fare
            + 0.30 * promo
            + 0.20 * cancel_rate
            + 0.15 * downgrade
        )
        return round(min(max(score, 0.0), 1.0), 4)

    def compute_loyalty_tier(self, total_rides: int, rides_last_30d: int) -> str:
        """Xác định loyalty tier dựa trên lịch sử chuyến.

        Tiers:
          - PLATINUM : total >= 200 hoặc last_30d >= 20
          - GOLD     : total >= 50  hoặc last_30d >= 10
          - SILVER   : total >= 10  hoặc last_30d >= 3
          - BRONZE   : còn lại
        """
        if total_rides >= 200 or rides_last_30d >= 20:
            return "PLATINUM"
        if total_rides >= 50 or rides_last_30d >= 10:
            return "GOLD"
        if total_rides >= 10 or rides_last_30d >= 3:
            return "SILVER"
        return "BRONZE"

    def build_cold_start_profile(self, user_id: str) -> UserOfferProfile:
        """Tạo profile mặc định cho user mới chưa có lịch sử.

        c_offer sẽ < 0.20 → OfferEngine không offer → tránh lãng phí budget.
        Override bằng new_user_welcome_promotion nếu có chiến dịch riêng.
        """
        profile = UserOfferProfile(user_id=user_id)
        return self.refresh_scores(profile)
