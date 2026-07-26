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
    # Tiêu đề mục của biểu mẫu bệnh án. Bài nền (đã kiểm chứng) luôn bắt tên kỹ
    # thuật cụ thể đứng ngay sau và cố ý bỏ chữ tiêu đề.
    "thủ thuật", "chẩn đoán hình ảnh", "khám lâm sàng", "cận lâm sàng",
    "thăm dò", "thăm khám chuyên khoa", "dấu hiệu sinh tồn", "dị ứng",
    "xét nghiệm cận lâm sàng", "xét nghiệm chuyên sâu", "khám da liễu",
    "chụp chẩn đoán hình ảnh", "phim chụp", "sàng lọc sớm",
    # Danh từ chung hay bị nâng cấp nhầm thành thực thể.
    "vi khuẩn", "vi nấm", "cân nặng", "thương tổn", "khó chịu", "buồn ngủ",
    "hóa trị", "mô bệnh học", "đại thực bào", "sợi fibrin", "tử vong",
    "thuốc kháng sinh", "thuốc cản quang", "kháng sinh tĩnh mạch",
    "kháng sinh tại chỗ", "vắc xin sống", "huyết áp", "mạch", "nang",
}

# Đơn âm tiết được phép đứng một mình. Ngoài danh sách này, mọi bề mặt mới phải
# có ít nhất 2 âm tiết — xem _is_single_syllable để biết lý do.
_SINGLE_TOKEN_ALLOW = {
    "ct", "mri", "ercp", "mrcp", "ekg", "ecg", "copd", "hba1c", "spo2",
    "ast", "alt", "got", "gpt", "ldh", "bun", "crp", "esr", "inr",
    "wbc", "rbc", "hgb", "plt", "egfr", "tsh", "psa", "cea", "afp",
    "troponin", "creatinin", "creatinine", "bilirubin", "albumin",
    "glucose", "insulin", "kali", "natri", "canxi", "ure", "amylase",
    "lipase", "ferritin", "prolactin", "cortisol", "nsaid", "nsaids",
}


def _is_single_syllable(key: str) -> bool:
    """Bề mặt chỉ có một âm tiết tiếng Việt.

    Tiếng Việt viết rời từng âm tiết, nên một âm tiết đứng lẻ vẫn thỏa điều kiện
    ranh giới từ ngay cả khi nó nằm giữa một từ ghép: "mạch" khớp được bên trong
    "tĩnh mạch", "tim mạch", "động mạch vành"; "nang" khớp trong "nang lông".
    Vòng thẩm định đối kháng cho thấy đây là nguồn lỗi span nghiêm trọng nhất,
    và mỗi lần như vậy còn kèm sai nhãn nên bị phạt kép.
    """
    return len(key.split()) < 2 and key not in _SINGLE_TOKEN_ALLOW

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


_CONF_RANK = {"low": 0, "medium": 1, "high": 2}


def curate(
    raw_entries: list[dict],
    texts: dict[int, str],
    baseline_lex: dict[str, str],
    *,
    min_confidence: str = "medium",
):
    """Gộp phiếu bầu theo bề mặt, loại entry rủi ro, trả về từ điển + báo cáo.

    min_confidence: sàn độ tin cậy. Ngưỡng hòa vốn khi thêm một khái niệm là
    ~0.43 (0.5 cho WER, ~0.36 cho assertions, còn candidates chấm theo tập mã
    cấp tài liệu nên không hưởng lợi từ triệu chứng). Entry 'low' hiếm khi vượt
    ngưỡng đó nên mặc định bị loại.
    """
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

    floor = _CONF_RANK[min_confidence]

    for key, type_votes in votes.items():
        best_conf = max(_CONF_RANK.get(c, 1) for c in confs[key])
        if best_conf < floor:
            reject(key, "below_confidence_floor")
            continue
        if key in _STOP_SURFACES:
            reject(key, "stop_surface")
            continue
        if _NUMERIC_ONLY.match(key):
            reject(key, "numeric_only")
            continue
        if len(key) < _MIN_LEN and key not in _ABBREV_ALLOW:
            reject(key, "too_short")
            continue
        if _is_single_syllable(key):
            reject(key, "single_syllable")
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
    parser.add_argument("--mined", type=Path, nargs="+", required=True,
                        help="Một hoặc nhiều file entry thô; gộp theo thứ tự truyền vào.")
    parser.add_argument("--codes", type=Path, default=None,
                        help="File entry chỉ mang mã ICD/RxNorm, dùng để bổ sung mã cho mục đã có.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--min-confidence", choices=("low", "medium", "high"), default="medium")
    parser.add_argument("--drop", type=Path, default=None,
                        help="File JSON {drop:[{surface}], retype:[{surface,correct_type}]} từ vòng thẩm định đối kháng.")
    parser.add_argument("--out", type=Path, default=here / "src" / "lexicon_v9.json")
    parser.add_argument("--report", type=Path, default=here / "lexicon_report.json")
    args = parser.parse_args()

    raw: list[dict] = []
    for path in args.mined:
        raw.extend(json.loads(path.read_text(encoding="utf-8")))
    texts = {
        int(p.stem): p.read_text(encoding="utf-8")
        for p in args.input.glob("*.txt")
        if p.stem.isdigit()
    }
    baseline_lex: dict[str, str] = {}
    for path in args.baseline.glob("*.json"):
        for concept in json.loads(path.read_text(encoding="utf-8")):
            baseline_lex[_norm(concept["text"])] = concept["type"]

    lexicon, rejected = curate(
        raw, texts, baseline_lex, min_confidence=args.min_confidence
    )

    # Áp kết quả thẩm định đối kháng: loại mục bị bác, sửa mục sai type.
    dropped_by_audit = 0
    retyped_by_audit = 0
    if args.drop and args.drop.exists():
        audit = json.loads(args.drop.read_text(encoding="utf-8"))
        for item in audit.get("retype") or []:
            key = _norm(str(item.get("surface", "")))
            correct = item.get("correct_type")
            if key in lexicon and correct in OFFICIAL_TYPES:
                if lexicon[key]["type"] != correct:
                    lexicon[key]["type"] = correct
                    # Mã cũ thuộc về type cũ, không còn hợp lệ sau khi đổi nhãn.
                    lexicon[key].pop("codes", None)
                    retyped_by_audit += 1
        for item in audit.get("drop") or []:
            key = _norm(str(item.get("surface", "")))
            if lexicon.pop(key, None) is not None:
                rejected.append({"surface": item.get("surface"), "reason": "audit_drop"})
                dropped_by_audit += 1

    # Bổ sung mã cho các mục đã nằm trong từ điển nhưng còn thiếu candidates.
    code_added = 0
    if args.codes and args.codes.exists():
        for entry in json.loads(args.codes.read_text(encoding="utf-8")):
            key = _norm(str(entry.get("surface", "")))
            target = lexicon.get(key)
            if not target or target.get("codes"):
                continue
            pattern = _ICD_RE if target["type"] == "CHẨN_ĐOÁN" else _RXCUI_RE
            valid = [c for c in (entry.get("codes") or []) if pattern.match(str(c).strip())]
            if valid:
                target["codes"] = [str(valid[0]).strip()]
                code_added += 1

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
        "codes_backfilled": code_added,
        "min_confidence": args.min_confidence,
        "audit_dropped": dropped_by_audit,
        "audit_retyped": retyped_by_audit,
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
