#!/usr/bin/env python3
"""Build the high-confidence cross-family Vietnamese exact-label batch.

V45 supersedes the narrower V44 artifact for submission.  It retains V44's
three reviewed I51 repairs and adds the exact Vietnamese distinction between
unspecified stroke (I64) and unspecified cerebral infarction (I63.9).

All five rewrites are candidate-only.  This intentionally excludes the
context-dependent ``tăng nhãn áp``/intracranial-pressure hypothesis and every
entity-boundary or recall change.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

from . import turn2_v19
from . import turn2_v24
from . import turn2_v44
from . import turn2_v9 as base


EXACT_STROKE_LABEL: dict[str, dict] = {
    "đột quỵ": {
        "before": ["I63.9"],
        "after": ["I64"],
        "expected_count": 2,
        "reason": "official_unspecified_stroke_not_cerebral_infarction",
    },
}


def normalize_label(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold().strip()


def repair_exact_vietnam_labels(
    control: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Apply the reviewed I51 and I64 exact-label distinctions."""

    output, i51_changes = turn2_v44.repair_exact_vietnam_i51_labels(control)
    stroke_changes: list[dict] = []
    for record_id, entities in output.items():
        for entity in entities:
            if entity["type"] != "CHẨN_ĐOÁN":
                continue
            normalized = normalize_label(entity["text"])
            target = EXACT_STROKE_LABEL.get(normalized)
            if target is None or entity.get("candidates") != target["before"]:
                continue
            before = list(entity["candidates"])
            entity["candidates"] = list(target["after"])
            stroke_changes.append(
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
    return output, [*i51_changes, *stroke_changes]


def run(input_dir: Path, control_zip: Path, output_zip: Path) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    control = turn2_v19.load_submission(control_zip)
    if set(control) != set(texts):
        raise ValueError("Control record IDs do not match input")

    output, changes = repair_exact_vietnam_labels(control)
    if len(changes) != 5:
        raise ValueError(f"Expected 5 exact-label changes, found {len(changes)}")
    change_counts = {
        "I51.4->I51.8": sum(
            change["before"] == ["I51.4"] and change["after"] == ["I51.8"]
            for change in changes
        ),
        "I51.9->I51.6": sum(
            change["before"] == ["I51.9"] and change["after"] == ["I51.6"]
            for change in changes
        ),
        "I63.9->I64": sum(
            change["before"] == ["I63.9"] and change["after"] == ["I64"]
            for change in changes
        ),
    }
    if change_counts != {
        "I51.4->I51.8": 1,
        "I51.9->I51.6": 2,
        "I63.9->I64": 2,
    }:
        raise ValueError(f"Unexpected V45 change counts: {change_counts}")

    before_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in control.items()
    }
    after_keys = {
        record_id: [turn2_v24.entity_key(entity) for entity in entities]
        for record_id, entities in output.items()
    }
    if before_keys != after_keys:
        raise AssertionError("V45 must not change entity spans or types")
    for record_id in control:
        for before, after in zip(control[record_id], output[record_id]):
            if before.get("assertions") != after.get("assertions"):
                raise AssertionError("V45 must not change assertions")
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    v42_score_gain_per_change = (41.9476 - 41.8315) / 7
    v42_jc_gain_per_change = (32.8870 - 32.5967) / 7
    return {
        "version": "D2-V45-v42-vietnam-exact-label-cross-family",
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
        "change_counts": change_counts,
        "changes": changes,
        "evidence": {
            "national_icd_2026": (
                "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/"
                "06-byt-kem.pdf"
            ),
            "national_icd_2026_xlsx_mirror": (
                "https://dongnaicdc.vn/UserFiles/Docs/2026/VBBYT/"
                "Phu%20luc%20Bang%20danh%20muc%20ICD10_FINAL%20.xlsx"
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
            "ministry_stroke_coding_guidance": (
                "https://kcb.vn/thong-tin/huong-dan-ma-hoa-benh-tat-"
                "tu-vong-theo-icd-10.html"
            ),
            "v42_observed_score_gain_per_change": round(
                v42_score_gain_per_change, 7
            ),
            "v42_observed_j_candidates_gain_per_change": round(
                v42_jc_gain_per_change, 7
            ),
            "conditional_projected_j_candidates_if_all_five_match": round(
                32.8870 + 5 * v42_jc_gain_per_change, 4
            ),
            "conditional_projected_score_if_all_five_match": round(
                41.9476 + 5 * v42_score_gain_per_change, 4
            ),
        },
        "excluded_hypotheses": {
            "contextual_translation": (
                "tăng nhãn áp -> G93.2 is held for a separate probe"
            ),
            "multi_candidate": (
                "Bệnh thủy đậu/Zona -> [B01.9, B02.9] is held separately"
            ),
            "recall": (
                "Bệnh amyloidosis tự miễn dịch -> E85.3 changes WER and "
                "is held separately"
            ),
            "boundary": "V43 official-label boundary changes remain held",
        },
        "leaderboard_decision_rule": {
            "wer": "must equal V42 55.4442",
            "j_assertion": "must equal V42 51.4203",
            "promote_if": "J_candidates > 32.8870 and total score > 41.9476",
            "reject_if": "WER or J_assertion changes, because V45 is candidate-only",
        },
        "submission_priority": (
            "highest current priority: five isolated exact-label repairs"
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
