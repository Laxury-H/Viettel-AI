"""Mô-đun băm nhỏ bệnh án theo cấu trúc lâm sàng Việt Nam (Section-Aware Slicing).

Giúp phân tách rõ 4 phân vùng lâm sàng:
1. HISTORY: Tiền sử, lý do vào viện, bệnh sử.
2. EXAM_PROGRESS: Khám lâm sàng, diễn biến, xét nghiệm.
3. MEDICATIONS: Đơn thuốc, y lệnh điều trị, thuốc dùng trước/trong/sau viện.
4. COUNSELING_QA: Tư vấn, hướng dẫn, lời dặn, hỏi thắc mắc Q&A ở cuối bệnh án.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Tuple, Dict, Any


# Các pattern tiêu đề phổ biến trong bệnh án Việt Nam
HISTORY_HEADERS = re.compile(
    r"(?i)(?:tiền\s+sử|lý\s+do\s+(?:vào|nhập)\s+viện|bệnh\s+sử|tiền\s+căn|hoàn\s+cảnh|triệu\s+chứng\s+cách\s+đây)"
)
EXAM_HEADERS = re.compile(
    r"(?i)(?:khám|diễn\s+biến|kết\s+quả|chẩn\s+đoán|tóm\s+tắt|thăm\s+khám|cận\s+lâm\s+sàng|xét\s+nghiệm)"
)
MEDS_HEADERS = re.compile(
    r"(?i)(?:đơn\s+thuốc|y\s+lệnh|điều\s+trị|thuốc\s+(?:trước|đã|đang|dùng|sau)|thuốc\s+khi\s+nhập\s+viện)"
)
COUNSELING_HEADERS = re.compile(
    r"(?i)(?:tư\s+vấn|hướng\s+dẫn|lời\s+dặn|câu\s+hỏi|hỏi\s+đáp|khuyên|phòng\s+ngừa|lưu\s+ý|tài\s+liệu\s+giáo\s+dục)"
)

# Lỗi dịch thuật hoặc lặp từ từng được xác nhận cần loại bỏ (như V51 hồ sơ 38)
TRANSLATION_SEAM_ARTIFACTS = {
    ("CHẨN_ĐOÁN", "đái tháo đườngđái tháo đường"),
    ("CHẨN_ĐOÁN", "tổng phân tích nước tiểu có đái tháo đườngđái tháo đường"),
}


def slice_sections(text: str) -> Dict[str, List[Tuple[int, int]]]:
    """Phân tách văn bản bệnh án thành các vùng chỉ số (start, end) cho từng phần lâm sàng."""
    lines = text.splitlines(keepends=True)
    sections: Dict[str, List[Tuple[int, int]]] = {
        "HISTORY": [],
        "EXAM_PROGRESS": [],
        "MEDICATIONS": [],
        "COUNSELING_QA": [],
    }

    current_section = "EXAM_PROGRESS" # Mặc định đầu văn bản hoặc khi chưa gặp tiêu đề
    offset = 0

    for line in lines:
        line_len = len(line)
        line_str = line.strip()

        # Kiểm tra nếu dòng là tiêu đề chuyển vùng
        if len(line_str) < 100:
            if COUNSELING_HEADERS.search(line_str):
                current_section = "COUNSELING_QA"
            elif MEDS_HEADERS.search(line_str):
                current_section = "MEDICATIONS"
            elif HISTORY_HEADERS.search(line_str):
                current_section = "HISTORY"
            elif EXAM_HEADERS.search(line_str):
                current_section = "EXAM_PROGRESS"

        sections[current_section].append((offset, offset + line_len))
        offset += line_len

    # Gộp các khoảng liên tiếp trong cùng một vùng
    merged_sections: Dict[str, List[Tuple[int, int]]] = {}
    for sec, spans in sections.items():
        if not spans:
            merged_sections[sec] = []
            continue
        merged = [list(spans[0])]
        for s, e in spans[1:]:
            if s == merged[-1][1]:
                merged[-1][1] = e
            else:
                merged.append([s, e])
        merged_sections[sec] = [(s, e) for s, e in merged]

    return merged_sections


def get_entity_section(start: int, end: int, sections: Dict[str, List[Tuple[int, int]]]) -> str:
    """Xác định thực thể tại tọa độ (start, end) thuộc vùng lâm sàng nào."""
    mid = (start + end) // 2
    for sec, spans in sections.items():
        for s, e in spans:
            if s <= mid < e:
                return sec
    return "EXAM_PROGRESS"


def prune_noise_entities(entities: Iterable[dict], text: str) -> List[dict]:
    """Cắt tỉa các thực thể lỗi dịch thuật hoặc nhiễu không mong muốn."""
    cleaned = []
    for e in entities:
        t = e["type"]
        txt = e["text"]
        norm_txt = txt.lower().strip()

        # 1. Loại bỏ các lỗi dịch ghép từ (Translation seam errors như V51)
        if (t, norm_txt) in TRANSLATION_SEAM_ARTIFACTS or "đái tháo đườngđái tháo đường" in norm_txt:
            continue

        cleaned.append(e)

    return cleaned
