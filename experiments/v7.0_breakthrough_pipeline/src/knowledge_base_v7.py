#!/usr/bin/env python3
"""Từ điển Y khoa mở rộng (Knowledge Base V7) cho V7 Breakthrough Pipeline.

Kế thừa toàn bộ danh mục tinh hoa (56 triệu chứng & chẩn đoán chuẩn, 70+ thuốc RxNorm,
xét nghiệm) từ bài DungLe, đồng thời bổ sung các từ điển mở rộng về thuốc và bệnh lý
thường gặp trong hồ sơ lâm sàng tiếng Việt để gia tăng độ phủ (Recall) và hỗ trợ
Candidate Linker đạt độ chính xác tối đa.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Thêm thư mục src gốc của DungLe vào sys.path để import chuẩn theo package
_dungle_src = Path(__file__).resolve().parents[3] / "reference_solutions" / "DungLe_41pt" / "NLP_for_hospital_report_classifier-main" / "src"
if str(_dungle_src) not in sys.path:
    sys.path.insert(0, str(_dungle_src))

try:
    from clinical_mentions.knowledge_base import (
        DIAGNOSES as _BASE_DIAGNOSES,
        LAB_TEST_PATTERNS as _BASE_LAB_TEST_PATTERNS,
        MEDICATIONS as _BASE_MEDICATIONS,
        OFFICIAL_TYPES as _BASE_OFFICIAL_TYPES,
        QUALITATIVE_RESULT as _BASE_QUALITATIVE_RESULT,
        SYMPTOMS as _BASE_SYMPTOMS,
    )
    OFFICIAL_TYPES = set(_BASE_OFFICIAL_TYPES)
    DIAGNOSES = list(_BASE_DIAGNOSES)
    MEDICATIONS = list(_BASE_MEDICATIONS)
    SYMPTOMS = list(_BASE_SYMPTOMS)
    LAB_TEST_PATTERNS = list(_BASE_LAB_TEST_PATTERNS)
    QUALITATIVE_RESULT = str(_BASE_QUALITATIVE_RESULT)
except ImportError as exc:
    raise RuntimeError(f"Không thể import package clinical_mentions từ {_dungle_src}: {exc}")

# Bổ sung các từ điển mở rộng cho V7 (Brand names, hoạt chất, liều dùng phổ biến)
EXPANDED_MEDICATIONS = [
    {"aliases": ("panadol", "efferalgan", "hapacol", "tylenol"), "code": "161"},
    {"aliases": ("amlodipine", "amlodipin", "norvasc"), "code": "17767"},
    {"aliases": ("losartan", "cozaar"), "code": "52175"},
    {"aliases": ("atorvastatin", "lipitor"), "code": "83367"},
    {"aliases": ("metformin", "glucophage"), "code": "6809"},
    {"aliases": ("gabapentin", "neurontin"), "code": "25480"},
    {"aliases": ("pantoprazole", "pantoprazol", "protonix"), "code": "40790"},
    {"aliases": ("lisinopril", "prinivil", "zestril"), "code": "29046"},
    {"aliases": ("amoxicillin", "amoxicil", "amoxil"), "code": "723"},
    {"aliases": ("ciprofloxacin", "cipro"), "code": "2551"},
    {"aliases": ("prednisone", "prednison", "deltasone"), "code": "8640"},
    {"aliases": ("clopidogrel", "plavix"), "code": "32968"},
    {"aliases": ("digoxin", "lanoxin"), "code": "3443"},
]

EXPANDED_DIAGNOSES = [
    {"aliases": ("tăng huyết áp", "cao huyết áp", "THA", "tăng HA"), "code": "I10"},
    {"aliases": ("đái tháo đường", "tiểu đường", "ĐTĐ", "ĐTD"), "code": "E11.9"},
    {"aliases": ("viêm phổi",), "code": "J18.9"},
    {"aliases": ("suy thận mạn", "bệnh thận mạn", "CKD"), "code": "N18.9"},
    {"aliases": ("viêm dạ dày", "đau dạ dày"), "code": "K29.70"},
    {"aliases": ("viêm gan B", "nhiễm HBV"), "code": "B18.1"},
    {"aliases": ("viêm gan C", "nhiễm HCV"), "code": "B18.2"},
    {"aliases": ("gút", "bệnh gout", "gout"), "code": "M10.9"},
    {"aliases": ("thoái hóa khớp", "viêm xương khớp"), "code": "M19.90"},
    {"aliases": ("viêm phế quản mạn tính", "COPD", "bệnh phổi tắc nghẽn mạn tính"), "code": "J44.9"},
]

# Gộp từ điển gốc và từ điển mở rộng
ALL_MEDICATIONS = MEDICATIONS + EXPANDED_MEDICATIONS
ALL_DIAGNOSES = DIAGNOSES + EXPANDED_DIAGNOSES
