#!/usr/bin/env python3
"""Rank unannotated occurrences of symptom surfaces accepted elsewhere."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v15
from src.clinical_mentions import turn2_v9 as base


SYMPTOM_TYPE = "TRIỆU_CHỨNG"


def normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def compact_context(text: str, start: int, end: int, radius: int = 90) -> str:
    left = max(
        text.rfind("\n", 0, start),
        text.rfind(".", 0, start),
        start - radius,
    )
    right_candidates = [
        position
        for position in (
            text.find("\n", end),
            text.find(".", end),
            end + radius,
        )
        if position >= 0
    ]
    right = min([len(text), *right_candidates])
    return " ".join(text[max(0, left + 1) : right].split())


def analyze(
    input_dir: Path,
    control_zip: Path,
    *,
    minimum_occurrences: int,
    lexicon: str,
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
            and len(str(entity["text"]).strip()) >= 4
        )
    )
    accepted_records: dict[str, set[str]] = defaultdict(set)
    for record_id, entities in control.items():
        for entity in entities:
            if entity["type"] == SYMPTOM_TYPE:
                accepted_records[normalize(entity["text"])].add(record_id)

    surfaces = set(counts)
    if lexicon in {"precision", "safe"}:
        aliases = (
            turn2_v15.PRECISION_SYMPTOMS
            if lexicon == "precision"
            else turn2_v15.SAFE_SYMPTOMS
        )
        surfaces.update(normalize(alias) for alias in aliases)

    gaps: list[dict] = []
    for record_id in sorted(texts, key=int):
        text = texts[record_id]
        historical, family = base.section_states(text)
        for surface in surfaces:
            count = counts[surface]
            if lexicon == "accepted" and count < minimum_occurrences:
                continue
            normalized = base.NormalizedText(text)
            for span in normalized.literal_spans(
                surface,
                boundary=base.should_use_boundary(surface, SYMPTOM_TYPE),
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
                    SYMPTOM_TYPE,
                    historical,
                    family,
                )
                gaps.append(
                    {
                        "accepted_count": count,
                        "accepted_record_count": len(accepted_records[surface]),
                        "accepted_record_ids": sorted(
                            accepted_records[surface],
                            key=int,
                        ),
                        "record_id": record_id,
                        "text": text[span.start : span.end],
                        "position": [span.start, span.end],
                        "assertions": proposed["assertions"],
                        "context": compact_context(text, span.start, span.end),
                    }
                )
    return sorted(
        gaps,
        key=lambda item: (
            -item["accepted_record_count"],
            -item["accepted_count"],
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
    parser.add_argument("--minimum-occurrences", type=int, default=2)
    parser.add_argument(
        "--lexicon",
        choices=("accepted", "precision", "safe"),
        default="accepted",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    gaps = analyze(
        args.input,
        args.control_zip,
        minimum_occurrences=args.minimum_occurrences,
        lexicon=args.lexicon,
    )
    rendered = json.dumps(gaps, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")


if __name__ == "__main__":
    main()
