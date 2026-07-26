#!/usr/bin/env python3
"""Audit lexical ICD corrections against the discourse around each mention.

Leaderboard evidence supports Vietnamese ICD normalization, but V36 also
showed that a generic mention must not automatically inherit a more specific
code from nearby context.  The reverse error is possible too: a short surface
such as ``đái tháo đường`` can occur in a chart whose source concept implicitly
means type 2, in generic educational prose, or in a machine-translation seam.

This audit keeps those roles separate.  It also inventories literal adjacent
duplicate entities, which are useful evidence of translation corruption but
are not automatically safe to delete.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.analyze_semantic_context_cohorts import local_context
from scripts.analyze_semantic_context_cohorts import template_roots
from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v9 as base


DIAGNOSIS_TYPE = "CHẨN_ĐOÁN"


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFC", value).casefold()
    return re.sub(r"\s+", " ", value).strip()


def classify_generic_diabetes(
    text: str,
    entity: dict,
) -> str:
    """Separate implicit chart type, generic education, and translation."""

    surface = normalize(entity["text"])
    start, end = entity["position"]
    before = normalize(text[max(0, start - 220) : start])
    around = normalize(text[max(0, start - 220) : min(len(text), end + 220)])
    if re.search(r"(?:tổng phân tích|xét nghiệm)\s+nước tiểu", before):
        return "urinalysis_translation_seam"
    if surface == "tiểu đường":
        return "generic_education"
    if (
        "yếu tố nguy cơ" in around
        and re.search(r"\bcó thể thay đổi\b", around)
    ):
        return "generic_education"
    return "clinical_chart_implicit_type"


def item(
    record_id: str,
    template_id: str,
    text: str,
    entity: dict,
    *,
    current: list[str],
    proposed: list[str],
    mechanism: str,
) -> dict:
    start, end = entity["position"]
    return {
        "record_id": record_id,
        "template_id": template_id,
        "text": entity["text"],
        "position": list(entity["position"]),
        "assertions": list(entity["assertions"]),
        "current": current,
        "proposed": proposed,
        "mechanism": mechanism,
        "context": local_context(text, start, end),
    }


def summarize(items: list[dict]) -> dict:
    return {
        "occurrences": len(items),
        "record_count": len({entry["record_id"] for entry in items}),
        "template_count": len({entry["template_id"] for entry in items}),
        "record_ids": sorted(
            {entry["record_id"] for entry in items},
            key=int,
        ),
        "template_ids": sorted(
            {entry["template_id"] for entry in items},
            key=int,
        ),
        "items": items,
    }


def audit(input_dir: Path, submission_zip: Path) -> dict:
    texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted(input_dir.glob("*.txt"), key=base.natural_key)
    }
    submission = turn2_v19.load_submission(submission_zip)
    if set(texts) != set(submission):
        raise ValueError("Submission record IDs do not match input")
    roots = template_roots(texts)

    diabetes: dict[str, list[dict]] = {
        "clinical_chart_implicit_type": [],
        "generic_education": [],
        "urinalysis_translation_seam": [],
    }
    osteoporosis: list[dict] = []
    cerebrovascular: list[dict] = []
    duplicate_pairs: list[dict] = []

    for record_id in sorted(texts, key=int):
        text = texts[record_id]
        entities = sorted(
            submission[record_id],
            key=lambda entity: (
                entity["position"][0],
                entity["position"][1],
                entity["type"],
            ),
        )
        for entity in entities:
            if entity["type"] != DIAGNOSIS_TYPE:
                continue
            surface = normalize(entity["text"])
            candidates = list(entity.get("candidates", []))
            if (
                surface in {"đái tháo đường", "tiểu đường"}
                and candidates == ["E11.9"]
            ):
                role = classify_generic_diabetes(text, entity)
                diabetes[role].append(
                    item(
                        record_id,
                        roots[record_id],
                        text,
                        entity,
                        current=candidates,
                        proposed=["E14.9"],
                        mechanism=role,
                    )
                )
            if surface == "loãng xương" and candidates == ["M81.0"]:
                osteoporosis.append(
                    item(
                        record_id,
                        roots[record_id],
                        text,
                        entity,
                        current=candidates,
                        proposed=["M81.9"],
                        mechanism="generic_label_not_postmenopausal",
                    )
                )
            if (
                surface == "tai biến mạch máu não"
                and candidates == ["I63.9"]
            ):
                cerebrovascular.append(
                    item(
                        record_id,
                        roots[record_id],
                        text,
                        entity,
                        current=candidates,
                        proposed=["I64"],
                        mechanism="unspecified_event_not_infarction",
                    )
                )

        for left, right in zip(entities, entities[1:]):
            if (
                left["type"] != right["type"]
                or normalize(left["text"]) != normalize(right["text"])
            ):
                continue
            gap = text[left["position"][1] : right["position"][0]]
            if gap not in {"", " "}:
                continue
            start = left["position"][0]
            end = right["position"][1]
            duplicate_pairs.append(
                {
                    "record_id": record_id,
                    "template_id": roots[record_id],
                    "type": left["type"],
                    "text": left["text"],
                    "gap": gap,
                    "left_position": list(left["position"]),
                    "right_position": list(right["position"]),
                    "left_candidates": list(left.get("candidates", [])),
                    "right_candidates": list(right.get("candidates", [])),
                    "context": local_context(text, start, end),
                }
            )

    reviewed_candidate_only = [
        *diabetes["generic_education"],
        *osteoporosis,
        *cerebrovascular,
    ]
    v42_score_gain_per_change = (41.9476 - 41.8315) / 7
    v45_score_gain_per_change = (41.9694 - 41.9476) / 5
    candidate_count = len(reviewed_candidate_only)
    duplicate_types = Counter(
        entry["type"] for entry in duplicate_pairs
    )
    return {
        "input": str(input_dir.resolve()),
        "submission": str(submission_zip.resolve()),
        "records": len(texts),
        "document_templates": len(set(roots.values())),
        "generic_diabetes": {
            role: summarize(entries) for role, entries in diabetes.items()
        },
        "generic_osteoporosis": summarize(osteoporosis),
        "unspecified_cerebrovascular_event": summarize(cerebrovascular),
        "literal_adjacent_duplicate_pairs": {
            **summarize(duplicate_pairs),
            "type_counts": dict(sorted(duplicate_types.items())),
        },
        "reviewed_candidate_only_occurrences": candidate_count,
        "reviewed_candidate_only_record_count": len(
            {entry["record_id"] for entry in reviewed_candidate_only}
        ),
        "reviewed_candidate_only_template_count": len(
            {entry["template_id"] for entry in reviewed_candidate_only}
        ),
        "score_projection": {
            "v42_optimistic_marginal": round(
                candidate_count * v42_score_gain_per_change,
                4,
            ),
            "v45_residual_marginal": round(
                candidate_count * v45_score_gain_per_change,
                4,
            ),
            "submission_threshold": 0.35,
        },
        "decision": (
            "hold: discourse-reviewed batch remains below +0.35 even at "
            "the optimistic V42 marginal"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.input, args.submission)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")


if __name__ == "__main__":
    main()
