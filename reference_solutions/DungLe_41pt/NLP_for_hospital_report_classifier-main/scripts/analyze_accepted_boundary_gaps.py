#!/usr/bin/env python3
"""Find short symptom boundaries where a full surface is accepted elsewhere."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v9 as base


SYMPTOM_TYPE = "TRIỆU_CHỨNG"


def normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def context(text: str, start: int, end: int) -> str:
    left = max(text.rfind("\n", 0, start), text.rfind(".", 0, start))
    right_positions = [
        position
        for position in (text.find("\n", end), text.find(".", end))
        if position >= 0
    ]
    right = min([len(text), *right_positions])
    return " ".join(text[left + 1 : right].split())


def analyze(
    input_dir: Path,
    control_zip: Path,
    *,
    minimum_occurrences: int,
) -> list[dict]:
    texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted(input_dir.glob("*.txt"), key=base.natural_key)
    }
    control = turn2_v19.load_submission(control_zip)
    if set(texts) != set(control):
        raise ValueError("Control record IDs do not match input")

    counts = Counter(
        normalize(entity["text"])
        for entities in control.values()
        for entity in entities
        if (
            entity["type"] == SYMPTOM_TYPE
            and len(str(entity["text"]).strip()) >= 5
        )
    )
    accepted_records: dict[str, set[str]] = defaultdict(set)
    for record_id, entities in control.items():
        for entity in entities:
            if entity["type"] == SYMPTOM_TYPE:
                accepted_records[normalize(entity["text"])].add(record_id)

    proposals: dict[tuple[str, int, int, int, int], dict] = {}
    for record_id in sorted(texts, key=int):
        text = texts[record_id]
        normalized = base.NormalizedText(text)
        symptoms = [
            entity
            for entity in control[record_id]
            if entity["type"] == SYMPTOM_TYPE
        ]
        for surface, count in counts.items():
            if count < minimum_occurrences:
                continue
            for span in normalized.literal_spans(
                surface,
                boundary=base.should_use_boundary(surface, SYMPTOM_TYPE),
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
                current_start, current_end = current["position"]
                if not (
                    span.start <= current_start
                    and span.end >= current_end
                    and (
                        span.start < current_start
                        or span.end > current_end
                    )
                ):
                    continue
                proposals[
                    (
                        record_id,
                        current_start,
                        current_end,
                        span.start,
                        span.end,
                    )
                ] = {
                    "accepted_occurrences": count,
                    "accepted_record_count": len(
                        accepted_records[surface]
                    ),
                    "accepted_record_ids": sorted(
                        accepted_records[surface],
                        key=int,
                    ),
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
            -item["accepted_record_count"],
            -item["accepted_occurrences"],
            int(item["record_id"]),
            item["after"]["position"][0],
            -len(item["after"]["text"]),
        ),
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--control-zip", type=Path, required=True)
    parser.add_argument("--minimum-occurrences", type=int, default=2)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(
        args.input,
        args.control_zip,
        minimum_occurrences=args.minimum_occurrences,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")


if __name__ == "__main__":
    main()
