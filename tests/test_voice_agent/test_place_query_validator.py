"""Regression tests for place query validation."""

import pytest

from src.voice_agent.place_query_validator import is_valid_place_query, is_valid_single_word_place_query


class TestSingleWordQueryValidation:
    """Tests for single-word place query validation."""

    def test_valid_single_word_places(self) -> None:
        """Single-word valid places should be accepted."""
        # These are actual places/aliases in the gazetteer
        assert is_valid_single_word_place_query("VinUni") is True

    def test_blocked_filler_words_single_word(self) -> None:
        """Single filler/discourse words should be rejected."""
        blocked_words = [
            "rồi",  # rồi
            "thôi",  # thôi
            "vâng",  # vâng
            "nhầm",  # nhầm (mistake)
            "muốn",  # muốn (want)
            "cho",  # cho (for)
            "đó",  # đó (that)
            "đây",  # đây (here)
            "đi",  # đi (go)
            "đến",  # đến (arrive)
            "tôi",  # tôi (I)
            "bạn",  # bạn (you)
        ]
        for word in blocked_words:
            assert is_valid_single_word_place_query(word) is False, f"Word '{word}' should be blocked"

    def test_invalid_single_word_unknown_place(self) -> None:
        """Single-word queries that don't match any known place should be rejected."""
        # These don't match canonical names or aliases in gazetteer
        assert is_valid_single_word_place_query("xyzunknown") is False
        assert is_valid_single_word_place_query("unknownplace") is False


class TestPickupDestinationQueryValidation:
    """Tests for comprehensive place query validation."""

    def test_empty_or_whitespace_queries(self) -> None:
        """Empty, None, or whitespace-only queries should be rejected."""
        assert is_valid_place_query("") is False
        assert is_valid_place_query("   ") is False
        assert is_valid_place_query("\t\n") is False

    def test_multi_word_queries_are_allowed(self) -> None:
        """Multi-word queries should pass validation (gazetteer handles substring matching)."""
        # These are multi-word queries that should pass validation
        # The actual gazetteer search will handle whether they find results
        assert is_valid_place_query("Bưu điện Hà Nội") is True
        assert is_valid_place_query("Đại học Bách khoa") is True

    def test_problematic_single_words_for_pickup(self) -> None:
        """Regression: filler words should be rejected for pickup point."""
        problematic_inputs = [
            "rồi",  # rồi - might be ASR for "resolve"
            "thôi",  # thôi - might be "stop"
            "vâng",  # vâng - "yes" in formal
            "nhầm",  # nhầm - "mistake"
            "muốn",  # muốn - "want"
            "cho",  # cho - "for"
            "đây",  # đây - "here"
            "đó",  # đó - "there"
            "đi",  # đi - "go"
            "đến",  # đến - "arrive"
        ]
        for word in problematic_inputs:
            assert is_valid_place_query(word) is False, f"Pickup query '{word}' should be blocked"

    def test_problematic_single_words_for_destination(self) -> None:
        """Regression: filler words should be rejected for destination point."""
        problematic_inputs = [
            "rồi",  # rồi
            "thôi",  # thôi
            "vâng",  # vâng
            "nhầm",  # nhầm
            "muốn",  # muốn
            "cho",  # cho
            "đây",  # đây
            "đó",  # đó
            "đi",  # đi
            "đến",  # đến
        ]
        for word in problematic_inputs:
            assert is_valid_place_query(word) is False, f"Destination query '{word}' should be blocked"

    def test_problematic_single_words_for_explicit_change(self) -> None:
        """Regression: filler words should not be accepted in explicit change queries."""
        # These come from extract_explicit_booking_change
        problematic_user_inputs = [
            "Đổi điểm đón thành rồi",
            "Đổi điểm đên thành thôi",
            "Sửa điểm đón là vâng",
            "Đổi địa điểm thành nhầm",
        ]
        # After extraction, the values would be:
        problematic_queries = ["rồi", "thôi", "vâng", "nhầm"]
        for query in problematic_queries:
            assert is_valid_place_query(query) is False

    def test_multi_word_with_mostly_filler_rejected(self) -> None:
        """Multi-word queries that are all filler words should be rejected."""
        # All filler words, no real place name
        assert is_valid_place_query("tôi rồi thôi") is False
        assert is_valid_place_query("cho đến đây") is False

    def test_multi_word_with_at_least_one_valid_word(self) -> None:
        """Multi-word queries with at least one non-filler word should pass."""
        # Has both filler and content words - should pass (gazetteer decides)
        assert is_valid_place_query("sảnh chính Bách khoa") is True
        assert is_valid_place_query("phía trước VinUni") is True

    def test_gazetteer_exact_names_allowed(self) -> None:
        """Exact canonical place names should pass validation."""
        # VinUni is a genuine single-word place
        assert is_valid_place_query("VinUni") is True


class TestRegressionCases:
    """Regression tests for the specific bug cases mentioned."""

    def test_regression_single_word_rồi_not_saved_to_pickup(self) -> None:
        """Bug: 'rồi' should not be saved as pickup_query."""
        assert is_valid_place_query("rồi") is False

    def test_regression_single_word_thôi_not_saved_to_destination(self) -> None:
        """Bug: 'thôi' should not be saved as destination_query."""
        assert is_valid_place_query("thôi") is False

    def test_regression_single_word_vâng_not_saved(self) -> None:
        """Bug: 'vâng' should not be saved as pickup or destination."""
        assert is_valid_place_query("vâng") is False

    def test_regression_cho_not_resolved_to_unrelated_place(self) -> None:
        """Bug: 'cho' should not cause substring match to Chợ Đồng Xuân."""
        # With validation, 'cho' should be rejected before reaching gazetteer
        assert is_valid_place_query("cho") is False

    def test_regression_diem_don_not_substring_match(self) -> None:
        """Bug: 'điểm đón' (point pickup) should not match any unrelated place as substring."""
        # This would be a multi-word query, which should pass validation
        # but 'điểm' and 'đón' are mostly filler-like words
        # However, it's a compound that users might say, so it passes validation
        # The gazetteer side handles rejecting generic location terms
        assert is_valid_place_query("điểm đón") is True  # Multi-word, passes validation

    def test_regression_labeled_input_validation(self) -> None:
        """Test labeled input extraction examples from user report."""
        # From extract_labeled_booking_places - these would be extracted as values
        # Examples from the bug report
        assert is_valid_place_query("rồi") is False  # Extracted from label, should reject
        assert is_valid_place_query("vâng") is False
        # But valid places should pass
        assert is_valid_place_query("Chợ Đồng Xuân") is True

    def test_regression_explicit_change_extraction(self) -> None:
        """Test explicit booking change extraction examples."""
        # From extract_explicit_booking_change
        # "Đổi điểm đón thành rồi" -> replacement="rồi" -> should reject
        assert is_valid_place_query("rồi") is False
        # "Đổi điểm đến thành Hồ Gươm" -> replacement="Hồ Gươm" -> should accept
        assert is_valid_place_query("Hồ Gươm") is True

    def test_regression_complete_route_extraction(self) -> None:
        """Test complete route extraction examples."""
        # From extract_complete_route
        # "Từ VinUni đến Hồ Gươm" -> pickup="VinUni", destination="Hồ Gươm"
        assert is_valid_place_query("VinUni") is True
        assert is_valid_place_query("Hồ Gươm") is True
        # But single words like would have failed in old code:
        assert is_valid_place_query("đi") is False
        assert is_valid_place_query("tới") is False
