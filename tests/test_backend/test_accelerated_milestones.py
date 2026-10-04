"""Unit tests for accelerated Week 4 & Week 5 milestones.

Covers:
1. VietnameseAudioChunker (Vietnamese streaming punctuation & clause boundaries)
2. OfferProfileRepository (Cold-start resolution & incremental trip updating)
3. GSMSandboxClient (OpenAPI quote, booking, status, cancellation in mock sandbox)
4. ECEService (Calibration error, reliability bins, optimal temperature scaling)
5. GeminiVisionService (Multimodal vision analysis & spatial landmark mapping)
"""
from __future__ import annotations

import pytest

from src.agents.core.audio_chunker import VietnameseAudioChunker
from src.backend.integrations.gsm_sandbox_client import GSMSandboxClient
from src.backend.repositories.offer_profile_repository import OfferProfileRepository
from src.backend.services.confidence_fusion_service import (
    AutonomyDecision,
    ConfidenceFusionService,
    MultimodalConfidenceInputs,
)
from src.backend.services.ece_service import ECEService
from src.backend.services.gemini_vision_service import GeminiVisionService


# ─── 1. Vietnamese Audio Chunker Tests ──────────────────────────────────────────


def test_vietnamese_audio_chunker_sentence_delimiters():
    chunker = VietnameseAudioChunker(min_chunk_chars=10)
    text = "Dạ chào bạn. Tôi là trợ lý ảo OlaSM! Bạn muốn đi đâu?"
    chunks = chunker.chunk_text(text)
    assert len(chunks) >= 2
    assert any("Dạ chào bạn." in c for c in chunks)
    assert any("Bạn muốn đi đâu?" in c for c in chunks)


def test_vietnamese_audio_chunker_preserves_abbreviations():
    chunker = VietnameseAudioChunker(min_chunk_chars=15)
    # TP.HCM and 0912.345.678 shouldn't cause premature splits on the dot
    text = "Đón tôi tại số 123 đường Lê Lợi, TP.HCM qua số 0912.345.678 nhé ạ."
    chunks = chunker.chunk_text(text)
    # Should not split inside TP.HCM
    full_reconstructed = " ".join(chunks)
    assert "TP.HCM" in full_reconstructed
    assert "0912.345.678" in full_reconstructed


def test_vietnamese_audio_chunker_stats():
    chunker = VietnameseAudioChunker(min_chunk_chars=12)
    tokens = ["Dạ, ", "tôi ", "đã ", "tìm ", "thấy ", "xe ", "cho ", "bạn ", "rồi ", "ạ.\n"]
    emitted = []
    for t in tokens:
        emitted.extend(chunker.push(t))
    if rem := chunker.flush():
        emitted.append(rem)

    assert chunker.stats.tokens_received == len(tokens)
    assert chunker.stats.chunks_emitted >= 1
    assert chunker.stats.first_chunk_chars > 0


# ─── 2. Offer Profile Repository & Cold-Start Tests ────────────────────────────


@pytest.mark.asyncio
async def test_offer_profile_cold_start_peak_hour():
    repo = OfferProfileRepository()
    # Peak hour = 8 (8am)
    profile = await repo.get_or_create_profile(user_id="usr_cold_peak", current_hour=8)
    assert profile.total_rides == 0
    assert profile.loyalty_tier == "BRONZE"
    # Peak hour prioritizes availability over deep discounts
    assert profile.price_sensitivity == 0.40
    assert profile.churn_risk_score == 0.25


@pytest.mark.asyncio
async def test_offer_profile_cold_start_offpeak_hour():
    repo = OfferProfileRepository()
    # Off-peak hour = 14 (2pm)
    profile = await repo.get_or_create_profile(user_id="usr_cold_offpeak", current_hour=14)
    assert profile.total_rides == 0
    assert profile.loyalty_tier == "BRONZE"
    # Off-peak gives higher sensitivity to stimulate first ride with vouchers
    assert profile.price_sensitivity == 0.60
    assert profile.churn_risk_score == 0.15


@pytest.mark.asyncio
async def test_offer_profile_incremental_update_after_trip():
    repo = OfferProfileRepository()
    uid = "usr_traveler_01"
    # Initially cold start
    await repo.get_or_create_profile(user_id=uid, current_hour=10)

    # Complete 1st trip
    p1 = await repo.update_after_trip(
        user_id=uid,
        fare_vnd=75_000,
        vehicle_type="CAR_4",
        used_promo=True,
        is_peak=False,
        zone="cau_giay",
    )
    assert p1.total_rides == 1
    assert p1.promo_usage_count == 1
    assert p1.avg_fare_accepted == 75_000
    assert "cau_giay" in p1.frequent_zones

    # Complete 4 more trips (total 5 -> tier SILVER)
    for _ in range(4):
        await repo.update_after_trip(user_id=uid, fare_vnd=80_000, vehicle_type="CAR_4")

    updated = await repo.get_or_create_profile(user_id=uid)
    assert updated.total_rides == 5
    assert updated.loyalty_tier == "SILVER"


# ─── 3. GSM Sandbox Client Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gsm_sandbox_client_quote_and_booking():
    client = GSMSandboxClient(mock_mode=True)

    # Request quote
    quote = await client.request_fare_quote(
        pickup_lat=21.0285,
        pickup_lng=105.8542,
        dropoff_lat=21.0116,
        dropoff_lng=105.8498,
        vehicle_type="CAR_4",
    )
    assert quote.quote_id.startswith("gquote_")
    assert quote.distance_km > 0
    assert quote.final_fare_vnd > 0
    assert quote.available_drivers_nearby >= 1

    # Create booking
    booking = await client.create_booking(
        quote_id=quote.quote_id,
        customer_phone="0912345678",
        customer_name="Nguyễn Văn A",
        pickup_address="12 Chùa Bộc",
        dropoff_address="88 Láng Hạ",
        pickup_lat=21.0285,
        pickup_lng=105.8542,
        dropoff_lat=21.0116,
        dropoff_lng=105.8498,
        vehicle_type="CAR_4",
    )
    assert booking.booking_id.startswith("gsm_bk_")
    assert booking.status == "ASSIGNED"
    assert booking.driver is not None
    assert "VinFast" in booking.driver.vehicle_model

    # Query status
    status = await client.get_booking_status(booking.booking_id)
    assert status.booking_id == booking.booking_id

    # Cancel booking
    cancel_res = await client.cancel_booking(booking.booking_id, reason="Khách đổi lịch")
    assert cancel_res["status"] == "CANCELLED"


# ─── 4. ECE Service Calibration Tests ─────────────────────────────────────────


def test_ece_service_evaluation():
    ece_svc = ECEService(target_ece_threshold=0.10, default_bins=5)
    # Well-calibrated predictions: confidences close to ground truth
    confs = [0.95, 0.90, 0.85, 0.80, 0.60, 0.55, 0.20, 0.10]
    gts = [1, 1, 1, 1, 1, 0, 0, 0]

    report = ece_svc.evaluate(confs, gts, num_bins=5)
    assert report.num_samples == len(confs)
    assert report.ece <= 0.25
    assert len(report.bins) == 5


def test_ece_service_optimal_temperature_finding():
    ece_svc = ECEService(target_ece_threshold=0.10)
    # Overconfident scenario
    confs = [0.99, 0.98, 0.95, 0.90, 0.85, 0.80, 0.70, 0.65]
    gts = [1, 1, 1, 0, 1, 0, 1, 0]

    t_opt = ece_svc.find_optimal_temperature(confs, gts, search_range=(0.5, 3.0), steps=20)
    assert t_opt > 0.0

    calibrated_report = ece_svc.evaluate(confs, gts, temperature=t_opt)
    uncalibrated_report = ece_svc.evaluate(confs, gts, temperature=1.0)
    assert calibrated_report.ece <= uncalibrated_report.ece + 1e-4


# ─── 5. Gemini Vision Service Tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_gemini_vision_service_complex_landmarks():
    svc = GeminiVisionService()

    # Airport pillar test
    res_tsn = await svc.analyze_pickup_image(
        image_data="base64_sample_airport_image",
        user_hint_text="Tôi đang ở cột 4 ga quốc nội Tân Sơn Nhất",
    )
    assert "Tân Sơn Nhất" in res_tsn.detected_landmark
    assert res_tsn.confidence_p_vision >= 0.80
    assert res_tsn.latitude is not None

    # Shopping mall basement pillar test
    res_vincom = await svc.analyze_pickup_image(
        image_data="base64_sample_basement_image",
        user_hint_text="Cột B3 hầm Vincom Bà Triệu",
    )
    assert "Vincom" in res_vincom.detected_landmark
    assert res_vincom.confidence_p_vision >= 0.80
    assert res_vincom.bounding_box_detected is True
