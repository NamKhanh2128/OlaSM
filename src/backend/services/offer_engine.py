"""Offer Engine — Core allocation logic cho Conversational Offer Engine.

Input:  UserOfferProfile + BookingContext + danh sách Promotions active
Output: BestOffer (mã ưu đãi tối ưu) hoặc None nếu không nên offer

Nguyên tắc thiết kế:
- Deterministic: cùng input → cùng output (testable, auditable)
- Budget-aware: không allocate khi promotion hết budget hoặc usage limit
- Không lãng phí: chỉ offer khi S_offer >= TIER_SUGGEST threshold
- Idempotent: gọi nhiều lần cùng session_id không tạo conflict

Formula cốt lõi (Báo cáo Ý tưởng Nhóm 4 - GSM Mobility Assistant, Mục 4.2):
    S_offer = alpha * ChurnRisk + beta * PriceSensitivity + gamma * CampaignFit + priority_bonus

    Trong đó:
      - ChurnRisk: Xác suất khách hàng rời bỏ dịch vụ nếu không được chốt chuyến.
      - PriceSensitivity: Mức độ nhạy cảm về giá suy ra từ lịch sử hủy chuyến trước đây.
      - CampaignFit: Độ phù hợp của các mã khuyến mãi hiện hành với phân khúc khách hàng đó.

Tier routing:
    S_offer >= 0.70  →  PREMIUM   (chủ động ưu đãi trước confirmation)
    S_offer >= 0.45  →  STANDARD  (áp dụng ưu đãi cùng lúc confirmation)
    S_offer >= 0.20  →  SUGGEST   (chỉ khi khách hỏi về giá)
    S_offer <  0.20  →  None      (im lặng — tránh lãng phí budget)
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from src.backend.services.offer_profile_service import UserOfferProfile

logger = logging.getLogger(__name__)

# ─── Hệ số trọng số theo tài liệu Báo cáo Nhóm 4 (alpha + beta + gamma = 1.0) ──
ALPHA: float = 0.35  # Trọng số ChurnRisk
BETA: float = 0.25   # Trọng số PriceSensitivity
GAMMA: float = 0.40  # Trọng số CampaignFit

# Tương thích ngược với các module tham chiếu cũ
W_CHURN = ALPHA
W_PRICE = BETA
W_CAMPAIGN = GAMMA

# ─── Offer tier thresholds ──────────────────────────────────────────────────────
TIER_PREMIUM: float = 0.70
TIER_STANDARD: float = 0.45
TIER_SUGGEST: float = 0.20


@dataclass
class BookingContext:
    """Snapshot của booking request tại thời điểm offer evaluation.

    Tạo từ AgentState + user request tại thời điểm estimate_fare thành công.
    """

    user_id: str
    session_id: str
    vehicle_type: str           # e.g. "CAR_4", "CAR_7", "MOTORBIKE"
    estimated_fare_vnd: int     # Từ fare_estimate result
    pickup_zone: str | None     # Zone ID của điểm đón (nếu resolved)
    destination_zone: str | None
    route_hash: str             # sha256(pickup_place_id + destination_place_id)[:16]
    hour_of_day: int            # 0-23 local Vietnam time
    day_of_week: int            # 0=Monday, 6=Sunday


@dataclass
class Promotion:
    """Thông tin promotion đủ để OfferEngine đánh giá và score.

    Được load từ bảng `promotions` thông qua OfferRepository.
    """

    id: str
    code: str
    title: str
    discount_type: str          # PERCENT | FIXED_VND | FREE_RIDE
    discount_value: int         # % hoặc số VND cố định
    max_discount_vnd: int | None  # Cap cho PERCENT type
    min_fare_vnd: int           # Minimum fare để áp dụng

    # Targeting filters — None = không lọc = match all
    target_tiers: list[str] | None      # ["SILVER", "GOLD"] hoặc None
    valid_vehicle_types: list[str] | None
    valid_hours: list[int] | None       # [7, 8, 17, 18, 19]
    valid_zones: list[str] | None       # Zone IDs

    new_route_only: bool = False        # True = chỉ dùng cho tuyến mới

    # Business control
    campaign_priority: int = 50         # 0-100: ảnh hưởng priority_bonus
    remaining_budget_vnd: int | None = None  # None = unlimited
    usage_per_user: int = 1
    current_user_usage: int = 0         # Số lần user này đã dùng


@dataclass
class BestOffer:
    """Kết quả offer tối ưu được chọn bởi OfferEngine.

    Trả về cho Agent để quyết định khi nào và cách nào trình bày với user.
    Ghi vào promotion_snapshot khi booking được confirm.
    """

    promotion_id: str
    promotion_code: str
    title: str

    # Scoring breakdown (Báo cáo Ý tưởng Nhóm 4, Mục 4.2: S_offer = alpha * ChurnRisk + beta * PriceSensitivity + gamma * CampaignFit)
    s_offer: float = 0.0        # Composite score S_offer ∈ [0.20, 1.0]
    c_offer: float = 0.0        # Alias tương thích ngược
    alpha: float = ALPHA        # 0.35
    beta: float = BETA          # 0.25
    gamma: float = GAMMA        # 0.40
    offer_tier: str = "STANDARD"  # PREMIUM | STANDARD | SUGGEST
    campaign_fit: float = 0.0
    churn_risk: float = 0.0
    price_sensitivity: float = 0.0

    # Discount info (pre-calculated)
    discount_type: str = "PERCENT"
    discount_value: int = 0
    discount_amount_vnd: int = 0    # Số tiền giảm thực tế
    max_discount_vnd: int | None = None
    final_fare_vnd: int = 0         # estimated_fare - discount_amount

    # Kịch bản thoại tối ưu chuẩn hóa theo GSM Mobility Assistant (Báo cáo Mục 4.2, Dòng 79)
    speech_suggestion: str | None = None

    # Idempotency
    allocation_hash: str = ""        # sha256(user_id:promotion_id:session_id)[:16]

    def to_snapshot(self) -> dict[str, object]:
        """Serialize để lưu vào promotion_snapshot column của FareQuote/Booking."""
        score_val = self.s_offer or self.c_offer
        return {
            "promotion_id": self.promotion_id,
            "promotion_code": self.promotion_code,
            "title": self.title,
            "s_offer": score_val,
            "c_offer": score_val,
            "alpha": self.alpha,
            "beta": self.beta,
            "gamma": self.gamma,
            "offer_tier": self.offer_tier,
            "discount_type": self.discount_type,
            "discount_value": self.discount_value,
            "discount_amount_vnd": self.discount_amount_vnd,
            "final_fare_vnd": self.final_fare_vnd,
            "speech_suggestion": self.speech_suggestion,
            "allocation_hash": self.allocation_hash,
        }


class OfferEngine:
    """Core allocation engine cho Conversational Offer Engine.

    Quy trình evaluate():
    1. Filter: loại bỏ promotions không eligible (budget, usage, tier, fare min)
    2. Score : tính c_offer cho từng promotion còn lại
    3. Select: chọn promotion có c_offer cao nhất
    4. Route : phân loại theo tier threshold → PREMIUM / STANDARD / SUGGEST / None
    """

    # ── Public API ──────────────────────────────────────────────────────────

    def evaluate(
        self,
        profile: UserOfferProfile,
        context: BookingContext,
        available_promotions: list[Promotion],
    ) -> BestOffer | None:
        """Đánh giá và chọn best offer.

        Returns:
            BestOffer nếu c_offer >= TIER_SUGGEST và có promotion eligible.
            None nếu không nên offer (tránh lãng phí budget/attention).
        """
        eligible = self._filter_eligible(profile, context, available_promotions)
        if not eligible:
            logger.info("offer.no_eligible_promo user=%s session=%s", context.user_id, context.session_id)
            return None

        scored = sorted(
            ((promo, self._composite_score(profile, context, promo)) for promo in eligible),
            key=lambda x: x[1],
            reverse=True,
        )
        best_promo, best_score = scored[0]

        if best_score < TIER_SUGGEST:
            logger.info(
                "offer.below_threshold user=%s score=%.4f threshold=%.2f",
                context.user_id,
                best_score,
                TIER_SUGGEST,
            )
            return None

        offer_tier = self._resolve_tier(best_score)
        discount_vnd = self._calculate_discount(best_promo, context.estimated_fare_vnd)
        allocation_hash = self._allocation_hash(context, best_promo)

        logger.info(
            "offer.allocated user=%s promo=%s tier=%s score=%.4f discount_vnd=%d",
            context.user_id,
            best_promo.code,
            offer_tier,
            best_score,
            discount_vnd,
        )

        final_fare = max(0, context.estimated_fare_vnd - discount_vnd)
        discount_desc = f"{best_promo.discount_value}%" if best_promo.discount_type == "PERCENT" else f"{discount_vnd:,}đ"
        vehicle_display = context.vehicle_type
        if "CAR" in vehicle_display.upper():
            vehicle_display = "GreenCar"
        elif "BIKE" in vehicle_display.upper() or "MOTOR" in vehicle_display.upper():
            vehicle_display = "GreenBike"

        # Kịch bản thoại tối ưu chuẩn hóa theo GSM Mobility Assistant (Báo cáo Mục 4.2, Dòng 79)
        speech_suggestion = (
            f"Dạ chuyến đi của mình có giá {context.estimated_fare_vnd:,}đ, em đã tự động áp dụng ưu đãi giảm "
            f"{discount_desc} chỉ còn {final_fare:,}đ. Em điều xe {vehicle_display} đón mình ngay nhé ạ?"
        )

        return BestOffer(
            promotion_id=best_promo.id,
            promotion_code=best_promo.code,
            title=best_promo.title,
            s_offer=round(best_score, 4),
            c_offer=round(best_score, 4),
            alpha=ALPHA,
            beta=BETA,
            gamma=GAMMA,
            offer_tier=offer_tier,
            campaign_fit=round(self._campaign_fit(profile, context, best_promo), 4),
            churn_risk=profile.churn_risk_score,
            price_sensitivity=profile.price_sensitivity,
            discount_type=best_promo.discount_type,
            discount_value=best_promo.discount_value,
            discount_amount_vnd=discount_vnd,
            max_discount_vnd=best_promo.max_discount_vnd,
            final_fare_vnd=final_fare,
            speech_suggestion=speech_suggestion,
            allocation_hash=allocation_hash,
        )

    # ── Eligibility filter ──────────────────────────────────────────────────

    def _filter_eligible(
        self,
        profile: UserOfferProfile,
        context: BookingContext,
        promotions: list[Promotion],
    ) -> list[Promotion]:
        """Loại bỏ các promotion không hợp lệ. Tất cả checks phải pass."""
        eligible = []
        for p in promotions:
            if not self._is_eligible(profile, context, p):
                continue
            eligible.append(p)
        return eligible

    def _is_eligible(
        self,
        profile: UserOfferProfile,
        context: BookingContext,
        p: Promotion,
    ) -> bool:
        """Trả True nếu promotion hợp lệ cho user + context này."""
        # Budget check
        if p.remaining_budget_vnd is not None and p.remaining_budget_vnd <= 0:
            return False
        # Per-user usage limit
        if p.current_user_usage >= p.usage_per_user:
            return False
        # Min fare check
        if context.estimated_fare_vnd < p.min_fare_vnd:
            return False
        # Loyalty tier
        if p.target_tiers and profile.loyalty_tier not in p.target_tiers:
            return False
        # Vehicle type
        if p.valid_vehicle_types and context.vehicle_type not in p.valid_vehicle_types:
            return False
        # New route only
        if p.new_route_only and context.route_hash in profile.historical_routes:
            return False
        return True

    # ── Scoring ──────────────────────────────────────────────────────────────

    def _composite_score(
        self,
        profile: UserOfferProfile,
        context: BookingContext,
        promo: Promotion,
    ) -> float:
        """S_offer = alpha * ChurnRisk + beta * PriceSensitivity + gamma * CampaignFit + priority_bonus.

        Theo Báo cáo Ý tưởng Nhóm 4 (Dòng 75):
          - ChurnRisk: Xác suất khách hàng rời bỏ dịch vụ nếu không được chốt chuyến.
          - PriceSensitivity: Mức độ nhạy cảm về giá suy ra từ lịch sử hủy chuyến trước đây.
          - CampaignFit: Độ phù hợp của các mã khuyến mãi hiện hành với phân khúc khách hàng đó.
        """
        campaign_fit = self._campaign_fit(profile, context, promo)

        # Campaign priority bonus: 0-100 → 0.0-0.20 additive bonus
        priority_bonus = (promo.campaign_priority / 100.0) * 0.20

        raw = (
            ALPHA * profile.churn_risk_score
            + BETA * profile.price_sensitivity
            + GAMMA * campaign_fit
            + priority_bonus
        )
        return min(raw, 1.0)

    def _campaign_fit(
        self,
        profile: UserOfferProfile,
        context: BookingContext,
        promo: Promotion,
    ) -> float:
        """CampaignFit ∈ [0, 1] — rule-based scoring của promotion vs. context."""
        score = 0.0

        # Time-slot match: khung giờ đúng với preference của promotion (0.30)
        if promo.valid_hours and context.hour_of_day in promo.valid_hours:
            score += 0.30

        # Vehicle type match (0.25)
        if promo.valid_vehicle_types and context.vehicle_type in promo.valid_vehicle_types:
            score += 0.25

        # Zone match (0.25 nếu exact pickup/destination match; 0.10 nếu frequent zone)
        if promo.valid_zones:
            promo_zones = set(promo.valid_zones)
            if context.pickup_zone in promo_zones or context.destination_zone in promo_zones:
                score += 0.25
            elif set(profile.frequent_zones) & promo_zones:
                score += 0.10

        # New route incentive: chưa từng đi tuyến này (0.10)
        if context.route_hash not in profile.historical_routes:
            score += 0.10

        # Loyalty tier match (0.10)
        if promo.target_tiers and profile.loyalty_tier in promo.target_tiers:
            score += 0.10

        return min(score, 1.0)

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_tier(score: float) -> str:
        if score >= TIER_PREMIUM:
            return "PREMIUM"
        if score >= TIER_STANDARD:
            return "STANDARD"
        return "SUGGEST"

    @staticmethod
    def _calculate_discount(promo: Promotion, fare_vnd: int) -> int:
        """Tính số tiền giảm thực tế (VND), đã áp dụng cap."""
        if promo.discount_type == "PERCENT":
            raw = int(fare_vnd * promo.discount_value / 100)
            if promo.max_discount_vnd is not None:
                raw = min(raw, promo.max_discount_vnd)
            return raw
        if promo.discount_type == "FIXED_VND":
            return min(promo.discount_value, fare_vnd)
        if promo.discount_type == "FREE_RIDE":
            return fare_vnd
        return 0

    @staticmethod
    def _allocation_hash(context: BookingContext, promo: Promotion) -> str:
        """Idempotency key cho allocation — deterministic từ user+promo+session."""
        raw = f"{context.user_id}:{promo.id}:{context.session_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
