#!/usr/bin/env python3
"""Bước 1 — Băm bệnh án thành vùng ngữ nghĩa, và Bước 4 — suy luận assertion.

Vùng được dùng cho hai việc: giới hạn phạm vi bổ sung khái niệm, và cấp ngữ cảnh
thời gian cho assertion.

Về assertion, module này cố tình DÈ DẶT. Phân bố của bài nền: 81.6% khái niệm có
assertions rỗng. Với Jaccard theo từng khái niệm, đoán rỗng có kỳ vọng ~0.82,
nên một luật chỉ đúng 50% sẽ KÉO ĐIỂM XUỐNG. Ngoài ra bất đối xứng đã đo được
rất lớn: V57 sửa đúng 8 assertion được +0.0183, còn V32 sửa sai 8 assertion mất
0.2393 — chênh khoảng 13 lần.

`isFamily` bị vô hiệu hóa hoàn toàn cho khái niệm mới: bài nền chỉ dùng nhãn này
6 lần trên 2687 khái niệm, và V32 chính là lần thử gán nó theo từ chỉ quan hệ.
"""

from __future__ import annotations

import re

# ---- Bước 1: phân vùng ----------------------------------------------------

SECTION_PATTERNS = (
    ("HISTORY", re.compile(
        r"^[ \t]*\d*[ \t]*\.?[ \t]*(tiền sử|tiền căn|bệnh sử|lý do (vào|nhập) viện|"
        r"các bệnh lý mãn tính|bệnh lý mãn tính|bệnh nền)", re.I | re.M)),
    ("MEDICATIONS", re.compile(
        r"^[ \t]*\d*[ \t]*\.?[ \t]*(thuốc|đơn thuốc|y lệnh|điều trị|"
        r"danh sách thuốc|thuốc (?:dùng )?trước (?:khi )?nhập viện)", re.I | re.M)),
    ("COUNSELING", re.compile(
        r"^[ \t]*\d*[ \t]*\.?[ \t]*(lời dặn|tư vấn|khuyến cáo|phòng bệnh|hỏi[ :]|"
        r"câu hỏi|trả lời)", re.I | re.M)),
    ("EXAM", re.compile(
        r"^[ \t]*\d*[ \t]*\.?[ \t]*(khám|thăm khám|diễn biến|cận lâm sàng|"
        r"xét nghiệm|chẩn đoán hình ảnh|dấu hiệu sinh tồn)", re.I | re.M)),
)


def slice_sections(text: str) -> list[tuple[int, int, str]]:
    """Trả về các đoạn (start, end, nhãn vùng), phủ kín văn bản."""
    marks: list[tuple[int, str]] = []
    for label, pattern in SECTION_PATTERNS:
        for m in pattern.finditer(text):
            marks.append((m.start(), label))
    if not marks:
        return [(0, len(text), "BODY")]

    marks.sort()
    spans: list[tuple[int, int, str]] = []
    if marks[0][0] > 0:
        spans.append((0, marks[0][0], "BODY"))
    for i, (pos, label) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        spans.append((pos, end, label))
    return spans


def section_at(spans: list[tuple[int, int, str]], offset: int) -> str:
    for start, end, label in spans:
        if start <= offset < end:
            return label
    return "BODY"


# ---- Bước 4: assertion ----------------------------------------------------

_NEG_WINDOW = 30
_HIST_WINDOW = 45

_NEG_CUES = (
    "không có", "không thấy", "không ghi nhận", "không phát hiện",
    "chưa phát hiện", "chưa ghi nhận", "không bị", "không còn",
    "không kèm", "không xuất hiện", "loại trừ", "phủ nhận",
)
_NEG_BLOCKER = re.compile(r"[.;:?!\n]|\bnhưng\b|\bmà\b|\btuy nhiên\b|\bcó\b|\bkèm theo\b")

_HIST_CUES = (
    "tiền sử", "tiền căn", "đã từng", "từng bị", "trước đây", "trước đó",
    "đã được chẩn đoán", "cách đây", "nhiều năm nay", "đã mắc", "bệnh nền",
)
_HIST_BLOCKER = re.compile(r"[.;?!\n]")


def _cue_hit(context: str, cues: tuple[str, ...], blocker: re.Pattern) -> bool:
    best = -1
    for cue in cues:
        idx = context.rfind(cue)
        if idx > best:
            best = idx + len(cue)
    if best < 0:
        return False
    return not blocker.search(context[best:])


def infer_assertions(text: str, start: int, end: int) -> list[str]:
    """Assertion cho một khái niệm MỚI. Mặc định rỗng — đó là lựa chọn an toàn."""
    found: list[str] = []

    negated = _cue_hit(text[max(0, start - _NEG_WINDOW):start].lower(),
                       _NEG_CUES, _NEG_BLOCKER)
    if negated:
        found.append("isNegated")

    # Đang bị phủ định thì không đồng thời là tiền sử; gán cả hai là lỗi ngược dấu.
    if not negated:
        if _cue_hit(text[max(0, start - _HIST_WINDOW):start].lower(),
                    _HIST_CUES, _HIST_BLOCKER):
            found.append("isHistorical")

    order = {"isNegated": 0, "isHistorical": 1}
    return sorted(set(found), key=lambda a: order[a])
