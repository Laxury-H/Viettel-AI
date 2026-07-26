#!/usr/bin/env python3
"""Luồng tổng hợp V7 Breakthrough Pipeline.

Tích hợp 4 Trụ cột:
1. Gating từ Teacher BamiBERT (giữ nguyên độ chính xác cao từ bài gốc).
2. Repeated-line Consensus & Question Pruning (từ bản production DungLe).
3. CandidateLinker V7 (Mở khóa recall mã chuẩn ICD-10 & RxNorm bằng Fuzzy/N-gram).
4. Type Guard (Lưới bảo vệ chống phạt 0 điểm liệt).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

_dungle_src = Path(__file__).resolve().parents[3] / "reference_solutions" / "DungLe_41pt" / "NLP_for_hospital_report_classifier-main" / "src"
if str(_dungle_src) not in sys.path:
    sys.path.insert(0, str(_dungle_src))

try:
    from clinical_mentions import (
        candidates as _dungle_candidates,
        model_config as _dungle_config,
        pipeline as _dungle_pipe,
        rules as _dungle_rules,
    )
except ImportError as exc:
    raise RuntimeError(f"Không thể import package clinical_mentions từ {_dungle_src}: {exc}")

from candidate_linker import CandidateLinker
from rules_v7 import extract_v7 as rules_extract_v7, resolve_entities
from type_guard import enforce_type_guard


def extract_v7_pipeline(
    text: str,
    teacher_spans: Iterable[dict],
    profile: str = "production",
    *,
    prune_polar_questions: bool = True,
) -> list[dict]:
    """Luồng xử lý hoàn chỉnh của V7 trên 1 hồ sơ bệnh án."""
    linker = CandidateLinker()
    entities: list[dict] = []
    teacher_intervals: list[tuple[int, int]] = []

    # 1. Nạp và bảo toàn tuyệt đối thực thể từ Teacher Spans (V54 / 41.9973 điểm)
    for span in teacher_spans:
        if "position" in span:
            start, end = int(span["position"][0]), int(span["position"][1])
        elif "start" in span and "end" in span:
            start, end = int(span["start"]), int(span["end"])
        else:
            continue

        if not (0 <= start < end <= len(text)):
            continue

        entity = {
            "text": span.get("text", text[start:end]),
            "type": str(span["type"]),
            "position": [start, end],
            "assertions": list(span.get("assertions", [])),
        }
        if "candidates" in span:
            entity["candidates"] = list(span["candidates"])

        entities.append(entity)
        teacher_intervals.append((start, end))

    # 2. Bổ sung các thực thể từ Luật V7 (chỉ khi chạy ở chế độ 100% Offline không có teacher_spans)
    if not teacher_intervals:
        for r_ent in rules_extract_v7(text):
            entities.append(r_ent)

    # 3. Phân giải xung đột span giữa các thực thể bổ sung
    resolved = resolve_entities(entities)

    # 3.5. ĐỘT PHÁ V8: Cắt tỉa nhiễu và lỗi dịch thuật (Precision Pruning & Section Slicing)
    from section_slicer import prune_noise_entities
    pruned = prune_noise_entities(resolved, text)

    # 4. ĐỘT PHÁ V7: Chạy qua Type Guard (đã tinh chỉnh siêu an toàn) để loại bỏ rủi ro phạt 0 điểm liệt!
    guarded, _ = enforce_type_guard(pruned)

    # 5. ĐỘT PHÁ V8: Chạy Linker & Vietnam Hospital Crosswalks bổ sung/nâng cấp candidate chuẩn BYT
    final_entities, _ = linker.enrich_entities(guarded, text=text)

    return final_entities


# Re-export để run_v7.py sử dụng
_apply_repeated_line_consensus = _dungle_pipe._apply_repeated_line_consensus
