#!/usr/bin/env python3
"""Deterministic Type Guard (Lưới bảo vệ chống phạt điểm liệt) cho V7.

Theo quy tắc chấm điểm: nếu dự đoán đúng text nhưng sai type sẽ bị 0 điểm ở cả
3 metric. Module này áp dụng các luật hậu kỳ (post-processing rules) cứng dựa trên
đơn vị đo lường, từ khóa đặc trưng và cú pháp y khoa để tự động sửa chữa các lỗi
phân loại nhãn của mô hình trước khi đóng gói JSON.
"""

from __future__ import annotations

import re
from typing import Iterable


# Pattern nhận biết thuốc thông qua liều lượng, đơn vị hoặc đường dùng (ngăn nhận nhầm đơn vị nồng độ /l, /dl và số La Mã IV)
MEDICATION_PATTERN = re.compile(
    r"(?i)\b(?:\d+(?:[.,]\d+)?\s*(?:mg|ml|g|gram|mcg|µg|ug|meq|mmol|iu|viên|lọ|ống|liều)(?![/\][ldl])|"
    r"(?:tiêm|truyền|uống|dùng|thuốc|liều)\s+(?:po|iv|im|sc|sl|pr)|prn|q\d+h|daily|bid|tid|qid|qam|qhs|nebs?|nebulizer|"
    r"uống\s+\d+|tiêm\s+(?:iv|im|sc|tĩnh\s+mạch|dưới\s+da)|truyền\s+(?:tĩnh\s+mạch|iv|dịch)|sau\s+ăn)\b"
)

# Các tên thuốc quen thuộc thường gặp trong bệnh án
KNOWN_DRUGS = re.compile(
    r"(?i)\b(?:aspirin|lasix|furosemide|furosemid|paracetamol|acetaminophen|"
    r"metoprolol|amlodipine|clonazepam|pravastatin|docusate|senna|guaifenesin|"
    r"nystatin|ceftriaxone|bactrim|vancomycin|levofloxacin|coumadin|methylprednisolone|"
    r"omeprazole|losartan|atorvastatin|gabapentin|metformin|pantoprazole|lisinopril|"
    r"amoxicillin|azithromycin|ciprofloxacin|prednisone|plavix|clopidogrel|digoxin)\b"
)

# Pattern nhận biết kết quả xét nghiệm qua chỉ số định lượng có đơn vị rõ ràng
LAB_RESULT_PATTERN = re.compile(
    r"(?i)\b\d+(?:[.,]\d+)?\s*(?:mmol/l|g/dl|mg/dl|u/l|iu/l|%|fl|pg|x\s*10\^9/l|g/l|ul)\b"
)


def enforce_type_guard(entities: Iterable[dict]) -> tuple[list[dict], int]:
    """Kiểm tra và chỉnh sửa type của các thực thể để loại bỏ rủi ro bị phạt điểm liệt.

    Returns:
        tuple[list[dict], int]: Danh sách entities đã được bảo vệ và số lượng overrides.
    """
    guarded: list[dict] = []
    overrides_count = 0

    for source in entities:
        entity = dict(source)
        entity["assertions"] = list(source.get("assertions", []))
        if "candidates" in source:
            entity["candidates"] = list(source["candidates"])
        
        current_type = entity["type"]
        text = entity["text"]

        # Rule 1: Ưu tiên bảo vệ nhãn KẾT_QUẢ_XÉT_NGHIỆM (định lượng rõ ràng)
        if current_type != "KẾT_QUẢ_XÉT_NGHIỆM" and LAB_RESULT_PATTERN.search(text):
            entity["type"] = "KẾT_QUẢ_XÉT_NGHIỆM"
            entity["assertions"] = []
            entity.pop("candidates", None)
            overrides_count += 1
        # Rule 2: Bảo vệ nhãn THUỐC (khi không phải là chỉ số xét nghiệm)
        elif current_type != "THUỐC" and (MEDICATION_PATTERN.search(text) or KNOWN_DRUGS.search(text)):
            entity["type"] = "THUỐC"
            entity.pop("candidates", None)
            overrides_count += 1

        # Chuẩn hóa schema chung theo loại
        if entity["type"] in {"TÊN_XÉT_NGHIỆM", "KẾT_QUẢ_XÉT_NGHIỆM"}:
            entity["assertions"] = []
            entity.pop("candidates", None)
        elif entity["type"] == "TRIỆU_CHỨNG":
            entity.pop("candidates", None)

        guarded.append(entity)

    return guarded, overrides_count
