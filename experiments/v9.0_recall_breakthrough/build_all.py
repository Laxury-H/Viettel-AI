#!/usr/bin/env python3
"""Dựng lại toàn bộ V9 từ đầu: giải nén bài nền -> từ điển -> output -> zip -> kiểm tra.

Sinh hai biến thể để có thể A/B trên leaderboard:

  v9-full         : sàn độ tin cậy 'medium'. Độ phủ cao nhất.
  v9-conservative : sàn độ tin cậy 'high'.   Chỉ giữ các bổ sung chắc chắn nhất.

Lý do phải có hai bản: mô hình hàm chấm cho thấy điểm hòa vốn của việc thêm một
khái niệm nằm quanh 0.5 — chỉ text_score và assertions_score hưởng lợi, còn
candidates_score đã được kiểm chứng là chỉ phản ứng với MÃ. Không có ground
truth thì không biết ta đang ở phía nào của ngưỡng; cách duy nhất để biết là
nộp cả hai và đọc leaderboard.
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
INPUT = PROJECT / "data" / "raw" / "input_turn2_vong1" / "input"
BASELINE_ZIP = (
    PROJECT
    / "reference_solutions"
    / "DungLe_41pt"
    / "NLP_for_hospital_report_classifier-main"
    / "submission"
    / "output.zip"
)
BASELINE_DIR = HERE / "_baseline"

MINED_FILES = ["mined_raw.json", "deep_raw.json", "code_raw.json"]
CODES_FILE = HERE / "coding_raw.json"
AUDIT_FILE = HERE / "audit_raw.json"

VARIANTS = (
    # (tên, sàn độ tin cậy, file từ điển, thư mục output, tên zip)
    ("full", "medium", "lexicon_v9.json", "output_v9", "submission_v9_full.zip"),
    ("conservative", "high", "lexicon_v9_hi.json", "output_v9_conservative", "submission_v9_conservative.zip"),
)


def run(script: str, *args: str) -> None:
    cmd = [sys.executable, str(HERE / script), *args]
    print("+", script, " ".join(args))
    if subprocess.run(cmd, cwd=HERE).returncode != 0:
        raise SystemExit(f"lệnh thất bại: {script}")


def extract_baseline() -> None:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(BASELINE_ZIP) as archive:
        for name in archive.namelist():
            if name.endswith(".json"):
                stem = Path(name).stem
                if stem.isdigit():
                    (BASELINE_DIR / f"{stem}.json").write_bytes(archive.read(name))
    print(f"[build] giải nén bài nền -> {BASELINE_DIR} ({len(list(BASELINE_DIR.glob('*.json')))} file)")


def main() -> None:
    extract_baseline()

    mined = [str(HERE / f) for f in MINED_FILES if (HERE / f).exists()]
    if not mined:
        raise SystemExit("không tìm thấy file entry thô nào")
    print(f"[build] nguồn entry thô: {[Path(m).name for m in mined]}")

    for name, floor, lexicon, outdir, zipname in VARIANTS:
        print(f"\n{'=' * 64}\nDỰNG BIẾN THỂ v9-{name}  (sàn độ tin cậy = {floor})\n{'=' * 64}")

        build_args = ["--mined", *mined, "--input", str(INPUT),
                      "--baseline", str(BASELINE_DIR),
                      "--min-confidence", floor,
                      "--out", str(HERE / "src" / lexicon),
                      "--report", str(HERE / f"lexicon_report_{name}.json")]
        if CODES_FILE.exists():
            build_args += ["--codes", str(CODES_FILE)]
        if AUDIT_FILE.exists():
            build_args += ["--drop", str(AUDIT_FILE)]
        run("build_lexicon.py", *build_args)

        run("run_v9.py",
            "--input", str(INPUT),
            "--baseline-zip", str(BASELINE_ZIP),
            "--lexicon", str(HERE / "src" / lexicon),
            "--output", str(HERE / outdir),
            "--zip", str(HERE / zipname),
            "--report", str(HERE / f"report_v9_{name}.json"))

        run("validate_v9.py", "--output", str(HERE / outdir), "--input", str(INPUT))

    print(f"\n{'=' * 64}\nHOÀN TẤT. Hai file nộp đã sẵn sàng:")
    for _, _, _, _, zipname in VARIANTS:
        print(f"  {HERE / zipname}")


if __name__ == "__main__":
    main()
