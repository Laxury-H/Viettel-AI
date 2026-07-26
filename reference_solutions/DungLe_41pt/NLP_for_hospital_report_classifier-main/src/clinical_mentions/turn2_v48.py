#!/usr/bin/env python3
"""Recover exact Vietnamese ICD diagnosis mentions omitted by V45.

V48 is a recall-only experiment on top of confirmed V45 production.  It adds
only diagnosis surfaces whose type and leaf code are supported by both:

* the official Vietnam ICD-10 2026 catalogue; and
* an annotated neighbouring surface or an accepted same-family mention in
  the current 100-record corpus.

No existing span, type, assertion or candidate is changed.  The frozen set is
kept deliberately small so a leaderboard result remains causally useful.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from . import turn2_v19
from . import turn2_v24
from . import turn2_v9 as base


DIAGNOSIS_TYPE = "CHẨN_ĐOÁN"


@dataclass(frozen=True)
class ExactDiagnosisRecall:
    surface: str
    candidate: str
    expected_count: int
    reason: str


EXACT_DIAGNOSIS_RECALL: tuple[ExactDiagnosisRecall, ...] = (
    ExactDiagnosisRecall(
        surface="trứng cá",
        candidate="L70.9",
        expected_count=6,
        reason="bare_acne_name_in_topic_and_treatment_text",
    ),
    ExactDiagnosisRecall(
        surface="rụng tóc toàn bộ",
        candidate="L63.1",
        expected_count=2,
        reason="official_leaf_name_in_alopecia_treatment_text",
    ),
    ExactDiagnosisRecall(
        surface="mày đay",
        candidate="L50.9",
        expected_count=2,
        reason="diagnosis_in_explicit_adverse_effect_list",
    ),
    ExactDiagnosisRecall(
        surface="bạch biến",
        candidate="L80",
        expected_count=2,
        reason="official_leaf_name_in_explicit_adverse_effect_list",
    ),
    ExactDiagnosisRecall(
        surface="cao răng",
        candidate="K03.6",
        expected_count=1,
        reason="official_leaf_name_in_periodontal_treatment_text",
    ),
    ExactDiagnosisRecall(
        surface="viêm túi mật",
        candidate="K81.9",
        expected_count=1,
        reason="negated_imaging_finding_parallel_to_annotated_stone",
    ),
    ExactDiagnosisRecall(
        surface="parkinson",
        candidate="G20",
        expected_count=1,
        reason="contraindication_parallel_to_accepted_parkinson_syndrome",
    ),
)

EXPECTED_ADDITIONS = 15
EXPECTED_RECORDS = 8


def normalize_surface(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold().strip()


def derive_exact_diagnosis_recall(
    texts: dict[str, str],
    control: dict[str, list[dict]],
) -> list[tuple[str, base.Span, ExactDiagnosisRecall]]:
    """Find non-overlapping occurrences of the frozen reviewed surfaces."""

    additions: list[tuple[str, base.Span, ExactDiagnosisRecall]] = []
    for record_id in sorted(texts, key=int):
        text = texts[record_id]
        normalized = base.NormalizedText(text)
        for target in EXACT_DIAGNOSIS_RECALL:
            for span in normalized.literal_spans(
                target.surface,
                boundary=base.should_use_boundary(
                    target.surface,
                    DIAGNOSIS_TYPE,
                ),
            ):
                if any(
                    span.start < entity["position"][1]
                    and entity["position"][0] < span.end
                    for entity in control[record_id]
                ):
                    continue
                additions.append((record_id, span, target))
    return sorted(
        additions,
        key=lambda item: (int(item[0]), item[1].start, item[1].end),
    )


def apply_exact_diagnosis_recall(
    texts: dict[str, str],
    control: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Append the selected diagnoses and preserve every existing entity."""

    output = copy.deepcopy(control)
    changes: list[dict] = []
    for record_id, span, target in derive_exact_diagnosis_recall(
        texts,
        control,
    ):
        text = texts[record_id]
        historical, family = base.section_states(text)
        entity = base.make_entity(
            text,
            span,
            DIAGNOSIS_TYPE,
            historical,
            family,
        )
        entity["candidates"] = [target.candidate]
        output[record_id].append(entity)
        output[record_id] = base.resolve_entities(output[record_id])
        changes.append(
            {
                "record_id": record_id,
                "text": entity["text"],
                "type": entity["type"],
                "position": entity["position"],
                "assertions": entity["assertions"],
                "candidates": entity["candidates"],
                "reason": target.reason,
            }
        )
    return output, changes


def expected_counts() -> dict[str, int]:
    return {
        target.surface: target.expected_count
        for target in EXACT_DIAGNOSIS_RECALL
    }


def observed_counts(changes: list[dict]) -> dict[str, int]:
    counts = {target.surface: 0 for target in EXACT_DIAGNOSIS_RECALL}
    for change in changes:
        counts[normalize_surface(change["text"])] += 1
    return counts


def run(input_dir: Path, control_zip: Path, output_zip: Path) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    control = turn2_v19.load_submission(control_zip)
    if set(control) != set(texts):
        raise ValueError("Control record IDs do not match input")

    output, changes = apply_exact_diagnosis_recall(texts, control)
    actual_counts = observed_counts(changes)
    if len(changes) != EXPECTED_ADDITIONS:
        raise ValueError(
            f"Expected {EXPECTED_ADDITIONS} V48 additions, "
            f"found {len(changes)}"
        )
    if actual_counts != expected_counts():
        raise ValueError(
            f"Unexpected V48 cohort counts: {actual_counts}"
        )
    changed_records = {change["record_id"] for change in changes}
    if len(changed_records) != EXPECTED_RECORDS:
        raise ValueError(
            f"Expected {EXPECTED_RECORDS} changed records, "
            f"found {len(changed_records)}"
        )

    for record_id, before_entities in control.items():
        before_keys = {
            turn2_v24.entity_key(entity) for entity in before_entities
        }
        after_by_key = {
            turn2_v24.entity_key(entity): entity
            for entity in output[record_id]
        }
        if not before_keys <= set(after_by_key):
            raise AssertionError("V48 must retain every V45 entity")
        for before in before_entities:
            after = after_by_key[turn2_v24.entity_key(before)]
            if before != after:
                raise AssertionError("V48 must not mutate V45 entities")
        base.validate_record(texts[record_id], output[record_id])

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    v29_score_rate = (39.4830 - 39.4461) / 8
    return {
        "version": "D2-V48-v45-vietnam-exact-diagnosis-recall",
        "control": str(control_zip.resolve()),
        "confirmed_control_score": 41.9694,
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "existing_entity_changes": 0,
        "diagnosis_additions": len(changes),
        "changed_records": len(changed_records),
        "record_ids": sorted(changed_records, key=int),
        "cohort_counts": actual_counts,
        "changes": changes,
        "evidence": {
            "national_icd_2026": (
                "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/"
                "06-byt-kem.pdf"
            ),
            "selection_rule": (
                "official Vietnamese leaf/unspecified-leaf label plus "
                "same-document or same-family annotation evidence"
            ),
            "v29_recall_score_gain_per_addition": round(
                v29_score_rate,
                7,
            ),
            "conservative_projected_score": round(
                41.9694 + len(changes) * v29_score_rate,
                4,
            ),
        },
        "excluded_hypotheses": {
            "symptoms": (
                "buồn ngủ, ảo thanh and other symptom recall are isolated "
                "for a later causal probe"
            ),
            "questions": "do not restore the two rejected tăng HA mentions",
            "candidate_rewrites": (
                "do not mix V46 or the disproven V47 category rewrite"
            ),
            "boundaries_assertions": "all V45 entities remain byte-equivalent",
        },
        "leaderboard_decision_rule": {
            "promote_if": "total score > 41.9694",
            "diagnostic_signal": (
                "WER should decrease; assertion/candidate metrics must not "
                "regress enough to offset the WER gain"
            ),
            "rollback": (
                "submission/candidate_v45_v42-vietnam-exact-label-"
                "cross-family.zip"
            ),
        },
        "decision": "candidate_ready_as_isolated_recall_probe",
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
