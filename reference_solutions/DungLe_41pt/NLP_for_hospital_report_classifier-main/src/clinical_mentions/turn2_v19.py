#!/usr/bin/env python3
"""Conservative XLM-R consensus refinements on top of scored V18 output.

The V18 ZIP is treated as an immutable control.  XLM-R may only contribute a
symptom when BamiBERT predicts the exact same character span with high
confidence.  New spans must not overlap the control; boundary changes must be
strict supersets of exactly one existing symptom and may not cross punctuation.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import turn2_v11
from . import turn2_v15
from . import turn2_v17
from . import turn2_v18
from . import turn2_v9 as base


SYMPTOM_TYPE = "TRIỆU_CHỨNG"
FIRST_THRESHOLD = 0.98


@dataclass(frozen=True)
class Profile:
    addition_threshold: float
    boundary_threshold: float | None
    require_empty_addition_assertions: bool = True


PROFILES = {
    "xlmr-additive-90": Profile(0.90, None),
    "xlmr-additive-85": Profile(0.85, None),
    "xlmr-additive-80": Profile(0.80, None),
    "xlmr-safe-94": Profile(0.90, 0.94),
    "xlmr-safe-93": Profile(0.90, 0.93),
    "xlmr-safe-91": Profile(0.90, 0.91),
}


def entity_key(entity: dict) -> tuple[int, int, str]:
    start, end = entity["position"]
    return int(start), int(end), str(entity["type"])


def overlaps(start: int, end: int, entity: dict) -> bool:
    other_start, other_end = entity["position"]
    return start < other_end and other_start < end


def load_submission(path: Path) -> dict[str, list[dict]]:
    records: dict[str, list[dict]] = {}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            member = Path(name)
            if (
                member.parent.as_posix() == "output"
                and member.suffix == ".json"
                and member.stem.isdigit()
            ):
                records[member.stem] = json.loads(
                    archive.read(name).decode("utf-8")
                )
    return records


def consensus_symptoms(
    first_spans: list[dict],
    second_spans: list[dict],
    *,
    second_threshold: float,
) -> list[tuple[int, int]]:
    first = {
        (int(span["start"]), int(span["end"]), str(span["type"]))
        for span in first_spans
        if (
            str(span["type"]) == SYMPTOM_TYPE
            and float(span["confidence"]) >= FIRST_THRESHOLD
        )
    }
    second = {
        (int(span["start"]), int(span["end"]), str(span["type"]))
        for span in second_spans
        if (
            str(span["type"]) == SYMPTOM_TYPE
            and float(span["confidence"]) >= second_threshold
        )
    }
    return sorted((start, end) for start, end, _ in first & second)


def safe_boundary_expansion(
    text: str,
    start: int,
    end: int,
    overlapping: list[dict],
) -> bool:
    if len(overlapping) != 1 or overlapping[0]["type"] != SYMPTOM_TYPE:
        return False
    existing_start, existing_end = overlapping[0]["position"]
    if not (
        start <= existing_start
        and end >= existing_end
        and (start < existing_start or end > existing_end)
    ):
        return False
    surface = text[start:end]
    if any(character in surface for character in ".\r\n/"):
        return False
    if turn2_v17.has_leading_change_modifier(text, start, existing_start):
        return False
    return True


def refine_entities(
    text: str,
    entities: list[dict],
    first_spans: list[dict],
    second_spans: list[dict],
    *,
    profile: str,
) -> tuple[list[dict], dict[str, int]]:
    configuration = PROFILES[profile]
    refined = [dict(entity) for entity in entities]
    historical, family = base.section_states(text)
    added = replaced = rejected = 0

    candidates = consensus_symptoms(
        first_spans,
        second_spans,
        second_threshold=configuration.addition_threshold,
    )
    for start, end in candidates:
        if not 0 <= start < end <= len(text):
            rejected += 1
            continue
        overlapping = [
            entity for entity in refined if overlaps(start, end, entity)
        ]
        if any(entity["position"] == [start, end] for entity in overlapping):
            continue
        if not overlapping:
            proposed = base.make_entity(
                text,
                base.Span(start, end),
                SYMPTOM_TYPE,
                historical,
                family,
            )
            if (
                configuration.require_empty_addition_assertions
                and proposed["assertions"]
            ):
                rejected += 1
                continue
            refined.append(proposed)
            added += 1

    if configuration.boundary_threshold is not None:
        candidates = consensus_symptoms(
            first_spans,
            second_spans,
            second_threshold=configuration.boundary_threshold,
        )
        for start, end in candidates:
            if not 0 <= start < end <= len(text):
                rejected += 1
                continue
            overlapping = [
                entity for entity in refined if overlaps(start, end, entity)
            ]
            if any(entity["position"] == [start, end] for entity in overlapping):
                continue
            if not safe_boundary_expansion(text, start, end, overlapping):
                if overlapping:
                    rejected += 1
                continue
            target = overlapping[0]
            refined = [entity for entity in refined if entity is not target]
            refined.append(
                base.make_entity(
                    text,
                    base.Span(start, end),
                    SYMPTOM_TYPE,
                    historical,
                    family,
                )
            )
            replaced += 1

    resolved = base.resolve_entities(refined)
    upgraded, _ = turn2_v11.upgrade_entities(
        text,
        resolved,
        enabled_groups=turn2_v15.V14_CANDIDATE_GROUPS,
    )
    return upgraded, {
        "entities_added": added,
        "boundaries_replaced": replaced,
        "proposals_rejected": rejected,
    }


def run(
    input_dir: Path,
    baseline_zip: Path,
    output_dir: Path,
    zip_path: Path,
    first_cache: Path,
    second_cache: Path,
    *,
    profile: str,
) -> dict:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}")
    baseline = load_submission(baseline_zip)
    first = json.loads(first_cache.read_text(encoding="utf-8"))
    second = json.loads(second_cache.read_text(encoding="utf-8"))
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    expected = {source.stem for source in sources}
    if set(baseline) != expected:
        raise ValueError("Baseline ZIP record IDs do not match the input")

    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("*.json"):
        if stale.stem.isdigit():
            stale.unlink()

    totals = {
        "entities_added": 0,
        "boundaries_replaced": 0,
        "proposals_rejected": 0,
    }
    changed_records = 0
    total_entities = 0
    for source in sources:
        record_id = source.stem
        text = source.read_text(encoding="utf-8")
        before = baseline[record_id]
        after, stats = refine_entities(
            text,
            before,
            first.get(record_id, []),
            second.get(record_id, []),
            profile=profile,
        )
        base.validate_record(text, after)
        if before != after:
            changed_records += 1
        for name, value in stats.items():
            totals[name] += value
        total_entities += len(after)
        (output_dir / f"{record_id}.json").write_text(
            base.format_json(after),
            encoding="utf-8",
            newline="\n",
        )

    turn2_v18.write_deterministic_zip(output_dir, zip_path)
    return {
        "version": f"D2-V19-{profile}",
        "profile": profile,
        "baseline": str(baseline_zip.resolve()),
        "records": len(sources),
        "changed_records": changed_records,
        "entities": total_entities,
        **totals,
        "zip": str(zip_path.resolve()),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--baseline-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--first-cache", type=Path, required=True)
    parser.add_argument("--second-cache", type=Path, required=True)
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    summary = run(
        args.input,
        args.baseline_zip,
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
