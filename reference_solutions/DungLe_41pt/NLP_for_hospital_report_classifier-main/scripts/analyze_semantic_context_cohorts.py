#!/usr/bin/env python3
"""Audit repeated semantic-context cohorts in a Turn-2 submission.

The candidate metric rewards correct code selection, but repeated surfaces can
hide several different mechanisms: a translated clinical term, a qualifier
outside the entity boundary, a composite label, or a genuinely omitted
entity.  This script keeps those mechanisms separate and reports both raw
occurrences and independent near-duplicate document templates.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from src.clinical_mentions import turn2_v19
from src.clinical_mentions import turn2_v9 as base


DIAGNOSIS_TYPE = "CHẨN_ĐOÁN"


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFC", value).casefold()
    return re.sub(r"\s+", " ", value).strip()


def document_ngrams(value: str, size: int = 5) -> set[str]:
    compact = normalize(value)
    if len(compact) < size:
        return {compact} if compact else set()
    return {
        compact[index : index + size]
        for index in range(len(compact) - size + 1)
    }


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def template_roots(
    texts: dict[str, str],
    *,
    threshold: float = 0.45,
) -> dict[str, str]:
    """Return the canonical record ID of each near-duplicate component."""

    record_ids = sorted(texts, key=int)
    parents = {record_id: record_id for record_id in record_ids}
    ngrams = {
        record_id: document_ngrams(texts[record_id])
        for record_id in record_ids
    }

    def find(record_id: str) -> str:
        root = record_id
        while parents[root] != root:
            root = parents[root]
        while parents[record_id] != record_id:
            parent = parents[record_id]
            parents[record_id] = root
            record_id = parent
        return root

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        canonical = min((left_root, right_root), key=int)
        other = right_root if canonical == left_root else left_root
        parents[other] = canonical

    for index, left in enumerate(record_ids):
        for right in record_ids[index + 1 :]:
            if jaccard(ngrams[left], ngrams[right]) >= threshold:
                union(left, right)
    return {record_id: find(record_id) for record_id in record_ids}


def local_context(
    text: str,
    start: int,
    end: int,
    *,
    left: int = 160,
    right: int = 180,
) -> str:
    return " ".join(
        text[max(0, start - left) : min(len(text), end + right)].split()
    )


def audit(input_dir: Path, submission_zip: Path) -> dict:
    texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted(input_dir.glob("*.txt"), key=base.natural_key)
    }
    submission = turn2_v19.load_submission(submission_zip)
    if set(texts) != set(submission):
        raise ValueError("Submission record IDs do not match input")

    roots = template_roots(texts)
    findings: dict[str, list[dict]] = defaultdict(list)

    for record_id in sorted(texts, key=int):
        text = texts[record_id]
        for entity in submission[record_id]:
            if entity["type"] != DIAGNOSIS_TYPE:
                continue
            surface = normalize(entity["text"])
            start, end = entity["position"]
            before = normalize(text[max(0, start - 180) : start])
            after = normalize(text[end : min(len(text), end + 180)])
            around = normalize(text[max(0, start - 180) : min(len(text), end + 180)])
            base_item = {
                "record_id": record_id,
                "template_id": roots[record_id],
                "text": entity["text"],
                "position": entity["position"],
                "current": entity.get("candidates", []),
                "assertions": entity["assertions"],
                "context": local_context(text, start, end),
            }

            if surface == "tăng nhãn áp" and re.search(
                r"(?:sọ|nội sọ|não úng|dẫn lưu|shunt|cắt lớp vi tính|"
                r"thời kỳ sơ sinh|sơ sinh)",
                around,
            ):
                findings["intracranial_pressure_translation"].append(
                    {
                        **base_item,
                        "proposed": ["G93.2"],
                        "mechanism": "candidate_only_cross_family",
                    }
                )

            if (
                surface == "tai biến mạch máu não"
                and entity.get("candidates") == ["I63.9"]
            ):
                findings["unspecified_cerebrovascular_event"].append(
                    {
                        **base_item,
                        "proposed": ["I64"],
                        "mechanism": "candidate_only_exact_vietnam_synonym",
                    }
                )

            if (
                surface == "bệnh amyloidosis"
                and re.match(
                    r"^[\s,;:()/-]*tự miễn dịch\b",
                    after,
                )
            ):
                findings["aa_amyloidosis_context_qualifier"].append(
                    {
                        **base_item,
                        "proposed": ["E85.3"],
                        "mechanism": "candidate_only_context_qualifier",
                        "boundary_uncertainty": True,
                    }
                )

            if surface in {"đái tháo đường", "tiểu đường"}:
                if re.search(
                    r"(?:tổng phân tích|xét nghiệm)\s+nước tiểu",
                    before,
                ):
                    findings["urinalysis_glucose_translation"].append(
                        {
                            **base_item,
                            "proposed": ["R81"],
                            "mechanism": "candidate_or_type_translation",
                        }
                    )
                if re.match(
                    r"^[\s,;:()-]*(?:có\s+)?biến chứng\s+"
                    r"(?:bệnh lý\s+)?thần kinh",
                    after,
                ):
                    findings["diabetes_neurologic_complication"].append(
                        {
                            **base_item,
                            "proposed": ["E11.4"],
                            "mechanism": "qualifier_outside_boundary",
                        }
                    )
                if re.search(
                    r"(?:bệnh|suy)\s+thận\s+mạn[^.;\n]{0,80}\bdo\s*$",
                    before,
                ):
                    findings["diabetes_renal_complication"].append(
                        {
                            **base_item,
                            "proposed": ["E11.2"],
                            "mechanism": "qualifier_outside_boundary",
                        }
                    )

            if surface in {"bệnh thận mạn", "bệnh thận mạn tính"} and re.match(
                r"^[\s,;:()-]*(?:không đặc hiệu\s+)?giai đoạn\s+4\b",
                after,
            ):
                findings["ckd_stage_4_outside_boundary"].append(
                    {
                        **base_item,
                        "proposed": ["N18.4"],
                        "mechanism": "qualifier_outside_boundary",
                    }
                )

            if surface in {
                "viêm tủy xương",
                "viêm xương tủy",
                "bệnh viêm tuỷ xương",
            } and (
                re.match(r"^[\s,;:()-]*(?:mạn|mãn)\s+tính\b", after)
                or re.search(
                    r"(?:viêm tủy xương|viêm xương tủy)\s+"
                    r"(?:mạn|mãn)\s+tính",
                    around,
                )
            ):
                findings["chronic_osteomyelitis_outside_boundary"].append(
                    {
                        **base_item,
                        "proposed": ["M86.6"],
                        "mechanism": "qualifier_and_site_underspecified",
                    }
                )

            if (
                surface == "rối loạn cảm xúc lưỡng cực"
                and re.match(r"^[\s,;:()-]*khác\b", after)
            ):
                findings["bipolar_other_outside_boundary"].append(
                    {
                        **base_item,
                        "proposed": ["F31.8"],
                        "mechanism": "qualifier_outside_boundary",
                    }
                )

            if surface == "bệnh thủy đậu/zona":
                findings["varicella_zoster_composite"].append(
                    {
                        **base_item,
                        "proposed": ["B01.9", "B02.9"],
                        "mechanism": "multi_candidate_composite",
                    }
                )

    cohorts = []
    for name, items in findings.items():
        cohorts.append(
            {
                "name": name,
                "mechanism": sorted({item["mechanism"] for item in items}),
                "occurrences": len(items),
                "record_count": len({item["record_id"] for item in items}),
                "template_count": len({item["template_id"] for item in items}),
                "record_ids": sorted(
                    {item["record_id"] for item in items},
                    key=int,
                ),
                "template_ids": sorted(
                    {item["template_id"] for item in items},
                    key=int,
                ),
                "items": items,
            }
        )
    cohorts.sort(
        key=lambda cohort: (
            -cohort["occurrences"],
            cohort["name"],
        )
    )

    candidate_only_mechanisms = {
        "candidate_only_cross_family",
        "candidate_only_exact_vietnam_synonym",
        "candidate_only_context_qualifier",
        "qualifier_outside_boundary",
        "multi_candidate_composite",
    }
    candidate_only_occurrences = sum(
        cohort["occurrences"]
        for cohort in cohorts
        if set(cohort["mechanism"]) <= candidate_only_mechanisms
    )
    return {
        "input": str(input_dir.resolve()),
        "submission": str(submission_zip.resolve()),
        "records": len(texts),
        "near_duplicate_threshold": 0.45,
        "document_templates": len(set(roots.values())),
        "cohort_count": len(cohorts),
        "reviewed_occurrences": sum(
            cohort["occurrences"] for cohort in cohorts
        ),
        "candidate_only_occurrences": candidate_only_occurrences,
        "cohorts": cohorts,
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
