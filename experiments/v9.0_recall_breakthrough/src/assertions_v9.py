#!/usr/bin/env python3
"""Suy luận assertion (isNegated / isFamily / isHistorical) cho thực thể MỚI.

Nguyên tắc: chỉ áp dụng cho thực thể do V9 bổ sung. Assertion của thực thể
kế thừa từ baseline được giữ nguyên tuyệt đối vì mô hình chấm điểm cho thấy
chất lượng assertion trên các span đã khớp gần như tối đa (a ~ 0.9-1.0).
"""

from __future__ import annotations

import re

# Cửa sổ ngữ cảnh (ký tự) nhìn ngược về trước mention.
_LEFT_WINDOW = 60
# Cửa sổ nhìn về sau, dùng cho các mẫu hậu tố kiểu "X: không".
_RIGHT_WINDOW = 25

# --- Phủ định -------------------------------------------------------------
# Các cụm đứng TRƯỚC mention và phủ định nó.
_NEG_CUES = (
    "không có",
    "không thấy",
    "không ghi nhận",
    "không phát hiện",
    "chưa phát hiện",
    "chưa ghi nhận",
    "không bị",
    "không còn",
    "không kèm",
    "không đau",
    "loại trừ",
    "âm tính với",
    "không",
    "chưa",
)

# Nếu giữa cue và mention xuất hiện các token này thì phạm vi phủ định bị chặn.
_NEG_BLOCKERS = re.compile(r"[.;?!]|\bnhưng\b|\bmà\b|\btuy nhiên\b|\bcó\b")

# --- Tiền sử --------------------------------------------------------------
_HIST_CUES = (
    "tiền sử",
    "tiền căn",
    "bệnh sử",
    "đã từng",
    "từng bị",
    "trước đây",
    "trước đó",
    "đã được chẩn đoán",
    "được chẩn đoán",
    "cách đây",
    "nhiều năm nay",
    "trong quá khứ",
    "đã mắc",
    "bệnh lý mãn tính",
    "các bệnh lý mãn tính",
    "bệnh nền",
    "đang điều trị",
)

# Heading section gợi ý toàn bộ vùng là tiền sử.
_HIST_SECTION = re.compile(
    r"^\s*\d*\s*\.?\s*(tiền sử|tiền căn|bệnh sử(?! hiện tại)|"
    r"các bệnh lý mãn tính|thuốc (?:dùng )?trước (?:khi )?nhập viện|"
    r"danh sách thuốc trước nhập viện)",
    re.I | re.M,
)

# --- Gia đình -------------------------------------------------------------
_FAMILY_CUES = (
    "tiền sử gia đình",
    "gia đình",
    "bố",
    "cha",
    "mẹ",
    "anh trai",
    "chị gái",
    "em trai",
    "em gái",
    "ông",
    "bà",
    "con trai",
    "con gái",
    "người thân",
    "họ hàng",
)

_FAMILY_BLOCKERS = re.compile(r"[.;?!]")


def _left_context(text: str, start: int, window: int = _LEFT_WINDOW) -> str:
    return text[max(0, start - window):start].lower()


def _cue_hit(context: str, cues: tuple[str, ...], blocker: re.Pattern | None) -> bool:
    """Tìm cue gần mention nhất; trả True nếu không bị chặn bởi ranh giới câu."""
    best = -1
    for cue in cues:
        idx = context.rfind(cue)
        if idx > best:
            best = idx + len(cue)
    if best < 0:
        return False
    if blocker is not None and blocker.search(context[best:]):
        return False
    return True


def _in_history_section(text: str, start: int) -> bool:
    """Mention có nằm dưới một heading tiền sử không (đến heading kế tiếp)?"""
    last = None
    for match in _HIST_SECTION.finditer(text, 0, start):
        last = match
    if last is None:
        return False
    # Heading mới dạng "2. ..." xuất hiện sau đó sẽ đóng vùng tiền sử.
    nxt = re.search(r"^\s*\d+\s*\.\s+\S", text[last.end():start], re.M)
    return nxt is None


def infer_assertions(text: str, start: int, end: int, etype: str) -> list[str]:
    """Trả về danh sách assertion cho một mention mới, theo thứ tự ổn định."""
    left = _left_context(text, start)
    found: list[str] = []

    if _cue_hit(left, _NEG_CUES, _NEG_BLOCKERS):
        found.append("isNegated")
    else:
        # Mẫu hậu tố: "phù: không", "sốt (-)"
        right = text[end:end + _RIGHT_WINDOW].lower()
        if re.match(r"\s*[:(]?\s*(?:không|\(-\)|-\))", right):
            found.append("isNegated")

    if _cue_hit(left, _FAMILY_CUES, _FAMILY_BLOCKERS):
        found.append("isFamily")

    if _cue_hit(left, _HIST_CUES, None) or _in_history_section(text, start):
        found.append("isHistorical")

    order = {"isNegated": 0, "isFamily": 1, "isHistorical": 2}
    return sorted(set(found), key=lambda a: order[a])
