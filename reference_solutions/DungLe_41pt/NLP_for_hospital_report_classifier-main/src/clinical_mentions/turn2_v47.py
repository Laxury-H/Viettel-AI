#!/usr/bin/env python3
"""Build the canonical Vietnamese ICD category-label probe.

V47 is a candidate-only experiment on top of confirmed V45 production.  It
targets diagnosis mentions whose canonical Vietnamese surface equals the
official ICD category label while production currently emits an unspecified
child of that category.

The mapping is intentionally frozen as 27 reviewed surface/code cohorts and
94 occurrences.  Canonicalization only removes presentation variants:

* Unicode, case and repeated-space differences;
* an optional leading ``bệnh``;
* bracketed synonyms such as ``[Migraine]``;
* dash variants and the catalogue's ``và/hoặc`` presentation.

No fuzzy matching, clinical inference, entity, boundary, type or assertion
change is allowed in this version.
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


CANONICAL_CATEGORY_LABELS: dict[str, dict[str, object]] = {
    "béo phì": {"before": "E66.9", "after": "E66", "expected_count": 12},
    "thoái hóa tinh bột": {
        "before": "E85.9",
        "after": "E85",
        "expected_count": 10,
    },
    "suy tim": {"before": "I50.9", "after": "I50", "expected_count": 7},
    "đau nửa đầu": {
        "before": "G43.9",
        "after": "G43",
        "expected_count": 7,
    },
    "xuất huyết dưới nhện": {
        "before": "I60.9",
        "after": "I60",
        "expected_count": 6,
    },
    "loét tá tràng": {
        "before": "K26.9",
        "after": "K26",
        "expected_count": 5,
    },
    "tiền sản giật": {
        "before": "O14.9",
        "after": "O14",
        "expected_count": 5,
    },
    "đái tháo đường típ 2": {
        "before": "E11.9",
        "after": "E11",
        "expected_count": 5,
    },
    "hẹp ống sống": {
        "before": "M48.00",
        "after": "M48.0",
        "expected_count": 4,
    },
    "hội chứng ruột kích thích": {
        "before": "K58.8",
        "after": "K58",
        "expected_count": 3,
    },
    "não úng thủy": {
        "before": "G91.9",
        "after": "G91",
        "expected_count": 3,
    },
    "sỏi mật": {"before": "K80.2", "after": "K80", "expected_count": 3},
    "bại não": {"before": "G80.9", "after": "G80", "expected_count": 2},
    "gan do rượu": {
        "before": "K70.9",
        "after": "K70",
        "expected_count": 2,
    },
    "gút": {"before": "M10.9", "after": "M10", "expected_count": 2},
    "hội chứng thận hư": {
        "before": "N04.9",
        "after": "N04",
        "expected_count": 2,
    },
    "thận mạn tính": {
        "before": "N18.9",
        "after": "N18",
        "expected_count": 2,
    },
    "trào ngược dạ dày thực quản": {
        "before": "K21.9",
        "after": "K21",
        "expected_count": 2,
    },
    "viêm da tiếp xúc dị ứng": {
        "before": "L23.9",
        "after": "L23",
        "expected_count": 2,
    },
    "viêm loét đại tràng": {
        "before": "K51.9",
        "after": "K51",
        "expected_count": 2,
    },
    "viêm xương tủy": {
        "before": "M86.9",
        "after": "M86",
        "expected_count": 2,
    },
    "hội chứng turner": {
        "before": "Q96.9",
        "after": "Q96",
        "expected_count": 1,
    },
    "rối loạn cảm xúc lưỡng cực": {
        "before": "F31.9",
        "after": "F31",
        "expected_count": 1,
    },
    "sâu răng": {"before": "K02.9", "after": "K02", "expected_count": 1},
    "thai ngoài tử cung": {
        "before": "O00.9",
        "after": "O00",
        "expected_count": 1,
    },
    "vảy nến": {"before": "L40.9", "after": "L40", "expected_count": 1},
    "xơ vữa động mạch": {
        "before": "I70.90",
        "after": "I70",
        "expected_count": 1,
    },
}

EXPECTED_CHANGES = 94
EXPECTED_RECORDS = 50
EXPECTED_TEMPLATES = 38


def normalize_label(value: str) -> str:
    """Normalize catalogue presentation without fuzzy semantics."""

    value = unicodedata.normalize("NFC", value).casefold()
    value = value.replace("–", "-").replace("—", "-")
    value = re.sub(r"\s+", " ", value)
    return value.strip(" \t\r\n.;:")


def canonical_label(value: str) -> str:
    """Remove only the reviewed presentation variants."""

    value = normalize_label(value)
    value = re.sub(r"^bệnh\s+", "", value)
    value = re.sub(r"\s*\[[^]]*]\s*", " ", value)
    value = value.replace("và/hoặc", " ")
    value = re.sub(r"[-–—]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def repair_canonical_category_labels(
    control: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Replace reviewed unspecified children with exact category labels."""

    output = copy.deepcopy(control)
    changes: list[dict] = []
    for record_id, entities in output.items():
        for entity in entities:
            if entity["type"] != "CHẨN_ĐOÁN":
                continue
            surface = canonical_label(entity["text"])
            target = CANONICAL_CATEGORY_LABELS.get(surface)
            if target is None:
                continue
            before_code = str(target["before"])
            after_code = str(target["after"])
            if entity.get("candidates") != [before_code]:
                continue
            entity["candidates"] = [after_code]
            changes.append(
                {
                    "record_id": record_id,
                    "text": entity["text"],
                    "canonical_surface": surface,
                    "type": entity["type"],
                    "position": list(entity["position"]),
                    "assertions": list(entity.get("assertions", [])),
                    "before": [before_code],
                    "after": [after_code],
                    "reason": "official_canonical_category_exact_label",
                }
            )
    return output, changes


def expected_cohort_counts() -> dict[str, int]:
    return {
        surface: int(target["expected_count"])
        for surface, target in CANONICAL_CATEGORY_LABELS.items()
    }


def observed_cohort_counts(changes: list[dict]) -> dict[str, int]:
    return {
        surface: sum(
            change["canonical_surface"] == surface for change in changes
        )
        for surface in CANONICAL_CATEGORY_LABELS
    }


def run(input_dir: Path, control_zip: Path, output_zip: Path) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    control = turn2_v19.load_submission(control_zip)
    if set(control) != set(texts):
        raise ValueError("Control record IDs do not match input")

    output, changes = repair_canonical_category_labels(control)
    expected_counts = expected_cohort_counts()
    actual_counts = observed_cohort_counts(changes)
    if len(changes) != EXPECTED_CHANGES or actual_counts != expected_counts:
        raise ValueError(
            f"Expected {EXPECTED_CHANGES} V47 changes with "
            f"{expected_counts}, found {len(changes)} with {actual_counts}"
        )
    changed_records = {change["record_id"] for change in changes}
    if len(changed_records) != EXPECTED_RECORDS:
        raise ValueError(
            f"Expected {EXPECTED_RECORDS} changed records, "
            f"found {len(changed_records)}"
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
        raise AssertionError("V47 must not change entity spans or types")
    for record_id in control:
        for before, after in zip(control[record_id], output[record_id]):
            if before.get("assertions") != after.get("assertions"):
                raise AssertionError("V47 must not change assertions")
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()

    v45_score_rate = (41.9694 - 41.9476) / 5
    v45_jc_rate = (32.9413 - 32.8870) / 5
    v42_score_rate = (41.9476 - 41.8315) / 7
    code_system_score_rate = ((1.4827 / 149) + (0.7769 / 78)) / 2
    projected_j_candidates = 32.9413 + len(changes) * v45_jc_rate

    return {
        "version": "D2-V47-v45-vietnam-icd-canonical-category-label",
        "control": str(control_zip.resolve()),
        "confirmed_control_score": 41.9694,
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entity_changes": 0,
        "span_changes": 0,
        "type_changes": 0,
        "assertion_changes": 0,
        "candidate_changes": len(changes),
        "record_count": len(changed_records),
        "template_count_from_audit": EXPECTED_TEMPLATES,
        "cohort_count": len(CANONICAL_CATEGORY_LABELS),
        "record_ids": sorted(changed_records, key=int),
        "cohort_counts": actual_counts,
        "changes": changes,
        "evidence": {
            "national_icd_2026": (
                "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/"
                "06-byt-kem.pdf"
            ),
            "official_problem_page": (
                "https://competition.viettel.vn/contests/medical-2026"
            ),
            "selection_rule": (
                "surface equals official category label after "
                "presentation-only canonicalization"
            ),
            "v36_specific_child_calibration": {
                "candidate_changes": 25,
                "j_candidates_delta": -0.0932,
                "score_delta": -0.0373,
            },
            "mechanical_projection": {
                "v45_residual_score_gain": round(
                    len(changes) * v45_score_rate, 4
                ),
                "v42_exact_label_score_gain": round(
                    len(changes) * v42_score_rate, 4
                ),
                "v34_v35_code_system_mean_score_gain": round(
                    len(changes) * code_system_score_rate, 4
                ),
                "v45_residual_projected_j_candidates": round(
                    projected_j_candidates, 4
                ),
                "v45_residual_projected_score_from_metric_formula": round(
                    0.3 * (100 - 55.4442)
                    + 0.3 * 51.4203
                    + 0.4 * projected_j_candidates,
                    4,
                ),
            },
        },
        "excluded_hypotheses": {
            "v46": "do not mix contextual H40.9 -> G93.2 changes",
            "augmentation": "do not add parent as a second code",
            "fuzzy_labels": "no semantic or edit-distance label matching",
            "boundaries_assertions_recall": "all remain identical to V45",
        },
        "leaderboard_decision_rule": {
            "wer": "must equal V45 55.4442",
            "j_assertion": "must equal V45 51.4203",
            "promote_if": (
                "total score > 42.3194 (minimum requested +0.35)"
            ),
            "rollback": (
                "submission/candidate_v45_v42-vietnam-exact-label-"
                "cross-family.zip"
            ),
        },
        "risk": (
            "high-upside causal probe: exact official category labels, but "
            "leaderboard category-versus-unspecified-child direction is "
            "not yet directly calibrated"
        ),
        "decision": "candidate_ready_for_controlled_submission",
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
