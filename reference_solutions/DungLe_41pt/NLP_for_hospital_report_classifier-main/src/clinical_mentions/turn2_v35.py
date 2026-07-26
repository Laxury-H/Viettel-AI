#!/usr/bin/env python3
"""Build the final two-submission branch from isolated leaderboard signals.

This module is intentionally parameterized.  V34 measures family-scope through
J_assertion and the ICD anchor through J_candidates.  After that score arrives,
V35 can keep or drop each subsystem independently and can expand the ICD
crosswalk only when the anchor improved its isolated metric.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from . import turn2_v19
from . import turn2_v24
from . import turn2_v33
from . import turn2_v34
from . import turn2_v9 as base


# Additional source codes absent from the official Vietnam appendix, mapped to
# reviewed codes that are present in it.  B19.1/B19.2 are excluded because the
# source span combines hepatitis B and C without acute/chronic status.
VIETNAM_ICD_EXPANSION: dict[str, str] = {
    "R90.82": "R90.8",
    "Q66.50": "Q66.5",
    "E85.81": "E85.8",
    "G47.30": "G47.3",
    "K58.9": "K58.8",
    "K80.20": "K80.2",
    "C90.00": "C90.0",
    "D84.821": "D84.8",
    "D89.89": "D89.8",
    "E78.00": "E78.0",
    "F10.20": "F10.2",
    "F11.10": "F11.1",
    "G82.20": "G82.2",
    "I20.89": "I20.8",
    "I25.41": "I25.4",
    "I27.20": "I27.2",
    "I31.39": "I31.3",
    "I51.89": "I51.8",
    "I82.409": "I80.2",
    "J47.9": "J47",
    "J81.0": "J81",
    "J98.11": "J98.1",
    "K20.90": "K20",
    "K22.10": "K22.1",
    "K51.90": "K51.9",
    "K59.39": "K59.3",
    # The two source records describe tophi at finger and toe joints, i.e.
    # multiple sites.  M10.9 is flagged by the Vietnam appendix because the
    # more specific five-character site extensions must be used.
    "M1A.9XX1": "M10.90",
    "A41.01": "A41.0",
    "C50.919": "C50.9",
    "C78.00": "C78.0",
    "E05.00": "E05.0",
    "I27.81": "I27.9",
    "I31.4": "I31.9",
    "K59.09": "K59.0",
    "K65.1": "K65.0",
    "K72.90": "K74.6",
    "K85.90": "K85.9",
    "L89.94": "L89.3",
    "N46.9": "N46",
    "R18.8": "R18",
    # No open wound is described; T14.20 is the Vietnam extension for a
    # fracture of an unspecified body region without an open wound.
    "T14.8XXA": "T14.20",
    "T86.12": "T86.1",
}

VIETNAM_ICD_FULL = {
    **turn2_v34.VIETNAM_ICD_ANCHOR,
    **VIETNAM_ICD_EXPANSION,
}


def select_icd_mapping(mode: str) -> dict[str, str]:
    if mode == "drop":
        return {}
    if mode == "anchor":
        return turn2_v34.VIETNAM_ICD_ANCHOR
    if mode == "full":
        return VIETNAM_ICD_FULL
    raise ValueError(f"Unknown ICD mode: {mode}")


def run(
    input_dir: Path,
    control_zip: Path,
    output_zip: Path,
    *,
    family_scope: str,
    icd_mode: str,
) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    control = turn2_v19.load_submission(control_zip)
    if set(control) != set(texts):
        raise ValueError("Control record IDs do not match input")

    if family_scope == "keep":
        assertion_output, assertion_changes = (
            turn2_v33.repair_primary_patient_family_scope(texts, control)
        )
    elif family_scope == "drop":
        assertion_output = control
        assertion_changes = []
    else:
        raise ValueError(f"Unknown family-scope mode: {family_scope}")

    mapping = select_icd_mapping(icd_mode)
    output, candidate_changes = turn2_v34.apply_vietnam_icd_anchor(
        assertion_output,
        mapping=mapping,
    )

    expected_candidate_changes = {"drop": 0, "anchor": 149, "full": 227}
    if len(candidate_changes) != expected_candidate_changes[icd_mode]:
        raise ValueError(
            f"Expected {expected_candidate_changes[icd_mode]} candidate "
            f"changes, found {len(candidate_changes)}"
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
        raise AssertionError("V35 must not change entity spans or types")
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": (
            f"D2-V35-v30-final-family-{family_scope}-icd-{icd_mode}"
        ),
        "control": str(control_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_changes": 0,
        "span_changes": 0,
        "type_changes": 0,
        "family_scope_mode": family_scope,
        "family_scope_removals": len(assertion_changes),
        "icd_mode": icd_mode,
        "icd_mapping_size": len(mapping),
        "candidate_changes": len(candidate_changes),
        "excluded_ambiguous_codes": ["B19.1", "B19.2"],
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
    parser.add_argument(
        "--family-scope",
        choices=("keep", "drop"),
        required=True,
    )
    parser.add_argument(
        "--icd-mode",
        choices=("drop", "anchor", "full"),
        required=True,
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    summary = run(
        args.input,
        args.control_zip,
        args.zip,
        family_scope=args.family_scope,
        icd_mode=args.icd_mode,
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
