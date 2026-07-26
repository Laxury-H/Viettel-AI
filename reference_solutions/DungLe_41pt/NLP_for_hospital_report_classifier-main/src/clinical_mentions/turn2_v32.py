#!/usr/bin/env python3
"""Repair direct-relative assertion scope without changing V30 entities."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from . import turn2_v19
from . import turn2_v24
from . import turn2_v28
from . import turn2_v9 as base


CLINICAL_TYPES = {"CHẨN_ĐOÁN", "THUỐC", "TRIỆU_CHỨNG"}
FAMILY_ASSERTION_SURFACES = frozenset(
    {
        "bệnh bàn chân bẹt",
        "dị tật thiểu sản vành tai",
        "tịt ống tai ngoài bẩm sinh",
        "run tay",
    }
)
DIRECT_RELATIVE_CUE = re.compile(
    r"(?i)\b(?:mẹ|cha|bố|ông|bà|con|bé|cháu\s+bé)"
    r"(?:\s+của\s+(?:tôi|em|mình|bạn|cháu))?"
    r"[^.;\n]{0,100}\b(?:bị|mắc\s+phải\s+là)\b"
    r"[^.;\n]{0,90}$"
)


def has_direct_relative_subject(text: str, start: int) -> bool:
    """Return whether the current clause explicitly assigns a relative."""

    prefix = text[max(0, start - 220) : start]
    return DIRECT_RELATIVE_CUE.search(prefix) is not None


def repair_direct_family_assertions(
    texts: dict[str, str],
    records: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Add isFamily to reviewed mentions with a direct relative subject."""

    output: dict[str, list[dict]] = {}
    changes: list[dict] = []
    for record_id in sorted(records, key=int):
        text = texts[record_id]
        entities: list[dict] = []
        for source in records[record_id]:
            entity = dict(source)
            entity["assertions"] = list(source["assertions"])
            if "candidates" in source:
                entity["candidates"] = list(source["candidates"])
            normalized = turn2_v28.normalized_surface(entity["text"])
            before = list(entity["assertions"])
            if (
                entity["type"] in CLINICAL_TYPES
                and normalized in FAMILY_ASSERTION_SURFACES
                and "isFamily" not in entity["assertions"]
                and has_direct_relative_subject(
                    text,
                    entity["position"][0],
                )
            ):
                insertion = (
                    1 if entity["assertions"][:1] == ["isNegated"] else 0
                )
                entity["assertions"].insert(insertion, "isFamily")
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

    output, changes = repair_direct_family_assertions(texts, control)
    if len(changes) != 8:
        raise ValueError(
            f"Expected eight direct-family assertion repairs, found {len(changes)}"
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
        raise AssertionError("V32 must not change entity spans or types")
    for record_id in control:
        for before, after in zip(control[record_id], output[record_id]):
            if before.get("candidates") != after.get("candidates"):
                raise AssertionError("V32 must not change candidates")

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V32-v30-direct-family-assertion",
        "control": str(control_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "changed_records": len({change["record_id"] for change in changes}),
        "assertion_repairs": len(changes),
        "span_changes": 0,
        "candidate_changes": 0,
        "changes": changes,
        "score_expectation": {
            "confirmed_control": 39.5367,
            "target_range": [39.54, 39.57],
            "status": "unscored_direct_family_assertion",
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
