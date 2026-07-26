#!/usr/bin/env python3
"""Script thực thi toàn bộ luồng V7 Breakthrough Pipeline và sinh output.zip.

Usage:
    python run_v7.py --input ../../data/raw/input_turn2_vong1/input --output ./output_v7 --zip ./submission_v7.zip
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

# Thêm src vào sys.path để import các module V7
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from pipeline_v7 import _apply_repeated_line_consensus, _dungle_rules, extract_v7_pipeline


def natural_key(path: Path) -> tuple[int, str]:
    return (int(path.stem), path.name) if path.stem.isdigit() else (10**9, path.name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run V7 Breakthrough Pipeline.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "data" / "raw" / "input_turn2_vong1" / "input",
        help="Thư mục chứa 100 file text bệnh án.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "output_v7",
        help="Thư mục chứa các file json output cho từng bệnh án.",
    )
    parser.add_argument(
        "--zip",
        type=Path,
        default=Path(__file__).resolve().parent / "submission_v7.zip",
        help="Đường dẫn file nộp zip.",
    )
    parser.add_argument(
        "--teacher-cache",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "reference_solutions" / "DungLe_41pt" / "NLP_for_hospital_report_classifier-main" / ".work" / "bamibert_spans.json",
        help="File json chứa prediction từ BamiBERT (nếu có).",
    )
    parser.add_argument(
        "--teacher-zip",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "reference_solutions" / "DungLe_41pt" / "NLP_for_hospital_report_classifier-main" / "submission" / "output.zip",
        help="File zip bài làm DungLe để dùng làm teacher spans.",
    )
    parser.add_argument(
        "--profile",
        choices=["production", "v23"],
        default="production",
        help="Profile chạy inference.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(__file__).resolve().parent / "report_v7.json",
        help="File báo cáo tổng kết chạy V7.",
    )

    args = parser.parse_args()

    if not args.input.exists() or not args.input.is_dir():
        raise FileNotFoundError(f"Không tìm thấy thư mục input: {args.input}")

    sources = sorted(args.input.glob("*.txt"), key=natural_key)
    if not sources:
        raise ValueError(f"Không tìm thấy file .txt nào trong {args.input}")

    texts = {source.stem: source.read_text(encoding="utf-8") for source in sources}

    if args.teacher_cache and args.teacher_cache.exists():
        print(f"[V7] Nạp teacher predictions từ cache: {args.teacher_cache}")
        predictions = json.loads(args.teacher_cache.read_text(encoding="utf-8"))
    elif args.teacher_zip and args.teacher_zip.exists():
        print(f"[V7] Nạp teacher predictions từ bài làm DungLe zip: {args.teacher_zip}")
        predictions = {record_id: [] for record_id in texts}
        with zipfile.ZipFile(args.teacher_zip, "r") as archive:
            for name in archive.namelist():
                if name.endswith(".json"):
                    record_id = Path(name).stem
                    if record_id in predictions:
                        data = json.loads(archive.read(name).decode("utf-8"))
                        for item in data:
                            predictions[record_id].append(dict(item))
    else:
        print(f"[V7] Cảnh báo: Không thấy teacher cache hay zip. Chạy ở chế độ 100% Offline Deterministic Rules + Fuzzy Linker + Type Guard.")
        predictions = {record_id: [] for record_id in texts}

    print(f"[V7] Bắt đầu trích xuất cho {len(sources)} hồ sơ với profile '{args.profile}'...")
    
    # 1. Trích xuất control & baseline cho Consensus
    control_by_record = {
        source.stem: extract_v7_pipeline(
            texts[source.stem],
            predictions.get(source.stem, []),
            "production",
            prune_polar_questions=False,
        )
        for source in sources
    }
    
    entities_by_record = {
        source.stem: extract_v7_pipeline(
            texts[source.stem],
            predictions.get(source.stem, []),
            args.profile,
        )
        for source in sources
    }

    # 2. Áp dụng Repeated-line consensus giữa các hồ sơ
    consensus_added = _apply_repeated_line_consensus(
        texts,
        control_by_record,
        entities_by_record,
    )
    print(f"[V7] Đã bổ sung {consensus_added} thực thể nhờ Đồng thuận câu lặp (Repeated-line consensus).")

    args.output.mkdir(parents=True, exist_ok=True)
    for stale in args.output.glob("*.json"):
        if stale.stem.isdigit():
            stale.unlink()

    total_entities = 0
    type_counts = {t: 0 for t in sorted(_dungle_rules.OFFICIAL_TYPES)}

    for source in sources:
        text = texts[source.stem]
        entities = entities_by_record[source.stem]
        
        # Verify schema hợp lệ (position khớp 100% text, type nằm trong allowlist,...)
        _dungle_rules.validate_record(text, entities)
        
        # Sắp xếp theo vị trí xuất hiện trong text
        entities.sort(key=lambda e: (e["position"][0], -e["position"][1], e["type"], e["text"]))
        
        total_entities += len(entities)
        for e in entities:
            if e["type"] in type_counts:
                type_counts[e["type"]] += 1

        dest = args.output / f"{source.stem}.json"
        dest.write_text(json.dumps(entities, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 3. Đóng gói file zip nộp bài
    args.zip.parent.mkdir(parents=True, exist_ok=True)
    if args.zip.exists():
        args.zip.unlink()

    with zipfile.ZipFile(args.zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sources:
            json_file = args.output / f"{source.stem}.json"
            archive.write(json_file, arcname=f"output/{source.stem}.json")

    summary = {
        "records": len(sources),
        "total_entities": total_entities,
        "type_counts": type_counts,
        "consensus_entities_added": consensus_added,
        "zip_path": str(args.zip),
    }

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[V7] HOÀN TẤT! Đã sinh {total_entities} thực thể.")
    print(f"[V7] Phân bố nhãn: {json.dumps(type_counts, ensure_ascii=False)}")
    print(f"[V7] File nộp bài sẵn sàng tại: {args.zip}")


if __name__ == "__main__":
    main()
