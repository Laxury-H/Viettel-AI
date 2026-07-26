#!/usr/bin/env python3
"""Recover accepted symptom surfaces from exact repeated clinical lines."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from . import turn2_v18
from . import turn2_v19
from . import turn2_v24
from . import turn2_v27
from . import turn2_v9 as base


SYMPTOM_TYPE = "TRIỆU_CHỨNG"
MINIMUM_ACCEPTED_OCCURRENCES = 2


def normalized_surface(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def derive_repeated_surface_additions(
    texts: dict[str, str],
    control: dict[str, list[dict]],
) -> list[turn2_v27.RepeatedLineAddition]:
    """Find missing accepted symptoms inside lines repeated across records."""

    counts = Counter(
        normalized_surface(entity["text"])
        for entities in control.values()
        for entity in entities
        if (
            entity["type"] == SYMPTOM_TYPE
            and len(str(entity["text"]).strip()) >= 4
        )
    )
    accepted_in_records: dict[str, set[str]] = defaultdict(set)
    for record_id, entities in control.items():
        for entity in entities:
            if entity["type"] == SYMPTOM_TYPE:
                accepted_in_records[normalized_surface(entity["text"])].add(
                    record_id
                )

    groups: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    for record_id, text in texts.items():
        for line, start, end in turn2_v18.line_occurrences(text):
            groups[line].append((record_id, start, end))

    proposals: set[turn2_v27.RepeatedLineAddition] = set()
    for line, occurrences in groups.items():
        if len({record_id for record_id, _, _ in occurrences}) < 2:
            continue
        for record_id, line_start, line_end in occurrences:
            line_text = texts[record_id][line_start:line_end]
            normalized = base.NormalizedText(line_text)
            for surface, count in counts.items():
                if count < MINIMUM_ACCEPTED_OCCURRENCES:
                    continue
                for span in normalized.literal_spans(
                    surface,
                    boundary=base.should_use_boundary(
                        surface,
                        SYMPTOM_TYPE,
                    ),
                ):
                    start = line_start + span.start
                    end = line_start + span.end
                    if any(
                        start < entity["position"][1]
                        and entity["position"][0] < end
                        for entity in control[record_id]
                    ):
                        continue
                    proposals.add(
                        turn2_v27.RepeatedLineAddition(
                            record_id=record_id,
                            start=start,
                            end=end,
                            entity_type=SYMPTOM_TYPE,
                            surface=texts[record_id][start:end],
                            source_record_ids=tuple(
                                sorted(
                                    accepted_in_records[surface],
                                    key=int,
                                )
                            ),
                        )
                    )
    return sorted(
        proposals,
        key=lambda item: (int(item.record_id), item.start, item.end),
    )


def run(input_dir: Path, control_zip: Path, output_zip: Path) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    control = turn2_v19.load_submission(control_zip)
    if set(control) != set(texts):
        raise ValueError("Control record IDs do not match input")

    additions = derive_repeated_surface_additions(texts, control)
    if len(additions) != 8:
        raise ValueError(
            f"Expected eight repeated-surface additions, found {len(additions)}"
        )
    output, changes = turn2_v27.apply_repeated_additions(
        texts,
        control,
        additions,
    )
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V28-v27-repeated-neurologic-recall",
        "control": str(control_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "changed_records": len({change["record_id"] for change in changes}),
        "repeated_surface_additions": len(changes),
        "changes": changes,
        "score_expectation": {
            "confirmed_control": 39.3762,
            "target_range": [39.40, 39.44],
            "status": "unscored_high_recall_batch",
        },
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
