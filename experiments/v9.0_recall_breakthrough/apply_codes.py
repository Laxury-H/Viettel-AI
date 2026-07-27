#!/usr/bin/env python3
"""Áp các mã đã được thẩm định lên bản nền, CHỈ đụng trường candidates.

Vì sao chỉ sửa mã:

  Ba lượt nộp thật đã đo được ranh giới an toàn.
    · v9  thêm 275 khái niệm (precision 32%)              -> −0.1732
    · v64 thêm 11 khái niệm vào 4 hồ sơ thưa              -> −0.3956
    · V63 sửa 19 mã, không đụng text                      -> **+0.1376**

  WER được tính macro theo hồ sơ với mẫu số là số TỪ của đáp án trong chính hồ
  sơ đó. Hồ sơ thưa có mẫu số rất nhỏ nên chỉ vài từ chèn thêm đã đủ đẩy WER của
  hồ sơ đó vượt 100%, mà mỗi hồ sơ luôn nặng đúng 1% điểm.

  Do đó bản này KHÔNG thêm, KHÔNG bớt, KHÔNG sửa text/position/type/assertions.
  WER và J_assertion bất biến theo thiết kế; chỉ J_candidates thay đổi. Script
  tự dừng nếu bất biến đó bị vi phạm dù chỉ một ký tự.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

ICD_RE = re.compile(r"^[A-TV-Z]\d{2}(?:\.\d{1,2})?$")
RXCUI_RE = re.compile(r"^\d{1,8}$")
CODED_TYPES = {"CHẨN_ĐOÁN", "THUỐC"}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip().lower()


def load_corrections(path: Path) -> dict[tuple[str, str, str], str]:
    """(type, text chuẩn hóa, mã cũ) -> mã mới."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw.get("confirmed", raw) if isinstance(raw, dict) else raw
    table: dict[tuple[str, str, str], str] = {}
    for item in items:
        etype = item.get("type")
        text = item.get("text")
        old = str(item.get("current_code", "")).strip()
        new = str(item.get("proposed_code", "")).strip()
        if not (etype in CODED_TYPES and text and old and new) or old == new:
            continue
        pattern = ICD_RE if etype == "CHẨN_ĐOÁN" else RXCUI_RE
        if not pattern.match(new):
            print(f"  [bỏ] mã đề xuất sai định dạng: {new!r} cho {text!r}")
            continue
        table[(etype, norm(text), old)] = new
    return table


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=HERE / "_v63")
    parser.add_argument("--corrections", type=Path, default=HERE / "corrections.json")
    parser.add_argument("--output", type=Path, default=HERE / "output_v66")
    parser.add_argument("--zip", type=Path, default=HERE / "submission_v66.zip")
    args = parser.parse_args()

    table = load_corrections(args.corrections)
    print(f"[apply] nạp {len(table)} quy tắc sửa mã")

    args.output.mkdir(parents=True, exist_ok=True)
    for stale in args.output.glob("*.json"):
        stale.unlink()

    applied = 0
    touched_docs: set[int] = set()

    for i in range(1, 101):
        concepts = json.loads((args.base / f"{i}.json").read_text(encoding="utf-8"))
        out = []
        for concept in concepts:
            # Sao chép nguyên trạng; chỉ trường candidates mới có thể đổi.
            item = dict(concept)
            etype = concept.get("type")
            cands = concept.get("candidates")
            if etype in CODED_TYPES and cands:
                key_text = norm(concept["text"])
                new_cands = []
                for code in cands:
                    repl = table.get((etype, key_text, str(code)))
                    if repl:
                        new_cands.append(repl)
                        applied += 1
                        touched_docs.add(i)
                    else:
                        new_cands.append(code)
                item["candidates"] = new_cands
            out.append(item)

        # --- BẤT BIẾN CỨNG: mọi trường ngoài candidates phải y hệt bản nền ---
        assert len(out) == len(concepts), f"{i}: số khái niệm đổi"
        for a, b in zip(concepts, out):
            assert a["text"] == b["text"], f"{i}: text đổi"
            assert a["type"] == b["type"], f"{i}: type đổi"
            assert a["position"] == b["position"], f"{i}: position đổi"
            assert a.get("assertions") == b.get("assertions"), f"{i}: assertions đổi"
            assert ("candidates" in a) == ("candidates" in b), f"{i}: sự hiện diện candidates đổi"
            if "candidates" in a:
                assert len(a["candidates"]) == len(b["candidates"]), f"{i}: số mã đổi"

        (args.output / f"{i}.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.zip.exists():
        args.zip.unlink()
    with zipfile.ZipFile(args.zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for i in range(1, 101):
            archive.write(args.output / f"{i}.json", f"output/{i}.json")

    print(f"[apply] sửa {applied} mention trên {len(touched_docs)} hồ sơ: {sorted(touched_docs)}")
    print(f"[apply] bất biến text/position/type/assertions: ĐẠT trên cả 100 file")
    print(f"[apply] zip: {args.zip}")


if __name__ == "__main__":
    main()
