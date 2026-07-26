#!/usr/bin/env python3
"""Audit entity consistency inside exact clinical lines repeated across records."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from src.clinical_mentions import turn2_v18
from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v9 as base


def entity_payload(entity: dict) -> dict:
    payload = {
        "text": entity["text"],
        "type": entity["type"],
        "position": entity["position"],
        "assertions": entity["assertions"],
    }
    if "candidates" in entity:
        payload["candidates"] = entity["candidates"]
    return payload


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
        for line, start, end in turn2_v18.line_occurrences(text):
            groups[line].append((record_id, start, end))

    findings: list[dict] = []
    for line, occurrences in groups.items():
        if len({record_id for record_id, _, _ in occurrences}) < 2:
            continue

        entities_by_occurrence: dict[tuple[str, int, int], list[dict]] = {}
        signature_sources: dict[tuple[int, int, str], list[tuple[str, int]]] = (
            defaultdict(list)
        )
        for record_id, line_start, line_end in occurrences:
            key = (record_id, line_start, line_end)
            contained = [
                entity
                for entity in control[record_id]
                if (
                    line_start
                    <= entity["position"][0]
                    < entity["position"][1]
                    <= line_end
                )
            ]
            entities_by_occurrence[key] = contained
            for entity in contained:
                signature = (
                    entity["position"][0] - line_start,
                    entity["position"][1] - line_start,
                    entity["type"],
                )
                signature_sources[signature].append((record_id, line_start))

        for signature, sources in signature_sources.items():
            relative_start, relative_end, entity_type = signature
            if len({record_id for record_id, _ in sources}) < 1:
                continue
            source_record_ids = sorted(
                {record_id for record_id, _ in sources},
                key=int,
            )
            for record_id, line_start, line_end in occurrences:
                target_start = line_start + relative_start
                target_end = line_start + relative_end
                if not line_start <= target_start < target_end <= line_end:
                    continue
                target_entities = entities_by_occurrence[
                    (record_id, line_start, line_end)
                ]
                exact = [
                    entity
                    for entity in target_entities
                    if (
                        entity["position"] == [target_start, target_end]
                        and entity["type"] == entity_type
                    )
                ]
                if exact:
                    source_entities = []
                    for source_record_id, source_line_start in sources:
                        source_start = source_line_start + relative_start
                        source_end = source_line_start + relative_end
                        source_entities.extend(
                            entity
                            for entity in control[source_record_id]
                            if (
                                entity["position"] == [
                                    source_start,
                                    source_end,
                                ]
                                and entity["type"] == entity_type
                            )
                        )
                    field_variants = {
                        (
                            tuple(entity["assertions"]),
                            tuple(entity.get("candidates", [])),
                        )
                        for entity in source_entities
                    }
                    target_fields = (
                        tuple(exact[0]["assertions"]),
                        tuple(exact[0].get("candidates", [])),
                    )
                    if len(field_variants) > 1 and target_fields in field_variants:
                        findings.append(
                            {
                                "action": "field_conflict",
                                "record_id": record_id,
                                "line_start": line_start,
                                "line": line,
                                "entity": entity_payload(exact[0]),
                                "variants": [
                                    {
                                        "assertions": list(assertions),
                                        "candidates": list(candidates),
                                    }
                                    for assertions, candidates in sorted(
                                        field_variants
                                    )
                                ],
                                "source_record_ids": source_record_ids,
                            }
                        )
                    continue

                overlapping = [
                    entity
                    for entity in target_entities
                    if (
                        entity["type"] == entity_type
                        and target_start < entity["position"][1]
                        and entity["position"][0] < target_end
                    )
                ]
                findings.append(
                    {
                        "action": (
                            "boundary_conflict" if overlapping else "missing"
                        ),
                        "record_id": record_id,
                        "line_start": line_start,
                        "line": line,
                        "proposed": {
                            "text": texts[record_id][target_start:target_end],
                            "type": entity_type,
                            "position": [target_start, target_end],
                        },
                        "overlapping": [
                            entity_payload(entity) for entity in overlapping
                        ],
                        "source_record_ids": source_record_ids,
                    }
                )

    unique: dict[tuple, dict] = {}
    for finding in findings:
        proposed = finding.get("proposed", finding.get("entity", {}))
        position = proposed.get("position", [-1, -1])
        key = (
            finding["action"],
            finding["record_id"],
            position[0],
            position[1],
            proposed.get("type", ""),
            finding["line_start"],
        )
        unique[key] = finding
    return sorted(
        unique.values(),
        key=lambda item: (
            item["action"],
            int(item["record_id"]),
            item.get("proposed", item.get("entity", {}))["position"][0],
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
    result = analyze(args.input, args.control_zip)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")


if __name__ == "__main__":
    main()
