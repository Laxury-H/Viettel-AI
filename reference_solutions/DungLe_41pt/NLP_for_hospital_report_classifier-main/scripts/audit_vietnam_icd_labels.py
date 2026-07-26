#!/usr/bin/env python3
"""Audit submission diagnosis labels against the official Vietnam ICD workbook.

The workbook is intentionally parsed with the Python standard library so the
audit remains runnable in the lightweight submission environment.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET


XMLNS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
CELL_COLUMN = re.compile(r"([A-Z]+)")


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFC", value).casefold()
    value = value.replace("–", "-").replace("—", "-")
    value = re.sub(r"\s+", " ", value)
    return value.strip(" \t\r\n.;:")


def parse_workbook(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        strings_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared_strings = [
            "".join(node.text or "" for node in item.iter(XMLNS + "t"))
            for item in strings_root.findall(XMLNS + "si")
        ]
        sheet_root = ET.fromstring(
            archive.read("xl/worksheets/sheet1.xml")
        )

    rows: list[dict[str, str]] = []
    for row in sheet_root.iter(XMLNS + "row"):
        row_number = int(row.attrib["r"])
        if row_number < 5:
            continue
        values: dict[str, str] = {}
        for cell in row.findall(XMLNS + "c"):
            match = CELL_COLUMN.match(cell.attrib["r"])
            if match is None:
                continue
            column = match.group(1)
            node = cell.find(XMLNS + "v")
            value = "" if node is None else (node.text or "")
            if cell.attrib.get("t") == "s" and value:
                value = shared_strings[int(value)]
            values[column] = value.strip()
        if values.get("R"):
            rows.append(values)
    return rows


def load_submission(path: Path) -> dict[str, list[dict]]:
    with zipfile.ZipFile(path) as archive:
        return {
            Path(name).stem: json.loads(archive.read(name))
            for name in archive.namelist()
            if name.endswith(".json")
        }


def code_stem(code: str) -> str:
    return code.replace(".", "")


def is_family_relation(left: str, right: str) -> bool:
    a = code_stem(left)
    b = code_stem(right)
    return a.startswith(b) or b.startswith(a)


def audit(workbook: Path, submission: Path) -> dict:
    rows = parse_workbook(workbook)
    official_by_code: dict[str, dict[str, str]] = {}
    exact_names: dict[str, set[str]] = defaultdict(set)
    group_names: dict[str, set[str]] = defaultdict(set)
    guidance_names: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        code = row["R"]
        official_by_code[code] = {
            "disease_name": row.get("V", ""),
            "group_name": row.get("Q", ""),
            "guidance": row.get("W", ""),
            "more_specific_forbidden": row.get("Z", ""),
        }
        disease_label = normalize(row.get("V", ""))
        if disease_label:
            exact_names[disease_label].add(code)
        group_label = normalize(row.get("Q", ""))
        if group_label:
            group_names[group_label].add(code)
        guidance = row.get("W", "")
        for part in re.split(r"[\n;]", guidance):
            label = normalize(part)
            if label:
                guidance_names[label].add(code)

    data = load_submission(submission)
    occurrences: Counter[tuple[str, tuple[str, ...]]] = Counter()
    record_ids: dict[tuple[str, tuple[str, ...]], set[str]] = defaultdict(set)
    assertions: dict[tuple[str, tuple[str, ...]], Counter[tuple[str, ...]]] = (
        defaultdict(Counter)
    )
    for record_id, entities in data.items():
        for entity in entities:
            if entity.get("type") != "CHẨN_ĐOÁN":
                continue
            key = (
                normalize(entity["text"]),
                tuple(entity.get("candidates", [])),
            )
            occurrences[key] += 1
            record_ids[key].add(record_id)
            assertions[key][tuple(entity.get("assertions", []))] += 1

    mismatches: list[dict] = []
    exact_matches: list[dict] = []
    for (surface, candidates), count in occurrences.items():
        targets = sorted(exact_names.get(surface, set()))
        group_targets = sorted(group_names.get(surface, set()))
        guidance_targets = sorted(guidance_names.get(surface, set()))
        if not targets and not guidance_targets:
            continue
        item = {
            "surface": surface,
            "count": count,
            "record_ids": sorted(record_ids[(surface, candidates)], key=int),
            "current": list(candidates),
            "exact_targets": targets,
            "group_targets": group_targets,
            "guidance_targets": guidance_targets,
            "assertions": {
                "|".join(key) or "present": value
                for key, value in assertions[(surface, candidates)].items()
            },
            "current_official_names": {
                code: official_by_code.get(code, {})
                for code in candidates
            },
            "target_official_names": {
                code: official_by_code.get(code, {})
                for code in targets
            },
        }
        if set(candidates) & set(targets):
            exact_matches.append(item)
            continue
        relations = [
            target
            for target in targets
            if any(is_family_relation(current, target) for current in candidates)
        ]
        item["family_targets"] = relations
        mismatches.append(item)

    mismatches.sort(
        key=lambda item: (
            not bool(item["family_targets"]),
            -item["count"],
            item["surface"],
        )
    )
    exact_matches.sort(key=lambda item: (-item["count"], item["surface"]))
    return {
        "workbook": str(workbook.resolve()),
        "submission": str(submission.resolve()),
        "official_codes": len(official_by_code),
        "diagnosis_occurrences": sum(occurrences.values()),
        "unique_surface_candidate_pairs": len(occurrences),
        "mismatch_occurrences": sum(item["count"] for item in mismatches),
        "family_mismatch_occurrences": sum(
            item["count"] for item in mismatches if item["family_targets"]
        ),
        "mismatches": mismatches,
        "exact_matches": exact_matches,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.workbook, args.submission)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")


if __name__ == "__main__":
    main()
