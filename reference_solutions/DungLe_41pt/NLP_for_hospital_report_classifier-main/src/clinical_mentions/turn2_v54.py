#!/usr/bin/env python3
"""Complete explicit past-temporality assertions on confirmed V53.

V54 covers two reviewed Vietnamese constructions:

* record 4 repeats six already-known historical concepts under the literal
  cue ``Triệu chứng cách đây vài năm``;
* record 69 denies two past concepts with ``đã bị ... trước đó``.  These
  mentions already carry ``isNegated`` and therefore need the compatible
  second assertion ``isHistorical``.

Every target surface also has an earlier occurrence with ``isHistorical`` in
the same record.  V54 changes assertion arrays only and preserves each mention
position independently.
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
PAST_SYMPTOM_LINE = re.compile(
    r"(?i)\btriệu\s+chứng\s+cách\s+đây\s+vài\s+năm\b"
)
NEGATED_PAST_LINE = re.compile(
    r"(?i)\bkhông\s+xác\s+nhận\s+đã\s+bị\b"
    r".*\btrước\s+đó\b.*\bkhông\s+xác\s+nhận\s+có\b"
)
EXPECTED_TARGETS = {
    ("4", 809, 817, "buồn nôn"),
    ("4", 821, 830, "tiêu chảy"),
    ("4", 1244, 1252, "buồn nôn"),
    ("4", 1256, 1265, "tiêu chảy"),
    ("4", 1277, 1302, "hội chứng ruột kích thích"),
    ("4", 1314, 1327, "loét tá tràng"),
    ("69", 555, 563, "trầm cảm"),
    ("69", 595, 607, "ý định tự tử"),
}


def ordered_assertions(values: set[str]) -> list[str]:
    """Return assertions in stable schema order."""

    return [value for value in ASSERTION_ORDER if value in values]


def line_containing(text: str, start: int, end: int) -> str:
    """Return the raw line containing an entity span."""

    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end < 0:
        line_end = len(text)
    return text[line_start:line_end]


def complete_explicit_past_assertions(
    texts: dict[str, str],
    control: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Add historical only for reviewed explicit-past mention positions."""

    output = copy.deepcopy(control)
    changes: list[dict] = []
    for record_id in sorted(output, key=int):
        source = texts[record_id]
        historical_surfaces = {
            (entity["type"], entity["text"].casefold())
            for entity in output[record_id]
            if "isHistorical" in entity.get("assertions", [])
        }
        for entity in output[record_id]:
            target = (
                record_id,
                *entity["position"],
                entity["text"],
            )
            if target not in EXPECTED_TARGETS:
                continue

            start, end = entity["position"]
            line = line_containing(source, start, end)
            assertions = set(entity.get("assertions", []))
            if record_id == "4":
                if PAST_SYMPTOM_LINE.search(line) is None:
                    raise AssertionError(
                        f"Record-4 target lost explicit past cue: {line!r}"
                    )
            elif record_id == "69":
                if (
                    "isNegated" not in assertions
                    or NEGATED_PAST_LINE.search(line) is None
                ):
                    raise AssertionError(
                        f"Record-69 target lost negated-past cue: {line!r}"
                    )

            same_surface = (entity["type"], entity["text"].casefold())
            if same_surface not in historical_surfaces:
                raise AssertionError(
                    "Every V54 target must have same-record historical "
                    f"evidence: {target}"
                )

            before = ordered_assertions(assertions)
            entity["assertions"] = ordered_assertions(
                assertions | {"isHistorical"}
            )
            changes.append(
                {
                    "record_id": record_id,
                    "text": entity["text"],
                    "type": entity["type"],
                    "position": list(entity["position"]),
                    "before_assertions": before,
                    "after_assertions": list(entity["assertions"]),
                    "line": " ".join(line.split()),
                    "reason": (
                        "same_record_surface_under_explicit_past_cue"
                    ),
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

    output, changes = complete_explicit_past_assertions(texts, control)
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
            f"Expected eight reviewed temporal changes, found {changes}"
        )

    for record_id, before_entities in control.items():
        if len(output[record_id]) != len(before_entities):
            raise AssertionError("V54 must preserve every mention")
        for before, after in zip(before_entities, output[record_id]):
            if turn2_v24.entity_key(before) != turn2_v24.entity_key(after):
                raise AssertionError("V54 must preserve spans and types")
            if before.get("candidates") != after.get("candidates"):
                raise AssertionError("V54 must preserve candidates")
            target = (
                record_id,
                *before["position"],
                before["text"],
            )
            if target not in EXPECTED_TARGETS and before != after:
                raise AssertionError(
                    "V54 must preserve non-target entities byte-for-byte"
                )
        base.validate_record(texts[record_id], output[record_id])

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V54-v53-explicit-past-mention-temporality",
        "control": str(control_zip.resolve()),
        "confirmed_control_score": 41.9901,
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_changes": 0,
        "span_changes": 0,
        "type_changes": 0,
        "candidate_changes": 0,
        "assertion_additions": len(changes),
        "record_ids": ["4", "69"],
        "changes": changes,
        "cohorts": {
            "explicit_few_years_ago": 6,
            "negated_prior_history": 2,
        },
        "invariants": {
            "all_mentions": "preserved",
            "all_text_spans_types_candidates": "unchanged",
            "non_target_entities": "byte_for_byte_unchanged",
            "same_record_historical_evidence": "required",
        },
        "leaderboard_decision_rule": {
            "control": "V53 41.9901",
            "promote_if": (
                "total score > 41.9901 and J_assertion > 51.4432"
            ),
            "expected_invariants": (
                "WER 55.4298 and J_candidates 32.9653"
            ),
            "rollback": (
                "submission/"
                "candidate_v53_v51-explicit-medication-section-"
                "temporality.zip"
            ),
        },
        "risk": (
            "low-to-medium: all cues are explicit and have same-record "
            "historical counterparts, but hidden annotation may treat a "
            "timeline recap inside current HPI differently from history"
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
