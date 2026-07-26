#!/usr/bin/env python3
"""Kiểm tra output V9 theo đúng yêu cầu đề bài, từng file JSON một.

Kiểm tra ĐÚNG HỢP ĐỒNG (fail => chặn nộp):
  C1  đủ 100 file 1.json..100.json, mỗi file là 1 JSON array
  C2  mỗi khái niệm là object có đủ text / type / position / assertions
  C3  type thuộc đúng 5 nhãn chính thức
  C4  position = [start, end] nguyên, 0 <= start < end <= len(text)
  C5  input[start:end] == text  (bất biến quan trọng nhất)
  C6  end - start == len(text)
  C7  assertions là mảng con của {isNegated, isFamily, isHistorical}, không trùng
  C8  candidates chỉ xuất hiện ở CHẨN_ĐOÁN / THUỐC, là mảng chuỗi không rỗng
  C9  mã ICD-10 đúng định dạng WHO; RxNorm là chuỗi số
  C10 JSON serialise được, không có NaN/Infinity

Kiểm tra CẢNH BÁO (không chặn nộp, chỉ báo cáo):
  W1  span chồng lấn nhau
  W2  khái niệm trùng khít hoàn toàn (cùng span + type)
  W3  text có khoảng trắng thừa ở đầu/cuối
  W4  khái niệm dài bất thường (> 12 từ)
  W5  tài liệu có quá ít khái niệm (đòn bẩy macro bị bỏ phí)
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

OFFICIAL_TYPES = {
    "TRIỆU_CHỨNG",
    "CHẨN_ĐOÁN",
    "THUỐC",
    "TÊN_XÉT_NGHIỆM",
    "KẾT_QUẢ_XÉT_NGHIỆM",
}
CODED_TYPES = {"CHẨN_ĐOÁN", "THUỐC"}
VALID_ASSERTIONS = {"isNegated", "isFamily", "isHistorical"}

# ICD-10 WHO: 1 chữ cái (trừ U) + 2 chữ số, tùy chọn .x hoặc .xx
ICD_RE = re.compile(r"^[A-TV-Z]\d{2}(?:\.\d{1,2})?$")
RXCUI_RE = re.compile(r"^\d{1,8}$")


def validate(output_dir: Path, input_dir: Path, expected: int = 100):
    errors: list[str] = []
    warnings: list[str] = []
    stats = {
        "files": 0,
        "concepts": 0,
        "by_type": collections.Counter(),
        "assertions": collections.Counter(),
        "with_candidates": 0,
        "per_doc": {},
    }

    for idx in range(1, expected + 1):
        jpath = output_dir / f"{idx}.json"
        tpath = input_dir / f"{idx}.txt"

        if not jpath.exists():
            errors.append(f"C1 [{idx}.json] thiếu file")
            continue
        if not tpath.exists():
            errors.append(f"C1 [{idx}.txt] thiếu input tương ứng")
            continue

        text = tpath.read_text(encoding="utf-8")
        raw = jpath.read_text(encoding="utf-8")
        try:
            concepts = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"C1 [{idx}.json] JSON hỏng: {exc}")
            continue
        if not isinstance(concepts, list):
            errors.append(f"C1 [{idx}.json] phải là JSON array, đang là {type(concepts).__name__}")
            continue

        stats["files"] += 1
        stats["per_doc"][idx] = len(concepts)
        seen_spans: set[tuple] = set()
        intervals: list[tuple[int, int, str]] = []

        for pos, concept in enumerate(concepts):
            tag = f"[{idx}.json #{pos}]"

            if not isinstance(concept, dict):
                errors.append(f"C2 {tag} không phải object")
                continue
            for field in ("text", "type", "position", "assertions"):
                if field not in concept:
                    errors.append(f"C2 {tag} thiếu trường '{field}'")
            if "text" not in concept or "type" not in concept or "position" not in concept:
                continue

            ctext = concept["text"]
            ctype = concept["type"]
            cpos = concept["position"]

            if not isinstance(ctext, str) or not ctext:
                errors.append(f"C2 {tag} text rỗng hoặc không phải chuỗi")
                continue
            if ctype not in OFFICIAL_TYPES:
                errors.append(f"C3 {tag} type không hợp lệ: {ctype!r}")
                continue

            if (
                not isinstance(cpos, list)
                or len(cpos) != 2
                or not all(isinstance(v, int) and not isinstance(v, bool) for v in cpos)
            ):
                errors.append(f"C4 {tag} position phải là [int, int], đang là {cpos!r}")
                continue
            start, end = cpos
            if not (0 <= start < end <= len(text)):
                errors.append(f"C4 {tag} position ngoài phạm vi: {cpos} (len text={len(text)})")
                continue
            if text[start:end] != ctext:
                errors.append(
                    f"C5 {tag} LỆCH OFFSET: text={ctext!r} nhưng input[{start}:{end}]={text[start:end]!r}"
                )
                continue
            if end - start != len(ctext):
                errors.append(f"C6 {tag} end-start={end - start} != len(text)={len(ctext)}")

            asserts = concept.get("assertions")
            if not isinstance(asserts, list):
                errors.append(f"C7 {tag} assertions phải là mảng")
            else:
                bad = [a for a in asserts if a not in VALID_ASSERTIONS]
                if bad:
                    errors.append(f"C7 {tag} assertion không hợp lệ: {bad}")
                if len(set(asserts)) != len(asserts):
                    errors.append(f"C7 {tag} assertions bị trùng: {asserts}")
                stats["assertions"][tuple(sorted(asserts))] += 1

            if "candidates" in concept:
                cands = concept["candidates"]
                if ctype not in CODED_TYPES:
                    errors.append(f"C8 {tag} type {ctype} không được có candidates")
                elif not isinstance(cands, list) or not cands:
                    errors.append(f"C8 {tag} candidates phải là mảng không rỗng: {cands!r}")
                elif not all(isinstance(c, str) and c for c in cands):
                    errors.append(f"C8 {tag} candidates phải là mảng chuỗi: {cands!r}")
                else:
                    stats["with_candidates"] += 1
                    for code in cands:
                        if ctype == "CHẨN_ĐOÁN" and not ICD_RE.match(code):
                            errors.append(f"C9 {tag} mã ICD-10 sai định dạng: {code!r}")
                        if ctype == "THUỐC" and not RXCUI_RE.match(code):
                            errors.append(f"C9 {tag} mã RxNorm sai định dạng: {code!r}")

            if ctext != ctext.strip():
                warnings.append(f"W3 {tag} text có khoảng trắng thừa: {ctext!r}")
            if len(ctext.split()) > 12:
                warnings.append(f"W4 {tag} khái niệm dài {len(ctext.split())} từ: {ctext[:60]!r}")

            key = (start, end, ctype)
            if key in seen_spans:
                warnings.append(f"W2 {tag} trùng khít khái niệm khác: {ctext!r}")
            seen_spans.add(key)
            intervals.append((start, end, ctext))

            stats["concepts"] += 1
            stats["by_type"][ctype] += 1

        intervals.sort()
        for a, b in zip(intervals, intervals[1:]):
            if b[0] < a[1]:
                warnings.append(
                    f"W1 [{idx}.json] span chồng lấn: {a[2]!r}[{a[0]}:{a[1]}] và {b[2]!r}[{b[0]}:{b[1]}]"
                )

        if math.isnan(len(concepts)):  # pragma: no cover - phòng thủ
            errors.append(f"C10 [{idx}.json] giá trị không hợp lệ")

    for idx, n in sorted(stats["per_doc"].items(), key=lambda kv: kv[1]):
        if n < 10:
            warnings.append(f"W5 [{idx}.json] chỉ có {n} khái niệm (đòn bẩy macro đang bị bỏ phí)")

    return errors, warnings, stats


def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=here / "output_v9")
    parser.add_argument(
        "--input",
        type=Path,
        default=here.parents[1] / "data" / "raw" / "input_turn2_vong1" / "input",
    )
    parser.add_argument("--max-show", type=int, default=40)
    args = parser.parse_args()

    errors, warnings, stats = validate(args.output, args.input)

    print("=" * 66)
    print("KIỂM TRA OUTPUT V9 THEO YÊU CẦU ĐỀ BÀI")
    print("=" * 66)
    print(f"File hợp lệ        : {stats['files']}/100")
    print(f"Tổng khái niệm     : {stats['concepts']}  ({stats['concepts'] / max(stats['files'], 1):.1f}/hồ sơ)")
    print(f"Có candidates      : {stats['with_candidates']}")
    print("Phân bố type       :")
    for t, n in stats["by_type"].most_common():
        print(f"    {t:22s} {n:5d}  {100 * n / max(stats['concepts'], 1):5.1f}%")
    print("Phân bố assertions :")
    for a, n in stats["assertions"].most_common(8):
        label = ", ".join(a) if a else "(rỗng)"
        print(f"    {label:34s} {n:5d}")

    print()
    print(f"LỖI CHẶN NỘP : {len(errors)}")
    for line in errors[: args.max_show]:
        print("   ✗ " + line)
    if len(errors) > args.max_show:
        print(f"   ... còn {len(errors) - args.max_show} lỗi nữa")

    print(f"CẢNH BÁO     : {len(warnings)}")
    for line in warnings[: args.max_show]:
        print("   ! " + line)
    if len(warnings) > args.max_show:
        print(f"   ... còn {len(warnings) - args.max_show} cảnh báo nữa")

    print()
    if errors:
        print("KẾT LUẬN: CHƯA ĐẠT — phải sửa hết lỗi chặn nộp.")
        return 1
    print("KẾT LUẬN: ĐẠT — output đúng hợp đồng đề bài.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
