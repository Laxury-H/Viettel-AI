#!/usr/bin/env python3
"""V65 — bổ sung khái niệm CHỈ vào các hồ sơ đang bị phủ kém.

Bài học từ lượt nộp v9-conservative (41.8241, thua bài nền 41.9973):

  Ngưỡng hòa vốn khi thêm một khái niệm KHÔNG phải hằng số. Với một hồ sơ đang
  có J_assertion = J, thêm một khái niệm đúng làm tử số tăng ā còn mẫu số giữ
  nguyên (khái niệm đó vốn đã nằm trong hợp dưới dạng gold chưa khớp); thêm một
  khái niệm sai làm mẫu số tăng 1. Cân bằng tại:

      p* = J / (J + ā)

  Hồ sơ phủ kém (J ≈ 0.08) chỉ cần precision 8%; hồ sơ phủ tốt (J ≈ 0.55) đòi
  tới 37%. V9 rải 84% bổ sung vào nhóm phủ tốt trong khi precision đo được chỉ
  32% — nên thua. Cùng bộ từ điển đó, nếu chỉ dùng cho nhóm phủ kém, sẽ lãi.

  Chấm điểm là MACRO nên mỗi hồ sơ đóng góp 1% bất kể dày mỏng, càng khuếch đại
  giá trị của việc vá các hồ sơ nghèo.

Nền là V63 (42.1787) — bản tốt nhất đã được xác nhận, không phải V54 (41.9973).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from engine_v9 import Matcher, extract, load_lexicon  # noqa: E402

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]

# Chỉ can thiệp vào hồ sơ có mật độ khái niệm dưới ngưỡng này so với trung vị.
COVERAGE_CUTOFF = 0.55


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path,
                        default=PROJECT / "data" / "raw" / "input_turn2_vong1" / "input")
    parser.add_argument("--base", type=Path, default=HERE / "_v63",
                        help="Thư mục JSON của bản nền tốt nhất đã xác nhận (V63).")
    parser.add_argument("--lexicon", type=Path, default=HERE / "src" / "lexicon_v9.json")
    parser.add_argument("--output", type=Path, default=HERE / "output_v65")
    parser.add_argument("--zip", type=Path, default=HERE / "submission_v65.zip")
    parser.add_argument("--cutoff", type=float, default=COVERAGE_CUTOFF)
    args = parser.parse_args()

    texts = {i: (args.input / f"{i}.txt").read_text(encoding="utf-8") for i in range(1, 101)}
    base = {i: json.loads((args.base / f"{i}.json").read_text(encoding="utf-8"))
            for i in range(1, 101)}

    # Mật độ khái niệm trên 1000 ký tự là proxy quan sát được cho J của hồ sơ.
    density = {i: len(base[i]) / (len(texts[i]) / 1000) for i in range(1, 101)}
    median = statistics.median(density.values())
    targets = {i for i in range(1, 101) if density[i] < median * args.cutoff}

    matcher = Matcher(load_lexicon(args.lexicon))

    args.output.mkdir(parents=True, exist_ok=True)
    for stale in args.output.glob("*.json"):
        stale.unlink()

    added_total = 0
    per_doc: dict[int, int] = {}

    for i in range(1, 101):
        text = texts[i]
        if i in targets:
            concepts = extract(text, base[i], matcher)
        else:
            # Ngoài nhóm mục tiêu: giữ nguyên bản nền, không đụng một ký tự.
            concepts = extract(text, base[i], Matcher({}))
        added = len(concepts) - len(base[i])
        added_total += added
        per_doc[i] = added

        for concept in concepts:
            start, end = concept["position"]
            assert text[start:end] == concept["text"], f"{i}: lệch offset"

        (args.output / f"{i}.json").write_text(
            json.dumps(concepts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.zip.exists():
        args.zip.unlink()
    with zipfile.ZipFile(args.zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for i in range(1, 101):
            archive.write(args.output / f"{i}.json", f"output/{i}.json")

    base_total = sum(len(v) for v in base.values())
    print(f"[V65] nền V63: {base_total} khái niệm")
    print(f"[V65] hồ sơ mục tiêu (mật độ < {args.cutoff:.0%} trung vị): "
          f"{len(targets)} -> {sorted(targets)}")
    print(f"[V65] bổ sung: +{added_total} khái niệm, tổng {base_total + added_total}")
    print("[V65] chi tiết:")
    for i in sorted(targets):
        if per_doc[i]:
            print(f"        doc {i:3d}: {len(base[i]):2d} -> {len(base[i]) + per_doc[i]:2d}  (+{per_doc[i]})")
    print(f"[V65] zip: {args.zip}")


if __name__ == "__main__":
    main()
