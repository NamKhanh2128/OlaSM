"""Vietnamese natural language schedule parser for ride booking.

Deterministic extraction of pickup times from spoken Vietnamese:
- Immediate ("đi luôn", "bây giờ", "ngay lập tức") -> ScheduleKind.NOW
- Relative ("15 phút nữa", "nửa tiếng nữa", "1 tiếng nữa") -> ScheduleKind.LATER
- Clock times ("8 giờ sáng", "8h30", "8 rưỡi tối", "14:00") -> ScheduleKind.LATER
- Day disambiguation ("mai", "hôm nay", "tối nay", "sáng mai")
All calculations use Indochina Time (UTC+7).
"""

from __future__ import annotations

import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator

VN_TZ = timezone(timedelta(hours=7))
SCHEDULE_NOW = "bây giờ"

_WHITESPACE = re.compile(r"\s+")

_NOW_PHRASES = (
    "bây giờ",
    "đi luôn",
    "đi ngay",
    "càng sớm càng tốt",
    "ngay lập tức",
    "luôn bây giờ",
)
_NOW_WORDS = ("luôn", "ngay")

_MORNING = ("sáng",)
_NOON = ("trưa",)
_AFTERNOON = ("chiều",)
_EVENING = ("tối", "đêm", "khuya")

_WINDOW_LABELS = ("sáng", "trưa", "chiều", "tối", "đêm", "khuya")
_TOMORROW = "mai"
_TODAY = "nay"

_CLOCK = re.compile(
    r"(?:^|\s)(\d{1,2})\s*(?:gio|h|:)\s*(\d{1,2})?(?!\d)|(?:^|\s)(\d{1,2})\s*(ruoi)"
)
_RELATIVE_MINUTES = re.compile(r"(?:^|\s)(\d{1,3})\s*(phut|tieng|gio)\s+nua")
_RELATIVE_HALF = re.compile(r"(?:^|\s)nua\s*(?:tieng|gio)\s+nua")
_MAX_AHEAD = timedelta(days=2)


class ScheduleKind(StrEnum):
    NOW = "NOW"
    LATER = "LATER"


class RideSchedule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ScheduleKind
    at_epoch_ms: int | None = None
    display: str

    @model_validator(mode="after")
    def _validate_kind(self) -> RideSchedule:
        if self.kind is ScheduleKind.LATER and self.at_epoch_ms is None:
            raise ValueError("a scheduled ride needs at_epoch_ms")
        if self.kind is ScheduleKind.NOW and self.at_epoch_ms is not None:
            raise ValueError("an immediate ride has no at_epoch_ms")
        return self


def _spoken(value: str) -> str:
    return _WHITESPACE.sub(" ", value.lower()).strip()


def _stripped(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower().replace("đ", "d"))
    without_tones = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _WHITESPACE.sub(" ", without_tones).strip()


def _has_word(text: str, word: str) -> bool:
    return re.search(rf"(?<![^\W\d_]){re.escape(word)}(?![^\W\d_])", text) is not None


def _first_word(text: str, words: tuple[str, ...]) -> str | None:
    return next((word for word in words if _has_word(text, word)), None)


def _immediate() -> RideSchedule:
    return RideSchedule(kind=ScheduleKind.NOW, display=SCHEDULE_NOW)


def _display(at: datetime, now: datetime) -> str:
    clock = at.strftime("%H:%M")
    days = (at.date() - now.date()).days
    if days == 0:
        return f"{clock} hôm nay"
    if days == 1:
        return f"{clock} ngày mai"
    return f"{clock} ngày {at.day:02d}/{at.month:02d}"


def _later(at: datetime, now: datetime) -> RideSchedule | None:
    if at <= now or at - now > _MAX_AHEAD:
        return None
    return RideSchedule(
        kind=ScheduleKind.LATER,
        at_epoch_ms=int(at.timestamp() * 1000),
        display=_display(at, now),
    )


def _relative(stripped: str, now: datetime) -> RideSchedule | None:
    if _RELATIVE_HALF.search(stripped):
        return _later(now + timedelta(minutes=30), now)
    match = _RELATIVE_MINUTES.search(stripped)
    if match is None:
        return None
    amount = int(match.group(1))
    minutes = amount if match.group(2) == "phut" else amount * 60
    if minutes <= 0:
        return None
    return _later(now + timedelta(minutes=minutes), now)


def _next_word(text: str, index: int) -> str:
    rest = text[index:].split()
    return rest[0] if rest else ""


def _clock_time(stripped: str) -> tuple[int, int] | None:
    match = _CLOCK.search(stripped)
    if match is None:
        return None
    if match.group(4) == "ruoi":
        return int(match.group(3)), 30
    hour = int(match.group(1))
    if match.group(2) is not None:
        return hour, int(match.group(2))
    return hour, 30 if _next_word(stripped, match.end()) == "ruoi" else 0


def _apply_window(hour: int, window: str | None) -> int | None:
    if window is None:
        return hour
    if window in _MORNING:
        if hour == 12:
            return 0
        return hour if hour < 12 else None
    if window in _NOON:
        if hour in (1, 2):
            return hour + 12
        return hour if hour in (11, 12) else None
    if window in _AFTERNOON or window in _EVENING:
        return hour + 12 if hour < 12 else hour
    return hour


def named_time_window(utterance: str) -> str | None:
    spoken = _spoken(utterance)
    stripped = _stripped(utterance)
    if _CLOCK.search(stripped) or _RELATIVE_MINUTES.search(stripped):
        return None
    if _RELATIVE_HALF.search(stripped):
        return None

    window = _first_word(spoken, _WINDOW_LABELS)
    day = _first_word(spoken, (_TOMORROW, _TODAY))
    if window is None:
        return "ngày mai" if day == _TOMORROW else None
    return f"{window} {day}" if day else window


def parse_schedule(utterance: str, now_ms: int | None = None) -> RideSchedule | None:
    """Parse a customer utterance for pickup schedule.

    Returns RideSchedule (NOW or LATER) or None if no valid schedule was mentioned.
    """
    if now_ms is None:
        now_ms = int(time.time() * 1000)

    spoken = _spoken(utterance)
    stripped = _stripped(utterance)
    now = datetime.fromtimestamp(now_ms / 1000, VN_TZ)

    relative = _relative(stripped, now)
    if relative is not None:
        return relative

    window = _first_word(spoken, _WINDOW_LABELS)
    tomorrow = _has_word(spoken, _TOMORROW)

    clock = _clock_time(stripped)
    if clock is None:
        if window is not None or tomorrow:
            return None
        if any(phrase in spoken for phrase in _NOW_PHRASES) or _first_word(spoken, _NOW_WORDS):
            return _immediate()
        return None

    hour, minute = clock
    if minute > 59:
        return None
    shifted = _apply_window(hour, window)
    if shifted is None or shifted > 23:
        return None

    at = now.replace(hour=shifted, minute=minute, second=0, microsecond=0)
    if tomorrow:
        at += timedelta(days=1)
    elif at <= now:
        at += timedelta(days=1)
    return _later(at, now)
