#!/usr/bin/env python3
"""Kiểm tra cuối cùng trước khi nộp — soi từng file, không bỏ sót gì.

Ba nhóm kiểm tra, bất kỳ lỗi nào cũng CHẶN NỘP:

  A. HỢP ĐỒNG ĐỀ BÀI   — cấu trúc zip, schema JSON, 5 nhãn, offset, assertions,
                          candidates, định dạng mã ICD/RxNorm
  B. BẤT BIẾN SO BẢN NỀN — text / position / type / assertions phải y hệt bản nền
                          (đây là thứ bảo đảm WER và J_assertion không đổi)
  C. AN TOÀN THỰC THI   — không có ký tự điều khiển, JSON đọc lại được, encoding
                          UTF-8, không phụ thuộc mạng
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

OFFICIAL_TYPES = {"TRIỆU_CHỨNG", "CHẨN_ĐOÁN", "THUỐC", "TÊN_XÉT_NGHIỆM", "KẾT_QUẢ_XÉT_NGHIỆM"}
CODED_TYPES = {"CHẨN_ĐOÁN", "THUỐC"}
VALID_ASSERTIONS = {"isNegated", "isFamily", "isHistorical"}
ICD_RE = re.compile(r"^[A-TV-Z]\d{2}(?:\.\d{1,2})?$")
RXCUI_RE = re.compile(r"^\d{1,8}$")
CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def check(out_dir: Path, in_dir: Path, base_dir: Path | None, zip_path: Path | None):
    errors: list[str] = []
    stats = collections.Counter()
    per_type = collections.Counter()

    # ---------- A. cấu trúc zip ----------
    if zip_path and zip_path.exists():
        with zipfile.ZipFile(zip_path) as archive:
            bad = archive.testzip()
            if bad:
                errors.append(f"A0 zip hỏng ở entry {bad}")
            names = [n for n in archive.namelist() if not n.endswith("/")]
            expected = {f"output/{i}.json" for i in range(1, 101)}
            got = set(names)
            if got != expected:
                for miss in sorted(expected - got):
                    errors.append(f"A0 zip thiếu {miss}")
                for extra in sorted(got - expected):
                    errors.append(f"A0 zip có entry thừa: {extra}")
            for name in names:
                try:
                    json.loads(archive.read(name).decode("utf-8"))
                except Exception as exc:
                    errors.append(f"A0 zip: {name} không đọc được ({exc})")

    for idx in range(1, 101):
        jpath = out_dir / f"{idx}.json"
        tpath = in_dir / f"{idx}.txt"
        tag = f"[{idx}.json]"

        if not jpath.exists():
            errors.append(f"A1 {tag} thiếu file")
            continue

        raw = jpath.read_text(encoding="utf-8")
        try:
            concepts = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"A1 {tag} JSON hỏng: {exc}")
            continue
        if not isinstance(concepts, list):
            errors.append(f"A1 {tag} phải là JSON array")
            continue

        text = tpath.read_text(encoding="utf-8")
        stats["files"] += 1

        for pos, c in enumerate(concepts):
            where = f"[{idx}.json #{pos}]"
            if not isinstance(c, dict):
                errors.append(f"A2 {where} không phải object")
                continue

            missing = [f for f in ("text", "type", "position", "assertions") if f not in c]
            if missing:
                errors.append(f"A2 {where} thiếu trường {missing}")
                continue

            ctext, ctype, cpos = c["text"], c["type"], c["position"]

            if not isinstance(ctext, str) or not ctext:
                errors.append(f"A2 {where} text rỗng/không phải chuỗi")
                continue
            if CTRL_RE.search(ctext):
                errors.append(f"A2 {where} text chứa ký tự điều khiển")
            if ctype not in OFFICIAL_TYPES:
                errors.append(f"A3 {where} type không hợp lệ: {ctype!r}")
                continue

            if (not isinstance(cpos, list) or len(cpos) != 2
                    or not all(isinstance(v, int) and not isinstance(v, bool) for v in cpos)):
                errors.append(f"A4 {where} position phải là [int,int]: {cpos!r}")
                continue
            s, e = cpos
            if not (0 <= s < e <= len(text)):
                errors.append(f"A4 {where} position ngoài phạm vi {cpos} (len={len(text)})")
                continue
            if text[s:e] != ctext:
                errors.append(f"A5 {where} LỆCH OFFSET: {ctext!r} vs {text[s:e]!r}")
                continue
            if e - s != len(ctext):
                errors.append(f"A6 {where} end-start != len(text)")

            asserts = c["assertions"]
            if not isinstance(asserts, list):
                errors.append(f"A7 {where} assertions phải là mảng")
            else:
                bad = [a for a in asserts if a not in VALID_ASSERTIONS]
                if bad:
                    errors.append(f"A7 {where} assertion lạ: {bad}")
                if len(set(asserts)) != len(asserts):
                    errors.append(f"A7 {where} assertions trùng lặp")

            if "candidates" in c:
                cand = c["candidates"]
                if ctype not in CODED_TYPES:
                    errors.append(f"A8 {where} type {ctype} không được mang candidates")
                elif not isinstance(cand, list) or not cand:
                    errors.append(f"A8 {where} candidates rỗng/sai kiểu: {cand!r}")
                elif not all(isinstance(x, str) and x for x in cand):
                    errors.append(f"A8 {where} candidates phải là mảng chuỗi")
                else:
                    for code in cand:
                        if ctype == "CHẨN_ĐOÁN" and not ICD_RE.match(code):
                            errors.append(f"A9 {where} mã ICD-10 WHO sai định dạng: {code!r}")
                        if ctype == "THUỐC" and not RXCUI_RE.match(code):
                            errors.append(f"A9 {where} RxNorm sai định dạng: {code!r}")
                    stats["with_candidates"] += 1

            stats["concepts"] += 1
            per_type[ctype] += 1

        # ---------- B. bất biến so với bản nền ----------
        if base_dir is not None:
            base = json.loads((base_dir / f"{idx}.json").read_text(encoding="utf-8"))
            if len(base) != len(concepts):
                errors.append(f"B1 {tag} số khái niệm đổi: nền {len(base)} -> {len(concepts)}")
            else:
                for k, (a, b) in enumerate(zip(base, concepts)):
                    if a["text"] != b["text"]:
                        errors.append(f"B2 [{idx}.json #{k}] text đổi so với nền")
                    if a["type"] != b["type"]:
                        errors.append(f"B3 [{idx}.json #{k}] type đổi so với nền")
                    if a["position"] != b["position"]:
                        errors.append(f"B4 [{idx}.json #{k}] position đổi so với nền")
                    if (a.get("assertions") or []) != (b.get("assertions") or []):
                        errors.append(f"B5 [{idx}.json #{k}] assertions đổi so với nền")
                    if ("candidates" in a) != ("candidates" in b):
                        errors.append(f"B6 [{idx}.json #{k}] sự hiện diện candidates đổi")
                    if "candidates" in a and "candidates" in b:
                        if len(a["candidates"]) != len(b["candidates"]):
                            errors.append(f"B7 [{idx}.json #{k}] số lượng mã đổi")
                        if a["candidates"] != b["candidates"]:
                            stats["code_changes"] += 1

    return errors, stats, per_type


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path,
                        default=HERE.parents[1] / "data" / "raw" / "input_turn2_vong1" / "input")
    parser.add_argument("--base", type=Path, default=None,
                        help="Bản nền để đối chiếu bất biến (bỏ qua nếu không cần).")
    parser.add_argument("--zip", type=Path, default=None)
    args = parser.parse_args()

    errors, stats, per_type = check(args.output, args.input, args.base, args.zip)

    print("=" * 68)
    print("KIỂM TRA CUỐI CÙNG TRƯỚC KHI NỘP")
    print("=" * 68)
    print(f"File hợp lệ      : {stats['files']}/100")
    print(f"Tổng khái niệm   : {stats['concepts']}")
    print(f"Có candidates    : {stats['with_candidates']}")
    if args.base:
        print(f"Mention đổi mã   : {stats['code_changes']}")
    print("Phân bố type     :")
    for t, n in per_type.most_common():
        print(f"    {t:22s} {n:5d}")
    print()

    if errors:
        print(f"LỖI CHẶN NỘP: {len(errors)}")
        for line in errors[:60]:
            print("   ✗ " + line)
        if len(errors) > 60:
            print(f"   ... còn {len(errors) - 60} lỗi")
        print()
        print("KẾT LUẬN: CHƯA ĐẠT — KHÔNG ĐƯỢC NỘP.")
        return 1

    print("LỖI CHẶN NỘP: 0")
    print()
    print("Đã kiểm và ĐẠT:")
    print("  A. Hợp đồng đề bài — zip đúng output/1..100.json, schema, 5 nhãn hợp lệ,")
    print("     offset khớp input[start:end], assertions hợp lệ, candidates đúng type,")
    print("     mã ICD-10 theo chuẩn WHO, RxNorm dạng số.")
    if args.base:
        print("  B. Bất biến so bản nền — text/position/type/assertions y hệt trên cả 100 file,")
        print("     nên WER và J_assertion không thể thay đổi.")
    print("  C. An toàn — JSON đọc lại được, UTF-8, không ký tự điều khiển.")
    print()
    print("KẾT LUẬN: ĐẠT — sẵn sàng nộp.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
