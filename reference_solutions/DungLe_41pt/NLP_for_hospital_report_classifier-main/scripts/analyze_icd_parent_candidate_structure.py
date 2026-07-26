#!/usr/bin/env python3
"""Audit whether generic Vietnamese ICD mentions should use category codes.

The production linker almost always emits one code.  The official problem
description, however, asks for a list of suitable identifiers and its GERD
example is rendered with two K21-family values.  This script measures the
corresponding hierarchy hypothesis without changing the submission:

* diagnosis mentions whose surface is exactly an official category label but
  whose current candidate is an unspecified child;
* the size of a broad child-plus-parent augmentation;
* projections for replacement versus two-code augmentation;
* the negative V36 calibration for blindly changing hierarchy depth.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.analyze_semantic_context_cohorts import local_context
from scripts.analyze_semantic_context_cohorts import template_roots
from scripts.audit_vietnam_icd_labels import code_stem
from scripts.audit_vietnam_icd_labels import normalize
from scripts.audit_vietnam_icd_labels import parse_workbook
from src.clinical_mentions import turn2_v19


DIAGNOSIS_TYPE = "CHẨN_ĐOÁN"


def category(code: str) -> str | None:
    """Return the ICD category above a dotted code."""

    if "." not in code:
        return None
    return code.split(".", 1)[0]


def canonical_label(value: str) -> str:
    """Normalize presentation-only variants in Vietnamese ICD labels."""

    value = normalize(value)
    value = re.sub(r"^bệnh\s+", "", value)
    value = re.sub(r"\s*\[[^]]*]\s*", " ", value)
    value = value.replace("và/hoặc", " ")
    value = re.sub(r"[-–—]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def score_projections(occurrences: int) -> dict[str, dict[str, float]]:
    """Project full replacement and half-credit two-code augmentation."""

    score_rates = {
        "v34_v35_code_system_mean": (
            (1.4827 / 149) + (0.7769 / 78)
        )
        / 2,
        "v42_exact_label_optimistic": 0.1161 / 7,
        "v45_exact_label_residual": 0.0218 / 5,
    }
    return {
        name: {
            "replacement": round(occurrences * rate, 4),
            "two_code_augmentation_max_half_credit": round(
                occurrences * rate / 2,
                4,
            ),
        }
        for name, rate in score_rates.items()
    }


def audit(input_dir: Path, submission_zip: Path, workbook: Path) -> dict:
    texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in input_dir.glob("*.txt")
    }
    records = turn2_v19.load_submission(submission_zip)
    if set(texts) != set(records):
        raise ValueError("Submission record IDs do not match input")
    roots = template_roots(texts)

    rows = parse_workbook(workbook)
    labels = {
        row["R"]: normalize(row.get("V", ""))
        for row in rows
        if row.get("R")
    }
    official_codes = set(labels)
    codes_by_label: dict[str, list[str]] = {}
    codes_by_canonical_label: dict[str, list[str]] = {}
    for code, label in labels.items():
        if label:
            codes_by_label.setdefault(label, []).append(code)
            codes_by_canonical_label.setdefault(
                canonical_label(label),
                [],
            ).append(code)

    cardinalities: Counter[int] = Counter()
    parent_eligible = 0
    exact_parent_items: list[dict] = []
    canonical_parent_items: list[dict] = []
    explicit_compounds: list[dict] = []

    for record_id in sorted(records, key=int):
        text = texts[record_id]
        for entity in records[record_id]:
            if entity["type"] != DIAGNOSIS_TYPE:
                continue
            candidates = list(entity.get("candidates", []))
            cardinalities[len(candidates)] += 1

            for code in candidates:
                parent = category(code)
                if parent in official_codes:
                    parent_eligible += 1

            if len(candidates) == 1:
                current = candidates[0]
                surface = normalize(entity["text"])
                canonical_surface = canonical_label(entity["text"])
                canonical_ancestors = [
                    code
                    for code in codes_by_canonical_label.get(
                        canonical_surface,
                        [],
                    )
                    if code != current
                    and code_stem(current).startswith(code_stem(code))
                ]
                canonical_parent = max(
                    canonical_ancestors,
                    key=lambda code: len(code_stem(code)),
                    default=None,
                )
                start, end = entity["position"]
                if canonical_parent is not None:
                    canonical_parent_items.append(
                        {
                            "record_id": record_id,
                            "template_id": roots[record_id],
                            "text": entity["text"],
                            "position": list(entity["position"]),
                            "current": current,
                            "exact_category": canonical_parent,
                            "context": local_context(text, start, end),
                        }
                    )

                ancestors = [
                    code
                    for code in codes_by_label.get(surface, [])
                    if code != current
                    and code_stem(current).startswith(code_stem(code))
                ]
                parent = max(
                    ancestors,
                    key=lambda code: len(code_stem(code)),
                    default=None,
                )
                if (
                    parent is not None
                    and labels.get(parent) == surface
                ):
                    exact_parent_items.append(
                        {
                            "record_id": record_id,
                            "template_id": roots[record_id],
                            "text": entity["text"],
                            "position": list(entity["position"]),
                            "current": current,
                            "exact_category": parent,
                            "context": local_context(text, start, end),
                        }
                    )

            normalized_surface = normalize(entity["text"])
            if "/" in normalized_surface or (
                "," in normalized_surface
                and "viêm gan b, c" in normalized_surface
            ):
                explicit_compounds.append(
                    {
                        "record_id": record_id,
                        "template_id": roots[record_id],
                        "text": entity["text"],
                        "candidates": candidates,
                    }
                )

    def summarize_parent_items(items: list[dict]) -> dict:
        cohorts: dict[tuple[str, str, str], list[dict]] = {}
        for item in items:
            key = (
                canonical_label(item["text"]),
                item["current"],
                item["exact_category"],
            )
            cohorts.setdefault(key, []).append(item)
        cohort_summary = []
        for (surface, current, parent), entries in sorted(
            cohorts.items(),
            key=lambda pair: (-len(pair[1]), pair[0][0]),
        ):
            cohort_summary.append(
                {
                    "surface": surface,
                    "current": current,
                    "exact_category": parent,
                    "occurrences": len(entries),
                    "record_count": len(
                        {item["record_id"] for item in entries}
                    ),
                    "template_count": len(
                        {item["template_id"] for item in entries}
                    ),
                    "record_ids": sorted(
                        {item["record_id"] for item in entries},
                        key=int,
                    ),
                }
            )
        return {
            "occurrences": len(items),
            "record_count": len({item["record_id"] for item in items}),
            "template_count": len(
                {item["template_id"] for item in items}
            ),
            "cohort_count": len(cohort_summary),
            "cohorts": cohort_summary,
            "score_projections": score_projections(len(items)),
        }

    occurrences = len(exact_parent_items)
    canonical_occurrences = len(canonical_parent_items)
    return {
        "input": str(input_dir.resolve()),
        "submission": str(submission_zip.resolve()),
        "workbook": str(workbook.resolve()),
        "diagnosis_candidate_cardinalities": {
            str(key): value for key, value in sorted(cardinalities.items())
        },
        "child_codes_with_official_parent_occurrences": parent_eligible,
        "exact_parent_label": summarize_parent_items(exact_parent_items),
        "canonical_exact_parent_label": summarize_parent_items(
            canonical_parent_items
        ),
        "explicit_compound_mentions": {
            "occurrences": len(explicit_compounds),
            "items": explicit_compounds,
        },
        "score_projections": score_projections(occurrences),
        "v36_hierarchy_calibration": {
            "changed_occurrences": 25,
            "replacement_j_candidates_delta": -0.0932,
            "replacement_score_delta": -0.03728,
            "same_batch_two_code_delta_if_singleton_gold": -0.01864,
        },
        "submission_threshold": 0.35,
        "decision": (
            "research_hold: the canonical exact replacement crosses +0.35 "
            "even at the V45 residual rate, but category-versus-unspecified "
            "direction still lacks a causal leaderboard calibration"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.input, args.submission, args.workbook)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")


if __name__ == "__main__":
    main()
