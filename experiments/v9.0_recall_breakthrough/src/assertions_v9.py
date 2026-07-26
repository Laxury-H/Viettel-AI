#!/usr/bin/env python3
"""Suy luận assertion cho thực thể MỚI do V9 bổ sung.

Assertion của thực thể kế thừa từ bài nền 41.9973 điểm được giữ nguyên tuyệt đối.

Nguyên tắc thiết kế — vì sao ở đây cố tình DÈ DẶT:

  J_assertions tính Jaccard theo từng khái niệm rồi lấy trung bình. Với một khái
  niệm, đoán rỗng khi đáp án rỗng được 1.0, đoán sai nhãn được 0.0. Phân bố quan
  sát trên bài nền: 81.6% khái niệm có assertions rỗng.

  Do đó đoán rỗng có kỳ vọng ~0.82, còn một luật chỉ đúng 50% sẽ KÉO ĐIỂM XUỐNG.
  Chỉ phát nhãn khi tín hiệu ngôn ngữ thực sự rõ.

  Riêng isFamily đã bị vô hiệu hóa: lần thử gán isFamily theo từ chỉ quan hệ
  (V32) làm mất 0.2393 điểm, và bài nền chỉ dùng nhãn này 6 lần trên 2687 khái
  niệm (0.2%). Trong corpus này "bố/mẹ/con" hầu hết là người kể chuyện nói về
  chính bệnh nhân, không phải tiền sử gia đình.
"""

from __future__ import annotations

import re

# Cửa sổ hẹp: cue phải nằm sát mention thì phạm vi phủ định mới đáng tin.
_NEG_WINDOW = 30
_HIST_WINDOW = 45

# --- Phủ định -------------------------------------------------------------
# Chỉ nhận cụm phủ định TƯỜNG MINH. Cố tình bỏ "không"/"chưa" đứng trần vì
# chúng bắt nhầm rất nhiều trong văn phong hỏi đáp ("không biết có phải...").
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
    "không xuất hiện",
    "loại trừ",
    "phủ định",
)

# Bất kỳ dấu ngắt câu hay liên từ đảo ý nào cũng cắt phạm vi phủ định.
_NEG_BLOCKER = re.compile(r"[.;:?!\n]|\bnhưng\b|\bmà\b|\btuy nhiên\b|\bcó\b|\bkèm theo\b")

# --- Tiền sử --------------------------------------------------------------
_HIST_CUES = (
    "tiền sử",
    "tiền căn",
    "đã từng",
    "từng bị",
    "trước đây",
    "trước đó",
    "đã được chẩn đoán",
    "cách đây",
    "nhiều năm nay",
    "đã mắc",
    "bệnh nền",
    "bệnh lý mãn tính",
)

_HIST_BLOCKER = re.compile(r"[.;?!\n]")

# Quy tắc "cả vùng dưới heading tiền sử đều là isHistorical" đã bị GỠ BỎ.
#
# Vòng thẩm định đối kháng cho thấy nó rò rỉ nghiêm trọng: heading tiền sử ở đầu
# hồ sơ khiến toàn bộ mục "Triệu chứng hiện tại", "Khám lúc vào viện", "Đánh giá
# tại bệnh viện" phía sau cũng bị đóng dấu isHistorical, trong khi bài nền để
# assertions rỗng cho chính các khái niệm nằm cùng câu. Vì 81.6% khái niệm của
# đáp án có assertions rỗng, một luật rò rỉ như vậy làm TỤT điểm.
#
# Nay isHistorical chỉ phát khi có cue tường minh nằm sát ngay trước mention.


def _cue_hit(context: str, cues: tuple[str, ...], blocker: re.Pattern) -> bool:
    """Cue gần mention nhất phải không bị ngăn cách bởi ranh giới câu."""
    best = -1
    for cue in cues:
        idx = context.rfind(cue)
        if idx > best:
            best = idx + len(cue)
    if best < 0:
        return False
    return not blocker.search(context[best:])


def infer_assertions(text: str, start: int, end: int, etype: str) -> list[str]:
    """Assertion cho một mention mới. Mặc định là rỗng — đó là lựa chọn an toàn."""
    found: list[str] = []

    negated = _cue_hit(
        text[max(0, start - _NEG_WINDOW):start].lower(), _NEG_CUES, _NEG_BLOCKER
    )
    if negated:
        found.append("isNegated")

    # Một mention đang bị phủ định thì không đồng thời là tiền sử: vòng thẩm định
    # bắt được nhiều trường hợp gán ngược dấu kiểu "phủ nhận khó thở" + isHistorical.
    if not negated:
        hist_left = text[max(0, start - _HIST_WINDOW):start].lower()
        if _cue_hit(hist_left, _HIST_CUES, _HIST_BLOCKER):
            found.append("isHistorical")

    # isFamily cố tình không bao giờ được phát: xem docstring đầu file.
    order = {"isNegated": 0, "isHistorical": 1}
    return sorted(set(found), key=lambda a: order[a])
