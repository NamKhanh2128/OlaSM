"""Unit tests for Ultra-Low-Cost mobile architecture service.

Validates:
1. On-device mobile speech payload (0 VND server TTS cost for iOS and Android).
2. Fallback behavior for traditional telephony/SIP hotline.
3. In-app zero-cost POI gazetteer lookup.
4. Scale unit economics calculation (>90% savings for GreenSM).
"""
from __future__ import annotations

from src.backend.services.ultra_low_cost_service import UltraLowCostService


def test_ultra_low_cost_android_payload():
    svc = UltraLowCostService()
    payload = svc.resolve_mobile_speech_payload(
        bot_response_text="Xe 4 chỗ đang tới đón bạn tại số 12 Chùa Bộc nhé ạ.",
        client_platform="android",
    )
    assert payload.estimated_server_cost_vnd == 0.0
    assert payload.fallback_cloud_tts_required is False
    assert payload.recommended_engine == "GoogleTTS"
    assert "Chùa Bộc" in payload.speech_text


def test_ultra_low_cost_ios_payload():
    svc = UltraLowCostService()
    payload = svc.resolve_mobile_speech_payload(
        bot_response_text="Dạ, GreenSM xin xác nhận.",
        client_platform="ios",
    )
    assert payload.estimated_server_cost_vnd == 0.0
    assert payload.fallback_cloud_tts_required is False
    assert payload.recommended_engine == "AVSpeechSynthesizer"


def test_ultra_low_cost_telephony_hotline_fallback():
    svc = UltraLowCostService()
    payload = svc.resolve_mobile_speech_payload(
        bot_response_text="Xin chào tổng đài viên.",
        client_platform="telephony_sip",
    )
    assert payload.fallback_cloud_tts_required is True
    assert payload.estimated_server_cost_vnd > 0.0


def test_ultra_low_cost_local_poi_lookup():
    svc = UltraLowCostService()
    poi = svc.lookup_local_poi("vincom bà triệu")
    assert poi is not None
    assert "Vincom Center" in poi["name"]
    assert poi["lat"] > 21.0

    # Non-existent POI returns None (safely fallbacks to map provider)
    missing = svc.lookup_local_poi("ngõ nhỏ vắng vẻ không tên 999")
    assert missing is None


def test_ultra_low_cost_economic_savings():
    svc = UltraLowCostService()
    # 50k rides per day
    estimate = svc.calculate_cost_comparison(rides_per_day=50_000)
    assert estimate.savings_percentage > 90.0
    assert estimate.monthly_savings_vnd > 400_000_000  # Tiết kiệm hàng trăm triệu đến cả tỷ đồng
