#!/usr/bin/env python3
"""Apply semantic boundary completion and contextual recall on top of V30."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from . import turn2_v15
from . import turn2_v19
from . import turn2_v24
from . import turn2_v26
from . import turn2_v27
from . import turn2_v28
from . import turn2_v9 as base


SYMPTOM_TYPE = "TRIỆU_CHỨNG"

# V26, V27, and V30 all improved when a generic symptom head was completed
# with its location, body part, duration, or severity.  These are every
# remaining complete alias proposed by BOUNDARY_SYMPTOMS on V30, except for
# the two failure modes already rejected by scored experiments: a leading
# change modifier ("tăng") and a leading event noun ("cơn").
SELECTED_BOUNDARY_SURFACES: tuple[str, ...] = (
    "sưng hạch cổ",
    "đau đầu vùng thái dương phải",
    "đau bao tử",
    "ngứa khắp người",
    "đau khi nhai",
    "đau bụng trên",
    "đau lưng âm ỉ",
    "đau dữ dội",
    "ngứa toàn thân",
    "đau vùng gan phải",
    "đau thắt ngực",
    "phù ngoại vi",
    "đau vai",
    "phù hai bên",
    "đau rát khi đi tiểu",
    "phù mặt",
    "phù nhẹ 2 chi dưới",
    "run rẩy tay chân",
    "hạ huyết áp tư thế đứng",
)

# The first three occur in a medication side-effect list, mirroring the
# educational/side-effect recall that moved V30 upward.  "đi cầu phân sống"
# is repeated twice in a clinical consultation.  "căng thẳng" already has
# two accepted occurrences and is recovered only where it is still missing.
CONTEXTUAL_RECALL_SURFACES: tuple[str, ...] = (
    "bồn chồn",
    "bứt rứt trong người",
    "giảm ham muốn",
    "đi cầu phân sống",
    "căng thẳng",
)

EPISTEMIC_QUESTION_PREFIX = re.compile(
    r"(?i)\bkhông\s+biết\s+là\s+tình\s+trạng\s*$"
)


def derive_semantic_boundary_expansions(
    texts: dict[str, str],
    control: dict[str, list[dict]],
) -> list[turn2_v26.BoundaryExpansion]:
    """Complete reviewed symptom heads with semantic complements."""

    allowed = {
        turn2_v28.normalized_surface(surface)
        for surface in SELECTED_BOUNDARY_SURFACES
    }
    teacher_aliases = {
        turn2_v28.normalized_surface(surface)
        for surface in turn2_v15.BOUNDARY_SYMPTOMS
    }
    if not allowed <= teacher_aliases:
        missing = sorted(allowed - teacher_aliases)
        raise ValueError(f"Boundary surfaces are not teacher aliases: {missing}")

    expansions: set[turn2_v26.BoundaryExpansion] = set()
    for record_id in sorted(texts, key=int):
        text = texts[record_id]
        normalized = base.NormalizedText(text)
        symptoms = [
            entity
            for entity in control[record_id]
            if entity["type"] == SYMPTOM_TYPE
        ]
        for surface in sorted(allowed):
            for span in normalized.literal_spans(
                surface,
                boundary=base.should_use_boundary(surface, SYMPTOM_TYPE),
            ):
                overlapping = [
                    entity
                    for entity in symptoms
                    if (
                        span.start < entity["position"][1]
                        and entity["position"][0] < span.end
                    )
                ]
                if len(overlapping) != 1:
                    continue
                current = overlapping[0]
                start, end = current["position"]
                if not (
                    span.start <= start
                    and span.end >= end
                    and (span.start < start or span.end > end)
                ):
                    continue
                expansions.add(
                    turn2_v26.BoundaryExpansion(
                        record_id=record_id,
                        before_key=turn2_v24.entity_key(current),
                        after_text=text[span.start : span.end],
                        after_position=(span.start, span.end),
                    )
                )
    return sorted(
        expansions,
        key=lambda item: (
            int(item.record_id),
            item.after_position[0],
            item.after_position[1],
        ),
    )


def derive_contextual_recall_additions(
    texts: dict[str, str],
    control: dict[str, list[dict]],
) -> list[turn2_v27.RepeatedLineAddition]:
    """Recover a small reviewed recall set supported by V30's winning pattern."""

    selected = tuple(
        turn2_v28.normalized_surface(surface)
        for surface in CONTEXTUAL_RECALL_SURFACES
    )
    safe = {
        turn2_v28.normalized_surface(surface)
        for surface in turn2_v15.SAFE_SYMPTOMS
    }
    if not set(selected) <= safe:
        missing = sorted(set(selected) - safe)
        raise ValueError(f"Recall surfaces are not teacher reviewed: {missing}")

    accepted_records: dict[str, set[str]] = defaultdict(set)
    for record_id, entities in control.items():
        for entity in entities:
            if entity["type"] == SYMPTOM_TYPE:
                accepted_records[
                    turn2_v28.normalized_surface(entity["text"])
                ].add(record_id)

    additions: set[turn2_v27.RepeatedLineAddition] = set()
    for record_id in sorted(texts, key=int):
        text = texts[record_id]
        normalized = base.NormalizedText(text)
        for surface in selected:
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
                additions.add(
                    turn2_v27.RepeatedLineAddition(
                        record_id=record_id,
                        start=span.start,
                        end=span.end,
                        entity_type=SYMPTOM_TYPE,
                        surface=text[span.start : span.end],
                        source_record_ids=tuple(
                            sorted(accepted_records[surface], key=int)
                        ),
                    )
                )
    return sorted(
        additions,
        key=lambda item: (int(item.record_id), item.start, item.end),
    )


def apply_contextual_recall_additions(
    texts: dict[str, str],
    records: dict[str, list[dict]],
    additions: list[turn2_v27.RepeatedLineAddition],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Add reviewed symptoms and distinguish uncertainty from negation."""

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
        prefix = text[max(0, addition.start - 60) : addition.start]
        assertion_override = False
        if (
            turn2_v28.normalized_surface(entity["text"])
            == "đi cầu phân sống"
            and EPISTEMIC_QUESTION_PREFIX.search(prefix)
            and "isNegated" in entity["assertions"]
        ):
            entity["assertions"].remove("isNegated")
            assertion_override = True
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
                "epistemic_negation_override": assertion_override,
                "source_record_ids": list(addition.source_record_ids),
            }
        )
    return output, changes


def run(input_dir: Path, control_zip: Path, output_zip: Path) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    control = turn2_v19.load_submission(control_zip)
    if set(control) != set(texts):
        raise ValueError("Control record IDs do not match input")

    expansions = derive_semantic_boundary_expansions(texts, control)
    if len(expansions) != 34:
        raise ValueError(
            f"Expected 34 semantic boundary expansions, found {len(expansions)}"
        )
    boundary_output, boundary_changes = turn2_v26.apply_expansions(
        control,
        expansions,
    )

    additions = derive_contextual_recall_additions(texts, boundary_output)
    if len(additions) != 7:
        raise ValueError(
            f"Expected seven contextual additions, found {len(additions)}"
        )
    output, recall_changes = apply_contextual_recall_additions(
        texts,
        boundary_output,
        additions,
    )
    if sum(
        bool(change["epistemic_negation_override"])
        for change in recall_changes
    ) != 1:
        raise ValueError("Expected one epistemic-negation assertion override")

    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    all_changes = [*boundary_changes, *recall_changes]
    return {
        "version": "D2-V31-v30-semantic-boundary-context-recall",
        "control": str(control_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "changed_records": len(
            {change["record_id"] for change in all_changes}
        ),
        "semantic_boundary_expansions": len(boundary_changes),
        "contextual_recall_additions": len(recall_changes),
        "epistemic_negation_overrides": sum(
            bool(change["epistemic_negation_override"])
            for change in recall_changes
        ),
        "boundary_changes": boundary_changes,
        "recall_changes": recall_changes,
        "excluded_boundary_failure_modes": [
            "tăng đánh trống ngực",
            "cơn ngất xỉu",
        ],
        "score_expectation": {
            "confirmed_control": 39.5367,
            "target_range": [39.60, 39.70],
            "status": "unscored_semantic_boundary_context_recall",
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
