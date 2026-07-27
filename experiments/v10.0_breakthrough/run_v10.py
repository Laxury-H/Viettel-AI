#!/usr/bin/env python3
"""V10 Breakthrough Pipeline — Vietnamese Clinical NER & ICD/RxNorm Linking.

Luồng 5 bước, chạy 100% offline trên CPU, không gọi API, không nạp model:

    Bước 1  sections.slice_sections      băm vùng bệnh án
    Bước 2  matcher.Matcher              dò từ điển (NFC/NFD + ranh giới âm tiết)
    Bước 3  semantic_linker.SemanticLinker  chuẩn hóa mã ICD-10 / RxNorm
    Bước 4  sections.infer_assertions    suy luận assertion theo phạm vi câu
    Bước 5  type_guard.apply             lớp khiên chống phạt điểm liệt

CHÍNH SÁCH MẶC ĐỊNH ĐƯỢC ĐẶT THEO ĐIỂM THẬT, KHÔNG THEO TRỰC GIÁC
-----------------------------------------------------------------
Bước 2 (bổ sung khái niệm) MẶC ĐỊNH TẮT. Ba thí nghiệm có kiểm soát đã đo:

    v9  thêm 275 khái niệm (precision đo được 32%)   ->  -0.1732 điểm
    v64 thêm 11 khái niệm vào 4 hồ sơ thưa           ->  -0.3956 điểm
    V48 thêm 15 khái niệm "đúng nhãn ICD chính thức" ->  -0.1813 điểm

Nguyên nhân đã truy được: WER tính macro theo hồ sơ với mẫu số là số TỪ của đáp
án trong chính hồ sơ đó. Hồ sơ thưa có mẫu số rất nhỏ nên vài từ chèn thêm đủ đẩy
WER hồ sơ đó vượt 100%, mà mỗi hồ sơ luôn nặng đúng 1% điểm.

Ngược lại, bước 3 (chỉ sửa mã) là kênh duy nhất được chứng minh dương: V63 sửa
19 mã và được +0.1814. Khi bước 2 tắt, WER và J_assertion bất biến theo thiết kế.

Bật bổ sung khái niệm bằng --enable-recall nếu muốn thử nghiệm; hãy nộp nó như
một giả thuyết riêng, đừng gộp với thay đổi mã.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from matcher import Matcher                                    # noqa: E402
from sections import infer_assertions, section_at, slice_sections  # noqa: E402
from semantic_linker import (                                  # noqa: E402
    SemanticLinker, load_moh_catalogue, validate_codes)
import type_guard                                              # noqa: E402

CODED_TYPES = {"CHẨN_ĐOÁN", "THUỐC"}
# Vùng bị cấm bổ sung khái niệm: văn tư vấn/hỏi đáp chứa nhiều câu chung chung.
RECALL_FORBIDDEN_SECTIONS = {"COUNSELING"}


def load_baseline(path: Path) -> dict[int, list[dict]]:
    """Nạp bài nền (teacher). Chấp nhận thư mục JSON hoặc file zip."""
    out: dict[int, list[dict]] = {}
    if path.is_dir():
        for f in path.glob("*.json"):
            if f.stem.isdigit():
                out[int(f.stem)] = json.loads(f.read_text(encoding="utf-8"))
    elif path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.endswith(".json"):
                    stem = Path(name).stem
                    if stem.isdigit():
                        out[int(stem)] = json.loads(archive.read(name).decode("utf-8"))
    return out


def normalize_inherited(concepts: list[dict], text: str) -> list[dict]:
    """Sao chép nguyên trạng khái niệm kế thừa, loại bản ghi lệch offset."""
    kept: list[dict] = []
    for c in concepts:
        pos = c.get("position")
        if not pos or len(pos) != 2:
            continue
        s, e = int(pos[0]), int(pos[1])
        if not (0 <= s < e <= len(text)) or text[s:e] != c.get("text"):
            continue
        item = {
            "text": c["text"],
            "type": c["type"],
            "position": [s, e],
            "assertions": list(c.get("assertions") or []),
        }
        if c["type"] in CODED_TYPES and c.get("candidates"):
            item["candidates"] = list(c["candidates"])
        kept.append(item)
    return kept


def process(text: str, baseline: list[dict], matcher: Matcher | None,
            linker: SemanticLinker) -> tuple[list[dict], dict]:
    stats = {"added": 0, "relinked": 0, "guard_dropped": 0}

    # --- Bước 1: băm vùng ---
    spans = slice_sections(text)

    # Bài nền là bất biến: giữ nguyên từng ký tự.
    concepts = normalize_inherited(baseline, text)
    protected = {(c["position"][0], c["position"][1], c["type"], c["text"])
                 for c in concepts}

    # --- Bước 2: bổ sung khái niệm (mặc định TẮT) ---
    if matcher is not None:
        blocked = [False] * len(text)
        for c in concepts:
            for p in range(c["position"][0], c["position"][1]):
                blocked[p] = True

        for hit in matcher.find(text, blocked):
            if section_at(spans, hit["position"][0]) in RECALL_FORBIDDEN_SECTIONS:
                continue
            new = {
                "text": hit["text"],
                "type": hit["type"],
                "position": hit["position"],
                # --- Bước 4: assertion cho khái niệm mới ---
                "assertions": infer_assertions(text, hit["position"][0], hit["position"][1]),
            }
            if hit["type"] in CODED_TYPES and hit["codes"]:
                new["candidates"] = list(hit["codes"])
            concepts.append(new)
            stats["added"] += 1

    # --- Bước 5: type guard ---
    before = len(concepts)
    concepts, _ = type_guard.apply(concepts, protected)
    stats["guard_dropped"] = before - len(concepts)

    # --- Bước 3: chuẩn hóa mã ---
    for c in concepts:
        if c.get("candidates"):
            codes, changed = linker.relink(c)
            c["candidates"] = codes
            stats["relinked"] += changed

    concepts.sort(key=lambda c: (c["position"][0], -c["position"][1], c["type"]))
    return concepts, stats


def main() -> int:
    parser = argparse.ArgumentParser(description="V10 Breakthrough Pipeline")
    parser.add_argument("--input", type=Path,
                        default=HERE.parents[1] / "data" / "raw" / "input_turn2_vong1" / "input")
    parser.add_argument("--baseline", type=Path, default=HERE / "baseline",
                        help="Bài nền (teacher). Thư mục JSON hoặc file zip.")
    parser.add_argument("--lexicon", type=Path, default=HERE / "src" / "data" / "lexicon.json")
    parser.add_argument("--corrections", type=Path,
                        default=HERE / "src" / "data" / "code_corrections.json")
    parser.add_argument("--output", type=Path, default=HERE / "output")
    parser.add_argument("--zip", type=Path, default=HERE / "output.zip")
    parser.add_argument("--moh-catalogue", type=Path,
                        default=HERE / "src" / "data" / "icd10_vn_tt06.json",
                        help="Danh mục ICD-10 chính thức TT06/2026/TT-BYT dùng làm cổng kiểm tra.")
    parser.add_argument("--enable-recall", action="store_true",
                        help="Bật bổ sung khái niệm. Mặc định TẮT: xem docstring đầu file.")
    args = parser.parse_args()

    t0 = time.time()

    baseline = load_baseline(args.baseline)
    if not baseline:
        print(f"LỖI: không nạp được bài nền từ {args.baseline}", file=sys.stderr)
        return 1

    linker = SemanticLinker(args.corrections)
    catalogue = load_moh_catalogue(args.moh_catalogue)

    matcher = None
    if args.enable_recall:
        lexicon = json.loads(args.lexicon.read_text(encoding="utf-8"))
        matcher = Matcher(lexicon)

    args.output.mkdir(parents=True, exist_ok=True)
    for stale in args.output.glob("*.json"):
        stale.unlink()

    total = {"added": 0, "relinked": 0, "guard_dropped": 0}
    n_concepts = 0
    problems: list[str] = []

    sources = sorted(args.input.glob("*.txt"), key=lambda p: int(p.stem) if p.stem.isdigit() else 10**9)
    for src in sources:
        if not src.stem.isdigit():
            continue
        idx = int(src.stem)
        text = src.read_text(encoding="utf-8")

        concepts, stats = process(text, baseline.get(idx, []), matcher, linker)
        for k in total:
            total[k] += stats[k]
        n_concepts += len(concepts)

        # Bất biến bắt buộc: mọi span phải trỏ đúng vào văn bản gốc.
        for c in concepts:
            s, e = c["position"]
            assert text[s:e] == c["text"], f"hồ sơ {idx}: lệch offset"
        problems.extend(f"[{idx}] {p}" for p in validate_codes(concepts, catalogue))

        (args.output / f"{idx}.json").write_text(
            json.dumps(concepts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.zip.exists():
        args.zip.unlink()
    # Timestamp cố định để chạy lại cho ra zip byte-identical (yêu cầu tái lập).
    with zipfile.ZipFile(args.zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for src in sources:
            if not src.stem.isdigit():
                continue
            info = zipfile.ZipInfo(f"output/{src.stem}.json", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, (args.output / f"{src.stem}.json").read_bytes())

    dt = time.time() - t0
    print(f"[V10] {len(sources)} hồ sơ | {n_concepts} khái niệm | {dt:.2f}s")
    print(f"[V10] bổ sung khái niệm : {total['added']}"
          f"{'' if args.enable_recall else '  (TẮT theo mặc định)'}")
    print(f"[V10] mã được chuẩn hóa : {total['relinked']}")
    print(f"[V10] type guard loại bỏ: {total['guard_dropped']}")
    if problems:
        print(f"[V10] CẢNH BÁO {len(problems)} vấn đề định dạng mã:")
        for p in problems[:10]:
            print("        " + p)
        return 1
    print(f"[V10] mã ICD: hợp lệ toàn bộ, đối chiếu danh mục BYT {len(catalogue)} mã")
    print(f"[V10] zip: {args.zip}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
