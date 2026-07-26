#!/usr/bin/env python3
"""Build a precision-pruning probe for a malformed urinalysis translation.

Record 38 contains the literal seam::

    tổng phân tích nước tiểu có đái tháo đườngđái tháo đường

The same record already has a valid historical diagnosis mention
``Đái tháo đường típ 2``.  The two adjacent generic diabetes entities at the
urinalysis seam are therefore isolated as likely translation/type false
positives.  V51 removes only those two entities from the confirmed V45
control; it does not globally prune diabetes mentions.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

from . import turn2_v19
from . import turn2_v24
from . import turn2_v9 as base


SEAM = "tổng phân tích nước tiểu có đái tháo đườngđái tháo đường"
TARGET_SURFACE = "đái tháo đường"
TARGET_CANDIDATES = ["E11.9"]
EXPECTED_REMOVALS = 2


def normalize(value: str) -> str:
    return " ".join(
        unicodedata.normalize("NFC", value).casefold().split()
    )


def is_urinalysis_translation_false_positive(
    source: str,
    entity: dict,
) -> bool:
    """Return whether an entity is one of the two reviewed seam mentions."""

    if (
        entity["type"] != "CHẨN_ĐOÁN"
        or normalize(entity["text"]) != TARGET_SURFACE
        or entity.get("candidates") != TARGET_CANDIDATES
        or entity.get("assertions") != []
    ):
        return False
    start, end = entity["position"]
    context = source[max(0, start - 100) : min(len(source), end + 100)]
    return SEAM in normalize(context)


def prune_urinalysis_translation_false_positives(
    texts: dict[str, str],
    control: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Remove only the two diabetes entities inside the reviewed seam."""

    output = copy.deepcopy(control)
    changes: list[dict] = []
    for record_id in sorted(output, key=int):
        source = texts[record_id]
        retained: list[dict] = []
        for entity in output[record_id]:
            if not is_urinalysis_translation_false_positive(source, entity):
                retained.append(entity)
                continue
            start, end = entity["position"]
            changes.append(
                {
                    "record_id": record_id,
                    "text": entity["text"],
                    "type": entity["type"],
                    "position": list(entity["position"]),
                    "assertions": list(entity["assertions"]),
                    "candidates": list(entity["candidates"]),
                    "context": " ".join(
                        source[
                            max(0, start - 80) : min(len(source), end + 80)
                        ].split()
                    ),
                    "reason": "urinalysis_glucose_translation_type_seam",
                }
            )
        output[record_id] = retained
    return output, changes


def run(input_dir: Path, control_zip: Path, output_zip: Path) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    control = turn2_v19.load_submission(control_zip)
    if set(control) != set(texts):
        raise ValueError("Control record IDs do not match input")

    output, changes = prune_urinalysis_translation_false_positives(
        texts,
        control,
    )
    if (
        len(changes) != EXPECTED_REMOVALS
        or {change["record_id"] for change in changes} != {"38"}
    ):
        raise ValueError(
            f"Expected two record-38 removals, found {changes}"
        )

    for record_id, before_entities in control.items():
        removed_keys = {
            turn2_v24.entity_key(change)
            for change in changes
            if change["record_id"] == record_id
        }
        expected = [
            entity
            for entity in before_entities
            if turn2_v24.entity_key(entity) not in removed_keys
        ]
        if output[record_id] != expected:
            raise AssertionError(
                "V51 must preserve every non-target V45 entity byte-for-byte"
            )
        base.validate_record(texts[record_id], output[record_id])

    valid_diabetes = [
        entity
        for entity in output["38"]
        if entity["type"] == "CHẨN_ĐOÁN"
        and normalize(entity["text"]) == "đái tháo đường típ 2"
        and entity.get("candidates") == ["E11.9"]
    ]
    if len(valid_diabetes) != 1:
        raise AssertionError(
            "V51 must retain the valid record-38 type-2 diabetes diagnosis"
        )

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V51-v45-urinalysis-translation-pruning",
        "control": str(control_zip.resolve()),
        "confirmed_control_score": 41.9694,
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_removals": len(changes),
        "diagnosis_removals": len(changes),
        "record_ids": ["38"],
        "changes": changes,
        "invariants": {
            "all_non_target_entities": "unchanged",
            "valid_record_38_type_2_diabetes": "retained",
            "record_level_candidate_set": (
                "E11.9 remains through the valid type-2 diagnosis"
            ),
        },
        "causal_question": (
            "Does precision pruning of two obvious urinalysis-translation "
            "false positives improve WER/assertion alignment?"
        ),
        "leaderboard_decision_rule": {
            "control": "V45 41.9694",
            "promote_if": "total score > 41.9694",
            "expected_signal": (
                "WER should decrease and/or J_assertion should increase; "
                "J_candidates may be unchanged"
            ),
            "rollback": "submission/output.zip",
        },
        "risk": (
            "low-to-medium: raw text is malformed and the same record retains "
            "an explicit valid diabetes diagnosis, but hidden gold may still "
            "annotate literal duplicate tokens"
        ),
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
