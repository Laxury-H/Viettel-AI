#!/usr/bin/env python3
"""Probe two orthogonal Vietnamese-clinical subsystems on the V30 control.

Subsystem A fixes ``isFamily`` scope when a relative is the primary patient in
a consultation.  Subsystem B replaces frequent US ICD-10-CM extensions with
the corresponding codes in Vietnam's official WHO-2019-based ICD-10 list.

The two interventions are deliberately orthogonal:

* family-scope changes can only move J_assertion;
* ICD changes can only move J_candidates;
* entity text, boundaries, types, and therefore WER remain byte-identical.
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
from . import turn2_v9 as base


DIAGNOSIS_TYPE = "CHẨN_ĐOÁN"

# High-frequency, direct-equivalence anchor set.  Every target is present in
# the official appendix to Circular 06/2026/TT-BYT, while every source code is
# absent from that appendix.  Ambiguous semantic remaps are intentionally
# deferred until this code-system hypothesis has leaderboard evidence.
VIETNAM_ICD_ANCHOR: dict[str, str] = {
    "K29.70": "K29.7",  # gastritis, unspecified
    "D75.A": "D55.0",  # G6PD deficiency
    "H47.10": "H47.1",  # papilloedema
    "I25.10": "I25.1",  # atherosclerotic heart disease
    "G43.909": "G43.9",  # migraine, unspecified
    "C92.10": "C92.1",  # chronic myeloid leukaemia
    "I48.91": "I48.9",  # atrial fibrillation/flutter, unspecified
    "K80.50": "K80.5",  # calculus of bile duct
    "I26.99": "I26.9",  # pulmonary embolism
    "L03.90": "L03.9",  # cellulitis, unspecified
    "D24.9": "D24",  # benign neoplasm of breast
    "D68.59": "D68.5",  # primary thrombophilia
    "N60.09": "N60.0",  # solitary cyst of breast
    "O14.90": "O14.9",  # pre-eclampsia, unspecified
    "G47.33": "G47.3",  # sleep apnoea
    "I62.03": "I62.0",  # nontraumatic subdural haemorrhage
    "K05.30": "K05.3",  # chronic periodontitis
    "K70.30": "K70.3",  # alcoholic cirrhosis of liver
    "N40.0": "N40",  # hyperplasia of prostate
    # The source records describe a closed injury after a fall; Vietnam's
    # five-character extension S06.30 is focal brain injury without an open
    # intracranial wound.
    "S06.33": "S06.30",
}

OFFICIAL_VIETNAM_SOURCE = (
    "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/06-byt-kem.pdf"
)


def apply_vietnam_icd_anchor(
    records: dict[str, list[dict]],
    mapping: dict[str, str] | None = None,
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Apply direct ICD-10-CM to Vietnam ICD-10 code replacements."""

    selected_mapping = VIETNAM_ICD_ANCHOR if mapping is None else mapping
    output: dict[str, list[dict]] = {}
    changes: list[dict] = []
    for record_id in sorted(records, key=int):
        entities: list[dict] = []
        for source in records[record_id]:
            entity = dict(source)
            entity["assertions"] = list(source["assertions"])
            if "candidates" in source:
                before = list(source["candidates"])
                after = [
                    selected_mapping.get(candidate, candidate)
                    if source["type"] == DIAGNOSIS_TYPE
                    else candidate
                    for candidate in before
                ]
                entity["candidates"] = after
                if after != before:
                    changes.append(
                        {
                            "record_id": record_id,
                            "text": source["text"],
                            "position": list(source["position"]),
                            "before_candidates": before,
                            "after_candidates": after,
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

    assertion_output, assertion_changes = (
        turn2_v33.repair_primary_patient_family_scope(texts, control)
    )
    if (
        len(assertion_changes) != 18
        or {change["record_id"] for change in assertion_changes}
        != {"64", "80", "95"}
    ):
        raise ValueError("Expected the reviewed 18 family-scope removals")

    output, candidate_changes = apply_vietnam_icd_anchor(assertion_output)
    if len(candidate_changes) != 149:
        raise ValueError(
            "Expected 149 high-frequency Vietnam ICD replacements, found "
            f"{len(candidate_changes)}"
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
        raise AssertionError("V34 must not change entity spans or types")

    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V34-v30-vietnam-clinical-orthogonal-probe",
        "control": str(control_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_changes": 0,
        "span_changes": 0,
        "type_changes": 0,
        "family_scope_removals": len(assertion_changes),
        "family_scope_records": sorted(
            {change["record_id"] for change in assertion_changes}, key=int
        ),
        "candidate_changes": len(candidate_changes),
        "candidate_source_codes": len(VIETNAM_ICD_ANCHOR),
        "candidate_records": len(
            {change["record_id"] for change in candidate_changes}
        ),
        "official_vietnam_icd_source": OFFICIAL_VIETNAM_SOURCE,
        "assertion_changes": assertion_changes,
        "icd_changes": candidate_changes,
        "leaderboard_decision_rule": {
            "wer": "must equal V30 55.4442",
            "keep_family_scope_if": "J_assertion > 51.3029",
            "keep_icd_anchor_if": "J_candidates > 26.9477",
            "final_submission": (
                "retain only winning subsystems; expand Vietnam ICD mapping "
                "only if its isolated candidate metric improves"
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
