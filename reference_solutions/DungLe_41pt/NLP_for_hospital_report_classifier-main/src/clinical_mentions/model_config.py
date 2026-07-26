"""Configuration for the promoted V16 model and conservative ablations."""

from __future__ import annotations


MODEL_ID = "cbc-528a/BamiBERT-ViMedNER"
MODEL_REVISION = "e508eedd34d124e05cf139cc565806c6d4fc5aad"
TEACHER_CONFIDENCE_MINIMUM = 0.98


# High-precision symptoms distilled from BamiBERT disagreements.  A mention is
# still emitted only when the teacher predicts the exact span with confidence
# >= TEACHER_CONFIDENCE_MINIMUM.
PRODUCTION_SYMPTOMS: tuple[str, ...] = (
    "nhìn mờ ở cả hai mắt",
    "rỉ dịch vàng đục giống mủ",
    "khó khăn khi nhìn gần",
    "miệng thấy hơi thở mùi khó chịu",
    "tiểu tiện không tự chủ",
    "tức nặng 2 chi dưới",
    "giảm cảm giác vị thế",
    "phát ban toàn thân",
    "run giật tay chân",
    "đi lại không vững",
    "lưỡi đỏ dâu tây",
    "suy giảm tri giác",
    "suy giảm trí nhớ",
    "vàng niêm mạc",
    "mất định hướng",
    "sợ tiếng động",
    "sợ ánh sáng",
    "răng lung lay",
    "nhìn mờ",
    "co giật",
    "cứng đờ",
    "cắn lưỡi",
    "ợ nóng",
    "môi đỏ",
    "tỉnh chậm",
    "lưỡi đỏ",
    "có mủ",
    "ù tai",
    "khó tập trung",
    "đỏ mặt",
    "rỉ máu",
    "lo lắng",
    "mất thị lực",
    "căng thẳng",
    "phát ban",
    "nặng mặt",
    "họng đỏ",
    "ruồi bay",
    "khó nhìn",
    "đỏ da",
)


# Stable, specific ICD-10 aliases retained from the positive V16 diagnosis
# ablation.  Broad or ambiguous concepts from rejected experiments are absent.
PRODUCTION_DIAGNOSES: tuple[dict[str, object], ...] = (
    {"aliases": ("ung thư tuyến đại tràng",), "code": "C18.9"},
    {"aliases": ("viêm da tiếp xúc dị ứng",), "code": "L23.9"},
    {"aliases": ("viêm da tiếp xúc",), "code": "L25.9"},
    {"aliases": ("viêm teo niêm mạc dạ dày",), "code": "K29.4"},
    {"aliases": ("bệnh viêm tuỷ xương", "bệnh viêm tủy xương"), "code": "M86.9"},
    {"aliases": ("hẹp tắc mạch vành",), "code": "I25.10"},
    {"aliases": ("ung thư cổ tử cung",), "code": "C53.9"},
    {"aliases": ("suy vành mạn tính",), "code": "I25.9"},
    {"aliases": ("tai biến mạch máu não", "đột quỵ"), "code": "I63.9"},
    {"aliases": ("suy thoái võng mạc",), "code": "H35.9"},
    {"aliases": ("tắc ống dẫn trứng",), "code": "N97.1"},
    {"aliases": ("thai ngoài tử cung",), "code": "O00.9"},
    {"aliases": ("sỏi ống mật",), "code": "K80.50"},
    {"aliases": ("sỏi thận",), "code": "N20.0"},
    {"aliases": ("bệnh đa xơ cứng",), "code": "G35"},
    {"aliases": ("bệnh viêm mạch máu",), "code": "I77.6"},
    {"aliases": ("viêm xoang",), "code": "J32.9"},
    {"aliases": ("bệnhgout",), "code": "M10.9"},
    {"aliases": ("tăng HA",), "code": "I10"},
    {"aliases": ("XHTH",), "code": "K92.2"},
)


PROFILES = {
    "production": PRODUCTION_SYMPTOMS,
    "v23": PRODUCTION_SYMPTOMS,
}
