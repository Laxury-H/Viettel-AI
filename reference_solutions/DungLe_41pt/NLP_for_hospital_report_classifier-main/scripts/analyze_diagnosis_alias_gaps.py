#!/usr/bin/env python3
"""Audit teacher-reviewed diagnosis aliases against the current control."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.clinical_mentions import turn2_v15
from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v9 as base


DIAGNOSIS_TYPE = "CHẨN_ĐOÁN"
TIERS = {
    "safe": turn2_v15.SAFE_DIAGNOSES,
    "extended": turn2_v15.EXTENDED_DIAGNOSES,
    "aggressive": turn2_v15.AGGRESSIVE_DIAGNOSES,
}


def context(text: str, start: int, end: int) -> str:
    left = max(text.rfind("\n", 0, start), text.rfind(".", 0, start))
    right_positions = [
        position
        for position in (text.find("\n", end), text.find(".", end))
        if position >= 0
    ]
    right = min([len(text), *right_positions])
    return " ".join(text[left + 1 : right].split())


def analyze(input_dir: Path, control_zip: Path, *, tier: str) -> list[dict]:
    texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted(input_dir.glob("*.txt"), key=base.natural_key)
    }
    control = turn2_v19.load_submission(control_zip)
    if set(texts) != set(control):
        raise ValueError("Control record IDs do not match input")

    gaps: dict[tuple[str, int, int, str], dict] = {}
    for record_id in sorted(texts, key=int):
        text = texts[record_id]
        normalized = base.NormalizedText(text)
        for entry in TIERS[tier]:
            for alias in entry["aliases"]:
                for span in normalized.literal_spans(
                    str(alias),
                    boundary=base.should_use_boundary(
                        str(alias),
                        DIAGNOSIS_TYPE,
                    ),
                ):
                    overlapping = [
                        entity
                        for entity in control[record_id]
                        if (
                            span.start < entity["position"][1]
                            and entity["position"][0] < span.end
                        )
                    ]
                    exact = [
                        entity
                        for entity in overlapping
                        if (
                            entity["type"] == DIAGNOSIS_TYPE
                            and entity["position"] == [span.start, span.end]
                        )
                    ]
                    if exact:
                        continue
                    action = "add" if not overlapping else "overlap"
                    gaps[(record_id, span.start, span.end, str(alias))] = {
                        "record_id": record_id,
                        "action": action,
                        "text": text[span.start : span.end],
                        "position": [span.start, span.end],
                        "candidate": entry["code"],
                        "overlapping": overlapping,
                        "context": context(text, span.start, span.end),
                    }
    return sorted(
        gaps.values(),
        key=lambda item: (
            int(item["record_id"]),
            item["position"][0],
            item["position"][1],
        ),
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--control-zip", type=Path, required=True)
    parser.add_argument("--tier", choices=sorted(TIERS), required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.input, args.control_zip, tier=args.tier)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")


if __name__ == "__main__":
    main()
