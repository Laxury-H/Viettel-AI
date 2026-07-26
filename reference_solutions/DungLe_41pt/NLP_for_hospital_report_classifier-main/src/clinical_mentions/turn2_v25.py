#!/usr/bin/env python3
"""Compose one conservative symptom-boundary repair onto scored V24.

The transform removes a non-clinical reporting prefix from a symptom mention
without changing its end offset, type, assertions, candidates, record count,
or entity count.  It operates on the immutable V24 ZIP, so no private input or
model cache is needed to reproduce the candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from . import turn2_v19
from . import turn2_v24


SYMPTOM_TYPE = "TRIỆU_CHỨNG"
REPORTING_PREFIX = re.compile(
    r"(?i)^(?:miệng|mồm)\s+(?:cảm\s+)?thấy\s+"
)


def trim_reporting_prefix(entity: dict) -> tuple[dict, bool]:
    """Trim a reporting prefix while preserving the exact source substring."""

    if entity.get("type") != SYMPTOM_TYPE:
        return dict(entity), False
    surface = str(entity.get("text", ""))
    match = REPORTING_PREFIX.match(surface)
    if match is None:
        return dict(entity), False

    start, end = entity["position"]
    refined = dict(entity)
    refined["text"] = surface[match.end() :]
    refined["position"] = [int(start) + match.end(), int(end)]
    return refined, True


def refine_records(
    records: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    output: dict[str, list[dict]] = {}
    changes: list[dict] = []
    for record_id in sorted(records, key=int):
        refined_entities: list[dict] = []
        seen: set[tuple[int, int, str]] = set()
        for entity in records[record_id]:
            refined, changed = trim_reporting_prefix(entity)
            key = turn2_v24.entity_key(refined)
            if key in seen:
                raise ValueError(
                    f"Boundary repair created a duplicate in record {record_id}"
                )
            seen.add(key)
            refined_entities.append(refined)
            if changed:
                changes.append(
                    {
                        "record_id": record_id,
                        "before": {
                            "text": entity["text"],
                            "position": entity["position"],
                        },
                        "after": {
                            "text": refined["text"],
                            "position": refined["position"],
                        },
                        "type": refined["type"],
                        "assertions": refined["assertions"],
                    }
                )
        output[record_id] = refined_entities
    return output, changes


def run(control_zip: Path, output_zip: Path) -> dict:
    control = turn2_v19.load_submission(control_zip)
    output, changes = refine_records(control)
    if len(changes) != 1:
        raise ValueError(
            f"Expected exactly one reporting-prefix repair, found {len(changes)}"
        )
    if sum(map(len, output.values())) != sum(map(len, control.values())):
        raise AssertionError("V25 changed the entity count")

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V25-v24-symptom-boundary-trim",
        "control": str(control_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "changed_records": len({change["record_id"] for change in changes}),
        "boundary_repairs": len(changes),
        "changes": changes,
        "score_expectation": {
            "control": 39.3762,
            "target_range_if_gold_uses_clinical_span": [39.3803, 39.3843],
            "status": "unscored_hypothesis",
        },
        "sha256": digest,
        "zip": str(output_zip.resolve()),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-zip", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    summary = run(args.control_zip, args.zip)
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
