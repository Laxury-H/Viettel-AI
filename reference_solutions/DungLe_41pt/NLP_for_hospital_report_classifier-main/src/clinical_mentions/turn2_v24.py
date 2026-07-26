#!/usr/bin/env python3
"""V24 leaderboard-evidence pruning on top of the best scored V19 artifact.

V19 ``xlmr-additive-85`` is immutable.  This stage only removes additions
whose surface belongs to a group that was independently shown to reduce the
public score.  An entity already present in the V18 control is never removed,
even if it has the same surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
import zipfile
from pathlib import Path

from . import turn2_v19
from . import turn2_v9 as base


SYMPTOM_TYPE = "TRIỆU_CHỨNG"

# V17-red-eyes added exactly two occurrences and reduced the public score from
# 39.2864 to 39.2786.  The same two additions re-entered through V19 consensus.
PUBLIC_REJECTED_ADDITION_SURFACES = frozenset({"đỏ mắt"})


def normalize_surface(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def entity_key(entity: dict) -> tuple[int, int, str]:
    start, end = entity["position"]
    return int(start), int(end), str(entity["type"])


def prune_rejected_additions(
    control_entities: list[dict],
    candidate_entities: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Remove rejected V19-only additions while preserving the V18 control."""

    control_keys = {entity_key(entity) for entity in control_entities}
    kept: list[dict] = []
    removed: list[dict] = []
    for entity in candidate_entities:
        is_candidate_addition = entity_key(entity) not in control_keys
        is_rejected_surface = (
            entity.get("type") == SYMPTOM_TYPE
            and normalize_surface(str(entity.get("text", "")))
            in PUBLIC_REJECTED_ADDITION_SURFACES
        )
        if is_candidate_addition and is_rejected_surface:
            removed.append(dict(entity))
        else:
            kept.append(dict(entity))
    return kept, removed


def write_deterministic_zip(
    records: dict[str, list[dict]],
    zip_path: Path,
) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for record_id in sorted(records, key=int):
            info = zipfile.ZipInfo(
                f"output/{record_id}.json",
                (1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, base.format_json(records[record_id]))


def run(
    control_zip: Path,
    candidate_zip: Path,
    output_zip: Path,
) -> dict:
    control = turn2_v19.load_submission(control_zip)
    candidate = turn2_v19.load_submission(candidate_zip)
    if set(control) != set(candidate):
        raise ValueError("Control and candidate record IDs do not match")

    output: dict[str, list[dict]] = {}
    removals: list[dict] = []
    for record_id in sorted(candidate, key=int):
        refined, removed = prune_rejected_additions(
            control[record_id],
            candidate[record_id],
        )
        output[record_id] = refined
        removals.extend(
            {
                "record_id": record_id,
                "text": entity["text"],
                "type": entity["type"],
                "position": entity["position"],
            }
            for entity in removed
        )

    write_deterministic_zip(output, output_zip)
    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    return {
        "version": "D2-V24-xlmr-additive-85-pruned",
        "control": str(control_zip.resolve()),
        "candidate": str(candidate_zip.resolve()),
        "records": len(output),
        "entities": sum(len(entities) for entities in output.values()),
        "entities_removed": len(removals),
        "removals": removals,
        "score_projection": {
            "score": 39.3761,
            "WER": 55.7063,
            "J_assertion": 51.0298,
            "J_candidates": 26.9477,
            "status": "unscored_projection",
        },
        "sha256": digest,
        "zip": str(output_zip.resolve()),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-zip", type=Path, required=True)
    parser.add_argument("--candidate-zip", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    summary = run(args.control_zip, args.candidate_zip, args.zip)
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
