#!/usr/bin/env python3
"""Build a Vietnamese document-archetype assertion probe on top of V35.

The base rules already handle standalone headings such as ``Tiền sử bệnh``.
This probe covers compact Vietnamese chart styles where the history cue and
clinical items share one line, plus two closely related discourse forms:

* personal history explicitly denied with ``chưa bị ... trước đó``;
* a recent, already treated infection;
* generic educational risk-factor text that mentions "family history" but
  does not describe a real relative of the current patient.

Only assertion arrays may change.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

from . import turn2_v19
from . import turn2_v24
from . import turn2_v9 as base


CLINICAL_TYPES = {"CHẨN_ĐOÁN", "THUỐC", "TRIỆU_CHỨNG"}
ASSERTION_ORDER = ("isNegated", "isFamily", "isHistorical")


def normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def ordered_assertions(values: set[str]) -> list[str]:
    return [value for value in ASSERTION_ORDER if value in values]


def repair_vietnamese_assertions(
    texts: dict[str, str],
    output: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Repair reusable Vietnamese history/family discourse structures."""

    changes: list[dict] = []
    for record_id, entities in output.items():
        text = texts[record_id]
        normalized_text = normalize(text)
        for entity_index, entity in enumerate(entities):
            if entity["type"] not in CLINICAL_TYPES:
                continue
            start, end = entity["position"]
            line_start = text.rfind("\n", 0, start) + 1
            line_end = text.find("\n", end)
            if line_end < 0:
                line_end = len(text)
            line_prefix = normalized_text[line_start:start]
            line_suffix = normalized_text[end:line_end]
            broad_prefix = normalized_text[max(0, start - 240):start]
            assertions = set(entity.get("assertions", []))
            before = ordered_assertions(assertions)

            # Compact chart form: "..., tiền sử: condition - condition".
            if (
                entity["type"] == "CHẨN_ĐOÁN"
                and re.search(r"\btiền\s+sử\s*:\s*[^.;]{0,180}$", broad_prefix)
            ):
                assertions.add("isHistorical")

            # Explicitly absent personal history: "Tiền sử bản thân: chưa bị
            # vàng da, vàng mắt trước đó".
            if (
                re.search(
                    r"\btiền\s+sử\s+bản\s+thân\s*:\s*chưa\s+bị\b"
                    r"[^.\n]{0,150}$",
                    line_prefix,
                )
                and re.match(r"[^.\n]{0,80}\btrước\s+đó\b", line_suffix)
            ):
                assertions.add("isNegated")
                assertions.add("isHistorical")

            # Recent infection described as a completed episode requiring
            # antibiotics.  A second mention in the same encounter is already
            # correctly marked historical by the existing "Đã dùng" rule.
            if (
                entity["type"] == "CHẨN_ĐOÁN"
                and re.match(
                    r"[^.\n]{0,45}\bgần\s+đây\s+cần\s+dùng\s+kháng\s+sinh\b",
                    line_suffix,
                )
            ):
                assertions.add("isHistorical")

            # "Tiền sử gia đình" in a generic educational risk-factor list is
            # a concept label, not a statement about an actual relative.
            if (
                "isFamily" in assertions
                and re.search(
                    r"\b(?:yếu\s+tố\s+nguy\s+cơ|không\s+thay\s+đổi\s+được)"
                    r"[\s\S]{0,180}\btiền\s+sử\s+gia\s+đình\b",
                    broad_prefix,
                )
            ):
                assertions.remove("isFamily")

            after = ordered_assertions(assertions)
            if after != before:
                entity["assertions"] = after
                changes.append(
                    {
                        "record_id": record_id,
                        "entity_index": entity_index,
                        "text": entity["text"],
                        "before": before,
                        "after": after,
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
    output, changes = repair_vietnamese_assertions(texts, control)
    if len(changes) != 7:
        raise ValueError(f"Expected 7 assertion changes, found {len(changes)}")

    after_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in output.items()
    }
    if before_keys != after_keys:
        raise AssertionError("V37 must not change entity spans or types")
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V37-v35-vietnam-document-archetype-assertion-probe",
        "control": str(control_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_changes": 0,
        "span_changes": 0,
        "type_changes": 0,
        "candidate_changes": 0,
        "assertion_changes": len(changes),
        "changes": changes,
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
