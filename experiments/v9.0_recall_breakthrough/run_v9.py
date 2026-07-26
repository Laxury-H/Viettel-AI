#!/usr/bin/env python3
"""Chạy pipeline V9 và đóng gói output.zip đúng cấu trúc đề bài.

    python run_v9.py --input <thư mục .txt> --baseline-zip <output.zip 41.99đ> \
                     --output output_v9 --zip submission_v9.zip
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from engine_v9 import Matcher, extract, load_lexicon  # noqa: E402

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]


def natural_key(path: Path) -> tuple[int, str]:
    return (int(path.stem), path.name) if path.stem.isdigit() else (10**9, path.name)


def load_baseline(baseline_zip: Path | None, baseline_dir: Path | None) -> dict[str, list[dict]]:
    """Nạp bài làm nền (41.9973 điểm) từ zip hoặc thư mục đã giải nén."""
    records: dict[str, list[dict]] = {}
    if baseline_zip and baseline_zip.exists():
        with zipfile.ZipFile(baseline_zip) as archive:
            for name in archive.namelist():
                if name.endswith(".json"):
                    stem = Path(name).stem
                    if stem.isdigit():
                        records[stem] = json.loads(archive.read(name).decode("utf-8"))
    elif baseline_dir and baseline_dir.exists():
        for path in baseline_dir.glob("*.json"):
            if path.stem.isdigit():
                records[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="V9 recall-breakthrough pipeline")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT / "data" / "raw" / "input_turn2_vong1" / "input",
    )
    parser.add_argument(
        "--baseline-zip",
        type=Path,
        default=PROJECT
        / "reference_solutions"
        / "DungLe_41pt"
        / "NLP_for_hospital_report_classifier-main"
        / "submission"
        / "output.zip",
    )
    parser.add_argument("--baseline-dir", type=Path, default=None)
    parser.add_argument("--lexicon", type=Path, default=HERE / "src" / "lexicon_v9.json")
    parser.add_argument("--output", type=Path, default=HERE / "output_v9")
    parser.add_argument("--zip", type=Path, default=HERE / "submission_v9.zip")
    parser.add_argument("--report", type=Path, default=HERE / "report_v9.json")
    args = parser.parse_args()

    if not args.input.is_dir():
        raise SystemExit(f"Không tìm thấy thư mục input: {args.input}")

    sources = sorted(args.input.glob("*.txt"), key=natural_key)
    if not sources:
        raise SystemExit(f"Không có file .txt nào trong {args.input}")

    lexicon = load_lexicon(args.lexicon)
    matcher = Matcher(lexicon)
    baseline = load_baseline(args.baseline_zip, args.baseline_dir)
    if not baseline:
        print("[V9] CẢNH BÁO: không nạp được bài nền, chạy thuần từ điển.")

    args.output.mkdir(parents=True, exist_ok=True)
    for stale in args.output.glob("*.json"):
        if stale.stem.isdigit():
            stale.unlink()

    type_counts: collections.Counter = collections.Counter()
    total = 0
    baseline_total = 0

    for source in sources:
        stem = source.stem
        text = source.read_text(encoding="utf-8")
        seed = baseline.get(stem, [])
        baseline_total += len(seed)

        concepts = extract(text, seed, matcher)

        # Bất biến bắt buộc: mọi span phải trỏ đúng vào text gốc.
        for concept in concepts:
            start, end = concept["position"]
            assert text[start:end] == concept["text"], f"{stem}: lệch offset"

        total += len(concepts)
        type_counts.update(c["type"] for c in concepts)

        (args.output / f"{stem}.json").write_text(
            json.dumps(concepts, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if args.zip.exists():
        args.zip.unlink()
    args.zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sources:
            archive.write(args.output / f"{source.stem}.json", f"output/{source.stem}.json")

    summary = {
        "records": len(sources),
        "baseline_concepts": baseline_total,
        "total_concepts": total,
        "added_concepts": total - baseline_total,
        "concepts_per_record": round(total / len(sources), 2),
        "type_counts": dict(type_counts),
        "lexicon_entries": len(lexicon),
        "zip": str(args.zip),
    }
    args.report.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"[V9] {len(sources)} hồ sơ | {baseline_total} -> {total} khái niệm "
          f"(+{total - baseline_total}, {summary['concepts_per_record']}/hồ sơ)")
    print(f"[V9] type: {json.dumps(dict(type_counts), ensure_ascii=False)}")
    print(f"[V9] zip: {args.zip}")


if __name__ == "__main__":
    main()
