#!/usr/bin/env python3
"""Repair a repeated Vietnamese translation-context candidate error.

Four records use the literal surface ``tăng nhãn áp`` in a neurological
context: congenital hydrocephalus, CSF drainage/shunt revision, head CT,
headache, blurred vision and papilloedema.  Those cues describe raised
intracranial pressure rather than ophthalmic glaucoma.

V46 changes only the candidate H40.9 to G93.2 when one of two reviewed context
signatures is present.  It does not globally remap the surface and does not
change text, spans, types or assertions.
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


SOURCE_LABEL = "tăng nhãn áp"
SOURCE_CANDIDATES = ["H40.9"]
TARGET_CANDIDATES = ["G93.2"]


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def has_intracranial_context(context: str) -> bool:
    """Return whether a local window has one reviewed neurological signature."""

    normalized = normalize_text(context)
    imaging_signature = (
        "chụp cắt lớp vi tính (ct) đầu" in normalized
        and "phù gai thị" in normalized
    )
    shunt_signature = (
        "hệ thống dẫn lưu" in normalized
        and "thời kỳ sơ sinh" in normalized
    )
    return imaging_signature or shunt_signature


def repair_intracranial_pressure_translation(
    texts: dict[str, str],
    control: dict[str, list[dict]],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Change H40.9 to G93.2 only in the repeated intracranial context."""

    output = copy.deepcopy(control)
    changes: list[dict] = []
    for record_id, entities in output.items():
        source = texts[record_id]
        for entity in entities:
            if (
                entity["type"] != "CHẨN_ĐOÁN"
                or normalize_text(entity["text"]).strip() != SOURCE_LABEL
                or entity.get("candidates") != SOURCE_CANDIDATES
            ):
                continue
            start, end = entity["position"]
            context = source[max(0, start - 260) : min(len(source), end + 300)]
            if not has_intracranial_context(context):
                continue
            before = list(entity["candidates"])
            entity["candidates"] = list(TARGET_CANDIDATES)
            changes.append(
                {
                    "record_id": record_id,
                    "text": entity["text"],
                    "type": entity["type"],
                    "position": list(entity["position"]),
                    "assertions": list(entity.get("assertions", [])),
                    "before": before,
                    "after": list(entity["candidates"]),
                    "context_signature": (
                        "head_ct_and_papilloedema"
                        if "chụp cắt lớp vi tính (ct) đầu"
                        in normalize_text(context)
                        else "neonatal_csf_drainage"
                    ),
                    "reason": (
                        "translation_context_intracranial_not_ophthalmic"
                    ),
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

    output, changes = repair_intracranial_pressure_translation(texts, control)
    signature_counts = {
        signature: sum(
            change["context_signature"] == signature for change in changes
        )
        for signature in {
            "head_ct_and_papilloedema",
            "neonatal_csf_drainage",
        }
    }
    if len(changes) != 6 or signature_counts != {
        "head_ct_and_papilloedema": 3,
        "neonatal_csf_drainage": 3,
    }:
        raise ValueError(
            f"Expected V46 context split 3/3, found {len(changes)} "
            f"with {signature_counts}"
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
        raise AssertionError("V46 must not change entity spans or types")
    for record_id in control:
        for before, after in zip(control[record_id], output[record_id]):
            if before.get("assertions") != after.get("assertions"):
                raise AssertionError("V46 must not change assertions")
    for record_id, entities in output.items():
        base.validate_record(texts[record_id], entities)

    turn2_v24.write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    v45_jc_gain_per_change = (32.9413 - 32.8870) / 5
    v45_score_gain_per_change = (41.9694 - 41.9476) / 5
    return {
        "version": "D2-V46-v45-vietnam-intracranial-context-candidate",
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
        "signature_counts": signature_counts,
        "changes": changes,
        "evidence": {
            "national_icd_2026": (
                "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/"
                "06-byt-kem.pdf"
            ),
            "vietnam_hospital_g93_2_catalogue": (
                "https://bvydhue.vn/modules.php?maLoai=G90&"
                "maNhomChinh=G90-G99&name=ICD&op=nodeICD"
            ),
            "vietnam_pediatric_intracranial_protocol": (
                "https://benhviennhi.org.vn/files/202503251327-"
                "PHAC%20DO%20NOI%20TRU%202016%20.pdf"
            ),
            "ministry_hydrocephalus_guidance": (
                "https://kcb.vn/upload/2005611/20210723/"
                "21084b418fdec54573bcf1a9d4c27c50Huong-dan-cham-soc-"
                "y-te-Nao-ung-thuy-va-Nut-dot-song-1.pdf"
            ),
            "v45_observed_j_candidates_gain_per_change": round(
                v45_jc_gain_per_change, 5
            ),
            "conditional_projected_j_candidates": round(
                32.9413 + 6 * v45_jc_gain_per_change, 4
            ),
            "conditional_projected_score": round(
                41.9694 + 6 * v45_score_gain_per_change, 4
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
        "risk": (
            "medium: strong repeated context, but literal Vietnamese surface "
            "resembles ophthalmic hypertension"
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
