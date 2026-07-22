#!/usr/bin/env python3
"""Print compact diagnostics for generated entity JSON files."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=("short", "medications", "assertions", "frequencies", "lab-results"),
        required=True,
    )
    args = parser.parse_args()

    rows: list[tuple[int, str, dict, str]] = []
    for path in sorted(args.output.glob("*.json"), key=lambda item: int(item.stem)):
        record_id = int(path.stem)
        source = (args.input / f"{record_id}.txt").read_text(encoding="utf-8")
        for entity in json.loads(path.read_text(encoding="utf-8")):
            rows.append((record_id, source, entity, entity["text"]))

    if args.mode == "short":
        counts = Counter(
            (entity["type"], text.casefold())
            for _, _, entity, text in rows
            if len(text.strip()) <= 3
        )
        for (entity_type, text), count in counts.most_common():
            print(f"{count:4} {entity_type:24} {text!r}")
    elif args.mode == "frequencies":
        counts = Counter((entity["type"], text.casefold()) for _, _, entity, text in rows)
        for (entity_type, text), count in counts.most_common(150):
            print(f"{count:4} {entity_type:24} {text}")
    elif args.mode == "medications":
        for record_id, source, entity, text in rows:
            if entity["type"] != "THUỐC":
                continue
            suspicious = (
                len(text) > 60
                or "\n" in text
                or len(text.split()) > 12
                or bool(re.search(r"(?i)\b(?:tuần|tháng|năm)\s*$", text))
                or bool(re.search(r"\s\d+\s*$", text))
            )
            if suspicious:
                start, end = entity["position"]
                context = source[max(0, start - 35) : min(len(source), end + 45)].replace("\n", " ")
                print(f"{record_id}: {text!r} {entity.get('candidates')} | {context}")
    elif args.mode == "assertions":
        for record_id, source, entity, text in rows:
            if not entity["assertions"]:
                continue
            start, end = entity["position"]
            context = source[max(0, start - 75) : min(len(source), end + 45)].replace("\n", " ")
            print(f"{record_id}: {entity['assertions']} {entity['type']} {text!r} | {context}")
    else:
        for record_id, source, entity, text in rows:
            if entity["type"] != "KẾT_QUẢ_XÉT_NGHIỆM":
                continue
            if not re.search(r"\d|âm|dương|tính|bình thường|tăng|giảm|bất thường", text, re.I):
                start, end = entity["position"]
                context = source[max(0, start - 40) : min(len(source), end + 40)].replace("\n", " ")
                print(f"{record_id}: {text!r} | {context}")


if __name__ == "__main__":
    main()
