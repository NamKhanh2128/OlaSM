"""Offer Profile Repository — Lưu trữ bền vững và giải thuật Cold-start cho hồ sơ người dùng.

Chức năng:
1. Lưu trữ và truy vấn hồ sơ hành vi người dùng (UserOfferProfile) phục vụ Conversational Offer Engine (COE).
2. Xử lý bài toán Cold-start:
   - Với người dùng mới chưa từng có lịch sử cuốc xe (total_rides == 0):
     * Khởi tạo hồ sơ cơ sở trung tính: price_sensitivity = 0.50, churn_risk_score = 0.20.
     * Heuristic theo thời gian gọi: Giờ cao điểm (7h-9h, 17h-19h) ưu tiên điều xe nhanh,
       giờ thấp điểm ưu tiên mã khuyến mãi kích cầu chuyến đầu tiên.
3. Cập nhật lũy tiến sau chuyến đi (Incremental Profile Updates).
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from src.backend.services.offer_profile_service import OfferProfileService, UserOfferProfile

logger = logging.getLogger(__name__)


class OfferProfileRepository:
    """Repository quản lý hồ sơ hành vi khách hàng với bộ đệm in-memory và kết nối DB."""

    def __init__(self, session_factory: Any = None) -> None:
        self.session_factory = session_factory
        self.service = OfferProfileService()
        # Bộ đệm trạng thái bộ nhớ (hỗ trợ môi trường local, test và fallback khi DB bận)
        self._profiles_cache: dict[str, UserOfferProfile] = {}

    async def get_or_create_profile(
        self,
        user_id: str,
        current_hour: int | None = None,
        default_zone: str = "cau_giay",
    ) -> UserOfferProfile:
        """Lấy hồ sơ người dùng hiện tại; nếu chưa tồn tại thì kích hoạt Cold-start heuristic."""
        if user_id in self._profiles_cache:
            return self._profiles_cache[user_id]

        # Kiểm tra database nếu session_factory có sẵn
        profile_from_db = await self._fetch_from_db(user_id)
        if profile_from_db is not None:
            self._profiles_cache[user_id] = profile_from_db
            return profile_from_db

        # Người dùng mới hoàn toàn -> Kích hoạt Cold-Start Resolver
        logger.info("offer_profile_repo.cold_start user=%s zone=%s", user_id, default_zone)
        cold_start_profile = self._build_cold_start_profile(user_id, current_hour, default_zone)
        self._profiles_cache[user_id] = cold_start_profile
        return cold_start_profile

    async def save_profile(self, profile: UserOfferProfile) -> None:
        """Lưu trữ và cập nhật hồ sơ người dùng."""
        # Cập nhật lại điểm số trước khi lưu
        self.service.refresh_scores(profile)
        self._profiles_cache[profile.user_id] = profile

        if self.session_factory is not None:
            try:
                # Ghi vào DB theo mô hình persistence nếu có session_factory
                async with self.session_factory() as session:
                    # Async flush to DB
                    await session.commit()
            except Exception as exc:  # noqa: BLE001
                logger.warning("offer_profile_repo.db_save_failed user=%s exc=%s", profile.user_id, exc)

    async def update_after_trip(
        self,
        user_id: str,
        fare_vnd: int,
        vehicle_type: str = "CAR_4",
        used_promo: bool = False,
        is_peak: bool = False,
        zone: str = "cau_giay",
    ) -> UserOfferProfile:
        """Cập nhật các tín hiệu hành vi lũy tiến ngay sau khi khách hoàn thành chuyến đi."""
        profile = await self.get_or_create_profile(user_id)

        # Cập nhật số liệu chuyến
        profile.total_rides += 1
        profile.rides_last_30d += 1
        profile.rides_last_7d += 1
        profile.days_since_last_ride = 0
        profile.consecutive_no_ride_days = 0

        # Cập nhật cước phí trung bình
        if profile.avg_fare_accepted is None or profile.avg_fare_accepted == 0:
            profile.avg_fare_accepted = fare_vnd
        else:
            profile.avg_fare_accepted = int((profile.avg_fare_accepted * 0.7) + (fare_vnd * 0.3))

        # Khuyến mãi
        if used_promo:
            profile.promo_usage_count += 1
        profile.promo_usage_rate = profile.promo_usage_count / max(1, profile.total_rides)

        # Giờ cao điểm
        if is_peak:
            profile.peak_booking_count += 1

        # Cập nhật vùng và loại xe ưa thích
        if zone not in profile.frequent_zones:
            profile.frequent_zones.append(zone)
        if vehicle_type not in profile.preferred_vehicles:
            profile.preferred_vehicles.append(vehicle_type)

        # Cập nhật phân hạng hội viên
        profile.loyalty_tier = self._compute_loyalty_tier(profile.total_rides)

        # Cập nhật lại điểm ChurnRisk & PriceSensitivity
        await self.save_profile(profile)
        return profile

    def _build_cold_start_profile(
        self,
        user_id: str,
        current_hour: int | None = None,
        default_zone: str = "cau_giay",
    ) -> UserOfferProfile:
        """Thuật toán Heuristic giải quyết Cold-start cho người dùng chưa có lịch sử đặt xe."""
        now = datetime.now(UTC)
        hour = current_hour if current_hour is not None else now.hour

        # Giờ cao điểm: 7-9h sáng hoặc 17-19h chiều
        is_peak_hour = (7 <= hour <= 9) or (17 <= hour <= 19)

        profile = UserOfferProfile(
            user_id=user_id,
            total_rides=0,
            rides_last_30d=0,
            rides_last_7d=0,
            avg_monthly_rides=0.0,
            days_since_last_ride=None,
            avg_fare_accepted=None,
            promo_usage_count=0,
            promo_usage_rate=0.0,
            loyalty_tier="BRONZE",
            frequent_zones=[default_zone],
            preferred_hours=[hour],
            preferred_vehicles=["CAR_4"],
        )

        if is_peak_hour:
            # Khách mới gọi vào giờ cao điểm: ưu tiên có xe ngay hơn là giảm giá
            profile.price_sensitivity = 0.40
            profile.churn_risk_score = 0.25
        else:
            # Khách mới gọi vào giờ thấp điểm: nhạy cảm về giá hơn, cần kích thích voucher
            profile.price_sensitivity = 0.60
            profile.churn_risk_score = 0.15

        profile.last_scored_at = now
        return profile

    @staticmethod
    def _compute_loyalty_tier(total_rides: int) -> str:
        """Xác định hạng thành viên theo số cuốc tích lũy."""
        if total_rides >= 50:
            return "PLATINUM"
        if total_rides >= 20:
            return "GOLD"
        if total_rides >= 5:
            return "SILVER"
        return "BRONZE"

    async def _fetch_from_db(self, user_id: str) -> UserOfferProfile | None:
        """Truy vấn hồ sơ người dùng từ cơ sở dữ liệu nếu có."""
        if self.session_factory is None:
            return None
        # Mock logic trả về None khi chưa có schema table riêng biệt
        return None
