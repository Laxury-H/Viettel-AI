#!/usr/bin/env python3
"""Build the V49 causal split containing only the exact stroke synonym.

V49 mixed two mechanisms: an exact Vietnamese synonym and an amyloidosis
qualifier outside the entity span.  Its negative result cannot identify the
sign of the synonym independently.  V50 returns to V45 and changes only the
two existing ``tai biến mạch máu não`` entities from I63.9 (cerebral
infarction, unspecified) to I64 (stroke, not specified as haemorrhage or
infarction).

No entity, span, type, assertion, or candidate-list length changes.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

from . import turn2_v19
from . import turn2_v24
from . import turn2_v9 as base


SOURCE_LABEL = "tai biến mạch máu não"
SOURCE_CANDIDATES = ["I63.9"]
TARGET_CANDIDATES = ["I64"]
EXPECTED_CHANGES = 2


def normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold().strip()


def repair_unspecified_stroke_synonym(
    control: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Replace I63.9 only on the exact reviewed Vietnamese synonym."""

    output = copy.deepcopy(control)
    changes: list[dict] = []
    for record_id, entities in output.items():
        for entity in entities:
            if (
                entity["type"] != "CHẨN_ĐOÁN"
                or normalize(entity["text"]) != SOURCE_LABEL
                or entity.get("candidates") != SOURCE_CANDIDATES
            ):
                continue
            before = list(entity["candidates"])
            entity["candidates"] = list(TARGET_CANDIDATES)
            changes.append(
                {
                    "record_id": record_id,
                    "text": entity["text"],
                    "type": entity["type"],
                    "position": list(entity["position"]),
                    "assertions": list(entity.get("assertions", [])),
                    "before": before,
                    "after": list(entity["candidates"]),
                    "reason": "exact_vietnamese_unspecified_stroke_synonym",
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

    output, changes = repair_unspecified_stroke_synonym(control)
    if (
        len(changes) != EXPECTED_CHANGES
        or {change["record_id"] for change in changes} != {"3"}
    ):
        raise ValueError(
            f"Expected two record-3 stroke changes, found {changes}"
        )

    before_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in control.items()
    }
    after_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in output.items()
    }
    if before_keys != after_keys:
        raise AssertionError("V50 must not change entity spans or types")
    for record_id in control:
        for before, after in zip(control[record_id], output[record_id]):
            if before.get("assertions") != after.get("assertions"):
                raise AssertionError("V50 must not change assertions")
            if len(before.get("candidates", [])) != len(
                after.get("candidates", [])
            ):
                raise AssertionError(
                    "V50 must not change candidate-list length"
                )
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    v42_score_rate = (41.9476 - 41.8315) / 7
    v45_score_rate = (41.9694 - 41.9476) / 5
    return {
        "version": "D2-V50-v45-vietnam-stroke-synonym-ablation",
        "control": str(control_zip.resolve()),
        "confirmed_control_score": 41.9694,
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_changes": 0,
        "span_changes": 0,
        "type_changes": 0,
        "assertion_changes": 0,
        "candidate_changes": len(changes),
        "candidate_list_length_changes": 0,
        "record_ids": ["3"],
        "changes": changes,
        "evidence": {
            "national_icd_2026": (
                "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/"
                "06-byt-kem.pdf"
            ),
            "vietnam_icd_i64_guidance": (
                "https://syt.quangbinh.gov.vn/3cms/upload/soyte/File/"
                "BIEU%20MAU/1754-syt-nvy/ICD%2010-%20Tap%202.pdf"
            ),
            "v45_residual_projected_score": round(
                41.9694 + len(changes) * v45_score_rate, 4
            ),
            "v42_optimistic_projected_score": round(
                41.9694 + len(changes) * v42_score_rate, 4
            ),
        },
        "causal_question": (
            "Was V49 negative because of additive E85.3 qualifiers while "
            "the exact stroke synonym remains useful?"
        ),
        "leaderboard_decision_rule": {
            "wer": "must equal V45 55.4442",
            "j_assertion": "must equal V45 51.4203",
            "promote_if": "total score > 41.9694",
            "rollback": (
                "submission/candidate_v45_v42-vietnam-exact-label-"
                "cross-family.zip"
            ),
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
