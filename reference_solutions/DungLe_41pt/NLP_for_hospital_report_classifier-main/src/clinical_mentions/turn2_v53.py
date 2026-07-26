#!/usr/bin/env python3
"""Complete temporality for drugs in explicit historical medication sections.

The official sample marks every medication in a pre-admission medication list
as ``isHistorical`` while leaving medication-indication symptoms unasserted.
V51 already follows that policy almost everywhere, but two medication mentions
remain unasserted inside strong, line-anchored section boundaries:

* record 57: ``Torsemide`` under ``Thuốc trước khi nhập viện``;
* record 92: ``bactrim`` under ``Thuốc đã dùng trước đây``.

V53 changes only those two assertion arrays.  It deliberately preserves every
mention, span, type and candidate, and does not propagate temporality from a
medication to its indication.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

from . import turn2_v19
from . import turn2_v24
from . import turn2_v9 as base


ASSERTION_ORDER = ("isNegated", "isFamily", "isHistorical")
MEDICATION_SECTION = re.compile(
    r"(?im)^\s*thuốc\s+(?:"
    r"trước\s+khi\s+nhập\s+viện(?:\s+lần\s+này)?"
    r"|đã\s+dùng\s+trước\s+đây"
    r"|đã\s+điều\s+trị\s+trước\s+khi\s+nhập\s+viện\s+lần\s+này"
    r")\s*:?[ \t]*(?:\n+|$)"
)
NEXT_STRONG_SECTION = re.compile(
    r"(?im)^\s*(?:"
    r"\d+\.\s+"
    r"|dị\s+ứng\s*:?"
    r"|các\s+yếu\s+tố\b"
    r"|tiền\s+sử\b"
    r"|bệnh\s+sử\b"
    r"|lý\s+do\s+nhập\s+viện\b"
    r"|cận\s+lâm\s+sàng\b"
    r"|khám\s+(?:tại|lâm\s+sàng)\b"
    r"|các\s+sự\s+kiện\b"
    r"|triệu\s+chứng\b"
    r")"
)
EXPECTED_TARGETS = {
    ("57", 224, 233, "Torsemide"),
    ("92", 321, 328, "bactrim"),
}


def ordered_assertions(values: set[str]) -> list[str]:
    """Return assertions in the repository's stable schema order."""

    return [value for value in ASSERTION_ORDER if value in values]


def medication_section_ranges(text: str) -> list[tuple[int, int, str]]:
    """Return strong historical-medication section ranges.

    Headings must start on their own line.  The range ends at the next strong
    section heading, preventing a medication-history cue from leaking across a
    Vietnamese chart/Q&A seam.
    """

    ranges: list[tuple[int, int, str]] = []
    for match in MEDICATION_SECTION.finditer(text):
        next_section = NEXT_STRONG_SECTION.search(text, match.end())
        end = next_section.start() if next_section is not None else len(text)
        ranges.append((match.end(), end, " ".join(match.group().split())))
    return ranges


def complete_historical_medication_assertions(
    texts: dict[str, str],
    control: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Add ``isHistorical`` only to drugs inside explicit target sections."""

    output = copy.deepcopy(control)
    changes: list[dict] = []
    for record_id in sorted(output, key=int):
        source = texts[record_id]
        ranges = medication_section_ranges(source)
        for entity in output[record_id]:
            if (
                entity["type"] != "THUỐC"
                or "isHistorical" in entity.get("assertions", [])
            ):
                continue
            start, end = entity["position"]
            matched_heading = next(
                (
                    heading
                    for section_start, section_end, heading in ranges
                    if section_start <= start < section_end
                ),
                None,
            )
            if matched_heading is None:
                continue

            before = list(entity.get("assertions", []))
            entity["assertions"] = ordered_assertions(
                set(before) | {"isHistorical"}
            )
            line_start = source.rfind("\n", 0, start) + 1
            line_end = source.find("\n", end)
            if line_end < 0:
                line_end = len(source)
            changes.append(
                {
                    "record_id": record_id,
                    "text": entity["text"],
                    "type": entity["type"],
                    "position": list(entity["position"]),
                    "before_assertions": before,
                    "after_assertions": list(entity["assertions"]),
                    "section_heading": matched_heading,
                    "line": " ".join(source[line_start:line_end].split()),
                    "reason": "explicit_historical_medication_section",
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

    output, changes = complete_historical_medication_assertions(texts, control)
    actual_targets = {
        (
            change["record_id"],
            *change["position"],
            change["text"],
        )
        for change in changes
    }
    if actual_targets != EXPECTED_TARGETS:
        raise ValueError(
            "Expected only the reviewed Torsemide/bactrim assertion changes; "
            f"found {changes}"
        )

    for record_id, before_entities in control.items():
        if len(output[record_id]) != len(before_entities):
            raise AssertionError("V53 must preserve every mention")
        for before, after in zip(before_entities, output[record_id]):
            if turn2_v24.entity_key(before) != turn2_v24.entity_key(after):
                raise AssertionError("V53 must preserve spans and types")
            if before.get("candidates") != after.get("candidates"):
                raise AssertionError("V53 must preserve candidates")
            if (
                (
                    record_id,
                    *before["position"],
                    before["text"],
                )
                not in EXPECTED_TARGETS
                and before != after
            ):
                raise AssertionError(
                    "V53 must preserve every non-target entity byte-for-byte"
                )
        base.validate_record(texts[record_id], output[record_id])

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V53-v51-explicit-medication-section-temporality",
        "control": str(control_zip.resolve()),
        "confirmed_control_score": 41.9878,
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_changes": 0,
        "span_changes": 0,
        "type_changes": 0,
        "candidate_changes": 0,
        "assertion_additions": len(changes),
        "record_ids": sorted(
            {change["record_id"] for change in changes},
            key=int,
        ),
        "changes": changes,
        "invariants": {
            "all_mentions": "preserved",
            "all_text_spans_types_candidates": "unchanged",
            "medication_indication_assertions": "unchanged",
            "non_target_entities": "byte_for_byte_unchanged",
        },
        "evidence": {
            "official_sample_policy": (
                "pre-admission medication entries carry isHistorical while "
                "their indication symptoms keep empty assertions"
            ),
            "within_section_consistency": (
                "the neighboring drugs in records 57 and 92 already carry "
                "isHistorical"
            ),
            "v37_precedent": (
                "a seven-change Vietnamese section/assertion batch improved "
                "J_assertion by 0.0305"
            ),
        },
        "leaderboard_decision_rule": {
            "control": "V51 41.9878",
            "promote_if": (
                "total score > 41.9878 and J_assertion > 51.4354"
            ),
            "expected_invariants": (
                "WER 55.4298 and J_candidates 32.9653"
            ),
            "rollback": "submission/output.zip",
        },
        "risk": (
            "low-to-medium: headings and entity positions are exact, but "
            "the hidden annotation may treat currently used pre-admission "
            "medications as current despite the official sample convention"
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
