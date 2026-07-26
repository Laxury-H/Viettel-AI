#!/usr/bin/env python3
"""Correct family assertion scope using the clinical subject point of view."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from . import turn2_v19
from . import turn2_v24
from . import turn2_v9 as base


QUESTION_HEADING = re.compile(r"(?i)^\s*câu\s+hỏi\b")
PRIMARY_RELATIVE_PATIENT = re.compile(
    r"(?i)\b(?:mẹ|cha|bố|ông|bà)\s+(?:của\s+)?(?:em|tôi|cháu)\b"
)


def has_relative_as_primary_patient(text: str) -> bool:
    """Return whether a Q&A document is explicitly about a relative patient."""

    opening = " ".join(text[:240].split())
    return (
        QUESTION_HEADING.search(opening) is not None
        and PRIMARY_RELATIVE_PATIENT.search(opening) is not None
    )


def repair_primary_patient_family_scope(
    texts: dict[str, str],
    records: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Remove isFamily when a relative is the consultation's primary patient."""

    output: dict[str, list[dict]] = {}
    changes: list[dict] = []
    for record_id in sorted(records, key=int):
        text = texts[record_id]
        primary_relative = has_relative_as_primary_patient(text)
        entities: list[dict] = []
        for source in records[record_id]:
            entity = dict(source)
            entity["assertions"] = list(source["assertions"])
            if "candidates" in source:
                entity["candidates"] = list(source["candidates"])
            before = list(entity["assertions"])
            if primary_relative and "isFamily" in entity["assertions"]:
                entity["assertions"].remove("isFamily")
            if entity["assertions"] != before:
                start, end = entity["position"]
                changes.append(
                    {
                        "record_id": record_id,
                        "text": entity["text"],
                        "type": entity["type"],
                        "position": entity["position"],
                        "before_assertions": before,
                        "after_assertions": entity["assertions"],
                        "context": " ".join(
                            text[max(0, start - 100) : min(len(text), end + 40)]
                            .split()
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

    output, changes = repair_primary_patient_family_scope(texts, control)
    changed_records = {change["record_id"] for change in changes}
    if len(changes) != 18 or changed_records != {"64", "80", "95"}:
        raise ValueError(
            "Expected 18 primary-patient family removals in records "
            f"64/80/95, found {len(changes)} in {sorted(changed_records)}"
        )
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    before_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in control.items()
    }
    after_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in output.items()
    }
    if before_keys != after_keys:
        raise AssertionError("V33 must not change entity spans or types")
    for record_id in control:
        for before, after in zip(control[record_id], output[record_id]):
            if before.get("candidates") != after.get("candidates"):
                raise AssertionError("V33 must not change candidates")

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V33-v30-primary-patient-family-scope",
        "control": str(control_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "changed_records": len(changed_records),
        "assertion_removals": len(changes),
        "span_changes": 0,
        "candidate_changes": 0,
        "preserved_secondary_family_records": ["24", "26", "42", "62", "81"],
        "changes": changes,
        "score_expectation": {
            "confirmed_control": 39.5367,
            "target_range": [39.60, 39.78],
            "status": "unscored_primary_patient_family_scope",
        },
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
