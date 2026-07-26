#!/usr/bin/env python3
"""Print entity-level differences between two deterministic submission ZIPs."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from pathlib import Path


def load_submission(path: Path) -> dict[str, list[dict]]:
    records: dict[str, list[dict]] = {}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.startswith("output/") or not name.endswith(".json"):
                continue
            records[Path(name).stem] = json.loads(
                archive.read(name).decode("utf-8")
            )
    return records


def key(entity: dict) -> tuple[int, int, str]:
    return (
        int(entity["position"][0]),
        int(entity["position"][1]),
        str(entity["type"]),
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("control", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--teacher-cache", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    before = load_submission(args.control)
    after = load_submission(args.candidate)
    teacher_payload = (
        json.loads(args.teacher_cache.read_text(encoding="utf-8"))
        if args.teacher_cache
        else {}
    )
    teacher = teacher_payload.get("records", teacher_payload)
    rows: list[dict] = []
    for record_id in sorted(after, key=int):
        text = (args.input / f"{record_id}.txt").read_text(encoding="utf-8")
        before_map = {key(entity): entity for entity in before[record_id]}
        after_map = {key(entity): entity for entity in after[record_id]}
        confidence = {
            (
                int(span["start"]),
                int(span["end"]),
                str(span["type"]),
            ): float(span["confidence"])
            for span in teacher.get(record_id, [])
        }
        for action, keys, source in (
            ("add", after_map.keys() - before_map.keys(), after_map),
            ("remove", before_map.keys() - after_map.keys(), before_map),
        ):
            for entity_key in sorted(keys):
                start, end, entity_type = entity_key
                left = max(0, text.rfind("\n", 0, start) + 1)
                right_newline = text.find("\n", end)
                right = len(text) if right_newline < 0 else right_newline
                entity = source[entity_key]
                assertions = "|".join(entity["assertions"])
                entity_candidates = "|".join(
                    entity.get("candidates", [])
                )
                rows.append(
                    {
                        "record": int(record_id),
                        "action": action,
                        "start": start,
                        "end": end,
                        "type": entity_type,
                        "text": text[start:end],
                        "confidence": confidence.get(entity_key, ""),
                        "previous_assertions": (
                            assertions if action == "remove" else ""
                        ),
                        "assertions": (
                            assertions if action == "add" else ""
                        ),
                        "previous_candidates": (
                            entity_candidates if action == "remove" else ""
                        ),
                        "candidates": (
                            entity_candidates if action == "add" else ""
                        ),
                        "context": text[left:right].strip(),
                    }
                )
        for entity_key in sorted(before_map.keys() & after_map.keys()):
            before_entity = before_map[entity_key]
            after_entity = after_map[entity_key]
            if before_entity == after_entity:
                continue
            start, end, entity_type = entity_key
            left = max(0, text.rfind("\n", 0, start) + 1)
            right_newline = text.find("\n", end)
            right = len(text) if right_newline < 0 else right_newline
            rows.append(
                {
                    "record": int(record_id),
                    "action": "change",
                    "start": start,
                    "end": end,
                    "type": entity_type,
                    "text": text[start:end],
                    "confidence": confidence.get(entity_key, ""),
                    "previous_assertions": "|".join(
                        before_entity["assertions"],
                    ),
                    "assertions": "|".join(after_entity["assertions"]),
                    "previous_candidates": "|".join(
                        before_entity.get("candidates", []),
                    ),
                    "candidates": "|".join(
                        after_entity.get("candidates", []),
                    ),
                    "context": text[left:right].strip(),
                }
            )

    buffer = io.StringIO()
    fieldnames = [
        "record",
        "action",
        "start",
        "end",
        "type",
        "text",
        "confidence",
        "previous_assertions",
        "assertions",
        "previous_candidates",
        "candidates",
        "context",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    output = buffer.getvalue()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8", newline="\n")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
