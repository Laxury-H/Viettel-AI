#!/usr/bin/env python3
"""Bước 3 — Chuẩn hóa mã ICD-10 / RxNorm.

Đây là kênh nâng điểm DUY NHẤT còn được chứng minh là dương, nên nó cũng là
module bị ràng buộc chặt nhất.

Mô hình chấm của candidates_score đã được phân định bằng thực nghiệm:

    Bản V45 và V51 khác nhau đúng 2 khái niệm bị xóa; tập mã cấp tài liệu GIỐNG
    HỆT ở cả 100 hồ sơ, vậy mà J_candidates vẫn đổi từ 32.9413 lên 32.9653.
    Mô hình "Jaccard trên tập mã cấp tài liệu" tiên đoán thay đổi bằng 0 tuyệt
    đối, nên nó BỊ BÁC BỎ. Thực tế là Jaccard tính theo TỪNG KHÁI NIỆM rồi lấy
    trung bình.

Hệ quả trực tiếp, và nó ngược với trực giác thông thường:

    Với một khái niệm mà đáp án có đúng 1 mã, đoán thêm mã thứ hai làm Jaccard
    của khái niệm đó tụt từ 1.0 xuống 0.5. Điểm hòa vốn là q* = p/(1−p) với p là
    xác suất mã hiện tại đã đúng. Khi p ≥ 0.5 thì q* ≥ 1, tức KHÔNG THỂ hòa vốn
    dù mã thêm vào đúng 100%.

    => Module này KHÔNG BAO GIỜ thêm mã thứ hai. Nó chỉ THAY THẾ mã sai.

Ngưỡng thay thế cũng rất nghiêm, vì V47 từng đổi 94 mã theo hướng "chuẩn hóa
mức đặc hiệu" và MẤT 0.4884 điểm. Chỉ hai loại lỗi được phép sửa:
  · mã không tồn tại trong danh mục ICD-10 WHO mà Bộ Y Tế áp dụng
  · mã nhầm chương / nhầm căn nguyên so với chính nội dung của span
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ICD_RE = re.compile(r"^[A-TV-Z]\d{2}(?:\.\d{1,2})?$")
RXCUI_RE = re.compile(r"^\d{1,8}$")
CODED_TYPES = {"CHẨN_ĐOÁN", "THUỐC"}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip().lower()


class SemanticLinker:
    """Bảng thay thế mã, tra theo (type, text chuẩn hóa, mã cũ)."""

    def __init__(self, corrections_path: Path):
        raw = json.loads(Path(corrections_path).read_text(encoding="utf-8"))
        items = raw.get("confirmed", raw) if isinstance(raw, dict) else raw
        self._table: dict[tuple[str, str, str], str] = {}
        for item in items:
            etype = item.get("type")
            text = item.get("text")
            old = str(item.get("current_code", "")).strip()
            new = str(item.get("proposed_code", "")).strip()
            if etype not in CODED_TYPES or not (text and old and new) or old == new:
                continue
            pattern = ICD_RE if etype == "CHẨN_ĐOÁN" else RXCUI_RE
            if not pattern.match(new):
                continue
            self._table[(etype, _norm(text), old)] = new

    def __len__(self) -> int:
        return len(self._table)

    def relink(self, concept: dict) -> tuple[list[str], int]:
        """Trả về (danh sách mã sau chuẩn hóa, số mã đã thay).

        Số lượng mã LUÔN được giữ nguyên: chỉ thay thế, không thêm, không bớt.
        """
        codes = list(concept.get("candidates") or [])
        etype = concept.get("type")
        if etype not in CODED_TYPES or not codes:
            return codes, 0

        key_text = _norm(concept["text"])
        out: list[str] = []
        changed = 0
        for code in codes:
            repl = self._table.get((etype, key_text, str(code)))
            if repl:
                out.append(repl)
                changed += 1
            else:
                out.append(code)
        return out, changed


def load_moh_catalogue(path: Path) -> dict[str, dict]:
    """Danh mục ICD-10 chính thức theo Thông tư 06/2026/TT-BYT (15.844 mã).

    Nguồn: phụ lục Thông tư 06/2026/TT-BYT ngày 02/04/2026, hiệu lực 01/07/2026,
    tải từ datafiles.chinhphu.vn. Mỗi mã có cờ `p` = dùng được làm bệnh chính.

    Danh mục này QUAN TRỌNG vì nó bác bỏ hai ngộ nhận phổ biến:
      · Việt Nam CÓ dùng mã 5 ký tự (3.532/15.844 mã). Điều 4.2.c của Thông tư
        nhắc thẳng cụm "mã 4 hoặc 5 ký tự cụ thể hơn".
      · Mã 5 ký tự của Việt Nam KHÔNG PHẢI ICD-10-CM Hoa Kỳ. Cùng chuỗi ký tự
        nhưng khác nghĩa, đôi khi ngược nghĩa: M48.00 ở Việt Nam là "hẹp ống
        sống, NHIỀU vị trí" còn ICD-10-CM là "site UNSPECIFIED". Dùng bảng Mỹ
        để "sửa" mã Việt Nam sẽ tạo ra lỗi mới.
    """
    if not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_codes(concepts: list[dict], catalogue: dict[str, dict] | None = None) -> list[str]:
    """Soát định dạng mã, và nếu có danh mục thì soát cả sự tồn tại thực tế."""
    problems: list[str] = []
    for c in concepts:
        codes = c.get("candidates") or []
        etype = c.get("type")
        if etype not in CODED_TYPES:
            if codes:
                problems.append(f"{etype} không được mang mã: {c['text']!r}")
            continue
        for code in codes:
            if etype == "CHẨN_ĐOÁN":
                if not ICD_RE.match(code):
                    problems.append(f"mã ICD-10 sai định dạng: {code!r} ({c['text']!r})")
                elif catalogue and code not in catalogue:
                    problems.append(
                        f"mã ICD-10 KHÔNG có trong danh mục Bộ Y Tế (TT06/2026): "
                        f"{code!r} ({c['text']!r})")
            if etype == "THUỐC" and not RXCUI_RE.match(code):
                problems.append(f"mã RxNorm sai định dạng: {code!r} ({c['text']!r})")
    return problems
