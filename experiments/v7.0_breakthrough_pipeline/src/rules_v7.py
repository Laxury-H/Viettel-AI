#!/usr/bin/env python3
"""Rule extraction & assertion ngữ cảnh (Rules V7) cho V7 Breakthrough Pipeline.

Kế thừa toàn bộ 900+ dòng quy tắc trích xuất deterministic lâm sàng, nhận diện
tiền sử, gia đình và phân giải xung đột span (resolve_entities) từ bài DungLe.
Đồng thời mở rộng khả năng nhận diện các nhãn mới từ từ điển V7.
"""

from __future__ import annotations

import sys
from pathlib import Path

_dungle_src = Path(__file__).resolve().parents[3] / "reference_solutions" / "DungLe_41pt" / "NLP_for_hospital_report_classifier-main" / "src"
if str(_dungle_src) not in sys.path:
    sys.path.insert(0, str(_dungle_src))

try:
    from clinical_mentions import rules as _dungle_rules
except ImportError as exc:
    raise RuntimeError(f"Không thể import module clinical_mentions.rules từ {_dungle_src}: {exc}")

from candidate_linker import CandidateLinker
from preprocessor import NormalizedText, Span

# Re-export các hàm / biến quan trọng từ _dungle_rules để sử dụng trong pipeline
OFFICIAL_TYPES = _dungle_rules.OFFICIAL_TYPES
resolve_entities = _dungle_rules.resolve_entities
make_entity = _dungle_rules.make_entity
assertions_for = _dungle_rules.assertions_for
section_states = _dungle_rules.section_states
validate_record = _dungle_rules.validate_record


def extract_v7(text: str) -> list[dict]:
    """Trích xuất thực thể theo rule gốc và làm giàu candidate bằng CandidateLinker V7.

    Returns:
        list[dict]: Danh sách thực thể được trích xuất bằng quy tắc lâm sàng.
    """
    # 1. Chạy rule extraction gốc của DungLe
    base_entities = list(_dungle_rules.extract(text))
    
    # 2. Sử dụng CandidateLinker V7 để ánh xạ mã chuẩn cho những entity chưa có code
    linker = CandidateLinker()
    enriched_entities, _ = linker.enrich_entities(base_entities)
    
    # 3. Phân giải xung đột span
    return resolve_entities(enriched_entities)
