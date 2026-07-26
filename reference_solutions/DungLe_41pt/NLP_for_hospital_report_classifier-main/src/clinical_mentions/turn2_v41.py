#!/usr/bin/env python3
"""Correct exact Vietnamese ICD labels whose current code is in another branch.

The confirmed V35 crosswalk fixed codes that were absent from the Vietnamese
ICD-10 appendix.  This probe addresses a different residual error: an entity
whose text is itself the official Vietnamese label for I25.1, but whose
candidate is currently the nonspecific atherosclerosis code I70.90.

Only the two exact repeated mentions are changed.  Entity spans, types and
assertions are kept byte-for-byte identical to the V37 production control.
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


EXACT_VIETNAM_ICD_LABELS: dict[str, dict] = {
    "bệnh tim mạch do xơ vữa động mạch": {
        "before": ["I70.90"],
        "after": ["I25.1"],
    }
}


def normalize_label(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold().strip()


def repair_exact_vietnam_icd_labels(
    control: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Apply the reviewed exact-label repairs to a copied submission."""

    output = copy.deepcopy(control)
    changes: list[dict] = []
    for record_id, entities in output.items():
        for entity in entities:
            if entity["type"] != "CHẨN_ĐOÁN":
                continue
            target = EXACT_VIETNAM_ICD_LABELS.get(
                normalize_label(entity["text"])
            )
            if target is None or entity.get("candidates") != target["before"]:
                continue
            before = entity["candidates"]
            entity["candidates"] = list(target["after"])
            changes.append(
                {
                    "record_id": record_id,
                    "text": entity["text"],
                    "type": entity["type"],
                    "position": entity["position"],
                    "before": before,
                    "after": entity["candidates"],
                    "reason": "exact_official_vietnam_icd_label",
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

    output, changes = repair_exact_vietnam_icd_labels(control)
    if len(changes) != 2:
        raise ValueError(f"Expected 2 candidate changes, found {len(changes)}")

    before_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in control.items()
    }
    after_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in output.items()
    }
    if before_keys != after_keys:
        raise AssertionError("V41 must not change entity spans or types")
    for record_id in control:
        for before, after in zip(control[record_id], output[record_id]):
            if before.get("assertions") != after.get("assertions"):
                raise AssertionError("V41 must not change assertions")
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V41-v37-vietnam-icd-exact-label-correction",
        "control": str(control_zip.resolve()),
        "confirmed_control_score": 41.8315,
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_changes": 0,
        "span_changes": 0,
        "type_changes": 0,
        "assertion_changes": 0,
        "candidate_changes": len(changes),
        "changes": changes,
        "evidence": {
            "official_vietnam_icd_source": (
                "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/"
                "06-byt-kem.pdf"
            ),
            "exact_label": "Bệnh tim mạch do xơ vữa động mạch",
            "official_code": "I25.1",
            "mean_j_candidates_gain_per_successful_v34_v35_change": 0.02489,
            "projected_j_candidates_if_both_match": 32.6465,
            "projected_score_if_both_match": 41.8514,
        },
        "leaderboard_decision_rule": {
            "wer": "must equal V37 55.4442",
            "j_assertion": "must equal V37 51.4203",
            "promote_if": "J_candidates > 32.5967 and total score > 41.8315",
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
