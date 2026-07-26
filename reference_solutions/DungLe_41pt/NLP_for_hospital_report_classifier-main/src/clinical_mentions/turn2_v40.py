#!/usr/bin/env python3
"""Compose the confirmed V37 production with V39 seam repairs.

V37 is now leaderboard-confirmed.  Applying the six V39 assertion repairs on
top of V37 preserves every known gain while making the next submission a
direct six-change assertion ablation against the current production.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from . import turn2_v19
from . import turn2_v24
from . import turn2_v39
from . import turn2_v9 as base


def run(input_dir: Path, control_zip: Path, output_zip: Path) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    control = turn2_v19.load_submission(control_zip)
    if set(control) != set(texts):
        raise ValueError("Control record IDs do not match input")

    before_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in control.items()
    }
    output, changes = turn2_v39.repair_hybrid_seam_assertions(texts, control)
    reason_counts = {
        reason: sum(change["reason"] == reason for change in changes)
        for reason in (
            "current_question",
            "generic_education",
            "generic_advice",
        )
    }
    if len(changes) != 6 or reason_counts != {
        "current_question": 2,
        "generic_education": 2,
        "generic_advice": 2,
    }:
        raise ValueError(
            "Expected six seam repairs split 2/2/2, found "
            f"{len(changes)} with {reason_counts}"
        )

    after_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in output.items()
    }
    if before_keys != after_keys:
        raise AssertionError("V40 must not change entity spans or types")
    for record_id in control:
        for before, after in zip(control[record_id], output[record_id]):
            if before.get("candidates") != after.get("candidates"):
                raise AssertionError("V40 must not change candidates")
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V40-v37-hybrid-document-seam-assertion-probe",
        "control": str(control_zip.resolve()),
        "confirmed_control_score": 41.8315,
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_changes": 0,
        "span_changes": 0,
        "type_changes": 0,
        "candidate_changes": 0,
        "assertion_changes": len(changes),
        "reason_counts": reason_counts,
        "changes": changes,
        "leaderboard_decision_rule": {
            "wer": "must equal V37 55.4442",
            "j_candidates": "must equal V37 32.5967",
            "promote_if": "J_assertion > 51.4203 and total score > 41.8315",
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
