#!/usr/bin/env python3
"""Find omitted diagnosis/drug surfaces and transfer their candidates."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v9 as base


NORMALIZED_TYPES = {"CHẨN_ĐOÁN", "THUỐC"}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFC", value).casefold()
    return re.sub(r"\s+", " ", value).strip()


def compact_context(text: str, start: int, end: int, radius: int = 100) -> str:
    left = max(text.rfind("\n", 0, start), text.rfind(".", 0, start))
    right_positions = [
        position
        for position in (text.find("\n", end), text.find(".", end))
        if position >= 0
    ]
    right = min([len(text), end + radius, *right_positions])
    return " ".join(text[max(0, left + 1) : right].split())


def analyze(
    input_dir: Path,
    control_zip: Path,
    *,
    entity_type: str,
    minimum_occurrences: int,
) -> list[dict]:
    if entity_type not in NORMALIZED_TYPES:
        raise ValueError(f"Unsupported entity type: {entity_type}")
    texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted(input_dir.glob("*.txt"), key=base.natural_key)
    }
    control = turn2_v19.load_submission(control_zip)
    if set(texts) != set(control):
        raise ValueError("Control record IDs do not match input")

    candidate_counts: dict[str, Counter[tuple[str, ...]]] = defaultdict(
        Counter
    )
    accepted_records: dict[str, set[str]] = defaultdict(set)
    for record_id, entities in control.items():
        for entity in entities:
            if entity["type"] != entity_type:
                continue
            surface = normalize(entity["text"])
            candidate_counts[surface][tuple(entity["candidates"])] += 1
            accepted_records[surface].add(record_id)

    gaps: list[dict] = []
    for record_id in sorted(texts, key=int):
        text = texts[record_id]
        historical, family = base.section_states(text)
        normalized = base.NormalizedText(text)
        for surface, sets in candidate_counts.items():
            total = sum(sets.values())
            if total < minimum_occurrences:
                continue
            for span in normalized.literal_spans(
                surface,
                boundary=base.should_use_boundary(surface, entity_type),
            ):
                if any(
                    span.start < entity["position"][1]
                    and entity["position"][0] < span.end
                    for entity in control[record_id]
                ):
                    continue
                proposed = base.make_entity(
                    text,
                    span,
                    entity_type,
                    historical,
                    family,
                )
                gaps.append(
                    {
                        "accepted_occurrences": total,
                        "accepted_record_count": len(
                            accepted_records[surface]
                        ),
                        "accepted_record_ids": sorted(
                            accepted_records[surface],
                            key=int,
                        ),
                        "record_id": record_id,
                        "text": text[span.start : span.end],
                        "type": entity_type,
                        "position": [span.start, span.end],
                        "assertions": proposed["assertions"],
                        "candidate_sets": [
                            {
                                "candidates": list(candidates),
                                "count": count,
                            }
                            for candidates, count in sets.most_common()
                        ],
                        "context": compact_context(text, span.start, span.end),
                    }
                )
    return sorted(
        gaps,
        key=lambda item: (
            -item["accepted_record_count"],
            -item["accepted_occurrences"],
            int(item["record_id"]),
            item["position"][0],
            -len(item["text"]),
        ),
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--control-zip", type=Path, required=True)
    parser.add_argument("--type", choices=sorted(NORMALIZED_TYPES), required=True)
    parser.add_argument("--minimum-occurrences", type=int, default=2)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(
        args.input,
        args.control_zip,
        entity_type=args.type,
        minimum_occurrences=args.minimum_occurrences,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")


if __name__ == "__main__":
    main()
