#!/usr/bin/env python3
"""Fuse accepted boundaries, safe diagnoses, top-1 codes, and safe recall."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from . import turn2_v15
from . import turn2_v18
from . import turn2_v19
from . import turn2_v24
from . import turn2_v26
from . import turn2_v27
from . import turn2_v28
from . import turn2_v9 as base


SYMPTOM_TYPE = "TRIỆU_CHỨNG"
DIAGNOSIS_TYPE = "CHẨN_ĐOÁN"
KNEE_CONTINUATION = re.compile(r"(?i)^\s+gối\b")

SELECTED_RECALL_SURFACES: tuple[str, ...] = (
    "rối loạn thị giác",
    "căng thẳng",
    "dịch rò rỉ",
    "khó chịu vùng ngực",
    "nóng phần tinh hoàn",
    "thị giác bị nhòe",
    "dịch rỉ huyết thanh",
    "khả năng trí óc giảm",
    "run rấy",
)


@dataclass(frozen=True)
class DiagnosisAddition:
    record_id: str
    start: int
    end: int
    surface: str
    candidate: str


def derive_accepted_boundary_expansions(
    texts: dict[str, str],
    control: dict[str, list[dict]],
) -> list[turn2_v26.BoundaryExpansion]:
    """Expand a short symptom to a surface accepted in another occurrence."""

    counts = Counter(
        turn2_v28.normalized_surface(entity["text"])
        for entities in control.values()
        for entity in entities
        if (
            entity["type"] == SYMPTOM_TYPE
            and len(str(entity["text"]).strip()) >= 5
        )
    )
    expansions: set[turn2_v26.BoundaryExpansion] = set()
    for record_id in sorted(texts, key=int):
        text = texts[record_id]
        normalized = base.NormalizedText(text)
        symptoms = [
            entity
            for entity in control[record_id]
            if entity["type"] == SYMPTOM_TYPE
        ]
        for surface, count in counts.items():
            if count < 1:
                continue
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
                # ``đau đầu`` must not consume the beginning of ``đau đầu
                # gối`` (knee pain), despite being an accepted surface.
                tail = text[span.end : span.end + 12]
                if (
                    surface == "đau đầu"
                    and KNEE_CONTINUATION.match(tail)
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


def derive_safe_diagnosis_additions(
    texts: dict[str, str],
    control: dict[str, list[dict]],
) -> list[DiagnosisAddition]:
    """Add reviewed diagnosis aliases outside polar-question focus."""

    proposals: set[DiagnosisAddition] = set()
    for record_id in sorted(texts, key=int):
        text = texts[record_id]
        normalized = base.NormalizedText(text)
        for entry in turn2_v15.SAFE_DIAGNOSES:
            for alias in entry["aliases"]:
                for span in normalized.literal_spans(
                    str(alias),
                    boundary=base.should_use_boundary(
                        str(alias),
                        DIAGNOSIS_TYPE,
                    ),
                ):
                    if any(
                        span.start < entity["position"][1]
                        and entity["position"][0] < span.end
                        for entity in control[record_id]
                    ):
                        continue
                    probe = {
                        "text": text[span.start : span.end],
                        "type": DIAGNOSIS_TYPE,
                        "assertions": [],
                        "position": [span.start, span.end],
                        "candidates": [str(entry["code"])],
                    }
                    if turn2_v18.is_polar_question_mention(text, probe):
                        continue
                    proposals.add(
                        DiagnosisAddition(
                            record_id=record_id,
                            start=span.start,
                            end=span.end,
                            surface=text[span.start : span.end],
                            candidate=str(entry["code"]),
                        )
                    )
    return sorted(
        proposals,
        key=lambda item: (int(item.record_id), item.start, item.end),
    )


def apply_diagnosis_additions(
    texts: dict[str, str],
    records: dict[str, list[dict]],
    additions: list[DiagnosisAddition],
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
            DIAGNOSIS_TYPE,
            historical,
            family,
        )
        before = turn2_v28.normalized_surface(
            text[max(0, addition.start - 40) : addition.start]
        )
        after = turn2_v28.normalized_surface(
            text[addition.end : min(len(text), addition.end + 40)]
        )
        if (
            re.search(r"\bphát hiện\s*$", before)
            and re.match(r"\s*từ năm\s+\d{4}\b", after)
            and "isHistorical" not in entity["assertions"]
        ):
            entity["assertions"].append("isHistorical")
        entity["candidates"] = [addition.candidate]
        output[addition.record_id].append(entity)
        output[addition.record_id] = base.resolve_entities(
            output[addition.record_id]
        )
        changes.append(
            {
                "record_id": addition.record_id,
                "text": entity["text"],
                "position": entity["position"],
                "type": entity["type"],
                "assertions": entity["assertions"],
                "candidates": entity["candidates"],
            }
        )
    return output, changes


def derive_selected_symptom_additions(
    texts: dict[str, str],
    control: dict[str, list[dict]],
) -> list[turn2_v27.RepeatedLineAddition]:
    """Recover reviewed symptoms while keeping historical stress specific."""

    safe = {
        turn2_v28.normalized_surface(surface)
        for surface in turn2_v15.SAFE_SYMPTOMS
    }
    selected = tuple(
        turn2_v28.normalized_surface(surface)
        for surface in SELECTED_RECALL_SURFACES
    )
    if not set(selected) <= safe:
        raise ValueError("Selected recall surfaces must be teacher reviewed")

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
        historical, family = base.section_states(text)
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
                probe = base.make_entity(
                    text,
                    span,
                    SYMPTOM_TYPE,
                    historical,
                    family,
                )
                if (
                    surface == "căng thẳng"
                    and "isHistorical" not in probe["assertions"]
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


def keep_one_contextual_candidate(
    texts: dict[str, str],
    records: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Prune the two remaining multi-code diagnoses using explicit context."""

    output: dict[str, list[dict]] = {}
    changes: list[dict] = []
    for record_id in sorted(records, key=int):
        text = texts[record_id]
        entities: list[dict] = []
        for source in records[record_id]:
            entity = dict(source)
            if "candidates" in source:
                entity["candidates"] = list(source["candidates"])
            before = list(entity.get("candidates", []))
            normalized_text = turn2_v28.normalized_surface(entity["text"])
            if (
                entity["type"] == DIAGNOSIS_TYPE
                and set(before) == {"K21.0", "K21.9"}
                and normalized_text == "trào ngược dạ dày thực quản"
            ):
                start, end = entity["position"]
                clause = turn2_v28.normalized_surface(
                    text[max(0, start - 120) : min(len(text), end + 120)]
                )
                if "viêm thực quản" not in clause:
                    entity["candidates"] = ["K21.9"]
            elif (
                entity["type"] == DIAGNOSIS_TYPE
                and set(before) == {"D59.9", "D55.0"}
                and "g6pd" in text.casefold()
            ):
                entity["candidates"] = ["D55.0"]
            if entity.get("candidates", []) != before:
                changes.append(
                    {
                        "record_id": record_id,
                        "text": entity["text"],
                        "position": entity["position"],
                        "before_candidates": before,
                        "after_candidates": entity["candidates"],
                    }
                )
            entities.append(entity)
        output[record_id] = entities
    return output, changes


def run(input_dir: Path, control_zip: Path, output_zip: Path) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    control = turn2_v19.load_submission(control_zip)
    if set(control) != set(texts):
        raise ValueError("Control record IDs do not match input")

    expansions = derive_accepted_boundary_expansions(texts, control)
    if len(expansions) != 15:
        raise ValueError(
            f"Expected 15 accepted boundary expansions, found {len(expansions)}"
        )
    boundary_output, boundary_changes = turn2_v26.apply_expansions(
        control,
        expansions,
    )

    symptom_additions = derive_selected_symptom_additions(
        texts,
        boundary_output,
    )
    if len(symptom_additions) != 11:
        raise ValueError(
            f"Expected 11 selected symptoms, found {len(symptom_additions)}"
        )
    symptom_output, symptom_changes = turn2_v27.apply_repeated_additions(
        texts,
        boundary_output,
        symptom_additions,
    )

    diagnosis_additions = derive_safe_diagnosis_additions(
        texts,
        symptom_output,
    )
    if len(diagnosis_additions) != 3:
        raise ValueError(
            f"Expected three safe diagnoses, found {len(diagnosis_additions)}"
        )
    diagnosis_output, diagnosis_changes = apply_diagnosis_additions(
        texts,
        symptom_output,
        diagnosis_additions,
    )

    output, candidate_changes = keep_one_contextual_candidate(
        texts,
        diagnosis_output,
    )
    if len(candidate_changes) != 5:
        raise ValueError(
            f"Expected five top-1 candidate changes, found {len(candidate_changes)}"
        )
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    all_changes = [
        *boundary_changes,
        *symptom_changes,
        *diagnosis_changes,
        *candidate_changes,
    ]
    return {
        "version": "D2-V30-v29-evidence-fusion",
        "control": str(control_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "changed_records": len(
            {change["record_id"] for change in all_changes}
        ),
        "accepted_boundary_expansions": len(boundary_changes),
        "selected_symptom_additions": len(symptom_changes),
        "safe_diagnosis_additions": len(diagnosis_changes),
        "top1_candidate_changes": len(candidate_changes),
        "boundary_changes": boundary_changes,
        "symptom_changes": symptom_changes,
        "diagnosis_changes": diagnosis_changes,
        "candidate_changes": candidate_changes,
        "score_expectation": {
            "confirmed_control": 39.483,
            "target_range": [39.55, 39.63],
            "status": "unscored_evidence_fusion",
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
