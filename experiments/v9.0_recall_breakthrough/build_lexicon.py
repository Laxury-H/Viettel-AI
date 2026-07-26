#!/usr/bin/env python3
"""Xây từ điển lâm sàng V9 từ kết quả khai thác corpus.

Đầu vào : mined_raw.json (danh sách entry thô do vòng khai thác corpus sinh ra)
Đầu ra  : src/lexicon_v9.json (từ điển đã kiểm duyệt, deterministic)

Bước kiểm duyệt được thiết kế quanh cấu trúc hàm chấm điểm:
  * Sai TYPE bị phạt kép (1 khái niệm bỏ sót + 1 khái niệm thừa) nên type phải
    chắc chắn hơn là phải nhiều.
  * Ngưỡng hòa vốn khi thêm khái niệm là ~0.36 nên vẫn ưu tiên độ phủ.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import unicodedata
from pathlib import Path

OFFICIAL_TYPES = {
    "TRIỆU_CHỨNG",
    "CHẨN_ĐOÁN",
    "THUỐC",
    "TÊN_XÉT_NGHIỆM",
    "KẾT_QUẢ_XÉT_NGHIỆM",
}

# Bề mặt quá chung: khớp ở khắp nơi và gần như chắc chắn lệch ranh giới gold.
_STOP_SURFACES = {
    "bệnh", "thuốc", "điều trị", "bác sĩ", "bệnh nhân", "triệu chứng",
    "chẩn đoán", "xét nghiệm", "kết quả", "tình trạng", "biến chứng",
    "nguyên nhân", "dấu hiệu", "cơn đau", "cơn", "thuốc giảm đau",
    "khám", "theo dõi", "phẫu thuật", "tổn thương", "nhiễm trùng",
    "nhiễm khuẩn", "kháng sinh", "vấn đề", "bình thường", "không",
    "tăng", "giảm", "cao", "thấp", "bất thường", "âm tính", "dương tính",
    "thuốc ức chế miễn dịch", "hormone tuyến giáp tổng hợp", "đau",
}

# Chuỗi số thuần / gần thuần: khớp lan man vào ngày tháng, liều lượng, số thứ tự.
_NUMERIC_ONLY = re.compile(r"^[\d\s.,:/%-]+$")

# Mã ICD-10 WHO hợp lệ: 1 chữ cái + 2 số, tùy chọn .x hoặc .xx
_ICD_RE = re.compile(r"^[A-TV-Z]\d{2}(?:\.\d{1,2})?$")
# RxNorm RXCUI: chuỗi số
_RXCUI_RE = re.compile(r"^\d{1,8}$")

# Độ dài bề mặt tối thiểu (ký tự) trừ khi nằm trong allowlist viết tắt.
_MIN_LEN = 4
_ABBREV_ALLOW = {
    "ct", "mri", "ecg", "ekg", "ast", "alt", "got", "gpt", "ldh", "bun",
    "crp", "esr", "inr", "hba1c", "spo2", "wbc", "rbc", "hgb", "plt",
    "egfr", "tsh", "ft4", "psa", "cea", "afp", "ck", "ckmb", "ptt", "pt",
    "na", "cl", "ca", "mg", "ure", "ercp", "mrcp", "copd",
}


def _norm(s: str) -> str:
    """Chuẩn hóa để so khớp: NFC + gộp khoảng trắng + lower."""
    s = unicodedata.normalize("NFC", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def curate(raw_entries: list[dict], texts: dict[int, str], baseline_lex: dict[str, str]):
    """Gộp phiếu bầu theo bề mặt, loại entry rủi ro, trả về từ điển + báo cáo."""
    votes: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    codes: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    confs: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    display: dict[str, str] = {}

    for entry in raw_entries:
        surface = unicodedata.normalize("NFC", str(entry.get("surface", ""))).strip()
        etype = entry.get("type")
        if not surface or etype not in OFFICIAL_TYPES:
            continue
        key = _norm(surface)
        votes[key][etype] += 1
        confs[key][entry.get("confidence", "medium")] += 1
        display.setdefault(key, surface)
        for code in entry.get("codes") or []:
            code = str(code).strip()
            if code:
                codes[key][code] += 1

    lexicon: dict[str, dict] = {}
    rejected: list[dict] = []

    def reject(key: str, reason: str) -> None:
        rejected.append({"surface": display.get(key, key), "reason": reason})

    for key, type_votes in votes.items():
        if key in _STOP_SURFACES:
            reject(key, "stop_surface")
            continue
        if _NUMERIC_ONLY.match(key):
            reject(key, "numeric_only")
            continue
        if len(key) < _MIN_LEN and key not in _ABBREV_ALLOW:
            reject(key, "too_short")
            continue
        # Baseline (bài 41.99 điểm) luôn thắng: không ghi đè nhãn đã kiểm chứng.
        if key in baseline_lex:
            reject(key, "already_in_baseline")
            continue
        # Bề mặt phải xuất hiện nguyên văn trong corpus.
        if not any(key in _norm(t) for t in texts.values()):
            reject(key, "not_grounded")
            continue

        top_type, top_n = type_votes.most_common(1)[0]
        # Xung đột type giữa các agent => bỏ, vì sai type bị phạt kép.
        if len(type_votes) > 1 and top_n == sum(type_votes.values()) / len(type_votes):
            reject(key, "type_conflict")
            continue

        entry = {"surface": display[key], "type": top_type}

        chosen: list[str] = []
        if top_type == "CHẨN_ĐOÁN":
            chosen = [c for c, _ in codes[key].most_common() if _ICD_RE.match(c)]
        elif top_type == "THUỐC":
            chosen = [c for c, _ in codes[key].most_common() if _RXCUI_RE.match(c)]
        # Gold thường chỉ có 1 mã: thêm mã thứ hai chỉ làm loãng Jaccard.
        if chosen:
            entry["codes"] = chosen[:1]

        entry["confidence"] = confs[key].most_common(1)[0][0]
        lexicon[key] = entry

    return lexicon, rejected


def main() -> None:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--mined", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=here / "src" / "lexicon_v9.json")
    parser.add_argument("--report", type=Path, default=here / "lexicon_report.json")
    args = parser.parse_args()

    raw = json.loads(args.mined.read_text(encoding="utf-8"))
    texts = {
        int(p.stem): p.read_text(encoding="utf-8")
        for p in args.input.glob("*.txt")
        if p.stem.isdigit()
    }
    baseline_lex: dict[str, str] = {}
    for path in args.baseline.glob("*.json"):
        for concept in json.loads(path.read_text(encoding="utf-8")):
            baseline_lex[_norm(concept["text"])] = concept["type"]

    lexicon, rejected = curate(raw, texts, baseline_lex)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(lexicon, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    by_type = collections.Counter(v["type"] for v in lexicon.values())
    coded = sum(1 for v in lexicon.values() if v.get("codes"))
    reasons = collections.Counter(r["reason"] for r in rejected)
    report = {
        "raw_entries": len(raw),
        "kept": len(lexicon),
        "kept_by_type": dict(by_type),
        "kept_with_codes": coded,
        "rejected": len(rejected),
        "rejected_by_reason": dict(reasons),
        "rejected_samples": rejected[:60],
    }
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"[lexicon] giữ {len(lexicon)} / {len(raw)} entry thô")
    print(f"[lexicon] theo type: {dict(by_type)}")
    print(f"[lexicon] có mã: {coded}")
    print(f"[lexicon] loại bỏ: {dict(reasons)}")
    print(f"[lexicon] -> {args.out}")


if __name__ == "__main__":
    main()
