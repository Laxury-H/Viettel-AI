#!/usr/bin/env python3
"""D2-V17 exact-consensus symptom boundary refinement.

V17 preserves the confirmed 39.2864 V16 diagnosis-precision output, then
allows a second independently trained biomedical teacher to propose symptom
additions or longer exact boundaries. A proposal must be the same character
span and type in both teachers and pass thresholds calibrated on official
ViMedNER dev/test data.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import turn2_v11
from . import turn2_v15
from . import turn2_v16
from . import turn2_v9 as base


@dataclass(frozen=True)
class Profile:
    second_threshold: float
    allow_boundary_replacement: bool
    max_replaced_entities: int | None = None
    direct_causal_negation: bool = False
    reject_leading_change_modifier: bool = False


PROFILES = {
    "additive-94": Profile(0.94, False, 0),
    "boundary-94": Profile(0.94, True),
    "boundary-94-single": Profile(0.94, True, 1),
    "boundary-94-single-causal": Profile(0.94, True, 1, True),
    "boundary-95": Profile(0.95, True),
    "boundary-95-single": Profile(0.95, True, 1),
    "boundary-97": Profile(0.97, True),
    "boundary-97-single": Profile(0.97, True, 1),
    "boundary-98": Profile(0.98, True),
    "boundary-98-single": Profile(0.98, True, 1),
    "boundary-98-single-stable": Profile(
        0.98,
        True,
        1,
        reject_leading_change_modifier=True,
    ),
    "boundary-9825": Profile(0.9825, True),
    "boundary-9825-single": Profile(0.9825, True, 1),
    "boundary-985": Profile(0.985, True),
    "boundary-985-single": Profile(0.985, True, 1),
    "boundary-9875": Profile(0.9875, True),
}
FIRST_THRESHOLD = 0.98
GENERIC_SYMPTOM_SURFACES = frozenset({"bụng", "đau vừa"})
LEADING_CHANGE_MODIFIERS = frozenset(
    {"\u0074\u0103\u006e\u0067", "\u0067\u0069\u1ea3\u006d"}
)


def normalize_surface(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def overlaps_span(start: int, end: int, entity: dict) -> bool:
    other_start, other_end = entity["position"]
    return start < other_end and other_start < end


def has_leading_change_modifier(
    text: str,
    proposed_start: int,
    existing_start: int,
) -> bool:
    """Return true when an expanded span only adds a change-of-degree word."""
    if proposed_start >= existing_start:
        return False
    prefix = normalize_surface(text[proposed_start:existing_start])
    prefix = prefix.strip(" \t\r\n:;-")
    return prefix in LEADING_CHANGE_MODIFIERS


def has_direct_causal_negation(text: str, start: int) -> bool:
    prefix = unicodedata.normalize(
        "NFC",
        text[max(0, start - 40) : start],
    ).casefold()
    return bool(
        re.search(
            r"\b(?:không|chưa)\s+(?:gây|làm)\s*$",
            prefix,
        )
    )


def eligible_consensus_spans(
    text: str,
    first_spans: list[dict],
    second_spans: list[dict],
    *,
    second_threshold: float,
) -> list[dict]:
    second_by_key = {
        (int(span["start"]), int(span["end"]), span["type"]): span
        for span in second_spans
    }
    output: list[dict] = []
    for first in first_spans:
        start = int(first["start"])
        end = int(first["end"])
        key = (start, end, first["type"])
        second = second_by_key.get(key)
        if (
            second is None
            or first["type"] != "TRIỆU_CHỨNG"
            or float(first["confidence"]) < FIRST_THRESHOLD
            or float(second["confidence"]) < second_threshold
            or not 0 <= start < end <= len(text)
            or normalize_surface(text[start:end]) in GENERIC_SYMPTOM_SURFACES
        ):
            continue
        output.append(
            {
                "start": start,
                "end": end,
                "type": first["type"],
                "first_confidence": float(first["confidence"]),
                "second_confidence": float(second["confidence"]),
            }
        )
    return output


def extract(
    text: str,
    first_spans: list[dict],
    second_spans: list[dict],
    profile: str,
) -> list[dict]:
    configuration = PROFILES[profile]
    baseline = turn2_v16.extract(
        text,
        first_spans,
        "diagnosis-precision",
    )
    historical, family = base.section_states(text)
    additions: list[dict] = []
    for span in eligible_consensus_spans(
        text,
        first_spans,
        second_spans,
        second_threshold=configuration.second_threshold,
    ):
        replaced = [
            entity
            for entity in baseline
            if overlaps_span(span["start"], span["end"], entity)
        ]
        if (
            configuration.reject_leading_change_modifier
            and replaced
            and has_leading_change_modifier(
                text,
                span["start"],
                min(entity["position"][0] for entity in replaced),
            )
        ):
            continue
        if not configuration.allow_boundary_replacement and replaced:
            continue
        if (
            configuration.max_replaced_entities is not None
            and len(replaced) > configuration.max_replaced_entities
        ):
            continue
        entity = base.make_entity(
            text,
            base.Span(span["start"], span["end"]),
            "TRIỆU_CHỨNG",
            historical,
            family,
        )
        if (
            configuration.direct_causal_negation
            and has_direct_causal_negation(text, span["start"])
            and "isNegated" not in entity["assertions"]
        ):
            entity["assertions"].insert(0, "isNegated")
        additions.append(entity)
    resolved = base.resolve_entities(baseline + additions)
    upgraded, _ = turn2_v11.upgrade_entities(
        text,
        resolved,
        enabled_groups=turn2_v15.V14_CANDIDATE_GROUPS,
    )
    return upgraded


def run(
    input_dir: Path,
    output_dir: Path,
    zip_path: Path,
    first_cache: Path,
    second_cache: Path,
    *,
    profile: str,
) -> dict:
    first_predictions = json.loads(first_cache.read_text(encoding="utf-8"))
    second_predictions = json.loads(second_cache.read_text(encoding="utf-8"))
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    if not sources:
        raise SystemExit(f"Không tìm thấy .txt trong {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("*.json"):
        if stale.stem.isdigit():
            stale.unlink()

    counts = {entity_type: 0 for entity_type in sorted(base.OFFICIAL_TYPES)}
    assertion_counts = {
        assertion: 0 for assertion in sorted(base.OFFICIAL_ASSERTIONS)
    }
    total = changed_records = added = removed = common_fields_changed = 0
    for source in sources:
        text = source.read_text(encoding="utf-8")
        first_spans = first_predictions.get(source.stem, [])
        second_spans = second_predictions.get(source.stem, [])
        control = turn2_v16.extract(
            text,
            first_spans,
            "diagnosis-precision",
        )
        entities = extract(
            text,
            first_spans,
            second_spans,
            profile,
        )
        base.validate_record(text, entities)
        key = lambda entity: (
            entity["position"][0],
            entity["position"][1],
            entity["type"],
        )
        before = {key(entity): entity for entity in control}
        after = {key(entity): entity for entity in entities}
        record_added = len(after.keys() - before.keys())
        record_removed = len(before.keys() - after.keys())
        if record_added or record_removed:
            changed_records += 1
        added += record_added
        removed += record_removed
        common_fields_changed += sum(
            before[entity_key] != after[entity_key]
            for entity_key in before.keys() & after.keys()
        )
        for entity in entities:
            counts[entity["type"]] += 1
            for assertion in entity["assertions"]:
                assertion_counts[assertion] += 1
        total += len(entities)
        (output_dir / f"{source.stem}.json").write_text(
            base.format_json(entities),
            encoding="utf-8",
            newline="\n",
        )

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

    configuration = PROFILES[profile]
    return {
        "version": f"D2-V17-consensus-{profile}",
        "profile": profile,
        "control": "D2-V16-teacher-diagnosis-precision",
        "first_teacher_confidence_minimum": FIRST_THRESHOLD,
        "second_teacher_confidence_minimum": (
            configuration.second_threshold
        ),
        "allow_boundary_replacement": (
            configuration.allow_boundary_replacement
        ),
        "max_replaced_entities": configuration.max_replaced_entities,
        "direct_causal_negation": configuration.direct_causal_negation,
        "reject_leading_change_modifier": (
            configuration.reject_leading_change_modifier
        ),
        "records": len(sources),
        "changed_records": changed_records,
        "entities": total,
        "entities_added": added,
        "entities_removed": removed,
        "common_entity_fields_changed": common_fields_changed,
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
    parser.add_argument("--profile", choices=sorted(PROFILES))
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
