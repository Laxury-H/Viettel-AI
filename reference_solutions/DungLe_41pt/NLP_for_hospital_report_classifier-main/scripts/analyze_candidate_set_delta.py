#!/usr/bin/env python3
"""Compare candidate changes at both entity and record-set granularity.

Leaderboard experiments are authored as entity edits, but repeated entities
can collapse to the same candidate set inside one record.  This audit reports
both views so occurrence counts are not mistaken for independent evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.clinical_mentions import turn2_v19


NORMALIZED_TYPES = ("CHẨN_ĐOÁN", "THUỐC")


def entity_key(entity: dict) -> tuple[int, int, str]:
    return (
        int(entity["position"][0]),
        int(entity["position"][1]),
        str(entity["type"]),
    )


def candidate_set(entities: list[dict], entity_type: str) -> set[str]:
    return {
        candidate
        for entity in entities
        if entity["type"] == entity_type
        for candidate in entity.get("candidates", [])
    }


def analyze(control_zip: Path, candidate_zip: Path) -> dict:
    control = turn2_v19.load_submission(control_zip)
    candidate = turn2_v19.load_submission(candidate_zip)
    if set(control) != set(candidate):
        raise ValueError("Submission record IDs do not match")

    entity_changes: list[dict] = []
    record_set_changes: list[dict] = []
    for record_id in sorted(control, key=int):
        before_map = {
            entity_key(entity): entity for entity in control[record_id]
        }
        after_map = {
            entity_key(entity): entity for entity in candidate[record_id]
        }
        for key in sorted(before_map.keys() & after_map.keys()):
            before = before_map[key]
            after = after_map[key]
            if before.get("candidates") == after.get("candidates"):
                continue
            entity_changes.append(
                {
                    "record_id": record_id,
                    "text": before["text"],
                    "type": before["type"],
                    "position": list(before["position"]),
                    "before": list(before.get("candidates", [])),
                    "after": list(after.get("candidates", [])),
                }
            )

        for entity_type in NORMALIZED_TYPES:
            before_set = candidate_set(control[record_id], entity_type)
            after_set = candidate_set(candidate[record_id], entity_type)
            if before_set == after_set:
                continue
            record_set_changes.append(
                {
                    "record_id": record_id,
                    "type": entity_type,
                    "before_size": len(before_set),
                    "after_size": len(after_set),
                    "removed": sorted(before_set - after_set),
                    "added": sorted(after_set - before_set),
                }
            )

    return {
        "control": str(control_zip.resolve()),
        "candidate": str(candidate_zip.resolve()),
        "records": len(control),
        "entity_candidate_changes": len(entity_changes),
        "record_candidate_set_changes": len(record_set_changes),
        "record_candidate_codes_removed": sum(
            len(change["removed"]) for change in record_set_changes
        ),
        "record_candidate_codes_added": sum(
            len(change["added"]) for change in record_set_changes
        ),
        "entity_changes": entity_changes,
        "record_set_changes": record_set_changes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("control", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = analyze(args.control, args.candidate)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")


if __name__ == "__main__":
    main()
