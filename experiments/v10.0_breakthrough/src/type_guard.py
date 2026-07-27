#!/usr/bin/env python3
"""Bước 5 — Lớp khiên chống lỗi phạt điểm liệt.

Đề bài: đoán đúng text nhưng SAI TYPE thì khái niệm bị tính hai lần và mỗi lần
đều 0 điểm trên cả ba metric. Đây là lỗi đắt nhất của hệ thống, nên module này
thà bỏ một khái niệm còn hơn để nó ra ngoài với nhãn đáng ngờ.

Nguyên tắc: chỉ can thiệp khi tín hiệu bề mặt CHẮC CHẮN, và chỉ theo hướng làm
khái niệm biến mất hoặc về đúng nhãn hiển nhiên. Không đoán mò.
"""

from __future__ import annotations

import re

OFFICIAL_TYPES = {
    "TRIỆU_CHỨNG", "CHẨN_ĐOÁN", "THUỐC", "TÊN_XÉT_NGHIỆM", "KẾT_QUẢ_XÉT_NGHIỆM",
}
CODED_TYPES = {"CHẨN_ĐOÁN", "THUỐC"}

# Liều lượng + đường dùng: dấu hiệu gần như chắc chắn của một mention THUỐC.
_DOSE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|µg|g|ml|l|iu|ui|đvqt)\b"
    r"|\b(?:po|iv|im|sc|sl|pr|prn|bid|tid|qid|qd|qhs|qam|q\d+h)\b",
    re.I,
)

# Tiêu đề mục của biểu mẫu bệnh án — không bao giờ là khái niệm y khoa.
_SECTION_HEADINGS = {
    "thủ thuật", "chẩn đoán hình ảnh", "khám lâm sàng", "cận lâm sàng",
    "thăm dò", "thăm khám chuyên khoa", "dấu hiệu sinh tồn", "dị ứng",
    "xét nghiệm", "kết quả", "chẩn đoán", "điều trị", "tiền sử",
    "bệnh sử", "y lệnh", "diễn biến",
}

# Danh từ chung hay bị nâng nhầm thành thực thể.
_GENERIC = {
    "bệnh", "thuốc", "bác sĩ", "bệnh nhân", "triệu chứng", "tình trạng",
    "biến chứng", "nguyên nhân", "dấu hiệu", "vấn đề", "tổn thương",
    "vi khuẩn", "vi nấm", "cân nặng", "thương tổn", "khó chịu",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def apply(concepts: list[dict], protected: set[tuple]) -> tuple[list[dict], list[str]]:
    """Lọc và sửa nhãn. `protected` là các khái niệm kế thừa, không bao giờ đụng tới.

    Trả về (danh sách đã lọc, nhật ký thao tác).
    """
    kept: list[dict] = []
    log: list[str] = []

    for c in concepts:
        key = (c["position"][0], c["position"][1], c["type"], c["text"])
        if key in protected:
            kept.append(c)
            continue

        surface = _norm(c["text"])
        etype = c["type"]

        if etype not in OFFICIAL_TYPES:
            log.append(f"bỏ (type lạ {etype!r}): {c['text']!r}")
            continue
        if surface in _SECTION_HEADINGS:
            log.append(f"bỏ (tiêu đề mục): {c['text']!r}")
            continue
        if surface in _GENERIC:
            log.append(f"bỏ (danh từ chung): {c['text']!r}")
            continue

        # Có liều lượng/đường dùng mà không phải THUỐC => nhãn gần như chắc sai.
        if _DOSE.search(c["text"]) and etype != "THUỐC":
            log.append(f"bỏ (có liều nhưng nhãn {etype}): {c['text']!r}")
            continue

        # Ba nhãn không mang mã thì tuyệt đối không được có candidates.
        if etype not in CODED_TYPES and c.get("codes"):
            c = dict(c)
            c["codes"] = []
            log.append(f"gỡ mã khỏi {etype}: {c['text']!r}")

        kept.append(c)

    return kept, log
