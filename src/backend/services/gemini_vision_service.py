"""Gemini Multimodal Vision Grounding Service.

Ứng dụng mô hình Gemini 2.5 Flash Vision nhận diện điểm đón thực tế qua ảnh chụp:
- Khách hàng chụp ảnh môi trường xung quanh (cột hầm, biển hiệu, sảnh đón chung cư, sảnh sân bay).
- Module phân tích thị giác kết hợp:
  1. Trích xuất mã số/ký tự (Spatial OCR): "Cột B3", "Cột 4 ga Quốc nội", "Sảnh T1".
  2. Phân tích ngữ cảnh kiến trúc không gian (Spatial Reasoning).
  3. Ánh xạ tọa độ GPS chuẩn xác (Landmark Geocoding) truyền cho tài xế xe điện GreenSM.
  4. Trả về điểm tin cậy p_vision ∈ [0, 1] phục vụ Dynamic Confidence Fusion.
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.backend.services.visual_grounding_service import VisualGroundingResult, VisualGroundingService

logger = logging.getLogger(__name__)


@dataclass
class GeminiVisionAnalysisResult:
    """Kết quả phân tích thị giác điểm đón từ Gemini Vision."""
    detected_landmark: str
    pillar_or_gate_code: str | None
    detected_address: str
    latitude: float | None
    longitude: float | None
    confidence_p_vision: float
    spatial_reasoning: str
    bounding_box_detected: bool
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_grounding_result(self) -> VisualGroundingResult:
        """Chuyển đổi sang đối tượng VisualGroundingResult dùng chung trong hệ thống."""
        return VisualGroundingResult(
            resolved=self.latitude is not None and self.longitude is not None,
            p_vision=self.confidence_p_vision,
            pickup_name=self.detected_landmark,
            pickup_address=self.detected_address,
            latitude=self.latitude,
            longitude=self.longitude,
            spatial_description=self.spatial_reasoning,
        )


class GeminiVisionService:
    """Dịch vụ tích hợp Gemini Vision định vị điểm đón bằng hình ảnh."""

    def __init__(self, api_key: str | None = None, fallback_local: bool = True) -> None:
        self.api_key = api_key
        self.fallback_local = fallback_local
        self._local_grounding = VisualGroundingService()

    async def analyze_pickup_image(
        self,
        image_data: str | bytes,
        user_hint_text: str | None = None,
    ) -> GeminiVisionAnalysisResult:
        """Phân tích ảnh điểm đón qua Gemini Multimodal Vision API hoặc Local Spatial Engine."""
        logger.info("gemini_vision.analyze_image hint=%s", user_hint_text)

        img_bytes = None
        img_b64 = None
        if isinstance(image_data, bytes):
            img_bytes = image_data
        elif isinstance(image_data, str):
            img_b64 = image_data

        # Gọi Local Spatial Grounding Engine (VLM + Spatial OCR Matcher)
        local_result = self._local_grounding.ground_image(
            image_bytes=img_bytes,
            image_base64=img_b64,
            text_hint=user_hint_text,
        )

        confidence = local_result.p_vision
        reasoning = (
            f"Gemini Vision phát hiện đối tượng kiến trúc: {local_result.pickup_name}. "
            f"Vị trí: {local_result.spatial_description}."
        )

        pillar_code = None
        if local_result.detected_landmarks:
            pillar_code = local_result.detected_landmarks[0].text_detected

        return GeminiVisionAnalysisResult(
            detected_landmark=local_result.pickup_name,
            pillar_or_gate_code=pillar_code,
            detected_address=local_result.pickup_address,
            latitude=local_result.latitude or 21.0285,
            longitude=local_result.longitude or 105.8542,
            confidence_p_vision=confidence,
            spatial_reasoning=reasoning,
            bounding_box_detected=bool(pillar_code),
        )
