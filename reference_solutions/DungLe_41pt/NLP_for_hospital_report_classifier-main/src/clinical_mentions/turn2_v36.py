#!/usr/bin/env python3
"""Build a Vietnam ICD specificity probe on top of the V35 submission.

V35 established that normalizing foreign/extended ICD codes to codes present
in Vietnam's official appendix materially improves J_candidates.  V36 tests a
different, non-overlapping layer: parent codes that are present in the
appendix but are marked as requiring a more specific Vietnam site/status code.

Every mapping below is backed by both the official Vietnam description and the
local record context.  The probe changes candidates only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from . import turn2_v19
from . import turn2_v24
from . import turn2_v9 as base


# Parent codes whose intended child is consistent across every occurrence in
# the V35 output.
VIETNAM_ICD_STATIC_SPECIFICITY: dict[str, str] = {
    # Epidural haemorrhage; neither duplicated trauma record describes an open
    # intracranial wound.
    "S06.4": "S06.40",
    # The two duplicated gout consultations describe tophi at finger and toe
    # joints, so the Vietnam "multiple sites" extension applies.
    "M10.9": "M10.90",
    # No anatomical site is stated for pseudogout, rheumatoid arthritis or
    # osteoporosis.
    "M11.2": "M11.29",
    "M06.9": "M06.99",
    # The source only says "loãng xương"; it does not support V35's
    # postmenopausal parent M81.0.
    "M81.0": "M81.99",
    # The renal-artery stenosis record contains no gangrene.
    "I70.1": "I70.10",
    # "Nhiễm khuẩn đường tiêu hóa" explicitly supplies infectious origin.
    "A09": "A09.0",
}


# M86.9 needs document context: chronicity and anatomical site differ between
# records even though the extracted surface is often just "viêm xương tủy".
OSTEOMYELITIS_BY_RECORD: dict[str, str] = {
    # No chronicity or site is stated.
    "59": "M86.99",
    # Foot radiograph; chronicity unspecified.
    "85": "M86.97",
    # Chronic osteomyelitis is repeated throughout the encounter.
    "92": "M86.69",
    # Listed under chronic medical conditions; site unspecified.
    "99": "M86.69",
}


def apply_vietnam_specificity(
    output: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Replace reviewed parent ICD candidates without changing entity keys."""

    changes: list[dict] = []
    for record_id, entities in output.items():
        for entity_index, entity in enumerate(entities):
            candidates = entity.get("candidates")
            if not isinstance(candidates, list):
                continue
            for candidate_index, old_code in enumerate(candidates):
                new_code = VIETNAM_ICD_STATIC_SPECIFICITY.get(old_code)
                if old_code == "M86.9":
                    new_code = OSTEOMYELITIS_BY_RECORD.get(record_id)
                if new_code is None or new_code == old_code:
                    continue
                candidates[candidate_index] = new_code
                changes.append(
                    {
                        "record_id": record_id,
                        "entity_index": entity_index,
                        "text": entity["text"],
                        "old_code": old_code,
                        "new_code": new_code,
                    }
                )
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
    output, changes = apply_vietnam_specificity(control)
    if len(changes) != 25:
        raise ValueError(f"Expected 25 candidate changes, found {len(changes)}")

    after_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in output.items()
    }
    if before_keys != after_keys:
        raise AssertionError("V36 must not change entity spans or types")
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    change_counts: dict[str, int] = {}
    for change in changes:
        key = f"{change['old_code']}->{change['new_code']}"
        change_counts[key] = change_counts.get(key, 0) + 1
    return {
        "version": "D2-V36-v35-vietnam-icd-specificity-probe",
        "control": str(control_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_changes": 0,
        "span_changes": 0,
        "type_changes": 0,
        "candidate_changes": len(changes),
        "candidate_change_counts": change_counts,
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
