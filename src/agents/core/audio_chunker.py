"""Vietnamese Streaming Audio Chunker — Tách cụm âm thanh đàm thoại thời gian thực.

Tối ưu hóa độ trễ phản hồi âm thanh đầu tiên (Time-To-First-Audio - TTFA):
- Trong môi trường LiveKit WebRTC, LLM sinh ra token theo luồng (streaming tokens).
- Nếu chờ cả câu dài hoàn tất mới gửi TTS, TTFA P95 có thể vượt quá 2.0s.
- VietnameseAudioChunker phát hiện các điểm ngắt tự nhiên trong ngữ pháp tiếng Việt:
    1. Dấu ngắt câu chính: chấm (.), chấm than (!), chấm hỏi (?), xuống dòng (\\n).
    2. Dấu ngắt mệnh đề hội thoại: phẩy (,), chấm phẩy (;), gạch ngang (—), ba chấm (...).
    3. Thán từ/từ đệm hội thoại cuối cụm: "dạ", "vâng", "ạ", "nhé", "nha".
- Bảo vệ các cụm viết tắt, địa danh và số điện thoại không bị tách sai:
    "TP.HCM", "TTTM", "Q.1", "P.2", "0912.xxx", "29E-123.45", "VinFast VF 8".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
import time


# Danh mục các từ viết tắt phổ biến cần bảo vệ không ngắt theo dấu chấm
_ABBREVIATIONS = {
    "tp.hcm", "tp. hn", "tttm", "q.", "p.", "tx.", "tp.",
    "gsm", "vinfast", "vinuni", "vric", "ts.", "ths.", "bs.", "mr.", "mrs.", "ms.",
}

# Regex nhận diện số điện thoại, biển số, tọa độ số
_NUMERIC_DOT_PATTERN = re.compile(r"\b\d+\.\d+\b")


@dataclass
class ChunkerStats:
    """Thống kê hiệu năng của luồng tách audio."""
    tokens_received: int = 0
    chunks_emitted: int = 0
    total_characters: int = 0
    first_chunk_chars: int = 0
    stream_started_at: float = field(default_factory=time.monotonic)
    first_chunk_emitted_at: float | None = None

    @property
    def time_to_first_chunk_ms(self) -> float | None:
        if self.first_chunk_emitted_at is None:
            return None
        return (self.first_chunk_emitted_at - self.stream_started_at) * 1000


class VietnameseAudioChunker:
    """Bộ tách câu và mệnh đề hội thoại phục vụ TTS streaming.

    Usage:
        chunker = VietnameseAudioChunker(min_chunk_chars=18)
        for token in llm_stream:
            for ready_chunk in chunker.push(token):
                await tts.send(ready_chunk)
        if remaining := chunker.flush():
            await tts.send(remaining)
    """

    def __init__(self, min_chunk_chars: int = 18, max_chunk_chars: int = 120) -> None:
        self.min_chunk_chars = max(5, min_chunk_chars)
        self.max_chunk_chars = max(self.min_chunk_chars, max_chunk_chars)
        self._buffer: str = ""
        self.stats = ChunkerStats()

    def reset(self) -> None:
        """Đặt lại trạng thái bộ đệm."""
        self._buffer = ""
        self.stats = ChunkerStats()

    def push(self, token: str) -> list[str]:
        """Đẩy 1 token mới vào buffer và trích xuất các cụm văn bản đã đủ điều kiện phát âm."""
        self._buffer += token
        self.stats.tokens_received += 1
        self.stats.total_characters += len(token)

        emitted: list[str] = []

        while True:
            chunk = self._try_extract_chunk()
            if chunk:
                emitted.append(chunk)
                self.stats.chunks_emitted += 1
                if self.stats.first_chunk_emitted_at is None:
                    self.stats.first_chunk_emitted_at = time.monotonic()
                    self.stats.first_chunk_chars = len(chunk)
            else:
                break

        return emitted

    def flush(self) -> str | None:
        """Đẩy toàn bộ ký tự còn lại trong buffer khi luồng kết thúc."""
        trimmed = self._buffer.strip()
        self._buffer = ""
        if trimmed:
            self.stats.chunks_emitted += 1
            if self.stats.first_chunk_emitted_at is None:
                self.stats.first_chunk_emitted_at = time.monotonic()
                self.stats.first_chunk_chars = len(trimmed)
            return trimmed
        return None

    def _try_extract_chunk(self) -> str | None:
        """Kiểm tra xem buffer hiện tại có thỏa mãn điều kiện ngắt cụm hay không."""
        buf = self._buffer
        if not buf:
            return None

        # Trường hợp buffer vượt quá độ dài tối đa cho phép
        if len(buf) >= self.max_chunk_chars:
            # Tìm khoảng trắng gần nhất từ ký tự 60 trở đi để ngắt tự nhiên
            split_idx = buf.rfind(" ", self.min_chunk_chars, self.max_chunk_chars)
            if split_idx != -1:
                chunk = buf[:split_idx].strip()
                self._buffer = buf[split_idx:].lstrip()
                return chunk

        # Tìm các điểm ngắt tự nhiên
        for idx in range(len(buf)):
            char = buf[idx]

            # 1. Dấu kết thúc câu hoàn chỉnh: ., !, ?, \n
            if char in {".", "!", "?", "\n"}:
                # Nếu là dấu chấm, kiểm tra các trường hợp ngoại lệ
                if char == ".":
                    # Ký tự tiếp theo không phải khoảng trắng -> là phần của số hoặc từ (vd: 0912.345, TP.HCM)
                    if idx + 1 < len(buf) and buf[idx + 1] not in {" ", "\t", "\n", '"', "'", ")", "]", "}"}:
                        continue
                    # Ký tự trước và sau là số
                    if idx > 0 and buf[idx - 1].isdigit() and idx + 1 < len(buf) and buf[idx + 1].isdigit():
                        continue
                    # Từ kết thúc bằng dấu chấm là từ viết tắt
                    sub_before = buf[: idx + 1].strip()
                    if self._is_abbreviation(sub_before):
                        continue

                chunk = buf[: idx + 1].strip()
                self._buffer = buf[idx + 1:].lstrip()
                return chunk

            # 2. Dấu ngắt mệnh đề hội thoại: ,, ;, —, ..., …
            if char in {",", ";", "—", "…"}:
                # Chỉ ngắt nếu độ dài đã đạt tối thiểu min_chunk_chars
                candidate = buf[: idx + 1].strip()
                if len(candidate) >= self.min_chunk_chars:
                    chunk = candidate
                    self._buffer = buf[idx + 1:].lstrip()
                    return chunk

        # 3. Kiểm tra thán từ đệm kết thúc cụm ngữ cảnh tiếng Việt (ạ, nhé, nha, vâng)
        words = buf.split()
        if len(words) >= 4 and len(buf.strip()) >= self.min_chunk_chars:
            last_word = words[-1].lower().rstrip(",.!?")
            if last_word in {"ạ", "nhé", "nha", "được không ạ"}:
                # Đảm bảo sau đó có khoảng trắng hoặc đã kết thúc
                if buf.endswith(" ") or buf.endswith("\n"):
                    chunk = buf.strip()
                    self._buffer = ""
                    return chunk

        return None

    @staticmethod
    def _is_abbreviation(text_prefix: str) -> bool:
        """Kiểm tra chuỗi kết thúc bằng dấu chấm có phải là từ viết tắt không."""
        last_word = text_prefix.split()[-1].lower() if text_prefix.split() else ""
        for abbr in _ABBREVIATIONS:
            if last_word == abbr or last_word.endswith(abbr):
                return True
        return False

    @classmethod
    def chunk_text(cls, text: str, min_chunk_chars: int = 18) -> list[str]:
        """Hàm tiện ích tách chuỗi văn bản hoàn chỉnh thành các cụm streaming chunk."""
        chunker = cls(min_chunk_chars=min_chunk_chars)
        # Giả lập streaming theo từng từ
        chunks: list[str] = []
        tokens = re.split(r"(\s+)", text)
        for token in tokens:
            emitted = chunker.push(token)
            chunks.extend(emitted)
        if final := chunker.flush():
            chunks.append(final)
        return chunks
