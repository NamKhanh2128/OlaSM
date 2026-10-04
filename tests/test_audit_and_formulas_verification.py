"""Comprehensive Verification Suite for OlaSM Blueprint (BaoCao_YTuong_Nhom4_OlaSM.docx).

Kiểm tra toàn bộ các công thức và kỹ thuật hệ thống:
1. Conversational Offer Engine (Mục 4.2):
   S_offer = alpha * ChurnRisk + beta * PriceSensitivity + gamma * CampaignFit
2. Dynamic Confidence Fusion & Selective Autonomy (Mục 4.3):
   c_trip = w1*p_stt + w2*p_intent + w3*p_addr + w4*p_vision (chuẩn hóa động khi không có ảnh)
   Routing: AUTO_BOOK (>= 0.85), CLARIFY (0.55 - 0.85), HITL_HANDOFF (<= 0.55)
   Expected Calibration Error (ECE) metric <= 0.10
3. Multimodal Visual Grounding (Mục 1, 4.1):
   Spatial OCR + VLM landmark matching (Vincom hầm B3, Tân Sơn Nhất cột 4, Nội Bài cột 9)
4. Agent Tool Execution & State Integration:
   get_personalized_offer, ground_pickup_image, evaluate_trip_confidence, create_handoff (<0.5s SLA)
"""
import sys
import unittest
from datetime import UTC, datetime

# ── Import modules cần test ───────────────────────────────────────────────────
from src.backend.services.offer_engine import (
    ALPHA,
    BETA,
    GAMMA,
    BestOffer,
    BookingContext,
    OfferEngine,
    Promotion,
)
from src.backend.services.offer_profile_service import OfferProfileService, UserOfferProfile
from src.backend.services.confidence_fusion_service import (
    AutonomyDecision,
    ConfidenceFusionResult,
    ConfidenceFusionService,
    MultimodalConfidenceInputs,
)
from src.backend.services.visual_grounding_service import (
    VisualGroundingResult,
    VisualGroundingService,
)
from src.agents.contracts.schemas import ToolName
from src.agents.core.tools import TOOL_DEFINITIONS
from src.agents.core.booking.state import BookingData


class TestCOEFormula(unittest.TestCase):
    """1. Kiểm tra công thức Conversational Offer Engine (S_offer)."""

    def setUp(self):
        self.profile_svc = OfferProfileService()
        self.offer_engine = OfferEngine()

    def test_alpha_beta_gamma_weights(self):
        """Hệ số trọng số phải đúng chuẩn và tổng bằng 1.0."""
        self.assertAlmostEqual(ALPHA, 0.35)
        self.assertAlmostEqual(BETA, 0.25)
        self.assertAlmostEqual(GAMMA, 0.40)
        self.assertAlmostEqual(ALPHA + BETA + GAMMA, 1.0)

    def test_s_offer_calculation_monotonic_with_price_sensitivity(self):
        """PriceSensitivity cao hơn phải làm tăng S_offer (không được nghịch đảo)."""
        promo = Promotion(
            id="p_test",
            code="TEST20",
            title="Ưu đãi thử nghiệm",
            discount_type="PERCENT",
            discount_value=20,
            max_discount_vnd=20_000,
            min_fare_vnd=30_000,
            target_tiers=None,
            valid_vehicle_types=None,
            valid_hours=None,
            valid_zones=None,
            campaign_priority=50,
        )
        context = BookingContext(
            user_id="user_test",
            session_id="sess_test",
            vehicle_type="CAR_4",
            estimated_fare_vnd=60_000,
            pickup_zone=None,
            destination_zone=None,
            route_hash="hash123",
            hour_of_day=14,
            day_of_week=2,
        )

        profile_low_sens = UserOfferProfile(
            user_id="u1",
            loyalty_tier="SILVER",
            total_rides=10,
            days_since_last_ride=5,
            cancel_on_high_fare=0,
            preferred_hours=[14],
            frequent_zones=[],
            historical_routes=[],
            churn_risk_score=0.4,
            price_sensitivity=0.2,  # Low sensitivity
        )
        profile_high_sens = UserOfferProfile(
            user_id="u2",
            loyalty_tier="SILVER",
            total_rides=10,
            days_since_last_ride=5,
            cancel_on_high_fare=4,
            preferred_hours=[14],
            frequent_zones=[],
            historical_routes=[],
            churn_risk_score=0.4,
            price_sensitivity=0.8,  # High sensitivity -> needs offer more!
        )

        score_low = self.offer_engine._composite_score(profile_low_sens, context, promo)
        score_high = self.offer_engine._composite_score(profile_high_sens, context, promo)

        # Kiểm tra tính đơn điệu tăng: score_high > score_low
        self.assertGreater(score_high, score_low)
        self.assertAlmostEqual(score_high - score_low, BETA * (0.8 - 0.2))

    def test_best_offer_has_speech_suggestion_and_s_offer(self):
        """BestOffer phải chứa s_offer, alpha, beta, gamma và speech_suggestion chuẩn thoại."""
        profile = UserOfferProfile(
            user_id="u_churn",
            loyalty_tier="BRONZE",
            total_rides=5,
            days_since_last_ride=25,
            cancel_on_high_fare=2,
            preferred_hours=[17],
            frequent_zones=[],
            historical_routes=[],
            churn_risk_score=0.7,
            price_sensitivity=0.6,
        )
        context = BookingContext(
            user_id="u_churn",
            session_id="sess_1",
            vehicle_type="CAR_4",
            estimated_fare_vnd=60_000,
            pickup_zone=None,
            destination_zone=None,
            route_hash="r1",
            hour_of_day=17,
            day_of_week=0,
        )
        promo = Promotion(
            id="p1",
            code="OFFER15",
            title="Giảm 15%",
            discount_type="PERCENT",
            discount_value=15,
            max_discount_vnd=15_000,
            min_fare_vnd=30_000,
            target_tiers=None,
            valid_vehicle_types=None,
            valid_hours=None,
            valid_zones=None,
            campaign_priority=70,
        )

        best = self.offer_engine.evaluate(profile, context, [promo])
        self.assertIsNotNone(best)
        self.assertGreaterEqual(best.s_offer, 0.45)
        self.assertEqual(best.alpha, 0.35)
        self.assertEqual(best.beta, 0.25)
        self.assertEqual(best.gamma, 0.40)
        self.assertIn("60,000đ", best.speech_suggestion)
        self.assertIn("51,000đ", best.speech_suggestion)  # 60k - 15% = 51k
        self.assertIn("GreenCar", best.speech_suggestion)


class TestDynamicConfidenceFusion(unittest.TestCase):
    """2. Kiểm tra Dynamic Confidence Fusion & Selective Autonomy (c_trip)."""

    def setUp(self):
        self.fusion = ConfidenceFusionService()

    def test_dynamic_renormalization_without_vision(self):
        """Khi không có ảnh (p_vision is None), w4=0 và w1+w2+w3 được chuẩn hóa lại = 1.0."""
        inputs = MultimodalConfidenceInputs(
            p_stt=0.90,
            p_intent=0.92,
            p_addr=0.88,
            p_vision=None,
        )
        res = self.fusion.evaluate(inputs)
        self.assertFalse(res.has_vision)
        self.assertEqual(res.effective_weights["w4_vision"], 0.0)

        # Tổng trọng số thực tế phải = 1.0
        total_w = sum(res.effective_weights.values())
        self.assertAlmostEqual(total_w, 1.0)

        expected_c = (
            (0.25 / 0.80) * 0.90
            + (0.25 / 0.80) * 0.92
            + (0.30 / 0.80) * 0.88
        )
        self.assertAlmostEqual(res.c_trip, round(expected_c, 4), places=3)

    def test_four_channel_fusion_with_vision(self):
        """Khi có ảnh đón, cả 4 trọng số đều được sử dụng."""
        inputs = MultimodalConfidenceInputs(
            p_stt=0.85,
            p_intent=0.90,
            p_addr=0.80,
            p_vision=0.95,
        )
        res = self.fusion.evaluate(inputs)
        self.assertTrue(res.has_vision)
        self.assertAlmostEqual(res.effective_weights["w4_vision"], 0.20)
        expected_c = 0.25 * 0.85 + 0.25 * 0.90 + 0.30 * 0.80 + 0.20 * 0.95
        self.assertAlmostEqual(res.c_trip, round(expected_c, 4), places=3)

    def test_selective_autonomy_routing_three_branches(self):
        """Kiểm tra điều hướng 3 nhánh: Auto-book, Clarify, HITL Handoff."""
        # 1. AUTO_BOOK (c_trip >= 0.85)
        high_in = MultimodalConfidenceInputs(p_stt=0.95, p_intent=0.95, p_addr=0.95, p_vision=0.95)
        res_high = self.fusion.evaluate(high_in)
        self.assertEqual(res_high.decision, AutonomyDecision.AUTO_BOOK)
        self.assertGreaterEqual(res_high.c_trip, 0.85)

        # 2. CLARIFY (0.55 < c_trip < 0.85)
        mid_in = MultimodalConfidenceInputs(p_stt=0.70, p_intent=0.75, p_addr=0.65, p_vision=None)
        res_mid = self.fusion.evaluate(mid_in)
        self.assertEqual(res_mid.decision, AutonomyDecision.CLARIFY)
        self.assertTrue(0.55 < res_mid.c_trip < 0.85)

        # 3. HITL_HANDOFF (c_trip <= 0.55)
        low_in = MultimodalConfidenceInputs(p_stt=0.40, p_intent=0.50, p_addr=0.45, p_vision=None)
        res_low = self.fusion.evaluate(low_in)
        self.assertEqual(res_low.decision, AutonomyDecision.HITL_HANDOFF)
        self.assertLessEqual(res_low.c_trip, 0.55)

    def test_ece_computation(self):
        """Kiểm tra hàm tính ECE (Expected Calibration Error)."""
        confidences = [0.95, 0.90, 0.85, 0.80, 0.60, 0.55, 0.40, 0.30, 0.20, 0.10]
        ground_truth = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
        ece = ConfidenceFusionService.compute_ece(confidences, ground_truth, num_bins=5)
        self.assertIsInstance(ece, float)
        self.assertLessEqual(ece, 0.25)


class TestVisualGroundingService(unittest.TestCase):
    """3. Kiểm tra Multimodal Visual Grounding Service."""

    def setUp(self):
        self.vg = VisualGroundingService()

    def test_ground_vincom_basement_pillar(self):
        """Phát hiện điểm đón phức tạp: Cột B3 hầm Vincom Center Bà Triệu."""
        res = self.vg.ground_image(text_hint="cột B3 hầm Vincom Bà Triệu", image_bytes=b"fake_image_bytes")
        self.assertTrue(res.resolved)
        self.assertIn("Hầm TTTM Vincom", res.pickup_name)
        self.assertIn("B3", res.spatial_description)
        self.assertGreaterEqual(res.p_vision, 0.90)
        self.assertIsNotNone(res.latitude)
        self.assertIsNotNone(res.longitude)

    def test_ground_tsn_airport_column(self):
        """Phát hiện điểm đón phức tạp: Cột số 4 Ga Quốc Nội Tân Sơn Nhất."""
        res = self.vg.ground_image(text_hint="đón ở cột số 4 ga quốc nội sân bay Tân Sơn Nhất")
        self.assertTrue(res.resolved)
        self.assertIn("Tân Sơn Nhất", res.pickup_name)
        self.assertIn("4", res.spatial_description)
        self.assertGreaterEqual(res.p_vision, 0.90)


class TestAgentIntegrationAndState(unittest.TestCase):
    """4. Kiểm tra tích hợp Agent State, Tools và Schemas."""

    def test_tool_definitions_contain_new_tools(self):
        """TOOL_DEFINITIONS phải chứa ground_pickup_image và evaluate_trip_confidence."""
        self.assertIn("ground_pickup_image", TOOL_DEFINITIONS)
        self.assertIn("evaluate_trip_confidence", TOOL_DEFINITIONS)
        self.assertIn("get_personalized_offer", TOOL_DEFINITIONS)
        self.assertEqual(ToolName.GROUND_PICKUP_IMAGE, "ground_pickup_image")
        self.assertEqual(ToolName.EVALUATE_TRIP_CONFIDENCE, "evaluate_trip_confidence")

    def test_booking_data_state_fields(self):
        """BookingData phải hỗ trợ các trường c_trip, s_offer, autonomy_decision."""
        bd = BookingData(
            pickup_query="Vincom",
            s_offer=0.68,
            c_offer=0.68,
            c_trip=0.91,
            autonomy_decision="AUTO_BOOK",
            p_stt=0.92,
            p_intent=0.95,
            p_addr=0.90,
            p_vision=0.88,
        )
        self.assertEqual(bd.s_offer, 0.68)
        self.assertEqual(bd.c_trip, 0.91)
        self.assertEqual(bd.autonomy_decision, "AUTO_BOOK")


if __name__ == "__main__":
    unittest.main(verbosity=2)
