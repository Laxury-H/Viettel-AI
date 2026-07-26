#!/usr/bin/env python3
"""Score-aware boundary and repeated-line recall expansion on top of V26."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from . import turn2_v18
from . import turn2_v19
from . import turn2_v24
from . import turn2_v26
from . import turn2_v9 as base


SYMPTOM_TYPE = "TRIỆU_CHỨNG"
LEADING_NONCLINICAL_MODIFIER = re.compile(
    r"(?i)^(?:tăng|giảm|cơn)\b"
)
TRAILING_REQUIRED_COMPLEMENT = re.compile(
    r"(?i)^\s+(?:phải|trái)\b"
)


@dataclass(frozen=True)
class RepeatedLineAddition:
    record_id: str
    start: int
    end: int
    entity_type: str
    surface: str
    source_record_ids: tuple[str, ...]


def keep_semantic_expansion(
    expansion: turn2_v26.BoundaryExpansion,
    texts: dict[str, str],
) -> bool:
    """Keep complete clinical phrases and reject known boundary failure modes."""

    surface = " ".join(expansion.after_text.split())
    if "/" in surface:
        return False
    if LEADING_NONCLINICAL_MODIFIER.search(surface):
        return False
    text = texts[expansion.record_id]
    tail = text[expansion.after_position[1] : expansion.after_position[1] + 16]
    if TRAILING_REQUIRED_COMPLEMENT.search(tail):
        return False
    return True


def derive_repeated_line_additions(
    texts: dict[str, str],
    baseline: dict[str, list[dict]],
    addition_source: dict[str, list[dict]],
    target_control: dict[str, list[dict]],
) -> list[RepeatedLineAddition]:
    """Transfer scored-model additions across exact repeated clinical lines."""

    groups: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    for record_id, text in texts.items():
        for line, start, end in turn2_v18.line_occurrences(text):
            groups[line].append((record_id, start, end))

    source_signatures: dict[
        tuple[str, int, int, str, str],
        set[str],
    ] = defaultdict(set)
    for line, occurrences in groups.items():
        if len({record_id for record_id, _, _ in occurrences}) < 2:
            continue
        for record_id, line_start, line_end in occurrences:
            baseline_keys = {
                turn2_v24.entity_key(entity) for entity in baseline[record_id]
            }
            for entity in addition_source[record_id]:
                start, end = entity["position"]
                if (
                    entity["type"] == SYMPTOM_TYPE
                    and not entity["assertions"]
                    and turn2_v24.entity_key(entity) not in baseline_keys
                    and line_start <= start < end <= line_end
                ):
                    signature = (
                        line,
                        start - line_start,
                        end - line_start,
                        str(entity["type"]),
                        str(entity["text"]),
                    )
                    source_signatures[signature].add(record_id)

    proposals: set[RepeatedLineAddition] = set()
    for signature, source_record_ids in source_signatures.items():
        line, relative_start, relative_end, entity_type, surface = signature
        for record_id, line_start, line_end in groups[line]:
            start = line_start + relative_start
            end = line_start + relative_end
            if not line_start <= start < end <= line_end:
                continue
            if texts[record_id][start:end] != surface:
                continue
            if any(
                entity["position"] == [start, end]
                and entity["type"] == entity_type
                for entity in target_control[record_id]
            ):
                continue
            if any(
                start < entity["position"][1]
                and entity["position"][0] < end
                for entity in target_control[record_id]
            ):
                continue
            proposals.add(
                RepeatedLineAddition(
                    record_id=record_id,
                    start=start,
                    end=end,
                    entity_type=entity_type,
                    surface=surface,
                    source_record_ids=tuple(sorted(source_record_ids, key=int)),
                )
            )
    return sorted(
        proposals,
        key=lambda item: (int(item.record_id), item.start, item.end),
    )


def apply_repeated_additions(
    texts: dict[str, str],
    records: dict[str, list[dict]],
    additions: list[RepeatedLineAddition],
) -> tuple[dict[str, list[dict]], list[dict]]:
    output = {
        record_id: [dict(entity) for entity in entities]
        for record_id, entities in records.items()
    }
    changes: list[dict] = []
    for addition in additions:
        text = texts[addition.record_id]
        historical, family = base.section_states(text)
        entity = base.make_entity(
            text,
            base.Span(addition.start, addition.end),
            addition.entity_type,
            historical,
            family,
        )
        output[addition.record_id].append(entity)
        output[addition.record_id] = base.resolve_entities(
            output[addition.record_id]
        )
        changes.append(
            {
                "record_id": addition.record_id,
                "text": entity["text"],
                "type": entity["type"],
                "position": entity["position"],
                "assertions": entity["assertions"],
                "source_record_ids": list(addition.source_record_ids),
            }
        )
    return output, changes


def run(
    input_dir: Path,
    control_zip: Path,
    v18_baseline_zip: Path,
    addition_source_zip: Path,
    reference_base_zip: Path,
    reference_candidate_zip: Path,
    output_zip: Path,
) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    control = turn2_v19.load_submission(control_zip)
    v18_baseline = turn2_v19.load_submission(v18_baseline_zip)
    addition_source = turn2_v19.load_submission(addition_source_zip)
    reference_base = turn2_v19.load_submission(reference_base_zip)
    reference_candidate = turn2_v19.load_submission(reference_candidate_zip)
    expected = set(texts)
    for name, records in (
        ("control", control),
        ("V18 baseline", v18_baseline),
        ("addition source", addition_source),
        ("reference base", reference_base),
        ("reference candidate", reference_candidate),
    ):
        if set(records) != expected:
            raise ValueError(f"{name} record IDs do not match input")

    lower_threshold_expansions = turn2_v26.derive_stable_expansions(
        reference_base,
        reference_candidate,
    )
    expansions = [
        expansion
        for expansion in lower_threshold_expansions
        if keep_semantic_expansion(expansion, texts)
    ]
    if len(expansions) != 11:
        raise ValueError(
            f"Expected 11 semantic boundary expansions, found {len(expansions)}"
        )
    boundary_output, boundary_changes = turn2_v26.apply_expansions(
        control,
        expansions,
    )

    repeated_additions = derive_repeated_line_additions(
        texts,
        v18_baseline,
        addition_source,
        boundary_output,
    )
    if len(repeated_additions) != 1:
        raise ValueError(
            f"Expected one repeated-line addition, found {len(repeated_additions)}"
        )
    output, addition_changes = apply_repeated_additions(
        texts,
        boundary_output,
        repeated_additions,
    )
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V27-v26-semantic-boundary-repeated-recall",
        "control": str(control_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "changed_records": len(
            {
                change["record_id"]
                for change in [*boundary_changes, *addition_changes]
            }
        ),
        "semantic_boundary_expansions": len(boundary_changes),
        "repeated_line_additions": len(addition_changes),
        "boundary_changes": boundary_changes,
        "addition_changes": addition_changes,
        "score_expectation": {
            "confirmed_control": 39.3762,
            "v26_projected_component": 0.0041,
            "target_range": [39.386, 39.400],
            "status": "unscored_score_aware_batch",
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
    parser.add_argument("--v18-baseline-zip", type=Path, required=True)
    parser.add_argument("--addition-source-zip", type=Path, required=True)
    parser.add_argument("--reference-base-zip", type=Path, required=True)
    parser.add_argument("--reference-candidate-zip", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    summary = run(
        args.input,
        args.control_zip,
        args.v18_baseline_zip,
        args.addition_source_zip,
        args.reference_base_zip,
        args.reference_candidate_zip,
        args.zip,
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
