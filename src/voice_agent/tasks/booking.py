"""LiveKit ``AgentTask`` implementing AloSM's native booking happy path."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import unicodedata
from collections.abc import Awaitable, Callable
from typing import Literal

from livekit.agents import AgentTask, RunContext, StopResponse, ToolError, function_tool, llm
from pydantic import BaseModel, ConfigDict

from src.voice_agent.persistence import (
    EphemeralVoiceStateStore,
    VoiceStateConflictError,
    VoiceStateStore,
)
from src.voice_agent.place_query_validator import is_valid_place_query
from src.voice_agent.session_data import (
    VEHICLE_TYPE_ORDER,
    AloSMSessionData,
    BookingDraft,
    BookingField,
    BookingResult,
    BookingTarget,
    PlaceCandidate,
    PostBookingSupportState,
    QuoteSnapshot,
    VehicleType,
    post_booking_menu_message,
    vehicle_spoken_label,
)
from src.voice_agent.state_sync import publish_booking_state
from src.voice_agent.tools import (
    BookingToolsService,
    PlaceToolsService,
    QuoteToolsService,
)
from src.voice_agent.transcript_rewrite import TranscriptRewriter, rewrite_livekit_user_turn

logger = logging.getLogger(__name__)

_LOW_CONFIDENCE_TRUSTED_PLACE_PROVIDERS = frozenset(
    {"local_gazetteer", "local_landmark_mock", "local_landmark_mock_exact"}
)


class BookingOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["created", "abandoned", "needs_handoff"]
    message: str
    booking: BookingResult | None = None
    reason: str | None = None


HandoffHandler = Callable[[str], Awaitable[str]]
BookingChangeToken = tuple[BookingField, int]

_REQUIRED_BOOKING_CONFIRMATION_PHRASE = "tôi xác nhận đặt xe"
_MIN_BOOKING_CONFIRMATION_WORDS = 4
_CONFIRMATION_CORE_PHRASES = (
    "xac nhan dat xe",
    "xac nhan dat chuyen",
    "dong y dat xe",
    "dong y dat chuyen",
    "dung roi dat xe",
    "dat xe giup toi",
    "dat xe cho toi",
)
_ADDITIONAL_REQUEST_MARKERS = (
    " nhung ",
    " tuy nhien ",
    " dong thoi ",
    " kem theo ",
    " va hay ",
    " voi yeu cau ",
    " nho tai xe ",
    " bao tai xe ",
)
_ALLOWED_CONFIRMATION_PREFIX_TOKENS = frozenset(
    {"toi", "vang", "dung", "roi", "xin", "hoan", "toan", "da", "ok"}
)
_ALLOWED_CONFIRMATION_SUFFIX_TOKENS = frozenset(
    {"nay", "nhe", "a", "giup", "toi", "luon", "di", "cho", "minh", "roi", "va", "cam", "on", "ban"}
)


def _normalize_confirmation(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold().replace("đ", "d"))
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    normalized = " ".join(re.sub(r"[^a-z0-9]+", " ", plain).split())
    return normalized.replace("xac nhan dap xe", "xac nhan dat xe")


def _confirmation_core_span(normalized: str) -> tuple[int, int] | None:
    matches = (
        (normalized.find(phrase), phrase)
        for phrase in _CONFIRMATION_CORE_PHRASES
        if phrase in normalized
    )
    start, phrase = min(matches, default=(-1, ""), key=lambda item: item[0])
    return (start, start + len(phrase)) if start >= 0 else None


def has_additional_driver_request(value: str) -> bool:
    """Reject confirmation turns that also contain a driver instruction."""

    normalized = _normalize_confirmation(value)
    padded = f" {normalized} "
    if any(marker in padded for marker in _ADDITIONAL_REQUEST_MARKERS):
        return True
    core_span = _confirmation_core_span(normalized)
    if core_span is None:
        return False
    start, end = core_span
    prefix_tokens = normalized[:start].split()
    suffix_tokens = normalized[end:].split()
    return any(token not in _ALLOWED_CONFIRMATION_PREFIX_TOKENS for token in prefix_tokens) or any(
        token not in _ALLOWED_CONFIRMATION_SUFFIX_TOKENS for token in suffix_tokens
    )


def is_explicit_confirmation(value: str) -> bool:
    normalized = _normalize_confirmation(value)
    tokens = normalized.split()
    if len(tokens) < _MIN_BOOKING_CONFIRMATION_WORDS:
        return False
    if {"khong", "chua", "huy", "thoi"}.intersection(tokens):
        return False
    if has_additional_driver_request(normalized):
        return False
    return _confirmation_core_span(normalized) is not None


def is_booking_abandonment_request(value: str) -> bool:
    """Recognize an explicit request to stop an unfinished booking draft."""

    normalized = _normalize_confirmation(value)
    return any(
        phrase in normalized
        for phrase in (
            "khong dat nua",
            "thoi khong dat",
            "dung dat nua",
            "bo dat xe",
            "huy yeu cau dat xe",
            "khong muon dat xe nua",
        )
    )


def requires_location_clarification(
    message: llm.ChatMessage | None,
    threshold: float,
    candidates: list[object] | None = None,
) -> bool:
    """Repeat only when low-confidence speech has no trusted location match.

    Scribe realtime can omit word logprobs and report zero confidence for an
    otherwise correct transcript. A canonical/alias gazetteer match is stronger
    evidence than that missing confidence signal; fuzzy matches remain blocked.
    """

    is_low_confidence = (
        message is not None and message.transcript_confidence is not None and message.transcript_confidence < threshold
    )
    has_trusted_candidate = any(
        getattr(candidate, "provider", None) in _LOW_CONFIDENCE_TRUSTED_PLACE_PROVIDERS
        for candidate in (candidates or [])
    )
    return is_low_confidence and not has_trusted_candidate


def can_auto_select_place(candidates: list[object]) -> bool:
    """Auto-select only one deterministic exact/alias gazetteer result.

    Fuzzy results and landmarks with multiple pickup points remain explicit
    clarification turns because a location is a booking-critical entity.
    """

    return len(candidates) == 1 and getattr(candidates[0], "provider", None) in {
        "local_gazetteer",
        "local_landmark_mock_exact",
    }


_SPOKEN_FILLER_PATTERN = re.compile(
    r"\b(?:ờ+|ơ+|ừm+|ừ+|ậm+|ưm+|hừm+|mmm+|à+)\b[,\s]*",
    re.IGNORECASE,
)
_BARGE_IN_PREFIX_PATTERN = re.compile(
    r"^(?:(?:ờ+|ơ+|ừm+|ừ+|ậm+|ưm+|hừm+|mmm+|à+|"
    r"khoan(?:\s+đã)?|đợi(?:\s+đã)?|chờ(?:\s+(?:đã|chút))?)[\s,.!?;:-]*)+",
    re.IGNORECASE,
)
_ASR_CUTOFF_FRAGMENT_PATTERN = re.compile(
    r"(?<!\S)[^\s,.!?;:]{1,8}-+(?=[\s,.!?;:]|$)",
    re.IGNORECASE,
)
_MAX_ROUTE_TRANSCRIPT_CHARS = 2_000
_ROUTE_START_MARKERS = (" đi từ ", " đi từ, ", " từ ", " từ, ")
_ROUTE_DESTINATION_MARKERS = (" tới ", " đến ")
_ROUTE_END_MARKERS = (
    " bằng xe ",
    " bằng ô tô ",
    " với xe ",
    " với ô tô ",
    ".",
    "!",
    "?",
    ";",
)


def _first_marker(
    value: str,
    markers: tuple[str, ...],
    *,
    start: int = 0,
) -> tuple[int, str] | None:
    """Find the earliest fixed marker in linear bounded text."""

    found = ((position, marker) for marker in markers if (position := value.find(marker, start)) >= 0)
    return min(found, key=lambda match: (match[0], -len(match[1])), default=None)


def extract_complete_route(value: str) -> tuple[str, str] | None:
    """Extract a bounded Vietnamese route without backtracking regex captures."""

    bounded = value[:_MAX_ROUTE_TRANSCRIPT_CHARS]
    compact = " ".join(_SPOKEN_FILLER_PATTERN.sub(" ", bounded).split())
    padded = f" {compact} "
    folded = padded.casefold()

    route_start = _first_marker(folded, _ROUTE_START_MARKERS)
    if route_start is None:
        return None
    pickup_start = route_start[0] + len(route_start[1])
    destination_marker = _first_marker(
        folded,
        _ROUTE_DESTINATION_MARKERS,
        start=pickup_start,
    )
    if destination_marker is None:
        return None

    destination_start = destination_marker[0] + len(destination_marker[1])
    route_end = _first_marker(folded, _ROUTE_END_MARKERS, start=destination_start)
    destination_end = route_end[0] if route_end is not None else len(padded) - 1
    pickup = padded[pickup_start : destination_marker[0]].strip(" ,")[:200]
    destination = padded[destination_start:destination_end].strip(" ,")[:200]
    if not pickup or not destination:
        return None

    # Validate extracted queries to prevent invalid single-word or filler words
    if not is_valid_place_query(pickup) or not is_valid_place_query(destination):
        return None

    return pickup, destination


_LABELED_PLACE_FIELD = (
    r"(?:điểm\s+đón|điểm\s+đi|nơi\s+đón|"
    r"điểm\s+đến|nơi\s+đến|đích\s+đến)"
)
_LABELED_PLACE_PATTERN = re.compile(
    rf"\b(?P<label>{_LABELED_PLACE_FIELD})\s*(?:(?:là|ở|tại)\s+)?"
    rf"(?P<value>[^.!?;]{{1,240}}?)(?=(?:\s*,\s*)?{_LABELED_PLACE_FIELD}\b|[.!?;]|$)",
    re.IGNORECASE,
)
_LABELED_PLACE_VALUE_PREFIXES = (
    ("phải", "là"),
    ("sẽ", "là"),
    ("là",),
    ("ở",),
    ("tại",),
    ("thành",),
    ("sang",),
)
_INVALID_LABELED_PLACE_VALUES = frozenset(
    {
        "la",
        "nhung",
        "phai",
        "phai la",
        "diem don",
        "diem den",
    }
)


def _clean_labeled_place_value(value: str) -> str:
    """Keep only a meaningful labelled place, never discourse/linker tokens."""

    raw_tokens = value.strip(" ,:").split()
    folded_tokens = tuple(_normalize_confirmation(token) for token in raw_tokens)
    for prefix in _LABELED_PLACE_VALUE_PREFIXES:
        normalized_prefix = tuple(_normalize_confirmation(token) for token in prefix)
        if _tokens_start_with(folded_tokens, 0, normalized_prefix):
            raw_tokens = raw_tokens[len(prefix) :]
            break
    place = _trim_trailing_non_entity_clause(" ".join(raw_tokens))
    normalized = _normalize_confirmation(place)
    if not normalized or normalized in _INVALID_LABELED_PLACE_VALUES:
        return ""

    # Use shared validator to reject filler words and invalid single-word queries
    if not is_valid_place_query(place):
        return ""

    return place[:200]


def extract_labeled_booking_places(value: str) -> dict[BookingTarget, str]:
    """Extract every explicitly labelled pickup/destination in one user turn."""

    places: dict[BookingTarget, str] = {}
    compact = " ".join(unicodedata.normalize("NFC", value[:1_000]).split())
    for match in _LABELED_PLACE_PATTERN.finditer(compact):
        label = " ".join(match.group("label").casefold().split())
        target: BookingTarget = "pickup" if label in {"điểm đón", "điểm đi", "nơi đón"} else "destination"
        place = _clean_labeled_place_value(match.group("value"))
        if place:
            places[target] = place
    return places


def extract_vehicle_type(value: str) -> VehicleType | None:
    """Map one explicit supported Vietnamese vehicle phrase without an LLM."""

    normalized = _normalize_confirmation(value)
    if re.search(r"\bxe may\b", normalized):
        return "MOTORBIKE"
    if re.search(r"\b(?:bon|4) cho\b", normalized):
        return "CAR_4"
    if re.search(r"\b(?:bay|7) cho\b", normalized):
        return "CAR_7"
    if re.search(r"\b(?:xe )?(?:cao cap|luxury)\b", normalized):
        return "LUXURY"
    return None


_CHANGE_CUE = r"(?:đổi|sửa|thay\s+đổi|thay|chuyển|cập\s+nhật)"
_CHANGE_FIELD = (
    r"(?P<field>điểm\s+đón|điểm\s+đi|nơi\s+đón|"
    r"điểm\s+đến|nơi\s+đến|đích\s+đến|loại\s+xe)"
)
_CHANGE_PATTERNS = (
    re.compile(
        rf"\b{_CHANGE_CUE}\s+(?:(?:cho|giúp)\s+(?:tôi|mình)\s+)?"
        rf"{_CHANGE_FIELD}(?=\s|[:,]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b{_CHANGE_FIELD}\s+{_CHANGE_CUE}(?=\s|[:,]|$)",
        re.IGNORECASE,
    ),
)
_CHANGE_LINKS = ("là", "thành", "sang", "qua")


def _normalize_change_field(value: str) -> str:
    """Canonicalize a captured field across Unicode case and whitespace variants."""

    normalized = unicodedata.normalize("NFC", value).casefold()
    return " ".join(normalized.split())


def _clean_booking_change_transcript(value: str) -> str:
    """Remove bounded interruption noise without changing meaningful words."""

    compact = " ".join(unicodedata.normalize("NFC", value).split())[:1_000]
    compact = _BARGE_IN_PREFIX_PATTERN.sub("", compact, count=1)
    compact = _ASR_CUTOFF_FRAGMENT_PATTERN.sub(" ", compact)
    compact = _SPOKEN_FILLER_PATTERN.sub(" ", compact)
    return " ".join(compact.split())


_TRAILING_CONNECTOR_TOKEN_SEQUENCES = (
    ("và", "sau", "đó"),
    ("sau", "đó"),
    ("và", "rồi"),
    ("rồi",),
    ("và",),
)
_TRAILING_ACTION_TOKEN_PREFIXES = (
    ("gọi", "cho", "tôi"),
    ("gọi", "giúp", "tôi"),
    ("gọi", "lại", "cho", "tôi"),
    ("nhắn", "cho", "tôi"),
    ("nhắn", "giúp", "tôi"),
    ("nhắn", "biển", "số"),
    ("báo", "cho", "tôi"),
    ("báo", "lại", "cho", "tôi"),
    ("liên", "hệ", "với", "tôi"),
    ("đặt", "xe"),
    ("đặt", "chuyến"),
    ("xác", "nhận", "chuyến"),
    ("xác", "nhận", "giúp", "tôi"),
    ("tính", "giá"),
    ("ước", "tính", "giá"),
    ("cho", "tôi", "biết"),
    ("giúp", "tôi"),
    ("giúp", "mình"),
    ("nói", "lại"),
    ("đọc", "lại"),
)
_TRAILING_POLITE_SUFFIX_TOKEN_SEQUENCES = (
    ("được", "không"),
    ("giúp", "tôi"),
    ("giúp", "mình"),
    ("nhé",),
    ("nha",),
    ("ạ",),
)
_TRAILING_REMARK_TOKEN_PREFIXES = (
    ("nhưng",),
    ("tuy", "nhiên"),
    ("tiện", "thể"),
    ("ngoài", "ra"),
    ("tôi", "muốn"),
    ("tôi", "cần"),
    ("tôi", "đang"),
    ("mình", "muốn"),
    ("mình", "cần"),
    ("bạn", "hãy"),
    ("bạn", "gọi"),
    ("trời", "đang"),
    ("trời", "mưa"),
)
_MAX_CHANGE_ENTITY_CHARS = 200
_MAX_CHANGE_ENTITY_TOKENS = 24


def _tokens_start_with(
    tokens: tuple[str, ...],
    start: int,
    prefix: tuple[str, ...],
) -> bool:
    return tokens[start : start + len(prefix)] == prefix


def _tokens_start_with_any(
    tokens: tuple[str, ...],
    start: int,
    prefixes: tuple[tuple[str, ...], ...],
) -> bool:
    return any(_tokens_start_with(tokens, start, prefix) for prefix in prefixes)


def _consume_change_link(value: str) -> str:
    """Consume one standalone linker without treating an address prefix as a linker."""

    remainder = value.lstrip(" ,:")
    folded = unicodedata.normalize("NFC", remainder).casefold()
    for link in _CHANGE_LINKS:
        if folded == link:
            return ""
        if folded.startswith(f"{link} "):
            return remainder[len(link) :].lstrip(" ,:")
    return remainder


def _trim_trailing_non_entity_clause(value: str) -> str:
    """Extract one bounded entity span with a single token scan."""

    entity = " ".join(unicodedata.normalize("NFC", value).split()).strip(" ,.!?;:")
    sentence_end = next(
        (index for index, character in enumerate(entity) if character in ".!?;"),
        len(entity),
    )
    raw_tokens = entity[:sentence_end].rstrip(" ,").split()
    folded_tokens = tuple(token.casefold().strip(" ,:") for token in raw_tokens)
    cut_at = len(raw_tokens)

    for index in range(len(folded_tokens)):
        if index > 0 and _tokens_start_with_any(
            folded_tokens,
            index,
            _TRAILING_REMARK_TOKEN_PREFIXES,
        ):
            cut_at = index
            break
        if raw_tokens[index].endswith(",") and _tokens_start_with_any(
            folded_tokens,
            index + 1,
            _TRAILING_ACTION_TOKEN_PREFIXES,
        ):
            cut_at = index + 1
            break
        connector_length = next(
            (
                len(connector)
                for connector in _TRAILING_CONNECTOR_TOKEN_SEQUENCES
                if _tokens_start_with(folded_tokens, index, connector)
            ),
            None,
        )
        if connector_length is not None and _tokens_start_with_any(
            folded_tokens,
            index + connector_length,
            _TRAILING_ACTION_TOKEN_PREFIXES,
        ):
            cut_at = index
            break

    raw_tokens = raw_tokens[:cut_at]
    folded_tokens = folded_tokens[:cut_at]
    while folded_tokens:
        suffix_length = next(
            (
                len(suffix)
                for suffix in _TRAILING_POLITE_SUFFIX_TOKEN_SEQUENCES
                if len(folded_tokens) >= len(suffix) and folded_tokens[-len(suffix) :] == suffix
            ),
            None,
        )
        if suffix_length is None:
            break
        raw_tokens = raw_tokens[:-suffix_length]
        folded_tokens = folded_tokens[:-suffix_length]

    entity = " ".join(raw_tokens).strip(" ,")
    if len(entity) > _MAX_CHANGE_ENTITY_CHARS or len(raw_tokens) > _MAX_CHANGE_ENTITY_TOKENS:
        return ""
    return entity


_CHANGE_FIELD_TARGETS: dict[str, BookingField] = {
    "điểm đón": "pickup",
    "điểm đi": "pickup",
    "nơi đón": "pickup",
    "điểm đến": "destination",
    "nơi đến": "destination",
    "đích đến": "destination",
    "loại xe": "vehicle_type",
}


def extract_explicit_booking_change(value: str) -> tuple[BookingField, str] | None:
    """Extract one explicit slot replacement without correcting the ASR text."""

    compact = _clean_booking_change_transcript(value)
    for pattern in _CHANGE_PATTERNS:
        match = pattern.search(compact)
        if match is None:
            continue
        field = _CHANGE_FIELD_TARGETS.get(_normalize_change_field(match.group("field")))
        if field is None:
            continue
        replacement = _trim_trailing_non_entity_clause(_consume_change_link(compact[match.end() :]))
        if not replacement:
            return None

        # Validate place queries to prevent invalid single-word or filler words
        if field in ("pickup", "destination"):
            if not is_valid_place_query(replacement):
                return None

        return field, replacement
    return None


_CONTRAST_NEGATION_TOKENS = ("khong", "phai")
_CONTRAST_REPLACEMENT_TOKENS = ("ma", "la")
_CONTEXT_CHANGE_CUE_TOKEN_SEQUENCES = (
    ("doi",),
    ("sua",),
    ("chuyen",),
    ("thay",),
    ("cap", "nhat"),
)
_CONTEXT_CHANGE_LINK_TOKEN_SEQUENCES = (
    ("thanh",),
    ("sang",),
    ("qua",),
)


def _find_token_sequence(
    tokens: tuple[str, ...],
    sequences: tuple[tuple[str, ...], ...],
    *,
    start: int = 0,
) -> tuple[int, tuple[str, ...]] | None:
    return next(
        (
            (index, sequence)
            for index in range(start, len(tokens))
            for sequence in sequences
            if _tokens_start_with(tokens, index, sequence)
        ),
        None,
    )


def _current_booking_surface_field(
    draft: BookingDraft,
    value: str,
) -> BookingField | None:
    """Resolve one old value against current slots without guessing from candidates."""

    normalized = _normalize_confirmation(value)
    if not normalized:
        return None
    surfaces: dict[BookingField, tuple[str | None, ...]] = {
        "pickup": (
            draft.pickup_query,
            draft.pickup.display_name if draft.pickup is not None else None,
            draft.pickup.address if draft.pickup is not None else None,
        ),
        "destination": (
            draft.destination_query,
            draft.destination.display_name if draft.destination is not None else None,
            draft.destination.address if draft.destination is not None else None,
        ),
        "vehicle_type": (
            draft.vehicle_query,
            vehicle_spoken_label(draft.vehicle_type),
        ),
    }
    matches = {
        field
        for field, values in surfaces.items()
        if any(surface and _normalize_confirmation(surface) == normalized for surface in values)
    }
    return next(iter(matches)) if len(matches) == 1 else None


def extract_contextual_booking_change(
    draft: BookingDraft,
    value: str,
) -> tuple[BookingField, str, str] | None:
    """Ground contrastive or ``CUE OLD LINK NEW`` speech to one current slot."""

    compact = _clean_booking_change_transcript(value)
    raw_tokens = tuple(cleaned for token in compact.split() if (cleaned := token.strip(" ,.!?;:")))
    folded_tokens = tuple(_normalize_confirmation(token) for token in raw_tokens)
    previous_value = ""
    replacement = ""

    contrast_link = _find_token_sequence(
        folded_tokens,
        (_CONTRAST_REPLACEMENT_TOKENS,),
    )
    if contrast_link is not None:
        replacement_marker, replacement_sequence = contrast_link
        negation_markers = [
            index
            for index in range(replacement_marker)
            if _tokens_start_with(folded_tokens, index, _CONTRAST_NEGATION_TOKENS)
        ]
        if negation_markers:
            negation_marker = negation_markers[-1]
            previous_value = " ".join(
                raw_tokens[negation_marker + len(_CONTRAST_NEGATION_TOKENS) : replacement_marker]
            ).strip()
            replacement = _trim_trailing_non_entity_clause(
                " ".join(raw_tokens[replacement_marker + len(replacement_sequence) :])
            )

    if not previous_value or not replacement:
        change_link = _find_token_sequence(
            folded_tokens,
            _CONTEXT_CHANGE_LINK_TOKEN_SEQUENCES,
        )
        if change_link is None:
            return None
        linker_marker, linker_sequence = change_link
        cue_markers = [
            (index, sequence)
            for index in range(linker_marker)
            for sequence in _CONTEXT_CHANGE_CUE_TOKEN_SEQUENCES
            if _tokens_start_with(folded_tokens, index, sequence)
        ]
        if not cue_markers:
            return None
        cue_marker, cue_sequence = cue_markers[-1]
        previous_value = " ".join(raw_tokens[cue_marker + len(cue_sequence) : linker_marker]).strip()
        replacement = _trim_trailing_non_entity_clause(" ".join(raw_tokens[linker_marker + len(linker_sequence) :]))

    if not previous_value or not replacement:
        return None
    field = _current_booking_surface_field(draft, previous_value)
    if field in {"pickup", "destination"} and not is_valid_place_query(replacement):
        return None
    return (field, replacement, previous_value) if field is not None else None


def seed_complete_booking_turn(
    draft: BookingDraft,
    places: PlaceToolsService,
    value: str,
) -> bool:
    """Populate every explicit slot before the conversational LLM asks follow-ups."""

    changed = False
    vehicle_type = extract_vehicle_type(value)
    if vehicle_type is not None and draft.slot_status("vehicle_type") != "resolved":
        draft.set_vehicle_type(vehicle_type)
        changed = True

    route = extract_complete_route(value)
    if route is None:
        return changed
    for target, query in zip(("pickup", "destination"), route, strict=True):
        if draft.slot_status(target) == "resolved":
            continue
        candidates = places.search(query)
        draft.set_candidates(target, query, candidates)
        if can_auto_select_place(candidates):
            draft.select_place(target, candidates[0].place_id)
        changed = True
    return changed


_CANDIDATE_NUMBER_TOKENS: dict[str, int] = {
    "1": 0,
    "mot": 0,
    "nhat": 0,
    "2": 1,
    "hai": 1,
    "3": 2,
    "ba": 2,
    "4": 3,
    "bon": 3,
    "tu": 3,
    "5": 4,
    "nam": 4,
}
_SHORT_CANDIDATE_SELECTION = re.compile(
    r"^(?:(?:toi|minh)\s+)?(?:(?:chon|lay)\s+)?(?:(?:phuong\s+an|lua\s+chon)\s+)?"
    r"(?:(?:so|thu)\s+)?(1|2|3|4|5|mot|hai|ba|bon|tu|nam|nhat)$"
)
_LEADING_CANDIDATE_SELECTION = re.compile(
    r"^(?:(?:toi|minh)\s+)?(?:(?:chon|lay)\s+)?(?:(?:phuong\s+an|lua\s+chon)\s+)?"
    r"(?:(?:so|thu)\s+)?(?P<ordinal>1|2|3|4|5|mot|hai|ba|bon|tu|nam|nhat)\b"
)

_ORDINAL_MENTION_PATTERN = re.compile(r"\b(?:(?:so|thu)\s+)?(?P<ordinal>1|2|3|4|5|mot|hai|ba|bon|tu|nam|nhat)\b")
_RESELECTION_CUE_PATTERN = re.compile(r"\b(?:nham|chon lai|doi lai)\b")
_RESELECTION_CONFIRMATIONS = frozenset({"dung", "dung roi", "vang", "chinh xac", "xac nhan"})
OrdinalReselectionAction = Literal["select", "confirm", "reopen"]
_ORDINAL_RESELECTION_WINDOW_SECONDS = 20.0


def _candidate_for_ordinal(
    draft: BookingDraft,
    target: BookingTarget,
    ordinal: str,
) -> PlaceCandidate | None:
    index = _CANDIDATE_NUMBER_TOKENS.get(ordinal)
    candidates = draft.pickup_candidates if target == "pickup" else draft.destination_candidates
    return candidates[index] if index is not None and index < len(candidates) else None


def grounded_candidate_reselection(
    draft: BookingDraft,
    user_text: str,
) -> tuple[OrdinalReselectionAction, BookingTarget, PlaceCandidate | None] | None:
    """Resolve immediate ordinal corrections without letting the LLM guess the slot."""

    normalized = _normalize_confirmation(user_text)
    mentions = list(_ORDINAL_MENTION_PATTERN.finditer(normalized))
    cues = list(_RESELECTION_CUE_PATTERN.finditer(normalized))
    next_field = draft.next_required_field()
    active_target: BookingTarget | None = None
    if next_field == "pickup" and draft.pickup_candidates:
        active_target = "pickup"
    elif next_field == "destination" and draft.destination_candidates:
        active_target = "destination"
    selection_age = (
        time.time() - draft.last_selected_candidate_at if draft.last_selected_candidate_at is not None else None
    )
    last_selection_is_recent = selection_age is not None and 0 <= selection_age <= _ORDINAL_RESELECTION_WINDOW_SECONDS
    recent_target = draft.last_selected_candidate_target if last_selection_is_recent else None
    if cues:
        mentions_before_cue = any(mention.end() <= cues[0].start() for mention in mentions)
        preferred_target = active_target if mentions_before_cue else recent_target
        target = draft.pending_reselection_target or preferred_target or active_target or recent_target
    else:
        target = draft.pending_reselection_target or active_target or recent_target
    if target is None:
        return None

    if cues:
        last_cue_end = cues[-1].end()
        corrected_mentions = [mention for mention in mentions if mention.start() >= last_cue_end]
        if not corrected_mentions:
            return "reopen", target, None
        candidate = _candidate_for_ordinal(
            draft,
            target,
            corrected_mentions[-1].group("ordinal"),
        )
        return ("select", target, candidate) if candidate is not None else None

    if not mentions:
        return None
    last_ordinal = mentions[-1].group("ordinal")
    candidate = _candidate_for_ordinal(draft, target, last_ordinal)
    if candidate is None:
        return None
    repeated_last = sum(mention.group("ordinal") == last_ordinal for mention in mentions) >= 2
    pending_same_candidate = (
        draft.pending_reselection_target == target and draft.pending_reselection_place_id == candidate.place_id
    )
    if repeated_last or pending_same_candidate:
        return "select", target, candidate
    if active_target is None or len(mentions) > 1:
        return "confirm", target, candidate
    return None


def is_candidate_reselection_confirmation(draft: BookingDraft, user_text: str) -> bool:
    """Confirm only a staged candidate change, never the booking itself."""

    return (
        draft.pending_reselection_target is not None
        and draft.pending_reselection_place_id is not None
        and _normalize_confirmation(user_text) in _RESELECTION_CONFIRMATIONS
    )


def grounded_ordinal_selection(
    draft: BookingDraft,
    user_text: str,
) -> tuple[BookingTarget, PlaceCandidate] | None:
    """Resolve a short ordinal only against the active server-owned candidate list."""

    normalized = _normalize_confirmation(user_text)
    match = _SHORT_CANDIDATE_SELECTION.fullmatch(normalized)
    # Recompute from slot state so persisted/stale pointers can never make a
    # destination ordinal skip an unresolved pickup.
    next_field = draft.next_required_field()
    target: BookingTarget | None = next_field if next_field in {"pickup", "destination"} else None
    if match is None or target is None:
        return None
    candidates = draft.pickup_candidates if target == "pickup" else draft.destination_candidates
    index = _CANDIDATE_NUMBER_TOKENS[match.group(1)]
    if index >= len(candidates):
        return None
    return target, candidates[index]


def grounded_ordinal_selection_in_labeled_turn(
    draft: BookingDraft,
    user_text: str,
    labelled_places: dict[BookingTarget, str],
) -> tuple[BookingTarget, PlaceCandidate] | None:
    """Resolve a leading ordinal before applying other explicitly labelled slots.

    This supports one self-correcting turn such as ``chọn số 1 là điểm đón,
    nhưng điểm đến phải là Hồ Gươm`` without allowing arbitrary long speech to
    take ownership of the active candidate list.
    """

    if not labelled_places:
        return None
    match = _LEADING_CANDIDATE_SELECTION.match(_normalize_confirmation(user_text))
    next_field = draft.next_required_field()
    target: BookingTarget | None = next_field if next_field in {"pickup", "destination"} else None
    if match is None or target is None:
        return None
    candidate = _candidate_for_ordinal(draft, target, match.group("ordinal"))
    return (target, candidate) if candidate is not None else None


def _candidate_surfaces(draft: BookingDraft, target: BookingTarget, candidate: PlaceCandidate) -> set[str]:
    query = draft.pickup_query if target == "pickup" else draft.destination_query
    normalized_query = _normalize_confirmation(query or "")
    normalized_name = _normalize_confirmation(candidate.display_name)
    surfaces = {normalized_name, _normalize_confirmation(candidate.address)}
    if normalized_query and normalized_name.endswith(normalized_query):
        short_name = normalized_name[: -len(normalized_query)].strip()
        if short_name:
            surfaces.add(short_name)
    return {surface for surface in surfaces if len(surface) >= 3}


def _surface_is_negated(normalized_text: str, surface: str) -> bool:
    return bool(re.search(rf"\bkhong\s+(?:phai\s+)?(?:la\s+)?{re.escape(surface)}\b", normalized_text))


def grounded_named_place_selection(
    draft: BookingDraft,
    user_text: str,
) -> tuple[BookingTarget, PlaceCandidate] | None:
    """Match exactly one saved candidate name while respecting explicit negation."""

    normalized = _normalize_confirmation(user_text)
    matches: dict[tuple[BookingTarget, str], PlaceCandidate] = {}
    for target, candidates in (
        ("pickup", draft.pickup_candidates),
        ("destination", draft.destination_candidates),
    ):
        current = draft.pickup if target == "pickup" else draft.destination
        for candidate in candidates:
            surfaces = _candidate_surfaces(draft, target, candidate)
            if not any(surface in normalized and not _surface_is_negated(normalized, surface) for surface in surfaces):
                continue
            if current is not None and current.place_id == candidate.place_id and "chon" not in normalized:
                continue
            matches[(target, candidate.place_id)] = candidate
    if len(matches) != 1:
        return None
    (target, _), candidate = next(iter(matches.items()))
    return target, candidate


_VEHICLE_SURFACES: dict[VehicleType, tuple[str, ...]] = {
    "MOTORBIKE": ("xe may",),
    "CAR_4": ("xe 4 cho", "xe bon cho", "o to 4 cho", "o to bon cho"),
    "CAR_7": ("xe 7 cho", "xe bay cho", "o to 7 cho", "o to bay cho"),
    "LUXURY": ("xe cao cap", "xe sang"),
}


def grounded_vehicle_selection(draft: BookingDraft, user_text: str) -> VehicleType | None:
    """Resolve one explicit supported vehicle, including numbered vehicle choices."""

    normalized = _normalize_confirmation(user_text)
    ordinal = _SHORT_CANDIDATE_SELECTION.fullmatch(normalized)
    if ordinal is not None and draft.next_required_field() == "vehicle_type":
        index = _CANDIDATE_NUMBER_TOKENS.get(ordinal.group(1))
        if index is None or not 0 <= index < len(VEHICLE_TYPE_ORDER):
            return None
        return VEHICLE_TYPE_ORDER[index]

    matches = {
        vehicle_type
        for vehicle_type, surfaces in _VEHICLE_SURFACES.items()
        if any(surface in normalized and not _surface_is_negated(normalized, surface) for surface in surfaces)
    }
    if len(matches) != 1:
        return None
    selected = next(iter(matches))
    if draft.vehicle_type is not None and draft.vehicle_type == selected:
        return None
    return selected


def has_booking_change_intent(draft: BookingDraft, value: str) -> bool:
    """Detect a slot correction before the turn can be treated as confirmation."""

    return (
        extract_explicit_booking_change(value) is not None
        or extract_contextual_booking_change(draft, value) is not None
        or bool(extract_labeled_booking_places(value))
        or grounded_vehicle_selection(draft, value) is not None
    )


def _target_label(target: BookingTarget) -> str:
    return "điểm đón" if target == "pickup" else "điểm đến"


def _candidate_clarification_prompt(draft: BookingDraft, target: BookingTarget) -> str | None:
    candidates = draft.pickup_candidates if target == "pickup" else draft.destination_candidates
    selected = draft.pickup if target == "pickup" else draft.destination
    query = draft.pickup_query if target == "pickup" else draft.destination_query
    if selected is not None or not candidates or not query:
        return None
    return (
        f"Đã tìm thấy {len(candidates)} địa điểm liên quan đến {query} cho {_target_label(target)} "
        "trong dữ liệu. Vui lòng chọn theo số thứ tự được liệt kê bên dưới."
    )


def _next_required_prompt(draft: BookingDraft) -> str | None:
    # This is the single workflow router. Never prioritize the field that was
    # merely changed most recently over pickup -> destination -> vehicle.
    target = draft.next_required_field()
    if target in {"pickup", "destination"}:
        clarification = _candidate_clarification_prompt(draft, target)
        if clarification is not None:
            return clarification
        return f"Vui lòng cho biết {_target_label(target)}. Nếu muốn đổi, bạn có thể nói lại."
    if target == "vehicle_type":
        return "Vui lòng chọn loại xe theo số thứ tự được liệt kê bên dưới. Nếu muốn đổi, bạn có thể nói lại."
    return None


def _selection_followup(draft: BookingDraft, target: BookingTarget, selected: PlaceCandidate) -> str | None:
    prefix = f"Đã chọn {_target_label(target)} là {selected.display_name}."
    return _acknowledgement_followup(draft, prefix)


def _acknowledgement_followup(draft: BookingDraft, acknowledgement: str) -> str | None:
    prompt = _next_required_prompt(draft)
    return f"{acknowledgement} {prompt}" if prompt is not None else None


def _vehicle_followup(draft: BookingDraft, vehicle_type: VehicleType) -> str | None:
    prefix = f"Đã chọn loại xe là {vehicle_spoken_label(vehicle_type)}."
    return _acknowledgement_followup(draft, prefix)


def _booking_confirmation_prompt(draft: BookingDraft) -> str:
    return (
        f"Đã ghi nhận chuyến xe của bạn đi từ {draft.pickup.display_name}, "
        f"đến {draft.destination.display_name}, {vehicle_spoken_label(draft.vehicle_type)}. "
        f'Hãy kiểm tra lại thông tin và xác nhận đặt xe bằng câu "{_REQUIRED_BOOKING_CONFIRMATION_PHRASE}", '
        "nếu cần sửa đổi thông tin gì thì hãy báo tôi nhé!"
    )


class BookingTask(AgentTask[BookingOutcome]):
    """Collect and validate one booking while preserving the single AloSM persona."""

    def __init__(
        self,
        *,
        chat_ctx: llm.ChatContext | None = None,
        places: PlaceToolsService | None = None,
        quotes: QuoteToolsService | None = None,
        bookings: BookingToolsService | None = None,
        state_store: VoiceStateStore | None = None,
        handoff_handler: HandoffHandler | None = None,
        session_data: AloSMSessionData | None = None,
        transcript_rewriter: TranscriptRewriter | None = None,
    ) -> None:
        self._places = places or PlaceToolsService()
        self._quotes = quotes or QuoteToolsService()
        self._bookings = bookings or BookingToolsService()
        self._state_store = state_store or EphemeralVoiceStateStore()
        self._handoff_handler = handoff_handler
        self._session_data = session_data
        self._transcript_rewriter = transcript_rewriter
        self._booking_change_generations: dict[BookingField, int] = {
            "pickup": 0,
            "destination": 0,
            "vehicle_type": 0,
        }
        self._booking_change_generation_lock = asyncio.Lock()
        # One explicit barge-in change is a transaction: lookup, draft mutation,
        # persistence, state publication, and acknowledgement must observe the
        # same session state. Generation tokens can still stale an older request
        # while it is awaiting provider I/O.
        self._booking_change_transaction_lock = asyncio.Lock()
        super().__init__(
            chat_ctx=chat_ctx,
            instructions=(
                "Bạn vẫn là tổng đài viên AloSM, đang thực hiện đúng một yêu cầu đặt xe. "
                "Nói tiếng Việt tự nhiên, ngắn gọn và mỗi lượt chỉ hỏi một thông tin. "
                "Đây là nội dung đọc thành tiếng: gọi khách là bạn hoặc quý khách; không dùng dấu "
                "gạch chéo, chữ viết tắt, mã enum hoặc ký hiệu tiền tệ trong câu trả lời. "
                "Đọc MOTORBIKE là xe máy, CAR_4 là xe ô tô bốn chỗ, CAR_7 là xe ô tô bảy chỗ, "
                "LUXURY là xe cao cấp và VND là đồng. "
                "Phải dùng search_place cho lời người dùng nói về địa điểm; không tự tạo place_id. "
                "Chỉ dùng select_place với candidate_id có trong kết quả tìm kiếm hiện hành. "
                "Nếu search_place báo đã tự chọn một kết quả khớp duy nhất thì không hỏi xác nhận "
                "địa điểm đó lần nữa. Với kết quả mơ hồ, phải hỏi khách chọn candidate. "
                "Khi có nhiều candidate, chỉ nói số lượng kết quả và yêu cầu khách chọn số hiển thị bên dưới; "
                "tuyệt đối không đọc tên hoặc địa chỉ trong danh sách vì giao diện đã hiển thị chúng. "
                "Một lựa chọn theo số hợp lệ cập nhật slot ngay và không cần xác nhận candidate lần hai. "
                "Mỗi slot có một trạng thái: missing là chưa có và hiển thị đỏ; needs_clarification "
                "là đã có thông tin nhưng chưa rõ và hiển thị vàng; resolved là đã xác minh và hiển thị xanh. "
                "Nếu khách cung cấp nhiều slot trong cùng một lượt, phải xử lý tất cả slot đã cung cấp "
                "bằng các tool tương ứng trước khi hỏi lại, kể cả khi một địa điểm đang mơ hồ. "
                "Nếu khách có nói loại xe nhưng chưa thể ánh xạ chắc chắn sang một loại hỗ trợ, gọi "
                "mark_vehicle_needs_clarification trước khi hỏi. Chỉ hỏi slot next_required_field và "
                "không hỏi lại slot đã resolved. "
                "Sau mọi thay đổi điểm đón, điểm đến hoặc loại xe, câu trả lời bắt buộc phải bắt đầu bằng "
                "'Đã chọn điểm đón là...', 'Đã chọn điểm đến là...' hoặc 'Đã chọn loại xe là...'; "
                "chỉ sau câu đó mới hỏi trường tiếp theo, trừ khi cả ba slot đã đủ và cần đọc prompt xác nhận. "
                "Nếu chưa có loại xe, phải hỏi khách chọn loại xe "
                "theo số thứ tự được liệt kê bên dưới để giao diện hiện danh sách xe. "
                "Thu thập đủ điểm đón, điểm đến và loại xe rồi gọi estimate_fare. "
                "estimate_fare đồng thời khóa báo giá ở trạng thái chờ xác nhận; đọc nguyên văn prompt "
                "mà tool trả về và không tự bỏ qua bước này. Chỉ gọi confirm_booking khi câu xác nhận có ít nhất "
                "bốn từ và thể hiện rõ ý định đặt xe. Luôn xử lý yêu cầu đổi slot trước confirmation; không dùng "
                "một câu vừa xác nhận vừa thêm yêu cầu cho tài xế để xác nhận booking. "
                "Chỉ gọi create_booking sau khi confirm_booking thành công. "
                "Nếu khách sửa điểm đón, điểm đến hoặc loại xe, gọi tool tương ứng; hệ thống sẽ "
                "tự xoá giá và xác nhận cũ. Không được tự bịa giá, ETA hoặc mã chuyến. "
                "Nếu tool báo ASR_LOW_CONFIDENCE thì yêu cầu khách nói lại hoặc nhập tay. "
                "Nếu khách muốn nói chuyện với người thật hoặc cần được chuyển tới tổng đài viên, "
                "hãy gọi request_handoff với lý do do khách cung cấp; không trả lời như thể đã chuyển "
                "nếu tool chưa trả về trạng thái pending, accepted hoặc connected. "
                "Nếu khách nói rõ không muốn đặt xe nữa, hãy kết thúc task với trạng thái abandoned."
            ),
        )

    async def on_enter(self) -> None:
        draft = self.session.userdata.booking_draft
        prompt = _next_required_prompt(draft)
        if prompt is not None:
            # Candidate lists were already seeded by the parent agent. Speaking
            # this bounded prompt prevents the LLM from replacing the actual
            # query label (for example VinUni) with the phrase "chưa rõ".
            self.session.say(prompt, allow_interruptions=True)
            return
        current_state = draft.conversation_summary()
        self.session.generate_reply(
            instructions=(
                f"Trạng thái booking hiện tại: {current_state}. "
                "Dựa trên yêu cầu đặt xe gần nhất của khách và trạng thái này, hãy gọi tool cần thiết ngay. "
                "Nếu yêu cầu chưa có đủ thông tin thì hỏi đúng một thông tin còn thiếu."
            )
        )

    @staticmethod
    def _draft(context: RunContext[AloSMSessionData]):
        return context.userdata.booking_draft

    def _latest_user_message(self) -> llm.ChatMessage | None:
        for item in reversed(self.chat_ctx.items):
            if getattr(item, "role", None) == "user":
                return item if isinstance(item, llm.ChatMessage) else None
        return None

    async def _respond_after_grounded_change(
        self,
        userdata: AloSMSessionData,
        *,
        acknowledgement: str,
        followup: str | None,
        change_token: BookingChangeToken | None = None,
    ) -> None:
        """Persist one deterministic slot change and speak acknowledgement first."""

        self._raise_if_stale_booking_change(change_token)
        draft = userdata.booking_draft
        response = followup
        if (
            response is None
            and draft.pickup is not None
            and draft.destination is not None
            and draft.vehicle_type is not None
        ):
            try:
                quote = await self._quotes.estimate(
                    user_id=userdata.user_id,
                    app_session_id=userdata.app_session_id,
                    draft=draft,
                )
                self._raise_if_stale_booking_change(change_token)
                draft.set_quote(quote)
                draft.request_confirmation()
                response = _booking_confirmation_prompt(draft)
                userdata.clear_failure()
            except ValueError:
                self._raise_if_stale_booking_change(change_token)
                userdata.record_failure(
                    "QUOTE_UNAVAILABLE",
                    "Chưa thể tính báo giá từ thông tin mới.",
                    fallback_action="retry",
                )
                response = f"{acknowledgement} Hiện chưa thể tính báo giá, bạn vui lòng thử lại."
        self._raise_if_stale_booking_change(change_token)
        try:
            await self._state_store.save(userdata)
        except VoiceStateConflictError:
            self._raise_if_stale_booking_change(change_token)
        userdata.record_failure(
                "STATE_CONFLICT",
                "Phiên này vừa được cập nhật ở kết nối khác.",
            retryable=False,
            fallback_action="handoff",
        )
        await publish_booking_state(self.session)
            raise StopResponse() from None
        self._raise_if_stale_booking_change(change_token)
        await publish_booking_state(self.session)
        self._raise_if_stale_booking_change(change_token)
        self.session.say(response or acknowledgement, allow_interruptions=True)
        raise StopResponse()

    async def _next_booking_change_token(self, field: BookingField) -> BookingChangeToken:
        """Issue one ordered token while allowing newer work to stale pending I/O."""

        async with self._booking_change_generation_lock:
            generation = self._booking_change_generations[field] + 1
            self._booking_change_generations[field] = generation
            return field, generation

    def _raise_if_stale_booking_change(self, token: BookingChangeToken | None) -> None:
        if token is None:
            return
        field, generation = token
        current = self._booking_change_generations[field]
        if generation != current:
            logger.info(
                "Ignoring stale booking change field=%s generation=%d current=%d",
                field,
                generation,
                current,
            )
            raise StopResponse()

    async def _force_barge_in_interrupt(self) -> None:
        """Cancel speech that may resume after a false-interruption window."""

        try:
            await self.session.interrupt(force=True)
        except RuntimeError:
            # Speech may already be fully interrupted by LiveKit VAD.
            return

    async def _handle_explicit_booking_change(
        self,
        userdata: AloSMSessionData,
        user_text: str,
    ) -> None:
        explicit_change = extract_explicit_booking_change(user_text)
        previous_value: str | None = None
        if explicit_change is not None:
            field, replacement = explicit_change
        else:
            draft_snapshot = userdata.booking_draft.model_copy(deep=True)
            contextual_change = extract_contextual_booking_change(draft_snapshot, user_text)
            if contextual_change is None:
                return
            field, replacement, previous_value = contextual_change
        if field in {"pickup", "destination"} and not is_valid_place_query(replacement):
            logger.info(
                "Ignoring invalid booking place change session=%s field=%s replacement=%r",
                userdata.app_session_id,
                field,
                replacement,
            )
            return
        change_token = await self._next_booking_change_token(field)
        await self._force_barge_in_interrupt()
        logger.info(
            "Booking barge-in change detected session=%s field=%s replacement=%r",
            userdata.app_session_id,
            field,
            replacement,
        )

        if field == "vehicle_type":
            async with self._booking_change_transaction_lock:
                self._raise_if_stale_booking_change(change_token)
                draft = userdata.booking_draft
                if previous_value is not None and _current_booking_surface_field(draft, previous_value) != field:
                raise StopResponse()
                vehicle_type = extract_vehicle_type(replacement)
                if vehicle_type is None:
                    draft.mark_vehicle_needs_clarification(replacement)
                    acknowledgement = f"Đã ghi nhận yêu cầu đổi loại xe thành {replacement}."
                    await self._respond_after_grounded_change(
                        userdata,
                        acknowledgement=acknowledgement,
                        followup=_acknowledgement_followup(draft, acknowledgement),
                        change_token=change_token,
                    )
                    return
                draft.set_vehicle_type(vehicle_type)
                acknowledgement = f"Đã đổi loại xe thành {vehicle_spoken_label(vehicle_type)}."
                await self._respond_after_grounded_change(
                    userdata,
                    acknowledgement=acknowledgement,
                    followup=_acknowledgement_followup(draft, acknowledgement),
                    change_token=change_token,
                )
            return

        target: BookingTarget = "pickup" if field == "pickup" else "destination"
        async with self._booking_change_transaction_lock:
            self._raise_if_stale_booking_change(change_token)
            if (
                previous_value is not None
                and _current_booking_surface_field(userdata.booking_draft, previous_value) != field
            ):
                raise StopResponse()
            candidates = tuple(await self._places.search_async(replacement))
            self._raise_if_stale_booking_change(change_token)
            draft = userdata.booking_draft
            draft.set_candidates(target, replacement, list(candidates))
            acknowledgement = f"Đã cập nhật {_target_label(target)} thành {replacement}."
            if not candidates:
                userdata.record_failure(
                    "PLACE_NOT_FOUND",
                    f"Không tìm thấy {_target_label(target)} phù hợp với {replacement}.",
                    fallback_action="repeat_or_text",
                )
                await self._respond_after_grounded_change(
                    userdata,
                    acknowledgement=acknowledgement,
                    followup=_acknowledgement_followup(
                        draft,
                        f"{acknowledgement} Chưa tìm thấy địa điểm phù hợp.",
                    ),
                    change_token=change_token,
                )
                return
            if can_auto_select_place(candidates):
                selected = draft.select_place(target, candidates[0].place_id)
                userdata.clear_failure()
                acknowledgement = f"Đã đổi {_target_label(target)} thành {selected.display_name}."
                await self._respond_after_grounded_change(
                    userdata,
                    acknowledgement=acknowledgement,
                    followup=_acknowledgement_followup(draft, acknowledgement),
                    change_token=change_token,
                )
                return

            userdata.clear_failure()
            await self._respond_after_grounded_change(
                userdata,
                acknowledgement=acknowledgement,
                followup=_acknowledgement_followup(draft, acknowledgement),
                change_token=change_token,
            )

    async def _handle_labeled_booking_places(
        self,
        userdata: AloSMSessionData,
        user_text: str,
    ) -> None:
        labelled = extract_labeled_booking_places(user_text)
        if not labelled:
            return

        await self._force_barge_in_interrupt()
        async with self._booking_change_transaction_lock:
            draft = userdata.booking_draft
            acknowledgements: list[str] = []
            missing: list[tuple[BookingTarget, str]] = []
            ordinal_selection = grounded_ordinal_selection_in_labeled_turn(
                draft,
                user_text,
                labelled,
            )
            if ordinal_selection is not None:
                ordinal_target, ordinal_candidate = ordinal_selection
                selected = draft.select_place(ordinal_target, ordinal_candidate.place_id)
                acknowledgements.append(
                    f"Đã chọn {_target_label(ordinal_target)} là {selected.display_name}."
                )
            for target in ("pickup", "destination"):
                query = labelled.get(target)
                if query is None:
                    continue
                candidates = tuple(await self._places.search_async(query))
                draft.set_candidates(target, query, list(candidates))
                if not candidates:
                    missing.append((target, query))
                    acknowledgements.append(f"Chưa tìm thấy {_target_label(target)} phù hợp với {query}.")
                    continue
                if can_auto_select_place(candidates):
                    selected = draft.select_place(target, candidates[0].place_id)
                    acknowledgements.append(f"Đã chọn {_target_label(target)} là {selected.display_name}.")
                else:
                    acknowledgements.append(f"Đã ghi nhận {_target_label(target)} là {query}.")

            if missing:
                target, query = missing[0]
                userdata.record_failure(
                    "PLACE_NOT_FOUND",
                    f"Không tìm thấy {_target_label(target)} phù hợp với {query}.",
                    fallback_action="repeat_or_text",
                )
            else:
                userdata.clear_failure()
            acknowledgement = " ".join(acknowledgements)
            await self._respond_after_grounded_change(
                userdata,
                acknowledgement=acknowledgement,
                followup=_acknowledgement_followup(draft, acknowledgement),
            )

    async def _handle_candidate_reselection(
        self,
        userdata: AloSMSessionData,
        user_text: str,
    ) -> None:
        draft = userdata.booking_draft
        if is_candidate_reselection_confirmation(draft, user_text):
            target, selected = draft.confirm_candidate_reselection()
            acknowledgement = f"Đã đổi {_target_label(target)} thành {selected.display_name}."
            await self._respond_after_grounded_change(
                userdata,
                acknowledgement=acknowledgement,
                followup=_acknowledgement_followup(draft, acknowledgement),
            )

        decision = grounded_candidate_reselection(draft, user_text)
        if decision is None:
            return
        action, target, candidate = decision
        if action == "reopen":
            draft.reopen_candidate_selection(target)
            acknowledgement = f"Đã ghi nhận bạn chọn nhầm {_target_label(target)}."
            await self._respond_after_grounded_change(
                userdata,
                acknowledgement=acknowledgement,
                followup=_acknowledgement_followup(draft, acknowledgement),
            )

        if candidate is None:
            return
        if action == "confirm":
            current = draft.pickup if target == "pickup" else draft.destination
            draft.stage_candidate_reselection(target, candidate.place_id)
            current_name = f" từ {current.display_name}" if current is not None else ""
            acknowledgement = (
                f"Bạn muốn đổi {_target_label(target)}{current_name} thành {candidate.display_name} đúng không? "
                "Vui lòng nói đúng hoặc lặp lại số đó để xác nhận."
            )
            await self._respond_after_grounded_change(
                userdata,
                acknowledgement=acknowledgement,
                followup=acknowledgement,
            )

        selected = draft.select_place(target, candidate.place_id)
        acknowledgement = f"Đã đổi {_target_label(target)} thành {selected.display_name}."
        await self._respond_after_grounded_change(
            userdata,
            acknowledgement=acknowledgement,
            followup=_acknowledgement_followup(draft, acknowledgement),
        )

    async def on_user_turn_completed(self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage) -> None:
        userdata = self._session_data or self.session.userdata
        await rewrite_livekit_user_turn(
            rewriter=self._transcript_rewriter,
            userdata=userdata,
            turn_ctx=turn_ctx,
            new_message=new_message,
        )
        user_text = new_message.text_content or ""
        await self._handle_candidate_reselection(userdata, user_text)

        # An explicit correction during barge-in always outranks the candidate
        # list that happened to be active when the agent started speaking.
        await self._handle_explicit_booking_change(
            userdata,
            user_text,
        )
        await self._handle_labeled_booking_places(userdata, user_text)

        grounded = grounded_ordinal_selection(
            userdata.booking_draft,
            user_text,
        ) or grounded_named_place_selection(
            userdata.booking_draft,
            user_text,
        )
        if grounded is not None:
            target, candidate = grounded
            selected = userdata.booking_draft.select_place(target, candidate.place_id)
            logger.info(
                "Booking candidate selected deterministically session=%s target=%s user_text=%r place_id=%s",
                userdata.app_session_id,
                target,
                new_message.text_content,
                selected.place_id,
            )
            followup = _selection_followup(userdata.booking_draft, target, selected)
            await self._respond_after_grounded_change(
                userdata,
                acknowledgement=f"Đã chọn {_target_label(target)} là {selected.display_name}.",
                followup=followup,
            )

        vehicle_type = grounded_vehicle_selection(userdata.booking_draft, user_text)
        if vehicle_type is not None:
            userdata.booking_draft.set_vehicle_type(vehicle_type)
            logger.info(
                "Booking vehicle selected deterministically session=%s user_text=%r vehicle_type=%s",
                userdata.app_session_id,
                new_message.text_content,
                vehicle_type,
            )
            await self._respond_after_grounded_change(
                userdata,
                acknowledgement=f"Đã chọn loại xe là {vehicle_spoken_label(vehicle_type)}.",
                followup=_vehicle_followup(userdata.booking_draft, vehicle_type),
            )

        # Handoff and abandonment are task completions, not booking tools. The
        # supervisor owns call-level handoff and the result remains typed.
        current = self.session.userdata.handoff
        if current is not None and current.status in {"pending", "accepted", "connected"}:
            raise StopResponse()
        if is_booking_abandonment_request(new_message.text_content or ""):
            outcome = BookingOutcome(
                status="abandoned",
                message="Đã dừng yêu cầu đặt xe.",
                reason=new_message.text_content or "Khách không muốn tiếp tục đặt xe.",
            )
            if not self.done():
                self.complete(outcome)
            raise StopResponse()

    @function_tool()
    async def request_handoff(self, context: RunContext[AloSMSessionData], reason: str) -> str:
        """Chuyển yêu cầu gặp người thật lên bộ điều phối của cuộc gọi.

        Args:
            reason: Lý do ngắn gọn do khách cung cấp để tổng đài viên hiểu yêu cầu.
        """
        context.disallow_interruptions()
        if self._handoff_handler is None:
            return json.dumps(
                {"status": "failed", "message": "Chưa cấu hình xử lý chuyển tổng đài viên."},
                ensure_ascii=False,
            )
        result = await self._handoff_handler(reason)
        try:
            status = str(json.loads(result).get("status") or "")
        except json.JSONDecodeError:
            status = ""
        if status in {"pending", "accepted", "connected"}:
            outcome = BookingOutcome(
                status="needs_handoff",
                message="Đã tạo yêu cầu chuyển tổng đài viên.",
                reason=reason,
            )
            if not self.done():
                self.complete(outcome)
            raise StopResponse()
        return result

    async def _interrupt_stale_speech(self, context: RunContext[AloSMSessionData]) -> None:
        """Cancel pre-tool speech so stale quote/location text is never played."""

        try:
            await context.session.interrupt()
        except RuntimeError:
            # A tool can run after speech has already completed or during startup.
            return

    async def _refresh_quote_after_change(self, context: RunContext[AloSMSessionData]) -> QuoteSnapshot | None:
        """Re-issue a quote after a correction when all booking fields remain present."""

        draft = self._draft(context)
        if draft.pickup is None or draft.destination is None or draft.vehicle_type is None:
            return None
        async with context.with_filler(
            "Đang tính lại báo giá, bạn chờ một chút nhé.",
            delay=0.8,
        ):
            try:
                quote = await self._quotes.estimate(
                    user_id=context.userdata.user_id,
                    app_session_id=context.userdata.app_session_id,
                    draft=draft,
                )
                draft.set_quote(quote)
                draft.request_confirmation()
            except ValueError:
                context.userdata.record_failure(
                    "QUOTE_UNAVAILABLE",
                    "Chưa thể tính lại báo giá từ thông tin mới.",
                    fallback_action="retry",
                )
                await self._commit(context)
                return None
            context.userdata.clear_failure()
            await self._commit(context)
            return quote

    async def _commit(self, context: RunContext[AloSMSessionData]) -> None:
        commit_started = time.perf_counter()
        state_started = time.perf_counter()
        try:
            await self._state_store.save(context.userdata)
        except VoiceStateConflictError as exc:
            logger.info(
                "[PERF-VOICE] stage=task.commit.state_store call_id=%s duration_ms=%.3f result=conflict",
                context.userdata.call_id,
                (time.perf_counter() - state_started) * 1000,
            )
            context.userdata.record_failure(
                "STATE_CONFLICT",
                "Phiên này vừa được cập nhật ở kết nối khác.",
                retryable=False,
                fallback_action="handoff",
            )
            await publish_booking_state(context.session)
            raise ToolError("STATE_CONFLICT") from exc
        logger.info(
            "[PERF-VOICE] stage=task.commit.state_store call_id=%s duration_ms=%.3f result=ok",
            context.userdata.call_id,
            (time.perf_counter() - state_started) * 1000,
        )
        await publish_booking_state(context.session)
        logger.info(
            "[PERF-VOICE] stage=task.commit.total call_id=%s duration_ms=%.3f result=ok",
            context.userdata.call_id,
            (time.perf_counter() - commit_started) * 1000,
        )

    @function_tool()
    async def search_place(
        self,
        context: RunContext[AloSMSessionData],
        target: BookingTarget,
        query: str,
    ) -> str:
        """Tìm địa điểm trong gazetteer demo từ lời nói của khách.

        Gọi sau khi khách cung cấp hoặc sửa điểm đón hay điểm đến. Tool lưu
        candidates vào booking draft. Nếu có một exact match hoặc alias duy
        nhất đáng tin cậy, tool có thể tự chọn; nếu booking đã đủ thông tin,
        tool đồng thời tính lại báo giá và trả về báo giá mới.

        Nếu có nhiều candidate, không tự chọn hoặc suy đoán: giao diện sẽ liệt
        kê các lựa chọn theo chiều dọc; chỉ nói số lượng kết quả và yêu cầu khách
        chọn theo số thứ tự, không đọc toàn bộ danh sách. Sau khi khách chọn, gọi
        select_place bằng place_id. Nếu không tìm
        thấy hoặc transcript có độ tin cậy thấp, yêu cầu khách nói lại hoặc
        nhập địa điểm.

        Không dùng để tính giá cho lộ trình thiếu dữ liệu, chọn loại xe, hoặc
        dùng place_id không có trong kết quả tìm kiếm hiện tại.

        Args:
            target: Trường cần cập nhật; chỉ dùng pickup cho điểm đón hoặc
                destination cho điểm đến.
            query: Các từ về địa điểm khách thực sự vừa nói; không tự thêm
                thông tin khách chưa cung cấp.

        Returns:
            JSON chứa candidates hoặc auto_selected. Có thể kèm quote_refreshed
            và hướng dẫn đọc báo giá mới; tìm thấy địa điểm không có nghĩa là
            đã tạo chuyến.
        """
        context.disallow_interruptions()

        # Validate query to prevent filler words and invalid single-word queries
        if not is_valid_place_query(query):
            context.userdata.record_failure(
                "PLACE_NOT_FOUND",
                f"Địa điểm '{query}' không hợp lệ.",
                fallback_action="repeat_or_text",
            )
            await self._commit(context)
            return f"Thông tin về {_target_label(target)} '{query}' không hợp lệ. Vui lòng nói rõ hơn hoặc nhập tay."

        latest = self._latest_user_message()
        confidence = latest.transcript_confidence if latest is not None else None
        context.userdata.last_asr_confidence = confidence
        candidates = self._places.search(query)
        if requires_location_clarification(
            latest,
            context.userdata.critical_confidence_threshold,
            candidates,
        ):
            context.userdata.record_failure(
                "ASR_LOW_CONFIDENCE",
                "Tổng đài chưa nghe rõ địa điểm quan trọng.",
                fallback_action="repeat_or_text",
            )
            await self._commit(context)
            return "ASR_LOW_CONFIDENCE: Hãy yêu cầu khách nói lại địa điểm hoặc nhập tay."

        draft = self._draft(context)
        had_quote = draft.quote is not None
        if had_quote:
            await self._interrupt_stale_speech(context)
        draft.set_candidates(target, query, candidates)
        if not candidates:
            context.userdata.record_failure(
                "PLACE_NOT_FOUND",
                "Không tìm thấy địa điểm phù hợp.",
                fallback_action="repeat_or_text",
            )
            await self._commit(context)
            prompt = _next_required_prompt(draft)
            return "Không tìm thấy địa điểm trong dữ liệu demo. " + (
                prompt or "Hãy hỏi khách tên địa điểm khác hoặc rõ hơn."
            )
        if can_auto_select_place(candidates):
            selected = draft.select_place(target, candidates[0].place_id)
            refreshed_quote = (
                await self._refresh_quote_after_change(context)
                if draft.pickup is not None and draft.destination is not None and draft.vehicle_type is not None
                else None
            )
            if (
                draft.pickup is not None
                and draft.destination is not None
                and draft.vehicle_type is not None
                and refreshed_quote is None
            ):
                return "Đã cập nhật địa điểm nhưng chưa thể tính lại giá; hãy gọi estimate_fare trước khi xác nhận."
            context.userdata.clear_failure()
            if refreshed_quote is None:
            await self._commit(context)
            acknowledgement = f"Đã chọn {_target_label(target)} là {selected.display_name}."
            spoken_prompt = (
                _booking_confirmation_prompt(draft)
                if refreshed_quote is not None
                else _selection_followup(draft, target, selected) or acknowledgement
            )
            return json.dumps(
                {
                    "target": target,
                    "auto_selected": True,
                    "place_id": selected.place_id,
                    "display_name": selected.display_name,
                    "quote_refreshed": refreshed_quote is not None,
                    "spoken_prompt": spoken_prompt,
                    "instruction": (
                        "Đọc nguyên văn spoken_prompt, bắt đầu bằng xác nhận slot vừa chọn; "
                        "không bỏ qua xác nhận và không hỏi xác nhận candidate lần hai."
                    ),
                },
                ensure_ascii=False,
            )
        context.userdata.clear_failure()
        await self._commit(context)
        return json.dumps(
            {
                "target": target,
                "candidates": [candidate.model_dump() for candidate in candidates],
                "spoken_prompt": _next_required_prompt(draft),
                "instruction": (
                    "Đọc nguyên văn spoken_prompt; không đọc tên hay địa chỉ candidates. "
                    "Danh sách đã được gửi riêng tới giao diện."
                ),
            },
            ensure_ascii=False,
        )

    @function_tool()
    async def select_place(
        self,
        context: RunContext[AloSMSessionData],
        target: BookingTarget,
        place_id: str,
    ) -> str:
        """Chọn và ghi nhận một candidate từ kết quả tìm kiếm hiện tại.

        Chỉ gọi sau khi search_place trả về nhiều candidate và khách đã chọn
        hoặc xác nhận một candidate. place_id phải lấy nguyên văn từ kết quả
        search_place gần nhất cho cùng target; không tự tạo, đoán, dịch hoặc
        dùng place_id cũ.

        Tool cập nhật booking draft. Khi pickup, destination và vehicle_type
        đã đủ, tool tự tính lại báo giá và làm mất hiệu lực báo giá cũ. Phải
        đọc giá mới, không dùng lại giá trước đó. Nếu chưa có candidate, gọi
        search_place trước.

        Args:
            target: Trường địa điểm cần chọn; chỉ dùng pickup hoặc destination.
            place_id: Mã chính xác do search_place trả về cho target hiện tại.

        Returns:
            Thông báo địa điểm đã chọn, có thể kèm báo giá mới. Tool không xác
            nhận khách đặt xe và không tạo booking.
        """
        context.disallow_interruptions()
        draft = self._draft(context)
        had_quote = draft.quote is not None
        if had_quote:
            await self._interrupt_stale_speech(context)
        try:
            selected = draft.select_place(target, place_id)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        refreshed_quote = (
            await self._refresh_quote_after_change(context)
            if draft.pickup is not None and draft.destination is not None and draft.vehicle_type is not None
            else None
        )
        if (
            draft.pickup is not None
            and draft.destination is not None
            and draft.vehicle_type is not None
            and refreshed_quote is None
        ):
            return "Đã xác nhận địa điểm nhưng chưa thể tính lại giá; hãy gọi estimate_fare trước khi xác nhận."
        context.userdata.clear_failure()
        if refreshed_quote is None:
        await self._commit(context)
        acknowledgement = f"Đã chọn {_target_label(target)} là {selected.display_name}."
        if refreshed_quote is not None:
            return _booking_confirmation_prompt(draft)
        return _selection_followup(draft, target, selected) or acknowledgement

    @function_tool()
    async def set_vehicle_type(
        self,
        context: RunContext[AloSMSessionData],
        vehicle_type: VehicleType,
    ) -> str:
        """Cập nhật loại xe mà khách đã chọn trong booking draft.

        Chỉ gọi khi khách nói rõ loại xe thuộc danh mục được hỗ trợ. Nếu pickup
        và destination đã có, tool tính lại báo giá theo loại xe mới và làm mất
        hiệu lực báo giá cũ. Không tự đọc mã enum hoặc tự tính giá.

        Không gọi khi khách chỉ hỏi các loại xe; Supervisor sẽ gọi
        get_vehicle_options. Không tự chọn xe thay khách và không coi việc chọn
        xe là xác nhận đặt chuyến.

        Args:
            vehicle_type: Một trong MOTORBIKE, CAR_4, CAR_7 hoặc LUXURY; truyền
                đúng enum, không truyền tên hiển thị tự do.

        Returns:
            Thông báo loại xe đã chọn, có thể kèm báo giá mới hoặc hướng dẫn
            tiếp tục thu thập dữ liệu nếu chưa đủ điều kiện báo giá.
        """
        context.disallow_interruptions()
        draft = self._draft(context)
        had_quote = draft.quote is not None
        if had_quote:
            await self._interrupt_stale_speech(context)
        draft.set_vehicle_type(vehicle_type)
        refreshed_quote = (
            await self._refresh_quote_after_change(context)
            if draft.pickup is not None and draft.destination is not None and draft.vehicle_type is not None
            else None
        )
        if (
            draft.pickup is not None
            and draft.destination is not None
            and draft.vehicle_type is not None
            and refreshed_quote is None
        ):
            return "Đã cập nhật loại xe nhưng chưa thể tính lại giá; hãy gọi estimate_fare trước khi xác nhận."
        context.userdata.clear_failure()
        if refreshed_quote is None:
        await self._commit(context)
        acknowledgement = f"Đã chọn loại xe là {vehicle_spoken_label(vehicle_type)}."
        if refreshed_quote is not None:
            return _booking_confirmation_prompt(draft)
        return _vehicle_followup(draft, vehicle_type) or acknowledgement

    @function_tool()
    async def mark_vehicle_needs_clarification(
        self,
        context: RunContext[AloSMSessionData],
        query: str,
    ) -> str:
        """Đánh dấu mô tả loại xe đã được nói nhưng chưa ánh xạ chắc chắn.

        Args:
            query: Nguyên văn phần mô tả loại xe mà khách vừa cung cấp.
        """

        context.disallow_interruptions()
        try:
            self._draft(context).mark_vehicle_needs_clarification(query)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        context.userdata.clear_failure()
        await self._commit(context)
        draft = self._draft(context)
        return json.dumps(
            {
                "message": "Loại xe cần được làm rõ.",
                "supported_vehicle_types": ["MOTORBIKE", "CAR_4", "CAR_7", "LUXURY"],
                "next_required_field": draft.next_required_field(),
                "spoken_prompt": _next_required_prompt(draft),
                "instruction": "Đọc nguyên văn spoken_prompt và tuân thủ thứ tự slot.",
            },
            ensure_ascii=False,
        )

    @function_tool()
    async def estimate_fare(self, context: RunContext[AloSMSessionData]) -> str:
        """Tính báo giá cho booking draft đủ thông tin và yêu cầu xác nhận.

        Chỉ gọi khi draft có pickup, destination và vehicle_type hợp lệ. Tool
        tạo hoặc dùng lại báo giá phù hợp, chuyển draft sang awaiting
        confirmation, rồi trả về prompt đọc lại điểm đón, điểm đến, loại xe và
        câu xác nhận được khuyến nghị.

        Không gọi khi còn thiếu trường; hãy dùng search_place, select_place
        hoặc set_vehicle_type. Không tự tính, làm tròn hay đoán giá/ETA. Báo
        giá không có nghĩa là chuyến đã tạo và không thay thế xác nhận rõ ràng.

        Returns:
            Prompt hướng dẫn khách xác nhận riêng, không gộp yêu cầu đổi slot
            hoặc yêu cầu thêm cho tài xế vào cùng lượt xác nhận.
        """
        context.disallow_interruptions()
        draft = self._draft(context)
        if (
            draft.quote is not None
            and draft.confirmation_status == "awaiting"
            and draft.confirmation_fingerprint == draft.quote.fingerprint
        ):
            return _booking_confirmation_prompt(draft)
        try:
            quote = await self._quotes.estimate(
                user_id=context.userdata.user_id,
                app_session_id=context.userdata.app_session_id,
                draft=draft,
            )
            draft.set_quote(quote)
            # Awaiting-confirmation is a business invariant, not an optional
            # second LLM tool choice. Keeping quote creation and confirmation
            # preparation atomic prevents a valid spoken confirmation from
            # failing when the model narrates the quote without calling another
            # tool first.
            draft.request_confirmation()
        except ValueError as exc:
            context.userdata.record_failure(
                "QUOTE_UNAVAILABLE",
                "Chưa thể tạo báo giá từ thông tin hiện tại.",
                fallback_action="retry",
            )
            await self._commit(context)
            raise ToolError(str(exc)) from exc
        context.userdata.clear_failure()
        await self._commit(context)
        return _booking_confirmation_prompt(draft)

    @function_tool()
    async def confirm_booking(self, context: RunContext[AloSMSessionData]) -> str:
        """Ghi nhận xác nhận đặt chuyến rõ ràng từ câu mới nhất của khách.

        Chỉ gọi sau khi khách đã được báo đầy đủ thông tin và câu mới nhất có
        ít nhất bốn từ, đồng thời thể hiện rõ ý định xác nhận đặt xe. Lỗi ASR
        đã biết “đập xe” được sửa deterministic trước khi phân loại.

        Yêu cầu đổi slot và yêu cầu thêm cho tài xế được ưu tiên trước
        confirmation. Không gọi cho câu hỏi về giá hoặc câu ngắn, mơ hồ
        hoặc sự đồng ý mơ hồ không nói rõ việc đặt chuyến. Tool này chỉ ghi
        nhận confirmation, chưa tạo booking. Nếu thành công, bắt buộc gọi
        create_booking.

        Returns:
            Thông báo xác nhận đã ghi nhận và hướng dẫn gọi create_booking.
            Nếu điều kiện chưa đúng, tool báo lỗi và không được coi booking đã
            xác nhận.
        """
        context.disallow_interruptions()
        latest = self._latest_user_message()
        latest_user_text = latest.text_content if latest is not None else ""
        draft = self._draft(context)
        if has_booking_change_intent(draft, latest_user_text):
            raise ToolError("LATEST_USER_MESSAGE_REQUESTS_BOOKING_CHANGE")
        if has_additional_driver_request(latest_user_text):
            raise ToolError("LATEST_USER_MESSAGE_CONTAINS_ADDITIONAL_DRIVER_REQUEST")
        if not is_explicit_confirmation(latest_user_text):
            raise ToolError("LATEST_USER_MESSAGE_IS_NOT_EXPLICIT_BOOKING_CONFIRMATION")
        existing_booking = draft.booking
        if existing_booking is not None and existing_booking.status != "CANCELLED":
            return f"Chuyến xe đã được đặt thành công với mã {existing_booking.booking_id}. Không tạo thêm chuyến mới."
        if draft.confirmation_status == "confirmed":
            if draft.quote is None or draft.confirmation_fingerprint != draft.quote.fingerprint:
                raise ToolError("BOOKING_CONTEXT_CHANGED")
            context.userdata.clear_failure()
            return "Khách đã xác nhận rõ ràng; có thể gọi create_booking."
        try:
            draft.confirm()
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        context.userdata.clear_failure()
        await self._commit(context)
        return "Khách đã xác nhận rõ ràng; có thể gọi create_booking."

    @function_tool(on_duplicate="confirm")
    async def create_booking(self, context: RunContext[AloSMSessionData]) -> None:
        """Tạo booking demo sau khi draft đã được xác nhận hợp lệ.

        Chỉ gọi sau khi confirm_booking thành công trong cùng quy trình và
        draft có pickup, destination, vehicle_type cùng báo giá hợp lệ. Đây là
        thao tác ghi dữ liệu cuối cùng: không gọi để xem trước giá, khi khách
        mới đồng ý mơ hồ, hoặc để lặp lại một kết quả không xác định.

        Tool idempotent theo cơ chế duplicate của LiveKit. Khi thành công,
        BookingTask hoàn tất với BookingOutcome status=created; kết quả trực
        tiếp là None và Supervisor nhận outcome chứa booking_id để thông báo.
        Nếu lỗi không xác định, không tự tạo chuyến lần nữa.

        Returns:
            Không trả nội dung hội thoại trực tiếp khi thành công; việc thông
            báo dựa trên BookingOutcome do task trả về.
        """
        # A confirmed write must finish deterministically even if the caller speaks
        # while this very short demo operation is being committed.
        context.disallow_interruptions()
        draft = self._draft(context)
        async with context.with_filler(
            "Đang hoàn tất đặt chuyến, bạn chờ một chút nhé.",
            delay=0.8,
        ):
        try:
            booking = await self._bookings.create(
                user_id=context.userdata.user_id,
                app_session_id=context.userdata.app_session_id,
                draft=draft,
            )
            draft.set_booking(booking)
            context.userdata.lifecycle_status = "completed"
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        except Exception as exc:
            logger.exception("failed to create booking handoff session=%s", context.userdata.app_session_id)
            context.userdata.record_failure(
                "BOOKING_RESULT_UNKNOWN",
                "Chưa xác định được kết quả tạo chuyến; không tự động tạo lại.",
                retryable=False,
                fallback_action="handoff",
            )
            await self._commit(context)
            raise ToolError("BOOKING_RESULT_UNKNOWN") from exc
        context.userdata.clear_failure()
            context.userdata.post_booking_support = PostBookingSupportState.for_booking(booking)
        await self._commit(context)
        outcome = BookingOutcome(
            status="created",
            booking=booking,
            message=post_booking_menu_message(
                booking.booking_id,
                booking.estimated_fare,
                booking.currency,
            ),
        )
        if not self.done():
            self.complete(outcome)
        return None
