"""Shared query validator for booking place inputs (pickup/destination)."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache


def _normalize(value: str) -> str:
    """Normalize Vietnamese text: casefold + remove diacritics + compress whitespace."""
    # Unicode decomposition removes combining marks from Vietnamese vowels, but
    # the distinct letter "đ" does not decompose into "d" automatically.
    casefolded = value.casefold().replace("đ", "d")
    decomposed = unicodedata.normalize("NFKD", casefolded)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", without_marks).split())


# Filler words, discourse particles, conversational verbs, pronouns that should
# not be treated as a place name when standing alone.
_BLOCKED_SINGLE_WORD_QUERIES = frozenset(
    {
        # Discourse particles (particles used in Vietnamese conversation)
        "roi",  # rồi
        "thoi",  # thôi
        "vang",  # vâng
        "nham",  # nhầm
        "muon",  # muốn (when used as "I want")
        "cho",  # for (preposition)
        "o",  # ở (preposition, at)
        "tai",  # tại (at, due to)
        "di",  # đi (go, used as narrative marker)
        "den",  # đến (arrive, come)
        "toi",  # tôi (I)
        "minh",  # mình (me, I)
        "ban",  # bạn (you, friend)
        "ay",  # ấy (that one)
        "nay",  # này (this)
        "kia",  # kia (that one over there)
        "day",  # đây (here)
        "do",  # đó (there)
        "dung",  # dùng (use)
        "khong",  # không (not)
        "co",  # có (have)
        "la",  # là (is)
        "phai",  # phải (must, should, right?)
        "nhung",  # nhưng (but)
        "va",  # và (and)
        "hay",  # hay (or)
        "sao",  # sao (why)
        "the",  # thế (so, that way)
        "thi",  # thì (then)
        "khi",  # khi (when)
        "neu",  # nếu (if)
        "vi",  # vì (because)
        "nhu",  # như (like)
        "cung",  # cũng (also)
        "da",  # đã (already)
        "se",  # sẽ (will)
        "ang",  # ăng (being, used as filler)
        "em",  # em (younger person, I, me)
        "anh",  # anh (older brother, he, you)
        "chi",  # chị (older sister, she, you)
        "chu",  # chú (uncle)
        "bac",  # bác (uncle/aunt)
        "on",  # ơn (thank)
        "nha",  # nhá (please)
        "day",  # dạy (teach)
        "dua",  # đưa (give)
        "lay",  # lấy (take)
        "cho",  # cho (give)
        "de",  # để (in order to)
        "buon",  # buồn (sad)
        "vui",  # vui (happy)
        "tot",  # tốt (good)
        "xau",  # xấu (bad)
        "lon",  # lớn (big)
        "nho",  # nhỏ (small)
        "tren",  # trên (above)
        "duoi",  # dưới (below)
        "trai",  # trái (left)
        "phai",  # phải (right)
        "trong",  # trong (in)
        "ngoai",  # ngoài (out)
        "truoc",  # trước (before)
        "sau",  # sau (after)
        "ben",  # bên (side)
        "canh",  # cạnh (next to)
        "gan",  # gần (near)
        "xa",  # xa (far)
        "bien",  # biên (border)
        "he",  # hế (is, used in speech)
        "huh",  # hủy (cancel)
        "huy",  # hủy (cancel)
        "ok",
        "okee",
        "okay",
    }
)


@lru_cache(maxsize=256)
def _load_place_names() -> frozenset[str]:
    """Load canonical place names from gazetteer for exact-name validation."""
    from src.backend.services.place_search_service import _load_place_names as gs_load

    return frozenset(_normalize(name) for name in gs_load())


@lru_cache(maxsize=256)
def _load_place_aliases() -> frozenset[str]:
    """Load all aliases from gazetteer for exact-alias validation."""
    from src.backend.services.place_search_service import _load_aliases

    aliases = _load_aliases()
    return frozenset(aliases.keys())  # keys are already normalized


def is_valid_single_word_place_query(query: str) -> bool:
    """Check if a single-word query is a valid place (exact canonical name or alias).

    Returns:
        True if the query is a valid place name or alias; False if it's a blocked
        word or doesn't match any known place exactly.
    """
    normalized = _normalize(query.strip())
    words = normalized.split()

    # Only validates single-word queries
    if len(words) != 1:
        return True  # Multi-word queries are handled by substring matching overrides

    single_word = words[0]

    # Reject blocked filler/conversational words
    if single_word in _BLOCKED_SINGLE_WORD_QUERIES:
        return False

    # Accept if it matches exactly a canonical name or alias
    place_names = _load_place_names()
    place_aliases = _load_place_aliases()
    if single_word in place_names or single_word in place_aliases:
        return True

    # Single-word query that doesn't match any known place
    return False


def is_valid_place_query(query: str) -> bool:
    """Comprehensive validation for place queries (pickup/destination).

    Blocks:
    - Empty/whitespace-only queries
    - Single-word queries that are blocked discourse words or don't match exact names/aliases

    Allows:
    - Multi-word queries (validated by gazetteer substring matching)
    - Single-word queries that exactly match canonical names or aliases (e.g., "VinUni")

    Args:
        query: The place query to validate

    Returns:
        True if the query is valid; False if it should be rejected
    """
    if not query or not query.strip():
        return False

    normalized = _normalize(query.strip())
    if not normalized:
        return False

    words = normalized.split()

    # Single-word queries require exact match
    if len(words) == 1:
        return is_valid_single_word_place_query(query)

    # Multi-word queries are valid if they contain at least one non-blocked word
    # and are not purely filler/discourse words
    blocked_count = sum(1 for word in words if word in _BLOCKED_SINGLE_WORD_QUERIES)
    return blocked_count < len(words)
