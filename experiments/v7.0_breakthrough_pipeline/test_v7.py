#!/usr/bin/env python3
"""Bộ kiểm thử unit test cho V7 Breakthrough Pipeline.

Verify các cơ chế trọng tâm:
1. CandidateLinker (ánh xạ mã RxNorm & ICD-10 chính xác).
2. Type Guard (bảo vệ chống phạt 0 điểm liệt).
3. Offset integrity (tọa độ position trùng khớp 100% văn bản).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Thêm src vào sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from candidate_linker import CandidateLinker
from rules_v7 import extract_v7
from type_guard import enforce_type_guard


def test_candidate_linker() -> None:
    print("--- [Test 1] Testing CandidateLinker ---")
    linker = CandidateLinker()
    
    # 1. Override chính xác
    res1 = linker.link_medication("aspirin 325 mg")
    assert "212033" in res1, f"Expected 212033, got {res1}"
    print("  [✓] Aspirin 325 mg override -> 212033")
    
    # 2. Fuzzy / N-gram matching
    res2 = linker.link_medication("amlodipine 10 mg po daily")
    assert "17767" in res2 or "308135" in res2, f"Expected amlodipine code, got {res2}"
    print(f"  [✓] Amlodipine fuzzy match -> {res2}")
    
    res3 = linker.link_diagnosis("bệnh nhân bị đái tháo đường typ II")
    assert "E11.9" in res3, f"Expected E11.9, got {res3}"
    print(f"  [✓] Đái tháo đường typ II match -> {res3}")


def test_type_guard() -> None:
    print("\n--- [Test 2] Testing Type Guard ---")
    fake_entities = [
        {
            "text": "lasix 40 mg po daily",
            "type": "TRIỆU_CHỨNG",  # Nhãn sai, dễ bị phạt điểm liệt
            "position": [10, 30],
            "assertions": [],
        },
        {
            "text": "138 mmol/l",
            "type": "CHẨN_ĐOÁN",  # Nhãn sai
            "position": [50, 60],
            "assertions": [],
        },
        {
            "text": "đau đầu dữ dội",
            "type": "TRIỆU_CHỨNG",  # Nhãn đúng
            "position": [70, 84],
            "assertions": [],
        },
    ]
    
    guarded, count = enforce_type_guard(fake_entities)
    assert count == 2, f"Expected 2 overrides, got {count}"
    assert guarded[0]["type"] == "THUỐC", f"Expected THUỐC, got {guarded[0]['type']}"
    assert guarded[1]["type"] == "KẾT_QUẢ_XÉT_NGHIỆM", f"Expected KẾT_QUẢ_XÉT_NGHIỆM, got {guarded[1]['type']}"
    assert guarded[2]["type"] == "TRIỆU_CHỨNG", f"Expected TRIỆU_CHỨNG, got {guarded[2]['type']}"
    print("  [✓] Type Guard successfully corrected 2 misclassified entities!")


def test_extract_v7_offset_integrity() -> None:
    print("\n--- [Test 3] Testing Extraction & Offset Integrity ---")
    sample_text = (
        "Bệnh nhân nam 65 tuổi, tiền sử đái tháo đường typ II và tăng huyết áp. "
        "Nhập viện vì khó thở khi gắng sức. "
        "Chỉ định điều trị: Aspirin 81 mg po daily và Amlodipine 5 mg po daily."
    )
    
    entities = extract_v7(sample_text)
    print(f"  Extracted {len(entities)} entities from sample text.")
    
    for e in entities:
        start, end = e["position"]
        sliced_text = sample_text[start:end]
        assert sliced_text == e["text"], f"Offset mismatch: sliced '{sliced_text}' != entity '{e['text']}'"
        print(f"  [✓] Offset check OK: [{start}, {end}] -> '{e['text']}' ({e['type']}) | Candidates: {e.get('candidates', [])}")


if __name__ == "__main__":
    test_candidate_linker()
    test_type_guard()
    test_extract_v7_offset_integrity()
    print("\n[✓] ALL UNIT TESTS PASSED FOR V7 BREAKTHROUGH PIPELINE!")
