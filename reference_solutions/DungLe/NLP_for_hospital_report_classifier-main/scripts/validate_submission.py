#!/usr/bin/env python3
"""Strict, dependency-free validator for a Turn 2 output ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath


TYPES = {
    "THUỐC",
    "TRIỆU_CHỨNG",
    "CHẨN_ĐOÁN",
    "TÊN_XÉT_NGHIỆM",
    "KẾT_QUẢ_XÉT_NGHIỆM",
}
ASSERTIONS = {"isNegated", "isFamily", "isHistorical"}
NORMALIZED_TYPES = {"THUỐC", "CHẨN_ĐOÁN"}
LAB_TYPES = {"TÊN_XÉT_NGHIỆM", "KẾT_QUẢ_XÉT_NGHIỆM"}
ICD10 = re.compile(r"^[A-TV-Z][0-9][0-9A-Z](?:\.[0-9A-Z]{1,4})?$")


def natural(path: Path) -> tuple[int, str]:
    return (int(path.stem), path.name) if path.stem.isdigit() else (10**9, path.name)


def fail(message: str) -> None:
    raise ValueError(message)


def validate_entity(entity: object, text: str, file_name: str, index: int) -> None:
    where = f"{file_name}[{index}]"
    if not isinstance(entity, dict):
        fail(f"{where}: entity must be an object")
    allowed = {"text", "type", "assertions", "position", "candidates"}
    if not set(entity) <= allowed:
        fail(f"{where}: unexpected keys {sorted(set(entity) - allowed)}")
    required = {"text", "type", "assertions", "position"}
    if not required <= set(entity):
        fail(f"{where}: missing keys {sorted(required - set(entity))}")
    entity_type = entity["type"]
    if entity_type not in TYPES:
        fail(f"{where}: invalid type {entity_type!r}")
    position = entity["position"]
    if (
        not isinstance(position, list)
        or len(position) != 2
        or any(type(value) is not int for value in position)
    ):
        fail(f"{where}: position must be [int, int]")
    start, end = position
    if not 0 <= start < end <= len(text):
        fail(f"{where}: position outside source")
    if not isinstance(entity["text"], str) or text[start:end] != entity["text"]:
        fail(f"{where}: exact source span mismatch")
    assertions = entity["assertions"]
    if (
        not isinstance(assertions, list)
        or len(assertions) != len(set(assertions))
        or not set(assertions) <= ASSERTIONS
    ):
        fail(f"{where}: invalid assertions")
    if entity_type in LAB_TYPES and assertions:
        fail(f"{where}: lab entities must have empty assertions")
    candidates = entity.get("candidates")
    if entity_type in NORMALIZED_TYPES:
        if not isinstance(candidates, list) or not candidates:
            fail(f"{where}: {entity_type} requires candidates")
        if any(not isinstance(value, str) or not value for value in candidates):
            fail(f"{where}: invalid candidate value")
        if entity_type == "THUỐC" and any(not value.isascii() or not value.isdigit() for value in candidates):
            fail(f"{where}: invalid RxNorm candidate")
        if entity_type == "CHẨN_ĐOÁN" and any(not ICD10.fullmatch(value) for value in candidates):
            fail(f"{where}: invalid ICD-10 candidate")
    elif candidates is not None:
        fail(f"{where}: candidates are not allowed for {entity_type}")


def validate(zip_path: Path, input_dir: Path) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=natural)
    expected = [f"output/{path.stem}.json" for path in sources]
    entity_count = 0
    by_type = {name: 0 for name in sorted(TYPES)}
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        if names != expected:
            missing = sorted(set(expected) - set(names))
            extra = sorted(set(names) - set(expected))
            fail(f"ZIP allowlist/order mismatch; missing={missing}, extra={extra}")
        if archive.testzip() is not None:
            fail("ZIP CRC failure")
        for source, name in zip(sources, names):
            if PurePosixPath(name).parent != PurePosixPath("output"):
                fail(f"unsafe archive path: {name}")
            try:
                payload = json.loads(archive.read(name).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                fail(f"{name}: invalid UTF-8/JSON: {exc}")
            if not isinstance(payload, list):
                fail(f"{name}: top-level JSON must be an array")
            text = source.read_text(encoding="utf-8")
            seen: set[tuple[int, int, str]] = set()
            for index, entity in enumerate(payload):
                validate_entity(entity, text, name, index)
                key = (*entity["position"], entity["type"])
                if key in seen:
                    fail(f"{name}[{index}]: duplicate entity")
                seen.add(key)
                entity_count += 1
                by_type[entity["type"]] += 1
    return {
        "status": "PASS",
        "records": len(sources),
        "entities": entity_count,
        "by_type": by_type,
        "sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("zip", type=Path)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.zip, args.input), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
