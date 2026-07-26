#!/usr/bin/env python3
"""Build a candidate-only Vietnamese source-semantic batch on V45.

V48 showed that adding diagnosis mentions from educational text is
false-positive-dominant.  V49 therefore changes no entity, boundary, type, or
assertion.  It only repairs two candidate mappings on diagnosis entities that
already exist in V45:

* ``tai biến mạch máu não`` is an unspecified cerebrovascular event (I64),
  not necessarily an unspecified cerebral infarction (I63.9);
* the source phrase translated as ``Bệnh amyloidosis tự miễn dịch`` denotes
  autoimmune/AA secondary systemic amyloidosis (E85.3), not unspecified
  amyloidosis (E85.9).
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


DIAGNOSIS_TYPE = "CHẨN_ĐOÁN"
EXPECTED_COUNTS = {
    "unspecified_cerebrovascular_event": 2,
    "aa_secondary_systemic_amyloidosis": 3,
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFC", value).casefold()
    return re.sub(r"\s+", " ", value).strip()


def has_aa_amyloidosis_suffix(value: str) -> bool:
    """Return whether text immediately after the span carries the AA cue."""

    return bool(
        re.match(
            r"^[\s,;:()/-]*tự\s+miễn\s+dịch\b",
            normalize(value),
        )
    )


def repair_source_semantic_candidates(
    texts: dict[str, str],
    control: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Apply the two reviewed cross-family candidate corrections."""

    output = copy.deepcopy(control)
    changes: list[dict] = []
    for record_id, entities in output.items():
        source = texts[record_id]
        for entity in entities:
            if entity["type"] != DIAGNOSIS_TYPE:
                continue

            surface = normalize(entity["text"])
            before = list(entity.get("candidates", []))
            cohort: str | None = None
            after: list[str] | None = None
            reason: str | None = None

            if surface == "tai biến mạch máu não" and before == ["I63.9"]:
                cohort = "unspecified_cerebrovascular_event"
                after = ["I64"]
                reason = "exact_vietnamese_unspecified_stroke_synonym"
            elif surface == "bệnh amyloidosis" and before == ["E85.9"]:
                _, end = entity["position"]
                suffix = source[end : min(len(source), end + 48)]
                if has_aa_amyloidosis_suffix(suffix):
                    cohort = "aa_secondary_systemic_amyloidosis"
                    after = ["E85.3"]
                    reason = "source_aa_qualifier_outside_existing_span"

            if after is None or cohort is None or reason is None:
                continue
            entity["candidates"] = after
            changes.append(
                {
                    "record_id": record_id,
                    "text": entity["text"],
                    "type": entity["type"],
                    "position": list(entity["position"]),
                    "assertions": list(entity.get("assertions", [])),
                    "before": before,
                    "after": after,
                    "cohort": cohort,
                    "reason": reason,
                }
            )
    return output, changes


def observed_counts(changes: list[dict]) -> dict[str, int]:
    return {
        cohort: sum(change["cohort"] == cohort for change in changes)
        for cohort in EXPECTED_COUNTS
    }


def run(input_dir: Path, control_zip: Path, output_zip: Path) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    control = turn2_v19.load_submission(control_zip)
    if set(control) != set(texts):
        raise ValueError("Control record IDs do not match input")

    output, changes = repair_source_semantic_candidates(texts, control)
    counts = observed_counts(changes)
    if counts != EXPECTED_COUNTS:
        raise ValueError(
            f"Expected V49 cohort counts {EXPECTED_COUNTS}, found {counts}"
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
        raise AssertionError("V49 must not change entity spans or types")
    for record_id in control:
        for before, after in zip(control[record_id], output[record_id]):
            if before.get("assertions") != after.get("assertions"):
                raise AssertionError("V49 must not change assertions")
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    v42_score_rate = (41.9476 - 41.8315) / 7
    v45_score_rate = (41.9694 - 41.9476) / 5
    v45_jc_rate = (32.9413 - 32.8870) / 5
    return {
        "version": "D2-V49-v45-vietnam-source-semantic-cross-family",
        "control": str(control_zip.resolve()),
        "confirmed_control_score": 41.9694,
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
        "cohort_counts": counts,
        "changes": changes,
        "evidence": {
            "national_icd_2026": (
                "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/"
                "06-byt-kem.pdf"
            ),
            "vietnam_hospital_e85_3_catalogue": (
                "https://phusannhidanang.org.vn/TraCuuXetNghiem/"
                "lstICD/GetICD?page=229"
            ),
            "vietnam_icd_i64_guidance": (
                "https://syt.quangbinh.gov.vn/3cms/upload/soyte/File/"
                "BIEU%20MAU/1754-syt-nvy/ICD%2010-%20Tap%202.pdf"
            ),
            "source_aa_wording": (
                "https://www.healthline.com/health/amyloidosis"
            ),
            "v45_residual_projected_j_candidates": round(
                32.9413 + len(changes) * v45_jc_rate, 4
            ),
            "v45_residual_projected_score": round(
                41.9694 + len(changes) * v45_score_rate, 4
            ),
            "v42_optimistic_projected_score": round(
                41.9694 + len(changes) * v42_score_rate, 4
            ),
        },
        "leaderboard_decision_rule": {
            "wer": "must equal V45 55.4442",
            "j_assertion": "must equal V45 51.4203",
            "promote_if": "J_candidates > 32.9413 and total score > 41.9694",
            "rollback": (
                "submission/candidate_v45_v42-vietnam-exact-label-"
                "cross-family.zip"
            ),
        },
        "submission_policy": (
            "validated artifact; HOLD because projected gain is below +0.35"
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
