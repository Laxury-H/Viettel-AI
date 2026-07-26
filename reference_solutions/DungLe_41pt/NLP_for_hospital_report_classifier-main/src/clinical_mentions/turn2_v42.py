#!/usr/bin/env python3
"""Build a candidate-only batch from exact labels used by Vietnamese hospitals.

V34/V35 established that the leaderboard candidate dialect follows the
Vietnamese ICD catalogue.  V42 extends that result from "code exists in the
catalogue" to "surface is the catalogue's exact Vietnamese diagnosis label".

Only exact diagnosis text with a reviewed source candidate is rewritten.
Entity spans, types and assertions remain identical to V37 production.
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


EXACT_HOSPITAL_ICD_LABELS: dict[str, dict] = {
    "bệnh tim mạch do xơ vữa động mạch": {
        "before": ["I70.90"],
        "after": ["I25.1"],
        "evidence": "official_and_hospital_exact_label",
    },
    "u xơ tuyến vú": {
        "before": ["D24"],
        "after": ["N60.2"],
        "evidence": "official_hospital_catalogue_and_chart_statistics",
    },
}


def normalize_label(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold().strip()


def repair_exact_hospital_icd_labels(
    control: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Rewrite only reviewed exact Vietnamese hospital ICD labels."""

    output = copy.deepcopy(control)
    changes: list[dict] = []
    for record_id, entities in output.items():
        for entity in entities:
            if entity["type"] != "CHẨN_ĐOÁN":
                continue
            target = EXACT_HOSPITAL_ICD_LABELS.get(
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
                    "reason": target["evidence"],
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

    output, changes = repair_exact_hospital_icd_labels(control)
    reason_counts = {
        reason: sum(change["reason"] == reason for change in changes)
        for reason in {
            target["evidence"] for target in EXACT_HOSPITAL_ICD_LABELS.values()
        }
    }
    if len(changes) != 7 or reason_counts != {
        "official_and_hospital_exact_label": 2,
        "official_hospital_catalogue_and_chart_statistics": 5,
    }:
        raise ValueError(
            f"Expected exact-label split 2/5, found {len(changes)} "
            f"with {reason_counts}"
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
        raise AssertionError("V42 must not change entity spans or types")
    for record_id in control:
        for before, after in zip(control[record_id], output[record_id]):
            if before.get("assertions") != after.get("assertions"):
                raise AssertionError("V42 must not change assertions")
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V42-v37-vietnam-hospital-exact-label-batch",
        "control": str(control_zip.resolve()),
        "confirmed_control_score": 41.8315,
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_changes": 0,
        "span_changes": 0,
        "type_changes": 0,
        "assertion_changes": 0,
        "candidate_changes": len(changes),
        "reason_counts": reason_counts,
        "changes": changes,
        "evidence": {
            "national_icd_2026": (
                "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/"
                "06-byt-kem.pdf"
            ),
            "hospital_icd_catalogue": (
                "https://phusannhidanang.org.vn/TraCuuXetNghiem/"
                "lstICD/GetICD"
            ),
            "hospital_chart_statistics": (
                "https://tapchinghiencuuyhoc.vn/index.php/tcncyh/"
                "article/download/1039/722"
            ),
            "mean_j_candidates_gain_per_successful_v34_v35_change": 0.02489,
            "projected_j_candidates_if_all_match": 32.7709,
            "projected_score_if_all_match": 41.9012,
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
