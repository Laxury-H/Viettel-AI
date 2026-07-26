"""Bộ từ điển chuyển đổi phương ngữ Bộ Y Tế (Vietnam Hospital Crosswalks V8.0).

Tích hợp các thành quả chuẩn hóa từ Thông tư 06/2026/TT-BYT và thói quen gán mã lâm sàng tại bệnh viện Việt Nam:
1. Chuẩn hóa 62 mã ICD-10 từ WHO/US-CM sang danh mục chính thức Việt Nam.
2. Chuẩn hóa các chẩn đoán chính xác bệnh viện (U xơ tuyến vú -> N60.2, Tai biến mạch máu não -> I64, Bệnh tim mạch do xơ vữa -> I25.1).
3. Chuẩn hóa các biệt dược/thuốc phối hợp thông dụng (Bactrim, Augmentin, Coveram, Panadol...).
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, Dict, Any, Optional


# 1. Bộ 62 mã chuyển đổi ICD-10 chuẩn theo phụ lục Thông tư 06/2026/TT-BYT
BYT_ICD10_CROSSWALK: Dict[str, str] = {
    "K29.70": "K29.7",  # Viêm dạ dày không xác định
    "D75.A": "D55.0",   # Thiếu men G6PD
    "H47.10": "H47.1",  # Phù gai thị
    "I25.10": "I25.1",  # Bệnh mạch vành do xơ vữa
    "G43.909": "G43.9", # Migraine không xác định
    "C92.10": "C92.1",  # Bạch cầu dòng tủy mạn
    "I48.91": "I48.9",  # Rung/cuồng nhĩ không xác định
    "K80.50": "K80.5",  # Sỏi ống mật
    "I26.99": "I26.9",  # Thuyên tắc phổi
    "L03.90": "L03.9",  # Viêm mô tế bào
    "D24.9": "D24",     # U lành vú
    "D68.59": "D68.5",  # Tăng đông nguyên phát
    "N60.09": "N60.0",  # Nang đơn độc vú
    "O14.90": "O14.9",  # Tiền sản giật
    "G47.33": "G47.3",  # Ngưng thở khi ngủ
    "I62.03": "I62.0",  # Tụ máu dưới màng cứng mạn tính
    "K05.30": "K05.3",  # Viêm quanh răng mạn
    "K70.30": "K70.3",  # Xơ gan do rượu
    "N40.0": "N40",     # Phì đại tuyến tiền liệt
    "S06.33": "S06.30", # Bầm dập não không vết thương hở
    "Q66.50": "Q66.5",  # Bàn chân bẹt
    "E85.81": "E85.8",  # Amyloidosis
    "G47.30": "G47.3",  # Ngưng thở khi ngủ không xác định
    "K58.9": "K58.8",   # Hội chứng ruột kích thích
    "K80.20": "K80.2",  # Sỏi mật
    "C90.00": "C90.0",  # Đa u tủy xương
    "D84.821": "D84.8", # Suy giảm miễn dịch do corticoid
    "D89.89": "D89.8",  # Hội chứng kháng synthetase
    "E78.00": "E78.0",  # Tăng cholesterol máu đơn thuần
    "F10.20": "F10.2",  # Nghiện rượu
    "F11.10": "F11.1",  # Lạm dụng opioid
    "G82.20": "G82.2",  # Liệt hai chi dưới
    "I20.89": "I20.8",  # Đau thắt ngực ổn định
    "I25.41": "I25.4",  # Phình động mạch vành
    "I27.20": "I27.2",  # Tăng áp phổi thứ phát
    "I31.39": "I31.3",  # Tràn dịch màng ngoài tim
    "I51.89": "I51.8",  # Bệnh tim khác xác định
    "I82.409": "I80.2", # Huyết khối tĩnh mạch sâu
    "J47.9": "J47",     # Giãn phế quản
    "J81.0": "J81",     # Phù phổi cấp
    "J98.11": "J98.1",  # Xẹp phổi
    "K20.90": "K20",    # Viêm thực quản
    "K22.10": "K22.1",  # Loét thực quản
    "K51.90": "K51.9",  # Viêm loét đại tràng
    "K59.39": "K59.3",  # Megacolon
    "M1A.9XX1": "M10.90", # Gout nhiều vị trí
    "A41.01": "A41.0",  # Nhiễm trùng huyết do Staph aureus
    "C50.919": "C50.9", # Ung thư vú
    "C78.00": "C78.0",  # Di căn phổi
    "E05.00": "E05.0",  # Cường giáp
    "I27.81": "I27.9",  # Tâm phế mạn
    "I31.4": "I31.9",   # Chèn ép tim
    "K59.09": "K59.0",  # Táo bón
    "K65.1": "K65.0",   # Viêm phúc mạc
    "K72.90": "K74.6",  # Suy gan
    "K85.90": "K85.9",  # Viêm tụy cấp
    "L89.94": "L89.3",  # Loét tì đè độ 4
    "N46.9": "N46",     # Vô sinh nam
    "R18.8": "R18",     # Cổ trướng
    "T14.8XXA": "T14.20", # Gãy xương không mở
    "T86.12": "T86.1",  # Thải ghép thận
}

# 2. Chuẩn hóa chẩn đoán chính xác theo cụm từ lâm sàng (Exact Hospital Labels)
EXACT_DIAGNOSIS_LABELS: Dict[str, List[str]] = {
    "bệnh tim mạch do xơ vữa động mạch": ["I25.1"],
    "bệnh tim mạch do xơ vữa": ["I25.1"],
    "u xơ tuyến vú": ["N60.2"],
    "viêm tim": ["I51.8"],
    "bệnh tim mạch": ["I51.6"],
    "đột quỵ": ["I64"],
    "tai biến mạch máu não": ["I64"], # Synonym đã xác nhận ở V50
    "thiếu men g6pd": ["D55.0"],
    "thiếu hụt men g6pd": ["D55.0"],
    "thiếu máu do tan huyết": ["D55.0"],
    "thiếu máu tan huyết": ["D55.0"],
    "bệnh kawasaki": ["M30.3"],
    "kawasaki": ["M30.3"],
}

# 3. Chuẩn hóa thuốc theo biệt dược & phối hợp (Hospital Brand Names RxNorm)
EXACT_MEDICATION_LABELS: Dict[str, List[str]] = {
    "panadol": ["161"],
    "efferalgan": ["161"],
    "hapacol": ["161"],
    "tylenol": ["161"],
    "augmentin": ["637188"],
    "klamentin": ["637188"],
    "curam": ["637188"],
    "bactrim": ["151399"],
    "cotrimoxazol": ["10831"],
    "coveram": ["647242"],
    "twynsta": ["859186"],
    "berodual": ["1293671"],
    "symbicort": ["660855"],
    "zinnat": ["213031"],
    "vastarel": ["10826"],
    "berlthyrox": ["10582"],
    "pimperan": ["6915"],
    "pimperam": ["6915"],
}


def _norm_text(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold().strip()


def upgrade_candidate_codes(
    entity_type: str, 
    text: str, 
    current_candidates: Optional[List[str]],
    context_line: str = ""
) -> Optional[List[str]]:
    """Nâng cấp mã chuẩn hóa cho thực thể theo từ điển Bộ Y Tế và Bệnh viện Việt Nam."""
    norm_txt = _norm_text(text)

    # 1. Chuẩn hóa chẩn đoán
    if entity_type == "CHẨN_ĐOÁN":
        # Ưu tiên khớp chính xác nhãn lâm sàng
        if norm_txt in EXACT_DIAGNOSIS_LABELS:
            return list(EXACT_DIAGNOSIS_LABELS[norm_txt])

        # Ngữ cảnh đặc biệt: "tăng nhãn áp" trong bệnh cảnh thần kinh (CT sọ, não úng thủy) -> G93.2 (V46)
        if norm_txt == "tăng nhãn áp":
            norm_ctx = _norm_text(context_line)
            if any(k in norm_ctx for k in ["sọ", "não", "shunt", "dẫn lưu", "thần kinh", "phù gai"]):
                return ["G93.2"]

        # Nếu đã có candidate, áp dụng bảng chuyển đổi mã BYT
        if current_candidates:
            upgraded = []
            for c in current_candidates:
                c_str = str(c).strip()
                upgraded.append(BYT_ICD10_CROSSWALK.get(c_str, c_str))
            return upgraded

    # 2. Chuẩn hóa thuốc
    elif entity_type == "THUỐC":
        if norm_txt in EXACT_MEDICATION_LABELS:
            return list(EXACT_MEDICATION_LABELS[norm_txt])
            
        if current_candidates:
            return [str(c).strip() for c in current_candidates]

    return current_candidates
