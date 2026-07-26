#!/usr/bin/env python3
"""Promoted BamiBERT-gated clinical mention extraction pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

from . import candidates
from . import model_config
from . import rules


def normalize_surface(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def diagnosis_candidates_by_alias() -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    for entry in model_config.PRODUCTION_DIAGNOSES:
        value = entry.get("codes", entry.get("code", ()))
        candidate_values = [value] if isinstance(value, str) else list(value)
        for alias in entry["aliases"]:
            aliases[normalize_surface(str(alias))] = [
                str(candidate) for candidate in candidate_values
            ]
    return aliases


DIAGNOSIS_CANDIDATES = diagnosis_candidates_by_alias()


def _is_polar_question_mention(text: str, entity: dict) -> bool:
    """Return whether a mention fills the focus of a yes/no question."""

    folded = normalize_surface(text)
    start, end = entity["position"]
    clause_start = max(
        folded.rfind("\n", 0, start),
        folded.rfind(".", 0, start),
        folded.rfind("?", 0, start),
        folded.rfind("!", 0, start),
    )
    before = folded[max(clause_start + 1, start - 160) : start]
    after = folded[end : min(len(folded), end + 40)]
    return (
        re.search(r"\bcó\s+phải(?:\s+là)?\s*$", before) is not None
        and re.match(r"\s+(?:thật\s+sự\s+)?không\b", after) is not None
    )


def _refine_entities(
    text: str,
    entities: list[dict],
    *,
    prune_polar_questions: bool,
    trim_symptom_reporting_prefix: bool = False,
) -> list[dict]:
    """Apply promoted pruning and isolated boundary refinements."""

    refined = entities
    if prune_polar_questions:
        refined = [
            entity
            for entity in refined
            if not (
                entity["type"] == "CHẨN_ĐOÁN"
                and _is_polar_question_mention(text, entity)
            )
        ]
    if not trim_symptom_reporting_prefix:
        return refined

    result: list[dict] = []
    reporting_prefix = re.compile(
        r"(?i)^(?:miệng|mồm)\s+(?:cảm\s+)?thấy\s+"
    )
    for entity in refined:
        if entity["type"] != "TRIỆU_CHỨNG":
            result.append(entity)
            continue
        match = reporting_prefix.match(entity["text"])
        if match is None:
            result.append(entity)
            continue
        start, end = entity["position"]
        trimmed_start = start + match.end()
        trimmed = dict(entity)
        trimmed["text"] = text[trimmed_start:end]
        trimmed["position"] = [trimmed_start, end]
        result.append(trimmed)
    return rules.resolve_entities(result)


def extract(
    text: str,
    teacher_spans: list[dict],
    profile: str,
    *,
    prune_polar_questions: bool = True,
) -> list[dict]:
    """Extract one record using rules plus exact-span teacher gating."""

    if profile not in model_config.PROFILES:
        raise ValueError(f"Unknown profile: {profile}")
    symptom_aliases = {
        normalize_surface(alias) for alias in model_config.PROFILES[profile]
    }
    historical, family = rules.section_states(text)
    entities = list(rules.extract(text))
    for teacher_span in teacher_spans:
        start = int(teacher_span["start"])
        end = int(teacher_span["end"])
        entity_type = str(teacher_span["type"])
        if (
            float(teacher_span["confidence"])
            < model_config.TEACHER_CONFIDENCE_MINIMUM
            or not 0 <= start < end <= len(text)
        ):
            continue
        surface = normalize_surface(text[start:end])
        if "text" in teacher_span and teacher_span["text"] != text[start:end]:
            raise ValueError(
                f"Teacher cache does not match source at [{start}, {end})"
            )
        entity_candidates = None
        if entity_type == "TRIỆU_CHỨNG":
            if surface not in symptom_aliases:
                continue
        elif entity_type == "CHẨN_ĐOÁN":
            entity_candidates = DIAGNOSIS_CANDIDATES.get(surface)
            if entity_candidates is None:
                continue
        else:
            continue
        entities.append(
            rules.make_entity(
                text,
                rules.Span(start, end),
                entity_type,
                historical,
                family,
                entity_candidates,
            )
        )
    resolved = rules.resolve_entities(entities)
    upgraded, _ = candidates.upgrade_entities(text, resolved)
    return _refine_entities(
        text,
        upgraded,
        prune_polar_questions=prune_polar_questions,
        trim_symptom_reporting_prefix=profile == "v23",
    )


def _line_occurrences(text: str) -> list[tuple[str, int, int]]:
    """Return non-trivial, whitespace-trimmed lines and their source offsets."""

    occurrences: list[tuple[str, int, int]] = []
    for match in re.finditer(r"[^\r\n]+", text):
        raw = match.group(0)
        value = raw.strip()
        if len(value) < 40:
            continue
        leading = len(raw) - len(raw.lstrip())
        start = match.start() + leading
        occurrences.append((value, start, start + len(value)))
    return occurrences


def _apply_repeated_line_consensus(
    texts: dict[str, str],
    teacher_records: dict[str, list[dict]],
    entities_by_record: dict[str, list[dict]],
) -> int:
    """Repair teacher fragmentation when an identical line provides support.

    Only a production-approved symptom can transfer, and the target occurrence
    must contain a high-confidence teacher fragment anchored to either edge of
    the proposed mention. Assertions are always inferred from the target
    record, never copied from the supporting occurrence.
    """

    allowed_symptoms = {
        normalize_surface(alias) for alias in model_config.PRODUCTION_SYMPTOMS
    }
    grouped: dict[str, list[tuple[str, int, int]]] = {}
    for record_id, text in texts.items():
        for line, start, end in _line_occurrences(text):
            grouped.setdefault(line, []).append((record_id, start, end))

    proposals: set[tuple[str, int, int, str]] = set()
    for occurrences in grouped.values():
        if len({record_id for record_id, _, _ in occurrences}) < 2:
            continue
        signatures: set[tuple[int, int, str]] = set()
        for record_id, line_start, line_end in occurrences:
            text = texts[record_id]
            for entity in entities_by_record[record_id]:
                start, end = entity["position"]
                if (
                    entity["type"] == "TRIỆU_CHỨNG"
                    and line_start <= start < end <= line_end
                    and normalize_surface(text[start:end]) in allowed_symptoms
                ):
                    signatures.add(
                        (start - line_start, end - line_start, entity["type"])
                    )
        for relative_start, relative_end, entity_type in signatures:
            for record_id, line_start, line_end in occurrences:
                start = line_start + relative_start
                end = line_start + relative_end
                if not line_start <= start < end <= line_end:
                    continue
                if any(
                    entity["position"] == [start, end]
                    and entity["type"] == entity_type
                    for entity in entities_by_record[record_id]
                ):
                    continue
                surface = texts[record_id][start:end]
                if normalize_surface(surface) not in allowed_symptoms:
                    continue
                teacher_support = any(
                    str(span["type"]) == entity_type
                    and float(span["confidence"]) >= 0.95
                    and start <= int(span["start"]) < int(span["end"]) <= end
                    and (
                        int(span["start"]) == start
                        or int(span["end"]) == end
                    )
                    for span in teacher_records[record_id]
                )
                if teacher_support:
                    proposals.add((record_id, start, end, entity_type))

    changed_records: set[str] = set()
    for record_id, start, end, entity_type in sorted(proposals):
        text = texts[record_id]
        historical, family = rules.section_states(text)
        entities_by_record[record_id].append(
            rules.make_entity(
                text,
                rules.Span(start, end),
                entity_type,
                historical,
                family,
            )
        )
        changed_records.add(record_id)
    for record_id in changed_records:
        text = texts[record_id]
        resolved = rules.resolve_entities(entities_by_record[record_id])
        entities_by_record[record_id], _ = candidates.upgrade_entities(
            text,
            resolved,
        )
    return len(proposals)


def _load_teacher_records(path: Path) -> tuple[dict[str, list[dict]], dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "records" in payload:
        records = payload["records"]
        metadata = {
            key: value for key, value in payload.items() if key != "records"
        }
    else:
        records = payload
        metadata = {"schema_version": 1}
    if not isinstance(records, dict):
        raise ValueError("Teacher cache records must be a JSON object")
    return records, metadata


def _write_deterministic_zip(output_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for output_file in sorted(
            output_dir.glob("*.json"),
            key=rules.natural_key,
        ):
            info = zipfile.ZipInfo(
                f"output/{output_file.name}",
                (1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, output_file.read_bytes())


def run(
    input_dir: Path,
    output_dir: Path,
    zip_path: Path,
    teacher_cache: Path,
    *,
    profile: str = "production",
) -> dict:
    """Build and summarize a deterministic submission archive."""

    if profile not in model_config.PROFILES:
        raise ValueError(f"Unknown profile: {profile}")
    predictions, cache_metadata = _load_teacher_records(teacher_cache)
    sources = sorted(input_dir.glob("*.txt"), key=rules.natural_key)
    if not sources:
        raise SystemExit(f"Không tìm thấy .txt trong {input_dir}")
    if int(cache_metadata.get("schema_version", 1)) >= 2:
        if cache_metadata.get("model") != model_config.MODEL_ID:
            raise ValueError("Teacher cache was generated by a different model")
        if cache_metadata.get("revision") != model_config.MODEL_REVISION:
            raise ValueError(
                "Teacher cache was generated from a different model revision"
            )
        if (
            float(cache_metadata.get("minimum_token_confidence", 1.0))
            > model_config.TEACHER_CONFIDENCE_MINIMUM
        ):
            raise ValueError(
                "Teacher cache threshold is too high for this profile"
            )
        fingerprint = hashlib.sha256()
        for source in sources:
            fingerprint.update(source.name.encode("utf-8"))
            fingerprint.update(b"\0")
            fingerprint.update(source.read_bytes())
            fingerprint.update(b"\0")
        if cache_metadata.get("input_sha256") != fingerprint.hexdigest():
            raise ValueError("Teacher cache was generated for different input")
    missing_predictions = [
        source.stem for source in sources if source.stem not in predictions
    ]
    if missing_predictions:
        raise ValueError(
            "Teacher cache is missing records: "
            + ", ".join(missing_predictions[:10])
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("*.json"):
        if stale.stem.isdigit():
            stale.unlink()

    texts = {
        source.stem: source.read_text(encoding="utf-8") for source in sources
    }
    if profile == "production":
        control_version = "D2-V16-teacher-diagnosis-precision"
        control_by_record = {
            source.stem: extract(
                texts[source.stem],
                predictions[source.stem],
                "production",
                prune_polar_questions=False,
            )
            for source in sources
        }
        entities_by_record = {
            source.stem: extract(
                texts[source.stem],
                predictions[source.stem],
                "production",
            )
            for source in sources
        }
    else:
        control_version = "D2-V21-question-diagnosis-pruning"
        control_by_record = {
            source.stem: extract(
                texts[source.stem],
                predictions[source.stem],
                "production",
            )
            for source in sources
        }
        _apply_repeated_line_consensus(
            texts,
            predictions,
            control_by_record,
        )
        entities_by_record = {
            source.stem: extract(
                texts[source.stem],
                predictions[source.stem],
                profile,
            )
            for source in sources
        }
    consensus_entities_added = _apply_repeated_line_consensus(
        texts,
        predictions,
        entities_by_record,
    )

    counts = {entity_type: 0 for entity_type in sorted(rules.OFFICIAL_TYPES)}
    assertion_counts = {
        assertion: 0 for assertion in sorted(rules.OFFICIAL_ASSERTIONS)
    }
    total = 0
    changed_records = 0
    added = 0
    removed = 0
    common_fields_changed = 0
    for source in sources:
        text = texts[source.stem]
        control = control_by_record[source.stem]
        entities = entities_by_record[source.stem]
        rules.validate_record(text, entities)

        key = lambda entity: (
            entity["position"][0],
            entity["position"][1],
            entity["type"],
        )
        before = {key(entity): entity for entity in control}
        after = {key(entity): entity for entity in entities}
        record_added = len(after.keys() - before.keys())
        record_removed = len(before.keys() - after.keys())
        record_common_fields_changed = sum(
            before[entity_key] != after[entity_key]
            for entity_key in before.keys() & after.keys()
        )
        if record_added or record_removed or record_common_fields_changed:
            changed_records += 1
        added += record_added
        removed += record_removed
        common_fields_changed += record_common_fields_changed
        for entity in entities:
            counts[entity["type"]] += 1
            for assertion in entity["assertions"]:
                assertion_counts[assertion] += 1
        total += len(entities)
        (output_dir / f"{source.stem}.json").write_text(
            rules.format_json(entities),
            encoding="utf-8",
            newline="\n",
        )

    _write_deterministic_zip(output_dir, zip_path)
    version = {
        "production": "D2-V21-question-diagnosis-pruning",
        "v23": "D2-V23-symptom-boundary-trim",
    }[profile]
    return {
        "version": version,
        "profile": profile,
        "control": control_version,
        "teacher_model": model_config.MODEL_ID,
        "teacher_revision": model_config.MODEL_REVISION,
        "teacher_confidence_minimum": (
            model_config.TEACHER_CONFIDENCE_MINIMUM
        ),
        "teacher_cache": cache_metadata,
        "records": len(sources),
        "changed_records": changed_records,
        "entities": total,
        "entities_added": added,
        "entities_removed": removed,
        "common_entity_fields_changed": common_fields_changed,
        "consensus_entities_added": consensus_entities_added,
        "by_type": counts,
        "by_assertion": assertion_counts,
        "zip": zip_path.name,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--teacher-cache", type=Path, required=True)
    parser.add_argument(
        "--profile",
        choices=sorted(model_config.PROFILES),
        default="production",
    )
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
