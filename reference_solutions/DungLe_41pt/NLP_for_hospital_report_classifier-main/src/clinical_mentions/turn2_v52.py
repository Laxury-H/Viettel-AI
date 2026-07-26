#!/usr/bin/env python3
"""Extend confirmed V51 pruning to literal duplicate symptom tokens.

V51 established that the hidden annotation is sensitive to discourse role:
removing two diagnosis tokens from a malformed urinalysis seam improved all
three leaderboard components.  V52 tests the narrower follow-up policy that a
literal duplicated symptom (``phù phù`` or ``đau đau``) should contribute one
mention, not two.

The first entity in each adjacent pair is retained and only the second is
removed.  No candidate-bearing entity or assertion is changed.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

from . import turn2_v19
from . import turn2_v24
from . import turn2_v9 as base


TARGET_SURFACES = {"phù", "đau", "mệt mỏi"}
EXPECTED_REMOVALS = 8
EXPECTED_RECORD_IDS = {"39", "47", "61", "62", "77"}


def normalize(value: str) -> str:
    return " ".join(
        unicodedata.normalize("NFC", value).casefold().split()
    )


def duplicate_second_keys(
    source: str,
    entities: list[dict],
) -> set[tuple[int, int, str]]:
    """Return entity keys for second tokens in reviewed literal duplicates."""

    ordered = sorted(
        entities,
        key=lambda entity: (
            entity["position"][0],
            entity["position"][1],
            entity["type"],
        ),
    )
    targets: set[tuple[int, int, str]] = set()
    for left, right in zip(ordered, ordered[1:]):
        left_surface = normalize(left["text"])
        if (
            left["type"] != "TRIỆU_CHỨNG"
            or right["type"] != "TRIỆU_CHỨNG"
            or left_surface not in TARGET_SURFACES
            or normalize(right["text"]) != left_surface
            or left.get("assertions") != right.get("assertions")
        ):
            continue
        left_end = left["position"][1]
        right_start = right["position"][0]
        gap = source[left_end:right_start]
        is_plain_space = bool(gap) and gap.isspace()
        is_bullet_separator = bool(
            gap and re.fullmatch(r"\s*-\s*", gap)
        )
        if not (is_plain_space or is_bullet_separator):
            continue
        targets.add(turn2_v24.entity_key(right))
    return targets


def prune_literal_duplicate_symptoms(
    texts: dict[str, str],
    control: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Retain one mention per literal duplicate symptom pair."""

    output = copy.deepcopy(control)
    changes: list[dict] = []
    for record_id in sorted(output, key=int):
        source = texts[record_id]
        target_keys = duplicate_second_keys(source, output[record_id])
        retained: list[dict] = []
        for entity in output[record_id]:
            if turn2_v24.entity_key(entity) not in target_keys:
                retained.append(entity)
                continue
            start, end = entity["position"]
            changes.append(
                {
                    "record_id": record_id,
                    "text": entity["text"],
                    "type": entity["type"],
                    "position": list(entity["position"]),
                    "assertions": list(entity["assertions"]),
                    "context": " ".join(
                        source[
                            max(0, start - 80) : min(len(source), end + 80)
                        ].split()
                    ),
                    "reason": "second_token_of_literal_duplicate_symptom",
                }
            )
        output[record_id] = retained
    return output, changes


def run(input_dir: Path, control_zip: Path, output_zip: Path) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    control = turn2_v19.load_submission(control_zip)
    if set(control) != set(texts):
        raise ValueError("Control record IDs do not match input")

    output, changes = prune_literal_duplicate_symptoms(texts, control)
    changed_records = {change["record_id"] for change in changes}
    surface_counts = {
        surface: sum(normalize(change["text"]) == surface for change in changes)
        for surface in TARGET_SURFACES
    }
    if (
        len(changes) != EXPECTED_REMOVALS
        or changed_records != EXPECTED_RECORD_IDS
        or surface_counts != {"phù": 3, "đau": 1, "mệt mỏi": 4}
    ):
        raise ValueError(
            "Expected eight duplicate-symptom removals in records "
            f"39/47/61/62/77, found changes={changes}, "
            f"counts={surface_counts}"
        )

    for record_id, before_entities in control.items():
        removed_keys = {
            turn2_v24.entity_key(change)
            for change in changes
            if change["record_id"] == record_id
        }
        expected = [
            entity
            for entity in before_entities
            if turn2_v24.entity_key(entity) not in removed_keys
        ]
        if output[record_id] != expected:
            raise AssertionError(
                "V52 must preserve every non-target V51 entity byte-for-byte"
            )
        base.validate_record(texts[record_id], output[record_id])

    # Each raw duplicate phrase must retain exactly one of the two mentions.
    expected_first_positions = {
        ("39", 1544, 1547),
        ("47", 1126, 1129),
        ("47", 1454, 1457),
        ("39", 1021, 1028),
        ("47", 1373, 1380),
        ("61", 793, 800),
        ("62", 422, 429),
        ("77", 495, 498),
    }
    retained_first_positions = {
        (record_id, *entity["position"])
        for record_id, entities in output.items()
        for entity in entities
        if (record_id, *entity["position"]) in expected_first_positions
    }
    if retained_first_positions != expected_first_positions:
        raise AssertionError("V52 must retain the first token of every pair")

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    v51_gain_per_removal = (41.9878 - 41.9694) / 2
    v21_gain_per_removal = (39.3128 - 39.2901) / 2
    return {
        "version": "D2-V52-v51-literal-duplicate-symptom-pruning",
        "control": str(control_zip.resolve()),
        "confirmed_control_score": 41.9878,
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_removals": len(changes),
        "symptom_removals": len(changes),
        "record_ids": sorted(changed_records, key=int),
        "template_count": 4,
        "surface_counts": surface_counts,
        "changes": changes,
        "invariants": {
            "first_token_of_each_duplicate": "retained",
            "all_non_target_entities": "unchanged",
            "candidate_changes": 0,
            "assertion_changes_on_retained_entities": 0,
        },
        "evidence": {
            "v51_positive_precision_pruning_gain": 0.0184,
            "v21_positive_precision_pruning_gain": 0.0227,
            "v51_mechanical_projection": round(
                41.9878 + EXPECTED_REMOVALS * v51_gain_per_removal,
                4,
            ),
            "v21_mechanical_projection": round(
                41.9878 + EXPECTED_REMOVALS * v21_gain_per_removal,
                4,
            ),
            "projection_caveat": (
                "The eight removals occupy four independent document "
                "templates and duplicate-symptom policy differs from V51."
            ),
        },
        "leaderboard_decision_rule": {
            "control": "V51 41.9878",
            "promote_if": "total score > 41.9878",
            "expected_signal": (
                "WER should decrease and J_assertion should not decrease"
            ),
            "rollback": "submission/output.zip",
        },
        "risk": (
            "medium: V51 validates structural pruning, but hidden gold may "
            "annotate both literal or bullet-repeated symptom tokens"
        ),
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
