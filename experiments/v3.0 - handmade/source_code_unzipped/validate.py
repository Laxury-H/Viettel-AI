#!/usr/bin/env python3
"""Validate an AI Race output ZIP against its source input directory."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


ALLOWED_TYPES = {
    "CHẨN_ĐOÁN",
    "TRIỆU_CHỨNG",
    "TÊN_XÉT_NGHIỆM",
    "KẾT_QUẢ_XÉT_NGHIỆM",
    "THUỐC",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_file", type=Path)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()

    sources = sorted(args.input.glob("*.txt"), key=lambda p: int(p.stem))
    expected = {f"output/{p.stem}.json" for p in sources}
    errors: list[str] = []
    entity_count = 0

    with zipfile.ZipFile(args.zip_file) as archive:
        actual = {name for name in archive.namelist() if not name.endswith("/")}
        if actual != expected:
            errors.append(
                f"Sai danh sách file: thiếu={sorted(expected-actual)}, thừa={sorted(actual-expected)}"
            )
        for source in sources:
            member = f"output/{source.stem}.json"
            if member not in actual:
                continue
            text = source.read_text(encoding="utf-8")
            try:
                entities = json.loads(archive.read(member).decode("utf-8"))
            except Exception as exc:  # noqa: BLE001 - validator should report all malformed files
                errors.append(f"{member}: JSON không hợp lệ: {exc}")
                continue
            if not isinstance(entities, list):
                errors.append(f"{member}: gốc JSON phải là list")
                continue
            entity_count += len(entities)
            for index, entity in enumerate(entities):
                label = f"{member}[{index}]"
                if not isinstance(entity, dict):
                    errors.append(f"{label}: phải là object")
                    continue
                if entity.get("type") not in ALLOWED_TYPES:
                    errors.append(f"{label}: type không hợp lệ")
                position = entity.get("position")
                if not (
                    isinstance(position, list)
                    and len(position) == 2
                    and all(isinstance(x, int) for x in position)
                ):
                    errors.append(f"{label}: position không hợp lệ")
                    continue
                start, end = position
                if not (0 <= start < end <= len(text)) or text[start:end] != entity.get("text"):
                    errors.append(f"{label}: text không khớp position")
                if not isinstance(entity.get("assertions"), list):
                    errors.append(f"{label}: assertions phải là list")
                normalized = entity.get("type") in {"CHẨN_ĐOÁN", "THUỐC"}
                if normalized and not entity.get("candidates"):
                    errors.append(f"{label}: thiếu candidates")
                if not normalized and "candidates" in entity:
                    errors.append(f"{label}: candidates không được dùng cho type này")

    if errors:
        print("VALIDATION FAILED")
        for error in errors:
            print("-", error)
        raise SystemExit(1)
    print(f"VALID: {len(sources)} records, {entity_count} entities")


if __name__ == "__main__":
    main()
