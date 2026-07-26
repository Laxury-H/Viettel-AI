#!/usr/bin/env python3
"""Recover high-evidence symptom occurrences omitted by the V28 control."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from . import turn2_v15
from . import turn2_v19
from . import turn2_v24
from . import turn2_v27
from . import turn2_v28
from . import turn2_v9 as base


SYMPTOM_TYPE = "TRIỆU_CHỨNG"

# These surfaces were selected by the reusable gap analyses in
# scripts/analyze_accepted_surface_gaps.py. They are restricted to current
# patient findings and repeated neurologic history/examination content.
RECOVERY_SURFACES: tuple[str, ...] = (
    "mất định hướng",
    "cứng đờ",
    "cắn lưỡi",
    "tiểu tiện không tự chủ",
    "tỉnh chậm",
    "nhắm mắt từng lúc",
    "tê bì vùng trán phải",
)


def derive_selected_recall_additions(
    texts: dict[str, str],
    control: dict[str, list[dict]],
    *,
    surfaces: tuple[str, ...] = RECOVERY_SURFACES,
) -> tuple[list[turn2_v27.RepeatedLineAddition], list[dict]]:
    """Find every non-overlapping occurrence of the selected clinical surfaces."""

    normalized_surfaces = tuple(
        turn2_v28.normalized_surface(surface) for surface in surfaces
    )
    safe_surfaces = {
        turn2_v28.normalized_surface(surface)
        for surface in turn2_v15.SAFE_SYMPTOMS
    }
    if not set(normalized_surfaces) <= safe_surfaces:
        raise ValueError("Every recovery surface must be in the teacher lexicon")

    accepted_counts = Counter(
        turn2_v28.normalized_surface(entity["text"])
        for entities in control.values()
        for entity in entities
        if entity["type"] == SYMPTOM_TYPE
    )
    accepted_records: dict[str, set[str]] = defaultdict(set)
    for record_id, entities in control.items():
        for entity in entities:
            if entity["type"] == SYMPTOM_TYPE:
                accepted_records[
                    turn2_v28.normalized_surface(entity["text"])
                ].add(record_id)

    additions: set[turn2_v27.RepeatedLineAddition] = set()
    evidence: list[dict] = []
    for record_id in sorted(texts, key=int):
        text = texts[record_id]
        normalized = base.NormalizedText(text)
        for surface in normalized_surfaces:
            for span in normalized.literal_spans(
                surface,
                boundary=base.should_use_boundary(surface, SYMPTOM_TYPE),
            ):
                if any(
                    span.start < entity["position"][1]
                    and entity["position"][0] < span.end
                    for entity in control[record_id]
                ):
                    continue
                addition = turn2_v27.RepeatedLineAddition(
                    record_id=record_id,
                    start=span.start,
                    end=span.end,
                    entity_type=SYMPTOM_TYPE,
                    surface=text[span.start : span.end],
                    source_record_ids=tuple(
                        sorted(accepted_records[surface], key=int)
                    ),
                )
                additions.add(addition)
                evidence.append(
                    {
                        "record_id": record_id,
                        "text": addition.surface,
                        "position": [span.start, span.end],
                        "accepted_occurrences_in_control": accepted_counts[
                            surface
                        ],
                        "accepted_record_ids": list(
                            addition.source_record_ids
                        ),
                        "teacher_lexicon": "SAFE_SYMPTOMS",
                    }
                )
    ordered = sorted(
        additions,
        key=lambda item: (int(item.record_id), item.start, item.end),
    )
    ordered_evidence = sorted(
        evidence,
        key=lambda item: (
            int(item["record_id"]),
            item["position"][0],
            item["position"][1],
        ),
    )
    return ordered, ordered_evidence


def run(input_dir: Path, control_zip: Path, output_zip: Path) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    control = turn2_v19.load_submission(control_zip)
    if set(control) != set(texts):
        raise ValueError("Control record IDs do not match input")

    additions, evidence = derive_selected_recall_additions(texts, control)
    if len(additions) != 8:
        raise ValueError(
            f"Expected eight high-evidence additions, found {len(additions)}"
        )
    output, changes = turn2_v27.apply_repeated_additions(
        texts,
        control,
        additions,
    )
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V29-v28-high-evidence-recall",
        "control": str(control_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "changed_records": len({change["record_id"] for change in changes}),
        "high_evidence_additions": len(changes),
        "changes": changes,
        "evidence": evidence,
        "score_expectation": {
            "confirmed_control": 39.4461,
            "target_range": [39.46, 39.49],
            "status": "unscored_high_evidence_recall",
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
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    summary = run(args.input, args.control_zip, args.zip)
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
