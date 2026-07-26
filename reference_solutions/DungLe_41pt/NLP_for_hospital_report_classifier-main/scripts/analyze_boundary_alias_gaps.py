#!/usr/bin/env python3
"""Find complete symptom aliases that strictly contain a current boundary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.clinical_mentions import turn2_v15
from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v9 as base


SYMPTOM_TYPE = "TRIỆU_CHỨNG"


def context(text: str, start: int, end: int) -> str:
    left = max(text.rfind("\n", 0, start), text.rfind(".", 0, start))
    right_positions = [
        position
        for position in (text.find("\n", end), text.find(".", end))
        if position >= 0
    ]
    right = min([len(text), *right_positions])
    return " ".join(text[left + 1 : right].split())


def analyze(input_dir: Path, control_zip: Path) -> list[dict]:
    texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted(input_dir.glob("*.txt"), key=base.natural_key)
    }
    control = turn2_v19.load_submission(control_zip)
    if set(texts) != set(control):
        raise ValueError("Control record IDs do not match input")

    proposals: dict[tuple[str, int, int], dict] = {}
    for record_id in sorted(texts, key=int):
        text = texts[record_id]
        normalized = base.NormalizedText(text)
        symptoms = [
            entity
            for entity in control[record_id]
            if entity["type"] == SYMPTOM_TYPE
        ]
        for alias in turn2_v15.BOUNDARY_SYMPTOMS:
            for span in normalized.literal_spans(
                alias,
                boundary=base.should_use_boundary(alias, SYMPTOM_TYPE),
            ):
                overlapping = [
                    entity
                    for entity in symptoms
                    if (
                        span.start < entity["position"][1]
                        and entity["position"][0] < span.end
                    )
                ]
                if len(overlapping) != 1:
                    continue
                current = overlapping[0]
                start, end = current["position"]
                if not (
                    span.start <= start
                    and span.end >= end
                    and (span.start < start or span.end > end)
                ):
                    continue
                proposals[(record_id, span.start, span.end)] = {
                    "record_id": record_id,
                    "before": {
                        "text": current["text"],
                        "position": current["position"],
                        "assertions": current["assertions"],
                    },
                    "after": {
                        "text": text[span.start : span.end],
                        "position": [span.start, span.end],
                    },
                    "context": context(text, span.start, span.end),
                }
    return sorted(
        proposals.values(),
        key=lambda item: (
            int(item["record_id"]),
            item["after"]["position"][0],
            item["after"]["position"][1],
        ),
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--control-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    proposals = analyze(args.input, args.control_zip)
    rendered = json.dumps(proposals, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")


if __name__ == "__main__":
    main()
