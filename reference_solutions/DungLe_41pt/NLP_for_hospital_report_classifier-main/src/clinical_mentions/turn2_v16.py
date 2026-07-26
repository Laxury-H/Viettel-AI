#!/usr/bin/env python3
"""D2-V16 model-gated version of the V15 distilled symptom expansion.

Unlike V15's portable lexicon profile, V16 adds an alias only when the
fine-tuned Vietnamese medical NER teacher also predicts that exact span with
high confidence.  The cache consumed by this module is generated inference,
not a hand-authored list of public record positions.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
import zipfile
from pathlib import Path

from . import turn2_v11
from . import turn2_v15
from . import turn2_v9 as base


CURATED_SAFE_SYMPTOMS = turn2_v15.PRECISION_SYMPTOMS + (
    "đỏ gan bàn tay",
    "run rấy",
    "dịch rò rỉ",
    "tê bì vùng trán phải",
    "rối loạn thị giác",
    "lưỡi dâu tây",
    "bong da",
    "khó chịu vùng ngực",
    "bồn chồn",
    "bứt rứt trong người",
    "giảm ham muốn",
    "nóng phần tinh hoàn",
    "tê bì",
    "thị giác bị nhòe",
    "mù vĩnh viễn",
    "dịch rỉ huyết thanh",
    "rụng tóc toàn bộ",
    "khả năng trí óc giảm",
)

CURATED_CORE_SYMPTOMS = turn2_v15.PRECISION_SYMPTOMS + (
    "bồn chồn",
    "bứt rứt trong người",
    "nóng phần tinh hoàn",
    "tê bì",
    "mù vĩnh viễn",
    "dịch rỉ huyết thanh",
)


PROFILES = {
    "diagnosis": (),
    "diagnosis-adenocarcinoma-precision": turn2_v15.PRECISION_SYMPTOMS,
    "diagnosis-blood-cancer-precision": turn2_v15.PRECISION_SYMPTOMS,
    "diagnosis-curated-core": CURATED_CORE_SYMPTOMS,
    "diagnosis-curated-safe": CURATED_SAFE_SYMPTOMS,
    "diagnosis-core99": (),
    "diagnosis-core99-precision": turn2_v15.PRECISION_SYMPTOMS,
    "diagnosis-core99-safe": turn2_v15.SAFE_SYMPTOMS,
    "diagnosis-core99-specific-extended-safe": turn2_v15.SAFE_SYMPTOMS,
    "diagnosis-core995": (),
    "diagnosis-core995-precision": turn2_v15.PRECISION_SYMPTOMS,
    "diagnosis-extended": (),
    "diagnosis-extended-precision": turn2_v15.PRECISION_SYMPTOMS,
    "diagnosis-extended-boundary": (),
    "diagnosis-max": (),
    "diagnosis-precision": turn2_v15.PRECISION_SYMPTOMS,
    "diagnosis-precision-empty": turn2_v15.PRECISION_SYMPTOMS,
    "diagnosis-specific-extended": (),
    "diagnosis-specific-extended-precision": turn2_v15.PRECISION_SYMPTOMS,
    "diagnosis-specific-extended-safe": turn2_v15.SAFE_SYMPTOMS,
    "diagnosis-tight-extended-curated": CURATED_SAFE_SYMPTOMS,
    "diagnosis-tight-extended-precision": turn2_v15.PRECISION_SYMPTOMS,
    "diagnosis-tight-adenocarcinoma-precision": turn2_v15.PRECISION_SYMPTOMS,
    "diagnosis-vctm-precision": turn2_v15.PRECISION_SYMPTOMS,
    "boundary": turn2_v15.BOUNDARY_SYMPTOMS,
    "precision": turn2_v15.PRECISION_SYMPTOMS,
    "precision-empty": turn2_v15.PRECISION_SYMPTOMS,
    "safe": turn2_v15.SAFE_SYMPTOMS,
    "safe-empty": turn2_v15.SAFE_SYMPTOMS,
    "safe-boundary": turn2_v15.SAFE_SYMPTOMS + turn2_v15.BOUNDARY_SYMPTOMS,
    "safe-diagnosis": turn2_v15.SAFE_SYMPTOMS,
    "full": turn2_v15.SAFE_SYMPTOMS + turn2_v15.BOUNDARY_SYMPTOMS,
    "top10-precision": turn2_v15.PRECISION_SYMPTOMS,
    "top10-safe": turn2_v15.SAFE_SYMPTOMS,
    "top10-aggressive": turn2_v15.SAFE_SYMPTOMS + turn2_v15.BOUNDARY_SYMPTOMS,
    "top10-max": turn2_v15.SAFE_SYMPTOMS + turn2_v15.BOUNDARY_SYMPTOMS,
}
EMPTY_ASSERTION_PROFILES = frozenset(
    {"precision-empty", "safe-empty", "diagnosis-precision-empty"}
)
DIAGNOSIS_PROFILES = frozenset(
    {
        "diagnosis",
        "diagnosis-adenocarcinoma-precision",
        "diagnosis-blood-cancer-precision",
        "diagnosis-curated-core",
        "diagnosis-curated-safe",
        "diagnosis-core99",
        "diagnosis-core99-precision",
        "diagnosis-core99-safe",
        "diagnosis-core99-specific-extended-safe",
        "diagnosis-core995",
        "diagnosis-core995-precision",
        "diagnosis-extended",
        "diagnosis-extended-precision",
        "diagnosis-extended-boundary",
        "diagnosis-max",
        "diagnosis-precision",
        "diagnosis-precision-empty",
        "diagnosis-specific-extended",
        "diagnosis-specific-extended-precision",
        "diagnosis-specific-extended-safe",
        "diagnosis-tight-extended-curated",
        "diagnosis-tight-extended-precision",
        "diagnosis-tight-adenocarcinoma-precision",
        "diagnosis-vctm-precision",
        "safe-diagnosis",
        "full",
        "top10-precision",
        "top10-safe",
        "top10-aggressive",
        "top10-max",
    }
)
EXTENDED_DIAGNOSIS_PROFILES = frozenset(
    {
        "diagnosis-extended",
        "diagnosis-extended-precision",
        "diagnosis-extended-boundary",
        "diagnosis-max",
        "top10-precision",
        "top10-safe",
        "top10-aggressive",
        "top10-max",
    }
)
SPECIFIC_EXTENDED_DIAGNOSIS_PROFILES = frozenset(
    {
        "diagnosis-specific-extended",
        "diagnosis-specific-extended-precision",
        "diagnosis-specific-extended-safe",
        "diagnosis-core99-specific-extended-safe",
    }
)
TIGHT_EXTENDED_DIAGNOSIS_PROFILES = frozenset(
    {
        "diagnosis-tight-extended-curated",
        "diagnosis-tight-extended-precision",
    }
)
DIAGNOSIS_BOUNDARY_PROFILES = frozenset(
    {
        "diagnosis-extended-boundary",
        "diagnosis-max",
        "top10-precision",
        "top10-safe",
        "top10-aggressive",
        "top10-max",
    }
)
AGGRESSIVE_DIAGNOSIS_PROFILES = frozenset({"diagnosis-max", "top10-max"})
MINIMUM_CONFIDENCE = 0.98
DIAGNOSIS_MINIMUM_BY_PROFILE = {
    "diagnosis-core99": 0.99,
    "diagnosis-core99-precision": 0.99,
    "diagnosis-core99-safe": 0.99,
    "diagnosis-core99-specific-extended-safe": 0.99,
    "diagnosis-core995": 0.995,
    "diagnosis-core995-precision": 0.995,
}
SPECIFIC_EXTENDED_ALIASES = frozenset(
    {"bệnh ung thư máu", "bệnh huyết áp", "vctm", "tắc mạch"}
)
TIGHT_EXTENDED_ALIASES = frozenset({"bệnh ung thư máu", "vctm", "tắc mạch"})
SELECTIVE_EXTENDED_ALIASES_BY_PROFILE = {
    "diagnosis-adenocarcinoma-precision": frozenset(
        {"ung thư biểu mô tuyến"}
    ),
    "diagnosis-blood-cancer-precision": frozenset({"bệnh ung thư máu"}),
    "diagnosis-tight-adenocarcinoma-precision": frozenset(
        {"bệnh ung thư máu", "vctm", "tắc mạch", "ung thư biểu mô tuyến"}
    ),
    "diagnosis-vctm-precision": frozenset({"vctm"}),
}


def diagnosis_candidates_by_alias(profile: str) -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    entries = list(turn2_v15.SAFE_DIAGNOSES)
    if profile in EXTENDED_DIAGNOSIS_PROFILES:
        entries.extend(turn2_v15.EXTENDED_DIAGNOSES)
    if profile in SPECIFIC_EXTENDED_DIAGNOSIS_PROFILES:
        entries.extend(
            entry
            for entry in turn2_v15.EXTENDED_DIAGNOSES
            if any(
                normalize_surface(str(alias)) in SPECIFIC_EXTENDED_ALIASES
                for alias in entry["aliases"]
            )
        )
    if profile in TIGHT_EXTENDED_DIAGNOSIS_PROFILES:
        entries.extend(
            entry
            for entry in turn2_v15.EXTENDED_DIAGNOSES
            if any(
                normalize_surface(str(alias)) in TIGHT_EXTENDED_ALIASES
                for alias in entry["aliases"]
            )
        )
    if profile in SELECTIVE_EXTENDED_ALIASES_BY_PROFILE:
        selected = SELECTIVE_EXTENDED_ALIASES_BY_PROFILE[profile]
        entries.extend(
            entry
            for entry in turn2_v15.EXTENDED_DIAGNOSES
            if any(
                normalize_surface(str(alias)) in selected
                for alias in entry["aliases"]
            )
        )
    if profile in AGGRESSIVE_DIAGNOSIS_PROFILES:
        entries.extend(turn2_v15.AGGRESSIVE_DIAGNOSES)
    if profile in DIAGNOSIS_BOUNDARY_PROFILES:
        entries.extend(turn2_v15.DIAGNOSIS_BOUNDARIES)
    for entry in entries:
        value = entry.get("codes", entry.get("code", ()))
        candidates = [value] if isinstance(value, str) else list(value)
        for alias in entry["aliases"]:
            aliases[normalize_surface(str(alias))] = [
                str(candidate) for candidate in candidates
            ]
    return aliases


def normalize_surface(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def extract(text: str, teacher_spans: list[dict], profile: str) -> list[dict]:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}")
    allowed = {normalize_surface(alias) for alias in PROFILES[profile]}
    diagnosis_candidates = diagnosis_candidates_by_alias(profile)
    historical, family = base.section_states(text)
    entities = list(base.extract(text))
    for teacher_span in teacher_spans:
        start = int(teacher_span["start"])
        end = int(teacher_span["end"])
        entity_type = teacher_span["type"]
        minimum_confidence = (
            0.95
            if profile in AGGRESSIVE_DIAGNOSIS_PROFILES
            and entity_type == "CHẨN_ĐOÁN"
            else (
                DIAGNOSIS_MINIMUM_BY_PROFILE.get(profile, MINIMUM_CONFIDENCE)
                if entity_type == "CHẨN_ĐOÁN"
                else MINIMUM_CONFIDENCE
            )
        )
        if (
            float(teacher_span["confidence"]) < minimum_confidence
            or not 0 <= start < end <= len(text)
        ):
            continue
        surface = normalize_surface(text[start:end])
        candidates = None
        if entity_type == "TRIỆU_CHỨNG":
            if surface not in allowed:
                continue
        elif entity_type == "CHẨN_ĐOÁN" and profile in DIAGNOSIS_PROFILES:
            candidates = diagnosis_candidates.get(surface)
            if candidates is None:
                continue
        else:
            continue
        entity = base.make_entity(
            text,
            base.Span(start, end),
            entity_type,
            historical,
            family,
            candidates,
        )
        if entity_type == "TRIỆU_CHỨNG" and profile in EMPTY_ASSERTION_PROFILES:
            entity["assertions"] = []
        entities.append(entity)
    resolved = base.resolve_entities(entities)
    upgraded, _ = turn2_v11.upgrade_entities(
        text,
        resolved,
        enabled_groups=turn2_v15.V14_CANDIDATE_GROUPS,
    )
    return upgraded


def run(
    input_dir: Path,
    output_dir: Path,
    zip_path: Path,
    teacher_cache: Path,
    *,
    profile: str,
) -> dict:
    predictions = json.loads(teacher_cache.read_text(encoding="utf-8"))
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    if not sources:
        raise SystemExit(f"Không tìm thấy .txt trong {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("*.json"):
        if stale.stem.isdigit():
            stale.unlink()

    counts = {entity_type: 0 for entity_type in sorted(base.OFFICIAL_TYPES)}
    assertion_counts = {
        assertion: 0 for assertion in sorted(base.OFFICIAL_ASSERTIONS)
    }
    total = 0
    changed_records = 0
    added = 0
    removed = 0
    common_fields_changed = 0
    for source in sources:
        text = source.read_text(encoding="utf-8")
        control, _ = turn2_v11.upgrade_entities(
            text,
            base.extract(text),
            enabled_groups=turn2_v15.V14_CANDIDATE_GROUPS,
        )
        entities = extract(text, predictions.get(source.stem, []), profile)
        base.validate_record(text, entities)
        key = lambda entity: (
            entity["position"][0],
            entity["position"][1],
            entity["type"],
        )
        before = {key(entity): entity for entity in control}
        after = {key(entity): entity for entity in entities}
        record_added = len(after.keys() - before.keys())
        record_removed = len(before.keys() - after.keys())
        if record_added or record_removed:
            changed_records += 1
        added += record_added
        removed += record_removed
        common_fields_changed += sum(
            before[entity_key] != after[entity_key]
            for entity_key in before.keys() & after.keys()
        )
        for entity in entities:
            counts[entity["type"]] += 1
            for assertion in entity["assertions"]:
                assertion_counts[assertion] += 1
        total += len(entities)
        (output_dir / f"{source.stem}.json").write_text(
            base.format_json(entities),
            encoding="utf-8",
            newline="\n",
        )

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for output_file in sorted(output_dir.glob("*.json"), key=base.natural_key):
            info = zipfile.ZipInfo(
                f"output/{output_file.name}",
                (1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, output_file.read_bytes())

    return {
        "version": f"D2-V16-teacher-{profile}",
        "profile": profile,
        "control": "D2-V14-metoprolol",
        "teacher_confidence_minimum": MINIMUM_CONFIDENCE,
        "records": len(sources),
        "changed_records": changed_records,
        "entities": total,
        "entities_added": added,
        "entities_removed": removed,
        "common_entity_fields_changed": common_fields_changed,
        "by_type": counts,
        "by_assertion": assertion_counts,
        "zip": str(zip_path.resolve()),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--teacher-cache", type=Path, required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="precision")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    summary = run(
        args.input,
        args.output,
        args.zip,
        args.teacher_cache,
        profile=args.profile,
    )
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
