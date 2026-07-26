#!/usr/bin/env python3
"""Find symptom annotation gaps inside exact repeated clauses."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v9 as base


SYMPTOM_TYPE = "TRIỆU_CHỨNG"


def clause_occurrences(text: str) -> list[tuple[str, int, int]]:
    occurrences: list[tuple[str, int, int]] = []
    for match in re.finditer(r"[^.!?\r\n]+", text):
        raw = match.group(0)
        value = raw.strip()
        if len(value) < 25:
            continue
        leading = len(raw) - len(raw.lstrip())
        start = match.start() + leading
        occurrences.append((value, start, start + len(value)))
    return occurrences


def analyze(input_dir: Path, control_zip: Path) -> list[dict]:
    texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted(input_dir.glob("*.txt"), key=base.natural_key)
    }
    control = turn2_v19.load_submission(control_zip)
    if set(texts) != set(control):
        raise ValueError("Control record IDs do not match input")

    groups: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    for record_id, text in texts.items():
        for clause, start, end in clause_occurrences(text):
            groups[clause].append((record_id, start, end))

    proposals: dict[tuple[str, int, int, str], dict] = {}
    for clause, occurrences in groups.items():
        if len({record_id for record_id, _, _ in occurrences}) < 2:
            continue
        signatures: dict[tuple[int, int, str], set[str]] = defaultdict(set)
        for record_id, clause_start, clause_end in occurrences:
            for entity in control[record_id]:
                start, end = entity["position"]
                if (
                    entity["type"] == SYMPTOM_TYPE
                    and clause_start <= start < end <= clause_end
                ):
                    signatures[
                        (
                            start - clause_start,
                            end - clause_start,
                            str(entity["text"]),
                        )
                    ].add(record_id)
        for (relative_start, relative_end, surface), sources in signatures.items():
            for record_id, clause_start, clause_end in occurrences:
                start = clause_start + relative_start
                end = clause_start + relative_end
                if not clause_start <= start < end <= clause_end:
                    continue
                if texts[record_id][start:end] != surface:
                    continue
                if any(
                    start < entity["position"][1]
                    and entity["position"][0] < end
                    for entity in control[record_id]
                ):
                    continue
                historical, family = base.section_states(texts[record_id])
                entity = base.make_entity(
                    texts[record_id],
                    base.Span(start, end),
                    SYMPTOM_TYPE,
                    historical,
                    family,
                )
                proposals[(record_id, start, end, surface)] = {
                    "record_id": record_id,
                    "text": surface,
                    "position": [start, end],
                    "assertions": entity["assertions"],
                    "source_record_ids": sorted(sources, key=int),
                    "clause": clause,
                }
    return sorted(
        proposals.values(),
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
