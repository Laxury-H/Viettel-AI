#!/usr/bin/env python3
"""Bước 2 — So khớp từ điển, an toàn với Unicode và ranh giới âm tiết tiếng Việt.

Hai bẫy đã làm hỏng bản V9 và được sửa ở đây:

1. `unicodedata.normalize("NFC", text)` LÀM ĐỔI ĐỘ DÀI CHUỖI trên 20/100 hồ sơ
   của corpus (chúng ở dạng tổ hợp NFD). Mọi offset trả về sau đó đều lệch, sinh
   ra span cắt ngang từ như `' do cào ho'` hay `'ộ C\\n'`. Vì vậy hàm fold ở đây
   CHỈ dùng `str.lower()` và tự assert độ dài không đổi; thay vào đó từ điển được
   dò theo cả hai biến thể NFC và NFD.

2. Tiếng Việt viết rời từng âm tiết, nên một âm tiết đứng lẻ vẫn thỏa điều kiện
   ranh giới từ ngay cả khi nằm giữa một từ ghép: `"mạch"` khớp bên trong
   `"tĩnh mạch"`, `"nang"` khớp trong `"nang lông"`. Mỗi lần như vậy sai cả span
   lẫn nhãn nên bị phạt kép. Bề mặt mới bắt buộc có ≥2 âm tiết trừ allowlist.
"""

from __future__ import annotations

import unicodedata

# Viết tắt lâm sàng được phép đứng một mình dù chỉ một âm tiết.
SINGLE_TOKEN_ALLOW = {
    "ct", "mri", "ercp", "mrcp", "ekg", "ecg", "copd", "hba1c", "spo2",
    "ast", "alt", "got", "gpt", "ldh", "bun", "crp", "esr", "inr",
    "wbc", "rbc", "hgb", "plt", "egfr", "tsh", "psa", "cea", "afp",
    "troponin", "creatinin", "creatinine", "bilirubin", "albumin",
    "glucose", "insulin", "kali", "natri", "canxi", "ure", "amylase",
}


def fold(text: str) -> str:
    """Hạ chữ hoa để so khớp, bảo toàn tuyệt đối độ dài (và do đó là offset)."""
    lowered = text.lower()
    if len(lowered) != len(text):
        raise ValueError("fold làm đổi độ dài chuỗi; offset sẽ sai")
    return lowered


def is_word_char(ch: str) -> bool:
    # Dấu thanh rời trong dạng NFD là ký tự tổ hợp, thuộc về âm tiết đứng trước.
    return ch.isalnum() or ch == "_" or unicodedata.combining(ch) != 0


def surface_variants(surface: str) -> list[str]:
    """Biến thể cần dò: corpus trộn cả dạng dựng sẵn (NFC) lẫn tổ hợp (NFD)."""
    seen: list[str] = []
    for form in (surface,
                 unicodedata.normalize("NFC", surface),
                 unicodedata.normalize("NFD", surface)):
        key = form.lower()
        if key and key not in seen:
            seen.append(key)
    return seen


def is_single_syllable(surface: str) -> bool:
    key = surface.strip().lower()
    return len(key.split()) < 2 and key not in SINGLE_TOKEN_ALLOW


class Matcher:
    """Dò từ điển theo nguyên tắc cụm dài thắng cụm ngắn, không chồng lấn."""

    def __init__(self, lexicon: dict[str, dict], allow_single_syllable: bool = False):
        probes: list[tuple[str, dict]] = []
        for spec in lexicon.values():
            surface = spec.get("surface", "")
            if not surface:
                continue
            if not allow_single_syllable and is_single_syllable(surface):
                continue
            for variant in surface_variants(surface):
                probes.append((variant, spec))
        probes.sort(key=lambda item: len(item[0]), reverse=True)
        self._probes = probes

    def find(self, text: str, blocked: list[bool]) -> list[dict]:
        """Trả về các khớp nằm ngoài mọi vùng đã bị chiếm, kèm offset chuẩn."""
        folded = fold(text)
        found: list[dict] = []

        for key, spec in self._probes:
            start = 0
            klen = len(key)
            while True:
                idx = folded.find(key, start)
                if idx < 0:
                    break
                start = idx + 1
                end = idx + klen

                if idx > 0 and is_word_char(folded[idx - 1]):
                    continue
                if end < len(folded) and is_word_char(folded[end]):
                    continue
                if any(blocked[idx:end]):
                    continue

                surface = text[idx:end]
                # Chốt chặn: span phải sạch hai đầu, lệch là dấu hiệu hỏng offset.
                if surface != surface.strip():
                    continue

                found.append({
                    "text": surface,
                    "type": spec["type"],
                    "position": [idx, end],
                    "codes": list(spec.get("codes") or []),
                })
                for pos in range(idx, end):
                    blocked[pos] = True

        return found
