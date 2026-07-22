#!/usr/bin/env python3
"""Validate a Viettel AI Race round-1 submission ZIP.

The validator is deliberately dependency-free.  It checks the archive layout,
the upgraded five-type entity schema, exact source spans, assertion/candidate
constraints, and duplicate entities before reporting a compact corpus summary.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


RECORD_IDS = tuple(str(index) for index in range(1, 101))
EXPECTED_MEMBERS = {f"output/{record_id}.json" for record_id in RECORD_IDS}
EXPECTED_SOURCES = {f"{record_id}.txt" for record_id in RECORD_IDS}

ALLOWED_TYPES = {
    "CHẨN_ĐOÁN",
    "TRIỆU_CHỨNG",
    "TÊN_XÉT_NGHIỆM",
    "KẾT_QUẢ_XÉT_NGHIỆM",
    "THUỐC",
}
NORMALIZED_TYPES = {"CHẨN_ĐOÁN", "THUỐC"}
LAB_TYPES = {"TÊN_XÉT_NGHIỆM", "KẾT_QUẢ_XÉT_NGHIỆM"}
ALLOWED_ASSERTIONS = {"isNegated", "isFamily", "isHistorical"}

BASE_FIELDS = {"text", "type", "assertions", "position"}
MAX_REPORTED_ERRORS = 200


class DuplicateJsonKey(ValueError):
    """Raised when a JSON object contains the same key more than once."""


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKey(f"trùng khóa JSON {key!r}")
        result[key] = value
    return result


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    error_count: int = 0
    parsed_records: int = 0
    entity_count: int = 0
    empty_records: list[str] = field(default_factory=list)
    entities_per_record: list[int] = field(default_factory=list)
    type_counts: Counter[str] = field(default_factory=Counter)
    assertion_counts: Counter[str] = field(default_factory=Counter)
    entities_with_assertions: int = 0
    candidate_entity_count: int = 0
    candidate_value_count: int = 0

    def error(self, message: str) -> None:
        self.error_count += 1
        if len(self.errors) < MAX_REPORTED_ERRORS:
            self.errors.append(message)

    def print_summary(self, archive_member_count: int) -> None:
        print("SUMMARY")
        print(f"- expected records: {len(RECORD_IDS)}")
        print(f"- archive files: {archive_member_count}")
        print(f"- parsed records: {self.parsed_records}")
        print(f"- entities: {self.entity_count}")

        if self.type_counts:
            rendered_types = ", ".join(
                f"{entity_type}={self.type_counts.get(entity_type, 0)}"
                for entity_type in sorted(ALLOWED_TYPES)
            )
            print(f"- by type: {rendered_types}")
        else:
            print("- by type: none")

        if self.assertion_counts:
            rendered_assertions = ", ".join(
                f"{assertion}={self.assertion_counts.get(assertion, 0)}"
                for assertion in sorted(ALLOWED_ASSERTIONS)
            )
            print(f"- assertions: {rendered_assertions}")
        else:
            print("- assertions: none")

        print(f"- entities with assertions: {self.entities_with_assertions}")
        print(
            "- candidates: "
            f"{self.candidate_entity_count} entities, "
            f"{self.candidate_value_count} values"
        )
        print(
            "- entities per parsed record: "
            + (
                f"min={min(self.entities_per_record)}, "
                f"max={max(self.entities_per_record)}, "
                f"avg={self.entity_count / self.parsed_records:.2f}"
                if self.entities_per_record
                else "n/a"
            )
        )
        print(
            "- empty records: "
            + (", ".join(self.empty_records) if self.empty_records else "none")
        )


def validate_input_directory(input_dir: Path, report: ValidationReport) -> None:
    if not input_dir.is_dir():
        report.error(f"input directory không tồn tại: {input_dir}")
        return

    actual_sources = {path.name for path in input_dir.glob("*.txt")}
    missing = sorted(EXPECTED_SOURCES - actual_sources, key=lambda name: int(Path(name).stem))
    extra = sorted(actual_sources - EXPECTED_SOURCES)
    if missing:
        report.error(f"input thiếu file: {missing}")
    if extra:
        report.error(f"input thừa file .txt: {extra}")


def validate_string_list(
    value: Any,
    *,
    label: str,
    report: ValidationReport,
    nonempty: bool,
) -> list[str] | None:
    if not isinstance(value, list):
        report.error(f"{label}: phải là list")
        return None
    if nonempty and not value:
        report.error(f"{label}: không được rỗng")
        return None
    if not all(isinstance(item, str) and item.strip() for item in value):
        report.error(f"{label}: mọi phần tử phải là chuỗi không rỗng")
        return None
    if len(value) != len(set(value)):
        report.error(f"{label}: chứa phần tử trùng lặp")
        return None
    return value


def validate_entity(
    entity: Any,
    *,
    label: str,
    source_text: str,
    seen_entities: set[tuple[str, str, int, int]],
    report: ValidationReport,
) -> None:
    if not isinstance(entity, dict):
        report.error(f"{label}: phải là object")
        return

    entity_type = entity.get("type")
    expected_fields = BASE_FIELDS | ({"candidates"} if entity_type in NORMALIZED_TYPES else set())
    actual_fields = set(entity)
    missing_fields = sorted(expected_fields - actual_fields)
    extra_fields = sorted(actual_fields - expected_fields)
    if missing_fields:
        report.error(f"{label}: thiếu trường {missing_fields}")
    if extra_fields:
        report.error(f"{label}: thừa trường {extra_fields}")

    if entity_type not in ALLOWED_TYPES:
        report.error(f"{label}.type: giá trị không hợp lệ {entity_type!r}")
    else:
        report.type_counts[entity_type] += 1

    text = entity.get("text")
    if not isinstance(text, str) or not text:
        report.error(f"{label}.text: phải là chuỗi không rỗng")

    position = entity.get("position")
    valid_position = (
        isinstance(position, list)
        and len(position) == 2
        and all(type(value) is int for value in position)
    )
    if not valid_position:
        report.error(f"{label}.position: phải là [start, end] gồm hai số nguyên")
    else:
        start, end = position
        if not 0 <= start < end <= len(source_text):
            report.error(
                f"{label}.position: ngoài phạm vi [0, {len(source_text)}]: {position}"
            )
        elif isinstance(text, str) and source_text[start:end] != text:
            report.error(
                f"{label}: text không khớp source_text[{start}:{end}] "
                f"({source_text[start:end]!r} != {text!r})"
            )
        elif isinstance(text, str) and entity_type in ALLOWED_TYPES:
            identity = (entity_type, text, start, end)
            if identity in seen_entities:
                report.error(
                    f"{label}: thực thể trùng exact (type, text, position)"
                )
            else:
                seen_entities.add(identity)

    assertions = validate_string_list(
        entity.get("assertions"),
        label=f"{label}.assertions",
        report=report,
        nonempty=False,
    )
    if assertions is not None:
        invalid_assertions = sorted(set(assertions) - ALLOWED_ASSERTIONS)
        if invalid_assertions:
            report.error(
                f"{label}.assertions: giá trị không hợp lệ {invalid_assertions}"
            )
        else:
            report.assertion_counts.update(assertions)
            if assertions:
                report.entities_with_assertions += 1
        if entity_type in LAB_TYPES and assertions:
            report.error(f"{label}.assertions: loại xét nghiệm bắt buộc phải rỗng")

    if entity_type in NORMALIZED_TYPES:
        candidates = validate_string_list(
            entity.get("candidates"),
            label=f"{label}.candidates",
            report=report,
            nonempty=True,
        )
        if candidates is not None:
            report.candidate_entity_count += 1
            report.candidate_value_count += len(candidates)
    elif "candidates" in entity:
        report.error(f"{label}.candidates: chỉ dùng cho CHẨN_ĐOÁN hoặc THUỐC")


def validate_record(
    record_id: str,
    payload: bytes,
    source_text: str,
    report: ValidationReport,
) -> None:
    member = f"output/{record_id}.json"
    try:
        decoded = payload.decode("utf-8-sig")
        entities = json.loads(decoded, object_pairs_hook=reject_duplicate_json_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, DuplicateJsonKey) as exc:
        report.error(f"{member}: JSON UTF-8 không hợp lệ: {exc}")
        return

    if not isinstance(entities, list):
        report.error(f"{member}: gốc JSON phải là list")
        return

    report.parsed_records += 1
    report.entities_per_record.append(len(entities))
    report.entity_count += len(entities)
    if not entities:
        report.empty_records.append(record_id)

    seen_entities: set[tuple[str, str, int, int]] = set()
    for entity_index, entity in enumerate(entities):
        validate_entity(
            entity,
            label=f"{member}[{entity_index}]",
            source_text=source_text,
            seen_entities=seen_entities,
            report=report,
        )


def validate_archive(zip_path: Path, input_dir: Path) -> ValidationReport:
    report = ValidationReport()
    validate_input_directory(input_dir, report)

    if not zip_path.is_file():
        report.error(f"ZIP không tồn tại: {zip_path}")
        report.print_summary(archive_member_count=0)
        return report

    try:
        with zipfile.ZipFile(zip_path) as archive:
            file_infos = [info for info in archive.infolist() if not info.is_dir()]
            member_names = [info.filename for info in file_infos]
            duplicate_members = sorted(
                name for name, count in Counter(member_names).items() if count > 1
            )
            if duplicate_members:
                report.error(f"ZIP chứa member trùng tên: {duplicate_members}")

            actual_members = set(member_names)
            missing_members = sorted(
                EXPECTED_MEMBERS - actual_members,
                key=lambda name: int(Path(name).stem),
            )
            extra_members = sorted(actual_members - EXPECTED_MEMBERS)
            if missing_members:
                report.error(f"ZIP thiếu file: {missing_members}")
            if extra_members:
                report.error(f"ZIP thừa file: {extra_members}")

            for record_id in RECORD_IDS:
                member = f"output/{record_id}.json"
                source_path = input_dir / f"{record_id}.txt"
                if member not in actual_members or not source_path.is_file():
                    continue
                try:
                    source_text = source_path.read_text(encoding="utf-8")
                    payload = archive.read(member)
                except (OSError, KeyError, RuntimeError) as exc:
                    report.error(f"{member}: không thể đọc dữ liệu: {exc}")
                    continue
                validate_record(record_id, payload, source_text, report)

            report.print_summary(archive_member_count=len(file_infos))
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        report.error(f"ZIP không hợp lệ: {exc}")
        report.print_summary(archive_member_count=0)

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate output.zip against the upgraded Viettel AI schema."
    )
    parser.add_argument("zip_file", type=Path, help="Submission ZIP to validate")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Directory containing source 1.txt through 100.txt",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = validate_archive(args.zip_file, args.input)
    if report.error_count:
        print(f"VALIDATION FAILED: {report.error_count} error(s)", file=sys.stderr)
        for error in report.errors:
            print(f"- {error}", file=sys.stderr)
        omitted = report.error_count - len(report.errors)
        if omitted:
            print(f"- ... {omitted} additional error(s) omitted", file=sys.stderr)
        return 1

    print("VALID: submission matches the upgraded schema")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
