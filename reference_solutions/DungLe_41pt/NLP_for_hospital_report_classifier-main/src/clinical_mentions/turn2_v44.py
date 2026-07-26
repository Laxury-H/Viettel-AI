#!/usr/bin/env python3
"""Split three exact Vietnamese I51 diagnosis labels from the V42 control.

V42 showed that exact Vietnamese hospital terminology is a productive signal
for the hidden candidate labels.  V44 stays inside that confirmed intervention
class and fixes two distinctions in the same ICD family:

* ``viêm tim`` is carditis (I51.8), not unspecified myocarditis (I51.4);
* ``bệnh tim mạch`` is unspecified cardiovascular disease (I51.6), not
  unspecified heart disease (I51.9).

Only candidate lists are rewritten.  Entity text, spans, types and assertions
remain byte-for-byte equivalent to the V42 production submission.
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


EXACT_VIETNAM_I51_LABELS: dict[str, dict] = {
    "viêm tim": {
        "before": ["I51.4"],
        "after": ["I51.8"],
        "expected_count": 1,
        "reason": "official_i51_carditis_inclusion_not_myocarditis",
    },
    "bệnh tim mạch": {
        "before": ["I51.9"],
        "after": ["I51.6"],
        "expected_count": 2,
        "reason": "exact_hospital_i51_cardiovascular_label",
    },
}


def normalize_label(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold().strip()


def repair_exact_vietnam_i51_labels(
    control: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Rewrite only reviewed, exact I51 candidate labels."""

    output = copy.deepcopy(control)
    changes: list[dict] = []
    for record_id, entities in output.items():
        for entity in entities:
            if entity["type"] != "CHẨN_ĐOÁN":
                continue
            normalized = normalize_label(entity["text"])
            target = EXACT_VIETNAM_I51_LABELS.get(normalized)
            if target is None or entity.get("candidates") != target["before"]:
                continue
            before = list(entity["candidates"])
            entity["candidates"] = list(target["after"])
            changes.append(
                {
                    "record_id": record_id,
                    "text": entity["text"],
                    "type": entity["type"],
                    "position": list(entity["position"]),
                    "assertions": list(entity.get("assertions", [])),
                    "before": before,
                    "after": list(entity["candidates"]),
                    "reason": target["reason"],
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

    output, changes = repair_exact_vietnam_i51_labels(control)
    observed_counts = {
        label: sum(
            normalize_label(change["text"]) == label for change in changes
        )
        for label in EXACT_VIETNAM_I51_LABELS
    }
    expected_counts = {
        label: target["expected_count"]
        for label, target in EXACT_VIETNAM_I51_LABELS.items()
    }
    if observed_counts != expected_counts:
        raise ValueError(
            f"Expected exact I51 counts {expected_counts}, found "
            f"{observed_counts}"
        )
    if len(changes) != 3:
        raise ValueError(f"Expected 3 candidate changes, found {len(changes)}")

    before_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in control.items()
    }
    after_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in output.items()
    }
    if before_keys != after_keys:
        raise AssertionError("V44 must not change entity spans or types")
    for record_id in control:
        for before, after in zip(control[record_id], output[record_id]):
            if before.get("assertions") != after.get("assertions"):
                raise AssertionError("V44 must not change assertions")
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    observed_gain_per_change = (41.9476 - 41.8315) / 7
    return {
        "version": "D2-V44-v42-vietnam-i51-exact-label-split",
        "control": str(control_zip.resolve()),
        "confirmed_control_score": 41.9476,
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_changes": 0,
        "span_changes": 0,
        "type_changes": 0,
        "assertion_changes": 0,
        "candidate_changes": len(changes),
        "record_ids": sorted(
            {change["record_id"] for change in changes}, key=int
        ),
        "label_counts": observed_counts,
        "changes": changes,
        "evidence": {
            "national_icd_2026": (
                "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/"
                "06-byt-kem.pdf"
            ),
            "ministry_implementation_notice": (
                "https://kcb.vn/tin-tuc/cong-van-so-4059-byt-bh-trien-"
                "khai-thong-tu-06-2026-tt-byt-quy-dinh-ma-hoa-benh-"
                "tat-theo-icd-10.html"
            ),
            "hospital_i51_catalogue": (
                "https://phusannhidanang.org.vn/TraCuuXetNghiem/"
                "lstICD/GetICD?page=371"
            ),
            "v42_observed_gain_per_candidate_change": round(
                observed_gain_per_change, 7
            ),
            "conditional_projected_score_if_all_three_match": round(
                41.9476 + 3 * observed_gain_per_change, 4
            ),
        },
        "leaderboard_decision_rule": {
            "wer": "must equal V42 55.4442",
            "j_assertion": "must equal V42 51.4203",
            "promote_if": "J_candidates > 32.8870 and total score > 41.9476",
            "reject_if": "WER or J_assertion changes, because V44 is candidate-only",
        },
        "submission_priority": (
            "high: isolated candidate-only continuation of the V42 signal"
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
