#!/usr/bin/env python3
"""Rank high-confidence teacher spans that are absent from a submission."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path


def normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold().strip()


def load_submission(path: Path) -> dict[str, list[dict]]:
    records: dict[str, list[dict]] = {}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.startswith("output/") and name.endswith(".json"):
                records[Path(name).stem] = json.loads(
                    archive.read(name).decode("utf-8")
                )
    return records


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--teacher-cache", type=Path, required=True)
    parser.add_argument("--type", default="CHẨN_ĐOÁN")
    parser.add_argument("--minimum", type=float, default=0.98)
    parser.add_argument(
        "--non-overlap",
        action="store_true",
        help="Exclude teacher spans that overlap an existing clinical entity.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    submission = load_submission(args.submission)
    payload = json.loads(args.teacher_cache.read_text(encoding="utf-8"))
    predictions = payload.get("records", payload)
    groups: dict[str, list[dict]] = defaultdict(list)
    for record_id, spans in predictions.items():
        text = (args.input / f"{record_id}.txt").read_text(encoding="utf-8")
        existing = {
            (
                int(entity["position"][0]),
                int(entity["position"][1]),
                str(entity["type"]),
            )
            for entity in submission[record_id]
        }
        existing_intervals = [
            (
                int(entity["position"][0]),
                int(entity["position"][1]),
            )
            for entity in submission[record_id]
        ]
        for span in spans:
            start, end = int(span["start"]), int(span["end"])
            entity_type = str(span["type"])
            confidence = float(span["confidence"])
            if (
                entity_type != args.type
                or confidence < args.minimum
                or (start, end, entity_type) in existing
                or (
                    args.non_overlap
                    and any(
                        start < existing_end and existing_start < end
                        for existing_start, existing_end in existing_intervals
                    )
                )
            ):
                continue
            surface = text[start:end]
            left = max(0, text.rfind("\n", 0, start) + 1)
            right_newline = text.find("\n", end)
            right = len(text) if right_newline < 0 else right_newline
            groups[normalize(surface)].append(
                {
                    "record": record_id,
                    "surface": surface,
                    "confidence": confidence,
                    "context": text[left:right].strip(),
                }
            )

    rows = []
    for normalized, mentions in groups.items():
        rows.append(
            {
                "surface": mentions[0]["surface"],
                "normalized": normalized,
                "count": len(mentions),
                "minimum_confidence": min(
                    mention["confidence"] for mention in mentions
                ),
                "mean_confidence": sum(
                    mention["confidence"] for mention in mentions
                )
                / len(mentions),
                "records": "|".join(mention["record"] for mention in mentions),
                "context": mentions[0]["context"],
            }
        )
    rows.sort(
        key=lambda row: (
            -int(row["count"]),
            -float(row["minimum_confidence"]),
            str(row["normalized"]),
        )
    )

    fieldnames = [
        "surface",
        "normalized",
        "count",
        "minimum_confidence",
        "mean_confidence",
        "records",
        "context",
    ]
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        handle = args.output.open("w", encoding="utf-8", newline="")
    else:
        handle = sys.stdout
    with handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
