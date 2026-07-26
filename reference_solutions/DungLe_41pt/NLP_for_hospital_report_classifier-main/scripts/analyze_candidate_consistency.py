#!/usr/bin/env python3
"""Audit ICD-10/RxNorm candidate consistency for repeated mention surfaces."""

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


def normalize_surface(value: str) -> str:
    value = unicodedata.normalize("NFC", value).casefold()
    return re.sub(r"\s+", " ", value).strip()


def compact_context(text: str, start: int, end: int, radius: int = 70) -> str:
    return " ".join(
        text[max(0, start - radius) : min(len(text), end + radius)].split()
    )


def analyze(input_dir: Path, control_zip: Path) -> dict:
    texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted(input_dir.glob("*.txt"), key=base.natural_key)
    }
    control = turn2_v19.load_submission(control_zip)
    if set(texts) != set(control):
        raise ValueError("Control record IDs do not match input")

    occurrences: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for record_id in sorted(control, key=int):
        text = texts[record_id]
        for entity in control[record_id]:
            if entity["type"] not in NORMALIZED_TYPES:
                continue
            start, end = entity["position"]
            occurrences[
                (str(entity["type"]), normalize_surface(entity["text"]))
            ].append(
                {
                    "record_id": record_id,
                    "text": entity["text"],
                    "position": entity["position"],
                    "candidates": entity["candidates"],
                    "context": compact_context(text, start, end),
                }
            )

    inconsistent: list[dict] = []
    repeated: list[dict] = []
    for (entity_type, surface), items in occurrences.items():
        candidate_counts = Counter(
            tuple(item["candidates"]) for item in items
        )
        summary = {
            "type": entity_type,
            "surface": surface,
            "occurrences": len(items),
            "record_count": len({item["record_id"] for item in items}),
            "candidate_sets": [
                {"candidates": list(candidates), "count": count}
                for candidates, count in candidate_counts.most_common()
            ],
            "items": items,
        }
        if len(candidate_counts) > 1:
            inconsistent.append(summary)
        if len(items) > 1:
            repeated.append(summary)

    sorter = lambda item: (
        -item["record_count"],
        -item["occurrences"],
        item["type"],
        item["surface"],
    )
    return {
        "inconsistent": sorted(inconsistent, key=sorter),
        "repeated": sorted(repeated, key=sorter),
        "surface_count": len(occurrences),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--control-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.input, args.control_zip)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")


if __name__ == "__main__":
    main()
