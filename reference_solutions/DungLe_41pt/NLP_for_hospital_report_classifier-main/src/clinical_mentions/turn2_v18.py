#!/usr/bin/env python3
"""Merge the independently positive V17 and V21 refinements.

V17 improved five symptom boundaries through exact agreement between two
teachers.  Upstream V21 independently improved the same V16 control by
dropping diagnoses that are merely the focus of a polar question and by
repairing a fragmented symptom from an identical repeated clinical line.
This module composes those disjoint refinements without changing candidates
or the remaining production entities.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

from . import turn2_v11
from . import turn2_v15
from . import turn2_v17
from . import turn2_v9 as base


PROFILES = ("v21-merge", "v23-trim")


def normalize_surface(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def is_polar_question_mention(text: str, entity: dict) -> bool:
    """Return whether a diagnosis fills the focus of a yes/no question."""

    folded = normalize_surface(text)
    start, end = entity["position"]
    clause_start = max(
        folded.rfind("\n", 0, start),
        folded.rfind(".", 0, start),
        folded.rfind("?", 0, start),
        folded.rfind("!", 0, start),
    )
    before = folded[max(clause_start + 1, start - 160) : start]
    after = folded[end : min(len(folded), end + 40)]
    return (
        re.search(r"\bcó\s+phải(?:\s+là)?\s*$", before) is not None
        and re.match(r"\s+(?:thật\s+sự\s+)?không\b", after) is not None
    )


def prune_polar_question_diagnoses(text: str, entities: list[dict]) -> list[dict]:
    return [
        entity
        for entity in entities
        if not (
            entity["type"] == "CHẨN_ĐOÁN"
            and is_polar_question_mention(text, entity)
        )
    ]


def trim_symptom_reporting_prefixes(
    text: str,
    entities: list[dict],
) -> list[dict]:
    """Trim a non-clinical reporting prefix while preserving source offsets."""

    reporting_prefix = re.compile(
        r"(?i)^(?:miệng|mồm)\s+(?:cảm\s+)?thấy\s+"
    )
    refined: list[dict] = []
    for entity in entities:
        if entity["type"] != "TRIỆU_CHỨNG":
            refined.append(entity)
            continue
        match = reporting_prefix.match(entity["text"])
        if match is None:
            refined.append(entity)
            continue
        start, end = entity["position"]
        trimmed_start = start + match.end()
        trimmed = dict(entity)
        trimmed["text"] = text[trimmed_start:end]
        trimmed["position"] = [trimmed_start, end]
        refined.append(trimmed)
    return base.resolve_entities(refined)


def line_occurrences(text: str) -> list[tuple[str, int, int]]:
    occurrences: list[tuple[str, int, int]] = []
    for match in re.finditer(r"[^\r\n]+", text):
        raw = match.group(0)
        value = raw.strip()
        if len(value) < 40:
            continue
        leading = len(raw) - len(raw.lstrip())
        start = match.start() + leading
        occurrences.append((value, start, start + len(value)))
    return occurrences


def apply_repeated_line_consensus(
    texts: dict[str, str],
    teacher_records: dict[str, list[dict]],
    entities_by_record: dict[str, list[dict]],
) -> int:
    """Repair a fragmented approved symptom using repeated-line agreement."""

    allowed_symptoms = {
        normalize_surface(alias) for alias in turn2_v15.PRECISION_SYMPTOMS
    }
    grouped: dict[str, list[tuple[str, int, int]]] = {}
    for record_id, text in texts.items():
        for line, start, end in line_occurrences(text):
            grouped.setdefault(line, []).append((record_id, start, end))

    proposals: set[tuple[str, int, int, str]] = set()
    for occurrences in grouped.values():
        if len({record_id for record_id, _, _ in occurrences}) < 2:
            continue
        signatures: set[tuple[int, int, str]] = set()
        for record_id, line_start, line_end in occurrences:
            text = texts[record_id]
            for entity in entities_by_record[record_id]:
                start, end = entity["position"]
                if (
                    entity["type"] == "TRIỆU_CHỨNG"
                    and line_start <= start < end <= line_end
                    and normalize_surface(text[start:end]) in allowed_symptoms
                ):
                    signatures.add(
                        (start - line_start, end - line_start, entity["type"])
                    )
        for relative_start, relative_end, entity_type in signatures:
            for record_id, line_start, line_end in occurrences:
                start = line_start + relative_start
                end = line_start + relative_end
                if not line_start <= start < end <= line_end:
                    continue
                if any(
                    entity["position"] == [start, end]
                    and entity["type"] == entity_type
                    for entity in entities_by_record[record_id]
                ):
                    continue
                text = texts[record_id]
                if normalize_surface(text[start:end]) not in allowed_symptoms:
                    continue
                teacher_support = any(
                    str(span["type"]) == entity_type
                    and float(span["confidence"]) >= 0.95
                    and start <= int(span["start"]) < int(span["end"]) <= end
                    and (
                        int(span["start"]) == start
                        or int(span["end"]) == end
                    )
                    for span in teacher_records[record_id]
                )
                if teacher_support:
                    proposals.add((record_id, start, end, entity_type))

    changed_records: set[str] = set()
    for record_id, start, end, entity_type in sorted(proposals):
        text = texts[record_id]
        historical, family = base.section_states(text)
        entities_by_record[record_id].append(
            base.make_entity(
                text,
                base.Span(start, end),
                entity_type,
                historical,
                family,
            )
        )
        changed_records.add(record_id)
    for record_id in changed_records:
        text = texts[record_id]
        resolved = base.resolve_entities(entities_by_record[record_id])
        entities_by_record[record_id], _ = turn2_v11.upgrade_entities(
            text,
            resolved,
            enabled_groups=turn2_v15.V14_CANDIDATE_GROUPS,
        )
    return len(proposals)


def write_deterministic_zip(output_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for output_file in sorted(
            output_dir.glob("*.json"),
            key=base.natural_key,
        ):
            info = zipfile.ZipInfo(
                f"output/{output_file.name}",
                (1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, output_file.read_bytes())


def run(
    input_dir: Path,
    output_dir: Path,
    zip_path: Path,
    first_cache: Path,
    second_cache: Path,
    *,
    profile: str,
) -> dict:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}")
    first_predictions = json.loads(first_cache.read_text(encoding="utf-8"))
    second_predictions = json.loads(second_cache.read_text(encoding="utf-8"))
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    control_by_record: dict[str, list[dict]] = {}
    entities_by_record: dict[str, list[dict]] = {}
    for source in sources:
        record_id = source.stem
        control = turn2_v17.extract(
            texts[record_id],
            first_predictions.get(record_id, []),
            second_predictions.get(record_id, []),
            "boundary-985-single",
        )
        control_by_record[record_id] = control
        entities_by_record[record_id] = prune_polar_question_diagnoses(
            texts[record_id],
            control,
        )

    consensus_entities_added = apply_repeated_line_consensus(
        texts,
        first_predictions,
        entities_by_record,
    )
    if profile == "v23-trim":
        entities_by_record = {
            record_id: trim_symptom_reporting_prefixes(
                texts[record_id],
                entities,
            )
            for record_id, entities in entities_by_record.items()
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("*.json"):
        if stale.stem.isdigit():
            stale.unlink()

    counts = {entity_type: 0 for entity_type in sorted(base.OFFICIAL_TYPES)}
    assertion_counts = {
        assertion: 0 for assertion in sorted(base.OFFICIAL_ASSERTIONS)
    }
    total = changed_records = added = removed = common_fields_changed = 0
    entity_key = lambda entity: (
        entity["position"][0],
        entity["position"][1],
        entity["type"],
    )
    for source in sources:
        record_id = source.stem
        entities = entities_by_record[record_id]
        base.validate_record(texts[record_id], entities)
        before = {entity_key(entity): entity for entity in control_by_record[record_id]}
        after = {entity_key(entity): entity for entity in entities}
        record_added = len(after.keys() - before.keys())
        record_removed = len(before.keys() - after.keys())
        record_changed = sum(
            before[key] != after[key] for key in before.keys() & after.keys()
        )
        if record_added or record_removed or record_changed:
            changed_records += 1
        added += record_added
        removed += record_removed
        common_fields_changed += record_changed
        for entity in entities:
            counts[entity["type"]] += 1
            for assertion in entity["assertions"]:
                assertion_counts[assertion] += 1
        total += len(entities)
        (output_dir / f"{record_id}.json").write_text(
            base.format_json(entities),
            encoding="utf-8",
            newline="\n",
        )

    write_deterministic_zip(output_dir, zip_path)
    return {
        "version": f"D2-V18-{profile}",
        "profile": profile,
        "control": "D2-V17-consensus-boundary-985-single",
        "records": len(sources),
        "changed_records": changed_records,
        "entities": total,
        "entities_added": added,
        "entities_removed": removed,
        "common_entity_fields_changed": common_fields_changed,
        "consensus_entities_added": consensus_entities_added,
        "by_type": counts,
        "by_assertion": assertion_counts,
        "zip": str(zip_path.resolve()),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--first-cache", type=Path, required=True)
    parser.add_argument("--second-cache", type=Path, required=True)
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    summary = run(
        args.input,
        args.output,
        args.zip,
        args.first_cache,
        args.second_cache,
        profile=args.profile,
    )
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
