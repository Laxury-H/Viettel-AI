#!/usr/bin/env python3
"""Build an assertion-only probe for hybrid-document seam leakage.

The public corpus is not one homogeneous note per record.  Several records
splice a consultation or an educational paragraph into a structured hospital
template.  A line-oriented section state can therefore leak ``isHistorical``
from a preceding ``Tiền sử`` heading into text that is semantically a current
question or generic advice.

This probe removes only those leaked historical assertions.  Entity text,
boundaries, types, candidates, negation, and family scope are preserved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

from . import turn2_v19
from . import turn2_v24
from . import turn2_v9 as base


CLINICAL_TYPES = {"CHẨN_ĐOÁN", "THUỐC", "TRIỆU_CHỨNG"}

CURRENT_QUESTION = re.compile(
    r"\b(?:em|tôi|cháu|mình)\s+(?:muốn|xin)\s+hỏi\b"
)
EXPLICIT_PAST = re.compile(
    r"\b(?:trước\s+đây|trước\s+đó|đã\s+từng|từng\s+bị|"
    r"\d+\s*(?:ngày|tuần|tháng|năm)\s+trước)\b"
)
GENERIC_EDUCATION = re.compile(
    r"\b(?:trong\s+thời\s+kỳ\s+mãn\s+kinh|phổ\s+biến\s+với\s+thai\s+kỳ)\b"
)
GENERIC_ADVICE = re.compile(
    r"\blời\s+khuyên\s+dành\s+cho\s+bạn\b[\s\S]{0,260}"
    r"\bcó\s+khả\s+năng\s+gây\s+ra\b"
)


def normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def repair_hybrid_seam_assertions(
    texts: dict[str, str],
    records: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Remove historical scope leaked across a hybrid-document seam."""

    output: dict[str, list[dict]] = {}
    changes: list[dict] = []
    for record_id in sorted(records, key=int):
        text = texts[record_id]
        normalized_text = normalize(text)
        entities: list[dict] = []
        for source in records[record_id]:
            entity = dict(source)
            entity["assertions"] = list(source["assertions"])
            if "candidates" in source:
                entity["candidates"] = list(source["candidates"])

            if (
                entity["type"] in CLINICAL_TYPES
                and "isHistorical" in entity["assertions"]
            ):
                start, end = entity["position"]
                line_start = text.rfind("\n", 0, start) + 1
                line_end = text.find("\n", end)
                if line_end < 0:
                    line_end = len(text)
                line = normalized_text[line_start:line_end]
                broad = normalized_text[max(0, start - 280) : min(len(text), end + 160)]

                current_question = (
                    entity["type"] == "TRIỆU_CHỨNG"
                    and CURRENT_QUESTION.search(line) is not None
                    and EXPLICIT_PAST.search(line) is None
                )
                generic_education = (
                    GENERIC_EDUCATION.search(line) is not None
                )
                generic_advice = (
                    GENERIC_ADVICE.search(broad) is not None
                )
                if current_question or generic_education or generic_advice:
                    before = list(entity["assertions"])
                    entity["assertions"].remove("isHistorical")
                    changes.append(
                        {
                            "record_id": record_id,
                            "text": entity["text"],
                            "type": entity["type"],
                            "position": list(entity["position"]),
                            "before": before,
                            "after": list(entity["assertions"]),
                            "reason": (
                                "current_question"
                                if current_question
                                else (
                                    "generic_education"
                                    if generic_education
                                    else "generic_advice"
                                )
                            ),
                        }
                    )
            entities.append(entity)
        output[record_id] = entities
    return output, changes


def run(input_dir: Path, control_zip: Path, output_zip: Path) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    control = turn2_v19.load_submission(control_zip)
    if set(control) != set(texts):
        raise ValueError("Control record IDs do not match input")

    before_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in control.items()
    }
    output, changes = repair_hybrid_seam_assertions(texts, control)
    reason_counts = {
        reason: sum(change["reason"] == reason for change in changes)
        for reason in (
            "current_question",
            "generic_education",
            "generic_advice",
        )
    }
    if len(changes) != 6 or reason_counts != {
        "current_question": 2,
        "generic_education": 2,
        "generic_advice": 2,
    }:
        raise ValueError(
            "Expected six seam repairs split 2/2/2, found "
            f"{len(changes)} with {reason_counts}"
        )

    after_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in output.items()
    }
    if before_keys != after_keys:
        raise AssertionError("V39 must not change entity spans or types")
    for record_id in control:
        for before, after in zip(control[record_id], output[record_id]):
            if before.get("candidates") != after.get("candidates"):
                raise AssertionError("V39 must not change candidates")
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V39-v35-hybrid-document-seam-assertion-probe",
        "control": str(control_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_changes": 0,
        "span_changes": 0,
        "type_changes": 0,
        "candidate_changes": 0,
        "assertion_changes": len(changes),
        "reason_counts": reason_counts,
        "changes": changes,
        "sha256": digest,
        "zip": str(output_zip.resolve()),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--control-zip", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    summary = run(args.input, args.control_zip, args.zip)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
