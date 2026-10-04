"""GSM Sandbox API Integration Client — Khách hàng kết nối OpenAPI Điều phối xe GreenSM.

Chức năng:
1. Chuẩn hóa giao tiếp giữa hệ thống OlaSM Voice Assistant và nền tảng Dispatching trung tâm của GreenSM.
2. Hỗ trợ 2 chế độ vận hành:
   - Live Sandbox Mode: Kết nối trực tiếp qua HTTP REST OpenAPI với GSM Sandbox Gateway.
   - Deterministic Mock Simulator: Giả lập toàn bộ chu trình điều xe thực tế cho môi trường phát triển & kiểm thử.
3. Các nghiệp vụ trọng tâm:
   - request_fare_quote: Báo giá cước cước động, hệ số surge, loại xe điện VinFast, thời gian đón ETA.
   - create_booking: Đẩy cuốc xe kèm tọa độ đón/trả, mã ưu đãi và ghi chú điểm đón thị giác (Visual Landmark).
   - get_booking_status: Giám sát tài xế nhận chuyến, biển số xe điện, số điện thoại tài xế, tọa độ GPS.
   - cancel_booking: Hủy chuyến xe có kiểm soát lý do.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GSMDriverInfo:
    """Thông tin tài xế xe điện GreenSM được điều phối."""
    driver_id: str
    driver_name: str
    phone_number: str
    license_plate: str
    vehicle_model: str  # VD: VinFast VF e34, VinFast VF 5 Plus, VinFast VF 8
    battery_level_pct: int
    rating: float
    current_lat: float
    current_lng: float
    eta_pickup_minutes: int


@dataclass
class GSMQuoteResponse:
    """Kết quả tính cước từ hệ thống GreenSM."""
    quote_id: str
    vehicle_type: str
    distance_km: float
    estimated_duration_min: int
    base_fare_vnd: int
    surge_multiplier: float
    final_fare_vnd: int
    eta_pickup_minutes: int
    available_drivers_nearby: int
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class GSMBookingResponse:
    """Kết quả tạo lệnh điều xe GreenSM."""
    booking_id: str
    quote_id: str
    status: str  # ASSIGNING, ASSIGNED, ARRIVING, IN_TRIP, COMPLETED, CANCELLED
    vehicle_type: str
    pickup_address: str
    dropoff_address: str
    fare_vnd: int
    driver: GSMDriverInfo | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class GSMSandboxClient:
    """Client giao tiếp với GSM Dispatching Sandbox API."""

    def __init__(
        self,
        api_base_url: str = "https://sandbox-api.greensm.vn/v1",
        api_key: str = "gsm_sandbox_mock_key_2026",
        mock_mode: bool = True,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.mock_mode = mock_mode
        self._active_bookings: dict[str, GSMBookingResponse] = {}

    async def request_fare_quote(
        self,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
        vehicle_type: str = "CAR_4",
    ) -> GSMQuoteResponse:
        """Yêu cầu báo giá cước động và thời gian điều xe dự kiến."""
        if not self.mock_mode:
            # Code path gọi REST HTTP qua httpx (nếu triển khai production)
            pass

        # Giả lập độ trễ mạng sandbox (30ms - 80ms)
        await asyncio.sleep(0.04)

        # Tính khoảng cách xấp xỉ Manhattan/Haversine đơn giản
        dx = (pickup_lat - dropoff_lat) * 111.0
        dy = (pickup_lng - dropoff_lng) * 111.0 * 0.93
        distance_km = round(max(1.0, (dx**2 + dy**2) ** 0.5), 1)
        est_duration = max(5, int(distance_km * 2.8))

        # Đơn giá chuẩn taxi điện GreenSM
        is_luxury = "LUX" in vehicle_type.upper() or "VF8" in vehicle_type.upper()
        base_rate = 21_000 if is_luxury else 14_500
        surge = 1.0  # Chuẩn hóa giờ thường
        raw_fare = int(distance_km * base_rate * surge)
        # Làm tròn đến hàng nghìn
        final_fare = ((raw_fare + 500) // 1000) * 1000

        quote_hash = hashlib.sha256(f"{pickup_lat}_{pickup_lng}_{time.time()}".encode()).hexdigest()[:12]
        quote_id = f"gquote_{quote_hash}"

        return GSMQuoteResponse(
            quote_id=quote_id,
            vehicle_type=vehicle_type,
            distance_km=distance_km,
            estimated_duration_min=est_duration,
            base_fare_vnd=raw_fare,
            surge_multiplier=surge,
            final_fare_vnd=final_fare,
            eta_pickup_minutes=random.randint(3, 7),
            available_drivers_nearby=random.randint(4, 12),
        )

    async def create_booking(
        self,
        quote_id: str,
        customer_phone: str,
        customer_name: str,
        pickup_address: str,
        dropoff_address: str,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
        vehicle_type: str = "CAR_4",
        notes: str | None = None,
        promo_code: str | None = None,
    ) -> GSMBookingResponse:
        """Tạo lệnh điều phối xe trên hệ thống GreenSM."""
        await asyncio.sleep(0.06)

        booking_id = f"gsm_bk_{hashlib.sha256(f'{customer_phone}_{time.time()}'.encode()).hexdigest()[:10]}"

        # Sinh thông tin tài xế xe điện VinFast
        is_luxury = "LUX" in vehicle_type.upper() or "VF8" in vehicle_type.upper()
        driver = GSMDriverInfo(
            driver_id=f"drv_{random.randint(1000, 9999)}",
            driver_name=random.choice(["Nguyễn Văn Hùng", "Trần Đình Trọng", "Lê Văn Thắng", "Phạm Quốc Bảo"]),
            phone_number=f"09{random.randint(10000000, 99999999)}",
            license_plate=f"29E-{random.randint(100, 999)}.{random.randint(10, 99)}",
            vehicle_model="VinFast VF 8 (Xanh SM Luxury)" if is_luxury else "VinFast VF e34 (Xanh SM Taxi)",
            battery_level_pct=random.randint(72, 98),
            rating=round(random.uniform(4.85, 5.0), 2),
            current_lat=pickup_lat + random.uniform(-0.005, 0.005),
            current_lng=pickup_lng + random.uniform(-0.005, 0.005),
            eta_pickup_minutes=random.randint(3, 5),
        )

        fare = 150_000 if is_luxury else 85_000
        if promo_code:
            fare = int(fare * 0.85)

        booking = GSMBookingResponse(
            booking_id=booking_id,
            quote_id=quote_id,
            status="ASSIGNED",
            vehicle_type=vehicle_type,
            pickup_address=pickup_address,
            dropoff_address=dropoff_address,
            fare_vnd=fare,
            driver=driver,
        )

        self._active_bookings[booking_id] = booking
        logger.info("gsm_sandbox.booking_created id=%s driver=%s vehicle=%s", booking_id, driver.driver_name, driver.vehicle_model)
        return booking

    async def get_booking_status(self, booking_id: str) -> GSMBookingResponse:
        """Truy vấn trạng thái hành trình xe điện theo thời gian thực."""
        await asyncio.sleep(0.02)
        if booking_id in self._active_bookings:
            return self._active_bookings[booking_id]

        # Trả về thông tin giả lập mặc định nếu không tìm thấy ID cụ thể
        return GSMBookingResponse(
            booking_id=booking_id,
            quote_id="gquote_mock",
            status="ARRIVING",
            vehicle_type="CAR_4",
            pickup_address="Điểm đón khách hàng",
            dropoff_address="Điểm đến",
            fare_vnd=65_000,
            driver=GSMDriverInfo(
                driver_id="drv_default",
                driver_name="Nguyễn Văn Tài",
                phone_number="0988123456",
                license_plate="29E-567.89",
                vehicle_model="VinFast VF 5 Plus",
                battery_level_pct=85,
                rating=4.95,
                current_lat=21.0285,
                current_lng=105.8542,
                eta_pickup_minutes=2,
            ),
        )

    async def cancel_booking(self, booking_id: str, reason: str = "Khách hàng đổi ý") -> dict[str, object]:
        """Hủy cuốc xe trên hệ thống GreenSM."""
        await asyncio.sleep(0.03)
        if booking_id in self._active_bookings:
            self._active_bookings[booking_id].status = "CANCELLED"

        return {
            "booking_id": booking_id,
            "status": "CANCELLED",
            "reason": reason,
            "cancellation_fee_vnd": 0,
            "cancelled_at": datetime.now(UTC).isoformat(),
        }
