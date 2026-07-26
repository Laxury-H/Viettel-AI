#!/usr/bin/env python3
"""Compose the independently positive stable boundary group onto V24.

The five expansions are derived from two immutable, model-generated reference
artifacts rather than from record IDs or handwritten offsets:

* V17 ``boundary-985-single`` is the reference base.
* V17 ``boundary-98-single-stable`` contains a stable expansion group.

Only strict one-to-one symptom supersets are transferred.  The contraction
``Nôn mửa`` -> ``Nôn`` is deliberately excluded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from . import turn2_v19
from . import turn2_v24


SYMPTOM_TYPE = "TRIỆU_CHỨNG"


@dataclass(frozen=True)
class BoundaryExpansion:
    record_id: str
    before_key: tuple[int, int, str]
    after_text: str
    after_position: tuple[int, int]


def overlaps(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def is_strict_superset(before: dict, after: dict) -> bool:
    before_start, before_end = before["position"]
    after_start, after_end = after["position"]
    return (
        before["type"] == after["type"] == SYMPTOM_TYPE
        and after_start <= before_start
        and after_end >= before_end
        and (after_start < before_start or after_end > before_end)
    )


def derive_stable_expansions(
    reference_base: dict[str, list[dict]],
    reference_candidate: dict[str, list[dict]],
) -> list[BoundaryExpansion]:
    if set(reference_base) != set(reference_candidate):
        raise ValueError("Reference record IDs do not match")

    expansions: list[BoundaryExpansion] = []
    for record_id in sorted(reference_base, key=int):
        before_by_key = {
            turn2_v24.entity_key(entity): entity
            for entity in reference_base[record_id]
        }
        after_by_key = {
            turn2_v24.entity_key(entity): entity
            for entity in reference_candidate[record_id]
        }
        removed = [
            before_by_key[key] for key in before_by_key.keys() - after_by_key.keys()
        ]
        added = [
            after_by_key[key] for key in after_by_key.keys() - before_by_key.keys()
        ]
        for after in added:
            overlapping = [
                before
                for before in removed
                if overlaps(
                    tuple(before["position"]),
                    tuple(after["position"]),
                )
                and before["type"] == after["type"]
            ]
            if len(overlapping) != 1:
                continue
            before = overlapping[0]
            if not is_strict_superset(before, after):
                continue
            expansions.append(
                BoundaryExpansion(
                    record_id=record_id,
                    before_key=turn2_v24.entity_key(before),
                    after_text=str(after["text"]),
                    after_position=tuple(map(int, after["position"])),
                )
            )
    return expansions


def apply_expansions(
    control: dict[str, list[dict]],
    expansions: list[BoundaryExpansion],
) -> tuple[dict[str, list[dict]], list[dict]]:
    by_record: dict[str, list[BoundaryExpansion]] = {}
    for expansion in expansions:
        by_record.setdefault(expansion.record_id, []).append(expansion)

    output: dict[str, list[dict]] = {}
    changes: list[dict] = []
    applied: set[BoundaryExpansion] = set()
    for record_id in sorted(control, key=int):
        replacements = {
            expansion.before_key: expansion
            for expansion in by_record.get(record_id, [])
        }
        entities: list[dict] = []
        for source in control[record_id]:
            key = turn2_v24.entity_key(source)
            expansion = replacements.get(key)
            if expansion is None:
                entities.append(dict(source))
                continue
            refined = dict(source)
            refined["text"] = expansion.after_text
            refined["position"] = list(expansion.after_position)
            entities.append(refined)
            applied.add(expansion)
            changes.append(
                {
                    "record_id": record_id,
                    "before": {
                        "text": source["text"],
                        "position": source["position"],
                    },
                    "after": {
                        "text": refined["text"],
                        "position": refined["position"],
                    },
                    "type": refined["type"],
                    "assertions": refined["assertions"],
                }
            )
        keys = [turn2_v24.entity_key(entity) for entity in entities]
        if len(keys) != len(set(keys)):
            raise ValueError(
                f"Boundary expansion created a duplicate in record {record_id}"
            )
        output[record_id] = entities

    missing = set(expansions) - applied
    if missing:
        raise ValueError(f"Control is missing {len(missing)} reference boundaries")
    return output, changes


def run(
    control_zip: Path,
    reference_base_zip: Path,
    reference_candidate_zip: Path,
    output_zip: Path,
) -> dict:
    control = turn2_v19.load_submission(control_zip)
    reference_base = turn2_v19.load_submission(reference_base_zip)
    reference_candidate = turn2_v19.load_submission(reference_candidate_zip)
    expansions = derive_stable_expansions(reference_base, reference_candidate)
    if len(expansions) != 5:
        raise ValueError(f"Expected five stable expansions, found {len(expansions)}")
    output, changes = apply_expansions(control, expansions)
    if sum(map(len, output.values())) != sum(map(len, control.values())):
        raise AssertionError("V26 changed the entity count")

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V26-v24-stable-boundary-group",
        "control": str(control_zip.resolve()),
        "reference_base": str(reference_base_zip.resolve()),
        "reference_candidate": str(reference_candidate_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "changed_records": len({change["record_id"] for change in changes}),
        "boundary_expansions": len(changes),
        "changes": changes,
        "score_projection": {
            "control": 39.3762,
            "score": 39.3803,
            "WER": 55.6927,
            "J_assertion": 51.0299,
            "J_candidates": 26.9477,
            "status": "unscored_causal_projection",
        },
        "sha256": digest,
        "zip": str(output_zip.resolve()),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-zip", type=Path, required=True)
    parser.add_argument("--reference-base-zip", type=Path, required=True)
    parser.add_argument("--reference-candidate-zip", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    summary = run(
        args.control_zip,
        args.reference_base_zip,
        args.reference_candidate_zip,
        args.zip,
    )
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
