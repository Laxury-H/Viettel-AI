#!/usr/bin/env python3
"""Complete exact Vietnamese ICD labels that include coding qualifiers.

This follow-up is intentionally separate from the V42 candidate-only batch.
It expands only diagnosis spans whose immediately adjacent suffix is part of
an official Vietnamese ICD label.  One expansion also changes F31.9 to F31.8;
the two J44.9 expansions keep their candidate unchanged.
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


EXACT_LABEL_SUFFIXES: dict[str, dict] = {
    "rối loạn cảm xúc lưỡng cực": {
        "suffix": " khác",
        "before_candidates": ["F31.9"],
        "after_candidates": ["F31.8"],
    },
    "bệnh phổi tắc nghẽn mạn tính": {
        "suffix": ", không xác định",
        "before_candidates": ["J44.9"],
        "after_candidates": ["J44.9"],
    },
}


def normalize_label(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold().strip()


def complete_exact_icd_label_boundaries(
    texts: dict[str, str],
    control: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Expand only an exact, immediately adjacent official-label suffix."""

    output = copy.deepcopy(control)
    changes: list[dict] = []
    for record_id, entities in output.items():
        source = texts[record_id]
        for entity in entities:
            if entity["type"] != "CHẨN_ĐOÁN":
                continue
            target = EXACT_LABEL_SUFFIXES.get(normalize_label(entity["text"]))
            if (
                target is None
                or entity.get("candidates") != target["before_candidates"]
            ):
                continue
            start, end = entity["position"]
            suffix = target["suffix"]
            if source[end : end + len(suffix)].casefold() != suffix:
                continue
            before = {
                "text": entity["text"],
                "position": list(entity["position"]),
                "candidates": list(entity["candidates"]),
            }
            entity["position"] = [start, end + len(suffix)]
            entity["text"] = source[start : end + len(suffix)]
            entity["candidates"] = list(target["after_candidates"])
            changes.append(
                {
                    "record_id": record_id,
                    "type": entity["type"],
                    "before": before,
                    "after": {
                        "text": entity["text"],
                        "position": list(entity["position"]),
                        "candidates": list(entity["candidates"]),
                    },
                    "reason": "complete_exact_official_icd_label",
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

    output, changes = complete_exact_icd_label_boundaries(texts, control)
    if len(changes) != 3:
        raise ValueError(f"Expected 3 exact-label expansions, found {len(changes)}")
    if sum(
        change["before"]["candidates"] != change["after"]["candidates"]
        for change in changes
    ) != 1:
        raise ValueError("Expected one candidate change in V43")

    for record_id in control:
        if len(output[record_id]) != len(control[record_id]):
            raise AssertionError("V43 must not add or remove entities")
        for before, after in zip(control[record_id], output[record_id]):
            if before["type"] != after["type"]:
                raise AssertionError("V43 must not change entity types")
            if before.get("assertions") != after.get("assertions"):
                raise AssertionError("V43 must not change assertions")
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V43-v42-vietnam-official-label-boundary-completion",
        "control": str(control_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_changes": 0,
        "span_changes": len(changes),
        "type_changes": 0,
        "assertion_changes": 0,
        "candidate_changes": 1,
        "changes": changes,
        "decision": "hold_until_v42_score",
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
